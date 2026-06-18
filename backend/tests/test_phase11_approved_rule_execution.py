from __future__ import annotations

import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

from traceready_backend.audit_engine.rule_execution import (
    _is_answered,
    build_phase11_rule_execution,
    check_kde_completeness,
    check_sortable_export_readiness,
    check_tlc_lineage,
    generate_exception_queue,
    map_events_to_approved_obligations,
)
from traceready_backend.audit_engine.customer_evidence import build_phase10_customer_evidence
from traceready_backend.audit_engine.cte_classification import build_phase10c_cte_hardening


ROOT = Path(__file__).resolve().parents[2]
RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
SAMPLE = ROOT / "data/samples/fsma204-full-audit-sample.xlsx"
FTL = ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json"


class Phase11ApprovedRuleExecutionTest(unittest.TestCase):
    def test_maps_customer_ctes_only_to_approved_rule_package_obligations(self) -> None:
        rule_package = json.loads(RULE_PACKAGE.read_text(encoding="utf-8"))
        approved = {
            obligation["obligation_id"]: obligation
            for obligation in rule_package["records"]["obligations"]
            if obligation["metadata"]["review_status"] == "approved"
        }
        phase10c = build_phase10c_cte_hardening(input_file=SAMPLE, ftl_food_items_file=FTL)

        mappings = map_events_to_approved_obligations(
            hardened_results=phase10c.production_event_results,
            approved_obligations=approved,
            rule_package=rule_package,
        )

        self.assertTrue(mappings)
        self.assertTrue(all(mapping.approved_obligation_id in approved for mapping in mappings))
        self.assertIn("FSMA204-OBL-DET-1340-SHIPPING-KDES", {mapping.approved_obligation_id for mapping in mappings})
        self.assertIn("FSMA204-OBL-DET-1345-RECEIVING-KDES", {mapping.approved_obligation_id for mapping in mappings})
        self.assertIn("FSMA204-OBL-DET-1350-TRANSFORMATION-KDES", {mapping.approved_obligation_id for mapping in mappings})
        cte_mappings = {mapping.approved_obligation_id for mapping in mappings if mapping.cte not in {"records_readiness", "sortable_export"}}
        self.assertNotIn("FSMA204-OBL-DET-1300-SCOPE", cte_mappings)

    def test_kde_completeness_checks_missing_and_present_customer_evidence(self) -> None:
        package = build_phase11_rule_execution(input_file=SAMPLE, approved_rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)
        by_event_field = {(check.event_id, check.field_key): check for check in package.kde_checks}

        self.assertEqual(by_event_field[("SHIP-1:PROD-1", "traceability_lot_code")].status, "present")
        self.assertEqual(by_event_field[("REC-1:PROD-1", "traceability_lot_code")].status, "missing")
        self.assertEqual(by_event_field[("TRANS-1:PROD-1", "source_lot_or_tlc")].status, "missing")

    def test_tlc_lineage_traceability_plan_and_export_checks_create_findings(self) -> None:
        package = build_phase11_rule_execution(input_file=SAMPLE, approved_rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)

        self.assertTrue(any(check.status == "gap" for check in package.tlc_checks))
        self.assertTrue(any(check.status == "missing" for check in package.traceability_plan_checks))
        self.assertTrue(any(check.status == "blocked" for check in package.sortable_export_checks))
        self.assertTrue(any(finding.finding_type == "tlc_lineage" for finding in package.audit_findings))
        self.assertFalse(any(finding.finding_type == "sortable_export_readiness" for finding in package.audit_findings))
        self.assertTrue(package.export_package.blockers)

    def test_exception_queue_is_generated_from_findings(self) -> None:
        package = build_phase11_rule_execution(input_file=SAMPLE, approved_rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)
        queue = generate_exception_queue(package.audit_findings)

        self.assertEqual(len(queue), len(package.audit_findings))
        # Findings are grouped by record + root cause, so the sample's missing-TLC
        # gaps surface as tlc_gap items (the KDE/lineage duplicates are merged in).
        self.assertTrue(any(item.queue_type == "tlc_gap" for item in queue))
        self.assertTrue(any(item.queue_type == "traceability_plan_gap" for item in queue))
        self.assertFalse(any(item.queue_type == "export_blocker" for item in queue))

    def test_findings_are_grouped_by_record_and_root_cause(self) -> None:
        package = build_phase11_rule_execution(input_file=SAMPLE, approved_rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)

        # One finding per affected record (not one per failing check). The sample has a
        # missing TLC on the receiving and transformation records plus an incomplete plan.
        by_event = defaultdict(list)
        for finding in package.audit_findings:
            by_event[finding.event_id].append(finding)
        self.assertEqual(len(by_event["REC-1:PROD-1"]), 1)
        self.assertEqual(len(by_event["TRANS-1:PROD-1"]), 1)
        # A single record is one finding even when it's missing several KDEs (grouped).
        # The full per-CTE KDE dictionary catches missing quantity/location too, so the
        # minimal sample fixture yields one finding per affected record + the plan + the
        # sample's small_producer exemption claim (claimed with no evidence -> not determined).
        self.assertEqual(len(package.audit_findings), 5)
        exemption_finding = next(f for f in package.audit_findings if f.finding_type == "exemption_claim")
        # Conservative: an unevidenced exemption claim is surfaced for review, never auto-granted.
        self.assertEqual(exemption_finding.status, "needs_review")
        self.assertIn("not determined", exemption_finding.message.lower())

        # Messages read in plain English and roll the specifics into sub_issues,
        # rather than exposing raw field keys to the partner.
        for finding in package.audit_findings:
            self.assertNotIn("_", finding.message)  # no raw field keys like traceability_lot_code
            self.assertTrue(finding.message[0].isupper())
        plan_finding = next(f for f in package.audit_findings if f.finding_type == "traceability_plan")
        # The sample is a distributor/processor (no harvest/cooling/packing CTEs), so the
        # farm map is not applicable and must not be reported as a missing plan component.
        self.assertNotIn("farm_map", plan_finding.affected_fields)
        self.assertEqual(len(plan_finding.affected_fields), 4)
        self.assertTrue(all(issue.startswith("Missing ") for issue in plan_finding.sub_issues))

    def test_phase11_package_generates_fda_style_export_package_and_summary(self) -> None:
        package = build_phase11_rule_execution(input_file=SAMPLE, approved_rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)

        self.assertEqual(package.summary["rulePackageId"], "approved-rule-package-v1")
        self.assertTrue(package.summary["approvedRuleOnly"])
        self.assertGreater(package.summary["obligationMappings"], 0)
        self.assertGreater(package.summary["auditFindings"], 0)
        self.assertIn(package.export_package.status, {"ready", "blocked"})
        self.assertIn("shipping", package.export_package.tabs)
        self.assertTrue(package.export_package.citations)
        self.assertTrue(package.summary["acceptanceCoverage"]["RI-109_fda_style_export_package"])

    def test_phase11_artifacts_include_workbook_file(self) -> None:
        from traceready_backend.audit_engine.rule_execution import write_phase11_rule_execution_artifacts

        package = build_phase11_rule_execution(input_file=SAMPLE, approved_rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs = write_phase11_rule_execution_artifacts(package, Path(tmpdir))

            self.assertTrue(Path(outputs["exportPackage"]).exists())
            self.assertTrue(Path(outputs["exportWorkbook"]).exists())
            self.assertTrue(Path(outputs["summary"]).exists())


class TlcLineageAndPlaceholderTest(unittest.TestCase):
    @staticmethod
    def _event(lot=None, source=None, output=None):
        return SimpleNamespace(lot_or_tlc=lot, source_lot_or_tlc=source, output_lot_or_tlc=output, evidence_ids=[])

    @staticmethod
    def _mapping(event_id, cte):
        return SimpleNamespace(event_id=event_id, cte=cte, approved_obligation_id="FSMA204-OBL-DET-1350-TRANSFORMATION-KDES")

    def test_placeholders_do_not_count_as_real_values(self):
        for placeholder in ["", "unknown", "UNKNOWN", "N/A", "n.a.", "tbd", "none", "null", "not provided", "-", "missing"]:
            self.assertFalse(_is_answered(placeholder), placeholder)
        for real in ["TLC-ROM-24-0602-A", "Fresh Cilantro", "2026-06-02", "55 cases"]:
            self.assertTrue(_is_answered(real), real)

    def test_placeholder_tlc_is_a_gap_not_linked(self):
        events = {"SHP-1": self._event(lot="UNKNOWN")}
        checks = check_tlc_lineage(mappings=[self._mapping("SHP-1", "shipping")], events=events)
        self.assertEqual(checks[0].status, "gap")

    def test_transformation_input_must_trace_upstream(self):
        # source lot exists nowhere upstream -> broken lineage even though codes are present
        events = {"TRN-1": self._event(source="LOT-X", output="LOT-NEW")}
        checks = check_tlc_lineage(mappings=[self._mapping("TRN-1", "transformation")], events=events)
        self.assertEqual(checks[0].status, "gap")
        self.assertIn("trace", checks[0].reason.lower())

    def test_transformation_input_that_traces_upstream_is_linked(self):
        events = {
            "REC-1": self._event(lot="LOT-X"),
            "TRN-1": self._event(source="LOT-X", output="LOT-NEW"),
        }
        checks = check_tlc_lineage(mappings=[self._mapping("TRN-1", "transformation")], events=events)
        trn = next(c for c in checks if c.event_id == "TRN-1")
        self.assertEqual(trn.status, "linked")

    def test_kde_contracts_cover_full_movement_kdes_and_cooling(self):
        from traceready_backend.audit_engine.rule_execution import _load_kde_check_contracts

        contracts = _load_kde_check_contracts()
        # The full FSMA KDE set per movement CTE — not the old 4-5 field subset.
        for cte in ("shipping", "receiving"):
            kdes = {k["kde"] for k in contracts[cte]["kdes"]}
            self.assertTrue({"traceability_lot_code", "quantity", "product_description"} <= kdes)
            self.assertTrue(any("location" in k for k in kdes), cte)
        # Cooling now has a KDE contract (it had none in the hardcoded list).
        self.assertIn("cooling", contracts)
        self.assertTrue(any(k["kde"] == "cooling_location" for k in contracts["cooling"]["kdes"]))


class ExemptionClaimEvaluationTest(unittest.TestCase):
    @staticmethod
    def _phase10(rows):
        records = []
        for row_number, fields in enumerate(rows, start=2):
            for field_key, value in fields.items():
                records.append(
                    SimpleNamespace(
                        evidence_id=f"ev-{row_number}-{field_key}",
                        sheet_name="10_Exemptions_Claims",
                        row_number=row_number,
                        field_key=field_key,
                        normalized_value=value,
                    )
                )
        return SimpleNamespace(evidence_records=records)

    def setUp(self):
        from traceready_backend.audit_engine.rule_execution import _load_exemption_rules

        self.rules = _load_exemption_rules()

    def _checks(self, rows):
        from traceready_backend.audit_engine.rule_execution import check_exemption_claims

        return check_exemption_claims(phase10=self._phase10(rows), exemption_rules=self.rules)

    def test_unevidenced_claim_is_not_determined_not_granted(self):
        checks = self._checks([
            {"exemption_claim_type": "small_producer", "exemption_claimed_by": "Supplier A", "exemption_evidence_provided": "no"}
        ])
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].status, "not_determined")
        self.assertIn("no supporting evidence", checks[0].reason.lower())

    def test_evidenced_claim_is_flagged_for_confirmation_never_auto_granted(self):
        checks = self._checks([
            {"exemption_claim_type": "non_ftl_product", "exemption_claimed_by": "Plant B", "exemption_evidence_provided": "yes"}
        ])
        self.assertEqual(checks[0].status, "needs_review")
        self.assertIn("does not auto-grant", checks[0].reason.lower())

    def test_unrecognized_claim_type_needs_reviewer_judgment(self):
        checks = self._checks([
            {"exemption_claim_type": "made_up_exemption", "exemption_evidence_provided": "yes"}
        ])
        self.assertEqual(checks[0].status, "needs_review")
        self.assertIn("could not be matched", checks[0].reason.lower())
        # Must NOT auto-grant: the records stay required until a reviewer confirms.
        self.assertIn("reviewer must confirm", checks[0].reason.lower())

    def test_tolerates_rich_supabase_card_schema(self):
        from traceready_backend.audit_engine.rule_execution import check_exemption_claims

        # The approved Supabase cards use prose exemption_type, documentation_needed, no aliases.
        rich_rules = [
            {
                "exemption_rule_id": "EXR-004-kill-step-applied",
                "exemption_type": "Kill Step Processing Exemption",
                "effect": "Partial Exemption",
                "documentation_needed": ["kill-step processing records", "validation study"],
            }
        ]
        checks = check_exemption_claims(
            phase10=self._phase10([
                {"exemption_claim_type": "Kill Step Processing Exemption", "exemption_evidence_provided": "no"}
            ]),
            exemption_rules=rich_rules,
        )
        self.assertEqual(checks[0].status, "not_determined")
        self.assertIn("kill step processing", checks[0].reason.lower())
        self.assertIn("kill-step processing records", checks[0].reason.lower())

    def test_alias_matches_canonical_rule(self):
        checks = self._checks([
            {"exemption_claim_type": "kill step", "exemption_evidence_provided": "no"}
        ])
        # 'kill step' is an alias of food_changed_no_longer_ftl
        self.assertEqual(checks[0].status, "not_determined")
        self.assertIn("food changed", checks[0].reason.lower())

    def test_blank_claim_type_is_ignored(self):
        checks = self._checks([{"exemption_claim_type": "", "exemption_evidence_provided": "yes"}])
        self.assertEqual(checks, [])


if __name__ == "__main__":
    unittest.main()
