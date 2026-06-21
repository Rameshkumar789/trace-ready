"""Seed AI-extracted regulatory draft records into Supabase for reviewer approval.

Run:  python -m scripts.ops.seed_regulatory_draft_records"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bellwether_backend.api.config import load_settings
from bellwether_backend.backend.db import supabase_connection
from bellwether_backend.backend.repositories.supabase_tables import RegulatoryRepository
from bellwether_backend.backend.services.regulatory_draft_import_service import (
    import_phase6_draft_review_records,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local Phase 6 regulatory draft cards into DB review tables.")
    parser.add_argument(
        "--phase6-review-package-file",
        default="../data/regulatory/intelligence/review/phase6-review-package.json",
    )
    parser.add_argument("--only-ready-for-review", action="store_true")
    parser.add_argument("--exclude-rejected", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    package_file = Path(args.phase6_review_package_file).resolve()

    with supabase_connection(settings) as connection:
        result = import_phase6_draft_review_records(
            phase6_review_package_file=package_file,
            repository=RegulatoryRepository(connection, auto_commit=False),
            include_rejected=not args.exclude_rejected,
            only_ready_for_review=args.only_ready_for_review,
        )

    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
