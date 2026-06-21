from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bellwether_backend.intelligence.phase06_review_workflow import (
    build_phase6_review_package,
    write_phase6_review_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 6 reviewer workflow artifacts from validated intelligence drafts.")
    parser.add_argument("--phase4-drafts-file", default="../data/regulatory/intelligence/drafts/phase4-drafts.json")
    parser.add_argument("--phase5-summary-file", default="../data/regulatory/intelligence/phase5/phase5-real-extraction-summary.json")
    parser.add_argument("--chunks-file", default="../data/regulatory/registry/source-chunks.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/review")
    args = parser.parse_args()

    package = build_phase6_review_package(
        phase4_drafts_file=Path(args.phase4_drafts_file),
        phase5_summary_file=Path(args.phase5_summary_file),
        chunks_file=Path(args.chunks_file),
    )
    outputs = write_phase6_review_artifacts(package, Path(args.output_dir))
    print(json.dumps({"summary": package.summary, "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
