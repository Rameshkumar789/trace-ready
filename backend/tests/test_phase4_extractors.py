import json
import unittest
from pathlib import Path

from traceready_backend.intelligence.phase04_deterministic_extractors import (
    extract_cte_kde_candidates,
    extract_defined_terms,
    extract_ftl_food_items,
    extract_scenario_benchmarks,
    extract_sortable_export_fields,
    extract_traceability_plan_requirements,
)
from traceready_backend.intelligence.schemas import CteType


ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = ROOT / "data/regulatory/registry/source-chunks.json"
WORKBOOK_PATH = ROOT / "data/regulatory/fda-sortable-spreadsheet-xlsx/raw/fda-sortable-spreadsheet-xlsx.xlsx"


class Phase4ExtractorsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    def test_extracts_full_ftl_taxonomy(self):
        records = extract_ftl_food_items(self.chunks)

        self.assertEqual(len(records), 20)
        commodities = {record.commodity for record in records}
        self.assertIn("Tomatoes (fresh)", commodities)
        self.assertIn("Ready-to-eat deli salads", commodities)
        self.assertTrue(all(record.citations for record in records))

    def test_extracts_sortable_workbook_fields(self):
        records = extract_sortable_export_fields(self.chunks, WORKBOOK_PATH)

        self.assertGreaterEqual(len(records), 300)
        self.assertTrue(any(record.workbook_tab == "Shipping" and "Traceability Lot Code" in record.field_name for record in records))
        self.assertTrue(any(record.workbook_tab == "Transformation" and record.applies_to_ctes == [CteType.TRANSFORMATION] for record in records))

    def test_extracts_cte_definitions_and_kde_candidates(self):
        cte_definitions, kde_requirements = extract_cte_kde_candidates(self.chunks)

        self.assertGreaterEqual(len(cte_definitions), 7)
        self.assertTrue(any(record.cte_type == CteType.RECEIVING for record in cte_definitions))
        self.assertGreaterEqual(len(kde_requirements), 45)
        self.assertTrue(any(record.cte_type == CteType.HARVESTING and "Date of harvesting" in record.kde_name for record in kde_requirements))

    def test_extracts_defined_terms(self):
        records = extract_defined_terms(self.chunks)

        self.assertGreaterEqual(len(records), 20)
        self.assertTrue(any(record.normalized_key == "traceability_lot_code" for record in records))
        self.assertTrue(any(record.normalized_key == "critical_tracking_event" for record in records))

    def test_extracts_traceability_plan_requirements(self):
        records = extract_traceability_plan_requirements(self.chunks)

        self.assertEqual(len(records), 6)
        self.assertTrue(any("point of contact" in record.required_detail.lower() for record in records))
        self.assertTrue(any("2 years" in record.required_detail for record in records))

    def test_extracts_scenario_benchmarks(self):
        records = extract_scenario_benchmarks(self.chunks)

        self.assertEqual(len(records), 6)
        self.assertTrue(any("sprouts" in record.scenario_name.lower() for record in records))
        self.assertTrue(all(record.open_questions for record in records))


if __name__ == "__main__":
    unittest.main()
