from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from traceready_backend.backend.repositories.supabase_tables import RegulatoryDraftRecordUpsert


class RegulatoryDraftRepository(Protocol):
    def upsert_draft_records(self, records: list[RegulatoryDraftRecordUpsert]) -> list[dict[str, object]]:
        ...


@dataclass(frozen=True)
class DraftImportResult:
    package_file: str
    package_draft_count: int
    imported_count: int
    ready_for_review_count: int
    rejected_count: int
    skipped_count: int
    collection_counts: dict[str, int]
    status_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "package_file": self.package_file,
            "package_draft_count": self.package_draft_count,
            "imported_count": self.imported_count,
            "ready_for_review_count": self.ready_for_review_count,
            "rejected_count": self.rejected_count,
            "skipped_count": self.skipped_count,
            "collection_counts": self.collection_counts,
            "status_counts": self.status_counts,
        }


def import_phase6_draft_review_records(
    *,
    phase6_review_package_file: Path,
    repository: RegulatoryDraftRepository,
    include_rejected: bool = True,
    only_ready_for_review: bool = False,
) -> DraftImportResult:
    package = json.loads(phase6_review_package_file.read_text(encoding="utf-8"))
    draft_records = package.get("draft_records", [])
    if not isinstance(draft_records, list):
        raise ValueError("Phase 6 review package must contain a draft_records array.")

    rows: list[RegulatoryDraftRecordUpsert] = []
    status_counts: dict[str, int] = {}
    collection_counts: dict[str, int] = {}
    skipped = 0

    for raw_record in draft_records:
        if not isinstance(raw_record, dict):
            skipped += 1
            continue
        review_status = str(raw_record.get("review_status") or "draft")
        if only_ready_for_review and review_status != "needs_review":
            skipped += 1
            continue
        if not include_rejected and review_status == "rejected":
            skipped += 1
            continue
        row = _to_upsert(raw_record)
        rows.append(row)
        status_counts[row.review_status] = status_counts.get(row.review_status, 0) + 1
        collection_counts[row.collection] = collection_counts.get(row.collection, 0) + 1

    imported_rows = repository.upsert_draft_records(rows) if rows else []
    return DraftImportResult(
        package_file=str(phase6_review_package_file),
        package_draft_count=len(draft_records),
        imported_count=len(imported_rows) if imported_rows else len(rows),
        ready_for_review_count=status_counts.get("needs_review", 0),
        rejected_count=status_counts.get("rejected", 0),
        skipped_count=skipped,
        collection_counts=dict(sorted(collection_counts.items())),
        status_counts=dict(sorted(status_counts.items())),
    )


def _to_upsert(record: dict[str, object]) -> RegulatoryDraftRecordUpsert:
    draft_id = _required_text(record, "draft_id")
    collection = _required_text(record, "collection")
    record_id = _required_text(record, "record_id")
    return RegulatoryDraftRecordUpsert(
        id=draft_id,
        collection=collection,
        record_id=record_id,
        source_phase=_text(record, "source_phase", "unknown"),
        extraction_method=_text(record, "extraction_method", "unknown"),
        confidence=_text(record, "confidence", "unknown"),
        review_status=_text(record, "review_status", "draft"),
        source_chunk_ids_json=_list(record.get("source_chunk_ids")),
        citation_count=_int(record.get("citation_count")),
        citation_coverage_status=_text(record, "citation_coverage_status", "unknown"),
        schema_valid=bool(record.get("schema_valid")),
        citation_valid=bool(record.get("citation_valid")),
        validation_errors_json=_list(record.get("validation_errors")),
        reviewer_blockers_json=_list(record.get("reviewer_blockers")),
        payload_json=_dict(record.get("payload")),
    )


def _required_text(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Draft record is missing required text field: {key}")
    return value


def _text(record: dict[str, object], key: str, default: str) -> str:
    value = record.get(key)
    return value if isinstance(value, str) and value else default


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}
