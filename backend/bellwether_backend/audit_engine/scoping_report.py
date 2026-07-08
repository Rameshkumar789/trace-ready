"""Scoping report: "you have just scoped my FSMA 204 project."

Deterministic aggregates over the FINAL findings/checks (so counts match what the app
displays), plus a plain-English executive narrative. The narrative is the only LLM part and
is generated strictly from the computed stats - a verifier rejects any narrative containing
numbers that don't appear in the stats, and a template fallback covers the no-key case.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

SCOPING_PROMPT_VERSION = "scope-v1"

_SYSTEM_PROMPT = """You write the executive summary of a digital FSMA 204 readiness audit for \
a food-business operator.

You receive a JSON object of deterministic audit statistics. Respond with a JSON array \
containing EXACTLY ONE object: {"narrative": "<3 short paragraphs of plain English>"}.

Hard rules:
- Use ONLY facts and numbers present in the statistics. Do not invent, extrapolate, or round
  numbers. Every number you write must appear verbatim in the statistics.
- Paragraph 1: the magnitude of their FSMA 204 scope (products on/possibly-on the Food
  Traceability List, trading partners involved, event volume and period covered).
- Paragraph 2: the biggest gaps, most severe first, in plain language a non-lawyer follows.
- Paragraph 3: what to do next, concretely, referencing the worst partners/areas by name when
  the statistics include them.
- No headings, no bullet lists, no marketing language. It should read like a sharp
  consultant's cover note."""


def build_scoping_stats(
    *,
    events: dict[str, Any],
    ftl_tier_results: dict[str, dict[str, Any]],
    partner_scorecard: dict[str, Any],
    kde_checks: list[Any],
    lot_integrity_checks: list[Any],
    audit_findings: list[Any],
    export_window: tuple[str | None, str | None],
    mapping_plan_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cte_counts = Counter(cte for event in events.values() for cte in (getattr(event, "classified_ctes", None) or []))
    tier_counts = Counter(result.get("tier") for result in ftl_tier_results.values())
    mismatches = [
        {"product_id": product_id, "declared": result.get("declared_category"), "tier": result.get("tier")}
        for product_id, result in sorted(ftl_tier_results.items())
        if result.get("mismatch")
    ]
    kde_status = Counter(check.status for check in kde_checks)
    graded_kde = kde_status.get("present", 0) + kde_status.get("missing", 0) + kde_status.get("conflicting", 0)
    kde_coverage = round(kde_status.get("present", 0) / graded_kde, 4) if graded_kde else None
    lot_status = Counter(f"{check.check_type}:{check.status}" for check in lot_integrity_checks)
    finding_counts = Counter(finding.finding_type for finding in audit_findings)
    severity_counts = Counter(finding.severity for finding in audit_findings)
    worst_partners = [
        {"name": row["name"], "band": row["quality_band"], "events": row["events"], "fill_rate": row["kde_fill_rate"]}
        for row in partner_scorecard.get("partners", [])
        if not row.get("internal") and not row.get("unknown_bucket") and row.get("quality_band") in {"C", "D"}
    ][:8]
    return {
        "exportWindow": {"start": export_window[0], "end": export_window[1]},
        "events": {"total": len(events), "byCte": dict(sorted(cte_counts.items()))},
        "products": {
            "total": len(ftl_tier_results),
            "byFtlTier": {tier: tier_counts.get(tier, 0) for tier in ("definite_on", "suspicious", "definite_off")},
            "declaredVsInferredMismatches": mismatches[:10],
            "mismatchCount": len(mismatches),
        },
        "partners": {
            "external": partner_scorecard.get("partner_count", 0),
            "bandCounts": partner_scorecard.get("band_counts", {}),
            "internalTransferEvents": partner_scorecard.get("internal_transfer_events", 0),
            "unknownDestinationEvents": partner_scorecard.get("unknown_destination_events", 0),
            "worst": worst_partners,
        },
        "kdeCoverage": {
            "rate": kde_coverage,
            "presentCount": kde_status.get("present", 0),
            "missingCount": kde_status.get("missing", 0),
            "gradedTotal": graded_kde,
            "statusCounts": dict(sorted(kde_status.items())),
        },
        "lotIntegrity": dict(sorted(lot_status.items())),
        "findings": {
            "total": len(audit_findings),
            "byType": dict(sorted(finding_counts.items())),
            "bySeverity": dict(sorted(severity_counts.items())),
        },
        "intake": mapping_plan_summary or {},
    }


def build_scoping_report(*, stats: dict[str, Any], cache: Any | None = None, client: Any | None = None) -> dict[str, Any]:
    from bellwether_backend.intelligence.llm_cache import LLMCache, cache_key
    from bellwether_backend.intelligence.llm_perception import run_cached_perception

    # Numbers are compared with thousands-separators removed on both sides ("6,785" must
    # match the stat 6785). The allowed set also holds pairwise sums of the integer stats
    # (the model legitimately writes "354 of 6,785" where 6785 = present + missing), and
    # percentage<->fraction conversions of every stat.
    stats_json = json.dumps(stats, sort_keys=True, ensure_ascii=False, default=str)
    stat_numbers = re.findall(r"\d+(?:\.\d+)?", stats_json.replace(",", ""))
    allowed_numbers: set[str] = set(stat_numbers)
    integer_stats = sorted({int(n) for n in stat_numbers if n.isdigit()})
    for i, a in enumerate(integer_stats):
        for b in integer_stats[i:]:
            allowed_numbers.add(str(a + b))
    for n in list(allowed_numbers):
        try:
            allowed_numbers.add(str(round(float(n) * 100, 4)).rstrip("0").rstrip("."))
        except ValueError:
            continue

    def _verify(items: list[Any]) -> list[str]:
        if len(items) != 1 or not isinstance(items[0].get("narrative"), str):
            return ["respond with exactly one object containing a 'narrative' string"]
        narrative = items[0]["narrative"]
        if len(narrative) < 200:
            return ["narrative is too short to be useful (min ~200 chars)"]
        errors = []
        for number in re.findall(r"\d+(?:\.\d+)?", narrative.replace(",", "")):
            if number in allowed_numbers:
                continue
            # Small integers are plain-English reasoning (dates, "1 in 20", "the 5 findings"),
            # never fabricated authoritative statistics - allow them.
            if number.isdigit() and int(number) <= 31:
                continue
            # A percentage the model derived from a stats fraction (0.9478 -> 94.78 / 95 / 94).
            try:
                fraction = str(round(float(number) / 100, 4))
                rounded_pcts = {str(round(float(n) * 100)) for n in allowed_numbers if _is_fraction(n)}
            except ValueError:
                fraction, rounded_pcts = "", set()
            if fraction in allowed_numbers or fraction.rstrip("0").rstrip(".") in allowed_numbers or number in rounded_pcts:
                continue
            errors.append(f"number {number!r} in the narrative does not appear in or derive from the statistics")
        return errors[:10]

    result = run_cached_perception(
        namespace="scoping_narrative",
        cache_key=cache_key(SCOPING_PROMPT_VERSION, stats_json),
        system=_SYSTEM_PROMPT,
        user_prompt="Audit statistics:\n" + json.dumps(stats, indent=1, ensure_ascii=False, default=str),
        verify=_verify,
        fallback=lambda: [{"narrative": _template_narrative(stats)}],
        cache=cache,
        client=client,
    )
    return {
        "stats": stats,
        "narrative": result.items[0]["narrative"],
        "narrative_method": result.method,
    }


def _is_fraction(value: str) -> bool:
    try:
        return 0 < float(value) < 1
    except ValueError:
        return False


def _template_narrative(stats: dict[str, Any]) -> str:
    products = stats.get("products", {})
    tiers = products.get("byFtlTier", {})
    partners = stats.get("partners", {})
    findings = stats.get("findings", {})
    window = stats.get("exportWindow", {})
    kde = stats.get("kdeCoverage", {})
    lines = [
        (
            f"This audit covered {stats.get('events', {}).get('total', 0)} traceability events from "
            f"{window.get('start')} to {window.get('end')}. Of {products.get('total', 0)} products, "
            f"{tiers.get('definite_on', 0)} are definitely on the FDA Food Traceability List, "
            f"{tiers.get('suspicious', 0)} need investigation before they can be ruled in or out, and "
            f"{tiers.get('definite_off', 0)} are out of scope. {partners.get('external', 0)} external "
            f"trading partners appear in the data."
        ),
        (
            f"The audit raised {findings.get('total', 0)} findings"
            + (f" (severity mix: {findings.get('bySeverity', {})})" if findings.get("bySeverity") else "")
            + (f"; required-KDE coverage is {kde.get('rate'):.0%}" if kde.get("rate") is not None else "")
            + (
                f", and {products.get('mismatchCount', 0)} product(s) are declared out of scope but look in scope"
                if products.get("mismatchCount")
                else ""
            )
            + "."
        ),
        (
            "Start with the highest-severity lot and traceability-plan findings, resolve the "
            "suspicious FTL products, and engage the lowest-scoring trading partners on their "
            "recurring data gaps"
            + (
                ": " + ", ".join(row["name"] for row in partners.get("worst", [])[:3])
                if partners.get("worst")
                else ""
            )
            + "."
        ),
    ]
    return "\n\n".join(lines)
