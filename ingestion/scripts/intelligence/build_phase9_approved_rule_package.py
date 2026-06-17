from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traceready_ingestion.intelligence.phase09_approved_rule_package import (
    build_phase9_rule_package,
    write_phase9_rule_package_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 9 approved structured rule package.")
    parser.add_argument("--approved-obligation-set-file", default="../data/regulatory/intelligence/obligations/phase7-approved-obligation-set-v1.json")
    parser.add_argument("--scenario-summary-file", default="../data/regulatory/intelligence/scenarios/phase8-summary.json")
    parser.add_argument("--scenario-results-file", default="../data/regulatory/intelligence/scenarios/phase8-regression-results.json")
    parser.add_argument("--sources-file", default="../data/regulatory/registry/sources.json")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--previous-package-file", default=None)
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/rules")
    args = parser.parse_args()

    phase9 = build_phase9_rule_package(
        approved_obligation_set_file=Path(args.approved_obligation_set_file),
        scenario_summary_file=Path(args.scenario_summary_file),
        scenario_results_file=Path(args.scenario_results_file),
        sources_file=Path(args.sources_file),
        chunks_file=Path(args.chunks_file),
        previous_package_file=Path(args.previous_package_file) if args.previous_package_file else None,
    )
    outputs = write_phase9_rule_package_artifacts(phase9, Path(args.output_dir))
    print(json.dumps({"summary": phase9["summary"], "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
