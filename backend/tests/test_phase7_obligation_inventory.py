from __future__ import annotations

import unittest
from pathlib import Path

from traceready_backend.intelligence.phase07_obligation_inventory import build_phase7_obligation_inventory


ROOT = Path(__file__).resolve().parents[2]


class Phase7ObligationInventoryTest(unittest.TestCase):
    def test_builds_linked_confidence_scored_approved_obligation_set(self) -> None:
        package = build_phase7_obligation_inventory(
            phase6_review_package_file=ROOT / "data/regulatory/intelligence/review/phase6-review-package.json",
            chunks_file=ROOT / "data/regulatory/registry/source-chunks.json",
        )

        self.assertGreaterEqual(package.summary["obligationDrafts"], 12)
        self.assertEqual(package.summary["inventoryRecords"], package.summary["obligationDrafts"])
        self.assertGreaterEqual(package.summary["approvedObligations"], 12)
        self.assertEqual(package.approved_obligation_set.status, "approved")
        self.assertTrue(package.approved_obligation_set.immutable)
        self.assertIn("traceability_plan", package.summary["cteCoverage"])
        self.assertIn("shipping", package.summary["cteCoverage"])
        self.assertIn("transformation", package.summary["cteCoverage"])
        self.assertGreater(package.summary["linkCoverage"]["with_kde_links"], 0)
        self.assertGreater(package.summary["linkCoverage"]["with_tlc_links"], 0)
        self.assertEqual(package.summary["citationCoverage"]["invalid"], 0)

    def test_approved_set_contains_only_approved_records(self) -> None:
        package = build_phase7_obligation_inventory(
            phase6_review_package_file=ROOT / "data/regulatory/intelligence/review/phase6-review-package.json",
            chunks_file=ROOT / "data/regulatory/registry/source-chunks.json",
        )

        for record in package.approved_obligation_set.records:
            self.assertEqual(record["metadata"]["review_status"], "approved")
            self.assertEqual(record["approval"]["immutable_package_id"], package.approved_obligation_set.package_id)
            self.assertEqual(record["confidence_score"]["level"], "high")


if __name__ == "__main__":
    unittest.main()
