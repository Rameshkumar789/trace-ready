from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from bellwether_backend.intelligence.citations import (
    build_citation_coverage_report,
    load_chunk_index,
)
from bellwether_backend.intelligence.schemas import (
    INTELLIGENCE_SCHEMA_MODELS,
    ConfidenceLevel,
    ExtractionMethod,
    ReviewStatus,
)


class ReviewValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: str
    message: str
    fields: list[str] = Field(default_factory=list)


class DraftReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    collection: str
    record_id: str
    source_phase: str
    extraction_method: str
    confidence: str
    review_status: ReviewStatus
    source_chunk_ids: list[str]
    citation_count: int
    citation_coverage_status: str
    schema_valid: bool
    citation_valid: bool
    validation_errors: list[str] = Field(default_factory=list)
    reviewer_blockers: list[str] = Field(default_factory=list)
    payload: dict[str, Any]


class ReviewActionLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    target_id: str
    action: str
    actor: str
    actor_role: str
    reason: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    created_at: str


class Phase6ReviewPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: dict[str, Any]
    draft_records: list[DraftReviewRecord]
    rejected_records: list[DraftReviewRecord]
    approved_records: list[dict[str, Any]]
    review_action_log: list[ReviewActionLogEntry]
    citation_coverage_report: dict[str, Any]


def build_phase6_review_package(
    *,
    phase4_drafts_file: Path,
    phase5_summary_file: Path,
    chunks_file: Path,
) -> Phase6ReviewPackage:
    chunk_index = load_chunk_index(chunks_file)
    raw_inputs = _load_phase4_records(phase4_drafts_file) + _load_phase5_records(phase5_summary_file)
    phase5_issue_map = _load_phase5_issue_map(phase5_summary_file)

    draft_records: list[DraftReviewRecord] = []
    review_action_log: list[ReviewActionLogEntry] = []
    records_for_citation_report: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for raw_input in raw_inputs:
        review_record = _validate_review_record(raw_input, chunk_index, phase5_issue_map)
        draft_records.append(review_record)
        records_for_citation_report[review_record.collection].append(review_record.payload)
        review_action_log.append(
            _action(
                target_id=review_record.draft_id,
                action="draft_ingested",
                reason="Draft loaded into Phase 6 reviewer workflow after schema and citation validation.",
                after=review_record.model_dump(mode="json"),
            )
        )
        if review_record.review_status == ReviewStatus.REJECTED:
            review_action_log.append(
                _action(
                    target_id=review_record.draft_id,
                    action="validation_rejected",
                    reason="Draft cannot enter reviewer approval queue until validation blockers are resolved.",
                    before=review_record.model_dump(mode="json"),
                    after=review_record.model_dump(mode="json"),
                )
            )
        elif review_record.review_status == ReviewStatus.CONFLICT_DETECTED:
            review_action_log.append(
                _action(
                    target_id=review_record.draft_id,
                    action="conflict_detected",
                    reason="Draft has a material conflict and requires reviewer resolution before approval.",
                    before=review_record.model_dump(mode="json"),
                    after=review_record.model_dump(mode="json"),
                )
            )

    rejected_records = [
        record
        for record in draft_records
        if record.review_status in {ReviewStatus.REJECTED, ReviewStatus.CONFLICT_DETECTED}
    ]
    approved_records: list[dict[str, Any]] = []
    citation_report = build_citation_coverage_report(records_for_citation_report, chunk_index)
    summary = _summary(draft_records, rejected_records, approved_records, review_action_log, citation_report.model_dump(mode="json"))

    return Phase6ReviewPackage(
        summary=summary,
        draft_records=draft_records,
        rejected_records=rejected_records,
        approved_records=approved_records,
        review_action_log=review_action_log,
        citation_coverage_report=citation_report.model_dump(mode="json"),
    )


def write_phase6_review_artifacts(package: Phase6ReviewPackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "package": output_dir / "phase6-review-package.json",
        "summary": output_dir / "phase6-summary.json",
        "draftRecords": output_dir / "phase6-draft-records.json",
        "rejectedRecords": output_dir / "phase6-rejected-records.json",
        "approvedRecords": output_dir / "phase6-approved-records.json",
        "reviewActionLog": output_dir / "phase6-review-action-log.json",
        "citationCoverageReport": output_dir / "phase6-citation-coverage-report.json",
    }
    _write_json(outputs["package"], package.model_dump(mode="json"))
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["draftRecords"], [record.model_dump(mode="json") for record in package.draft_records])
    _write_json(outputs["rejectedRecords"], [record.model_dump(mode="json") for record in package.rejected_records])
    _write_json(outputs["approvedRecords"], package.approved_records)
    _write_json(outputs["reviewActionLog"], [entry.model_dump(mode="json") for entry in package.review_action_log])
    _write_json(outputs["citationCoverageReport"], package.citation_coverage_report)
    return {key: str(path) for key, path in outputs.items()}


def _load_phase4_records(phase4_drafts_file: Path) -> list[dict[str, Any]]:
    phase4 = json.loads(phase4_drafts_file.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for collection, items in phase4.items():
        for record in items:
            records.append(
                {
                    "collection": collection,
                    "source_phase": "phase4_deterministic",
                    "validation_origin": "accepted",
                    "record": record,
                    "issues": [],
                }
            )
    return records


def _load_phase5_records(phase5_summary_file: Path) -> list[dict[str, Any]]:
    summary = json.loads(phase5_summary_file.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for run in summary.get("runs", []):
        for collection, stats in run.get("collections", {}).items():
            validation_file = _resolve_artifact_path(phase5_summary_file, stats["validationFile"])
            validation = json.loads(validation_file.read_text(encoding="utf-8"))
            for key, origin in [
                ("accepted_records", "accepted"),
                ("rejected_records", "rejected"),
                ("conflict_records", "conflict"),
            ]:
                for record in validation.get(key, []):
                    records.append(
                        {
                            "collection": collection,
                            "source_phase": "phase5_ai_assisted",
                            "validation_origin": origin,
                            "record": record,
                            "issues": validation.get("issues", []),
                        }
                    )
    return records


def _load_phase5_issue_map(phase5_summary_file: Path) -> dict[tuple[str, str], list[ReviewValidationIssue]]:
    summary = json.loads(phase5_summary_file.read_text(encoding="utf-8"))
    issues_by_record: dict[tuple[str, str], list[ReviewValidationIssue]] = defaultdict(list)
    for run in summary.get("runs", []):
        for collection, stats in run.get("collections", {}).items():
            validation_file = _resolve_artifact_path(phase5_summary_file, stats["validationFile"])
            validation = json.loads(validation_file.read_text(encoding="utf-8"))
            for issue in validation.get("issues", []):
                record_id = str(issue.get("record_id", "unknown"))
                issues_by_record[(collection, record_id)].append(
                    ReviewValidationIssue(
                        code=str(issue.get("code", "validation_issue")),
                        severity=str(issue.get("severity", "error")),
                        message=str(issue.get("message", "Validation issue.")),
                        fields=list(issue.get("fields", [])),
                    )
                )
    return issues_by_record


def _validate_review_record(
    raw_input: dict[str, Any],
    chunk_index: dict[str, dict[str, Any]],
    phase5_issue_map: dict[tuple[str, str], list[ReviewValidationIssue]],
) -> DraftReviewRecord:
    collection = str(raw_input["collection"])
    record = raw_input["record"]
    source_phase = str(raw_input["source_phase"])
    origin = str(raw_input["validation_origin"])
    model = INTELLIGENCE_SCHEMA_MODELS[collection]

    schema_valid = True
    schema_errors: list[str] = []
    parsed_record: Any | None = None
    try:
        parsed_record = model.model_validate(record)
        payload = parsed_record.model_dump(mode="json")
    except Exception as exc:
        schema_valid = False
        schema_errors = [str(exc)]
        payload = record

    record_id = _record_id(payload, collection)
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    source_chunk_ids = list(metadata.get("source_chunk_ids") or _citation_chunk_ids(payload))
    citation_report = build_citation_coverage_report({collection: [payload]}, chunk_index)
    record_citation = citation_report.records[0] if citation_report.records else None
    citation_valid = bool(record_citation and record_citation.coverage_status == "complete")
    citation_status = record_citation.coverage_status if record_citation else "missing"
    citation_count = record_citation.citation_count if record_citation else 0

    phase5_issues = phase5_issue_map.get((collection, record_id), [])
    reviewer_blockers = [
        *schema_errors,
        *([] if citation_valid else [f"Citation coverage is {citation_status}."]),
        *[f"{issue.code}: {issue.message}" for issue in phase5_issues],
    ]

    if origin == "conflict":
        review_status = ReviewStatus.CONFLICT_DETECTED
    elif origin == "rejected" or reviewer_blockers:
        review_status = ReviewStatus.REJECTED
    else:
        review_status = ReviewStatus.NEEDS_REVIEW

    extraction_method = str(metadata.get("extraction_method") or ExtractionMethod.IMPORTED_TEMPLATE.value)
    confidence = str(metadata.get("confidence") or ConfidenceLevel.LOW.value)
    draft_id = f"{source_phase}:{collection}:{record_id}"

    return DraftReviewRecord(
        draft_id=draft_id,
        collection=collection,
        record_id=record_id,
        source_phase=source_phase,
        extraction_method=extraction_method,
        confidence=confidence,
        review_status=review_status,
        source_chunk_ids=source_chunk_ids,
        citation_count=citation_count,
        citation_coverage_status=citation_status,
        schema_valid=schema_valid,
        citation_valid=citation_valid,
        validation_errors=schema_errors + [issue.message for issue in phase5_issues],
        reviewer_blockers=reviewer_blockers,
        payload=_with_review_status(payload, review_status),
    )


def _summary(
    draft_records: list[DraftReviewRecord],
    rejected_records: list[DraftReviewRecord],
    approved_records: list[dict[str, Any]],
    action_log: list[ReviewActionLogEntry],
    citation_report: dict[str, Any],
) -> dict[str, Any]:
    status_counts = Counter(record.review_status.value for record in draft_records)
    collection_counts = Counter(record.collection for record in draft_records)
    phase_counts = Counter(record.source_phase for record in draft_records)
    return {
        "generatedAt": "2026-06-16T00:00:00Z",
        "draftRecords": len(draft_records),
        "readyForReview": status_counts[ReviewStatus.NEEDS_REVIEW.value],
        "rejectedRecords": len(rejected_records),
        "approvedRecords": len(approved_records),
        "reviewActions": len(action_log),
        "statusCounts": dict(sorted(status_counts.items())),
        "collectionCounts": dict(sorted(collection_counts.items())),
        "sourcePhaseCounts": dict(sorted(phase_counts.items())),
        "citationCoverage": citation_report.get("summary", {}),
        "approvedRecordsPolicy": "Product audit engines must read approved_records only; Phase 6 does not auto-approve extracted drafts.",
    }


def _with_review_status(payload: dict[str, Any], review_status: ReviewStatus) -> dict[str, Any]:
    updated = json.loads(json.dumps(payload))
    metadata = updated.setdefault("metadata", {})
    metadata["review_status"] = review_status.value
    return updated


def _record_id(record: dict[str, Any], collection: str) -> str:
    for key in [
        "term_id",
        "obligation_id",
        "ftl_item_id",
        "cte_id",
        "kde_id",
        "tlc_rule_id",
        "exemption_rule_id",
        "traceability_plan_requirement_id",
        "sortable_export_field_id",
        "scenario_benchmark_id",
        "id",
    ]:
        if record.get(key):
            return str(record[key])
    return f"{collection}:unknown"


def _citation_chunk_ids(record: dict[str, Any]) -> list[str]:
    return sorted({str(citation.get("chunk_id")) for citation in record.get("citations", []) if citation.get("chunk_id")})


def _action(
    *,
    target_id: str,
    action: str,
    reason: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> ReviewActionLogEntry:
    return ReviewActionLogEntry(
        action_id=f"phase6-{action}-{target_id}",
        target_id=target_id,
        action=action,
        actor="system",
        actor_role="validation_worker",
        reason=reason,
        before=before,
        after=after,
        created_at="2026-06-16T00:00:00Z",
    )


def _resolve_artifact_path(anchor_file: Path, artifact_path: str) -> Path:
    candidate = Path(artifact_path)
    if candidate.is_absolute():
        return candidate
    ingestion_relative = anchor_file.parents[3] / candidate
    if ingestion_relative.exists():
        return ingestion_relative
    repo_relative = anchor_file.parents[4] / artifact_path.replace("../", "")
    if repo_relative.exists():
        return repo_relative
    return (anchor_file.parent / artifact_path).resolve()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
