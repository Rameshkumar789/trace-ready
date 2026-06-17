from __future__ import annotations

import mimetypes
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from traceready_ingestion.api.config import ObjectStoreMode, RuntimeEnvironment, ServiceSettings
from traceready_ingestion.versioning.hashing import sha256_bytes


def write_artifact(root: Path, name: str, content: str | bytes) -> str:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return str(path)


class ObjectStorageError(RuntimeError):
    pass


class NonDurableObjectStoreError(ObjectStorageError):
    pass


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    size_bytes: int
    sha256: str
    content_type: str


@dataclass(frozen=True)
class ObjectPayload:
    data: bytes
    size_bytes: int
    sha256: str
    content_type: str | None = None


class ObjectStore(Protocol):
    def upload_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
        upsert: bool = False,
    ) -> StoredObject:
        ...

    def download_bytes(self, *, bucket: str, key: str) -> ObjectPayload:
        ...

    def list_keys(self, *, bucket: str, prefix: str) -> list[str]:
        ...


def capture_payload(data: bytes, content_type: str | None = None) -> ObjectPayload:
    return ObjectPayload(
        data=data,
        size_bytes=len(data),
        sha256=sha256_bytes(data),
        content_type=content_type,
    )


def guess_content_type(filename_or_key: str, fallback: str = "application/octet-stream") -> str:
    guessed, _encoding = mimetypes.guess_type(filename_or_key)
    return guessed or fallback


def source_raw_key(*, source_id: str, version: int, filename: str) -> str:
    return join_object_key(
        "regulatory",
        "sources",
        source_id,
        "versions",
        str(version),
        "raw",
        filename,
    )


def source_normalized_key(*, source_id: str, version: int, filename: str) -> str:
    return join_object_key(
        "regulatory",
        "sources",
        source_id,
        "versions",
        str(version),
        "normalized",
        filename,
    )


def source_chunk_package_key(*, source_id: str, version: int, filename: str = "source-chunks.json") -> str:
    return join_object_key(
        "regulatory",
        "sources",
        source_id,
        "versions",
        str(version),
        "chunks",
        filename,
    )


def source_draft_payload_key(*, source_id: str, version: int, draft_id: str, filename: str = "draft-payload.json") -> str:
    return join_object_key(
        "regulatory",
        "sources",
        source_id,
        "versions",
        str(version),
        "drafts",
        draft_id,
        filename,
    )


def source_approval_artifact_key(*, source_id: str, version: int, filename: str) -> str:
    return join_object_key(
        "regulatory",
        "sources",
        source_id,
        "versions",
        str(version),
        "approval",
        filename,
    )


def regulatory_package_key(*, package_id: str, version: int, filename: str) -> str:
    return join_object_key("regulatory", "packages", package_id, "versions", str(version), filename)


def audit_upload_key(
    *,
    customer_id: str,
    audit_project_id: str,
    audit_run_id: str,
    filename: str,
) -> str:
    return join_object_key(
        "customers",
        customer_id,
        "audits",
        audit_project_id,
        "runs",
        audit_run_id,
        "uploads",
        filename,
    )


def audit_artifact_key(
    *,
    customer_id: str,
    audit_project_id: str,
    audit_run_id: str,
    artifact_type: str,
    filename: str,
) -> str:
    return join_object_key(
        "customers",
        customer_id,
        "audits",
        audit_project_id,
        "runs",
        audit_run_id,
        "artifacts",
        artifact_type,
        filename,
    )


def join_object_key(*segments: str) -> str:
    cleaned: list[str] = []
    for segment in segments:
        cleaned.extend(_clean_segment(segment))
    if not cleaned:
        raise ValueError("Object key must include at least one segment.")
    return "/".join(cleaned)


def _clean_segment(segment: str) -> list[str]:
    raw = str(segment).replace("\\", "/").strip("/")
    if not raw:
        raise ValueError("Object key segment cannot be empty.")

    parts: list[str] = []
    for part in raw.split("/"):
        stripped = part.strip()
        if not stripped or stripped in {".", ".."}:
            raise ValueError(f"Unsafe object key segment: {segment!r}")
        safe = re.sub(r"[^A-Za-z0-9._=-]+", "-", stripped).strip("-")
        if not safe or safe in {".", ".."}:
            raise ValueError(f"Unsafe object key segment: {segment!r}")
        parts.append(safe)
    return parts


def _is_production_like(environ: Mapping[str, str]) -> bool:
    env = environ.get("TRACEREADY_ENV") or environ.get("VERCEL_ENV")
    return env != "test"


class LocalObjectStore:
    def __init__(self, root: Path, *, environ: Mapping[str, str] | None = None):
        env = os.environ if environ is None else environ
        if _is_production_like(env):
            raise NonDurableObjectStoreError(
                "LocalObjectStore is test-only. Use SupabaseObjectStore for runtime."
            )
        self.root = root

    def upload_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
        upsert: bool = False,
    ) -> StoredObject:
        safe_key = join_object_key(key)
        target = self._resolve(bucket, safe_key)
        if target.exists() and not upsert:
            raise ObjectStorageError(f"Object already exists: {bucket}/{safe_key}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return StoredObject(
            bucket=bucket,
            key=safe_key,
            size_bytes=len(data),
            sha256=sha256_bytes(data),
            content_type=content_type or guess_content_type(safe_key),
        )

    def download_bytes(self, *, bucket: str, key: str) -> ObjectPayload:
        safe_key = join_object_key(key)
        data = self._resolve(bucket, safe_key).read_bytes()
        return capture_payload(data, guess_content_type(safe_key))

    def list_keys(self, *, bucket: str, prefix: str) -> list[str]:
        safe_prefix = join_object_key(prefix)
        base = self._resolve(bucket, safe_prefix)
        if base.is_file():
            return [safe_prefix]
        if not base.exists():
            return []
        bucket_root = self._bucket_root(bucket).resolve()
        return sorted(
            path.resolve().relative_to(bucket_root).as_posix()
            for path in base.rglob("*")
            if path.is_file()
        )

    def _bucket_root(self, bucket: str) -> Path:
        return self.root / join_object_key(bucket)

    def _resolve(self, bucket: str, key: str) -> Path:
        bucket_root = self._bucket_root(bucket).resolve()
        target = (bucket_root / key).resolve()
        if bucket_root != target and bucket_root not in target.parents:
            raise ObjectStorageError("Resolved object path escaped the storage root.")
        return target


class SupabaseObjectStore:
    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: str,
        client: object | None = None,
    ):
        if not supabase_url:
            raise ObjectStorageError("Supabase URL is required.")
        if not service_role_key:
            raise ObjectStorageError("Supabase service-role key is required.")
        self._client = client or self._create_client(supabase_url, service_role_key)

    def upload_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
        upsert: bool = False,
    ) -> StoredObject:
        safe_key = join_object_key(key)
        resolved_content_type = content_type or guess_content_type(safe_key)
        storage_bucket = self._client.storage.from_(bucket)
        storage_bucket.upload(
            path=safe_key,
            file=data,
            file_options={
                "content-type": resolved_content_type,
                "upsert": "true" if upsert else "false",
            },
        )
        return StoredObject(
            bucket=bucket,
            key=safe_key,
            size_bytes=len(data),
            sha256=sha256_bytes(data),
            content_type=resolved_content_type,
        )

    def download_bytes(self, *, bucket: str, key: str) -> ObjectPayload:
        safe_key = join_object_key(key)
        payload = self._client.storage.from_(bucket).download(safe_key)
        if isinstance(payload, str):
            data = payload.encode("utf-8")
        else:
            data = bytes(payload)
        return capture_payload(data, guess_content_type(safe_key))

    def list_keys(self, *, bucket: str, prefix: str) -> list[str]:
        safe_prefix = join_object_key(prefix)
        objects = self._client.storage.from_(bucket).list(path=safe_prefix)
        return _extract_supabase_keys(safe_prefix, objects)

    @staticmethod
    def _create_client(supabase_url: str, service_role_key: str) -> object:
        try:
            from supabase import create_client
        except ModuleNotFoundError as exc:
            raise ObjectStorageError(
                "supabase is required for production object storage. Install the ingestion package dependencies."
            ) from exc
        return create_client(supabase_url, service_role_key)


def build_object_store(settings: ServiceSettings) -> ObjectStore:
    if settings.effective_object_store_mode == ObjectStoreMode.LOCAL:
        if settings.environment != RuntimeEnvironment.TEST:
            raise ObjectStorageError("Local object storage is test-only. Configure Supabase storage for runtime use.")
        return LocalObjectStore(
            Path(settings.local_object_store_root),
            environ={
                "TRACEREADY_ENV": settings.environment.value,
            },
        )

    if not settings.supabase_url:
        raise ObjectStorageError("NEXT_PUBLIC_SUPABASE_URL is required.")
    if not settings.supabase_service_role_key:
        raise ObjectStorageError("SUPABASE_SERVICE_ROLE_KEY is required.")
    return SupabaseObjectStore(
        supabase_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
    )


def _extract_supabase_keys(prefix: str, objects: Sequence[object]) -> list[str]:
    keys: list[str] = []
    for obj in objects:
        name: str | None = None
        if isinstance(obj, Mapping):
            raw_name = obj.get("name")
            name = str(raw_name) if raw_name else None
        else:
            raw_name = getattr(obj, "name", None)
            name = str(raw_name) if raw_name else None
        if name:
            keys.append(join_object_key(prefix, name))
    return sorted(keys)
