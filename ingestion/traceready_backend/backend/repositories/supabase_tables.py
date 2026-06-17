from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4


JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
JSONB_COLUMN_NAMES = {
    "source_chunk_ids",
    "validation_errors",
    "reviewer_blockers",
    "payload",
}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def stable_row_id(prefix: str, *parts: object) -> str:
    raw = "|".join("" if part is None else str(part) for part in parts)
    return f"{prefix}_{sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _drop_none(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}


def _jsonb(value: JsonValue) -> Any:
    if value is None:
        return None
    try:
        from psycopg.types.json import Jsonb
    except ModuleNotFoundError:
        return value
    return Jsonb(value)


def _prepare_row(row: Mapping[str, Any]) -> dict[str, Any]:
    prepared: dict[str, Any] = {}
    for key, value in row.items():
        if key.endswith("_json") or key.endswith("_jsonb") or key in JSONB_COLUMN_NAMES:
            prepared[key] = _jsonb(value)
        else:
            prepared[key] = value
    return prepared


def _insert_sql(table: str, row: Mapping[str, Any], returning: str = "*") -> tuple[str, list[Any]]:
    prepared = _prepare_row(_drop_none(row))
    columns = list(prepared)
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    sql = f"insert into public.{table} ({column_sql}) values ({placeholders}) returning {returning}"
    return sql, [prepared[column] for column in columns]


def _upsert_sql(
    table: str,
    row: Mapping[str, Any],
    conflict_columns: Sequence[str],
    update_columns: Sequence[str] | None = None,
    returning: str = "*",
) -> tuple[str, list[Any]]:
    prepared = _prepare_row(_drop_none(row))
    columns = list(prepared)
    conflict_sql = ", ".join(conflict_columns)
    update_targets = list(update_columns or [column for column in columns if column not in conflict_columns])
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    if update_targets:
        update_sql = ", ".join(f"{column} = excluded.{column}" for column in update_targets)
        sql = (
            f"insert into public.{table} ({column_sql}) values ({placeholders}) "
            f"on conflict ({conflict_sql}) do update set {update_sql} returning {returning}"
        )
    else:
        sql = (
            f"insert into public.{table} ({column_sql}) values ({placeholders}) "
            f"on conflict ({conflict_sql}) do nothing returning {returning}"
        )
    return sql, [prepared[column] for column in columns]


@dataclass(frozen=True)
class AuditJobCreate:
    audit_project_id: str
    job_type: str
    id: str = field(default_factory=lambda: _new_id("job"))
    audit_run_id: str | None = None
    audit_file_id: str | None = None
    status: str = "queued"
    priority: int = 100
    max_attempts: int = 3
    available_at: datetime | None = None
    checkpoint_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditFileCreate:
    audit_project_id: str
    file_name: str
    file_type: str
    storage_bucket: str
    storage_key: str
    id: str = field(default_factory=lambda: _new_id("file"))
    audit_run_id: str | None = None
    content_type: str | None = None
    file_hash: str | None = None
    size_bytes: int | None = None
    uploaded_by_user_id: str | None = None
    status: str = "uploaded"
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditArtifactCreate:
    audit_project_id: str
    artifact_type: str
    file_name: str
    content_type: str
    storage_bucket: str
    storage_key: str
    id: str = field(default_factory=lambda: _new_id("artifact"))
    audit_run_id: str | None = None
    size_bytes: int | None = None
    artifact_hash: str | None = None
    status: str = "available"
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceItemCreate:
    audit_project_id: str
    evidence_type: str
    id: str = field(default_factory=lambda: _new_id("evidence"))
    audit_run_id: str | None = None
    audit_file_id: str | None = None
    canonical_field: str | None = None
    source_sheet: str | None = None
    source_row_number: int | None = None
    source_column: str | None = None
    raw_value: str | None = None
    normalized_value: str | None = None
    confidence: float | None = None
    review_status: str = "unreviewed"
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedWorkbookSheetUpsert:
    id: str
    audit_project_id: str
    audit_file_id: str
    sheet_name: str
    audit_run_id: str | None = None
    sheet_index: int | None = None
    header_row_number: int | None = None
    row_count: int = 0
    column_count: int = 0
    parser_version: str | None = None
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedWorkbookRowUpsert:
    id: str
    audit_project_id: str
    audit_file_id: str
    sheet_id: str
    sheet_name: str
    source_row_number: int
    source_row_key: str
    audit_run_id: str | None = None
    row_kind: str = "data"
    raw_row_json: JsonValue = None
    normalized_row_json: JsonValue = None
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedWorkbookCellUpsert:
    id: str
    audit_project_id: str
    audit_file_id: str
    sheet_id: str
    row_id: str
    sheet_name: str
    source_row_number: int
    source_column: str
    audit_run_id: str | None = None
    source_column_index: int | None = None
    cell_address: str | None = None
    raw_value: str | None = None
    normalized_value: str | None = None
    canonical_field: str | None = None
    evidence_item_id: str | None = None
    parser_version: str | None = None
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditFindingCreate:
    audit_project_id: str
    title: str
    severity: str
    finding_type: str
    recommendation: str
    review_state: str
    id: str = field(default_factory=lambda: _new_id("finding"))
    audit_run_id: str | None = None
    status: str = "open"
    event_id: str | None = None
    event_line_id: str | None = None
    field_or_kde: str | None = None
    observed_value: str | None = None
    expected_or_required: str | None = None
    rule_card_id: str | None = None
    rule_card_version: int | None = None
    approved_record_id: str | None = None
    approved_obligation_id: str | None = None
    source_chunk_id: str | None = None
    kde_requirement_id: str | None = None
    rule_package_id: str | None = None
    rule_package_version: int | None = None
    check_code: str | None = None
    check_version: str | None = None
    evidence_refs_json: JsonValue = None
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FindingTraceCreate:
    finding_id: str
    sequence: int
    trace_type: str
    title: str
    payload_json: JsonValue
    audit_run_id: str | None = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegulatorySourceUpsert:
    id: str
    title: str
    source_type: str
    source_status: str
    authority_rank: str
    url: str
    citation: str
    retrieved_at: datetime
    text_hash: str
    published_date: datetime | None = None
    effective_date: datetime | None = None
    compliance_date: datetime | None = None
    is_finalized: bool = False
    raw_artifact_bucket: str | None = None
    raw_artifact_key: str | None = None
    normalized_artifact_bucket: str | None = None
    normalized_artifact_key: str | None = None
    summary: str | None = None
    notes: str | None = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceChunkUpsert:
    id: str
    regulatory_source_id: str
    chunk_code: str
    section_label: str
    source_location: str
    text: str
    summary: str
    citation: str
    text_hash: str
    status: str
    source_version_id: str | None = None
    section_ref: str | None = None
    page_number: int | None = None
    citation_anchor: str | None = None
    authority_rank: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    raw_artifact_bucket: str | None = None
    raw_artifact_key: str | None = None
    normalized_artifact_bucket: str | None = None
    normalized_artifact_key: str | None = None
    usage_role: str = "extraction"
    quality_flags_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RegulatoryDraftRecordUpsert:
    id: str
    collection: str
    record_id: str
    source_phase: str
    extraction_method: str
    confidence: str
    review_status: str
    source_chunk_ids_json: JsonValue
    citation_count: int
    citation_coverage_status: str
    schema_valid: bool
    citation_valid: bool
    validation_errors_json: JsonValue
    reviewer_blockers_json: JsonValue
    payload_json: JsonValue

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["source_chunk_ids"] = row.pop("source_chunk_ids_json")
        row["validation_errors"] = row.pop("validation_errors_json")
        row["reviewer_blockers"] = row.pop("reviewer_blockers_json")
        row["payload"] = row.pop("payload_json")
        return row


@dataclass(frozen=True)
class SourceIngestionJobCreate:
    source_type: str
    job_type: str
    id: str = field(default_factory=lambda: _new_id("source_job"))
    regulatory_source_id: str | None = None
    source_url: str | None = None
    status: str = "queued"
    max_attempts: int = 3
    checkpoint_json: JsonValue = None
    created_by: str | None = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedBusinessObjectUpsert:
    id: str
    audit_project_id: str
    object_type: str
    object_key: str
    name: str
    audit_run_id: str | None = None
    normalized_name: str | None = None
    confidence: float | None = None
    review_status: str = "unreviewed"
    attributes_json: JsonValue = None
    evidence_ids_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedEventUpsert:
    id: str
    audit_project_id: str
    source_row_key: str
    audit_run_id: str | None = None
    audit_file_id: str | None = None
    event_type_claim: str | None = None
    event_datetime: datetime | None = None
    event_datetime_raw: str | None = None
    actor_object_id: str | None = None
    product_object_id: str | None = None
    lot_object_id: str | None = None
    source_lot_object_id: str | None = None
    output_lot_object_id: str | None = None
    from_object_id: str | None = None
    to_object_id: str | None = None
    document_object_id: str | None = None
    destination_type: str | None = None
    action_terms_json: JsonValue = None
    classified_ctes_json: JsonValue = None
    suppressed_ctes_json: JsonValue = None
    reviewer_questions_json: JsonValue = None
    confidence: float | None = None
    review_status: str = "unreviewed"
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedEventEvidenceRefCreate:
    normalized_event_id: str
    evidence_item_id: str
    role: str = "source_cell"

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedKdeValueCreate:
    id: str
    audit_project_id: str
    kde_key: str
    audit_run_id: str | None = None
    normalized_event_id: str | None = None
    evidence_item_id: str | None = None
    kde_label: str | None = None
    raw_value: str | None = None
    normalized_value: str | None = None
    confidence: float | None = None
    review_status: str = "unreviewed"
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TlcLineageLinkCreate:
    id: str
    audit_project_id: str
    link_type: str
    audit_run_id: str | None = None
    normalized_event_id: str | None = None
    source_tlc: str | None = None
    output_tlc: str | None = None
    confidence: float | None = None
    review_status: str = "unreviewed"
    evidence_ids_json: JsonValue = None
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedReviewItemCreate:
    id: str
    audit_project_id: str
    review_type: str
    question: str
    reason: str
    severity: str
    audit_run_id: str | None = None
    normalized_event_id: str | None = None
    normalized_kde_value_id: str | None = None
    business_object_id: str | None = None
    status: str = "needs_review"
    evidence_ids_json: JsonValue = None
    metadata_json: JsonValue = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


class SupabaseTableRepository:
    def __init__(self, connection: Any, *, auto_commit: bool = True):
        self.connection = connection
        self.auto_commit = auto_commit

    def _fetch_one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, list(params))
            return cursor.fetchone()

    def _fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, list(params))
            return list(cursor.fetchall())

    def _execute_returning(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        row = self._fetch_one(sql, params)
        self._commit_if_needed()
        return row

    def _execute_many_returning(
        self, statements: Iterable[tuple[str, Sequence[Any]]]
    ) -> list[dict[str, Any]]:
        # Batch by identical SQL so each group runs as ONE pipelined executemany round-trip
        # instead of one network round-trip per row. Persisting a real workbook can be
        # hundreds of rows; per-row execution turned that into tens of seconds. _upsert_sql
        # drops None columns, so different rows may produce different SQL — grouping by the
        # exact SQL string keeps each executemany batch homogeneous. Return order is
        # preserved to match the previous per-statement behaviour.
        prepared = [(sql, list(params)) for sql, params in statements]
        if not prepared:
            return []
        groups: dict[str, list[int]] = {}
        for index, (sql, _params) in enumerate(prepared):
            groups.setdefault(sql, []).append(index)
        results_by_index: dict[int, list[dict[str, Any]]] = {}
        with self.connection.cursor() as cursor:
            for sql, indices in groups.items():
                if len(indices) == 1:
                    cursor.execute(sql, prepared[indices[0]][1])
                    results_by_index[indices[0]] = list(cursor.fetchall()) if cursor.description else []
                    continue
                cursor.executemany(sql, [prepared[i][1] for i in indices], returning=True)
                position = 0
                while True:
                    if position < len(indices):
                        results_by_index[indices[position]] = list(cursor.fetchall()) if cursor.description else []
                    position += 1
                    if not cursor.nextset():
                        break
        self._commit_if_needed()
        rows: list[dict[str, Any]] = []
        for index in range(len(prepared)):
            rows.extend(results_by_index.get(index, []))
        return rows

    def _commit_if_needed(self) -> None:
        if self.auto_commit and hasattr(self.connection, "commit"):
            self.connection.commit()


class AuditJobRepository(SupabaseTableRepository):
    def create_job(self, job: AuditJobCreate) -> dict[str, Any] | None:
        sql, params = _insert_sql("audit_jobs", job.to_row())
        return self._execute_returning(sql, params)

    def claim_next_job(
        self,
        worker_id: str,
        job_types: Sequence[str],
        *,
        stale_lock_minutes: int = 15,
    ) -> dict[str, Any] | None:
        sql = """
        update public.audit_jobs
        set status = 'running',
            locked_by = %s,
            locked_at = now(),
            started_at = coalesce(started_at, now()),
            attempt_count = attempt_count + 1
        where id = (
          select id
          from public.audit_jobs
          where (
              status in ('queued', 'retryable')
              or (
                status = 'running'
                and locked_at is not null
                and locked_at < now() - (%s * interval '1 minute')
              )
            )
            and available_at <= now()
            and job_type = any(%s)
            and attempt_count < max_attempts
          order by priority asc, available_at asc, created_at asc
          for update skip locked
          limit 1
        )
        returning *
        """
        return self._execute_returning(sql, [worker_id, stale_lock_minutes, list(job_types)])

    def checkpoint_job(self, job_id: str, checkpoint_json: JsonValue) -> dict[str, Any] | None:
        sql = """
        update public.audit_jobs
        set checkpoint_json = %s
        where id = %s
        returning *
        """
        return self._execute_returning(sql, [_jsonb(checkpoint_json), job_id])

    def complete_job(self, job_id: str, checkpoint_json: JsonValue | None = None) -> dict[str, Any] | None:
        sql = """
        update public.audit_jobs
        set status = 'succeeded',
            completed_at = now(),
            locked_by = null,
            locked_at = null,
            checkpoint_json = coalesce(%s, checkpoint_json)
        where id = %s
        returning *
        """
        return self._execute_returning(sql, [_jsonb(checkpoint_json), job_id])

    def fail_job(
        self,
        job_id: str,
        *,
        failure_category: str,
        error_json: JsonValue,
        retryable: bool,
    ) -> dict[str, Any] | None:
        next_status = "retryable" if retryable else "failed"
        sql = """
        update public.audit_jobs
        set status = %s,
            failure_category = %s,
            error_json = %s,
            available_at = case when %s then now() + interval '5 minutes' else available_at end,
            locked_by = null,
            locked_at = null
        where id = %s
        returning *
        """
        return self._execute_returning(
            sql, [next_status, failure_category, _jsonb(error_json), retryable, job_id]
        )

    def retry_job(
        self,
        job_id: str,
        *,
        requested_by: str,
        reason: str,
    ) -> dict[str, Any] | None:
        sql = """
        update public.audit_jobs
        set status = 'retryable',
            failure_category = null,
            error_json = null,
            locked_by = null,
            locked_at = null,
            available_at = now(),
            checkpoint_json = jsonb_set(
              coalesce(checkpoint_json, '{}'::jsonb),
              '{manualRetry}',
              %s::jsonb,
              true
            )
        where id = %s
          and status in ('failed', 'retryable')
          and attempt_count < max_attempts
        returning *
        """
        return self._execute_returning(
            sql,
            [
                _jsonb(
                    {
                        "requestedBy": requested_by,
                        "reason": reason,
                    }
                ),
                job_id,
            ],
        )

    def append_event(
        self,
        *,
        audit_job_id: str,
        event_type: str,
        audit_project_id: str | None = None,
        audit_run_id: str | None = None,
        message: str | None = None,
        payload_json: JsonValue = None,
    ) -> dict[str, Any] | None:
        row = {
            "audit_job_id": audit_job_id,
            "audit_project_id": audit_project_id,
            "audit_run_id": audit_run_id,
            "event_type": event_type,
            "message": message,
            "payload_json": payload_json,
        }
        sql, params = _insert_sql("audit_job_events", row)
        return self._execute_returning(sql, params)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select *
            from public.audit_jobs
            where id = %s
            """,
            [job_id],
        )

    def list_for_project(self, audit_project_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select *
            from public.audit_jobs
            where audit_project_id = %s
            order by created_at desc
            limit %s
            """,
            [audit_project_id, limit],
        )

    def list_events(self, job_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select *
            from public.audit_job_events
            where audit_job_id = %s
            order by created_at desc
            limit %s
            """,
            [job_id, limit],
        )


class AuditProjectRepository(SupabaseTableRepository):
    def update_status(self, *, audit_project_id: str, status: str) -> dict[str, Any] | None:
        sql = """
        update public.audit_projects
        set status = %s
        where id = %s
        returning *
        """
        return self._execute_returning(sql, [status, audit_project_id])

    def update_parse_errors(
        self, *, audit_project_id: str, parse_errors: JsonValue
    ) -> dict[str, Any] | None:
        sql = """
        update public.audit_projects
        set parse_errors = %s
        where id = %s
        returning *
        """
        return self._execute_returning(sql, [_jsonb(parse_errors), audit_project_id])

    def update_dataset_snapshot(
        self, *, audit_project_id: str, dataset_json: JsonValue
    ) -> dict[str, Any] | None:
        sql = """
        update public.audit_projects
        set dataset_json = %s
        where id = %s
        returning *
        """
        return self._execute_returning(sql, [_jsonb(dataset_json), audit_project_id])


class AuditRunRepository(SupabaseTableRepository):
    def update_rule_execution_summary(
        self,
        *,
        audit_run_id: str,
        status: str,
        rule_package_id: str,
        rule_package_version: int,
        rule_package_hash: str | None,
        summary_json: JsonValue,
    ) -> dict[str, Any] | None:
        sql = """
        update public.audit_runs
        set status = %s,
            rule_package_id = %s,
            rule_package_version = %s,
            rule_package_hash = %s,
            summary_json = %s,
            completed_at = case when %s in ('succeeded', 'completed') then coalesce(completed_at, now()) else completed_at end
        where id = %s
        returning *
        """
        return self._execute_returning(
            sql,
            [
                status,
                rule_package_id,
                rule_package_version,
                rule_package_hash,
                _jsonb(summary_json),
                status,
                audit_run_id,
            ],
        )


class AuditFileRepository(SupabaseTableRepository):
    def create_file(self, file_record: AuditFileCreate) -> dict[str, Any] | None:
        sql, params = _insert_sql("audit_files", file_record.to_row())
        return self._execute_returning(sql, params)

    def create_artifact(self, artifact: AuditArtifactCreate) -> dict[str, Any] | None:
        sql, params = _upsert_sql("audit_artifacts", artifact.to_row(), ["id"])
        return self._execute_returning(sql, params)

    def list_artifacts(
        self,
        *,
        audit_project_id: str,
        audit_run_id: str | None = None,
        artifact_types: Sequence[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params: list[Any] = [audit_project_id]
        filters = ["audit_project_id = %s"]
        if audit_run_id:
            filters.append("audit_run_id = %s")
            params.append(audit_run_id)
        if artifact_types:
            filters.append("artifact_type = any(%s)")
            params.append(list(artifact_types))
        params.append(limit)
        return self._fetch_all(
            f"""
            select *
            from public.audit_artifacts
            where {' and '.join(filters)}
            order by created_at desc
            limit %s
            """,
            params,
        )


class EvidenceRepository(SupabaseTableRepository):
    def create_items(self, evidence_items: Sequence[EvidenceItemCreate]) -> list[dict[str, Any]]:
        statements = [_upsert_sql("evidence_items", item.to_row(), ["id"]) for item in evidence_items]
        return self._execute_many_returning(statements)

    def list_for_run(self, audit_run_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select *
            from public.evidence_items
            where audit_run_id = %s
            order by source_sheet asc nulls last, source_row_number asc nulls last, created_at asc
            """,
            [audit_run_id],
        )


class ParsedWorkbookRepository(SupabaseTableRepository):
    def upsert_sheets(self, sheets: Sequence[ParsedWorkbookSheetUpsert]) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql(
                "parsed_workbook_sheets",
                sheet.to_row(),
                ["audit_file_id", "sheet_name"],
            )
            for sheet in sheets
        ]
        return self._execute_many_returning(statements)

    def upsert_rows(self, rows: Sequence[ParsedWorkbookRowUpsert]) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql(
                "parsed_workbook_rows",
                row.to_row(),
                ["audit_file_id", "sheet_name", "source_row_number"],
            )
            for row in rows
        ]
        return self._execute_many_returning(statements)

    def upsert_cells(self, cells: Sequence[ParsedWorkbookCellUpsert]) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql(
                "parsed_workbook_cells",
                cell.to_row(),
                ["audit_file_id", "sheet_name", "source_row_number", "source_column"],
            )
            for cell in cells
        ]
        return self._execute_many_returning(statements)


class NormalizedEvidenceRepository(SupabaseTableRepository):
    def upsert_business_objects(
        self, objects: Sequence[NormalizedBusinessObjectUpsert]
    ) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql("normalized_business_objects", item.to_row(), ["id"])
            for item in objects
        ]
        return self._execute_many_returning(statements)

    def upsert_events(self, events: Sequence[NormalizedEventUpsert]) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql("normalized_events", item.to_row(), ["id"])
            for item in events
        ]
        return self._execute_many_returning(statements)

    def create_event_evidence_refs(
        self, refs: Sequence[NormalizedEventEvidenceRefCreate]
    ) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql(
                "normalized_event_evidence_refs",
                ref.to_row(),
                ["normalized_event_id", "evidence_item_id", "role"],
            )
            for ref in refs
        ]
        return self._execute_many_returning(statements)

    def create_kde_values(self, values: Sequence[NormalizedKdeValueCreate]) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql("normalized_kde_values", value.to_row(), ["id"])
            for value in values
        ]
        return self._execute_many_returning(statements)

    def create_tlc_lineage_links(
        self, links: Sequence[TlcLineageLinkCreate]
    ) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql("tlc_lineage_links", link.to_row(), ["id"])
            for link in links
        ]
        return self._execute_many_returning(statements)

    def create_review_items(
        self, items: Sequence[NormalizedReviewItemCreate]
    ) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql("normalized_review_items", item.to_row(), ["id"])
            for item in items
        ]
        return self._execute_many_returning(statements)


class FindingRepository(SupabaseTableRepository):
    def delete_for_run(self, audit_run_id: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                delete from public.finding_evidence_refs
                where finding_id in (
                  select id from public.audit_findings where audit_run_id = %s
                )
                """,
                [audit_run_id],
            )
            cursor.execute(
                """
                delete from public.finding_traces
                where finding_id in (
                  select id from public.audit_findings where audit_run_id = %s
                )
                """,
                [audit_run_id],
            )
            cursor.execute(
                "delete from public.audit_findings where audit_run_id = %s",
                [audit_run_id],
            )
        self._commit_if_needed()

    def create_finding(self, finding: AuditFindingCreate) -> dict[str, Any] | None:
        sql, params = _insert_sql("audit_findings", finding.to_row())
        return self._execute_returning(sql, params)

    def link_evidence(
        self, *, finding_id: str, evidence_item_id: str, role: str
    ) -> dict[str, Any] | None:
        sql, params = _insert_sql(
            "finding_evidence_refs",
            {
                "finding_id": finding_id,
                "evidence_item_id": evidence_item_id,
                "role": role,
            },
        )
        return self._execute_returning(sql, params)

    def create_trace(self, trace: FindingTraceCreate) -> dict[str, Any] | None:
        sql, params = _insert_sql("finding_traces", trace.to_row())
        return self._execute_returning(sql, params)

    def list_for_run(self, audit_run_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select *
            from public.audit_findings
            where audit_run_id = %s
            order by severity asc, created_at asc
            """,
            [audit_run_id],
        )


class RegulatoryRepository(SupabaseTableRepository):
    def upsert_source(self, source: RegulatorySourceUpsert) -> dict[str, Any] | None:
        sql, params = _upsert_sql("regulatory_sources", source.to_row(), ["id"])
        return self._execute_returning(sql, params)

    def upsert_chunks(self, chunks: Sequence[SourceChunkUpsert]) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql("source_chunks", chunk.to_row(), ["chunk_code"])
            for chunk in chunks
        ]
        return self._execute_many_returning(statements)

    def upsert_draft_records(self, records: Sequence[RegulatoryDraftRecordUpsert]) -> list[dict[str, Any]]:
        statements = [
            _upsert_sql("regulatory_draft_records", record.to_row(), ["id"])
            for record in records
        ]
        return self._execute_many_returning(statements)

    def list_sources_for_integrity(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        params: list[Any] = []
        limit_sql = ""
        if limit is not None:
            limit_sql = "limit %s"
            params.append(limit)
        return self._fetch_all(
            f"""
            select *
            from public.regulatory_sources
            order by id asc
            {limit_sql}
            """,
            params,
        )

    def list_chunks_for_integrity(self, *, source_ids: Sequence[str] | None = None) -> list[dict[str, Any]]:
        params: list[Any] = []
        filter_sql = ""
        if source_ids:
            filter_sql = "where regulatory_source_id = any(%s)"
            params.append(list(source_ids))
        return self._fetch_all(
            f"""
            select *
            from public.source_chunks
            {filter_sql}
            order by regulatory_source_id asc, chunk_code asc
            """,
            params,
        )

    def create_source_ingestion_job(
        self, job: SourceIngestionJobCreate
    ) -> dict[str, Any] | None:
        sql, params = _insert_sql("source_ingestion_jobs", job.to_row())
        return self._execute_returning(sql, params)

    def append_source_job_event(
        self,
        *,
        job_id: str,
        event_type: str,
        message: str | None = None,
        payload_json: JsonValue = None,
    ) -> dict[str, Any] | None:
        sql, params = _insert_sql(
            "source_ingestion_job_events",
            {
                "job_id": job_id,
                "event_type": event_type,
                "message": message,
                "payload_json": payload_json,
            },
        )
        return self._execute_returning(sql, params)

    def get_source_ingestion_job(self, job_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select *
            from public.source_ingestion_jobs
            where id = %s
            """,
            [job_id],
        )

    def list_source_ingestion_jobs(self, *, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        params: list[Any] = []
        filter_sql = ""
        if status:
            filter_sql = "where status = %s"
            params.append(status)
        params.append(limit)
        return self._fetch_all(
            f"""
            select *
            from public.source_ingestion_jobs
            {filter_sql}
            order by created_at desc
            limit %s
            """,
            params,
        )

    def list_source_job_events(self, job_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select *
            from public.source_ingestion_job_events
            where job_id = %s
            order by created_at desc
            limit %s
            """,
            [job_id, limit],
        )

    def load_approved_card_payloads(self, collection: str) -> list[dict[str, Any]]:
        """Approved regulatory cards of a collection (e.g. 'ftl_food_items', 'kde_requirements',
        'exemption_rules') from Supabase — the source of truth. When the regulation changes, the
        cards change and the engine follows; nothing in code needs editing."""
        rows = self._fetch_all(
            """
            select payload
            from public.approved_regulatory_records
            where collection = %s
            order by record_id asc
            """,
            [collection],
        )
        return [row["payload"] for row in rows if isinstance(row.get("payload"), dict)]


class ApprovedRulePackageRepository(SupabaseTableRepository):
    def load_package(
        self,
        *,
        package_id: str,
        version: int,
        package_hash: str | None = None,
    ) -> dict[str, Any]:
        params: list[Any] = [package_id, version]
        hash_filter = ""
        if package_hash:
            hash_filter = "and package_hash = %s"
            params.append(package_hash)
        package = self._fetch_one(
            f"""
            select *
            from public.approved_rule_packages
            where package_id = %s
              and version = %s
              and status = 'approved'
              {hash_filter}
            """,
            params,
        )
        if not package:
            raise LookupError(f"Approved rule package not found: {package_id}@{version}")
        records = self._fetch_all(
            """
            select *
            from public.approved_rule_package_records
            where approved_rule_package_id = %s
            order by collection asc, record_id asc, record_version asc nulls last
            """,
            [package["id"]],
        )
        return _compose_rule_package(package, records)


def _compose_rule_package(package: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_collection: dict[str, list[Any]] = {}
    for record in records:
        collection = str(record["collection"])
        by_collection.setdefault(collection, []).append(record["payload"])

    obligations = by_collection.get("obligations") or by_collection.get("obligation") or []
    result = {
        "package_id": package["package_id"],
        "version": package["version"],
        "status": package["status"],
        "package_hash": package["package_hash"],
        "generated_at": _json_safe(package.get("generated_at")),
        "approved_at": _json_safe(package.get("approved_at")),
        "approved_by": package.get("approved_by"),
        "records": {
            "obligations": obligations,
            **{
                collection: payloads
                for collection, payloads in by_collection.items()
                if collection not in {"obligations", "obligation"}
            },
        },
        "metadata": package.get("metadata_json") or {},
        "source_versions": package.get("source_versions") or {},
        "rollback": package.get("rollback") or {},
    }
    return result


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
