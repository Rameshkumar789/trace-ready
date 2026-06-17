import unittest

from traceready_ingestion.context import build_source_context, fsma_rules_guidance_context


class FsmaRulesContextTest(unittest.TestCase):
    def test_context_identifies_core_traceability_rule(self):
        context = fsma_rules_guidance_context()
        self.assertIn("FDA-2014-N-0053", context.core_rule_dockets)
        self.assertEqual(context.core_sources_to_ingest[0].applicability, "direct_core")

    def test_build_source_context_matches_subpart_s(self):
        context = build_source_context(
            "ecfr-21-cfr-1-subpart-s-real",
            "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
        )
        self.assertEqual(context["matchedSource"]["source_role"], "codified_legal_text")
        self.assertEqual(context["matchedSource"]["trace_ready_priority"], "must_ingest")


if __name__ == "__main__":
    unittest.main()
