"""Bellwether core — minimal FastAPI route (the new /v2 entry point).

Thin shell over handler.py. Synchronous: upload runs the audit inline and returns the run id.
Kept isolated from legacy api/main.py. FastAPI/supabase imports are lazy so the rest of the
core package stays importable (and unit-testable) without them installed.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
DEFAULT_FTL = ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json"


def _store():
    from supabase import create_client  # lazy import

    client = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    from .store import SupabaseStore

    return SupabaseStore(client)


def create_app():
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # lazy import

    from .handler import get_audit, process_upload

    app = FastAPI(title="Bellwether Core v2")

    @app.get("/v2/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v2/audits")
    async def create_audit(
        audit_project_id: str = Form(...),
        file: UploadFile = File(...),
    ) -> dict:
        data = await file.read()
        return process_upload(
            store=_store(),
            data=data,
            file_name=file.filename or "upload.xlsx",
            audit_project_id=audit_project_id,
            rule_package_file=DEFAULT_RULE_PACKAGE,
            ftl_food_items_file=DEFAULT_FTL,
        )

    @app.get("/v2/audits/{run_id}")
    def read_audit(run_id: str) -> dict:
        result = get_audit(store=_store(), run_id=run_id)
        if not result:
            raise HTTPException(status_code=404, detail="audit run not found")
        return result

    return app
