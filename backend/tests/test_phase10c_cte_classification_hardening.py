from __future__ import annotations

import unittest
from pathlib import Path

from bellwether_backend.audit_engine.cte_classification import (
    _benchmark_event,
    build_cte_precedence_matrix,
    build_phase10c_benchmark_cases,
    build_phase10c_cte_hardening,
    build_precision_recall_report,
    classify_event_with_multisignal,
    evaluate_benchmark_case,
)


ROOT = Path(__file__).resolve().parents[2]


class Phase10CCteClassificationHardeningTest(unittest.TestCase):
    def test_precedence_matrix_contains_core_suppression_rules(self) -> None:
        matrix = build_cte_precedence_matrix()
        rule_ids = {rule.rule_id for rule in matrix.rules}

        self.assertIn("precedence-first-land-over-generic-receiving", rule_ids)
        self.assertIn("suppress-direct-to-consumer-shipping", rule_ids)
        self.assertIn("abstain-transporter-only", rule_ids)
        self.assertIn("suppress-non-ftl-output", rule_ids)
        self.assertIn("traceability-plan-exclusive", rule_ids)

    def test_first_land_based_receiving_suppresses_generic_receiving(self) -> None:
        event = _benchmark_event(
            event_id="first-land",
            event_type="receiving",
            actor_role="first_land_based_receiver",
            product_name="Fresh Tuna",
            destination=None,
            output_remains_ftl=True,
            action_terms=["receiving", "seafood_landing_record"],
        )

        result = classify_event_with_multisignal(event=event, document_type="seafood_landing_record")

        self.assertEqual(result.final_ctes, ["first_land_based_receiving"])
        self.assertIn("receiving", result.suppressed_ctes)
        self.assertIn("precedence-first-land-over-generic-receiving", result.applied_precedence_rules)

    def test_direct_to_consumer_suppresses_shipping(self) -> None:
        event = _benchmark_event(
            event_id="dtc",
            event_type="shipping",
            actor_role="shipper",
            product_name="Fresh Basil",
            destination="direct to consumer",
            output_remains_ftl=True,
            action_terms=["shipping", "direct to consumer"],
        )

        result = classify_event_with_multisignal(event=event, document_type="shipping_log")

        self.assertEqual(result.final_ctes, [])
        self.assertIn("shipping", result.suppressed_ctes)
        self.assertIn("suppress-direct-to-consumer-shipping", result.applied_precedence_rules)

    def test_transporter_only_abstains_instead_of_confident_shipping(self) -> None:
        event = _benchmark_event(
            event_id="transporter",
            event_type="shipping",
            actor_role="transporter",
            product_name="Fresh Cucumber",
            destination=None,
            output_remains_ftl=True,
            action_terms=["shipping", "carrier"],
        )

        result = classify_event_with_multisignal(event=event, document_type="bill_of_lading")

        self.assertEqual(result.final_ctes, [])
        self.assertIn("shipping", result.suppressed_ctes)
        self.assertIn("shipping", result.abstained_ctes)
        self.assertTrue(result.reviewer_questions)

    def test_non_ftl_output_suppresses_transformation(self) -> None:
        event = _benchmark_event(
            event_id="non-ftl-output",
            event_type="transformation",
            actor_role="processor",
            product_name="Canned Tuna Salad",
            destination=None,
            output_remains_ftl=False,
            action_terms=["transformation", "canned", "shelf stable"],
            source_lot="RAW-1",
            output_lot="CAN-1",
        )

        result = classify_event_with_multisignal(event=event, document_type="transformation_batch_record")

        self.assertEqual(result.final_ctes, [])
        self.assertIn("transformation", result.suppressed_ctes)
        self.assertIn("suppress-non-ftl-output", result.applied_precedence_rules)

    def test_incorrect_barcode_text_does_not_create_correction_abstention(self) -> None:
        event = _benchmark_event(
            event_id="incorrect-barcode-product-note",
            event_type="shipping",
            actor_role="shipper",
            product_name="Fresh Basil",
            destination="Regional distributor",
            output_remains_ftl=True,
            action_terms=["shipping", "incorrect barcode printed on product label"],
        )

        result = classify_event_with_multisignal(event=event, document_type="shipping_log")

        self.assertEqual(result.final_ctes, ["shipping"])
        self.assertNotIn("abstain-return-or-correction", result.applied_precedence_rules)

    def test_traceability_plan_is_exclusive(self) -> None:
        event = _benchmark_event(
            event_id="plan",
            event_type="traceability_plan",
            actor_role="unknown",
            product_name="Fresh Basil",
            destination=None,
            output_remains_ftl=True,
            action_terms=["traceability_plan", "record_maintenance_procedure"],
        )

        result = classify_event_with_multisignal(event=event, document_type="traceability_plan")

        self.assertEqual(result.final_ctes, ["traceability_plan"])
        self.assertIn("traceability-plan-exclusive", result.applied_precedence_rules)

    def test_gold_benchmark_set_has_50_cases_and_reports_perfect_metrics(self) -> None:
        matrix = build_cte_precedence_matrix()
        cases = build_phase10c_benchmark_cases()
        results = [evaluate_benchmark_case(case=case, precedence_matrix=matrix) for case in cases]
        report = build_precision_recall_report(results)

        self.assertEqual(len(cases), 50)
        self.assertEqual(report.exact_match_count, 50)
        self.assertEqual(report.exact_match_rate, 1.0)
        self.assertEqual(report.suppression_correctness_rate, 1.0)
        self.assertEqual(report.abstention_correctness_rate, 1.0)

    def test_phase10c_package_builds_from_sample_workbook(self) -> None:
        package = build_phase10c_cte_hardening(
            input_file=ROOT / "data/samples/fsma204-full-audit-sample.xlsx",
            ftl_food_items_file=ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json",
        )

        self.assertEqual(package.summary["benchmarkCases"], 50)
        self.assertEqual(package.summary["benchmarkFailures"], 0)
        self.assertEqual(package.summary["exactMatchRate"], 1.0)
        self.assertTrue(package.summary["acceptanceCoverage"]["RI-10C-006_cte_precision_recall_report"])


if __name__ == "__main__":
    unittest.main()
