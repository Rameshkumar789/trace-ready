from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bellwether_backend.audit_engine.rule_execution import (
    build_phase11_rule_execution,
    write_phase11_rule_execution_artifacts,
)
from bellwether_backend.audit_engine.customer_evidence import (
    build_phase10_customer_evidence,
    write_phase10_customer_evidence_artifacts,
)
from bellwether_backend.audit_engine.cte_classification import (
    build_phase10c_cte_hardening,
    write_phase10c_cte_hardening_artifacts,
)
from bellwether_backend.audit_engine.field_mapping_governance import (
    build_phase10b_mapping_governance,
    write_phase10b_mapping_governance_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Phase 10 customer evidence normalization and CTE classification artifacts.")
    parser.add_argument("--input-file", default="../data/samples/fsma204-full-audit-sample.xlsx")
    parser.add_argument("--ftl-food-items-file", default="../data/regulatory/intelligence/drafts/ftl-food-items.json")
    parser.add_argument("--output-dir", default="../data/regulatory/intelligence/customer-evidence")
    parser.add_argument("--customer-id", default="pilot_customer")
    parser.add_argument("--source-system", default="sample_workbook")
    parser.add_argument("--approved-rule-package-file", default="../data/regulatory/intelligence/rules/approved-rule-package-v1.json")
    parser.add_argument(
        "--inbound-file",
        action="append",
        default=[],
        help="Supplier inbound document (X12 856 ASN, BOL PDF, or spreadsheet) to diff against the workbook (door-vs-database). Repeatable.",
    )
    parser.add_argument(
        "--previous-findings",
        default=None,
        help="Path to a previous run's phase11-audit-findings.json; emits a re-audit delta (what got fixed / what's new).",
    )
    args = parser.parse_args()

    package = build_phase10_customer_evidence(
        input_file=Path(args.input_file),
        ftl_food_items_file=Path(args.ftl_food_items_file),
    )
    phase10_outputs = write_phase10_customer_evidence_artifacts(package, Path(args.output_dir))
    phase10b = build_phase10b_mapping_governance(
        input_file=Path(args.input_file),
        customer_id=args.customer_id,
        source_system=args.source_system,
    )
    phase10b_outputs = write_phase10b_mapping_governance_artifacts(phase10b, Path(args.output_dir))
    phase10c = build_phase10c_cte_hardening(
        input_file=Path(args.input_file),
        ftl_food_items_file=Path(args.ftl_food_items_file),
    )
    phase10c_outputs = write_phase10c_cte_hardening_artifacts(phase10c, Path(args.output_dir))
    phase11 = build_phase11_rule_execution(
        input_file=Path(args.input_file),
        approved_rule_package_file=Path(args.approved_rule_package_file),
        ftl_food_items_file=Path(args.ftl_food_items_file),
        inbound_files=tuple(Path(f) for f in args.inbound_file),
    )
    phase11_outputs = write_phase11_rule_execution_artifacts(phase11, Path(args.output_dir))
    audit_delta = None
    if args.previous_findings:
        from bellwether_backend.audit_engine.audit_delta import diff_audit_findings

        previous = json.loads(Path(args.previous_findings).read_text(encoding="utf-8"))
        current = [finding.model_dump(mode="json") for finding in phase11.audit_findings]
        audit_delta = diff_audit_findings(previous, current)
        delta_path = Path(args.output_dir) / "phase11-audit-delta.json"
        delta_path.write_text(json.dumps(audit_delta, indent=1) + "\n", encoding="utf-8")
        phase11_outputs["auditDelta"] = str(delta_path)
    print(
        json.dumps(
            {
                "summary": package.summary,
                "phase10bSummary": phase10b.summary,
                "phase10cSummary": phase10c.summary,
                "phase11Summary": phase11.summary,
                "phase10Outputs": phase10_outputs,
                "phase10bOutputs": phase10b_outputs,
                "phase10cOutputs": phase10c_outputs,
                "phase11Outputs": phase11_outputs,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
