from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from traceready_ingestion.backend.schemas.audit_parse import AuditParseJobPayload
from traceready_ingestion.backend.schemas.rule_execution import RuleExecutionJobPayload
from traceready_ingestion.backend.services.audit_parse_service import run_audit_parse_job
from traceready_ingestion.backend.services.normalized_evidence_service import (
    persist_normalized_customer_evidence,
)
from traceready_ingestion.backend.services.rule_execution_service import run_rule_execution_job
from traceready_ingestion.audit_engine.customer_evidence import build_phase10_customer_evidence
from traceready_ingestion.storage.artifacts import LocalObjectStore, audit_upload_key


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
        return {"id": job_id, "status": "succeeded", "checkpoint_json": checkpoint_json}

    def fail_job(self, job_id, *, failure_category, error_json, retryable):
        self.failed.append((job_id, failure_category, error_json, retryable))
        return {"id": job_id, "status": "failed", "error_json": error_json}


class FakeAuditProjectRepository:
    def __init__(self):
        self.parse_errors = []
        self.dataset_snapshots = []
        self.statuses = []

    def update_parse_errors(self, *, audit_project_id, parse_errors):
        self.parse_errors.append((audit_project_id, parse_errors))
        return {"id": audit_project_id, "parse_errors": parse_errors}

    def update_dataset_snapshot(self, *, audit_project_id, dataset_json):
        self.dataset_snapshots.append((audit_project_id, dataset_json))
        return {"id": audit_project_id, "dataset_json": dataset_json}

    def update_status(self, *, audit_project_id, status):
        self.statuses.append((audit_project_id, status))
        return {"id": audit_project_id, "status": status}


class FakeEvidenceRepository:
    def __init__(self):
        self.items = []

    def create_items(self, evidence_items):
        self.items.extend(evidence_items)
        return [{"id": item.id} for item in evidence_items]

    def list_for_run(self, audit_run_id):
        return [{"id": item.id} for item in self.items if item.audit_run_id == audit_run_id]


class FakeNormalizedEvidenceRepository:
    def __init__(self):
        self.business_objects = []
        self.events = []
        self.event_refs = []
        self.kde_values = []
        self.lineage_links = []
        self.review_items = []

    def upsert_business_objects(self, objects):
        self.business_objects.extend(objects)
        return [{"id": item.id} for item in objects]

    def upsert_events(self, events):
        self.events.extend(events)
        return [{"id": item.id} for item in events]

    def create_event_evidence_refs(self, refs):
        self.event_refs.extend(refs)
        return [{"id": index} for index, _item in enumerate(refs)]

    def create_kde_values(self, values):
        self.kde_values.extend(values)
        return [{"id": item.id} for item in values]

    def create_tlc_lineage_links(self, links):
        self.lineage_links.extend(links)
        return [{"id": item.id} for item in links]

    def create_review_items(self, items):
        self.review_items.extend(items)
        return [{"id": item.id} for item in items]


class FakeAuditRunRepository:
    def __init__(self):
        self.summaries = []

    def update_rule_execution_summary(self, **kwargs):
        self.summaries.append(kwargs)
        return {"id": kwargs["audit_run_id"], "summary_json": kwargs["summary_json"]}


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


class FakeParsedWorkbookRepository:
    def __init__(self):
        self.sheets = []
        self.rows = []
        self.cells = []

    def upsert_sheets(self, sheets):
        self.sheets.extend(sheets)
        return [{"id": sheet.id} for sheet in sheets]

    def upsert_rows(self, rows):
        self.rows.extend(rows)
        return [{"id": row.id} for row in rows]

    def upsert_cells(self, cells):
        self.cells.extend(cells)
        return [{"id": cell.id} for cell in cells]


class EnterpriseAuditRepositories:
    def __init__(self, approved_package):
        self.audit_jobs = FakeAuditJobRepository()
        self.audit_projects = FakeAuditProjectRepository()
        self.evidence = FakeEvidenceRepository()
        self.parsed_workbook = FakeParsedWorkbookRepository()
        self.normalized_evidence = FakeNormalizedEvidenceRepository()
        self.audit_runs = FakeAuditRunRepository()
        self.approved_rule_packages = FakeApprovedRulePackageRepository(approved_package)
        self.findings = FakeFindingRepository()
        self.audit_files = FakeAuditFileRepository()
        self.regulatory = type("_Reg", (), {"load_approved_card_payloads": lambda self, collection: []})()


class EnterpriseAuditIntegrationTest(unittest.TestCase):
    def test_upload_job_parse_normalize_rule_execution_review_and_artifact_flow(self):
        approved_package = json.loads(RULE_PACKAGE.read_text(encoding="utf-8"))
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"TRACEREADY_ENV": "test"})
            input_file = Path(tmpdir) / "records.csv"
            workbook_bytes = (
                b"Event ID,Event Type,Lot #,Product,Quantity,Ship Date,From Partner,To Partner\n"
                b"SHIP-1,Shipping,LOT-1,Fresh salsa,10 cases,2026-06-01,Plant A,DC B\n"
                b"RECV-1,Receiving,LOT-1,Fresh salsa,10 cases,2026-06-02,Plant A,DC B\n"
            )
            input_file.write_bytes(workbook_bytes)
            upload_key = audit_upload_key(
                customer_id="customer_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                filename="records.csv",
            )
            stored_upload = store.upload_bytes(
                bucket="private",
                key=upload_key,
                data=workbook_bytes,
                content_type="text/csv",
            )
            repositories = EnterpriseAuditRepositories(approved_package)

            parse_result = run_audit_parse_job(
                payload=AuditParseJobPayload(
                    job_id="job_parse_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    audit_file_id="file_1",
                    customer_id="customer_1",
                    storage_bucket=stored_upload.bucket,
                    storage_key=stored_upload.key,
                    original_file_name="records.csv",
                    content_type=stored_upload.content_type,
                ),
                object_store=store,
                repositories=repositories,
            )
            self.assertEqual(parse_result.status, "succeeded")
            self.assertGreater(parse_result.persisted_evidence_count, 0)
            self.assertGreater(len(repositories.parsed_workbook.rows), 0)
            self.assertEqual(len(repositories.parsed_workbook.cells), parse_result.persisted_evidence_count)
            self.assertEqual(repositories.audit_projects.parse_errors, [("audit_1", [])])

            evidence_package = build_phase10_customer_evidence(input_file=input_file)
            normalized_result = persist_normalized_customer_evidence(
                audit_project_id="audit_1",
                audit_run_id="run_1",
                audit_file_id="file_1",
                package=evidence_package,
                repositories=repositories,
            )
            self.assertGreater(normalized_result.event_count, 0)
            self.assertGreater(normalized_result.kde_value_count, 0)
            self.assertGreater(normalized_result.event_evidence_ref_count, 0)

            rule_result = run_rule_execution_job(
                payload=RuleExecutionJobPayload(
                    job_id="job_rules_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    audit_file_id="file_1",
                    customer_id="customer_1",
                    storage_bucket=stored_upload.bucket,
                    storage_key=stored_upload.key,
                    original_file_name="records.csv",
                    approved_rule_package_id="approved-rule-package-v1",
                    approved_rule_package_version=1,
                    approved_rule_package_hash=approved_package["package_hash"],
                    artifact_bucket="private",
                ),
                object_store=store,
                repositories=repositories,
            )

            self.assertEqual(rule_result.status, "succeeded")
            self.assertGreater(rule_result.finding_count, 0)
            self.assertEqual(rule_result.finding_count, len(repositories.findings.findings))
            self.assertEqual(rule_result.trace_count, len(repositories.findings.traces))
            self.assertGreater(rule_result.artifact_count, 0)
            self.assertEqual(rule_result.artifact_count, len(repositories.audit_files.artifacts))
            self.assertTrue(repositories.audit_runs.summaries[0]["summary_json"]["approvedRuleOnly"])
            self.assertTrue(all(trace.finding_id for trace in repositories.findings.traces))

            artifact = next(item for item in repositories.audit_files.artifacts if item.artifact_type == "exportPackage")
            downloaded = store.download_bytes(bucket=artifact.storage_bucket, key=artifact.storage_key)
            self.assertEqual(downloaded.content_type, "application/json")
            self.assertGreater(downloaded.size_bytes, 0)

            event_types = [event["event_type"] for event in repositories.audit_jobs.events]
            self.assertEqual(
                event_types,
                [
                    "parse_started",
                    "parse_completed",
                    "rule_execution_started",
                    "rule_execution_completed",
                ],
            )


if __name__ == "__main__":
    unittest.main()
