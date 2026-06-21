from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bellwether_backend.backend.services.normalized_evidence_service import (
    persist_normalized_customer_evidence,
)
from bellwether_backend.audit_engine.customer_evidence import build_phase10_customer_evidence


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


class FakeRepositories:
    def __init__(self):
        self.normalized_evidence = FakeNormalizedEvidenceRepository()


class NormalizedEvidenceServiceTest(unittest.TestCase):
    def test_persists_events_kdes_lineage_business_objects_and_review_items(self):
        with TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "records.csv"
            input_file.write_text(
                "Event ID,Event Type,Lot #,Product,Quantity,Ship Date,From Partner,To Partner\n"
                "SHIP-1,Shipping,LOT-1,Fresh salsa,10 cases,2026-06-01,Plant A,DC B\n"
                "RECV-1,Receiving,LOT-1,Fresh salsa,10 cases,2026-06-02,Plant A,DC B\n",
                encoding="utf-8",
            )
            package = build_phase10_customer_evidence(input_file=input_file)
            first_event = package.event_graph[0]
            package = package.model_copy(
                update={
                    "reviewer_questions": [
                        {
                            "eventId": first_event.event_id,
                            "question": "Confirm the event type from the customer source.",
                            "reason": "Test ambiguity routing.",
                            "severity": "medium",
                            "evidenceIds": first_event.evidence_ids,
                        }
                    ]
                }
            )
            repositories = FakeRepositories()

            result = persist_normalized_customer_evidence(
                audit_project_id="audit_1",
                audit_run_id="run_1",
                audit_file_id="file_1",
                package=package,
                repositories=repositories,
            )

            repo = repositories.normalized_evidence
            self.assertEqual(result.business_object_count, len(repo.business_objects))
            self.assertEqual(result.event_count, len(package.event_graph))
            self.assertEqual(result.kde_value_count, len(package.evidence_records))
            self.assertGreater(result.event_evidence_ref_count, 0)
            self.assertGreater(result.tlc_lineage_link_count, 0)
            self.assertGreater(result.review_item_count, 0)

            object_types = {item.object_type for item in repo.business_objects}
            self.assertIn("product", object_types)
            self.assertIn("lot", object_types)
            self.assertIn("document", object_types)

            event = repo.events[0]
            self.assertEqual(event.audit_project_id, "audit_1")
            self.assertEqual(event.audit_run_id, "run_1")
            self.assertEqual(event.audit_file_id, "file_1")
            self.assertIn(event.review_status, {"unreviewed", "needs_review"})
            self.assertIsInstance(event.classified_ctes_json, list)

            kde_keys = {item.kde_key for item in repo.kde_values}
            self.assertIn("traceability_lot_code", kde_keys)
            self.assertIn("quantity", kde_keys)

            self.assertTrue(all(item.normalized_event_id for item in repo.event_refs))
            self.assertTrue(any(item.source_tlc == "LOT-1" for item in repo.lineage_links))
            self.assertTrue(any(item.review_type == "reviewer_question" for item in repo.review_items))


if __name__ == "__main__":
    unittest.main()
