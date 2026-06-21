import unittest

from bellwether_backend.backend.repositories.supabase_tables import (
    AuditFileCreate,
    AuditFileRepository,
    AuditFindingCreate,
    AuditJobCreate,
    AuditJobRepository,
    ApprovedRulePackageRepository,
    EvidenceItemCreate,
    EvidenceRepository,
    FindingRepository,
    FindingTraceCreate,
    ParsedWorkbookCellUpsert,
    ParsedWorkbookRepository,
    ParsedWorkbookRowUpsert,
    ParsedWorkbookSheetUpsert,
    RegulatoryRepository,
    RegulatorySourceUpsert,
    NormalizedBusinessObjectUpsert,
    NormalizedEvidenceRepository,
    NormalizedEventEvidenceRefCreate,
    NormalizedEventUpsert,
    NormalizedKdeValueCreate,
    NormalizedReviewItemCreate,
    TlcLineageLinkCreate,
    SourceChunkUpsert,
    SourceIngestionJobCreate,
)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.last_result = None
        self.description = [("id",)]
        self._many_results = None
        self._many_pos = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.connection.statements.append((sql, list(params)))
        self.last_result = {"id": "row-1"}
        self._many_results = None

    def executemany(self, sql, params_seq, returning=False):
        params_seq = [list(params) for params in params_seq]
        for params in params_seq:
            self.connection.statements.append((sql, params))
        if returning:
            self._many_results = [[{"id": f"row-{index + 1}"}] for index in range(len(params_seq))]
            self._many_pos = 0
            self.last_result = self._many_results[0][0] if self._many_results else None
        else:
            self._many_results = None

    def fetchone(self):
        return self.last_result

    def fetchall(self):
        if self._many_results is not None:
            return list(self._many_results[self._many_pos]) if 0 <= self._many_pos < len(self._many_results) else []
        return [self.last_result] if self.last_result else []

    def nextset(self):
        if self._many_results is None:
            return False
        self._many_pos += 1
        return self._many_pos < len(self._many_results)


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.commits = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


class BackendRepositoryTest(unittest.TestCase):
    def test_audit_job_repository_creates_claims_and_events(self):
        connection = FakeConnection()
        repository = AuditJobRepository(connection)

        repository.create_job(
            AuditJobCreate(
                id="job_parse_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                audit_file_id="file_1",
                job_type="parse_customer_workbook",
            )
        )
        repository.claim_next_job("worker-1", ["parse_customer_workbook"])
        repository.append_event(audit_job_id="job_parse_1", event_type="started")

        sql = "\n".join(statement for statement, _params in connection.statements)
        self.assertIn("insert into public.audit_jobs", sql)
        self.assertIn("for update skip locked", sql)
        self.assertIn("insert into public.audit_job_events", sql)
        self.assertEqual(connection.commits, 3)

    def test_audit_job_repository_reads_status_events_and_retries(self):
        connection = FakeConnection()
        repository = AuditJobRepository(connection)

        repository.get_job("job_1")
        repository.list_for_project("audit_1", limit=10)
        repository.list_events("job_1", limit=20)
        repository.retry_job("job_1", requested_by="ops@example.com", reason="retry after config fix")

        sql = "\n".join(statement for statement, _params in connection.statements)
        self.assertIn("from public.audit_jobs", sql)
        self.assertIn("from public.audit_job_events", sql)
        self.assertIn("status = 'retryable'", sql)
        self.assertIn("manualRetry", sql)

    def test_file_evidence_finding_and_trace_repositories_target_audit_tables(self):
        connection = FakeConnection()

        AuditFileRepository(connection).create_file(
            AuditFileCreate(
                id="file_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                file_name="records.xlsx",
                file_type="customer_workbook",
                storage_bucket="private",
                storage_key="customer/audit_1/records.xlsx",
            )
        )
        EvidenceRepository(connection).create_items(
            [
                EvidenceItemCreate(
                    id="evidence_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    evidence_type="workbook_cell",
                    canonical_field="tlc",
                    raw_value="LOT-1",
                    normalized_value="LOT-1",
                )
            ]
        )
        FindingRepository(connection).create_finding(
            AuditFindingCreate(
                id="finding_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                title="Missing receiving KDE",
                severity="major",
                finding_type="missing_kde",
                recommendation="Capture the required receiving KDE.",
                review_state="needs_review",
            )
        )
        FindingRepository(connection).create_trace(
            FindingTraceCreate(
                finding_id="finding_1",
                audit_run_id="run_1",
                sequence=1,
                trace_type="rule",
                title="Approved rule applied",
                payload_json={"citation": "21 CFR 1.1345"},
            )
        )

        sql = "\n".join(statement for statement, _params in connection.statements)
        self.assertIn("insert into public.audit_files", sql)
        self.assertIn("insert into public.evidence_items", sql)
        self.assertIn("insert into public.audit_findings", sql)
        self.assertIn("insert into public.finding_traces", sql)

    def test_audit_file_repository_lists_artifact_metadata(self):
        connection = FakeConnection()

        AuditFileRepository(connection).list_artifacts(
            audit_project_id="audit_1",
            audit_run_id="run_1",
            artifact_types=["audit_report", "export_package"],
        )

        sql = "\n".join(statement for statement, _params in connection.statements)
        self.assertIn("from public.audit_artifacts", sql)
        self.assertIn("artifact_type = any", sql)

    def test_parsed_workbook_repository_targets_sheet_row_cell_tables(self):
        connection = FakeConnection()
        repository = ParsedWorkbookRepository(connection)

        repository.upsert_sheets(
            [
                ParsedWorkbookSheetUpsert(
                    id="parsed_sheet_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    audit_file_id="file_1",
                    sheet_name="records",
                    row_count=2,
                    column_count=5,
                )
            ]
        )
        repository.upsert_rows(
            [
                ParsedWorkbookRowUpsert(
                    id="parsed_row_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    audit_file_id="file_1",
                    sheet_id="parsed_sheet_1",
                    sheet_name="records",
                    source_row_number=2,
                    source_row_key="records.csv:records:row:2",
                )
            ]
        )
        repository.upsert_cells(
            [
                ParsedWorkbookCellUpsert(
                    id="parsed_cell_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    audit_file_id="file_1",
                    sheet_id="parsed_sheet_1",
                    row_id="parsed_row_1",
                    sheet_name="records",
                    source_row_number=2,
                    source_column="Lot #",
                    raw_value="LOT-1",
                    canonical_field="traceability_lot_code",
                    evidence_item_id="evidence_1",
                )
            ]
        )

        sql = "\n".join(statement for statement, _params in connection.statements)
        self.assertIn("insert into public.parsed_workbook_sheets", sql)
        self.assertIn("on conflict (audit_file_id, sheet_name) do update", sql)
        self.assertIn("insert into public.parsed_workbook_rows", sql)
        self.assertIn("on conflict (audit_file_id, sheet_name, source_row_number) do update", sql)
        self.assertIn("insert into public.parsed_workbook_cells", sql)
        self.assertIn("on conflict (audit_file_id, sheet_name, source_row_number, source_column) do update", sql)

    def test_regulatory_repository_upserts_source_and_chunks(self):
        connection = FakeConnection()
        repository = RegulatoryRepository(connection)

        repository.upsert_source(
            RegulatorySourceUpsert(
                id="source_1",
                title="FSMA 204",
                source_type="ecfr",
                source_status="active",
                authority_rank="primary",
                url="https://example.test",
                citation="21 CFR Part 1 Subpart S",
                retrieved_at="2026-06-16T00:00:00Z",
                text_hash="hash",
            )
        )
        repository.upsert_chunks(
            [
                SourceChunkUpsert(
                    id="chunk_1",
                    regulatory_source_id="source_1",
                    chunk_code="21-cfr-1-1345-a",
                    section_label="Receiving",
                    source_location="21 CFR 1.1345",
                    text="Receiving records must include required KDEs.",
                    summary="Receiving KDE rule",
                    citation="21 CFR 1.1345",
                    text_hash="chunk-hash",
                    status="approved_for_extraction",
                )
            ]
        )

        sql = "\n".join(statement for statement, _params in connection.statements)
        self.assertIn("insert into public.regulatory_sources", sql)
        self.assertIn("on conflict (id) do update", sql)
        self.assertIn("insert into public.source_chunks", sql)
        self.assertIn("on conflict (chunk_code) do update", sql)

    def test_regulatory_repository_creates_and_reads_source_ingestion_jobs(self):
        connection = FakeConnection()
        repository = RegulatoryRepository(connection)

        repository.create_source_ingestion_job(
            SourceIngestionJobCreate(
                id="source_job_1",
                source_type="ecfr",
                job_type="ingest_regulatory_source",
                source_url="https://example.test/ecfr",
            )
        )
        repository.append_source_job_event(job_id="source_job_1", event_type="queued")
        repository.get_source_ingestion_job("source_job_1")
        repository.list_source_ingestion_jobs(status="queued", limit=10)
        repository.list_source_job_events("source_job_1", limit=10)

        sql = "\n".join(statement for statement, _params in connection.statements)
        self.assertIn("insert into public.source_ingestion_jobs", sql)
        self.assertIn("insert into public.source_ingestion_job_events", sql)
        self.assertIn("from public.source_ingestion_jobs", sql)
        self.assertIn("from public.source_ingestion_job_events", sql)

    def test_approved_rule_package_repository_composes_package_from_rows(self):
        class PackageCursor(FakeCursor):
            def execute(self, sql, params):
                self.connection.statements.append((sql, list(params)))
                if "from public.approved_rule_packages" in sql:
                    self.last_result = {
                        "id": "pkg_row_1",
                        "package_id": "approved-rule-package-v1",
                        "version": 1,
                        "status": "approved",
                        "package_hash": "hash-1",
                        "generated_at": "2026-06-16T00:00:00Z",
                        "approved_at": "2026-06-16T00:00:00Z",
                        "approved_by": "reviewer",
                        "metadata_json": {"scenarioGateStatus": "passed"},
                    }
                else:
                    self.last_result = None

            def fetchall(self):
                return [
                    {
                        "collection": "obligations",
                        "record_id": "obl_1",
                        "payload": {
                            "obligation_id": "obl_1",
                            "metadata": {"review_status": "approved"},
                        },
                    }
                ]

        class PackageConnection(FakeConnection):
            def cursor(self):
                return PackageCursor(self)

        repository = ApprovedRulePackageRepository(PackageConnection())

        package = repository.load_package(package_id="approved-rule-package-v1", version=1)

        self.assertEqual(package["package_id"], "approved-rule-package-v1")
        self.assertEqual(package["version"], 1)
        self.assertEqual(package["records"]["obligations"][0]["obligation_id"], "obl_1")
        self.assertEqual(package["metadata"]["scenarioGateStatus"], "passed")

    def test_normalized_evidence_repository_targets_normalized_tables(self):
        connection = FakeConnection()
        repository = NormalizedEvidenceRepository(connection)

        repository.upsert_business_objects(
            [
                NormalizedBusinessObjectUpsert(
                    id="nbo_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    object_type="product",
                    object_key="product:fresh-salsa",
                    name="Fresh salsa",
                )
            ]
        )
        repository.upsert_events(
            [
                NormalizedEventUpsert(
                    id="nev_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    source_row_key="records.csv:csv:2",
                )
            ]
        )
        repository.create_event_evidence_refs(
            [
                NormalizedEventEvidenceRefCreate(
                    normalized_event_id="nev_1",
                    evidence_item_id="ev_1",
                )
            ]
        )
        repository.create_kde_values(
            [
                NormalizedKdeValueCreate(
                    id="kde_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    normalized_event_id="nev_1",
                    evidence_item_id="ev_1",
                    kde_key="traceability_lot_code",
                )
            ]
        )
        repository.create_tlc_lineage_links(
            [
                TlcLineageLinkCreate(
                    id="tlc_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    link_type="event_lot",
                    source_tlc="LOT-1",
                    output_tlc="LOT-1",
                )
            ]
        )
        repository.create_review_items(
            [
                NormalizedReviewItemCreate(
                    id="nri_1",
                    audit_project_id="audit_1",
                    audit_run_id="run_1",
                    review_type="event_ambiguity",
                    question="Confirm event type.",
                    reason="Ambiguous event.",
                    severity="medium",
                )
            ]
        )

        sql = "\n".join(statement for statement, _params in connection.statements)
        self.assertIn("insert into public.normalized_business_objects", sql)
        self.assertIn("insert into public.normalized_events", sql)
        self.assertIn("insert into public.normalized_event_evidence_refs", sql)
        self.assertIn("on conflict (normalized_event_id, evidence_item_id, role) do nothing", sql)
        self.assertIn("insert into public.normalized_kde_values", sql)
        self.assertIn("insert into public.tlc_lineage_links", sql)
        self.assertIn("insert into public.normalized_review_items", sql)


if __name__ == "__main__":
    unittest.main()
