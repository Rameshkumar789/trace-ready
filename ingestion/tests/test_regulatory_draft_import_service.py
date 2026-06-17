from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from traceready_backend.backend.repositories.supabase_tables import RegulatoryDraftRecordUpsert
from traceready_backend.backend.services.regulatory_draft_import_service import (
    import_phase6_draft_review_records,
)


class FakeDraftRepository:
    def __init__(self) -> None:
        self.records: list[RegulatoryDraftRecordUpsert] = []

    def upsert_draft_records(self, records: list[RegulatoryDraftRecordUpsert]) -> list[dict[str, object]]:
        self.records.extend(records)
        return [{"id": record.id} for record in records]


class RegulatoryDraftImportServiceTest(unittest.TestCase):
    def test_imports_phase6_drafts_without_approving_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_file = Path(temp_dir) / "phase6-review-package.json"
            package_file.write_text(
                json.dumps(
                    {
                        "draft_records": [
                            {
                                "draft_id": "draft:one",
                                "collection": "obligations",
                                "record_id": "obligation_one",
                                "source_phase": "phase5_ai_assisted",
                                "extraction_method": "ai_assisted",
                                "confidence": "medium",
                                "review_status": "needs_review",
                                "source_chunk_ids": ["chunk-1"],
                                "citation_count": 1,
                                "citation_coverage_status": "complete",
                                "schema_valid": True,
                                "citation_valid": True,
                                "validation_errors": [],
                                "reviewer_blockers": [],
                                "payload": {"obligation_id": "obligation_one"},
                            },
                            {
                                "draft_id": "draft:two",
                                "collection": "tlc_rules",
                                "record_id": "tlc_two",
                                "source_phase": "phase5_ai_assisted",
                                "extraction_method": "ai_assisted",
                                "confidence": "low",
                                "review_status": "rejected",
                                "source_chunk_ids": [],
                                "citation_count": 0,
                                "citation_coverage_status": "invalid",
                                "schema_valid": False,
                                "citation_valid": False,
                                "validation_errors": ["invalid citation"],
                                "reviewer_blockers": ["citation invalid"],
                                "payload": {"tlc_rule_id": "tlc_two"},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            repository = FakeDraftRepository()

            result = import_phase6_draft_review_records(
                phase6_review_package_file=package_file,
                repository=repository,
            )

        self.assertEqual(result.imported_count, 2)
        self.assertEqual(result.ready_for_review_count, 1)
        self.assertEqual(result.rejected_count, 1)
        self.assertEqual({record.review_status for record in repository.records}, {"needs_review", "rejected"})
        self.assertEqual(repository.records[0].payload_json, {"obligation_id": "obligation_one"})

    def test_can_import_only_ready_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_file = Path(temp_dir) / "phase6-review-package.json"
            package_file.write_text(
                json.dumps(
                    {
                        "draft_records": [
                            {
                                "draft_id": "draft:one",
                                "collection": "obligations",
                                "record_id": "obligation_one",
                                "review_status": "needs_review",
                            },
                            {
                                "draft_id": "draft:two",
                                "collection": "tlc_rules",
                                "record_id": "tlc_two",
                                "review_status": "rejected",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            repository = FakeDraftRepository()

            result = import_phase6_draft_review_records(
                phase6_review_package_file=package_file,
                repository=repository,
                only_ready_for_review=True,
            )

        self.assertEqual(result.imported_count, 1)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(repository.records[0].id, "draft:one")


if __name__ == "__main__":
    unittest.main()
