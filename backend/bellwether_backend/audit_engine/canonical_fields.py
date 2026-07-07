"""Canonical field registry and sheet record-kind vocabulary for universal intake.

This is the ONLY vocabulary LLM perception may map customer data onto, and the ground truth
the deterministic verifier checks every LLM answer against. It is assembled from the field
aliases the engine already consumes plus the KDE-contract ``satisfied_by`` slugs, so a
verified mapping is guaranteed to feed the existing checks. Nothing in here is specific to
any customer template.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class CanonicalField:
    slug: str
    label: str
    description: str
    examples: tuple[str, ...] = ()


# Fields the engine reads today (from FIELD_ALIASES targets) plus additive slugs needed for
# real-world exports: locations with owners, source/destination location pairs, contact KDEs,
# CTE-specific dates and quantities, product commodity/variety, TLC assignment plan fields.
_EXPLICIT_FIELDS: tuple[CanonicalField, ...] = (
    CanonicalField("event_id", "Event ID", "Identifier of a traceability event", ("event id",)),
    CanonicalField("event_line_id", "Event line ID", "Identifier of a line item within an event", ("event line id",)),
    CanonicalField("event_type", "Event type", "Claimed CTE/event type (shipping, receiving, transformation...)", ("event type",)),
    CanonicalField("event_datetime", "Event date", "Date/time the event happened", ("event date",)),
    CanonicalField("date_you_shipped_the_food", "Ship date", "Shipping KDE: date you shipped the food", ("ship date", "shipping date")),
    CanonicalField("received_date", "Receive date", "Receiving KDE: date you received the food", ("receive date", "received date", "receiving date")),
    CanonicalField("landing_date", "Landing date", "First land-based receiver KDE: date the food was landed/offloaded", ("landing date",)),
    CanonicalField("transformation_date", "Transformation date", "Transformation KDE: date the new food was produced", ("transformation date", "production date")),
    CanonicalField("harvest_date", "Harvest date", "Harvesting KDE: date (or date range start) the food was harvested", ("harvesting date", "harvest date")),
    CanonicalField("cooling_date", "Cooling date", "Cooling KDE: date the food was cooled", ("cooling date",)),
    CanonicalField("packing_date", "Packing date", "Initial packing KDE: date the food was packed", ("packing date", "pack date")),
    CanonicalField("traceability_lot_code", "Traceability lot code", "The TLC / lot number identifying a lot of food", ("lot", "lot #", "lot number", "tlc", "lot assigned")),
    CanonicalField("source_lot_or_tlc", "Source/ingredient lot", "Lot code of an input/ingredient food (transformation input)", ("source lot", "ingredient lot")),
    CanonicalField("output_lot_or_tlc", "Output lot", "Lot code assigned to the newly produced food (transformation output)", ("output lot", "new lot")),
    CanonicalField("target_lot_or_tlc", "Target lot", "Lot code a lineage row points at", ("target lot",)),
    CanonicalField("tlc_source", "TLC source", "Where the traceability lot code was assigned / the TLC source reference", ("lot source", "tlc source")),
    CanonicalField("product_id", "Product ID", "Product identifier (SKU, GTIN, item code)", ("product id", "item number", "gtin")),
    CanonicalField("product_name", "Product name", "Product name/title/description", ("product", "product name", "item", "product title", "description of product")),
    CanonicalField("commodity", "Commodity", "Commodity of the food (e.g. shrimp, romaine)", ("commodity",)),
    CanonicalField("variety", "Variety", "Variety of the commodity", ("variety",)),
    CanonicalField("food_form", "Food form", "Form/state of the food (fresh, frozen, cooked...)", ("form", "food form")),
    CanonicalField("ftl_category", "FTL category", "Customer-declared Food Traceability List category/group for the product", ("ftl category", "ftl group")),
    CanonicalField("is_ftl_maybe", "Declared FTL flag", "Customer-declared yes/no flag whether the product is on the FTL", ("is ftl",)),
    CanonicalField("quantity", "Quantity", "Quantity of food in the event line", ("quantity", "qty")),
    CanonicalField("quantity_received", "Quantity received", "Quantity of food received/unpacked (when a row carries both received and packed quantities)", ("quantity received food", "quantity unpacked food")),
    CanonicalField("quantity_packed", "Quantity packed", "Quantity of food packed/produced (when a row carries both received and packed quantities)", ("quantity packed food",)),
    CanonicalField("unit", "Unit of measure", "Unit of measure for the quantity", ("unit", "uom", "measure unit")),
    CanonicalField("location_id", "Location ID", "Identifier of the location where the event happened / the master location", ("location_id", "gln")),
    CanonicalField("location_name", "Location name", "Name/description of the location", ("location_name", "location description")),
    CanonicalField("location_type", "Location type", "Type of the location (farm, dock, warehouse, store...)", ("location_type",)),
    CanonicalField("location_owner", "Location owner", "Business that owns/operates the location (master-data join key)", ("owner",)),
    CanonicalField("actor_location_id", "Actor location ID", "Location identifier of the party performing the event", ("actor_location_id",)),
    CanonicalField("source_location_id", "Source location ID", "Location the food came from / was shipped from", ("source location id", "ship from id", "origin location")),
    CanonicalField("source_location_name", "Source location name", "Name/description of the source (ship-from) location", ("source location description", "ship from")),
    CanonicalField("destination_location_id", "Destination location ID", "Location the food went to / immediate subsequent recipient location", ("destination location id", "ship to id")),
    CanonicalField("destination_location_name", "Destination location name", "Name/description of the destination (ship-to) location", ("destination location description", "ship to")),
    CanonicalField("coordinates", "Coordinates", "Geo coordinates of a location", ("coordinates", "lat/long")),
    CanonicalField("address", "Address", "Street address", ("address", "address line 1")),
    CanonicalField("city", "City", "City", ("city",)),
    CanonicalField("state", "State", "State/province", ("state",)),
    CanonicalField("zip_code", "ZIP", "Postal/ZIP code", ("zip", "zip code", "postal code")),
    CanonicalField("country", "Country", "Country", ("country",)),
    CanonicalField("partner_id", "Partner ID", "Identifier of a trading partner (counterparty)", ("partner_id",)),
    CanonicalField("partner_name", "Partner name", "Name of a trading partner", ("partner_name",)),
    CanonicalField("partner_type", "Partner type", "Type of the partner (supplier, customer, carrier...)", ("partner_type", "customer type")),
    CanonicalField("partner_relationship", "Partner relationship", "Relationship of the partner to the operator", ("relationship",)),
    CanonicalField("from_partner_id", "From partner", "Counterparty the food came from", ("from_partner_id",)),
    CanonicalField("to_partner_id", "To partner", "Counterparty the food went to (immediate subsequent recipient)", ("to_partner_id",)),
    CanonicalField("destination_type", "Destination type", "Destination category (business, consumer, retailer...)", ("destination", "destination type")),
    CanonicalField("business_id", "Business ID", "Identifier of a business entity", ("business_id",)),
    CanonicalField("business_type", "Business type", "Type of the business (internal/external, supplier/customer...)", ("business_type",)),
    CanonicalField("company_name", "Company name", "Name/title of a business entity", ("company_name", "business description", "title")),
    CanonicalField("contact_person", "Contact person", "Point-of-contact person name", ("contact person", "poc")),
    CanonicalField("phone_number", "Phone number", "Phone number (traceability plan point of contact or partner)", ("phone", "phone number")),
    CanonicalField("email", "Email", "Email address", ("email", "e-mail")),
    CanonicalField("handles_ftl_foods", "Handles FTL foods", "Whether the business handles FTL foods", ("handles_ftl_foods",)),
    CanonicalField("covered_entity_status", "Covered entity status", "FSMA 204 coverage status of the entity", ("covered_entity_status",)),
    CanonicalField("reference_record_type", "Reference document type", "Type of the source/reference document (BOL, PO, SO, invoice...)", ("reference_record_type", "ref. document type", "ref doc type")),
    CanonicalField("reference_record_no", "Reference document number", "Number of the source/reference document", ("reference_record_no", "ref. document number", "ref doc number")),
    CanonicalField("source_document_id", "Source document ID", "Identifier of an evidence/source document", ("evidence_id",)),
    CanonicalField("source_document_type", "Source document type", "Type of an evidence/source document", ("evidence_type",)),
    CanonicalField("source_document_status", "Source document status", "Status of an evidence/source document", ("evidence_status",)),
    CanonicalField("source_system", "Source system", "System of record the data came from (ERP, WMS...)", ("source system",)),
    CanonicalField("exemption_claim_id", "Exemption claim ID", "Identifier of an exemption claim", ("claim_id",)),
    CanonicalField("exemption_claim_type", "Exemption claim type", "Type of exemption claimed (small farm <$25k, RFE...)", ("claim_type", "exemption")),
    CanonicalField("exemption_claimed_by", "Exemption claimed by", "Party claiming the exemption", ("claimed_by",)),
    CanonicalField("exemption_evidence_provided", "Exemption evidence", "Whether evidence supports the exemption claim", ("evidence_provided",)),
    CanonicalField("traceability_plan_item", "Traceability plan item", "A traceability plan component/question", ("plan_item", "required records")),
    CanonicalField("traceability_plan_answer", "Traceability plan answer", "The customer's answer for a traceability plan component", ("answer",)),
    CanonicalField("tlc_assignment_method", "TLC assignment method", "Documented method for assigning traceability lot codes", ("method", "lot assignment method")),
    CanonicalField("tlc_assignment_format", "TLC assignment format", "Documented format/template for traceability lot codes", ("format", "lot format", "template title")),
    CanonicalField("transformation_role", "Transformation role", "Whether a transformation row is an input (ingredient) or output (produced food)", ()),
    CanonicalField("kde_id", "KDE ID", "Identifier of a KDE reference row", ("kde_id",)),
    CanonicalField("cte_type", "CTE type", "CTE a KDE reference row belongs to", ("cte_type",)),
    CanonicalField("kde_name", "KDE name", "Name of a KDE in a reference row", ("kde_name",)),
    CanonicalField("kde_field_key", "KDE field key", "Field key of a KDE reference row", ("field_key",)),
    CanonicalField("kde_value", "KDE value", "Value of a KDE reference row", ("kde_value",)),
    CanonicalField("lineage_id", "Lineage ID", "TLC lineage row identifier", ("lineage_id",)),
    CanonicalField("relationship_type", "Lineage relationship", "TLC lineage relationship type", ("relationship_type",)),
    CanonicalField("lineage_status", "Lineage status", "TLC lineage status", ("lineage_status",)),
)


def _alias_fields() -> dict[str, CanonicalField]:
    """Fields derived from the engine's existing header-alias table."""
    from bellwether_backend.audit_engine.customer_evidence import FIELD_ALIASES

    fields: dict[str, CanonicalField] = {}
    examples: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    for alias, (slug, label) in FIELD_ALIASES.items():
        labels.setdefault(slug, label)
        examples.setdefault(slug, [])
        if alias != slug:
            examples[slug].append(alias)
    for slug, label in labels.items():
        fields[slug] = CanonicalField(slug, label, label, tuple(examples[slug][:4]))
    return fields


def _contract_slugs() -> set[str]:
    """Every satisfied_by slug in the bundled KDE contracts must be mappable."""
    contracts_path = Path(__file__).resolve().parent / "bundled_rules" / "kde-check-contracts.json"
    try:
        payload = json.loads(contracts_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    slugs: set[str] = set()
    for contract in (payload.get("cte_contracts") or {}).values():
        for kde in contract.get("kdes", []):
            slugs.update(kde.get("satisfied_by", []))
    return slugs


@lru_cache(maxsize=1)
def canonical_field_registry() -> dict[str, CanonicalField]:
    registry: dict[str, CanonicalField] = dict(_alias_fields())
    for entry in _EXPLICIT_FIELDS:
        registry[entry.slug] = entry  # explicit entries win: richer descriptions
    for slug in _contract_slugs():
        registry.setdefault(slug, CanonicalField(slug, slug.replace("_", " ").title(), f"KDE contract field {slug}"))
    return registry


def is_canonical_slug(slug: str) -> bool:
    return slug in canonical_field_registry()


@lru_cache(maxsize=1)
def registry_alias_map() -> dict[str, str]:
    """Header-text -> slug lookup built from the registry's example headers, used by the
    deterministic fallback so 'landing date' / 'receiving date' style columns still map
    without the LLM. Conflicting examples (same text, two slugs) are dropped."""
    import re as _re

    def _key(value: str) -> str:
        return _re.sub(r"\s+", " ", value.strip().lower().replace("_", " "))

    mapping: dict[str, str] = {}
    conflicts: set[str] = set()
    for field in canonical_field_registry().values():
        for example in (*field.examples, field.label):
            key = _key(example)
            if not key or key in conflicts:
                continue
            if key in mapping and mapping[key] != field.slug:
                conflicts.add(key)
                mapping.pop(key, None)
                continue
            mapping[key] = field.slug
    return mapping


# ---------------------------------------------------------------------------
# Sheet/record kinds


RECORD_KIND_DESCRIPTIONS: dict[str, str] = {
    "cte_shipping": "Shipping events: food leaving the operator toward a customer/recipient",
    "cte_receiving": "Receiving events: food arriving from a trading partner",
    "cte_transformation_input": "Transformation ingredients: input lots consumed to make a new food",
    "cte_transformation_output": "Transformation outputs: newly produced foods with their new lots",
    "cte_first_land_based_receiving": "First land-based receiver events for seafood landed from fishing vessels",
    "cte_harvesting": "Harvesting events (farms: crop harvest records)",
    "cte_cooling": "Cooling events (pre initial-packing cooling records)",
    "cte_initial_packing": "Initial packing events (first packing of a raw agricultural commodity)",
    "master_products": "Product master data: the catalog of products/SKUs, not events",
    "master_locations": "Location master data: locations/facilities with addresses and owners, not events",
    "master_partners": "Trading partner master data: suppliers/customers directory, not events",
    "master_business": "Business master data: legal/business entities directory, not events",
    "traceability_plan": "Traceability plan: how records are kept, TLC assignment description, point of contact",
    "lot_assignment": "Lot code assignment reference: method/format/examples of how TLCs are assigned, not events",
    "exemption_claims": "Exemption claims: who claims which FSMA 204 exemption and evidence",
    "source_documents": "Source document register: evidence documents backing the records",
    "kde_reference": "KDE reference/values sheet: rows of key data elements keyed by event",
    "not_traceability": "Not traceability data (unrelated content, notes, marketing...)",
}

RECORD_KINDS: frozenset[str] = frozenset(RECORD_KIND_DESCRIPTIONS)

RECORD_KIND_TO_CTE: dict[str, str] = {
    "cte_shipping": "shipping",
    "cte_receiving": "receiving",
    "cte_transformation_input": "transformation",
    "cte_transformation_output": "transformation",
    "cte_first_land_based_receiving": "first land based receiving",
    "cte_harvesting": "harvesting",
    "cte_cooling": "cooling",
    "cte_initial_packing": "initial packing",
}

NON_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "master_products",
        "master_locations",
        "master_partners",
        "master_business",
        "traceability_plan",
        "lot_assignment",
        "exemption_claims",
        "source_documents",
        "kde_reference",
        "not_traceability",
    }
)

# Order in which per-row date slugs are promoted to event_datetime when a sheet has no
# explicit event date column. Sheet-kind specific first entries are added at plan time.
DEFAULT_DATE_SLUG_PRIORITY: tuple[str, ...] = (
    "event_datetime",
    "date_you_shipped_the_food",
    "received_date",
    "landing_date",
    "transformation_date",
    "harvest_date",
    "cooling_date",
    "packing_date",
)

QUANTITY_SLUG_PRIORITY: tuple[str, ...] = ("quantity", "quantity_packed", "quantity_received")
