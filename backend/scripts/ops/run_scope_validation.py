#!/usr/bin/env python3
"""P0 — run the audit engine against a real dataset and print the *differentiated* outputs.

This is the "validate with Jim's Craig's data" harness (issue #2). Point it at any supported
input (XLSX / CSV / EDI .edi / EPCIS .xml) and it runs the full Phase-11 engine and surfaces
exactly the verification-depth results that distinguish this from a file-cleaner:

  - supplier x product coverage (P1)        - which suppliers/products to worry about
  - TLC link-integrity (P2)                  - retain/reassign, mass-balance
  - data-quality anomalies (P5)              - chronology, lot reuse, GS1 check digits
  - supplier scorecards (P4)                 - graded, citation-backed
  - traceback fire-drill (P5)                - one-up/one-down completeness for a lot

Usage:
  python3 scripts/ops/run_scope_validation.py --input data/samples/fsma204-full-audit-sample.xlsx
  python3 scripts/ops/run_scope_validation.py --input /path/to/craigs.xlsx --lot LOT-8841 --json out.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bellwether_backend.audit_engine.rule_execution import (
    build_phase11_rule_execution,
    run_traceback_fire_drill,
)
from bellwether_backend.audit_engine.customer_evidence import build_phase10_customer_evidence

ROOT = Path(__file__).resolve().parents[3]  # repo root (backend/scripts/ops/<file>)
DEFAULT_RULE_PACKAGE = ROOT / "data/regulatory/intelligence/rules/approved-rule-package-v1.json"
DEFAULT_FTL = ROOT / "data/regulatory/intelligence/drafts/ftl-food-items.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the audit engine and print differentiated findings.")
    parser.add_argument("--input", required=True, type=Path, help="Customer dataset (xlsx/csv/edi/xml)")
    parser.add_argument("--rule-package", type=Path, default=DEFAULT_RULE_PACKAGE)
    parser.add_argument("--ftl-items", type=Path, default=DEFAULT_FTL)
    parser.add_argument("--lot", type=str, default=None, help="Lot code to run the traceback fire-drill on")
    parser.add_argument("--json", type=Path, default=None, help="Optional path to write the full package JSON")
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"input file not found: {args.input}")

    pkg = build_phase11_rule_execution(
        input_file=args.input,
        approved_rule_package_file=args.rule_package,
        ftl_food_items_file=args.ftl_items if args.ftl_items.exists() else None,
    )

    def header(title: str) -> None:
        print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")

    header(f"SCOPE — supplier x product coverage  ({len(pkg.supplier_product_coverage)} cells)")
    for row in pkg.supplier_product_coverage[:40]:
        flag = {"gap": "⚠ GAP", "out_of_scope": "· off", "covered": "✓ ok"}.get(row.status, row.status)
        miss = f"  missing={row.missing_fields}" if row.missing_fields else ""
        tlc = "  TLC-BROKEN" if row.tlc_gap else ""
        print(f"  [{flag:6}] {row.supplier_id} / {row.product}  (ftl={row.ftl_status}, events={row.event_count}){tlc}{miss}")

    header(f"TLC LINK-INTEGRITY  ({len(pkg.tlc_integrity_checks)} issues)")
    for chk in pkg.tlc_integrity_checks:
        print(f"  [{chk.check_kind}] event={chk.event_id}: {chk.reason}  {chk.details}")
    if not pkg.tlc_integrity_checks:
        print("  (none)")

    header(f"DATA-QUALITY ANOMALIES  ({len(pkg.quality_anomalies)} found)")
    for anom in pkg.quality_anomalies:
        print(f"  [{anom.anomaly_type} · {anom.severity}/{anom.status}] {anom.reason}  {anom.details}")
    if not pkg.quality_anomalies:
        print("  (none)")

    header(f"SUPPLIER SCORECARDS  ({len(pkg.supplier_scorecards)} suppliers)")
    for card in pkg.supplier_scorecards:
        print(f"  {card.grade}  {card.supplier_id} ({card.supplier_name})  "
              f"gaps={card.products_with_gaps}/{card.in_scope_products}  tlc_gap={card.tlc_gap}")
        for action in card.recommended_actions[:6]:
            print(f"        → {action.action}  [{action.citation}]")

    if args.lot:
        header(f"TRACEBACK FIRE-DRILL — lot {args.lot}")
        phase10 = build_phase10_customer_evidence(
            input_file=args.input, ftl_food_items_file=args.ftl_items if args.ftl_items.exists() else None
        )
        events = {event.event_id: event for event in phase10.event_graph}
        result = run_traceback_fire_drill(events, args.lot)
        print(f"  passed={result.passed}  score={result.completeness_score}  "
              f"events={result.event_count}  one_up={result.one_up_linked}  one_down={result.one_down_linked}")
        for miss in result.missing_links:
            print(f"        missing: {miss}")

    header("SUMMARY")
    print(f"  findings={len(pkg.audit_findings)}  exceptions={len(pkg.exception_queue)}  "
          f"coverage_cells={len(pkg.supplier_product_coverage)}  integrity_issues={len(pkg.tlc_integrity_checks)}  "
          f"anomalies={len(pkg.quality_anomalies)}  scorecards={len(pkg.supplier_scorecards)}")

    if args.json:
        args.json.write_text(pkg.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nFull package written to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
