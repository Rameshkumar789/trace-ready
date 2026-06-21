"""P1 — FTL three-tier status + supplier x product coverage matrix."""

from bellwether_backend.audit_engine.customer_evidence import (
    ActorRoleResolution,
    CustomerEventNode,
    FoodFormResolution,
    classify_ftl_status,
    resolve_food_form,
)
from bellwether_backend.audit_engine.rule_execution import (
    KdeCompletenessCheck,
    TlcLineageCheck,
    build_supplier_product_coverage,
)


def _event(event_id, *, supplier, product, ftl_status):
    return CustomerEventNode(
        event_id=event_id,
        source_row_key=f"row::{event_id}",
        evidence_ids=[f"ev::{event_id}"],
        actor_role=ActorRoleResolution(role="shipper", confidence=0.8),
        food_form=FoodFormResolution(confidence=0.5, ftl_status=ftl_status),
        product_name=product,
        from_partner_id=supplier,
    )


def test_classify_ftl_status_three_tiers():
    assert classify_ftl_status(is_ftl_likely=True, review_required=False) == "on"
    assert classify_ftl_status(is_ftl_likely=True, review_required=True) == "investigate"
    assert classify_ftl_status(is_ftl_likely=None, review_required=False) == "investigate"
    assert classify_ftl_status(is_ftl_likely=False, review_required=True) == "off"


def test_resolve_food_form_sets_status():
    # Claimed FTL category, fresh form -> clearly on the list.
    on = resolve_food_form(product_name="Roma tomatoes", ftl_category="vegetables")
    assert on.ftl_status == "on"
    # Canned -> a kill step may take the output off-list -> investigate, not silently off.
    canned = resolve_food_form(product_name="Tomatoes", ftl_category="vegetables", food_form="canned shelf stable")
    assert canned.ftl_status == "investigate"
    # No category, no library match, unknown product -> investigate (never a false "off").
    unknown = resolve_food_form(product_name="Mystery item")
    assert unknown.ftl_status == "investigate"


def test_supplier_product_coverage_flags_gaps_and_scope():
    events = {
        e.event_id: e
        for e in [
            _event("E1", supplier="SUP-A", product="Romaine", ftl_status="on"),
            _event("E2", supplier="SUP-A", product="Romaine", ftl_status="on"),
            _event("E3", supplier="SUP-B", product="Crackers", ftl_status="off"),
            _event("E4", supplier="SUP-C", product="Basil", ftl_status="on"),
        ]
    }
    kde_checks = [
        KdeCompletenessCheck(
            check_id="K1", event_id="E1", cte="shipping", field_key="traceability_lot_code",
            status="missing", expected_reason="required", approved_obligation_id="OBL-1",
        ),
    ]
    tlc_checks = [
        TlcLineageCheck(check_id="T1", event_id="E2", cte="shipping", status="gap", reason="no source link"),
    ]

    rows = build_supplier_product_coverage(events=events, kde_checks=kde_checks, tlc_checks=tlc_checks)
    by_key = {(r.supplier_id, r.product): r for r in rows}

    a = by_key[("SUP-A", "Romaine")]
    assert a.status == "gap" and a.tlc_gap is True
    assert "traceability_lot_code" in a.missing_fields and a.event_count == 2

    b = by_key[("SUP-B", "Crackers")]
    assert b.status == "out_of_scope" and b.ftl_status == "off"

    c = by_key[("SUP-C", "Basil")]
    assert c.status == "covered"

    # Worst-first ordering: the gap cell comes first.
    assert rows[0].status == "gap"
