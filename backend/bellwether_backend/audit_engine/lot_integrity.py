"""Lot & lineage integrity checks (deterministic, cited).

The checks nobody runs today, per the ENSESO4Food advisory calls: backward lineage for every
shipped lot (with export-window awareness), forward linkage, duplicate/static TLC signals
(with the multi-SKU transformation carve-out), mass balance, lot-format profiling learned
from the operator's own data (never hardcoded), and date plausibility for lots whose format
embeds a date.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictLotModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class LotIntegrityCheck(StrictLotModel):
    check_id: str
    check_type: str  # backward_lineage | forward_linkage | lot_format | duplicate_tlc | mass_balance | date_ordering
    status: str  # linked | pass | gap | needs_review
    severity: str  # high | medium
    lot: str | None = None
    event_id: str | None = None
    cte: str | None = None
    reason: str
    citation_section: str
    related_event_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


ORIGIN_CTES = {"receiving", "first_land_based_receiving", "initial_packing", "harvesting"}
PLACEHOLDER_LOT_VALUES = {"", "unknown", "n/a", "na", "null", "none", "-", "tbd", "pending", "?"}

_DATE_RUN = re.compile(r"\d{6,8}")


def _is_real_lot(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() not in PLACEHOLDER_LOT_VALUES and len(value.strip()) >= 3


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def lot_embedded_date(lot: str) -> date | None:
    """Best-effort date embedded in a lot code. Only calendar-plausible parses count.

    Handles digit runs longer than the date itself (e.g. "2509190205" = YYMMDD + sequence)
    by probing the leading/trailing 6- and 8-digit windows of each run.
    """
    windows: list[str] = []
    for run in re.findall(r"\d{6,}", lot):
        for size in (8, 6):
            if len(run) >= size:
                windows.append(run[:size])
                if len(run) > size:
                    windows.append(run[-size:])
    for window in windows:
        candidates: list[date] = []
        patterns = ("%Y%m%d", "%m%d%Y") if len(window) == 8 else ("%y%m%d", "%m%d%y")
        for pattern in patterns:
            try:
                candidates.append(datetime.strptime(window, pattern).date())
            except ValueError:
                continue
        plausible = [d for d in candidates if date(2015, 1, 1) <= d <= date(2032, 12, 31)]
        if plausible:
            # Prefer the first (most conventional) parse order.
            return plausible[0]
    return None


def lot_signature(lot: str) -> str:
    signature = re.sub(r"[A-Za-z]+", "A", lot)
    return re.sub(r"\d+", "9", signature)


def _event_ctes(event: Any) -> list[str]:
    ctes = list(getattr(event, "classified_ctes", None) or [])
    if ctes:
        return ctes
    claim = getattr(event, "event_type_claim", None)
    return [claim] if claim else []


def _quantity_and_unit(facts: dict[str, list[str]]) -> tuple[float | None, str | None]:
    quantity = None
    for value in facts.get("quantity", []):
        try:
            quantity = float(str(value).replace(",", ""))
            break
        except ValueError:
            continue
    unit_values = facts.get("unit") or []
    unit = str(unit_values[0]).lower() if unit_values else None
    return quantity, unit


def _norm_id(values: list[str] | None) -> str:
    for value in values or []:
        text = str(value).strip()
        if text:
            return text.lower()
    return ""


def _merged_facts(row_facts: dict[str, dict[str, Any]], source_row_key: str) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = defaultdict(list)
    for part in source_row_key.split("+"):
        row = row_facts.get(part)
        if row:
            for key, values in row["facts"].items():
                merged[key].extend(values)
    return merged


def compute_export_window(events: dict[str, Any]) -> tuple[str | None, str | None]:
    dates = sorted(d for d in (_parse_iso_date(getattr(e, "event_datetime", None)) for e in events.values()) if d)
    if not dates:
        return None, None
    return dates[0].isoformat(), dates[-1].isoformat()


def check_lot_integrity(
    *,
    events: dict[str, Any],
    row_facts: dict[str, dict[str, Any]],
    export_window: tuple[str | None, str | None] | None = None,
) -> list[LotIntegrityCheck]:
    checks: list[LotIntegrityCheck] = []

    def _add(**kwargs: Any) -> None:
        checks.append(LotIntegrityCheck(check_id=f"lot-check-{len(checks) + 1:04d}", **kwargs))

    window_start, window_end = export_window or compute_export_window(events)
    window_start_date = _parse_iso_date(window_start)

    # ------------------------------------------------------------------ index the events
    origin_events_by_lot: dict[str, list[Any]] = defaultdict(list)
    output_events_by_lot: dict[str, list[Any]] = defaultdict(list)
    shipped_events_by_lot: dict[str, list[Any]] = defaultdict(list)
    consumed_lots: set[str] = set()
    lot_products: dict[str, set[str]] = defaultdict(set)
    operator_assigned_lots: list[str] = []

    self_receive_events: list[Any] = []
    for event in events.values():
        ctes = set(_event_ctes(event))
        lot = event.lot_or_tlc if _is_real_lot(event.lot_or_tlc) else None
        output_lot = event.output_lot_or_tlc if _is_real_lot(event.output_lot_or_tlc) else None
        source_lot = event.source_lot_or_tlc if _is_real_lot(event.source_lot_or_tlc) else None
        product = event.product_id or event.product_name
        if lot and product:
            lot_products[lot].add(str(product))
        if output_lot and product:
            lot_products[output_lot].add(str(product))
        if ctes & ORIGIN_CTES and lot:
            # A "receive" from the operator's own location into the same location is a stock
            # movement, not new material entering: it must not count as a lineage origin or
            # inflate origin quantities, and it deserves its own review item.
            facts = _merged_facts(row_facts, event.source_row_key)
            source_location = _norm_id(facts.get("source_location_id"))
            destination_location = _norm_id(facts.get("destination_location_id"))
            if "receiving" in ctes and source_location and source_location == destination_location:
                self_receive_events.append(event)
            else:
                origin_events_by_lot[lot].append(event)
                if not (ctes & {"receiving"}):
                    operator_assigned_lots.append(lot)
        if "transformation" in ctes and output_lot:
            output_events_by_lot[output_lot].append(event)
            operator_assigned_lots.append(output_lot)
        if "transformation" in ctes and source_lot:
            consumed_lots.add(source_lot)
        if "shipping" in ctes and lot:
            shipped_events_by_lot[lot].append(event)

    for event in self_receive_events:
        _add(
            check_type="self_receive",
            status="needs_review",
            severity="medium",
            lot=event.lot_or_tlc,
            cte="receiving",
            event_id=event.event_id,
            reason=(
                f"Receiving record for lot {event.lot_or_tlc} shows the same location as both "
                "source and destination - a self-receive. This is a stock movement, not food "
                "entering from a trading partner, and cannot serve as the lot's origin record."
            ),
            citation_section="21 CFR 1.1345",
            related_event_ids=[event.event_id],
            evidence_ids=_first_evidence([event]),
        )

    known_origin_lots = set(origin_events_by_lot) | set(output_events_by_lot)

    # ------------------------------------------------------------------ backward lineage
    for lot in sorted(shipped_events_by_lot):
        ship_events = shipped_events_by_lot[lot]
        related = [e.event_id for e in ship_events[:20]]
        evidence = _first_evidence(ship_events)
        if lot in known_origin_lots:
            _add(
                check_type="backward_lineage",
                status="linked",
                severity="medium",
                lot=lot,
                cte="shipping",
                event_id=related[0],
                reason="Shipped lot traces back to an origin record in this dataset.",
                citation_section="21 CFR 1.1340",
                related_event_ids=related,
                evidence_ids=evidence,
            )
            continue
        embedded = lot_embedded_date(lot)
        if embedded and window_start_date and embedded < window_start_date:
            _add(
                check_type="backward_lineage",
                status="needs_review",
                severity="medium",
                lot=lot,
                cte="shipping",
                event_id=related[0],
                reason=(
                    f"Shipped lot {lot} has no origin record in this dataset, but its lot code "
                    f"pattern dates it to {embedded.isoformat()}, before the export window starts "
                    f"({window_start}). The origin records likely exist in a prior period - "
                    "request them rather than treating the chain as broken."
                ),
                citation_section="21 CFR 1.1345",
                related_event_ids=related,
                evidence_ids=evidence,
                details={"embeddedDate": embedded.isoformat(), "windowStart": window_start, "reasonCode": "records_predate_window"},
            )
            continue
        _add(
            check_type="backward_lineage",
            status="gap",
            severity="high",
            lot=lot,
            cte="shipping",
            event_id=related[0],
            reason=(
                f"Shipped lot {lot} has no receiving, first-land-based-receiving, initial packing, "
                "or transformation record establishing where it came from. Backward traceability "
                "for these shipments cannot be demonstrated."
            ),
            citation_section="21 CFR 1.1345",
            related_event_ids=related,
            evidence_ids=evidence,
        )

    # ------------------------------------------------------------------ forward linkage
    unmoved = sorted(lot for lot in known_origin_lots if lot not in shipped_events_by_lot and lot not in consumed_lots)
    if unmoved:
        _add(
            check_type="forward_linkage",
            status="needs_review",
            severity="medium",
            reason=(
                f"{len(unmoved)} originated lot(s) never appear in a shipping or transformation "
                "record. This may be inventory still on hand, or missing forward records - "
                "confirm which."
            ),
            citation_section="21 CFR 1.1340",
            details={"lots": unmoved[:25], "totalCount": len(unmoved)},
        )

    # ------------------------------------------------------------------ duplicate TLC across products
    for lot in sorted(lot_products):
        products = lot_products[lot]
        if len(products) < 2:
            continue
        output_events = output_events_by_lot.get(lot, [])
        output_products = {str(e.product_id or e.product_name) for e in output_events}
        related_events = [e.event_id for e in (output_events + shipped_events_by_lot.get(lot, []))][:20]
        if output_events and len(output_products) > 1:
            _add(
                check_type="duplicate_tlc",
                status="needs_review",
                severity="medium",
                lot=lot,
                cte="transformation",
                event_id=related_events[0] if related_events else None,
                reason=(
                    f"Lot {lot} is assigned to {len(products)} different products produced by the "
                    "same transformation. A lot-level recall cannot distinguish these products. "
                    "Confirm whether this multi-product lot assignment is intended, or assign a "
                    "distinct TLC per product."
                ),
                citation_section="21 CFR 1.1350",
                related_event_ids=related_events,
                evidence_ids=_first_evidence(output_events),
                details={"products": sorted(products)[:10]},
            )
        else:
            _add(
                check_type="duplicate_tlc",
                status="gap",
                severity="high",
                lot=lot,
                event_id=related_events[0] if related_events else None,
                reason=(
                    f"Lot {lot} appears on {len(products)} different products with no transformation "
                    "explaining the reuse. Reused lot codes across products defeat recall precision "
                    "and can indicate duplicated or unreliable lot data."
                ),
                citation_section="21 CFR 1.1320",
                related_event_ids=related_events,
                details={"products": sorted(products)[:10]},
            )

    # ------------------------------------------------------------------ mass balance
    for lot in sorted(shipped_events_by_lot):
        if lot not in known_origin_lots:
            continue  # no origin data in window; lineage checks already cover it
        origin_total: dict[str, float] = defaultdict(float)
        shipped_total: dict[str, float] = defaultdict(float)
        for event in origin_events_by_lot.get(lot, []) + output_events_by_lot.get(lot, []):
            quantity, unit = _quantity_and_unit(_merged_facts(row_facts, event.source_row_key))
            if quantity is not None:
                origin_total[unit or "?"] += quantity
        for event in shipped_events_by_lot[lot]:
            quantity, unit = _quantity_and_unit(_merged_facts(row_facts, event.source_row_key))
            if quantity is not None:
                shipped_total[unit or "?"] += quantity
        if not origin_total or not shipped_total:
            continue
        if set(origin_total) != set(shipped_total):
            _add(
                check_type="mass_balance",
                status="needs_review",
                severity="medium",
                lot=lot,
                reason=(
                    f"Lot {lot} uses different units of measure across origin and shipping records "
                    f"({', '.join(sorted(origin_total))} vs {', '.join(sorted(shipped_total))}); "
                    "quantity reconciliation cannot be verified automatically."
                ),
                citation_section="21 CFR 1.1340",
                details={"originByUnit": dict(origin_total), "shippedByUnit": dict(shipped_total)},
            )
            continue
        for unit in origin_total:
            if shipped_total[unit] > origin_total[unit] * 1.001:
                related = [e.event_id for e in shipped_events_by_lot[lot]][:20]
                _add(
                    check_type="mass_balance",
                    status="gap",
                    severity="medium",
                    lot=lot,
                    event_id=related[0],
                    reason=(
                        f"Lot {lot} shipped {shipped_total[unit]:g} {unit} but only "
                        f"{origin_total[unit]:g} {unit} was received or produced on paper - "
                        f"{shipped_total[unit] - origin_total[unit]:g} {unit} shipped with no "
                        "documented origin quantity."
                    ),
                    citation_section="21 CFR 1.1340",
                    related_event_ids=related,
                    evidence_ids=_first_evidence(shipped_events_by_lot[lot]),
                    details={"shipped": shipped_total[unit], "originated": origin_total[unit], "unit": unit},
                )

    # ------------------------------------------------------------------ date ordering + embedded-date plausibility
    for lot in sorted(shipped_events_by_lot):
        ship_dates = sorted(d for d in (_parse_iso_date(e.event_datetime) for e in shipped_events_by_lot[lot]) if d)
        origin_dates = sorted(
            d
            for d in (
                _parse_iso_date(e.event_datetime)
                for e in origin_events_by_lot.get(lot, []) + output_events_by_lot.get(lot, [])
            )
            if d
        )
        if ship_dates and origin_dates and ship_dates[0] < origin_dates[0]:
            _add(
                check_type="date_ordering",
                status="needs_review",
                severity="medium",
                lot=lot,
                reason=(
                    f"Lot {lot} was shipped on {ship_dates[0].isoformat()}, before its earliest "
                    f"origin record ({origin_dates[0].isoformat()}). One of the dates is likely "
                    "wrong, or records are missing."
                ),
                citation_section="21 CFR 1.1340",
                details={"firstShipped": ship_dates[0].isoformat(), "firstOriginated": origin_dates[0].isoformat()},
            )
        embedded = lot_embedded_date(lot)
        if embedded and ship_dates and embedded > ship_dates[0] and (embedded - ship_dates[0]) <= timedelta(days=366):
            _add(
                check_type="date_ordering",
                status="needs_review",
                severity="medium",
                lot=lot,
                reason=(
                    f"Lot {lot} embeds the date {embedded.isoformat()} in its code but was shipped "
                    f"on {ship_dates[0].isoformat()}, before that date. The lot code or the ship "
                    "date is implausible."
                ),
                citation_section="21 CFR 1.1320",
                details={"embeddedDate": embedded.isoformat(), "firstShipped": ship_dates[0].isoformat(), "reasonCode": "lot_date_implausible"},
            )

    # ------------------------------------------------------------------ lot format profiler
    signatures = Counter(lot_signature(lot) for lot in operator_assigned_lots if lot)
    total = sum(signatures.values())
    if total >= 5:
        dominant: set[str] = set()
        covered = 0
        for signature, count in signatures.most_common():
            if covered / total >= 0.9:
                break
            if count >= 5:
                dominant.add(signature)
            covered += count
        if dominant:
            outliers = sorted({lot for lot in operator_assigned_lots if lot_signature(lot) not in dominant})
            if outliers:
                _add(
                    check_type="lot_format",
                    status="needs_review",
                    severity="medium",
                    reason=(
                        f"{len(outliers)} operator-assigned lot code(s) do not follow the dominant "
                        f"lot code pattern learned from this dataset "
                        f"({', '.join(sorted(dominant)[:3])}). Confirm they follow the documented "
                        "TLC assignment procedure."
                    ),
                    citation_section="21 CFR 1.1315",
                    details={"outliers": outliers[:15], "totalOutliers": len(outliers), "dominantPatterns": sorted(dominant)[:5]},
                )

    return checks


def _first_evidence(events: list[Any], limit: int = 20) -> list[str]:
    evidence: list[str] = []
    for event in events:
        for evidence_id in getattr(event, "evidence_ids", [])[:3]:
            if evidence_id not in evidence:
                evidence.append(evidence_id)
        if len(evidence) >= limit:
            break
    return evidence[:limit]
