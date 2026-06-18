"""Seed the approved rule package into public.approved_rule_packages -- the package the
runtime audit engine loads from Supabase at request time.

Run:  python -m scripts.ops.seed_approved_rule_package"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from traceready_backend.api.config import load_settings
from traceready_backend.backend.db import supabase_connection
from traceready_backend.backend.repositories.supabase_tables import stable_row_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed an approved rule package JSON into Supabase package tables.")
    parser.add_argument(
        "--package-file",
        default="../data/regulatory/intelligence/rules/approved-rule-package-v1.json",
        help="Approved immutable rule package JSON file.",
    )
    args = parser.parse_args()

    package_file = Path(args.package_file).resolve()
    package = json.loads(package_file.read_text(encoding="utf-8"))
    package_id = str(package["package_id"])
    version = int(package["version"])
    approval = package.get("approval") or {}
    records = package.get("records") or {}
    package_hash = package.get("package_hash") or _stable_hash(package)
    db_package_id = stable_row_id("pkg", package_id, version)

    settings = load_settings()
    with supabase_connection(settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into public.approved_rule_packages (
                  id,
                  package_id,
                  version,
                  status,
                  immutable,
                  package_hash,
                  generated_at,
                  approved_at,
                  approved_by,
                  approval_role,
                  approval_reason,
                  scenario_gate_status,
                  source_versions,
                  rollback,
                  metadata_json
                )
                values (
                  %(id)s,
                  %(package_id)s,
                  %(version)s,
                  %(status)s,
                  %(immutable)s,
                  %(package_hash)s,
                  %(generated_at)s,
                  %(approved_at)s,
                  %(approved_by)s,
                  %(approval_role)s,
                  %(approval_reason)s,
                  %(scenario_gate_status)s,
                  %(source_versions)s,
                  %(rollback)s,
                  %(metadata_json)s
                )
                on conflict (package_id, version) do update set
                  status = excluded.status,
                  immutable = excluded.immutable,
                  package_hash = excluded.package_hash,
                  generated_at = excluded.generated_at,
                  approved_at = excluded.approved_at,
                  approved_by = excluded.approved_by,
                  approval_role = excluded.approval_role,
                  approval_reason = excluded.approval_reason,
                  scenario_gate_status = excluded.scenario_gate_status,
                  source_versions = excluded.source_versions,
                  rollback = excluded.rollback,
                  metadata_json = excluded.metadata_json
                returning id
                """,
                {
                    "id": db_package_id,
                    "package_id": package_id,
                    "version": version,
                    "status": package.get("status") or "approved",
                    "immutable": bool(package.get("immutable", True)),
                    "package_hash": package_hash,
                    "generated_at": package.get("generated_at"),
                    "approved_at": approval.get("approved_at") or package.get("generated_at"),
                    "approved_by": approval.get("approved_by") or "local-package-seed",
                    "approval_role": approval.get("approval_role") or "ops_seed",
                    "approval_reason": approval.get("approval_reason") or "Seeded from approved package JSON.",
                    "scenario_gate_status": (package.get("scenario_regression_gate") or {}).get("status"),
                    "source_versions": json.dumps(package.get("source_versions") or []),
                    "rollback": json.dumps(package.get("rollback") or {}),
                    "metadata_json": json.dumps(
                        {
                            "recordCounts": package.get("record_counts") or {},
                            "approvedRecordIds": package.get("approved_record_ids") or {},
                            "scenarioRegressionGate": package.get("scenario_regression_gate") or {},
                            "seededFrom": str(package_file),
                        },
                        sort_keys=True,
                    ),
                },
            )
            approved_rule_package_id = cursor.fetchone()["id"]
            record_count = 0
            for collection, collection_records in records.items():
                if not isinstance(collection_records, list):
                    continue
                for index, payload in enumerate(collection_records):
                    if not isinstance(payload, dict):
                        continue
                    record_id = _record_id(collection, payload, index)
                    record_version = _record_version(payload, version)
                    source_chunk_ids = _source_chunk_ids(payload)
                    cursor.execute(
                        """
                        insert into public.approved_rule_package_records (
                          id,
                          approved_rule_package_id,
                          collection,
                          record_id,
                          record_version,
                          approved_regulatory_record_id,
                          payload,
                          source_chunk_ids,
                          record_hash
                        )
                        values (
                          %(id)s,
                          %(approved_rule_package_id)s,
                          %(collection)s,
                          %(record_id)s,
                          %(record_version)s,
                          %(approved_regulatory_record_id)s,
                          %(payload)s,
                          %(source_chunk_ids)s,
                          %(record_hash)s
                        )
                        on conflict (approved_rule_package_id, collection, record_id, record_version)
                        do update set
                          payload = excluded.payload,
                          source_chunk_ids = excluded.source_chunk_ids,
                          record_hash = excluded.record_hash
                        """,
                        {
                            "id": stable_row_id("pkgrec", approved_rule_package_id, collection, record_id, record_version),
                            "approved_rule_package_id": approved_rule_package_id,
                            "collection": collection,
                            "record_id": record_id,
                            "record_version": record_version,
                            "approved_regulatory_record_id": None,
                            "payload": json.dumps(payload, sort_keys=True),
                            "source_chunk_ids": json.dumps(source_chunk_ids),
                            "record_hash": _stable_hash(payload),
                        },
                    )
                    record_count += 1

    print(
        json.dumps(
            {
                "status": "ok",
                "package_id": package_id,
                "version": version,
                "approved_rule_package_id": approved_rule_package_id,
                "package_hash": package_hash,
                "record_count": record_count,
            },
            indent=2,
            sort_keys=True,
        )
    )


def _record_id(collection: str, payload: dict[str, Any], index: int) -> str:
    if collection == "obligations" and payload.get("obligation_id"):
        return str(payload["obligation_id"])
    for key in ("id", "record_id", "rule_id", "card_id", "kde_requirement_id"):
        if payload.get(key):
            return str(payload[key])
    return stable_row_id("record", collection, index)


def _record_version(payload: dict[str, Any], default_version: int) -> int:
    raw_version = payload.get("version") or payload.get("record_version") or default_version
    try:
        return int(raw_version)
    except (TypeError, ValueError):
        return default_version


def _source_chunk_ids(payload: dict[str, Any]) -> list[str]:
    metadata = payload.get("metadata") or {}
    source_chunk_ids = metadata.get("source_chunk_ids")
    if isinstance(source_chunk_ids, list):
        return [str(chunk_id) for chunk_id in source_chunk_ids]
    citations = payload.get("citations") or []
    if not isinstance(citations, list):
        return []
    chunk_ids = []
    for citation in citations:
        if isinstance(citation, dict) and citation.get("chunk_id"):
            chunk_ids.append(str(citation["chunk_id"]))
    return chunk_ids


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


if __name__ == "__main__":
    main()
