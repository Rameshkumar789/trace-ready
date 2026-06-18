from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traceready_backend.intelligence.phase13_release_gates import (
    build_phase13_release_gates,
    write_phase13_release_gate_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 13 release gate artifacts.")
    parser.add_argument("--approved-rule-package-file", default="../data/regulatory/intelligence/rules/approved-rule-package-v1.json")
    parser.add_argument("--source-chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--approved-subparagraph-targets-file", default="../data/regulatory/intelligence/rules/approved-subparagraph-targets-v1.json")
    parser.add_argument("--web500-records-file", default="../data/regulatory/intelligence/generalization/phase12-web500-input-records.json")
    parser.add_argument("--web500-metrics-file", default="../data/regulatory/intelligence/generalization/phase12-web500-metrics.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/generalization")
    args = parser.parse_args()

    package = build_phase13_release_gates(
        approved_rule_package_file=Path(args.approved_rule_package_file),
        source_chunks_file=Path(args.source_chunks_file),
        approved_subparagraph_targets_file=Path(args.approved_subparagraph_targets_file),
        web500_records_file=Path(args.web500_records_file),
        web500_metrics_file=Path(args.web500_metrics_file),
    )
    outputs = write_phase13_release_gate_artifacts(package, Path(args.output_dir))
    print(json.dumps({"summary": package.summary, "outputs": outputs}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
