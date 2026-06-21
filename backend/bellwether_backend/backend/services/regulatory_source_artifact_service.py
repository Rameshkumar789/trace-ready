from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from bellwether_backend.backend.repositories.supabase_tables import (
    RegulatoryRepository,
    RegulatorySourceUpsert,
    SourceChunkUpsert,
)
from bellwether_backend.storage.artifacts import (
    ObjectStore,
    StoredObject,
    guess_content_type,
    source_approval_artifact_key,
    source_chunk_package_key,
    source_draft_payload_key,
    source_normalized_key,
    source_raw_key,
)


@dataclass(frozen=True)
class NamedArtifactPayload:
    filename: str
    data: bytes
    content_type: str | None = None


@dataclass(frozen=True)
class DraftPayloadArtifact:
    draft_id: str
    filename: str
    data: bytes
    content_type: str | None = None


@dataclass(frozen=True)
class PersistedRegulatorySourceArtifacts:
    source_id: str
    version: int
    raw: StoredObject
    normalized: StoredObject
    chunk_package: StoredObject
    draft_payloads: list[StoredObject]
    approval_artifacts: list[StoredObject]
    source_row: dict | None
    chunk_rows: list[dict]


class RegulatorySourceArtifactRepositories:
    def __init__(self, regulatory: RegulatoryRepository):
        self.regulatory = regulatory


def persist_regulatory_source_artifacts(
    *,
    source: RegulatorySourceUpsert,
    source_version: int,
    chunks: Sequence[SourceChunkUpsert],
    raw_artifact: NamedArtifactPayload,
    normalized_artifact: NamedArtifactPayload,
    chunk_package: NamedArtifactPayload,
    object_store: ObjectStore,
    repositories: RegulatorySourceArtifactRepositories,
    bucket: str,
    draft_payloads: Sequence[DraftPayloadArtifact] = (),
    approval_artifacts: Sequence[NamedArtifactPayload] = (),
) -> PersistedRegulatorySourceArtifacts:
    raw = object_store.upload_bytes(
        bucket=bucket,
        key=source_raw_key(source_id=source.id, version=source_version, filename=raw_artifact.filename),
        data=raw_artifact.data,
        content_type=raw_artifact.content_type or guess_content_type(raw_artifact.filename),
        upsert=True,
    )
    normalized = object_store.upload_bytes(
        bucket=bucket,
        key=source_normalized_key(source_id=source.id, version=source_version, filename=normalized_artifact.filename),
        data=normalized_artifact.data,
        content_type=normalized_artifact.content_type or guess_content_type(normalized_artifact.filename),
        upsert=True,
    )
    chunk_package_object = object_store.upload_bytes(
        bucket=bucket,
        key=source_chunk_package_key(source_id=source.id, version=source_version, filename=chunk_package.filename),
        data=chunk_package.data,
        content_type=chunk_package.content_type or guess_content_type(chunk_package.filename),
        upsert=True,
    )
    draft_objects = [
        object_store.upload_bytes(
            bucket=bucket,
            key=source_draft_payload_key(
                source_id=source.id,
                version=source_version,
                draft_id=draft.draft_id,
                filename=draft.filename,
            ),
            data=draft.data,
            content_type=draft.content_type or guess_content_type(draft.filename),
            upsert=True,
        )
        for draft in draft_payloads
    ]
    approval_objects = [
        object_store.upload_bytes(
            bucket=bucket,
            key=source_approval_artifact_key(source_id=source.id, version=source_version, filename=artifact.filename),
            data=artifact.data,
            content_type=artifact.content_type or guess_content_type(artifact.filename),
            upsert=True,
        )
        for artifact in approval_artifacts
    ]

    source_row = repositories.regulatory.upsert_source(
        replace(
            source,
            raw_artifact_bucket=raw.bucket,
            raw_artifact_key=raw.key,
            normalized_artifact_bucket=normalized.bucket,
            normalized_artifact_key=normalized.key,
        )
    )
    chunk_rows = repositories.regulatory.upsert_chunks(
        [
            replace(
                chunk,
                raw_artifact_bucket=raw.bucket,
                raw_artifact_key=raw.key,
                normalized_artifact_bucket=normalized.bucket,
                normalized_artifact_key=normalized.key,
            )
            for chunk in chunks
        ]
    )
    return PersistedRegulatorySourceArtifacts(
        source_id=source.id,
        version=source_version,
        raw=raw,
        normalized=normalized,
        chunk_package=chunk_package_object,
        draft_payloads=draft_objects,
        approval_artifacts=approval_objects,
        source_row=source_row,
        chunk_rows=chunk_rows,
    )
