"""LLM perception for universal workbook understanding.

Given mechanical sheet profiles (headers, sample values, fill rates) the model proposes, per
sheet, a record kind and a per-column mapping onto the canonical field registry. Every
answer is deterministically verified: unknown kinds, unknown slugs, invented headers, or
missing sheets are rejected (with one retry) before anything reaches the audit engine.
"""

from __future__ import annotations

import json
from typing import Any

from bellwether_backend.audit_engine.canonical_fields import (
    RECORD_KIND_DESCRIPTIONS,
    canonical_field_registry,
)

MAPPING_PROMPT_VERSION = "wmap-v1"

_SYSTEM_PROMPT = """You are a food-traceability data engineer mapping a customer's export \
(any ERP/WMS/traceability system, any layout) onto a canonical FSMA 204 schema.

You will receive JSON sheet profiles: sheet name, headers (with column index), row count, \
per-column fill rate and sample values.

For EVERY sheet in the input, return one object:
{
  "sheet_name": "<exactly as given>",
  "record_kind": "<one of the record kinds listed in the user message>",
  "confidence": 0.0-1.0,
  "columns": [
    {"index": <column index as given>, "header": "<exactly as given>",
     "canonical_slug": "<one of the canonical slugs, or null if no slug fits>",
     "confidence": 0.0-1.0, "why": "<short reason>"}
  ]
}

Rules:
- Respond with a JSON array only. One object per input sheet, every sheet exactly once.
- Use ONLY the provided canonical slugs and record kinds. Never invent identifiers.
- Judge record_kind from the sheet name AND the columns AND the sample values. A sheet of \
events has dates/quantities/lots per row; master data describes products/locations/partners; \
"lot assignment"/plan sheets describe procedures, not events.
- Transformation data split across two sheets: ingredients/inputs consumed -> \
cte_transformation_input; produced/output foods -> cte_transformation_output.
- Map a column to null rather than guessing a wrong slug. Prefer the most specific slug \
(e.g. a landing date column -> landing_date, not event_datetime; a destination location id \
-> destination_location_id, not location_id).
- A column holding the lot code of THIS sheet's food maps to traceability_lot_code even on \
transformation sheets (the engine derives input/output roles from the sheet kind).
- Columns that merely point at another sheet ("See X sheet") map to null.
"""


def build_mapping_user_prompt(sheet_profiles: list[dict[str, Any]]) -> str:
    registry = canonical_field_registry()
    slug_lines = [
        {"slug": field.slug, "label": field.label, "description": field.description, "example_headers": list(field.examples)}
        for field in sorted(registry.values(), key=lambda f: f.slug)
    ]
    payload = {
        "record_kinds": RECORD_KIND_DESCRIPTIONS,
        "canonical_fields": slug_lines,
        "sheets": sheet_profiles,
    }
    return (
        "Map every sheet below. Sheet profiles, allowed record kinds and allowed canonical "
        "slugs:\n" + json.dumps(payload, ensure_ascii=False, indent=1)
    )


def mapping_system_prompt() -> str:
    return _SYSTEM_PROMPT


def verify_mapping_items(items: list[dict[str, Any]], sheet_profiles: list[dict[str, Any]]) -> list[str]:
    """Deterministic verification of an LLM mapping answer. Returns error strings; [] = ok."""
    errors: list[str] = []
    registry = canonical_field_registry()
    expected: dict[str, dict[int, str]] = {
        profile["sheet_name"]: {column["index"]: column["header"] for column in profile["columns"]}
        for profile in sheet_profiles
    }
    seen: set[str] = set()
    for item in items:
        sheet_name = item.get("sheet_name")
        if sheet_name not in expected:
            errors.append(f"unknown sheet_name {sheet_name!r}")
            continue
        if sheet_name in seen:
            errors.append(f"sheet {sheet_name!r} returned more than once")
            continue
        seen.add(sheet_name)
        kind = item.get("record_kind")
        if kind not in RECORD_KIND_DESCRIPTIONS:
            errors.append(f"sheet {sheet_name!r}: unknown record_kind {kind!r}")
        confidence = item.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append(f"sheet {sheet_name!r}: confidence must be a number in [0,1]")
        columns = item.get("columns")
        if not isinstance(columns, list):
            errors.append(f"sheet {sheet_name!r}: columns must be a list")
            continue
        expected_columns = expected[sheet_name]
        for column in columns:
            index = column.get("index")
            header = column.get("header")
            if index not in expected_columns:
                errors.append(f"sheet {sheet_name!r}: unknown column index {index!r}")
                continue
            if header != expected_columns[index]:
                errors.append(
                    f"sheet {sheet_name!r} column {index}: header {header!r} does not match profiled header {expected_columns[index]!r}"
                )
            slug = column.get("canonical_slug")
            if slug is not None and slug not in registry:
                errors.append(f"sheet {sheet_name!r} column {index}: {slug!r} is not a canonical slug")
            col_confidence = column.get("confidence")
            if not isinstance(col_confidence, (int, float)) or not 0 <= float(col_confidence) <= 1:
                errors.append(f"sheet {sheet_name!r} column {index}: confidence must be in [0,1]")
    missing = set(expected) - seen
    for sheet_name in sorted(missing):
        errors.append(f"sheet {sheet_name!r} missing from the answer")
    return errors
