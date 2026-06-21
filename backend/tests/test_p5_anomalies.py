"""P5 — data-quality / plausibility anomaly detection."""

from bellwether_backend.audit_engine.customer_evidence import (
    ActorRoleResolution,
    CustomerEventNode,
    FoodFormResolution,
)
from bellwether_backend.audit_engine.rule_execution import (
    _gs1_check_digit_valid,
    detect_data_quality_anomalies,
)


def _event(event_id, *, lot=None, product=None, ctes=None, dt=None, product_id=None):
    return CustomerEventNode(
        event_id=event_id,
        source_row_key=f"row::{event_id}",
        evidence_ids=[f"ev::{event_id}"],
        actor_role=ActorRoleResolution(role="operator", confidence=0.8),
        food_form=FoodFormResolution(confidence=0.5),
        lot_or_tlc=lot,
        product_name=product,
        product_id=product_id,
        event_datetime=dt,
        classified_ctes=ctes or [],
    )


def test_gs1_check_digit():
    assert _gs1_check_digit_valid("00012345678905") is True   # valid GTIN-14
    assert _gs1_check_digit_valid("00012345678901") is False  # wrong check digit
    assert _gs1_check_digit_valid("ABC") is False


def test_impossible_chronology_ship_before_receive():
    events = {
        "R": _event("R", lot="LOT-1", ctes=["receiving"], dt="2026-03-10T10:00:00Z"),
        "S": _event("S", lot="LOT-1", ctes=["shipping"], dt="2026-03-01T10:00:00Z"),
    }
    anomalies = detect_data_quality_anomalies(events)
    kinds = {a.anomaly_type for a in anomalies}
    assert "impossible_chronology" in kinds


def test_lot_reused_across_products_needs_review():
    events = {
        "E1": _event("E1", lot="LOT-9", product="Romaine"),
        "E2": _event("E2", lot="LOT-9", product="Cilantro"),
    }
    anomalies = detect_data_quality_anomalies(events)
    reuse = [a for a in anomalies if a.anomaly_type == "lot_code_reused_across_products"]
    assert len(reuse) == 1 and reuse[0].status == "needs_review"
    assert sorted(reuse[0].details["products"]) == ["Cilantro", "Romaine"]


def test_gs1_invalid_identifier_flagged():
    events = {"E1": _event("E1", lot="LOT-1", product="X", product_id="00012345678901")}
    anomalies = detect_data_quality_anomalies(events)
    assert any(a.anomaly_type == "gs1_check_digit_invalid" for a in anomalies)


def test_clean_data_no_anomalies():
    events = {
        "R": _event("R", lot="LOT-1", product="Romaine", ctes=["receiving"], dt="2026-03-01T10:00:00Z"),
        "S": _event("S", lot="LOT-1", product="Romaine", ctes=["shipping"], dt="2026-03-05T10:00:00Z"),
    }
    assert detect_data_quality_anomalies(events) == []
