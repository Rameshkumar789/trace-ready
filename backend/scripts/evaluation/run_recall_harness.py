"""Recall-first evaluation harness against the labeled gold set (accuracy roadmap WS5.2).

A missed gap (false pass) is the catastrophic error for a compliance auditor, so the gate
is RECALL on must-find expected findings; forbidden findings guard the worst false-positive
classes. Exit code 1 on any recall failure -> usable as a CI regression gate.

Usage (from backend/):
    python scripts/evaluation/run_recall_harness.py
    python scripts/evaluation/run_recall_harness.py --workbook-override seaegle=/path/to/SeaEgle.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REPO = Path(__file__).resolve().parents[3]
GOLD_DIR = REPO / "data" / "evaluation" / "gold"

from bellwether_backend.audit_engine.rule_execution import build_phase11_rule_execution  # noqa: E402


def evaluate_gold(gold: dict, workbook: Path) -> tuple[list[str], list[str], dict]:
    package = build_phase11_rule_execution(
        input_file=workbook,
        approved_rule_package_file=REPO / "data/regulatory/intelligence/rules/approved-rule-package-v1.json",
        ftl_food_items_file=REPO / "data/regulatory/intelligence/drafts/ftl-food-items.json",
    )
    findings = package.audit_findings
    type_counts = Counter(finding.finding_type for finding in findings)
    type_status_counts = Counter((finding.finding_type, finding.status) for finding in findings)

    failures: list[str] = []
    notes: list[str] = []

    hits = 0
    must_find = [e for e in gold.get("expected_findings", []) if e.get("must_find")]
    for expected in gold.get("expected_findings", []):
        finding_type = expected["finding_type"]
        needed = expected.get("min_count", 1)
        got = type_counts.get(finding_type, 0)
        ok = got >= needed
        if ok:
            hits += 1 if expected.get("must_find") else 0
            notes.append(f"found {finding_type} x{got} (needed {needed})")
        elif expected.get("must_find"):
            failures.append(f"MISSED (false pass): {finding_type} needed>={needed} got={got} - {expected.get('note', '')}")
        else:
            notes.append(f"optional {finding_type} not found (got {got})")

    for forbidden in gold.get("forbidden_findings", []):
        finding_type = forbidden["finding_type"]
        status = forbidden.get("status")
        got = type_status_counts.get((finding_type, status), 0) if status else type_counts.get(finding_type, 0)
        if got:
            failures.append(f"FORBIDDEN present: {finding_type} status={status} x{got} - {forbidden.get('note', '')}")

    expected_events = gold.get("expected_event_counts") or {}
    scoping_events = package.summary.get("scoping", {}).get("events", {})
    if expected_events.get("total") and scoping_events.get("total") != expected_events["total"]:
        failures.append(f"event count drift: expected {expected_events['total']}, got {scoping_events.get('total')}")
    for cte, count in (expected_events.get("byCte") or {}).items():
        if scoping_events.get("byCte", {}).get(cte) != count:
            failures.append(f"event drift for {cte}: expected {count}, got {scoping_events.get('byCte', {}).get(cte)}")

    recall = hits / len(must_find) if must_find else 1.0
    stats = {
        "recall_must_find": round(recall, 4),
        "must_find_total": len(must_find),
        "must_find_hit": hits,
        "findings_total": len(findings),
        "finding_types": dict(sorted(type_counts.items())),
    }
    return failures, notes, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workbook-override",
        action="append",
        default=[],
        help="name=path pairs mapping a gold file stem to a local workbook (for gold entries whose data isn't committed).",
    )
    args = parser.parse_args()
    overrides = dict(pair.split("=", 1) for pair in args.workbook_override)

    total_failures: list[str] = []
    for gold_file in sorted(GOLD_DIR.glob("*.gold.json")):
        gold = json.loads(gold_file.read_text(encoding="utf-8"))
        stem = gold_file.name.replace(".gold.json", "")
        workbook_ref = overrides.get(stem) or gold.get("workbook", "")
        workbook = (REPO / workbook_ref) if not str(workbook_ref).startswith("/") else Path(workbook_ref)
        print(f"== {stem}")
        if str(workbook_ref).startswith("<") or not workbook.exists():
            print(f"   SKIPPED: workbook not available ({workbook_ref}); pass --workbook-override {stem}=/path")
            continue
        failures, notes, stats = evaluate_gold(gold, workbook)
        print(f"   recall(must-find): {stats['recall_must_find']:.0%} ({stats['must_find_hit']}/{stats['must_find_total']}) | findings: {stats['findings_total']}")
        for failure in failures:
            print(f"   [FAIL] {failure}")
        total_failures.extend(f"{stem}: {failure}" for failure in failures)

    print("\n== Result:", "PASS" if not total_failures else f"FAIL ({len(total_failures)})")
    if total_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
