from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from traceready_backend.intelligence.phase12_generalization_evaluation import (
    build_generalization_metrics,
    build_inference_error_report,
    build_phase12_generalization_evaluation,
    build_phase12_unseen_scenarios,
    evaluate_phase12_scenario,
    write_phase12_generalization_artifacts,
)


ROOT = Path(__file__).resolve().parents[2]
RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"


class Phase12GeneralizationEvaluationTest(unittest.TestCase):
    def test_unseen_scenario_set_has_100_gold_labeled_customer_like_cases(self) -> None:
        package = build_phase12_generalization_evaluation(approved_rule_package_file=RULE_PACKAGE)

        self.assertEqual(package.summary["scenarioCount"], 100)
        self.assertEqual(len(package.scenarios), 100)
        self.assertEqual(len(package.gold_labels), 100)
        self.assertGreaterEqual(len(package.summary["scenarioFamilies"]), 20)
        self.assertTrue(all(scenario.gold_label.expected_product_name for scenario in package.scenarios))
        self.assertTrue(all("expected_ctes" in label.model_dump(mode="json") for label in package.gold_labels))

    def test_generalization_metrics_track_ctes_obligations_abstention_and_citations(self) -> None:
        package = build_phase12_generalization_evaluation(approved_rule_package_file=RULE_PACKAGE)
        metrics = package.metrics

        self.assertEqual(metrics.scenario_count, 100)
        self.assertEqual(metrics.exact_scenario_pass_rate, 1.0)
        self.assertIn("shipping", metrics.cte_precision_by_cte)
        self.assertIn("receiving", metrics.cte_recall_by_cte)
        self.assertEqual(metrics.obligation_precision, 1.0)
        self.assertEqual(metrics.obligation_recall, 1.0)
        self.assertEqual(metrics.abstention_correctness, 1.0)
        self.assertEqual(metrics.citation_correctness, 1.0)

    def test_inference_error_report_has_required_error_categories(self) -> None:
        package = build_phase12_generalization_evaluation(approved_rule_package_file=RULE_PACKAGE)
        report = package.inference_error_report

        self.assertEqual(report.scenario_count, 100)
        self.assertIn("over_triggered_ctes", report.summary_counts)
        self.assertIn("missed_ctes", report.summary_counts)
        self.assertIn("wrong_food_scope_decisions", report.summary_counts)
        self.assertIn("wrong_actor_role_decisions", report.summary_counts)
        self.assertIn("missing_abstentions", report.summary_counts)
        self.assertEqual(report.summary_counts["citation_failures"], 0)

    def test_parser_evaluation_harness_compares_candidate_parsers_without_rule_changes(self) -> None:
        package = build_phase12_generalization_evaluation(approved_rule_package_file=RULE_PACKAGE)
        harness = package.parser_evaluation_harness

        self.assertEqual(len(harness.evaluation_runs), 3)
        self.assertTrue(all(run.deterministic_rule_execution_unchanged for run in harness.evaluation_runs))
        by_parser = {run.parser_id: run for run in harness.evaluation_runs}
        self.assertEqual(by_parser["deterministic_multisignal_parser"].exact_cte_match_rate, 1.0)
        self.assertLess(by_parser["conservative_abstention_parser"].recall, 1.0)

    def test_drift_monitor_blocks_future_changes_until_suites_rerun(self) -> None:
        package = build_phase12_generalization_evaluation(
            approved_rule_package_file=RULE_PACKAGE,
            phase8_summary_file=ROOT / "data/regulatory/intelligence/scenarios/phase8-summary.json",
            phase10c_summary_file=ROOT / "data/regulatory/intelligence/customer-evidence/phase10c-summary.json",
            phase11_summary_file=ROOT / "data/regulatory/intelligence/customer-evidence/phase11-summary.json",
        )
        drift = package.drift_change_monitor_report

        self.assertEqual(drift.status, "stable")
        self.assertEqual(drift.publication_gate, "pass")
        self.assertIn("approved_rule_package_change", drift.change_policy)
        self.assertTrue(any(item["input"] == "approved_rule_package" for item in drift.monitored_inputs))
        self.assertTrue(any("phase12_generalization" in item["rerun_suites_on_change"] for item in drift.monitored_inputs if "rerun_suites_on_change" in item))

    def test_phase12_artifact_writer_outputs_all_required_files(self) -> None:
        package = build_phase12_generalization_evaluation(approved_rule_package_file=RULE_PACKAGE)
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs = write_phase12_generalization_artifacts(package, Path(tmpdir))

            self.assertTrue(Path(outputs["summary"]).exists())
            self.assertTrue(Path(outputs["metrics"]).exists())
            self.assertTrue(Path(outputs["challengeSet"]).exists())
            self.assertTrue(Path(outputs["goldLabels"]).exists())
            self.assertTrue(Path(outputs["inferenceErrorReport"]).exists())
            self.assertTrue(Path(outputs["parserEvaluationHarness"]).exists())
            self.assertTrue(Path(outputs["driftChangeMonitor"]).exists())


if __name__ == "__main__":
    unittest.main()
