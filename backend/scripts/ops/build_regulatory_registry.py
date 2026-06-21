"""Build the canonical regulatory registry (sources.json + source-chunks.json) from every
normalized source under data/regulatory/.

Run:  python -m scripts.ops.build_regulatory_registry"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bellwether_backend.registry.builder import write_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Build canonical Bellwether regulatory source/chunk registry artifacts.")
    parser.add_argument("--regulatory-dir", default="../data/regulatory")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    regulatory_dir = Path(args.regulatory_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None
    result = write_registry(regulatory_dir=regulatory_dir, output_dir=output_dir)
    print(json.dumps(result["health"]["summary"], indent=2))


if __name__ == "__main__":
    main()
