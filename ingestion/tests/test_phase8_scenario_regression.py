from __future__ import annotations

import unittest
from pathlib import Path

from traceready_backend.intelligence.citations import build_citation_coverage_report, load_chunk_index
from traceready_backend.intelligence.phase08_scenario_regression import (
    FDA_REQUEST_OBLIGATION_ID,
    SORTABLE_EXPORT_OBLIGATION_ID,
    TLC_ASSIGNMENT_OBLIGATION_ID,
    TRACEABILITY_PLAN_OBLIGATION_ID,
    build_phase8_scenario_regressions,
    run_phase8_regression,
)


ROOT = Path(__file__).resolve().parents[2]


class Phase8ScenarioRegressionTest(unittest.TestCase):
    def _package(self):
        return build_phase8_scenario_regressions(
            scenario_benchmarks_file=ROOT / "data/regulatory/intelligence/drafts/scenario-benchmarks.json",
            approved_obligation_set_file=ROOT / "data/regulatory/intelligence/obligations/phase7-approved-obligation-set-v1.json",
            chunks_file=ROOT / "data/regulatory/registry/source-chunks.json",
            kde_candidates_file=ROOT / "data/regulatory/intelligence/drafts/cte-kde-candidates.json",
        )

    def test_builds_all_phase8_benchmarks_and_passes_gate(self) -> None:
        package = self._package()

        self.assertEqual(package.summary["fdaScenarioBenchmarks"], 6)
        self.assertEqual(package.summary["traceabilityPlanBenchmarks"], 7)
        self.assertEqual(package.summary["totalBenchmarks"], 13)
        self.assertTrue(package.summary["canPublishRuleChanges"])
        self.assertEqual(package.summary["publishGateStatus"], "passed")
        self.assertEqual(package.summary["citationCoverage"]["invalid"], 0)
        self.assertEqual(package.summary["regressionStatusCounts"], {"pass": 13})

    def test_fda_scenario_benchmarks_include_required_domain_expectations(self) -> None:
        package = self._package()
        by_id = {benchmark.benchmark_id: benchmark for benchmark in package.scenario_benchmarks}

        cucumber = by_id["phase8:fda_scenario:cucumber"]
        self.assertIn("harvesting", cucumber.expected_ctes)
        self.assertIn("initial_packing", cucumber.expected_ctes)
        self.assertGreater(len(cucumber.actors), 0)
        self.assertGreater(len(cucumber.events[0].expected_kde_field_keys), 0)
        self.assertIn(TLC_ASSIGNMENT_OBLIGATION_ID, cucumber.expected_tlc_obligation_ids)

        tuna = by_id["phase8:fda_scenario:tuna"]
        self.assertIn("first_land_based_receiving", tuna.expected_ctes)
        self.assertIn("FSMA204-OBL-DET-1335-FIRST-LAND-BASED-RECEIVING-KDES", tuna.expected_kde_obligation_ids)
        self.assertIn("first land-based receiving", tuna.expected_food_scope_behavior)

        cheese = by_id["phase8:fda_scenario:cheese"]
        self.assertIn("transformation", cheese.expected_ctes)
        self.assertIn("Soft cheese", cheese.food_scope)

        deli = by_id["phase8:fda_scenario:deli_salad_ftl_ingredients"]
        self.assertIn("transformation", deli.expected_ctes)
        self.assertIn("Ready-to-eat deli salad", deli.food_scope)

        canned_tuna = by_id["phase8:fda_scenario:deli_salad_canned_tuna"]
        self.assertIn("non-FTL input", canned_tuna.expected_food_scope_behavior)
        self.assertIn("transformation", canned_tuna.expected_ctes)

        sprouts = by_id["phase8:fda_scenario:sprouts"]
        self.assertIn("initial_packing", sprouts.expected_ctes)
        self.assertIn("seed", sprouts.expected_food_scope_behavior.lower())

    def test_traceability_plan_benchmarks_cover_all_fda_example_types(self) -> None:
        package = self._package()
        expected_ids = {
            "phase8:traceability_plan:farm",
            "phase8:traceability_plan:restaurant",
            "phase8:traceability_plan:sprouter",
            "phase8:traceability_plan:food_processor",
            "phase8:traceability_plan:distribution_center",
            "phase8:traceability_plan:seafood_processing",
            "phase8:traceability_plan:aquaculture",
        }
        actual_ids = {benchmark.benchmark_id for benchmark in package.traceability_plan_benchmarks}

        self.assertEqual(actual_ids, expected_ids)
        for benchmark in package.traceability_plan_benchmarks:
            self.assertIn(TRACEABILITY_PLAN_OBLIGATION_ID, benchmark.expected_traceability_plan_obligation_ids)
            self.assertIn(FDA_REQUEST_OBLIGATION_ID, benchmark.expected_records_obligation_ids)
            self.assertIn(SORTABLE_EXPORT_OBLIGATION_ID, benchmark.expected_sortable_export_obligation_ids)
            self.assertGreater(len(benchmark.citations), 0)

    def test_regression_runner_blocks_publish_when_expected_obligation_is_not_approved(self) -> None:
        package = self._package()
        full_approved_set = {
            "records": [
                {"obligation_id": obligation_id}
                for benchmark in package.scenario_benchmarks + package.traceability_plan_benchmarks
                for obligation_id in benchmark.expected_obligation_ids
                if obligation_id != "FSMA204-OBL-DET-1335-FIRST-LAND-BASED-RECEIVING-KDES"
            ]
        }
        chunk_index = load_chunk_index(ROOT / "data/regulatory/registry/source-chunks.json")
        citation_report = build_citation_coverage_report(
            {
                "scenario_regression_benchmarks": [
                    benchmark.model_dump(mode="json")
                    for benchmark in package.scenario_benchmarks + package.traceability_plan_benchmarks
                ]
            },
            chunk_index,
        ).model_dump(mode="json")

        results = run_phase8_regression(
            benchmarks=package.scenario_benchmarks + package.traceability_plan_benchmarks,
            approved_obligation_set=full_approved_set,
            citation_coverage_report=citation_report,
        )

        tuna_result = next(result for result in results if result.benchmark_id == "phase8:fda_scenario:tuna")
        self.assertEqual(tuna_result.status, "fail")
        self.assertTrue(
            any(
                "FSMA204-OBL-DET-1335-FIRST-LAND-BASED-RECEIVING-KDES" in check.message
                for check in tuna_result.checks
            )
        )


if __name__ == "__main__":
    unittest.main()
