from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traceready_ingestion.intelligence.phase07_obligation_inventory import (
    build_phase7_obligation_inventory,
    write_phase7_obligation_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 7 obligation inventory and approved obligation set.")
    parser.add_argument("--phase6-review-package-file", default="../data/regulatory/intelligence/review/phase6-review-package.json")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/obligations")
    args = parser.parse_args()

    package = build_phase7_obligation_inventory(
        phase6_review_package_file=Path(args.phase6_review_package_file),
        chunks_file=Path(args.chunks_file),
    )
    outputs = write_phase7_obligation_artifacts(package, Path(args.output_dir))
    print(json.dumps({"summary": package.summary, "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
