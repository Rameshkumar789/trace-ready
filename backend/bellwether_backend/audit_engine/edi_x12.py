"""Deterministic X12 EDI parsing — 856 (ASN) first-class.

"What comes through the door, not what goes into their system": suppliers send far more on
the wire than most ERPs ingest. This parser turns raw X12 into the same canonical facts the
audit engine grades, so an ASN can be validated pre-receipt and diffed against the ERP.

No LLM: X12 is positional. Separators are read from the ISA envelope, never assumed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictEdiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class EdiSegment(StrictEdiModel):
    index: int
    tag: str
    elements: list[str] = Field(default_factory=list)


class EdiTransaction(StrictEdiModel):
    transaction_set: str  # e.g. "856"
    control_number: str | None = None
    segments: list[EdiSegment] = Field(default_factory=list)


class EdiInterchange(StrictEdiModel):
    sender: str | None = None
    receiver: str | None = None
    interchange_date: str | None = None
    component_separator: str | None = None  # ISA16; splits composite data elements
    transactions: list[EdiTransaction] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


# X12 unit-of-measure codes -> engine units
_UOM = {"LB": "lb", "KG": "kg", "CA": "case", "EA": "each", "PC": "each", "BX": "case", "CT": "case"}

# DTM qualifiers that carry a ship/receive date
_DTM_SHIP = {"011", "017", "067", "002"}

# LIN/REF qualifiers
_PRODUCT_ID_QUALIFIERS = {"UP", "EN", "UK", "GTIN", "VN", "SK", "IN"}
_LOT_QUALIFIERS = {"LT", "LV", "SE", "BT"}


def looks_like_x12(data: bytes) -> bool:
    return data.lstrip()[:3] == b"ISA"


def parse_x12(data: bytes) -> EdiInterchange:
    text = data.decode("utf-8", errors="replace").lstrip("﻿ \r\n")
    issues: list[str] = []
    if not text.startswith("ISA"):
        return EdiInterchange(issues=["not an X12 interchange (missing ISA header)"])
    if len(text) < 106:
        return EdiInterchange(issues=["truncated ISA envelope"])
    element_sep = text[3]
    # ISA is fixed-width: component separator at 104, segment terminator at 105.
    component_sep = text[104]
    segment_term = text[105]
    body = text
    raw_segments = [seg.strip("\r\n ") for seg in body.split(segment_term)]
    segments: list[EdiSegment] = []
    for index, raw in enumerate(raw_segments):
        if not raw:
            continue
        parts = raw.split(element_sep)
        segments.append(EdiSegment(index=index, tag=parts[0].strip(), elements=[p.strip() for p in parts[1:]]))

    isa = next((s for s in segments if s.tag == "ISA"), None)
    interchange = EdiInterchange(
        sender=(isa.elements[5].strip() if isa and len(isa.elements) > 5 else None),
        receiver=(isa.elements[7].strip() if isa and len(isa.elements) > 7 else None),
        interchange_date=(isa.elements[8].strip() if isa and len(isa.elements) > 8 else None),
        component_separator=component_sep,
        issues=issues,
    )

    current: EdiTransaction | None = None
    for segment in segments:
        if segment.tag == "ST":
            current = EdiTransaction(
                transaction_set=segment.elements[0] if segment.elements else "",
                control_number=segment.elements[1] if len(segment.elements) > 1 else None,
            )
            interchange.transactions.append(current)
        elif segment.tag == "SE":
            if current is not None and segment.elements:
                try:
                    declared = int(segment.elements[0])
                    actual = len(current.segments) + 2  # + ST and SE themselves
                    if declared != actual:
                        issues.append(
                            f"transaction {current.control_number or '?'}: SE declares {declared} segments, found {actual}"
                        )
                except ValueError:
                    pass
            current = None
        elif current is not None:
            current.segments.append(segment)
    return interchange


def _format_date(value: str | None) -> str | None:
    if not value:
        return None
    digits = value.strip()
    if len(digits) == 8 and digits.isdigit():
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    if len(digits) == 6 and digits.isdigit():
        return f"20{digits[0:2]}-{digits[2:4]}-{digits[4:6]}"
    return None


def edi_856_to_lines(transaction: EdiTransaction, *, component_separator: str | None = None) -> list[dict[str, Any]]:
    """Flatten an 856's HL hierarchy into item lines with canonical facts.

    Shipment-level facts (dates, parties, BOL reference) inherit down to every item line.
    Handles shipment->order->item and shipment->order->tare/pack->item shapes: any non-item
    HL level just accumulates context. Composite data elements (qualifier<sep>value inside
    one element, ISA16 separator) are split before qualifier scanning. Free-text fields
    containing the element separator itself are truncated by positional X12 — inherent to
    the format.
    """

    def _decompose(value: str | None) -> list[str]:
        if value is None:
            return []
        if component_separator and component_separator in value:
            return [part for part in value.split(component_separator)]
        return [value]
    shipment_context: dict[str, list[str]] = {}
    lines: list[dict[str, Any]] = []
    current_line: dict[str, list[str]] | None = None
    declared_count: int | None = None

    def _push(target: dict[str, list[str]], key: str, value: str | None) -> None:
        if value is None or str(value).strip() == "":
            return
        target.setdefault(key, []).append(str(value).strip())

    for segment in transaction.segments:
        tag, elements = segment.tag, segment.elements
        get = lambda i: elements[i] if len(elements) > i else None  # noqa: E731

        if tag == "HL":
            level_code = (get(2) or "").upper()
            if level_code == "I":
                current_line = {}
                lines.append({"facts": current_line, "hl_index": segment.index})
            # S/O/T/P levels accumulate into shipment context; item facts win on conflict.
        elif tag == "BSN":
            _push(shipment_context, "reference_record_no", get(1))
            _push(shipment_context, "reference_record_type", "ASN")
            date = _format_date(get(2))
            if date:
                _push(shipment_context, "date_you_shipped_the_food", date)
        elif tag == "DTM" and (get(0) or "") in _DTM_SHIP:
            date = _format_date(get(1))
            if date:
                _push(current_line if current_line is not None else shipment_context, "date_you_shipped_the_food", date)
        elif tag == "REF":
            qualifier = (get(0) or "").upper()
            if qualifier in _LOT_QUALIFIERS:
                _push(current_line if current_line is not None else shipment_context, "traceability_lot_code", get(1))
            elif qualifier == "BM":
                # The transaction's document type stays "ASN" (from BSN); the BOL is an
                # additional reference number, not a second conflicting document type.
                _push(shipment_context, "reference_record_no", get(1))
        elif tag == "PER":
            # Administrative contact: PER*IC*name*TE*phone*EM*email
            for qualifier_index in range(1, len(elements) - 1):
                qualifier = (elements[qualifier_index] or "").upper()
                value = elements[qualifier_index + 1] if len(elements) > qualifier_index + 1 else None
                if qualifier == "TE":
                    _push(shipment_context, "phone_number", value)
                elif qualifier == "EM":
                    _push(shipment_context, "email", value)
        elif tag == "N1":
            role = (get(0) or "").upper()
            name, id_value = get(1), get(3)
            if role == "SF":
                _push(shipment_context, "source_location_name", name)
                _push(shipment_context, "source_location_id", id_value)
            elif role == "ST":
                _push(shipment_context, "destination_location_name", name)
                _push(shipment_context, "destination_location_id", id_value)
            elif role in {"SU", "VN"}:
                _push(shipment_context, "partner_name", name)
                _push(shipment_context, "partner_id", id_value)
        elif tag == "LIN" and current_line is not None:
            # Expand composite elements (qualifier<ISA16>value packed into one element) so
            # the qualifier/value pair scan sees them.
            expanded: list[str] = []
            for element in elements:
                expanded.extend(_decompose(element))
            for qualifier_index in range(1, len(expanded) - 1, 2):
                qualifier = (expanded[qualifier_index] or "").upper()
                value = expanded[qualifier_index + 1] if len(expanded) > qualifier_index + 1 else None
                if qualifier in _PRODUCT_ID_QUALIFIERS:
                    _push(current_line, "product_id", value)
                elif qualifier in _LOT_QUALIFIERS:
                    _push(current_line, "traceability_lot_code", value)
        elif tag == "SN1" and current_line is not None:
            _push(current_line, "quantity", get(1))
            uom = (get(2) or "").upper()
            _push(current_line, "unit", _UOM.get(uom, uom.lower() or None))
        elif tag == "SLN" and current_line is not None:
            _push(current_line, "quantity", get(3))
            uom = (get(4) or "").upper()
            _push(current_line, "unit", _UOM.get(uom, uom.lower() or None))
        elif tag == "PID" and current_line is not None:
            description = get(4) or get(3)
            _push(current_line, "product_name", description)
        elif tag == "CTT":
            try:
                declared_count = int(get(0) or "")
            except ValueError:
                declared_count = None

    resolved: list[dict[str, Any]] = []
    for position, line in enumerate(lines, start=1):
        facts: dict[str, list[str]] = {}
        for key, values in shipment_context.items():
            facts[key] = list(values)
        for key, values in line["facts"].items():
            facts[key] = list(values)  # item-level wins over shipment context
        resolved.append({"line_number": position, "facts": facts})

    issues: list[str] = []
    if declared_count is not None and declared_count != len(lines):
        issues.append(f"CTT declares {declared_count} line items, found {len(lines)}")
    if resolved:
        resolved[0]["transaction_issues"] = issues
    return resolved
