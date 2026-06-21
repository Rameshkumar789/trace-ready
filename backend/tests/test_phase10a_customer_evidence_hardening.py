from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from bellwether_backend.audit_engine.customer_evidence import (
    build_document_profiles,
    build_field_mapping_suggestions,
    build_phase10_customer_evidence,
    build_customer_evidence_quality_report,
    detect_evidence_conflicts,
    infer_filename_and_sheet_facts,
    read_spreadsheet_evidence,
)


ROOT = Path(__file__).resolve().parents[2]


class Phase10ACustomerEvidenceHardeningTest(unittest.TestCase):
    def test_csv_parser_handles_blank_header_band_notes_rows_and_repeated_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "SupplierA_shipping_lot_TLC-900_2026-06-10.csv"
            rows = [
                ["Generated export from customer ERP"],
                [],
                ["Shipping", "Shipping", "Product", "Lot"],
                ["Ship Date", "Destination", "Product", "Lot #"],
                ["06/10/2026", "Regional DC", "Fresh Basil", "TLC-900"],
                ["Ship Date", "Destination", "Product", "Lot #"],
                ["Notes: second page starts below"],
                ["20260611", "Restaurant", "Fresh Basil", "TLC-901"],
            ]
            with path.open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerows(rows)

            records = read_spreadsheet_evidence(path)
            by_value = {(record.field_key, record.normalized_value) for record in records}

            self.assertIn(("date_you_shipped_the_food", "2026-06-10"), by_value)
            self.assertIn(("date_you_shipped_the_food", "2026-06-11"), by_value)
            self.assertIn(("traceability_lot_code", "TLC-900"), by_value)
            self.assertNotIn(("product_name", "Product"), by_value)

    def test_xlsx_parser_handles_hidden_rows_columns_and_merged_cells(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "BOL_TLC-777_2026-06-12.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Shipping BOL"
            sheet["A1"] = "Shipping records"
            sheet.merge_cells("A1:D1")
            sheet["A2"] = "hide me"
            sheet.row_dimensions[2].hidden = True
            sheet["A3"] = "Ship Date"
            sheet["B3"] = "Lot #"
            sheet["C3"] = "Product"
            sheet["D3"] = "Hidden Column"
            sheet["E3"] = "Quantity"
            sheet.column_dimensions["D"].hidden = True
            sheet["A4"] = "6/12/26"
            sheet["B4"] = "tlc-777"
            sheet["C4"] = "Fresh Cucumber"
            sheet["D4"] = "should not parse"
            sheet["E4"] = "=2+3"
            workbook.save(path)

            records = read_spreadsheet_evidence(path)
            by_field = {record.field_key: record for record in records}

            self.assertEqual(by_field["date_you_shipped_the_food"].normalized_value, "2026-06-12")
            self.assertEqual(by_field["traceability_lot_code"].normalized_value, "TLC-777")
            self.assertEqual(by_field["traceability_lot_code"].cell, "B4")
            self.assertEqual(by_field["quantity"].raw_value, "=2+3")
            self.assertEqual(by_field["quantity"].field_type, "formula")
            self.assertNotIn("hidden_column", {record.field_key for record in records})

    def test_filename_and_sheet_name_fact_extraction_detects_lot_date_document_and_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invoice_basil_lot_TLC-200_2026-06-10.csv"
            path.write_text("Product,Lot #\nFresh Basil,TLC-200\n", encoding="utf-8")
            records = read_spreadsheet_evidence(path)

            inferred = infer_filename_and_sheet_facts(input_file=path, evidence_records=records)
            facts = {(fact.field_key, fact.normalized_value) for fact in inferred}

            self.assertIn(("traceability_lot_code", "TLC-200"), facts)
            self.assertIn(("event_datetime", "2026-06-10"), facts)
            self.assertIn(("source_document_type", "invoice"), facts)
            self.assertIn(("product_name", "Basil"), facts)

    def test_document_profiles_classify_supported_customer_document_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "landing_ticket_vessel_tuna_TLC-333.csv"
            path.write_text("Vessel,Landing Date,Product,Lot #\nFV A,2026-06-10,Fresh Tuna,TLC-333\n", encoding="utf-8")
            records = read_spreadsheet_evidence(path)
            inferred = infer_filename_and_sheet_facts(input_file=path, evidence_records=records)

            profiles = build_document_profiles(input_file=path, evidence_records=records, inferred_facts=inferred)

            self.assertEqual(profiles[0].document_type, "seafood_landing_record")
            self.assertEqual(profiles[0].supported_parser, "seafood_landing_record_parser_v1")

    def test_conflict_model_preserves_same_row_conflicts_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "receiving_conflict.csv"
            path.write_text("Lot #,TLC,Product\nTLC-1,TLC-2,Fresh Basil\n", encoding="utf-8")
            records = read_spreadsheet_evidence(path)

            conflicts = detect_evidence_conflicts(records)

            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0].field_key, "traceability_lot_code")
            self.assertEqual(conflicts[0].severity, "high")
            self.assertEqual(set(conflicts[0].values), {"TLC-1", "TLC-2"})

    def test_quality_report_surfaces_unmapped_columns_conflicts_and_acceptance_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "shipping_unknown_conflict.csv"
            path.write_text("Lot #,TLC,Odd Customer Field,Ship Date\nTLC-1,TLC-2,abc,2026-06-10\n", encoding="utf-8")
            package = build_phase10_customer_evidence(input_file=path, ftl_food_items_file=ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json")

            self.assertIsNotNone(package.quality_report)
            self.assertEqual(package.quality_report.quality_gate, "needs_review")
            self.assertEqual(package.quality_report.conflict_count, 1)
            self.assertGreaterEqual(len(package.quality_report.unmapped_columns), 1)
            self.assertTrue(package.summary["acceptanceCoverage"]["RI-10A-006_customer_evidence_quality_report"])


if __name__ == "__main__":
    unittest.main()
