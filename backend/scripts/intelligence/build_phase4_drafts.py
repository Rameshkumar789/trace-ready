from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from typing import Any

from pydantic import BaseModel

from bellwether_backend.intelligence.phase04_deterministic_extractors import (
    extract_cte_kde_candidates,
    extract_defined_terms,
    extract_ftl_food_items,
    extract_scenario_benchmarks,
    extract_sortable_export_fields,
    extract_traceability_plan_requirements,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 4 deterministic regulatory intelligence drafts.")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--sortable-workbook", default="../data/regulatory/fda-sortable-spreadsheet-xlsx/raw/fda-sortable-spreadsheet-xlsx.xlsx")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/drafts")
    args = parser.parse_args()

    chunks_path = Path(args.chunks_file)
    workbook_path = Path(args.sortable_workbook)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    cte_definitions, kde_requirements = extract_cte_kde_candidates(chunks)
    collections: dict[str, list[BaseModel]] = {
        "ftl_food_items": extract_ftl_food_items(chunks),
        "sortable_export_fields": extract_sortable_export_fields(chunks, workbook_path),
        "cte_definitions": cte_definitions,
        "kde_requirements": kde_requirements,
        "defined_terms": extract_defined_terms(chunks),
        "traceability_plan_requirements": extract_traceability_plan_requirements(chunks),
        "scenario_benchmarks": extract_scenario_benchmarks(chunks),
    }

    json_collections = {
        collection: [record.model_dump(mode="json") for record in records]
        for collection, records in collections.items()
    }

    file_map = {
        "ftl_food_items": "ftl-food-items.json",
        "sortable_export_fields": "sortable-export-fields.json",
        "cte_definitions": "cte-definitions.json",
        "kde_requirements": "cte-kde-candidates.json",
        "defined_terms": "defined-terms.json",
        "traceability_plan_requirements": "traceability-plan-requirements.json",
        "scenario_benchmarks": "scenario-benchmarks.json",
    }

    for collection, filename in file_map.items():
        _write_json(output_dir / filename, json_collections[collection])

    combined_path = output_dir / "phase4-drafts.json"
    _write_json(combined_path, json_collections)

    summary: dict[str, Any] = {
        "outputDir": str(output_dir),
        "combinedFile": str(combined_path),
        "counts": {collection: len(records) for collection, records in json_collections.items()},
    }
    _write_json(output_dir / "phase4-summary.json", summary)
    print(json.dumps(summary, indent=2))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
