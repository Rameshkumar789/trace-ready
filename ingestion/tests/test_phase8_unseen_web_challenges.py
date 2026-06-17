from __future__ import annotations

import unittest

from traceready_ingestion.intelligence.phase08_unseen_web_challenges import build_unseen_web_challenge_package


class Phase8UnseenWebChallengeTest(unittest.TestCase):
    def test_unseen_web_challenge_set_exposes_generalization_gaps(self) -> None:
        package = build_unseen_web_challenge_package()

        self.assertEqual(package.summary["challengeCount"], 8)
        self.assertEqual(package.summary["statusCounts"], {"gap": 3, "pass": 5})
        self.assertEqual(package.summary["passRate"], 0.625)

        by_id = {result.challenge_id: result for result in package.results}
        self.assertEqual(by_id["unseen_web:romaine_salad_kit"].status, "pass")
        self.assertEqual(by_id["unseen_web:fresh_mango_salsa"].status, "pass")
        self.assertEqual(by_id["unseen_web:tomato_paste_shelf_stable"].status, "gap")
        self.assertIn("shipping", by_id["unseen_web:tomato_paste_shelf_stable"].unexpected_ctes)
        self.assertEqual(by_id["unseen_web:dockside_mahi_mahi"].status, "gap")
        self.assertIn("receiving", by_id["unseen_web:dockside_mahi_mahi"].unexpected_ctes)


if __name__ == "__main__":
    unittest.main()
