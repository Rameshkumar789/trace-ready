from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from traceready_ingestion.audit_engine.customer_evidence import (
    build_customer_event_graph,
    build_field_mapping_suggestions,
    build_phase10_customer_evidence,
    build_traceability_entity_graph,
    classify_event_ctes,
    read_spreadsheet_evidence,
    resolve_food_form,
)


ROOT = Path(__file__).resolve().parents[2]


class Phase10CustomerEvidenceTest(unittest.TestCase):
    def _write_csv(self, rows: list[dict[str, str]]) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "messy-customer-evidence.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_spreadsheet_ingestion_keeps_cell_lineage_and_mapping_confidence(self) -> None:
        path = self._write_csv(
            [
                {
                    "Lot #": "TLC-001",
                    "Ship Date": "06/10/2026",
                    "Product": "Fresh Basil",
                    "Destination": "Regional distributor",
                }
            ]
        )

        evidence_records = read_spreadsheet_evidence(path)
        by_column = {record.column_name: record for record in evidence_records}

        self.assertEqual(by_column["Lot #"].field_key, "traceability_lot_code")
        self.assertEqual(by_column["Lot #"].cell, "A2")
        self.assertEqual(by_column["Lot #"].source_pointer.row_number, 2)
        self.assertEqual(by_column["Ship Date"].field_key, "date_you_shipped_the_food")
        self.assertEqual(by_column["Ship Date"].normalized_value, "2026-06-10")
        self.assertGreaterEqual(by_column["Ship Date"].confidence, 0.9)

    def test_field_mapping_suggestions_are_reviewable_and_evidence_backed(self) -> None:
        path = self._write_csv([{"Lot #": "TLC-001", "Ship Date": "06/10/2026", "Product": "Fresh Basil"}])
        suggestions = build_field_mapping_suggestions(read_spreadsheet_evidence(path))
        by_column = {suggestion.source_column: suggestion for suggestion in suggestions}

        self.assertEqual(by_column["Lot #"].field_key, "traceability_lot_code")
        self.assertEqual(by_column["Ship Date"].field_key, "date_you_shipped_the_food")
        self.assertEqual(by_column["Lot #"].review_status, "needs_review")
        self.assertTrue(by_column["Lot #"].evidence_ids)
        self.assertEqual(by_column["Lot #"].suggestion_method, "ai_assisted_field_mapping_suggestion")

    def test_entity_and_event_graph_are_built_before_cte_classification(self) -> None:
        path = self._write_csv(
            [
                {
                    "Event Type": "shipping",
                    "Lot #": "TLC-001",
                    "Ship Date": "06/10/2026",
                    "Product": "Fresh Basil",
                    "Destination": "Regional distributor",
                }
            ]
        )
        evidence_records = read_spreadsheet_evidence(path)
        entity_graph = build_traceability_entity_graph(evidence_records, ftl_food_items=[])
        event_graph = build_customer_event_graph(evidence_records, entity_graph=entity_graph, ftl_food_items=[])
        classification = classify_event_ctes(event_graph[0])

        self.assertEqual(entity_graph.products[0].name, "Fresh Basil")
        self.assertEqual(entity_graph.lots[0].name, "TLC-001")
        self.assertEqual(event_graph[0].product_name, "Fresh Basil")
        self.assertEqual(classification.final_ctes, ["shipping"])
        self.assertEqual(classification.suppressed_ctes, [])

    def test_suppression_prevents_first_land_based_receiving_double_count(self) -> None:
        path = self._write_csv(
            [
                {
                    "Event Type": "receiving",
                    "Location Type": "first land based receiver",
                    "Product": "Fresh Tuna",
                    "Lot #": "TUNA-001",
                }
            ]
        )
        event = build_customer_event_graph(read_spreadsheet_evidence(path), ftl_food_items=[])[0]
        classification = classify_event_ctes(event)

        self.assertEqual(classification.final_ctes, ["first_land_based_receiving"])
        self.assertEqual(classification.suppressed_ctes, ["receiving"])

    def test_suppression_prevents_direct_to_consumer_shipping(self) -> None:
        path = self._write_csv(
            [
                {
                    "Event Type": "shipping",
                    "Product": "Fresh Basil",
                    "Lot #": "TLC-001",
                    "Destination": "direct to consumer",
                    "Ship Date": "2026-06-10",
                }
            ]
        )
        event = build_customer_event_graph(read_spreadsheet_evidence(path), ftl_food_items=[])[0]
        classification = classify_event_ctes(event)

        self.assertEqual(classification.final_ctes, [])
        self.assertEqual(classification.suppressed_ctes, ["shipping"])

    def test_non_ftl_form_generates_reviewer_question_and_suppression(self) -> None:
        path = self._write_csv(
            [
                {
                    "Event Type": "transformation",
                    "Product": "Canned Tuna Salad",
                    "Food Form": "canned shelf stable",
                    "Lot #": "CAN-001",
                    "Source Lot": "RAW-001",
                    "Output Lot": "CAN-001",
                }
            ]
        )
        event = build_customer_event_graph(read_spreadsheet_evidence(path), ftl_food_items=[])[0]
        classification = classify_event_ctes(event)

        self.assertEqual(event.food_form.output_remains_ftl, False)
        self.assertEqual(classification.final_ctes, [])
        self.assertIn("transformation", classification.suppressed_ctes)
        self.assertTrue(classification.reviewer_questions)

    def test_food_form_resolver_matches_ftl_library(self) -> None:
        ftl_items = [
            {
                "category": "herbs",
                "commodity": "Herbs (fresh)",
                "included_examples": ["basil"],
                "description": "Fresh herbs",
            }
        ]

        resolution = resolve_food_form(product_name="Fresh Basil", ftl_category=None, ftl_food_items=ftl_items)

        self.assertTrue(resolution.is_ftl_likely)
        self.assertTrue(resolution.output_remains_ftl)
        self.assertGreaterEqual(resolution.confidence, 0.9)

    def test_phase10_package_builds_from_real_sample_workbook(self) -> None:
        package = build_phase10_customer_evidence(
            input_file=ROOT / "data/samples/fsma204-full-audit-sample.xlsx",
            ftl_food_items_file=ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json",
        )

        self.assertGreater(package.summary["evidenceRecords"], 0)
        self.assertGreater(package.summary["eventNodes"], 0)
        self.assertTrue(package.summary["acceptanceCoverage"]["RI-097_deterministic_cte_classifier"])
        self.assertIn("receiving", package.summary["finalCteCounts"])


if __name__ == "__main__":
    unittest.main()
