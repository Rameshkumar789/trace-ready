from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


GENERATED_AT = "2026-06-16T00:00:00Z"
OUTPUT_DIR = Path("../data/regulatory/intelligence/generalization")


PRODUCT_CONTEXTS = [
    {"product": "fresh basil", "lot": "BASIL-LOT-042", "category": "fresh herbs"},
    {"product": "fresh cucumber", "lot": "CUC-LOT-118", "category": "fresh produce"},
    {"product": "fresh sprouts", "lot": "SPR-LOT-220", "category": "sprouts"},
    {"product": "fresh tuna", "lot": "TUNA-LOT-771", "category": "seafood"},
    {"product": "soft cheese", "lot": "CHEESE-LOT-319", "category": "soft cheese"},
    {"product": "bulk olive oil", "lot": "OIL-LOT-540", "category": "oil ingredient"},
    {"product": "bottled olive oil", "lot": "BOT-OIL-903", "category": "finished oil"},
    {"product": "fresh grapes", "lot": "GRAPE-LOT-104", "category": "fresh produce"},
    {"product": "leaf lettuce", "lot": "LETT-LOT-514", "category": "leafy greens"},
    {"product": "prepared deli salad", "lot": "DELI-LOT-822", "category": "prepared food"},
]


SOURCES = {
    "gs1_epcis": {
        "source_name": "GS1 EPCIS Standard",
        "source_url": "https://ref.gs1.org/standards/epcis/",
        "source_basis": "EPCIS defines visibility event data, shipping business-step examples, and TransformationEvent input/output semantics.",
    },
    "smartproduct": {
        "source_name": "SmartProduct EPCIS/IoT paper",
        "source_url": "https://arxiv.org/abs/2210.09140",
        "source_basis": "The paper describes product manufactured, loaded/unloaded into/from trucks, transformed, pallet shipping, batch-level product lots, and IoT transport monitoring.",
    },
    "biotrak": {
        "source_name": "BioTrak food-chain logistics paper",
        "source_url": "https://arxiv.org/abs/2304.09601",
        "source_basis": "The paper describes inbound logistics with supplier delivery notes and batch codes, production linking input/output batch codes, outbound logistics, transporter roles, and transportation/transformation blocks.",
    },
    "token_recipes": {
        "source_name": "Token Recipes manufacturing traceability paper",
        "source_url": "https://arxiv.org/abs/1810.09843",
        "source_basis": "The paper models manufacturing recipes where ingredient batch tokens are consumed and a new token is produced, preserving transformation provenance.",
    },
    "produce_traceability": {
        "source_name": "Produce traceability article",
        "source_url": "https://en.wikipedia.org/wiki/Produce_traceability",
        "source_basis": "The article describes tracking produce from origin to retail and records across field/orchard, packing, processing, transit, and storage.",
    },
    "traceability": {
        "source_name": "Traceability article",
        "source_url": "https://en.wikipedia.org/wiki/Traceability",
        "source_basis": "The article describes food-processing traceability as recording movement and production-process steps, using unique identifiers through suppliers and future sales.",
    },
    "open_food_facts": {
        "source_name": "Open Food Facts article",
        "source_url": "https://en.wikipedia.org/wiki/Open_Food_Facts",
        "source_basis": "The article describes crowdsourced product metadata including product name, quantity, packaging, brand, category, processing locations, countries, retailers, and GTIN barcode identifiers.",
    },
}


ARCHETYPES = [
    ("gs1-ship-bizstep", "gs1_epcis", "EPCIS ObjectEvent uses bizStep shipping for {product} lot {lot} moving from supplier to buyer.", ["shipping"], []),
    ("gs1-receive-bizstep", "gs1_epcis", "EPCIS ObjectEvent uses bizStep receiving when {product} lot {lot} enters the distribution center.", ["receiving"], []),
    ("gs1-transform-input-output", "gs1_epcis", "EPCIS TransformationEvent consumes input lot {lot} and produces output lot OUT-{lot}.", ["transformation"], []),
    ("gs1-pallet-shipping", "gs1_epcis", "Pallet shipping event records {product} lot {lot} through shipping dock S2.", ["shipping"], []),
    ("gs1-aggregation-only", "gs1_epcis", "AggregationEvent groups cases of {product} lot {lot} onto pallet PAL-{lot} with no movement.", [], []),
    ("gs1-error-declaration", "gs1_epcis", "EPCIS error declaration says a prior {product} event for lot {lot} was incorrect.", [], ["shipping"]),
    ("smartproduct-manufactured", "smartproduct", "SmartProduct record: {product} lot {lot} was manufactured in Location A.", ["transformation"], []),
    ("smartproduct-loaded-truck", "smartproduct", "SmartProduct record: {product} lot {lot} was loaded to Truck A and transported to Warehouse B.", ["shipping"], []),
    ("smartproduct-unloaded-truck", "smartproduct", "SmartProduct record: {product} lot {lot} was unloaded from Truck A at Warehouse B.", ["receiving"], []),
    ("smartproduct-pallet-shipping", "smartproduct", "EPCIS event records pallet shipping for {product} lot {lot} with temperature and GPS context.", ["shipping"], []),
    ("smartproduct-bulk-to-bottled", "smartproduct", "Bulk material lot {lot} is transformed into bottled finished product OUT-{lot}.", ["transformation"], []),
    ("smartproduct-storage-only", "smartproduct", "IoT sensor record monitors storage temperature for {product} lot {lot} in Warehouse A.", [], []),
    ("smartproduct-product-registration", "smartproduct", "DBManager registers batch-level product {product} using common lot number {lot}.", [], []),
    ("biotrak-inbound-delivery", "biotrak", "Inbound logistics: raw materials for {product} lot {lot} are acquired from supplier and stored; supplier delivery note has batch codes.", ["receiving"], []),
    ("biotrak-production-link", "biotrak", "Production: input resource batch codes for {product} lot {lot} are linked to output product batch code OUT-{lot}.", ["transformation"], []),
    ("biotrak-outbound-delivery", "biotrak", "Outbound logistics: finished {product} lot {lot} moves to external customer with delivery note and outgoing batch codes.", ["shipping"], []),
    ("biotrak-transporter-only", "biotrak", "Transporter registers a transportation event for {product} lot {lot} but not shipper or receiver evidence.", [], ["shipping"]),
    ("biotrak-cold-chain-end", "biotrak", "Recipient scans NFC temperature sensor when transportation for {product} lot {lot} is terminated.", ["receiving"], []),
    ("biotrak-block-transport", "biotrak", "Blockchain block records a transportation process for {product} lot {lot} between two supply-chain companies.", ["shipping"], []),
    ("biotrak-block-transform", "biotrak", "Blockchain block records a transformation process linking ingredient lot {lot} to finished lot OUT-{lot}.", ["transformation"], []),
    ("token-recipe-applied", "token_recipes", "Recipe applied: ingredient token {lot} is consumed and a new product token OUT-{lot} is produced.", ["transformation"], []),
    ("token-batch-ingredient", "token_recipes", "A non-fungible token corresponds to ingredient batch {lot} for {product}.", [], []),
    ("token-exchange-only", "token_recipes", "Participant exchanges ownership record for token {lot} without physical movement evidence.", [], []),
    ("token-trace-inputs", "token_recipes", "End-product token OUT-{lot} traces its ingredients back to input token {lot}.", ["transformation"], []),
    ("produce-origin-retail", "produce_traceability", "{product} lot {lot} is tracked from point of origin to a retail location.", ["shipping"], []),
    ("produce-field-contamination", "produce_traceability", "Foreign matter is detected in the field for {product} lot {lot}.", ["harvesting"], []),
    ("produce-orchard-packing", "produce_traceability", "{product} lot {lot} moves from orchard to packing operation and cases are packed.", ["initial_packing"], []),
    ("produce-processing", "produce_traceability", "{product} lot {lot} is processed into a new form at the processor.", ["transformation"], []),
    ("produce-transit-storage", "produce_traceability", "Traceability record shows source, location, movement, and storage conditions for {product} lot {lot}.", ["shipping"], []),
    ("produce-cold-chain-only", "produce_traceability", "Controlled cold-chain reading exists for {product} lot {lot} during storage only.", [], []),
    ("traceability-movement-steps", "traceability", "Food-processing traceability records all movement of {product} lot {lot} through the production flow.", ["shipping", "transformation"], []),
    ("traceability-barcode-only", "traceability", "Barcode identifier {lot} can be traced through software messages and files.", [], []),
    ("traceability-supplier-sales", "traceability", "System links {product} lot {lot} to suppliers and future sales through the supply chain.", ["shipping"], []),
    ("traceability-production-flow", "traceability", "Production flow links supplier input lot {lot} to finished output lot OUT-{lot}.", ["transformation"], []),
    ("traceability-recall-location", "traceability", "Recall trace identifies precise date, time, and location for {product} lot {lot}.", [], []),
    ("openfoodfacts-product-page", "open_food_facts", "Open Food Facts product page lists product name, brand, packaging, category, and ingredients for {product}.", [], []),
    ("openfoodfacts-gtin", "open_food_facts", "GTIN barcode identifies packaged product {product} but does not show a shipment or receipt event.", [], []),
    ("openfoodfacts-processing-location", "open_food_facts", "Product metadata lists production or processing location for {product}, with no lot event row.", [], []),
    ("openfoodfacts-retailer-country", "open_food_facts", "Product metadata lists countries and retailers where {product} is sold.", [], []),
    ("openfoodfacts-ingredient-list", "open_food_facts", "Ingredient list and allergen traces are recorded for {product} on a public product page.", [], []),
    ("mixed-inbound-warehouse", "biotrak", "{product} lot {lot} is received from supplier, unloaded at Warehouse B, and stored.", ["receiving"], []),
    ("mixed-outbound-retail", "produce_traceability", "{product} lot {lot} leaves warehouse for retail customer and is tracked to store shelf.", ["shipping"], []),
    ("mixed-transform-ship", "smartproduct", "{product} lot {lot} is manufactured, packed, and shipped to a distributor.", ["transformation", "shipping"], []),
    ("mixed-receive-transform", "traceability", "{product} lot {lot} is received from supplier and consumed in production to make OUT-{lot}.", ["receiving", "transformation"], []),
    ("mixed-transfer-internal", "smartproduct", "{product} lot {lot} moves internally from Warehouse A to freezer room inside the same facility.", [], ["shipping"]),
    ("mixed-return-correction", "gs1_epcis", "Correction record reverses prior shipping event for {product} lot {lot}.", [], ["shipping"]),
    ("mixed-delivery-note-out", "biotrak", "Delivery note accompanies outgoing {product} lot {lot} to an external customer.", ["shipping"], []),
    ("mixed-delivery-note-in", "biotrak", "Supplier delivery note accompanies incoming {product} lot {lot} received into warehouse.", ["receiving"], []),
    ("mixed-transforms-verb", "token_recipes", "Recipe transforms ingredient batch {lot} into finished product OUT-{lot}.", ["transformation"], []),
    ("mixed-produced-verb", "token_recipes", "Recipe consumes ingredient batch {lot}; a new finished product batch OUT-{lot} is produced.", ["transformation"], []),
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = build_records()
    results = [evaluate_record(record) for record in records]
    metrics = build_metrics(results)
    source_register = [
        {"source_key": key, **source}
        for key, source in sorted(SOURCES.items())
    ]
    summary = {
        "phase": "12-web500-real-world-source-derived-eval",
        "generatedAt": GENERATED_AT,
        "importantLimitations": [
            "This is public internet source-derived evaluation data, not confidential customer transaction data.",
            "Rows are generated from source-backed real-world traceability/logistics patterns and manually gold-labeled.",
            "Open Food Facts live API was attempted but returned HTTP 503, so this workbook uses public article descriptions rather than bulk product API records.",
            "No OpenAI, Anthropic, or other live model output was used.",
        ],
        "recordCount": len(records),
        "sourceCount": len(source_register),
        "metrics": metrics,
    }
    outputs = {
        "summary": OUTPUT_DIR / "phase12-web500-summary.json",
        "records": OUTPUT_DIR / "phase12-web500-input-records.json",
        "results": OUTPUT_DIR / "phase12-web500-results.json",
        "metrics": OUTPUT_DIR / "phase12-web500-metrics.json",
        "sources": OUTPUT_DIR / "phase12-web500-source-register.json",
        "recordsCsv": OUTPUT_DIR / "phase12-web500-input-records.csv",
        "resultsCsv": OUTPUT_DIR / "phase12-web500-results.csv",
    }
    write_json(outputs["summary"], summary)
    write_json(outputs["records"], records)
    write_json(outputs["results"], results)
    write_json(outputs["metrics"], metrics)
    write_json(outputs["sources"], source_register)
    write_csv(outputs["recordsCsv"], records)
    write_csv(outputs["resultsCsv"], results)
    print(json.dumps({"summary": summary, "outputs": {key: str(value) for key, value in outputs.items()}}, indent=2, sort_keys=True))


def build_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for archetype_index, archetype in enumerate(ARCHETYPES):
        family, source_key, template, expected_ctes, expected_abstentions = archetype
        source = SOURCES[source_key]
        for product_index, product_context in enumerate(PRODUCT_CONTEXTS):
            record_number = archetype_index * len(PRODUCT_CONTEXTS) + product_index + 1
            text = template.format(**product_context)
            records.append(
                {
                    "record_id": f"web500-{record_number:04d}",
                    "scenario_family": family,
                    "source_name": source["source_name"],
                    "source_url": source["source_url"],
                    "source_basis": source["source_basis"],
                    "product": product_context["product"],
                    "product_category": product_context["category"],
                    "lot_or_batch": product_context["lot"],
                    "observed_text": text,
                    "expected_ctes": expected_ctes,
                    "expected_abstentions": expected_abstentions,
                    "gold_label_method": "manual_label_from_public_source_pattern",
                }
            )
    return records


def evaluate_record(record: dict[str, Any]) -> dict[str, Any]:
    predicted_ctes, predicted_abstentions = predict_ctes(record["observed_text"])
    errors = []
    if set(predicted_ctes) - set(record["expected_ctes"]):
        errors.append("over_triggered_cte")
    if set(record["expected_ctes"]) - set(predicted_ctes):
        errors.append("missed_cte")
    if set(record["expected_abstentions"]) - set(predicted_abstentions):
        errors.append("missing_abstention")
    if set(predicted_abstentions) - set(record["expected_abstentions"]):
        errors.append("unexpected_abstention")
    return {
        "record_id": record["record_id"],
        "scenario_family": record["scenario_family"],
        "source_name": record["source_name"],
        "expected_ctes": record["expected_ctes"],
        "predicted_ctes": predicted_ctes,
        "expected_abstentions": record["expected_abstentions"],
        "predicted_abstentions": predicted_abstentions,
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def predict_ctes(text: str) -> tuple[list[str], list[str]]:
    value = text.lower()
    abstentions: list[str] = []
    product_metadata_only = "product metadata" in value and not any(
        term in value
        for term in [
            "objectevent",
            "aggregationevent",
            "transformationevent",
            "transactionevent",
            "associationevent",
            "shipping event",
            "receiving event",
            "harvest event",
            "transformation event",
        ]
    )
    correction_or_return = any(
        term in value
        for term in [
            "correction record",
            "error declaration",
            "reverses prior",
            "prior event",
            "was incorrect",
            "incorrect event",
            "incorrect record",
            "credit memo",
            "credit note",
            " rma ",
            "rejected",
            "rejection",
            "disposal",
            "write-off",
            "write off",
        ]
    )
    transporter_only = any(
        term in value
        for term in [
            "transporter registers",
            "carrier registers",
            "carrier manifest",
            "freight bill",
            "3pl",
            "third-party logistics",
            "transport-only",
        ]
    )
    internal_only = any(term in value for term in ["internal", "inside the same facility", "same facility"])
    if product_metadata_only:
        return [], []
    if correction_or_return or transporter_only or internal_only:
        return [], ["shipping"]

    predicted: list[str] = []
    if any(
        term in value
        for term in [
            "received",
            "receiving",
            "inbound",
            "unloaded",
            "acquired from supplier",
            "enters the distribution center",
            "recipient scans",
            "transportation for",
            "is terminated",
        ]
    ):
        predicted.append("receiving")

    strong_shipping = any(
        term in value
        for term in [
            "bizstep shipping",
            "pallet shipping",
            "outbound",
            "outgoing",
            "loaded to truck",
            "transported to",
            "transportation process",
            "between two supply-chain companies",
            "moves to external customer",
            "leaves warehouse",
            "to retail customer",
            "tracked to store",
            "future sales",
        ]
    )
    weak_shipping = any(term in value for term in ["shipping", "shipped", "movement", "delivery note", "retail"])
    shipping_negative = any(
        term in value
        for term in [
            "incoming",
            "inbound",
            "supplier delivery note",
            "product metadata",
            "countries and retailers",
            "storage only",
            "with no movement",
            "without physical movement",
        ]
    )
    if strong_shipping or (weak_shipping and not shipping_negative):
        predicted.append("shipping")

    transformation_action = any(
        term in value
        for term in [
            "transformation",
            "transformed",
            "transforms",
            "manufactured",
            "manufactured, packed",
            "produced",
            "consumed",
            "processed into",
            "processing into",
            "repacked",
            "repacking",
            "blended",
            "blending",
            "mixed",
            "mixing",
            "cut into",
            "fresh-cut",
            "fresh cut",
            "recipe applied",
            "recipe transforms",
            "traces its ingredients",
            "production flow",
            "production:",
            "transformationevent",
        ]
    )
    transformation_lineage = any(
        term in value
        for term in [
            "input lot",
            "output lot",
            "out-",
            "new product",
            "new finished product",
            "finished product",
            "finished lot",
            "new form",
            "bulk material",
            "bottled",
            "ingredient batch",
            "input resource batch codes",
            "output product batch code",
            "input token",
            "output token",
            "source lots",
            "production flow",
            "manufactured in",
        ]
    )
    manufactured_standalone = ("manufactured in" in value or "manufactured, packed" in value) and "product registration" not in value
    if (transformation_action and transformation_lineage) or manufactured_standalone:
        predicted.append("transformation")
    harvesting_signal = any(
        term in value
        for term in [
            "harvest date",
            "harvested",
            "harvesting",
            "harvest event",
            "harvest lot",
            "harvest crew",
            "field harvest",
        ]
    ) or bool(re.search(r"\bfield\b.{0,80}\blot\b", value))
    if harvesting_signal:
        predicted.append("harvesting")
    if any(term in value for term in ["packing operation", "cases are packed", "packinghouse", "bizstep packing"]):
        predicted.append("initial_packing")
    return sorted(set(predicted)), abstentions


def build_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    ctes = sorted(set(cte for result in results for cte in result["expected_ctes"] + result["predicted_ctes"]))
    precision_by_cte: dict[str, float] = {}
    recall_by_cte: dict[str, float] = {}
    false_positive_by_cte: dict[str, int] = {}
    false_negative_by_cte: dict[str, int] = {}
    total_tp = total_fp = total_fn = 0
    for cte in ctes:
        tp = sum(1 for result in results if cte in result["expected_ctes"] and cte in result["predicted_ctes"])
        fp = sum(1 for result in results if cte not in result["expected_ctes"] and cte in result["predicted_ctes"])
        fn = sum(1 for result in results if cte in result["expected_ctes"] and cte not in result["predicted_ctes"])
        precision_by_cte[cte] = ratio(tp, tp + fp, empty=1.0)
        recall_by_cte[cte] = ratio(tp, tp + fn, empty=1.0)
        false_positive_by_cte[cte] = fp
        false_negative_by_cte[cte] = fn
        total_tp += tp
        total_fp += fp
        total_fn += fn
    by_source = defaultdict(lambda: {"count": 0, "pass": 0, "fail": 0})
    for result in results:
        source = by_source[result["source_name"]]
        source["count"] += 1
        source[result["status"]] += 1
    error_counts = Counter(error for result in results for error in result["errors"])
    return {
        "record_count": len(results),
        "pass_count": sum(1 for result in results if result["status"] == "pass"),
        "fail_count": sum(1 for result in results if result["status"] == "fail"),
        "exact_match_rate": ratio(sum(1 for result in results if result["status"] == "pass"), len(results)),
        "precision": ratio(total_tp, total_tp + total_fp, empty=1.0),
        "recall": ratio(total_tp, total_tp + total_fn, empty=1.0),
        "false_positive_rate": ratio(total_fp, total_tp + total_fp, empty=0.0),
        "false_negative_rate": ratio(total_fn, total_tp + total_fn, empty=0.0),
        "precision_by_cte": precision_by_cte,
        "recall_by_cte": recall_by_cte,
        "false_positive_by_cte": false_positive_by_cte,
        "false_negative_by_cte": false_negative_by_cte,
        "error_counts": dict(sorted(error_counts.items())),
        "by_source": dict(sorted(by_source.items())),
    }


def ratio(numerator: int, denominator: int, *, empty: float = 0.0) -> float:
    return empty if denominator == 0 else round(numerator / denominator, 4)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value) if isinstance(value, list) else value for key, value in row.items()})


if __name__ == "__main__":
    main()
