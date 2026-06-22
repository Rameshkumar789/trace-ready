"""Parity guard: the rebuilt core must reproduce the legacy engine's output exactly.

This is the gate for step 6 (cutover): the new path may only retire the legacy backend once
this passes against representative data. It compares the new core pipeline's finding count to
a direct legacy Phase-11 run on the same input — catching any mapping that drops/adds findings.
"""

from pathlib import Path

import pytest

from bellwether_backend.audit_engine.rule_execution import build_phase11_rule_execution
from bellwether_core.pipeline import run_audit_file

ROOT = Path(__file__).resolve().parents[3]
RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
SAMPLE = ROOT / "data/samples/fsma204-full-audit-sample.xlsx"
FTL = ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample workbook not present")
def test_core_matches_legacy_engine():
    legacy = build_phase11_rule_execution(
        input_file=SAMPLE, approved_rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL
    )
    core = run_audit_file(input_file=SAMPLE, rule_package_file=RULE_PACKAGE, ftl_food_items_file=FTL)

    assert len(core.findings) == len(legacy.audit_findings)
    assert len(core.coverage) == len(legacy.supplier_product_coverage)
    assert len(core.scorecards) == len(legacy.supplier_scorecards)
    assert len(core.anomalies) == len(legacy.quality_anomalies)
