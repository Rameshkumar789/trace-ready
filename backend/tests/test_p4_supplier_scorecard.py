"""P4 — per-supplier citation-backed scorecard."""

from bellwether_backend.audit_engine.rule_execution import (
    SupplierProductCoverage,
    build_supplier_scorecards,
)


def _cov(supplier, product, *, status, ftl_status="on", missing=None, tlc_gap=False):
    return SupplierProductCoverage(
        supplier_id=supplier,
        supplier_name=f"{supplier} Inc",
        product=product,
        ftl_status=ftl_status,
        event_count=1,
        event_ids=["E"],
        missing_fields=missing or [],
        tlc_gap=tlc_gap,
        gap_count=len(missing or []),
        status=status,
    )


def test_scorecard_grades_and_actions():
    coverage = [
        # SUP-A: 2 in-scope, both gaps incl. TLC -> F, with citation-backed actions.
        _cov("SUP-A", "Romaine", status="gap", missing=["traceability_lot_code"], tlc_gap=True),
        _cov("SUP-A", "Basil", status="gap", missing=["event_datetime"]),
        # SUP-B: 1 in-scope, clean -> A.
        _cov("SUP-B", "Melon", status="covered"),
        # SUP-C: out-of-scope only -> A (not penalized).
        _cov("SUP-C", "Crackers", status="out_of_scope", ftl_status="off"),
    ]
    cards = {c.supplier_id: c for c in build_supplier_scorecards(coverage)}

    a = cards["SUP-A"]
    assert a.grade == "F" and a.tlc_gap is True and a.products_with_gaps == 2
    citations = {action.citation for action in a.recommended_actions}
    assert any("1.1340" in c for c in citations)  # TLC citation present
    assert any(action.field_or_issue == "tlc_lineage" for action in a.recommended_actions)

    assert cards["SUP-B"].grade == "A"
    assert cards["SUP-C"].grade == "A" and cards["SUP-C"].in_scope_products == 0

    # Worst-first ordering.
    assert build_supplier_scorecards(coverage)[0].supplier_id == "SUP-A"
