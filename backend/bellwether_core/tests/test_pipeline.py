"""Core pipeline (rebuild) — file in -> clean AuditResult out, reusing the validated engine."""

from pathlib import Path

import pytest

from bellwether_core.domain import AuditResult
from bellwether_core.pipeline import run_audit_bytes, run_audit_file

ROOT = Path(__file__).resolve().parents[3]
RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
SAMPLE = ROOT / "data/samples/fsma204-full-audit-sample.xlsx"
FTL = ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample workbook not present")
def test_run_audit_file_produces_clean_result():
    result = run_audit_file(input_file=SAMPLE, rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)
    assert isinstance(result, AuditResult)
    # The sample has known gaps -> findings + coverage + scorecards must be produced.
    assert result.findings, "expected findings from the sample"
    assert result.coverage, "expected supplier x product coverage"
    assert result.scorecards, "expected supplier scorecards"
    # Findings carry citations (the wiring we added).
    assert any(f.citation.section for f in result.findings)
    assert result.summary["findings"] == len(result.findings)


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample workbook not present")
def test_run_audit_bytes_matches_file():
    data = SAMPLE.read_bytes()
    by_bytes = run_audit_bytes(data=data, file_name="sample.xlsx", rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)
    by_file = run_audit_file(input_file=SAMPLE, rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)
    assert len(by_bytes.findings) == len(by_file.findings)
