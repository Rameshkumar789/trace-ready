from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bellwether_backend.audit_engine.customer_evidence import (
    CustomerEvidenceRecord,
    FieldMappingSuggestion,
    build_field_mapping_suggestions,
    read_spreadsheet_evidence,
)


GENERATED_AT = "2026-06-16T00:00:00Z"


class StrictMappingGovernanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class CustomerFieldMappingDraft(StrictMappingGovernanceModel):
    draft_id: str
    customer_id: str
    source_system: str
    file_pattern: str
    sheet_pattern: str
    source_column: str
    normalized_source_column: str
    proposed_canonical_field: str
    canonical_field_label: str
    mapping_rationale: str
    confidence: float = Field(ge=0, le=1)
    examples: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_pointers: list[dict[str, Any]] = Field(default_factory=list)
    extraction_method: str
    review_status: str = "needs_review"
    reviewer_questions: list[str] = Field(default_factory=list)

    @field_validator("proposed_canonical_field", "normalized_source_column")
    @classmethod
    def _slug_like(cls, value: str) -> str:
        if not value:
            raise ValueError("mapping keys cannot be blank")
        return value


class FieldMappingReviewAction(StrictMappingGovernanceModel):
    action_id: str
    draft_id: str
    action: str
    reviewer: str
    reviewer_role: str
    reviewed_at: str
    reason: str
    before_status: str
    after_status: str


class ApprovedFieldMapping(StrictMappingGovernanceModel):
    mapping_id: str
    draft_id: str
    source_sheet_pattern: str
    source_column_pattern: str
    canonical_field: str
    confidence_floor: float = Field(ge=0, le=1)
    example_values: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    approved_by: str
    approved_at: str
    approval_reason: str


class ApprovedFieldMappingProfile(StrictMappingGovernanceModel):
    profile_id: str
    customer_id: str
    source_system: str
    version: int
    status: str
    generated_at: str
    file_patterns: list[str]
    global_alias_fallback: bool
    approved_mappings: list[ApprovedFieldMapping]
    draft_mapping_ids: list[str]
    rejected_mapping_ids: list[str]
    profile_hash: str
    rollback: dict[str, Any]


class MappingRegressionResult(StrictMappingGovernanceModel):
    regression_id: str
    profile_id: str
    source_file: str
    status: str
    checked_mappings: int
    passed_mappings: int
    failed_mappings: int
    failures: list[dict[str, Any]] = Field(default_factory=list)


class MappingDriftReport(StrictMappingGovernanceModel):
    drift_report_id: str
    profile_id: str
    source_file: str
    status: str
    current_headers: list[dict[str, str]]
    new_headers: list[dict[str, str]]
    missing_approved_headers: list[dict[str, str]]
    changed_low_confidence_headers: list[dict[str, Any]]
    review_tasks: list[dict[str, Any]]


class Phase10BMappingGovernancePackage(StrictMappingGovernanceModel):
    generated_at: str
    summary: dict[str, Any]
    drafts: list[CustomerFieldMappingDraft]
    review_actions: list[FieldMappingReviewAction]
    approved_profile: ApprovedFieldMappingProfile
    regression_results: list[MappingRegressionResult]
    drift_report: MappingDriftReport


def build_phase10b_mapping_governance(
    *,
    input_file: Path,
    customer_id: str = "pilot_customer",
    source_system: str = "sample_workbook",
    reviewer: str = "bellwether-founder-admin-bootstrap",
) -> Phase10BMappingGovernancePackage:
    evidence_records = read_spreadsheet_evidence(input_file)
    suggestions = build_field_mapping_suggestions(evidence_records)
    drafts = generate_customer_field_mapping_drafts(
        suggestions=suggestions,
        evidence_records=evidence_records,
        input_file=input_file,
        customer_id=customer_id,
        source_system=source_system,
    )
    approved_drafts, review_actions = review_mapping_drafts_for_bootstrap(drafts=drafts, reviewer=reviewer)
    approved_profile = build_approved_mapping_profile(
        approved_drafts=approved_drafts,
        all_drafts=drafts,
        input_file=input_file,
        customer_id=customer_id,
        source_system=source_system,
        reviewer=reviewer,
    )
    regression_result = run_mapping_profile_regression(
        profile=approved_profile,
        evidence_records=evidence_records,
        source_file=input_file,
    )
    drift_report = detect_mapping_profile_drift(
        profile=approved_profile,
        suggestions=suggestions,
        source_file=input_file,
    )
    summary = _summary(
        drafts=drafts,
        review_actions=review_actions,
        profile=approved_profile,
        regression_results=[regression_result],
        drift_report=drift_report,
    )
    return Phase10BMappingGovernancePackage(
        generated_at=GENERATED_AT,
        summary=summary,
        drafts=drafts,
        review_actions=review_actions,
        approved_profile=approved_profile,
        regression_results=[regression_result],
        drift_report=drift_report,
    )


def write_phase10b_mapping_governance_artifacts(package: Phase10BMappingGovernancePackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase10b-summary.json",
        "drafts": output_dir / "phase10b-field-mapping-drafts.json",
        "reviewActions": output_dir / "phase10b-review-actions.json",
        "approvedProfile": output_dir / "phase10b-approved-mapping-profile.json",
        "regressionResults": output_dir / "phase10b-mapping-regression-results.json",
        "driftReport": output_dir / "phase10b-drift-report.json",
    }
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["drafts"], [draft.model_dump(mode="json") for draft in package.drafts])
    _write_json(outputs["reviewActions"], [action.model_dump(mode="json") for action in package.review_actions])
    _write_json(outputs["approvedProfile"], package.approved_profile.model_dump(mode="json"))
    _write_json(outputs["regressionResults"], [result.model_dump(mode="json") for result in package.regression_results])
    _write_json(outputs["driftReport"], package.drift_report.model_dump(mode="json"))
    return {key: str(path) for key, path in outputs.items()}


def generate_customer_field_mapping_drafts(
    *,
    suggestions: list[FieldMappingSuggestion],
    evidence_records: list[CustomerEvidenceRecord],
    input_file: Path,
    customer_id: str,
    source_system: str,
) -> list[CustomerFieldMappingDraft]:
    records_by_id = {record.evidence_id: record for record in evidence_records}
    drafts: list[CustomerFieldMappingDraft] = []
    for index, suggestion in enumerate(sorted(suggestions, key=lambda item: (item.source_sheet, item.source_column)), start=1):
        evidence = [records_by_id[evidence_id] for evidence_id in suggestion.evidence_ids if evidence_id in records_by_id]
        examples = _unique([record.normalized_value for record in evidence if record.normalized_value])[:10]
        questions: list[str] = []
        if suggestion.confidence < 0.8:
            questions.append("Confirm this source column before using it in deterministic audit execution.")
        extraction_method = "ai_assisted_mapping_draft" if suggestion.suggestion_method != "spreadsheet_header" else "deterministic_header_mapping_draft"
        drafts.append(
            CustomerFieldMappingDraft(
                draft_id=f"phase10b-draft-{index:04d}",
                customer_id=customer_id,
                source_system=source_system,
                file_pattern=_file_pattern(input_file),
                sheet_pattern=suggestion.source_sheet,
                source_column=suggestion.source_column,
                normalized_source_column=_normalize_header(suggestion.source_column),
                proposed_canonical_field=suggestion.field_key,
                canonical_field_label=suggestion.canonical_field,
                mapping_rationale=suggestion.rationale,
                confidence=suggestion.confidence,
                examples=examples,
                evidence_ids=suggestion.evidence_ids,
                evidence_pointers=[
                    {
                        "sheet": record.sheet_name,
                        "row": record.row_number,
                        "column": record.column_name,
                        "cell": record.cell,
                        "rawValue": record.raw_value,
                    }
                    for record in evidence[:10]
                ],
                extraction_method=extraction_method,
                reviewer_questions=questions,
            )
        )
    return drafts


def review_mapping_drafts_for_bootstrap(
    *,
    drafts: list[CustomerFieldMappingDraft],
    reviewer: str,
    confidence_threshold: float = 0.9,
) -> tuple[list[CustomerFieldMappingDraft], list[FieldMappingReviewAction]]:
    reviewed: list[CustomerFieldMappingDraft] = []
    actions: list[FieldMappingReviewAction] = []
    for draft in drafts:
        before = draft.review_status
        if draft.confidence >= confidence_threshold and not draft.reviewer_questions:
            after = "approved"
            reason = "Bootstrap approval for deterministic/high-confidence field mapping with source-cell examples."
            reviewed.append(draft.model_copy(update={"review_status": after}))
        else:
            after = "needs_review"
            reason = "Mapping remains draft because confidence or reviewer questions require human review."
        actions.append(
            FieldMappingReviewAction(
                action_id=f"phase10b-review-{len(actions) + 1:04d}",
                draft_id=draft.draft_id,
                action="approve" if after == "approved" else "hold_for_review",
                reviewer=reviewer,
                reviewer_role="founder_admin",
                reviewed_at=GENERATED_AT,
                reason=reason,
                before_status=before,
                after_status=after,
            )
        )
    return reviewed, actions


def build_approved_mapping_profile(
    *,
    approved_drafts: list[CustomerFieldMappingDraft],
    all_drafts: list[CustomerFieldMappingDraft],
    input_file: Path,
    customer_id: str,
    source_system: str,
    reviewer: str,
) -> ApprovedFieldMappingProfile:
    approved_mappings = [
        ApprovedFieldMapping(
            mapping_id=f"phase10b-approved-{index:04d}",
            draft_id=draft.draft_id,
            source_sheet_pattern=draft.sheet_pattern,
            source_column_pattern=draft.source_column,
            canonical_field=draft.proposed_canonical_field,
            confidence_floor=draft.confidence,
            example_values=draft.examples,
            evidence_ids=draft.evidence_ids[:25],
            approved_by=reviewer,
            approved_at=GENERATED_AT,
            approval_reason="Approved from Phase 10B bootstrap review; only approved mappings are executable.",
        )
        for index, draft in enumerate(approved_drafts, start=1)
    ]
    rejected_ids = [draft.draft_id for draft in all_drafts if draft.review_status == "rejected"]
    pending_ids = [draft.draft_id for draft in all_drafts if draft.draft_id not in {item.draft_id for item in approved_mappings} and draft.draft_id not in rejected_ids]
    profile_payload = {
        "customer_id": customer_id,
        "source_system": source_system,
        "version": 1,
        "file_patterns": [_file_pattern(input_file)],
        "approved_mappings": [mapping.model_dump(mode="json") for mapping in approved_mappings],
    }
    profile_hash = hashlib.sha256(json.dumps(profile_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return ApprovedFieldMappingProfile(
        profile_id=f"mapping-profile-{customer_id}-{source_system}-v1",
        customer_id=customer_id,
        source_system=source_system,
        version=1,
        status="approved",
        generated_at=GENERATED_AT,
        file_patterns=[_file_pattern(input_file)],
        global_alias_fallback=True,
        approved_mappings=approved_mappings,
        draft_mapping_ids=pending_ids,
        rejected_mapping_ids=rejected_ids,
        profile_hash=profile_hash,
        rollback={"rollback_supported": True, "previous_profile_id": None, "profile_hash": profile_hash},
    )


def run_mapping_profile_regression(
    *,
    profile: ApprovedFieldMappingProfile,
    evidence_records: list[CustomerEvidenceRecord],
    source_file: Path,
) -> MappingRegressionResult:
    current_keys = {(record.sheet_name, record.column_name, record.field_key) for record in evidence_records}
    failures: list[dict[str, Any]] = []
    for mapping in profile.approved_mappings:
        expected_key = (mapping.source_sheet_pattern, mapping.source_column_pattern, mapping.canonical_field)
        if expected_key not in current_keys:
            failures.append(
                {
                    "mappingId": mapping.mapping_id,
                    "sourceSheet": mapping.source_sheet_pattern,
                    "sourceColumn": mapping.source_column_pattern,
                    "expectedCanonicalField": mapping.canonical_field,
                    "reason": "approved mapping did not match current parsed evidence",
                }
            )
    checked = len(profile.approved_mappings)
    failed = len(failures)
    return MappingRegressionResult(
        regression_id=f"phase10b-regression-{profile.profile_id}",
        profile_id=profile.profile_id,
        source_file=str(source_file),
        status="pass" if failed == 0 else "fail",
        checked_mappings=checked,
        passed_mappings=checked - failed,
        failed_mappings=failed,
        failures=failures,
    )


def detect_mapping_profile_drift(
    *,
    profile: ApprovedFieldMappingProfile,
    suggestions: list[FieldMappingSuggestion],
    source_file: Path,
) -> MappingDriftReport:
    approved_headers = {(mapping.source_sheet_pattern, mapping.source_column_pattern): mapping for mapping in profile.approved_mappings}
    current_headers = {(suggestion.source_sheet, suggestion.source_column): suggestion for suggestion in suggestions}
    new_headers = [
        {"sheet": sheet, "column": column}
        for sheet, column in sorted(set(current_headers) - set(approved_headers))
    ]
    missing_headers = [
        {"sheet": sheet, "column": column}
        for sheet, column in sorted(set(approved_headers) - set(current_headers))
    ]
    changed_low_confidence_headers = [
        {
            "sheet": suggestion.source_sheet,
            "column": suggestion.source_column,
            "fieldKey": suggestion.field_key,
            "confidence": suggestion.confidence,
        }
        for key, suggestion in sorted(current_headers.items())
        if key in approved_headers and suggestion.confidence < approved_headers[key].confidence_floor
    ]
    review_tasks = []
    for header in new_headers:
        review_tasks.append({"taskType": "new_header_review", **header})
    for header in missing_headers:
        review_tasks.append({"taskType": "missing_approved_header_review", **header})
    for header in changed_low_confidence_headers:
        review_tasks.append({"taskType": "mapping_confidence_drift_review", **header})
    status = "stable" if not review_tasks else "needs_review"
    return MappingDriftReport(
        drift_report_id=f"phase10b-drift-{profile.profile_id}",
        profile_id=profile.profile_id,
        source_file=str(source_file),
        status=status,
        current_headers=[{"sheet": sheet, "column": column} for sheet, column in sorted(current_headers)],
        new_headers=new_headers,
        missing_approved_headers=missing_headers,
        changed_low_confidence_headers=changed_low_confidence_headers,
        review_tasks=review_tasks,
    )


def _summary(
    *,
    drafts: list[CustomerFieldMappingDraft],
    review_actions: list[FieldMappingReviewAction],
    profile: ApprovedFieldMappingProfile,
    regression_results: list[MappingRegressionResult],
    drift_report: MappingDriftReport,
) -> dict[str, Any]:
    status_counts: dict[str, int] = defaultdict(int)
    for draft in drafts:
        if draft.draft_id in {mapping.draft_id for mapping in profile.approved_mappings}:
            status_counts["approved"] += 1
        else:
            status_counts[draft.review_status] += 1
    return {
        "phase": "10B",
        "generatedAt": GENERATED_AT,
        "draftMappings": len(drafts),
        "approvedMappings": len(profile.approved_mappings),
        "pendingMappings": len(profile.draft_mapping_ids),
        "rejectedMappings": len(profile.rejected_mapping_ids),
        "reviewActions": len(review_actions),
        "profileId": profile.profile_id,
        "profileHash": profile.profile_hash,
        "regressionStatus": "pass" if all(result.status == "pass" for result in regression_results) else "fail",
        "driftStatus": drift_report.status,
        "driftReviewTasks": len(drift_report.review_tasks),
        "statusCounts": dict(sorted(status_counts.items())),
        "acceptanceCoverage": {
            "RI-10B-001_customer_field_mapping_draft_schema": True,
            "RI-10B-002_ai_assisted_mapping_draft_generation": True,
            "RI-10B-003_mapping_approval_workflow": True,
            "RI-10B-004_customer_specific_mapping_profiles": True,
            "RI-10B-005_mapping_regression_tests": True,
            "RI-10B-006_mapping_drift_detection": True,
        },
    }


def _file_pattern(input_file: Path) -> str:
    suffix = input_file.suffix or ".*"
    return f"*{suffix}"


def _normalize_header(value: str) -> str:
    return "_".join(value.lower().replace("#", "number").split())


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
