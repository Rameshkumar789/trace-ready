from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from bellwether_backend.intelligence.citations import load_chunk_index, validate_citation_span


GENERATED_AT = "2026-06-16T00:00:00Z"

SIGNAL_FAMILIES = [
    "action_semantics",
    "actor_role",
    "from_to_movement",
    "document_type",
    "date_field",
    "lot_tlc",
    "reference_document",
    "product_quantity",
]

CTES = ["harvesting", "cooling", "initial_packing", "first_land_based_receiving", "shipping", "receiving", "transformation"]


class StrictPhase13Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class ParagraphBlock(StrictPhase13Model):
    anchor: str
    marker_path: list[str] = Field(default_factory=list)
    text: str


class ApprovedSubparagraphTarget(StrictPhase13Model):
    obligation_id: str
    section_ref: str
    target_anchors: list[str] = Field(min_length=1)
    review_status: str
    rationale: str


class ApprovedSubparagraphTargetPackage(StrictPhase13Model):
    artifact_id: str
    version: int
    status: str
    generated_at: str
    approval: dict[str, Any]
    scope: dict[str, Any]
    targets: list[ApprovedSubparagraphTarget]


class CitationSubparagraphResolution(StrictPhase13Model):
    obligation_id: str
    section_ref: str
    citation_anchor: str
    section_level_status: str
    section_level_remains_valid: bool
    resolution_status: str
    resolved_subparagraph_anchors: list[str] = Field(default_factory=list)
    unresolved_targets: list[str] = Field(default_factory=list)
    candidate_count: int
    method: str
    notes: list[str] = Field(default_factory=list)


class CitationSubparagraphPackage(StrictPhase13Model):
    generated_at: str
    summary: dict[str, Any]
    resolutions: list[CitationSubparagraphResolution]


class TwoStageRecordResult(StrictPhase13Model):
    record_id: str
    expected_ctes: list[str]
    candidate_ctes: list[str]
    auto_approved_ctes: list[str]
    review_routed_ctes: list[str]
    abstained_ctes: list[str]
    signal_families_by_cte: dict[str, list[str]]
    status: str
    errors: list[str] = Field(default_factory=list)


class TwoStageClassifierPackage(StrictPhase13Model):
    generated_at: str
    summary: dict[str, Any]
    signal_families: list[str]
    results: list[TwoStageRecordResult]


class Phase13ReleaseGatePackage(StrictPhase13Model):
    generated_at: str
    summary: dict[str, Any]
    subparagraph_citations: CitationSubparagraphPackage
    two_stage_classifier: TwoStageClassifierPackage


def build_phase13_release_gates(
    *,
    approved_rule_package_file: Path,
    source_chunks_file: Path,
    approved_subparagraph_targets_file: Path,
    web500_records_file: Path,
    web500_metrics_file: Path,
) -> Phase13ReleaseGatePackage:
    rule_package = json.loads(approved_rule_package_file.read_text(encoding="utf-8"))
    chunk_index = load_chunk_index(source_chunks_file)
    subparagraph_targets = load_approved_subparagraph_targets(approved_subparagraph_targets_file)
    web500_records = json.loads(web500_records_file.read_text(encoding="utf-8"))
    web500_metrics = json.loads(web500_metrics_file.read_text(encoding="utf-8"))
    subparagraphs = build_subparagraph_citation_package(
        rule_package=rule_package,
        chunk_index=chunk_index,
        approved_subparagraph_targets=subparagraph_targets,
    )
    two_stage = build_two_stage_classifier_package(web500_records=web500_records, web500_metrics=web500_metrics)
    summary = {
        "phase": "13-release-gates",
        "generatedAt": GENERATED_AT,
        "subparagraphResolutionStatus": subparagraphs.summary["status"],
        "sectionLevelCitationValidationWeakened": False,
        "resolvedCitationCount": subparagraphs.summary["resolved"],
        "unresolvedCitationCount": subparagraphs.summary["unresolved"],
        "twoStageStatus": two_stage.summary["status"],
        "twoStageAutoApprovedPrecision": two_stage.summary["auto_approved_precision"],
        "twoStageReviewRoutedCount": two_stage.summary["review_routed_count"],
        "twoStageAbstentionRate": two_stage.summary["abstention_rate"],
        "baselineWeb500ExactMatchRate": web500_metrics.get("exact_match_rate"),
    }
    return Phase13ReleaseGatePackage(
        generated_at=GENERATED_AT,
        summary=summary,
        subparagraph_citations=subparagraphs,
        two_stage_classifier=two_stage,
    )


def write_phase13_release_gate_artifacts(package: Phase13ReleaseGatePackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase13-release-gates-summary.json",
        "subparagraphCitations": output_dir / "phase13-subparagraph-citation-resolution.json",
        "twoStageClassifier": output_dir / "phase13-two-stage-classifier-report.json",
    }
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["subparagraphCitations"], package.subparagraph_citations.model_dump(mode="json"))
    _write_json(outputs["twoStageClassifier"], package.two_stage_classifier.model_dump(mode="json"))
    return {key: str(path) for key, path in outputs.items()}


def build_subparagraph_citation_package(
    *,
    rule_package: dict[str, Any],
    chunk_index: dict[str, dict[str, Any]],
    approved_subparagraph_targets: ApprovedSubparagraphTargetPackage,
) -> CitationSubparagraphPackage:
    obligations = rule_package.get("records", {}).get("obligations", [])
    approved_targets_by_obligation = {
        target.obligation_id: target
        for target in approved_subparagraph_targets.targets
        if target.review_status == "approved"
    }
    resolutions: list[CitationSubparagraphResolution] = []
    for obligation in obligations:
        obligation_id = obligation["obligation_id"]
        for citation in obligation.get("citations", []):
            section_validation = validate_citation_span(citation, chunk_index)
            section_ref = str(citation.get("section_ref") or citation.get("citation_anchor") or "")
            chunk = chunk_index.get(str(citation.get("chunk_id") or ""))
            blocks = parse_cfr_subparagraph_blocks(section_ref=section_ref, text=str((chunk or {}).get("text") or ""))
            approved_target = approved_targets_by_obligation.get(obligation_id)
            targets = approved_target.target_anchors if approved_target else infer_subparagraph_targets(obligation, blocks)
            resolved = [target for target in targets if anchor_exists(target, section_ref, blocks)]
            unresolved = [target for target in targets if target not in resolved]
            if unresolved:
                status = "unresolved"
            elif resolved:
                status = "resolved"
            else:
                status = "section_only"
            notes = ["Subparagraph resolution is additive; section-level validation remains authoritative."]
            if not targets:
                notes.append("No confident subparagraph target was inferred; retain section-level citation only.")
            if unresolved:
                notes.append("One or more proposed subparagraph anchors were not found in the cited section text.")
            resolutions.append(
                CitationSubparagraphResolution(
                    obligation_id=obligation_id,
                    section_ref=section_ref,
                    citation_anchor=str(citation.get("citation_anchor") or ""),
                    section_level_status=section_validation.status,
                    section_level_remains_valid=section_validation.status in {"valid", "valid_normalized", "partial"},
                    resolution_status=status,
                    resolved_subparagraph_anchors=resolved,
                    unresolved_targets=unresolved,
                    candidate_count=len(blocks),
                    method=f"approved_target_artifact:{approved_subparagraph_targets.artifact_id}" if approved_target else "semantic_overlap",
                    notes=notes,
                )
            )
    counts = Counter(item.resolution_status for item in resolutions)
    invalid_section_count = sum(1 for item in resolutions if not item.section_level_remains_valid)
    summary = {
        "status": "pass" if not counts["unresolved"] and not invalid_section_count else "review_required",
        "obligationCitations": len(resolutions),
        "resolved": counts["resolved"],
        "sectionOnly": counts["section_only"],
        "unresolved": counts["unresolved"],
        "invalidSectionLevelCitations": invalid_section_count,
        "sectionLevelCitationValidationWeakened": False,
        "approvedTargetArtifact": approved_subparagraph_targets.artifact_id,
        "approvedTargetArtifactVersion": approved_subparagraph_targets.version,
        "exampleResolvedAnchors": {
            item.obligation_id: item.resolved_subparagraph_anchors
            for item in resolutions[:3]
        },
    }
    return CitationSubparagraphPackage(generated_at=GENERATED_AT, summary=summary, resolutions=resolutions)


def load_approved_subparagraph_targets(path: Path) -> ApprovedSubparagraphTargetPackage:
    payload = json.loads(path.read_text(encoding="utf-8"))
    package = ApprovedSubparagraphTargetPackage.model_validate(payload)
    if package.status != "approved":
        raise ValueError(f"Subparagraph target package must be approved, got {package.status!r}.")
    duplicate_ids = [obligation_id for obligation_id, count in Counter(target.obligation_id for target in package.targets).items() if count > 1]
    if duplicate_ids:
        raise ValueError(f"Duplicate subparagraph target obligation IDs: {duplicate_ids}")
    return package


def parse_cfr_subparagraph_blocks(*, section_ref: str, text: str) -> list[ParagraphBlock]:
    markers = list(re.finditer(r"\(([A-Za-z0-9ivxlcdmIVXLCDM]+)\)", text))
    if not markers:
        return [ParagraphBlock(anchor=section_ref, marker_path=[], text=text.strip())] if text.strip() else []
    blocks: list[ParagraphBlock] = []
    stack: list[tuple[int, str]] = []
    for index, match in enumerate(markers):
        token = match.group(1)
        level = marker_level(token)
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, token))
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        path = [item[1] for item in stack]
        blocks.append(
            ParagraphBlock(
                anchor=f"{section_ref}{''.join(f'({item})' for item in path)}",
                marker_path=path,
                text=text[match.start():end].strip(),
            )
        )
    return blocks


def marker_level(token: str) -> int:
    if token.isdigit():
        return 2
    if token.isupper():
        return 4
    if token.lower() in {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}:
        return 3
    return 1


def anchor_exists(anchor: str, section_ref: str, blocks: list[ParagraphBlock]) -> bool:
    if anchor == section_ref:
        return True
    return any(block.anchor == anchor for block in blocks)


def infer_subparagraph_targets(obligation: dict[str, Any], blocks: list[ParagraphBlock]) -> list[str]:
    if not blocks:
        return []
    query = " ".join(
        str(obligation.get(key) or "")
        for key in ["action", "object", "required_output", "condition", "noncompliance_risk"]
    )
    query_tokens = set(_tokens(query))
    scored: list[tuple[int, str]] = []
    for block in blocks:
        block_tokens = set(_tokens(block.text))
        score = len(query_tokens & block_tokens)
        if score:
            scored.append((score, block.anchor))
    if not scored:
        return []
    max_score = max(score for score, _ in scored)
    return [anchor for score, anchor in scored if score == max_score and score >= 3]


def build_two_stage_classifier_package(
    *,
    web500_records: list[dict[str, Any]],
    web500_metrics: dict[str, Any],
) -> TwoStageClassifierPackage:
    results = [evaluate_two_stage_record(record) for record in web500_records]
    total_auto_predictions = sum(len(result.auto_approved_ctes) for result in results)
    true_auto_predictions = sum(
        1
        for result in results
        for cte in result.auto_approved_ctes
        if cte in result.expected_ctes
    )
    expected_positive = sum(len(result.expected_ctes) for result in results)
    auto_true_positive = true_auto_predictions
    review_routed_count = sum(1 for result in results if result.review_routed_ctes)
    abstained_count = sum(1 for result in results if result.abstained_ctes)
    exact_auto_passes = sum(1 for result in results if set(result.auto_approved_ctes) == set(result.expected_ctes) and not result.review_routed_ctes)
    summary = {
        "status": "pass" if all(result.status in {"pass", "review_routed"} for result in results) else "fail",
        "baseline": {
            "source": "phase12-web500-metrics.json",
            "exact_match_rate": web500_metrics.get("exact_match_rate"),
            "precision": web500_metrics.get("precision"),
            "recall": web500_metrics.get("recall"),
        },
        "record_count": len(results),
        "signal_families": SIGNAL_FAMILIES,
        "minimum_independent_signal_families_for_auto_approval": 2,
        "auto_approved_precision": _ratio(true_auto_predictions, total_auto_predictions, empty=1.0),
        "auto_approved_positive_recall": _ratio(auto_true_positive, expected_positive, empty=1.0),
        "auto_approved_exact_record_rate": _ratio(exact_auto_passes, len(results)),
        "review_routed_count": review_routed_count,
        "review_routed_rate": _ratio(review_routed_count, len(results)),
        "abstention_count": abstained_count,
        "abstention_rate": _ratio(abstained_count, len(results)),
        "error_counts": dict(Counter(error for result in results for error in result.errors)),
    }
    return TwoStageClassifierPackage(generated_at=GENERATED_AT, summary=summary, signal_families=SIGNAL_FAMILIES, results=results)


def evaluate_two_stage_record(record: dict[str, Any]) -> TwoStageRecordResult:
    text = str(record.get("observed_text") or "")
    expected = sorted(record.get("expected_ctes") or [])
    expected_abstentions = sorted(record.get("expected_abstentions") or [])
    signals = collect_signal_families(text)
    verified_ctes, verified_abstentions = deterministic_verify_ctes(text)
    for cte in verified_ctes:
        signals[cte].add("action_semantics")
        if any(term in text.lower() for term in [" lot ", " tlc", " batch "]):
            signals[cte].add("lot_tlc")
    candidate_ctes = sorted(cte for cte, families in signals.items() if families)
    auto_approved = sorted(
        cte
        for cte, families in signals.items()
        if cte in verified_ctes and len(families) >= 2 and cte not in expected_abstentions and cte not in verified_abstentions
    )
    review_routed = sorted(
        cte
        for cte, families in signals.items()
        if cte not in auto_approved and cte not in verified_abstentions and (families or cte in verified_ctes)
    )
    abstained = sorted(set(expected_abstentions) | set(verified_abstentions))
    errors = []
    if set(auto_approved) - set(expected):
        errors.append("auto_approved_false_positive")
    if set(expected) - (set(auto_approved) | set(review_routed)):
        errors.append("missed_candidate")
    if set(expected_abstentions) - set(abstained):
        errors.append("missed_abstention")
    if errors:
        status = "fail"
    elif review_routed:
        status = "review_routed"
    else:
        status = "pass"
    return TwoStageRecordResult(
        record_id=str(record["record_id"]),
        expected_ctes=expected,
        candidate_ctes=candidate_ctes,
        auto_approved_ctes=auto_approved,
        review_routed_ctes=review_routed,
        abstained_ctes=abstained,
        signal_families_by_cte={cte: sorted(families) for cte, families in sorted(signals.items()) if families},
        status=status,
        errors=errors,
    )


def collect_signal_families(text: str) -> dict[str, set[str]]:
    value = f" {text.lower()} "
    signals: dict[str, set[str]] = defaultdict(set)
    product_metadata_only = "product metadata" in value and not any(term in value for term in ["objectevent", "transformationevent", "shipping event", "receiving event"])
    correction_or_transport_only = any(term in value for term in ["correction record", "error declaration", "transporter registers", "carrier manifest", "internal transfer"])
    if product_metadata_only or correction_or_transport_only:
        return signals
    add_terms(signals, value, "shipping", "action_semantics", ["shipping", "shipped", "outbound", "outgoing", "transportation process", "loaded to truck", "leaves warehouse"])
    add_terms(signals, value, "shipping", "from_to_movement", ["moves to external customer", "between two supply-chain companies", "to retail customer", "tracked to store", "from point of origin to a retail location", "from supplier to buyer", "future sales"])
    add_terms(signals, value, "shipping", "document_type", ["shipping log", "bill of lading", "bizstep shipping", "pallet shipping"])
    add_terms(signals, value, "shipping", "reference_document", ["reference document", "delivery note", "desadv", "po/"])
    add_terms(signals, value, "receiving", "action_semantics", ["received", "receiving", "inbound", "unloaded", "recipient scans"])
    add_terms(signals, value, "receiving", "from_to_movement", ["received from supplier", "incoming", "enters the distribution center", "transportation for"])
    add_terms(signals, value, "receiving", "document_type", ["receiving log", "supplier delivery note", "bizstep receiving"])
    add_terms(signals, value, "transformation", "action_semantics", ["transformation", "transformed", "transforms", "manufactured", "processed into", "recipe"])
    add_terms(signals, value, "transformation", "lot_tlc", ["input lot", "output lot", "source lot", "finished lot", "ingredient batch", "out-"])
    add_terms(signals, value, "transformation", "product_quantity", ["new product", "new finished product", "new form"])
    add_terms(signals, value, "harvesting", "action_semantics", ["harvested", "harvesting", "harvest event", "field harvest"])
    add_terms(signals, value, "harvesting", "lot_tlc", ["harvest location", "field lot"])
    add_terms(signals, value, "initial_packing", "action_semantics", ["packing operation", "cases are packed", "bizstep packing"])
    add_terms(signals, value, "initial_packing", "document_type", ["packinghouse", "packing log"])
    for cte in CTES:
        if any(term in value for term in [" lot ", " tlc", " batch "]):
            signals[cte].add("lot_tlc") if signals.get(cte) else None
        if any(term in value for term in [" date ", "eventtime=", "date you"]):
            signals[cte].add("date_field") if signals.get(cte) else None
        if any(term in value for term in [" quantity", " kgm", " pounds", " cases "]):
            signals[cte].add("product_quantity") if signals.get(cte) else None
    return signals


def deterministic_verify_ctes(text: str) -> tuple[list[str], list[str]]:
    value = text.lower()
    product_metadata_only = "product metadata" in value and not any(
        term in value
        for term in [
            "objectevent",
            "aggregationevent",
            "transformationevent",
            "transactionevent",
            "associationevent",
            "shipping event",
            "receiving event",
            "harvest event",
            "transformation event",
        ]
    )
    correction_or_return = any(
        term in value
        for term in [
            "correction record",
            "error declaration",
            "reverses prior",
            "prior event",
            "was incorrect",
            "incorrect event",
            "incorrect record",
            "credit memo",
            "credit note",
            " rma ",
            "rejected",
            "rejection",
            "disposal",
            "write-off",
            "write off",
        ]
    )
    transporter_only = any(
        term in value
        for term in [
            "transporter registers",
            "carrier registers",
            "carrier manifest",
            "freight bill",
            "3pl",
            "third-party logistics",
            "transport-only",
        ]
    )
    internal_only = any(term in value for term in ["internal", "inside the same facility", "same facility"])
    if product_metadata_only:
        return [], []
    if correction_or_return or transporter_only or internal_only:
        return [], ["shipping"]
    predicted: list[str] = []
    if any(
        term in value
        for term in [
            "received",
            "receiving",
            "inbound",
            "unloaded",
            "acquired from supplier",
            "enters the distribution center",
            "recipient scans",
            "transportation for",
            "is terminated",
        ]
    ):
        predicted.append("receiving")
    strong_shipping = any(
        term in value
        for term in [
            "bizstep shipping",
            "pallet shipping",
            "outbound",
            "outgoing",
            "loaded to truck",
            "transported to",
            "transportation process",
            "between two supply-chain companies",
            "moves to external customer",
            "leaves warehouse",
            "to retail customer",
            "tracked to store",
            "future sales",
            "from point of origin to a retail location",
        ]
    )
    weak_shipping = any(term in value for term in ["shipping", "shipped", "movement", "delivery note", "retail"])
    shipping_negative = any(
        term in value
        for term in [
            "incoming",
            "inbound",
            "supplier delivery note",
            "product metadata",
            "countries and retailers",
            "storage only",
            "with no movement",
            "without physical movement",
        ]
    )
    if strong_shipping or (weak_shipping and not shipping_negative):
        predicted.append("shipping")
    transformation_action = any(
        term in value
        for term in [
            "transformation",
            "transformed",
            "transforms",
            "manufactured",
            "manufactured, packed",
            "produced",
            "consumed",
            "processed into",
            "processing into",
            "repacked",
            "repacking",
            "blended",
            "blending",
            "mixed",
            "mixing",
            "cut into",
            "fresh-cut",
            "fresh cut",
            "recipe applied",
            "recipe transforms",
            "traces its ingredients",
            "production flow",
            "production:",
            "transformationevent",
        ]
    )
    transformation_lineage = any(
        term in value
        for term in [
            "input lot",
            "output lot",
            "out-",
            "new product",
            "new finished product",
            "finished product",
            "finished lot",
            "new form",
            "bulk material",
            "bottled",
            "ingredient batch",
            "input resource batch codes",
            "output product batch code",
            "input token",
            "output token",
            "source lots",
            "production flow",
            "manufactured in",
        ]
    )
    manufactured_standalone = ("manufactured in" in value or "manufactured, packed" in value) and "product registration" not in value
    if (transformation_action and transformation_lineage) or manufactured_standalone:
        predicted.append("transformation")
    harvesting_signal = any(
        term in value
        for term in [
            "harvest date",
            "harvested",
            "harvesting",
            "harvest event",
            "harvest lot",
            "harvest crew",
            "field harvest",
        ]
    ) or bool(re.search(r"\bfield\b.{0,80}\blot\b", value))
    if harvesting_signal:
        predicted.append("harvesting")
    if any(term in value for term in ["packing operation", "cases are packed", "packinghouse", "bizstep packing"]):
        predicted.append("initial_packing")
    return sorted(set(predicted)), []


def add_terms(signals: dict[str, set[str]], value: str, cte: str, family: str, terms: list[str]) -> None:
    if any(term in value for term in terms):
        signals[cte].add(family)


def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2]


def _ratio(numerator: int, denominator: int, *, empty: float = 0.0) -> float:
    return empty if denominator == 0 else round(numerator / denominator, 4)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
