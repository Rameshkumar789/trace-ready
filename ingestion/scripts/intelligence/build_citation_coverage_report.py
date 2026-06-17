from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traceready_ingestion.intelligence.citations import (
    build_citation_coverage_report,
    load_chunk_index,
    load_records_from_intelligence_output,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a citation coverage report for TraceReady structured intelligence records.")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--records-file", default="../data/regulatory/intelligence/schema-smoke-output.json")
    parser.add_argument("--output-file", default="../data/regulatory/intelligence/citation-coverage-report.json")
    args = parser.parse_args()

    chunk_index = load_chunk_index(Path(args.chunks_file))
    records = load_records_from_intelligence_output(Path(args.records_file))
    report = build_citation_coverage_report(records, chunk_index)

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(json.dumps({"summary": report.summary, "outputFile": str(output_path)}, indent=2))


if __name__ == "__main__":
    main()
