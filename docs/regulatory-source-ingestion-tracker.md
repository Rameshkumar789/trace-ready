# TraceReady Regulatory Source Ingestion Tracker

Last updated: 2026-06-16

This file is the control tracker for the TraceReady regulatory intelligence source library. It separates legal authority, FDA implementation support, scenario examples, product-design evidence, and cross-reference sources so the system does not confuse guidance or proposed material with executable compliance logic.

## Ingestion Rules

- Binding legal text can produce executable rule cards only after schema validation and reviewer approval.
- FDA guidance can support explanations and reviewer notes, but must not override binding CFR text.
- Proposed rules, public meetings, discussion papers, and reports are change-monitoring or product-research sources, not executable rule logic.
- FDA templates, examples, and spreadsheets are implementation support. They can drive schemas and scenario tests, but findings still need citations to approved rule cards.
- Every source must preserve URL, source type, content date when available, retrieval timestamp, raw artifact path, normalized artifact path, content hash, and citation anchors.
- Every generated rule card, KDE requirement, scenario, and finding must cite one or more source chunks.

## Current Control Manifests

| Manifest | Purpose | Result |
|---|---|---|
| `traceready/data/regulatory/fda-fsma204-hub-ingestion-manifest.json` | FDA FSMA 204 final-rule hub crawl plus English/core sublinks, PDFs, workbooks, scenario slides/transcripts, FTL support documents, guidance, training pages, and change-monitoring sources. | 53 sources ingested, 0 failed, 983 chunks. |
| `traceready/data/regulatory/local-fda-documents-ingestion-manifest.json` | Local FDA/CFR document drop from `/Users/ramesh/Downloads/fda-documents`. | 29 files ingested, 12 exact duplicates skipped, 0 failed. |

Important correction from the 2026-06-16 pass:

- The FDA FSMA 204 final-rule hub page is not enough by itself. The hub links to core implementation artifacts that must be ingested separately.
- The Federal Register final rule PDF is now ingested as `fr-2022-24417-final-rule-pdf` from the official govinfo PDF URL.
- The Food Traceability List page is now treated as a product-scope source, and its risk-ranking/model/memo attachments are now ingested as product-scope support.
- PDF ingestion must be run with the bundled Codex Python runtime because the system Python does not include `pdfplumber`, `pypdf`, or `openpyxl`. If system Python is used, PDF chunks can silently degrade into raw `%PDF` bytes.

Use this runtime for production-quality local ingestion:

```bash
env SSL_CERT_FILE=/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/certifi/cacert.pem \
  /Users/ramesh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  ingest_fda_fsma204_hub_sources.py \
  --output-dir ../data/regulatory \
  --manifest ../data/regulatory/fda-fsma204-hub-ingestion-manifest.json \
  --include-traceready-context
```

## FDA FSMA 204 Hub Crawl: Core English Sources

This is the current source inventory generated from the FDA FSMA 204 final-rule hub and its English/core linked artifacts. Translations are intentionally excluded from the MVP rule engine unless multilingual support becomes a product requirement.

| Source ID | Tier | Current Status | Notes |
|---|---|---|---|
| `fda-fsma204-final-rule-page` | core hub | `ingested` | FDA operational hub and link source. |
| `ecfr-21-cfr-1-subpart-s` | binding rule | `ingested` | Primary executable legal source after approval. |
| `fr-2022-24417-final-rule` | binding rule history | `ingested` | Federal Register HTML page. |
| `fr-2022-24417-final-rule-pdf` | binding rule history | `ingested` | Official Federal Register PDF from govinfo; 58 readable chunks after layout-aware extraction. |
| `fda-food-traceability-list` | product scope | `ingested` | Covered food taxonomy and FTL notes. |
| `fda-ftl-risk-ranking-memo-final-rule` | product-scope support | `ingested` | Final-rule FTL memo. |
| `fda-ftl-risk-ranking-designation-memo` | product-scope support | `ingested` | Designation memo using the risk-ranking model. |
| `fda-ftl-risk-ranking-methodology` | product-scope support | `ingested` | Risk-ranking methodology. |
| `fda-ftl-risk-ranking-results-table-1a` | product-scope support | `ingested` | FTL commodity risk-score table. |
| `fda-ftl-risk-ranking-results-table-1b` | product-scope support | `ingested` | FTL commodity-hazard pair table. |
| `fda-ftl-risk-ranking-results-all` | product-scope support | `ingested` | All commodities and commodity-hazard pairs. |
| `fda-ftl-risk-ranking-references` | product-scope support | `ingested` | Risk-ranking reference list. |
| `fda-risk-ranking-model-web-app` | product-scope support | `ingested` | FDA interactive risk-ranking model web application landing page. |
| `fda-fish-guidance-chapter-3` | cross-reference | `ingested` | Finfish examples referenced by FTL footnote. |
| `fda-cte-kde-pdf` | CTE/KDE schema support | `ingested` | FDA CTE/KDE visual guide; 11 readable chunks. |
| `fda-traceability-lot-code` | TLC support | `ingested` | TLC assignment and source-reference support. |
| `fda-sortable-spreadsheet-xlsx` | export schema | `ingested` | FDA blank electronic sortable spreadsheet workbook. |
| `fda-sortable-spreadsheet-pdf` | export schema | `ingested` | PDF rendering of the blank spreadsheet. |
| `fda-sortable-spreadsheet-sample-xlsx` | export schema sample | `ingested` | FDA sample-data workbook. |
| `fda-sortable-spreadsheet-sample-pdf` | export schema sample | `ingested` | PDF rendering of the sample workbook. |
| `fda-qa-guidance-2026` | guidance | `ingested` | Q&A guidance source; support/reviewer use only. |
| `fda-small-entity-guide-2023` | guidance | `ingested` | Small-entity guide; support/reviewer use only. |
| `fda-faq-food-traceability-rule` | guidance | `ingested` | FDA operational FAQ. |
| `fda-at-a-glance` | summary | `ingested` | FDA summary document. |
| `scenario-produce-cucumbers-transcript` | scenario | `ingested` | Golden scenario source. |
| `scenario-produce-cucumbers-slides` | scenario | `ingested` | Golden scenario source. |
| `scenario-seafood-tuna-transcript` | scenario | `ingested` | Golden scenario source. |
| `scenario-seafood-tuna-slides` | scenario | `ingested` | Golden scenario source. |
| `scenario-cheese-transcript` | scenario | `ingested` | Golden scenario source. |
| `scenario-cheese-slides` | scenario | `ingested` | Golden scenario source. |
| `scenario-deli-salad-slides` | scenario | `ingested` | Golden scenario source. |
| `scenario-sprouts-slides` | scenario | `ingested` | Golden scenario source. |
| `scenario-additional-supply-chain-examples-2024` | scenario | `ingested` | Additional scenario source. |
| `scenario-additional-supply-chain-examples-2025-08` | scenario | `ingested` | Additional August 2025 scenario source. |
| `traceability-plan-farms` | traceability plan example | `ingested` | Traceability plan benchmark. |
| `traceability-plan-restaurants` | traceability plan example | `ingested` | Traceability plan benchmark. |
| `traceability-plan-sprouters` | traceability plan example | `ingested` | Traceability plan benchmark. |
| `traceability-plan-food-processors` | traceability plan example | `ingested` | Traceability plan benchmark. |
| `traceability-plan-distribution-centers` | traceability plan example | `ingested` | Traceability plan benchmark. |
| `traceability-plan-seafood-processing` | traceability plan example | `ingested` | Traceability plan benchmark. |
| `traceability-plan-aquaculture` | traceability plan example | `ingested` | Traceability plan benchmark. |
| `rfe-restaurants-records-needed` | operator support | `ingested` | RFE/restaurant recordkeeping support. |
| `rfe-restaurants-rule-overview` | operator support | `ingested` | RFE/restaurant overview. |
| `rfe-restaurants-traceability-plan` | operator support | `ingested` | RFE/restaurant traceability plan support. |
| `produce-farms-coverage-exemptions` | operator support | `ingested` | Produce farm coverage/exemption support. |
| `produce-farms-recordkeeping` | operator support | `ingested` | Produce farm recordkeeping support. |
| `fda-produce-farms-exemptions` | exemption support | `ingested` | Produce Safety Rule cross-reference. |
| `fda-final-rule-regulatory-impact-analysis` | market impact | `ingested` | Economic impact analysis page. |
| `fda-webinar-food-traceability-final-rule-2022-12-07` | training support | `ingested` | FDA webinar page for the Food Traceability Final Rule held on December 7, 2022. |
| `fda-lot-level-flexibility-discussion-paper` | change monitor | `ingested` | Lot-level tracking flexibility discussion paper. |
| `fda-tabletop-exercises-report` | product research | `ingested` | Real implementation challenge source. |
| `fr-2025-compliance-date-extension` | change monitor | `ingested` | Proposed extension/current change monitor. |
| `fr-2026-cottage-cheese-exemption` | exemption change monitor | `ingested` | Cottage cheese exemption notice. |

Quality notes from this pass:

- Final-rule PDF chunks are now readable legal text, not raw PDF bytes.
- FTL risk-ranking PDFs are readable and preserve table text enough for support/search; typed table normalization is still required before turning them into structured product-scope objects.
- CTE/KDE PDF chunks are readable, but the next accuracy step is typed extraction into `CTE -> KDE -> required/conditional -> citation`.
- Scenario slides/transcripts are now searchable source chunks, but should become curated golden test cases before they drive audit logic.

## Status Legend

| Status | Meaning |
|---|---|
| `ingested` | Raw and normalized artifacts exist in `traceready/data/regulatory`. |
| `indexed` | Source row/metadata is captured, but linked content has not been fetched and chunked yet. |
| `pending_ingestion` | Known required source, not yet ingested. |
| `blocked_by_extractor` | Source requires PDF/XLSX/table-specific ingestion work before it can be accurately normalized. |
| `monitor_only` | Track changes, do not use for executable findings. |
| `support_only` | Use for explanations, scenario tests, UI, or reviewer training, not direct findings. |

## Resolved Source URL Index

Use this as the canonical link list for ingestion jobs. Rows that say `source page anchor` are tracked as sections inside the FDA FSMA 204 final-rule page artifact.

| Source ID | Source URL |
|---|---|
| `ecfr-21-cfr-1-subpart-s` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-S |
| `ecfr-21-cfr-1-subpart-s-api` | https://www.ecfr.gov/api/versioner/v1/full/2026-06-11/title-21.xml?part=1 |
| `fr-2022-24417-final-rule` | https://www.federalregister.gov/documents/2022/11/21/2022-24417/requirements-for-additional-traceability-records-for-certain-foods |
| `fr-2023-technical-amendment` | https://www.federalregister.gov/documents/2023/09/26/2023-20898/requirements-for-additional-traceability-records-for-certain-foods-technical-amendment |
| `fr-2025-compliance-date-extension` | https://www.federalregister.gov/documents/2025/08/07/2025-14967/requirements-for-additional-traceability-records-for-certain-foods-compliance-date-extension |
| `fr-2026-cottage-cheese-exemption` | https://www.federalregister.gov/documents/2026/02/20/2026-03362/requirements-for-additional-traceability-records-for-certain-foods-exemption-for-cottage-cheese |
| `fda-fsma-rules-guidance-industry` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-rules-guidance-industry |
| `fda-fsma204-final-rule-page` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods |
| `fda-food-traceability-list` | https://www.fda.gov/food/food-safety-modernization-act-fsma/food-traceability-list |
| `fda-cte-kde` | https://www.fda.gov/media/163132/download?attachment |
| `fda-traceability-lot-code` | https://www.fda.gov/food/food-safety-modernization-act-fsma/traceability-lot-code |
| `fda-exemptions-tool` | https://collaboration.fda.gov/tefcv13/ |
| `fda-produce-farms-exemptions` | https://www.fda.gov/food/food-safety-modernization-act-fsma/exemptions-relevant-produce-farms-under-produce-safety-rule-and-food-traceability-rule |
| `fda-modified-requirements-waivers` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods#6a2fec02d1588 |
| `fda-sortable-spreadsheet-xlsx` | https://www.fda.gov/media/179617/download?attachment |
| `fda-sortable-spreadsheet-pdf` | https://www.fda.gov/media/179616/download?attachment |
| `fda-sortable-spreadsheet-sample-xlsx` | https://www.fda.gov/media/181946/download?attachment |
| `fda-sortable-spreadsheet-sample-pdf` | https://www.fda.gov/media/181945/download?attachment |
| `fda-qa-guidance-2026` | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-about-requirements-additional-traceability-records-certain-foods |
| `fda-small-entity-guide-2023` | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/small-entity-compliance-guide-requirements-additional-traceability-records-certain-foods-what-you |
| `fda-faq-food-traceability-rule` | https://www.fda.gov/food/food-safety-modernization-act-fsma/frequently-asked-questions-fsma-food-traceability-rule |
| `fda-at-a-glance` | https://www.fda.gov/media/183514/download?attachment |
| `fda-risk-ranking-model-web-app` | https://hfpappexternal.fda.gov/scripts/FDARiskRankingModelforFoodTracingfinalrule/ |
| `fda-webinar-food-traceability-final-rule-2022-12-07` | https://www.fda.gov/food/workshops-meetings-webinars-food-and-dietary-supplements/webinar-food-traceability-final-rule-12072022 |
| `fspca-ftr-training` | https://www.fspca.net/ |
| `scenario-produce-cucumbers-transcript` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods#6a2fec02d16dd |
| `scenario-produce-cucumbers-video` | https://youtu.be/ |
| `scenario-seafood-tuna-transcript` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods#6a2fec02d16dd |
| `scenario-seafood-tuna-video` | https://youtu.be/ |
| `scenario-cheese-transcript` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods#6a2fec02d16dd |
| `scenario-cheese-video` | https://youtu.be/ |
| `scenario-deli-salad` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods#6a2fec02d16dd |
| `scenario-sprouts` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods#6a2fec02d16dd |
| `scenario-additional-2025` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods#6a2fec02d16dd |
| `scenario-additional-2025-august` | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods#6a2fec02d16dd |
| `traceability-plan-farms` | https://www.fda.gov/media/174057/download?attachment |
| `traceability-plan-restaurants` | https://www.fda.gov/media/174058/download?attachment |
| `traceability-plan-sprouters` | https://www.fda.gov/media/181575/download?attachment |
| `traceability-plan-food-processors` | https://www.fda.gov/media/188100/download?attachment |
| `traceability-plan-distribution-centers` | https://www.fda.gov/media/188101/download?attachment |
| `traceability-plan-seafood-processing` | https://www.fda.gov/media/188102/download?attachment |
| `traceability-plan-aquaculture` | https://www.fda.gov/media/188103/download?attachment |
| `fda-whats-new-fsma` | https://www.fda.gov/food/food-safety-modernization-act-fsma/whats-new-fsma |
| `fda-lot-level-flexibility-discussion-paper` | https://www.fda.gov/media/192696/download?attachment |
| `fda-tabletop-exercises-report` | https://www.fda.gov/media/192993/download?attachment |
| `fda-public-meeting-2026` | https://www.federalregister.gov/documents/2026/05/28/2026-09537/challenges-and-solutions-in-lot-level-food-traceability-public-meeting-and-request-for-comments |
| `cfr-21-112-2` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-112/subpart-A/section-112.2 |
| `cfr-21-123` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-123 |
| `cfr-21-123-3` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-123/subpart-A/section-123.3 |
| `cfr-21-1240-60` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-L/part-1240/subpart-D/section-1240.60 |
| `cfr-21-133-150` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-133/subpart-B/section-133.150 |
| `cfr-21-133-118` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-133/subpart-B/section-133.118 |
| `cfr-21-133-111` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-B/part-133/subpart-B/section-133.111 |
| `cfr-21-1-subpart-j` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-J |
| `cfr-21-10-30` | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-10/subpart-B/section-10.30 |


## Current Ingestion Artifact Summary

This is the current state of `traceready/data/regulatory` after the 2026-06-16 ingestion pass.

| Source ID | Sections | Chunks | Rejected | Content Type | Normalized Artifact |
|---|---:|---:|---:|---|---|
| `ecfr-21-cfr-1-subpart-s` | 33 | 33 | 0 | XML/API text | `traceready/data/regulatory/ecfr-21-cfr-1-subpart-s/normalized/ecfr-21-cfr-1-subpart-s.json` |
| `fda-fsma-rules-guidance-industry` | 94 | 94 | 0 | HTML index | `traceready/data/regulatory/fda-fsma-rules-guidance-industry/normalized/fda-fsma-rules-guidance-industry.json` |
| `fda-fsma204-final-rule-page` | 31 | 31 | 0 | HTML | `traceready/data/regulatory/fda-fsma204-final-rule-page/normalized/fda-fsma204-final-rule-page.json` |
| `fda-food-traceability-list` | 8 | 8 | 0 | HTML | `traceready/data/regulatory/fda-food-traceability-list/normalized/fda-food-traceability-list.json` |
| `fr-2022-24417-final-rule` | 2 | 2 | 0 | HTML | `traceready/data/regulatory/fr-2022-24417-final-rule/normalized/fr-2022-24417-final-rule.json` |
| `fr-2025-compliance-date-extension` | 2 | 2 | 0 | HTML | `traceready/data/regulatory/fr-2025-compliance-date-extension/normalized/fr-2025-compliance-date-extension.json` |
| `fda-qa-guidance-2026` | 6 | 6 | 0 | HTML | `traceready/data/regulatory/fda-qa-guidance-2026/normalized/fda-qa-guidance-2026.json` |
| `fda-small-entity-guide-2023` | 7 | 7 | 0 | HTML | `traceready/data/regulatory/fda-small-entity-guide-2023/normalized/fda-small-entity-guide-2023.json` |
| `fda-faq-food-traceability-rule` | 5 | 5 | 0 | HTML | `traceready/data/regulatory/fda-faq-food-traceability-rule/normalized/fda-faq-food-traceability-rule.json` |
| `fda-traceability-lot-code` | 15 | 15 | 0 | HTML | `traceready/data/regulatory/fda-traceability-lot-code/normalized/fda-traceability-lot-code.json` |
| `fda-produce-farms-exemptions` | 3 | 3 | 0 | HTML | `traceready/data/regulatory/fda-produce-farms-exemptions/normalized/fda-produce-farms-exemptions.json` |
| `fda-whats-new-fsma` | 4 | 4 | 0 | HTML | `traceready/data/regulatory/fda-whats-new-fsma/normalized/fda-whats-new-fsma.json` |
| `fda-cte-kde` | 11 | 11 | 0 | PDF | `traceready/data/regulatory/fda-cte-kde/normalized/fda-cte-kde.json` |
| `fda-at-a-glance` | 4 | 4 | 0 | PDF | `traceready/data/regulatory/fda-at-a-glance/normalized/fda-at-a-glance.json` |
| `fda-lot-level-flexibility-discussion-paper` | 9 | 9 | 0 | PDF | `traceready/data/regulatory/fda-lot-level-flexibility-discussion-paper/normalized/fda-lot-level-flexibility-discussion-paper.json` |
| `fda-tabletop-exercises-report` | 10 | 10 | 0 | PDF | `traceready/data/regulatory/fda-tabletop-exercises-report/normalized/fda-tabletop-exercises-report.json` |
| `fda-sortable-spreadsheet-xlsx` | 15 | 15 | 0 | XLSX | `traceready/data/regulatory/fda-sortable-spreadsheet-xlsx/normalized/fda-sortable-spreadsheet-xlsx.json` |
| `fda-sortable-spreadsheet-sample-xlsx` | 15 | 15 | 0 | XLSX | `traceready/data/regulatory/fda-sortable-spreadsheet-sample-xlsx/normalized/fda-sortable-spreadsheet-sample-xlsx.json` |
| `fda-sortable-spreadsheet-pdf` | 50 | 50 | 0 | PDF | `traceready/data/regulatory/fda-sortable-spreadsheet-pdf/normalized/fda-sortable-spreadsheet-pdf.json` |
| `fda-sortable-spreadsheet-sample-pdf` | 100 | 100 | 0 | PDF | `traceready/data/regulatory/fda-sortable-spreadsheet-sample-pdf/normalized/fda-sortable-spreadsheet-sample-pdf.json` |
| `traceability-plan-farms` | 3 | 3 | 0 | PDF | `traceready/data/regulatory/traceability-plan-farms/normalized/traceability-plan-farms.json` |
| `traceability-plan-restaurants` | 2 | 2 | 0 | PDF | `traceready/data/regulatory/traceability-plan-restaurants/normalized/traceability-plan-restaurants.json` |
| `traceability-plan-sprouters` | 3 | 3 | 0 | PDF | `traceready/data/regulatory/traceability-plan-sprouters/normalized/traceability-plan-sprouters.json` |
| `traceability-plan-food-processors` | 2 | 2 | 0 | PDF | `traceready/data/regulatory/traceability-plan-food-processors/normalized/traceability-plan-food-processors.json` |
| `traceability-plan-distribution-centers` | 2 | 2 | 0 | PDF | `traceready/data/regulatory/traceability-plan-distribution-centers/normalized/traceability-plan-distribution-centers.json` |
| `traceability-plan-seafood-processing` | 2 | 2 | 0 | PDF | `traceready/data/regulatory/traceability-plan-seafood-processing/normalized/traceability-plan-seafood-processing.json` |
| `traceability-plan-aquaculture` | 2 | 2 | 0 | PDF | `traceready/data/regulatory/traceability-plan-aquaculture/normalized/traceability-plan-aquaculture.json` |

### Current Quality Notes

- PDF ingestion now uses `pdfplumber`, then `pypdf`, then PyMuPDF/fallback. Earlier raw-PDF byte chunks were regenerated with real extracted text.
- Federal Register PDF ingestion now uses layout-aware column ordering before semantic sectioning. This is required because naive text extraction scrambles multi-column pages.
- XLSX ingestion now extracts workbook sheets, preserving sheet names and rows as source chunks. This is enough to start deriving FDA export schemas from the sortable spreadsheet.
- Federal Register HTML pages are still coarse, but local Federal Register PDFs are now better source artifacts: final rule PDF is split into 58 semantic chunks; 2025 extension PDF into 12 chunks; 2026 cottage cheese exemption into 5 chunks.
- HTML article pages are acceptable for source discovery and support chunks, but CTE/KDE and FTL tables will need structured table normalization before they can become production-grade schemas.

## Local FDA Document Drop Ingestion

Local source folder: `/Users/ramesh/Downloads/fda-documents`

Manifest: `traceready/data/regulatory/local-fda-documents-ingestion-manifest.json`

Run result:

| Metric | Count |
|---|---:|
| Files seen | 41 |
| Files ingested | 29 |
| Exact duplicates skipped | 12 |
| Failed files | 0 |

Important local-ingestion improvements added:

- Local batch importer maps downloaded FDA/CFR filenames to tracker source IDs.
- Exact duplicate PDFs are skipped by SHA-256 hash.
- PDF extraction now uses semantic sectioning instead of only page-level chunks.
- Federal Register PDFs use layout-aware word-coordinate ordering so text is read down each column before moving to the next column.
- CFR/eCFR PDFs are split by `§` section references.
- CFR/eCFR PDFs are deduplicated by section reference, keeping the longest body chunk.
- Source-specific CFR range filtering is applied for Subpart S and Subpart J so broad CFR PDFs do not pollute the source library.
- XLSX templates are ingested by workbook sheet.

Additional local sources now ingested:

| Source ID | Local Document Role | Sections | Notes |
|---|---:|---:|---|
| `fr-2022-24417-final-rule-pdf` | Federal Register final rule PDF | 58 | Layout-aware column extraction plus semantic sectioning. Use as final-rule reasoning/history support; eCFR XML remains executable legal truth. |
| `fr-2023-technical-amendment` | Technical amendment PDF | 2 | Change-monitoring source. |
| `fr-2025-compliance-date-extension-pdf` | Compliance-date extension PDF | 12 | Proposed/update source; do not execute as final rule logic. |
| `fr-2026-cottage-cheese-exemption` | Cottage cheese exemption notice | 5 | Exemption/change-monitoring source with clean section-level chunks. |
| `fda-public-meeting-2026` | Public meeting notice | 2 | Product research and change monitor. |
| `ecfr-21-cfr-1-subpart-s-pdf` | Local PDF copy of Subpart S | 33 | Cross-check source; use eCFR XML as primary executable legal text. |
| `cfr-21-1-subpart-j` | Existing recordkeeping context | 8 | Scoped to Subpart J after range filtering. |
| `cfr-21-10-30` | Citizen petition procedure | 1 | Exemption/petition support. |
| `cfr-21-112-2` | Produce exemptions | 1 | FTL/exemption edge-case support. |
| `cfr-21-123` | Seafood HACCP part | 14 | Seafood context; broad support source. |
| `cfr-21-123-3` | Seafood definitions | 1 | Seafood definitions. |
| `cfr-21-1240-60` | Molluscan shellfish | 3 | Shellfish context. |
| `cfr-21-133-111` | Cheese definition | 1 | Needs manual verification because local PDF text begins near adjacent cheese sections. |
| `cfr-21-133-118` | Colby cheese definition | 2 | Cheese classification support. |
| `cfr-21-133-150` | Hard cheeses definition | 2 | Cheese classification support. |
| `fda-qa-guidance-2026-pdf` | Q&A draft guidance PDF | 46 | Guidance only; TOC sections are still present and should be excluded before rule-card drafting. |
| `fda-small-entity-guide-2023-pdf` | Small Entity Compliance Guide PDF | 86 | Guidance only; TOC sections are still present and should be excluded before rule-card drafting. |
| `fda-cte-kde-pdf` | FDA CTE/KDE PDF | 11 | Core schema support. Needs table normalization into typed KDE requirements. |
| `fda-sortable-spreadsheet-xlsx` | FDA blank export workbook | 15 | Core export schema support. |
| `fda-sortable-spreadsheet-sample-xlsx` | FDA sample export workbook | 15 | Golden output/sample-data support. |

Accuracy caveats after local ingestion:

- The eCFR XML artifact remains the primary source for executable Subpart S rule cards. The local Subpart S PDF is useful as a cross-check.
- Federal Register final-rule PDF extraction is now column-aware. Still use it as supporting history/rationale; do not make it the primary executable source while current eCFR XML is available.
- Q&A and Small Entity Guide PDFs include table-of-contents chunks. These are safe in the source library but should be filtered before LLM drafting.
- CTE/KDE PDF and FDA spreadsheet workbooks are ingested, but the next accuracy step is typed table extraction: `CTE -> KDE -> required/conditional -> citation`.
- If rule-card drafting starts now, use source filters: `authority=codified_rule`, `source_id=ecfr-21-cfr-1-subpart-s`, plus FTL and typed FDA spreadsheet/CTE-KDE tables after normalization.

## Tier 1: Binding Rule Sources

| ID | Source | URL | Authority Role | Product Use | Status | Artifact |
|---|---|---|---|---|---|---|
| `ecfr-21-cfr-1-subpart-s` | eCFR 21 CFR Part 1 Subpart S, Additional Traceability Records for Certain Foods | https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-S | Current codified legal text | Executable rule cards for scope, exemptions, CTEs, KDEs, TLCs, traceability plan, record retention, sortable export, 24-hour response | `ingested` from eCFR XML sample previously; persist final repo artifact if missing | `traceready/data/regulatory/fsma204-source-chunks.json` plus future normalized source folder |
| `fr-2022-24417-final-rule` | Federal Register Final Rule, Requirements for Additional Traceability Records for Certain Foods, 87 FR 70910 | https://www.federalregister.gov/documents/2022/11/21/2022-24417/requirements-for-additional-traceability-records-for-certain-foods | Final rule history and reasoning | Interpret edge cases, connect CFR sections to final-rule rationale | `pending_ingestion` | TBD |
| `fr-2023-technical-amendment` | Federal Register technical amendment / correction under FDA-2014-N-0053 | Federal Register related document under FDA-2014-N-0053 | Amendment/change authority | Prevent stale final-rule interpretation | `pending_ingestion` | TBD |

## Tier 2: FDA Core Implementation Sources

| ID | Source | URL | Authority Role | Product Use | Status | Artifact |
|---|---|---|---|---|---|---|
| `fda-fsma204-final-rule-page` | FDA FSMA Final Rule on Requirements for Additional Traceability Records for Certain Foods | https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods | FDA operational hub | Source discovery, CTE/KDE/TLC/exemption/template/example links, product explanations | `pending_ingestion` | TBD |
| `fda-food-traceability-list` | FDA Food Traceability List | https://www.fda.gov/food/food-safety-modernization-act-fsma/food-traceability-list | Product scope source | Determine whether a food is on the FTL; maintain covered-product taxonomy | `pending_ingestion` | TBD |
| `fda-cte-kde` | FDA Critical Tracking Events and Key Data Elements | Linked from FDA FSMA 204 final-rule page | FDA implementation support | KDE schemas by CTE; scenario/test scaffolding | `pending_ingestion` | TBD |
| `fda-traceability-lot-code` | FDA Traceability Lot Code page | Linked from FDA FSMA 204 final-rule page | FDA implementation support | TLC assignment, preservation, source reference, and gap checks | `pending_ingestion` | TBD |
| `fda-exemptions-tool` | FDA Exemptions to the Food Traceability Rule | Linked from FDA FSMA 204 final-rule page | Exemption support | Exemption triage and reviewer workflows | `pending_ingestion` | TBD |
| `fda-modified-requirements-waivers` | FDA modified requirements, exemptions, and waivers materials | Linked from FDA FSMA 204 final-rule page and CFR §§ 1.1360-1.1450 | Exemption/change support | Waiver/exemption state and monitor logic | `pending_ingestion` | TBD |

## Tier 3: FDA Output Schema and Templates

| ID | Source | URL | Authority Role | Product Use | Status | Artifact |
|---|---|---|---|---|---|---|
| `fda-sortable-spreadsheet-xlsx` | FDA Electronic Sortable Spreadsheet in Excel | Linked from FDA FSMA 204 final-rule page | Implementation template | TraceReady export schema; CTE tabs; KDE column naming | `blocked_by_extractor` | Needs XLSX ingestion/table parser |
| `fda-sortable-spreadsheet-pdf` | FDA Electronic Sortable Spreadsheet in PDF | Linked from FDA FSMA 204 final-rule page | Implementation template | Cross-check export schema and citations | `blocked_by_extractor` | Needs PDF ingestion path |
| `fda-sortable-spreadsheet-sample-xlsx` | FDA Electronic Sortable Spreadsheet with Sample Data in Excel | Linked from FDA FSMA 204 final-rule page | Implementation sample | Golden output and demo workbook alignment | `blocked_by_extractor` | Needs XLSX ingestion/table parser |
| `fda-sortable-spreadsheet-sample-pdf` | FDA Electronic Sortable Spreadsheet with Sample Data in PDF | Linked from FDA FSMA 204 final-rule page | Implementation sample | Visual/schema cross-check | `blocked_by_extractor` | Needs PDF ingestion path |

## Tier 4: FDA Guidance and Reviewer Support

| ID | Source | URL | Authority Role | Product Use | Status | Artifact |
|---|---|---|---|---|---|---|
| `fda-qa-guidance-2026` | Questions and Answers About Requirements for Additional Traceability Records for Certain Foods | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/questions-and-answers-about-requirements-additional-traceability-records-certain-foods | Draft guidance / interpretation support | Reviewer notes, practical interpretation, customer explanations | `indexed` from FDA FSMA rules page; linked content pending | `traceready/data/regulatory/fda-fsma-rules-guidance-industry/normalized/fda-fsma-rules-guidance-industry.json` |
| `fda-small-entity-guide-2023` | Small Entity Compliance Guide: Requirements for Additional Traceability Records for Certain Foods | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/small-entity-compliance-guide-requirements-additional-traceability-records-certain-foods-what-you | Guidance / small-operator support | Translate rule into smaller-operator workflows | `indexed` from FDA FSMA rules page; linked content pending | `traceready/data/regulatory/fda-fsma-rules-guidance-industry/normalized/fda-fsma-rules-guidance-industry.json` |
| `fda-faq-food-traceability-rule` | Frequently Asked Questions: FSMA Food Traceability Rule | https://www.fda.gov/food/food-safety-modernization-act-fsma/frequently-asked-questions-fsma-food-traceability-rule | FAQ support | Operational Q&A and reviewer context | `pending_ingestion` | TBD |
| `fda-at-a-glance` | Food Traceability Rule At-A-Glance | Linked from FDA FSMA 204 final-rule page | Summary support | UI/explanation content, not executable findings | `pending_ingestion` | TBD |
| `fspca-ftr-training` | FSPCA Food Traceability Rule training | Linked from FDA FSMA 204 final-rule page | Training support | Reviewer training and onboarding | `support_only` | Not first ingestion target |

## Tier 5: FDA Scenario and Benchmark Sources

| ID | Source | URL | Product Use | Status |
|---|---|---|---|---|
| `scenario-produce-cucumbers` | FDA produce supply-chain example: fresh cucumbers | Linked from FDA FSMA 204 final-rule page | Golden scenario tests for harvest, cooling, initial packing, shipping, receiving | `pending_ingestion` |
| `scenario-seafood-tuna` | FDA seafood supply-chain example: tuna steaks | Linked from FDA FSMA 204 final-rule page | Golden scenario tests for first land-based receiving and seafood flow | `pending_ingestion` |
| `scenario-cheese` | FDA cheese supply-chain example | Linked from FDA FSMA 204 final-rule page | Golden scenario tests for cheese scope and transformation | `pending_ingestion` |
| `scenario-deli-salad` | FDA deli salad example | Linked from FDA FSMA 204 final-rule page | Transformation and RTE scenario tests | `pending_ingestion` |
| `scenario-sprouts` | FDA sprouts example | Linked from FDA FSMA 204 final-rule page | Sprout-specific scenario tests | `pending_ingestion` |
| `scenario-additional-2025` | FDA additional supply-chain examples: aquacultured tilapia, canned tomatoes, canned salmon, imported mangos, shell eggs, fresh produce meal kits | Linked from FDA FSMA 204 final-rule page | Edge-case scenario library | `pending_ingestion` |
| `scenario-additional-2025-august` | FDA added examples: shell eggs, frozen produce, fresh-cut produce, farm-packed produce, food hubs, peanut butter crackers, dual jurisdiction facilities | Linked from FDA FSMA 204 final-rule page | Edge-case scenario library | `pending_ingestion` |

## Tier 6: Traceability Plan Examples

| ID | Source | URL | Product Use | Status |
|---|---|---|---|---|
| `traceability-plan-farms` | Traceability Plan Example for Farms | Linked from FDA FSMA 204 final-rule page | Traceability plan audit benchmark | `pending_ingestion` |
| `traceability-plan-restaurants` | Traceability Plan Example for Restaurants | Linked from FDA FSMA 204 final-rule page | RFE/restaurant plan benchmark | `pending_ingestion` |
| `traceability-plan-sprouters` | Traceability Plan Example for Sprouters | Linked from FDA FSMA 204 final-rule page | Sprouter plan benchmark | `pending_ingestion` |
| `traceability-plan-food-processors` | Traceability Plan Example for Food Processors | Linked from FDA FSMA 204 final-rule page | Processor plan benchmark | `pending_ingestion` |
| `traceability-plan-distribution-centers` | Traceability Plan Example for Distribution Centers | Linked from FDA FSMA 204 final-rule page | Distributor/DC plan benchmark | `pending_ingestion` |
| `traceability-plan-seafood-processing` | Traceability Plan Example for Seafood Processing Facilities | Linked from FDA FSMA 204 final-rule page | Seafood processor plan benchmark | `pending_ingestion` |
| `traceability-plan-aquaculture` | Traceability Plan Example for Aquaculture Farms | Linked from FDA FSMA 204 final-rule page | Aquaculture plan benchmark | `pending_ingestion` |

## Tier 7: Change Monitoring and Market Pain Sources

| ID | Source | URL | Product Use | Status |
|---|---|---|---|---|
| `fr-2025-compliance-date-extension` | Requirements for Additional Traceability Records for Certain Foods: Compliance Date Extension | https://www.federalregister.gov/documents/2025/08/07/2025-14967/requirements-for-additional-traceability-records-for-certain-foods-compliance-date-extension | Compliance-date monitor only | `indexed` from FDA FSMA rules page; linked content pending |
| `fda-whats-new-fsma` | FDA What's New in FSMA | https://www.fda.gov/food/food-safety-modernization-act-fsma/whats-new-fsma | Regulatory change monitor | `pending_ingestion` |
| `fda-lot-level-flexibility-discussion-paper` | Discussion Paper: Identifying Additional Flexibilities for Satisfying the Food Traceability Rule's Lot-Level Tracking Requirement | Linked from FDA FSMA 204 final-rule page | Product design and future rule-change monitor | `pending_ingestion` |
| `fda-tabletop-exercises-report` | FDA Traceability Readiness Tabletop Exercises Final Report | Linked from FDA FSMA 204 final-rule page | Product pain points, workflow and exception design | `pending_ingestion` |
| `fda-public-meeting-2026` | Challenges and Solutions in Lot-Level Food Traceability; Public Meeting and Request for Comments | Federal Register related document under FDA-2014-N-0053 | Product research and change monitor | `pending_ingestion` |

## Tier 8: Cross-Reference CFR Sources

| ID | Source | URL | Product Use | Status |
|---|---|---|---|---|
| `cfr-21-112-2` | 21 CFR 112.2 | Produce exemptions and produce-safety references | FTL and exemption edge cases | `pending_ingestion` |
| `cfr-21-123` | 21 CFR Part 123 | Seafood HACCP references | Seafood/shellfish edge cases | `pending_ingestion` |
| `cfr-21-1240-60` | 21 CFR 1240.60 | Shellfish control reference | Shellfish exemption edge cases | `pending_ingestion` |
| `cfr-21-123-3` | 21 CFR 123.3 | Seafood definitions | Definitions for seafood and smoked fish references | `pending_ingestion` |
| `cfr-21-133-150` | 21 CFR 133.150 | Hard cheese definition | Cheese classification | `pending_ingestion` |
| `cfr-21-133-118` | 21 CFR 133.118 | Colby cheese definition | Cheese classification | `pending_ingestion` |
| `cfr-21-133-111` | 21 CFR 133.111 | Caciocavallo siciliano cheese definition | Cheese classification | `pending_ingestion` |
| `cfr-21-1-subpart-j` | 21 CFR Part 1 Subpart J | Existing food recordkeeping context | Background/supporting recordkeeping context | `pending_ingestion` |
| `cfr-21-10-30` | 21 CFR 10.30 | Citizen petitions | Exemption and modified-requirement process | `pending_ingestion` |

## Already Indexed Source Registry

| Source | Status | Notes |
|---|---|---|
| FDA FSMA Rules & Guidance for Industry page | `ingested` | 94 entries, 94 chunks, 0 rejected. This is an index/registry, not recursive linked-content ingestion. |

## Next Ingestion Order

1. Persist current eCFR Subpart S XML normalized artifact under a dedicated folder.
2. Ingest FDA FSMA 204 final-rule page.
3. Ingest FDA Food Traceability List.
4. Ingest Federal Register final rule.
5. Ingest Q&A guidance and Small Entity Compliance Guide.
6. Ingest FAQ, CTE/KDE page, TLC page, and exemptions pages.
7. Build PDF/XLSX ingestion for sortable spreadsheet templates and FDA example slides.
8. Ingest scenario examples and traceability plan examples.
9. Ingest cross-reference CFR sections.
10. Build change monitor for FDA What's New, Federal Register docket, and FDA-2014-N-0053 related documents.
