from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from traceready_backend.backend.services.source_artifact_integrity_service import check_source_artifact_integrity
from traceready_backend.storage.artifacts import LocalObjectStore, source_chunk_package_key, source_normalized_key, source_raw_key
from traceready_backend.versioning.hashing import sha256_bytes, sha256_text


class FakeIntegrityRepository:
    def __init__(self, sources, chunks):
        self.sources = sources
        self.chunks = chunks

    def list_sources_for_integrity(self, *, limit=None):
        return self.sources[:limit] if limit else self.sources

    def list_chunks_for_integrity(self, *, source_ids=None):
        if not source_ids:
            return self.chunks
        allowed = set(source_ids)
        return [chunk for chunk in self.chunks if chunk.get("regulatory_source_id") in allowed]


class SourceArtifactIntegrityServiceTest(unittest.TestCase):
    def test_passes_when_source_artifacts_hashes_and_citations_are_complete(self):
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"TRACEREADY_ENV": "test"})
            raw = b"<xml>source</xml>"
            normalized = b'{"text":"source"}'
            chunk_text = "Shipping KDEs are required."
            source_id = "source_1"
            raw_key = source_raw_key(source_id=source_id, version=1, filename="source.xml")
            normalized_key = source_normalized_key(source_id=source_id, version=1, filename="normalized.json")
            package_key = source_chunk_package_key(source_id=source_id, version=1)
            store.upload_bytes(bucket="private", key=raw_key, data=raw, upsert=True)
            store.upload_bytes(bucket="private", key=normalized_key, data=normalized, upsert=True)
            store.upload_bytes(
                bucket="private",
                key=package_key,
                data=json.dumps([{"chunk_id": "chunk_1"}]).encode("utf-8"),
                upsert=True,
            )
            repository = FakeIntegrityRepository(
                sources=[
                    {
                        "id": source_id,
                        "url": "https://example.test/source",
                        "text_hash": sha256_bytes(raw),
                        "raw_artifact_bucket": "private",
                        "raw_artifact_key": raw_key,
                        "normalized_artifact_bucket": "private",
                        "normalized_artifact_key": normalized_key,
                        "retrieved_at": datetime(2026, 6, 16, tzinfo=timezone.utc),
                    }
                ],
                chunks=[
                    {
                        "id": "chunk_1",
                        "regulatory_source_id": source_id,
                        "chunk_code": "chunk-code",
                        "text": chunk_text,
                        "text_hash": f"sha256:{sha256_text(chunk_text)}",
                        "citation": "21 CFR 1.1340",
                        "citation_anchor": "21 CFR 1.1340",
                    }
                ],
            )

            report = check_source_artifact_integrity(
                repository=repository,
                object_store=store,
                default_bucket="private",
            )

        self.assertEqual(report.status, "pass")
        self.assertEqual(report.summary["sourceCount"], 1)
        self.assertEqual(report.summary["chunkCount"], 1)
        self.assertEqual(report.issues, [])

    def test_fails_for_missing_artifacts_count_mismatch_and_bad_chunk_hash(self):
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"TRACEREADY_ENV": "test"})
            source_id = "source_1"
            raw_key = source_raw_key(source_id=source_id, version=1, filename="source.xml")
            normalized_key = source_normalized_key(source_id=source_id, version=1, filename="normalized.json")
            package_key = source_chunk_package_key(source_id=source_id, version=1)
            store.upload_bytes(bucket="private", key=raw_key, data=b"changed", upsert=True)
            store.upload_bytes(bucket="private", key=normalized_key, data=b"{}", upsert=True)
            store.upload_bytes(bucket="private", key=package_key, data=b"[]", upsert=True)
            repository = FakeIntegrityRepository(
                sources=[
                    {
                        "id": source_id,
                        "url": "https://example.test/source",
                        "text_hash": sha256_bytes(b"expected"),
                        "raw_artifact_bucket": "private",
                        "raw_artifact_key": raw_key,
                        "normalized_artifact_bucket": "private",
                        "normalized_artifact_key": normalized_key,
                    }
                ],
                chunks=[
                    {
                        "id": "chunk_1",
                        "regulatory_source_id": source_id,
                        "chunk_code": "chunk-code",
                        "text": "actual text",
                        "text_hash": f"sha256:{sha256_text('different text')}",
                        "citation": "",
                        "citation_anchor": "",
                    }
                ],
            )

            report = check_source_artifact_integrity(
                repository=repository,
                object_store=store,
                default_bucket="private",
            )

        codes = {issue.code for issue in report.issues}
        self.assertEqual(report.status, "fail")
        self.assertIn("raw_artifact_hash_mismatch", codes)
        self.assertIn("chunk_package_count_mismatch", codes)
        self.assertIn("chunk_missing_citation", codes)
        self.assertIn("chunk_missing_citation_anchor", codes)


if __name__ == "__main__":
    unittest.main()
