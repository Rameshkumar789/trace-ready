import unittest

from traceready_ingestion.intelligence.citations import (
    build_citation_coverage_report,
    validate_citation_span,
)


class CitationValidationTest(unittest.TestCase):
    def setUp(self):
        self.chunk_index = {
            "chunk-a": {
                "source_id": "source-a",
                "chunk_id": "chunk-a",
                "citation_anchor": "Section A",
                "text": "Traceability records must include a traceability lot code when required.",
            }
        }

    def test_validates_exact_support_text(self):
        result = validate_citation_span(
            {
                "source_id": "source-a",
                "chunk_id": "chunk-a",
                "citation_anchor": "Section A",
                "support_text": "traceability lot code",
            },
            self.chunk_index,
        )
        self.assertEqual(result.status, "valid")
        self.assertTrue(result.exact_match)

    def test_validates_normalized_support_text(self):
        result = validate_citation_span(
            {
                "source_id": "source-a",
                "chunk_id": "chunk-a",
                "citation_anchor": "Section A",
                "support_text": "Traceability records must include a\ntraceability lot code",
            },
            self.chunk_index,
        )
        self.assertEqual(result.status, "valid_normalized")
        self.assertTrue(result.normalized_match)

    def test_rejects_missing_chunk(self):
        result = validate_citation_span(
            {
                "source_id": "source-a",
                "chunk_id": "missing",
                "citation_anchor": "Section A",
                "support_text": "traceability lot code",
            },
            self.chunk_index,
        )
        self.assertEqual(result.status, "invalid")
        self.assertFalse(result.chunk_exists)

    def test_coverage_report_classifies_complete_partial_missing_invalid(self):
        report = build_citation_coverage_report(
            {
                "complete_records": [
                    {
                        "id": "complete",
                        "citations": [
                            {
                                "source_id": "source-a",
                                "chunk_id": "chunk-a",
                                "citation_anchor": "Section A",
                                "support_text": "traceability lot code",
                            }
                        ],
                    }
                ],
                "partial_records": [
                    {
                        "id": "partial",
                        "citations": [
                            {
                                "source_id": "source-a",
                                "chunk_id": "chunk-a",
                                "citation_anchor": "Section A",
                            }
                        ],
                    }
                ],
                "missing_records": [{"id": "missing"}],
                "invalid_records": [
                    {
                        "id": "invalid",
                        "citations": [
                            {
                                "source_id": "source-a",
                                "chunk_id": "missing",
                                "citation_anchor": "Section A",
                                "support_text": "traceability lot code",
                            }
                        ],
                    }
                ],
            },
            self.chunk_index,
        )
        self.assertEqual(report.summary["complete"], 1)
        self.assertEqual(report.summary["partial"], 1)
        self.assertEqual(report.summary["missing"], 1)
        self.assertEqual(report.summary["invalid"], 1)


if __name__ == "__main__":
    unittest.main()
