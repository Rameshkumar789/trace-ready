"""P5 (part 2) — flexibility-aware citations + 24-hr traceback fire-drill."""

from bellwether_backend.audit_engine.customer_evidence import (
    ActorRoleResolution,
    CustomerEventNode,
    FoodFormResolution,
)
from bellwether_backend.audit_engine.rule_execution import (
    resolve_flexible_citation,
    run_traceback_fire_drill,
)


def _event(event_id, *, lot=None, source=None, output=None, ctes=None):
    return CustomerEventNode(
        event_id=event_id,
        source_row_key=f"row::{event_id}",
        evidence_ids=[f"ev::{event_id}"],
        actor_role=ActorRoleResolution(role="operator", confidence=0.8),
        food_form=FoodFormResolution(confidence=0.5),
        lot_or_tlc=lot,
        source_lot_or_tlc=source,
        output_lot_or_tlc=output,
        classified_ctes=ctes or [],
    )


def test_flexible_citation_known_scenarios():
    waste = resolve_flexible_citation("shipping", scenario="food_waste_recovery")
    assert waste["effect"] == "out_of_scope_shipping" and "1.1305" in waste["section"]

    cheese = resolve_flexible_citation("receiving", scenario="cottage_cheese_ims")
    assert cheese["effect"] == "exempt"

    # Unknown/None scenario falls back to the base CTE section, marked required.
    base = resolve_flexible_citation("transformation")
    assert base["effect"] == "required" and base["section"] == "21 CFR 1.1350"


def test_fire_drill_passes_with_full_chain():
    events = {
        "R": _event("R", lot="LOT-1", ctes=["receiving"]),
        "S": _event("S", lot="LOT-1", ctes=["shipping"]),
    }
    result = run_traceback_fire_drill(events, "LOT-1")
    assert result.passed is True and result.completeness_score == 1.0
    assert result.one_up_linked and result.one_down_linked and result.event_count == 2


def test_fire_drill_flags_missing_one_down():
    events = {"R": _event("R", lot="LOT-1", ctes=["receiving"])}  # received but never shipped
    result = run_traceback_fire_drill(events, "LOT-1")
    assert result.passed is False
    assert result.one_up_linked is True and result.one_down_linked is False
    assert any("one-down" in m for m in result.missing_links)
    assert 0 < result.completeness_score < 1


def test_fire_drill_unknown_lot():
    result = run_traceback_fire_drill({}, "NOPE")
    assert result.passed is False and result.event_count == 0 and result.completeness_score == 0.0
