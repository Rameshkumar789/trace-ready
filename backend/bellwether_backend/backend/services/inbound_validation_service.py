"""Pre-receipt inbound validation: "you're shipping me something I can't accept —
tell me before it happens."

Accepts an ASN (X12 856), a BOL PDF, or a spreadsheet of intended shipments and returns
per-line verdicts immediately (no job queue, no persistence): missing/invalid KDEs against
the receiving contract (cited), FTL scope per product, and lot-code plausibility. The same
engine that audits historical records, pointed forward at the trading partner.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from bellwether_backend.audit_engine.edi_x12 import edi_856_to_lines, looks_like_x12, parse_x12
from bellwether_backend.audit_engine.lot_integrity import PLACEHOLDER_LOT_VALUES, lot_embedded_date
from bellwether_backend.audit_engine.rule_execution import _load_kde_check_contracts, evaluate_kde_contract_facts

# KDEs the receiver stamps at the dock; a supplier's pre-receipt document can't carry them.
_RECEIVER_SIDE_KDES = {"received_date", "received_location"}


def _derive_inbound_facts(facts: dict[str, list[str]], cte: str) -> dict[str, list[str]]:
    """Mirror the workbook intake's derivations so inbound docs grade against the same
    contracts: source/destination locations become partner/actor links, and the best
    available date becomes the event date."""
    derived = {key: list(values) for key, values in facts.items()}

    def _copy(source: str, target: str) -> None:
        if derived.get(source) and not derived.get(target):
            derived[target] = list(derived[source])

    if cte == "receiving":
        _copy("source_location_id", "from_partner_id")
        _copy("source_location_name", "from_partner_id")
        _copy("destination_location_id", "actor_location_id")
        _copy("destination_location_name", "actor_location_id")
        _copy("received_date", "event_datetime")
    elif cte == "shipping":
        _copy("destination_location_id", "to_partner_id")
        _copy("source_location_id", "actor_location_id")
    for date_slug in ("date_you_shipped_the_food", "received_date", "landing_date", "transformation_date"):
        _copy(date_slug, "event_datetime")
    return derived


def validate_inbound_document(
    *,
    data: bytes,
    file_name: str,
    document_type_hint: str | None = None,
    cte: str = "receiving",
    contracts_file: Path | None = None,
    ftl_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    document_type, lines, intake_issues = _extract_lines(data=data, file_name=file_name, document_type_hint=document_type_hint)

    contracts = _load_kde_check_contracts(contracts_file)
    cte_contract = contracts.get(cte)
    if cte_contract is None:
        return {
            "status": "error",
            "file_name": file_name,
            "document_type": document_type,
            "error": f"no KDE contract for cte {cte!r}",
            "lines": [],
        }

    ftl_results: dict[str, dict[str, Any]] = {}
    if ftl_items:
        from bellwether_backend.intelligence.ftl_tier_classifier import classify_products

        products = []
        seen: set[str] = set()
        for line in lines:
            facts = line.get("facts") or {}
            product_id = (facts.get("product_id") or [None])[0] or (facts.get("product_name") or [None])[0]
            name = (facts.get("product_name") or [None])[0] or product_id
            if product_id and str(product_id) not in seen:
                seen.add(str(product_id))
                products.append({"product_id": str(product_id), "name": name, "declared_category": None})
        if products:
            ftl_results = classify_products(products, ftl_items)

    line_verdicts: list[dict[str, Any]] = []
    for line in lines:
        facts = dict(line.get("facts") or {})
        if not facts:
            line_verdicts.append(
                {
                    "line_number": line.get("line_number"),
                    "verdict": "insufficient_mapping",
                    "problems": [
                        {
                            "kde": None,
                            "message": "No recognizable traceability data on this line; it cannot be validated.",
                            "citation": None,
                        }
                    ],
                    "ftl": None,
                }
            )
            continue

        problems: list[dict[str, Any]] = []
        facts = _derive_inbound_facts(facts, cte)
        kde_results = evaluate_kde_contract_facts(cte_contract=cte_contract, facts=facts)
        for result in kde_results:
            # Pre-receipt: receiver-side KDEs (receive date, received location) are stamped
            # by the receiver at the dock - their absence on a supplier's ASN/BOL must not
            # hold the shipment. Everything the SUPPLIER owes is still enforced.
            if result["kde"] in _RECEIVER_SIDE_KDES:
                continue
            if result["status"] == "missing":
                problems.append(
                    {
                        "kde": result["kde"],
                        "message": f"Missing required KDE: {result['label']}.",
                        "citation": result["citation_section"],
                    }
                )
            elif result["status"] == "conflicting":
                problems.append(
                    {
                        "kde": result["kde"],
                        "message": f"Conflicting values for {result['label']}: {', '.join(result['observed_values'][:4])}.",
                        "citation": result["citation_section"],
                    }
                )

        lots = [value for value in facts.get("traceability_lot_code", []) if str(value).strip()]
        for lot in lots:
            if str(lot).strip().lower() in PLACEHOLDER_LOT_VALUES:
                problems.append(
                    {
                        "kde": "traceability_lot_code",
                        "message": f"Lot code {lot!r} is a placeholder, not a real traceability lot code.",
                        "citation": cte_contract.get("citation_section"),
                    }
                )

        product_id = (facts.get("product_id") or [None])[0] or (facts.get("product_name") or [None])[0]
        ftl = ftl_results.get(str(product_id)) if product_id else None
        ftl_summary = (
            {"tier": ftl.get("tier"), "matched_commodity": ftl.get("matched_commodity"), "reasoning": ftl.get("reasoning")}
            if ftl
            else None
        )

        if ftl and ftl.get("tier") == "definite_off":
            verdict = "not_in_scope"
        elif problems:
            verdict = "hold"
        else:
            verdict = "accept"
        line_verdicts.append(
            {
                "line_number": line.get("line_number"),
                "verdict": verdict,
                "lot": lots[0] if lots else None,
                "product": (facts.get("product_name") or facts.get("product_id") or [None])[0],
                "problems": problems,
                "ftl": ftl_summary,
            }
        )

    verdict_counts = Counter(line["verdict"] for line in line_verdicts)
    return {
        "status": "ok",
        "file_name": file_name,
        "document_type": document_type,
        "cte": cte,
        "line_count": len(line_verdicts),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "overall": (
            "reject" if verdict_counts.get("hold") else ("accept" if line_verdicts else "empty")
        ),
        "intake_issues": intake_issues,
        "lines": line_verdicts,
    }


def _extract_lines(
    *, data: bytes, file_name: str, document_type_hint: str | None
) -> tuple[str, list[dict[str, Any]], list[str]]:
    issues: list[str] = []
    hint = (document_type_hint or "").lower()

    if hint.startswith("edi") or looks_like_x12(data):
        interchange = parse_x12(data)
        issues.extend(interchange.issues)
        lines: list[dict[str, Any]] = []
        for transaction in interchange.transactions:
            if transaction.transaction_set == "856":
                transaction_lines = edi_856_to_lines(transaction)
                if transaction_lines and transaction_lines[0].get("transaction_issues"):
                    issues.extend(transaction_lines[0]["transaction_issues"])
                lines.extend(transaction_lines)
            else:
                issues.append(f"transaction set {transaction.transaction_set} parsed structurally but not mapped (856 is first-class)")
        return "edi_x12", lines, issues

    if hint.startswith("bol") or data[:5] == b"%PDF-":
        from bellwether_backend.intelligence.bol_extractor import extract_bol_lines

        result = extract_bol_lines(data, file_name=file_name)
        issues.extend(result.get("issues", []))
        return "bol_pdf", result.get("lines", []), issues

    # Spreadsheet path: the same universal intake as the audit.
    from bellwether_backend.audit_engine.customer_evidence import _row_facts, read_spreadsheet_evidence

    suffix = Path(file_name).suffix.lower() or ".xlsx"
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        suffix = ".xlsx"
    with TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / f"inbound{suffix}"
        path.write_bytes(data)
        try:
            records = read_spreadsheet_evidence(path)
        except Exception as exc:
            return "unknown", [], [f"could not parse the document as a spreadsheet: {exc}"]
        rows = _row_facts(records)
        lines = []
        for position, row in enumerate(sorted(rows.values(), key=lambda r: (r["sheet"], r["row_number"])), start=1):
            facts = {
                key: [v for v in values if str(v).strip()]
                for key, values in row["facts"].items()
                if not key.startswith("source_column:")
            }
            facts = {key: values for key, values in facts.items() if values}
            lines.append({"line_number": position, "sheet": row["sheet"], "row": row["row_number"], "facts": facts})
        return "spreadsheet", lines, issues
