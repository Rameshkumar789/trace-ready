from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SourceVersion:
    source_version_id: str
    source_id: str
    version: int
    raw_text_hash: str
    normalized_text_hash: str
    created_at: str
    supersedes_version: int | None = None


def next_source_version(source_id: str, prior_versions: list[SourceVersion], raw_hash: str, normalized_hash: str) -> SourceVersion:
    latest = max((version.version for version in prior_versions), default=0)
    return SourceVersion(
        source_version_id=f"{source_id}-v{latest + 1}",
        source_id=source_id,
        version=latest + 1,
        raw_text_hash=raw_hash,
        normalized_text_hash=normalized_hash,
        created_at=datetime.now(timezone.utc).isoformat(),
        supersedes_version=latest or None,
    )
