from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from traceready_backend.storage.artifacts import ObjectStore, source_chunk_package_key
@dataclass(frozen=True)
class SourceIntegrityIssue:
    severity: str
    code: str
    message: str
    source_id: str | None = None
    chunk_id: str | None = None
    object_key: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class SourceArtifactIntegrityReport:
    status: str
    summary: dict[str, int]
    issues: list[SourceIntegrityIssue]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def check_source_artifact_integrity(
    *,
    repository: object,
    object_store: ObjectStore,
    default_bucket: str,
    source_version: int = 1,
    limit: int | None = None,
) -> SourceArtifactIntegrityReport:
    sources = repository.list_sources_for_integrity(limit=limit)
    source_ids = [str(source.get("id")) for source in sources if source.get("id")]
    chunks = repository.list_chunks_for_integrity(source_ids=source_ids if source_ids else None)
    chunks_by_source: dict[str, list[Mapping[str, object]]] = {}
    issues: list[SourceIntegrityIssue] = []

    for chunk in chunks:
        source_id = _string(chunk.get("regulatory_source_id"))
        if source_id:
            chunks_by_source.setdefault(source_id, []).append(chunk)

    source_by_id = {_string(source.get("id")): source for source in sources if _string(source.get("id"))}
    for source in sources:
        source_id = _string(source.get("id")) or "unknown-source"
        source_chunks = chunks_by_source.get(source_id, [])
        issues.extend(_validate_source_row(source))
        issues.extend(
            _validate_source_objects(
                source=source,
                object_store=object_store,
                default_bucket=default_bucket,
            )
        )
        issues.extend(
            _validate_chunk_package(
                source_id=source_id,
                source_chunks=source_chunks,
                object_store=object_store,
                default_bucket=default_bucket,
                source_version=source_version,
            )
        )
        if not source_chunks:
            issues.append(
                SourceIntegrityIssue(
                    severity="error",
                    code="source_has_no_chunks",
                    message="Regulatory source has no source_chunks rows.",
                    source_id=source_id,
                )
            )

    for chunk in chunks:
        source_id = _string(chunk.get("regulatory_source_id"))
        chunk_id = _string(chunk.get("id")) or _string(chunk.get("chunk_code"))
        if source_id not in source_by_id:
            issues.append(
                SourceIntegrityIssue(
                    severity="error",
                    code="chunk_missing_source",
                    message="Source chunk references a missing regulatory source row.",
                    source_id=source_id,
                    chunk_id=chunk_id,
                )
            )
        issues.extend(_validate_chunk_row(chunk))

    summary = {
        "sourceCount": len(sources),
        "chunkCount": len(chunks),
        "sourceObjectCount": sum(1 for source in sources if source.get("raw_artifact_key") and source.get("normalized_artifact_key")),
        "chunkPackageCount": len(sources) - sum(1 for issue in issues if issue.code == "chunk_package_unreachable"),
        "errorCount": sum(1 for issue in issues if issue.severity == "error"),
        "warningCount": sum(1 for issue in issues if issue.severity == "warning"),
    }
    return SourceArtifactIntegrityReport(
        status="pass" if summary["errorCount"] == 0 else "fail",
        summary=summary,
        issues=issues,
    )


def _validate_source_row(source: Mapping[str, object]) -> list[SourceIntegrityIssue]:
    source_id = _string(source.get("id")) or "unknown-source"
    issues: list[SourceIntegrityIssue] = []
    for field_name, code in (
        ("url", "source_missing_url"),
        ("text_hash", "source_missing_hash"),
        ("raw_artifact_key", "source_missing_raw_artifact_key"),
        ("normalized_artifact_key", "source_missing_normalized_artifact_key"),
    ):
        if not _string(source.get(field_name)):
            issues.append(
                SourceIntegrityIssue(
                    severity="error",
                    code=code,
                    message=f"Regulatory source is missing {field_name}.",
                    source_id=source_id,
                )
            )
    return issues


def _validate_source_objects(
    *,
    source: Mapping[str, object],
    object_store: ObjectStore,
    default_bucket: str,
) -> list[SourceIntegrityIssue]:
    source_id = _string(source.get("id")) or "unknown-source"
    issues: list[SourceIntegrityIssue] = []
    raw_payload = _download(
        object_store=object_store,
        bucket=_string(source.get("raw_artifact_bucket")) or default_bucket,
        key=_string(source.get("raw_artifact_key")),
        source_id=source_id,
        code="raw_artifact_unreachable",
        label="raw artifact",
    )
    if isinstance(raw_payload, SourceIntegrityIssue):
        issues.append(raw_payload)
    else:
        expected_hash = _normalize_sha256(_string(source.get("text_hash")))
        if expected_hash and raw_payload.sha256 != expected_hash:
            issues.append(
                SourceIntegrityIssue(
                    severity="error",
                    code="raw_artifact_hash_mismatch",
                    message="Raw artifact SHA-256 does not match the regulatory source hash.",
                    source_id=source_id,
                    object_key=_string(source.get("raw_artifact_key")),
                )
            )

    normalized_payload = _download(
        object_store=object_store,
        bucket=_string(source.get("normalized_artifact_bucket")) or default_bucket,
        key=_string(source.get("normalized_artifact_key")),
        source_id=source_id,
        code="normalized_artifact_unreachable",
        label="normalized artifact",
    )
    if isinstance(normalized_payload, SourceIntegrityIssue):
        issues.append(normalized_payload)
    return issues


def _validate_chunk_package(
    *,
    source_id: str,
    source_chunks: Sequence[Mapping[str, object]],
    object_store: ObjectStore,
    default_bucket: str,
    source_version: int,
) -> list[SourceIntegrityIssue]:
    key = source_chunk_package_key(source_id=source_id, version=source_version)
    payload = _download(
        object_store=object_store,
        bucket=default_bucket,
        key=key,
        source_id=source_id,
        code="chunk_package_unreachable",
        label="source chunk package",
    )
    if isinstance(payload, SourceIntegrityIssue):
        return [payload]
    try:
        package = json.loads(payload.data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [
            SourceIntegrityIssue(
                severity="error",
                code="chunk_package_invalid_json",
                message="Source chunk package artifact is not valid JSON.",
                source_id=source_id,
                object_key=key,
            )
        ]
    if not isinstance(package, list):
        return [
            SourceIntegrityIssue(
                severity="error",
                code="chunk_package_invalid_shape",
                message="Source chunk package artifact must be a JSON array.",
                source_id=source_id,
                object_key=key,
            )
        ]
    if len(package) != len(source_chunks):
        return [
            SourceIntegrityIssue(
                severity="error",
                code="chunk_package_count_mismatch",
                message=f"Chunk package has {len(package)} chunks but DB has {len(source_chunks)} chunks for the source.",
                source_id=source_id,
                object_key=key,
            )
        ]
    issues: list[SourceIntegrityIssue] = []
    chunks_by_id = {
        _string(chunk.get("id")) or _string(chunk.get("chunk_code")): chunk
        for chunk in source_chunks
    }
    for item in package:
        if not isinstance(item, Mapping):
            continue
        chunk_id = _string(item.get("chunk_id")) or _string(item.get("id"))
        row = chunks_by_id.get(chunk_id)
        if not row:
            issues.append(
                SourceIntegrityIssue(
                    severity="error",
                    code="chunk_package_row_missing",
                    message="Source chunk package includes a chunk that is missing from DB rows.",
                    source_id=source_id,
                    chunk_id=chunk_id,
                    object_key=key,
                )
            )
            continue
        package_hash = _string(item.get("text_hash"))
        if package_hash and _string(row.get("text_hash")) != package_hash:
            issues.append(
                SourceIntegrityIssue(
                    severity="error",
                    code="chunk_package_hash_mismatch",
                    message="DB source chunk hash does not match the seeded chunk package hash.",
                    source_id=source_id,
                    chunk_id=chunk_id,
                    object_key=key,
                )
            )
        package_text = _string(item.get("text"))
        if package_text and _string(row.get("text")) != package_text:
            issues.append(
                SourceIntegrityIssue(
                    severity="error",
                    code="chunk_package_text_mismatch",
                    message="DB source chunk text does not match the seeded chunk package text.",
                    source_id=source_id,
                    chunk_id=chunk_id,
                    object_key=key,
                )
            )
    if issues:
        return issues
    return []


def _validate_chunk_row(chunk: Mapping[str, object]) -> list[SourceIntegrityIssue]:
    source_id = _string(chunk.get("regulatory_source_id"))
    chunk_id = _string(chunk.get("id")) or _string(chunk.get("chunk_code"))
    issues: list[SourceIntegrityIssue] = []
    for field_name, code in (
        ("text", "chunk_missing_text"),
        ("text_hash", "chunk_missing_hash"),
        ("citation", "chunk_missing_citation"),
    ):
        if not _string(chunk.get(field_name)):
            issues.append(
                SourceIntegrityIssue(
                    severity="error",
                    code=code,
                    message=f"Source chunk is missing {field_name}.",
                    source_id=source_id,
                    chunk_id=chunk_id,
                )
            )
    if not (_string(chunk.get("citation_anchor")) or _string(chunk.get("section_ref")) or _string(chunk.get("source_location"))):
        issues.append(
            SourceIntegrityIssue(
                severity="error",
                code="chunk_missing_citation_anchor",
                message="Source chunk is missing citation anchor coverage.",
                source_id=source_id,
                chunk_id=chunk_id,
            )
        )

    return issues


def _download(
    *,
    object_store: ObjectStore,
    bucket: str,
    key: str | None,
    source_id: str,
    code: str,
    label: str,
) -> object:
    if not key:
        return SourceIntegrityIssue(
            severity="error",
            code=code,
            message=f"Cannot reach {label} because object key is missing.",
            source_id=source_id,
        )
    try:
        return object_store.download_bytes(bucket=bucket, key=key)
    except Exception as exc:
        return SourceIntegrityIssue(
            severity="error",
            code=code,
            message=f"Cannot download {label}: {exc}",
            source_id=source_id,
            object_key=key,
        )


def _normalize_sha256(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.removeprefix("sha256:").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", cleaned):
        return cleaned
    return None


def _string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
