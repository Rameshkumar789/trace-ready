from __future__ import annotations

from pathlib import Path

from traceready_ingestion.intelligence.phase06_review_workflow import build_phase6_review_package


ROOT = Path(__file__).resolve().parents[2]


def test_phase6_review_package_separates_drafts_rejections_and_approvals() -> None:
    package = build_phase6_review_package(
        phase4_drafts_file=ROOT / "data/regulatory/intelligence/drafts/phase4-drafts.json",
        phase5_summary_file=ROOT / "data/regulatory/intelligence/phase5/phase5-real-extraction-summary.json",
        chunks_file=ROOT / "data/regulatory/registry/source-chunks.json",
    )

    assert package.summary["draftRecords"] == 550
    assert package.summary["readyForReview"] == 534
    assert package.summary["rejectedRecords"] == 16
    assert package.summary["approvedRecords"] == 0
    assert package.summary["citationCoverage"]["records"] == 550
    assert package.summary["citationCoverage"]["invalid"] == 11
    assert package.summary["citationCoverage"]["missing"] == 0
    assert package.summary["citationCoverage"]["partial"] == 0
    assert all(record.citation_valid for record in package.draft_records if record.review_status.value == "needs_review")


def test_phase6_does_not_auto_approve_ai_or_deterministic_drafts() -> None:
    package = build_phase6_review_package(
        phase4_drafts_file=ROOT / "data/regulatory/intelligence/drafts/phase4-drafts.json",
        phase5_summary_file=ROOT / "data/regulatory/intelligence/phase5/phase5-real-extraction-summary.json",
        chunks_file=ROOT / "data/regulatory/registry/source-chunks.json",
    )

    statuses = {record.review_status.value for record in package.draft_records}
    assert "approved" not in statuses
    assert statuses == {"needs_review", "rejected"}
    assert package.approved_records == []
    assert len(package.review_action_log) == 566
