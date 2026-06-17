from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from traceready_ingestion.intelligence.citations import (
    build_citation_coverage_report,
    validate_citation_span,
)
from traceready_ingestion.intelligence.schemas import (
    ConfidenceLevel,
    DraftMetadata,
    ExemptionRule,
    ExtractionMethod,
    Obligation,
    ReviewStatus,
    TlcRule,
    dump_json_schemas,
)


PHASE5_COLLECTION_MODELS = {
    "obligations": Obligation,
    "exemption_rules": ExemptionRule,
    "tlc_rules": TlcRule,
}

CRITICAL_CLAIM_FIELDS = {
    "obligations": ["subject", "condition", "action", "object", "required_output", "deadline"],
    "exemption_rules": ["exemption_type", "eligibility_condition", "effect", "reviewer_warning"],
    "tlc_rules": [
        "assignment_rule",
        "preservation_rule",
        "source_reference_rule",
        "transformation_handling",
        "uniqueness_rule",
        "lineage_rule",
    ],
}


class PromptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_id: str
    collection: str
    title: str
    purpose: str
    system_instructions: str
    user_template: str
    output_schema: dict[str, Any]
    guardrails: list[str] = Field(default_factory=list)


class AIValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    collection: str
    severity: str
    code: str
    message: str
    fields: list[str] = Field(default_factory=list)


class AIValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection: str
    accepted_records: list[dict[str, Any]] = Field(default_factory=list)
    rejected_records: list[dict[str, Any]] = Field(default_factory=list)
    conflict_records: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[AIValidationIssue] = Field(default_factory=list)


def build_phase5_prompt_specs() -> list[PromptSpec]:
    schemas = dump_json_schemas()
    return [
        _prompt_spec(
            prompt_id="phase5_obligation_extraction_v1",
            collection="obligations",
            title="AI-Assisted Obligation Extraction",
            purpose="Extract obligation drafts from authoritative FSMA 204 source chunks without approving compliance logic.",
            schema=schemas["obligations"],
            instructions=[
                "Return only JSON matching the Obligation schema.",
                "Use only the supplied source chunks. Do not use outside knowledge.",
                "Return at most 10 records.",
                "Every draft obligation must include at least one citation with support_text copied exactly from a supplied chunk.",
                "support_text must be one exact contiguous substring; do not combine clauses, paraphrase, or rewrite punctuation.",
                "If one claim needs multiple source spans, create multiple citation objects.",
                "If the source text is ambiguous, set confidence to low and review_status to needs_review.",
                "Do not mark any record approved.",
            ],
            extraction_focus=[
                "covered subject",
                "triggering condition",
                "required action",
                "required object or records",
                "deadline or timing requirement when explicit",
                "exceptions or cross-references when explicit",
            ],
        ),
        _prompt_spec(
            prompt_id="phase5_exemption_extraction_v1",
            collection="exemption_rules",
            title="AI-Assisted Exemption Extraction",
            purpose="Extract exemption-rule drafts with eligibility conditions, effect, documentation needs, and decision questions.",
            schema=schemas["exemption_rules"],
            instructions=[
                "Return only JSON matching the ExemptionRule schema.",
                "Use only the supplied source chunks. Do not infer exemption eligibility from general FSMA knowledge.",
                "Return at most 8 records.",
                "Every exemption condition/effect must cite exact support_text from a supplied chunk.",
                "support_text must be one exact contiguous substring; do not combine clauses, paraphrase, or rewrite punctuation.",
                "If one claim needs multiple source spans, create multiple citation objects.",
                "If the effect is not explicit, use unknown and add a reviewer warning.",
                "Do not mark any record approved.",
            ],
            extraction_focus=[
                "exemption type",
                "eligibility condition",
                "full, partial, modified, or unknown effect",
                "requirements affected",
                "documentation needed",
                "entity, food, and CTE applicability",
            ],
        ),
        _prompt_spec(
            prompt_id="phase5_tlc_rule_extraction_v1",
            collection="tlc_rules",
            title="AI-Assisted TLC Rule Extraction",
            purpose="Extract traceability-lot-code rule drafts for assignment, preservation, source reference, transformation handling, uniqueness, and linkage.",
            schema=schemas["tlc_rules"],
            instructions=[
                "Return only JSON matching the TlcRule schema.",
                "Use only supplied source chunks. Do not invent TLC behavior.",
                "Return at most 8 records.",
                "Each rule text field must be supported by cited source text.",
                "support_text must be one exact contiguous substring; do not combine clauses, paraphrase, or rewrite punctuation.",
                "If one rule needs multiple source spans, create multiple citation objects.",
                "If a rule depends on CTE, food scope, or exemption context, keep required_status conditional and add unresolved_questions.",
                "Do not mark any record approved.",
            ],
            extraction_focus=[
                "TLC assignment trigger",
                "TLC preservation through shipping/receiving",
                "TLC source and source-reference handling",
                "transformation input-to-output TLC linkage",
                "uniqueness or lot identity requirements",
            ],
        ),
    ]


def render_prompt(spec: PromptSpec, chunks: list[dict[str, Any]]) -> str:
    chunk_payload = [
        {
            "source_id": chunk["source_id"],
            "chunk_id": chunk["chunk_id"],
            "citation_anchor": chunk["citation_anchor"],
            "authority_rank": chunk["authority_rank"],
            "source_url": chunk["source_url"],
            "section_ref": chunk.get("section_ref"),
            "page_number": chunk.get("page_number"),
            "text": chunk["text"],
        }
        for chunk in chunks
    ]
    return spec.user_template.replace("{{SOURCE_CHUNKS_JSON}}", json.dumps(chunk_payload, indent=2)).replace(
        "{{OUTPUT_SCHEMA_JSON}}", json.dumps(spec.output_schema, indent=2)
    )


def select_phase5_source_chunks(collection: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if collection == "obligations":
        return [
            chunk
            for chunk in chunks
            if chunk.get("source_id") == "ecfr-21-cfr-1-subpart-s"
            and str(chunk.get("section_ref"))
            in {
                "21 CFR 1.1300",
                "21 CFR 1.1325",
                "21 CFR 1.1330",
                "21 CFR 1.1335",
                "21 CFR 1.1340",
                "21 CFR 1.1345",
                "21 CFR 1.1350",
                "21 CFR 1.1455",
            }
        ]
    if collection == "exemption_rules":
        return [
            chunk
            for chunk in chunks
            if chunk.get("source_id") == "ecfr-21-cfr-1-subpart-s" and str(chunk.get("section_ref")) == "21 CFR 1.1305"
        ][:4]
    if collection == "tlc_rules":
        return [
            chunk
            for chunk in chunks
            if (
                chunk.get("source_id") == "ecfr-21-cfr-1-subpart-s"
                and str(chunk.get("section_ref"))
                in {"21 CFR 1.1320", "21 CFR 1.1330", "21 CFR 1.1335", "21 CFR 1.1340", "21 CFR 1.1345", "21 CFR 1.1350"}
            )
            or chunk.get("source_id") == "fda-traceability-lot-code"
        ][:10]
    raise ValueError(f"Unsupported prompt collection: {collection}")


def validate_ai_records(
    collection: str,
    raw_records: list[dict[str, Any]],
    chunk_index: dict[str, dict[str, Any]],
) -> AIValidationResult:
    if collection not in PHASE5_COLLECTION_MODELS:
        raise ValueError(f"Phase 5 does not accept collection: {collection}")

    model = PHASE5_COLLECTION_MODELS[collection]
    accepted: list[Any] = []
    rejected: list[dict[str, Any]] = []
    issues: list[AIValidationIssue] = []

    for index, raw_record in enumerate(raw_records):
        try:
            record = model.model_validate(raw_record)
        except Exception as exc:  # Pydantic raises ValidationError; keep message stable for reports.
            record_id = str(raw_record.get(_id_field(collection), f"record_{index}"))
            rejected.append(raw_record)
            issues.append(
                AIValidationIssue(
                    record_id=record_id,
                    collection=collection,
                    severity="error",
                    code="schema_validation_failed",
                    message=str(exc),
                )
            )
            continue

        record_id = _record_id(record, collection)
        record_issues = _record_gate_issues(collection, record, chunk_index)
        if record_issues:
            rejected_record = _mark_record(record, ConfidenceLevel.UNSUPPORTED, ReviewStatus.REJECTED, record_issues)
            rejected.append(rejected_record.model_dump(mode="json"))
            issues.extend(record_issues)
        else:
            accepted.append(record)

    accepted, conflict_records, conflict_issues = detect_conflicts(collection, accepted)
    issues.extend(conflict_issues)

    return AIValidationResult(
        collection=collection,
        accepted_records=[record.model_dump(mode="json") for record in accepted],
        rejected_records=rejected,
        conflict_records=[record.model_dump(mode="json") for record in conflict_records],
        issues=issues,
    )


def detect_conflicts(collection: str, records: list[Any]) -> tuple[list[Any], list[Any], list[AIValidationIssue]]:
    groups: dict[str, list[Any]] = defaultdict(list)
    for record in records:
        groups[_conflict_key(collection, record)].append(record)

    accepted: list[Any] = []
    conflicts: list[Any] = []
    issues: list[AIValidationIssue] = []

    for key, grouped_records in groups.items():
        signatures = {_conflict_signature(collection, record) for record in grouped_records}
        if len(grouped_records) > 1 and len(signatures) > 1:
            for record in grouped_records:
                issue = AIValidationIssue(
                    record_id=_record_id(record, collection),
                    collection=collection,
                    severity="error",
                    code="conflict_detected",
                    message=f"Conflicting draft records share semantic key {key!r} but disagree on material rule content.",
                )
                issues.append(issue)
                conflicts.append(_mark_record(record, ConfidenceLevel.CONFLICT, ReviewStatus.CONFLICT_DETECTED, [issue]))
        else:
            accepted.extend(grouped_records)
    return accepted, conflicts, issues


def _prompt_spec(
    *,
    prompt_id: str,
    collection: str,
    title: str,
    purpose: str,
    schema: dict[str, Any],
    instructions: list[str],
    extraction_focus: list[str],
) -> PromptSpec:
    system = "\n".join(
        [
            "You are a regulatory extraction assistant for TraceReady.",
            "You draft structured records only; you do not decide legal compliance.",
            "The rules engine and human reviewer are the authority.",
            *[f"- {instruction}" for instruction in instructions],
        ]
    )
    user_template = "\n\n".join(
        [
            f"# {title}",
            purpose,
            "## Extraction focus",
            "\n".join(f"- {item}" for item in extraction_focus),
            "## Required JSON schema",
            "{{OUTPUT_SCHEMA_JSON}}",
            "## Source chunks",
            "{{SOURCE_CHUNKS_JSON}}",
            "Return a JSON array of records. No Markdown. No commentary.",
        ]
    )
    return PromptSpec(
        prompt_id=prompt_id,
        collection=collection,
        title=title,
        purpose=purpose,
        system_instructions=system,
        user_template=user_template,
        output_schema=schema,
        guardrails=instructions,
    )


def _record_gate_issues(collection: str, record: Any, chunk_index: dict[str, dict[str, Any]]) -> list[AIValidationIssue]:
    issues: list[AIValidationIssue] = []
    record_id = _record_id(record, collection)
    record_dict = record.model_dump(mode="json")

    if record.metadata.extraction_method != ExtractionMethod.AI_ASSISTED:
        issues.append(
            AIValidationIssue(
                record_id=record_id,
                collection=collection,
                severity="error",
                code="not_ai_assisted",
                message="Phase 5 AI records must have metadata.extraction_method='ai_assisted'.",
            )
        )

    if record.metadata.review_status == ReviewStatus.APPROVED:
        issues.append(
            AIValidationIssue(
                record_id=record_id,
                collection=collection,
                severity="error",
                code="ai_attempted_approval",
                message="AI-assisted records cannot be approved directly.",
            )
        )

    citation_report = build_citation_coverage_report({collection: [record_dict]}, chunk_index)
    if citation_report.summary["invalid"] or citation_report.summary["missing"] or citation_report.summary["partial"]:
        issues.append(
            AIValidationIssue(
                record_id=record_id,
                collection=collection,
                severity="error",
                code="citation_coverage_failed",
                message="AI draft has missing, partial, or invalid citations.",
            )
        )

    unsupported_fields = _unsupported_claim_fields(collection, record_dict, chunk_index)
    if unsupported_fields:
        issues.append(
            AIValidationIssue(
                record_id=record_id,
                collection=collection,
                severity="error",
                code="unsupported_claim",
                message="AI draft contains material fields that are not sufficiently supported by cited source text.",
                fields=unsupported_fields,
            )
        )

    return issues


def _unsupported_claim_fields(collection: str, record: dict[str, Any], chunk_index: dict[str, dict[str, Any]]) -> list[str]:
    support_text = " ".join(
        str(citation.get("support_text") or "")
        for citation in record.get("citations", [])
        if validate_citation_span(citation, chunk_index).status in {"valid", "valid_normalized"}
    )
    cited_chunk_text = " ".join(
        str(chunk_index.get(str(citation.get("chunk_id")), {}).get("text", ""))
        for citation in record.get("citations", [])
    )
    support_corpus = f"{support_text} {cited_chunk_text}"

    unsupported: list[str] = []
    for field_name in CRITICAL_CLAIM_FIELDS[collection]:
        value = record.get(field_name)
        if value is None or value == "":
            continue
        if not _value_supported_by_text(str(value), support_corpus):
            unsupported.append(field_name)
    return unsupported


def _value_supported_by_text(value: str, support_corpus: str) -> bool:
    value_norm = _normalize(value)
    corpus_norm = _normalize(support_corpus)
    if not value_norm:
        return True
    if value_norm in corpus_norm:
        return True
    value_tokens = _content_tokens(value_norm)
    if not value_tokens:
        return True
    corpus_tokens = set(_content_tokens(corpus_norm))
    overlap = sum(1 for token in value_tokens if token in corpus_tokens)
    return overlap >= max(2, int(len(set(value_tokens)) * 0.35))


def _mark_record(record: Any, confidence: ConfidenceLevel, status: ReviewStatus, issues: list[AIValidationIssue]) -> Any:
    metadata = DraftMetadata(
        extraction_method=record.metadata.extraction_method,
        confidence=confidence,
        review_status=status,
        reviewer_notes=[f"{issue.code}: {issue.message}" for issue in issues],
        source_chunk_ids=record.metadata.source_chunk_ids,
    )
    return record.model_copy(update={"metadata": metadata})


def _conflict_key(collection: str, record: Any) -> str:
    if collection == "obligations":
        ctes = ",".join(sorted(cte.value for cte in record.applies_to_ctes))
        return "|".join([_normalize(record.subject), _normalize(record.condition), _normalize(record.object), ctes])
    if collection == "exemption_rules":
        return "|".join([_normalize(record.exemption_type), _normalize(record.eligibility_condition)])
    if collection == "tlc_rules":
        ctes = ",".join(sorted(cte.value for cte in record.applies_to_ctes))
        return "|".join([record.rule_kind.value, _normalize(record.applies_to_food_scope), ctes])
    raise ValueError(f"Unsupported conflict collection: {collection}")


def _conflict_signature(collection: str, record: Any) -> str:
    if collection == "obligations":
        return "|".join([_normalize(record.action), _normalize(record.required_output or ""), _normalize(record.deadline or "")])
    if collection == "exemption_rules":
        return "|".join([record.effect.value, ",".join(sorted(record.affected_requirements))])
    if collection == "tlc_rules":
        values = [
            record.assignment_rule,
            record.preservation_rule,
            record.source_reference_rule,
            record.transformation_handling,
            record.uniqueness_rule,
            record.lineage_rule,
        ]
        return "|".join(_normalize(value or "") for value in values)
    raise ValueError(f"Unsupported conflict collection: {collection}")


def _record_id(record: Any, collection: str) -> str:
    return str(getattr(record, _id_field(collection)))


def _id_field(collection: str) -> str:
    return {
        "obligations": "obligation_id",
        "exemption_rules": "exemption_rule_id",
        "tlc_rules": "tlc_rule_id",
    }[collection]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def _content_tokens(value: str) -> list[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "by",
        "for",
        "from",
        "if",
        "in",
        "is",
        "must",
        "of",
        "or",
        "the",
        "to",
        "under",
        "with",
        "you",
        "your",
    }
    return [token for token in re.findall(r"[a-z0-9]{3,}", value) if token not in stop_words]
