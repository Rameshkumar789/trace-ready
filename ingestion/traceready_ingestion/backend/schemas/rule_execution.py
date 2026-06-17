from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BackendSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RuleExecutionJobPayload(BackendSchema):
    job_id: str
    audit_project_id: str
    audit_run_id: str
    audit_file_id: str
    customer_id: str
    storage_bucket: str
    storage_key: str
    original_file_name: str
    approved_rule_package_id: str
    approved_rule_package_version: int
    approved_rule_package_hash: str | None = None
    ftl_food_items_bucket: str | None = None
    ftl_food_items_key: str | None = None
    artifact_bucket: str
    execution_version: str = "approved_rule_execution_v1"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuleExecutionJobResult(BackendSchema):
    job_id: str
    audit_project_id: str
    audit_run_id: str
    status: Literal["succeeded", "failed"]
    approved_rule_package_id: str
    approved_rule_package_version: int
    finding_count: int = 0
    evidence_ref_count: int = 0
    trace_count: int = 0
    artifact_count: int = 0
    readiness_status: str | None = None
    checkpoint: dict[str, Any] = Field(default_factory=dict)
