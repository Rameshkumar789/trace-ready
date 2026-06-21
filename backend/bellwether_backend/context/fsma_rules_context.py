from __future__ import annotations

from .._compat import BaseModel


class FsmaRuleContext(BaseModel):
    title: str
    docket: str | None = None
    issued_date: str | None = None
    applicability: str
    trace_ready_priority: str
    source_role: str
    reason: str


class SourceContext(BaseModel):
    source_page: str
    source_page_current_as_of: str
    trace_ready_scope: str
    core_rule_dockets: list[str]
    core_sources_to_ingest: list[FsmaRuleContext]
    adjacent_customer_rules: list[FsmaRuleContext]
    not_mvp_rules: list[FsmaRuleContext]
    ingestion_policy: list[str]


FSMA_RULES_PAGE = "https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-rules-guidance-industry"


def fsma_rules_guidance_context() -> SourceContext:
    core_sources = [
        FsmaRuleContext(
            title="Final Rule: Requirements for Additional Traceability Records for Certain Foods",
            docket="FDA-2014-N-0053",
            issued_date="2022/11",
            applicability="direct_core",
            trace_ready_priority="must_ingest",
            source_role="binding_rule_family",
            reason="This is FSMA 204. It defines the traceability-record requirements Bellwether audits: CTEs, KDEs, TLCs, traceability plan, record maintenance, and sortable export readiness.",
        ),
        FsmaRuleContext(
            title="21 CFR Part 1 Subpart S: Additional Traceability Records for Certain Foods",
            docket="FDA-2014-N-0053",
            issued_date="current_eCFR",
            applicability="direct_core",
            trace_ready_priority="must_ingest",
            source_role="codified_legal_text",
            reason="This is the executable legal source for the rule engine. Use sections 1.1300 through 1.1465 as source-backed chunks.",
        ),
        FsmaRuleContext(
            title="Food Traceability List",
            docket="FDA-2014-N-0053",
            issued_date="current_FDA",
            applicability="direct_core",
            trace_ready_priority="must_ingest",
            source_role="product_scope_source",
            reason="Determines whether a product is on the Food Traceability List and therefore whether FSMA 204 records may be required.",
        ),
        FsmaRuleContext(
            title="Proposed Rule: Requirements for Additional Traceability Records for Certain Foods: Compliance Date Extension",
            docket="FDA-2014-N-0053",
            issued_date="2025/08",
            applicability="direct_change_monitoring",
            trace_ready_priority="track_not_executable",
            source_role="proposed_rule_or_change_signal",
            reason="Same traceability docket. Track for compliance-date and regulatory-change monitoring, but do not treat proposed text as final executable rule logic unless finalized or otherwise legally directed.",
        ),
        FsmaRuleContext(
            title="Draft Guidance: Questions and Answers About Requirements for Additional Traceability Records for Certain Foods",
            docket="FDA-2025-D-2837",
            issued_date="2026/02",
            applicability="direct_guidance",
            trace_ready_priority="ingest_as_guidance",
            source_role="interpretation_support",
            reason="Useful for practical interpretation and customer-facing explanations. It should support reviewer decisions, not override codified eCFR rule logic.",
        ),
        FsmaRuleContext(
            title="Small Entity Compliance Guide: Requirements for Additional Traceability Records for Certain Foods",
            docket="FDA-2023-D-1336",
            issued_date="2023/05",
            applicability="direct_guidance",
            trace_ready_priority="ingest_as_guidance",
            source_role="operator_translation_support",
            reason="Useful for small and mid-sized operator workflows, onboarding, explanations, and examples.",
        ),
    ]

    adjacent = [
        FsmaRuleContext(
            title="Standards for the Growing, Harvesting, Packing, and Holding of Produce for Human Consumption",
            docket="FDA-2011-N-0921",
            issued_date="2015/11",
            applicability="adjacent_customer_context",
            trace_ready_priority="defer_full_implementation",
            source_role="produce_activity_context",
            reason="Applies to many grower/packer customers and helps interpret farm, harvest, cooling, and packing context. It is not the Bellwether MVP rule engine.",
        ),
        FsmaRuleContext(
            title="Final Rule: Pre-Harvest Agricultural Water",
            docket="FDA-2021-N-0471",
            issued_date="2024/05",
            applicability="adjacent_customer_context",
            trace_ready_priority="defer_full_implementation",
            source_role="produce_safety_context",
            reason="Important for produce farms, but it concerns water safety standards rather than FSMA 204 traceability-record readiness.",
        ),
        FsmaRuleContext(
            title="Current Good Manufacturing Practice and Hazard Analysis and Risk-Based Preventive Controls for Human Food",
            docket="FDA-2011-N-0920",
            issued_date="2015/09",
            applicability="adjacent_customer_context",
            trace_ready_priority="future_expansion_candidate",
            source_role="food_safety_program_context",
            reason="Relevant for processors and manufacturers. Later useful for recall plans and supply-chain controls, but not first-scope CTE/KDE/TLC checks.",
        ),
        FsmaRuleContext(
            title="Foreign Supplier Verification Programs for Importers of Food for Humans and Animals",
            docket="FDA-2011-N-0143",
            issued_date="2015/11",
            applicability="adjacent_customer_context",
            trace_ready_priority="future_expansion_candidate",
            source_role="importer_supplier_context",
            reason="Relevant for importers and foreign supplier evidence. Later useful if Bellwether handles imported supplier records.",
        ),
        FsmaRuleContext(
            title="Sanitary Transportation of Human and Animal Food",
            docket="FDA-2013-N-0013",
            issued_date="2016/04",
            applicability="adjacent_customer_context",
            trace_ready_priority="future_expansion_candidate",
            source_role="transportation_context",
            reason="Shipment and transportation records may support evidence, but this rule is not the FSMA 204 traceability audit itself.",
        ),
        FsmaRuleContext(
            title="Amendments to Registration of Food Facilities",
            docket="FDA-2002-N-0323",
            issued_date="2016/07",
            applicability="adjacent_metadata_context",
            trace_ready_priority="metadata_only",
            source_role="entity_location_metadata",
            reason="Facility registration identifiers may help entity/location resolution but should not drive MVP traceability findings.",
        ),
        FsmaRuleContext(
            title="Record Availability Requirements: Establishment, Maintenance, and Availability of Records",
            docket="FDA-2002-N-0153",
            issued_date="2014/04",
            applicability="adjacent_records_context",
            trace_ready_priority="supporting_context",
            source_role="general_records_access_context",
            reason="Relevant to FDA record-access authority, but FSMA 204 has its own specific record and 24-hour sortable-export requirements.",
        ),
    ]

    not_mvp = [
        FsmaRuleContext(
            title="Laboratory Accreditation for Analyses of Foods",
            docket="FDA-2019-N-3325",
            issued_date="2021/12",
            applicability="not_mvp",
            trace_ready_priority="do_not_implement_now",
            source_role="lab_accreditation",
            reason="Lab accreditation is not traceability record readiness.",
        ),
        FsmaRuleContext(
            title="Mitigation Strategies to Protect Food Against Intentional Adulteration",
            docket="FDA-2013-N-1425",
            issued_date="2016/05",
            applicability="not_mvp",
            trace_ready_priority="do_not_implement_now",
            source_role="food_defense",
            reason="Food defense and intentional adulteration are outside the FSMA 204 traceability wedge.",
        ),
        FsmaRuleContext(
            title="Accredited Third-Party Certification",
            docket="FDA-2011-N-0146",
            issued_date="2015/11",
            applicability="not_mvp",
            trace_ready_priority="do_not_implement_now",
            source_role="certification_body_accreditation",
            reason="This governs certification-body accreditation, not Bellwether audit-readiness checks.",
        ),
        FsmaRuleContext(
            title="Current Good Manufacturing Practice and Hazard Analysis and Risk-Based Preventive Controls for Food for Animals",
            docket="FDA-2011-N-0922",
            issued_date="2015/09",
            applicability="not_current_scope",
            trace_ready_priority="do_not_implement_now",
            source_role="animal_food_safety",
            reason="Bellwether's current wedge is FDA-regulated human food on the Food Traceability List. Animal food is not on the current FTL.",
        ),
        FsmaRuleContext(
            title="Information Required in Prior Notice of Imported Food",
            docket="FDA-2011-N-0179",
            issued_date="2013/05",
            applicability="future_import_adjacency",
            trace_ready_priority="do_not_implement_now",
            source_role="import_notice",
            reason="Import notice workflow is adjacent only if Bellwether later expands into import compliance operations.",
        ),
        FsmaRuleContext(
            title="Criteria Used to Order Administrative Detention of Food for Human or Animal Consumption",
            docket="FDA-2011-N-0197",
            issued_date="2013/02",
            applicability="not_mvp",
            trace_ready_priority="do_not_implement_now",
            source_role="enforcement_authority",
            reason="Administrative detention is FDA enforcement authority, not customer traceability-readiness workflow.",
        ),
        FsmaRuleContext(
            title="Implementation of FSMA Amendments to the Reportable Food Registry Provisions",
            docket="FDA-2013-N-0590",
            issued_date="2014/03",
            applicability="not_mvp",
            trace_ready_priority="do_not_implement_now",
            source_role="reporting_registry",
            reason="Reportable Food Registry workflow is not part of the FSMA 204 MVP.",
        ),
    ]

    return SourceContext(
        source_page=FSMA_RULES_PAGE,
        source_page_current_as_of="2026-02-19",
        trace_ready_scope="FSMA 204 traceability readiness: covered foods, covered entities, CTEs, KDEs, TLCs, traceability plan, evidence links, and sortable export readiness.",
        core_rule_dockets=["FDA-2014-N-0053", "FDA-2025-D-2837", "FDA-2023-D-1336"],
        core_sources_to_ingest=core_sources,
        adjacent_customer_rules=adjacent,
        not_mvp_rules=not_mvp,
        ingestion_policy=[
            "Use eCFR 21 CFR Part 1 Subpart S as codified legal truth for executable rule logic.",
            "Use FDA Food Traceability List as product-scope truth.",
            "Use FDA guidance and small-entity guides as interpretation support, not as override authority.",
            "Track proposed rules and compliance-date changes as regulatory-change signals, not final executable rules unless finalized or legally directed.",
            "Keep adjacent FSMA rules as customer context until Bellwether intentionally expands beyond FSMA 204 traceability readiness.",
        ],
    )


def build_source_context(source_id: str, url: str) -> dict:
    context = fsma_rules_guidance_context()
    source_key = f"{source_id} {url}".lower()
    source_match = _find_matching_source(context, source_key)
    return {
        "sourcePage": context.source_page,
        "sourcePageCurrentAsOf": context.source_page_current_as_of,
        "traceReadyScope": context.trace_ready_scope,
        "matchedSource": source_match.model_dump() if source_match else None,
        "coreRuleDockets": context.core_rule_dockets,
        "coreSourcesToIngest": [source.model_dump() for source in context.core_sources_to_ingest],
        "adjacentCustomerRules": [source.model_dump() for source in context.adjacent_customer_rules],
        "notMvpRules": [source.model_dump() for source in context.not_mvp_rules],
        "ingestionPolicy": context.ingestion_policy,
    }


def classify_fsma_rule_entry(title: str, docket: str | None = None) -> dict | None:
    context = fsma_rules_guidance_context()
    source_key = f"{title} {docket or ''}".lower()
    if docket == "FDA-2014-N-0053" and "compliance date extension" in source_key:
        return context.core_sources_to_ingest[3].model_dump()
    match = _find_matching_source(context, source_key)
    return match.model_dump() if match else None


def _find_matching_source(context: SourceContext, source_key: str) -> FsmaRuleContext | None:
    candidates = context.core_sources_to_ingest + context.adjacent_customer_rules + context.not_mvp_rules
    source_dockets = set(_extract_dockets(source_key))
    best_candidate: FsmaRuleContext | None = None
    best_score = 0.0
    best_overlap = 0
    for candidate in candidates:
        docket = (candidate.docket or "").lower()
        title_words = _specific_title_words(candidate.title)
        overlap = sum(1 for word in title_words if word in source_key)
        title_score = overlap / max(len(title_words), 1)
        docket_matches = bool(docket and docket in source_key)

        if source_dockets and not docket_matches:
            continue

        score = title_score
        if docket_matches:
            score += 2.0
        if score > best_score or (score == best_score and overlap > best_overlap):
            best_score = score
            best_overlap = overlap
            best_candidate = candidate

    if best_candidate and (best_score >= 2.15 or best_score >= 0.45):
        return best_candidate
    if "subpart-s" in source_key or "1-subpart-s" in source_key or "1.1300" in source_key:
        return context.core_sources_to_ingest[1]
    if "food-traceability-list" in source_key:
        return context.core_sources_to_ingest[2]
    return None


def _extract_dockets(value: str) -> list[str]:
    import re

    return [match.group(0).lower() for match in re.finditer(r"fda-\d{4}-[a-z]-\d{4}", value.lower())]


def _specific_title_words(title: str) -> list[str]:
    import re

    stop_words = {
        "about",
        "additional",
        "amendments",
        "certain",
        "compliance",
        "current",
        "draft",
        "final",
        "foods",
        "guidance",
        "industry",
        "know",
        "requirements",
        "rule",
        "small",
        "traceability",
        "what",
    }
    return [
        word
        for word in re.findall(r"[a-z0-9]+", title.lower())
        if len(word) > 4 and word not in stop_words
    ]
