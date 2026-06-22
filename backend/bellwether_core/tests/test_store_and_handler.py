"""Core store + handler — persist an AuditResult and read it back (no DB needed)."""

from pathlib import Path

import pytest

from bellwether_core.domain import AuditResult, Citation, Finding
from bellwether_core.handler import get_audit, process_upload
from bellwether_core.store import InMemoryStore

ROOT = Path(__file__).resolve().parents[3]
RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
SAMPLE = ROOT / "data/samples/fsma204-full-audit-sample.xlsx"
FTL = ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json"


def test_store_roundtrip():
    store = InMemoryStore()
    store.create_run(run_id="r1", audit_project_id="p1", audit_file_id="f1", run_number=1, rule_package_id="rp1")
    result = AuditResult(
        findings=[Finding(id="x", severity="high", status="gap", finding_type="tlc_lineage",
                          title="Missing TLC", citation=Citation(section="21 CFR 1.1340"))],
        readiness_passed=False,
        summary={"findings": 1},
    )
    store.save_result(run_id="r1", result=result)

    run = store.get_run("r1")
    assert run["status"] == "succeeded" and run["readiness_passed"] is False
    findings = store.get_findings("r1")
    assert len(findings) == 1
    assert findings[0]["citation_section"] == "21 CFR 1.1340"
    assert findings[0]["audit_run_id"] == "r1"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample workbook not present")
def test_process_upload_end_to_end_in_memory():
    store = InMemoryStore()
    out = process_upload(
        store=store,
        data=SAMPLE.read_bytes(),
        file_name="sample.xlsx",
        audit_project_id="p1",
        rule_package_file=RULE_PACKAGE,
        ftl_food_items_file=FTL,
    )
    run_id = out["run_id"]
    assert out["summary"]["findings"] > 0

    fetched = get_audit(store=store, run_id=run_id)
    assert fetched is not None
    assert len(fetched["findings"]) == out["summary"]["findings"]
    assert fetched["scorecards"], "scorecards should be persisted on the run summary"
    assert get_audit(store=store, run_id="nope") is None
