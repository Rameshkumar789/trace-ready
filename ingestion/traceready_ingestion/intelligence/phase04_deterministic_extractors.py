from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from traceready_ingestion.intelligence.schemas import (
    CitationRef,
    ConfidenceLevel,
    CteDefinition,
    CteType,
    DefinedTerm,
    DraftMetadata,
    ExtractionMethod,
    FtlFoodItem,
    KdeRequirement,
    RequirementStatus,
    ReviewStatus,
    ScenarioActor,
    ScenarioBenchmark,
    ScenarioEvent,
    ScenarioExpectedFinding,
    ScenarioExpectation,
    SortableExportField,
    TraceabilityPlanRequirement,
)


FTL_HEADINGS = [
    "Cheese (made from pasteurized milk), fresh soft or soft unripened",
    "Cheese (made from pasteurized milk), soft ripened or semi-soft",
    "Cheese (made from unpasteurized milk), other than hard cheese",
    "Shell eggs",
    "Nut butters",
    "Cucumbers (fresh)",
    "Herbs (fresh)",
    "Leafy greens (fresh)",
    "Leafy greens (fresh-cut)",
    "Melons (fresh)",
    "Peppers (fresh)",
    "Sprouts (fresh)",
    "Tomatoes (fresh)",
    "Tropical tree fruits (fresh)",
    "Fruits (fresh-cut)",
    "Vegetables other than leafy greens (fresh-cut)",
    "Finfish (fresh, frozen, and previously frozen), specifically:",
    "Crustaceans",
    "Molluscan shellfish, bivalves",
    "Ready-to-eat deli salads",
]

DEFINED_TERMS = [
    "Commingled raw agricultural commodity",
    "Cooling",
    "Critical tracking event",
    "Farm",
    "First land-based receiver",
    "Fishing vessel",
    "Food Traceability List",
    "Harvesting",
    "Initial packing",
    "Key data element",
    "Location description",
    "Person",
    "Point of contact",
    "Produce",
    "Product description",
    "Reference document",
    "Reference document number",
    "Restaurant",
    "Retail food establishment",
    "Shipping",
    "Traceability lot",
    "Traceability lot code",
    "Traceability lot code source",
    "Traceability lot code source reference",
    "Transformation",
    "Transporter",
]

CTE_DEFINITION_TERMS = {
    CteType.HARVESTING: "Harvesting",
    CteType.COOLING: "Cooling",
    CteType.INITIAL_PACKING: "Initial packing",
    CteType.FIRST_LAND_BASED_RECEIVING: "First land-based receiver",
    CteType.SHIPPING: "Shipping",
    CteType.TRANSFORMATION: "Transformation",
}

DEFINED_TERM_MARKERS = {
    "Harvesting": "Harvesting applies",
    "Person": "Person includes",
}

SORTABLE_TAB_CTES = {
    "Harvesting": CteType.HARVESTING,
    "Cooling": CteType.COOLING,
    "Initial Packing": CteType.INITIAL_PACKING,
    "Initial Packing Sprouts": CteType.INITIAL_PACKING,
    "Initial Packing from Exempt": CteType.INITIAL_PACKING,
    "First Land-Based Receiving": CteType.FIRST_LAND_BASED_RECEIVING,
    "Shipping": CteType.SHIPPING,
    "Receiving": CteType.RECEIVING,
    "Receiving From Exempt": CteType.RECEIVING,
    "Transformation": CteType.TRANSFORMATION,
    "Farm Purchase by RFE or Rest.": CteType.OTHER,
    "Ad-hoc RFE or Rest. Purchase": CteType.OTHER,
    "Farm to School or Institution": CteType.OTHER,
}

CTE_KDE_PAGE_MAP = {
    2: CteType.HARVESTING,
    3: CteType.COOLING,
    4: CteType.INITIAL_PACKING,
    5: CteType.INITIAL_PACKING,
    7: CteType.FIRST_LAND_BASED_RECEIVING,
    8: CteType.SHIPPING,
    9: CteType.RECEIVING,
    10: CteType.TRANSFORMATION,
}


def extract_ftl_food_items(chunks: list[dict[str, Any]]) -> list[FtlFoodItem]:
    chunk = _require_chunk(chunks, "fda-food-traceability-list", section_ref="21 CFR 1.1305")
    text = _squash(chunk["text"])
    heading_matches = _find_ordered_headings(text, FTL_HEADINGS)
    records: list[FtlFoodItem] = []

    for index, (heading, start) in enumerate(heading_matches):
        end = heading_matches[index + 1][1] if index + 1 < len(heading_matches) else len(text)
        raw = text[start:end].strip()
        if not raw:
            continue
        description = _first_sentence(raw.replace(heading, "", 1).strip()) or raw
        records.append(
            FtlFoodItem(
                ftl_item_id=f"ftl_{_slug(heading)}",
                category=_ftl_category(heading),
                commodity=_strip_footnotes(heading),
                description=description,
                included_examples=_extract_examples(raw, "Examples include"),
                excluded_examples=_extract_excluded(raw),
                form_notes=_extract_form_notes(raw),
                raw_list_text=raw,
                risk_ranking_refs=[],
                citations=[_citation(chunk, support_text=_strip_footnotes(heading))],
                metadata=_metadata(ExtractionMethod.DETERMINISTIC, ConfidenceLevel.HIGH, chunk),
            )
        )
    return records


def extract_sortable_export_fields(chunks: list[dict[str, Any]], workbook_path: Path) -> list[SortableExportField]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    records: list[SortableExportField] = []

    for worksheet in workbook.worksheets:
        tab = worksheet.title.strip()
        if tab in {"Introduction", "Definitions"}:
            continue
        cte_type = SORTABLE_TAB_CTES.get(tab, CteType.OTHER)
        chunk = _require_chunk(chunks, "fda-sortable-spreadsheet-xlsx", section_ref=tab)
        headers = [_clean_header(cell.value) for cell in worksheet[1] if cell.value not in (None, "")]
        for position, header in enumerate(headers, start=1):
            field_key = _dedupe_field_key(tab, header, position)
            records.append(
                SortableExportField(
                    sortable_export_field_id=f"sortable_{_slug(tab)}_{position:03d}_{field_key}",
                    workbook_tab=tab,
                    field_name=header,
                    field_key=field_key,
                    data_type=_infer_data_type(header),
                    required_status=_infer_required_status(header),
                    source_mapping=f"FDA sortable spreadsheet tab: {tab}",
                    applies_to_ctes=[cte_type] if cte_type != CteType.OTHER else [],
                    accepted_examples=_extract_parenthetical_examples(header),
                    validation_notes=_sortable_validation_notes(header),
                    citations=[_citation(chunk, support_text=_support_text_for(chunk, header))],
                    metadata=_metadata(ExtractionMethod.IMPORTED_TEMPLATE, ConfidenceLevel.HIGH, chunk),
                )
            )
    return records


def extract_cte_kde_candidates(chunks: list[dict[str, Any]]) -> tuple[list[CteDefinition], list[KdeRequirement]]:
    records: list[KdeRequirement] = []
    for page_number, cte_type in CTE_KDE_PAGE_MAP.items():
        chunk = _require_chunk(chunks, "fda-cte-kde-pdf", page_number=page_number)
        bullets = _extract_bullets(chunk["text"])
        for position, bullet in enumerate(bullets, start=1):
            kde_name = _clean_kde_candidate(bullet)
            if not _is_kde_like(kde_name):
                continue
            records.append(
                KdeRequirement(
                    kde_id=f"kde_{cte_type.value}_{position:02d}_{_truncate_slug(_slug(kde_name), 80)}",
                    cte_type=cte_type,
                    kde_name=kde_name,
                    field_key=_truncate_slug(_slug(kde_name), 100),
                    required_status=_infer_required_status(kde_name),
                    applies_to=_cte_applies_to(cte_type),
                    data_type=_infer_data_type(kde_name),
                    conditional_logic=_conditional_logic(kde_name),
                    evidence_examples=_kde_evidence_examples(kde_name),
                    severity_if_missing="review_required",
                    citations=[_citation(chunk, support_text=_support_text_for(chunk, bullet))],
                    metadata=_metadata(ExtractionMethod.DETERMINISTIC, ConfidenceLevel.MEDIUM, chunk),
                )
            )

    cte_records = extract_cte_definitions(chunks)
    return cte_records, _dedupe_records(records, "kde_id")


def extract_defined_terms(chunks: list[dict[str, Any]]) -> list[DefinedTerm]:
    chunk = _require_chunk(chunks, "ecfr-21-cfr-1-subpart-s", section_ref="21 CFR 1.1310")
    text = _squash(chunk["text"])
    term_markers = [(term, DEFINED_TERM_MARKERS.get(term, f"{term} means")) for term in DEFINED_TERMS]
    term_positions: list[tuple[str, str, int]] = []
    for term, marker in term_markers:
        match = re.search(re.escape(marker), text, flags=re.IGNORECASE)
        if match:
            term_positions.append((term, marker, match.start()))
    term_positions.sort(key=lambda item: item[2])
    records: list[DefinedTerm] = []

    for index, (term, marker, start) in enumerate(term_positions):
        end = term_positions[index + 1][2] if index + 1 < len(term_positions) else len(text)
        definition = text[start:end].replace(marker, "", 1).strip()
        definition = definition.rstrip(" .") + "."
        records.append(
            DefinedTerm(
                term_id=f"term_{_slug(term)}",
                term=term,
                normalized_key=_slug(term),
                definition=definition,
                scope="21 CFR Part 1 Subpart S",
                source_authority="eCFR current text",
                related_terms=_related_terms(term, DEFINED_TERMS),
                citations=[_citation(chunk, support_text=marker)],
                metadata=_metadata(ExtractionMethod.DETERMINISTIC, ConfidenceLevel.HIGH, chunk),
            )
        )
    return records


def extract_cte_definitions(chunks: list[dict[str, Any]]) -> list[CteDefinition]:
    terms = {record.term: record for record in extract_defined_terms(chunks)}
    definitions: list[CteDefinition] = []
    chunk = _require_chunk(chunks, "ecfr-21-cfr-1-subpart-s", section_ref="21 CFR 1.1310")

    for cte_type, term in CTE_DEFINITION_TERMS.items():
        record = terms.get(term)
        if not record:
            continue
        definitions.append(
            CteDefinition(
                cte_id=f"cte_{cte_type.value}",
                cte_type=cte_type,
                display_name=term,
                definition=record.definition,
                trigger_conditions=[_first_sentence(record.definition)],
                actor_roles=_actor_roles_for_cte(cte_type),
                input_event_relationship=_input_relationship(cte_type),
                output_event_relationship=_output_relationship(cte_type),
                excluded_conditions=[],
                citations=[_citation(chunk, support_text=DEFINED_TERM_MARKERS.get(term, f"{term} means"))],
                metadata=_metadata(ExtractionMethod.DETERMINISTIC, ConfidenceLevel.HIGH, chunk),
            )
        )

    receiving_chunk = _require_chunk(chunks, "ecfr-21-cfr-1-subpart-s", section_ref="21 CFR 1.1345")
    definitions.append(
        CteDefinition(
            cte_id="cte_receiving",
            cte_type=CteType.RECEIVING,
            display_name="Receiving",
            definition="Receiving is treated as a critical tracking event when a person receives a food on the Food Traceability List and must keep the required receiving records.",
            trigger_conditions=["Person receives a food on the Food Traceability List."],
            actor_roles=["receiver"],
            input_event_relationship="Inbound traceability lot from immediate previous source.",
            output_event_relationship="Receiving records link inbound food to source, TLC, and reference documents.",
            excluded_conditions=[],
            citations=[_citation(receiving_chunk, support_text="For each traceability lot of a food on the Food Traceability List you receive")],
            metadata=_metadata(ExtractionMethod.DETERMINISTIC, ConfidenceLevel.MEDIUM, receiving_chunk),
        )
    )
    return definitions


def extract_traceability_plan_requirements(chunks: list[dict[str, Any]]) -> list[TraceabilityPlanRequirement]:
    chunk = _require_chunk(chunks, "ecfr-21-cfr-1-subpart-s", section_ref="21 CFR 1.1315")
    requirements = [
        (
            "record_maintenance_procedures",
            "Record maintenance procedures",
            "A description of the procedures you use to maintain the records you are required to keep under this subpart, including the format and location of these records.",
            "all covered entities subject to Subpart S",
            "food safety / compliance owner",
            None,
        ),
        (
            "ftl_food_identification",
            "FTL food identification procedures",
            "A description of the procedures you use to identify foods on the Food Traceability List that you manufacture, process, pack, or hold.",
            "all covered entities that manufacture, process, pack, or hold FTL foods",
            "food safety / operations owner",
            None,
        ),
        (
            "tlc_assignment_procedure",
            "Traceability lot code assignment procedure",
            "A description of how you assign traceability lot codes to foods on the Food Traceability List in accordance with § 1.1320, if applicable.",
            "entities that assign traceability lot codes",
            "traceability program owner",
            None,
        ),
        (
            "point_of_contact",
            "Traceability point of contact",
            "A statement identifying a point of contact for questions regarding your traceability plan and records.",
            "all covered entities subject to Subpart S",
            "point of contact named in the traceability plan",
            None,
        ),
        (
            "farm_map",
            "Farm map",
            "If you grow or raise a food on the Food Traceability List (other than eggs), a farm map showing the areas in which you grow or raise such foods.",
            "farms that grow or raise FTL foods other than eggs",
            "farm operator",
            "Update when growing areas, containers, or location-identifying information change.",
        ),
        (
            "plan_update_and_retention",
            "Plan update and retention",
            "You must update your traceability plan as needed to ensure that the information provided reflects your current practices and retain your previous traceability plan for 2 years after you update the plan.",
            "all covered entities subject to Subpart S",
            "traceability program owner",
            "Update as needed to reflect current practices.",
        ),
    ]

    records: list[TraceabilityPlanRequirement] = []
    for requirement_id, component, detail, applies_to, owner_role, update_trigger in requirements:
        records.append(
            TraceabilityPlanRequirement(
                traceability_plan_requirement_id=f"traceability_plan_{requirement_id}",
                plan_component=component,
                required_detail=detail,
                applies_to=applies_to,
                required_status=RequirementStatus.REQUIRED,
                evidence_examples=_plan_evidence_examples(component),
                update_trigger=update_trigger,
                owner_role=owner_role,
                citations=[_citation(chunk, support_text=_support_text_for(chunk, detail))],
                metadata=_metadata(ExtractionMethod.DETERMINISTIC, ConfidenceLevel.HIGH, chunk),
            )
        )
    return records


def extract_scenario_benchmarks(chunks: list[dict[str, Any]]) -> list[ScenarioBenchmark]:
    scenario_specs = [
        ("scenario-produce-cucumbers-slides", 2, "FDA cucumber supply chain example", "Fresh cucumbers on the Food Traceability List", [CteType.HARVESTING, CteType.INITIAL_PACKING, CteType.SHIPPING, CteType.RECEIVING]),
        ("scenario-seafood-tuna-slides", 2, "FDA wild-caught tuna supply chain example", "Wild-caught tuna / finfish on the Food Traceability List", [CteType.FIRST_LAND_BASED_RECEIVING, CteType.SHIPPING, CteType.RECEIVING]),
        ("scenario-cheese-slides", 2, "FDA soft cheese supply chain example", "Soft cheese on the Food Traceability List", [CteType.TRANSFORMATION, CteType.SHIPPING, CteType.RECEIVING]),
        ("scenario-deli-salad-slides", 3, "FDA deli salad with FTL and non-FTL ingredients example", "Ready-to-eat deli salad with FTL ingredients", [CteType.RECEIVING, CteType.TRANSFORMATION, CteType.SHIPPING]),
        ("scenario-deli-salad-slides", 4, "FDA tuna salad using canned tuna example", "Ready-to-eat deli salad using canned tuna", [CteType.RECEIVING, CteType.TRANSFORMATION, CteType.SHIPPING]),
        ("scenario-sprouts-slides", 3, "FDA sprouts supply chain example", "Fresh sprouts on the Food Traceability List", [CteType.INITIAL_PACKING, CteType.SHIPPING, CteType.RECEIVING]),
    ]
    records: list[ScenarioBenchmark] = []

    for source_id, page_number, name, food_scope, ctes in scenario_specs:
        chunk = _require_chunk(chunks, source_id, page_number=page_number)
        actors = [
            ScenarioActor(actor_id="covered_entity", actor_name="Covered entity in FDA scenario", role="covered operator"),
            ScenarioActor(actor_id="trading_partner", actor_name="Trading partner in FDA scenario", role="supplier or recipient"),
        ]
        events = [
            ScenarioEvent(
                event_id=f"event_{index}_{cte.value}",
                cte_type=cte,
                actor_id="covered_entity",
                event_description=f"Reviewer should map the FDA scenario graphic/narrative to the {cte.value.replace('_', ' ')} CTE.",
                expected_kde_field_keys=[],
                expected_tlc_behavior="KDEs must remain linked to the applicable traceability lot when the CTE requires lot linkage.",
            )
            for index, cte in enumerate(ctes, start=1)
        ]
        records.append(
            ScenarioBenchmark(
                scenario_benchmark_id=f"scenario_{_slug(source_id)}_page_{page_number}",
                scenario_name=name,
                scenario_source=source_id,
                food_scope=food_scope,
                actors=actors,
                events=events,
                expectations=[
                    ScenarioExpectation(
                        expectation_id="expectation_traceability_plan",
                        expected_finding=ScenarioExpectedFinding.NEEDS_REVIEW,
                        expected_behavior="Covered entities shown in the FDA scenario should maintain a traceability plan in addition to CTE/KDE records.",
                        required_evidence=["traceability plan", "event records", "linked KDEs"],
                        expected_export_behavior="Scenario-derived records should be exportable only after reviewer confirms actor roles and CTE sequence.",
                    )
                ],
                open_questions=[
                    "Reviewer must confirm exact actor names and arrows from the FDA scenario graphic.",
                    "Reviewer must confirm which KDE rows apply to each actor before this benchmark becomes executable.",
                ],
                citations=[_citation(chunk, support_text=_scenario_support_text(chunk))],
                metadata=_metadata(ExtractionMethod.DETERMINISTIC, ConfidenceLevel.LOW, chunk),
            )
        )
    return records


def _require_chunk(
    chunks: Iterable[dict[str, Any]],
    source_id: str,
    *,
    section_ref: str | None = None,
    page_number: int | None = None,
) -> dict[str, Any]:
    for chunk in chunks:
        if chunk.get("source_id") != source_id:
            continue
        if section_ref is not None and str(chunk.get("section_ref", "")).strip() != section_ref:
            continue
        if page_number is not None and chunk.get("page_number") != page_number:
            continue
        return chunk
    raise LookupError(f"Missing chunk for source_id={source_id!r}, section_ref={section_ref!r}, page_number={page_number!r}")


def _citation(chunk: dict[str, Any], support_text: str | None = None) -> CitationRef:
    support = support_text if support_text and support_text in chunk["text"] else _fallback_support_text(chunk)
    return CitationRef(
        source_id=chunk["source_id"],
        chunk_id=chunk["chunk_id"],
        citation_anchor=chunk["citation_anchor"],
        authority_rank=chunk["authority_rank"],
        source_url=chunk["source_url"],
        section_ref=chunk.get("section_ref"),
        page_number=chunk.get("page_number"),
        support_text=support,
    )


def _metadata(method: ExtractionMethod, confidence: ConfidenceLevel, chunk: dict[str, Any]) -> DraftMetadata:
    return DraftMetadata(
        extraction_method=method,
        confidence=confidence,
        review_status=ReviewStatus.DRAFT,
        source_chunk_ids=[chunk["chunk_id"]],
    )


def _fallback_support_text(chunk: dict[str, Any]) -> str:
    text = _squash(chunk.get("text", ""))
    return text[: min(160, len(text))]


def _support_text_for(chunk: dict[str, Any], preferred: str) -> str:
    preferred = _squash(preferred)
    if preferred and preferred in chunk["text"]:
        return preferred
    if preferred and preferred in _squash(chunk["text"]):
        return preferred
    return _fallback_support_text(chunk)


def _find_ordered_headings(text: str, headings: list[str]) -> list[tuple[str, int]]:
    matches: list[tuple[str, int]] = []
    for heading in headings:
        match = re.search(re.escape(heading), text, flags=re.IGNORECASE)
        if match:
            matches.append((heading, match.start()))
    return sorted(matches, key=lambda item: item[1])


def _extract_examples(text: str, marker: str) -> list[str]:
    match = re.search(rf"{re.escape(marker)}[^.]*\.", text, flags=re.IGNORECASE)
    if not match:
        return []
    example_text = re.sub(r"^.*?include,?\s*(but are not limited to,)?", "", match.group(0), flags=re.IGNORECASE).rstrip(".")
    return [_strip_footnotes(part.strip()) for part in re.split(r",| and ", example_text) if part.strip()]


def _extract_excluded(text: str) -> list[str]:
    return [sentence for sentence in _sentences(text) if sentence.lower().startswith("does not include")]


def _extract_form_notes(text: str) -> list[str]:
    return [
        sentence
        for sentence in _sentences(text)
        if any(token in sentence.lower() for token in ["fresh", "frozen", "shelf stable", "aseptically", "exempt"])
    ][:4]


def _extract_parenthetical_examples(header: str) -> list[str]:
    examples: list[str] = []
    for group in re.findall(r"\((?:e\.g\.,|example:)?\s*([^)]+)\)", header, flags=re.IGNORECASE):
        for part in re.split(r",| or ", group):
            value = part.strip()
            if value and not value.lower().startswith(("mm/dd", "if applicable")):
                examples.append(value)
    return examples[:8]


def _extract_bullets(text: str) -> list[str]:
    first_half = text[: max(1, len(text) // 2)]
    parts = [part.strip() for part in re.split(r"\s*•\s*", first_half) if part.strip()]
    bullets: list[str] = []
    seen: set[str] = set()
    for part in parts[1:]:
        bullet = re.split(r"\s*www\.fda\.gov\s*|\nFood Traceability Rule:", part)[0].strip()
        bullet = re.sub(r"\s+", " ", bullet)
        if bullet and bullet not in seen:
            seen.add(bullet)
            bullets.append(bullet)
    return bullets


def _clean_kde_candidate(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" -")
    value = re.sub(r"\s+•.*$", "", value)
    return value.rstrip(".")


def _is_kde_like(value: str) -> bool:
    lowered = value.lower()
    if len(value) < 8:
        return False
    blocked = ["www.fda.gov", "provide to", "kdes must be linked"]
    return not any(token in lowered for token in blocked)


def _clean_header(value: Any) -> str:
    return _squash(str(value)).strip()


def _slug(value: str) -> str:
    value = _strip_footnotes(value).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def _truncate_slug(value: str, length: int) -> str:
    return value[:length].strip("_") or "unknown"


def _dedupe_field_key(tab: str, header: str, position: int) -> str:
    key = _slug(header)
    return _truncate_slug(f"{_slug(tab)}_{position:03d}_{key}", 120)


def _strip_footnotes(value: str) -> str:
    return re.sub(r"\[\d+\]", "", value).strip()


def _squash(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=\.)\s+", _squash(text)) if part.strip()]


def _first_sentence(text: str) -> str:
    return _sentences(text)[0] if _sentences(text) else _squash(text)


def _ftl_category(heading: str) -> str:
    if "cheese" in heading.lower():
        return "cheese"
    if heading in {"Finfish, including smoked finfish", "Crustaceans", "Molluscan shellfish, bivalves"}:
        return "seafood"
    if "deli salads" in heading.lower():
        return "ready-to-eat deli salads"
    if heading in {"Shell eggs", "Nut butters"}:
        return "other"
    return "produce"


def _infer_data_type(value: str) -> str:
    lowered = value.lower()
    if "date" in lowered or "mm/dd/yyyy" in lowered:
        return "date"
    if "quantity" in lowered:
        return "number"
    if "phone" in lowered:
        return "phone"
    if "zip" in lowered or "postal" in lowered:
        return "postal_code"
    return "text"


def _infer_required_status(value: str) -> RequirementStatus:
    lowered = value.lower()
    if "if applicable" in lowered or "if available" in lowered or "if needed" in lowered:
        return RequirementStatus.CONDITIONAL
    return RequirementStatus.REQUIRED


def _conditional_logic(value: str) -> str | None:
    lowered = value.lower()
    if "if applicable" in lowered:
        return "Required when applicable to the event, product, or entity context."
    if "if available" in lowered:
        return "Expected when available from the source event or trading partner."
    return None


def _sortable_validation_notes(header: str) -> list[str]:
    notes: list[str] = []
    if "Traceability Lot Code" in header:
        notes.append("Validate presence and linkage to the applicable traceability lot.")
    if "Reference Document" in header:
        notes.append("Validate that document type and number are paired.")
    if "Location Description" in header:
        notes.append("Validate that the location description contains enough detail to identify the location.")
    return notes


def _kde_evidence_examples(kde_name: str) -> list[str]:
    lowered = kde_name.lower()
    if "reference document" in lowered:
        return ["bill of lading", "invoice", "ASN", "work order", "production log"]
    if "location" in lowered:
        return ["business name", "street address", "geographic coordinates"]
    if "traceability lot code" in lowered:
        return ["TLC registry", "lot record", "case label", "ASN"]
    return []


def _cte_applies_to(cte_type: CteType) -> str:
    return {
        CteType.HARVESTING: "harvesters of raw agricultural commodities on the FTL",
        CteType.COOLING: "persons cooling raw agricultural commodities on the FTL before initial packing",
        CteType.INITIAL_PACKING: "initial packers of raw agricultural commodities on the FTL",
        CteType.FIRST_LAND_BASED_RECEIVING: "first land-based receivers of food obtained from fishing vessels",
        CteType.SHIPPING: "shippers of FTL foods",
        CteType.RECEIVING: "receivers of FTL foods",
        CteType.TRANSFORMATION: "persons transforming FTL foods",
    }.get(cte_type, "covered entities")


def _related_terms(term: str, all_terms: list[str]) -> list[str]:
    lowered = term.lower()
    related = []
    for other in all_terms:
        if other == term:
            continue
        other_lower = other.lower()
        if any(token in other_lower for token in lowered.split()[:2]):
            related.append(other)
    return related[:5]


def _actor_roles_for_cte(cte_type: CteType) -> list[str]:
    return {
        CteType.HARVESTING: ["harvester", "farm"],
        CteType.COOLING: ["cooler"],
        CteType.INITIAL_PACKING: ["initial packer"],
        CteType.FIRST_LAND_BASED_RECEIVING: ["first land-based receiver"],
        CteType.SHIPPING: ["shipper"],
        CteType.RECEIVING: ["receiver"],
        CteType.TRANSFORMATION: ["transformer", "processor"],
    }.get(cte_type, [])


def _input_relationship(cte_type: CteType) -> str | None:
    if cte_type in {CteType.RECEIVING, CteType.TRANSFORMATION}:
        return "Consumes or receives an inbound traceability lot or source event."
    return None


def _output_relationship(cte_type: CteType) -> str | None:
    if cte_type in {CteType.INITIAL_PACKING, CteType.FIRST_LAND_BASED_RECEIVING, CteType.TRANSFORMATION}:
        return "May establish or assign the traceability lot code for downstream records."
    if cte_type == CteType.SHIPPING:
        return "Passes linked KDE/TLC information to the immediate subsequent recipient."
    return None


def _plan_evidence_examples(component: str) -> list[str]:
    lowered = component.lower()
    if "record" in lowered:
        return ["record retention SOP", "system export location", "spreadsheet storage path"]
    if "food" in lowered:
        return ["covered food list", "item master mapping", "supplier product list"]
    if "lot code" in lowered:
        return ["lot code SOP", "TLC assignment procedure"]
    if "map" in lowered:
        return ["farm map", "aquaculture container map"]
    return ["traceability plan document"]


def _scenario_support_text(chunk: dict[str, Any]) -> str:
    sentences = _sentences(chunk["text"])
    for sentence in sentences:
        if "scenario" in sentence.lower():
            return sentence[:180]
    return _fallback_support_text(chunk)


def _dedupe_records(records: list[Any], id_attr: str) -> list[Any]:
    seen: set[str] = set()
    output: list[Any] = []
    for record in records:
        record_id = getattr(record, id_attr)
        if record_id in seen:
            continue
        seen.add(record_id)
        output.append(record)
    return output
