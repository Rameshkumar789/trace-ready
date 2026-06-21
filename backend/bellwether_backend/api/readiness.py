from __future__ import annotations

from typing import Any

from bellwether_backend.api.config import ServiceSettings


def build_readiness_report(settings: ServiceSettings) -> dict[str, Any]:
    checks = [
        {
            "name": "supabase_database_url",
            "status": "configured" if settings.database_url else "missing",
            "required": settings.dependency_config_required,
        },
        {
            "name": "supabase_url",
            "status": "configured" if settings.supabase_url else "missing",
            "required": settings.dependency_config_required,
        },
        {
            "name": "supabase_service_role_key",
            "status": "configured" if settings.supabase_service_role_key else "missing",
            "required": settings.dependency_config_required,
        },
        {
            "name": "supabase_storage_bucket",
            "status": "configured" if settings.supabase_storage_bucket else "missing",
            "required": True,
        },
        {
            "name": "object_store_mode",
            "status": "configured",
            "value": settings.effective_object_store_mode.value,
            "required": True,
        },
        {
            "name": "internal_api_token",
            "status": "configured" if settings.internal_api_token else "missing",
            "required": settings.dependency_config_required,
        },
    ]
    blocking = [check for check in checks if check["required"] and check["status"] != "configured"]
    return {
        "status": "ready" if not blocking else "not_ready",
        "environment": settings.environment.value,
        "checks": checks,
    }
