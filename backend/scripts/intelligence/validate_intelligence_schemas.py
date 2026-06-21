from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bellwether_backend.intelligence.schemas import (
    CitationRef,
    ConfidenceLevel,
    CteDefinition,
    CteType,
    DefinedTerm,
    DraftMetadata,
    ExemptionEffect,
    ExemptionRule,
    ExtractionMethod,
    FtlFoodItem,
    KdeRequirement,
    Obligation,
    RequirementStatus,
    ReviewStatus,
    RiskRankingRef,
    ScenarioActor,
    ScenarioBenchmark,
    ScenarioEvent,
    ScenarioExpectedFinding,
    ScenarioExpectation,
    SortableExportField,
    TlcRule,
    TlcRuleKind,
    TraceabilityPlanRequirement,
    dump_json_schemas,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Bellwether regulatory intelligence schemas with real registry citations.")
    parser.add_argument("--registry-dir", default="../data/regulatory/registry")
    parser.add_argument("--output-file", default="../data/regulatory/intelligence/schema-smoke-output.json")
    args = parser.parse_args()

    registry_dir = Path(args.registry_dir)
    chunks = json.loads((registry_dir / "source-chunks.json").read_text(encoding="utf-8"))

    ecfr_citation = _citation_for(chunks, source_id="ecfr-21-cfr-1-subpart-s", contains="Critical tracking event")
    ftl_citation = _citation_for(chunks, source_id="fda-food-traceability-list", contains="Food Traceability List Description")
    kde_citation = _citation_for(chunks, source_id="fda-cte-kde-pdf", contains="Harvesting KDEs")
    tlc_citation = _citation_for(chunks, source_id="fda-traceability-lot-code", contains="traceability lot code (TLC) is an integral component")
    exemption_citation = _citation_for(chunks, source_id="fda-produce-farms-exemptions", contains="exemptions relevant to produce farms")
    plan_citation = _citation_for(chunks, source_id="ecfr-21-cfr-1-subpart-s", contains="traceability plan")
    sortable_citation = _citation_for(chunks, source_id="fda-sortable-spreadsheet-xlsx", contains="sortable spreadsheet template")
    scenario_citation = _citation_for(chunks, source_id="scenario-produce-cucumbers-slides", contains="Supply Chain Example: Cucumbers")

    samples = {
        "defined_terms": DefinedTerm(
            term_id="defined_term_critical_tracking_event",
            term="Critical tracking event",
            normalized_key="critical_tracking_event",
            definition="An event in the supply chain involving a food on the Food Traceability List for which records are required.",
            scope="FSMA 204 / 21 CFR Part 1 Subpart S",
            source_authority="codified_rule",
            related_terms=["key_data_element", "traceability_lot_code"],
            citations=[ecfr_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.MEDIUM, [ecfr_citation]),
        ),
        "obligations": Obligation(
            obligation_id="obligation_maintain_traceability_records_for_ctes",
            subject="Persons who manufacture, process, pack, or hold foods on the Food Traceability List",
            condition="A covered critical tracking event is performed and no exemption applies.",
            action="maintain and provide required traceability records",
            object="key data elements for the applicable critical tracking event",
            required_output="records sufficient to support traceability and FDA-requested sortable export",
            deadline="As required by applicable Subpart S recordkeeping and FDA request provisions",
            exceptions=[],
            applies_to_ctes=[CteType.HARVESTING, CteType.SHIPPING, CteType.RECEIVING],
            applies_to_food_scope="Food Traceability List foods",
            noncompliance_risk="missing audit evidence or incomplete FDA response package",
            citations=[ecfr_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.MEDIUM, [ecfr_citation]),
        ),
        "ftl_food_items": FtlFoodItem(
            ftl_item_id="ftl_food_item_leafy_greens",
            category="Produce - RAC",
            commodity="Leafy greens",
            description="Leafy greens listed on the FDA Food Traceability List.",
            included_examples=["lettuces", "leafy greens"],
            excluded_examples=[],
            form_notes=["Requires exact FDA row extraction in deterministic parser before approval."],
            risk_ranking_refs=[RiskRankingRef(source_id="fda-ftl-risk-ranking-results-table-1a", commodity_risk_score=430)],
            raw_list_text="Food Traceability List Description ... Leafy Greens ...",
            citations=[ftl_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.LOW, [ftl_citation]),
        ),
        "cte_definitions": CteDefinition(
            cte_id="cte_harvesting",
            cte_type=CteType.HARVESTING,
            display_name="Harvesting",
            definition="Harvesting is a critical tracking event for certain raw agricultural commodities.",
            trigger_conditions=["A raw agricultural commodity on the FTL is harvested."],
            actor_roles=["harvester", "farm"],
            input_event_relationship=None,
            output_event_relationship="Provides KDEs to the initial packer when applicable.",
            excluded_conditions=[],
            citations=[kde_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.LOW, [kde_citation]),
        ),
        "kde_requirements": KdeRequirement(
            kde_id="kde_harvesting_location_description",
            cte_type=CteType.HARVESTING,
            kde_name="Location description for the immediate subsequent recipient",
            field_key="immediate_subsequent_recipient_location_description",
            required_status=RequirementStatus.REQUIRED,
            applies_to="Harvesting KDEs for applicable raw agricultural commodities.",
            provider_role="harvester",
            recipient_role="initial packer",
            data_type="text",
            conditional_logic=None,
            evidence_examples=["harvest record", "grower record", "supplier-provided KDE file"],
            severity_if_missing="high",
            citations=[kde_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.MEDIUM, [kde_citation]),
        ),
        "tlc_rules": TlcRule(
            tlc_rule_id="tlc_rule_assignment_and_preservation_for_ftl_lots",
            rule_kind=TlcRuleKind.ASSIGNMENT,
            applies_to_ctes=[CteType.INITIAL_PACKING, CteType.FIRST_LAND_BASED_RECEIVING, CteType.TRANSFORMATION],
            applies_to_food_scope="Food Traceability List foods when a traceability lot code must be assigned or preserved.",
            assignment_rule="Covered records must support identifying the traceability lot code assigned to the food when the rule requires one.",
            preservation_rule="Downstream records should preserve the traceability lot code or source reference needed to link the lot through the supply chain.",
            source_reference_rule="If the TLC source is not directly available, source-reference fields must support traceback to the TLC source.",
            transformation_handling="Transformation events may require linking input TLCs to a new output traceability lot code.",
            uniqueness_rule="The TLC should be usable as an identifier for the relevant traceability lot in the operator's records.",
            lineage_rule="The TLC must support linking event records across the applicable chain of custody.",
            required_status=RequirementStatus.CONDITIONAL,
            evidence_examples=["lot registry", "receiving record", "transformation record", "supplier ASN"],
            unresolved_questions=["Exact executable applies-when logic must come from deterministic extraction and reviewer approval."],
            citations=[tlc_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.LOW, [tlc_citation]),
        ),
        "exemption_rules": ExemptionRule(
            exemption_rule_id="exemption_rule_produce_farm_relevant_exemptions",
            exemption_type="Produce farm exemption or partial exemption candidate",
            eligibility_condition="A produce farm claims an exemption relevant to the Produce Safety Rule or Food Traceability Rule.",
            effect=ExemptionEffect.UNKNOWN,
            affected_requirements=["FSMA 204 applicability", "recordkeeping duties"],
            documentation_needed=["business/entity facts", "food/product facts", "supporting exemption documentation"],
            applies_to_entities=["produce farms"],
            applies_to_foods=["produce"],
            applies_to_ctes=[CteType.HARVESTING, CteType.COOLING, CteType.INITIAL_PACKING],
            decision_questions=[
                "Which exemption is claimed?",
                "Does the entity meet the eligibility conditions?",
                "Is the exemption full, partial, or only modifying requirements?",
            ],
            reviewer_warning="Do not treat exemption status as approved until reviewed against exact CFR text and entity facts.",
            citations=[exemption_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.LOW, [exemption_citation]),
        ),
        "traceability_plan_requirements": TraceabilityPlanRequirement(
            traceability_plan_requirement_id="traceability_plan_requirement_plan_must_exist",
            plan_component="Traceability plan",
            required_detail="Covered entities must maintain traceability plan information sufficient to explain how required traceability records are maintained.",
            applies_to="Entities covered by 21 CFR Part 1 Subpart S unless an exemption applies.",
            required_status=RequirementStatus.REQUIRED,
            evidence_examples=["traceability plan document", "SOP", "location and recordkeeping map"],
            update_trigger="Update when recordkeeping procedures, products, locations, systems, or responsible parties change.",
            owner_role="food safety, quality, compliance, or operations owner",
            citations=[plan_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.MEDIUM, [plan_citation]),
        ),
        "sortable_export_fields": SortableExportField(
            sortable_export_field_id="sortable_export_field_traceability_lot_code",
            workbook_tab="Receiving",
            field_name="Traceability Lot Code",
            field_key="traceability_lot_code",
            data_type="text",
            required_status=RequirementStatus.CONDITIONAL,
            source_mapping="Map from receiving event line item, supplier ASN, EDI 856, label, or lot registry.",
            applies_to_ctes=[CteType.RECEIVING],
            accepted_examples=["ABC123", "supplier-assigned lot code"],
            validation_notes=["Required status depends on CTE, food scope, and applicable exemption or source-reference pathway."],
            citations=[sortable_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.LOW, [sortable_citation]),
        ),
        "scenario_benchmarks": ScenarioBenchmark(
            scenario_benchmark_id="scenario_benchmark_cucumbers_initial_pack_to_receiving",
            scenario_name="FDA cucumber supply chain example",
            scenario_source="FDA supply chain example slides",
            food_scope="Cucumbers on the Food Traceability List",
            actors=[
                ScenarioActor(
                    actor_id="actor_farm",
                    actor_name="Cucumber farm",
                    role="harvester",
                    location_description="farm/growing area",
                ),
                ScenarioActor(
                    actor_id="actor_receiver",
                    actor_name="Receiving customer",
                    role="receiver",
                    location_description="receiving location",
                ),
            ],
            events=[
                ScenarioEvent(
                    event_id="event_harvest",
                    cte_type=CteType.HARVESTING,
                    actor_id="actor_farm",
                    event_description="Cucumbers are harvested and associated KDEs are expected for applicable records.",
                    expected_kde_field_keys=["commodity", "quantity", "harvest_date"],
                    expected_tlc_behavior="TLC behavior must be validated by exact scenario extraction.",
                ),
                ScenarioEvent(
                    event_id="event_receiving",
                    cte_type=CteType.RECEIVING,
                    actor_id="actor_receiver",
                    event_description="Customer receives cucumbers and must have receiving evidence for applicable KDEs.",
                    expected_kde_field_keys=["traceability_lot_code", "quantity", "received_date"],
                    expected_tlc_behavior="Receiving record should support lot-level linkage.",
                ),
            ],
            expectations=[
                ScenarioExpectation(
                    expectation_id="expectation_receiving_export_ready",
                    event_id="event_receiving",
                    expected_finding=ScenarioExpectedFinding.NEEDS_REVIEW,
                    expected_behavior="Scenario parser should produce expected receiving KDEs and flag unresolved assumptions for reviewer approval.",
                    required_evidence=["scenario slide text", "event relationship"],
                    expected_export_behavior="Sortable export expectation must be derived from approved KDE and export-field records.",
                )
            ],
            open_questions=["Exact actors and CTE sequence must be extracted from the complete scenario document in Phase 4."],
            citations=[scenario_citation],
            metadata=_metadata(ExtractionMethod.HUMAN_AUTHORED, ConfidenceLevel.LOW, [scenario_citation]),
        ),
    }

    output = {
        "samples": {name: sample.model_dump(mode="json") for name, sample in samples.items()},
        "jsonSchemas": dump_json_schemas(),
    }
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"validatedSchemas": sorted(samples), "outputFile": str(output_path)}, indent=2))


def _metadata(method: ExtractionMethod, confidence: ConfidenceLevel, citations: list[CitationRef]) -> DraftMetadata:
    return DraftMetadata(
        extraction_method=method,
        confidence=confidence,
        review_status=ReviewStatus.DRAFT,
        source_chunk_ids=[citation.chunk_id for citation in citations],
    )


def _citation_for(chunks: list[dict], *, source_id: str, contains: str) -> CitationRef:
    for chunk in chunks:
        if chunk.get("source_id") == source_id and contains.lower() in str(chunk.get("text", "")).lower():
            return CitationRef(
                source_id=chunk["source_id"],
                chunk_id=chunk["chunk_id"],
                citation_anchor=chunk["citation_anchor"],
                authority_rank=chunk["authority_rank"],
                source_url=chunk["source_url"],
                section_ref=chunk.get("section_ref"),
                page_number=chunk.get("page_number"),
                support_text=contains,
            )
    raise ValueError(f"No chunk found for source_id={source_id!r} containing {contains!r}")


if __name__ == "__main__":
    main()
