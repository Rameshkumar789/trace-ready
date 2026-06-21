from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from bellwether_backend.backend.jobs.rule_execution import execute_rule_execution_job
from bellwether_backend.backend.repositories.supabase_tables import stable_row_id
from bellwether_backend.backend.schemas.rule_execution import RuleExecutionJobPayload
from bellwether_backend.backend.services.rule_execution_service import run_rule_execution_job
from bellwether_backend.storage.artifacts import LocalObjectStore, audit_upload_key


SAMPLE_CSV = (
    b"Event ID,Event Type,Lot #,Product,Quantity,Ship Date,From Partner,To Partner\n"
    b"SHIP-1,Shipping,LOT-1,Fresh salsa,10 cases,2026-06-01,Plant A,DC B\n"
    b"RECV-1,Receiving,LOT-1,Fresh salsa,10 cases,2026-06-02,Plant A,DC B\n"
)


ROOT = Path(__file__).resolve().parents[2]
RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"


class FakeAuditJobRepository:
    def __init__(self):
        self.events = []
        self.checkpoints = []
        self.completed = []
        self.failed = []

    def append_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs

    def checkpoint_job(self, job_id, checkpoint_json):
        self.checkpoints.append((job_id, checkpoint_json))
        return {"id": job_id, "checkpoint_json": checkpoint_json}

    def complete_job(self, job_id, checkpoint_json=None):
        self.completed.append((job_id, checkpoint_json))
        return {"id": job_id, "checkpoint_json": checkpoint_json}

    def fail_job(self, job_id, *, failure_category, error_json, retryable):
        self.failed.append((job_id, failure_category, error_json, retryable))
        return {"id": job_id, "error_json": error_json}


class FakeAuditRunRepository:
    def __init__(self):
        self.summaries = []

    def update_rule_execution_summary(self, **kwargs):
        self.summaries.append(kwargs)
        return {"id": kwargs["audit_run_id"], "summary_json": kwargs["summary_json"]}


class FakeAuditProjectRepository:
    def __init__(self):
        self.statuses = []

    def update_status(self, *, audit_project_id, status):
        self.statuses.append((audit_project_id, status))
        return {"id": audit_project_id, "status": status}


class FakeApprovedRulePackageRepository:
    def __init__(self, package):
        self.package = package
        self.calls = []

    def load_package(self, *, package_id, version, package_hash=None):
        self.calls.append((package_id, version, package_hash))
        if package_id != self.package["package_id"] or version != self.package["version"]:
            raise LookupError("not found")
        return self.package


class FakeFindingRepository:
    def __init__(self):
        self.deleted_runs = []
        self.findings = []
        self.refs = []
        self.traces = []

    def delete_for_run(self, audit_run_id):
        self.deleted_runs.append(audit_run_id)

    def create_finding(self, finding):
        self.findings.append(finding)
        return {"id": finding.id}

    def link_evidence(self, *, finding_id, evidence_item_id, role):
        self.refs.append((finding_id, evidence_item_id, role))
        return {"finding_id": finding_id, "evidence_item_id": evidence_item_id, "role": role}

    def create_trace(self, trace):
        self.traces.append(trace)
        return {"id": f"trace-{len(self.traces)}"}


class FakeAuditFileRepository:
    def __init__(self):
        self.artifacts = []

    def create_artifact(self, artifact):
        self.artifacts.append(artifact)
        return {"id": artifact.id}


class FakeEvidenceRepository:
    def __init__(self, existing_ids=None):
        self.existing_ids = list(existing_ids or [])

    def list_for_run(self, audit_run_id):
        return [{"id": evidence_id} for evidence_id in self.existing_ids]


class FakeRegulatoryRepository:
    def load_approved_card_payloads(self, collection):
        return []


class FakeRepositories:
    def __init__(self, package, evidence_ids=None):
        self.audit_jobs = FakeAuditJobRepository()
        self.audit_projects = FakeAuditProjectRepository()
        self.audit_runs = FakeAuditRunRepository()
        self.approved_rule_packages = FakeApprovedRulePackageRepository(package)
        self.findings = FakeFindingRepository()
        self.audit_files = FakeAuditFileRepository()
        self.evidence = FakeEvidenceRepository(evidence_ids)
        self.regulatory = FakeRegulatoryRepository()


class RuleExecutionServiceTest(unittest.TestCase):
    def test_rule_execution_loads_package_runs_checks_persists_outputs_and_artifacts(self):
        approved_package = json.loads(RULE_PACKAGE.read_text(encoding="utf-8"))
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"BELLWETHER_ENV": "test"})
            workbook_key = audit_upload_key(
                customer_id="customer_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                filename="records.csv",
            )
            store.upload_bytes(
                bucket="private",
                key=workbook_key,
                data=(
                    b"Event ID,Event Type,Lot #,Product,Quantity,Ship Date,From Partner,To Partner\n"
                    b"SHIP-1,Shipping,LOT-1,Fresh salsa,10 cases,2026-06-01,Plant A,DC B\n"
                    b"RECV-1,Receiving,LOT-1,Fresh salsa,10 cases,2026-06-02,Plant A,DC B\n"
                ),
                content_type="text/csv",
            )
            repositories = FakeRepositories(approved_package)

            result = run_rule_execution_job(
                payload=RuleExecutionJobPayload(
                    job_id="job_rules_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    audit_file_id="file_1",
                    customer_id="customer_1",
                    storage_bucket="private",
                    storage_key=workbook_key,
                    original_file_name="records.csv",
                    approved_rule_package_id="approved-rule-package-v1",
                    approved_rule_package_version=1,
                    approved_rule_package_hash=approved_package["package_hash"],
                    artifact_bucket="private",
                ),
                object_store=store,
                repositories=repositories,
            )

            self.assertEqual(result.status, "succeeded")
            self.assertEqual(repositories.approved_rule_packages.calls[0][0], "approved-rule-package-v1")
            self.assertGreater(result.finding_count, 0)
            self.assertEqual(result.finding_count, len(repositories.findings.findings))
            self.assertEqual(repositories.findings.deleted_runs, ["run_1"])
            self.assertEqual(result.trace_count, len(repositories.findings.traces))
            self.assertEqual(result.trace_count, result.finding_count * 3)
            self.assertGreater(result.artifact_count, 0)
            self.assertEqual(result.artifact_count, len(repositories.audit_files.artifacts))
            self.assertEqual(len(repositories.audit_runs.summaries), 1)
            self.assertTrue(repositories.audit_runs.summaries[0]["summary_json"]["approvedRuleOnly"])
            self.assertEqual(repositories.audit_projects.statuses, [("audit_1", "succeeded")])
            self.assertIn(result.readiness_status, {"ready", "needs_review", "blocked"})
            self.assertEqual(repositories.audit_jobs.completed[0][0], "job_rules_1")
            event_types = [event["event_type"] for event in repositories.audit_jobs.events]
            self.assertEqual(event_types, ["rule_execution_started", "rule_execution_completed"])

    def test_rule_execution_is_fk_safe_and_links_scoped_evidence(self):
        approved_package = json.loads(RULE_PACKAGE.read_text(encoding="utf-8"))
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"BELLWETHER_ENV": "test"})
            workbook_key = audit_upload_key(
                customer_id="customer_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                filename="records.csv",
            )
            store.upload_bytes(bucket="private", key=workbook_key, data=SAMPLE_CSV, content_type="text/csv")
            payload = RuleExecutionJobPayload(
                job_id="job_rules_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                audit_file_id="file_1",
                customer_id="customer_1",
                storage_bucket="private",
                storage_key=workbook_key,
                original_file_name="records.csv",
                approved_rule_package_id="approved-rule-package-v1",
                approved_rule_package_version=1,
                approved_rule_package_hash=approved_package["package_hash"],
                artifact_bucket="private",
            )

            # No evidence_items persisted for the run: links must be skipped, not raise a
            # foreign-key violation. The job still succeeds and findings still persist.
            repo_empty = FakeRepositories(approved_package)
            result_empty = run_rule_execution_job(payload=payload, object_store=store, repositories=repo_empty)
            self.assertEqual(result_empty.status, "succeeded")
            self.assertGreater(result_empty.finding_count, 0)
            self.assertEqual(result_empty.evidence_ref_count, 0)
            self.assertEqual(repo_empty.findings.refs, [])

            # Evidence persisted under the same file-scoped ids the parser uses: links now
            # resolve, and every linked id is a scoped id that exists for the run.
            raw_ids = {eid for finding in repo_empty.findings.findings for eid in (finding.evidence_refs_json or [])}
            scoped_ids = {stable_row_id("evidence", "file_1", raw_id) for raw_id in raw_ids}
            repo_full = FakeRepositories(approved_package, evidence_ids=scoped_ids)
            result_full = run_rule_execution_job(payload=payload, object_store=store, repositories=repo_full)
            self.assertEqual(result_full.status, "succeeded")
            linked_ids = {ref[1] for ref in repo_full.findings.refs}
            self.assertTrue(linked_ids.issubset(scoped_ids))
            if scoped_ids:
                self.assertGreater(result_full.evidence_ref_count, 0)

    def test_rule_execution_failure_persists_failed_job(self):
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"BELLWETHER_ENV": "test"})
            repositories = FakeRepositories({"package_id": "different", "version": 1})

            result = execute_rule_execution_job(
                payload={
                    "job_id": "job_rules_2",
                    "audit_project_id": "audit_1",
                    "audit_run_id": "run_1",
                    "audit_file_id": "file_1",
                    "customer_id": "customer_1",
                    "storage_bucket": "private",
                    "storage_key": "missing.csv",
                    "original_file_name": "records.csv",
                    "approved_rule_package_id": "approved-rule-package-v1",
                    "approved_rule_package_version": 1,
                    "artifact_bucket": "private",
                },
                object_store=store,
                repositories=repositories,
            )

            self.assertEqual(result.status, "failed")
            self.assertEqual(len(repositories.audit_jobs.failed), 1)
            self.assertEqual(repositories.audit_jobs.failed[0][1], "rule_execution_error")
            self.assertFalse(repositories.audit_jobs.failed[0][3])
            self.assertEqual(repositories.audit_projects.statuses, [("audit_1", "failed")])
            event_types = [event["event_type"] for event in repositories.audit_jobs.events]
            self.assertEqual(event_types, ["rule_execution_started", "rule_execution_failed"])


if __name__ == "__main__":
    unittest.main()
