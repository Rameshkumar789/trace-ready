from __future__ import annotations

from .._compat import BaseModel, Field


class RuleCardDraft(BaseModel):
    title: str
    rule_area: str
    decision_question: str
    source_chunk_ids: list[str] = Field(min_length=1)
    extracted_conditions: list[str] = []
    deterministic_logic: str
    allowed_finding_states: list[str] = Field(min_length=1)
    uncertainty_notes: list[str] = []
    requires_expert_review: bool = True


class KdeRequirementDraft(BaseModel):
    cte_type: str
    kde_name: str
    field_key: str
    required_status: str
    applies_when: str
    source_chunk_id: str
    severity_if_missing: str
    uncertainty_notes: list[str] = []
    requires_expert_review: bool = True
