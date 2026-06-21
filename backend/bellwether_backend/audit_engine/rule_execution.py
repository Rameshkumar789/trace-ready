from __future__ import annotations

import json
import re
from collections import Counter, OrderedDict, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from bellwether_backend.audit_engine.cte_classification import (
    MultiSignalCteResult,
    build_phase10c_cte_hardening,
)
from bellwether_backend.audit_engine.customer_evidence import (
    CustomerEventNode,
    CustomerEvidenceRecord,
    Phase10CustomerEvidencePackage,
    build_phase10_customer_evidence,
)


GENERATED_AT = "2026-06-16T00:00:00Z"


class StrictRuleExecutionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class EventObligationMapping(StrictRuleExecutionModel):
    mapping_id: str
    event_id: str
    cte: str
    approved_obligation_id: str
    obligation_action: str
    required_output: str | None = None
    citation: dict[str, Any]
    rule_package_id: str
    rule_package_version: int


class KdeCompletenessCheck(StrictRuleExecutionModel):
    check_id: str
    event_id: str
    cte: str
    field_key: str
    status: str
    expected_reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    observed_values: list[str] = Field(default_factory=list)
    approved_obligation_id: str


class TlcLineageCheck(StrictRuleExecutionModel):
    check_id: str
    event_id: str
    cte: str
    status: str
    lot_or_tlc: str | None = None
    source_lot_or_tlc: str | None = None
    output_lot_or_tlc: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    approved_obligation_id: str | None = None
    reason: str


class TraceabilityPlanCheck(StrictRuleExecutionModel):
    check_id: str
    component: str
    status: str
    evidence_ids: list[str] = Field(default_factory=list)
    approved_obligation_id: str
    reason: str


class ScopeExemptionCheck(StrictRuleExecutionModel):
    check_id: str
    event_id: str | None = None
    check_type: str
    status: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class RecordsReadinessCheck(StrictRuleExecutionModel):
    check_id: str
    check_type: str
    status: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    approved_obligation_id: str


class SortableExportReadinessCheck(StrictRuleExecutionModel):
    check_id: str
    event_id: str
    cte: str
    status: str
    missing_fields: list[str] = Field(default_factory=list)
    populated_fields: list[str] = Field(default_factory=list)
    approved_obligation_id: str


class SupplierProductCoverage(StrictRuleExecutionModel):
    """One cell of the "scope the problem" matrix: for a given supplier (trading partner)
    and product, what is the FTL scope and is the required data actually there? This is the
    artifact Jim asked to lead with — "which products and which suppliers to worry about" —
    aggregated from the per-event KDE/TLC checks already produced by the engine."""

    supplier_id: str
    supplier_name: str | None = None
    product: str
    ftl_status: str  # on | investigate | off
    event_count: int
    event_ids: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    tlc_gap: bool = False
    gap_count: int = 0
    status: str  # covered | gap | out_of_scope


class TlcIntegrityCheck(StrictRuleExecutionModel):
    """P2 — deeper-than-presence lot-code checks: does the chain actually hold together?
    check_kind ∈ {retention, reassignment, uom_reconciliation}. These catch the failures FDA's
    tabletop flagged as hardest: TLCs that are present but wrong (reused at transformation,
    silently changed in transit) or quantities that can't reconcile across a transformation."""

    check_id: str
    event_id: str
    cte: str
    check_kind: str
    status: str  # ok | gap
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class QualityAnomaly(StrictRuleExecutionModel):
    """P5 — data-quality / plausibility anomalies that presence checks miss: impossible
    chronology (ship before receive), one lot code reused across many products (the "same lot
    on everything" pattern Jim flagged — surfaced as needs_review, since our research could not
    confirm it is fraud vs. a placeholder), and GS1 GTIN/GLN check-digit failures."""

    anomaly_id: str
    anomaly_type: str
    severity: str
    status: str  # gap | needs_review
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class SupplierScorecardAction(StrictRuleExecutionModel):
    field_or_issue: str
    action: str
    citation: str


class SupplierScorecard(StrictRuleExecutionModel):
    """P4 — the per-supplier report card a buyer hands to a trading partner: a grade, what's
    missing, and citation-backed actions. The enforcement instrument (mirrors the Walmart/Kroger
    chargeback model) rather than just an internal report."""

    supplier_id: str
    supplier_name: str | None = None
    grade: str  # A | B | C | D | F
    in_scope_products: int
    products_with_gaps: int
    tlc_gap: bool
    missing_fields: list[str] = Field(default_factory=list)
    recommended_actions: list[SupplierScorecardAction] = Field(default_factory=list)


class TracebackFireDrillResult(StrictRuleExecutionModel):
    """P5 (part 2) — a practice version of FDA's tabletop: pick a lot and ask whether a
    complete, linked one-up/one-down record could be produced (the 24-hour test). The
    completeness score is the readiness proxy."""

    target_lot: str
    event_count: int
    event_ids: list[str] = Field(default_factory=list)
    one_up_linked: bool = False   # do we know where the lot came from?
    one_down_linked: bool = False  # do we know where it went?
    completeness_score: float = Field(ge=0, le=1)
    passed: bool = False
    missing_links: list[str] = Field(default_factory=list)


class AuditFinding(StrictRuleExecutionModel):
    finding_id: str
    event_id: str | None = None
    cte: str | None = None
    severity: str
    status: str
    finding_type: str
    message: str
    approved_obligation_id: str
    source_citation: dict[str, Any]
    customer_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reviewer_status: str
    # Specific gaps rolled up into this single record-level finding (human-readable),
    # so one root cause is reported once instead of as several near-duplicate findings.
    sub_issues: list[str] = Field(default_factory=list)
    affected_fields: list[str] = Field(default_factory=list)


class ExceptionQueueItem(StrictRuleExecutionModel):
    exception_id: str
    finding_id: str | None = None
    event_id: str | None = None
    queue_type: str
    priority: str
    title: str
    details: str
    evidence_ids: list[str] = Field(default_factory=list)
    assigned_role: str
    status: str = "open"


class FdaStyleExportPackage(StrictRuleExecutionModel):
    package_id: str
    generated_at: str
    rule_package_id: str
    rule_package_version: int
    status: str
    workbook_file: str
    tabs: dict[str, list[dict[str, Any]]]
    blockers: list[dict[str, Any]]
    citations: list[dict[str, Any]]


class Phase11RuleExecutionPackage(StrictRuleExecutionModel):
    generated_at: str
    summary: dict[str, Any]
    obligation_mappings: list[EventObligationMapping]
    kde_checks: list[KdeCompletenessCheck]
    tlc_checks: list[TlcLineageCheck]
    traceability_plan_checks: list[TraceabilityPlanCheck]
    scope_exemption_checks: list[ScopeExemptionCheck]
    records_readiness_checks: list[RecordsReadinessCheck]
    sortable_export_checks: list[SortableExportReadinessCheck]
    audit_findings: list[AuditFinding]
    exception_queue: list[ExceptionQueueItem]
    export_package: FdaStyleExportPackage
    # P1 "scope the problem" matrix (supplier x product). Optional/additive so existing
    # constructors and persisted artifacts stay backward-compatible.
    supplier_product_coverage: list[SupplierProductCoverage] = Field(default_factory=list)
    # P2 lot-code integrity checks (retention / reassignment / UoM). Additive/optional.
    tlc_integrity_checks: list[TlcIntegrityCheck] = Field(default_factory=list)
    # P5 data-quality / plausibility anomalies. Additive/optional.
    quality_anomalies: list[QualityAnomaly] = Field(default_factory=list)
    # P4 per-supplier scorecards. Additive/optional.
    supplier_scorecards: list[SupplierScorecard] = Field(default_factory=list)


BUNDLED_RULES_DIR = Path(__file__).resolve().parent / "bundled_rules"
KDE_CHECK_CONTRACTS_PATH = BUNDLED_RULES_DIR / "kde-check-contracts.json"


@lru_cache(maxsize=8)
def _load_kde_check_contracts(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """The full FSMA 204 KDE list per CTE, each mapped to the customer field(s) the parser
    produces. Source of truth is the approved kde_check_contracts cards in Supabase, written
    to a run-scoped file and passed in; the bundled JSON is only an offline/dev fallback. Not
    a hardcoded code list, so coverage stays complete and in sync with the regulation."""
    data = json.loads((path or KDE_CHECK_CONTRACTS_PATH).read_text(encoding="utf-8"))
    return data["cte_contracts"]


EXEMPTION_RULES_PATH = BUNDLED_RULES_DIR / "exemption-rules.json"


@lru_cache(maxsize=8)
def _load_exemption_rules(path: Path | None = None) -> list[dict[str, Any]]:
    """FSMA 204 exemption rules (21 CFR 1.1305). Source of truth is the approved
    exemption_rules cards in Supabase, written to a run-scoped file and passed in; the bundled
    JSON is only an offline/dev fallback. Reviewable data, not code."""
    data = json.loads((path or EXEMPTION_RULES_PATH).read_text(encoding="utf-8"))
    return data["exemptions"]


PLAN_COMPONENTS_PATH = BUNDLED_RULES_DIR / "traceability-plan-components.json"


@lru_cache(maxsize=8)
def _load_plan_components(path: Path | None = None) -> list[dict[str, Any]]:
    """The traceability-plan components a covered entity must document (21 CFR 1.1315). Source
    of truth is the approved traceability_plan_components cards in Supabase, written to a
    run-scoped file and passed in; the bundled JSON is only an offline/dev fallback."""
    data = json.loads((path or PLAN_COMPONENTS_PATH).read_text(encoding="utf-8"))
    return data["components"]

CTE_SECTION_REFS = {
    "harvesting": "21 CFR 1.1325",
    "cooling": "21 CFR 1.1325",
    "initial_packing": "21 CFR 1.1330",
    "first_land_based_receiving": "21 CFR 1.1335",
    "shipping": "21 CFR 1.1340",
    "receiving": "21 CFR 1.1345",
    "transformation": "21 CFR 1.1350",
}

# Grower/harvester-style CTEs. A traceability-plan "farm map" is only required of these
# operations (21 CFR 1.1315(a)(4)); for a distributor/processor it is not applicable.
FARM_OPERATION_CTES = {"harvesting", "cooling", "initial_packing"}

# TLC fields are the "root cause" lever: a missing TLC tends to trigger both a
# KDE-completeness gap and a TLC-lineage gap on the same record. We collapse those
# into one record-level finding instead of counting the same problem multiple times.
TLC_FIELD_KEYS = {"traceability_lot_code", "output_lot_or_tlc", "source_lot_or_tlc"}
HIGH_SEVERITY_FIELD_KEYS = {"traceability_lot_code", "output_lot_or_tlc"}

# Partner-facing names so findings read in plain English, not internal field keys.
FRIENDLY_CTE_LABELS = {
    "shipping": "Shipping record",
    "receiving": "Receiving record",
    "transformation": "Transformation record",
    "first_land_based_receiving": "First land-based receiving record",
    "initial_packing": "Initial packing record",
    "harvesting": "Harvest record",
    "cooling": "Cooling record",
    "traceability_plan": "Traceability plan",
}

FRIENDLY_FIELD_LABELS = {
    "traceability_lot_code": "Traceability Lot Code (TLC)",
    "output_lot_or_tlc": "new Traceability Lot Code for the transformed product",
    "source_lot_or_tlc": "source Traceability Lot Code for the incoming product",
    "product_name": "product description",
    "event_datetime": "event date",
    "reference_record_type": "reference document type",
    "reference_record_no": "reference document number",
}

FRIENDLY_PLAN_COMPONENT_LABELS = {
    "ftl_food_identification": "procedure to identify Food Traceability List foods",
    "tlc_assignment_procedure": "Traceability Lot Code assignment procedure",
    "point_of_contact": "traceability point of contact",
    "farm_map": "farm map",
    "plan_update_and_retention": "plan update and record-retention procedure",
    "record_maintenance_procedure": "record maintenance procedure",
}


def _cte_label(cte: str | None) -> str:
    if not cte:
        return "Record"
    return FRIENDLY_CTE_LABELS.get(cte, cte.replace("_", " ").strip().title())


def _field_label(field_key: str) -> str:
    return FRIENDLY_FIELD_LABELS.get(field_key, field_key.replace("_", " ").strip())


def _plan_component_label(component: str) -> str:
    return FRIENDLY_PLAN_COMPONENT_LABELS.get(component, component.replace("_", " ").strip())


def _extend_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


KDE_GAP_STATUSES = {"missing", "conflicting", "not_captured"}


def build_supplier_product_coverage(
    *,
    events: dict[str, CustomerEventNode],
    kde_checks: list[KdeCompletenessCheck],
    tlc_checks: list[TlcLineageCheck],
    counterparties: list[Any] | None = None,
) -> list[SupplierProductCoverage]:
    """Aggregate per-event checks into a supplier x product coverage matrix.

    Supplier is the trading partner on the record (who sent it, falling back to who received
    it). FTL status rolls up the three-tier per-event scope; a cell is a "gap" only when it is
    in scope (not "off") AND a required KDE is missing/conflicting or the TLC link is broken.
    """
    name_by_id: dict[str, str] = {}
    for cp in counterparties or []:
        entity_id = getattr(cp, "entity_id", None)
        if entity_id:
            name_by_id[entity_id] = getattr(cp, "name", None)

    kde_by_event: dict[str, list[KdeCompletenessCheck]] = defaultdict(list)
    for check in kde_checks:
        kde_by_event[check.event_id].append(check)
    tlc_by_event: dict[str, list[TlcLineageCheck]] = defaultdict(list)
    for check in tlc_checks:
        tlc_by_event[check.event_id].append(check)

    cells: "OrderedDict[tuple[str, str], dict[str, Any]]" = OrderedDict()
    for event in events.values():
        supplier_id = event.from_partner_id or event.to_partner_id or "unknown_supplier"
        product = event.product_name or event.product_id or "unknown_product"
        ftl_status = event.food_form.ftl_status if event.food_form else "investigate"
        cell = cells.setdefault((supplier_id, product), {"event_ids": [], "ftl_statuses": set()})
        cell["event_ids"].append(event.event_id)
        cell["ftl_statuses"].add(ftl_status)

    rows: list[SupplierProductCoverage] = []
    for (supplier_id, product), cell in cells.items():
        statuses = cell["ftl_statuses"]
        if statuses == {"off"}:
            ftl_status = "off"
        elif statuses == {"on"}:
            ftl_status = "on"
        else:
            ftl_status = "investigate"

        missing_fields: list[str] = []
        gap_count = 0
        for event_id in cell["event_ids"]:
            for check in kde_by_event.get(event_id, []):
                if check.status in KDE_GAP_STATUSES:
                    gap_count += 1
                    if check.field_key not in missing_fields:
                        missing_fields.append(check.field_key)
        tlc_gap = any(
            check.status == "gap"
            for event_id in cell["event_ids"]
            for check in tlc_by_event.get(event_id, [])
        )

        if ftl_status == "off":
            status = "out_of_scope"
        elif gap_count or tlc_gap:
            status = "gap"
        else:
            status = "covered"

        rows.append(
            SupplierProductCoverage(
                supplier_id=supplier_id,
                supplier_name=name_by_id.get(supplier_id),
                product=product,
                ftl_status=ftl_status,
                event_count=len(cell["event_ids"]),
                event_ids=sorted(cell["event_ids"]),
                missing_fields=missing_fields,
                tlc_gap=tlc_gap,
                gap_count=gap_count,
                status=status,
            )
        )

    # Worst first: open gaps (broken TLC, then most missing fields), then everything else.
    rows.sort(key=lambda row: (row.status != "gap", not row.tlc_gap, -row.gap_count, row.supplier_id, row.product))
    return rows


def build_lot_lineage_graph(events: dict[str, CustomerEventNode]) -> dict[str, dict[str, list[str]]]:
    """Map each output lot to the distinct input lots that fed it (across transformation
    events). An output fed by >1 distinct input is a commingling node — the high-fan-out point
    where one missing upstream link invalidates everything downstream."""
    graph: dict[str, dict[str, list[str]]] = {}
    for event in events.values():
        output = _real_value(event.output_lot_or_tlc)
        source = _real_value(event.source_lot_or_tlc)
        if not output:
            continue
        node = graph.setdefault(output.strip().lower(), {"sources": [], "events": []})
        if source and source.strip().lower() not in node["sources"]:
            node["sources"].append(source.strip().lower())
        if event.event_id not in node["events"]:
            node["events"].append(event.event_id)
    return graph


def check_tlc_integrity(
    *,
    mappings: list[EventObligationMapping],
    events: dict[str, CustomerEventNode],
) -> list[TlcIntegrityCheck]:
    """Retention + reassignment correctness (the retain-vs-reassign error FDA/Jim call out)."""
    checks: list[TlcIntegrityCheck] = []
    for mapping in mappings:
        event = events[mapping.event_id]
        lot = _real_value(event.lot_or_tlc)
        source = _real_value(event.source_lot_or_tlc)
        output = _real_value(event.output_lot_or_tlc)

        if mapping.cte == "transformation":
            # A transformation must MINT a new TLC; reusing the incoming lot breaks traceability.
            if output and source and output.strip().lower() == source.strip().lower():
                checks.append(
                    TlcIntegrityCheck(
                        check_id=f"phase11-tlcint-{len(checks) + 1:04d}",
                        event_id=mapping.event_id, cte=mapping.cte, check_kind="reassignment",
                        status="gap",
                        reason="Transformation reused the incoming lot code as its output — a new Traceability Lot Code must be assigned.",
                        details={"source": source, "output": output},
                        evidence_ids=event.evidence_ids,
                    )
                )
        elif mapping.cte in {"shipping", "receiving"}:
            # Shipping/receiving must carry the TLC forward unchanged — never reassign it.
            if output and lot and output.strip().lower() != lot.strip().lower():
                checks.append(
                    TlcIntegrityCheck(
                        check_id=f"phase11-tlcint-{len(checks) + 1:04d}",
                        event_id=mapping.event_id, cte=mapping.cte, check_kind="retention",
                        status="gap",
                        reason="A shipping/receiving record changed the Traceability Lot Code — it must carry the existing TLC forward, not assign a new one.",
                        details={"lot": lot, "output": output},
                        evidence_ids=event.evidence_ids,
                    )
                )
    return checks


def _parse_quantity(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def check_uom_reconciliation(
    *,
    mappings: list[EventObligationMapping],
    events: dict[str, CustomerEventNode],
) -> list[TlcIntegrityCheck]:
    """Mass-balance: a transformation's output quantity cannot exceed its input quantity
    (yield > 100% signals dilution/fraud/error). Runs only where quantities are present."""
    qty_by_lot: dict[str, float] = {}
    for event in events.values():
        qty = _parse_quantity(event.quantity)
        lot = _real_value(event.lot_or_tlc) or _real_value(event.output_lot_or_tlc)
        if qty is not None and lot:
            qty_by_lot[lot.strip().lower()] = qty

    checks: list[TlcIntegrityCheck] = []
    for mapping in mappings:
        if mapping.cte != "transformation":
            continue
        event = events[mapping.event_id]
        output_qty = _parse_quantity(event.quantity)
        source = _real_value(event.source_lot_or_tlc)
        if output_qty is None or not source:
            continue
        input_qty = qty_by_lot.get(source.strip().lower())
        if input_qty is None:
            continue
        if output_qty > input_qty * 1.02:  # 2% tolerance for rounding/unit noise
            checks.append(
                TlcIntegrityCheck(
                    check_id=f"phase11-uom-{len(checks) + 1:04d}",
                    event_id=mapping.event_id, cte="transformation", check_kind="uom_reconciliation",
                    status="gap",
                    reason="Transformation output quantity exceeds the input quantity — the lot cannot mass-balance.",
                    details={"input_qty": input_qty, "output_qty": output_qty, "source_lot": source},
                    evidence_ids=event.evidence_ids,
                )
            )
    return checks


def _gs1_check_digit_valid(code: str) -> bool:
    """GS1 mod-10 check digit (GTIN-8/12/13/14, GLN-13). Returns True only for the valid
    GS1 lengths with a correct check digit; non-GS1-shaped values are not judged here."""
    digits = [int(ch) for ch in code if ch.isdigit()]
    if len(code) != len(digits) or len(digits) not in {8, 12, 13, 14}:
        return False
    body, check = digits[:-1], digits[-1]
    # Weights alternate 3/1 from the rightmost body digit.
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - (total % 10)) % 10 == check


def _parse_dt(value: str | None):
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        from datetime import datetime

        return datetime.fromisoformat(text)
    except ValueError:
        return None


_RECEIVE_CTES = {"receiving", "first_land_based_receiving", "initial_packing", "harvesting"}


def detect_data_quality_anomalies(events: dict[str, CustomerEventNode]) -> list[QualityAnomaly]:
    anomalies: list[QualityAnomaly] = []

    # 1) Impossible chronology: a lot shipped before it was received/packed.
    by_lot: dict[str, dict[str, Any]] = defaultdict(lambda: {"receive": [], "ship": [], "events": []})
    for event in events.values():
        lot = _real_value(event.lot_or_tlc) or _real_value(event.output_lot_or_tlc)
        dt = _parse_dt(event.event_datetime)
        if not lot or dt is None:
            continue
        key = lot.strip().lower()
        by_lot[key]["events"].append(event.event_id)
        for cte in event.classified_ctes:
            if cte in _RECEIVE_CTES:
                by_lot[key]["receive"].append(dt)
            elif cte == "shipping":
                by_lot[key]["ship"].append(dt)
    for lot, rec in by_lot.items():
        if rec["receive"] and rec["ship"] and min(rec["ship"]) < min(rec["receive"]):
            anomalies.append(
                QualityAnomaly(
                    anomaly_id=f"anom-chrono-{len(anomalies) + 1:03d}",
                    anomaly_type="impossible_chronology", severity="high", status="gap",
                    reason="Lot was shipped before it was received/packed — the dates cannot be correct.",
                    details={"lot": lot, "earliest_ship": min(rec["ship"]).isoformat(), "earliest_receive": min(rec["receive"]).isoformat()},
                )
            )

    # 2) One lot code reused across many distinct products (Jim's "same lot on everything").
    products_by_lot: dict[str, set[str]] = defaultdict(set)
    for event in events.values():
        lot = _real_value(event.lot_or_tlc)
        product = event.product_name or event.product_id
        if lot and product:
            products_by_lot[lot.strip().lower()].add(product)
    for lot, products in products_by_lot.items():
        if len(products) > 1:
            anomalies.append(
                QualityAnomaly(
                    anomaly_id=f"anom-lotreuse-{len(anomalies) + 1:03d}",
                    anomaly_type="lot_code_reused_across_products", severity="medium", status="needs_review",
                    reason="The same lot code appears on multiple distinct products — verify it is a real lot, not a placeholder or duplicate.",
                    details={"lot": lot, "products": sorted(products)},
                )
            )

    # 3) GS1 check-digit failures on GS1-shaped identifiers (product_id as GTIN, partner ids as GLN).
    seen_ids: set[str] = set()
    for event in events.values():
        for label, value in (("product_id", event.product_id), ("from_partner_id", event.from_partner_id), ("to_partner_id", event.to_partner_id)):
            candidate = (value or "").strip()
            if not candidate or candidate in seen_ids or not candidate.isdigit() or len(candidate) not in {8, 12, 13, 14}:
                continue
            seen_ids.add(candidate)
            if not _gs1_check_digit_valid(candidate):
                anomalies.append(
                    QualityAnomaly(
                        anomaly_id=f"anom-gs1-{len(anomalies) + 1:03d}",
                        anomaly_type="gs1_check_digit_invalid", severity="medium", status="needs_review",
                        reason=f"{label} looks like a GS1 identifier but its check digit is invalid (Walmart/Kroger require valid GS1 GTIN/GLN).",
                        details={"field": label, "value": candidate},
                    )
                )
    return anomalies


# P5 (part 2) — flexibility-aware citations. The carve-outs FDA is weighing under docket
# FDA-2014-N-0053 (June/Nov 2026 lot-level-traceability engagements), plus the finalized
# cottage-cheese exemption. Encoded as reviewable data so a finding can cite the correct
# pathway instead of always defaulting to the base CTE section.
FLEXIBILITY_RULES = {
    "returns_reclamation": {
        "citation": "21 CFR 1.1345 (receiving) — returns/reclamation flexibility under review (FDA-2014-N-0053)",
        "effect": "may_reduce_kdes",
        "note": "Items returned to a supplier may not require the full receiving KDE set; confirm against final guidance.",
    },
    "food_waste_recovery": {
        "citation": "21 CFR 1.1305 — 'shipping' excludes donation of surplus food",
        "effect": "out_of_scope_shipping",
        "note": "Donating surplus food is not a 'shipping' CTE; donor need not keep shipping KDEs.",
    },
    "intracompany_no_transformation": {
        "citation": "FDA-2014-N-0053 — intracompany-shipment flexibility under review",
        "effect": "may_reduce_kdes",
        "note": "Moves between locations of the same firm with no transformation may not need full ship/receive KDEs.",
    },
    "cottage_cheese_ims": {
        "citation": "21 CFR 1.1305 — Grade 'A' cottage cheese exemption (final, Feb 2026)",
        "effect": "exempt",
        "note": "Grade 'A' cottage cheese on the IMS list is exempt; immediate-source/recipient records still apply.",
    },
}


def resolve_flexible_citation(cte: str | None, *, scenario: str | None = None) -> dict[str, Any]:
    """Pick the citation pathway for a finding: a recognized flexibility scenario when one
    applies, otherwise the base CTE section. Conservative — flexibilities are 'under review'
    unless final, so the note tells the operator to confirm rather than auto-granting relief."""
    if scenario and scenario in FLEXIBILITY_RULES:
        rule = FLEXIBILITY_RULES[scenario]
        return {"scenario": scenario, "section": rule["citation"], "effect": rule["effect"], "note": rule["note"]}
    return {"scenario": None, "section": CTE_SECTION_REFS.get(cte or "", "21 CFR 1.1315"), "effect": "required", "note": ""}


# Field -> representative CFR citation for the supplier-facing recommended actions.
FIELD_CITATIONS = {
    "traceability_lot_code": "21 CFR 1.1340 / 1.1345",
    "output_lot_or_tlc": "21 CFR 1.1350",
    "source_lot_or_tlc": "21 CFR 1.1350",
    "event_datetime": "21 CFR 1.1340(a) / 1.1345(a)",
    "reference_record_no": "21 CFR 1.1340(a) / 1.1345(a)",
    "reference_record_type": "21 CFR 1.1340(a) / 1.1345(a)",
    "product_name": "21 CFR 1.1340(a) / 1.1345(a)",
    "location_id": "21 CFR 1.1340(a) / 1.1345(a)",
}
DEFAULT_FIELD_CITATION = "21 CFR 1.1315"


def _supplier_grade(in_scope: int, with_gaps: int, tlc_gap: bool) -> str:
    if in_scope == 0:
        return "A"
    ratio = with_gaps / in_scope
    if tlc_gap and ratio >= 0.5:
        return "F"
    if ratio >= 0.5:
        return "F"
    if ratio >= 0.3:
        return "D"
    if ratio >= 0.15:
        return "C"
    if ratio > 0:
        return "B"
    return "A"


def build_supplier_scorecards(coverage: list[SupplierProductCoverage]) -> list[SupplierScorecard]:
    """Roll the supplier x product coverage up into a per-supplier graded scorecard with
    citation-backed actions a buyer can send to the supplier."""
    by_supplier: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for row in coverage:
        bucket = by_supplier.setdefault(
            row.supplier_id,
            {"name": row.supplier_name, "in_scope": 0, "gaps": 0, "tlc_gap": False, "missing": []},
        )
        if row.ftl_status != "off":  # out-of-scope products don't count against the supplier
            bucket["in_scope"] += 1
            if row.status == "gap":
                bucket["gaps"] += 1
        if row.tlc_gap:
            bucket["tlc_gap"] = True
        for field in row.missing_fields:
            if field not in bucket["missing"]:
                bucket["missing"].append(field)

    scorecards: list[SupplierScorecard] = []
    for supplier_id, bucket in by_supplier.items():
        actions: list[SupplierScorecardAction] = []
        for field in bucket["missing"]:
            actions.append(
                SupplierScorecardAction(
                    field_or_issue=field,
                    action=f"Provide {_field_label(field)} on every covered record.",
                    citation=FIELD_CITATIONS.get(field, DEFAULT_FIELD_CITATION),
                )
            )
        if bucket["tlc_gap"]:
            actions.append(
                SupplierScorecardAction(
                    field_or_issue="tlc_lineage",
                    action="Link each shipped lot back to its source/transformation lot so the chain is unbroken.",
                    citation="21 CFR 1.1350",
                )
            )
        scorecards.append(
            SupplierScorecard(
                supplier_id=supplier_id,
                supplier_name=bucket["name"],
                grade=_supplier_grade(bucket["in_scope"], bucket["gaps"], bucket["tlc_gap"]),
                in_scope_products=bucket["in_scope"],
                products_with_gaps=bucket["gaps"],
                tlc_gap=bucket["tlc_gap"],
                missing_fields=bucket["missing"],
                recommended_actions=actions,
            )
        )
    # Worst grade first so the buyer sees who to chase.
    grade_rank = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
    scorecards.sort(key=lambda s: (grade_rank.get(s.grade, 5), -s.products_with_gaps, s.supplier_id))
    return scorecards


def run_traceback_fire_drill(events: dict[str, CustomerEventNode], target_lot: str) -> TracebackFireDrillResult:
    """Simulate an FDA records request for one lot: can we assemble a complete one-up/one-down
    linked record? Scored over {found, one-up, one-down}; passes only if all three hold."""
    needle = (target_lot or "").strip().lower()
    matching: list[CustomerEventNode] = []
    one_up = False
    one_down = False
    for event in events.values():
        lots = {
            _real_value(value).strip().lower()
            for value in (event.lot_or_tlc, event.source_lot_or_tlc, event.output_lot_or_tlc)
            if _real_value(value)
        }
        if needle not in lots:
            continue
        matching.append(event)
        ctes = set(event.classified_ctes)
        # We know where it came from if it was received/packed/transformed (with a source lot).
        if ctes & {"receiving", "first_land_based_receiving", "initial_packing", "harvesting"}:
            one_up = True
        if "transformation" in ctes and _real_value(event.source_lot_or_tlc):
            one_up = True
        # We know where it went if it was shipped.
        if "shipping" in ctes:
            one_down = True

    found = bool(matching)
    components = [found, one_up, one_down]
    score = round(sum(1 for c in components if c) / len(components), 3)
    missing: list[str] = []
    if not found:
        missing.append("no record references this lot")
    if not one_up:
        missing.append("no one-up source (where the lot came from)")
    if not one_down:
        missing.append("no one-down destination (where the lot went)")
    return TracebackFireDrillResult(
        target_lot=target_lot,
        event_count=len(matching),
        event_ids=sorted(event.event_id for event in matching),
        one_up_linked=one_up,
        one_down_linked=one_down,
        completeness_score=score,
        passed=found and one_up and one_down,
        missing_links=missing,
    )


def build_phase11_rule_execution(
    *,
    input_file: Path,
    approved_rule_package_file: Path,
    ftl_food_items_file: Path | None = None,
    kde_contracts_file: Path | None = None,
    exemption_rules_file: Path | None = None,
    plan_components_file: Path | None = None,
) -> Phase11RuleExecutionPackage:
    phase10 = build_phase10_customer_evidence(input_file=input_file, ftl_food_items_file=ftl_food_items_file)
    phase10c = build_phase10c_cte_hardening(input_file=input_file, ftl_food_items_file=ftl_food_items_file)
    rule_package = json.loads(approved_rule_package_file.read_text(encoding="utf-8"))
    approved_obligations = _approved_obligations(rule_package)
    evidence_by_id = {record.evidence_id: record for record in phase10.evidence_records}
    event_by_id = {event.event_id: event for event in phase10.event_graph}
    hardened_by_event = {result.event_id: result for result in phase10c.production_event_results}
    # A farm map (21 CFR 1.1315(a)(4)) is only required of growers/harvesters. Detect a
    # farm/grower operation from the hardened CTEs so we don't flag a distributor/processor
    # for a "missing" farm map it never needs.
    is_farm_operation = any(
        cte in FARM_OPERATION_CTES
        for result in phase10c.production_event_results
        for cte in result.final_ctes
    )

    obligation_mappings = map_events_to_approved_obligations(
        hardened_results=phase10c.production_event_results,
        approved_obligations=approved_obligations,
        rule_package=rule_package,
    )
    kde_checks = check_kde_completeness(
        mappings=obligation_mappings,
        events=event_by_id,
        evidence_by_id=evidence_by_id,
        contracts_file=kde_contracts_file,
    )
    tlc_checks = check_tlc_lineage(
        mappings=obligation_mappings,
        events=event_by_id,
    )
    traceability_plan_checks = check_traceability_plan(
        phase10=phase10,
        approved_obligations=approved_obligations,
        rule_package=rule_package,
        is_farm_operation=is_farm_operation,
        plan_components_file=plan_components_file,
    )
    scope_exemption_checks = check_scope_and_exemptions(
        events=event_by_id,
        hardened_results=hardened_by_event,
        evidence_conflicts=phase10.evidence_conflicts,
        quality_report=phase10.quality_report.model_dump(mode="json") if phase10.quality_report else {},
    )
    scope_exemption_checks += check_exemption_claims(
        phase10=phase10, exemption_rules=_load_exemption_rules(exemption_rules_file)
    )
    records_readiness_checks = check_records_readiness(
        phase10=phase10,
        approved_obligations=approved_obligations,
    )
    sortable_export_checks = check_sortable_export_readiness(kde_checks)
    audit_findings = generate_audit_findings(
        kde_checks=kde_checks,
        tlc_checks=tlc_checks,
        traceability_plan_checks=traceability_plan_checks,
        scope_exemption_checks=scope_exemption_checks,
        records_readiness_checks=records_readiness_checks,
        sortable_export_checks=sortable_export_checks,
        approved_obligations=approved_obligations,
    )
    exception_queue = generate_exception_queue(audit_findings)
    supplier_product_coverage = build_supplier_product_coverage(
        events=event_by_id,
        kde_checks=kde_checks,
        tlc_checks=tlc_checks,
        counterparties=getattr(phase10.entity_graph, "counterparties", []),
    )
    tlc_integrity_checks = check_tlc_integrity(mappings=obligation_mappings, events=event_by_id)
    tlc_integrity_checks += check_uom_reconciliation(mappings=obligation_mappings, events=event_by_id)
    quality_anomalies = detect_data_quality_anomalies(event_by_id)
    supplier_scorecards = build_supplier_scorecards(supplier_product_coverage)
    export_package = build_fda_style_export_package(
        rule_package=rule_package,
        events=event_by_id,
        hardened_results=phase10c.production_event_results,
        kde_checks=kde_checks,
        audit_findings=audit_findings,
        sortable_export_checks=sortable_export_checks,
    )
    summary = _summary(
        rule_package=rule_package,
        obligation_mappings=obligation_mappings,
        kde_checks=kde_checks,
        tlc_checks=tlc_checks,
        traceability_plan_checks=traceability_plan_checks,
        scope_exemption_checks=scope_exemption_checks,
        records_readiness_checks=records_readiness_checks,
        sortable_export_checks=sortable_export_checks,
        audit_findings=audit_findings,
        exception_queue=exception_queue,
        export_package=export_package,
    )
    return Phase11RuleExecutionPackage(
        generated_at=GENERATED_AT,
        summary=summary,
        obligation_mappings=obligation_mappings,
        kde_checks=kde_checks,
        tlc_checks=tlc_checks,
        traceability_plan_checks=traceability_plan_checks,
        scope_exemption_checks=scope_exemption_checks,
        records_readiness_checks=records_readiness_checks,
        sortable_export_checks=sortable_export_checks,
        audit_findings=audit_findings,
        exception_queue=exception_queue,
        export_package=export_package,
        supplier_product_coverage=supplier_product_coverage,
        tlc_integrity_checks=tlc_integrity_checks,
        quality_anomalies=quality_anomalies,
        supplier_scorecards=supplier_scorecards,
    )


def write_phase11_rule_execution_artifacts(package: Phase11RuleExecutionPackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase11-summary.json",
        "obligationMapping": output_dir / "phase11-obligation-mapping.json",
        "kdeCompleteness": output_dir / "phase11-kde-completeness-results.json",
        "tlcLineage": output_dir / "phase11-tlc-lineage-results.json",
        "traceabilityPlan": output_dir / "phase11-traceability-plan-results.json",
        "scopeExemption": output_dir / "phase11-scope-exemption-results.json",
        "recordsReadiness": output_dir / "phase11-records-readiness-results.json",
        "sortableExportReadiness": output_dir / "phase11-sortable-export-readiness.json",
        "auditFindings": output_dir / "phase11-audit-findings.json",
        "exceptionQueue": output_dir / "phase11-exception-queue.json",
        "exportPackage": output_dir / "phase11-export-package.json",
        "exportWorkbook": output_dir / "phase11-fda-style-export-package.xlsx",
    }
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["obligationMapping"], [item.model_dump(mode="json") for item in package.obligation_mappings])
    _write_json(outputs["kdeCompleteness"], [item.model_dump(mode="json") for item in package.kde_checks])
    _write_json(outputs["tlcLineage"], [item.model_dump(mode="json") for item in package.tlc_checks])
    _write_json(outputs["traceabilityPlan"], [item.model_dump(mode="json") for item in package.traceability_plan_checks])
    _write_json(outputs["scopeExemption"], [item.model_dump(mode="json") for item in package.scope_exemption_checks])
    _write_json(outputs["recordsReadiness"], [item.model_dump(mode="json") for item in package.records_readiness_checks])
    _write_json(outputs["sortableExportReadiness"], [item.model_dump(mode="json") for item in package.sortable_export_checks])
    _write_json(outputs["auditFindings"], [item.model_dump(mode="json") for item in package.audit_findings])
    _write_json(outputs["exceptionQueue"], [item.model_dump(mode="json") for item in package.exception_queue])
    export_payload = package.export_package.model_copy(update={"workbook_file": str(outputs["exportWorkbook"])}).model_dump(mode="json")
    _write_json(outputs["exportPackage"], export_payload)
    _write_export_workbook(outputs["exportWorkbook"], package.export_package, package.audit_findings)
    return {key: str(path) for key, path in outputs.items()}


def map_events_to_approved_obligations(
    *,
    hardened_results: list[MultiSignalCteResult],
    approved_obligations: dict[str, dict[str, Any]],
    rule_package: dict[str, Any],
) -> list[EventObligationMapping]:
    mappings: list[EventObligationMapping] = []
    for result in hardened_results:
        for cte in result.final_ctes:
            for obligation in approved_obligations.values():
                applies = obligation.get("applies_to_ctes") or []
                if cte not in applies and "other" not in applies:
                    continue
                if "other" in applies:
                    continue
                if not _is_specific_cte_obligation(obligation, cte):
                    continue
                mappings.append(_mapping(result.event_id, cte, obligation, rule_package, len(mappings) + 1))
    other_ctes = {"records_readiness", "sortable_export"}
    for result in hardened_results:
        if result.final_ctes:
            for obligation in approved_obligations.values():
                if "other" in (obligation.get("applies_to_ctes") or []):
                    for cte in other_ctes:
                        mappings.append(_mapping(result.event_id, cte, obligation, rule_package, len(mappings) + 1))
    return mappings


def check_kde_completeness(
    *,
    mappings: list[EventObligationMapping],
    events: dict[str, CustomerEventNode],
    evidence_by_id: dict[str, CustomerEvidenceRecord],
    contracts_file: Path | None = None,
) -> list[KdeCompletenessCheck]:
    contracts = _load_kde_check_contracts(contracts_file)
    # Promote the customer's 07_KDE_Values rows (each declares its own field key + value) into
    # per-event facts so KDEs the workbook DOES carry — source references, harvest origin —
    # actually feed the completeness check instead of being perpetually "not captured".
    promoted_kde_facts = _promote_kde_value_rows(evidence_by_id)
    checks: list[KdeCompletenessCheck] = []
    for mapping in mappings:
        cte_contract = contracts.get(mapping.cte)
        if not cte_contract:
            continue
        section = cte_contract.get("citation_section", "")
        event = events[mapping.event_id]
        facts = _event_facts(event, evidence_by_id)
        _merge_promoted_kde_facts(facts, promoted_kde_facts, event.event_id)
        for kde in cte_contract["kdes"]:
            kde_key = str(kde["kde"])
            satisfied_by = kde.get("satisfied_by") or []
            label = kde.get("label", kde_key)
            # A placeholder ("UNKNOWN", "N/A", "TBD", ...) is NOT a real value — it must not
            # count as a present KDE, or a non-compliant record would pass (a false pass).
            # satisfied_by is "any of": the KDE is met if ANY of those fields carries a value.
            real_by_field = {field: sorted({v for v in facts.get(field, []) if _is_answered(v)}) for field in satisfied_by}
            values = sorted({v for vals in real_by_field.values() for v in vals})
            evidence_ids = sorted({ev for field in satisfied_by for ev in facts.get(f"evidence:{field}", [])})
            if not satisfied_by:
                # Required by FSMA but the parser does not extract this field yet. Tracked
                # honestly (not failed, not silently dropped) until parser support is added.
                status = "not_captured"
            elif len(satisfied_by) == 1 and len(real_by_field[satisfied_by[0]]) > 1:
                status = "conflicting"
            elif values:
                status = "present"
            elif kde.get("requirement") == "conditional":
                status = "not_applicable"
            else:
                status = "missing"
            checks.append(
                KdeCompletenessCheck(
                    check_id=f"phase11-kde-{len(checks) + 1:04d}",
                    event_id=mapping.event_id,
                    cte=mapping.cte,
                    field_key=kde_key,
                    status=status,
                    expected_reason=f"{label} ({section})" if section else label,
                    evidence_ids=evidence_ids,
                    observed_values=values,
                    approved_obligation_id=mapping.approved_obligation_id,
                )
            )
    return checks


def check_tlc_lineage(
    *,
    mappings: list[EventObligationMapping],
    events: dict[str, CustomerEventNode],
) -> list[TlcLineageCheck]:
    # Lots that exist as a real receipt/output anywhere in these records. A transformation
    # input must trace back to one of these, otherwise the chain is broken even though a
    # lot code is "present" — presence alone is not linkage.
    upstream_lots = {
        value.strip().lower()
        for event in events.values()
        for value in (_real_value(event.lot_or_tlc), _real_value(event.output_lot_or_tlc))
        if value
    }

    checks: list[TlcLineageCheck] = []
    for mapping in mappings:
        if mapping.cte not in {"initial_packing", "first_land_based_receiving", "transformation", "shipping", "receiving"}:
            continue
        event = events[mapping.event_id]
        lot = _real_value(event.lot_or_tlc)
        source = _real_value(event.source_lot_or_tlc)
        output = _real_value(event.output_lot_or_tlc)
        if mapping.cte == "transformation":
            if not (output and source):
                status = "gap"
                reason = "Transformation must record both an incoming (source) and a new (output) traceability lot code."
            elif source.strip().lower() not in upstream_lots:
                status = "gap"
                reason = "Transformation input lot code does not trace to any upstream receiving/packing record — the lineage is broken."
            else:
                status = "linked"
                reason = "Input and output lot codes are present and the input lot traces to an upstream event."
        elif mapping.cte in {"initial_packing", "first_land_based_receiving"}:
            status = "linked" if (lot or output) else "gap"
            reason = "A new traceability lot code must be assigned at this event." if status == "gap" else "Traceability lot code assigned."
        else:
            status = "linked" if lot else "gap"
            reason = "A traceability lot code must be present on this shipping/receiving record." if status == "gap" else "Traceability lot code present."
        checks.append(
            TlcLineageCheck(
                check_id=f"phase11-tlc-{len(checks) + 1:04d}",
                event_id=mapping.event_id,
                cte=mapping.cte,
                status=status,
                lot_or_tlc=event.lot_or_tlc,
                source_lot_or_tlc=event.source_lot_or_tlc,
                output_lot_or_tlc=event.output_lot_or_tlc,
                evidence_ids=event.evidence_ids,
                approved_obligation_id=mapping.approved_obligation_id,
                reason=reason,
            )
        )
    return checks


def check_traceability_plan(
    *,
    phase10: Phase10CustomerEvidencePackage,
    approved_obligations: dict[str, dict[str, Any]],
    rule_package: dict[str, Any],
    is_farm_operation: bool = False,
    plan_components_file: Path | None = None,
) -> list[TraceabilityPlanCheck]:
    obligation = _find_obligation_by_cte(approved_obligations, "traceability_plan")
    plan_records = [record for record in phase10.evidence_records if record.sheet_name == "04_Traceability_Plan"]

    # Reconstruct plan rows (item -> answer). A component is only "present" if its row
    # exists AND its answer cell is actually filled in. The previous logic matched on the
    # item label alone, so a blank answer (e.g. a missing TLC-assignment procedure) was
    # silently counted as present. For a compliance tool, a missed gap is worse than a
    # duplicate, so blank/placeholder answers must surface as gaps.
    rows: "OrderedDict[Any, dict[str, Any]]" = OrderedDict()
    for record in plan_records:
        row = rows.setdefault(record.row_number, {"item": None, "answer": "", "evidence_ids": []})
        if record.field_key == "traceability_plan_item":
            row["item"] = record.normalized_value.strip().lower()
        elif record.field_key == "traceability_plan_answer":
            row["answer"] = record.normalized_value.strip()
        _extend_unique(row["evidence_ids"], [record.evidence_id])

    components = _load_plan_components(plan_components_file)
    checks: list[TraceabilityPlanCheck] = []
    for spec in components:
        component = spec["component"]
        terms = spec.get("match_terms", [])
        farm_only = bool(spec.get("farm_only"))
        matching_rows = [row for row in rows.values() if row["item"] and any(term in row["item"] for term in terms)]
        answered_rows = [row for row in matching_rows if _is_answered(row["answer"])]
        evidence_ids: list[str] = []
        for row in matching_rows:
            _extend_unique(evidence_ids, row["evidence_ids"])
        if answered_rows:
            status = "present"
            reason = f"Traceability plan component expected by approved obligation in {rule_package['package_id']}."
        elif farm_only and not is_farm_operation:
            status = "not_applicable"
            reason = "Farm map is required only for farms/growers (21 CFR 1.1315(a)(4)); not applicable to this operation."
        elif matching_rows:
            status = "missing"
            reason = "Traceability plan lists this component but the answer is blank or undetermined."
        else:
            status = "missing"
            reason = "Traceability plan does not document this required component."
        checks.append(
            TraceabilityPlanCheck(
                check_id=f"phase11-plan-{len(checks) + 1:04d}",
                component=component,
                status=status,
                evidence_ids=evidence_ids,
                approved_obligation_id=obligation["obligation_id"],
                reason=reason,
            )
        )
    return checks


_PLACEHOLDER_VALUES = {
    "",
    "unknown",
    "n/a",
    "n.a.",
    "na",
    "tbd",
    "tbc",
    "none",
    "null",
    "-",
    "--",
    "pending",
    "not provided",
    "not available",
    "unassigned",
    "missing",
}


def _is_answered(value: str) -> bool:
    return value.strip().lower() not in _PLACEHOLDER_VALUES


def _real_value(value: str | None) -> str | None:
    """A customer-supplied value, or None if it's blank/a placeholder ("UNKNOWN", "N/A", ...).
    A placeholder must never count as a present KDE or a linked TLC — that would be a false pass."""
    if value is None:
        return None
    return value if _is_answered(value) else None


def _scope_review_reason(event: CustomerEventNode, hardened: MultiSignalCteResult | None) -> str:
    product = (getattr(event, "product_name", "") or "").strip() or "This record"
    questions = list(getattr(hardened, "reviewer_questions", []) or []) if hardened else []
    if questions:
        return f"{product} needs a scope/exemption review: {questions[0]}"
    return f"{product} needs a food-scope review before this record can produce a final finding."


def check_scope_and_exemptions(
    *,
    events: dict[str, CustomerEventNode],
    hardened_results: dict[str, MultiSignalCteResult],
    evidence_conflicts: list[Any],
    quality_report: dict[str, Any],
) -> list[ScopeExemptionCheck]:
    checks: list[ScopeExemptionCheck] = []
    for event_id, event in events.items():
        hardened = hardened_results.get(event_id)
        if event.food_form.review_required or (hardened and hardened.reviewer_questions):
            checks.append(
                ScopeExemptionCheck(
                    check_id=f"phase11-scope-{len(checks) + 1:04d}",
                    event_id=event_id,
                    check_type="scope_or_exemption_uncertainty",
                    status="needs_review",
                    reason=_scope_review_reason(event, hardened),
                    evidence_ids=event.evidence_ids,
                )
            )
    if evidence_conflicts:
        checks.append(
            ScopeExemptionCheck(
                check_id=f"phase11-scope-{len(checks) + 1:04d}",
                event_id=None,
                check_type="evidence_conflicts",
                status="needs_review",
                reason="Customer evidence conflicts must be resolved before final execution.",
                evidence_ids=[],
            )
        )
    if quality_report.get("quality_gate") not in {None, "pass"}:
        checks.append(
            ScopeExemptionCheck(
                check_id=f"phase11-scope-{len(checks) + 1:04d}",
                event_id=None,
                check_type="customer_evidence_quality_gate",
                status="needs_review",
                reason=f"Customer evidence quality gate is {quality_report.get('quality_gate')}.",
                evidence_ids=[],
            )
        )
    return checks


def _normalize_match_token(value: str) -> str:
    """Lower-case, collapse non-alphanumerics to single spaces — so 'small_producer',
    'Small Producer', and 'small-producer' all compare equal."""
    return " ".join("".join(ch if ch.isalnum() else " " for ch in str(value).lower()).split())


def _match_exemption_rule(claim_type: str, exemption_rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Match a customer's claimed exemption type to an approved 21 CFR 1.1305 rule. Tolerant of
    both card schemas: the bundled rules (canonical snake_case exemption_type + aliases) and the
    approved Supabase cards (prose exemption_type, exemption_rule_id, no aliases). Matches on a
    normalized exemption_type/alias/id, then on token containment as a last resort."""
    needle = _normalize_match_token(claim_type)
    if not needle:
        return None
    for rule in exemption_rules:
        candidates = [rule.get("exemption_type", ""), rule.get("exemption_rule_id", "")]
        candidates.extend(rule.get("aliases", []) or [])
        normalized = [_normalize_match_token(c) for c in candidates if c]
        if any(needle == c for c in normalized):
            return rule
    # Last resort: the claim text contains (or is contained by) a known type/alias token string.
    for rule in exemption_rules:
        candidates = [rule.get("exemption_type", "")] + list(rule.get("aliases", []) or [])
        for candidate in candidates:
            token = _normalize_match_token(candidate)
            if token and (token in needle or needle in token):
                return rule
    return None


def _exemption_evidence_text(rule: dict[str, Any]) -> str:
    """The documentation a customer must show, across both card schemas."""
    value = rule.get("evidence_required") or rule.get("documentation_needed") or rule.get("eligibility_condition")
    if isinstance(value, (list, tuple)):
        value = "; ".join(str(item) for item in value if item)
    return str(value).strip() if value else "supporting eligibility records"


def _exemption_label(rule: dict[str, Any], fallback: str) -> str:
    raw = str(rule.get("exemption_type") or fallback).replace("_", " ").strip()
    return raw[:1].upper() + raw[1:] if raw else fallback


def check_exemption_claims(
    *,
    phase10: Phase10CustomerEvidencePackage,
    exemption_rules: list[dict[str, Any]],
) -> list[ScopeExemptionCheck]:
    """Evaluate the customer's claimed exemptions (sheet 10_Exemptions_Claims) against the
    approved 21 CFR 1.1305 exemption rules.

    Conservative by design: a claim is NEVER allowed to auto-suppress a CTE/KDE obligation.
    Every claim is surfaced for human confirmation. A claim with supporting evidence becomes a
    'review/confirm' item; a claim with no evidence is 'not_determined' (we neither grant nor
    deny it); an unrecognized claim type is flagged for reviewer judgment. Telling a customer
    they are exempt when they are not is the worst possible error, so the engine only ever
    raises the question — a human grants the exemption."""
    claim_records = [r for r in phase10.evidence_records if r.sheet_name == "10_Exemptions_Claims"]
    rows: "OrderedDict[Any, dict[str, Any]]" = OrderedDict()
    for record in claim_records:
        row = rows.setdefault(
            record.row_number,
            {"claim_id": None, "claim_type": None, "claimed_by": None, "evidence": "", "evidence_ids": []},
        )
        if record.field_key == "exemption_claim_id":
            row["claim_id"] = record.normalized_value.strip()
        elif record.field_key == "exemption_claim_type":
            row["claim_type"] = record.normalized_value.strip()
        elif record.field_key == "exemption_claimed_by":
            row["claimed_by"] = record.normalized_value.strip()
        elif record.field_key == "exemption_evidence_provided":
            row["evidence"] = record.normalized_value.strip()
        _extend_unique(row["evidence_ids"], [record.evidence_id])

    checks: list[ScopeExemptionCheck] = []
    for row in rows.values():
        claim_type = (row["claim_type"] or "").strip()
        if not claim_type:
            continue
        claimant = row["claimed_by"] or "the operation"
        rule = _match_exemption_rule(claim_type, exemption_rules)
        has_evidence = row["evidence"].strip().lower() in {"yes", "y", "true", "1", "provided", "attached"}
        if rule is None:
            status = "needs_review"
            reason = (
                f"{claimant} claims a '{claim_type}' exemption that could not be matched automatically to an "
                "approved 21 CFR 1.1305 exemption rule. A reviewer must confirm whether any exemption applies "
                "before the related records are treated as not required."
            )
        else:
            label = _exemption_label(rule, claim_type)
            effect = str(rule.get("effect") or "review required")
            if has_evidence:
                status = "needs_review"
                reason = (
                    f"{claimant} claims the {label} exemption ({effect}) and provided supporting evidence. "
                    "Confirm the evidence before relying on it — Bellwether does not auto-grant exemptions."
                )
            else:
                status = "not_determined"
                reason = (
                    f"{claimant} claims the {label} exemption ({effect}) but provided no supporting evidence "
                    f"({_exemption_evidence_text(rule)}). The exemption is not determined; the underlying records "
                    "remain required until eligibility is documented and confirmed."
                )
        checks.append(
            ScopeExemptionCheck(
                check_id=f"phase11-exemption-{len(checks) + 1:04d}",
                event_id=None,
                check_type="exemption_claim",
                status=status,
                reason=reason,
                evidence_ids=row["evidence_ids"],
            )
        )
    return checks


def check_records_readiness(
    *,
    phase10: Phase10CustomerEvidencePackage,
    approved_obligations: dict[str, dict[str, Any]],
) -> list[RecordsReadinessCheck]:
    records_obligation = _find_obligation_containing(approved_obligations, "RECORDS-MAINTENANCE")
    request_obligation = _find_obligation_containing(approved_obligations, "FDA-REQUEST")
    export_obligation = _find_obligation_containing(approved_obligations, "SORTABLE-SPREADSHEET")
    evidence_records = phase10.evidence_records
    checks = [
        RecordsReadinessCheck(
            check_id="phase11-records-0001",
            check_type="legible_linked_records",
            status="present" if evidence_records and not phase10.evidence_conflicts else "needs_review",
            reason="Parsed evidence has cell-level lineage and no unresolved evidence conflicts." if not phase10.evidence_conflicts else "Evidence conflicts require review.",
            evidence_ids=[record.evidence_id for record in evidence_records[:50]],
            approved_obligation_id=records_obligation["obligation_id"],
        ),
        RecordsReadinessCheck(
            check_id="phase11-records-0002",
            check_type="fda_24_hour_response_readiness",
            status="present" if phase10.quality_report and phase10.quality_report.quality_gate == "pass" else "needs_review",
            reason="Evidence package is parseable and linked for FDA request workflow." if phase10.quality_report and phase10.quality_report.quality_gate == "pass" else "Evidence quality gate blocks FDA response readiness.",
            evidence_ids=[record.evidence_id for record in evidence_records[:50]],
            approved_obligation_id=request_obligation["obligation_id"],
        ),
        RecordsReadinessCheck(
            check_id="phase11-records-0003",
            check_type="sortable_export_source_data",
            status="present" if phase10.event_graph else "missing",
            reason="Normalized event graph exists for sortable export population.",
            evidence_ids=[evidence_id for event in phase10.event_graph for evidence_id in event.evidence_ids[:5]],
            approved_obligation_id=export_obligation["obligation_id"],
        ),
    ]
    return checks


def check_sortable_export_readiness(kde_checks: list[KdeCompletenessCheck]) -> list[SortableExportReadinessCheck]:
    by_event_cte: dict[tuple[str, str], list[KdeCompletenessCheck]] = defaultdict(list)
    for check in kde_checks:
        by_event_cte[(check.event_id, check.cte)].append(check)
    results: list[SortableExportReadinessCheck] = []
    for (event_id, cte), checks in sorted(by_event_cte.items()):
        missing = [check.field_key for check in checks if check.status in {"missing", "conflicting"}]
        populated = [check.field_key for check in checks if check.status == "present"]
        results.append(
            SortableExportReadinessCheck(
                check_id=f"phase11-export-{len(results) + 1:04d}",
                event_id=event_id,
                cte=cte,
                status="ready" if not missing else "blocked",
                missing_fields=missing,
                populated_fields=populated,
                approved_obligation_id=checks[0].approved_obligation_id,
            )
        )
    return results


def generate_audit_findings(
    *,
    kde_checks: list[KdeCompletenessCheck],
    tlc_checks: list[TlcLineageCheck],
    traceability_plan_checks: list[TraceabilityPlanCheck],
    scope_exemption_checks: list[ScopeExemptionCheck],
    records_readiness_checks: list[RecordsReadinessCheck],
    sortable_export_checks: list[SortableExportReadinessCheck],
    approved_obligations: dict[str, dict[str, Any]],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    fallback_obligation = next(iter(approved_obligations.values()))

    # --- Event-scoped gaps: one finding per record, root cause grouped ---
    # A missing TLC commonly surfaces as both a KDE-completeness gap and a TLC-lineage
    # gap on the same event. We merge all KDE/TLC gaps for one event into a single
    # record-level finding so the partner sees one real problem, not several copies.
    event_groups: "OrderedDict[str, dict[str, Any]]" = OrderedDict()

    def _group_for(event_id: str, cte: str, obligation_id: str | None) -> dict[str, Any]:
        group = event_groups.get(event_id)
        if group is None:
            group = {
                "event_id": event_id,
                "cte": cte,
                "missing_fields": [],
                "tlc_reasons": [],
                "evidence_ids": [],
                "obligation_id": obligation_id,
                "tlc_root": False,
            }
            event_groups[event_id] = group
        if not group.get("obligation_id") and obligation_id:
            group["obligation_id"] = obligation_id
        return group

    for check in kde_checks:
        # Only real gaps become findings. "present" passes; "not_applicable" (conditional KDE
        # that doesn't apply) and "not_captured" (FSMA-required but not yet parser-extracted)
        # are not customer-facing failures.
        if check.status in {"present", "not_applicable", "not_captured"}:
            continue
        group = _group_for(check.event_id, check.cte, check.approved_obligation_id)
        if check.field_key not in group["missing_fields"]:
            group["missing_fields"].append(check.field_key)
        _extend_unique(group["evidence_ids"], check.evidence_ids)
        if check.field_key in TLC_FIELD_KEYS:
            group["tlc_root"] = True

    for check in tlc_checks:
        if check.status == "linked":
            continue
        group = _group_for(check.event_id, check.cte, check.approved_obligation_id)
        if check.reason not in group["tlc_reasons"]:
            group["tlc_reasons"].append(check.reason)
        _extend_unique(group["evidence_ids"], check.evidence_ids)
        group["tlc_root"] = True

    for group in event_groups.values():
        is_tlc_root = bool(group["tlc_root"])
        finding_type = "tlc_lineage" if is_tlc_root else "kde_completeness"
        high = is_tlc_root or any(field in HIGH_SEVERITY_FIELD_KEYS for field in group["missing_fields"])
        obligation = approved_obligations.get(group["obligation_id"]) or fallback_obligation
        findings.append(
            _finding(
                findings,
                event_id=group["event_id"],
                cte=group["cte"],
                severity="high" if high else "medium",
                status="gap",
                finding_type=finding_type,
                message=_record_gap_message(group["cte"], group["missing_fields"], is_tlc_root),
                obligation=obligation,
                evidence_ids=group["evidence_ids"],
                confidence=0.9 if is_tlc_root else 0.88,
                sub_issues=_record_sub_issues(group["missing_fields"], group["tlc_reasons"]),
                affected_fields=list(group["missing_fields"]),
            )
        )

    # --- Traceability plan: one finding listing all missing components ---
    missing_plan = [check for check in traceability_plan_checks if check.status not in {"present", "not_applicable"}]
    if missing_plan:
        plan_evidence: list[str] = []
        for check in missing_plan:
            _extend_unique(plan_evidence, check.evidence_ids)
        components = [check.component for check in missing_plan]
        findings.append(
            _finding(
                findings,
                event_id=None,
                cte="traceability_plan",
                severity="medium",
                status="gap",
                finding_type="traceability_plan",
                message=(
                    f"Traceability plan is incomplete: {len(components)} required "
                    f"component{'s' if len(components) != 1 else ''} not documented."
                ),
                obligation=approved_obligations.get(missing_plan[0].approved_obligation_id) or fallback_obligation,
                evidence_ids=plan_evidence,
                confidence=0.86,
                sub_issues=[f"Missing {_plan_component_label(component)}" for component in components],
                affected_fields=list(components),
            )
        )

    # --- Scope / exemption review items: grouped per record + check type ---
    scope_groups: "OrderedDict[tuple[str, str], dict[str, Any]]" = OrderedDict()
    for check in scope_exemption_checks:
        if check.check_type == "customer_evidence_quality_gate":
            continue
        key = (check.event_id or "__global__", check.check_type)
        group = scope_groups.get(key)
        if group is None:
            group = {"event_id": check.event_id, "check_type": check.check_type, "reasons": [], "evidence_ids": []}
            scope_groups[key] = group
        if check.reason not in group["reasons"]:
            group["reasons"].append(check.reason)
        _extend_unique(group["evidence_ids"], check.evidence_ids)

    for group in scope_groups.values():
        reasons = group["reasons"]
        message = reasons[0] if len(reasons) == 1 else f"{len(reasons)} items need reviewer judgment for this record."
        findings.append(
            _finding(
                findings,
                event_id=group["event_id"],
                cte=None,
                severity="medium",
                status="needs_review",
                finding_type=group["check_type"],
                message=message,
                obligation=fallback_obligation,
                evidence_ids=group["evidence_ids"],
                confidence=0.68,
                sub_issues=list(reasons),
            )
        )
    return findings


def _record_gap_message(cte: str | None, missing_fields: list[str], is_tlc_root: bool) -> str:
    label = _cte_label(cte)
    if is_tlc_root:
        other_fields = [field for field in missing_fields if field not in TLC_FIELD_KEYS]
        message = f"{label} is missing its Traceability Lot Code (TLC)"
        if other_fields:
            message += f" and {len(other_fields)} other required field{'s' if len(other_fields) != 1 else ''}"
        return message + "."
    if len(missing_fields) == 1:
        return f"{label} is missing a required field: {_field_label(missing_fields[0])}."
    return f"{label} is missing {len(missing_fields)} required fields."


def _record_sub_issues(missing_fields: list[str], tlc_reasons: list[str]) -> list[str]:
    issues = [f"Missing {_field_label(field)}" for field in missing_fields]
    for reason in tlc_reasons:
        if reason not in issues:
            issues.append(reason)
    return issues


def generate_exception_queue(findings: list[AuditFinding]) -> list[ExceptionQueueItem]:
    queue: list[ExceptionQueueItem] = []
    for finding in findings:
        queue_type = {
            "kde_completeness": "missing_kde",
            "tlc_lineage": "tlc_gap",
            "traceability_plan": "traceability_plan_gap",
            "sortable_export_readiness": "export_blocker",
            "exemption_claim": "exemption_review",
        }.get(finding.finding_type, "review_item")
        queue.append(
            ExceptionQueueItem(
                exception_id=f"phase11-exception-{len(queue) + 1:04d}",
                finding_id=finding.finding_id,
                event_id=finding.event_id,
                queue_type=queue_type,
                priority="high" if finding.severity == "high" else "medium",
                title=f"{finding.finding_type}: {finding.status}",
                details=finding.message,
                evidence_ids=finding.customer_evidence_ids,
                assigned_role="compliance_reviewer",
            )
        )
    return queue


def build_fda_style_export_package(
    *,
    rule_package: dict[str, Any],
    events: dict[str, CustomerEventNode],
    hardened_results: list[MultiSignalCteResult],
    kde_checks: list[KdeCompletenessCheck],
    audit_findings: list[AuditFinding],
    sortable_export_checks: list[SortableExportReadinessCheck],
) -> FdaStyleExportPackage:
    checks_by_event = defaultdict(list)
    for check in kde_checks:
        checks_by_event[(check.event_id, check.cte)].append(check)
    tabs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in hardened_results:
        event = events[result.event_id]
        for cte in result.final_ctes:
            row = {
                "event_id": result.event_id,
                "cte": cte,
                "product_name": event.product_name,
                "traceability_lot_code": event.lot_or_tlc,
                "source_lot_or_tlc": event.source_lot_or_tlc,
                "output_lot_or_tlc": event.output_lot_or_tlc,
                "event_datetime": event.event_datetime,
                "source_evidence_ids": event.evidence_ids,
            }
            for check in checks_by_event.get((result.event_id, cte), []):
                row[check.field_key] = check.observed_values[0] if check.observed_values else None
            tabs[cte].append(row)
    blockers = [
        {
            "check_id": check.check_id,
            "event_id": check.event_id,
            "cte": check.cte,
            "message": f"Sortable export blocked by missing fields: {', '.join(check.missing_fields)}.",
            "missing_fields": check.missing_fields,
        }
        for check in sortable_export_checks
        if check.status != "ready"
    ]
    citations = [
        citation
        for obligation in rule_package["records"]["obligations"]
        for citation in obligation.get("citations", [])[:1]
    ]
    return FdaStyleExportPackage(
        package_id="phase11-fda-style-export-package",
        generated_at=GENERATED_AT,
        rule_package_id=rule_package["package_id"],
        rule_package_version=rule_package["version"],
        status="blocked" if blockers else "ready",
        workbook_file="phase11-fda-style-export-package.xlsx",
        tabs=dict(sorted(tabs.items())),
        blockers=blockers,
        citations=citations,
    )


def _approved_obligations(rule_package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    obligations = {}
    for obligation in rule_package["records"]["obligations"]:
        if obligation.get("metadata", {}).get("review_status") != "approved":
            continue
        obligations[obligation["obligation_id"]] = obligation
    return obligations


def _mapping(event_id: str, cte: str, obligation: dict[str, Any], rule_package: dict[str, Any], index: int) -> EventObligationMapping:
    return EventObligationMapping(
        mapping_id=f"phase11-map-{index:04d}",
        event_id=event_id,
        cte=cte,
        approved_obligation_id=obligation["obligation_id"],
        obligation_action=obligation.get("action", ""),
        required_output=obligation.get("required_output"),
        citation=obligation.get("citations", [{}])[0],
        rule_package_id=rule_package["package_id"],
        rule_package_version=rule_package["version"],
    )


def _promote_kde_value_rows(
    evidence_by_id: dict[str, CustomerEvidenceRecord],
) -> dict[str, dict[str, list[tuple[str, str]]]]:
    """Reconstruct the 07_KDE_Values sheet (one logical KDE per row, declaring its own
    field_key + value) into event_id -> field_key -> [(value, evidence_id)]. This lets a
    contract's satisfied_by reference KDE-sheet fields the customer actually provided."""
    rows: "OrderedDict[Any, dict[str, tuple[str, str]]]" = OrderedDict()
    for record in evidence_by_id.values():
        if record.sheet_name != "07_KDE_Values":
            continue
        rows.setdefault(record.row_number, {})[record.field_key] = (record.normalized_value, record.evidence_id)
    promoted: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows.values():
        event_id = (row.get("event_id") or ("", ""))[0].strip()
        field_key = (row.get("kde_field_key") or ("", ""))[0].strip()
        value, evidence_id = row.get("kde_value") or ("", "")
        if event_id and field_key and value:
            promoted[event_id][field_key].append((value, evidence_id))
    return promoted


def _merge_promoted_kde_facts(
    facts: dict[str, list[str]],
    promoted: dict[str, dict[str, list[tuple[str, str]]]],
    event_node_id: str,
) -> None:
    """Merge promoted KDE-sheet facts into an event's facts. KDE rows key by the raw event id
    (e.g. SHIP-1); event nodes are scoped by product (SHIP-1:PROD-1), so match on the prefix."""
    raw_event_id = event_node_id.split(":", 1)[0]
    for candidate_event_id, field_values in promoted.items():
        if candidate_event_id != raw_event_id and not event_node_id.startswith(f"{candidate_event_id}:"):
            continue
        for field_key, pairs in field_values.items():
            for value, evidence_id in pairs:
                facts[field_key].append(value)
                if evidence_id:
                    facts[f"evidence:{field_key}"].append(evidence_id)


def _event_facts(event: CustomerEventNode, evidence_by_id: dict[str, CustomerEvidenceRecord]) -> dict[str, list[str]]:
    facts: dict[str, list[str]] = defaultdict(list)
    direct = {
        "event_datetime": event.event_datetime,
        "product_name": event.product_name,
        "traceability_lot_code": event.lot_or_tlc,
        "source_lot_or_tlc": event.source_lot_or_tlc,
        "output_lot_or_tlc": event.output_lot_or_tlc,
    }
    for key, value in direct.items():
        if value:
            facts[key].append(value)
            facts[f"evidence:{key}"].extend(event.evidence_ids)
    for evidence_id in event.evidence_ids:
        record = evidence_by_id.get(evidence_id)
        if not record:
            continue
        facts[record.field_key].append(record.normalized_value)
        facts[f"evidence:{record.field_key}"].append(record.evidence_id)
    return facts


def _find_obligation_by_cte(approved_obligations: dict[str, dict[str, Any]], cte: str) -> dict[str, Any]:
    for obligation in approved_obligations.values():
        if cte in (obligation.get("applies_to_ctes") or []):
            return obligation
    raise ValueError(f"missing approved obligation for CTE {cte}")


def _is_specific_cte_obligation(obligation: dict[str, Any], cte: str) -> bool:
    section_ref = CTE_SECTION_REFS.get(cte)
    if not section_ref:
        return False
    citations = obligation.get("citations") or []
    return any(
        isinstance(citation, dict) and str(citation.get("section_ref") or "").startswith(section_ref)
        for citation in citations
    )


def _find_obligation_containing(approved_obligations: dict[str, dict[str, Any]], token: str) -> dict[str, Any]:
    for obligation in approved_obligations.values():
        if token in obligation["obligation_id"]:
            return obligation
    raise ValueError(f"missing approved obligation containing {token}")


def _finding(
    findings: list[AuditFinding],
    *,
    event_id: str | None,
    cte: str | None,
    severity: str,
    status: str,
    finding_type: str,
    message: str,
    obligation: dict[str, Any],
    evidence_ids: list[str],
    confidence: float,
    sub_issues: list[str] | None = None,
    affected_fields: list[str] | None = None,
) -> AuditFinding:
    return AuditFinding(
        finding_id=f"phase11-finding-{len(findings) + 1:04d}",
        event_id=event_id,
        cte=cte,
        severity=severity,
        status=status,
        finding_type=finding_type,
        message=message,
        approved_obligation_id=obligation["obligation_id"],
        source_citation=obligation.get("citations", [{}])[0],
        customer_evidence_ids=evidence_ids,
        confidence=confidence,
        reviewer_status="needs_review" if status in {"gap", "needs_review"} else "system_pass",
        sub_issues=sub_issues or [],
        affected_fields=affected_fields or [],
    )


def _summary(
    *,
    rule_package: dict[str, Any],
    obligation_mappings: list[EventObligationMapping],
    kde_checks: list[KdeCompletenessCheck],
    tlc_checks: list[TlcLineageCheck],
    traceability_plan_checks: list[TraceabilityPlanCheck],
    scope_exemption_checks: list[ScopeExemptionCheck],
    records_readiness_checks: list[RecordsReadinessCheck],
    sortable_export_checks: list[SortableExportReadinessCheck],
    audit_findings: list[AuditFinding],
    exception_queue: list[ExceptionQueueItem],
    export_package: FdaStyleExportPackage,
) -> dict[str, Any]:
    finding_status_counts = Counter(finding.status for finding in audit_findings)
    return {
        "phase": 11,
        "generatedAt": GENERATED_AT,
        "rulePackageId": rule_package["package_id"],
        "rulePackageVersion": rule_package["version"],
        "approvedRuleOnly": True,
        "obligationMappings": len(obligation_mappings),
        "kdeChecks": len(kde_checks),
        "kdeStatusCounts": dict(sorted(Counter(check.status for check in kde_checks).items())),
        "tlcChecks": len(tlc_checks),
        "tlcStatusCounts": dict(sorted(Counter(check.status for check in tlc_checks).items())),
        "traceabilityPlanChecks": len(traceability_plan_checks),
        "scopeExemptionChecks": len(scope_exemption_checks),
        "recordsReadinessChecks": len(records_readiness_checks),
        "sortableExportChecks": len(sortable_export_checks),
        "auditFindings": len(audit_findings),
        "findingStatusCounts": dict(sorted(finding_status_counts.items())),
        "exceptionQueueItems": len(exception_queue),
        "exportPackageStatus": export_package.status,
        "acceptanceCoverage": {
            "RI-100_map_customer_ctes_to_approved_obligations": True,
            "RI-101_kde_completeness_checks": True,
            "RI-102_tlc_lineage_checks": True,
            "RI-103_traceability_plan_checks": True,
            "RI-104_exemption_scope_uncertainty_checks": True,
            "RI-105_records_fda_request_readiness": True,
            "RI-106_sortable_export_readiness": True,
            "RI-107_audit_findings": True,
            "RI-108_exception_queue": True,
            "RI-109_fda_style_export_package": True,
        },
    }


def _write_export_workbook(path: Path, export_package: FdaStyleExportPackage, findings: list[AuditFinding]) -> None:
    try:
        from openpyxl import Workbook  # type: ignore
    except Exception:
        return
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["package_id", export_package.package_id])
    summary.append(["status", export_package.status])
    summary.append(["rule_package_id", export_package.rule_package_id])
    summary.append(["rule_package_version", export_package.rule_package_version])
    summary.append(["blockers", len(export_package.blockers)])
    for tab_name, rows in export_package.tabs.items():
        sheet = workbook.create_sheet(tab_name[:31] or "Events")
        headers = sorted({key for row in rows for key in row.keys()})
        sheet.append(headers)
        for row in rows:
            sheet.append([json.dumps(row.get(header)) if isinstance(row.get(header), (list, dict)) else row.get(header) for header in headers])
    findings_sheet = workbook.create_sheet("Findings")
    findings_sheet.append(["finding_id", "event_id", "cte", "severity", "status", "type", "message", "approved_obligation_id"])
    for finding in findings:
        findings_sheet.append([
            finding.finding_id,
            finding.event_id,
            finding.cte,
            finding.severity,
            finding.status,
            finding.finding_type,
            finding.message,
            finding.approved_obligation_id,
        ])
    workbook.save(path)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
