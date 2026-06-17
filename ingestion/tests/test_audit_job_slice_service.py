import unittest
from types import SimpleNamespace
from unittest.mock import patch

from traceready_ingestion.backend.services.audit_job_slice_service import run_audit_job_slice


class FakeAuditJobs:
    def __init__(self, job):
        self.job = job
        self.created_jobs = []
        self.events = []
        self.failed = []
        self.claims = 0

    def claim_next_job(self, worker_id, job_types, *, stale_lock_minutes=15):
        self.claims += 1
        if self.claims > 1:
            return None
        return self.job

    def append_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs

    def create_job(self, job):
        self.created_jobs.append(job)
        return {"id": job.id}

    def fail_job(self, job_id, *, failure_category, error_json, retryable):
        self.failed.append((job_id, failure_category, error_json, retryable))
        return {"id": job_id, "status": "retryable" if retryable else "failed"}


class FakeRepositories:
    def __init__(self, job):
        self.audit_jobs = FakeAuditJobs(job)


class AuditJobSliceServiceTest(unittest.TestCase):
    def test_parse_job_success_queues_rule_execution_job(self):
        job = {
            "id": "job_parse_1",
            "audit_project_id": "audit_1",
            "audit_run_id": "run_1",
            "audit_file_id": "file_1",
            "job_type": "parse_customer_workbook",
            "attempt_count": 1,
            "max_attempts": 3,
            "priority": 100,
            "checkpoint_json": {
                "customerId": "customer_1",
                "storageBucket": "private",
                "storageKey": "customers/customer_1/audits/audit_1/runs/run_1/uploads/records.csv",
                "originalFileName": "records.csv",
                "parserVersion": "customer_evidence_v1",
                "approvedRulePackageId": "approved-rule-package-v1",
                "approvedRulePackageVersion": 1,
            },
        }
        repositories = FakeRepositories(job)

        with patch(
            "traceready_ingestion.backend.services.audit_job_slice_service.run_audit_parse_job",
            return_value=SimpleNamespace(status="succeeded", checkpoint={"stage": "completed"}),
        ) as parse_job:
            result = run_audit_job_slice(
                repositories=repositories,
                object_store=object(),
                worker_id="worker-1",
                job_types=["parse_customer_workbook"],
                max_jobs=1,
            )

        self.assertEqual(result["processedCount"], 1)
        self.assertEqual(result["processed"][0]["status"], "succeeded")
        self.assertEqual(len(repositories.audit_jobs.created_jobs), 1)
        self.assertEqual(repositories.audit_jobs.created_jobs[0].job_type, "execute_approved_rules")
        self.assertEqual(repositories.audit_jobs.events[0]["event_type"], "job_claimed")
        self.assertEqual(repositories.audit_jobs.events[1]["event_type"], "rule_execution_queued")
        parse_job.assert_called_once()


if __name__ == "__main__":
    unittest.main()
