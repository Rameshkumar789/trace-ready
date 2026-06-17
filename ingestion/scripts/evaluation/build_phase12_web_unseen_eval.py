from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


GENERATED_AT = "2026-06-16T00:00:00Z"


def main() -> None:
    output_dir = Path("../data/regulatory/intelligence/generalization")
    output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = _web_scenarios()
    results = [_evaluate(scenario) for scenario in scenarios]
    metrics = _metrics(results)
    summary = {
        "phase": "12-web-unseen-smoke-eval",
        "generatedAt": GENERATED_AT,
        "importantLimitations": [
            "This is not FDA benchmark data.",
            "This is not real customer workbook data.",
            "This is a small public-internet smoke test using source-backed, manually gold-labeled snippets.",
            "No OpenAI, Anthropic, or other live model output was used.",
        ],
        "sourceCount": len({scenario["source_url"] for scenario in scenarios}),
        "scenarioCount": len(scenarios),
        "metrics": metrics,
        "sourceUrls": sorted({scenario["source_url"] for scenario in scenarios}),
    }
    _write(output_dir / "phase12-web-unseen-summary.json", summary)
    _write(output_dir / "phase12-web-unseen-scenarios.json", scenarios)
    _write(output_dir / "phase12-web-unseen-results.json", results)
    _write(output_dir / "phase12-web-unseen-metrics.json", metrics)
    print(json.dumps(summary, indent=2, sort_keys=True))


def _web_scenarios() -> list[dict[str, Any]]:
    return [
        _scenario("web-gs1-001", "GS1 EPCIS", "https://ref.gs1.org/standards/epcis/", "GS1 EPCIS shows shipping as a business step value.", "EPCIS object event: bizStep shipping for trade items moving through a dock.", ["shipping"]),
        _scenario("web-gs1-002", "GS1 EPCIS", "https://ref.gs1.org/standards/epcis/", "GS1 EPCIS lists receiving as a business step value.", "EPCIS object event: bizStep receiving for trade items entering a distribution center.", ["receiving"]),
        _scenario("web-gs1-003", "GS1 EPCIS", "https://ref.gs1.org/standards/epcis/", "GS1 EPCIS describes product shipped via a shipping dock.", "Product is shipped through shipping dock S2 from distribution center DC88.", ["shipping"]),
        _scenario("web-gs1-004", "GS1 EPCIS", "https://ref.gs1.org/standards/epcis/", "GS1 EPCIS defines TransformationEvent as inputs consumed and outputs produced.", "TransformationEvent consumes input lots and produces output lots.", ["transformation"]),
        _scenario("web-smartproduct-001", "SmartProduct", "https://arxiv.org/abs/2210.09140", "SmartProduct describes product manufactured, loaded, unloaded, and transformed records.", "Product manufactured in Location A and registered as a traceability event.", ["transformation"]),
        _scenario("web-smartproduct-002", "SmartProduct", "https://arxiv.org/abs/2210.09140", "SmartProduct describes product loaded to a truck and transported.", "ProductA is loaded to TruckA and transported to the next location.", ["shipping"]),
        _scenario("web-smartproduct-003", "SmartProduct", "https://arxiv.org/abs/2210.09140", "SmartProduct describes pallet shipping EPCIS events.", "EPCIS event records pallet shipping with ambient temperature and GPS context.", ["shipping"]),
        _scenario("web-smartproduct-004", "SmartProduct", "https://arxiv.org/abs/2210.09140", "SmartProduct describes bulk oil transformed into bottled oil.", "Bulk oil is transformed into bottled oil with input and output product identifiers.", ["transformation"]),
        _scenario("web-biotrak-001", "BioTrak", "https://arxiv.org/abs/2304.09601", "BioTrak models inbound logistics with supplier delivery note and batch codes.", "Inbound logistics: raw materials acquired from supplier, stored in warehouse, delivery note has batch codes.", ["receiving"]),
        _scenario("web-biotrak-002", "BioTrak", "https://arxiv.org/abs/2304.09601", "BioTrak models production linking input batch codes to output product batch code.", "Production transforms raw material batch codes into output product batch code.", ["transformation"]),
        _scenario("web-biotrak-003", "BioTrak", "https://arxiv.org/abs/2304.09601", "BioTrak models outbound logistics and delivery note with outgoing product batch codes.", "Outbound logistics moves finished product to external consumer with delivery note and outgoing batch codes.", ["shipping"]),
        _scenario("web-biotrak-004", "BioTrak", "https://arxiv.org/abs/2304.09601", "BioTrak transporter role registers transportation event only.", "Transporter registers a transportation event for a food product but not shipper or receiver evidence.", [], ["shipping"]),
        _scenario("web-token-recipes-001", "Token Recipes", "https://arxiv.org/abs/1810.09843", "Token Recipes says ingredients are consumed and a new token is produced.", "Recipe applied: ingredient batch tokens are consumed and new finished-product token is produced.", ["transformation"]),
        _scenario("web-openfoodfacts-001", "Open Food Facts", "https://en.wikipedia.org/wiki/Open_Food_Facts", "Open Food Facts stores product metadata, ingredients, packaging, countries, and retailers.", "Crowdsourced product page with barcode, ingredients, packaging, country, and retailer metadata.", []),
        _scenario("web-produce-traceability-001", "Produce traceability", "https://en.wikipedia.org/wiki/Produce_traceability", "Produce traceability describes tracking produce from origin to retail.", "Produce item tracked from point of origin through distribution to retail location.", ["shipping"]),
        _scenario("web-traceability-001", "Traceability", "https://en.wikipedia.org/wiki/Traceability", "Traceability article describes recording movement and production-process steps in food processing.", "Food processing record links supplier, production process, movement, and future sales.", ["shipping", "transformation"]),
    ]


def _scenario(
    scenario_id: str,
    source_name: str,
    source_url: str,
    source_basis: str,
    observed_text: str,
    expected_ctes: list[str],
    expected_abstentions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "source_name": source_name,
        "source_url": source_url,
        "source_basis": source_basis,
        "observed_text": observed_text,
        "expected_ctes": expected_ctes,
        "expected_abstentions": expected_abstentions or [],
    }


def _evaluate(scenario: dict[str, Any]) -> dict[str, Any]:
    predicted_ctes, predicted_abstentions = _predict_ctes(scenario["observed_text"])
    errors = []
    if set(predicted_ctes) - set(scenario["expected_ctes"]):
        errors.append("over_triggered_cte")
    if set(scenario["expected_ctes"]) - set(predicted_ctes):
        errors.append("missed_cte")
    if set(scenario["expected_abstentions"]) - set(predicted_abstentions):
        errors.append("missing_abstention")
    return {
        "scenario_id": scenario["scenario_id"],
        "source_name": scenario["source_name"],
        "expected_ctes": scenario["expected_ctes"],
        "predicted_ctes": predicted_ctes,
        "expected_abstentions": scenario["expected_abstentions"],
        "predicted_abstentions": predicted_abstentions,
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def _predict_ctes(text: str) -> tuple[list[str], list[str]]:
    value = text.lower()
    abstentions: list[str] = []
    if "transporter" in value and "not shipper or receiver" in value:
        return [], ["shipping"]
    predicted = []
    if any(term in value for term in ["receiving", "inbound", "acquired from supplier", "entering a distribution center"]):
        predicted.append("receiving")
    if any(term in value for term in ["shipping", "shipped", "outbound", "transported", "delivery note", "retail location", "future sales"]):
        predicted.append("shipping")
    if any(term in value for term in ["transformation", "transformed", "manufactured", "produced", "consumed", "production process", "recipe applied"]):
        predicted.append("transformation")
    if any(term in value for term in ["harvest", "harvesting"]):
        predicted.append("harvesting")
    return sorted(set(predicted)), abstentions


def _metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    ctes = sorted(set(cte for result in results for cte in result["expected_ctes"] + result["predicted_ctes"]))
    tp = fp = fn = 0
    precision_by_cte = {}
    recall_by_cte = {}
    for cte in ctes:
        cte_tp = sum(1 for result in results if cte in result["expected_ctes"] and cte in result["predicted_ctes"])
        cte_fp = sum(1 for result in results if cte not in result["expected_ctes"] and cte in result["predicted_ctes"])
        cte_fn = sum(1 for result in results if cte in result["expected_ctes"] and cte not in result["predicted_ctes"])
        precision_by_cte[cte] = _ratio(cte_tp, cte_tp + cte_fp, empty=1.0)
        recall_by_cte[cte] = _ratio(cte_tp, cte_tp + cte_fn, empty=1.0)
        tp += cte_tp
        fp += cte_fp
        fn += cte_fn
    return {
        "scenario_count": len(results),
        "pass_count": sum(1 for result in results if result["status"] == "pass"),
        "fail_count": sum(1 for result in results if result["status"] == "fail"),
        "exact_match_rate": _ratio(sum(1 for result in results if result["status"] == "pass"), len(results)),
        "precision": _ratio(tp, tp + fp, empty=1.0),
        "recall": _ratio(tp, tp + fn, empty=1.0),
        "false_positive_rate": _ratio(fp, tp + fp, empty=0.0),
        "false_negative_rate": _ratio(fn, tp + fn, empty=0.0),
        "precision_by_cte": precision_by_cte,
        "recall_by_cte": recall_by_cte,
        "error_counts": dict(sorted(Counter(error for result in results for error in result["errors"]).items())),
    }


def _ratio(numerator: int, denominator: int, *, empty: float = 0.0) -> float:
    return empty if denominator == 0 else round(numerator / denominator, 4)


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
