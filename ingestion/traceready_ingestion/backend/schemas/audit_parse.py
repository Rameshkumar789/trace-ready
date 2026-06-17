from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BackendSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AuditParseJobPayload(BackendSchema):
    job_id: str
    audit_project_id: str
    audit_run_id: str
    audit_file_id: str
    customer_id: str | None = None
    storage_bucket: str
    storage_key: str
    original_file_name: str
    parser_version: str = "customer_evidence_v1"
    content_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParseIssue(BackendSchema):
    scope: Literal["file", "sheet", "row", "cell"]
    error_type: str
    message: str
    sheet_name: str | None = None
    row_number: int | None = None
    column_name: str | None = None
    raw_value: str | None = None


class AuditParseJobResult(BackendSchema):
    job_id: str
    audit_project_id: str
    audit_run_id: str
    audit_file_id: str
    parser_version: str
    status: Literal["succeeded", "failed"]
    evidence_record_count: int = 0
    persisted_evidence_count: int = 0
    parse_errors: list[ParseIssue] = Field(default_factory=list)
    checkpoint: dict[str, Any] = Field(default_factory=dict)
