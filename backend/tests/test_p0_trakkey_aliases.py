"""P0 follow-up — the Trakkey / Sea Eagle real-export column variants map correctly
(learned from running issue #2 validation on Jim's workbook)."""

from bellwether_backend.audit_engine.customer_evidence import _suggest_field_key, resolve_food_form


def test_trakkey_column_aliases():
    cases = {
        "Product title": "product_name",
        "ProductTitle": "product_name",
        "FTL Group": "ftl_category",
        "LOT Number": "traceability_lot_code",
        "LOT Assigned": "traceability_lot_code",
        "Source Location ID": "from_partner_id",
        "Receiving date": "received_date",
        "Landing date": "event_datetime",
    }
    for header, expected in cases.items():
        field_key, _conf, _method = _suggest_field_key(header)
        assert field_key == expected, f"{header!r} -> {field_key!r}, expected {expected!r}"


def test_seafood_ftl_group_resolves_on():
    # "Crustaceans" (Sea Eagle's FTL Group) is on the Food Traceability List -> status "on".
    resolution = resolve_food_form(product_name="White Shrimp Head Off Tails 21/25", ftl_category="Crustaceans")
    assert resolution.ftl_status == "on"
    assert resolution.is_ftl_likely is True
