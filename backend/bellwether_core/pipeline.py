"""Bellwether core — the one audit pipeline (ground-up rebuild).

A single, synchronous entry point: bytes (or a path) in → AuditResult out. It reuses the
*validated* deterministic engine (bellwether_backend.audit_engine) — the rule logic proven on
Jim's real Sea Eagle data — and maps its output into the clean core domain. No DB, no job
queue, no regulatory-pipeline coupling. DB persistence is a thin adapter layered on top
(separate module), so the core stays pure and unit-testable.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from bellwether_backend.audit_engine.rule_execution import build_phase11_rule_execution

from .domain import (
    Anomaly,
    AuditResult,
    Citation,
    CoverageCell,
    Finding,
    ScorecardAction,
    SupplierScorecard,
)

_SUFFIX_BY_TYPE = {"xlsx": ".xlsx", "csv": ".csv", "edi": ".edi", "epcis": ".xml", "gdsn": ".xml"}


def run_audit_file(
    *,
    input_file: Path,
    rule_package_file: Path,
    ftl_food_items_file: Path | None = None,
) -> AuditResult:
    """Run an audit on a file already on disk and return the clean result."""
    package = build_phase11_rule_execution(
        input_file=input_file,
        approved_rule_package_file=rule_package_file,
        ftl_food_items_file=ftl_food_items_file if ftl_food_items_file and ftl_food_items_file.exists() else None,
    )
    return _to_result(package)


def run_audit_bytes(
    *,
    data: bytes,
    file_name: str,
    rule_package_file: Path,
    ftl_food_items_file: Path | None = None,
) -> AuditResult:
    """Run an audit on raw uploaded bytes (the API/worker entry point)."""
    suffix = Path(file_name).suffix.lower() or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as handle:
        handle.write(data)
        handle.flush()
        return run_audit_file(
            input_file=Path(handle.name),
            rule_package_file=rule_package_file,
            ftl_food_items_file=ftl_food_items_file,
        )


def _to_result(package) -> AuditResult:
    findings = [
        Finding(
            id=f.finding_id,
            severity=f.severity,
            status=f.status,
            finding_type=f.finding_type,
            title=(f.message or f.finding_type)[:160],
            message=f.message,
            event_id=f.event_id,
            cte=f.cte,
            field_or_kde=(f.affected_fields[0] if f.affected_fields else None),
            citation=Citation(
                section=(f.source_citation or {}).get("section")
                or (f.source_citation or {}).get("section_ref")
                or (f.source_citation or {}).get("citation_anchor"),
                scenario=(f.source_citation or {}).get("scenario"),
                note=(f.source_citation or {}).get("note"),
            ),
            confidence=f.confidence,
            evidence_ids=list(f.customer_evidence_ids),
        )
        for f in package.audit_findings
    ]

    coverage = [
        CoverageCell(
            supplier_id=c.supplier_id,
            product=c.product,
            ftl_status=c.ftl_status,
            event_count=c.event_count,
            gap_count=c.gap_count,
            tlc_gap=c.tlc_gap,
            status=c.status,
        )
        for c in package.supplier_product_coverage
    ]

    scorecards = [
        SupplierScorecard(
            supplier_id=s.supplier_id,
            supplier_name=s.supplier_name,
            grade=s.grade,
            in_scope_products=s.in_scope_products,
            products_with_gaps=s.products_with_gaps,
            tlc_gap=s.tlc_gap,
            recommended_actions=[
                ScorecardAction(field_or_issue=a.field_or_issue, action=a.action, citation=a.citation)
                for a in s.recommended_actions
            ],
        )
        for s in package.supplier_scorecards
    ]

    anomalies = [
        Anomaly(
            anomaly_type=a.anomaly_type,
            severity=a.severity,
            status=a.status,
            reason=a.reason,
            details=a.details,
        )
        for a in package.quality_anomalies
    ]

    readiness_passed = str(package.export_package.status).lower() != "blocked"

    return AuditResult(
        findings=findings,
        coverage=coverage,
        scorecards=scorecards,
        anomalies=anomalies,
        readiness_passed=readiness_passed,
        summary={
            "findings": len(findings),
            "coverage_cells": len(coverage),
            "scorecards": len(scorecards),
            "anomalies": len(anomalies),
        },
    )
