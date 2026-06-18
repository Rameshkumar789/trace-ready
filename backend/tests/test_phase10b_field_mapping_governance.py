from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from traceready_backend.audit_engine.customer_evidence import (
    build_field_mapping_suggestions,
    read_spreadsheet_evidence,
)
from traceready_backend.audit_engine.field_mapping_governance import (
    build_approved_mapping_profile,
    build_phase10b_mapping_governance,
    detect_mapping_profile_drift,
    generate_customer_field_mapping_drafts,
    review_mapping_drafts_for_bootstrap,
    run_mapping_profile_regression,
)


ROOT = Path(__file__).resolve().parents[2]


class Phase10BFieldMappingGovernanceTest(unittest.TestCase):
    def _write_csv(self, name: str, text: str) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_generates_evidence_backed_mapping_drafts(self) -> None:
        path = self._write_csv("customer_shipping.csv", "Lot #,Ship Date,Product\nTLC-1,2026-06-10,Fresh Basil\n")
        records = read_spreadsheet_evidence(path)
        suggestions = build_field_mapping_suggestions(records)

        drafts = generate_customer_field_mapping_drafts(
            suggestions=suggestions,
            evidence_records=records,
            input_file=path,
            customer_id="customer_a",
            source_system="wms_export",
        )
        lot_draft = next(draft for draft in drafts if draft.source_column == "Lot #")

        self.assertEqual(lot_draft.customer_id, "customer_a")
        self.assertEqual(lot_draft.proposed_canonical_field, "traceability_lot_code")
        self.assertEqual(lot_draft.review_status, "needs_review")
        self.assertTrue(lot_draft.evidence_ids)
        self.assertEqual(lot_draft.evidence_pointers[0]["cell"], "A2")
        self.assertEqual(lot_draft.extraction_method, "ai_assisted_mapping_draft")

    def test_review_workflow_approves_only_high_confidence_mappings(self) -> None:
        path = self._write_csv("customer_shipping.csv", "Lot #,Odd Customer Field\nTLC-1,abc\n")
        records = read_spreadsheet_evidence(path)
        drafts = generate_customer_field_mapping_drafts(
            suggestions=build_field_mapping_suggestions(records),
            evidence_records=records,
            input_file=path,
            customer_id="customer_a",
            source_system="wms_export",
        )

        approved, actions = review_mapping_drafts_for_bootstrap(drafts=drafts, reviewer="reviewer@example.com")

        self.assertEqual(len(actions), len(drafts))
        self.assertTrue(any(action.action == "approve" for action in actions))
        self.assertTrue(any(action.action == "hold_for_review" for action in actions))
        self.assertNotIn("odd_customer_field", {draft.proposed_canonical_field for draft in approved})

    def test_approved_profile_is_customer_specific_and_regression_checked(self) -> None:
        path = self._write_csv("customer_shipping.csv", "Lot #,Ship Date,Product\nTLC-1,2026-06-10,Fresh Basil\n")
        records = read_spreadsheet_evidence(path)
        drafts = generate_customer_field_mapping_drafts(
            suggestions=build_field_mapping_suggestions(records),
            evidence_records=records,
            input_file=path,
            customer_id="customer_a",
            source_system="wms_export",
        )
        approved, _ = review_mapping_drafts_for_bootstrap(drafts=drafts, reviewer="reviewer@example.com")

        profile = build_approved_mapping_profile(
            approved_drafts=approved,
            all_drafts=drafts,
            input_file=path,
            customer_id="customer_a",
            source_system="wms_export",
            reviewer="reviewer@example.com",
        )
        regression = run_mapping_profile_regression(profile=profile, evidence_records=records, source_file=path)

        self.assertEqual(profile.customer_id, "customer_a")
        self.assertEqual(profile.source_system, "wms_export")
        self.assertEqual(profile.status, "approved")
        self.assertEqual(len(profile.profile_hash), 64)
        self.assertEqual(regression.status, "pass")
        self.assertEqual(regression.failed_mappings, 0)

    def test_drift_detection_creates_review_tasks_for_new_or_missing_headers(self) -> None:
        baseline = self._write_csv("customer_shipping.csv", "Lot #,Ship Date,Product\nTLC-1,2026-06-10,Fresh Basil\n")
        baseline_records = read_spreadsheet_evidence(baseline)
        baseline_drafts = generate_customer_field_mapping_drafts(
            suggestions=build_field_mapping_suggestions(baseline_records),
            evidence_records=baseline_records,
            input_file=baseline,
            customer_id="customer_a",
            source_system="wms_export",
        )
        approved, _ = review_mapping_drafts_for_bootstrap(drafts=baseline_drafts, reviewer="reviewer@example.com")
        profile = build_approved_mapping_profile(
            approved_drafts=approved,
            all_drafts=baseline_drafts,
            input_file=baseline,
            customer_id="customer_a",
            source_system="wms_export",
            reviewer="reviewer@example.com",
        )
        changed = self._write_csv("customer_shipping_v2.csv", "Lot #,Product,New Customer Header\nTLC-1,Fresh Basil,x\n")
        changed_suggestions = build_field_mapping_suggestions(read_spreadsheet_evidence(changed))

        drift = detect_mapping_profile_drift(profile=profile, suggestions=changed_suggestions, source_file=changed)

        self.assertEqual(drift.status, "needs_review")
        self.assertTrue(any(task["taskType"] == "new_header_review" for task in drift.review_tasks))
        self.assertTrue(any(task["taskType"] == "missing_approved_header_review" for task in drift.review_tasks))

    def test_phase10b_package_builds_from_sample_workbook(self) -> None:
        package = build_phase10b_mapping_governance(
            input_file=ROOT / "data/samples/fsma204-full-audit-sample.xlsx",
            customer_id="pilot_customer",
            source_system="sample_workbook",
        )

        self.assertEqual(package.summary["draftMappings"], 50)
        self.assertEqual(package.summary["approvedMappings"], 50)
        self.assertEqual(package.summary["regressionStatus"], "pass")
        self.assertEqual(package.summary["driftStatus"], "stable")
        self.assertTrue(package.summary["acceptanceCoverage"]["RI-10B-006_mapping_drift_detection"])


if __name__ == "__main__":
    unittest.main()
