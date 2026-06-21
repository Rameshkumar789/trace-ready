import json
import unittest
from pathlib import Path

from bellwether_backend.intelligence.phase05_ai_assisted_extraction import (
    build_phase5_prompt_specs,
    render_prompt,
    validate_ai_records,
)
from bellwether_backend.intelligence.citations import load_chunk_index


ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = ROOT / "data/regulatory/registry/source-chunks.json"


class Phase5AIAssistedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
        cls.chunk_index = load_chunk_index(CHUNKS_PATH)
        cls.tlc_chunk = next(
            chunk
            for chunk in cls.chunk_index.values()
            if chunk.get("source_id") == "ecfr-21-cfr-1-subpart-s" and chunk.get("section_ref") == "21 CFR 1.1320"
        )

    def test_prompt_specs_are_schema_bound(self):
        specs = build_phase5_prompt_specs()

        self.assertEqual({spec.collection for spec in specs}, {"obligations", "exemption_rules", "tlc_rules"})
        for spec in specs:
            prompt = render_prompt(spec, self.chunks[:1])
            self.assertIn("Return a JSON array of records. No Markdown. No commentary.", prompt)
            self.assertIn('"properties"', prompt)
            self.assertIn("source_id", prompt)

    def test_rejects_unsupported_ai_claims(self):
        result = validate_ai_records(
            "obligations",
            [
                {
                    "obligation_id": "unsupported",
                    "subject": "You",
                    "condition": "when you do any of the following",
                    "action": "launch a blockchain satellite",
                    "object": "traceability lot code",
                    "required_output": "traceability lot code",
                    "deadline": None,
                    "exceptions": [],
                    "applies_to_ctes": ["initial_packing"],
                    "applies_to_food_scope": "foods on the Food Traceability List",
                    "noncompliance_risk": None,
                    "citations": [self._citation("You must assign a traceability lot code")],
                    "metadata": self._metadata(),
                }
            ],
            self.chunk_index,
        )

        self.assertEqual(len(result.accepted_records), 0)
        self.assertEqual(len(result.rejected_records), 1)
        self.assertTrue(any(issue.code == "unsupported_claim" for issue in result.issues))

    def test_detects_conflicting_tlc_rule_drafts(self):
        base = {
            "rule_kind": "assignment",
            "applies_to_ctes": ["initial_packing"],
            "applies_to_food_scope": "foods on the Food Traceability List",
            "preservation_rule": None,
            "source_reference_rule": None,
            "transformation_handling": None,
            "uniqueness_rule": None,
            "lineage_rule": None,
            "required_status": "conditional",
            "evidence_examples": [],
            "unresolved_questions": [],
            "citations": [self._citation("You must assign a traceability lot code")],
            "metadata": self._metadata(),
        }
        result = validate_ai_records(
            "tlc_rules",
            [
                {**base, "tlc_rule_id": "tlc_a", "assignment_rule": "Initially pack a raw agricultural commodity"},
                {**base, "tlc_rule_id": "tlc_b", "assignment_rule": "perform the first land-based receiving of a food"},
            ],
            self.chunk_index,
        )

        self.assertEqual(len(result.accepted_records), 0)
        self.assertEqual(len(result.conflict_records), 2)
        self.assertTrue(any(issue.code == "conflict_detected" for issue in result.issues))

    def _citation(self, support_text: str) -> dict:
        return {
            "source_id": self.tlc_chunk["source_id"],
            "chunk_id": self.tlc_chunk["chunk_id"],
            "citation_anchor": self.tlc_chunk["citation_anchor"],
            "authority_rank": self.tlc_chunk["authority_rank"],
            "source_url": self.tlc_chunk["source_url"],
            "section_ref": self.tlc_chunk["section_ref"],
            "page_number": self.tlc_chunk.get("page_number"),
            "support_text": support_text,
        }

    def _metadata(self) -> dict:
        return {
            "extraction_method": "ai_assisted",
            "confidence": "medium",
            "review_status": "draft",
            "reviewer_notes": [],
            "source_chunk_ids": [self.tlc_chunk["chunk_id"]],
        }


if __name__ == "__main__":
    unittest.main()
