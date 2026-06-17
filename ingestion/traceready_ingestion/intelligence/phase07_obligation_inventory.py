from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from traceready_ingestion.intelligence.citations import build_citation_coverage_report, load_chunk_index
from traceready_ingestion.intelligence.schemas import (
    CitationRef,
    ConfidenceLevel,
    CteType,
    DraftMetadata,
    ExtractionMethod,
    Obligation,
    ReviewStatus,
)


class ObligationComponentLinks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kde_requirement_ids: list[str] = Field(default_factory=list)
    tlc_rule_ids: list[str] = Field(default_factory=list)
    exemption_rule_ids: list[str] = Field(default_factory=list)
    traceability_plan_requirement_ids: list[str] = Field(default_factory=list)
    sortable_export_field_ids: list[str] = Field(default_factory=list)


class ObligationConfidenceScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float
    level: ConfidenceLevel
    factors: list[str] = Field(default_factory=list)


class ObligationInventoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inventory_record_id: str
    obligation: dict[str, Any]
    links: ObligationComponentLinks
    confidence_score: ObligationConfidenceScore
    review_status: ReviewStatus
    approval_ready: bool


class ApprovedObligationSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: str
    version: int
    status: str
    approved_at: str
    approved_by: str
    approval_role: str
    approval_reason: str
    immutable: bool
    source_review_package: str
    obligation_record_ids: list[str]
    records: list[dict[str, Any]]


class Phase7ObligationInventoryPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: dict[str, Any]
    obligation_drafts: list[dict[str, Any]]
    inventory_records: list[ObligationInventoryRecord]
    approved_obligation_set: ApprovedObligationSet
    citation_coverage_report: dict[str, Any]


def build_phase7_obligation_inventory(
    *,
    phase6_review_package_file: Path,
    chunks_file: Path,
) -> Phase7ObligationInventoryPackage:
    phase6_package = json.loads(phase6_review_package_file.read_text(encoding="utf-8"))
    chunk_index = load_chunk_index(chunks_file)
    source_chunks = list(chunk_index.values())
    draft_records = phase6_package["draft_records"]
    ready_records = [record for record in draft_records if record["review_status"] == ReviewStatus.NEEDS_REVIEW.value]

    deterministic_obligations = _build_deterministic_obligations(source_chunks)
    phase6_ready_obligations = [
        _normalize_phase6_obligation(record["payload"])
        for record in ready_records
        if record["collection"] == "obligations"
    ]
    obligation_drafts = _dedupe_obligations(deterministic_obligations + phase6_ready_obligations)

    citation_report = build_citation_coverage_report({"obligations": obligation_drafts}, chunk_index)
    component_index = _build_component_index(ready_records)
    inventory_records = [
        _inventory_record(obligation, component_index, citation_report.model_dump(mode="json"))
        for obligation in obligation_drafts
    ]
    approved_records = [_approved_obligation(record) for record in inventory_records if record.approval_ready]
    approved_set = ApprovedObligationSet(
        package_id="phase7-approved-obligation-set-v1",
        version=1,
        status="approved",
        approved_at="2026-06-16T00:00:00Z",
        approved_by="trace-ready-founder-admin-bootstrap",
        approval_role="founder_admin",
        approval_reason=(
            "Bootstrap approval for deterministic eCFR Subpart S obligation inventory. "
            "Records are exact-source cited, schema-valid, citation-span validated, and limited to codified-rule obligations."
        ),
        immutable=True,
        source_review_package=str(phase6_review_package_file),
        obligation_record_ids=[record["obligation_id"] for record in approved_records],
        records=approved_records,
    )
    summary = _summary(obligation_drafts, inventory_records, approved_set, citation_report.model_dump(mode="json"))
    return Phase7ObligationInventoryPackage(
        summary=summary,
        obligation_drafts=obligation_drafts,
        inventory_records=inventory_records,
        approved_obligation_set=approved_set,
        citation_coverage_report=citation_report.model_dump(mode="json"),
    )


def write_phase7_obligation_artifacts(package: Phase7ObligationInventoryPackage, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase7-summary.json",
        "obligationDrafts": output_dir / "phase7-obligation-drafts.json",
        "inventory": output_dir / "phase7-obligation-inventory.json",
        "approvedSet": output_dir / "phase7-approved-obligation-set-v1.json",
        "citationCoverageReport": output_dir / "phase7-citation-coverage-report.json",
    }
    _write_json(outputs["summary"], package.summary)
    _write_json(outputs["obligationDrafts"], package.obligation_drafts)
    _write_json(outputs["inventory"], [record.model_dump(mode="json") for record in package.inventory_records])
    _write_json(outputs["approvedSet"], package.approved_obligation_set.model_dump(mode="json"))
    _write_json(outputs["citationCoverageReport"], package.citation_coverage_report)
    return {key: str(path) for key, path in outputs.items()}


def _build_deterministic_obligations(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_section = {
        str(chunk.get("section_ref")): chunk
        for chunk in chunks
        if chunk.get("source_id") == "ecfr-21-cfr-1-subpart-s"
    }
    obligations: list[dict[str, Any]] = []
    for spec in _OBLIGATION_SPECS:
        chunk = by_section[spec["section_ref"]]
        citation = CitationRef(
            source_id=str(chunk["source_id"]),
            chunk_id=str(chunk["chunk_id"]),
            citation_anchor=str(chunk["citation_anchor"]),
            authority_rank=str(chunk["authority_rank"]),
            source_url=str(chunk["source_url"]),
            section_ref=str(chunk["section_ref"]),
            page_number=chunk.get("page_number"),
            support_text=str(chunk["text"]),
        )
        obligation = Obligation(
            citations=[citation],
            metadata=DraftMetadata(
                extraction_method=ExtractionMethod.DETERMINISTIC,
                confidence=ConfidenceLevel.HIGH,
                review_status=ReviewStatus.NEEDS_REVIEW,
                source_chunk_ids=[str(chunk["chunk_id"])],
            ),
            obligation_id=str(spec["obligation_id"]),
            subject=str(spec["subject"]),
            condition=str(spec["condition"]),
            action=str(spec["action"]),
            object=str(spec["object"]),
            required_output=spec.get("required_output"),
            deadline=spec.get("deadline"),
            exceptions=list(spec.get("exceptions", [])),
            applies_to_ctes=[CteType(value) for value in spec.get("applies_to_ctes", [])],
            applies_to_food_scope=spec.get("applies_to_food_scope"),
            noncompliance_risk=spec.get("noncompliance_risk"),
        )
        obligations.append(obligation.model_dump(mode="json"))
    return obligations


def _normalize_phase6_obligation(record: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(record))
    updated["metadata"]["review_status"] = ReviewStatus.NEEDS_REVIEW.value
    return updated


def _dedupe_obligations(obligations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for obligation in obligations:
        key = str(obligation["obligation_id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(obligation)
    return deduped


def _build_component_index(ready_records: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    index: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for record in ready_records:
        collection = str(record["collection"])
        payload = record["payload"]
        record_id = str(record["record_id"])
        for chunk_id in record["source_chunk_ids"]:
            index[str(chunk_id)][collection].append(record_id)
        for cte in payload.get("applies_to_ctes", []):
            index[f"cte:{cte}"][collection].append(record_id)
        if payload.get("cte_type"):
            index[f"cte:{payload['cte_type']}"][collection].append(record_id)
        if collection == "traceability_plan_requirements":
            index["cte:traceability_plan"][collection].append(record_id)
        if collection == "sortable_export_fields":
            index["records_and_export"][collection].append(record_id)
    return index


def _inventory_record(
    obligation: dict[str, Any],
    component_index: dict[str, dict[str, list[str]]],
    citation_report: dict[str, Any],
) -> ObligationInventoryRecord:
    obligation_id = str(obligation["obligation_id"])
    chunk_ids = list(obligation["metadata"].get("source_chunk_ids", []))
    ctes = list(obligation.get("applies_to_ctes", []))
    linked: dict[str, set[str]] = defaultdict(set)
    for chunk_id in chunk_ids:
        for collection, ids in component_index.get(chunk_id, {}).items():
            linked[collection].update(ids)
    for cte in ctes:
        for collection, ids in component_index.get(f"cte:{cte}", {}).items():
            linked[collection].update(ids)
    if obligation_id in {"FSMA204-OBL-DET-1455-FDA-REQUEST", "FSMA204-OBL-DET-1455-SORTABLE-SPREADSHEET"}:
        for collection, ids in component_index.get("records_and_export", {}).items():
            linked[collection].update(ids)

    links = ObligationComponentLinks(
        kde_requirement_ids=sorted(linked["kde_requirements"]),
        tlc_rule_ids=sorted(linked["tlc_rules"]),
        exemption_rule_ids=sorted(linked["exemption_rules"]),
        traceability_plan_requirement_ids=sorted(linked["traceability_plan_requirements"]),
        sortable_export_field_ids=sorted(linked["sortable_export_fields"]),
    )
    confidence = _confidence_score(obligation, citation_report)
    approval_ready = (
        confidence.level == ConfidenceLevel.HIGH
        and obligation["metadata"]["extraction_method"] == ExtractionMethod.DETERMINISTIC.value
        and _record_citation_status(obligation_id, citation_report) == "complete"
        and all(citation["authority_rank"] == "codified_rule" for citation in obligation["citations"])
    )
    return ObligationInventoryRecord(
        inventory_record_id=f"inventory:{obligation_id}",
        obligation=obligation,
        links=links,
        confidence_score=confidence,
        review_status=ReviewStatus.APPROVED if approval_ready else ReviewStatus.NEEDS_REVIEW,
        approval_ready=approval_ready,
    )


def _confidence_score(obligation: dict[str, Any], citation_report: dict[str, Any]) -> ObligationConfidenceScore:
    score = 0.0
    factors: list[str] = []
    if all(citation["authority_rank"] == "codified_rule" for citation in obligation["citations"]):
        score += 0.35
        factors.append("codified_rule_source")
    if obligation["metadata"]["extraction_method"] == ExtractionMethod.DETERMINISTIC.value:
        score += 0.25
        factors.append("deterministic_extraction")
    elif obligation["metadata"]["extraction_method"] == ExtractionMethod.AI_ASSISTED.value:
        score += 0.15
        factors.append("ai_assisted_extraction")
    if _record_citation_status(str(obligation["obligation_id"]), citation_report) == "complete":
        score += 0.25
        factors.append("complete_citation_span_validation")
    if obligation["metadata"]["review_status"] in {ReviewStatus.NEEDS_REVIEW.value, ReviewStatus.APPROVED.value}:
        score += 0.1
        factors.append("review_workflow_ready")
    if obligation["metadata"]["confidence"] == ConfidenceLevel.HIGH.value:
        score += 0.05
        factors.append("high_extraction_confidence")
    score = min(round(score, 2), 1.0)
    if score >= 0.9:
        level = ConfidenceLevel.HIGH
    elif score >= 0.7:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW
    return ObligationConfidenceScore(score=score, level=level, factors=factors)


def _record_citation_status(obligation_id: str, citation_report: dict[str, Any]) -> str:
    for record in citation_report.get("records", []):
        if record.get("record_id") == obligation_id:
            return str(record.get("coverage_status"))
    return "missing"


def _approved_obligation(record: ObligationInventoryRecord) -> dict[str, Any]:
    approved = json.loads(json.dumps(record.obligation))
    approved["metadata"]["review_status"] = ReviewStatus.APPROVED.value
    approved["metadata"]["reviewer_notes"] = [
        *approved["metadata"].get("reviewer_notes", []),
        "Approved in Phase 7 bootstrap obligation set from deterministic eCFR extraction.",
    ]
    return {
        **approved,
        "approval": {
            "approved_by": "trace-ready-founder-admin-bootstrap",
            "approval_role": "founder_admin",
            "approved_at": "2026-06-16T00:00:00Z",
            "approval_reason": "Deterministic codified-rule obligation with complete citation span validation.",
            "immutable_package_id": "phase7-approved-obligation-set-v1",
        },
        "links": record.links.model_dump(mode="json"),
        "confidence_score": record.confidence_score.model_dump(mode="json"),
    }


def _summary(
    obligation_drafts: list[dict[str, Any]],
    inventory_records: list[ObligationInventoryRecord],
    approved_set: ApprovedObligationSet,
    citation_report: dict[str, Any],
) -> dict[str, Any]:
    cte_coverage = sorted({cte for obligation in obligation_drafts for cte in obligation.get("applies_to_ctes", [])})
    links_counter = Counter()
    for record in inventory_records:
        if record.links.kde_requirement_ids:
            links_counter["with_kde_links"] += 1
        if record.links.tlc_rule_ids:
            links_counter["with_tlc_links"] += 1
        if record.links.exemption_rule_ids:
            links_counter["with_exemption_links"] += 1
        if record.links.traceability_plan_requirement_ids:
            links_counter["with_traceability_plan_links"] += 1
        if record.links.sortable_export_field_ids:
            links_counter["with_sortable_export_links"] += 1
    confidence_counts = Counter(record.confidence_score.level.value for record in inventory_records)
    return {
        "generatedAt": "2026-06-16T00:00:00Z",
        "obligationDrafts": len(obligation_drafts),
        "inventoryRecords": len(inventory_records),
        "approvedObligations": len(approved_set.records),
        "approvedPackageId": approved_set.package_id,
        "approvedPackageVersion": approved_set.version,
        "cteCoverage": cte_coverage,
        "linkCoverage": dict(sorted(links_counter.items())),
        "confidenceCounts": dict(sorted(confidence_counts.items())),
        "citationCoverage": citation_report.get("summary", {}),
        "coverageAreas": [
            "scope",
            "traceability_plan",
            "tlc_assignment",
            "cte_kde_duties",
            "records_maintenance",
            "fda_request_timing",
            "sortable_export",
        ],
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


_ALL_CORE_CTES = [
    "harvesting",
    "cooling",
    "initial_packing",
    "first_land_based_receiving",
    "shipping",
    "receiving",
    "transformation",
]

_OBLIGATION_SPECS: list[dict[str, Any]] = [
    {
        "obligation_id": "FSMA204-OBL-DET-1300-SCOPE",
        "section_ref": "21 CFR 1.1300",
        "subject": "Persons who manufacture, process, pack, or hold foods on the Food Traceability List",
        "condition": "Except as otherwise specified in Subpart S",
        "action": "Comply with the requirements in 21 CFR Part 1 Subpart S",
        "object": "Foods that appear on the Food Traceability List",
        "required_output": "Additional traceability records required by FSMA section 204(d)(2)",
        "exceptions": ["As otherwise specified in Subpart S"],
        "applies_to_ctes": _ALL_CORE_CTES,
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "Entity may fail to maintain required Subpart S traceability records.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1315-TRACEABILITY-PLAN",
        "section_ref": "21 CFR 1.1315",
        "subject": "Person subject to Subpart S",
        "condition": "When subject to Subpart S requirements",
        "action": "Establish and maintain a traceability plan",
        "object": "Traceability plan containing record procedures, FTL identification procedures, TLC assignment procedures when applicable, contact, and farm map where required",
        "required_output": "Traceability plan",
        "applies_to_ctes": ["traceability_plan"],
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "Traceability plan evidence may be missing or incomplete.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1320-TLC-ASSIGNMENT",
        "section_ref": "21 CFR 1.1320",
        "subject": "Person initially packing, first land-based receiving, or transforming FTL food",
        "condition": "When initially packing a RAC other than food from a fishing vessel, first land-based receiving food from a fishing vessel, or transforming food",
        "action": "Assign a traceability lot code and do not establish a new TLC for other activities unless otherwise specified",
        "object": "Traceability lot code",
        "required_output": "Assigned TLC for triggering CTEs",
        "applies_to_ctes": ["initial_packing", "first_land_based_receiving", "transformation"],
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "TLC assignment or preservation may be incorrect.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1325-HARVEST-COOLING-KDES",
        "section_ref": "21 CFR 1.1325",
        "subject": "Harvester or cooler of a raw agricultural commodity on the Food Traceability List",
        "condition": "When harvesting or cooling a RAC not obtained from a fishing vessel before initial packing",
        "action": "Maintain and provide required harvesting or cooling records",
        "object": "Harvesting and cooling KDE records",
        "required_output": "Harvesting/cooling information and reference document details",
        "applies_to_ctes": ["harvesting", "cooling"],
        "applies_to_food_scope": "Raw agricultural commodities on the Food Traceability List",
        "noncompliance_risk": "Harvesting or cooling KDEs may not be available to the initial packer.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1330-INITIAL-PACKING-KDES",
        "section_ref": "21 CFR 1.1330",
        "subject": "Initial packer of a raw agricultural commodity on the Food Traceability List",
        "condition": "When initially packing each traceability lot of RAC other than food obtained from a fishing vessel",
        "action": "Maintain records containing required initial packing information and link the information to the traceability lot",
        "object": "Initial packing KDE records",
        "required_output": "Initial packing records linked to the traceability lot",
        "applies_to_ctes": ["initial_packing"],
        "applies_to_food_scope": "Raw agricultural commodities on the Food Traceability List",
        "noncompliance_risk": "Initial packing records may not establish TLC source and required inbound facts.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1335-FIRST-LAND-BASED-RECEIVING-KDES",
        "section_ref": "21 CFR 1.1335",
        "subject": "First land-based receiver of FTL food obtained from a fishing vessel",
        "condition": "When first land-based receiving food obtained from a fishing vessel",
        "action": "Maintain records containing required first land-based receiving information and link the information to the traceability lot",
        "object": "First land-based receiving KDE records",
        "required_output": "First land-based receiving records linked to the traceability lot",
        "applies_to_ctes": ["first_land_based_receiving"],
        "applies_to_food_scope": "Food obtained from a fishing vessel on the Food Traceability List",
        "noncompliance_risk": "Seafood first land-based receiving KDEs may be missing.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1340-SHIPPING-KDES",
        "section_ref": "21 CFR 1.1340",
        "subject": "Person who ships food on the Food Traceability List",
        "condition": "For each traceability lot of FTL food shipped",
        "action": "Maintain shipping records linked to the traceability lot and provide required information to the immediate subsequent recipient",
        "object": "Shipping KDE records",
        "required_output": "Shipping records and pass-forward information",
        "applies_to_ctes": ["shipping"],
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "Shipping KDEs or pass-forward records may be missing.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1345-RECEIVING-KDES",
        "section_ref": "21 CFR 1.1345",
        "subject": "Person who receives food on the Food Traceability List",
        "condition": "For each traceability lot of FTL food received",
        "action": "Maintain receiving records containing required information and link the information to the traceability lot",
        "object": "Receiving KDE records",
        "required_output": "Receiving records linked to the traceability lot",
        "applies_to_ctes": ["receiving"],
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "Receiving KDEs or previous-source evidence may be missing.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1350-TRANSFORMATION-KDES",
        "section_ref": "21 CFR 1.1350",
        "subject": "Person who produces food through transformation involving FTL food",
        "condition": "For each new traceability lot of food produced through transformation",
        "action": "Maintain transformation records containing input and output traceability information and link it to the new traceability lot",
        "object": "Transformation KDE records",
        "required_output": "Transformation records linked to the new traceability lot",
        "applies_to_ctes": ["transformation"],
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "Input-output TLC lineage may be incomplete.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1455-RECORDS-MAINTENANCE",
        "section_ref": "21 CFR 1.1455",
        "subject": "Person required to maintain Subpart S records",
        "condition": "When maintaining records required under Subpart S",
        "action": "Keep records as original paper or electronic records or true copies, ensure legibility, and store records to prevent deterioration or loss",
        "object": "Subpart S records",
        "required_output": "Legible maintained records",
        "applies_to_ctes": ["other"],
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "Records may be unavailable, illegible, or not preserved.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1455-FDA-REQUEST",
        "section_ref": "21 CFR 1.1455",
        "subject": "Person required to maintain Subpart S records",
        "condition": "When an authorized FDA representative requests required records",
        "action": "Make all required records available within 24 hours or within a reasonable time agreed to by FDA",
        "object": "Required Subpart S records and explanatory information",
        "required_output": "Records and information needed to understand the records",
        "deadline": "within 24 hours unless FDA agrees to a reasonable time",
        "applies_to_ctes": ["other"],
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "FDA request response may be late or incomplete.",
    },
    {
        "obligation_id": "FSMA204-OBL-DET-1455-SORTABLE-SPREADSHEET",
        "section_ref": "21 CFR 1.1455",
        "subject": "Person required to maintain Subpart S records",
        "condition": "When FDA requests information necessary to help prevent or mitigate a foodborne illness outbreak, assist in recall implementation, or address a public health threat",
        "action": "Provide required information in an electronic sortable spreadsheet unless an exception applies",
        "object": "Electronic sortable spreadsheet",
        "required_output": "Sortable spreadsheet for specified foods and date ranges or TLCs",
        "deadline": "within 24 hours unless FDA agrees to a reasonable time",
        "exceptions": ["Specified smaller-entity exceptions in 21 CFR 1.1455(c)(3)(iii)"],
        "applies_to_ctes": ["other"],
        "applies_to_food_scope": "Foods on the Food Traceability List",
        "noncompliance_risk": "Sortable export package may not be generated for FDA response.",
    },
]
