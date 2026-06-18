from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traceready_backend.intelligence.phase08_scenario_regression import (
    build_phase8_scenario_regressions,
    write_phase8_scenario_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 8 scenario regression benchmarks and gate results.")
    parser.add_argument("--scenario-benchmarks-file", default="../data/regulatory/intelligence/drafts/scenario-benchmarks.json")
    parser.add_argument("--approved-obligation-set-file", default="../data/regulatory/intelligence/obligations/phase7-approved-obligation-set-v1.json")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--kde-candidates-file", default="../data/regulatory/intelligence/drafts/cte-kde-candidates.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/scenarios")
    parser.add_argument("--override-reason", default=None)
    args = parser.parse_args()

    package = build_phase8_scenario_regressions(
        scenario_benchmarks_file=Path(args.scenario_benchmarks_file),
        approved_obligation_set_file=Path(args.approved_obligation_set_file),
        chunks_file=Path(args.chunks_file),
        kde_candidates_file=Path(args.kde_candidates_file),
        override_reason=args.override_reason,
    )
    outputs = write_phase8_scenario_artifacts(package, Path(args.output_dir))
    print(json.dumps({"summary": package.summary, "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
