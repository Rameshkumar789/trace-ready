from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from traceready_ingestion.backend.repositories.supabase_tables import RegulatoryRepository, RegulatorySourceUpsert, SourceChunkUpsert
from traceready_ingestion.backend.services.regulatory_source_artifact_service import (
    NamedArtifactPayload,
    RegulatorySourceArtifactRepositories,
    persist_regulatory_source_artifacts,
)
from traceready_ingestion.storage.artifacts import ObjectStore, guess_content_type
from traceready_ingestion.versioning.hashing import sha256_text


@dataclass(frozen=True)
class RegulatorySeedImportResult:
    source_count: int
    chunk_count: int
    raw_artifact_count: int
    normalized_artifact_count: int
    chunk_package_count: int
    skipped_sources: list[str]


def import_regulatory_registry_seed(
    *,
    regulatory_dir: Path,
    object_store: ObjectStore,
    repository: RegulatoryRepository,
    bucket: str,
    source_version: int = 1,
) -> RegulatorySeedImportResult:
    registry_dir = regulatory_dir / "registry"
    sources = _read_json_list(registry_dir / "sources.json")
    chunks = _read_json_list(registry_dir / "source-chunks.json")
    chunks_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        chunks_by_source[str(chunk.get("source_id") or "")].append(chunk)

    skipped: list[str] = []
    imported_sources = 0
    imported_chunks = 0
    for source in sources:
        source_id = str(source.get("source_id") or "")
        raw_path = _resolve_registry_path(regulatory_dir, source.get("raw_artifact_path"))
        normalized_path = _resolve_registry_path(regulatory_dir, source.get("normalized_artifact_path"))
        if not source_id or not raw_path or not normalized_path or not raw_path.exists() or not normalized_path.exists():
            skipped.append(source_id or "<missing-source-id>")
            continue
        source_chunks = chunks_by_source.get(source_id, [])
        chunk_rows = [_chunk_upsert(chunk) for chunk in source_chunks]
        persist_regulatory_source_artifacts(
            source=_source_upsert(source, raw_path),
            source_version=source_version,
            chunks=chunk_rows,
            raw_artifact=_payload(raw_path),
            normalized_artifact=_payload(normalized_path),
            chunk_package=NamedArtifactPayload(
                filename="source-chunks.json",
                data=json.dumps(source_chunks, indent=2).encode("utf-8"),
                content_type="application/json",
            ),
            object_store=object_store,
            repositories=RegulatorySourceArtifactRepositories(repository),
            bucket=bucket,
        )
        imported_sources += 1
        imported_chunks += len(chunk_rows)

    return RegulatorySeedImportResult(
        source_count=imported_sources,
        chunk_count=imported_chunks,
        raw_artifact_count=imported_sources,
        normalized_artifact_count=imported_sources,
        chunk_package_count=imported_sources,
        skipped_sources=skipped,
    )


def _source_upsert(source: dict[str, Any], raw_path: Path) -> RegulatorySourceUpsert:
    source_id = str(source["source_id"])
    return RegulatorySourceUpsert(
        id=source_id,
        title=str(source.get("title") or source_id),
        source_type=str(source.get("source_type") or "unknown"),
        source_status=str(source.get("source_status") or "ingested"),
        authority_rank=str(source.get("authority_rank") or "support"),
        url=str(source.get("url") or ""),
        citation=str(source.get("title") or source_id),
        retrieved_at=_parse_datetime(source.get("retrieved_at")),
        text_hash=str(source.get("raw_hash") or sha256_text(raw_path.read_text(encoding="utf-8", errors="ignore"))),
        effective_date=_parse_optional_datetime(source.get("effective_date")),
        compliance_date=_parse_optional_datetime(source.get("compliance_date")),
        is_finalized=str(source.get("source_status") or "") != "failed",
        summary=f"{source.get('sections_extracted', 0)} sections; {source.get('chunks_count', 0)} chunks",
        notes="; ".join(str(note) for note in source.get("notes") or []) or None,
    )


def _chunk_upsert(chunk: dict[str, Any]) -> SourceChunkUpsert:
    chunk_id = str(chunk["chunk_id"])
    return SourceChunkUpsert(
        id=chunk_id,
        regulatory_source_id=str(chunk["source_id"]),
        chunk_code=chunk_id,
        section_label=str(chunk.get("section_label") or "Document"),
        source_location=str(chunk.get("section_ref") or chunk.get("citation_anchor") or "document"),
        section_ref=str(chunk.get("section_ref") or ""),
        page_number=chunk.get("page_number") if isinstance(chunk.get("page_number"), int) else None,
        text=str(chunk.get("text") or ""),
        summary=str(chunk.get("section_label") or chunk.get("citation_anchor") or "Document chunk"),
        citation=str(chunk.get("citation_anchor") or chunk.get("section_ref") or "document"),
        citation_anchor=str(chunk.get("citation_anchor") or ""),
        text_hash=str(chunk.get("text_hash") or sha256_text(str(chunk.get("text") or ""))),
        authority_rank=str(chunk.get("authority_rank") or ""),
        source_url=str(chunk.get("source_url") or ""),
        source_type=str(chunk.get("source_type") or ""),
        usage_role=str(chunk.get("usage_role") or "extraction"),
        quality_flags_json=chunk.get("quality_flags") or [],
        status="approved_for_extraction",
    )


def _payload(path: Path) -> NamedArtifactPayload:
    return NamedArtifactPayload(
        filename=path.name,
        data=path.read_bytes(),
        content_type=_seed_content_type(path.name),
    )


def _seed_content_type(filename: str) -> str:
    content_type = guess_content_type(filename)
    if content_type == "text/html":
        return "text/plain"
    return content_type


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array: {path}")
    return [item for item in data if isinstance(item, dict)]


def _resolve_registry_path(regulatory_dir: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    normalized = value.replace("\\", "/")
    marker = "data/regulatory/"
    if marker in normalized:
        return regulatory_dir / normalized.split(marker, 1)[1]
    for candidate in (Path.cwd() / path, regulatory_dir / path, regulatory_dir.parent.parent / path):
        if candidate.exists():
            return candidate
    return regulatory_dir / path


def _parse_datetime(value: object) -> datetime:
    parsed = _parse_optional_datetime(value)
    return parsed or datetime.now(UTC)


def _parse_optional_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value or value == "local-file":
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
