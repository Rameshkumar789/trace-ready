from __future__ import annotations

import argparse
import json

from traceready_backend.api.config import load_settings
from traceready_backend.backend.db import supabase_connection
from traceready_backend.backend.repositories.supabase_tables import RegulatoryRepository
from traceready_backend.backend.services.source_artifact_integrity_service import check_source_artifact_integrity
from traceready_backend.storage.artifacts import build_object_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Check regulatory source DB/object-storage artifact integrity.")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--source-version", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    settings = load_settings()
    object_store = build_object_store(settings)
    bucket = args.bucket or settings.supabase_storage_bucket
    with supabase_connection(settings) as connection:
        report = check_source_artifact_integrity(
            repository=RegulatoryRepository(connection),
            object_store=object_store,
            default_bucket=bucket,
            source_version=args.source_version,
            limit=args.limit,
        )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    if report.status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
