from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bellwether_backend.backend.repositories.supabase_tables import RegulatorySourceUpsert, SourceChunkUpsert
from bellwether_backend.backend.services.regulatory_source_artifact_service import (
    DraftPayloadArtifact,
    NamedArtifactPayload,
    RegulatorySourceArtifactRepositories,
    persist_regulatory_source_artifacts,
)
from bellwether_backend.storage.artifacts import LocalObjectStore


class FakeRegulatoryRepository:
    def __init__(self):
        self.sources = []
        self.chunks = []

    def upsert_source(self, source):
        self.sources.append(source)
        return {"id": source.id, "raw_artifact_key": source.raw_artifact_key}

    def upsert_chunks(self, chunks):
        self.chunks.extend(chunks)
        return [{"id": chunk.id, "raw_artifact_key": chunk.raw_artifact_key} for chunk in chunks]


class RegulatorySourceArtifactServiceTest(unittest.TestCase):
    def test_persists_source_artifacts_and_db_metadata(self):
        with TemporaryDirectory() as tmpdir:
            store = LocalObjectStore(Path(tmpdir), environ={"BELLWETHER_ENV": "test"})
            regulatory = FakeRegulatoryRepository()

            result = persist_regulatory_source_artifacts(
                source=RegulatorySourceUpsert(
                    id="source_1",
                    title="21 CFR Part 1 Subpart S",
                    source_type="ecfr",
                    source_status="active",
                    authority_rank="primary",
                    url="https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-S",
                    citation="21 CFR Part 1 Subpart S",
                    retrieved_at=datetime(2026, 6, 16, tzinfo=timezone.utc),
                    text_hash="source-hash",
                    is_finalized=True,
                ),
                source_version=1,
                chunks=[
                    SourceChunkUpsert(
                        id="chunk_1",
                        regulatory_source_id="source_1",
                        chunk_code="21-cfr-1-1345",
                        section_label="Receiving",
                        source_location="21 CFR 1.1345",
                        text="Receiving KDEs",
                        summary="Receiving",
                        citation="21 CFR 1.1345",
                        text_hash="chunk-hash",
                        status="approved_for_extraction",
                    )
                ],
                raw_artifact=NamedArtifactPayload(filename="subpart-s.xml", data=b"<xml />", content_type="application/xml"),
                normalized_artifact=NamedArtifactPayload(filename="normalized.json", data=b'{"ok":true}', content_type="application/json"),
                chunk_package=NamedArtifactPayload(filename="source-chunks.json", data=b"[]", content_type="application/json"),
                draft_payloads=[
                    DraftPayloadArtifact(draft_id="draft_1", filename="draft.json", data=b'{"draft":true}', content_type="application/json")
                ],
                approval_artifacts=[
                    NamedArtifactPayload(filename="approval-manifest.json", data=b'{"approved":true}', content_type="application/json")
                ],
                object_store=store,
                repositories=RegulatorySourceArtifactRepositories(regulatory),
                bucket="private",
            )

            self.assertEqual(result.raw.key, "regulatory/sources/source_1/versions/1/raw/subpart-s.xml")
            self.assertEqual(result.normalized.key, "regulatory/sources/source_1/versions/1/normalized/normalized.json")
            self.assertEqual(result.chunk_package.key, "regulatory/sources/source_1/versions/1/chunks/source-chunks.json")
            self.assertEqual(result.draft_payloads[0].key, "regulatory/sources/source_1/versions/1/drafts/draft_1/draft.json")
            self.assertEqual(result.approval_artifacts[0].key, "regulatory/sources/source_1/versions/1/approval/approval-manifest.json")
            self.assertEqual(regulatory.sources[0].raw_artifact_bucket, "private")
            self.assertEqual(regulatory.sources[0].normalized_artifact_key, result.normalized.key)
            self.assertEqual(regulatory.chunks[0].raw_artifact_key, result.raw.key)
            self.assertEqual(regulatory.chunks[0].normalized_artifact_key, result.normalized.key)


if __name__ == "__main__":
    unittest.main()
