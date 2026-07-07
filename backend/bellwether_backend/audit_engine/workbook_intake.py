"""Universal workbook intake: AI-mapped, deterministically verified, content-cached.

No customer template is hardcoded anywhere. For any uploaded spreadsheet we:

1. profile every sheet mechanically (headers, samples, fill rates),
2. resolve a per-sheet mapping plan — record kind + column -> canonical slug — from the
   persistent cache (keyed by sheet name + headers), calling the LLM only for sheets never
   seen before, verifying every answer against the canonical registry, and falling back to
   deterministic heuristics when no key is configured,
3. synthesize derived evidence records per data row (event type from the sheet kind, best
   event date, transformation input/output lot roles, partner links from source/destination
   locations) so the downstream event graph and KDE checks work on any layout.

The parse job and the rule-execution job each parse the file independently; because the plan
is content-addressed, both resolve the identical plan with no plumbing between them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from bellwether_backend.audit_engine.canonical_fields import (
    DEFAULT_DATE_SLUG_PRIORITY,
    NON_EVENT_KINDS,
    QUANTITY_SLUG_PRIORITY,
    RECORD_KIND_TO_CTE,
    RECORD_KINDS,
    canonical_field_registry,
)

if TYPE_CHECKING:  # avoid import cycle at runtime; customer_evidence imports us lazily
    from bellwether_backend.audit_engine.customer_evidence import CustomerEvidenceRecord, SheetGrid


logger = logging.getLogger("bellwether.intake")

JUNK_PLACEHOLDER_VALUES = {"undefined", "n/a", "na", "null", "none", "-", "--", "tbd", "?"}


class StrictIntakeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class ColumnMapping(StrictIntakeModel):
    column_index: int
    source_header: str
    canonical_slug: str | None = None
    confidence: float = 0.0
    method: str = "unmapped"  # llm_field_mapping_verified | alias | fallback_slug | unmapped
    rationale: str = ""


class SheetMappingPlan(StrictIntakeModel):
    sheet_name: str
    record_kind: str
    confidence: float
    header_fingerprint: str
    generated_by: str  # llm_cached | llm_live | deterministic_fallback
    columns: list[ColumnMapping] = Field(default_factory=list)
    date_slug_priority: list[str] = Field(default_factory=list)

    def column_by_index(self) -> dict[int, ColumnMapping]:
        return {column.column_index: column for column in self.columns}

    @property
    def cte(self) -> str | None:
        return RECORD_KIND_TO_CTE.get(self.record_kind)

    @property
    def is_event_kind(self) -> bool:
        return self.record_kind in RECORD_KIND_TO_CTE


class WorkbookMappingPlan(StrictIntakeModel):
    plan_id: str
    source_file: str
    generated_by: str  # llm_cached | llm_live | deterministic_fallback | mixed
    model: str | None = None
    sheet_plans: dict[str, SheetMappingPlan] = Field(default_factory=dict)

    def sheet_kinds(self) -> dict[str, str]:
        return {name: plan.record_kind for name, plan in self.sheet_plans.items()}

    def plan_for(self, sheet_name: str) -> SheetMappingPlan | None:
        return self.sheet_plans.get(sheet_name)


# ---------------------------------------------------------------------------
# Profiling


def profile_sheet_grid(grid: "SheetGrid") -> dict[str, Any]:
    from bellwether_backend.audit_engine.customer_evidence import _cell_to_string

    columns: list[dict[str, Any]] = []
    data_rows = grid.data_rows
    for position, header in enumerate(grid.headers):
        values: list[str] = []
        filled = 0
        for _, row in data_rows:
            raw = row[position] if position < len(row) else ""
            text = _cell_to_string(raw)
            if text.strip():
                filled += 1
                if len(values) < 8 and text not in values:
                    values.append(text[:60])
        columns.append(
            {
                "index": grid.column_indexes[position],
                "header": header,
                "fill_rate": round(filled / len(data_rows), 3) if data_rows else 0.0,
                "samples": values,
            }
        )
    return {
        "sheet_name": grid.sheet_name,
        "data_row_count": len(data_rows),
        "columns": columns,
    }


def sheet_fingerprint(sheet_name: str, headers: list[str]) -> str:
    import os

    from bellwether_backend.intelligence.llm_cache import cache_key
    from bellwether_backend.intelligence.workbook_mapping_llm import MAPPING_PROMPT_VERSION

    # Tenant salt: two customers whose sheets share a name+headers must not silently share
    # a cached mapping. Default empty (single-tenant/local) keeps existing cache entries.
    tenant = os.getenv("BELLWETHER_TENANT_ID", "").strip()
    return cache_key(MAPPING_PROMPT_VERSION, tenant, sheet_name, *headers) if tenant else cache_key(MAPPING_PROMPT_VERSION, sheet_name, *headers)


# ---------------------------------------------------------------------------
# Deterministic fallback (used when no API key / verification exhausted)

_KIND_NAME_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cte_first_land_based_receiving", ("first land", "landing", "land based rec")),
    ("cte_transformation_input", ("ingredient", "input", "consumed", "components")),
    ("cte_transformation_output", ("produced", "output", "transformation kdes produced", "finished")),
    ("cte_shipping", ("shipping", "ship ", "shipment", "dispatch", "outbound")),
    ("cte_receiving", ("receiving", "received", "receipt", "inbound")),
    ("cte_harvesting", ("harvest",)),
    ("cte_cooling", ("cooling", "cooler")),
    ("cte_initial_packing", ("packing", "packed", "pack ")),
    ("master_products", ("product master", "product list", "item master", "sku")),
    ("master_locations", ("location master", "locations", "facilities", "sites")),
    ("master_partners", ("partner", "supplier master", "customer master", "vendors")),
    ("master_business", ("business master", "business profile", "company master", "entities")),
    ("traceability_plan", ("traceability plan", "trace plan")),
    ("lot_assignment", ("lot assignment", "lot code assignment", "tlc assignment")),
    ("exemption_claims", ("exemption",)),
    ("source_documents", ("source document", "evidence", "documents")),
    ("kde_reference", ("kde",)),
)


def heuristic_record_kind(sheet_name: str, headers: list[str]) -> tuple[str, float]:
    lowered = f" {sheet_name.lower()} "
    for kind, tokens in _KIND_NAME_HINTS:
        if any(token in lowered for token in tokens):
            # transformation sheets often say "Transformation KDEs Ingredients" - both
            # "transformation" and "ingredient" style tokens hit; the hint order encodes
            # specificity so the first match wins.
            return kind, 0.6
    from bellwether_backend.audit_engine.customer_evidence import _suggest_field_key

    alias_hits = 0
    event_hits = 0
    event_keys = {
        "event_type",
        "event_datetime",
        "date_you_shipped_the_food",
        "received_date",
        "traceability_lot_code",
        "quantity",
    }
    for header in headers:
        field_key, confidence, _ = _suggest_field_key(header)
        if confidence >= 0.9:
            alias_hits += 1
            if field_key in event_keys:
                event_hits += 1
    if alias_hits == 0:
        return "not_traceability", 0.35
    if event_hits >= 2:
        return "kde_reference", 0.4  # event-like but unclassifiable without perception
    return "kde_reference", 0.4


def fallback_sheet_plan(profile: dict[str, Any]) -> SheetMappingPlan:
    from bellwether_backend.audit_engine.canonical_fields import registry_alias_map
    from bellwether_backend.audit_engine.customer_evidence import _header_key, _suggest_field_key

    headers = [column["header"] for column in profile["columns"]]
    kind, kind_confidence = heuristic_record_kind(profile["sheet_name"], headers)
    aliases = registry_alias_map()
    columns: list[ColumnMapping] = []
    for column in profile["columns"]:
        field_key, confidence, method = _suggest_field_key(column["header"])
        mapped = confidence >= 0.9 and field_key in canonical_field_registry()
        if not mapped:
            registry_slug = aliases.get(_header_key(column["header"]))
            if registry_slug:
                field_key, confidence, mapped = registry_slug, 0.85, True
        columns.append(
            ColumnMapping(
                column_index=column["index"],
                source_header=column["header"],
                canonical_slug=field_key if mapped else None,
                confidence=confidence if mapped else 0.0,
                method="alias" if mapped else "unmapped",
                rationale="header alias / registry example match" if mapped else "no alias match; needs perception or review",
            )
        )
    return SheetMappingPlan(
        sheet_name=profile["sheet_name"],
        record_kind=kind,
        confidence=kind_confidence,
        header_fingerprint=sheet_fingerprint(profile["sheet_name"], headers),
        generated_by="deterministic_fallback",
        columns=columns,
        date_slug_priority=_date_priority_for(kind, {c.canonical_slug for c in columns if c.canonical_slug}),
    )


def _date_priority_for(record_kind: str, mapped_slugs: set[str]) -> list[str]:
    kind_first = {
        "cte_shipping": ("date_you_shipped_the_food",),
        "cte_receiving": ("received_date",),
        "cte_first_land_based_receiving": ("landing_date", "received_date"),
        "cte_transformation_input": ("transformation_date",),
        "cte_transformation_output": ("transformation_date", "received_date"),
        "cte_harvesting": ("harvest_date",),
        "cte_cooling": ("cooling_date",),
        "cte_initial_packing": ("packing_date",),
    }.get(record_kind, ())
    ordered = [*kind_first, *DEFAULT_DATE_SLUG_PRIORITY]
    seen: set[str] = set()
    priority: list[str] = []
    for slug in ordered:
        if slug in mapped_slugs and slug not in seen:
            seen.add(slug)
            priority.append(slug)
    return priority


# ---------------------------------------------------------------------------
# Plan resolution


def resolve_workbook_mapping_plan(input_file, *, cache=None, client=None) -> WorkbookMappingPlan:
    """Resolve the mapping plan for a workbook. Content-addressed and idempotent."""
    from bellwether_backend.audit_engine.customer_evidence import read_sheet_grids
    from bellwether_backend.intelligence.llm_cache import LLMCache, cache_key
    from bellwether_backend.intelligence.llm_perception import run_cached_perception
    from bellwether_backend.intelligence.workbook_mapping_llm import (
        build_mapping_user_prompt,
        mapping_system_prompt,
        verify_mapping_items,
    )

    cache = cache or LLMCache()
    grids = read_sheet_grids(input_file)
    profiles = [profile_sheet_grid(grid) for grid in grids]
    fingerprints = {profile["sheet_name"]: sheet_fingerprint(profile["sheet_name"], [c["header"] for c in profile["columns"]]) for profile in profiles}

    sheet_plans: dict[str, SheetMappingPlan] = {}
    missing_profiles: list[dict[str, Any]] = []
    for profile in profiles:
        cached_items = cache.get("workbook_mapping", fingerprints[profile["sheet_name"]])
        if cached_items:
            plan = _plan_from_item(cached_items[0], profile, generated_by="llm_cached")
            if plan is not None:
                sheet_plans[profile["sheet_name"]] = plan
                continue
            cache.delete("workbook_mapping", fingerprints[profile["sheet_name"]])
        missing_profiles.append(profile)

    model_used: str | None = None
    overall_methods: set[str] = {plan.generated_by for plan in sheet_plans.values()}
    # Batch wide workbooks: mapping answers for many sheets can overflow the output-token
    # budget in one call; chunked calls degrade (at worst) per chunk, not wholesale.
    SHEETS_PER_CALL = 6
    for start in range(0, len(missing_profiles), SHEETS_PER_CALL):
        chunk = missing_profiles[start : start + SHEETS_PER_CALL]
        call_key = cache_key("wmap-call-v1", *(fingerprints[p["sheet_name"]] for p in chunk))
        result = run_cached_perception(
            namespace="workbook_mapping_call",
            cache_key=call_key,
            system=mapping_system_prompt(),
            user_prompt=build_mapping_user_prompt(chunk),
            verify=lambda items, _chunk=chunk: verify_mapping_items(items, _chunk),
            fallback=lambda: [],
            cache=cache,
            client=client,
        )
        model_used = result.model or model_used
        if result.items:
            by_sheet = {item.get("sheet_name"): item for item in result.items}
            for profile in chunk:
                item = by_sheet.get(profile["sheet_name"])
                plan = _plan_from_item(item, profile, generated_by=result.method) if item else None
                if plan is None:
                    plan = fallback_sheet_plan(profile)
                else:
                    cache.put(
                        "workbook_mapping",
                        fingerprints[profile["sheet_name"]],
                        [item],
                        model=result.model,
                        method=result.method,
                    )
                sheet_plans[profile["sheet_name"]] = plan
                overall_methods.add(plan.generated_by)
        else:
            for profile in chunk:
                plan = fallback_sheet_plan(profile)
                sheet_plans[profile["sheet_name"]] = plan
                overall_methods.add(plan.generated_by)

    generated_by = overall_methods.pop() if len(overall_methods) == 1 else "mixed"
    plan_id = cache_key("wmap-plan-v1", *(fingerprints[name] for name in sorted(sheet_plans)))
    return WorkbookMappingPlan(
        plan_id=f"wmap-{plan_id[:16]}",
        source_file=str(getattr(input_file, "name", input_file)),
        generated_by=generated_by or "deterministic_fallback",
        model=model_used,
        sheet_plans=sheet_plans,
    )


def _plan_from_item(item: dict[str, Any] | None, profile: dict[str, Any], *, generated_by: str) -> SheetMappingPlan | None:
    """Convert one verified LLM sheet item into a SheetMappingPlan. None if malformed."""
    if not item or item.get("record_kind") not in RECORD_KINDS:
        return None
    registry = canonical_field_registry()
    profiled = {column["index"]: column["header"] for column in profile["columns"]}
    columns: list[ColumnMapping] = []
    seen_indexes: set[int] = set()
    for column in item.get("columns", []):
        index = column.get("index")
        if index not in profiled or index in seen_indexes:
            continue
        seen_indexes.add(index)
        slug = column.get("canonical_slug")
        if slug is not None and slug not in registry:
            slug = None
        confidence = float(column.get("confidence") or 0.0)
        columns.append(
            ColumnMapping(
                column_index=index,
                source_header=profiled[index],
                canonical_slug=slug,
                confidence=max(0.0, min(confidence, 1.0)),
                method="llm_field_mapping_verified" if slug else "unmapped",
                rationale=str(column.get("why") or "")[:240],
            )
        )
    for index, header in profiled.items():
        if index not in seen_indexes:
            columns.append(
                ColumnMapping(column_index=index, source_header=header, canonical_slug=None, confidence=0.0, method="unmapped", rationale="not mapped by perception")
            )
    columns.sort(key=lambda column: column.column_index)
    mapped_slugs = {column.canonical_slug for column in columns if column.canonical_slug}
    kind = item["record_kind"]
    return SheetMappingPlan(
        sheet_name=profile["sheet_name"],
        record_kind=kind,
        confidence=max(0.0, min(float(item.get("confidence") or 0.0), 1.0)),
        header_fingerprint=sheet_fingerprint(profile["sheet_name"], [column["header"] for column in profile["columns"]]),
        generated_by=generated_by,
        columns=columns,
        date_slug_priority=_date_priority_for(kind, mapped_slugs),
    )


# ---------------------------------------------------------------------------
# Row-level synthesis


def is_junk_placeholder_row(values: list[Any]) -> bool:
    from bellwether_backend.audit_engine.customer_evidence import _cell_to_string

    non_empty = [_cell_to_string(value).strip().lower() for value in values]
    non_empty = [value for value in non_empty if value]
    if not non_empty:
        return True
    return all(value in JUNK_PLACEHOLDER_VALUES for value in non_empty)


def derived_records_for_row(
    sheet_plan: SheetMappingPlan | None,
    row_records: list["CustomerEvidenceRecord"],
) -> list["CustomerEvidenceRecord"]:
    """Synthesize derived evidence records for one data row (generic, layout-driven)."""
    if sheet_plan is None or not row_records or not sheet_plan.is_event_kind:
        return []

    facts: dict[str, "CustomerEvidenceRecord"] = {}
    for record in row_records:
        facts.setdefault(record.field_key, record)
    anchor = row_records[0]
    derived: list["CustomerEvidenceRecord"] = []

    def emit(field_key: str, value: str, source: "CustomerEvidenceRecord", method: str) -> None:
        derived.append(_derived_record(source=source, anchor=anchor, field_key=field_key, value=value, method=method, confidence=max(sheet_plan.confidence, 0.7)))

    # 1. event_type from the sheet kind, only when the row carries no structured signal of
    #    its own (protects workbooks that already have event_type/event_id columns).
    if "event_type" not in facts and "event_id" not in facts:
        emit("event_type", RECORD_KIND_TO_CTE[sheet_plan.record_kind], anchor, "derived_sheet_kind")

    # 2. best event date (plan priority first; any known date slug as the safety net so a
    #    thin fallback mapping never strands a dated row without an event date)
    if "event_datetime" not in facts:
        for slug in [*sheet_plan.date_slug_priority, *DEFAULT_DATE_SLUG_PRIORITY]:
            if slug in facts and slug != "event_datetime":
                emit("event_datetime", facts[slug].normalized_value, facts[slug], "derived_best_date")
                break

    # 3. best quantity
    if "quantity" not in facts:
        for slug in QUANTITY_SLUG_PRIORITY:
            if slug in facts and slug != "quantity":
                emit("quantity", facts[slug].normalized_value, facts[slug], "derived_best_quantity")
                break

    # 4. transformation lot roles
    if sheet_plan.record_kind == "cte_transformation_input":
        emit("transformation_role", "input", anchor, "derived_sheet_kind")
        if "traceability_lot_code" in facts and "source_lot_or_tlc" not in facts:
            emit("source_lot_or_tlc", facts["traceability_lot_code"].normalized_value, facts["traceability_lot_code"], "derived_lot_role")
    elif sheet_plan.record_kind == "cte_transformation_output":
        emit("transformation_role", "output", anchor, "derived_sheet_kind")
        if "traceability_lot_code" in facts and "output_lot_or_tlc" not in facts:
            emit("output_lot_or_tlc", facts["traceability_lot_code"].normalized_value, facts["traceability_lot_code"], "derived_lot_role")

    # 5. partner links from source/destination locations (direction depends on the CTE)
    if sheet_plan.record_kind == "cte_shipping":
        if "destination_location_id" in facts and "to_partner_id" not in facts:
            emit("to_partner_id", facts["destination_location_id"].normalized_value, facts["destination_location_id"], "derived_location_partner")
        if "source_location_id" in facts and "actor_location_id" not in facts and "location_id" not in facts:
            emit("actor_location_id", facts["source_location_id"].normalized_value, facts["source_location_id"], "derived_location_partner")
    elif sheet_plan.record_kind == "cte_receiving":
        if "source_location_id" in facts and "from_partner_id" not in facts:
            emit("from_partner_id", facts["source_location_id"].normalized_value, facts["source_location_id"], "derived_location_partner")
        if "destination_location_id" in facts and "actor_location_id" not in facts and "location_id" not in facts:
            emit("actor_location_id", facts["destination_location_id"].normalized_value, facts["destination_location_id"], "derived_location_partner")

    return derived


def _derived_record(*, source, anchor, field_key: str, value: str, method: str, confidence: float):
    from bellwether_backend.audit_engine.customer_evidence import (
        CustomerEvidenceRecord,
        EvidenceSourcePointer,
        _detect_field_type,
        _normalize_value,
        _slug,
    )

    normalized = _normalize_value(value, field_key=field_key)
    evidence_id = f"{anchor.evidence_id}-d-{_slug(field_key)}"
    pointer = EvidenceSourcePointer(
        file_name=source.source_pointer.file_name,
        sheet_name=source.source_pointer.sheet_name,
        row_number=source.source_pointer.row_number,
        column_name=source.source_pointer.column_name,
        column_index=source.source_pointer.column_index,
        cell=source.source_pointer.cell,
    )
    return CustomerEvidenceRecord(
        evidence_id=evidence_id,
        uploaded_file=anchor.uploaded_file,
        sheet_name=anchor.sheet_name,
        row_number=anchor.row_number,
        column_name=f"__derived__{field_key}",
        column_index=source.column_index,
        cell=source.cell,
        raw_value=value,
        normalized_value=normalized,
        field_key=field_key,
        field_type=_detect_field_type(field_key, normalized),
        extraction_method=method,
        confidence=confidence,
        source_pointer=pointer,
    )


def event_gated_kinds() -> frozenset[str]:
    """Sheet kinds whose standalone rows must never mint events.

    Transformation *input* (ingredient) rows are gated too: they are facts about a
    transformation, not events of their own. Minting them as events fabricates KDE gaps
    (an ingredient row graded for output-lot/date KDEs it cannot carry) and double-counts
    the transformation CTE. Their lots still flow into lineage checks via row facts.
    """
    return frozenset(kind for kind in NON_EVENT_KINDS if kind != "kde_reference") | {"cte_transformation_input"}
