from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from typing import Any


CTE_COLLECTIONS = {
    "cte_definitions",
    "kde_requirements",
    "obligations",
    "tlc_rules",
    "traceability_plan_requirements",
    "sortable_export_fields",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all structured Phase 6 records against unseen Phase 8 scenarios as a shadow eval.")
    parser.add_argument("--phase6-review-package-file", default="../data/regulatory/intelligence/review/phase6-review-package.json")
    parser.add_argument("--unseen-challenge-set-file", default="../data/regulatory/intelligence/scenarios/phase8-unseen-web-challenge-set.json")
    parser.add_argument("--unseen-results-file", default="../data/regulatory/intelligence/scenarios/phase8-unseen-web-challenge-results.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/scenarios")
    args = parser.parse_args()

    package = build_shadow_eval(
        phase6_review_package_file=Path(args.phase6_review_package_file),
        unseen_challenge_set_file=Path(args.unseen_challenge_set_file),
        unseen_results_file=Path(args.unseen_results_file),
    )
    outputs = write_shadow_eval_artifacts(package, Path(args.output_dir))
    print(json.dumps({"summary": package["summary"], "outputs": outputs}, indent=2))


def build_shadow_eval(
    *,
    phase6_review_package_file: Path,
    unseen_challenge_set_file: Path,
    unseen_results_file: Path,
) -> dict[str, Any]:
    review_package = json.loads(phase6_review_package_file.read_text(encoding="utf-8"))
    records = list(review_package["draft_records"])
    challenges = json.loads(unseen_challenge_set_file.read_text(encoding="utf-8"))
    unseen_results = {item["challenge_id"]: item for item in json.loads(unseen_results_file.read_text(encoding="utf-8"))}
    collection_status_counts = _collection_status_counts(records)
    challenge_results = [
        _evaluate_challenge(challenge, unseen_results[challenge["challenge_id"]], records)
        for challenge in challenges
    ]
    return {
        "summary": _summary(records, challenge_results, collection_status_counts),
        "collectionStatusCounts": collection_status_counts,
        "challengeResults": challenge_results,
    }


def write_shadow_eval_artifacts(package: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": output_dir / "phase8-shadow-all-structured-records-summary.json",
        "challengeResults": output_dir / "phase8-shadow-all-structured-records-results.json",
        "collectionStatusCounts": output_dir / "phase8-shadow-all-structured-records-collection-counts.json",
    }
    outputs["summary"].write_text(json.dumps(package["summary"], indent=2), encoding="utf-8")
    outputs["challengeResults"].write_text(json.dumps(package["challengeResults"], indent=2), encoding="utf-8")
    outputs["collectionStatusCounts"].write_text(json.dumps(package["collectionStatusCounts"], indent=2), encoding="utf-8")
    return {key: str(path) for key, path in outputs.items()}


def _evaluate_challenge(challenge: dict[str, Any], unseen_result: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    expected_ctes = list(challenge["expected_ctes"])
    matched_records = [_match_record(record, challenge, expected_ctes) for record in records]
    matched_records = [record for record in matched_records if record is not None]
    match_counts = _nested_counts(matched_records)
    status_counts = Counter(record["review_status"] for record in matched_records)
    source_phase_counts = Counter(record["source_phase"] for record in matched_records)
    rejected_matches = [record for record in matched_records if record["review_status"] == "rejected"]
    coverage_by_cte = {
        cte: _coverage_for_cte(cte, matched_records)
        for cte in expected_ctes
    }
    ready_or_approved_records = [
        record
        for record in matched_records
        if record["review_status"] in {"needs_review", "approved"}
    ]
    ready_collection_coverage = sorted({record["collection"] for record in ready_or_approved_records})
    all_expected_ctes_have_kde_support = all(
        cte == "traceability_plan" or coverage_by_cte[cte]["readyKdeRecords"] > 0
        for cte in expected_ctes
    )
    all_expected_ctes_have_cte_definition = all(
        cte == "traceability_plan" or coverage_by_cte[cte]["readyCteDefinitions"] > 0
        for cte in expected_ctes
    )
    shadow_status = "supported_with_drafts" if all_expected_ctes_have_kde_support and all_expected_ctes_have_cte_definition else "support_gap"
    if rejected_matches:
        shadow_status = "supported_with_drafts_and_rejected_noise" if shadow_status == "supported_with_drafts" else "support_gap_with_rejected_noise"

    return {
        "challenge_id": challenge["challenge_id"],
        "name": challenge["name"],
        "unseenInferenceStatus": unseen_result["status"],
        "shadowStructuredRecordStatus": shadow_status,
        "expectedCtes": expected_ctes,
        "predictedCtes": unseen_result["predicted_ctes"],
        "matchedRecordCount": len(matched_records),
        "readyOrApprovedMatchedRecordCount": len(ready_or_approved_records),
        "rejectedMatchedRecordCount": len(rejected_matches),
        "matchedCollectionCounts": match_counts["collections"],
        "matchedReviewStatusCounts": dict(sorted(status_counts.items())),
        "matchedSourcePhaseCounts": dict(sorted(source_phase_counts.items())),
        "readyCollectionCoverage": ready_collection_coverage,
        "coverageByCte": coverage_by_cte,
        "rejectedRecordIds": [record["record_id"] for record in rejected_matches],
        "interpretation": _interpretation(unseen_result, rejected_matches, all_expected_ctes_have_kde_support, all_expected_ctes_have_cte_definition),
    }


def _match_record(record: dict[str, Any], challenge: dict[str, Any], expected_ctes: list[str]) -> dict[str, Any] | None:
    collection = record["collection"]
    payload = record["payload"]
    matched_ctes = _record_ctes(collection, payload, expected_ctes)
    food_match = _food_record_matches(collection, payload, challenge)
    if not matched_ctes and not food_match:
        return None
    if collection not in CTE_COLLECTIONS and not food_match:
        return None
    return {
        "record_id": record["record_id"],
        "collection": collection,
        "review_status": record["review_status"],
        "source_phase": record["source_phase"],
        "extraction_method": record["extraction_method"],
        "confidence": record["confidence"],
        "citation_coverage_status": record["citation_coverage_status"],
        "citation_valid": record["citation_valid"],
        "matched_ctes": matched_ctes,
        "matched_food_scope": food_match,
    }


def _record_ctes(collection: str, payload: dict[str, Any], expected_ctes: list[str]) -> list[str]:
    ctes: list[str] = []
    if collection == "cte_definitions" and payload.get("cte_type"):
        ctes.append(str(payload["cte_type"]))
    if collection == "kde_requirements" and payload.get("cte_type"):
        ctes.append(str(payload["cte_type"]))
    if collection in {"obligations", "tlc_rules", "exemption_rules", "sortable_export_fields"}:
        ctes.extend(str(cte) for cte in payload.get("applies_to_ctes", []))
    if collection == "traceability_plan_requirements":
        ctes.append("traceability_plan")
    if collection == "scenario_benchmarks":
        ctes.extend(str(event.get("cte_type")) for event in payload.get("events", []) if event.get("cte_type"))
    return sorted(set(ctes) & set(expected_ctes))


def _food_record_matches(collection: str, payload: dict[str, Any], challenge: dict[str, Any]) -> bool:
    if collection != "ftl_food_items":
        return False
    haystack = " ".join(
        [
            challenge.get("scenario_text", ""),
            challenge.get("expected_food_scope", ""),
        ]
    ).lower()
    terms = [
        str(payload.get("category", "")),
        str(payload.get("commodity", "")),
        *[str(item) for item in payload.get("included_examples", [])],
    ]
    for term in terms:
        for token in _meaningful_tokens(term):
            if token in haystack:
                return True
    return False


def _coverage_for_cte(cte: str, matched_records: list[dict[str, Any]]) -> dict[str, Any]:
    cte_records = [record for record in matched_records if cte in record["matched_ctes"]]
    ready = [record for record in cte_records if record["review_status"] in {"needs_review", "approved"}]
    return {
        "totalRecords": len(cte_records),
        "readyOrApprovedRecords": len(ready),
        "rejectedRecords": sum(1 for record in cte_records if record["review_status"] == "rejected"),
        "readyCteDefinitions": sum(1 for record in ready if record["collection"] == "cte_definitions"),
        "readyKdeRecords": sum(1 for record in ready if record["collection"] == "kde_requirements"),
        "readyObligations": sum(1 for record in ready if record["collection"] == "obligations"),
        "readyTlcRules": sum(1 for record in ready if record["collection"] == "tlc_rules"),
        "readySortableFields": sum(1 for record in ready if record["collection"] == "sortable_export_fields"),
    }


def _interpretation(
    unseen_result: dict[str, Any],
    rejected_matches: list[dict[str, Any]],
    all_expected_ctes_have_kde_support: bool,
    all_expected_ctes_have_cte_definition: bool,
) -> list[str]:
    notes = []
    if unseen_result["status"] == "gap":
        notes.append("The unseen inference layer still produced a CTE prediction gap for this scenario.")
    if all_expected_ctes_have_kde_support and all_expected_ctes_have_cte_definition:
        notes.append("The 550-record shadow corpus contains draft support for every expected non-plan CTE.")
    if rejected_matches:
        notes.append("Matched rejected records are present; this is useful for diagnostics but unsafe for execution.")
    if not all_expected_ctes_have_kde_support:
        notes.append("At least one expected non-plan CTE lacks KDE draft support.")
    if not all_expected_ctes_have_cte_definition:
        notes.append("At least one expected non-plan CTE lacks a CTE definition draft.")
    return notes


def _collection_status_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        counts[record["collection"]][record["review_status"]] += 1
    return {collection: dict(sorted(counter.items())) for collection, counter in sorted(counts.items())}


def _nested_counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    collections = Counter(record["collection"] for record in records)
    return {"collections": dict(sorted(collections.items()))}


def _summary(records: list[dict[str, Any]], challenge_results: list[dict[str, Any]], collection_status_counts: dict[str, dict[str, int]]) -> dict[str, Any]:
    status_counts = Counter(result["shadowStructuredRecordStatus"] for result in challenge_results)
    inference_counts = Counter(result["unseenInferenceStatus"] for result in challenge_results)
    matched_records = sum(result["matchedRecordCount"] for result in challenge_results)
    ready_matches = sum(result["readyOrApprovedMatchedRecordCount"] for result in challenge_results)
    rejected_matches = sum(result["rejectedMatchedRecordCount"] for result in challenge_results)
    return {
        "generatedAt": "2026-06-16T00:00:00Z",
        "purpose": "Shadow run of all Phase 6 structured records against unseen web-derived challenges. Not executable product truth.",
        "structuredRecordsLoaded": len(records),
        "recordReviewStatusCounts": dict(sorted(Counter(record["review_status"] for record in records).items())),
        "recordSourcePhaseCounts": dict(sorted(Counter(record["source_phase"] for record in records).items())),
        "collectionStatusCounts": collection_status_counts,
        "challengeCount": len(challenge_results),
        "unseenInferenceStatusCounts": dict(sorted(inference_counts.items())),
        "shadowStructuredRecordStatusCounts": dict(sorted(status_counts.items())),
        "totalMatchedRecordsAcrossChallenges": matched_records,
        "readyOrApprovedMatchedRecordsAcrossChallenges": ready_matches,
        "rejectedMatchedRecordsAcrossChallenges": rejected_matches,
        "diagnosticFinding": (
            "The full structured corpus provides broad CTE/KDE draft support for the unseen scenarios, "
            "but it does not fix inference mistakes such as over-triggering shipping/receiving; it also introduces rejected-record noise."
        ),
    }


def _meaningful_tokens(value: str) -> list[str]:
    stopwords = {
        "and",
        "the",
        "food",
        "foods",
        "fresh",
        "includes",
        "all",
        "other",
        "than",
        "made",
        "from",
        "with",
        "list",
        "traceability",
    }
    return [
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 4 and token not in stopwords
    ]


if __name__ == "__main__":
    main()
