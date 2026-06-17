import unittest

from traceready_ingestion.chunking.legal_chunker import chunk_legal_meaning
from traceready_ingestion.drafting.kde_drafter import draft_kde_requirement
from traceready_ingestion.drafting.rule_card_drafter import draft_rule_card


class RuleCardDrafterTest(unittest.TestCase):
    def test_drafts_schema_valid_rule_and_kde_cards(self):
        chunks = chunk_legal_meaning(
            source_id="src-ecfr",
            source_url="https://example.test/ecfr",
            source_hash="abc",
            retrieved_at="2026-06-14T00:00:00Z",
            sections=[
                {
                    "section_label": "Receiving KDEs",
                    "section": "21 CFR 1.1345",
                    "text": "Receiving records must maintain TLC and immediate previous source KDEs.",
                }
            ],
        )
        rule = draft_rule_card(chunks, "receiving")
        kde = draft_kde_requirement(chunks[0], "receiving", "Immediate previous source")
        self.assertEqual(rule.source_chunk_ids, [chunks[0].chunk_id])
        self.assertTrue(rule.requires_expert_review)
        self.assertEqual(kde.source_chunk_id, chunks[0].chunk_id)
        self.assertTrue(kde.requires_expert_review)


if __name__ == "__main__":
    unittest.main()
