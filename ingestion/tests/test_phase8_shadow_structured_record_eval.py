from __future__ import annotations

import unittest
from pathlib import Path

from scripts.intelligence.build_phase8_shadow_structured_record_eval import build_shadow_eval


ROOT = Path(__file__).resolve().parents[2]


class Phase8ShadowStructuredRecordEvalTest(unittest.TestCase):
    def test_all_structured_records_shadow_eval_reports_support_and_noise(self) -> None:
        package = build_shadow_eval(
            phase6_review_package_file=ROOT / "data/regulatory/intelligence/review/phase6-review-package.json",
            unseen_challenge_set_file=ROOT / "data/regulatory/intelligence/scenarios/phase8-unseen-web-challenge-set.json",
            unseen_results_file=ROOT / "data/regulatory/intelligence/scenarios/phase8-unseen-web-challenge-results.json",
        )

        self.assertEqual(package["summary"]["structuredRecordsLoaded"], 550)
        self.assertEqual(package["summary"]["challengeCount"], 8)
        self.assertEqual(package["summary"]["unseenInferenceStatusCounts"], {"gap": 3, "pass": 5})
        self.assertEqual(
            package["summary"]["shadowStructuredRecordStatusCounts"],
            {"supported_with_drafts_and_rejected_noise": 8},
        )
        self.assertGreater(package["summary"]["readyOrApprovedMatchedRecordsAcrossChallenges"], 0)
        self.assertGreater(package["summary"]["rejectedMatchedRecordsAcrossChallenges"], 0)


if __name__ == "__main__":
    unittest.main()
