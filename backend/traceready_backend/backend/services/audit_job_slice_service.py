from __future__ import annotations

import logging
from typing import Any, Protocol

from traceready_backend.backend.repositories.supabase_tables import (
    ApprovedRulePackageRepository,
    AuditFileRepository,
    AuditJobCreate,
    AuditJobRepository,
    AuditProjectRepository,
    AuditRunRepository,
    EvidenceRepository,
    FindingRepository,
    NormalizedEvidenceRepository,
    ParsedWorkbookRepository,
)
from traceready_backend.backend.schemas.audit_parse import AuditParseJobPayload
from traceready_backend.backend.schemas.rule_execution import RuleExecutionJobPayload
from traceready_backend.backend.services.audit_parse_service import run_audit_parse_job
from traceready_backend.backend.services.rule_execution_service import run_rule_execution_job
from traceready_backend.storage.artifacts import ObjectStore


class AuditJobSliceRepositories(Protocol):
    audit_jobs: AuditJobRepository
    audit_projects: AuditProjectRepository
    audit_runs: AuditRunRepository
    evidence: EvidenceRepository
    parsed_workbook: ParsedWorkbookRepository
    normalized_evidence: NormalizedEvidenceRepository
    approved_rule_packages: ApprovedRulePackageRepository
    findings: FindingRepository
    audit_files: AuditFileRepository


def run_audit_job_slice(
    *,
    repositories: AuditJobSliceRepositories,
    object_store: ObjectStore,
    worker_id: str,
    job_types: list[str],
    max_jobs: int,
    stale_lock_minutes: int = 15,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    _log(
        logger,
        "Audit worker slice started",
        worker_id=worker_id,
        stage="slice_started",
    )
    processed: list[dict[str, Any]] = []
    for _ in range(max_jobs):
        job = repositories.audit_jobs.claim_next_job(
            worker_id,
            job_types,
            stale_lock_minutes=stale_lock_minutes,
        )
        if not job:
            _log(
                logger,
                "Audit worker found no claimable jobs",
                worker_id=worker_id,
                stage="no_claimable_jobs",
                processed_count=len(processed),
            )
            break
        _log(
            logger,
            "Audit job claimed",
            worker_id=worker_id,
            job_id=str(job.get("id")),
            job_type=str(job.get("job_type") or ""),
            audit_project_id=str(job.get("audit_project_id") or ""),
            audit_run_id=str(job.get("audit_run_id") or ""),
            audit_file_id=str(job.get("audit_file_id") or ""),
            attempt_count=int(job.get("attempt_count") or 0),
            stage="job_claimed",
        )
        repositories.audit_jobs.append_event(
            audit_job_id=job["id"],
            audit_project_id=job.get("audit_project_id"),
            audit_run_id=job.get("audit_run_id"),
            event_type="job_claimed",
            message="Job claimed by bounded audit job processor.",
            payload_json={
                "workerId": worker_id,
                "jobType": job.get("job_type"),
                "attemptCount": job.get("attempt_count"),
            },
        )
        processed.append(_process_claimed_job(job=job, repositories=repositories, object_store=object_store, logger=logger, worker_id=worker_id))
    _log(
        logger,
        "Audit worker slice completed",
        worker_id=worker_id,
        stage="slice_completed",
        processed_count=len(processed),
    )
    return {
        "status": "ok",
        "processedCount": len(processed),
        "processed": processed,
        "continue": len(processed) == max_jobs,
    }


def _process_claimed_job(
    *,
    job: dict[str, Any],
    repositories: AuditJobSliceRepositories,
    object_store: ObjectStore,
    logger: logging.Logger | None = None,
    worker_id: str | None = None,
) -> dict[str, Any]:
    job_type = str(job.get("job_type") or "")
    try:
        if job_type == "parse_customer_workbook":
            _log_job(logger, "Audit parse job started", job, worker_id=worker_id, stage="parse_started")
            result = run_audit_parse_job(
                payload=_parse_payload(job),
                object_store=object_store,
                repositories=repositories,
            )
            queued_next_job_id: str | None = None
            if result.status == "succeeded":
                queued_next_job_id = _queue_rule_execution_job(job=job, repositories=repositories)
            _log_job(
                logger,
                "Audit parse job completed",
                job,
                worker_id=worker_id,
                stage="parse_completed",
                status=result.status,
                evidence_record_count=getattr(result, "evidence_record_count", None),
                queued_next_job_id=queued_next_job_id,
            )
            return {
                "jobId": job["id"],
                "jobType": job_type,
                "status": result.status,
                "queuedNextJobId": queued_next_job_id,
                "checkpoint": result.checkpoint,
            }
        if job_type == "execute_approved_rules":
            _log_job(logger, "Audit rule execution job started", job, worker_id=worker_id, stage="rule_execution_started")
            result = run_rule_execution_job(
                payload=_rule_execution_payload(job),
                object_store=object_store,
                repositories=repositories,
            )
            _log_job(
                logger,
                "Audit rule execution job completed",
                job,
                worker_id=worker_id,
                stage="rule_execution_completed",
                status=result.status,
                finding_count=getattr(result, "finding_count", None),
                artifact_count=getattr(result, "artifact_count", None),
                readiness_status=getattr(result, "readiness_status", None),
            )
            return {
                "jobId": job["id"],
                "jobType": job_type,
                "status": result.status,
                "readinessStatus": result.readiness_status,
                "checkpoint": result.checkpoint,
            }
        raise ValueError(f"Unsupported audit job type: {job_type}")
    except Exception as exc:
        _log_job(
            logger,
            "Audit job processor failed",
            job,
            worker_id=worker_id,
            stage="processor_failed",
            status="failed",
            error_type=exc.__class__.__name__,
        )
        repositories.audit_jobs.fail_job(
            job["id"],
            failure_category="processor_error",
            error_json={
                "stage": "processor_error",
                "jobType": job_type,
                "errorType": exc.__class__.__name__,
                "message": str(exc),
            },
            retryable=_can_retry(job),
        )
        repositories.audit_jobs.append_event(
            audit_job_id=job["id"],
            audit_project_id=job.get("audit_project_id"),
            audit_run_id=job.get("audit_run_id"),
            event_type="job_processor_failed",
            message="Bounded job processor failed before the job service completed.",
            payload_json={"errorType": exc.__class__.__name__, "message": str(exc), "jobType": job_type},
        )
        return {
            "jobId": job["id"],
            "jobType": job_type,
            "status": "failed",
            "error": str(exc),
        }


def _log(logger: logging.Logger | None, message: str, **fields: object) -> None:
    if logger:
        logger.info(message, extra={key: value for key, value in fields.items() if value is not None})


def _log_job(
    logger: logging.Logger | None,
    message: str,
    job: dict[str, Any],
    **fields: object,
) -> None:
    _log(
        logger,
        message,
        job_id=str(job.get("id") or ""),
        job_type=str(job.get("job_type") or ""),
        audit_project_id=str(job.get("audit_project_id") or ""),
        audit_run_id=str(job.get("audit_run_id") or ""),
        audit_file_id=str(job.get("audit_file_id") or ""),
        **fields,
    )


def _parse_payload(job: dict[str, Any]) -> AuditParseJobPayload:
    checkpoint = _checkpoint(job)
    return AuditParseJobPayload(
        job_id=str(job["id"]),
        audit_project_id=str(job["audit_project_id"]),
        audit_run_id=str(job["audit_run_id"]),
        audit_file_id=str(job["audit_file_id"]),
        customer_id=_string(checkpoint.get("customerId")) or _customer_id_from_storage_key(_required_string(checkpoint, "storageKey")),
        storage_bucket=_required_string(checkpoint, "storageBucket"),
        storage_key=_required_string(checkpoint, "storageKey"),
        original_file_name=_required_string(checkpoint, "originalFileName"),
        parser_version=_string(checkpoint.get("parserVersion")) or "customer_evidence_v1",
        metadata={"sliceProcessor": "vercel_bounded_v1"},
    )


def _rule_execution_payload(job: dict[str, Any]) -> RuleExecutionJobPayload:
    checkpoint = _checkpoint(job)
    storage_key = _required_string(checkpoint, "storageKey")
    storage_bucket = _required_string(checkpoint, "storageBucket")
    return RuleExecutionJobPayload(
        job_id=str(job["id"]),
        audit_project_id=str(job["audit_project_id"]),
        audit_run_id=str(job["audit_run_id"]),
        audit_file_id=str(job["audit_file_id"]),
        customer_id=_string(checkpoint.get("customerId")) or _customer_id_from_storage_key(storage_key),
        storage_bucket=storage_bucket,
        storage_key=storage_key,
        original_file_name=_required_string(checkpoint, "originalFileName"),
        approved_rule_package_id=_required_string(checkpoint, "approvedRulePackageId"),
        approved_rule_package_version=int(checkpoint.get("approvedRulePackageVersion") or 1),
        approved_rule_package_hash=_string(checkpoint.get("approvedRulePackageHash")),
        ftl_food_items_bucket=_string(checkpoint.get("ftlFoodItemsBucket")),
        ftl_food_items_key=_string(checkpoint.get("ftlFoodItemsKey")),
        artifact_bucket=_string(checkpoint.get("artifactBucket")) or storage_bucket,
        execution_version=_string(checkpoint.get("executionVersion")) or "approved_rule_execution_v1",
        metadata={"sliceProcessor": "vercel_bounded_v1"},
    )


def _queue_rule_execution_job(
    *,
    job: dict[str, Any],
    repositories: AuditJobSliceRepositories,
) -> str | None:
    checkpoint = _checkpoint(job)
    if not checkpoint.get("approvedRulePackageId"):
        return None
    next_job = AuditJobCreate(
        audit_project_id=str(job["audit_project_id"]),
        audit_run_id=str(job["audit_run_id"]),
        audit_file_id=str(job["audit_file_id"]),
        job_type="execute_approved_rules",
        priority=int(job.get("priority") or 100) + 10,
        checkpoint_json={
            **checkpoint,
            "stage": "queued",
            "previousJobId": job["id"],
            "executionVersion": checkpoint.get("executionVersion") or "approved_rule_execution_v1",
            "artifactBucket": checkpoint.get("artifactBucket") or checkpoint.get("storageBucket"),
        },
    )
    created = repositories.audit_jobs.create_job(next_job)
    repositories.audit_jobs.append_event(
        audit_job_id=next_job.id,
        audit_project_id=job.get("audit_project_id"),
        audit_run_id=job.get("audit_run_id"),
        event_type="rule_execution_queued",
        message="Approved-rule execution queued after successful workbook parse.",
        payload_json={"previousJobId": job["id"]},
    )
    return str((created or {}).get("id") or next_job.id)


def _checkpoint(job: dict[str, Any]) -> dict[str, Any]:
    raw = job.get("checkpoint_json")
    return raw if isinstance(raw, dict) else {}


def _required_string(checkpoint: dict[str, Any], key: str) -> str:
    value = _string(checkpoint.get(key))
    if not value:
        raise ValueError(f"Missing job checkpoint field: {key}")
    return value


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _customer_id_from_storage_key(storage_key: str) -> str:
    parts = storage_key.split("/")
    if len(parts) >= 2 and parts[0] == "customers":
        return parts[1]
    raise ValueError("Unable to derive customer ID from storage key.")


def _can_retry(job: dict[str, Any]) -> bool:
    return int(job.get("attempt_count") or 0) < int(job.get("max_attempts") or 1)
