from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol

from traceready_backend.backend.repositories.supabase_tables import (
    AuditProjectRepository,
    AuditJobRepository,
    EvidenceItemCreate,
    EvidenceRepository,
    JsonValue,
    ParsedWorkbookCellUpsert,
    ParsedWorkbookRepository,
    ParsedWorkbookRowUpsert,
    ParsedWorkbookSheetUpsert,
    stable_row_id,
)
from traceready_backend.backend.schemas.audit_parse import (
    AuditParseJobPayload,
    AuditParseJobResult,
    ParseIssue,
)
from traceready_backend.audit_engine.customer_evidence import (
    CustomerEvidenceRecord,
    read_spreadsheet_evidence,
)
from traceready_backend.storage.artifacts import ObjectStore


logger = logging.getLogger("traceready.api")


class AuditParseRepositories(Protocol):
    audit_jobs: AuditJobRepository
    audit_projects: AuditProjectRepository
    evidence: EvidenceRepository
    parsed_workbook: ParsedWorkbookRepository


def run_audit_parse_job(
    *,
    payload: AuditParseJobPayload,
    object_store: ObjectStore,
    repositories: AuditParseRepositories,
) -> AuditParseJobResult:
    repositories.audit_jobs.append_event(
        audit_job_id=payload.job_id,
        audit_project_id=payload.audit_project_id,
        audit_run_id=payload.audit_run_id,
        event_type="parse_started",
        message="Customer workbook parse job started.",
        payload_json=payload.model_dump(mode="json"),
    )
    repositories.audit_jobs.checkpoint_job(
        payload.job_id,
        {
            "stage": "downloading",
            "auditFileId": payload.audit_file_id,
            "storageBucket": payload.storage_bucket,
            "storageKey": payload.storage_key,
        },
    )

    try:
        _log_parse_stage(payload, "parse_download_started")
        stored_payload = object_store.download_bytes(
            bucket=payload.storage_bucket,
            key=payload.storage_key,
        )
        _log_parse_stage(
            payload,
            "parse_download_completed",
            size_bytes=stored_payload.size_bytes,
        )
        repositories.audit_jobs.checkpoint_job(
            payload.job_id,
            {
                "stage": "downloaded",
                "sizeBytes": stored_payload.size_bytes,
                "sha256": stored_payload.sha256,
                "contentType": stored_payload.content_type,
            },
        )

        with TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / _safe_input_filename(payload.original_file_name)
            input_path.write_bytes(stored_payload.data)
            _log_parse_stage(payload, "spreadsheet_parse_started", file_name=input_path.name)
            repositories.audit_jobs.checkpoint_job(
                payload.job_id,
                {"stage": "parsing", "fileName": input_path.name},
            )
            evidence_records = read_spreadsheet_evidence(input_path)
            _log_parse_stage(
                payload,
                "spreadsheet_parse_completed",
                evidence_record_count=len(evidence_records),
            )

        _log_parse_stage(payload, "evidence_persist_started", evidence_record_count=len(evidence_records))
        repositories.audit_jobs.checkpoint_job(
            payload.job_id,
            {"stage": "persisting_evidence", "evidenceRecordCount": len(evidence_records)},
        )
        persisted = repositories.evidence.create_items(
            [_to_evidence_item(payload, record) for record in evidence_records]
        )
        _log_parse_stage(payload, "evidence_persist_completed", evidence_record_count=len(persisted))
        sheets, rows, cells = _to_parsed_workbook_records(payload, evidence_records)
        _log_parse_stage(
            payload,
            "parsed_workbook_persist_started",
            sheet_count=len(sheets),
            row_count=len(rows),
            cell_count=len(cells),
        )
        persisted_sheets = repositories.parsed_workbook.upsert_sheets(sheets)
        persisted_rows = repositories.parsed_workbook.upsert_rows(rows)
        persisted_cells = repositories.parsed_workbook.upsert_cells(cells)
        _log_parse_stage(
            payload,
            "parsed_workbook_persist_completed",
            sheet_count=len(persisted_sheets),
            row_count=len(persisted_rows),
            cell_count=len(persisted_cells),
        )
        summary = _build_dataset_snapshot(payload, evidence_records, stored_payload.sha256)
        _log_parse_stage(payload, "audit_project_snapshot_update_started")
        repositories.audit_projects.update_dataset_snapshot(
            audit_project_id=payload.audit_project_id,
            dataset_json=summary,
        )
        repositories.audit_projects.update_parse_errors(
            audit_project_id=payload.audit_project_id,
            parse_errors=[],
        )
        _log_parse_stage(payload, "audit_project_snapshot_update_completed")

        checkpoint = {
            "stage": "completed",
            "parserVersion": payload.parser_version,
            "evidenceRecordCount": len(evidence_records),
            "persistedEvidenceCount": len(persisted),
            "parsedSheetCount": len(persisted_sheets),
            "parsedRowCount": len(persisted_rows),
            "parsedCellCount": len(persisted_cells),
            "sourceSha256": stored_payload.sha256,
        }
        repositories.audit_jobs.complete_job(payload.job_id, checkpoint)
        repositories.audit_jobs.append_event(
            audit_job_id=payload.job_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            event_type="parse_completed",
            message="Customer workbook parse job completed.",
            payload_json=checkpoint,
        )
        _log_parse_stage(payload, "parse_job_completed", evidence_record_count=len(evidence_records))
        return AuditParseJobResult(
            job_id=payload.job_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            audit_file_id=payload.audit_file_id,
            parser_version=payload.parser_version,
            status="succeeded",
            evidence_record_count=len(evidence_records),
            persisted_evidence_count=len(persisted),
            checkpoint=checkpoint,
        )
    except Exception as exc:
        _log_parse_stage(
            payload,
            "parse_job_failed",
            status="failed",
            error_type=exc.__class__.__name__,
        )
        issue = ParseIssue(
            scope="file",
            error_type=exc.__class__.__name__,
            message=str(exc),
        )
        parse_errors = [issue.model_dump(mode="json")]
        error_payload: dict[str, JsonValue] = {
            "stage": "failed",
            "parserVersion": payload.parser_version,
            "parseErrors": parse_errors,
        }
        repositories.audit_projects.update_parse_errors(
            audit_project_id=payload.audit_project_id,
            parse_errors=parse_errors,
        )
        repositories.audit_jobs.fail_job(
            payload.job_id,
            failure_category="parse_error",
            error_json=error_payload,
            retryable=False,
        )
        repositories.audit_jobs.append_event(
            audit_job_id=payload.job_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            event_type="parse_failed",
            message="Customer workbook parse job failed.",
            payload_json=error_payload,
        )
        return AuditParseJobResult(
            job_id=payload.job_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            audit_file_id=payload.audit_file_id,
            parser_version=payload.parser_version,
            status="failed",
            parse_errors=[issue],
            checkpoint=error_payload,
        )


def _log_parse_stage(payload: AuditParseJobPayload, stage: str, **fields: object) -> None:
    logger.info(
        "Audit parse stage",
        extra={
            "stage": stage,
            "job_id": payload.job_id,
            "job_type": "parse_customer_workbook",
            "audit_project_id": payload.audit_project_id,
            "audit_run_id": payload.audit_run_id,
            "audit_file_id": payload.audit_file_id,
            **{key: value for key, value in fields.items() if value is not None},
        },
    )


def _safe_input_filename(filename: str) -> str:
    safe = Path(filename).name.replace("\\", "-").replace("/", "-")
    if not safe:
        return "customer-upload.csv"
    return safe


def _to_evidence_item(
    payload: AuditParseJobPayload,
    record: CustomerEvidenceRecord,
) -> EvidenceItemCreate:
    return EvidenceItemCreate(
        id=_scoped_evidence_id(payload, record),
        audit_project_id=payload.audit_project_id,
        audit_run_id=payload.audit_run_id,
        audit_file_id=payload.audit_file_id,
        evidence_type="customer_workbook_cell",
        canonical_field=record.field_key,
        source_sheet=record.sheet_name,
        source_row_number=record.row_number,
        source_column=record.column_name,
        raw_value=record.raw_value,
        normalized_value=record.normalized_value,
        confidence=record.confidence,
        review_status="unreviewed",
        metadata_json={
            "uploadedFile": record.uploaded_file,
            "sourceEvidenceId": record.evidence_id,
            "cell": record.cell,
            "columnIndex": record.column_index,
            "fieldType": record.field_type,
            "extractionMethod": record.extraction_method,
            "sourcePointer": record.source_pointer.model_dump(mode="json"),
            "parserVersion": payload.parser_version,
        },
    )


def _scoped_evidence_id(payload: AuditParseJobPayload, record: CustomerEvidenceRecord) -> str:
    return stable_row_id("evidence", payload.audit_file_id, record.evidence_id)


def _to_parsed_workbook_records(
    payload: AuditParseJobPayload,
    evidence_records: list[CustomerEvidenceRecord],
) -> tuple[list[ParsedWorkbookSheetUpsert], list[ParsedWorkbookRowUpsert], list[ParsedWorkbookCellUpsert]]:
    by_sheet: dict[str, list[CustomerEvidenceRecord]] = defaultdict(list)
    by_row: dict[tuple[str, int], list[CustomerEvidenceRecord]] = defaultdict(list)
    for record in evidence_records:
        by_sheet[record.sheet_name].append(record)
        by_row[(record.sheet_name, record.row_number)].append(record)

    sheets: list[ParsedWorkbookSheetUpsert] = []
    rows: list[ParsedWorkbookRowUpsert] = []
    cells: list[ParsedWorkbookCellUpsert] = []
    sheet_ids: dict[str, str] = {}
    row_ids: dict[tuple[str, int], str] = {}

    for sheet_index, (sheet_name, records) in enumerate(sorted(by_sheet.items()), start=1):
        sheet_id = stable_row_id("parsed_sheet", payload.audit_file_id, sheet_name)
        sheet_ids[sheet_name] = sheet_id
        row_numbers = {record.row_number for record in records}
        column_names = {record.column_name for record in records}
        sheets.append(
            ParsedWorkbookSheetUpsert(
                id=sheet_id,
                audit_project_id=payload.audit_project_id,
                audit_run_id=payload.audit_run_id,
                audit_file_id=payload.audit_file_id,
                sheet_name=sheet_name,
                sheet_index=sheet_index,
                row_count=len(row_numbers),
                column_count=len(column_names),
                parser_version=payload.parser_version,
                metadata_json={
                    "derivedFromEvidenceRecords": True,
                    "uploadedFile": payload.original_file_name,
                },
            )
        )

    for (sheet_name, row_number), records in sorted(by_row.items()):
        sheet_id = sheet_ids[sheet_name]
        row_id = stable_row_id("parsed_row", payload.audit_file_id, sheet_name, row_number)
        row_ids[(sheet_name, row_number)] = row_id
        sorted_records = sorted(records, key=lambda record: (record.column_index, record.column_name))
        raw_cells = [
            {
                "columnName": record.column_name,
                "columnIndex": record.column_index,
                "cell": record.cell,
                "rawValue": record.raw_value,
            }
            for record in sorted_records
        ]
        normalized_cells = [
            {
                "canonicalField": record.field_key,
                "columnName": record.column_name,
                "normalizedValue": record.normalized_value,
                "confidence": record.confidence,
                "evidenceId": _scoped_evidence_id(payload, record),
            }
            for record in sorted_records
        ]
        rows.append(
            ParsedWorkbookRowUpsert(
                id=row_id,
                audit_project_id=payload.audit_project_id,
                audit_run_id=payload.audit_run_id,
                audit_file_id=payload.audit_file_id,
                sheet_id=sheet_id,
                sheet_name=sheet_name,
                source_row_number=row_number,
                source_row_key=f"{payload.original_file_name}:{sheet_name}:row:{row_number}",
                raw_row_json={"cells": raw_cells},
                normalized_row_json={"cells": normalized_cells},
                metadata_json={
                    "derivedFromEvidenceRecords": True,
                    "evidenceIds": [_scoped_evidence_id(payload, record) for record in sorted_records],
                },
            )
        )

    for record in sorted(evidence_records, key=lambda item: (item.sheet_name, item.row_number, item.column_index, item.column_name)):
        sheet_id = sheet_ids[record.sheet_name]
        row_id = row_ids[(record.sheet_name, record.row_number)]
        cells.append(
            ParsedWorkbookCellUpsert(
                id=stable_row_id(
                    "parsed_cell",
                    payload.audit_file_id,
                    record.sheet_name,
                    record.row_number,
                    record.column_name,
                ),
                audit_project_id=payload.audit_project_id,
                audit_run_id=payload.audit_run_id,
                audit_file_id=payload.audit_file_id,
                sheet_id=sheet_id,
                row_id=row_id,
                sheet_name=record.sheet_name,
                source_row_number=record.row_number,
                source_column=record.column_name,
                source_column_index=record.column_index,
                cell_address=record.cell,
                raw_value=record.raw_value,
                normalized_value=record.normalized_value,
                canonical_field=record.field_key,
                evidence_item_id=_scoped_evidence_id(payload, record),
                parser_version=payload.parser_version,
                metadata_json={
                    "fieldType": record.field_type,
                    "extractionMethod": record.extraction_method,
                    "sourcePointer": record.source_pointer.model_dump(mode="json"),
                },
            )
        )

    return sheets, rows, cells


def _build_dataset_snapshot(
    payload: AuditParseJobPayload,
    evidence_records: list[CustomerEvidenceRecord],
    source_sha256: str,
) -> dict[str, Any]:
    sheets = sorted({record.sheet_name for record in evidence_records})
    fields = sorted({record.field_key for record in evidence_records})
    return {
        "parserVersion": payload.parser_version,
        "source": {
            "auditFileId": payload.audit_file_id,
            "storageBucket": payload.storage_bucket,
            "storageKey": payload.storage_key,
            "fileName": payload.original_file_name,
            "sha256": source_sha256,
        },
        "recordCounts": {
            "evidenceRecords": len(evidence_records),
            "sheets": len(sheets),
            "canonicalFields": len(fields),
            "parsedRows": len({(record.sheet_name, record.row_number) for record in evidence_records}),
            "parsedCells": len(evidence_records),
        },
        "sheets": sheets,
        "canonicalFields": fields,
    }
