"""Door-vs-database diff: what the supplier actually sent vs what survived into the system.

John's caution from the advisory call: a compliant supplier may ship every KDE on the
ASN/BOL while the ERP silently drops the fields it has no columns for. Given inbound
document lines and the parsed system events, this reports, per lot, the KDEs that came
through the door but are absent (or different) in the system of record.
"""

from __future__ import annotations

from typing import Any

# Fields worth diffing door-vs-database (canonical slugs present on inbound docs).
DIFF_FIELDS = (
    "traceability_lot_code",
    "product_id",
    "product_name",
    "quantity",
    "unit",
    "date_you_shipped_the_food",
    "received_date",
    "source_location_id",
    "source_location_name",
    "destination_location_id",
    "reference_record_type",
    "reference_record_no",
    "phone_number",
    "email",
)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def diff_inbound_vs_erp(
    *,
    inbound_lines: list[dict[str, Any]],
    events: dict[str, Any],
    row_facts: dict[str, dict[str, Any]],
    source_label: str = "inbound document",
) -> list[dict[str, Any]]:
    """-> finding dicts: {finding_type, severity, status, message, details}."""
    erp_by_lot: dict[str, dict[str, list[str]]] = {}
    for event in events.values():
        lot = getattr(event, "lot_or_tlc", None)
        if not lot:
            continue
        merged: dict[str, list[str]] = {}
        for part in str(getattr(event, "source_row_key", "")).split("+"):
            row = row_facts.get(part)
            if row:
                for key, values in row["facts"].items():
                    merged.setdefault(key, []).extend(values)
        existing = erp_by_lot.setdefault(_norm(lot), {})
        for key, values in merged.items():
            existing.setdefault(key, []).extend(values)

    findings: list[dict[str, Any]] = []
    unmatched_lots: list[str] = []
    for line in inbound_lines:
        facts = line.get("facts") or {}
        lots = [value for value in facts.get("traceability_lot_code", []) if str(value).strip()]
        if not lots:
            continue
        lot_key = _norm(lots[0])
        erp_facts = erp_by_lot.get(lot_key)
        if erp_facts is None:
            unmatched_lots.append(lots[0])
            continue
        dropped: list[str] = []
        conflicting: list[dict[str, Any]] = []
        for field in DIFF_FIELDS:
            inbound_values = [v for v in facts.get(field, []) if str(v).strip()]
            if not inbound_values:
                continue
            erp_values = [v for v in erp_facts.get(field, []) if str(v).strip()]
            if not erp_values:
                dropped.append(field)
            elif field in {"quantity", "traceability_lot_code"} and not (
                {_norm(v) for v in inbound_values} & {_norm(v) for v in erp_values}
            ):
                conflicting.append({"field": field, "inbound": inbound_values[:3], "system": erp_values[:3]})
        if dropped:
            findings.append(
                {
                    "finding_type": "inbound_erp_mismatch",
                    "severity": "medium",
                    "status": "needs_review",
                    "message": (
                        f"Lot {lots[0]}: the supplier's {source_label} carries {len(dropped)} data "
                        f"element(s) that never made it into the system of record "
                        f"({', '.join(dropped[:6])}). The supplier is sending KDEs your system is "
                        "dropping."
                    ),
                    "details": {"lot": lots[0], "dropped_fields": dropped, "source": source_label},
                }
            )
        for conflict in conflicting:
            findings.append(
                {
                    "finding_type": "inbound_erp_mismatch",
                    "severity": "high",
                    "status": "gap",
                    "message": (
                        f"Lot {lots[0]}: {conflict['field']} on the supplier's {source_label} "
                        f"({', '.join(map(str, conflict['inbound']))}) disagrees with the system of "
                        f"record ({', '.join(map(str, conflict['system']))})."
                    ),
                    "details": {"lot": lots[0], **conflict, "source": source_label},
                }
            )
    if unmatched_lots:
        findings.append(
            {
                "finding_type": "inbound_erp_mismatch",
                "severity": "medium",
                "status": "needs_review",
                "message": (
                    f"{len(unmatched_lots)} lot(s) on the supplier's {source_label} have no matching "
                    f"record in the system at all (e.g. {', '.join(unmatched_lots[:5])}). Either the "
                    "receipt was never recorded or the lot codes were rewritten on entry."
                ),
                "details": {"unmatched_lots": unmatched_lots[:25], "source": source_label},
            }
        )
    return findings
