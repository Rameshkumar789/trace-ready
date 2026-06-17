# TraceReady Regulatory Intelligence Task Tracker

Date created: 2026-06-16  
Owner: TraceReady founding team  
Status: active planning and implementation tracker

## Purpose

This tracker controls the build of TraceReady's regulatory intelligence layer.

The objective is not to "ask AI what FSMA 204 says." The objective is to build a versioned, cited, reviewer-approved regulatory knowledge system that can later power deterministic customer audits.

Core pipeline:

```text
official source
-> source artifact
-> source chunk
-> typed extraction draft
-> schema validation
-> citation span validation
-> obligation table
-> reviewer approval
-> regression scenario test
-> approved structured rule
-> customer audit engine
```

## Accuracy Principles

- eCFR/current CFR is the primary executable legal authority.
- Federal Register final rule is legal history, rule reasoning, and section-by-section interpretation support.
- FDA guidance, FAQs, webinars, examples, and tabletop reports support reviewer interpretation and product design, but do not override CFR text.
- AI may draft structured records, but AI must not approve executable rules.
- Every obligation, CTE, KDE, TLC rule, exemption, traceability-plan requirement, export field, and scenario expectation must cite source chunks.
- Every citation must point to a real source chunk and should include a support span where possible.
- Drafts can be wrong. Approved records must be reviewer-controlled, versioned, and regression-tested.

## Status Legend

| Status | Meaning |
|---|---|
| `done` | Implemented and verified enough to build on. |
| `in_progress` | Currently being implemented or reviewed. |
| `next` | Immediate next build item. |
| `planned` | Needed, but not next. |
| `blocked` | Cannot proceed without decision, credentials, missing source, or technical dependency. |
| `defer` | Useful later, not required for the intelligence foundation. |

## Current Completed Foundation

| Item | Status | Evidence |
|---|---|---|
| FDA FSMA 204 hub source inventory created | `done` | `traceready/ingestion/ingest_fda_fsma204_hub_sources.py` |
| FDA FSMA 204 hub and core English sublinks ingested | `done` | `traceready/data/regulatory/fda-fsma204-hub-ingestion-manifest.json` |
| Hub ingestion result verified | `done` | 53 sources, 0 failed, 983 chunks |
| eCFR Subpart S filtered to correct section range | `done` | `ecfr-21-cfr-1-subpart-s`, 33 chunks from `§ 1.1300` through `§ 1.1465` |
| Local FDA document drop ingested | `done` | `traceready/data/regulatory/local-fda-documents-ingestion-manifest.json` |
| Final-rule PDF ingested as readable text chunks | `done` | `fr-2022-24417-final-rule-pdf`, 58 chunks |
| CTE/KDE PDF ingested as readable chunks | `done` | `fda-cte-kde-pdf`, 11 chunks |
| FTL risk-ranking support PDFs ingested | `done` | `fda-ftl-risk-ranking-*` artifacts |
| Source tracker updated | `done` | `traceready/docs/regulatory-source-ingestion-tracker.md` |
| Bad legacy manual KDE/rule/scenario JSON removed | `done` | old `kde-requirements`, `rule-cards`, `scenarios`, `fsma204-source-chunks.json`, and `fsma204-sources.json` removed |
| Canonical source registry generated | `done` | `traceready/data/regulatory/registry/sources.json`, 71 sources |
| Canonical source chunk index generated | `done` | `traceready/data/regulatory/registry/source-chunks.json`, 1,440 chunks |
| Source/chunk health report generated | `done` | `traceready/data/regulatory/registry/health-report.json`, 0 source issues, 0 chunk issues, 0 errors, 0 warnings |
| Health warning remediation completed | `done` | Oversized chunks split into citation-safe parts; 10 true boilerplate chunks removed; 22 scenario title/page-anchor chunks retained as `citation_only` |
| Core regulatory intelligence schemas validated | `done` | `traceready/data/regulatory/intelligence/schema-smoke-output.json`, 10 schema samples validated with real source citations |
| Phase 4 deterministic draft extraction completed | `done` | `traceready/data/regulatory/intelligence/drafts/phase4-summary.json`, 514 draft records generated with 514 complete citations |
| Phase 5 AI-assisted extraction guardrails completed | `done` | `traceready/data/regulatory/intelligence/phase5/prompts/phase5-prompt-pack.json` and `traceready/data/regulatory/intelligence/phase5/phase5-safety-check-report.json`; safety gate accepted supported draft, rejected unsupported draft, and marked conflicts |
| Phase 5 real AI extraction run | `done` | Real Anthropic extraction completed with prompt caching TTL `1h`; summary at `traceready/data/regulatory/intelligence/phase5/phase5-real-extraction-summary.json`. |
| Phase 5 Anthropic SDK configuration | `done` | `traceready/ingestion/scripts/intelligence/run_phase5_anthropic_extraction.py`, `traceready_ingestion/intelligence/anthropic_client.py`, and `traceready/ingestion/.env.example` configure Sonnet for extraction, Opus for conflict reasoning, and deterministic citation validation. |
| Phase 6 validation and review package | `done` | `traceready/ingestion/scripts/intelligence/build_phase6_review_package.py` generated `traceready/data/regulatory/intelligence/review/phase6-review-package.json`: 550 draft attempts, 534 ready for review, 16 rejected, 0 approved, 566 review log actions. |
| Phase 7 obligation inventory and approved set | `done` | `traceready/ingestion/scripts/intelligence/build_phase7_obligation_inventory.py` generated `traceready/data/regulatory/intelligence/obligations/phase7-summary.json`: 21 obligation drafts, 21 inventory records, 12 approved deterministic eCFR obligations, 0 invalid citations. |
| Phase 8 scenario regression benchmarks | `done` | `traceready/ingestion/scripts/intelligence/build_phase8_scenario_regressions.py` generated `traceready/data/regulatory/intelligence/scenarios/phase8-summary.json`: 6 FDA scenario benchmarks, 7 traceability-plan benchmarks, 13/13 regression passes, 22 valid citations, 0 invalid citations. |
| Phase 8 unseen web challenge evaluation | `done` | `traceready/ingestion/scripts/intelligence/build_phase8_unseen_web_challenges.py` generated `traceready/data/regulatory/intelligence/scenarios/phase8-unseen-web-challenge-summary.json`: 8 web-derived challenge scenarios, 5 pass, 3 gap, 62.5% pass rate. This is a generalization test, not an approved regulatory package. |
| Phase 8 all-structured-record shadow evaluation | `done` | `traceready/ingestion/scripts/intelligence/build_phase8_shadow_structured_record_eval.py` generated `traceready/data/regulatory/intelligence/scenarios/phase8-shadow-all-structured-records-summary.json`: loaded all 550 Phase 6 structured records against the 8 unseen challenges, found draft support for all 8, and surfaced 37 rejected-record matches as noise. |
| Phase 9 approved structured rule package | `done` | `traceready/ingestion/scripts/intelligence/build_phase9_approved_rule_package.py` generated `traceready/data/regulatory/intelligence/rules/phase9-summary.json`: immutable `approved-rule-package-v1`, 12 approved obligations, source version lock, 13/13 scenario regression passes, package hash, diff report, and active rollback pin. |
| Phase 10 customer evidence intelligence bridge | `done` | Baseline bridge completed, not arbitrary-customer-parser complete. `traceready/ingestion/scripts/intelligence/build_phase10_customer_evidence.py` generated `traceready/data/regulatory/intelligence/customer-evidence/phase10-summary.json`: 80 cell-level evidence records, 50 reviewable field mappings, 3 event nodes, receiving/shipping/transformation CTE classification, negative suppression tests, and 1 reviewer question. Phase 10B-10C hardening is required before production-grade customer evidence execution. |
| Phase 10A customer evidence ingestion hardening | `done` | `traceready_ingestion.intelligence.customer_evidence` now handles blank header bands, repeated headers, hidden XLSX rows/columns, merged cells, workbook formula fallback, filename/sheet-name fact inference, robust value normalization, document profiles, conflict facts, and quality reports. Generated `traceready/data/regulatory/intelligence/customer-evidence/phase10a-quality-report.json`: 80/80 mapped records, 11 sheets parsed, 11 document profiles, 0 conflicts, quality gate `pass`; tests cover messy CSV/XLSX, formulas, and conflict cases. |
| Phase 10B field mapping governance | `done` | `traceready_ingestion.intelligence.field_mapping_governance` generated `traceready/data/regulatory/intelligence/customer-evidence/phase10b-summary.json`: 50 evidence-backed draft mappings, 50 review actions, 50 approved mappings in customer/source-system profile `mapping-profile-pilot_customer-sample_workbook-v1`, regression `pass`, drift status `stable`, and 0 drift review tasks. Tests cover draft generation, approval gating, customer profiles, regression, and drift detection. |
| Phase 10C CTE classification hardening | `done` | `traceready_ingestion.intelligence.cte_classification_hardening` generated `traceready/data/regulatory/intelligence/customer-evidence/phase10c-summary.json`: 8 precedence/suppression rules, multi-signal classifier, 50 gold-labeled customer-like benchmark cases, 50/50 benchmark passes, exact match 1.0, suppression correctness 1.0, abstention correctness 1.0, and production hardened classifications for 3 sample events. |
| Phase 11 approved rule execution | `done` | `traceready_ingestion.intelligence.approved_rule_execution` generated `traceready/data/regulatory/intelligence/customer-evidence/phase11-summary.json`: approved-rule-only execution against `approved-rule-package-v1`, 25 event-obligation mappings, 38 KDE checks, 7 TLC checks, 6 traceability-plan checks, 3 records-readiness checks, 3 sortable-export checks, 17 audit findings, 17 exception items, and blocked FDA-style export workbook due to sample evidence gaps. |
| Phase 12 generalization evaluation and performance | `done` | `traceready_ingestion.intelligence.generalization_evaluation` generated `traceready/data/regulatory/intelligence/generalization/phase12-summary.json`: 100 non-benchmark customer-like synthetic scenarios, 100 gold labels, 100/100 exact passes for the deterministic Phase 10C classifier, CTE false-positive rate 0.0, CTE false-negative rate 0.0, obligation precision/recall 1.0, citation correctness 1.0, parser evaluation harness with the deterministic classifier and two non-AI baseline parsers, and drift monitor status `stable`. No live OpenAI/Anthropic customer-record parser was run in Phase 12. |

## Phase 1: Source Registry Hardening

Goal: make the source library trustworthy before extracting rules.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-001 | Create canonical source registry schema | `done` | Schema includes `sourceId`, `title`, `url`, `sourceType`, `authorityRank`, `sourceStatus`, `effectiveDate`, `complianceDate`, `retrievedAt`, `hash`, `artifactPath`, `normalizedPath`. |
| RI-002 | Generate registry records from both manifests | `done` | One canonical JSON/DB record per source; duplicates resolved by `sourceId` and hash. |
| RI-003 | Add authority ranking | `done` | Sources are ranked: `codified_rule`, `final_rule`, `federal_register_notice`, `guidance`, `faq`, `template`, `scenario`, `training`, `research`, `market_impact`, `change_monitor`. |
| RI-004 | Add source health report | `done` | Script reports missing raw artifacts, missing normalized artifacts, empty chunks, raw `%PDF` chunks, duplicate URLs, and failed sources. |
| RI-005 | Store source registry in Supabase | `planned` | Supabase tables exist and are populated; no local fallback for product truth. |

## Phase 2: Chunk Quality And Citation Anchors

Goal: make source chunks usable for accurate extraction and citation.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-010 | Define source chunk schema | `done` | Schema includes `chunkId`, `sourceId`, `sectionLabel`, `sectionRef`, `pageNumber`, `text`, `textHash`, `citationAnchor`, `authorityRank`. |
| RI-011 | Normalize all current chunks into canonical records | `done` | All 983 hub chunks and local important chunks can be loaded through one reader. |
| RI-012 | Add chunk quality scoring | `done` | Detects empty text, raw PDF bytes, too-short chunks, giant chunks, duplicate text, missing citation anchors. |
| RI-013 | Add citation span validation utility | `done` | `traceready_ingestion.intelligence.citations.validate_citation_span` verifies cited chunk existence, source/anchor match, and support text span using exact or normalized text matching. |
| RI-014 | Add citation coverage report | `done` | `traceready/ingestion/scripts/intelligence/build_citation_coverage_report.py` generated `traceready/data/regulatory/intelligence/citation-coverage-report.json`: 10 records, 10 complete, 0 partial, 0 missing, 0 invalid. |
| RI-015 | Add health warning triage | `done` | Health report classifies warnings as `blocking`, `needs_remediation`, or `accepted_nonblocking` with a reason and recommended action. |
| RI-016 | Remediate FAQ table chunking | `done` | Large FAQ source chunk split into citation-safe canonical subchunks; non-informative metadata chunks removed from canonical registry. |
| RI-017 | Remediate final-rule rationale chunks | `done` | Large Federal Register final-rule history chunks split into citation-safe canonical subchunks. |
| RI-018 | Remediate scenario slide extraction | `done` | Scenario title/page-anchor chunks retained as `citation_only`; meaningful scenario slide text retained for later benchmark extraction. |

## Phase 3: Typed Extraction Schemas

Goal: define strict schemas before using AI or deterministic parsers.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-020 | Define `DefinedTerm` schema | `done` | Captures term, definition, scope, citation, source authority. |
| RI-021 | Define `Obligation` schema | `done` | Captures subject, condition, action, object, required output, exception, deadline, citation, confidence. |
| RI-022 | Define `FtlFoodItem` schema | `done` | Captures category, commodity, included examples, excluded examples, notes, risk-ranking links, citation. |
| RI-023 | Define `CteDefinition` schema | `done` | Captures CTE type, triggering event, actor, input/output event relationship, citation. |
| RI-024 | Define `KdeRequirement` schema | `done` | Captures CTE, KDE name, required/conditional status, appliesTo, provider/recipient, citation. |
| RI-025 | Define `TlcRule` schema | `done` | Captures assignment, preservation, source reference, transformation handling, uniqueness, lineage, evidence examples, unresolved questions, citation, and review metadata. |
| RI-026 | Define `ExemptionRule` schema | `done` | Captures exemption type, eligibility condition, full/partial/modified effect, affected requirements, documentation needed, entity/food/CTE applicability, decision questions, citation, and review metadata. |
| RI-027 | Define `TraceabilityPlanRequirement` schema | `done` | Captures plan component, required detail, appliesTo, required status, evidence examples, update trigger, owner role, citation, and review metadata. |
| RI-028 | Define `SortableExportField` schema | `done` | Captures FDA workbook tab, field name, datatype, required/conditional status, source mapping, CTE applicability, accepted examples, validation notes, citation, and review metadata. |
| RI-029 | Define `ScenarioBenchmark` schema | `done` | Captures FDA scenario source, actors, events, expected KDEs, expected TLC behavior, expected findings, expected export behavior, open questions, citation, and review metadata. |

## Phase 4: Deterministic Extractors First

Goal: use deterministic parsing where the source format is structured enough.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-030 | Extract FTL food taxonomy from FDA FTL page | `done` | Generated `traceready/data/regulatory/intelligence/drafts/ftl-food-items.json`: 20 FTL food items with included/excluded notes and citations. |
| RI-031 | Extract FDA sortable spreadsheet schema from XLSX | `done` | Generated `traceready/data/regulatory/intelligence/drafts/sortable-export-fields.json`: 370 FDA workbook fields across event tabs, with tab citations. |
| RI-032 | Extract CTE/KDE candidates from FDA CTE/KDE PDF | `done` | Generated `traceready/data/regulatory/intelligence/drafts/cte-definitions.json` and `traceready/data/regulatory/intelligence/drafts/cte-kde-candidates.json`: 7 CTE definitions and 79 KDE candidates with page citations. |
| RI-033 | Extract defined terms from eCFR Subpart S | `done` | Generated `traceready/data/regulatory/intelligence/drafts/defined-terms.json`: 26 regulatory definitions with CFR citations. |
| RI-034 | Extract traceability-plan requirements from eCFR and FDA examples | `done` | Generated `traceready/data/regulatory/intelligence/drafts/traceability-plan-requirements.json`: 6 traceability-plan requirements with CFR citations. |
| RI-035 | Extract scenario benchmark candidates from FDA scenario slides/transcripts | `done` | Generated `traceready/data/regulatory/intelligence/drafts/scenario-benchmarks.json`: 6 FDA scenario benchmark drafts with open reviewer questions and source citations. |

## Phase 5: AI-Assisted Extraction

Goal: use AI only where deterministic extraction is insufficient.

Completion note: RI-040 through RI-044 complete the AI-assisted extraction infrastructure and guardrails. Phase 5 is not product-complete until RI-045 and RI-046 run a real model extraction job and validate the generated draft records.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-040 | Create structured-output prompts for obligations | `done` | Generated `traceready/data/regulatory/intelligence/phase5/prompts/phase5_obligation_extraction_v1.md`; prompt includes the Pydantic JSON schema and requires JSON-only output with citations. |
| RI-041 | Create structured-output prompts for exemptions | `done` | Generated `traceready/data/regulatory/intelligence/phase5/prompts/phase5_exemption_extraction_v1.md`; prompt requires exemption condition, effect, documentation, applicability, decision questions, and citations. |
| RI-042 | Create structured-output prompts for TLC rules | `done` | Generated `traceready/data/regulatory/intelligence/phase5/prompts/phase5_tlc_rule_extraction_v1.md`; prompt covers assignment, preservation, source-reference, transformation, uniqueness, lineage, and citations. |
| RI-043 | Add unsupported-claim rejection | `done` | `traceready_ingestion.intelligence.ai_assisted.validate_ai_records` rejects schema-invalid, citation-invalid, approved-by-AI, non-AI-assisted, and unsupported-claim records; safety report shows 1 unsupported draft rejected. |
| RI-044 | Add conflict detection | `done` | `traceready_ingestion.intelligence.ai_assisted.detect_conflicts` marks same-key contradictory drafts as `conflict_detected`; safety report shows 2 TLC conflict records marked. |
| RI-045 | Run real model extraction for obligations, exemptions, and TLC rules | `done` | Real Anthropic runs completed: obligations run `phase5-anthropic-20260616T091539Z`; exemptions/TLC run `phase5-anthropic-20260616T092748Z`. Raw prompts and model outputs are stored under each run's `input/`, `output/`, and `raw/` folders. |
| RI-046 | Validate real model extraction outputs | `done` | Real AI outputs were schema-validated, citation-span-validated, unsupported-claim checked, and conflict-checked. Accepted/rejected totals: 20 accepted, 16 rejected, 0 conflicts. |

## Phase 6: Validation And Review

Goal: prevent unreviewed or unsupported records from becoming executable.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-050 | Validate every draft with Pydantic | `done` | `traceready_ingestion.intelligence.review_workflow` validates all Phase 4 deterministic records and Phase 5 AI records. Generated package has 550 draft attempts: 534 ready for review and 16 rejected. |
| RI-051 | Validate citation spans | `done` | `phase6-citation-coverage-report.json` validates citations against canonical chunks. Ready-for-review records all have complete citation validation; 11 invalid citations remain only inside rejected records. |
| RI-052 | Build reviewer status model | `done` | `DraftReviewRecord.review_status` uses `draft`, `needs_review`, `approved`, `rejected`, `superseded`, and `conflict_detected`; generated status counts are `needs_review: 534`, `rejected: 16`, `approved: 0`. |
| RI-053 | Create review action log | `done` | `phase6-review-action-log.json` records 566 system validation actions; Next review helpers create approve/edit/reject actions with reviewer, timestamp, reason, before, and after payloads. |
| RI-054 | Add Supabase tables for draft and approved records | `done` | Added Prisma models and `app/supabase/migrations/003_regulatory_intelligence_review.sql` for `regulatory_draft_records`, `approved_regulatory_records`, and `regulatory_review_actions`; approved records are separated and product policy is approved-records-only. |
| RI-055 | Build reviewer console page | `done` | `/admin/regulatory/review`, `/admin/regulatory/drafts`, and `/admin/regulatory/coverage` read the Phase 6 review package and show draft records, citations, rejected records, review readiness, and approved-record gate status. |

## Phase 7: Obligation Inventory

Goal: create the core compliance brain.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-060 | Generate obligation drafts from eCFR Subpart S | `done` | `phase7-obligation-drafts.json` contains 21 source-backed obligations covering scope, traceability plan, TLC assignment, CTE/KDE duties, records maintenance, FDA request timing, and sortable export. |
| RI-061 | Link obligations to CTE/KDE/TLC/exemption records | `done` | `phase7-obligation-inventory.json` links obligation records to operational components: 17 with KDE links, 14 with TLC links, 13 with exemption links, 6 with traceability-plan links, and 19 with sortable-export links. |
| RI-062 | Add obligation confidence scoring | `done` | Every obligation inventory record has a confidence score based on source authority, extraction method, citation coverage, and review status; summary shows 21 high-confidence records. |
| RI-063 | Publish first approved obligation set | `done` | `phase7-approved-obligation-set-v1.json` is immutable version 1 with 12 approved deterministic eCFR obligations; AI-assisted obligations remain draft/review-only until human approval. |

## Phase 8: Scenario Regression Benchmarks

Goal: prove rules behave correctly on FDA examples before customer audits.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-070 | Create FDA cucumber scenario benchmark | `done` | `phase8-scenario-benchmarks.json` includes `phase8:fda_scenario:cucumber` with actors, harvesting, initial packing, shipping, receiving, KDE field expectations, TLC behavior, approved obligation IDs, and FDA scenario citations. |
| RI-071 | Create FDA tuna scenario benchmark | `done` | `phase8:fda_scenario:tuna` includes first land-based receiving, seafood-specific first-land KDE obligation `FSMA204-OBL-DET-1335-FIRST-LAND-BASED-RECEIVING-KDES`, TLC assignment, shipping, receiving, and citations. |
| RI-072 | Create FDA cheese scenario benchmark | `done` | `phase8:fda_scenario:cheese` includes soft-cheese scope, transformation, shipping, receiving, transformation KDE/TLC expectations, and citations. |
| RI-073 | Create FDA deli salad scenario benchmark | `done` | `phase8:fda_scenario:deli_salad_ftl_ingredients` and `phase8:fda_scenario:deli_salad_canned_tuna` cover ready-to-eat deli salad, FTL ingredient receiving, transformation, canned-tuna non-FTL form-change behavior, shipping, and citations. |
| RI-074 | Create FDA sprouts scenario benchmark | `done` | `phase8:fda_scenario:sprouts` covers fresh sprouts, seed input scope behavior, initial packing, shipping, receiving, TLC/KDE expectations, and citations. |
| RI-075 | Create traceability plan scenario benchmarks | `done` | `phase8-traceability-plan-benchmarks.json` covers FDA traceability plan examples for farms, restaurants, sprouters, food processors, distribution centers, seafood processing, and aquaculture. |
| RI-076 | Add regression runner | `done` | `traceready_ingestion.intelligence.scenario_regression.run_phase8_regression` blocks publish when expected obligations, event contracts, traceability-plan expectations, or citations fail; `phase8-regression-results.json` shows 13/13 pass and `canPublishRuleChanges: true`. |

## Phase 9: Approved Structured Rule Library

Goal: publish versioned structured rules that the audit engine can safely consume.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-080 | Define approved rule package format | `done` | `approved-rule-package-v1.json` includes package/version/status, immutable package hash, approved records, source versions with cited chunk hashes, Phase 8 scenario gate status, approval metadata, and rollback metadata. |
| RI-081 | Generate approved rule package from reviewer-approved records | `done` | `build_phase9_approved_rule_package.py` generates a read-only package from the current approved obligation set; generated package contains only 12 records with `metadata.review_status: approved`. |
| RI-082 | Add package diffing | `done` | `approved-rule-package-v1-diff.json` reports added/removed/changed/unchanged records, source version changes, scenario gate changes, and rollback safety; tests verify changed-record detection between synthetic versions. |
| RI-083 | Add rollback support | `done` | `active-rule-package-pin.json` pins active package ID, version, package hash, scenario gate status, diff status, and previous package ID for audit-engine rollback/version pinning. |

## Phase 10: Connect To Customer Audit Engine

Goal: turn messy customer evidence into normalized traceability facts, then run approved intelligence against those facts.

Scope note: RI-090 through RI-099 establish the baseline bridge from customer evidence to normalized facts. They do not mean TraceReady can reliably parse arbitrary distributor, processor, restaurant/RFE, farm, or seafood workbooks yet. Real customer evidence requires dedicated hardening for workbook chaos, reviewable field-mapping approval, and CTE precedence/suppression behavior before Phase 11 findings should be trusted in production.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-090 | Define customer evidence model | `done` | `CustomerEvidenceRecord` in `traceready_ingestion.intelligence.customer_evidence` captures uploaded file, sheet, row, column, cell, raw value, normalized value, field type, extraction method, confidence, and source evidence pointer. |
| RI-091 | Define traceability entity model | `done` | `TraceabilityEntityGraph` captures products, product forms, lots/TLCs, actors, locations, counterparties, documents, and evidence links before classifying CTEs. |
| RI-092 | Build spreadsheet evidence ingestion | `done` | CSV/XLSX ingestion parses uploaded files into normalized evidence records with sheet/row/cell lineage and field-mapping confidence; sample workbook run produced 80 evidence records. |
| RI-093 | Add AI-assisted field mapping suggestions | `done` | `phase10-field-mapping-suggestions.json` contains reviewable, evidence-backed mapping suggestions including messy aliases such as `Lot # -> traceability_lot_code` and `Ship Date -> date_you_shipped_the_food`. |
| RI-094 | Build customer event graph | `done` | `phase10-event-graph.json` assembles evidence into actor/product/lot/location movement and transformation event nodes with source evidence references. |
| RI-095 | Add food/form resolver | `done` | `resolve_food_form` resolves FTL likelihood, fresh/fresh-cut/frozen/canned/shelf-stable/refrigerated/cooked/kill-step/RAC/seafood vessel states, output FTL status, confidence, and review requirement. |
| RI-096 | Add actor and role resolver | `done` | `resolve_actor_role` resolves farm, harvester, cooler, initial packer, first land-based receiver, processor, shipper, receiver, distributor, restaurant/RFE, transporter, consumer, and unknown roles with confidence. |
| RI-097 | Add deterministic CTE classifier | `done` | `phase10-cte-classification-results.json` classifies CTEs from structured facts and supports harvesting, cooling, initial packing, first land-based receiving, shipping, receiving, transformation, and traceability plan candidates. |
| RI-098 | Add negative/suppression logic | `done` | Tests verify first land-based receiving suppresses generic receiving, direct-to-consumer suppresses shipping, and non-FTL finished form suppresses downstream FTL CTE duties. |
| RI-099 | Add abstention and reviewer-question generation | `done` | `phase10-reviewer-questions.json` captures low-confidence/ambiguous food form, destination, output FTL scope, exemption, and unmapped-column questions instead of confident findings. |

## Phase 10A: Customer Evidence Ingestion Hardening

Goal: survive real customer spreadsheets before producing deterministic audit findings.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-10A-001 | Build messy workbook parser | `done` | Parser now detects best header row after blank/header bands, skips notes and repeated headers, resolves merged XLSX cells, skips hidden XLSX rows/columns, falls back to formula text when cached formula values are unavailable, supports multi-sheet workbooks, and preserves cell lineage; tests cover messy CSV and XLSX cases. |
| RI-10A-002 | Add filename and sheet-name fact extraction | `done` | `phase10a-inferred-facts.json` captures filename/sheet-name inferred lots/TLCs, dates, document types, products, and locations with evidence pointers and confidence; tests cover filename inference. |
| RI-10A-003 | Normalize dates, quantities, units, and identifiers robustly | `done` | Normalization supports ISO, slash, compact `YYYYMMDD`, two-digit-year dates, filename separator dates, lot/batch/TLC casing, quantity cleanup, unit aliases, whitespace cleanup, and raw value preservation. |
| RI-10A-004 | Add document-type specific parsers | `done` | `phase10a-document-profiles.json` classifies sheets/files into invoice, BOL, receiving log, shipping log, transformation batch record, harvest log, cooling log, packing log, seafood landing record, traceability plan, or generic parser profile. |
| RI-10A-005 | Build evidence conflict model | `done` | `phase10a-evidence-conflicts.json` preserves same-row conflicting mapped values with source evidence IDs; tests verify conflicting lot/TLC values become review-blocking conflict facts. |
| RI-10A-006 | Add customer evidence quality report | `done` | `phase10a-quality-report.json` reports parse coverage, unmapped sheets/columns, low-confidence mappings, inferred facts, conflicts, duplicates, missing lineage anchors, abstentions, issues, and quality gate; sample run quality gate is `pass`. |

## Phase 10B: Field Mapping Review And Approval

Goal: treat customer field mappings like regulated product configuration, not disposable AI guesses.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-10B-001 | Define customer field mapping draft schema | `done` | `CustomerFieldMappingDraft` captures customer/source system, file pattern, sheet pattern, column/header evidence, proposed canonical field, rationale, confidence, examples, extraction method, review status, reviewer questions, and source-cell pointers. |
| RI-10B-002 | Add AI-assisted mapping draft generation | `done` | `phase10b-field-mapping-drafts.json` contains reviewable draft mappings generated from field suggestions; ambiguous/contextual mappings use `ai_assisted_mapping_draft`, include evidence pointers, and remain unapproved unless reviewed. |
| RI-10B-003 | Add mapping approval workflow | `done` | `phase10b-review-actions.json` records approve/hold actions with reviewer, role, timestamp, reason, before/after status; only reviewed approved mappings enter the executable profile. |
| RI-10B-004 | Add customer-specific mapping profiles | `done` | `phase10b-approved-mapping-profile.json` pins approved mappings by customer, source system, file pattern, sheet pattern, source column pattern, version, hash, and rollback metadata with global alias fallback. |
| RI-10B-005 | Add mapping regression tests | `done` | `phase10b-mapping-regression-results.json` reruns approved profile mappings against parsed evidence; sample profile checks 50 mappings, 50 passed, 0 failed, status `pass`. |
| RI-10B-006 | Add mapping drift detection | `done` | `phase10b-drift-report.json` compares current headers with the approved profile, reports new/missing/low-confidence changed headers, and creates review tasks instead of silently using stale mappings; sample drift status is `stable`. |

## Phase 10C: CTE Classification And Suppression Hardening

Goal: make CTE classification precise enough that Phase 11 findings are not polluted by over-triggered events.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-10C-001 | Define CTE precedence matrix | `done` | `phase10c-cte-precedence-matrix.json` encodes 8 precedence/exclusivity rules covering first-land over receiving, direct-to-consumer, transporter-only, internal transfer, return/correction, non-FTL output, kill-step/exemption uncertainty, and traceability-plan exclusivity. |
| RI-10C-002 | Add multi-signal CTE classifier | `done` | `classify_event_with_multisignal` uses event type, document type, actor role, movement direction, product/form state, lot lineage, date fields, traceability-plan evidence, conflicts, and precedence rules instead of any single keyword. |
| RI-10C-003 | Expand suppression tests | `done` | Tests and benchmarks cover first-land versus receiving, direct-to-consumer, transporter-only rows, internal transfers, returns/corrections, non-FTL transformed outputs, kill-step/exemption uncertainty, and traceability-plan exclusivity. |
| RI-10C-004 | Add abstention thresholds by fact type | `done` | Low-confidence actor role, unresolved food/form scope, transporter-only movement, internal transfers, returns/corrections, conflicts, kill-step, and exemption uncertainty produce reviewer questions/abstentions instead of confident CTEs. |
| RI-10C-005 | Add gold-labeled customer workbook benchmark set | `done` | `phase10c-gold-benchmark-set.json` contains 50 customer-like workbook fixture cases across shipping, receiving, first-land seafood receiving, direct-to-consumer, transformation, non-FTL output, transporter-only, internal transfer, return/correction, and traceability-plan scenarios. |
| RI-10C-006 | Add CTE precision/recall report | `done` | `phase10c-precision-recall-report.json` reports 50 benchmark cases, exact match 1.0, per-CTE precision/recall, false positives/negatives, suppression correctness 1.0, abstention correctness 1.0, and top error categories. |

## Phase 11: Approved Rule Execution Against Customer Evidence

Goal: convert normalized customer events into deterministic, citation-backed audit findings.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-100 | Map customer CTEs to approved obligations | `done` | `phase11-obligation-mapping.json` maps hardened customer CTEs only to obligations from immutable `approved-rule-package-v1`; no draft or rejected record is executable. |
| RI-101 | Implement KDE completeness checks | `done` | `phase11-kde-completeness-results.json` checks required event fields against customer evidence with `present`, `missing`, and `conflicting` statuses; sample run produced 38 KDE checks: 33 present, 5 missing. |
| RI-102 | Implement TLC lineage checks | `done` | `phase11-tlc-lineage-results.json` checks TLC assignment, preservation, source reference, input/output links, and transformation lineage; sample run produced 7 TLC checks: 2 linked, 5 gaps. |
| RI-103 | Implement traceability plan checks | `done` | `phase11-traceability-plan-results.json` checks record-maintenance procedure, FTL identification procedure, TLC assignment procedure, point of contact, farm map, and plan update/retention evidence. |
| RI-104 | Implement exemption and scope uncertainty checks | `done` | `phase11-scope-exemption-results.json` converts food-scope uncertainty, exemption/kill-step uncertainty, CTE abstentions, evidence conflicts, and quality-gate issues into review items instead of confident findings. |
| RI-105 | Implement records and FDA-request readiness checks | `done` | `phase11-records-readiness-results.json` checks linked/legible records, evidence quality for FDA 24-hour response readiness, and sortable export source-data availability against approved records obligations. |
| RI-106 | Implement sortable export readiness checks | `done` | `phase11-sortable-export-readiness.json` determines whether each normalized event can populate FDA-style sortable fields and identifies blockers by missing field/event. |
| RI-107 | Generate audit findings | `done` | `phase11-audit-findings.json` emits findings with severity, gap/review status, event/CTE, approved obligation ID, source citation, customer evidence IDs, confidence, and reviewer status; sample run produced 17 findings. |
| RI-108 | Generate exception queue | `done` | `phase11-exception-queue.json` turns missing KDEs, TLC gaps, traceability-plan gaps, scope uncertainty, and export blockers into assignable compliance-review items; sample run produced 17 open exceptions. |
| RI-109 | Generate FDA-style export package | `done` | `phase11-export-package.json` and `phase11-fda-style-export-package.xlsx` produce FDA-style event tabs/report with approved rule citations, customer evidence references, and export blockers; sample package status is `blocked` because evidence gaps remain. |

## Phase 12: Generalization Evaluation And Performance

Goal: prove the audit engine works on unseen customer-like situations, not only FDA benchmark examples.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-110 | Define generalization metrics | `done` | `phase12-generalization-metrics.json` tracks CTE precision/recall, obligation precision/recall, false positive rate, false negative rate, abstention correctness, suppression correctness, citation correctness, food/actor review correctness, and exact scenario pass rate. |
| RI-111 | Expand unseen scenario challenge set | `done` | `phase12-unseen-scenario-challenge-set.json` contains 100 non-benchmark customer-like scenarios across 20 families, 5 food categories, actors, forms, transformations, exemptions/review cases, and ambiguous cases. |
| RI-112 | Add gold-label expected outputs | `done` | `phase12-gold-labels.json` gives each scenario expected actor role, product/form state, CTEs, approved obligations, negative CTE expectations, suppressed CTEs, abstentions, and review expectations. |
| RI-113 | Add regression report for inference errors | `done` | `phase12-inference-error-report.json` reports over-triggered CTEs, missed CTEs, wrong food-scope decisions, wrong actor-role decisions, missing abstentions, obligation false positives/negatives, and citation failures. |
| RI-114 | Add model/prompt evaluation harness | `done` | `phase12-parser-evaluation-harness.json` defines the comparison harness and currently compares deterministic multi-signal parsing against two non-AI baselines: permissive keyword parsing and conservative abstention parsing. No real OpenAI/Anthropic prompt output has been evaluated yet; the harness is ready for that next step while approved deterministic rule execution remains unchanged. |
| RI-115 | Add drift and change monitoring | `done` | `phase12-drift-change-monitor-report.json` hashes the approved rule package and Phase 12 challenge set, records current suite statuses, and defines publication-blocking rerun policy for source, approved-rule, parser/prompt, and customer mapping changes. |

## Phase 13: Accuracy Improvement And Classifier Release Gates

Goal: turn Phase 12 evaluation failures into measured parser improvements before customer-facing audit claims.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-120 | Add parser accuracy improvement plan | `done` | Phase 13 records the measured baseline from `phase12-web500-metrics.json` and defines deterministic improvements for shipping false positives, transformation false negatives, transporter/correction abstentions, and citation subparagraph precision. |
| RI-121 | Add shipping hard-negative and threshold experiment | `done` | Shipping classifier applies negative-weight context for document-only movement terms, internal movement, transporter/carrier records, corrections, returns, and weak logistics terms; Phase 12 web500 metrics are rerun and compared against the 71.6% baseline. |
| RI-122 | Add transformation synonym and lineage recall experiment | `done` | Transformation detection covers transforms/processing/repacking/blending/mixing/cutting/fresh-cut/recipe/manufacturing terms, but verifies CFR-style transformation context with input/output/new lot signals before confident classification. |
| RI-123 | Expand abstention handling for transporter, correction, return, and internal records | `done` | Carrier/3PL/freight/transport-only, credit memo/RMA/rejected/disposal/correction, and internal transfer records route to abstention/review instead of confident shipping when covered-entity evidence is weak. |
| RI-124 | Add before/after web500 performance report | `done` | `phase13-web500-accuracy-comparison.json` records baseline and post-change exact match, precision, recall, false positive/negative rates, pass/fail counts, and per-CTE precision/recall. |
| RI-125 | Add fresh public-internet 2,000-record holdout | `done` | `phase13-web2000-input-records.*`, `phase13-web2000-results.*`, and separate input/output Excel workbooks cover 2,000 fresh public rows: 1,813 Open Food Facts static bulk product metadata rows and 187 GS1 EPCIS public example events. Final run: 2,000/2,000 exact passes, precision 1.0, recall 1.0, false-positive rate 0.0, false-negative rate 0.0. |
| RI-126 | Add citation subparagraph resolution workstream | `done` | `approved-subparagraph-targets-v1.json` stores the reviewed obligation-to-subparagraph targets outside code; `phase13-subparagraph-citation-resolution.json` loads that approved artifact and resolves 12/12 approved obligation citations to verified paragraph/subparagraph anchors, including `21 CFR 1.1325(a)`, `21 CFR 1.1325(b)`, and `21 CFR 1.1455(c)(3)(ii)`, with 0 unresolved anchors and without weakening section-level citation validation. |
| RI-127 | Add two-stage candidate/verification classifier | `done` | `phase13-two-stage-classifier-report.json` separates high-recall candidate generation from high-precision verification, requires at least two independent signal families (action semantics, actor role, from/to movement, document type, date field, lot/TLC, reference document, product/quantity), and reports auto-approved precision 1.0, review-routed count 30, review-routed rate 0.06, and abstention rate 0.08 against the 500-row eval baseline. |

## Phase 14: Reviewer Operations And Governance

Goal: make the system safe for enterprise compliance operations.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-130 | Build customer evidence review console | `done` | Next.js `/audits/[auditId]/review` exposes extracted customer facts, event/source context, evidence references, confidence/review state, unresolved questions, and proposed recommendations for reviewer inspection. |
| RI-131 | Build finding review workflow | `done` | `review/actions.ts` persists approve, reject, edit, assign, comment, and more-evidence decisions with reviewer identity, reason, timestamp, finding/rule context, and an append-only action log. |
| RI-132 | Add package/version pinning per audit | `done` | New audit runs initialize `StoredAudit.governance.packagePin` with approved rule package version, scenario regression status, customer evidence version, parser version, and model/prompt policy for repeatable audit reconstruction. |
| RI-133 | Add explainability trace | `done` | `buildExplainabilityTraces` powers the review console trace from customer evidence to normalized event to deterministic check to approved rule package and source citation for each finding. |
| RI-134 | Add reviewer override controls | `done` | Override forms require reviewer, reason, timestamp, affected finding/rule, and evidence scope; overrides default to `excluded_from_automation` and can only be promoted through a recorded reviewer approval action. |

## Phase 15: Post-MVP Source And Worker Hardening

Goal: harden broader source onboarding and operations after the Vercel/Supabase MVP path is working end to end.

| ID | Task | Status | Acceptance Criteria |
|---|---|---|---|
| RI-140 | Add generalized structured PDF table extraction | `defer` | Build reusable PDF table extraction into normalized table objects with page/cell lineage, confidence, and citation anchors. Not required for the first FSMA 204 MVP because current source chunks and targeted extractors support the approved package. |
| RI-141 | Add generalized typed XLSX source-schema extraction | `defer` | Build reusable XLSX schema extraction for regulatory/source templates beyond the current FDA sortable workbook and customer evidence parser. Existing FDA sortable-field extraction and customer workbook parsing remain sufficient for MVP validation. |
| RI-142 | Add regulatory change monitor | `planned` | Periodically check FDA/eCFR/Federal Register source URLs, compare hashes/effective dates, write source-ingestion review tasks, and block automatic rule publication until reviewer approval and regression gates pass. |
| RI-143 | Reassess worker hosting beyond Vercel job slices | `defer` | Keep Vercel bounded HTTP job slices and cron as the MVP production model. Consider a separate always-on worker only if audit volume, file size, or source-monitor cadence exceeds Vercel function limits. |

## Immediate Build Order

Completed foundation build order:

1. RI-030: deterministic FTL extraction.
2. RI-031: deterministic sortable spreadsheet schema extraction.
3. RI-032: CTE/KDE candidate extraction.
4. RI-033: eCFR defined-term extraction.
5. RI-034: traceability-plan requirement extraction.
6. RI-035: FDA scenario benchmark draft extraction.
7. RI-013: citation span validation utility.
8. RI-014: citation coverage report.

Next implementation area:

1. RI-090 through RI-099: customer evidence model, event graph, food/form resolver, actor resolver, CTE classifier, suppression logic, and abstention.
2. RI-100 through RI-109: approved rule execution, gap detection, exception queue, and FDA-style export.
3. RI-110 through RI-115: generalization evaluation and performance metrics. `done`

Completed before Phase 4:

- RI-025 through RI-029: typed schemas for TLC, exemptions, traceability plans, export fields, and scenario benchmarks.

Validation evidence:

- `traceready/ingestion/traceready_ingestion/intelligence/schemas.py`
- `traceready/ingestion/traceready_ingestion/intelligence/citations.py`
- `traceready/ingestion/traceready_ingestion/intelligence/ai_assisted.py`
- `traceready/ingestion/traceready_ingestion/intelligence/anthropic_client.py`
- `traceready/ingestion/traceready_ingestion/intelligence/phase4_extractors.py`
- `traceready/ingestion/scripts/intelligence/validate_intelligence_schemas.py`
- `traceready/ingestion/scripts/intelligence/build_citation_coverage_report.py`
- `traceready/ingestion/scripts/intelligence/build_phase4_drafts.py`
- `traceready/ingestion/scripts/intelligence/build_phase5_prompt_pack.py`
- `traceready/ingestion/scripts/intelligence/run_phase5_anthropic_extraction.py`
- `traceready/ingestion/scripts/intelligence/run_phase5_safety_checks.py`
- `traceready/ingestion/scripts/intelligence/build_phase8_scenario_regressions.py`
- `traceready/ingestion/scripts/intelligence/build_phase8_unseen_web_challenges.py`
- `traceready/ingestion/scripts/intelligence/build_phase8_shadow_structured_record_eval.py`
- `traceready/ingestion/scripts/intelligence/build_phase9_approved_rule_package.py`
- `traceready/ingestion/scripts/intelligence/build_phase12_generalization_evaluation.py`
- `traceready/ingestion/tests/test_citation_validation.py`
- `traceready/ingestion/tests/test_intelligence_schemas.py`
- `traceready/ingestion/tests/test_phase4_extractors.py`
- `traceready/ingestion/tests/test_ai_assisted_phase5.py`
- `traceready/ingestion/tests/test_anthropic_client.py`
- `traceready/ingestion/tests/test_phase8_scenario_regression.py`
- `traceready/ingestion/tests/test_phase8_unseen_web_challenges.py`
- `traceready/ingestion/tests/test_phase8_shadow_structured_record_eval.py`
- `traceready/ingestion/tests/test_phase9_approved_rule_package.py`
- `traceready/ingestion/tests/test_phase12_generalization_evaluation.py`
- `traceready/data/regulatory/intelligence/schema-smoke-output.json`
- `traceready/data/regulatory/intelligence/citation-coverage-report.json`
- `traceready/data/regulatory/intelligence/drafts/phase4-drafts.json`
- `traceready/data/regulatory/intelligence/drafts/citation-coverage-report.json`
- `traceready/data/regulatory/intelligence/phase5/prompts/phase5-prompt-pack.json`
- `traceready/data/regulatory/intelligence/phase5/phase5-safety-check-report.json`
- `traceready/data/regulatory/intelligence/phase5/phase5-real-extraction-summary.json`
- `traceready/data/regulatory/intelligence/phase5/anthropic-runs/phase5-anthropic-20260616T091539Z/phase5-anthropic-extraction-report.json`
- `traceready/data/regulatory/intelligence/phase5/anthropic-runs/phase5-anthropic-20260616T092748Z/phase5-anthropic-extraction-report.json`
- `traceready/data/regulatory/intelligence/scenarios/phase8-summary.json`
- `traceready/data/regulatory/intelligence/scenarios/phase8-regression-results.json`
- `traceready/data/regulatory/intelligence/scenarios/phase8-unseen-web-challenge-summary.json`
- `traceready/data/regulatory/intelligence/scenarios/phase8-unseen-web-challenge-results.json`
- `traceready/data/regulatory/intelligence/scenarios/phase8-shadow-all-structured-records-summary.json`
- `traceready/data/regulatory/intelligence/scenarios/phase8-shadow-all-structured-records-results.json`
- `traceready/data/regulatory/intelligence/rules/phase9-summary.json`
- `traceready/data/regulatory/intelligence/rules/approved-rule-package-v1.json`
- `traceready/data/regulatory/intelligence/rules/approved-rule-package-v1-diff.json`
- `traceready/data/regulatory/intelligence/rules/active-rule-package-pin.json`
- `traceready/data/regulatory/intelligence/generalization/phase12-summary.json`
- `traceready/data/regulatory/intelligence/generalization/phase12-generalization-metrics.json`
- `traceready/data/regulatory/intelligence/generalization/phase12-unseen-scenario-challenge-set.json`
- `traceready/data/regulatory/intelligence/generalization/phase12-gold-labels.json`
- `traceready/data/regulatory/intelligence/generalization/phase12-regression-results.json`
- `traceready/data/regulatory/intelligence/generalization/phase12-inference-error-report.json`
- `traceready/data/regulatory/intelligence/generalization/phase12-parser-evaluation-harness.json`
- `traceready/data/regulatory/intelligence/generalization/phase12-drift-change-monitor-report.json`
- `/Users/ramesh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s tests`: 79 tests passing

## Definition Of Done For The Intelligence Layer

The intelligence layer is not ready until all of the following are true:

- Every approved structured record has source citations.
- Every citation resolves to a real source chunk.
- Every executable rule comes from approved records, not raw AI output.
- Every approved package has an immutable version.
- Every package has scenario regression results.
- Customer-facing audit findings can explain:

```text
customer evidence
-> normalized event
-> deterministic check
-> approved structured rule
-> source citation
```
