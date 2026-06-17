from __future__ import annotations

from traceready_ingestion.backend.schemas.rule_execution import RuleExecutionJobPayload
from traceready_ingestion.backend.services.rule_execution_service import (
    RuleExecutionRepositories,
    run_rule_execution_job,
)
from traceready_ingestion.storage.artifacts import ObjectStore


def execute_rule_execution_job(
    *,
    payload: dict,
    object_store: ObjectStore,
    repositories: RuleExecutionRepositories,
):
    return run_rule_execution_job(
        payload=RuleExecutionJobPayload.model_validate(payload),
        object_store=object_store,
        repositories=repositories,
    )
