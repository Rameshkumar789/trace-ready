from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingest import ingest_html_url


FDA_FSMA204_HUB_SOURCES = [
    {
        "sourceId": "fda-fsma204-final-rule-page",
        "url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods",
        "tier": "core_hub",
        "use": "Source discovery and FDA operational summary for FSMA 204.",
    },
    {
        "sourceId": "ecfr-21-cfr-1-subpart-s",
        "url": "https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1",
        "tier": "binding_rule",
        "use": "Current codified legal text for executable rules after approval.",
        "minSection": 1.13,
        "maxSection": 1.1465,
    },
    {
        "sourceId": "fr-2022-24417-final-rule",
        "url": "https://www.federalregister.gov/documents/2022/11/21/2022-24417/requirements-for-additional-traceability-records-for-certain-foods",
        "tier": "binding_rule_history",
        "use": "Final rule preamble, reasoning, responses to comments, and section-by-section explanation.",
    },
    {
        "sourceId": "fr-2022-24417-final-rule-pdf",
        "url": "https://www.govinfo.gov/content/pkg/FR-2022-11-21/pdf/2022-24417.pdf",
        "tier": "binding_rule_history",
        "use": "Official Federal Register PDF for layout-aware final-rule extraction.",
    },
    {
        "sourceId": "fda-food-traceability-list",
        "url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/food-traceability-list",
        "tier": "product_scope",
        "use": "Covered food taxonomy and FTL scope notes.",
    },
    {
        "sourceId": "fda-ftl-risk-ranking-memo-final-rule",
        "url": "https://www.fda.gov/media/142283/download?attachment",
        "tier": "product_scope_support",
        "use": "Memo explaining FTL designation for the final rule.",
    },
    {
        "sourceId": "fda-ftl-risk-ranking-designation-memo",
        "url": "https://www.fda.gov/media/142282/download?attachment",
        "tier": "product_scope_support",
        "use": "Designation memo for the Food Traceability List using the risk-ranking model.",
    },
    {
        "sourceId": "fda-ftl-risk-ranking-methodology",
        "url": "https://www.fda.gov/media/142247/download?attachment",
        "tier": "product_scope_support",
        "use": "Methodology for the risk-ranking model used to develop the FTL.",
    },
    {
        "sourceId": "fda-ftl-risk-ranking-results-table-1a",
        "url": "https://www.fda.gov/media/166878/download?attachment",
        "tier": "product_scope_support",
        "use": "Risk-ranking results for FTL commodities.",
    },
    {
        "sourceId": "fda-ftl-risk-ranking-results-table-1b",
        "url": "https://www.fda.gov/media/166879/download?attachment",
        "tier": "product_scope_support",
        "use": "Risk-ranking results for FTL commodity-hazard pairs.",
    },
    {
        "sourceId": "fda-ftl-risk-ranking-results-all",
        "url": "https://www.fda.gov/media/166880/download?attachment",
        "tier": "product_scope_support",
        "use": "Risk-ranking results for all commodities and commodity-hazard pairs.",
    },
    {
        "sourceId": "fda-ftl-risk-ranking-references",
        "url": "https://www.fda.gov/media/143495/download?attachment",
        "tier": "product_scope_support",
        "use": "Full references for the risk-ranking model.",
    },
    {
        "sourceId": "fda-risk-ranking-model-web-app",
        "url": "https://hfpappexternal.fda.gov/scripts/FDARiskRankingModelforFoodTracingfinalrule/",
        "tier": "product_scope_support",
        "use": "FDA interactive risk-ranking model web application landing page.",
    },
    {
        "sourceId": "fda-fish-guidance-chapter-3",
        "url": "https://www.fda.gov/media/80637/download?attachment",
        "tier": "cross_reference",
        "use": "Finfish species examples referenced by the FTL.",
    },
    {
        "sourceId": "fda-cte-kde-pdf",
        "url": "https://www.fda.gov/media/163132/download?attachment",
        "tier": "cte_kde_schema",
        "use": "FDA CTE/KDE implementation support by event type.",
    },
    {
        "sourceId": "fda-traceability-lot-code",
        "url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/traceability-lot-code",
        "tier": "tlc_support",
        "use": "TLC assignment, source reference, and preservation support.",
    },
    {
        "sourceId": "fda-sortable-spreadsheet-xlsx",
        "url": "https://www.fda.gov/media/179617/download?attachment",
        "tier": "export_schema",
        "use": "FDA electronic sortable spreadsheet template.",
    },
    {
        "sourceId": "fda-sortable-spreadsheet-pdf",
        "url": "https://www.fda.gov/media/179616/download?attachment",
        "tier": "export_schema",
        "use": "PDF rendering of the FDA electronic sortable spreadsheet template.",
    },
    {
        "sourceId": "fda-sortable-spreadsheet-sample-xlsx",
        "url": "https://www.fda.gov/media/181946/download?attachment",
        "tier": "export_schema_sample",
        "use": "FDA sample-data workbook for golden output tests.",
    },
    {
        "sourceId": "fda-sortable-spreadsheet-sample-pdf",
        "url": "https://www.fda.gov/media/181945/download?attachment",
        "tier": "export_schema_sample",
        "use": "PDF rendering of the sample-data workbook.",
    },
    {
        "sourceId": "fda-qa-guidance-2026",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-about-requirements-additional-traceability-records-certain-foods",
        "tier": "guidance",
        "use": "FDA draft Q&A guidance for reviewer support.",
    },
    {
        "sourceId": "fda-small-entity-guide-2023",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/small-entity-compliance-guide-requirements-additional-traceability-records-certain-foods-what-you",
        "tier": "guidance",
        "use": "Small entity compliance guide for operator-facing interpretation.",
    },
    {
        "sourceId": "fda-faq-food-traceability-rule",
        "url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/frequently-asked-questions-fsma-food-traceability-rule",
        "tier": "guidance",
        "use": "Operational FAQ support.",
    },
    {
        "sourceId": "fda-at-a-glance",
        "url": "https://www.fda.gov/media/183514/download?attachment",
        "tier": "guidance_summary",
        "use": "FDA At-A-Glance summary.",
    },
    {
        "sourceId": "scenario-produce-cucumbers-transcript",
        "url": "https://www.fda.gov/media/163059/download?attachment",
        "tier": "scenario",
        "use": "Produce cucumber supply-chain transcript for golden scenario tests.",
    },
    {
        "sourceId": "scenario-produce-cucumbers-slides",
        "url": "https://www.fda.gov/media/163054/download?attachment",
        "tier": "scenario",
        "use": "Produce cucumber supply-chain slides for scenario/evidence mapping.",
    },
    {
        "sourceId": "scenario-seafood-tuna-transcript",
        "url": "https://www.fda.gov/media/163058/download?attachment",
        "tier": "scenario",
        "use": "Seafood tuna supply-chain transcript for golden scenario tests.",
    },
    {
        "sourceId": "scenario-seafood-tuna-slides",
        "url": "https://www.fda.gov/media/163055/download?attachment",
        "tier": "scenario",
        "use": "Seafood tuna supply-chain slides for scenario/evidence mapping.",
    },
    {
        "sourceId": "scenario-cheese-transcript",
        "url": "https://www.fda.gov/media/163060/download?attachment",
        "tier": "scenario",
        "use": "Cheese supply-chain transcript for golden scenario tests.",
    },
    {
        "sourceId": "scenario-cheese-slides",
        "url": "https://www.fda.gov/media/163056/download?attachment",
        "tier": "scenario",
        "use": "Cheese supply-chain slides for scenario/evidence mapping.",
    },
    {
        "sourceId": "scenario-deli-salad-slides",
        "url": "https://www.fda.gov/media/173215/download?attachment",
        "tier": "scenario",
        "use": "Deli salad scenario slides.",
    },
    {
        "sourceId": "scenario-sprouts-slides",
        "url": "https://www.fda.gov/media/177855/download?attachment",
        "tier": "scenario",
        "use": "Sprouts scenario slides.",
    },
    {
        "sourceId": "scenario-additional-supply-chain-examples-2024",
        "url": "https://www.fda.gov/media/169511/download?attachment",
        "tier": "scenario",
        "use": "Additional supply-chain scenario slides.",
    },
    {
        "sourceId": "scenario-additional-supply-chain-examples-2025-08",
        "url": "https://www.fda.gov/media/188084/download?attachment",
        "tier": "scenario",
        "use": "Additional August 2025 supply-chain scenario slides.",
    },
    {
        "sourceId": "traceability-plan-farms",
        "url": "https://www.fda.gov/media/174057/download?attachment",
        "tier": "traceability_plan_example",
        "use": "Traceability plan example for farms.",
    },
    {
        "sourceId": "traceability-plan-restaurants",
        "url": "https://www.fda.gov/media/174058/download?attachment",
        "tier": "traceability_plan_example",
        "use": "Traceability plan example for restaurants.",
    },
    {
        "sourceId": "traceability-plan-sprouters",
        "url": "https://www.fda.gov/media/181575/download?attachment",
        "tier": "traceability_plan_example",
        "use": "Traceability plan example for sprouters.",
    },
    {
        "sourceId": "traceability-plan-food-processors",
        "url": "https://www.fda.gov/media/188100/download?attachment",
        "tier": "traceability_plan_example",
        "use": "Traceability plan example for food processors.",
    },
    {
        "sourceId": "traceability-plan-distribution-centers",
        "url": "https://www.fda.gov/media/188101/download?attachment",
        "tier": "traceability_plan_example",
        "use": "Traceability plan example for distribution centers.",
    },
    {
        "sourceId": "traceability-plan-seafood-processing",
        "url": "https://www.fda.gov/media/188102/download?attachment",
        "tier": "traceability_plan_example",
        "use": "Traceability plan example for seafood processing facilities.",
    },
    {
        "sourceId": "traceability-plan-aquaculture",
        "url": "https://www.fda.gov/media/188103/download?attachment",
        "tier": "traceability_plan_example",
        "use": "Traceability plan example for aquaculture farms.",
    },
    {
        "sourceId": "rfe-restaurants-records-needed",
        "url": "https://www.fda.gov/media/163014/download?attachment",
        "tier": "operator_support",
        "use": "RFE/restaurant recordkeeping support.",
    },
    {
        "sourceId": "rfe-restaurants-rule-overview",
        "url": "https://www.fda.gov/media/163015/download?attachment",
        "tier": "operator_support",
        "use": "RFE/restaurant Food Traceability Rule overview.",
    },
    {
        "sourceId": "rfe-restaurants-traceability-plan",
        "url": "https://www.fda.gov/media/163016/download?attachment",
        "tier": "operator_support",
        "use": "RFE/restaurant traceability plan support.",
    },
    {
        "sourceId": "produce-farms-coverage-exemptions",
        "url": "https://www.fda.gov/media/169509/download?attachment",
        "tier": "operator_support",
        "use": "Produce farms coverage and exemptions.",
    },
    {
        "sourceId": "produce-farms-recordkeeping",
        "url": "https://www.fda.gov/media/169510/download?attachment",
        "tier": "operator_support",
        "use": "Produce farms recordkeeping support.",
    },
    {
        "sourceId": "fda-produce-farms-exemptions",
        "url": "https://www.fda.gov/food/food-safety-modernization-act-fsma/exemptions-relevant-produce-farms-under-produce-safety-rule-and-food-traceability-rule",
        "tier": "exemption_support",
        "use": "Produce Safety Rule and Food Traceability Rule exemption cross-reference.",
    },
    {
        "sourceId": "fda-final-rule-regulatory-impact-analysis",
        "url": "https://www.fda.gov/about-fda/economic-impact-analyses-fda-regulations/requirements-additional-traceability-records-certain-foods-final-rule-regulatory-impact-analysis",
        "tier": "market_impact",
        "use": "Final rule regulatory impact analysis.",
    },
    {
        "sourceId": "fda-webinar-food-traceability-final-rule-2022-12-07",
        "url": "https://www.fda.gov/food/workshops-meetings-webinars-food-and-dietary-supplements/webinar-food-traceability-final-rule-12072022",
        "tier": "training_support",
        "use": "FDA webinar page for the Food Traceability Final Rule held on December 7, 2022.",
    },
    {
        "sourceId": "fda-lot-level-flexibility-discussion-paper",
        "url": "https://www.fda.gov/media/192696/download?attachment",
        "tier": "change_monitor",
        "use": "Lot-level tracking flexibility discussion paper.",
    },
    {
        "sourceId": "fda-tabletop-exercises-report",
        "url": "https://www.fda.gov/media/192993/download?attachment",
        "tier": "product_research",
        "use": "FDA tabletop exercises report for real implementation challenges.",
    },
    {
        "sourceId": "fr-2025-compliance-date-extension",
        "url": "https://www.federalregister.gov/documents/2025/08/07/2025-14967/requirements-for-additional-traceability-records-for-certain-foods-compliance-date-extension",
        "tier": "change_monitor",
        "use": "Proposed compliance-date extension/change monitor.",
    },
    {
        "sourceId": "fr-2026-cottage-cheese-exemption",
        "url": "https://www.federalregister.gov/documents/2026/02/20/2026-03362/requirements-for-additional-traceability-records-for-certain-foods-exemption-for-cottage-cheese",
        "tier": "exemption_change_monitor",
        "use": "Cottage cheese exemption notice.",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the FDA FSMA 204 hub page and English/core linked artifacts.")
    parser.add_argument("--output-dir", default="../data/regulatory")
    parser.add_argument("--manifest", default="../data/regulatory/fda-fsma204-hub-ingestion-manifest.json")
    parser.add_argument("--include-traceready-context", action="store_true")
    parser.add_argument("--source-id", action="append", help="Limit ingestion to one or more source IDs.")
    args = parser.parse_args()

    selected = set(args.source_id or [])
    output_root = Path(args.output_dir)
    manifest = []
    for source in FDA_FSMA204_HUB_SOURCES:
        if selected and source["sourceId"] not in selected:
            continue
        source_id = source["sourceId"]
        source_output_dir = output_root / source_id
        try:
            result = ingest_html_url(
                source["url"],
                source_id,
                source_output_dir,
                min_section=source.get("minSection"),
                max_section=source.get("maxSection"),
                include_trace_ready_context=args.include_traceready_context,
            )
            manifest.append(
                {
                    **source,
                    "status": "ingested",
                    "sectionsExtracted": result["sectionsExtracted"],
                    "chunks": len(result["chunks"]),
                    "rejectedChunks": len(result["rejectedChunks"]),
                    "contentType": result.get("contentType"),
                    "rawArtifact": result["rawArtifact"],
                    "normalizedArtifact": str(source_output_dir / "normalized" / f"{source_id}.json"),
                }
            )
        except Exception as error:
            manifest.append({**source, "status": "failed", "error": str(error)})

    manifest_path = Path(args.manifest)
    if selected and manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        selected_ids = {item["sourceId"] for item in manifest}
        manifest = [item for item in previous if item.get("sourceId") not in selected_ids] + manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "sourcesSeen": len(manifest),
                "ingested": sum(1 for item in manifest if item["status"] == "ingested"),
                "failed": sum(1 for item in manifest if item["status"] == "failed"),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
