"""Regulatory corpus integrity check (from the 2026-07-07 product audit, defect D-1).

Four normalized corpus files were found to be wrong documents or paywall stubs (the
"2023 technical amendment" was sea-lamprey notices; the "2026 public meeting" a USITC
hearing). Any engine logic or citation leaning on such files is unbacked. This script
verifies every normalized regulatory doc actually contains tokens its docket implies,
and flags stubs (<2 kB of substantive text). Run after every ingestion.

Usage: python backend/scripts/regulatory/check_corpus_integrity.py
Exit 1 when any tracked source fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CORPUS = REPO / "data" / "regulatory"

# source-dir prefix -> tokens the normalized text MUST contain (case-insensitive, any-of
# per tuple, all tuples required)
EXPECTATIONS: dict[str, list[tuple[str, ...]]] = {
    "ecfr-21-cfr-1-subpart-s": [("traceability",), ("1.1310", "1310")],
    "fr-2022-24417-final-rule": [("traceability",), ("food",)],
    "fr-2023-technical-amendment": [("traceability",), ("1.1310", "1.1305", "subpart s")],
    "fr-2025-compliance-date-extension": [("compliance date",), ("july 20, 2028", "2028")],
    "fr-2026-cottage-cheese-exemption": [("cottage cheese",)],
    "fda-food-traceability-list": [("traceability list", "ftl")],
    "fda-cte-kde": [("critical tracking", "key data element")],
    "fda-qa-guidance-2026": [("traceability",)],
    "fda-public-meeting-2026": [("traceability",), ("food",)],
    "fda-faq-food-traceability-rule": [("traceability",)],
}

MIN_SUBSTANTIVE_BYTES = 2000


_TEXT_KEYS = {"text", "content", "body", "support_text", "section_text", "raw_text", "title", "heading"}


def _collect_text(node: object, out: list[str]) -> None:
    """Only CONTENT fields count - metadata (source ids/urls) contains the expected tokens
    even in wrong documents and would mask the exact failure this check exists to catch."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _TEXT_KEYS and isinstance(value, str):
                out.append(value)
            else:
                _collect_text(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_text(item, out)


def _normalized_text(source_dir: Path) -> str:
    texts: list[str] = []
    normalized = source_dir / "normalized"
    if not normalized.is_dir():
        return ""
    for path in sorted(normalized.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        _collect_text(payload, texts)
    return "\n".join(texts)


def main() -> None:
    failures: list[str] = []
    for prefix, token_groups in EXPECTATIONS.items():
        matches = sorted(p for p in CORPUS.iterdir() if p.is_dir() and p.name.startswith(prefix) and not p.name.endswith("-pdf"))
        if not matches:
            failures.append(f"{prefix}: source directory missing")
            continue
        for source_dir in matches:
            text = _normalized_text(source_dir).lower()
            if len(text) < MIN_SUBSTANTIVE_BYTES:
                failures.append(
                    f"{source_dir.name}: normalized content is a stub ({len(text)} bytes) - "
                    "re-ingest from the -pdf sibling or the primary source"
                )
                continue
            for group in token_groups:
                if not any(token in text for token in group):
                    failures.append(
                        f"{source_dir.name}: expected token(s) {group} not found - the normalized "
                        "document may be the WRONG document (see audit defect D-1)"
                    )
    print(f"checked {len(EXPECTATIONS)} tracked sources")
    for failure in failures:
        print(f"  [FAIL] {failure}")
    if failures:
        print("\nRe-ingest the failing sources before citing them. Known-bad from the audit:")
        print("  fr-2023-technical-amendment (wrong doc), fda-public-meeting-2026 (wrong doc),")
        print("  fr-2025-compliance-date-extension + fr-2026-cottage-cheese-exemption (stubs).")
        sys.exit(1)
    print("corpus integrity OK")


if __name__ == "__main__":
    main()
