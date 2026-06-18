from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from traceready_backend.intelligence.phase09_approved_rule_package import (
    build_phase9_rule_package,
    diff_rule_packages,
)


ROOT = Path(__file__).resolve().parents[2]


class Phase9ApprovedRulePackageTest(unittest.TestCase):
    def _build(self):
        return build_phase9_rule_package(
            approved_obligation_set_file=ROOT / "data/regulatory/intelligence/obligations/phase7-approved-obligation-set-v1.json",
            scenario_summary_file=ROOT / "data/regulatory/intelligence/scenarios/phase8-summary.json",
            scenario_results_file=ROOT / "data/regulatory/intelligence/scenarios/phase8-regression-results.json",
            sources_file=ROOT / "data/regulatory/registry/sources.json",
            chunks_file=ROOT / "data/regulatory/registry/source-chunks.json",
        )

    def test_builds_immutable_approved_rule_package_from_green_scenario_gate(self) -> None:
        phase9 = self._build()
        package = phase9["package"]

        self.assertEqual(package.package_id, "approved-rule-package-v1")
        self.assertEqual(package.status, "approved")
        self.assertTrue(package.immutable)
        self.assertEqual(package.record_counts, {"obligations": 12})
        self.assertEqual(len(package.records["obligations"]), 12)
        self.assertEqual(package.scenario_regression_gate.status, "passed")
        self.assertTrue(package.scenario_regression_gate.can_publish_rule_changes)
        self.assertEqual(package.scenario_regression_gate.benchmark_count, 13)
        self.assertEqual(package.scenario_regression_gate.pass_count, 13)
        self.assertEqual(package.scenario_regression_gate.fail_count, 0)
        self.assertGreater(len(package.source_versions), 0)
        self.assertEqual(len(package.package_hash), 64)
        self.assertTrue(package.rollback["rollback_supported"])
        for record in package.records["obligations"]:
            self.assertEqual(record["metadata"]["review_status"], "approved")

    def test_diff_reports_added_records_against_empty_baseline(self) -> None:
        phase9 = self._build()
        diff = phase9["diff"]

        self.assertEqual(diff.from_package_id, None)
        self.assertEqual(diff.to_package_id, "approved-rule-package-v1")
        self.assertEqual(diff.status, "changed")
        self.assertEqual(len(diff.added_records["obligations"]), 12)
        self.assertEqual(diff.removed_records["obligations"], [])
        self.assertEqual(diff.changed_records["obligations"], [])
        self.assertTrue(diff.rollback_safe)

    def test_diff_detects_record_change_between_versions(self) -> None:
        phase9 = self._build()
        previous = phase9["package"].model_dump(mode="json")
        current = copy.deepcopy(previous)
        current["version"] = 2
        current["package_id"] = "approved-rule-package-v2"
        current["records"]["obligations"][0]["action"] = "Changed action text for test diff"

        diff = diff_rule_packages(previous, current)

        self.assertEqual(diff.status, "changed")
        self.assertEqual(diff.added_records["obligations"], [])
        self.assertEqual(diff.removed_records["obligations"], [])
        self.assertEqual(diff.changed_records["obligations"], [current["records"]["obligations"][0]["obligation_id"]])
        self.assertEqual(len(diff.unchanged_records["obligations"]), 11)

    def test_package_rejects_failed_scenario_gate(self) -> None:
        scenario_summary = json.loads((ROOT / "data/regulatory/intelligence/scenarios/phase8-summary.json").read_text(encoding="utf-8"))
        scenario_summary["canPublishRuleChanges"] = False
        scenario_summary["publishGateStatus"] = "blocked_without_reviewer_override"

        with tempfile.TemporaryDirectory() as tmpdir:
            failed_summary = Path(tmpdir) / "failed-summary.json"
            failed_summary.write_text(json.dumps(scenario_summary), encoding="utf-8")

            with self.assertRaises(ValueError):
                build_phase9_rule_package(
                    approved_obligation_set_file=ROOT / "data/regulatory/intelligence/obligations/phase7-approved-obligation-set-v1.json",
                    scenario_summary_file=failed_summary,
                    scenario_results_file=ROOT / "data/regulatory/intelligence/scenarios/phase8-regression-results.json",
                    sources_file=ROOT / "data/regulatory/registry/sources.json",
                    chunks_file=ROOT / "data/regulatory/registry/source-chunks.json",
                )


if __name__ == "__main__":
    unittest.main()
