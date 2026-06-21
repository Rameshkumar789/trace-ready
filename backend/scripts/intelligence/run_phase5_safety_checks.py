from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from typing import Any

from bellwether_backend.intelligence.phase05_ai_assisted_extraction import validate_ai_records
from bellwether_backend.intelligence.citations import load_chunk_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 5 AI-assisted extraction safety checks.")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--output-file", default="../data/regulatory/intelligence/phase5/phase5-safety-check-report.json")
    args = parser.parse_args()

    chunks_path = Path(args.chunks_file)
    chunk_index = load_chunk_index(chunks_path)

    obligation_result = validate_ai_records("obligations", _obligation_fixtures(chunk_index), chunk_index)
    tlc_result = validate_ai_records("tlc_rules", _tlc_conflict_fixtures(chunk_index), chunk_index)

    report = {
        "summary": {
            "collectionsChecked": 2,
            "acceptedRecords": len(obligation_result.accepted_records) + len(tlc_result.accepted_records),
            "rejectedRecords": len(obligation_result.rejected_records) + len(tlc_result.rejected_records),
            "conflictRecords": len(obligation_result.conflict_records) + len(tlc_result.conflict_records),
            "issueCount": len(obligation_result.issues) + len(tlc_result.issues),
        },
        "results": {
            "obligations": obligation_result.model_dump(mode="json"),
            "tlc_rules": tlc_result.model_dump(mode="json"),
        },
    }

    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "outputFile": str(output_file)}, indent=2))


def _obligation_fixtures(chunk_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    chunk = _chunk_by_section(chunk_index, "ecfr-21-cfr-1-subpart-s", "21 CFR 1.1320")
    return [
        {
            "obligation_id": "ai_obligation_supported_assign_tlc",
            "subject": "You",
            "condition": "when you do any of the following",
            "action": "assign a traceability lot code",
            "object": "traceability lot code",
            "required_output": "traceability lot code",
            "deadline": None,
            "exceptions": [],
            "applies_to_ctes": ["initial_packing", "first_land_based_receiving", "transformation"],
            "applies_to_food_scope": "foods on the Food Traceability List",
            "noncompliance_risk": "missing lot identity in downstream traceability records",
            "citations": [_citation(chunk, "You must assign a traceability lot code")],
            "metadata": _metadata(chunk, confidence="medium"),
        },
        {
            "obligation_id": "ai_obligation_unsupported_blockchain_satellite",
            "subject": "You",
            "condition": "when you do any of the following",
            "action": "launch a blockchain satellite",
            "object": "traceability lot code",
            "required_output": "traceability lot code",
            "deadline": None,
            "exceptions": [],
            "applies_to_ctes": ["initial_packing"],
            "applies_to_food_scope": "foods on the Food Traceability List",
            "noncompliance_risk": "unsupported invented claim",
            "citations": [_citation(chunk, "You must assign a traceability lot code")],
            "metadata": _metadata(chunk, confidence="medium"),
        },
    ]


def _tlc_conflict_fixtures(chunk_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    chunk = _chunk_by_section(chunk_index, "ecfr-21-cfr-1-subpart-s", "21 CFR 1.1320")
    base = {
        "rule_kind": "assignment",
        "applies_to_ctes": ["initial_packing"],
        "applies_to_food_scope": "foods on the Food Traceability List",
        "preservation_rule": None,
        "source_reference_rule": None,
        "transformation_handling": None,
        "uniqueness_rule": None,
        "lineage_rule": None,
        "required_status": "conditional",
        "evidence_examples": [],
        "unresolved_questions": [],
        "citations": [_citation(chunk, "Initially pack a raw agricultural commodity")],
        "metadata": _metadata(chunk, confidence="medium"),
    }
    return [
        {
            **base,
            "tlc_rule_id": "ai_tlc_conflict_a",
            "assignment_rule": "Initially pack a raw agricultural commodity",
        },
        {
            **base,
            "tlc_rule_id": "ai_tlc_conflict_b",
            "assignment_rule": "perform the first land-based receiving of a food",
        },
    ]


def _chunk_by_section(chunk_index: dict[str, dict[str, Any]], source_id: str, section_ref: str) -> dict[str, Any]:
    for chunk in chunk_index.values():
        if chunk.get("source_id") == source_id and chunk.get("section_ref") == section_ref:
            return chunk
    raise LookupError(f"Missing chunk for {source_id} {section_ref}")


def _citation(chunk: dict[str, Any], support_text: str) -> dict[str, Any]:
    return {
        "source_id": chunk["source_id"],
        "chunk_id": chunk["chunk_id"],
        "citation_anchor": chunk["citation_anchor"],
        "authority_rank": chunk["authority_rank"],
        "source_url": chunk["source_url"],
        "section_ref": chunk.get("section_ref"),
        "page_number": chunk.get("page_number"),
        "support_text": support_text,
    }


def _metadata(chunk: dict[str, Any], *, confidence: str) -> dict[str, Any]:
    return {
        "extraction_method": "ai_assisted",
        "confidence": confidence,
        "review_status": "draft",
        "reviewer_notes": [],
        "source_chunk_ids": [chunk["chunk_id"]],
    }


if __name__ == "__main__":
    main()
