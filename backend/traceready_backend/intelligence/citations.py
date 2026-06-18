from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CitationSpanValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    chunk_id: str
    citation_anchor: str | None = None
    support_text: str | None = None
    chunk_exists: bool
    source_matches: bool
    anchor_matches: bool
    support_text_present: bool
    exact_match: bool
    normalized_match: bool
    status: str
    message: str


class RecordCitationCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection: str
    record_id: str
    citation_count: int
    valid_citation_count: int
    invalid_citation_count: int
    missing_support_text_count: int
    coverage_status: str
    validations: list[CitationSpanValidation] = Field(default_factory=list)


class CitationCoverageReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: dict[str, Any]
    by_collection: dict[str, dict[str, int]]
    records: list[RecordCitationCoverage]


def load_chunk_index(chunks_path: Path) -> dict[str, dict[str, Any]]:
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    return {str(chunk["chunk_id"]): chunk for chunk in chunks}


def validate_citation_span(citation: dict[str, Any], chunk_index: dict[str, dict[str, Any]]) -> CitationSpanValidation:
    source_id = str(citation.get("source_id") or citation.get("sourceId") or "")
    chunk_id = str(citation.get("chunk_id") or citation.get("chunkId") or "")
    citation_anchor = citation.get("citation_anchor") or citation.get("citationAnchor")
    support_text = citation.get("support_text") or citation.get("supportText")

    chunk = chunk_index.get(chunk_id)
    if not chunk:
        return CitationSpanValidation(
            source_id=source_id,
            chunk_id=chunk_id,
            citation_anchor=citation_anchor,
            support_text=support_text,
            chunk_exists=False,
            source_matches=False,
            anchor_matches=False,
            support_text_present=bool(support_text),
            exact_match=False,
            normalized_match=False,
            status="invalid",
            message="Cited chunk does not exist in canonical source chunk index.",
        )

    source_matches = str(chunk.get("source_id")) == source_id
    anchor_matches = not citation_anchor or str(chunk.get("citation_anchor")).strip() == str(citation_anchor).strip()
    support_text_present = bool(support_text and str(support_text).strip())
    exact_match = False
    normalized_match = False
    if support_text_present:
        chunk_text = str(chunk.get("text") or "")
        support = str(support_text).strip()
        exact_match = support in chunk_text
        normalized_match = _normalize_text(support) in _normalize_text(chunk_text)

    if not source_matches:
        status = "invalid"
        message = "Cited chunk exists, but source_id does not match the citation."
    elif not anchor_matches:
        status = "invalid"
        message = "Cited chunk exists, but citation_anchor does not match the canonical chunk anchor."
    elif not support_text_present:
        status = "partial"
        message = "Citation resolves to a chunk, but no support_text span was provided."
    elif exact_match:
        status = "valid"
        message = "Citation support_text appears exactly in the cited chunk."
    elif normalized_match:
        status = "valid_normalized"
        message = "Citation support_text appears in the cited chunk after whitespace normalization."
    else:
        status = "invalid"
        message = "Citation support_text was not found in the cited chunk."

    return CitationSpanValidation(
        source_id=source_id,
        chunk_id=chunk_id,
        citation_anchor=citation_anchor,
        support_text=support_text,
        chunk_exists=True,
        source_matches=source_matches,
        anchor_matches=anchor_matches,
        support_text_present=support_text_present,
        exact_match=exact_match,
        normalized_match=normalized_match,
        status=status,
        message=message,
    )


def build_citation_coverage_report(records_by_collection: dict[str, Any], chunk_index: dict[str, dict[str, Any]]) -> CitationCoverageReport:
    record_reports: list[RecordCitationCoverage] = []
    by_collection: dict[str, Counter[str]] = defaultdict(Counter)

    for collection, records in records_by_collection.items():
        iterable_records = _records_iterable(records)
        for record in iterable_records:
            record_id = _record_id(record, collection)
            citations = record.get("citations") or []
            validations = [validate_citation_span(citation, chunk_index) for citation in citations]
            valid_count = sum(1 for item in validations if item.status in {"valid", "valid_normalized"})
            invalid_count = sum(1 for item in validations if item.status == "invalid")
            missing_support_count = sum(1 for item in validations if item.status == "partial")

            if not citations:
                coverage_status = "missing"
            elif invalid_count:
                coverage_status = "invalid"
            elif missing_support_count:
                coverage_status = "partial"
            else:
                coverage_status = "complete"

            by_collection[collection][coverage_status] += 1
            record_reports.append(
                RecordCitationCoverage(
                    collection=collection,
                    record_id=record_id,
                    citation_count=len(citations),
                    valid_citation_count=valid_count,
                    invalid_citation_count=invalid_count,
                    missing_support_text_count=missing_support_count,
                    coverage_status=coverage_status,
                    validations=validations,
                )
            )

    summary_counter = Counter(record.coverage_status for record in record_reports)
    summary = {
        "records": len(record_reports),
        "complete": summary_counter["complete"],
        "partial": summary_counter["partial"],
        "missing": summary_counter["missing"],
        "invalid": summary_counter["invalid"],
        "citations": sum(record.citation_count for record in record_reports),
        "validCitations": sum(record.valid_citation_count for record in record_reports),
        "invalidCitations": sum(record.invalid_citation_count for record in record_reports),
        "missingSupportTextCitations": sum(record.missing_support_text_count for record in record_reports),
    }

    return CitationCoverageReport(
        summary=summary,
        by_collection={collection: dict(counter) for collection, counter in sorted(by_collection.items())},
        records=record_reports,
    )


def load_records_from_intelligence_output(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "samples" in data and isinstance(data["samples"], dict):
        return {collection: [record] for collection, record in data["samples"].items()}
    return data


def _records_iterable(records: Any) -> list[dict[str, Any]]:
    if isinstance(records, list):
        return [record for record in records if isinstance(record, dict)]
    if isinstance(records, dict):
        return [records]
    return []


def _record_id(record: dict[str, Any], collection: str) -> str:
    for key in [
        "term_id",
        "obligation_id",
        "ftl_item_id",
        "cte_id",
        "kde_id",
        "tlc_rule_id",
        "exemption_rule_id",
        "traceability_plan_requirement_id",
        "sortable_export_field_id",
        "scenario_benchmark_id",
        "benchmark_id",
        "id",
    ]:
        if record.get(key):
            return str(record[key])
    return f"{collection}:unknown"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
