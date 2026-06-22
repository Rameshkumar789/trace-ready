#!/usr/bin/env python3
"""Offline rule-package builder (quarantine seam).

This is the ONLY contract between the (offline) regulatory-intelligence pipeline and the
runtime: it validates a rule package and emits a versioned, hashed artifact. Runtime
(bellwether_core) consumes that artifact and nothing else from the regulatory subsystem.

Today it validates + versions the existing approved package; once the legacy intelligence
pipeline is fully quarantined, this is where its output is assembled. Runtime never imports
the intelligence/ package.

Usage:
  python3 -m bellwether_core.scripts.build_rule_package \
      --source data/regulatory/intelligence/rules/approved-rule-package-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
DIST_DIR = ROOT / "data/regulatory/intelligence/rules/dist"

REQUIRED_KEYS = ("package_id", "version")


def build(source: Path, dist_dir: Path) -> dict:
    package = json.loads(source.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KEYS if not package.get(k)]
    if missing:
        raise SystemExit(f"rule package is missing required keys: {missing}")

    body = json.dumps(package, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    version = package["version"]
    package_id = package["package_id"]

    dist_dir.mkdir(parents=True, exist_ok=True)
    artifact = dist_dir / f"{package_id}-v{version}.json"
    artifact.write_text(json.dumps(package, indent=2), encoding="utf-8")

    manifest = dist_dir / "manifest.json"
    record = {
        "package_id": package_id,
        "version": version,
        "sha256": digest,
        "artifact": artifact.name,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate + version a rule package artifact.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dist", type=Path, default=DIST_DIR)
    args = parser.parse_args()
    if not args.source.exists():
        parser.error(f"source not found: {args.source}")
    record = build(args.source, args.dist)
    print(f"built {record['artifact']}  sha256={record['sha256'][:12]}…  (package {record['package_id']} v{record['version']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
