from __future__ import annotations

from traceready_ingestion.backend.schemas.audit_parse import AuditParseJobPayload
from traceready_ingestion.backend.services.audit_parse_service import (
    AuditParseRepositories,
    run_audit_parse_job,
)
from traceready_ingestion.storage.artifacts import ObjectStore


def execute_audit_parse_job(
    *,
    payload: dict,
    object_store: ObjectStore,
    repositories: AuditParseRepositories,
):
    return run_audit_parse_job(
        payload=AuditParseJobPayload.model_validate(payload),
        object_store=object_store,
        repositories=repositories,
    )
