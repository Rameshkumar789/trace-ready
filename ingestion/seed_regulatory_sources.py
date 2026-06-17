from __future__ import annotations

import argparse
from pathlib import Path

from traceready_backend.api.config import load_settings
from traceready_backend.backend.db import supabase_connection
from traceready_backend.backend.repositories.supabase_tables import RegulatoryRepository
from traceready_backend.backend.services.regulatory_seed_import_service import import_regulatory_registry_seed
from traceready_backend.storage.artifacts import build_object_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed regulatory source registry artifacts into DB/object storage.")
    parser.add_argument("--regulatory-dir", default="../data/regulatory")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--source-version", type=int, default=1)
    args = parser.parse_args()

    settings = load_settings()
    regulatory_dir = Path(args.regulatory_dir).resolve()
    object_store = build_object_store(settings)
    bucket = args.bucket or settings.supabase_storage_bucket
    with supabase_connection(settings) as connection:
        result = import_regulatory_registry_seed(
            regulatory_dir=regulatory_dir,
            object_store=object_store,
            repository=RegulatoryRepository(connection, auto_commit=False),
            bucket=bucket,
            source_version=args.source_version,
        )
    print(
        {
            "source_count": result.source_count,
            "chunk_count": result.chunk_count,
            "raw_artifact_count": result.raw_artifact_count,
            "normalized_artifact_count": result.normalized_artifact_count,
            "chunk_package_count": result.chunk_package_count,
            "skipped_sources": result.skipped_sources,
        }
    )


if __name__ == "__main__":
    main()
