"""Regulatory watch job (accuracy roadmap WS5.3, automated).

Fetches the FDA pages the engine's rules are derived from, hashes their substantive
content, and diffs against the last recorded hashes. A change means a human must review
whether the FTL / KDE contracts / exemption cards need updating. Schedule this (cron /
Routine) weekly; it exits 1 when drift is detected so it can page.

State file: data/regulatory/watch-state.json (committed, so drift history is reviewable).
Note: fda.gov intermittently bot-blocks (403). A fetch failure is reported as
'unreachable', never as drift.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[3]
STATE_FILE = REPO / "data" / "regulatory" / "watch-state.json"

WATCHED = {
    "ftl": "https://www.fda.gov/food/food-safety-modernization-act-fsma/food-traceability-list",
    "final_rule_page": "https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods",
    "faq": "https://www.fda.gov/food/food-safety-modernization-act-fsma/frequently-asked-questions-fsma-food-traceability-rule",
    "ecfr_subpart_s": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-S",
}


def _content_hash(html: str) -> str:
    # Strip volatile chrome (scripts, styles, nonces, dates in footers) before hashing.
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {"pages": {}}
    drift: list[str] = []
    unreachable: list[str] = []
    for name, url in WATCHED.items():
        try:
            response = httpx.get(url, timeout=30, follow_redirects=True, headers={"user-agent": "TraceReady-regwatch/1.0"})
            response.raise_for_status()
        except Exception as exc:
            unreachable.append(f"{name}: {exc}")
            continue
        digest = _content_hash(response.text)
        previous = state["pages"].get(name, {}).get("hash")
        if previous and previous != digest:
            drift.append(f"{name}: content changed since {state['pages'][name].get('checked_at')}")
        state["pages"][name] = {"url": url, "hash": digest, "checked_at": datetime.now(timezone.utc).isoformat()}

    STATE_FILE.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for line in drift:
        print(f"[DRIFT] {line}")
    for line in unreachable:
        print(f"[UNREACHABLE] {line}")
    if not drift and not unreachable:
        print("no regulatory drift detected")
    if drift:
        print("\nReview whether ftl-food-items.json, kde-check-contracts.json, or exemption-rules.json need updating, then re-run the corpus integrity check and the recall harness.")
        sys.exit(1)


if __name__ == "__main__":
    main()
