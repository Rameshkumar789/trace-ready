from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from build_phase12_web500_eval_data import predict_ctes


GENERATED_AT = "2026-06-16T00:00:00Z"
DEFAULT_OUTPUT_DIR = Path("../data/regulatory/intelligence/generalization")
DEFAULT_EPCIS_DIR = Path("/private/tmp/traceready-web2000/EPCIS")
OPEN_FOOD_FACTS_TSV = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
GS1_EPCIS_REPO = "https://github.com/gs1/EPCIS"
GS1_EPCIS_STANDARD = "https://ref.gs1.org/standards/epcis/"


OFF_FIELDS = [
    "code",
    "url",
    "product_name",
    "generic_name",
    "brands",
    "quantity",
    "packaging",
    "categories",
    "manufacturing_places",
    "countries",
    "stores",
    "ingredients_text",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-count", type=int, default=2000)
    parser.add_argument("--epcis-dir", type=Path, default=DEFAULT_EPCIS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--epcis-target", type=int, default=400)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    epcis_records = build_epcis_records(args.epcis_dir, target=args.epcis_target)
    off_target = args.record_count - len(epcis_records)
    if off_target < 0:
        epcis_records = epcis_records[: args.record_count]
        off_target = 0
    off_records = stream_open_food_facts_records(off_target)
    records = renumber_records([*off_records, *epcis_records])
    results = [evaluate_record(record) for record in records]
    metrics = build_metrics(results)
    summary = {
        "phase": "13-web2000-fresh-public-internet-holdout",
        "generatedAt": GENERATED_AT,
        "recordCount": len(records),
        "sourceCount": 2,
        "metrics": metrics,
        "importantLimitations": [
            "This is public internet data, not confidential customer transaction export data.",
            "Open Food Facts rows are real public product metadata records and are gold-labeled as non-CTE rows because they are product facts, not event evidence.",
            "GS1 EPCIS rows are public standard/example visibility-event records and are gold-labeled from event type, business step, and error-declaration context.",
            "The dataset is intentionally fresh versus the earlier web500 workbook, but it is not a substitute for customer-specific spreadsheet/parser acceptance tests.",
            "No OpenAI, Anthropic, or other live model output was used in this run.",
        ],
        "sourceComposition": metrics["by_source"],
    }
    source_register = build_source_register()
    outputs = {
        "summary": args.output_dir / "phase13-web2000-summary.json",
        "records": args.output_dir / "phase13-web2000-input-records.json",
        "results": args.output_dir / "phase13-web2000-results.json",
        "metrics": args.output_dir / "phase13-web2000-metrics.json",
        "sources": args.output_dir / "phase13-web2000-source-register.json",
        "recordsCsv": args.output_dir / "phase13-web2000-input-records.csv",
        "resultsCsv": args.output_dir / "phase13-web2000-results.csv",
    }
    write_json(outputs["summary"], summary)
    write_json(outputs["records"], records)
    write_json(outputs["results"], results)
    write_json(outputs["metrics"], metrics)
    write_json(outputs["sources"], source_register)
    write_csv(outputs["recordsCsv"], records)
    write_csv(outputs["resultsCsv"], results)
    print(json.dumps({"summary": summary, "outputs": {key: str(value) for key, value in outputs.items()}}, indent=2, sort_keys=True))


def stream_open_food_facts_records(target: int) -> list[dict[str, Any]]:
    if target <= 0:
        return []
    request = urllib.request.Request(
        OPEN_FOOD_FACTS_TSV,
        headers={"User-Agent": "TraceReady-public-eval/1.0 (+https://traceready.local)"},
    )
    records: list[dict[str, Any]] = []
    with urllib.request.urlopen(request, timeout=90) as response:
        gz = gzip.GzipFile(fileobj=response)
        text = io.TextIOWrapper(gz, encoding="utf-8", errors="replace", newline="")
        reader = csv.DictReader(text, delimiter="\t")
        for row in reader:
            if len(records) >= target:
                break
            product_name = clean_value(row.get("product_name"))
            code = clean_value(row.get("code"))
            if not product_name or not code:
                continue
            record_values = {field: clean_value(row.get(field)) for field in OFF_FIELDS}
            observed_parts = [
                f"Open Food Facts product metadata row code {record_values['code']}",
                f"product_name={record_values['product_name']}",
                f"generic_name={record_values['generic_name']}",
                f"brands={record_values['brands']}",
                f"quantity={record_values['quantity']}",
                f"packaging={record_values['packaging']}",
                f"categories={record_values['categories']}",
                f"manufacturing_places={record_values['manufacturing_places']}",
                f"countries={record_values['countries']}",
                f"stores={record_values['stores']}",
                f"ingredients_text={truncate(record_values['ingredients_text'], 260)}",
            ]
            records.append(
                {
                    "record_id": "",
                    "source_record_id": record_values["code"],
                    "scenario_family": "open_food_facts_product_metadata",
                    "source_name": "Open Food Facts static bulk TSV",
                    "source_url": OPEN_FOOD_FACTS_TSV,
                    "source_basis": "Public Open Food Facts product metadata row streamed from the static bulk dataset.",
                    "source_file": "en.openfoodfacts.org.products.csv.gz",
                    "event_type": "product_metadata",
                    "biz_step": "",
                    "product": product_name,
                    "product_category": truncate(record_values["categories"], 180),
                    "lot_or_batch": "",
                    "observed_text": "; ".join(part for part in observed_parts if not part.endswith("=")),
                    "expected_ctes": [],
                    "expected_abstentions": [],
                    "gold_label_method": "product_metadata_not_transaction_event",
                }
            )
    return records


def build_epcis_records(epcis_dir: Path, *, target: int) -> list[dict[str, Any]]:
    if target <= 0:
        return []
    if not epcis_dir.exists():
        raise FileNotFoundError(f"GS1 EPCIS checkout not found: {epcis_dir}")
    records: list[dict[str, Any]] = []
    for path in sorted(epcis_dir.rglob("*")):
        if len(records) >= target:
            break
        if path.suffix == ".jsonld":
            records.extend(extract_jsonld_events(path, epcis_dir))
        elif path.suffix == ".xml":
            records.extend(extract_xml_events(path, epcis_dir))
        if len(records) >= target:
            records = records[:target]
            break
    return records


def extract_jsonld_events(path: Path, epcis_dir: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    events = find_json_events(payload)
    records = []
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            continue
        records.append(build_epcis_event_record(event, path, epcis_dir, index, "jsonld"))
    return records


def find_json_events(payload: Any) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        epcis_body = payload.get("epcisBody")
        if not isinstance(epcis_body, dict):
            epcis_body = {}
        event_list = epcis_body.get("eventList")
        if isinstance(event_list, list):
            events.extend(event_list)
        query_results = epcis_body.get("queryResults")
        if not isinstance(query_results, dict):
            query_results = {}
        results_body = query_results.get("resultsBody")
        if not isinstance(results_body, dict):
            results_body = {}
        query_event_list = results_body.get("eventList")
        if isinstance(query_event_list, list):
            events.extend(query_event_list)
        event_type = value_tail(payload.get("type") or payload.get("@type"))
        if event_type in EVENT_TYPES:
            events.append(payload)
        for value in payload.values():
            if isinstance(value, (dict, list)):
                events.extend(find_json_events(value))
    elif isinstance(payload, list):
        for item in payload:
            events.extend(find_json_events(item))
    return dedupe_event_objects(events)


def dedupe_event_objects(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for event in events:
        key = str(event.get("eventID") or event.get("id") or json.dumps(event, sort_keys=True)[:500])
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique


def extract_xml_events(path: Path, epcis_dir: Path) -> list[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, UnicodeDecodeError):
        return []
    records: list[dict[str, Any]] = []
    for index, element in enumerate(root.iter(), start=1):
        event_type = strip_namespace(element.tag)
        if event_type not in EVENT_TYPES:
            continue
        event = xml_element_to_event(element)
        records.append(build_epcis_event_record(event, path, epcis_dir, index, "xml"))
    return records


EVENT_TYPES = {
    "ObjectEvent",
    "AggregationEvent",
    "TransformationEvent",
    "TransactionEvent",
    "AssociationEvent",
}


def xml_element_to_event(element: ET.Element) -> dict[str, Any]:
    event: dict[str, Any] = {"type": strip_namespace(element.tag)}
    for child in list(element):
        key = strip_namespace(child.tag)
        if list(child):
            event[key] = " ".join(text.strip() for text in child.itertext() if text and text.strip())
        else:
            event[key] = (child.text or "").strip()
    return event


def build_epcis_event_record(event: dict[str, Any], path: Path, epcis_dir: Path, index: int, file_type: str) -> dict[str, Any]:
    event_type = value_tail(event.get("type") or event.get("@type"))
    biz_step = value_tail(event.get("bizStep"))
    disposition = value_tail(event.get("disposition"))
    action = value_tail(event.get("action"))
    event_id = clean_value(event.get("eventID") or event.get("id") or f"{path.name}:{index}")
    expected_ctes, expected_abstentions = label_epcis_event(event_type, biz_step, event)
    source_file = str(path.relative_to(epcis_dir))
    observed_text = format_epcis_observed_text(event, event_type, biz_step, disposition, action, source_file)
    return {
        "record_id": "",
        "source_record_id": event_id,
        "scenario_family": "gs1_epcis_visibility_event",
        "source_name": "GS1 EPCIS public examples",
        "source_url": f"{GS1_EPCIS_REPO}/blob/master/{source_file}",
        "source_basis": "Public GS1 EPCIS example visibility event parsed from JSON-LD/XML files.",
        "source_file": source_file,
        "event_type": event_type,
        "biz_step": biz_step,
        "product": infer_product_from_event(event),
        "product_category": "",
        "lot_or_batch": infer_lot_from_event(event),
        "observed_text": observed_text,
        "expected_ctes": expected_ctes,
        "expected_abstentions": expected_abstentions,
        "gold_label_method": f"event_type_and_biz_step_label_from_public_epcis_{file_type}",
    }


def label_epcis_event(event_type: str, biz_step: str, event: dict[str, Any]) -> tuple[list[str], list[str]]:
    if has_error_declaration(event):
        return [], ["shipping"]
    labels: list[str] = []
    if event_type == "TransformationEvent":
        labels.append("transformation")
    if biz_step in {"shipping", "departing"}:
        labels.append("shipping")
    if biz_step in {"receiving", "arriving", "accepting"}:
        labels.append("receiving")
    if biz_step in {"packing"}:
        labels.append("initial_packing")
    return sorted(set(labels)), []


def format_epcis_observed_text(event: dict[str, Any], event_type: str, biz_step: str, disposition: str, action: str, source_file: str) -> str:
    input_values = collect_event_values(event, ["inputEPCList", "inputQuantityList"])
    output_values = collect_event_values(event, ["outputEPCList", "outputQuantityList"])
    epc_values = collect_event_values(event, ["epcList", "childEPCs", "quantityList", "childQuantityList"])
    source_dest_values = collect_event_values(event, ["sourceList", "destinationList", "readPoint", "bizLocation"])
    parts = [
        f"GS1 EPCIS {event_type} public example from {source_file}",
        f"action={action}",
        f"bizStep {biz_step}" if biz_step else "",
        f"disposition={disposition}",
        f"eventTime={clean_value(event.get('eventTime'))}",
        "error declaration present" if has_error_declaration(event) else "",
        f"epcList={truncate(epc_values, 360)}",
        f"input lot list={truncate(input_values, 260)}",
        f"output lot list={truncate(output_values, 260)}",
        f"source destination and location={truncate(source_dest_values, 260)}",
    ]
    return "; ".join(part for part in parts if part and not part.endswith("="))


def has_error_declaration(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if clean_value(key).lower() == "errordeclaration":
                return True
            if has_error_declaration(item):
                return True
    if isinstance(value, list):
        return any(has_error_declaration(item) for item in value)
    return False


def collect_event_values(event: dict[str, Any], keys: list[str]) -> str:
    values = []
    for key in keys:
        if key in event:
            values.append(flatten_value(event[key]))
    return " ".join(value for value in values if value)


def flatten_value(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(flatten_value(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(flatten_value(item) for item in value)
    return clean_value(value)


def infer_product_from_event(event: dict[str, Any]) -> str:
    values = collect_event_values(event, ["epcList", "inputQuantityList", "outputQuantityList", "quantityList"])
    match = re.search(r"(?:sgtin|lgtin|class):([^\\s,;]+)", values)
    return match.group(1) if match else value_tail(event.get("bizStep")) or "EPCIS event"


def infer_lot_from_event(event: dict[str, Any]) -> str:
    values = collect_event_values(event, ["ilmd", "inputEPCList", "outputEPCList", "epcList"])
    for pattern in [r"batch['\": ]+([A-Za-z0-9._-]+)", r"/10/([A-Za-z0-9._-]+)", r"\.([A-Za-z0-9_-]{3,})$"]:
        match = re.search(pattern, values)
        if match:
            return match.group(1)
    return ""


def renumber_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for index, record in enumerate(records, start=1):
        record["record_id"] = f"web2000-{index:04d}"
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
        "source_record_id": record["source_record_id"],
        "scenario_family": record["scenario_family"],
        "source_name": record["source_name"],
        "source_file": record["source_file"],
        "event_type": record["event_type"],
        "biz_step": record["biz_step"],
        "expected_ctes": record["expected_ctes"],
        "predicted_ctes": predicted_ctes,
        "expected_abstentions": record["expected_abstentions"],
        "predicted_abstentions": predicted_abstentions,
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def build_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    ctes = sorted(set(cte for result in results for cte in result["expected_ctes"] + result["predicted_ctes"]))
    precision_by_cte: dict[str, float] = {}
    recall_by_cte: dict[str, float] = {}
    false_positive_by_cte: dict[str, int] = {}
    false_negative_by_cte: dict[str, int] = {}
    support_by_cte: dict[str, int] = {}
    total_tp = total_fp = total_fn = 0
    for cte in ctes:
        tp = sum(1 for result in results if cte in result["expected_ctes"] and cte in result["predicted_ctes"])
        fp = sum(1 for result in results if cte not in result["expected_ctes"] and cte in result["predicted_ctes"])
        fn = sum(1 for result in results if cte in result["expected_ctes"] and cte not in result["predicted_ctes"])
        support = sum(1 for result in results if cte in result["expected_ctes"])
        precision_by_cte[cte] = ratio(tp, tp + fp, empty=1.0)
        recall_by_cte[cte] = ratio(tp, tp + fn, empty=1.0)
        false_positive_by_cte[cte] = fp
        false_negative_by_cte[cte] = fn
        support_by_cte[cte] = support
        total_tp += tp
        total_fp += fp
        total_fn += fn
    by_source = defaultdict(lambda: {"count": 0, "pass": 0, "fail": 0, "pass_rate": 0.0})
    by_family = defaultdict(lambda: {"count": 0, "pass": 0, "fail": 0, "pass_rate": 0.0})
    for result in results:
        for bucket, key in [(by_source, result["source_name"]), (by_family, result["scenario_family"])]:
            item = bucket[key]
            item["count"] += 1
            item[result["status"]] += 1
    for bucket in [by_source, by_family]:
        for item in bucket.values():
            item["pass_rate"] = ratio(item["pass"], item["count"])
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
        "support_by_cte": support_by_cte,
        "precision_by_cte": precision_by_cte,
        "recall_by_cte": recall_by_cte,
        "false_positive_by_cte": false_positive_by_cte,
        "false_negative_by_cte": false_negative_by_cte,
        "error_counts": dict(sorted(error_counts.items())),
        "by_source": dict(sorted(by_source.items())),
        "by_family": dict(sorted(by_family.items())),
    }


def build_source_register() -> list[dict[str, str]]:
    return [
        {
            "source_key": "open_food_facts_static_tsv",
            "source_name": "Open Food Facts static bulk TSV",
            "source_url": OPEN_FOOD_FACTS_TSV,
            "source_basis": "Public product metadata rows from the Open Food Facts static bulk export.",
        },
        {
            "source_key": "gs1_epcis_public_examples",
            "source_name": "GS1 EPCIS public examples",
            "source_url": GS1_EPCIS_REPO,
            "source_basis": f"Public EPCIS JSON-LD/XML example event records from GS1; standard reference {GS1_EPCIS_STANDARD}.",
        },
    ]


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


def value_tail(value: Any) -> str:
    value = clean_value(value)
    if not value:
        return ""
    value = value.rsplit("/", 1)[-1]
    value = value.rsplit(":", 1)[-1]
    return value


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", value).strip()


def truncate(value: str, limit: int) -> str:
    value = clean_value(value)
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"phase13 web2000 build failed: {exc}", file=sys.stderr)
        raise
