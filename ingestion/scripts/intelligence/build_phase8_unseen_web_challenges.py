from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traceready_ingestion.intelligence.phase08_unseen_web_challenges import (
    build_unseen_web_challenge_package,
    write_unseen_web_challenge_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 8 unseen web-derived challenge scenarios.")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/scenarios")
    args = parser.parse_args()

    package = build_unseen_web_challenge_package()
    outputs = write_unseen_web_challenge_artifacts(package, Path(args.output_dir))
    print(json.dumps({"summary": package.summary, "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
