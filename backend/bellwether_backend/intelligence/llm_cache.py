"""Persistent file cache for verified LLM perception outputs.

Only deterministically verified LLM outputs are ever written here, so a cache hit is as
trustworthy as a fresh verified call. Entries live under ``data/llm-cache/<namespace>/``
(committed to git so demo runs are reproducible) and the directory can be overridden with
``BELLWETHER_LLM_CACHE_DIR``. Cache keys embed a prompt-version literal so prompt edits
invalidate cleanly.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SAFE_NAMESPACE = re.compile(r"^[a-z0-9_\-]+$")


def default_cache_root() -> Path:
    env_dir = os.getenv("BELLWETHER_LLM_CACHE_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    # backend/bellwether_backend/intelligence/llm_cache.py -> repo root is parents[3]
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "data" / "llm-cache"


def cache_key(*parts: str) -> str:
    joined = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class LLMCache:
    """Content-addressed store: <root>/<namespace>/<key>.json."""

    def __init__(self, root: Path | None = None):
        self.root = root or default_cache_root()

    def _entry_path(self, namespace: str, key: str) -> Path:
        if not _SAFE_NAMESPACE.match(namespace):
            raise ValueError(f"invalid llm cache namespace: {namespace!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", key):
            raise ValueError("llm cache keys must be sha256 hex digests")
        return self.root / namespace / f"{key}.json"

    def get(self, namespace: str, key: str) -> list[dict[str, Any]] | None:
        path = self._entry_path(namespace, key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        items = entry.get("items")
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            return None
        return items

    def put(
        self,
        namespace: str,
        key: str,
        items: list[dict[str, Any]],
        *,
        model: str | None,
        request_sha256: str = "",
        method: str = "llm_live",
    ) -> None:
        path = self._entry_path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "namespace": namespace,
            "key": key,
            "model": model,
            "method": method,
            "request_sha256": request_sha256,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
        }
        path.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def delete(self, namespace: str, key: str) -> None:
        path = self._entry_path(namespace, key)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
