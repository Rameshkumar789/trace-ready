"""Generate plain-English explanations for approved FSMA 204 obligations.

This belongs to the ingestion / regulatory-intelligence layer, NOT the per-audit runtime.
For each approved obligation we draft, ONCE, a customer-friendly "what this rule requires"
and "why it matters", grounded strictly in the obligation's own source-chunk text
(``support_text``). The drafts are guardrailed (no invented requirements), reviewer-approved,
and stored as versioned data. The customer audit view then looks them up by obligation id;
nothing is generated per audit and nothing is hardcoded.

Wiring this into a publish step (e.g. when an obligation is approved into a rule package)
keeps the explanation set automatically in sync with approved coverage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

EXPLANATION_SYSTEM_PROMPT = """You explain FSMA 204 (21 CFR Part 1, Subpart S) obligations in plain English for food-industry operators who are not lawyers.

For each obligation you are given its real regulatory text (rule_text). Follow these rules strictly:
- Ground every statement ONLY in that obligation's rule_text. Never invent requirements, key data elements, dates, numbers, or sections that are not in the rule_text.
- Produce exactly two fields:
  - "plain_requirement": ONE sentence, plain language, stating what the rule requires.
  - "why_it_matters": ONE or TWO sentences on why it matters for traceability and recall response. Concrete and conversational. No legalese, no fear language, no legal advice, no compliance guarantees.
- Sentence case. No emojis. Do not address the reader as "you must"; describe the requirement.
- Return ONLY a JSON array; one object per obligation with keys: "obligation_id", "plain_requirement", "why_it_matters". No prose outside the array.
"""


class JSONArrayClient(Protocol):
    def complete_json_array(self, *, system: str, user_prompt: str) -> Any: ...


@dataclass(frozen=True)
class ObligationExplanation:
    obligation_id: str
    section_ref: str | None
    cte: str | None
    plain_requirement: str
    why_it_matters: str
    support_text: str | None
    source_chunk_id: str | None
    source_url: str | None
    model: str


def _primary_citation(obligation: dict[str, Any]) -> dict[str, Any]:
    citations = obligation.get("citations") or []
    return citations[0] if citations else {}


def build_explanation_prompt(obligations: list[dict[str, Any]]) -> str:
    items = []
    for obligation in obligations:
        citation = _primary_citation(obligation)
        ctes = obligation.get("applies_to_ctes") or []
        items.append(
            {
                "obligation_id": obligation["obligation_id"],
                "section_ref": citation.get("section_ref"),
                "applies_to_ctes": ctes,
                "rule_text": (citation.get("support_text") or "")[:2000],
            }
        )
    import json

    return (
        "Write plain_requirement and why_it_matters for each obligation below, grounded only "
        "in its rule_text. Return a JSON array.\n\n" + json.dumps(items, indent=2, ensure_ascii=False)
    )


def _word_set(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower())}


def generate_obligation_explanations(
    obligations: list[dict[str, Any]],
    *,
    client: JSONArrayClient,
) -> list[ObligationExplanation]:
    """Draft grounded plain-English explanations for the given approved obligations."""
    if not obligations:
        return []
    response = client.complete_json_array(
        system=EXPLANATION_SYSTEM_PROMPT,
        user_prompt=build_explanation_prompt(obligations),
    )
    by_id = {record.get("obligation_id"): record for record in getattr(response, "parsed_json", [])}
    model = getattr(response, "model", "unknown")

    explanations: list[ObligationExplanation] = []
    for obligation in obligations:
        oid = obligation["obligation_id"]
        record = by_id.get(oid)
        if not record:
            raise ValueError(f"Model returned no explanation for obligation {oid}.")
        plain = (record.get("plain_requirement") or "").strip()
        why = (record.get("why_it_matters") or "").strip()
        if not plain or not why:
            raise ValueError(f"Empty explanation field for obligation {oid}.")
        citation = _primary_citation(obligation)
        _assert_grounded(oid, plain, why, citation)
        ctes = obligation.get("applies_to_ctes") or []
        explanations.append(
            ObligationExplanation(
                obligation_id=oid,
                section_ref=citation.get("section_ref"),
                cte=ctes[0] if len(ctes) == 1 else None,
                plain_requirement=plain,
                why_it_matters=why,
                support_text=citation.get("support_text"),
                source_chunk_id=citation.get("chunk_id"),
                source_url=citation.get("source_url"),
                model=model,
            )
        )
    return explanations


def _assert_grounded(oid: str, plain: str, why: str, citation: dict[str, Any]) -> None:
    """Lightweight guardrail: the explanation must not introduce a different CFR section,
    and should overlap the rule text rather than invent unrelated content."""
    section = citation.get("section_ref") or ""
    cited_sections = set(re.findall(r"1\.1\d{3}", section))
    mentioned_sections = set(re.findall(r"1\.1\d{3}", f"{plain} {why}"))
    stray = mentioned_sections - cited_sections
    if stray:
        raise ValueError(f"Explanation for {oid} references uncited sections {sorted(stray)}.")
    support_words = _word_set(citation.get("support_text") or "")
    if support_words:
        overlap = support_words & _word_set(plain)
        if not overlap:
            raise ValueError(f"Explanation for {oid} does not appear grounded in its rule text.")
