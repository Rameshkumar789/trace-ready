"""Reviewer-feedback flywheel (accuracy roadmap WS4, storage layer).

Every human decision should make the next audit smarter instead of being thrown away.
Confirmed labels are stored as JSONL (one decision per line, append-only, committed like the
LLM cache) and consulted BEFORE cache and model: a reviewer's confirmation is the strongest
evidence tier and auto-resolves the same question next time.

Current label kinds:
- ``ftl_tier``: {product signature -> tier, matched_commodity} (feeds classify_products)
- ``finding_verdict``: {finding fingerprint -> confirmed|rejected} (feeds future noise
  suppression and the gold set)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bellwether_backend.intelligence.llm_cache import cache_key, default_cache_root


def labels_path() -> Path:
    env = os.getenv("BELLWETHER_REVIEWER_LABELS_FILE", "").strip()
    if env:
        return Path(env)
    return default_cache_root() / "reviewer-labels" / "labels.jsonl"


def record_label(
    *,
    kind: str,
    key: str,
    label: dict[str, Any],
    reviewer: str,
    note: str = "",
) -> None:
    path = labels_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "kind": kind,
        "key": key,
        "label": label,
        "reviewer": reviewer,
        "note": note,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def load_labels(kind: str) -> dict[str, dict[str, Any]]:
    """Latest label per key for a kind (later lines win - reviewers can overturn)."""
    path = labels_path()
    if not path.exists():
        return {}
    labels: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("kind") == kind and entry.get("key"):
                labels[entry["key"]] = entry
    return labels


def ftl_label_key(product_name: str | None, declared_category: str | None) -> str:
    normalized_name = " ".join(str(product_name or "").lower().split())
    normalized_declared = " ".join(str(declared_category or "").lower().split())
    return cache_key("ftl-label-v1", normalized_name, normalized_declared)
