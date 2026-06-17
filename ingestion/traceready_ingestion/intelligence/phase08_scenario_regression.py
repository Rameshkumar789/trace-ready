from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from traceready_ingestion.intelligence.citations import build_citation_coverage_report, load_chunk_index
from traceready_ingestion.intelligence.schemas import CitationRef, CteType


PHASE8_GENERATED_AT = "2026-06-16T00:00:00Z"

SCOPE_OBLIGATION_ID = "FSMA204-OBL-DET-1300-SCOPE"
TRACEABILITY_PLAN_OBLIGATION_ID = "FSMA204-OBL-DET-1315-TRACEABILITY-PLAN"
TLC_ASSIGNMENT_OBLIGATION_ID = "FSMA204-OBL-DET-1320-TLC-ASSIGNMENT"
RECORDS_MAINTENANCE_OBLIGATION_ID = "FSMA204-OBL-DET-1455-RECORDS-MAINTENANCE"
FDA_REQUEST_OBLIGATION_ID = "FSMA204-OBL-DET-1455-FDA-REQUEST"
SORTABLE_EXPORT_OBLIGATION_ID = "FSMA204-OBL-DET-1455-SORTABLE-SPREADSHEET"

KDE_OBLIGATION_BY_CTE = {
    CteType.HARVESTING.value: "FSMA204-OBL-DET-1325-HARVEST-COOLING-KDES",
    CteType.COOLING.value: "FSMA204-OBL-DET-1325-HARVEST-COOLING-KDES",
    CteType.INITIAL_PACKING.value: "FSMA204-OBL-DET-1330-INITIAL-PACKING-KDES",
    CteType.FIRST_LAND_BASED_RECEIVING.value: "FSMA204-OBL-DET-1335-FIRST-LAND-BASED-RECEIVING-KDES",
    CteType.SHIPPING.value: "FSMA204-OBL-DET-1340-SHIPPING-KDES",
    CteType.RECEIVING.value: "FSMA204-OBL-DET-1345-RECEIVING-KDES",
    CteType.TRANSFORMATION.value: "FSMA204-OBL-DET-1350-TRANSFORMATION-KDES",
}

TLC_ASSIGNMENT_CTES = {
    CteType.INITIAL_PACKING.value,
    CteType.FIRST_LAND_BASED_RECEIVING.value,
    CteType.TRANSFORMATION.value,
}

TRACEABILITY_PLAN_SOURCES = {
    "traceability-plan-farms": {
        "benchmark_id": "phase8:traceability_plan:farm",
        "scenario_name": "FDA traceability plan example for farms",
        "food_scope": "Farms handling Food Traceability List foods, including farm map expectations where applicable",
        "actor_name": "Farm operator",
        "expected_ctes": ["traceability_plan", "harvesting", "cooling", "initial_packing"],
        "notes": ["Farm examples must include map/location evidence where required by 21 CFR 1.1315."],
    },
    "traceability-plan-restaurants": {
        "benchmark_id": "phase8:traceability_plan:restaurant",
        "scenario_name": "FDA traceability plan example for restaurants",
        "food_scope": "Restaurant handling Food Traceability List foods",
        "actor_name": "Restaurant operator",
        "expected_ctes": ["traceability_plan", "receiving"],
        "notes": ["Restaurant examples emphasize record maintenance procedures for incoming FTL foods."],
    },
    "traceability-plan-sprouters": {
        "benchmark_id": "phase8:traceability_plan:sprouter",
        "scenario_name": "FDA traceability plan example for sprouters",
        "food_scope": "Sprouter handling fresh sprouts on the Food Traceability List",
        "actor_name": "Sprouter",
        "expected_ctes": ["traceability_plan", "initial_packing", "shipping"],
        "notes": ["Sprouter examples must preserve seed source and sprout initial-packing expectations."],
    },
    "traceability-plan-food-processors": {
        "benchmark_id": "phase8:traceability_plan:food_processor",
        "scenario_name": "FDA traceability plan example for food processors",
        "food_scope": "Food processor handling Food Traceability List ingredients or finished foods",
        "actor_name": "Food processor",
        "expected_ctes": ["traceability_plan", "receiving", "transformation", "shipping"],
        "notes": ["Processor examples must cover transformation and outbound traceability records."],
    },
    "traceability-plan-distribution-centers": {
        "benchmark_id": "phase8:traceability_plan:distribution_center",
        "scenario_name": "FDA traceability plan example for distribution centers",
        "food_scope": "Distribution center receiving and shipping Food Traceability List foods",
        "actor_name": "Distribution center",
        "expected_ctes": ["traceability_plan", "receiving", "shipping"],
        "notes": ["Distribution center examples must cover inbound and outbound record procedures."],
    },
    "traceability-plan-seafood-processing": {
        "benchmark_id": "phase8:traceability_plan:seafood_processing",
        "scenario_name": "FDA traceability plan example for seafood processing facilities",
        "food_scope": "Seafood processor handling finfish or other Food Traceability List seafood",
        "actor_name": "Seafood processor",
        "expected_ctes": ["traceability_plan", "receiving", "transformation", "shipping"],
        "notes": ["Seafood processing examples must preserve fresh seafood source and transformation expectations."],
    },
    "traceability-plan-aquaculture": {
        "benchmark_id": "phase8:traceability_plan:aquaculture",
        "scenario_name": "FDA traceability plan example for aquaculture farms",
        "food_scope": "Aquaculture farm handling Food Traceability List seafood",
        "actor_name": "Aquaculture farm",
        "expected_ctes": ["traceability_plan", "harvesting", "initial_packing"],
        "notes": ["Aquaculture examples must cover container or harvest-location traceability evidence."],
    },
}


class ScenarioRegressionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    cte_type: str
    actor_id: str
    event_description: str
    expected_obligation_ids: list[str] = Field(default_factory=list)
    expected_kde_field_keys: list[str] = Field(default_factory=list)
    expected_tlc_behavior: str | None = None


class ScenarioRegressionBenchmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str
    benchmark_type: str
    scenario_name: str
    scenario_source_id: str
    source_scenario_id: str | None = None
    food_scope: str
    citations: list[CitationRef]
    actors: list[dict[str, Any]]
    events: list[ScenarioRegressionEvent]
    expected_ctes: list[str]
    expected_obligation_ids: list[str]
    expected_kde_obligation_ids: list[str]
    expected_tlc_obligation_ids: list[str]
    expected_traceability_plan_obligation_ids: list[str]
    expected_records_obligation_ids: list[str]
    expected_sortable_export_obligation_ids: list[str]
    expected_food_scope_behavior: str
    reviewer_notes: list[str] = Field(default_factory=list)
    regression_status: str


class RegressionCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str
    status: str
    message: str


class ScenarioRegressionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str
    status: str
    checks: list[RegressionCheckResult]


class Phase8ScenarioRegressionPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: dict[str, Any]
    scenario_benchmarks: list[ScenarioRegressionBenchmark]
    traceability_plan_benchmarks: list[ScenarioRegressionBenchmark]
    regression_results: list[ScenarioRegressionResult]
    citation_coverage_report: dict[str, Any]


def build_phase8_scenario_regressions(
    *,
    scenario_benchmarks_file: Path,
    approved_obligation_set_file: Path,
    chunks_file: Path,
    kde_candidates_file: Path,
    override_reason: str | None = None,
) -> Phase8ScenarioRegressionPackage:
    scenario_drafts = json.loads(scenario_benchmarks_file.read_text(encoding="utf-8"))
    approved_set = json.loads(approved_obligation_set_file.read_text(encoding="utf-8"))
    chunk_index = load_chunk_index(chunks_file)
    kde_candidates = json.loads(kde_candidates_file.read_text(encoding="utf-8"))
    kde_fields_by_cte = _kde_fields_by_cte(kde_candidates)

    scenario_benchmarks = [
        _scenario_benchmark_from_draft(draft, kde_fields_by_cte)
        for draft in scenario_drafts
    ]
    traceability_plan_benchmarks = _traceability_plan_benchmarks(chunk_index, kde_fields_by_cte)
    all_benchmarks = scenario_benchmarks + traceability_plan_benchmarks

    citation_report = build_citation_coverage_report(
        {
            "scenario_regression_benchmarks": [
                benchmark.model_dump(mode="json") for benchmark in all_benchmarks
            ]
        },
        chunk_index,
    ).model_dump(mode="json")
    regression_results = run_phase8_regression(
        benchmarks=all_benchmarks,
        approved_obligation_set=approved_set,
        citation_coverage_report=citation_report,
        override_reason=override_reason,
    )
    summary = _summary(
        scenario_benchmarks=scenario_benchmarks,
        traceability_plan_benchmarks=traceability_plan_benchmarks,
        regression_results=regression_results,
        citation_coverage_report=citation_report,
        approved_set=approved_set,
        override_reason=override_reason,
    )
    return Phase8ScenarioRegressionPackage(
        summary=summary,
        scenario_benchmarks=scenario_benchmarks,
        traceability_plan_benchmarks=traceability_plan_benchmarks,
        regression_results=regression_results,
        citation_coverage_report=citation_report,
    )


def run_phase8_regression(
    *,
    benchmarks: list[ScenarioRegressionBenchmark],
    approved_obligation_set: dict[str, Any],
    citation_coverage_report: dict[str, Any],
    override_reason: str | None = None,
) -> list[ScenarioRegressionResult]:
    approved_ids = {str(record["obligation_id"]) for record in approved_obligation_set.get("records", [])}
    citation_status_by_record = {
        str(record["record_id"]): str(record["coverage_status"])
        for record in citation_coverage_report.get("records", [])
    }
    results: list[ScenarioRegressionResult] = []
    for benchmark in benchmarks:
        checks = [
            _check_citations_complete(benchmark, citation_status_by_record),
            _check_expected_obligations_approved(benchmark, approved_ids),
            _check_event_contract(benchmark, approved_ids),
            _check_traceability_plan_contract(benchmark),
        ]
        failed = [check for check in checks if check.status == "fail"]
        if not failed:
            status = "pass"
        elif override_reason and override_reason.strip():
            status = "reviewer_override"
        else:
            status = "fail"
        results.append(ScenarioRegressionResult(benchmark_id=benchmark.benchmark_id, status=status, checks=checks))
    return results


def write_phase8_scenario_artifacts(package: Phase8ScenarioRegressionPackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase8-summary.json",
        "scenarioBenchmarks": output_dir / "phase8-scenario-benchmarks.json",
        "traceabilityPlanBenchmarks": output_dir / "phase8-traceability-plan-benchmarks.json",
        "regressionResults": output_dir / "phase8-regression-results.json",
        "citationCoverageReport": output_dir / "phase8-citation-coverage-report.json",
    }
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["scenarioBenchmarks"], [record.model_dump(mode="json") for record in package.scenario_benchmarks])
    _write_json(
        outputs["traceabilityPlanBenchmarks"],
        [record.model_dump(mode="json") for record in package.traceability_plan_benchmarks],
    )
    _write_json(outputs["regressionResults"], [record.model_dump(mode="json") for record in package.regression_results])
    _write_json(outputs["citationCoverageReport"], package.citation_coverage_report)
    return {key: str(path) for key, path in outputs.items()}


def _scenario_benchmark_from_draft(
    draft: dict[str, Any],
    kde_fields_by_cte: dict[str, list[str]],
) -> ScenarioRegressionBenchmark:
    scenario_key = _scenario_key(draft)
    events = [_scenario_event(event, kde_fields_by_cte) for event in draft["events"]]
    expected_ctes = _ordered_unique(event.cte_type for event in events)
    expected_kde_obligations = _expected_kde_obligations(expected_ctes)
    expected_tlc_obligations = _expected_tlc_obligations(expected_ctes)
    expected_records = [RECORDS_MAINTENANCE_OBLIGATION_ID, FDA_REQUEST_OBLIGATION_ID]
    expected_sortable = [SORTABLE_EXPORT_OBLIGATION_ID]
    expected_plan = [TRACEABILITY_PLAN_OBLIGATION_ID]
    expected_obligations = _ordered_unique(
        [
            SCOPE_OBLIGATION_ID,
            *expected_plan,
            *expected_kde_obligations,
            *expected_tlc_obligations,
            *expected_records,
            *expected_sortable,
        ]
    )
    return ScenarioRegressionBenchmark(
        benchmark_id=f"phase8:fda_scenario:{scenario_key}",
        benchmark_type="fda_supply_chain_scenario",
        scenario_name=str(draft["scenario_name"]),
        scenario_source_id=str(draft["scenario_source"]),
        source_scenario_id=str(draft["scenario_benchmark_id"]),
        food_scope=str(draft["food_scope"]),
        citations=[CitationRef.model_validate(citation) for citation in draft["citations"]],
        actors=list(draft["actors"]),
        events=events,
        expected_ctes=expected_ctes,
        expected_obligation_ids=expected_obligations,
        expected_kde_obligation_ids=expected_kde_obligations,
        expected_tlc_obligation_ids=expected_tlc_obligations,
        expected_traceability_plan_obligation_ids=expected_plan,
        expected_records_obligation_ids=expected_records,
        expected_sortable_export_obligation_ids=expected_sortable,
        expected_food_scope_behavior=_food_scope_behavior(scenario_key),
        reviewer_notes=_scenario_reviewer_notes(draft, scenario_key),
        regression_status="regression_ready",
    )


def _traceability_plan_benchmarks(
    chunk_index: dict[str, dict[str, Any]],
    kde_fields_by_cte: dict[str, list[str]],
) -> list[ScenarioRegressionBenchmark]:
    benchmarks: list[ScenarioRegressionBenchmark] = []
    chunks_by_source: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunk_index.values():
        chunks_by_source.setdefault(str(chunk["source_id"]), []).append(chunk)

    for source_id, spec in TRACEABILITY_PLAN_SOURCES.items():
        chunks = sorted(chunks_by_source[source_id], key=lambda item: str(item["chunk_id"]))
        citations = [_citation_from_chunk(chunk) for chunk in chunks]
        expected_ctes = list(spec["expected_ctes"])
        expected_kde_obligations = _expected_kde_obligations(expected_ctes)
        expected_tlc_obligations = _expected_tlc_obligations(expected_ctes)
        expected_records = [RECORDS_MAINTENANCE_OBLIGATION_ID, FDA_REQUEST_OBLIGATION_ID]
        expected_sortable = [SORTABLE_EXPORT_OBLIGATION_ID]
        expected_plan = [TRACEABILITY_PLAN_OBLIGATION_ID]
        expected_obligations = _ordered_unique(
            [
                SCOPE_OBLIGATION_ID,
                *expected_plan,
                *expected_kde_obligations,
                *expected_tlc_obligations,
                *expected_records,
                *expected_sortable,
            ]
        )
        plan_event = ScenarioRegressionEvent(
            event_id="event_traceability_plan",
            cte_type=CteType.TRACEABILITY_PLAN.value,
            actor_id="covered_entity",
            event_description="Covered entity establishes and maintains a traceability plan for the FDA example business type.",
            expected_obligation_ids=[TRACEABILITY_PLAN_OBLIGATION_ID],
            expected_kde_field_keys=[],
            expected_tlc_behavior="Traceability plan must describe TLC assignment procedures when the business performs TLC-triggering CTEs.",
        )
        cte_events = [
            ScenarioRegressionEvent(
                event_id=f"event_{cte}",
                cte_type=cte,
                actor_id="covered_entity",
                event_description=f"Traceability plan example must support operational records for {cte.replace('_', ' ')}.",
                expected_obligation_ids=_event_obligation_ids(cte),
                expected_kde_field_keys=kde_fields_by_cte.get(cte, []),
                expected_tlc_behavior=_tlc_behavior(cte),
            )
            for cte in expected_ctes
            if cte != CteType.TRACEABILITY_PLAN.value
        ]
        benchmarks.append(
            ScenarioRegressionBenchmark(
                benchmark_id=str(spec["benchmark_id"]),
                benchmark_type="fda_traceability_plan_example",
                scenario_name=str(spec["scenario_name"]),
                scenario_source_id=source_id,
                source_scenario_id=None,
                food_scope=str(spec["food_scope"]),
                citations=citations,
                actors=[
                    {
                        "actor_id": "covered_entity",
                        "actor_name": str(spec["actor_name"]),
                        "role": "covered operator",
                        "location_description": None,
                    }
                ],
                events=[plan_event, *cte_events],
                expected_ctes=expected_ctes,
                expected_obligation_ids=expected_obligations,
                expected_kde_obligation_ids=expected_kde_obligations,
                expected_tlc_obligation_ids=expected_tlc_obligations,
                expected_traceability_plan_obligation_ids=expected_plan,
                expected_records_obligation_ids=expected_records,
                expected_sortable_export_obligation_ids=expected_sortable,
                expected_food_scope_behavior="Entity must maintain traceability plan evidence in addition to applicable CTE/KDE records.",
                reviewer_notes=list(spec["notes"]),
                regression_status="regression_ready",
            )
        )
    return benchmarks


def _scenario_event(event: dict[str, Any], kde_fields_by_cte: dict[str, list[str]]) -> ScenarioRegressionEvent:
    cte = str(event["cte_type"])
    return ScenarioRegressionEvent(
        event_id=str(event["event_id"]),
        cte_type=cte,
        actor_id=str(event["actor_id"]),
        event_description=str(event["event_description"]),
        expected_obligation_ids=_event_obligation_ids(cte),
        expected_kde_field_keys=kde_fields_by_cte.get(cte, []),
        expected_tlc_behavior=_tlc_behavior(cte),
    )


def _event_obligation_ids(cte: str) -> list[str]:
    obligations = []
    if cte in KDE_OBLIGATION_BY_CTE:
        obligations.append(KDE_OBLIGATION_BY_CTE[cte])
    if cte in TLC_ASSIGNMENT_CTES:
        obligations.append(TLC_ASSIGNMENT_OBLIGATION_ID)
    return obligations


def _expected_kde_obligations(ctes: list[str]) -> list[str]:
    return _ordered_unique(KDE_OBLIGATION_BY_CTE[cte] for cte in ctes if cte in KDE_OBLIGATION_BY_CTE)


def _expected_tlc_obligations(ctes: list[str]) -> list[str]:
    return [TLC_ASSIGNMENT_OBLIGATION_ID] if any(cte in TLC_ASSIGNMENT_CTES for cte in ctes) else []


def _tlc_behavior(cte: str) -> str:
    if cte == CteType.TRANSFORMATION.value:
        return "Transformation must assign a new traceability lot code for output food and preserve input lot lineage."
    if cte in {CteType.INITIAL_PACKING.value, CteType.FIRST_LAND_BASED_RECEIVING.value}:
        return "This CTE must assign the traceability lot code and link KDEs to the assigned lot."
    if cte in {CteType.SHIPPING.value, CteType.RECEIVING.value}:
        return "This CTE must preserve the traceability lot code and link pass-forward records to the lot."
    if cte in {CteType.HARVESTING.value, CteType.COOLING.value}:
        return "Harvesting or cooling KDEs must remain available for linkage to the initial packed traceability lot."
    return "TLC behavior follows the approved Subpart S obligation set for this CTE."


def _food_scope_behavior(scenario_key: str) -> str:
    behaviors = {
        "cucumber": "Fresh cucumbers are treated as FTL produce; harvesting, initial packing, shipping, and receiving duties must be executable.",
        "tuna": "Wild-caught tuna must include first land-based receiving before downstream shipping and receiving checks.",
        "cheese": "Soft cheese scope must trigger transformation, shipping, and receiving checks for FTL food.",
        "deli_salad_ftl_ingredients": "Ready-to-eat deli salad with FTL ingredients must preserve inbound FTL receiving and output transformation/shipping expectations.",
        "deli_salad_canned_tuna": "Canned tuna is treated as a non-FTL input in the FDA example, while finished deli salad still triggers transformation and shipping expectations.",
        "sprouts": "Fresh sprouts are FTL food; seed inputs are out of FTL scope but sprout initial-packing, shipping, and receiving checks remain required.",
    }
    return behaviors[scenario_key]


def _scenario_reviewer_notes(draft: dict[str, Any], scenario_key: str) -> list[str]:
    notes = list(draft.get("open_questions", []))
    if scenario_key == "tuna":
        notes.append("Regression contract requires first land-based receiving for seafood obtained from a fishing vessel.")
    if scenario_key == "deli_salad_canned_tuna":
        notes.append("Regression contract explicitly checks the FDA canned-tuna form-change behavior.")
    if scenario_key == "sprouts":
        notes.append("Regression contract checks that seed suppliers are not treated as covered FTL actors for the sprouts example.")
    return notes


def _scenario_key(draft: dict[str, Any]) -> str:
    value = f"{draft.get('scenario_benchmark_id', '')} {draft.get('scenario_name', '')}".lower()
    if "cucumber" in value:
        return "cucumber"
    if "wild-caught tuna" in value:
        return "tuna"
    if "cheese" in value:
        return "cheese"
    if "tuna salad" in value or "canned tuna" in value:
        return "deli_salad_canned_tuna"
    if "deli salad" in value:
        return "deli_salad_ftl_ingredients"
    if "sprout" in value:
        return "sprouts"
    return _slug(str(draft["scenario_name"]))


def _kde_fields_by_cte(kde_candidates: list[dict[str, Any]]) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for item in kde_candidates:
        cte = str(item["cte_type"])
        fields.setdefault(cte, []).append(str(item["field_key"]))
    return {cte: _ordered_unique(values) for cte, values in fields.items()}


def _citation_from_chunk(chunk: dict[str, Any]) -> CitationRef:
    return CitationRef(
        source_id=str(chunk["source_id"]),
        chunk_id=str(chunk["chunk_id"]),
        citation_anchor=str(chunk["citation_anchor"]),
        authority_rank=str(chunk["authority_rank"]),
        source_url=str(chunk["source_url"]),
        section_ref=chunk.get("section_ref"),
        page_number=chunk.get("page_number"),
        support_text=str(chunk["text"]),
    )


def _check_citations_complete(
    benchmark: ScenarioRegressionBenchmark,
    citation_status_by_record: dict[str, str],
) -> RegressionCheckResult:
    status = citation_status_by_record.get(benchmark.benchmark_id)
    if status == "complete":
        return RegressionCheckResult(
            check_id="citations_complete",
            status="pass",
            message="All benchmark citations resolve to canonical source chunks with support text.",
        )
    return RegressionCheckResult(
        check_id="citations_complete",
        status="fail",
        message=f"Benchmark citation coverage is {status or 'missing'}.",
    )


def _check_expected_obligations_approved(
    benchmark: ScenarioRegressionBenchmark,
    approved_ids: set[str],
) -> RegressionCheckResult:
    missing = sorted(set(benchmark.expected_obligation_ids) - approved_ids)
    if not missing:
        return RegressionCheckResult(
            check_id="expected_obligations_approved",
            status="pass",
            message="Every expected benchmark obligation exists in the approved Phase 7 obligation set.",
        )
    return RegressionCheckResult(
        check_id="expected_obligations_approved",
        status="fail",
        message=f"Expected obligations are not approved: {missing}",
    )


def _check_event_contract(
    benchmark: ScenarioRegressionBenchmark,
    approved_ids: set[str],
) -> RegressionCheckResult:
    failures = []
    for event in benchmark.events:
        if event.cte_type != CteType.TRACEABILITY_PLAN.value and not event.expected_obligation_ids:
            failures.append(f"{event.event_id} has no executable obligation")
        missing = sorted(set(event.expected_obligation_ids) - approved_ids)
        if missing:
            failures.append(f"{event.event_id} missing approved obligations {missing}")
        if event.cte_type in KDE_OBLIGATION_BY_CTE and not event.expected_kde_field_keys:
            failures.append(f"{event.event_id} has no KDE field expectations")
        if not event.expected_tlc_behavior:
            failures.append(f"{event.event_id} has no TLC behavior expectation")
    if not failures:
        return RegressionCheckResult(
            check_id="event_contract",
            status="pass",
            message="All benchmark events include CTE, KDE, TLC, and approved-obligation expectations.",
        )
    return RegressionCheckResult(check_id="event_contract", status="fail", message="; ".join(failures))


def _check_traceability_plan_contract(benchmark: ScenarioRegressionBenchmark) -> RegressionCheckResult:
    if TRACEABILITY_PLAN_OBLIGATION_ID not in benchmark.expected_traceability_plan_obligation_ids:
        return RegressionCheckResult(
            check_id="traceability_plan_contract",
            status="fail",
            message="Benchmark does not require the approved traceability plan obligation.",
        )
    if not benchmark.expected_records_obligation_ids or not benchmark.expected_sortable_export_obligation_ids:
        return RegressionCheckResult(
            check_id="traceability_plan_contract",
            status="fail",
            message="Benchmark does not include record-maintenance and sortable-export expectations.",
        )
    return RegressionCheckResult(
        check_id="traceability_plan_contract",
        status="pass",
        message="Benchmark includes traceability plan, records, FDA request, and sortable-export expectations.",
    )


def _summary(
    *,
    scenario_benchmarks: list[ScenarioRegressionBenchmark],
    traceability_plan_benchmarks: list[ScenarioRegressionBenchmark],
    regression_results: list[ScenarioRegressionResult],
    citation_coverage_report: dict[str, Any],
    approved_set: dict[str, Any],
    override_reason: str | None,
) -> dict[str, Any]:
    statuses = Counter(result.status for result in regression_results)
    failed = statuses["fail"]
    overridden = statuses["reviewer_override"]
    can_publish = failed == 0
    return {
        "generatedAt": PHASE8_GENERATED_AT,
        "sourceApprovedObligationPackage": approved_set.get("package_id"),
        "sourceApprovedObligationPackageVersion": approved_set.get("version"),
        "fdaScenarioBenchmarks": len(scenario_benchmarks),
        "traceabilityPlanBenchmarks": len(traceability_plan_benchmarks),
        "totalBenchmarks": len(scenario_benchmarks) + len(traceability_plan_benchmarks),
        "regressionStatusCounts": dict(sorted(statuses.items())),
        "canPublishRuleChanges": can_publish,
        "publishGateStatus": "passed" if can_publish else "blocked_without_reviewer_override",
        "reviewerOverrideReason": override_reason,
        "reviewerOverrides": overridden,
        "citationCoverage": citation_coverage_report.get("summary", {}),
        "fdaScenarioCoverage": sorted(_scenario_key_from_benchmark(benchmark) for benchmark in scenario_benchmarks),
        "traceabilityPlanCoverage": sorted(TRACEABILITY_PLAN_SOURCES.keys()),
        "cteCoverage": sorted({cte for benchmark in scenario_benchmarks + traceability_plan_benchmarks for cte in benchmark.expected_ctes}),
    }


def _scenario_key_from_benchmark(benchmark: ScenarioRegressionBenchmark) -> str:
    return benchmark.benchmark_id.rsplit(":", maxsplit=1)[-1]


def _ordered_unique(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value)
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _slug(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
