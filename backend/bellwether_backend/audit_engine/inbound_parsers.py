"""P3 — inbound trading-partner format normalizers.

Each parser converts a partner-supplied document (EDI 856 ASN, EPCIS event XML, GDSN
product master XML) into a list of flat "rows" — dicts of canonical column name -> value —
using the same canonical column vocabulary the workbook ingest already understands
(see FIELD_ALIASES in customer_evidence). customer_evidence then turns each row/cell into a
CustomerEvidenceRecord via the shared _evidence_record helper, so everything downstream
(field mapping, entity/event graph, CTE classification, rule execution) is format-agnostic.

These are deliberately pragmatic readers that extract the FSMA-204-relevant KDEs, not full
EDI/EPCIS validators.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

Row = dict[str, str]


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _edi_date(value: str) -> str:
    """X12 date CCYYMMDD (optionally with time) -> ISO date."""
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return value


def parse_edi_856(text: str) -> list[Row]:
    """X12 856 Advance Ship Notice -> one row per shipped line item."""
    # Segment terminator is conventionally '~' (or newlines); elements by '*', sub-elements ':'.
    raw = text.replace("\r", "").replace("\n", "~")
    segments = [seg for seg in raw.split("~") if seg.strip()]
    ship_from = ship_to = ""
    ship_date = ""
    shipment_id = ""
    rows: list[Row] = []
    current: Row | None = None

    def flush() -> None:
        nonlocal current
        if current and (current.get("product_id") or current.get("traceability_lot_code")):
            current.setdefault("event_type", "shipping")
            current.setdefault("event_datetime", ship_date)
            current["from_partner_id"] = current.get("from_partner_id") or ship_from
            current["to_partner_id"] = current.get("to_partner_id") or ship_to
            current.setdefault("event_id", f"{shipment_id or 'ASN'}-{len(rows) + 1}")
            rows.append(current)
        current = None

    for segment in segments:
        elements = segment.split("*")
        tag = elements[0].strip().upper()
        if tag == "BSN":
            shipment_id = _clean(elements[2]) if len(elements) > 2 else ""
            if len(elements) > 3:
                ship_date = _edi_date(_clean(elements[3]))
        elif tag == "DTM" and len(elements) > 2:
            ship_date = _edi_date(_clean(elements[2]))
        elif tag == "N1" and len(elements) > 1:
            qualifier = _clean(elements[1]).upper()
            name = _clean(elements[2]) if len(elements) > 2 else ""
            ident = _clean(elements[4]) if len(elements) > 4 else ""
            party = ident or name
            if qualifier == "SF":
                ship_from = party
            elif qualifier == "ST":
                ship_to = party
        elif tag == "HL" and len(elements) > 3 and _clean(elements[3]).upper() == "I":
            flush()
            current = {}
        elif tag == "LIN" and current is not None:
            # LIN segments alternate qualifier/value pairs; pull a GTIN-ish product id.
            for index in range(2, len(elements) - 1, 2):
                qualifier = _clean(elements[index]).upper()
                value = _clean(elements[index + 1])
                if qualifier in {"UP", "EN", "UK", "GT"}:
                    current["product_id"] = value
                elif qualifier in {"PI", "VN"}:
                    current.setdefault("product_name", value)
        elif tag == "SN1" and current is not None:
            if len(elements) > 2:
                current["quantity"] = _clean(elements[2])
            if len(elements) > 3:
                current["unit"] = _clean(elements[3])
        elif tag == "REF" and current is not None and len(elements) > 2 and _clean(elements[1]).upper() == "LT":
            current["traceability_lot_code"] = _clean(elements[2])
        elif tag == "PID" and current is not None and len(elements) > 5:
            current.setdefault("product_name", _clean(elements[5]))
    flush()
    return rows


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _findall_local(root: ET.Element, name: str) -> list[ET.Element]:
    return [el for el in root.iter() if _localname(el.tag) == name]


def _first_text(parent: ET.Element, name: str) -> str:
    for el in parent.iter():
        if _localname(el.tag) == name and el.text:
            return el.text.strip()
    return ""


_BIZSTEP_TO_CTE = {
    "shipping": "shipping",
    "receiving": "receiving",
    "commissioning": "initial_packing",
    "packing": "initial_packing",
    "transforming": "transformation",
}


def parse_epcis_xml(text: str) -> list[Row]:
    """EPCIS event XML -> rows (ObjectEvent -> shipping/receiving; TransformationEvent -> transform)."""
    root = ET.fromstring(text)
    rows: list[Row] = []
    index = 0
    for event in root.iter():
        local = _localname(event.tag)
        if local not in {"ObjectEvent", "TransformationEvent", "AggregationEvent"}:
            continue
        index += 1
        event_time = _first_text(event, "eventTime")
        bizstep = _first_text(event, "bizStep").rsplit(":", 1)[-1].lower()
        location = _first_text(event, "id") or _first_text(event, "bizLocation")
        row: Row = {
            "event_id": f"EPCIS-{index}",
            "event_datetime": event_time,
            "event_type": _BIZSTEP_TO_CTE.get(bizstep, bizstep or "shipping"),
        }
        if location:
            row["location_id"] = location
        if local == "TransformationEvent":
            row["event_type"] = "transformation"
            in_list = _epc_list(event, "inputEPCList")
            out_list = _epc_list(event, "outputEPCList")
            if in_list:
                row["source_lot_or_tlc"] = in_list[0]
            if out_list:
                row["output_lot_or_tlc"] = out_list[0]
        else:
            epcs = _epc_list(event, "epcList")
            if epcs:
                row["traceability_lot_code"] = epcs[0]
        rows.append(row)
    return rows


def _epc_list(event: ET.Element, list_name: str) -> list[str]:
    for el in event.iter():
        if _localname(el.tag) == list_name:
            return [child.text.strip() for child in el if child.text and child.text.strip()]
    return []


def parse_gdsn_xml(text: str) -> list[Row]:
    """GDSN trade-item master XML -> product rows (GTIN + description)."""
    root = ET.fromstring(text)
    rows: list[Row] = []
    for index, item in enumerate(_findall_local(root, "tradeItem") or _findall_local(root, "TradeItem"), start=1):
        gtin = _first_text(item, "gtin")
        description = _first_text(item, "descriptionShort") or _first_text(item, "tradeItemDescription") or _first_text(item, "description")
        if not (gtin or description):
            continue
        row: Row = {"event_id": f"GDSN-{index}", "event_type": "product_master"}
        if gtin:
            row["product_id"] = gtin
        if description:
            row["product_name"] = description
        rows.append(row)
    return rows
