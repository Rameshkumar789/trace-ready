from __future__ import annotations

import re

from .schemas import RuleCardDraft
from ..chunking.legal_chunker import SourceChunkDraft


def draft_rule_card(chunks: list[SourceChunkDraft], rule_area: str) -> RuleCardDraft:
    finalized_states = ["pass", "gap", "missing_evidence", "not_determined"]
    return RuleCardDraft(
        title=f"Draft {rule_area} rule card",
        rule_area=rule_area,
        decision_question=f"Does the customer evidence satisfy {rule_area}?",
        source_chunk_ids=[chunk.chunk_id for chunk in chunks],
        extracted_conditions=_extract_conditions(" ".join(chunk.text for chunk in chunks)),
        deterministic_logic=f"evaluate_{re.sub(r'[^a-z0-9]+', '_', rule_area.lower()).strip('_')}",
        allowed_finding_states=finalized_states,
        uncertainty_notes=["AI/local draft only; FSMA expert review required before publication."],
    )


def _extract_conditions(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.;]", text) if re.search(r"\b(if|when|unless|where)\b", part, re.I)]
