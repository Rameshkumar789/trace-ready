from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from traceready_backend.backend.jobs.audit_parse import execute_audit_parse_job
from traceready_backend.backend.schemas.audit_parse import AuditParseJobPayload
from traceready_backend.backend.services.audit_parse_service import run_audit_parse_job
from traceready_backend.storage.artifacts import LocalObjectStore, audit_upload_key


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

    def update_parse_errors(self, *, audit_project_id, parse_errors):
        self.parse_errors.append((audit_project_id, parse_errors))
        return {"id": audit_project_id, "parse_errors": parse_errors}

    def update_dataset_snapshot(self, *, audit_project_id, dataset_json):
        self.dataset_snapshots.append((audit_project_id, dataset_json))
        return {"id": audit_project_id, "dataset_json": dataset_json}


class FakeEvidenceRepository:
    def __init__(self):
        self.items = []

    def create_items(self, evidence_items):
        self.items.extend(evidence_items)
        return [{"id": item.id} for item in evidence_items]


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


class FakeRepositories:
    def __init__(self):
        self.audit_jobs = FakeAuditJobRepository()
        self.audit_projects = FakeAuditProjectRepository()
        self.evidence = FakeEvidenceRepository()
        self.parsed_workbook = FakeParsedWorkbookRepository()


class AuditParseJobTest(unittest.TestCase):
    def test_audit_parse_job_downloads_parses_persists_and_completes(self):
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"TRACEREADY_ENV": "test"})
            key = audit_upload_key(
                customer_id="customer_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                filename="records.csv",
            )
            store.upload_bytes(
                bucket="private",
                key=key,
                data=(
                    b"Event Type,Lot #,Product,Quantity,Ship Date\n"
                    b"Shipping,LOT-1,Fresh salsa,10 cases,2026-06-01\n"
                    b"Receiving,LOT-1,Fresh salsa,10 cases,2026-06-02\n"
                ),
                content_type="text/csv",
            )
            repositories = FakeRepositories()

            result = run_audit_parse_job(
                payload=AuditParseJobPayload(
                    job_id="job_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    audit_file_id="file_1",
                    customer_id="customer_1",
                    storage_bucket="private",
                    storage_key=key,
                    original_file_name="records.csv",
                ),
                object_store=store,
                repositories=repositories,
            )

            self.assertEqual(result.status, "succeeded")
            self.assertGreater(result.evidence_record_count, 0)
            self.assertEqual(result.evidence_record_count, result.persisted_evidence_count)
            self.assertEqual(len(repositories.audit_jobs.completed), 1)
            self.assertEqual(repositories.audit_projects.parse_errors, [("audit_1", [])])
            self.assertEqual(len(repositories.audit_projects.dataset_snapshots), 1)
            snapshot = repositories.audit_projects.dataset_snapshots[0][1]
            self.assertEqual(snapshot["source"]["storageKey"], key)
            self.assertEqual(snapshot["recordCounts"]["evidenceRecords"], len(repositories.evidence.items))
            self.assertEqual(snapshot["recordCounts"]["parsedCells"], len(repositories.parsed_workbook.cells))
            self.assertEqual(snapshot["recordCounts"]["parsedRows"], len(repositories.parsed_workbook.rows))
            canonical_fields = {item.canonical_field for item in repositories.evidence.items}
            self.assertIn("event_type", canonical_fields)
            self.assertIn("traceability_lot_code", canonical_fields)
            self.assertIn("quantity", canonical_fields)
            self.assertEqual([sheet.sheet_name for sheet in repositories.parsed_workbook.sheets], ["csv"])
            self.assertEqual({row.source_row_number for row in repositories.parsed_workbook.rows}, {2, 3})
            self.assertEqual(
                {cell.evidence_item_id for cell in repositories.parsed_workbook.cells},
                {item.id for item in repositories.evidence.items},
            )
            event_types = [event["event_type"] for event in repositories.audit_jobs.events]
            self.assertEqual(event_types, ["parse_started", "parse_completed"])

    def test_audit_parse_job_persists_parse_error_and_fails_job(self):
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"TRACEREADY_ENV": "test"})
            store.upload_bytes(
                bucket="private",
                key="customers/customer_1/audits/audit_1/runs/run_1/uploads/readme.txt",
                data=b"not a supported workbook",
                content_type="text/plain",
            )
            repositories = FakeRepositories()

            result = execute_audit_parse_job(
                payload={
                    "job_id": "job_2",
                    "audit_project_id": "audit_1",
                    "audit_run_id": "run_1",
                    "audit_file_id": "file_2",
                    "customer_id": "customer_1",
                    "storage_bucket": "private",
                    "storage_key": "customers/customer_1/audits/audit_1/runs/run_1/uploads/readme.txt",
                    "original_file_name": "readme.txt",
                },
                object_store=store,
                repositories=repositories,
            )

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.evidence_record_count, 0)
            self.assertEqual(len(result.parse_errors), 1)
            self.assertEqual(result.parse_errors[0].scope, "file")
            self.assertEqual(len(repositories.audit_jobs.failed), 1)
            self.assertEqual(repositories.audit_jobs.failed[0][1], "parse_error")
            self.assertFalse(repositories.audit_jobs.failed[0][3])
            self.assertEqual(repositories.audit_projects.parse_errors[0][0], "audit_1")
            self.assertEqual(repositories.audit_projects.parse_errors[0][1][0]["scope"], "file")
            self.assertEqual(repositories.evidence.items, [])
            self.assertEqual(repositories.parsed_workbook.sheets, [])
            self.assertEqual(repositories.parsed_workbook.rows, [])
            self.assertEqual(repositories.parsed_workbook.cells, [])
            event_types = [event["event_type"] for event in repositories.audit_jobs.events]
            self.assertEqual(event_types, ["parse_started", "parse_failed"])


if __name__ == "__main__":
    unittest.main()
