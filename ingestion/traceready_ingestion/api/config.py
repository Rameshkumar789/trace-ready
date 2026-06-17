from __future__ import annotations

import os
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class RuntimeEnvironment(str, Enum):
    LOCAL = "local"
    TEST = "test"
    PREVIEW = "preview"
    PRODUCTION = "production"


class ObjectStoreMode(str, Enum):
    LOCAL = "local"
    SUPABASE = "supabase"


class ServiceSettings(BaseModel):
    service_name: str = "traceready-python-backend"
    service_version: str = "0.1.0"
    environment: RuntimeEnvironment = RuntimeEnvironment.LOCAL
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "traceready-private"
    object_store_mode: ObjectStoreMode | None = None
    local_object_store_root: str = ".traceready-object-store"
    internal_api_token: str | None = None
    require_configured_dependencies: bool = False
    allowed_origins: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def dependency_config_required(self) -> bool:
        return self.require_configured_dependencies or self.environment != RuntimeEnvironment.TEST

    @property
    def effective_object_store_mode(self) -> ObjectStoreMode:
        if self.environment == RuntimeEnvironment.TEST and self.object_store_mode:
            return self.object_store_mode
        return ObjectStoreMode.SUPABASE


def _read_bool(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _read_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _read_environment(environ: Mapping[str, str]) -> RuntimeEnvironment:
    explicit = environ.get("TRACEREADY_ENV")
    vercel_env = environ.get("VERCEL_ENV")
    value = explicit or vercel_env or RuntimeEnvironment.LOCAL.value
    if value == "development":
        value = RuntimeEnvironment.LOCAL.value
    try:
        return RuntimeEnvironment(value)
    except ValueError:
        return RuntimeEnvironment.LOCAL


def load_settings(environ: Mapping[str, str] | None = None) -> ServiceSettings:
    env = _environment_with_local_dotenv(os.environ) if environ is None else environ
    return ServiceSettings(
        environment=_read_environment(env),
        database_url=env.get("SUPABASE_DATABASE_URL"),
        supabase_url=env.get("NEXT_PUBLIC_SUPABASE_URL"),
        supabase_service_role_key=env.get("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_storage_bucket=env.get("TRACEREADY_STORAGE_BUCKET", "traceready-private"),
        object_store_mode=_read_object_store_mode(env),
        local_object_store_root=env.get("TRACEREADY_LOCAL_OBJECT_STORE_ROOT", ".traceready-object-store"),
        internal_api_token=env.get("TRACEREADY_INTERNAL_API_TOKEN"),
        require_configured_dependencies=_read_bool(
            env.get("TRACEREADY_REQUIRE_CONFIGURED_DEPENDENCIES")
        ),
        allowed_origins=_read_csv(env.get("TRACEREADY_ALLOWED_ORIGINS")),
    )


def get_settings(request: Any) -> ServiceSettings:
    return request.app.state.settings


def _environment_with_local_dotenv(environ: Mapping[str, str]) -> Mapping[str, str]:
    dotenv_values: dict[str, str] = {}
    for path in _local_dotenv_candidates():
        dotenv_values.update(_read_dotenv_file(path))
    return {**dotenv_values, **dict(environ)}


def _local_dotenv_candidates() -> tuple[Path, ...]:
    ingestion_root = Path(__file__).resolve().parents[2]
    cwd = Path.cwd()
    candidates = [
        cwd / ".env",
        cwd / "ingestion" / ".env",
        ingestion_root / ".env",
    ]
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return tuple(unique)


def _read_dotenv_file(path: Path) -> dict[str, str]:
    if not path.exists() or not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_dotenv_quotes(value.strip())
    return values


def _strip_dotenv_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _read_object_store_mode(environ: Mapping[str, str]) -> ObjectStoreMode | None:
    raw = environ.get("TRACEREADY_OBJECT_STORE_MODE")
    if not raw:
        return None
    try:
        return ObjectStoreMode(raw)
    except ValueError:
        return None
