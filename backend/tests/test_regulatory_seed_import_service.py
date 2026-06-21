import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bellwether_backend.backend.services.regulatory_seed_import_service import import_regulatory_registry_seed
from bellwether_backend.storage.artifacts import LocalObjectStore


class FakeRegulatoryRepository:
    def __init__(self):
        self.sources = []
        self.chunks = []

    def upsert_source(self, source):
        self.sources.append(source)
        return {"id": source.id}

    def upsert_chunks(self, chunks):
        self.chunks.extend(chunks)
        return [{"id": chunk.id} for chunk in chunks]


class RegulatorySeedImportServiceTest(unittest.TestCase):
    def test_imports_registry_sources_chunks_and_artifacts(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            regulatory_dir = root / "data" / "regulatory"
            source_dir = regulatory_dir / "source_1"
            raw_dir = source_dir / "raw"
            normalized_dir = source_dir / "normalized"
            registry_dir = regulatory_dir / "registry"
            raw_dir.mkdir(parents=True)
            normalized_dir.mkdir(parents=True)
            registry_dir.mkdir(parents=True)
            (raw_dir / "source.pdf").write_bytes(b"raw")
            (normalized_dir / "source.json").write_text('{"sourceId":"source_1"}', encoding="utf-8")
            (registry_dir / "sources.json").write_text(
                json.dumps(
                    [
                        {
                            "source_id": "source_1",
                            "title": "Source One",
                            "url": "https://example.test/source",
                            "source_type": "fda_pdf",
                            "authority_rank": "guidance",
                            "source_status": "ingested",
                            "retrieved_at": "2026-06-16T00:00:00Z",
                            "raw_hash": "raw-hash",
                            "raw_artifact_path": "../data/regulatory/source_1/raw/source.pdf",
                            "normalized_artifact_path": "../data/regulatory/source_1/normalized/source.json",
                            "sections_extracted": 1,
                            "chunks_count": 1,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (registry_dir / "source-chunks.json").write_text(
                json.dumps(
                    [
                        {
                            "chunk_id": "chunk_1",
                            "source_id": "source_1",
                            "section_label": "Section",
                            "section_ref": "section",
                            "text": "Chunk text",
                            "text_hash": "chunk-hash",
                            "citation_anchor": "section",
                            "authority_rank": "guidance",
                            "source_url": "https://example.test/source",
                            "source_type": "fda_pdf",
                            "usage_role": "extraction",
                            "quality_flags": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            store = LocalObjectStore(root / "objects", environ={"BELLWETHER_ENV": "test"})
            repository = FakeRegulatoryRepository()

            result = import_regulatory_registry_seed(
                regulatory_dir=regulatory_dir,
                object_store=store,
                repository=repository,
                bucket="private",
            )

            self.assertEqual(result.source_count, 1)
            self.assertEqual(result.chunk_count, 1)
            self.assertEqual(repository.sources[0].raw_artifact_key, "regulatory/sources/source_1/versions/1/raw/source.pdf")
            self.assertEqual(repository.sources[0].normalized_artifact_key, "regulatory/sources/source_1/versions/1/normalized/source.json")
            self.assertEqual(repository.chunks[0].raw_artifact_key, repository.sources[0].raw_artifact_key)
            self.assertIn(
                "regulatory/sources/source_1/versions/1/chunks/source-chunks.json",
                store.list_keys(bucket="private", prefix="regulatory/sources/source_1"),
            )


if __name__ == "__main__":
    unittest.main()
