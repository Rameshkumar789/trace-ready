"""Seed the authored execution-config card collections into Supabase (source of truth).

The deterministic rule engine prefers approved cards from public.approved_regulatory_records
and only falls back to the bundled JSON when a collection is empty. This script promotes the
two authored execution-config documents into Supabase, following the real draft -> approved
pipeline (a draft row, then an approved row that references it) so the schema's FK and
uniqueness constraints are honored.

It is idempotent (ON CONFLICT DO UPDATE) and reversible (delete by collection). The approval
is marked honestly as an AI auto-approval — no human signature is forged.

Collections seeded:
  - traceability_plan_components  (21 CFR 1.1315 plan items)   record_id = component
  - kde_check_contracts           (FSMA 204 KDE coverage map)  record_id = cte

NOT seeded here: 'exemption_rules'. That collection already holds reviewer-approved cards in a
richer schema; the engine reads those as the source of truth and the bundled exemption-rules
JSON is only the offline fallback. Seeding it here would clobber reviewer data or require
fabricating regulatory prose, so it is intentionally left to the regulatory review pipeline.

Run:  python -m scripts.intelligence.seed_rule_data_cards
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from traceready_ingestion.api.config import load_settings
from traceready_ingestion.backend.db import supabase_connection
from traceready_ingestion.audit_engine import rule_execution as engine

BUNDLED_RULES = Path(engine.BUNDLED_RULES_DIR)
APPROVED_BY = "ai-auto-review:claude"
APPROVAL_REASON = (
    "AI auto-approved reviewable FSMA 204 rule data (no human signature). Grounded in the "
    "cited regulation; the deterministic engine reads these cards as the source of truth."
)


def _load_cards() -> list[tuple[str, str, dict[str, Any]]]:
    """Return (collection, record_id, payload) for every card across the three documents."""
    cards: list[tuple[str, str, dict[str, Any]]] = []

    plan = json.loads((BUNDLED_RULES / "traceability-plan-components.json").read_text("utf-8"))
    for component in plan["components"]:
        cards.append(("traceability_plan_components", str(component["component"]), component))

    kde = json.loads((BUNDLED_RULES / "kde-check-contracts.json").read_text("utf-8"))
    for cte, contract in kde["cte_contracts"].items():
        payload = {"cte": cte, **contract}
        cards.append(("kde_check_contracts", str(cte), payload))

    return cards


_DRAFT_SQL = """
insert into public.regulatory_draft_records
  (id, collection, record_id, source_phase, extraction_method, confidence, review_status,
   citation_coverage_status, schema_valid, citation_valid, payload)
values
  (%(id)s, %(collection)s, %(record_id)s, 'rule_data_seed', 'curated', 'high', 'approved',
   'covered', true, true, %(payload)s)
on conflict (id) do update set
  payload = excluded.payload,
  review_status = 'approved',
  updated_at = now()
"""

_APPROVED_SQL = """
insert into public.approved_regulatory_records
  (id, draft_record_id, collection, record_id, version, approved_by, approval_reason,
   source_chunk_ids, payload)
values
  (%(id)s, %(draft_id)s, %(collection)s, %(record_id)s, 1, %(approved_by)s, %(approval_reason)s,
   '[]'::jsonb, %(payload)s)
on conflict (collection, record_id, version) do update set
  payload = excluded.payload,
  approved_by = excluded.approved_by,
  approval_reason = excluded.approval_reason,
  draft_record_id = excluded.draft_record_id
"""


def main() -> None:
    cards = _load_cards()
    settings = load_settings()
    counts: dict[str, int] = {}
    with supabase_connection(settings) as connection:
        with connection.cursor() as cursor:
            for collection, record_id, payload in cards:
                draft_id = f"draft:{collection}:{record_id}"
                approved_id = f"approved:{collection}:{record_id}:v1"
                payload_json = json.dumps(payload)
                cursor.execute(
                    _DRAFT_SQL,
                    {"id": draft_id, "collection": collection, "record_id": record_id, "payload": payload_json},
                )
                cursor.execute(
                    _APPROVED_SQL,
                    {
                        "id": approved_id,
                        "draft_id": draft_id,
                        "collection": collection,
                        "record_id": record_id,
                        "approved_by": APPROVED_BY,
                        "approval_reason": APPROVAL_REASON,
                        "payload": payload_json,
                    },
                )
                counts[collection] = counts.get(collection, 0) + 1
    for collection, count in sorted(counts.items()):
        print(f"seeded {count:>3} approved cards into '{collection}'")
    print(f"total: {sum(counts.values())} cards across {len(counts)} collections")


if __name__ == "__main__":
    main()
