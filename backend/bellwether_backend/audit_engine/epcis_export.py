"""EPCIS 2.0 JSON-LD export: turn audited events into standards-native traceability data.

The "export clean data" bridge: once the audit has canonical, cited events, emitting GS1
EPCIS 2.0 events lets the customer load their (now validated) data into any EPCIS-speaking
platform (iFoodDS, ReposiTrak, Wholechain, ...). Shapes follow the GS1 EPCIS 2.0 JSON-LD
examples and the GS1 US "EPCIS Recommendations for FSMA 204 CTEs" mapping:

- shipping / receiving -> ObjectEvent (bizStep shipping/receiving, action OBSERVE)
- transformation      -> TransformationEvent (inputs from consumed lots when linkable)
- FLR / initial pack / harvest / cooling -> ObjectEvent (action ADD, commissioning-style)

Identifiers: GTIN-14 product ids become EPC class LGTINs; everything else falls back to
readable non-EPC identifiers under the FSMA extension namespace so no data is dropped.
"""

from __future__ import annotations

import re
from typing import Any

EPCIS_CONTEXT = "https://ref.gs1.org/standards/epcis/2.0.0/epcis-context.jsonld"
FSMA_EXT_NS = "traceready"

_CTE_BIZSTEP = {
    "shipping": "shipping",
    "receiving": "receiving",
    "first_land_based_receiving": "receiving",
    "initial_packing": "packing",
    "harvesting": "commissioning",
    "cooling": "storing",
}


def _lgtin_or_fallback(product_id: str | None, lot: str | None) -> dict[str, Any] | None:
    if not lot:
        return None
    digits = re.sub(r"[\s-]", "", str(product_id or ""))
    if digits.isdigit() and len(digits) == 14:
        # GS1 Digital Link class-level identifier for GTIN + lot
        return {"epcClass": f"https://id.gs1.org/01/{digits}/10/{lot}", "quantity": None}
    return {"epcClass": f"urn:{FSMA_EXT_NS}:product:{product_id or 'unknown'}:lot:{lot}", "quantity": None}


def _quantity_element(product_id: str | None, lot: str | None, quantity: str | None, unit: str | None) -> dict[str, Any] | None:
    element = _lgtin_or_fallback(product_id, lot)
    if element is None:
        return None
    try:
        element["quantity"] = float(str(quantity).replace(",", "")) if quantity else None
    except ValueError:
        element["quantity"] = None
    if unit:
        element["uom"] = {"lb": "LBR", "kg": "KGM", "case": "CS", "each": "EA"}.get(str(unit).lower(), str(unit).upper()[:3])
    if element["quantity"] is None:
        element.pop("quantity")
    return element


def _event_facts(event: Any, row_facts: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for part in str(getattr(event, "source_row_key", "")).split("+"):
        row = row_facts.get(part)
        if row:
            for key, values in row["facts"].items():
                merged.setdefault(key, []).extend(values)
    return merged


def _first(facts: dict[str, list[str]], key: str) -> str | None:
    for value in facts.get(key, []):
        if str(value).strip():
            return str(value)
    return None


def build_epcis_document(
    *,
    events: dict[str, Any],
    row_facts: dict[str, dict[str, Any]],
    operator: str | None = None,
) -> dict[str, Any]:
    epcis_events: list[dict[str, Any]] = []
    skipped: list[str] = []

    for event in events.values():
        ctes = set(getattr(event, "classified_ctes", None) or [])
        facts = _event_facts(event, row_facts)
        lot = getattr(event, "lot_or_tlc", None)
        product_id = getattr(event, "product_id", None)
        when = getattr(event, "event_datetime", None)
        base: dict[str, Any] = {
            "eventTime": f"{when}T00:00:00Z" if when else None,
            "eventTimeZoneOffset": "+00:00",
            f"{FSMA_EXT_NS}:sourceEventId": event.event_id,
        }

        if "transformation" in ctes:
            output_lot = getattr(event, "output_lot_or_tlc", None) or lot
            source_lot = getattr(event, "source_lot_or_tlc", None)
            output_element = _quantity_element(product_id, output_lot, _first(facts, "quantity"), _first(facts, "unit"))
            if output_element is None:
                skipped.append(event.event_id)
                continue
            epcis_event = {
                **base,
                "type": "TransformationEvent",
                "bizStep": "commissioning",
                "outputQuantityList": [output_element],
            }
            if source_lot:
                input_element = _quantity_element(None, source_lot, None, None)
                if input_element:
                    epcis_event["inputQuantityList"] = [input_element]
            else:
                epcis_event[f"{FSMA_EXT_NS}:note"] = "input lots not linkable from the source export (see lot_transformation_linkage finding)"
            epcis_events.append(epcis_event)
            continue

        cte = next((c for c in ("shipping", "receiving", "first_land_based_receiving", "initial_packing", "harvesting", "cooling") if c in ctes), None)
        if cte is None:
            skipped.append(event.event_id)
            continue
        element = _quantity_element(product_id, lot, _first(facts, "quantity"), _first(facts, "unit"))
        if element is None:
            skipped.append(event.event_id)
            continue
        epcis_event = {
            **base,
            "type": "ObjectEvent",
            "action": "OBSERVE" if cte in {"shipping", "receiving"} else "ADD",
            "bizStep": _CTE_BIZSTEP[cte],
            "disposition": "in_transit" if cte == "shipping" else "in_progress",
            "quantityList": [element],
        }
        source_location = _first(facts, "source_location_id") or getattr(event, "actor_id", None)
        destination_location = _first(facts, "destination_location_id") or getattr(event, "to_partner_id", None)
        if source_location:
            epcis_event["sourceList"] = [{"type": "location", "source": f"urn:{FSMA_EXT_NS}:location:{source_location}"}]
        if destination_location:
            epcis_event["destinationList"] = [{"type": "location", "destination": f"urn:{FSMA_EXT_NS}:location:{destination_location}"}]
        reference_no = _first(facts, "reference_record_no")
        reference_type = _first(facts, "reference_record_type")
        if reference_no:
            epcis_event["bizTransactionList"] = [
                {"type": (reference_type or "inv").lower(), "bizTransaction": f"urn:{FSMA_EXT_NS}:doc:{reference_no}"}
            ]
        epcis_events.append(epcis_event)

    return {
        "@context": [EPCIS_CONTEXT, {FSMA_EXT_NS: f"urn:{FSMA_EXT_NS}:ns#"}],
        "type": "EPCISDocument",
        "schemaVersion": "2.0",
        "creationDate": None,  # stamped by the caller (kept null for reproducible artifacts)
        f"{FSMA_EXT_NS}:operator": operator,
        "epcisBody": {"eventList": epcis_events},
        f"{FSMA_EXT_NS}:stats": {
            "exportedEvents": len(epcis_events),
            "skippedEvents": len(skipped),
            "skippedEventIds": skipped[:25],
        },
    }
