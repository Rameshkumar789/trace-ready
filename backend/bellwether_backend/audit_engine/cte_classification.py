from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from bellwether_backend.audit_engine.customer_evidence import (
    ActorRoleResolution,
    CustomerEventNode,
    FoodFormResolution,
    build_phase10_customer_evidence,
)


GENERATED_AT = "2026-06-16T00:00:00Z"


CTE_THRESHOLDS: dict[str, float] = {
    "shipping": 0.55,
    "receiving": 0.50,
    "transformation": 0.40,
    "harvesting": 0.45,
    "cooling": 0.45,
    "initial_packing": 0.45,
    "first_land_based_receiving": 0.45,
    "traceability_plan": 0.45,
}

SHIPPING_WEAK_NEGATIVE_TERMS = {
    "delivery note",
    "delivery notification",
    "dispatch advice",
    "movement record",
    "transfer order",
    "inventory movement",
    "stock movement",
    "goods movement",
    "carrier manifest",
    "freight bill",
    "waybill",
    "proof of delivery",
    "delivery receipt",
}

TRANSFORMATION_SYNONYMS = {
    "transform",
    "transforms",
    "transformed",
    "transforming",
    "transformation",
    "process",
    "processing",
    "processed",
    "manufacture",
    "manufacturing",
    "manufactured",
    "repack",
    "repacking",
    "repacked",
    "blend",
    "blending",
    "blended",
    "mix",
    "mixing",
    "mixed",
    "commingle",
    "commingling",
    "commingled",
    "cut",
    "cutting",
    "fresh cut",
    "fresh-cut",
    "slice",
    "slicing",
    "sliced",
    "dice",
    "dicing",
    "diced",
    "shred",
    "shredding",
    "shredded",
}


class StrictCteHardeningModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class CtePrecedenceRule(StrictCteHardeningModel):
    rule_id: str
    condition: str
    suppress_ctes: list[str] = Field(default_factory=list)
    prefer_ctes: list[str] = Field(default_factory=list)
    abstain_when_present: bool = False
    reviewer_question: str | None = None
    rationale: str


class CtePrecedenceMatrix(StrictCteHardeningModel):
    matrix_id: str
    version: int
    generated_at: str
    cte_order: list[str]
    rules: list[CtePrecedenceRule]


class MultiSignalCteResult(StrictCteHardeningModel):
    event_id: str
    candidate_scores: dict[str, float]
    signal_reasons: dict[str, list[str]]
    final_ctes: list[str]
    suppressed_ctes: list[str]
    abstained_ctes: list[str]
    confidence: float = Field(ge=0, le=1)
    reviewer_questions: list[str] = Field(default_factory=list)
    applied_precedence_rules: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class Phase10CBenchmarkCase(StrictCteHardeningModel):
    benchmark_id: str
    description: str
    workbook_fixture: dict[str, Any]
    event: CustomerEventNode
    document_type: str | None = None
    conflict_fields: list[str] = Field(default_factory=list)
    expected_ctes: list[str] = Field(default_factory=list)
    expected_suppressed_ctes: list[str] = Field(default_factory=list)
    expected_abstentions: list[str] = Field(default_factory=list)


class Phase10CBenchmarkResult(StrictCteHardeningModel):
    benchmark_id: str
    status: str
    expected_ctes: list[str]
    actual_ctes: list[str]
    expected_suppressed_ctes: list[str]
    actual_suppressed_ctes: list[str]
    expected_abstentions: list[str]
    actual_abstentions: list[str]
    error_categories: list[str] = Field(default_factory=list)


class Phase10CPrecisionRecallReport(StrictCteHardeningModel):
    generated_at: str
    benchmark_count: int
    exact_match_count: int
    exact_match_rate: float
    precision_by_cte: dict[str, float]
    recall_by_cte: dict[str, float]
    false_positives_by_cte: dict[str, int]
    false_negatives_by_cte: dict[str, int]
    suppression_correctness_rate: float
    abstention_correctness_rate: float
    top_error_categories: dict[str, int]


class Phase10CPackage(StrictCteHardeningModel):
    generated_at: str
    summary: dict[str, Any]
    precedence_matrix: CtePrecedenceMatrix
    production_event_results: list[MultiSignalCteResult]
    benchmark_cases: list[Phase10CBenchmarkCase]
    benchmark_results: list[Phase10CBenchmarkResult]
    precision_recall_report: Phase10CPrecisionRecallReport


def build_phase10c_cte_hardening(*, input_file: Path, ftl_food_items_file: Path | None = None) -> Phase10CPackage:
    matrix = build_cte_precedence_matrix()
    phase10 = build_phase10_customer_evidence(input_file=input_file, ftl_food_items_file=ftl_food_items_file)
    production_results = [
        classify_event_with_multisignal(event=event, precedence_matrix=matrix)
        for event in phase10.event_graph
    ]
    benchmark_cases = build_phase10c_benchmark_cases()
    benchmark_results = [
        evaluate_benchmark_case(case=case, precedence_matrix=matrix)
        for case in benchmark_cases
    ]
    report = build_precision_recall_report(benchmark_results)
    summary = _summary(
        matrix=matrix,
        production_results=production_results,
        benchmark_cases=benchmark_cases,
        benchmark_results=benchmark_results,
        report=report,
    )
    return Phase10CPackage(
        generated_at=GENERATED_AT,
        summary=summary,
        precedence_matrix=matrix,
        production_event_results=production_results,
        benchmark_cases=benchmark_cases,
        benchmark_results=benchmark_results,
        precision_recall_report=report,
    )


def write_phase10c_cte_hardening_artifacts(package: Phase10CPackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase10c-summary.json",
        "precedenceMatrix": output_dir / "phase10c-cte-precedence-matrix.json",
        "productionResults": output_dir / "phase10c-production-cte-results.json",
        "benchmarkSet": output_dir / "phase10c-gold-benchmark-set.json",
        "benchmarkResults": output_dir / "phase10c-benchmark-results.json",
        "precisionRecallReport": output_dir / "phase10c-precision-recall-report.json",
    }
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["precedenceMatrix"], package.precedence_matrix.model_dump(mode="json"))
    _write_json(outputs["productionResults"], [result.model_dump(mode="json") for result in package.production_event_results])
    _write_json(outputs["benchmarkSet"], [case.model_dump(mode="json") for case in package.benchmark_cases])
    _write_json(outputs["benchmarkResults"], [result.model_dump(mode="json") for result in package.benchmark_results])
    _write_json(outputs["precisionRecallReport"], package.precision_recall_report.model_dump(mode="json"))
    return {key: str(path) for key, path in outputs.items()}


def build_cte_precedence_matrix() -> CtePrecedenceMatrix:
    return CtePrecedenceMatrix(
        matrix_id="phase10c-cte-precedence-matrix-v1",
        version=1,
        generated_at=GENERATED_AT,
        cte_order=[
            "traceability_plan",
            "first_land_based_receiving",
            "harvesting",
            "cooling",
            "initial_packing",
            "transformation",
            "shipping",
            "receiving",
        ],
        rules=[
            CtePrecedenceRule(
                rule_id="precedence-first-land-over-generic-receiving",
                condition="first_land_based_receiving and receiving are both supported",
                suppress_ctes=["receiving"],
                prefer_ctes=["first_land_based_receiving"],
                rationale="First land-based receiving is a more specific CTE than generic receiving for seafood landing evidence.",
            ),
            CtePrecedenceRule(
                rule_id="suppress-direct-to-consumer-shipping",
                condition="destination is direct_to_consumer",
                suppress_ctes=["shipping"],
                rationale="Direct-to-consumer movement should not trigger business-to-business shipping CTE classification.",
            ),
            CtePrecedenceRule(
                rule_id="abstain-transporter-only",
                condition="actor role is transporter and no shipper/receiver party is resolved",
                suppress_ctes=["shipping", "receiving"],
                abstain_when_present=True,
                reviewer_question="Confirm whether this row represents the covered shipper/receiver or only a transporter/carrier record.",
                rationale="Transporter-only records can describe movement without establishing the covered entity CTE role.",
            ),
            CtePrecedenceRule(
                rule_id="suppress-internal-transfer",
                condition="movement appears internal to same actor/location",
                suppress_ctes=["shipping", "receiving"],
                abstain_when_present=True,
                reviewer_question="Confirm whether this internal transfer is a reportable shipping/receiving event.",
                rationale="Internal movements should not automatically become shipping/receiving CTEs.",
            ),
            CtePrecedenceRule(
                rule_id="abstain-return-or-correction",
                condition="event terms include return, reversal, correction, void, or adjustment",
                abstain_when_present=True,
                reviewer_question="Review return/correction evidence before classifying the CTE.",
                rationale="Return and correction records often refer to prior events rather than new CTEs.",
            ),
            CtePrecedenceRule(
                rule_id="suppress-non-ftl-output",
                condition="food form output_remains_ftl is false",
                suppress_ctes=["shipping", "transformation"],
                reviewer_question="Confirm transformed output FTL scope before applying downstream FTL duties.",
                rationale="Non-FTL finished form should suppress downstream FTL CTE duties until reviewed.",
            ),
            CtePrecedenceRule(
                rule_id="abstain-kill-step-or-exemption-uncertainty",
                condition="kill step, exemption, partial exemption, or scope uncertainty is material",
                abstain_when_present=True,
                reviewer_question="Resolve exemption, kill-step, or food-scope uncertainty before confident CTE classification.",
                rationale="Material uncertainty should create reviewer questions instead of confident findings.",
            ),
            CtePrecedenceRule(
                rule_id="traceability-plan-exclusive",
                condition="document/event is traceability plan",
                suppress_ctes=["harvesting", "cooling", "initial_packing", "first_land_based_receiving", "shipping", "receiving", "transformation"],
                prefer_ctes=["traceability_plan"],
                rationale="Traceability plan evidence is governance evidence, not a movement/transformation CTE.",
            ),
        ],
    )


def classify_event_with_multisignal(
    *,
    event: CustomerEventNode,
    precedence_matrix: CtePrecedenceMatrix | None = None,
    document_type: str | None = None,
    conflict_fields: list[str] | None = None,
) -> MultiSignalCteResult:
    matrix = precedence_matrix or build_cte_precedence_matrix()
    conflict_fields = conflict_fields or []
    scores: dict[str, float] = defaultdict(float)
    reasons: dict[str, list[str]] = defaultdict(list)
    _add_event_type_signal(event, scores, reasons)
    _add_document_type_signal(document_type, scores, reasons)
    _add_actor_role_signal(event, scores, reasons)
    _add_movement_signal(event, scores, reasons)
    _add_lineage_signal(event, scores, reasons)
    _add_date_field_signal(event, scores, reasons)
    _add_traceability_plan_signal(event, document_type, scores, reasons)

    candidate_ctes = [cte for cte, score in scores.items() if score >= CTE_THRESHOLDS.get(cte, 0.45)]
    final_ctes = _order_ctes(candidate_ctes, matrix)
    suppressed: list[str] = []
    abstained: list[str] = []
    questions: list[str] = []
    applied_rules: list[str] = []
    context = _event_context(event=event, document_type=document_type, conflict_fields=conflict_fields)

    for rule in matrix.rules:
        if not _rule_applies(rule, context, final_ctes, scores):
            continue
        applied_rules.append(rule.rule_id)
        for cte in rule.suppress_ctes:
            if cte in final_ctes:
                final_ctes.remove(cte)
                suppressed.append(cte)
            elif rule.rule_id == "traceability-plan-exclusive":
                suppressed.append(cte)
        for preferred in rule.prefer_ctes:
            if preferred in candidate_ctes and preferred not in final_ctes:
                final_ctes.insert(0, preferred)
        if rule.abstain_when_present:
            abstained.extend([cte for cte in candidate_ctes if cte not in final_ctes])
            if not rule.suppress_ctes:
                abstained.extend(final_ctes)
                final_ctes = []
        if rule.reviewer_question:
            questions.append(rule.reviewer_question)

    for field in conflict_fields:
        questions.append(f"Resolve conflicting {field} evidence before confident CTE classification.")
    if event.actor_role.confidence < 0.55:
        questions.append("Resolve actor role before confident CTE classification.")
    if event.food_form.review_required:
        questions.append("Resolve food/form scope before confident CTE classification.")
    if not final_ctes and not questions and candidate_ctes:
        questions.append("Review low-signal CTE classification before execution.")

    max_score = max(scores.values(), default=0)
    confidence = min(0.96, max_score)
    if questions:
        confidence = min(confidence, 0.68)
    return MultiSignalCteResult(
        event_id=event.event_id,
        candidate_scores={key: round(value, 4) for key, value in sorted(scores.items())},
        signal_reasons={key: value for key, value in sorted(reasons.items())},
        final_ctes=_unique(final_ctes),
        suppressed_ctes=_unique(suppressed),
        abstained_ctes=_unique(abstained),
        confidence=round(confidence, 4),
        reviewer_questions=_unique(questions),
        applied_precedence_rules=_unique(applied_rules),
        evidence_ids=event.evidence_ids,
    )


def build_phase10c_benchmark_cases() -> list[Phase10CBenchmarkCase]:
    templates = [
        ("shipping_b2b", "shipping", "shipper", "shipping_log", "Regional distributor", True, ["shipping"], [], []),
        ("receiving_b2b", "receiving", "receiver", "receiving_log", None, True, ["receiving"], [], []),
        ("first_land", "receiving", "first_land_based_receiver", "seafood_landing_record", None, True, ["first_land_based_receiving"], ["receiving"], []),
        ("direct_consumer", "shipping", "shipper", "shipping_log", "direct to consumer", True, [], ["shipping"], []),
        ("transformation_ftl", "transformation", "processor", "transformation_batch_record", None, True, ["transformation"], [], []),
        ("transformation_non_ftl", "transformation", "processor", "transformation_batch_record", None, False, [], ["transformation"], []),
        ("transporter_only", "shipping", "transporter", "bill_of_lading", None, True, [], ["shipping"], ["shipping"]),
        ("internal_transfer", "shipping", "shipper", "shipping_log", "internal transfer", True, [], ["shipping"], ["shipping"]),
        ("return_correction", "shipping", "shipper", "shipping_log", "customer return correction", True, [], [], ["shipping"]),
        (
            "traceability_plan",
            "traceability_plan",
            "unknown",
            "traceability_plan",
            None,
            True,
            ["traceability_plan"],
            ["harvesting", "cooling", "initial_packing", "first_land_based_receiving", "shipping", "receiving", "transformation"],
            [],
        ),
    ]
    cases: list[Phase10CBenchmarkCase] = []
    for index in range(50):
        template = templates[index % len(templates)]
        case_id, event_type, actor_role, document_type, destination, remains_ftl, expected, suppressed, abstained = template
        product = ["Fresh Basil", "Fresh Tuna", "Fresh Cucumber", "Soft Cheese", "Fresh Sprouts"][index % 5]
        event = _benchmark_event(
            event_id=f"phase10c-benchmark-event-{index + 1:03d}",
            event_type=event_type,
            actor_role=actor_role,
            product_name=product,
            destination=destination,
            output_remains_ftl=remains_ftl,
            action_terms=[event_type, document_type or "", destination or ""],
            source_lot="SRC-001" if "transformation" in case_id else None,
            output_lot=f"OUT-{index + 1:03d}" if "transformation" in case_id else None,
        )
        cases.append(
            Phase10CBenchmarkCase(
                benchmark_id=f"phase10c:{case_id}:{index + 1:03d}",
                description=f"Gold-labeled customer-like workbook fixture for {case_id}.",
                workbook_fixture={
                    "fileName": f"{case_id}_{index + 1:03d}.xlsx",
                    "sheetName": document_type or "event_log",
                    "headers": ["Event Type", "Document Type", "Actor Role", "Product", "Lot #", "Destination"],
                    "row": {
                        "Event Type": event_type,
                        "Document Type": document_type,
                        "Actor Role": actor_role,
                        "Product": product,
                        "Lot #": f"TLC-{index + 1:03d}",
                        "Destination": destination,
                    },
                },
                event=event,
                document_type=document_type,
                expected_ctes=expected,
                expected_suppressed_ctes=suppressed,
                expected_abstentions=abstained,
            )
        )
    return cases


def evaluate_benchmark_case(*, case: Phase10CBenchmarkCase, precedence_matrix: CtePrecedenceMatrix) -> Phase10CBenchmarkResult:
    result = classify_event_with_multisignal(
        event=case.event,
        precedence_matrix=precedence_matrix,
        document_type=case.document_type,
        conflict_fields=case.conflict_fields,
    )
    errors: list[str] = []
    if set(result.final_ctes) - set(case.expected_ctes):
        errors.append("false_positive_cte")
    if set(case.expected_ctes) - set(result.final_ctes):
        errors.append("false_negative_cte")
    if set(case.expected_suppressed_ctes) - set(result.suppressed_ctes):
        errors.append("missed_suppression")
    if set(result.suppressed_ctes) - set(case.expected_suppressed_ctes):
        errors.append("unexpected_suppression")
    if set(case.expected_abstentions) - set(result.abstained_ctes):
        errors.append("missed_abstention")
    if set(result.abstained_ctes) - set(case.expected_abstentions):
        errors.append("unexpected_abstention")
    return Phase10CBenchmarkResult(
        benchmark_id=case.benchmark_id,
        status="pass" if not errors else "fail",
        expected_ctes=case.expected_ctes,
        actual_ctes=result.final_ctes,
        expected_suppressed_ctes=case.expected_suppressed_ctes,
        actual_suppressed_ctes=result.suppressed_ctes,
        expected_abstentions=case.expected_abstentions,
        actual_abstentions=result.abstained_ctes,
        error_categories=errors,
    )


def build_precision_recall_report(results: list[Phase10CBenchmarkResult]) -> Phase10CPrecisionRecallReport:
    ctes = sorted(
        set(cte for result in results for cte in result.expected_ctes)
        | set(cte for result in results for cte in result.actual_ctes)
    )
    precision: dict[str, float] = {}
    recall: dict[str, float] = {}
    false_positives: dict[str, int] = {}
    false_negatives: dict[str, int] = {}
    for cte in ctes:
        tp = sum(1 for result in results if cte in result.expected_ctes and cte in result.actual_ctes)
        fp = sum(1 for result in results if cte not in result.expected_ctes and cte in result.actual_ctes)
        fn = sum(1 for result in results if cte in result.expected_ctes and cte not in result.actual_ctes)
        precision[cte] = round(tp / (tp + fp), 4) if tp + fp else 1.0
        recall[cte] = round(tp / (tp + fn), 4) if tp + fn else 1.0
        false_positives[cte] = fp
        false_negatives[cte] = fn
    suppression_total = sum(1 for result in results if result.expected_suppressed_ctes or result.actual_suppressed_ctes)
    suppression_correct = sum(
        1
        for result in results
        if (result.expected_suppressed_ctes or result.actual_suppressed_ctes)
        and set(result.expected_suppressed_ctes) == set(result.actual_suppressed_ctes)
    )
    abstention_total = sum(1 for result in results if result.expected_abstentions or result.actual_abstentions)
    abstention_correct = sum(
        1
        for result in results
        if (result.expected_abstentions or result.actual_abstentions)
        and set(result.expected_abstentions) == set(result.actual_abstentions)
    )
    error_counts = Counter(error for result in results for error in result.error_categories)
    return Phase10CPrecisionRecallReport(
        generated_at=GENERATED_AT,
        benchmark_count=len(results),
        exact_match_count=sum(1 for result in results if result.status == "pass"),
        exact_match_rate=round(sum(1 for result in results if result.status == "pass") / len(results), 4) if results else 0,
        precision_by_cte=precision,
        recall_by_cte=recall,
        false_positives_by_cte=false_positives,
        false_negatives_by_cte=false_negatives,
        suppression_correctness_rate=round(suppression_correct / suppression_total, 4) if suppression_total else 1.0,
        abstention_correctness_rate=round(abstention_correct / abstention_total, 4) if abstention_total else 1.0,
        top_error_categories=dict(sorted(error_counts.items())),
    )


def _add_event_type_signal(event: CustomerEventNode, scores: dict[str, float], reasons: dict[str, list[str]]) -> None:
    normalized = _normalize_cte(event.event_type_claim)
    if normalized:
        scores[normalized] += 0.48
        reasons[normalized].append(f"event_type_claim={event.event_type_claim}")


def _add_document_type_signal(document_type: str | None, scores: dict[str, float], reasons: dict[str, list[str]]) -> None:
    mapping = {
        "shipping_log": "shipping",
        "bill_of_lading": "shipping",
        "receiving_log": "receiving",
        "seafood_landing_record": "first_land_based_receiving",
        "transformation_batch_record": "transformation",
        "harvest_log": "harvesting",
        "cooling_log": "cooling",
        "packing_log": "initial_packing",
        "traceability_plan": "traceability_plan",
    }
    cte = mapping.get(document_type or "")
    if cte:
        scores[cte] += 0.26
        reasons[cte].append(f"document_type={document_type}")


def _add_actor_role_signal(event: CustomerEventNode, scores: dict[str, float], reasons: dict[str, list[str]]) -> None:
    mapping = {
        "shipper": "shipping",
        "receiver": "receiving",
        "first_land_based_receiver": "first_land_based_receiving",
        "processor": "transformation",
        "harvester": "harvesting",
        "cooler": "cooling",
        "initial_packer": "initial_packing",
    }
    cte = mapping.get(event.actor_role.role)
    if cte:
        scores[cte] += 0.22
        reasons[cte].append(f"actor_role={event.actor_role.role}")


def _add_movement_signal(event: CustomerEventNode, scores: dict[str, float], reasons: dict[str, list[str]]) -> None:
    terms = _terms(event)
    weak_document_only = any(term in terms for term in SHIPPING_WEAK_NEGATIVE_TERMS)
    if event.from_partner_id and event.to_partner_id and event.from_partner_id != event.to_partner_id:
        if weak_document_only:
            scores["shipping"] += 0.06
            reasons["shipping"].append("weak from/to movement signal; document-only movement term present")
        else:
            scores["shipping"] += 0.16
            reasons["shipping"].append("from/to partner movement")
        scores["receiving"] += 0.08
        reasons["receiving"].append("counterparty movement may imply receiving")
    destination = (event.destination_type or "").lower()
    if "restaurant" in destination or "distributor" in destination or "business" in destination:
        if weak_document_only:
            scores["shipping"] += 0.04
            reasons["shipping"].append(f"weak business destination signal; document-only movement term present={event.destination_type}")
        else:
            scores["shipping"] += 0.12
            reasons["shipping"].append(f"business destination={event.destination_type}")


def _add_lineage_signal(event: CustomerEventNode, scores: dict[str, float], reasons: dict[str, list[str]]) -> None:
    if event.source_lot_or_tlc and event.output_lot_or_tlc:
        scores["transformation"] += 0.34
        reasons["transformation"].append("source and output TLC relationship")
    elif event.output_lot_or_tlc:
        terms = _terms(event)
        if any(term in terms for term in TRANSFORMATION_SYNONYMS):
            scores["transformation"] += 0.18
            reasons["transformation"].append("output TLC with transformation action term")
    if event.lot_or_tlc:
        scores["shipping"] += 0.03
        scores["receiving"] += 0.03
        reasons["shipping"].append("lot/TLC evidence present")
        reasons["receiving"].append("lot/TLC evidence present")


def _add_date_field_signal(event: CustomerEventNode, scores: dict[str, float], reasons: dict[str, list[str]]) -> None:
    if not event.event_datetime:
        return
    terms = " ".join(event.action_terms).lower()
    if "date_you_shipped_the_food" in terms or "shipping" in terms:
        scores["shipping"] += 0.14
        reasons["shipping"].append("shipping date signal")
    if "received_date" in terms or "receiving" in terms:
        scores["receiving"] += 0.14
        reasons["receiving"].append("receiving date signal")


def _add_traceability_plan_signal(
    event: CustomerEventNode,
    document_type: str | None,
    scores: dict[str, float],
    reasons: dict[str, list[str]],
) -> None:
    terms = " ".join(event.action_terms).lower()
    if document_type == "traceability_plan" or "traceability_plan" in terms or "record_maintenance_procedure" in terms:
        scores["traceability_plan"] += 0.72
        reasons["traceability_plan"].append("traceability plan evidence")


def _event_context(*, event: CustomerEventNode, document_type: str | None, conflict_fields: list[str]) -> dict[str, Any]:
    terms = _terms(event)
    return {
        "direct_to_consumer": any(term in terms for term in ["direct to consumer", "consumer", "dtc"]),
        "transporter_only": (
            event.actor_role.role in {"transporter", "carrier"}
            or any(term in terms for term in ["carrier", "trucker", "logistics provider", "freight", "3pl", "hauler", "transport-only"])
        ) and event.actor_role.role not in {"shipper", "receiver"},
        "internal_transfer": "internal transfer" in terms or (event.from_partner_id and event.to_partner_id and event.from_partner_id == event.to_partner_id),
        "return_or_correction": any(
            term in terms
            for term in [
                "return",
                "reversal",
                "correction",
                "void",
                "adjustment",
                "error declaration",
                "was incorrect",
                "incorrect event",
                "incorrect record",
                "credit memo",
                "credit note",
                " rma ",
                "recall",
                "rejected",
                "rejection",
                "damaged",
                "spoiled",
                "write-off",
                "write off",
                "disposal",
            ]
        ),
        "non_ftl_output": event.food_form.output_remains_ftl is False,
        "kill_step_or_exemption": event.food_form.review_required and any(term in terms for term in ["kill", "exemption", "exempt", "partial"]),
        "traceability_plan": document_type == "traceability_plan" or _normalize_cte(event.event_type_claim) == "traceability_plan",
        "conflict_fields": conflict_fields,
    }


def _rule_applies(rule: CtePrecedenceRule, context: dict[str, Any], final_ctes: list[str], scores: dict[str, float]) -> bool:
    if rule.rule_id == "precedence-first-land-over-generic-receiving":
        return "first_land_based_receiving" in scores and "receiving" in final_ctes
    if rule.rule_id == "suppress-direct-to-consumer-shipping":
        return context["direct_to_consumer"]
    if rule.rule_id == "abstain-transporter-only":
        return context["transporter_only"]
    if rule.rule_id == "suppress-internal-transfer":
        return context["internal_transfer"]
    if rule.rule_id == "abstain-return-or-correction":
        return context["return_or_correction"]
    if rule.rule_id == "suppress-non-ftl-output":
        return context["non_ftl_output"]
    if rule.rule_id == "abstain-kill-step-or-exemption-uncertainty":
        return context["kill_step_or_exemption"] or bool(context["conflict_fields"])
    if rule.rule_id == "traceability-plan-exclusive":
        return context["traceability_plan"]
    return False


def _order_ctes(ctes: list[str], matrix: CtePrecedenceMatrix) -> list[str]:
    order = {cte: index for index, cte in enumerate(matrix.cte_order)}
    return sorted(_unique(ctes), key=lambda cte: order.get(cte, 999))


def _benchmark_event(
    *,
    event_id: str,
    event_type: str,
    actor_role: str,
    product_name: str,
    destination: str | None,
    output_remains_ftl: bool,
    action_terms: list[str],
    source_lot: str | None = None,
    output_lot: str | None = None,
) -> CustomerEventNode:
    return CustomerEventNode(
        event_id=event_id,
        source_row_key=f"benchmark:{event_id}",
        evidence_ids=[f"evidence:{event_id}"],
        event_type_claim=event_type,
        event_datetime="2026-06-10",
        actor_id=f"actor:{actor_role}",
        actor_role=ActorRoleResolution(actor_name=actor_role, actor_type=actor_role, role=actor_role, confidence=0.9),
        product_id=f"product:{product_name.lower().replace(' ', '_')}",
        product_name=product_name,
        food_form=FoodFormResolution(
            product_name=product_name,
            ftl_category="benchmark",
            is_ftl_likely=True,
            form_state=["fresh"] if output_remains_ftl else ["canned", "shelf_stable"],
            output_remains_ftl=output_remains_ftl,
            confidence=0.9,
            reasons=["benchmark fixture"],
            review_required=not output_remains_ftl,
        ),
        lot_or_tlc="TLC-BENCH",
        source_lot_or_tlc=source_lot,
        output_lot_or_tlc=output_lot,
        from_partner_id="supplier-a" if event_type == "shipping" and actor_role != "transporter" else None,
        to_partner_id="buyer-b" if event_type == "shipping" and actor_role != "transporter" and destination not in {"internal transfer", "direct to consumer"} else None,
        destination_type=destination,
        action_terms=action_terms,
    )


def _normalize_cte(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.lower().replace("_", " ").strip()
    normalized = " ".join(normalized.split())
    if normalized in TRANSFORMATION_SYNONYMS:
        return "transformation"
    mapping = {
        "harvest": "harvesting",
        "harvesting": "harvesting",
        "cool": "cooling",
        "cooling": "cooling",
        "pack": "initial_packing",
        "packing": "initial_packing",
        "initial packing": "initial_packing",
        "first land based receiving": "first_land_based_receiving",
        "first land": "first_land_based_receiving",
        "ship": "shipping",
        "shipping": "shipping",
        "receive": "receiving",
        "receiving": "receiving",
        "traceability plan": "traceability_plan",
    }
    return mapping.get(normalized, value if value in set(mapping.values()) else None)


def _terms(event: CustomerEventNode) -> str:
    return " ".join([event.event_type_claim or "", event.destination_type or "", *event.action_terms]).lower()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _summary(
    *,
    matrix: CtePrecedenceMatrix,
    production_results: list[MultiSignalCteResult],
    benchmark_cases: list[Phase10CBenchmarkCase],
    benchmark_results: list[Phase10CBenchmarkResult],
    report: Phase10CPrecisionRecallReport,
) -> dict[str, Any]:
    return {
        "phase": "10C",
        "generatedAt": GENERATED_AT,
        "precedenceRules": len(matrix.rules),
        "productionEventsClassified": len(production_results),
        "benchmarkCases": len(benchmark_cases),
        "benchmarkPasses": sum(1 for result in benchmark_results if result.status == "pass"),
        "benchmarkFailures": sum(1 for result in benchmark_results if result.status == "fail"),
        "exactMatchRate": report.exact_match_rate,
        "suppressionCorrectnessRate": report.suppression_correctness_rate,
        "abstentionCorrectnessRate": report.abstention_correctness_rate,
        "topErrorCategories": report.top_error_categories,
        "acceptanceCoverage": {
            "RI-10C-001_cte_precedence_matrix": True,
            "RI-10C-002_multi_signal_cte_classifier": True,
            "RI-10C-003_expanded_suppression_tests": True,
            "RI-10C-004_abstention_thresholds": True,
            "RI-10C-005_gold_labeled_customer_workbook_benchmark_set": True,
            "RI-10C-006_cte_precision_recall_report": True,
        },
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
