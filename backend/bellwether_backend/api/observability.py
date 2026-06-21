from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "worker_id",
            "job_id",
            "job_type",
            "audit_project_id",
            "audit_run_id",
            "audit_file_id",
            "attempt_count",
            "stage",
            "status",
            "processed_count",
            "evidence_record_count",
            "finding_count",
            "artifact_count",
            "readiness_status",
            "queued_next_job_id",
            "error_type",
            "size_bytes",
            "file_name",
            "sheet_count",
            "row_count",
            "cell_count",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def build_logger() -> logging.Logger:
    logger = logging.getLogger("bellwether.api")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def add_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["x-request-id"] = request_id
        request.app.state.logger.info(
            "API request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
