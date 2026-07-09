"""Trading-partner scorecard: which partners, products, and fields fail — ranked.

The supplier gap analysis from the advisory calls: "here's the list of people who don't give
me the information I need, and the products I don't get it for." Counterparties are resolved
per event through partner ids, then location->owner joins from master data, then business
master names (whitespace/float-artifact tolerant). Events whose destination can't be
resolved land in an explicit unknown bucket instead of disappearing.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

UNKNOWN_PARTNER = "__unknown_destination__"

# KDE slugs a partner-facing record is graded on (presence per event row). Only genuine
# per-event Subpart S KDEs: partner phone/email are NOT shipping/receiving KDEs under the
# current eCFR, so grading them would manufacture bad bands (they are tracked separately
# as informational contact coverage below).
GRADED_FIELDS = (
    "traceability_lot_code",
    "product_name",
    "quantity",
    "unit",
    "event_datetime",
    "reference_record_type",
    "reference_record_no",
)

# Informational only - never affects fill rate or bands.
CONTACT_FIELDS = ("phone_number", "email", "contact_person")

BAND_THRESHOLDS = (
    ("A", 0.95),
    ("B", 0.85),
    ("C", 0.70),
    ("D", 0.0),
)


def _norm(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def _band(fill_rate: float, integrity_gaps: int) -> str:
    if integrity_gaps > 0:
        return "D"
    for band, threshold in BAND_THRESHOLDS:
        if fill_rate >= threshold:
            return band
    return "D"


class _PartnerResolver:
    def __init__(self, entity_graph: Any):
        self.location_owner: dict[str, str] = {}
        self.location_name: dict[str, str] = {}
        for location in getattr(entity_graph, "locations", []):
            owner = (location.attributes or {}).get("owner")
            key = _norm(location.entity_id)
            if owner:
                self.location_owner[key] = str(owner)
            self.location_name[key] = location.name
        self.counterparty_by_id: dict[str, Any] = {_norm(c.entity_id): c for c in getattr(entity_graph, "counterparties", [])}
        self.counterparty_by_name: dict[str, Any] = {_norm(c.name): c for c in getattr(entity_graph, "counterparties", [])}

    def resolve(self, raw_id: str | None) -> tuple[str, str]:
        """-> (partner_key, partner_display_name). Falls back to the unknown bucket."""
        key = _norm(raw_id)
        if not key:
            return UNKNOWN_PARTNER, "Unknown destination"
        owner = self.location_owner.get(key)
        if owner:
            return _norm(owner), owner
        counterparty = self.counterparty_by_id.get(key) or self.counterparty_by_name.get(key)
        if counterparty is not None:
            return _norm(counterparty.name), counterparty.name
        if key in self.location_name:
            name = self.location_name[key]
            return _norm(name), name
        return UNKNOWN_PARTNER, "Unknown destination"


def _operator_name(events: dict[str, Any], resolver: _PartnerResolver) -> str:
    """The operator = the most common owner of the locations this file's events act from."""
    counts: dict[str, int] = defaultdict(int)
    for event in events.values():
        actor = _norm(getattr(event, "actor_id", None))
        owner = resolver.location_owner.get(actor)
        if owner:
            counts[_norm(owner)] += 1
    if counts:
        # Deterministic tie-break (sorted key order); co-packer/3PL sites with multiple
        # brands can tie here, and dict-order ties are non-reproducible.
        return max(sorted(counts), key=lambda key: counts[key])
    return ""


def build_partner_scorecard(
    *,
    events: dict[str, Any],
    entity_graph: Any,
    row_facts: dict[str, dict[str, Any]],
    lot_integrity_checks: list[Any] = (),
) -> dict[str, Any]:
    resolver = _PartnerResolver(entity_graph)
    operator_key = _operator_name(events, resolver)

    lot_gap_lots = {check.lot for check in lot_integrity_checks if check.status == "gap" and check.lot}

    partners: dict[str, dict[str, Any]] = {}

    def _partner(partner_key: str, display: str) -> dict[str, Any]:
        entry = partners.get(partner_key)
        if entry is None:
            entry = {
                "partner_key": partner_key,
                "name": display,
                "internal": bool(operator_key) and partner_key == operator_key,
                "direction_counts": defaultdict(int),
                "event_count": 0,
                "field_filled": defaultdict(int),
                "field_expected": defaultdict(int),
                "contact_filled": defaultdict(int),
                "contact_expected": defaultdict(int),
                "products": defaultdict(lambda: {"events": 0, "missing_fields": defaultdict(int)}),
                "integrity_gap_lots": set(),
            }
            partners[partner_key] = entry
        return entry

    def _facts_for(event: Any) -> dict[str, list[str]]:
        merged: dict[str, list[str]] = defaultdict(list)
        for part in str(getattr(event, "source_row_key", "")).split("+"):
            row = row_facts.get(part)
            if row:
                for key, values in row["facts"].items():
                    merged[key].extend(values)
        return merged

    landing_events = 0
    for event in events.values():
        ctes = set(getattr(event, "classified_ctes", None) or [])
        if not ctes:
            claim = getattr(event, "event_type_claim", None)
            ctes = {claim} if claim else set()
        if "shipping" in ctes:
            raw_partner, direction = getattr(event, "to_partner_id", None), "ships_to"
        elif "first_land_based_receiving" in ctes:
            # A landing is the operator's own record of receiving from a fishing vessel;
            # the vessel/harvest documentation is graded by the FLR KDE contract, not the
            # partner scorecard. Counting these as "unknown counterparty" manufactured a
            # false undocumented-source alarm on the whole first-receiver population.
            landing_events += 1
            if not getattr(event, "from_partner_id", None):
                continue
            raw_partner, direction = getattr(event, "from_partner_id", None), "receives_from"
        elif "receiving" in ctes:
            raw_partner, direction = getattr(event, "from_partner_id", None), "receives_from"
        else:
            continue  # internal processing events don't grade a partner

        partner_key, display = resolver.resolve(raw_partner)
        entry = _partner(partner_key, display)
        entry["event_count"] += 1
        entry["direction_counts"][direction] += 1

        facts = _facts_for(event)
        product = getattr(event, "product_name", None) or getattr(event, "product_id", None) or "(unknown product)"
        product_entry = entry["products"][str(product)]
        product_entry["events"] += 1
        for field in GRADED_FIELDS:
            entry["field_expected"][field] += 1
            values = [value for value in facts.get(field, []) if str(value).strip()]
            if values:
                entry["field_filled"][field] += 1
            else:
                product_entry["missing_fields"][field] += 1
        for field in CONTACT_FIELDS:
            entry["contact_expected"][field] += 1
            if any(str(value).strip() for value in facts.get(field, [])):
                entry["contact_filled"][field] += 1
        lot = getattr(event, "lot_or_tlc", None)
        if lot and lot in lot_gap_lots:
            entry["integrity_gap_lots"].add(lot)

    # ------------------------------------------------------------------ rollup
    partner_rows: list[dict[str, Any]] = []
    for entry in partners.values():
        expected = sum(entry["field_expected"].values())
        filled = sum(entry["field_filled"].values())
        fill_rate = round(filled / expected, 4) if expected else 0.0
        missing_by_field = {
            field: entry["field_expected"][field] - entry["field_filled"][field]
            for field in GRADED_FIELDS
            if entry["field_expected"][field] - entry["field_filled"][field] > 0
        }
        products = [
            {
                "product": product,
                "events": data["events"],
                "missing_fields": dict(sorted(data["missing_fields"].items(), key=lambda item: -item[1])),
            }
            for product, data in sorted(entry["products"].items(), key=lambda item: -item[1]["events"])
        ]
        band = _band(fill_rate, len(entry["integrity_gap_lots"]))
        contact_expected = sum(entry["contact_expected"].values())
        contact_rate = round(sum(entry["contact_filled"].values()) / contact_expected, 4) if contact_expected else None
        partner_rows.append(
            {
                "partner_key": entry["partner_key"],
                "name": entry["name"],
                "internal": entry["internal"],
                "unknown_bucket": entry["partner_key"] == UNKNOWN_PARTNER,
                "events": entry["event_count"],
                "directions": dict(entry["direction_counts"]),
                "kde_fill_rate": fill_rate,
                "contact_info_rate": contact_rate,  # informational; never affects the band
                "missing_by_field": dict(sorted(missing_by_field.items(), key=lambda item: -item[1])),
                "integrity_gap_lots": sorted(entry["integrity_gap_lots"])[:15],
                "quality_band": band,
                "products": products[:25],
            }
        )
    partner_rows.sort(key=lambda row: ({"D": 0, "C": 1, "B": 2, "A": 3}[row["quality_band"]], -row["events"]))

    external = [row for row in partner_rows if not row["internal"] and not row["unknown_bucket"]]
    unknown = next((row for row in partner_rows if row["unknown_bucket"]), None)
    return {
        "operator": operator_key or None,
        "partner_count": len(external),
        "internal_transfer_events": sum(row["events"] for row in partner_rows if row["internal"]),
        "unknown_destination_events": unknown["events"] if unknown else 0,
        "landing_events": landing_events,
        "band_counts": {
            band: sum(1 for row in external if row["quality_band"] == band) for band in ("A", "B", "C", "D")
        },
        "partners": partner_rows,
    }


def scorecard_summary_findings(scorecard: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic summary findings for the worst partners + the unknown bucket."""
    findings: list[dict[str, Any]] = []
    for row in scorecard.get("partners", []):
        if row["internal"] or row["unknown_bucket"]:
            continue
        if row["quality_band"] == "D":
            worst = ", ".join(list(row["missing_by_field"])[:4]) or "multiple KDE fields"
            findings.append(
                {
                    "finding_type": "partner_data_quality",
                    "severity": "medium",
                    "status": "needs_review",
                    "message": (
                        f"Trading partner {row['name']} grades D: KDE fill rate "
                        f"{row['kde_fill_rate']:.0%} across {row['events']} event(s), recurring gaps in "
                        f"{worst}"
                        + (f"; {len(row['integrity_gap_lots'])} lot integrity gap(s)" if row["integrity_gap_lots"] else "")
                        + ". Engage this partner on the missing data elements."
                    ),
                    "details": row,
                }
            )
    if scorecard.get("unknown_destination_events"):
        findings.append(
            {
                "finding_type": "partner_data_quality",
                "severity": "medium",
                "status": "needs_review",
                "message": (
                    f"{scorecard['unknown_destination_events']} event(s) have a counterparty that "
                    "cannot be resolved to any known partner or location. For shipments this breaks "
                    "the immediate-subsequent-recipient link; for receiving-side events it means the "
                    "source (supplier, vessel, or harvester) is undocumented."
                ),
                "details": {"unknown_destination_events": scorecard["unknown_destination_events"]},
            }
        )
    return findings
