"""Bellwether core — persistence adapter (thin DB edge).

Maps the pure AuditResult onto the lean schema. Two implementations:
  * InMemoryStore  — for tests and local dev (no DB needed).
  * SupabaseStore  — thin wrapper over the supabase-py client (the real edge).

The pipeline and handler depend only on the Store protocol, so the core stays DB-agnostic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol

from .domain import AuditResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store(Protocol):
    def create_run(self, *, run_id: str, audit_project_id: str, audit_file_id: str | None,
                   run_number: int, rule_package_id: str | None) -> None: ...
    def save_result(self, *, run_id: str, result: AuditResult) -> None: ...
    def get_run(self, run_id: str) -> dict[str, Any] | None: ...
    def get_findings(self, run_id: str) -> list[dict[str, Any]]: ...


def _finding_rows(run_id: str, result: AuditResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, f in enumerate(result.findings, start=1):
        rows.append({
            "id": f"{run_id}-f{index:04d}",
            "audit_run_id": run_id,
            "severity": f.severity,
            "status": f.status,
            "finding_type": f.finding_type,
            "title": f.title,
            "message": f.message,
            "event_id": f.event_id,
            "cte": f.cte,
            "field_or_kde": f.field_or_kde,
            "recommendation": f.recommendation,
            "citation_section": f.citation.section,
            "citation_scenario": f.citation.scenario,
            "citation_note": f.citation.note,
            "confidence": f.confidence,
            "evidence_ids_json": f.evidence_ids,
            "review_state": "pending",
        })
    return rows


def _run_summary(result: AuditResult) -> dict[str, Any]:
    # Coverage / scorecards / anomalies are aggregations — stored on the run, not as tables.
    return {
        **result.summary,
        "coverage": [c.model_dump() for c in result.coverage],
        "scorecards": [s.model_dump() for s in result.scorecards],
        "anomalies": [a.model_dump() for a in result.anomalies],
    }


class InMemoryStore:
    """A dict-backed Store for tests/local dev."""

    def __init__(self) -> None:
        self.runs: dict[str, dict[str, Any]] = {}
        self.findings: dict[str, list[dict[str, Any]]] = {}

    def create_run(self, *, run_id, audit_project_id, audit_file_id, run_number, rule_package_id) -> None:
        self.runs[run_id] = {
            "id": run_id, "audit_project_id": audit_project_id, "audit_file_id": audit_file_id,
            "run_number": run_number, "rule_package_id": rule_package_id,
            "status": "pending", "summary_json": {}, "created_at": _now(),
        }
        self.findings[run_id] = []

    def save_result(self, *, run_id, result) -> None:
        run = self.runs.setdefault(run_id, {"id": run_id})
        run.update({
            "status": "succeeded",
            "readiness_passed": result.readiness_passed,
            "summary_json": _run_summary(result),
            "completed_at": _now(),
        })
        self.findings[run_id] = _finding_rows(run_id, result)

    def get_run(self, run_id):
        return self.runs.get(run_id)

    def get_findings(self, run_id):
        return self.findings.get(run_id, [])


class SupabaseStore:
    """Thin wrapper over a supabase-py client (the production edge)."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def create_run(self, *, run_id, audit_project_id, audit_file_id, run_number, rule_package_id) -> None:
        self.client.table("audit_runs").insert({
            "id": run_id, "audit_project_id": audit_project_id, "audit_file_id": audit_file_id,
            "run_number": run_number, "rule_package_id": rule_package_id, "status": "pending",
        }).execute()

    def save_result(self, *, run_id, result) -> None:
        self.client.table("audit_runs").update({
            "status": "succeeded",
            "readiness_passed": result.readiness_passed,
            "summary_json": _run_summary(result),
            "completed_at": _now(),
        }).eq("id", run_id).execute()
        rows = _finding_rows(run_id, result)
        # findings are run-scoped + immutable; clear any prior rows then insert.
        self.client.table("findings").delete().eq("audit_run_id", run_id).execute()
        if rows:
            self.client.table("findings").insert(rows).execute()

    def get_run(self, run_id):
        res = self.client.table("audit_runs").select("*").eq("id", run_id).limit(1).execute()
        data = getattr(res, "data", None) or []
        return data[0] if data else None

    def get_findings(self, run_id):
        res = self.client.table("findings").select("*").eq("audit_run_id", run_id).execute()
        return getattr(res, "data", None) or []
