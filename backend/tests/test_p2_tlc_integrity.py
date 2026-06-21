"""P2 — TLC link-integrity: retain/reassign correctness, lineage graph, UoM mass-balance."""

from bellwether_backend.audit_engine.customer_evidence import (
    ActorRoleResolution,
    CustomerEventNode,
    FoodFormResolution,
)
from bellwether_backend.audit_engine.rule_execution import (
    EventObligationMapping,
    build_lot_lineage_graph,
    check_tlc_integrity,
    check_uom_reconciliation,
)


def _event(event_id, *, cte, lot=None, source=None, output=None, quantity=None):
    return CustomerEventNode(
        event_id=event_id,
        source_row_key=f"row::{event_id}",
        evidence_ids=[f"ev::{event_id}"],
        actor_role=ActorRoleResolution(role="operator", confidence=0.8),
        food_form=FoodFormResolution(confidence=0.5),
        lot_or_tlc=lot,
        source_lot_or_tlc=source,
        output_lot_or_tlc=output,
        quantity=quantity,
    )


def _mapping(event_id, cte):
    return EventObligationMapping(
        mapping_id=f"m::{event_id}", event_id=event_id, cte=cte,
        approved_obligation_id="OBL-1", obligation_action="record",
        citation={"section": "21 CFR 1.1350"}, rule_package_id="rp", rule_package_version=1,
    )


def test_reassignment_violation_transform_reuses_source():
    events = {"E1": _event("E1", cte="transformation", source="LOT-1", output="LOT-1")}
    checks = check_tlc_integrity(mappings=[_mapping("E1", "transformation")], events=events)
    assert len(checks) == 1 and checks[0].check_kind == "reassignment" and checks[0].status == "gap"


def test_transform_with_new_output_is_clean():
    events = {"E1": _event("E1", cte="transformation", source="LOT-1", output="LOT-2")}
    checks = check_tlc_integrity(mappings=[_mapping("E1", "transformation")], events=events)
    assert checks == []


def test_retention_violation_shipping_changes_lot():
    events = {"E1": _event("E1", cte="shipping", lot="LOT-1", output="LOT-9")}
    checks = check_tlc_integrity(mappings=[_mapping("E1", "shipping")], events=events)
    assert len(checks) == 1 and checks[0].check_kind == "retention" and checks[0].status == "gap"


def test_lineage_graph_detects_commingling():
    events = {
        "E1": _event("E1", cte="transformation", source="IN-A", output="OUT-1"),
        "E2": _event("E2", cte="transformation", source="IN-B", output="OUT-1"),
    }
    graph = build_lot_lineage_graph(events)
    assert set(graph["out-1"]["sources"]) == {"in-a", "in-b"}  # commingling node: 2 inputs -> 1 output


def test_uom_reconciliation_flags_yield_over_100pct():
    events = {
        "IN": _event("IN", cte="receiving", lot="LOT-1", quantity="100 kg"),
        "OUT": _event("OUT", cte="transformation", source="LOT-1", output="LOT-2", quantity="150 kg"),
    }
    mappings = [_mapping("IN", "receiving"), _mapping("OUT", "transformation")]
    checks = check_uom_reconciliation(mappings=mappings, events=events)
    assert len(checks) == 1 and checks[0].check_kind == "uom_reconciliation"
    assert checks[0].details["input_qty"] == 100.0 and checks[0].details["output_qty"] == 150.0


def test_uom_reconciliation_ok_when_output_within_input():
    events = {
        "IN": _event("IN", cte="receiving", lot="LOT-1", quantity="100 kg"),
        "OUT": _event("OUT", cte="transformation", source="LOT-1", output="LOT-2", quantity="95 kg"),
    }
    mappings = [_mapping("IN", "receiving"), _mapping("OUT", "transformation")]
    assert check_uom_reconciliation(mappings=mappings, events=events) == []
