from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Protocol

from traceready_ingestion.backend.repositories.supabase_tables import (
    ApprovedRulePackageRepository,
    AuditArtifactCreate,
    AuditFileRepository,
    AuditFindingCreate,
    AuditJobRepository,
    AuditProjectRepository,
    AuditRunRepository,
    EvidenceRepository,
    FindingRepository,
    FindingTraceCreate,
    RegulatoryRepository,
    stable_row_id,
)
from traceready_ingestion.backend.schemas.rule_execution import (
    RuleExecutionJobPayload,
    RuleExecutionJobResult,
)
from traceready_ingestion.audit_engine.rule_execution import (
    AuditFinding,
    Phase11RuleExecutionPackage,
    build_phase11_rule_execution,
    write_phase11_rule_execution_artifacts,
)
from traceready_ingestion.storage.artifacts import (
    ObjectStore,
    audit_artifact_key,
    guess_content_type,
)
from traceready_ingestion.versioning.hashing import sha256_text


class RuleExecutionRepositories(Protocol):
    audit_jobs: AuditJobRepository
    audit_projects: AuditProjectRepository
    audit_runs: AuditRunRepository
    approved_rule_packages: ApprovedRulePackageRepository
    findings: FindingRepository
    audit_files: AuditFileRepository
    evidence: EvidenceRepository
    regulatory: RegulatoryRepository


def run_rule_execution_job(
    *,
    payload: RuleExecutionJobPayload,
    object_store: ObjectStore,
    repositories: RuleExecutionRepositories,
) -> RuleExecutionJobResult:
    repositories.audit_jobs.append_event(
        audit_job_id=payload.job_id,
        audit_project_id=payload.audit_project_id,
        audit_run_id=payload.audit_run_id,
        event_type="rule_execution_started",
        message="Approved-rule execution job started.",
        payload_json=payload.model_dump(mode="json"),
    )
    repositories.audit_jobs.checkpoint_job(
        payload.job_id,
        {
            "stage": "loading_approved_rule_package",
            "packageId": payload.approved_rule_package_id,
            "packageVersion": payload.approved_rule_package_version,
            "packageHash": payload.approved_rule_package_hash,
        },
    )

    try:
        approved_rule_package = repositories.approved_rule_packages.load_package(
            package_id=payload.approved_rule_package_id,
            version=payload.approved_rule_package_version,
            package_hash=payload.approved_rule_package_hash,
        )
        repositories.audit_jobs.checkpoint_job(
            payload.job_id,
            {
                "stage": "downloading_customer_workbook",
                "storageBucket": payload.storage_bucket,
                "storageKey": payload.storage_key,
            },
        )
        workbook_payload = object_store.download_bytes(
            bucket=payload.storage_bucket,
            key=payload.storage_key,
        )

        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            workbook_path = tmp_path / _safe_filename(payload.original_file_name)
            package_path = tmp_path / "approved-rule-package.json"
            artifacts_dir = tmp_path / "artifacts"
            workbook_path.write_bytes(workbook_payload.data)
            package_path.write_text(json.dumps(approved_rule_package, indent=2), encoding="utf-8")

            ftl_path = _write_optional_ftl_file(
                tmp_path=tmp_path,
                object_store=object_store,
                bucket=payload.ftl_food_items_bucket,
                key=payload.ftl_food_items_key,
                repositories=repositories,
            )
            # The KDE coverage dictionary and the 1.1305 exemption rules are reviewable
            # regulation, not code. We load the approved cards from Supabase when present so a
            # re-approval (e.g. an FTL/exemption change) flows through with no code edit; the
            # bundled JSON is only an offline/dev fallback.
            kde_contracts_path = _write_optional_card_file(
                tmp_path=tmp_path,
                repositories=repositories,
                collection="kde_check_contracts",
                filename="kde-check-contracts.json",
                # Each card payload is one per-CTE contract carrying its own "cte" key.
                build_document=lambda cards: {
                    "cte_contracts": {card["cte"]: card for card in cards if card.get("cte")}
                },
            )
            exemption_rules_path = _write_optional_card_file(
                tmp_path=tmp_path,
                repositories=repositories,
                collection="exemption_rules",
                filename="exemption-rules.json",
                build_document=lambda cards: {"exemptions": cards},
            )
            plan_components_path = _write_optional_card_file(
                tmp_path=tmp_path,
                repositories=repositories,
                collection="traceability_plan_components",
                filename="traceability-plan-components.json",
                build_document=lambda cards: {"components": cards},
            )

            repositories.audit_jobs.checkpoint_job(
                payload.job_id,
                {
                    "stage": "running_deterministic_checks",
                    "approvedRuleOnly": True,
                    "sourceWorkbookSha256": workbook_payload.sha256,
                },
            )
            package = build_phase11_rule_execution(
                input_file=workbook_path,
                approved_rule_package_file=package_path,
                ftl_food_items_file=ftl_path,
                kde_contracts_file=kde_contracts_path,
                exemption_rules_file=exemption_rules_path,
                plan_components_file=plan_components_path,
            )
            artifacts = write_phase11_rule_execution_artifacts(package, artifacts_dir)

            repositories.audit_jobs.checkpoint_job(
                payload.job_id,
                {
                    "stage": "persisting_rule_execution_outputs",
                    "findingCount": len(package.audit_findings),
                    "artifactCount": len(artifacts),
                },
            )
            finding_count, evidence_ref_count, trace_count = _persist_findings(
                payload=payload,
                package=package,
                repositories=repositories,
            )
            stored_artifacts = _upload_artifacts(
                payload=payload,
                artifacts=artifacts,
                object_store=object_store,
                repositories=repositories,
            )

        readiness_status = _readiness_status(package)
        summary = {
            **package.summary,
            "readinessStatus": readiness_status,
            "artifactCount": len(stored_artifacts),
            "executionVersion": payload.execution_version,
            "sourceWorkbook": {
                "storageBucket": payload.storage_bucket,
                "storageKey": payload.storage_key,
                "sha256": workbook_payload.sha256,
                "sizeBytes": workbook_payload.size_bytes,
            },
        }
        repositories.audit_runs.update_rule_execution_summary(
            audit_run_id=payload.audit_run_id,
            status="succeeded",
            rule_package_id=payload.approved_rule_package_id,
            rule_package_version=payload.approved_rule_package_version,
            rule_package_hash=approved_rule_package.get("package_hash"),
            summary_json=summary,
        )
        repositories.audit_projects.update_status(audit_project_id=payload.audit_project_id, status="succeeded")

        checkpoint = {
            "stage": "completed",
            "approvedRuleOnly": True,
            "findingCount": finding_count,
            "evidenceRefCount": evidence_ref_count,
            "traceCount": trace_count,
            "artifactCount": len(stored_artifacts),
            "readinessStatus": readiness_status,
        }
        repositories.audit_jobs.complete_job(payload.job_id, checkpoint)
        repositories.audit_jobs.append_event(
            audit_job_id=payload.job_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            event_type="rule_execution_completed",
            message="Approved-rule execution job completed.",
            payload_json=checkpoint,
        )
        return RuleExecutionJobResult(
            job_id=payload.job_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            status="succeeded",
            approved_rule_package_id=payload.approved_rule_package_id,
            approved_rule_package_version=payload.approved_rule_package_version,
            finding_count=finding_count,
            evidence_ref_count=evidence_ref_count,
            trace_count=trace_count,
            artifact_count=len(stored_artifacts),
            readiness_status=readiness_status,
            checkpoint=checkpoint,
        )
    except Exception as exc:
        error_payload = {
            "stage": "failed",
            "errorType": exc.__class__.__name__,
            "message": str(exc),
            "approvedRuleOnly": True,
        }
        repositories.audit_jobs.fail_job(
            payload.job_id,
            failure_category="rule_execution_error",
            error_json=error_payload,
            retryable=False,
        )
        repositories.audit_projects.update_status(audit_project_id=payload.audit_project_id, status="failed")
        repositories.audit_jobs.append_event(
            audit_job_id=payload.job_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            event_type="rule_execution_failed",
            message="Approved-rule execution job failed.",
            payload_json=error_payload,
        )
        return RuleExecutionJobResult(
            job_id=payload.job_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            status="failed",
            approved_rule_package_id=payload.approved_rule_package_id,
            approved_rule_package_version=payload.approved_rule_package_version,
            checkpoint=error_payload,
        )


def _persist_findings(
    *,
    payload: RuleExecutionJobPayload,
    package: Phase11RuleExecutionPackage,
    repositories: RuleExecutionRepositories,
) -> tuple[int, int, int]:
    finding_count = 0
    evidence_ref_count = 0
    trace_count = 0
    repositories.findings.delete_for_run(payload.audit_run_id)
    # evidence_items are persisted under a file-scoped id (see audit_parse_service:
    # stable_row_id("evidence", audit_file_id, raw_evidence_id)), while findings carry the
    # raw customer evidence id. Scope them the same way before linking, and only link ids
    # that were actually persisted for this run. This prevents a single missing/inferred
    # evidence id from raising a foreign-key violation that aborts the whole transaction
    # (which previously left parse+execute jobs stuck in a queued retry loop).
    existing_evidence_ids = {
        str(row["id"]) for row in repositories.evidence.list_for_run(payload.audit_run_id)
    }
    skipped_evidence_refs = 0
    for index, finding in enumerate(package.audit_findings, start=1):
        finding_id = _db_finding_id(payload.audit_run_id, finding.finding_id)
        repositories.findings.create_finding(_finding_row(payload, finding_id, finding))
        finding_count += 1
        linked_for_finding: set[str] = set()
        for evidence_id in finding.customer_evidence_ids:
            scoped_id = stable_row_id("evidence", payload.audit_file_id, evidence_id)
            if scoped_id not in existing_evidence_ids or scoped_id in linked_for_finding:
                skipped_evidence_refs += 1
                continue
            repositories.findings.link_evidence(
                finding_id=finding_id,
                evidence_item_id=scoped_id,
                role="supporting_evidence",
            )
            linked_for_finding.add(scoped_id)
            evidence_ref_count += 1
        for trace in _trace_rows(payload, finding_id, finding, index):
            repositories.findings.create_trace(trace)
            trace_count += 1
    return finding_count, evidence_ref_count, trace_count


def _finding_row(
    payload: RuleExecutionJobPayload,
    finding_id: str,
    finding: AuditFinding,
) -> AuditFindingCreate:
    citation = finding.source_citation or {}
    return AuditFindingCreate(
        id=finding_id,
        audit_project_id=payload.audit_project_id,
        audit_run_id=payload.audit_run_id,
        title=finding.message[:160],
        status=finding.status,
        severity=finding.severity,
        finding_type=finding.finding_type,
        event_id=finding.event_id,
        field_or_kde=finding.cte,
        recommendation=_recommendation_for(finding),
        approved_obligation_id=finding.approved_obligation_id,
        rule_package_id=payload.approved_rule_package_id,
        rule_package_version=payload.approved_rule_package_version,
        check_code=finding.finding_type,
        check_version=payload.execution_version,
        evidence_refs_json=finding.customer_evidence_ids,
        metadata_json={
            "sourceCitation": citation,
            "confidence": finding.confidence,
            "cte": finding.cte,
            "sourceFindingId": finding.finding_id,
            "approvedRuleOnly": True,
        },
        review_state=finding.reviewer_status,
    )


def _trace_rows(
    payload: RuleExecutionJobPayload,
    finding_id: str,
    finding: AuditFinding,
    index: int,
) -> list[FindingTraceCreate]:
    return [
        FindingTraceCreate(
            finding_id=finding_id,
            audit_run_id=payload.audit_run_id,
            sequence=1,
            trace_type="customer_evidence",
            title="Customer evidence used by finding",
            payload_json={
                "evidenceIds": finding.customer_evidence_ids,
                "eventId": finding.event_id,
                "cte": finding.cte,
            },
        ),
        FindingTraceCreate(
            finding_id=finding_id,
            audit_run_id=payload.audit_run_id,
            sequence=2,
            trace_type="approved_rule",
            title="Approved rule package obligation",
            payload_json={
                "approvedObligationId": finding.approved_obligation_id,
                "rulePackageId": payload.approved_rule_package_id,
                "rulePackageVersion": payload.approved_rule_package_version,
                "rulePackageHash": payload.approved_rule_package_hash,
                "citation": finding.source_citation,
            },
        ),
        FindingTraceCreate(
            finding_id=finding_id,
            audit_run_id=payload.audit_run_id,
            sequence=3,
            trace_type="deterministic_check",
            title="Deterministic approved-rule execution",
            payload_json={
                "checkCode": finding.finding_type,
                "checkVersion": payload.execution_version,
                "sourceFindingId": finding.finding_id,
                "ordinal": index,
                "approvedRuleOnly": True,
            },
        ),
    ]


def _upload_artifacts(
    *,
    payload: RuleExecutionJobPayload,
    artifacts: dict[str, str],
    object_store: ObjectStore,
    repositories: RuleExecutionRepositories,
) -> list[dict[str, Any]]:
    stored_rows: list[dict[str, Any]] = []
    for artifact_type, path_value in artifacts.items():
        path = Path(path_value)
        if not path.exists():
            continue
        data = path.read_bytes()
        storage_key = audit_artifact_key(
            customer_id=payload.customer_id,
            audit_project_id=payload.audit_project_id,
            audit_run_id=payload.audit_run_id,
            artifact_type=artifact_type,
            filename=path.name,
        )
        content_type = guess_content_type(path.name)
        stored = object_store.upload_bytes(
            bucket=payload.artifact_bucket,
            key=storage_key,
            data=data,
            content_type=content_type,
            upsert=True,
        )
        row = repositories.audit_files.create_artifact(
            AuditArtifactCreate(
                id=_stable_id("artifact", payload.audit_run_id, artifact_type, stored.key),
                audit_project_id=payload.audit_project_id,
                audit_run_id=payload.audit_run_id,
                artifact_type=artifact_type,
                file_name=path.name,
                content_type=stored.content_type,
                storage_bucket=stored.bucket,
                storage_key=stored.key,
                size_bytes=stored.size_bytes,
                artifact_hash=stored.sha256,
                metadata_json={
                    "executionVersion": payload.execution_version,
                    "approvedRuleOnly": True,
                    "sourceArtifactPath": str(path),
                },
            )
        )
        stored_rows.append(row or {"id": artifact_type})
    return stored_rows


def _write_optional_ftl_file(
    *,
    tmp_path: Path,
    object_store: ObjectStore,
    bucket: str | None,
    key: str | None,
    repositories: RuleExecutionRepositories | None = None,
) -> Path | None:
    # Explicit object-storage override wins (a pinned FTL snapshot for this run).
    if bucket and key:
        payload = object_store.download_bytes(bucket=bucket, key=key)
        path = tmp_path / "ftl-food-items.json"
        path.write_bytes(payload.data)
        return path
    # Source of truth: the approved Food Traceability List cards in Supabase. When FDA
    # updates the FTL (21 CFR 1.1465), the cards are re-approved and the engine follows —
    # no code edit. The bundled JSON is only an offline/dev fallback.
    if repositories is not None:
        try:
            ftl_items = repositories.regulatory.load_approved_card_payloads("ftl_food_items")
        except Exception:
            ftl_items = []
        if ftl_items:
            path = tmp_path / "ftl-food-items.json"
            path.write_text(json.dumps(ftl_items), encoding="utf-8")
            return path
    bundled = Path(__file__).resolve().parents[4] / "data/regulatory/intelligence/drafts/ftl-food-items.json"
    return bundled if bundled.exists() else None


def _write_optional_card_file(
    *,
    tmp_path: Path,
    repositories: RuleExecutionRepositories | None,
    collection: str,
    filename: str,
    build_document: Callable[[list[dict[str, Any]]], dict[str, Any]],
) -> Path | None:
    """Materialize a reviewable regulatory document (KDE contracts, exemption rules, plan
    components) for a run from the approved Supabase cards, so re-approvals flow through with no
    code edit. Returns None when no cards exist — the engine loader then falls back to the
    bundled copy that ships inside the package (traceready_ingestion/intelligence/bundled_rules)."""
    if repositories is not None:
        try:
            cards = repositories.regulatory.load_approved_card_payloads(collection)
        except Exception:
            cards = []
        if cards:
            path = tmp_path / filename
            path.write_text(json.dumps(build_document(cards)), encoding="utf-8")
            return path
    return None


def _readiness_status(package: Phase11RuleExecutionPackage) -> str:
    if package.export_package.status == "blocked":
        return "blocked"
    if package.audit_findings:
        return "needs_review"
    return "ready"


def _recommendation_for(finding: AuditFinding) -> str:
    if finding.finding_type == "kde_completeness":
        return "Capture and retain the missing KDE in the customer traceability record."
    if finding.finding_type == "tlc_lineage":
        return "Link source and output TLC values across the relevant traceability event."
    if finding.finding_type == "sortable_export_readiness":
        return "Populate missing fields before generating the FDA sortable spreadsheet export."
    return "Review the cited approved obligation and resolve the customer evidence gap."


def _safe_filename(filename: str) -> str:
    safe = Path(filename).name.replace("\\", "-").replace("/", "-")
    return safe or "customer-upload.csv"


def _db_finding_id(audit_run_id: str, source_finding_id: str) -> str:
    return _stable_id("finding", audit_run_id, source_finding_id)


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{sha256_text('|'.join(parts))[:24]}"
