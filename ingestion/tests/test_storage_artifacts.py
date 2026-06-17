from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from traceready_ingestion.api.config import ObjectStoreMode, RuntimeEnvironment, ServiceSettings
from traceready_ingestion.storage.artifacts import (
    LocalObjectStore,
    NonDurableObjectStoreError,
    ObjectStorageError,
    SupabaseObjectStore,
    audit_artifact_key,
    audit_upload_key,
    build_object_store,
    capture_payload,
    regulatory_package_key,
    source_approval_artifact_key,
    source_chunk_package_key,
    source_draft_payload_key,
    source_normalized_key,
    source_raw_key,
)


class FakeSupabaseBucket:
    def __init__(self):
        self.objects = {}
        self.upload_calls = []

    def upload(self, *, path, file, file_options):
        self.upload_calls.append((path, file, file_options))
        self.objects[path] = bytes(file)
        return {"path": path}

    def download(self, path):
        return self.objects[path]

    def list(self, path):
        prefix = path.rstrip("/") + "/"
        return [
            {"name": key.removeprefix(prefix)}
            for key in sorted(self.objects)
            if key.startswith(prefix) and "/" not in key.removeprefix(prefix)
        ]


class FakeSupabaseStorage:
    def __init__(self):
        self.buckets = {}

    def from_(self, bucket):
        self.buckets.setdefault(bucket, FakeSupabaseBucket())
        return self.buckets[bucket]


class FakeSupabaseClient:
    def __init__(self):
        self.storage = FakeSupabaseStorage()


class StorageArtifactsTest(unittest.TestCase):
    def test_object_key_conventions_are_stable_and_sanitized(self):
        self.assertEqual(
            source_raw_key(source_id="ecfr 21/cfr", version=2, filename="part 1.xml"),
            "regulatory/sources/ecfr-21/cfr/versions/2/raw/part-1.xml",
        )
        self.assertEqual(
            source_normalized_key(source_id="source_1", version=1, filename="normalized.json"),
            "regulatory/sources/source_1/versions/1/normalized/normalized.json",
        )
        self.assertEqual(
            source_chunk_package_key(source_id="source_1", version=1),
            "regulatory/sources/source_1/versions/1/chunks/source-chunks.json",
        )
        self.assertEqual(
            regulatory_package_key(package_id="approved-rule-package-v1", version=3, filename="package.json"),
            "regulatory/packages/approved-rule-package-v1/versions/3/package.json",
        )
        self.assertEqual(
            source_draft_payload_key(source_id="source_1", version=1, draft_id="draft 1", filename="payload.json"),
            "regulatory/sources/source_1/versions/1/drafts/draft-1/payload.json",
        )
        self.assertEqual(
            source_approval_artifact_key(source_id="source_1", version=1, filename="approval manifest.json"),
            "regulatory/sources/source_1/versions/1/approval/approval-manifest.json",
        )
        self.assertEqual(
            audit_upload_key(
                customer_id="customer_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                filename="ERP Export.xlsx",
            ),
            "customers/customer_1/audits/audit_1/runs/run_1/uploads/ERP-Export.xlsx",
        )
        self.assertEqual(
            audit_artifact_key(
                customer_id="customer_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                artifact_type="fda_export",
                filename="sortable.xlsx",
            ),
            "customers/customer_1/audits/audit_1/runs/run_1/artifacts/fda_export/sortable.xlsx",
        )

    def test_local_object_store_upload_download_list_and_hash(self):
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"TRACEREADY_ENV": "test"})
            key = audit_upload_key(
                customer_id="customer_1",
                audit_project_id="audit_1",
                audit_run_id="run_1",
                filename="records.xlsx",
            )

            stored = store.upload_bytes(
                bucket="private",
                key=key,
                data=b"workbook-bytes",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            payload = store.download_bytes(bucket="private", key=key)

            self.assertEqual(stored.bucket, "private")
            self.assertEqual(stored.key, key)
            self.assertEqual(stored.size_bytes, len(b"workbook-bytes"))
            self.assertEqual(stored.sha256, payload.sha256)
            self.assertEqual(payload.data, b"workbook-bytes")
            self.assertIn(key, store.list_keys(bucket="private", prefix="customers/customer_1"))

            with self.assertRaises(ObjectStorageError):
                store.upload_bytes(bucket="private", key=key, data=b"again")

    def test_local_object_store_is_blocked_in_production(self):
        with TemporaryDirectory() as tmpdir:
            with self.assertRaises(NonDurableObjectStoreError):
                LocalObjectStore(Path(tmpdir), environ={"TRACEREADY_ENV": "production"})

    def test_supabase_object_store_uses_bucket_api_and_records_metadata(self):
        client = FakeSupabaseClient()
        store = SupabaseObjectStore(
            supabase_url="https://example.supabase.co",
            service_role_key="service-role",
            client=client,
        )

        stored = store.upload_bytes(
            bucket="private",
            key="reports/audit report.json",
            data=b'{"ok":true}',
            content_type="application/json",
            upsert=True,
        )
        payload = store.download_bytes(bucket="private", key=stored.key)
        keys = store.list_keys(bucket="private", prefix="reports")
        bucket = client.storage.from_("private")

        self.assertEqual(stored.key, "reports/audit-report.json")
        self.assertEqual(stored.content_type, "application/json")
        self.assertEqual(payload.data, b'{"ok":true}')
        self.assertEqual(keys, ["reports/audit-report.json"])
        self.assertEqual(bucket.upload_calls[0][2]["upsert"], "true")

    def test_build_object_store_uses_local_only_for_explicit_test_mode(self):
        with TemporaryDirectory() as tmpdir:
            local_store = build_object_store(
                ServiceSettings(
                    environment=RuntimeEnvironment.TEST,
                    object_store_mode=ObjectStoreMode.LOCAL,
                    local_object_store_root=tmpdir,
                )
            )

            self.assertIsInstance(local_store, LocalObjectStore)

        with self.assertRaises(ObjectStorageError):
            build_object_store(ServiceSettings(environment=RuntimeEnvironment.PRODUCTION))

    def test_capture_payload_records_size_hash_and_content_type(self):
        payload = capture_payload(b"abc", "text/plain")

        self.assertEqual(payload.size_bytes, 3)
        self.assertEqual(payload.content_type, "text/plain")
        self.assertEqual(
            payload.sha256,
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )


if __name__ == "__main__":
    unittest.main()
