from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from traceready_ingestion.intelligence.phase13_release_gates import (
    build_phase13_release_gates,
    build_two_stage_classifier_package,
    load_approved_subparagraph_targets,
    marker_level,
    parse_cfr_subparagraph_blocks,
    write_phase13_release_gate_artifacts,
)


ROOT = Path(__file__).resolve().parents[2]
RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
SOURCE_CHUNKS = ROOT / "data/regulatory/registry/source-chunks.json"
SUBPARAGRAPH_TARGETS = ROOT / "data/regulatory/intelligence/rules/approved-subparagraph-targets-v1.json"
WEB500_RECORDS = ROOT / "data/regulatory/intelligence/generalization/phase12-web500-input-records.json"
WEB500_METRICS = ROOT / "data/regulatory/intelligence/generalization/phase12-web500-metrics.json"


class Phase13ReleaseGatesTest(unittest.TestCase):
    def test_paragraph_parser_builds_nested_cfr_anchors(self) -> None:
        blocks = parse_cfr_subparagraph_blocks(
            section_ref="21 CFR 1.1455",
            text="(c) Record availability. (3) When necessary. (ii) You must provide an electronic sortable spreadsheet.",
        )

        self.assertIn("21 CFR 1.1455(c)(3)(ii)", {block.anchor for block in blocks})
        self.assertEqual(marker_level("c"), 1)
        self.assertEqual(marker_level("3"), 2)
        self.assertEqual(marker_level("ii"), 3)

    def test_subparagraph_resolution_is_additive_and_resolves_known_problem_anchors(self) -> None:
        package = build_phase13_release_gates(
            approved_rule_package_file=RULE_PACKAGE,
            source_chunks_file=SOURCE_CHUNKS,
            approved_subparagraph_targets_file=SUBPARAGRAPH_TARGETS,
            web500_records_file=WEB500_RECORDS,
            web500_metrics_file=WEB500_METRICS,
        )
        by_obligation = {item.obligation_id: item for item in package.subparagraph_citations.resolutions}

        self.assertEqual(package.subparagraph_citations.summary["status"], "pass")
        self.assertFalse(package.subparagraph_citations.summary["sectionLevelCitationValidationWeakened"])
        self.assertTrue(by_obligation["FSMA204-OBL-DET-1325-HARVEST-COOLING-KDES"].section_level_remains_valid)
        self.assertIn("21 CFR 1.1325(a)", by_obligation["FSMA204-OBL-DET-1325-HARVEST-COOLING-KDES"].resolved_subparagraph_anchors)
        self.assertIn("21 CFR 1.1325(b)", by_obligation["FSMA204-OBL-DET-1325-HARVEST-COOLING-KDES"].resolved_subparagraph_anchors)
        self.assertIn("21 CFR 1.1455(c)(3)(ii)", by_obligation["FSMA204-OBL-DET-1455-SORTABLE-SPREADSHEET"].resolved_subparagraph_anchors)
        self.assertEqual(package.subparagraph_citations.summary["approvedTargetArtifact"], "approved-subparagraph-targets-v1")

    def test_subparagraph_targets_are_loaded_from_approved_artifact(self) -> None:
        package = load_approved_subparagraph_targets(SUBPARAGRAPH_TARGETS)
        by_obligation = {target.obligation_id: target for target in package.targets}

        self.assertEqual(package.status, "approved")
        self.assertIn("FSMA204-OBL-DET-1455-SORTABLE-SPREADSHEET", by_obligation)
        self.assertEqual(by_obligation["FSMA204-OBL-DET-1455-SORTABLE-SPREADSHEET"].target_anchors, ["21 CFR 1.1455(c)(3)(ii)"])

    def test_two_stage_classifier_reports_signal_families_and_web500_metrics(self) -> None:
        package = build_phase13_release_gates(
            approved_rule_package_file=RULE_PACKAGE,
            source_chunks_file=SOURCE_CHUNKS,
            approved_subparagraph_targets_file=SUBPARAGRAPH_TARGETS,
            web500_records_file=WEB500_RECORDS,
            web500_metrics_file=WEB500_METRICS,
        )
        summary = package.two_stage_classifier.summary

        self.assertEqual(summary["baseline"]["exact_match_rate"], 1.0)
        self.assertEqual(summary["minimum_independent_signal_families_for_auto_approval"], 2)
        self.assertIn("action_semantics", summary["signal_families"])
        self.assertIn("reference_document", summary["signal_families"])
        self.assertGreaterEqual(summary["auto_approved_precision"], 0.95)
        self.assertIn("review_routed_count", summary)
        self.assertIn("abstention_rate", summary)

    def test_artifact_writer_outputs_phase13_files(self) -> None:
        package = build_phase13_release_gates(
            approved_rule_package_file=RULE_PACKAGE,
            source_chunks_file=SOURCE_CHUNKS,
            approved_subparagraph_targets_file=SUBPARAGRAPH_TARGETS,
            web500_records_file=WEB500_RECORDS,
            web500_metrics_file=WEB500_METRICS,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs = write_phase13_release_gate_artifacts(package, Path(tmpdir))

            self.assertTrue(Path(outputs["summary"]).exists())
            self.assertTrue(Path(outputs["subparagraphCitations"]).exists())
            self.assertTrue(Path(outputs["twoStageClassifier"]).exists())


if __name__ == "__main__":
    unittest.main()
