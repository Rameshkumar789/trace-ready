import unittest

from traceready_ingestion.chunking.legal_chunker import chunk_legal_meaning, chunk_legal_meaning_with_rejections


class LegalChunkerTest(unittest.TestCase):
    def test_chunks_by_legal_meaning_with_citation_anchor(self):
        chunks = chunk_legal_meaning(
            source_id="src-ecfr",
            source_url="https://example.test/ecfr",
            source_hash="abc",
            retrieved_at="2026-06-14T00:00:00Z",
            sections=[
                {
                    "section_label": "Shipping KDEs",
                    "section": "21 CFR 1.1340",
                    "text": "Shipping records must maintain TLC and immediate subsequent recipient KDEs.",
                }
            ],
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].anchors[0].section, "21 CFR 1.1340")

    def test_rejects_condition_without_obligation(self):
        with self.assertRaises(ValueError):
            chunk_legal_meaning(
                source_id="src",
                source_url="https://example.test",
                source_hash="abc",
                retrieved_at="2026-06-14T00:00:00Z",
                sections=[{"section_label": "Bad", "section": "x", "text": "When food is shipped."}],
            )

    def test_safe_chunking_records_rejections(self):
        chunks, rejected = chunk_legal_meaning_with_rejections(
            source_id="src",
            source_url="https://example.test",
            source_hash="abc",
            retrieved_at="2026-06-14T00:00:00Z",
            sections=[
                {"section_label": "Bad", "section": "x", "text": "When food is shipped."},
                {"section_label": "Good", "section": "y", "text": "Shipping records must maintain TLC."},
            ],
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].section_label, "Bad")


if __name__ == "__main__":
    unittest.main()
