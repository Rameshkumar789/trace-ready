from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bellwether_backend.intelligence.phase12_generalization_evaluation import (
    build_phase12_generalization_evaluation,
    write_phase12_generalization_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 12 generalization evaluation and drift-monitor artifacts.")
    parser.add_argument("--approved-rule-package-file", default="../data/regulatory/intelligence/rules/approved-rule-package-v1.json")
    parser.add_argument("--phase8-summary-file", default="../data/regulatory/intelligence/scenarios/phase8-summary.json")
    parser.add_argument("--phase10c-summary-file", default="../data/regulatory/intelligence/customer-evidence/phase10c-summary.json")
    parser.add_argument("--phase11-summary-file", default="../data/regulatory/intelligence/customer-evidence/phase11-summary.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/generalization")
    args = parser.parse_args()

    package = build_phase12_generalization_evaluation(
        approved_rule_package_file=Path(args.approved_rule_package_file),
        phase8_summary_file=Path(args.phase8_summary_file),
        phase10c_summary_file=Path(args.phase10c_summary_file),
        phase11_summary_file=Path(args.phase11_summary_file),
    )
    outputs = write_phase12_generalization_artifacts(package, Path(args.output_dir))
    print(json.dumps({"summary": package.summary, "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
