from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    CONFLICT_DETECTED = "conflict_detected"


class ExtractionMethod(str, Enum):
    DETERMINISTIC = "deterministic"
    AI_ASSISTED = "ai_assisted"
    HUMAN_AUTHORED = "human_authored"
    IMPORTED_TEMPLATE = "imported_template"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSUPPORTED = "unsupported"
    CONFLICT = "conflict"


class RequirementStatus(str, Enum):
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    OPTIONAL = "optional"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class CteType(str, Enum):
    HARVESTING = "harvesting"
    COOLING = "cooling"
    INITIAL_PACKING = "initial_packing"
    FIRST_LAND_BASED_RECEIVING = "first_land_based_receiving"
    SHIPPING = "shipping"
    RECEIVING = "receiving"
    TRANSFORMATION = "transformation"
    TRACEABILITY_PLAN = "traceability_plan"
    OTHER = "other"


class TlcRuleKind(str, Enum):
    ASSIGNMENT = "assignment"
    PRESERVATION = "preservation"
    SOURCE_REFERENCE = "source_reference"
    TRANSFORMATION_HANDLING = "transformation_handling"
    UNIQUENESS = "uniqueness"
    LINKAGE = "linkage"
    OTHER = "other"


class ExemptionEffect(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    MODIFIED_REQUIREMENTS = "modified_requirements"
    NOT_EXEMPT = "not_exempt"
    UNKNOWN = "unknown"


class ScenarioExpectedFinding(str, Enum):
    PASS = "pass"
    GAP = "gap"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


class StrictIntelligenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class CitationRef(StrictIntelligenceModel):
    source_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    citation_anchor: str = Field(min_length=1)
    authority_rank: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    section_ref: str | None = None
    page_number: int | None = None
    support_text: str | None = None

    @field_validator("source_id", "chunk_id", "citation_anchor", "authority_rank", "source_url")
    @classmethod
    def _no_blank_required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required citation field cannot be blank")
        return value


class DraftMetadata(StrictIntelligenceModel):
    extraction_method: ExtractionMethod
    confidence: ConfidenceLevel
    review_status: ReviewStatus = ReviewStatus.DRAFT
    reviewer_notes: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _approved_requires_high_confidence(self) -> "DraftMetadata":
        if self.review_status == ReviewStatus.APPROVED and self.confidence in {
            ConfidenceLevel.UNSUPPORTED,
            ConfidenceLevel.CONFLICT,
        }:
            raise ValueError("approved records cannot be unsupported or conflict confidence")
        return self


class CitedIntelligenceRecord(StrictIntelligenceModel):
    citations: list[CitationRef] = Field(min_length=1)
    metadata: DraftMetadata

    @model_validator(mode="after")
    def _metadata_chunk_ids_match_citations(self) -> "CitedIntelligenceRecord":
        citation_chunk_ids = {citation.chunk_id for citation in self.citations}
        if not self.metadata.source_chunk_ids:
            self.metadata.source_chunk_ids = sorted(citation_chunk_ids)
        missing = set(self.metadata.source_chunk_ids) - citation_chunk_ids
        if missing:
            raise ValueError(f"metadata.source_chunk_ids missing citation records: {sorted(missing)}")
        return self


class DefinedTerm(CitedIntelligenceRecord):
    term_id: str = Field(min_length=1)
    term: str = Field(min_length=1)
    normalized_key: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    scope: str | None = None
    source_authority: str = Field(min_length=1)
    related_terms: list[str] = Field(default_factory=list)

    @field_validator("normalized_key")
    @classmethod
    def _normalized_key_is_slug(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", value):
            raise ValueError("normalized_key must be snake_case")
        return value


class Obligation(CitedIntelligenceRecord):
    obligation_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    action: str = Field(min_length=1)
    object: str = Field(min_length=1)
    required_output: str | None = None
    deadline: str | None = None
    exceptions: list[str] = Field(default_factory=list)
    applies_to_ctes: list[CteType] = Field(default_factory=list)
    applies_to_food_scope: str | None = None
    noncompliance_risk: str | None = None


class RiskRankingRef(StrictIntelligenceModel):
    source_id: str = Field(min_length=1)
    commodity_risk_score: int | None = None
    hazard_pairs: list[str] = Field(default_factory=list)
    notes: str | None = None


class FtlFoodItem(CitedIntelligenceRecord):
    ftl_item_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    commodity: str = Field(min_length=1)
    description: str = Field(min_length=1)
    included_examples: list[str] = Field(default_factory=list)
    excluded_examples: list[str] = Field(default_factory=list)
    form_notes: list[str] = Field(default_factory=list)
    risk_ranking_refs: list[RiskRankingRef] = Field(default_factory=list)
    raw_list_text: str = Field(min_length=1)


class CteDefinition(CitedIntelligenceRecord):
    cte_id: str = Field(min_length=1)
    cte_type: CteType
    display_name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    trigger_conditions: list[str] = Field(min_length=1)
    actor_roles: list[str] = Field(default_factory=list)
    input_event_relationship: str | None = None
    output_event_relationship: str | None = None
    excluded_conditions: list[str] = Field(default_factory=list)


class KdeRequirement(CitedIntelligenceRecord):
    kde_id: str = Field(min_length=1)
    cte_type: CteType
    kde_name: str = Field(min_length=1)
    field_key: str = Field(min_length=1)
    required_status: RequirementStatus
    applies_to: str = Field(min_length=1)
    provider_role: str | None = None
    recipient_role: str | None = None
    data_type: str | None = None
    conditional_logic: str | None = None
    evidence_examples: list[str] = Field(default_factory=list)
    severity_if_missing: str | None = None

    @field_validator("field_key")
    @classmethod
    def _field_key_is_slug(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", value):
            raise ValueError("field_key must be snake_case")
        return value


class TlcRule(CitedIntelligenceRecord):
    tlc_rule_id: str = Field(min_length=1)
    rule_kind: TlcRuleKind
    applies_to_ctes: list[CteType] = Field(min_length=1)
    applies_to_food_scope: str = Field(min_length=1)
    assignment_rule: str | None = None
    preservation_rule: str | None = None
    source_reference_rule: str | None = None
    transformation_handling: str | None = None
    uniqueness_rule: str | None = None
    lineage_rule: str | None = None
    required_status: RequirementStatus = RequirementStatus.CONDITIONAL
    evidence_examples: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _has_rule_text_for_kind(self) -> "TlcRule":
        rule_fields = [
            self.assignment_rule,
            self.preservation_rule,
            self.source_reference_rule,
            self.transformation_handling,
            self.uniqueness_rule,
            self.lineage_rule,
        ]
        if not any(field for field in rule_fields):
            raise ValueError("TlcRule requires at least one TLC rule text field")
        return self


class ExemptionRule(CitedIntelligenceRecord):
    exemption_rule_id: str = Field(min_length=1)
    exemption_type: str = Field(min_length=1)
    eligibility_condition: str = Field(min_length=1)
    effect: ExemptionEffect
    affected_requirements: list[str] = Field(default_factory=list)
    documentation_needed: list[str] = Field(default_factory=list)
    applies_to_entities: list[str] = Field(default_factory=list)
    applies_to_foods: list[str] = Field(default_factory=list)
    applies_to_ctes: list[CteType] = Field(default_factory=list)
    decision_questions: list[str] = Field(default_factory=list)
    reviewer_warning: str | None = None


class TraceabilityPlanRequirement(CitedIntelligenceRecord):
    traceability_plan_requirement_id: str = Field(min_length=1)
    plan_component: str = Field(min_length=1)
    required_detail: str = Field(min_length=1)
    applies_to: str = Field(min_length=1)
    required_status: RequirementStatus = RequirementStatus.REQUIRED
    evidence_examples: list[str] = Field(default_factory=list)
    update_trigger: str | None = None
    owner_role: str | None = None


class SortableExportField(CitedIntelligenceRecord):
    sortable_export_field_id: str = Field(min_length=1)
    workbook_tab: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    field_key: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    required_status: RequirementStatus
    source_mapping: str = Field(min_length=1)
    applies_to_ctes: list[CteType] = Field(default_factory=list)
    accepted_examples: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)

    @field_validator("field_key")
    @classmethod
    def _sortable_field_key_is_slug(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", value):
            raise ValueError("field_key must be snake_case")
        return value


class ScenarioActor(StrictIntelligenceModel):
    actor_id: str = Field(min_length=1)
    actor_name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    location_description: str | None = None


class ScenarioEvent(StrictIntelligenceModel):
    event_id: str = Field(min_length=1)
    cte_type: CteType
    actor_id: str = Field(min_length=1)
    event_description: str = Field(min_length=1)
    expected_kde_field_keys: list[str] = Field(default_factory=list)
    expected_tlc_behavior: str | None = None

    @field_validator("expected_kde_field_keys")
    @classmethod
    def _scenario_kde_keys_are_slugs(cls, value: list[str]) -> list[str]:
        for key in value:
            if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", key):
                raise ValueError(f"expected_kde_field_keys must be snake_case: {key}")
        return value


class ScenarioExpectation(StrictIntelligenceModel):
    expectation_id: str = Field(min_length=1)
    event_id: str | None = None
    expected_finding: ScenarioExpectedFinding
    expected_behavior: str = Field(min_length=1)
    required_evidence: list[str] = Field(default_factory=list)
    expected_export_behavior: str | None = None


class ScenarioBenchmark(CitedIntelligenceRecord):
    scenario_benchmark_id: str = Field(min_length=1)
    scenario_name: str = Field(min_length=1)
    scenario_source: str = Field(min_length=1)
    food_scope: str = Field(min_length=1)
    actors: list[ScenarioActor] = Field(min_length=1)
    events: list[ScenarioEvent] = Field(min_length=1)
    expectations: list[ScenarioExpectation] = Field(min_length=1)
    open_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _events_reference_known_actors(self) -> "ScenarioBenchmark":
        actor_ids = {actor.actor_id for actor in self.actors}
        unknown_actor_ids = sorted({event.actor_id for event in self.events} - actor_ids)
        if unknown_actor_ids:
            raise ValueError(f"scenario events reference unknown actors: {unknown_actor_ids}")

        event_ids = {event.event_id for event in self.events}
        unknown_event_ids = sorted(
            {
                expectation.event_id
                for expectation in self.expectations
                if expectation.event_id is not None and expectation.event_id not in event_ids
            }
        )
        if unknown_event_ids:
            raise ValueError(f"scenario expectations reference unknown events: {unknown_event_ids}")
        return self


INTELLIGENCE_SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "defined_terms": DefinedTerm,
    "obligations": Obligation,
    "ftl_food_items": FtlFoodItem,
    "cte_definitions": CteDefinition,
    "kde_requirements": KdeRequirement,
    "tlc_rules": TlcRule,
    "exemption_rules": ExemptionRule,
    "traceability_plan_requirements": TraceabilityPlanRequirement,
    "sortable_export_fields": SortableExportField,
    "scenario_benchmarks": ScenarioBenchmark,
}


def dump_json_schemas() -> dict[str, dict[str, Any]]:
    return {name: model.model_json_schema() for name, model in INTELLIGENCE_SCHEMA_MODELS.items()}
