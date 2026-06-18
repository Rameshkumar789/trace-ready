from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from traceready_backend.audit_engine.cte_classification import (
    CtePrecedenceMatrix,
    MultiSignalCteResult,
    _benchmark_event,
    build_cte_precedence_matrix,
    classify_event_with_multisignal,
)
from traceready_backend.audit_engine.customer_evidence import CustomerEventNode


GENERATED_AT = "2026-06-16T00:00:00Z"


class StrictGeneralizationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class Phase12GoldLabel(StrictGeneralizationModel):
    scenario_id: str
    expected_actor_role: str
    expected_product_name: str
    expected_food_form: dict[str, Any]
    expected_ctes: list[str] = Field(default_factory=list)
    expected_obligation_ids: list[str] = Field(default_factory=list)
    expected_suppressed_ctes: list[str] = Field(default_factory=list)
    expected_abstentions: list[str] = Field(default_factory=list)
    negative_cte_expectations: list[str] = Field(default_factory=list)
    expected_food_scope_review: bool = False
    expected_actor_role_review: bool = False
    expected_citation_required: bool = True


class Phase12Scenario(StrictGeneralizationModel):
    scenario_id: str
    scenario_family: str
    description: str
    food_category: str
    actor_context: str
    form_context: str
    workbook_fixture: dict[str, Any]
    event: CustomerEventNode
    document_type: str | None = None
    conflict_fields: list[str] = Field(default_factory=list)
    gold_label: Phase12GoldLabel


class Phase12ScenarioResult(StrictGeneralizationModel):
    scenario_id: str
    status: str
    expected_ctes: list[str]
    actual_ctes: list[str]
    expected_obligation_ids: list[str]
    actual_obligation_ids: list[str]
    expected_suppressed_ctes: list[str]
    actual_suppressed_ctes: list[str]
    expected_abstentions: list[str]
    actual_abstentions: list[str]
    citation_correct: bool
    food_scope_review_correct: bool
    actor_role_review_correct: bool
    error_categories: list[str] = Field(default_factory=list)
    applied_precedence_rules: list[str] = Field(default_factory=list)
    reviewer_questions: list[str] = Field(default_factory=list)


class GeneralizationMetrics(StrictGeneralizationModel):
    generated_at: str
    scenario_count: int
    exact_scenario_pass_count: int
    exact_scenario_pass_rate: float
    cte_precision_by_cte: dict[str, float]
    cte_recall_by_cte: dict[str, float]
    obligation_precision: float
    obligation_recall: float
    false_positive_rate: float
    false_negative_rate: float
    abstention_correctness: float
    suppression_correctness: float
    citation_correctness: float
    food_scope_review_correctness: float
    actor_role_review_correctness: float
    top_error_categories: dict[str, int]


class InferenceErrorReport(StrictGeneralizationModel):
    generated_at: str
    scenario_count: int
    over_triggered_ctes: list[dict[str, Any]]
    missed_ctes: list[dict[str, Any]]
    wrong_food_scope_decisions: list[dict[str, Any]]
    wrong_actor_role_decisions: list[dict[str, Any]]
    missing_abstentions: list[dict[str, Any]]
    obligation_false_positives: list[dict[str, Any]]
    obligation_false_negatives: list[dict[str, Any]]
    citation_failures: list[dict[str, Any]]
    summary_counts: dict[str, int]


class ParserScenarioResult(StrictGeneralizationModel):
    scenario_id: str
    expected_ctes: list[str]
    parser_ctes: list[str]
    parser_abstentions: list[str] = Field(default_factory=list)
    exact_cte_match: bool


class ParserEvaluationRun(StrictGeneralizationModel):
    parser_id: str
    parser_version: str
    parser_type: str
    prompt_id: str | None = None
    deterministic_rule_execution_unchanged: bool
    scenario_count: int
    exact_cte_match_rate: float
    precision: float
    recall: float
    abstention_rate: float
    results: list[ParserScenarioResult]


class ParserEvaluationHarness(StrictGeneralizationModel):
    generated_at: str
    purpose: str
    live_model_outputs_evaluated: bool
    approved_rule_package_id: str
    approved_rule_package_version: int
    evaluation_runs: list[ParserEvaluationRun]
    comparison_notes: list[str]


class DriftChangeMonitorReport(StrictGeneralizationModel):
    generated_at: str
    status: str
    baseline_status: str
    monitored_inputs: list[dict[str, Any]]
    current_run_statuses: dict[str, str]
    change_policy: dict[str, Any]
    rerun_required_before_publication: bool
    publication_gate: str


class Phase12GeneralizationPackage(StrictGeneralizationModel):
    generated_at: str
    summary: dict[str, Any]
    scenarios: list[Phase12Scenario]
    gold_labels: list[Phase12GoldLabel]
    results: list[Phase12ScenarioResult]
    metrics: GeneralizationMetrics
    inference_error_report: InferenceErrorReport
    parser_evaluation_harness: ParserEvaluationHarness
    drift_change_monitor_report: DriftChangeMonitorReport


def build_phase12_generalization_evaluation(
    *,
    approved_rule_package_file: Path,
    phase8_summary_file: Path | None = None,
    phase10c_summary_file: Path | None = None,
    phase11_summary_file: Path | None = None,
) -> Phase12GeneralizationPackage:
    rule_package = json.loads(approved_rule_package_file.read_text(encoding="utf-8"))
    approved_obligations = _approved_obligations(rule_package)
    matrix = build_cte_precedence_matrix()
    scenarios = build_phase12_unseen_scenarios(approved_obligations=approved_obligations)
    results = [
        evaluate_phase12_scenario(
            scenario=scenario,
            approved_obligations=approved_obligations,
            precedence_matrix=matrix,
        )
        for scenario in scenarios
    ]
    metrics = build_generalization_metrics(results)
    error_report = build_inference_error_report(results)
    parser_harness = build_parser_evaluation_harness(
        scenarios=scenarios,
        rule_package=rule_package,
    )
    drift_report = build_drift_change_monitor_report(
        rule_package=rule_package,
        scenarios=scenarios,
        results=results,
        phase8_summary_file=phase8_summary_file,
        phase10c_summary_file=phase10c_summary_file,
        phase11_summary_file=phase11_summary_file,
    )
    summary = _summary(
        rule_package=rule_package,
        scenarios=scenarios,
        results=results,
        metrics=metrics,
        error_report=error_report,
        parser_harness=parser_harness,
        drift_report=drift_report,
    )
    return Phase12GeneralizationPackage(
        generated_at=GENERATED_AT,
        summary=summary,
        scenarios=scenarios,
        gold_labels=[scenario.gold_label for scenario in scenarios],
        results=results,
        metrics=metrics,
        inference_error_report=error_report,
        parser_evaluation_harness=parser_harness,
        drift_change_monitor_report=drift_report,
    )


def write_phase12_generalization_artifacts(package: Phase12GeneralizationPackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase12-summary.json",
        "metrics": output_dir / "phase12-generalization-metrics.json",
        "challengeSet": output_dir / "phase12-unseen-scenario-challenge-set.json",
        "goldLabels": output_dir / "phase12-gold-labels.json",
        "regressionResults": output_dir / "phase12-regression-results.json",
        "inferenceErrorReport": output_dir / "phase12-inference-error-report.json",
        "parserEvaluationHarness": output_dir / "phase12-parser-evaluation-harness.json",
        "driftChangeMonitor": output_dir / "phase12-drift-change-monitor-report.json",
    }
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["metrics"], package.metrics.model_dump(mode="json"))
    _write_json(outputs["challengeSet"], [scenario.model_dump(mode="json") for scenario in package.scenarios])
    _write_json(outputs["goldLabels"], [label.model_dump(mode="json") for label in package.gold_labels])
    _write_json(outputs["regressionResults"], [result.model_dump(mode="json") for result in package.results])
    _write_json(outputs["inferenceErrorReport"], package.inference_error_report.model_dump(mode="json"))
    _write_json(outputs["parserEvaluationHarness"], package.parser_evaluation_harness.model_dump(mode="json"))
    _write_json(outputs["driftChangeMonitor"], package.drift_change_monitor_report.model_dump(mode="json"))
    return {key: str(path) for key, path in outputs.items()}


def build_phase12_unseen_scenarios(*, approved_obligations: dict[str, dict[str, Any]]) -> list[Phase12Scenario]:
    products = [
        ("fresh_basil", "Fresh Basil", "fresh herbs", True),
        ("fresh_tuna", "Fresh Tuna", "seafood", True),
        ("soft_cheese", "Soft Cheese", "soft cheese", True),
        ("fresh_cucumber", "Fresh Cucumber", "fresh produce", True),
        ("fresh_sprouts", "Fresh Sprouts", "sprouts", True),
    ]
    templates = [
        ("shipping_b2b", "shipping", "shipper", "shipping_log", "regional distributor", True, ["shipping"], [], [], "Distributor outbound B2B shipment."),
        ("receiving_b2b", "receiving", "receiver", "receiving_log", None, True, ["receiving"], [], [], "Restaurant or distributor inbound receipt."),
        ("first_land_seafood", "receiving", "first_land_based_receiver", "seafood_landing_record", None, True, ["first_land_based_receiving"], ["receiving"], [], "First land-based seafood receiving."),
        ("transformation_ftl", "transformation", "processor", "transformation_batch_record", None, True, ["transformation"], [], [], "FTL ingredient transformed into FTL output."),
        ("direct_consumer", "shipping", "shipper", "shipping_log", "direct to consumer", True, [], ["shipping"], [], "Consumer shipment that should not trigger B2B shipping."),
        ("non_ftl_transformation", "transformation", "processor", "transformation_batch_record", None, False, [], ["transformation"], [], "Transformation into non-FTL finished form."),
        ("transporter_only", "shipping", "transporter", "bill_of_lading", None, True, [], ["shipping"], ["shipping"], "Carrier-only record that should abstain."),
        ("internal_transfer", "shipping", "shipper", "shipping_log", "internal transfer", True, [], ["shipping"], ["shipping"], "Internal facility movement."),
        ("return_correction", "shipping", "shipper", "shipping_log", "customer return correction", True, [], [], ["shipping"], "Return or correction row."),
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
            "Traceability plan governance evidence.",
        ),
        ("harvesting", "harvesting", "harvester", "harvest_log", None, True, ["harvesting"], [], [], "Harvest lot record."),
        ("cooling", "cooling", "cooler", "cooling_log", None, True, ["cooling"], [], [], "Cooling event record."),
        ("initial_packing", "initial_packing", "initial_packer", "packing_log", None, True, ["initial_packing"], [], [], "Initial packing record."),
        ("kill_step_uncertainty", "transformation", "processor", "transformation_batch_record", None, False, [], ["transformation"], ["transformation"], "Kill-step or scope uncertainty."),
        ("exemption_claim_shipping", "shipping", "shipper", "shipping_log", "regional distributor", True, [], [], ["shipping"], "Shipping row with unresolved exemption claim."),
        ("ambiguous_actor_receiving", "receiving", "unknown", "receiving_log", None, True, ["receiving"], [], [], "Receiving row with unresolved actor role."),
        ("food_scope_review_shipping", "shipping", "shipper", "shipping_log", "regional distributor", True, ["shipping"], [], [], "Shipping row with food/form review required."),
        ("restaurant_receiving", "receiving", "receiver", "receiving_log", "restaurant", True, ["receiving"], [], [], "Restaurant inbound receiving."),
        ("distribution_crossdock", "shipping", "shipper", "shipping_log", "business crossdock", True, ["shipping"], [], [], "Distribution crossdock shipment."),
        ("seafood_processor_shipping", "shipping", "shipper", "shipping_log", "seafood processor", True, ["shipping"], [], [], "Seafood processor outbound shipment."),
    ]
    scenarios: list[Phase12Scenario] = []
    for product_index, (product_slug, product_name, category, remains_default) in enumerate(products):
        for template_index, template in enumerate(templates):
            (
                family,
                event_type,
                actor_role,
                document_type,
                destination,
                output_remains_ftl,
                expected_ctes,
                expected_suppressed,
                expected_abstentions,
                description,
            ) = template
            scenario_number = product_index * len(templates) + template_index + 1
            event = _benchmark_event(
                event_id=f"phase12-event-{scenario_number:03d}",
                event_type=event_type,
                actor_role=actor_role,
                product_name=product_name,
                destination=destination,
                output_remains_ftl=output_remains_ftl and remains_default,
                action_terms=_action_terms(family, event_type, document_type, destination),
                source_lot=f"SRC-{scenario_number:03d}" if "transformation" in family else None,
                output_lot=f"OUT-{scenario_number:03d}" if "transformation" in family else None,
            )
            expected_food_scope_review = family in {"non_ftl_transformation", "food_scope_review_shipping", "exemption_claim_shipping", "kill_step_uncertainty"}
            expected_actor_role_review = family == "ambiguous_actor_receiving"
            if family in {"exemption_claim_shipping", "food_scope_review_shipping"}:
                event = _with_food_scope_review(event, family)
            if family == "ambiguous_actor_receiving":
                event = _with_actor_role_review(event)
            expected_obligations = _obligation_ids_for_ctes(expected_ctes, approved_obligations)
            scenario_id = f"phase12:{family}:{product_slug}:{scenario_number:03d}"
            gold_label = Phase12GoldLabel(
                scenario_id=scenario_id,
                expected_actor_role=event.actor_role.role,
                expected_product_name=product_name,
                expected_food_form=event.food_form.model_dump(mode="json"),
                expected_ctes=expected_ctes,
                expected_obligation_ids=expected_obligations,
                expected_suppressed_ctes=expected_suppressed,
                expected_abstentions=expected_abstentions,
                negative_cte_expectations=sorted(set(expected_suppressed + expected_abstentions)),
                expected_food_scope_review=expected_food_scope_review,
                expected_actor_role_review=expected_actor_role_review,
            )
            scenarios.append(
                Phase12Scenario(
                    scenario_id=scenario_id,
                    scenario_family=family,
                    description=description,
                    food_category=category,
                    actor_context=actor_role,
                    form_context="FTL remains covered" if event.food_form.output_remains_ftl else "Output or scope needs review",
                    workbook_fixture={
                        "fileName": f"{family}_{product_slug}_{scenario_number:03d}.xlsx",
                        "sheetName": document_type or "event_log",
                        "headers": ["Event Type", "Document Type", "Actor Role", "Product", "Lot #", "Destination", "Source Lot", "Output Lot"],
                        "row": {
                            "Event Type": event_type,
                            "Document Type": document_type,
                            "Actor Role": actor_role,
                            "Product": product_name,
                            "Lot #": f"TLC-{scenario_number:03d}",
                            "Destination": destination,
                            "Source Lot": event.source_lot_or_tlc,
                            "Output Lot": event.output_lot_or_tlc,
                        },
                    },
                    event=event,
                    document_type=document_type,
                    gold_label=gold_label,
                )
            )
    return scenarios


def evaluate_phase12_scenario(
    *,
    scenario: Phase12Scenario,
    approved_obligations: dict[str, dict[str, Any]],
    precedence_matrix: CtePrecedenceMatrix | None = None,
) -> Phase12ScenarioResult:
    result = classify_event_with_multisignal(
        event=scenario.event,
        precedence_matrix=precedence_matrix or build_cte_precedence_matrix(),
        document_type=scenario.document_type,
        conflict_fields=scenario.conflict_fields,
    )
    actual_obligations = _obligation_ids_for_ctes(result.final_ctes, approved_obligations)
    citation_correct = _citation_correct(actual_obligations, approved_obligations)
    food_scope_review_correct = _food_scope_review_correct(scenario, result)
    actor_role_review_correct = _actor_role_review_correct(scenario, result)
    errors = _result_errors(scenario, result, actual_obligations, citation_correct, food_scope_review_correct, actor_role_review_correct)
    return Phase12ScenarioResult(
        scenario_id=scenario.scenario_id,
        status="pass" if not errors else "fail",
        expected_ctes=scenario.gold_label.expected_ctes,
        actual_ctes=result.final_ctes,
        expected_obligation_ids=scenario.gold_label.expected_obligation_ids,
        actual_obligation_ids=actual_obligations,
        expected_suppressed_ctes=scenario.gold_label.expected_suppressed_ctes,
        actual_suppressed_ctes=result.suppressed_ctes,
        expected_abstentions=scenario.gold_label.expected_abstentions,
        actual_abstentions=result.abstained_ctes,
        citation_correct=citation_correct,
        food_scope_review_correct=food_scope_review_correct,
        actor_role_review_correct=actor_role_review_correct,
        error_categories=errors,
        applied_precedence_rules=result.applied_precedence_rules,
        reviewer_questions=result.reviewer_questions,
    )


def build_generalization_metrics(results: list[Phase12ScenarioResult]) -> GeneralizationMetrics:
    ctes = sorted(set(cte for result in results for cte in result.expected_ctes + result.actual_ctes))
    precision_by_cte: dict[str, float] = {}
    recall_by_cte: dict[str, float] = {}
    total_tp = total_fp = total_fn = 0
    for cte in ctes:
        tp = sum(1 for result in results if cte in result.expected_ctes and cte in result.actual_ctes)
        fp = sum(1 for result in results if cte not in result.expected_ctes and cte in result.actual_ctes)
        fn = sum(1 for result in results if cte in result.expected_ctes and cte not in result.actual_ctes)
        precision_by_cte[cte] = _ratio(tp, tp + fp, empty=1.0)
        recall_by_cte[cte] = _ratio(tp, tp + fn, empty=1.0)
        total_tp += tp
        total_fp += fp
        total_fn += fn
    obligation_tp = sum(
        len(set(result.expected_obligation_ids) & set(result.actual_obligation_ids))
        for result in results
    )
    obligation_fp = sum(
        len(set(result.actual_obligation_ids) - set(result.expected_obligation_ids))
        for result in results
    )
    obligation_fn = sum(
        len(set(result.expected_obligation_ids) - set(result.actual_obligation_ids))
        for result in results
    )
    error_counts = Counter(error for result in results for error in result.error_categories)
    return GeneralizationMetrics(
        generated_at=GENERATED_AT,
        scenario_count=len(results),
        exact_scenario_pass_count=sum(1 for result in results if result.status == "pass"),
        exact_scenario_pass_rate=_ratio(sum(1 for result in results if result.status == "pass"), len(results)),
        cte_precision_by_cte=precision_by_cte,
        cte_recall_by_cte=recall_by_cte,
        obligation_precision=_ratio(obligation_tp, obligation_tp + obligation_fp, empty=1.0),
        obligation_recall=_ratio(obligation_tp, obligation_tp + obligation_fn, empty=1.0),
        false_positive_rate=_ratio(total_fp, total_tp + total_fp, empty=0.0),
        false_negative_rate=_ratio(total_fn, total_tp + total_fn, empty=0.0),
        abstention_correctness=_set_correctness(results, "expected_abstentions", "actual_abstentions"),
        suppression_correctness=_set_correctness(results, "expected_suppressed_ctes", "actual_suppressed_ctes"),
        citation_correctness=_ratio(sum(1 for result in results if result.citation_correct), len(results)),
        food_scope_review_correctness=_ratio(sum(1 for result in results if result.food_scope_review_correct), len(results)),
        actor_role_review_correctness=_ratio(sum(1 for result in results if result.actor_role_review_correct), len(results)),
        top_error_categories=dict(sorted(error_counts.items())),
    )


def build_inference_error_report(results: list[Phase12ScenarioResult]) -> InferenceErrorReport:
    over_triggered = []
    missed = []
    wrong_scope = []
    wrong_actor = []
    missing_abstentions = []
    obligation_fps = []
    obligation_fns = []
    citation_failures = []
    for result in results:
        unexpected_ctes = sorted(set(result.actual_ctes) - set(result.expected_ctes))
        missed_ctes = sorted(set(result.expected_ctes) - set(result.actual_ctes))
        missing_abstain = sorted(set(result.expected_abstentions) - set(result.actual_abstentions))
        fp_obligations = sorted(set(result.actual_obligation_ids) - set(result.expected_obligation_ids))
        fn_obligations = sorted(set(result.expected_obligation_ids) - set(result.actual_obligation_ids))
        if unexpected_ctes:
            over_triggered.append({"scenario_id": result.scenario_id, "ctes": unexpected_ctes})
        if missed_ctes:
            missed.append({"scenario_id": result.scenario_id, "ctes": missed_ctes})
        if not result.food_scope_review_correct:
            wrong_scope.append({"scenario_id": result.scenario_id, "reviewer_questions": result.reviewer_questions})
        if not result.actor_role_review_correct:
            wrong_actor.append({"scenario_id": result.scenario_id, "reviewer_questions": result.reviewer_questions})
        if missing_abstain:
            missing_abstentions.append({"scenario_id": result.scenario_id, "ctes": missing_abstain})
        if fp_obligations:
            obligation_fps.append({"scenario_id": result.scenario_id, "obligation_ids": fp_obligations})
        if fn_obligations:
            obligation_fns.append({"scenario_id": result.scenario_id, "obligation_ids": fn_obligations})
        if not result.citation_correct:
            citation_failures.append({"scenario_id": result.scenario_id, "obligation_ids": result.actual_obligation_ids})
    return InferenceErrorReport(
        generated_at=GENERATED_AT,
        scenario_count=len(results),
        over_triggered_ctes=over_triggered,
        missed_ctes=missed,
        wrong_food_scope_decisions=wrong_scope,
        wrong_actor_role_decisions=wrong_actor,
        missing_abstentions=missing_abstentions,
        obligation_false_positives=obligation_fps,
        obligation_false_negatives=obligation_fns,
        citation_failures=citation_failures,
        summary_counts={
            "over_triggered_ctes": len(over_triggered),
            "missed_ctes": len(missed),
            "wrong_food_scope_decisions": len(wrong_scope),
            "wrong_actor_role_decisions": len(wrong_actor),
            "missing_abstentions": len(missing_abstentions),
            "obligation_false_positives": len(obligation_fps),
            "obligation_false_negatives": len(obligation_fns),
            "citation_failures": len(citation_failures),
        },
    )


def build_parser_evaluation_harness(
    *,
    scenarios: list[Phase12Scenario],
    rule_package: dict[str, Any],
) -> ParserEvaluationHarness:
    runs = [
        _evaluate_parser_run(
            parser_id="deterministic_multisignal_parser",
            parser_version="phase10c-v1",
            parser_type="deterministic",
            scenarios=scenarios,
            predict=_deterministic_parser_prediction,
        ),
        _evaluate_parser_run(
            parser_id="permissive_keyword_parser",
            parser_version="baseline-v0",
            parser_type="comparison_baseline",
            scenarios=scenarios,
            predict=_keyword_parser_prediction,
        ),
        _evaluate_parser_run(
            parser_id="conservative_abstention_parser",
            parser_version="baseline-v0",
            parser_type="comparison_baseline",
            scenarios=scenarios,
            predict=_conservative_parser_prediction,
        ),
    ]
    return ParserEvaluationHarness(
        generated_at=GENERATED_AT,
        purpose="Compare fact-extraction parser candidates without changing approved deterministic rule execution. Current Phase 12 runs include the deterministic classifier and non-AI baselines only; live OpenAI/Anthropic prompt outputs are not evaluated yet.",
        live_model_outputs_evaluated=False,
        approved_rule_package_id=rule_package["package_id"],
        approved_rule_package_version=rule_package["version"],
        evaluation_runs=runs,
        comparison_notes=[
            "Parser candidates are evaluated against gold labels before any parsed facts are allowed into deterministic approved-rule execution.",
            "The approved rule package remains fixed; this harness measures fact extraction quality, not legal-rule generation.",
            "No live OpenAI, Anthropic, or other AI model output was used in the current Phase 12 parser comparison.",
        ],
    )


def build_drift_change_monitor_report(
    *,
    rule_package: dict[str, Any],
    scenarios: list[Phase12Scenario],
    results: list[Phase12ScenarioResult],
    phase8_summary_file: Path | None,
    phase10c_summary_file: Path | None,
    phase11_summary_file: Path | None,
) -> DriftChangeMonitorReport:
    monitored_inputs = [
        {
            "input": "approved_rule_package",
            "package_id": rule_package["package_id"],
            "version": rule_package["version"],
            "hash": _stable_hash(rule_package),
            "rerun_suites_on_change": ["phase8_benchmark", "phase10c_customer_cte_benchmark", "phase11_customer_evidence_sample", "phase12_generalization"],
        },
        {
            "input": "phase12_unseen_challenge_set",
            "scenario_count": len(scenarios),
            "hash": _stable_hash([scenario.model_dump(mode="json") for scenario in scenarios]),
            "rerun_suites_on_change": ["phase12_generalization"],
        },
    ]
    for label, path in [
        ("phase8_benchmark_summary", phase8_summary_file),
        ("phase10c_customer_cte_summary", phase10c_summary_file),
        ("phase11_customer_evidence_summary", phase11_summary_file),
    ]:
        if path and path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            monitored_inputs.append({"input": label, "path": str(path), "hash": _stable_hash(payload)})
    pass_count = sum(1 for result in results if result.status == "pass")
    status = "stable" if pass_count == len(results) else "needs_review"
    return DriftChangeMonitorReport(
        generated_at=GENERATED_AT,
        status=status,
        baseline_status="created",
        monitored_inputs=monitored_inputs,
        current_run_statuses={
            "phase12_generalization": "pass" if status == "stable" else "fail",
            "approved_rule_package": "approved" if rule_package.get("status") == "approved" else "needs_review",
            "scenario_exact_passes": f"{pass_count}/{len(results)}",
        },
        change_policy={
            "source_version_change": "rerun Phase 8, Phase 10C, Phase 11 sample, and Phase 12 before publishing new package.",
            "approved_rule_package_change": "block publication until benchmark, unseen, and customer-evidence regression suites pass.",
            "parser_or_prompt_change": "rerun parser evaluation harness and require no degradation against the pinned gold labels.",
            "customer_mapping_profile_change": "rerun customer-evidence regression and field-mapping drift checks.",
        },
        rerun_required_before_publication=False,
        publication_gate="pass" if status == "stable" and rule_package.get("status") == "approved" else "blocked",
    )


def _approved_obligations(rule_package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        obligation["obligation_id"]: obligation
        for obligation in rule_package["records"]["obligations"]
        if obligation.get("metadata", {}).get("review_status") == "approved"
    }


def _obligation_ids_for_ctes(ctes: list[str], approved_obligations: dict[str, dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    if ctes:
        for obligation in approved_obligations.values():
            applies = obligation.get("applies_to_ctes") or []
            if "other" in applies:
                ids.append(obligation["obligation_id"])
    for cte in ctes:
        for obligation in approved_obligations.values():
            applies = obligation.get("applies_to_ctes") or []
            if cte in applies and "other" not in applies:
                ids.append(obligation["obligation_id"])
    return sorted(set(ids))


def _action_terms(family: str, event_type: str, document_type: str | None, destination: str | None) -> list[str]:
    terms = [event_type, document_type or "", destination or "", family]
    if family == "kill_step_uncertainty":
        terms.extend(["kill step", "scope uncertainty", "exemption review"])
    if family == "exemption_claim_shipping":
        terms.extend(["partial exemption", "exemption claim"])
    if family == "food_scope_review_shipping":
        terms.extend(["food scope review"])
    return [term for term in terms if term]


def _with_food_scope_review(event: CustomerEventNode, reason: str) -> CustomerEventNode:
    food_form = event.food_form.model_copy(
        update={
            "review_required": True,
            "confidence": 0.52,
            "reasons": [*event.food_form.reasons, f"phase12 {reason}"],
        }
    )
    return event.model_copy(update={"food_form": food_form})


def _with_actor_role_review(event: CustomerEventNode) -> CustomerEventNode:
    actor_role = event.actor_role.model_copy(update={"confidence": 0.4})
    return event.model_copy(update={"actor_role": actor_role})


def _citation_correct(obligation_ids: list[str], approved_obligations: dict[str, dict[str, Any]]) -> bool:
    for obligation_id in obligation_ids:
        obligation = approved_obligations.get(obligation_id)
        if not obligation:
            return False
        citation = (obligation.get("citations") or [{}])[0]
        if not (citation.get("chunk_id") or citation.get("source_id")):
            return False
    return True


def _food_scope_review_correct(scenario: Phase12Scenario, result: MultiSignalCteResult) -> bool:
    has_food_scope_question = any("food/form scope" in question or "exemption" in question or "kill-step" in question for question in result.reviewer_questions)
    return scenario.gold_label.expected_food_scope_review == has_food_scope_question


def _actor_role_review_correct(scenario: Phase12Scenario, result: MultiSignalCteResult) -> bool:
    has_actor_question = any("actor role" in question for question in result.reviewer_questions)
    return scenario.gold_label.expected_actor_role_review == has_actor_question


def _result_errors(
    scenario: Phase12Scenario,
    result: MultiSignalCteResult,
    actual_obligations: list[str],
    citation_correct: bool,
    food_scope_review_correct: bool,
    actor_role_review_correct: bool,
) -> list[str]:
    errors: list[str] = []
    if set(result.final_ctes) - set(scenario.gold_label.expected_ctes):
        errors.append("over_triggered_cte")
    if set(scenario.gold_label.expected_ctes) - set(result.final_ctes):
        errors.append("missed_cte")
    if set(result.suppressed_ctes) != set(scenario.gold_label.expected_suppressed_ctes):
        errors.append("suppression_mismatch")
    if set(result.abstained_ctes) != set(scenario.gold_label.expected_abstentions):
        errors.append("abstention_mismatch")
    if set(actual_obligations) - set(scenario.gold_label.expected_obligation_ids):
        errors.append("obligation_false_positive")
    if set(scenario.gold_label.expected_obligation_ids) - set(actual_obligations):
        errors.append("obligation_false_negative")
    if not citation_correct:
        errors.append("citation_failure")
    if not food_scope_review_correct:
        errors.append("wrong_food_scope_decision")
    if not actor_role_review_correct:
        errors.append("wrong_actor_role_decision")
    return errors


def _evaluate_parser_run(
    *,
    parser_id: str,
    parser_version: str,
    parser_type: str,
    scenarios: list[Phase12Scenario],
    predict: Any,
) -> ParserEvaluationRun:
    results: list[ParserScenarioResult] = []
    tp = fp = fn = 0
    abstentions = 0
    for scenario in scenarios:
        predicted_ctes, parser_abstentions = predict(scenario)
        results.append(
            ParserScenarioResult(
                scenario_id=scenario.scenario_id,
                expected_ctes=scenario.gold_label.expected_ctes,
                parser_ctes=predicted_ctes,
                parser_abstentions=parser_abstentions,
                exact_cte_match=set(predicted_ctes) == set(scenario.gold_label.expected_ctes),
            )
        )
        tp += len(set(predicted_ctes) & set(scenario.gold_label.expected_ctes))
        fp += len(set(predicted_ctes) - set(scenario.gold_label.expected_ctes))
        fn += len(set(scenario.gold_label.expected_ctes) - set(predicted_ctes))
        if parser_abstentions:
            abstentions += 1
    return ParserEvaluationRun(
        parser_id=parser_id,
        parser_version=parser_version,
        parser_type=parser_type,
        deterministic_rule_execution_unchanged=True,
        scenario_count=len(scenarios),
        exact_cte_match_rate=_ratio(sum(1 for result in results if result.exact_cte_match), len(results)),
        precision=_ratio(tp, tp + fp, empty=1.0),
        recall=_ratio(tp, tp + fn, empty=1.0),
        abstention_rate=_ratio(abstentions, len(scenarios)),
        results=results,
    )


def _deterministic_parser_prediction(scenario: Phase12Scenario) -> tuple[list[str], list[str]]:
    result = classify_event_with_multisignal(event=scenario.event, document_type=scenario.document_type, conflict_fields=scenario.conflict_fields)
    return result.final_ctes, result.abstained_ctes


def _keyword_parser_prediction(scenario: Phase12Scenario) -> tuple[list[str], list[str]]:
    text = _fixture_text(scenario)
    ctes: list[str] = []
    mapping = [
        ("traceability_plan", ["traceability_plan", "traceability plan"]),
        ("first_land_based_receiving", ["seafood_landing", "first land", "landing"]),
        ("harvesting", ["harvest"]),
        ("cooling", ["cooling"]),
        ("initial_packing", ["packing", "initial"]),
        ("transformation", ["transformation", "batch"]),
        ("shipping", ["ship", "bol", "bill_of_lading", "distributor"]),
        ("receiving", ["receiv", "restaurant"]),
    ]
    for cte, terms in mapping:
        if any(term in text for term in terms):
            ctes.append(cte)
    return sorted(set(ctes)), []


def _conservative_parser_prediction(scenario: Phase12Scenario) -> tuple[list[str], list[str]]:
    if scenario.gold_label.expected_ctes:
        return [], scenario.gold_label.expected_ctes
    return [], []


def _fixture_text(scenario: Phase12Scenario) -> str:
    return json.dumps(scenario.workbook_fixture, sort_keys=True).lower()


def _set_correctness(results: list[Phase12ScenarioResult], expected_attr: str, actual_attr: str) -> float:
    count = sum(1 for result in results if set(getattr(result, expected_attr)) == set(getattr(result, actual_attr)))
    return _ratio(count, len(results))


def _ratio(numerator: int, denominator: int, *, empty: float = 0.0) -> float:
    if denominator == 0:
        return empty
    return round(numerator / denominator, 4)


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _summary(
    *,
    rule_package: dict[str, Any],
    scenarios: list[Phase12Scenario],
    results: list[Phase12ScenarioResult],
    metrics: GeneralizationMetrics,
    error_report: InferenceErrorReport,
    parser_harness: ParserEvaluationHarness,
    drift_report: DriftChangeMonitorReport,
) -> dict[str, Any]:
    families = Counter(scenario.scenario_family for scenario in scenarios)
    food_categories = Counter(scenario.food_category for scenario in scenarios)
    return {
        "phase": 12,
        "generatedAt": GENERATED_AT,
        "rulePackageId": rule_package["package_id"],
        "rulePackageVersion": rule_package["version"],
        "scenarioCount": len(scenarios),
        "scenarioFamilies": dict(sorted(families.items())),
        "foodCategories": dict(sorted(food_categories.items())),
        "goldLabels": len(scenarios),
        "exactScenarioPassRate": metrics.exact_scenario_pass_rate,
        "exactScenarioPassCount": metrics.exact_scenario_pass_count,
        "cteFalsePositiveRate": metrics.false_positive_rate,
        "cteFalseNegativeRate": metrics.false_negative_rate,
        "obligationPrecision": metrics.obligation_precision,
        "obligationRecall": metrics.obligation_recall,
        "abstentionCorrectness": metrics.abstention_correctness,
        "citationCorrectness": metrics.citation_correctness,
        "errorSummaryCounts": error_report.summary_counts,
        "parserEvaluationRuns": len(parser_harness.evaluation_runs),
        "liveModelOutputsEvaluated": parser_harness.live_model_outputs_evaluated,
        "parserEvaluationScope": "deterministic classifier plus non-AI baselines; live model/prompt parser run not yet executed",
        "driftMonitorStatus": drift_report.status,
        "publicationGate": drift_report.publication_gate,
        "acceptanceCoverage": {
            "RI-110_generalization_metrics": True,
            "RI-111_unseen_scenario_challenge_set_100": len(scenarios) >= 100,
            "RI-112_gold_label_expected_outputs": all(scenario.gold_label.expected_product_name for scenario in scenarios),
            "RI-113_inference_error_report": True,
            "RI-114_model_prompt_evaluation_harness": True,
            "RI-115_drift_change_monitoring": True,
        },
        "resultStatusCounts": dict(sorted(Counter(result.status for result in results).items())),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
