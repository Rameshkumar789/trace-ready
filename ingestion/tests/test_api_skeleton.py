import asyncio
import json
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from traceready_ingestion.api.config import RuntimeEnvironment, ServiceSettings, load_settings
from traceready_ingestion.api.main import create_app


def call_asgi(app, path, headers=None, method="GET", json_body=None):
    messages = []
    request_sent = False
    body_bytes = b"" if json_body is None else json.dumps(json_body).encode("utf-8")

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    request_headers = dict(headers or {})
    if json_body is not None:
        request_headers.setdefault("content-type", "application/json")
    encoded_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in request_headers.items()
    ]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": encoded_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))

    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], dict(start["headers"]), body


class ApiSkeletonTest(unittest.TestCase):
    def test_health_endpoint_returns_service_metadata(self):
        app = create_app(
            ServiceSettings(environment=RuntimeEnvironment.TEST, internal_api_token="secret")
        )

        status, headers, body = call_asgi(app, "/health", {"x-request-id": "req-test"})

        self.assertEqual(status, 200)
        self.assertEqual(headers[b"x-request-id"], b"req-test")
        self.assertIn(b'"status":"ok"', body)
        self.assertIn(b'"service":"traceready-python-backend"', body)
        self.assertIn(b'"environment":"test"', body)

    def test_ready_endpoint_reports_missing_required_config(self):
        app = create_app(
            ServiceSettings(
                environment=RuntimeEnvironment.PRODUCTION,
                require_configured_dependencies=True,
            )
        )

        status, _headers, body = call_asgi(app, "/ready")

        self.assertEqual(status, 503)
        self.assertIn(b'"status":"not_ready"', body)
        self.assertIn(b'"name":"supabase_database_url"', body)
        self.assertIn(b'"name":"supabase_service_role_key"', body)

    def test_internal_endpoint_requires_configured_token(self):
        app = create_app(
            ServiceSettings(environment=RuntimeEnvironment.TEST, internal_api_token="secret")
        )

        denied_status, _denied_headers, _denied_body = call_asgi(app, "/internal/ping")
        allowed_status, _allowed_headers, allowed_body = call_asgi(
            app, "/internal/ping", {"x-traceready-internal-token": "secret"}
        )

        self.assertEqual(denied_status, 401)
        self.assertEqual(allowed_status, 200)
        self.assertIn(b'"status":"ok"', allowed_body)
        self.assertIn(b'"scope":"internal"', allowed_body)

    def test_load_settings_reads_vercel_and_supabase_environment(self):
        settings = load_settings(
            {
                "VERCEL_ENV": "preview",
                "SUPABASE_DATABASE_URL": "postgresql://example",
                "NEXT_PUBLIC_SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "service-role",
                "TRACEREADY_INTERNAL_API_TOKEN": "internal",
                "TRACEREADY_ALLOWED_ORIGINS": "https://app.example.com, https://ops.example.com",
            }
        )

        self.assertEqual(settings.environment, RuntimeEnvironment.PREVIEW)
        self.assertEqual(settings.database_url, "postgresql://example")
        self.assertEqual(settings.supabase_url, "https://example.supabase.co")
        self.assertEqual(settings.allowed_origins, ("https://app.example.com", "https://ops.example.com"))

    def test_internal_audit_retry_endpoint_uses_repository(self):
        app = create_app(
            ServiceSettings(environment=RuntimeEnvironment.TEST, internal_api_token="secret")
        )
        fake_jobs = FakeAuditJobs()

        with patch("traceready_ingestion.api.main.supabase_connection", fake_supabase_connection), patch(
            "traceready_ingestion.api.main.AuditJobRepository", return_value=fake_jobs
        ):
            status, _headers, body = call_asgi(
                app,
                "/internal/jobs/audit/job_1/retry",
                {"x-traceready-internal-token": "secret"},
                method="POST",
                json_body={"requested_by": "ops@example.com", "reason": "operator retry"},
            )

        self.assertEqual(status, 200)
        self.assertIn(b'"status":"ok"', body)
        self.assertEqual(fake_jobs.retry_requests, [("job_1", "ops@example.com", "operator retry")])
        self.assertEqual(fake_jobs.events[0]["event_type"], "manual_retry_requested")

    def test_internal_source_ingestion_endpoint_queues_job(self):
        app = create_app(
            ServiceSettings(environment=RuntimeEnvironment.TEST, internal_api_token="secret")
        )
        fake_regulatory = FakeRegulatory()

        with patch("traceready_ingestion.api.main.supabase_connection", fake_supabase_connection), patch(
            "traceready_ingestion.api.main.RegulatoryRepository", return_value=fake_regulatory
        ):
            status, _headers, body = call_asgi(
                app,
                "/internal/regulatory/source-ingestion-jobs",
                {"x-traceready-internal-token": "secret"},
                method="POST",
                json_body={
                    "source_type": "ecfr",
                    "source_url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-S",
                },
            )

        self.assertEqual(status, 200)
        self.assertIn(b'"job_1"', body)
        self.assertEqual(fake_regulatory.created_jobs[0].source_type, "ecfr")
        self.assertEqual(fake_regulatory.events[0]["event_type"], "source_ingestion_queued")

    def test_internal_process_slice_endpoint_runs_bounded_processor(self):
        app = create_app(
            ServiceSettings(environment=RuntimeEnvironment.TEST, internal_api_token="secret")
        )

        with patch("traceready_ingestion.api.main.supabase_connection", fake_supabase_connection), patch(
            "traceready_ingestion.api.main.build_object_store", return_value=object()
        ), patch(
            "traceready_ingestion.api.main.run_audit_job_slice",
            return_value={"status": "ok", "processedCount": 1, "processed": [{"jobId": "job_1"}], "continue": False},
        ) as processor:
            status, _headers, body = call_asgi(
                app,
                "/internal/jobs/audit/process-slice",
                {"x-traceready-internal-token": "secret"},
                method="POST",
                json_body={"worker_id": "worker-test", "job_types": ["parse_customer_workbook"], "max_jobs": 1},
            )

        self.assertEqual(status, 200)
        self.assertIn(b'"processedCount":1', body)
        self.assertEqual(processor.call_args.kwargs["worker_id"], "worker-test")
        self.assertEqual(processor.call_args.kwargs["job_types"], ["parse_customer_workbook"])

    def test_internal_source_integrity_endpoint_runs_checker(self):
        app = create_app(
            ServiceSettings(environment=RuntimeEnvironment.TEST, internal_api_token="secret")
        )

        with patch("traceready_ingestion.api.main.supabase_connection", fake_supabase_connection), patch(
            "traceready_ingestion.api.main.build_object_store", return_value=object()
        ), patch(
            "traceready_ingestion.api.main.RegulatoryRepository", return_value=object()
        ), patch(
            "traceready_ingestion.api.main.check_source_artifact_integrity",
            return_value=FakeIntegrityReport(),
        ) as checker:
            status, _headers, body = call_asgi(
                app,
                "/internal/regulatory/source-integrity-check",
                {"x-traceready-internal-token": "secret"},
                method="POST",
            )

        self.assertEqual(status, 200)
        self.assertIn(b'"status":"pass"', body)
        self.assertEqual(checker.call_args.kwargs["source_version"], 1)


@contextmanager
def fake_supabase_connection(_settings):
    yield object()


class FakeAuditJobs:
    def __init__(self):
        self.retry_requests = []
        self.events = []

    def retry_job(self, job_id, *, requested_by, reason):
        self.retry_requests.append((job_id, requested_by, reason))
        return {"id": job_id, "audit_project_id": "audit_1", "audit_run_id": "run_1", "status": "retryable"}

    def append_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs


class FakeRegulatory:
    def __init__(self):
        self.created_jobs = []
        self.events = []

    def create_source_ingestion_job(self, job):
        self.created_jobs.append(job)
        return {"id": "job_1", "source_type": job.source_type, "status": job.status}

    def append_source_job_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs


class FakeIntegrityReport:
    def to_dict(self):
        return {"status": "pass", "summary": {"sourceCount": 1, "chunkCount": 1}, "issues": []}


if __name__ == "__main__":
    unittest.main()
