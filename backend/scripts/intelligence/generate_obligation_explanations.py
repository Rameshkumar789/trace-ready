"""Generate + store plain-English explanations for approved obligations.

Reads the approved obligations (their source-chunk text), drafts grounded plain-English
explanations via the ingestion LLM client, and upserts them into Supabase
``obligation_explanations`` as status='ai_generated' (pending reviewer approval).

Run from bellwether/ingestion:  python scripts/intelligence/generate_obligation_explanations.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from bellwether_backend.intelligence.anthropic_client import AnthropicJSONClient, AnthropicLLMConfig
from bellwether_backend.intelligence.obligation_explanations import generate_obligation_explanations

REPO = Path(__file__).resolve().parents[3]
PACKAGE = REPO / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
GENERATED_BY = "ai_explanation_drafter_v1"


def _load_env() -> None:
    env_path = REPO / "backend/.env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value.strip())


def main() -> None:
    _load_env()
    obligations = json.loads(PACKAGE.read_text())["records"]["obligations"]
    client = AnthropicJSONClient(AnthropicLLMConfig.from_env())
    explanations = generate_obligation_explanations(obligations, client=client)

    from supabase import create_client

    sb = create_client(os.environ["NEXT_PUBLIC_SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    rows = [
        {
            "obligation_id": e.obligation_id,
            "section_ref": e.section_ref,
            "cte": e.cte,
            "plain_requirement": e.plain_requirement,
            "why_it_matters": e.why_it_matters,
            "support_text": e.support_text,
            "source_chunk_id": e.source_chunk_id,
            "source_url": e.source_url,
            "generated_by": GENERATED_BY,
            "model": e.model,
            "status": "ai_generated",
            "version": 1,
        }
        for e in explanations
    ]
    sb.table("obligation_explanations").upsert(rows, on_conflict="obligation_id").execute()

    for e in explanations:
        print("—" * 70)
        print(e.obligation_id, "·", e.section_ref)
        print("  requires:", e.plain_requirement)
        print("  why:", e.why_it_matters)
    print("—" * 70)
    print(f"generated + upserted {len(explanations)} explanations (model={explanations[0].model if explanations else 'n/a'})")


if __name__ == "__main__":
    main()
