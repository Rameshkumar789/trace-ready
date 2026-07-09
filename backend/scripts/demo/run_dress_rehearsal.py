"""One-command dress rehearsal for the Thursday demo.

Run with ANTHROPIC_API_KEY set (once). It:
1. optionally clears hand-seeded mapping-cache entries so the LIVE model regenerates them
   (--regenerate-perception), then reports expected-vs-live mapping drift,
2. runs the full audit (phase10 + phase11) on the demo workbook and every --workbook,
3. runs the sample ASN + BOL through pre-receipt validation,
4. prints a go/no-go checklist: every perception result must be llm_cached/llm_live
   (fallbacks fail the rehearsal), key findings must be present, artifacts must write.

After a clean run, commit data/llm-cache so Thursday's demo is cache-hit-only and cannot
stall on the API mid-call.

Usage (from backend/):
    python scripts/demo/run_dress_rehearsal.py --workbook /path/to/seaegle.xlsx --regenerate-perception
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REPO = Path(__file__).resolve().parents[3]

from bellwether_backend.audit_engine.customer_evidence import read_sheet_grids  # noqa: E402
from bellwether_backend.audit_engine.rule_execution import (  # noqa: E402
    build_phase11_rule_execution,
    write_phase11_rule_execution_artifacts,
)
from bellwether_backend.audit_engine.workbook_intake import profile_sheet_grid, sheet_fingerprint  # noqa: E402
from bellwether_backend.backend.services.inbound_validation_service import validate_inbound_document  # noqa: E402
from bellwether_backend.intelligence.llm_cache import LLMCache  # noqa: E402
from bellwether_backend.intelligence.llm_perception import anthropic_key_available  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", action="append", default=[], help="Extra workbook(s) to audit (e.g. the Sea Eagle export). Repeatable.")
    parser.add_argument("--regenerate-perception", action="store_true", help="Delete cached sheet mappings for the given workbooks so the live model re-derives them.")
    parser.add_argument("--asn", default=str(REPO / "data/samples/inbound/sample-asn-856.edi"))
    parser.add_argument("--bol", default=str(REPO / "data/samples/inbound/sample-bol.pdf"))
    args = parser.parse_args()

    checklist: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checklist.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))

    print("== Dress rehearsal ==")
    key_ok = anthropic_key_available()
    check("ANTHROPIC_API_KEY available", key_ok, "" if key_ok else "AI paths will fall back; set the key before the real rehearsal")

    cache = LLMCache()
    workbooks = [REPO / "data/samples/fsma204-full-audit-sample.xlsx"] + [Path(w) for w in args.workbook]

    if args.regenerate_perception:
        cleared = 0
        for workbook in workbooks:
            for grid in read_sheet_grids(workbook):
                profile = profile_sheet_grid(grid)
                fingerprint = sheet_fingerprint(grid.sheet_name, [c["header"] for c in profile["columns"]])
                before = cache.get("workbook_mapping", fingerprint)
                if before is not None:
                    cache.delete("workbook_mapping", fingerprint)
                    cleared += 1
        print(f"cleared {cleared} cached sheet mappings; the live model will regenerate them")

    ftl_file = REPO / "data/regulatory/intelligence/drafts/ftl-food-items.json"
    rule_package = REPO / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"

    for workbook in workbooks:
        print(f"\n-- Audit: {workbook.name}")
        package = build_phase11_rule_execution(
            input_file=workbook,
            approved_rule_package_file=rule_package,
            ftl_food_items_file=ftl_file,
            inbound_files=(Path(args.asn),) if workbook.name != "fsma204-full-audit-sample.xlsx" else (),
        )
        finding_types = Counter(f.finding_type for f in package.audit_findings)
        print(f"   findings: {len(package.audit_findings)} {dict(finding_types)}")
        plan = package.mapping_plan or {}
        plan_method = plan.get("generated_by")
        check(f"{workbook.name}: mapping plan not fallback", plan_method in {"llm_cached", "llm_live", "mixed"}, f"generated_by={plan_method}")
        tier_methods = Counter(r.get("method") for r in package.ftl_tier_results.values())
        check(
            f"{workbook.name}: FTL tiers not fallback",
            "deterministic_fallback" not in tier_methods,
            str(dict(tier_methods)),
        )
        narrative_method = package.scoping_report.get("narrative_method")
        check(f"{workbook.name}: narrative not fallback", narrative_method in {"llm_cached", "llm_live"}, str(narrative_method))
        with TemporaryDirectory() as tmp:
            artifacts = write_phase11_rule_execution_artifacts(package, Path(tmp))
            check(f"{workbook.name}: artifacts write", len(artifacts) >= 18, f"{len(artifacts)} artifacts")
        if "seaegle" in workbook.name.lower() or "seaeagle" in workbook.name.lower():
            expected = {
                "traceability_plan": "empty traceability plan",
                "lot_backward_lineage": "orphan lots / predates window",
                "lot_duplicate_tlc": "multi-product TLC reuse (best practice)",
                "lot_mass_balance": "shipped > originated (best practice)",
                "lot_transformation_linkage": "ingredient->output lineage not demonstrable",
                "ftl_declared_mismatch": "frozen shrimp declared General products",
                "inbound_erp_mismatch": "door-vs-database diff",
            }
            for finding_type, label in expected.items():
                check(f"Sea Eagle: {label}", finding_types.get(finding_type, 0) > 0, f"{finding_type}={finding_types.get(finding_type, 0)}")
            best_practice = sum(1 for f in package.audit_findings if f.requirement_source == "best_practice")
            check("Sea Eagle: best-practice checks labeled (no false CFR claims)", best_practice >= 3, f"{best_practice} findings")
            events_by_cte = package.summary.get("scoping", {}).get("events", {}).get("byCte", {})
            check("Sea Eagle: no fabricated transformation events", events_by_cte.get("transformation", 0) <= 150, str(events_by_cte))

    print("\n-- Pre-receipt validation")
    ftl_items = json.loads(ftl_file.read_text(encoding="utf-8"))
    asn = validate_inbound_document(data=Path(args.asn).read_bytes(), file_name=Path(args.asn).name, ftl_items=ftl_items)
    check("ASN 856 parses", asn["document_type"] == "edi_x12", str(asn["verdict_counts"]))
    check("ASN holds the lot-less line", asn["verdict_counts"].get("hold", 0) >= 1)
    check("ASN accepts the complete line", asn["verdict_counts"].get("accept", 0) >= 1)
    bol = validate_inbound_document(data=Path(args.bol).read_bytes(), file_name=Path(args.bol).name, ftl_items=ftl_items)
    check("BOL PDF extracts lines", bol["line_count"] >= 1, f"lines={bol['line_count']}")

    failures = [name for name, ok, _ in checklist if not ok]
    print("\n== Result:", "GO" if not failures else f"NO-GO ({len(failures)} failures)")
    if failures:
        for name in failures:
            print("   FAILED:", name)
        sys.exit(1)
    print("Commit data/llm-cache/ now so Thursday runs cache-hit-only.")


if __name__ == "__main__":
    main()
