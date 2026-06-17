from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


GENERATED_AT = "2026-06-16T00:00:00Z"
RULE_PACKAGE_ID = "approved-rule-package-v1"


class RulePackageSourceVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    url: str
    authority_rank: str
    retrieved_at: str
    raw_hash: str | None = None
    chunks_count: int | None = None
    cited_chunk_ids: list[str] = Field(default_factory=list)
    cited_chunk_hashes: dict[str, str] = Field(default_factory=dict)


class RulePackageScenarioGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_summary_file: str
    source_results_file: str
    status: str
    can_publish_rule_changes: bool
    benchmark_count: int
    pass_count: int
    fail_count: int
    reviewer_override_count: int
    result_hash: str
    results: list[dict[str, Any]]


class RulePackageApprovalMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_at: str
    approved_by: str
    approval_role: str
    approval_reason: str
    source_approved_obligation_package: str
    source_approved_obligation_package_version: int


class ApprovedStructuredRulePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: str
    version: int
    status: str
    immutable: bool
    generated_at: str
    approval: RulePackageApprovalMetadata
    source_versions: list[RulePackageSourceVersion]
    scenario_regression_gate: RulePackageScenarioGate
    record_counts: dict[str, int]
    approved_record_ids: dict[str, list[str]]
    records: dict[str, list[dict[str, Any]]]
    rollback: dict[str, Any]
    package_hash: str

    @model_validator(mode="after")
    def _approved_package_requires_green_gate(self) -> "ApprovedStructuredRulePackage":
        if self.status == "approved" and not self.scenario_regression_gate.can_publish_rule_changes:
            raise ValueError("approved rule package requires passing scenario regression gate")
        if self.status == "approved" and not self.immutable:
            raise ValueError("approved rule package must be immutable")
        return self


class RulePackageDiff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_package_id: str | None
    to_package_id: str
    from_version: int | None
    to_version: int
    status: str
    added_records: dict[str, list[str]]
    removed_records: dict[str, list[str]]
    changed_records: dict[str, list[str]]
    unchanged_records: dict[str, list[str]]
    source_version_changes: dict[str, list[str]]
    scenario_gate_change: dict[str, Any]
    rollback_safe: bool


class RulePackageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_package_id: str
    active_version: int
    active_package_hash: str
    generated_at: str
    package_files: list[str]
    rollback_pin_file: str
    latest_diff_file: str
    available_versions: list[dict[str, Any]]


def build_phase9_rule_package(
    *,
    approved_obligation_set_file: Path,
    scenario_summary_file: Path,
    scenario_results_file: Path,
    sources_file: Path,
    chunks_file: Path,
    previous_package_file: Path | None = None,
) -> dict[str, Any]:
    approved_obligation_set = json.loads(approved_obligation_set_file.read_text(encoding="utf-8"))
    scenario_summary = json.loads(scenario_summary_file.read_text(encoding="utf-8"))
    scenario_results = json.loads(scenario_results_file.read_text(encoding="utf-8"))
    sources = json.loads(sources_file.read_text(encoding="utf-8"))
    chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
    previous_package = _load_optional_json(previous_package_file)

    package = _approved_rule_package(
        approved_obligation_set=approved_obligation_set,
        approved_obligation_set_file=approved_obligation_set_file,
        scenario_summary=scenario_summary,
        scenario_summary_file=scenario_summary_file,
        scenario_results=scenario_results,
        scenario_results_file=scenario_results_file,
        sources=sources,
        chunks=chunks,
        previous_package=previous_package,
    )
    diff = diff_rule_packages(previous_package, package.model_dump(mode="json"))
    rollback_pin = _rollback_pin(package, diff)
    manifest = RulePackageManifest(
        active_package_id=package.package_id,
        active_version=package.version,
        active_package_hash=package.package_hash,
        generated_at=GENERATED_AT,
        package_files=[f"{package.package_id}.json"],
        rollback_pin_file="active-rule-package-pin.json",
        latest_diff_file="approved-rule-package-v1-diff.json",
        available_versions=[
            {
                "package_id": package.package_id,
                "version": package.version,
                "status": package.status,
                "package_hash": package.package_hash,
                "scenario_gate_status": package.scenario_regression_gate.status,
                "record_counts": package.record_counts,
            }
        ],
    )
    summary = _summary(package, diff)
    return {
        "summary": summary,
        "package": package,
        "diff": diff,
        "rollback_pin": rollback_pin,
        "manifest": manifest,
    }


def write_phase9_rule_package_artifacts(phase9: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    package: ApprovedStructuredRulePackage = phase9["package"]
    outputs = {
        "summary": output_dir / "phase9-summary.json",
        "package": output_dir / f"{package.package_id}.json",
        "diff": output_dir / "approved-rule-package-v1-diff.json",
        "rollbackPin": output_dir / "active-rule-package-pin.json",
        "manifest": output_dir / "approved-rule-package-manifest.json",
    }
    _write_json(outputs["summary"], phase9["summary"])
    _write_json(outputs["package"], package.model_dump(mode="json"))
    _write_json(outputs["diff"], phase9["diff"].model_dump(mode="json"))
    _write_json(outputs["rollbackPin"], phase9["rollback_pin"])
    _write_json(outputs["manifest"], phase9["manifest"].model_dump(mode="json"))
    return {key: str(path) for key, path in outputs.items()}


def diff_rule_packages(previous_package: dict[str, Any] | None, current_package: dict[str, Any]) -> RulePackageDiff:
    current_records = _record_hashes_by_collection(current_package.get("records", {}))
    previous_records = _record_hashes_by_collection(previous_package.get("records", {}) if previous_package else {})
    collections = sorted(set(current_records) | set(previous_records))
    added: dict[str, list[str]] = {}
    removed: dict[str, list[str]] = {}
    changed: dict[str, list[str]] = {}
    unchanged: dict[str, list[str]] = {}
    for collection in collections:
        current_ids = set(current_records.get(collection, {}))
        previous_ids = set(previous_records.get(collection, {}))
        added[collection] = sorted(current_ids - previous_ids)
        removed[collection] = sorted(previous_ids - current_ids)
        common = current_ids & previous_ids
        changed[collection] = sorted(
            record_id
            for record_id in common
            if current_records[collection][record_id] != previous_records[collection][record_id]
        )
        unchanged[collection] = sorted(
            record_id
            for record_id in common
            if current_records[collection][record_id] == previous_records[collection][record_id]
        )

    source_changes = _source_version_changes(previous_package, current_package)
    scenario_gate_change = _scenario_gate_change(previous_package, current_package)
    has_changes = any(added.values()) or any(removed.values()) or any(changed.values()) or any(source_changes.values()) or bool(scenario_gate_change)
    return RulePackageDiff(
        from_package_id=previous_package.get("package_id") if previous_package else None,
        to_package_id=str(current_package["package_id"]),
        from_version=previous_package.get("version") if previous_package else None,
        to_version=int(current_package["version"]),
        status="changed" if has_changes else "unchanged",
        added_records=added,
        removed_records=removed,
        changed_records=changed,
        unchanged_records=unchanged,
        source_version_changes=source_changes,
        scenario_gate_change=scenario_gate_change,
        rollback_safe=True,
    )


def _approved_rule_package(
    *,
    approved_obligation_set: dict[str, Any],
    approved_obligation_set_file: Path,
    scenario_summary: dict[str, Any],
    scenario_summary_file: Path,
    scenario_results: list[dict[str, Any]],
    scenario_results_file: Path,
    sources: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    previous_package: dict[str, Any] | None,
) -> ApprovedStructuredRulePackage:
    approved_obligations = list(approved_obligation_set["records"])
    if not approved_obligations:
        raise ValueError("approved rule package requires at least one approved obligation")
    if any(record["metadata"]["review_status"] != "approved" for record in approved_obligations):
        raise ValueError("approved rule package cannot include non-approved obligations")

    scenario_gate = _scenario_gate(scenario_summary, scenario_summary_file, scenario_results, scenario_results_file)
    records = {"obligations": approved_obligations}
    source_versions = _source_versions(approved_obligations, sources, chunks)
    rollback = {
        "rollback_supported": True,
        "previous_package_id": previous_package.get("package_id") if previous_package else None,
        "compatible_previous_package_ids": [previous_package["package_id"]] if previous_package else [],
        "pinning_required_for_audit_engine": True,
        "pin_fields": ["package_id", "version", "package_hash", "scenario_regression_gate.result_hash"],
    }
    approval = RulePackageApprovalMetadata(
        approved_at=str(approved_obligation_set["approved_at"]),
        approved_by=str(approved_obligation_set["approved_by"]),
        approval_role=str(approved_obligation_set["approval_role"]),
        approval_reason=str(approved_obligation_set["approval_reason"]),
        source_approved_obligation_package=str(approved_obligation_set_file),
        source_approved_obligation_package_version=int(approved_obligation_set["version"]),
    )
    base = {
        "package_id": RULE_PACKAGE_ID,
        "version": 1,
        "status": "approved",
        "immutable": True,
        "generated_at": GENERATED_AT,
        "approval": approval.model_dump(mode="json"),
        "source_versions": [source_version.model_dump(mode="json") for source_version in source_versions],
        "scenario_regression_gate": scenario_gate.model_dump(mode="json"),
        "record_counts": {"obligations": len(approved_obligations)},
        "approved_record_ids": {"obligations": [record["obligation_id"] for record in approved_obligations]},
        "records": records,
        "rollback": rollback,
    }
    package_hash = _hash_json(base)
    return ApprovedStructuredRulePackage(**base, package_hash=package_hash)


def _scenario_gate(
    scenario_summary: dict[str, Any],
    scenario_summary_file: Path,
    scenario_results: list[dict[str, Any]],
    scenario_results_file: Path,
) -> RulePackageScenarioGate:
    status_counter = Counter(str(result["status"]) for result in scenario_results)
    can_publish = bool(scenario_summary.get("canPublishRuleChanges"))
    if not can_publish:
        raise ValueError("cannot publish approved rule package when Phase 8 scenario gate is not passing")
    return RulePackageScenarioGate(
        source_summary_file=str(scenario_summary_file),
        source_results_file=str(scenario_results_file),
        status=str(scenario_summary.get("publishGateStatus")),
        can_publish_rule_changes=can_publish,
        benchmark_count=len(scenario_results),
        pass_count=status_counter["pass"],
        fail_count=status_counter["fail"],
        reviewer_override_count=int(scenario_summary.get("reviewerOverrides") or 0),
        result_hash=_hash_json(scenario_results),
        results=[
            {
                "benchmark_id": result["benchmark_id"],
                "status": result["status"],
                "check_count": len(result.get("checks", [])),
            }
            for result in scenario_results
        ],
    )


def _source_versions(
    approved_records: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> list[RulePackageSourceVersion]:
    source_by_id = {str(source["source_id"]): source for source in sources}
    chunk_by_id = {str(chunk["chunk_id"]): chunk for chunk in chunks}
    cited_chunks_by_source: dict[str, set[str]] = {}
    for record in approved_records:
        for citation in record.get("citations", []):
            cited_chunks_by_source.setdefault(str(citation["source_id"]), set()).add(str(citation["chunk_id"]))

    source_versions: list[RulePackageSourceVersion] = []
    for source_id in sorted(cited_chunks_by_source):
        source = source_by_id[source_id]
        cited_chunk_ids = sorted(cited_chunks_by_source[source_id])
        source_versions.append(
            RulePackageSourceVersion(
                source_id=source_id,
                title=str(source.get("title") or source_id),
                url=str(source.get("url") or ""),
                authority_rank=str(source.get("authority_rank") or ""),
                retrieved_at=str(source.get("retrieved_at") or ""),
                raw_hash=source.get("raw_hash"),
                chunks_count=source.get("chunks_count"),
                cited_chunk_ids=cited_chunk_ids,
                cited_chunk_hashes={
                    chunk_id: str(chunk_by_id[chunk_id].get("text_hash") or _hash_text(str(chunk_by_id[chunk_id].get("text") or "")))
                    for chunk_id in cited_chunk_ids
                },
            )
        )
    return source_versions


def _rollback_pin(package: ApprovedStructuredRulePackage, diff: RulePackageDiff) -> dict[str, Any]:
    return {
        "active_package_id": package.package_id,
        "active_version": package.version,
        "active_package_hash": package.package_hash,
        "pinned_at": GENERATED_AT,
        "pin_reason": "Active approved rule package for deterministic audit-engine consumption.",
        "rollback_supported": package.rollback["rollback_supported"],
        "previous_package_id": package.rollback["previous_package_id"],
        "latest_diff_status": diff.status,
        "scenario_gate_status": package.scenario_regression_gate.status,
        "can_publish_rule_changes": package.scenario_regression_gate.can_publish_rule_changes,
    }


def _summary(package: ApprovedStructuredRulePackage, diff: RulePackageDiff) -> dict[str, Any]:
    return {
        "generatedAt": GENERATED_AT,
        "packageId": package.package_id,
        "version": package.version,
        "status": package.status,
        "immutable": package.immutable,
        "packageHash": package.package_hash,
        "approvedObligations": package.record_counts["obligations"],
        "sourceVersions": len(package.source_versions),
        "scenarioGateStatus": package.scenario_regression_gate.status,
        "scenarioBenchmarks": package.scenario_regression_gate.benchmark_count,
        "scenarioPasses": package.scenario_regression_gate.pass_count,
        "scenarioFailures": package.scenario_regression_gate.fail_count,
        "diffStatus": diff.status,
        "rollbackSupported": package.rollback["rollback_supported"],
        "previousPackageId": package.rollback["previous_package_id"],
    }


def _record_hashes_by_collection(records: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for collection, collection_records in records.items():
        output[collection] = {}
        for record in collection_records:
            record_id = _record_id(record, collection)
            output[collection][record_id] = _hash_json(record)
    return output


def _record_id(record: dict[str, Any], collection: str) -> str:
    for key in [
        "obligation_id",
        "term_id",
        "ftl_item_id",
        "cte_id",
        "kde_id",
        "tlc_rule_id",
        "exemption_rule_id",
        "traceability_plan_requirement_id",
        "sortable_export_field_id",
        "benchmark_id",
        "id",
    ]:
        if record.get(key):
            return str(record[key])
    return f"{collection}:unknown"


def _source_version_changes(previous_package: dict[str, Any] | None, current_package: dict[str, Any]) -> dict[str, list[str]]:
    previous = {source["source_id"]: _hash_json(source) for source in previous_package.get("source_versions", [])} if previous_package else {}
    current = {source["source_id"]: _hash_json(source) for source in current_package.get("source_versions", [])}
    previous_ids = set(previous)
    current_ids = set(current)
    return {
        "added": sorted(current_ids - previous_ids),
        "removed": sorted(previous_ids - current_ids),
        "changed": sorted(source_id for source_id in current_ids & previous_ids if current[source_id] != previous[source_id]),
        "unchanged": sorted(source_id for source_id in current_ids & previous_ids if current[source_id] == previous[source_id]),
    }


def _scenario_gate_change(previous_package: dict[str, Any] | None, current_package: dict[str, Any]) -> dict[str, Any]:
    if not previous_package:
        return {"from": None, "to": current_package["scenario_regression_gate"]["status"]}
    previous_gate = previous_package.get("scenario_regression_gate", {})
    current_gate = current_package.get("scenario_regression_gate", {})
    if _hash_json(previous_gate) == _hash_json(current_gate):
        return {}
    return {
        "from": previous_gate.get("status"),
        "to": current_gate.get("status"),
        "from_result_hash": previous_gate.get("result_hash"),
        "to_result_hash": current_gate.get("result_hash"),
    }


def _load_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
