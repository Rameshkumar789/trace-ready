"""Bellwether core — request handlers (framework-agnostic).

The actual upload/read logic, decoupled from FastAPI so it's unit-testable without a web
server or DB. app.py is a thin FastAPI shell over these.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .domain import AuditResult
from .pipeline import run_audit_bytes
from .store import Store


def process_upload(
    *,
    store: Store,
    data: bytes,
    file_name: str,
    audit_project_id: str,
    rule_package_file: Path,
    ftl_food_items_file: Path | None = None,
    audit_file_id: str | None = None,
    run_number: int = 1,
    rule_package_id: str | None = None,
) -> dict[str, Any]:
    """Synchronous: create a run, audit the bytes inline, persist, return the summary."""
    run_id = f"run-{uuid.uuid4().hex[:16]}"
    store.create_run(
        run_id=run_id,
        audit_project_id=audit_project_id,
        audit_file_id=audit_file_id,
        run_number=run_number,
        rule_package_id=rule_package_id,
    )
    result: AuditResult = run_audit_bytes(
        data=data,
        file_name=file_name,
        rule_package_file=rule_package_file,
        ftl_food_items_file=ftl_food_items_file,
    )
    store.save_result(run_id=run_id, result=result)
    return {
        "run_id": run_id,
        "readiness_passed": result.readiness_passed,
        "summary": result.summary,
    }


def get_audit(*, store: Store, run_id: str) -> dict[str, Any] | None:
    run = store.get_run(run_id)
    if not run:
        return None
    return {
        "run": run,
        "findings": store.get_findings(run_id),
        "coverage": (run.get("summary_json") or {}).get("coverage", []),
        "scorecards": (run.get("summary_json") or {}).get("scorecards", []),
        "anomalies": (run.get("summary_json") or {}).get("anomalies", []),
    }
