from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from bellwether_backend.api.config import ServiceSettings, load_settings
from bellwether_backend.api.errors import register_error_handlers
from bellwether_backend.api.observability import add_request_logging, build_logger
from bellwether_backend.api.readiness import build_readiness_report
from bellwether_backend.api.security import require_internal_token
from bellwether_backend.backend.db import supabase_connection
from bellwether_backend.backend.repositories.supabase_tables import (
    ApprovedRulePackageRepository,
    AuditFileRepository,
    AuditJobRepository,
    AuditProjectRepository,
    AuditRunRepository,
    EvidenceRepository,
    FindingRepository,
    NormalizedEvidenceRepository,
    ParsedWorkbookRepository,
    RegulatoryRepository,
    SourceIngestionJobCreate,
)
from bellwether_backend.backend.services.audit_job_slice_service import run_audit_job_slice
from bellwether_backend.backend.services.source_artifact_integrity_service import check_source_artifact_integrity
from bellwether_backend.storage.artifacts import build_object_store


class AuditJobSliceRequest(BaseModel):
    worker_id: str = Field(default="vercel-worker")
    job_types: list[str] = Field(default_factory=lambda: ["parse_customer_workbook", "execute_approved_rules"])
    max_jobs: int = Field(default=1, ge=1, le=10)
    stale_lock_minutes: int = Field(default=15, ge=1, le=240)


class AuditJobRetryRequest(BaseModel):
    requested_by: str = Field(default="internal-api")
    reason: str = Field(min_length=1, max_length=500)


class SourceIngestionJobRequest(BaseModel):
    source_type: str = Field(min_length=1, max_length=80)
    job_type: str = Field(default="ingest_regulatory_source", min_length=1, max_length=100)
    regulatory_source_id: str | None = None
    source_url: str | None = None
    max_attempts: int = Field(default=3, ge=1, le=10)
    checkpoint_json: dict[str, object] | None = None
    created_by: str | None = None


class InboundValidateRequest(BaseModel):
    """Pre-receipt validation: an ASN/EDI file, BOL PDF, or spreadsheet of intended
    shipments, base64-encoded (JSON body avoids a multipart dependency; keep payloads under
    ~4 MB, the serverless request limit)."""

    file_name: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=4)
    document_type_hint: str | None = Field(default=None, description="edi_856 | bol_pdf | spreadsheet")
    cte: str = Field(default="receiving", max_length=50)


def create_app(settings: ServiceSettings | None = None) -> FastAPI:
    loaded_settings = settings or load_settings()
    api = FastAPI(
        title="Bellwether Python Backend",
        version=loaded_settings.service_version,
        docs_url="/docs" if loaded_settings.environment.value != "production" else None,
        redoc_url=None,
    )
    api.state.settings = loaded_settings
    api.state.logger = build_logger()

    if loaded_settings.allowed_origins:
        api.add_middleware(
            CORSMiddleware,
            allow_origins=list(loaded_settings.allowed_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["authorization", "content-type", "x-request-id", "x-bellwether-internal-token"],
        )

    add_request_logging(api)
    register_error_handlers(api)

    @api.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": loaded_settings.service_name,
            "version": loaded_settings.service_version,
            "environment": loaded_settings.environment.value,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    @api.get("/ready", tags=["system"])
    async def ready(response: Response) -> dict[str, object]:
        report = build_readiness_report(loaded_settings)
        if report["status"] != "ready":
            response.status_code = 503
        return report

    @api.get("/internal/ping", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def internal_ping() -> dict[str, str]:
        return {"status": "ok", "scope": "internal"}

    @api.post("/internal/inbound/validate", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def inbound_validate(payload: InboundValidateRequest) -> dict[str, object]:
        """Pre-receipt validation: per-line accept/hold verdicts with citations, synchronous."""
        import base64
        import binascii
        import json as _json
        from pathlib import Path as _Path

        from bellwether_backend.backend.services.inbound_validation_service import validate_inbound_document

        try:
            data = base64.b64decode(payload.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"content_base64 is not valid base64: {exc}") from exc
        if len(data) > 4_000_000:
            raise HTTPException(status_code=413, detail="document exceeds the 4MB synchronous validation limit")

        ftl_items: list[dict[str, object]] = []
        try:
            with supabase_connection(loaded_settings) as connection:
                ftl_items = RegulatoryRepository(connection).load_approved_card_payloads("ftl_food_items")
        except Exception:
            ftl_items = []
        if not ftl_items:
            bundled = _Path(__file__).resolve().parents[3] / "data" / "regulatory" / "intelligence" / "drafts" / "ftl-food-items.json"
            if bundled.exists():
                loaded = _json.loads(bundled.read_text(encoding="utf-8"))
                ftl_items = loaded if isinstance(loaded, list) else []

        return validate_inbound_document(
            data=data,
            file_name=payload.file_name,
            document_type_hint=payload.document_type_hint,
            cte=payload.cte,
            ftl_items=ftl_items,
        )

    @api.post("/internal/jobs/audit/slice", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def audit_job_slice(payload: AuditJobSliceRequest) -> dict[str, object]:
        claimed: list[dict[str, object]] = []
        with supabase_connection(loaded_settings) as connection:
            jobs = AuditJobRepository(connection, auto_commit=False)
            for _ in range(payload.max_jobs):
                job = jobs.claim_next_job(
                    payload.worker_id,
                    payload.job_types,
                    stale_lock_minutes=payload.stale_lock_minutes,
                )
                if not job:
                    break
                jobs.append_event(
                    audit_job_id=job["id"],
                    audit_project_id=job.get("audit_project_id"),
                    audit_run_id=job.get("audit_run_id"),
                    event_type="job_claimed",
                    message="Job claimed by bounded audit job slice.",
                    payload_json={
                        "workerId": payload.worker_id,
                        "jobType": job.get("job_type"),
                        "attemptCount": job.get("attempt_count"),
                    },
                )
                claimed.append(
                    {
                        "jobId": job["id"],
                        "jobType": job.get("job_type"),
                        "auditProjectId": job.get("audit_project_id"),
                        "auditRunId": job.get("audit_run_id"),
                        "attemptCount": job.get("attempt_count"),
                    }
                )
        return {
            "status": "ok",
            "claimedCount": len(claimed),
            "claimed": claimed,
        }

    @api.post("/internal/jobs/audit/process-slice", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def audit_job_process_slice(payload: AuditJobSliceRequest) -> dict[str, object]:
        object_store = build_object_store(loaded_settings)
        with supabase_connection(loaded_settings) as connection:
            repositories = AuditJobProcessingRepositories(connection)
            return run_audit_job_slice(
                repositories=repositories,
                object_store=object_store,
                worker_id=payload.worker_id,
                job_types=payload.job_types,
                max_jobs=payload.max_jobs,
                stale_lock_minutes=payload.stale_lock_minutes,
                logger=api.state.logger,
            )

    @api.get("/internal/audits/{audit_project_id}/jobs", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def audit_project_jobs(audit_project_id: str, limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
        with supabase_connection(loaded_settings) as connection:
            jobs = AuditJobRepository(connection)
            rows = jobs.list_for_project(audit_project_id, limit=limit)
        return {"status": "ok", "auditProjectId": audit_project_id, "jobs": rows}

    @api.get("/internal/jobs/audit/{job_id}", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def audit_job_status(job_id: str) -> dict[str, object]:
        with supabase_connection(loaded_settings) as connection:
            jobs = AuditJobRepository(connection)
            job = jobs.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Audit job not found.")
            events = jobs.list_events(job_id)
        return {"status": "ok", "job": job, "events": events}

    @api.post("/internal/jobs/audit/{job_id}/retry", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def audit_job_retry(job_id: str, payload: AuditJobRetryRequest) -> dict[str, object]:
        with supabase_connection(loaded_settings) as connection:
            jobs = AuditJobRepository(connection)
            job = jobs.retry_job(job_id, requested_by=payload.requested_by, reason=payload.reason)
            if not job:
                raise HTTPException(status_code=409, detail="Audit job is not retryable.")
            jobs.append_event(
                audit_job_id=job_id,
                audit_project_id=job.get("audit_project_id"),
                audit_run_id=job.get("audit_run_id"),
                event_type="manual_retry_requested",
                message="Audit job retry requested through internal API.",
                payload_json={"requestedBy": payload.requested_by, "reason": payload.reason},
            )
        return {"status": "ok", "job": job}

    @api.get("/internal/audits/{audit_project_id}/artifacts", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def audit_artifacts(
        audit_project_id: str,
        audit_run_id: str | None = None,
        artifact_type: list[str] | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, object]:
        with supabase_connection(loaded_settings) as connection:
            files = AuditFileRepository(connection)
            artifacts = files.list_artifacts(
                audit_project_id=audit_project_id,
                audit_run_id=audit_run_id,
                artifact_types=artifact_type,
                limit=limit,
            )
        return {"status": "ok", "auditProjectId": audit_project_id, "artifacts": artifacts}

    @api.post("/internal/regulatory/source-ingestion-jobs", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def create_source_ingestion_job(payload: SourceIngestionJobRequest) -> dict[str, object]:
        with supabase_connection(loaded_settings) as connection:
            regulatory = RegulatoryRepository(connection)
            job = regulatory.create_source_ingestion_job(
                SourceIngestionJobCreate(
                    regulatory_source_id=payload.regulatory_source_id,
                    source_url=payload.source_url,
                    source_type=payload.source_type,
                    job_type=payload.job_type,
                    max_attempts=payload.max_attempts,
                    checkpoint_json=payload.checkpoint_json,
                    created_by=payload.created_by,
                )
            )
            if not job:
                raise HTTPException(status_code=500, detail="Source ingestion job was not created.")
            regulatory.append_source_job_event(
                job_id=job["id"],
                event_type="source_ingestion_queued",
                message="Regulatory source ingestion job queued through internal API.",
                payload_json=payload.model_dump(mode="json"),
            )
        return {"status": "ok", "job": job}

    @api.get("/internal/regulatory/source-ingestion-jobs", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def source_ingestion_jobs(status: str | None = None, limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
        with supabase_connection(loaded_settings) as connection:
            regulatory = RegulatoryRepository(connection)
            jobs = regulatory.list_source_ingestion_jobs(status=status, limit=limit)
        return {"status": "ok", "jobs": jobs}

    @api.get("/internal/regulatory/source-ingestion-jobs/{job_id}", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def source_ingestion_job_status(job_id: str) -> dict[str, object]:
        with supabase_connection(loaded_settings) as connection:
            regulatory = RegulatoryRepository(connection)
            job = regulatory.get_source_ingestion_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Source ingestion job not found.")
            events = regulatory.list_source_job_events(job_id)
        return {"status": "ok", "job": job, "events": events}

    @api.post("/internal/regulatory/source-integrity-check", tags=["internal"], dependencies=[Depends(require_internal_token)])
    async def source_integrity_check(
        source_version: int = Query(default=1, ge=1),
        limit: int | None = Query(default=None, ge=1, le=5000),
    ) -> dict[str, object]:
        object_store = build_object_store(loaded_settings)
        with supabase_connection(loaded_settings) as connection:
            report = check_source_artifact_integrity(
                repository=RegulatoryRepository(connection),
                object_store=object_store,
                default_bucket=loaded_settings.supabase_storage_bucket,
                source_version=source_version,
                limit=limit,
            )
        return report.to_dict()

    return api


app = create_app()


class AuditJobProcessingRepositories:
    def __init__(self, connection: object):
        self.audit_jobs = AuditJobRepository(connection, auto_commit=False)
        self.audit_projects = AuditProjectRepository(connection, auto_commit=False)
        self.audit_runs = AuditRunRepository(connection, auto_commit=False)
        self.evidence = EvidenceRepository(connection, auto_commit=False)
        self.parsed_workbook = ParsedWorkbookRepository(connection, auto_commit=False)
        self.normalized_evidence = NormalizedEvidenceRepository(connection, auto_commit=False)
        self.approved_rule_packages = ApprovedRulePackageRepository(connection, auto_commit=False)
        self.findings = FindingRepository(connection, auto_commit=False)
        self.audit_files = AuditFileRepository(connection, auto_commit=False)
        self.regulatory = RegulatoryRepository(connection, auto_commit=False)
