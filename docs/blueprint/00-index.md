# TraceReady Startup Blueprint

Date: 2026-06-12  
Company name: TraceReady  
Primary product: TraceReady Audit  
Expansion products: TraceReady Remediation, TraceReady Integrations

## Purpose

This folder is the pre-coding blueprint for TraceReady.

The goal is to prevent the team from jumping into a broad traceability platform too early. The first build should prove a narrow, valuable workflow:

> A digital FSMA 204 readiness audit that tells food operators whether their products, suppliers, records, lot-code workflows, transformations, and data-sharing processes are actually ready.

## Files

1. `01-company-product-strategy.md`  
   Company thesis, product sequence, naming, positioning, ICP, moat, and what not to build.

2. `02-mvp-prd.md`  
   Product requirements for the first MVP: TraceReady Audit.

3. `03-system-architecture.md`  
   High-level and low-level architecture for a low-budget AI-native system.

4. `04-ai-agents-and-rules.md`  
   Agent design, rule engine boundaries, human review, and trust guardrails.

5. `05-data-model.md`  
   Core data objects, fields, relationships, and MVP schema direction.

6. `06-audit-report-spec.md`  
   Exact output spec for the customer-facing audit report.

7. `07-website-and-messaging.md`  
   Website structure, homepage copy, demo offer, and positioning.

8. `08-roadmap-and-build-plan.md`  
   Build sequence from no-budget MVP to paid pilots to productized workflow.

9. `09-customer-pilot-plan.md`  
   How to get the first pilots, what to ask for, what to deliver, and how to measure success.

10. `10-engineering-backlog.md`  
   Granular engineering epics and tasks for the internal audit workbench and first website.

11. `11-website-build-spec.md`  
   Page structure, components, copy, and implementation guidance for the first website.

12. `12-granular-implementation-task-plan.md`  
   Architecture decisions, exact technology choices, module boundaries, task IDs, dependencies, files, and acceptance criteria for coding agents.

13. `13-mvp-pilot-task-list.md`  
   Full FSMA 204 MVP audit task list for coding agents: Excel upload, regulatory intelligence, all major CTE/KDE areas, TLC lineage, deterministic checks, human review, full audit report, and deployment gates.

14. `14-regulatory-intelligence-task-tracker.md`  
   Active implementation tracker for the regulatory intelligence layer: source registry, chunk quality, typed extraction, citation validation, obligation inventory, reviewer approval, scenario regression tests, and approved structured rules.

15. `../market/similar-product-build-patterns.md`  
   Research note connecting public docs from Wholechain, AscentAI, Regology, Norm Ai, and Vanta to TraceReady's product architecture: source library, obligation inventory, event evidence, deterministic checks, reviewer approval, exception workflow, and proof package.

## Core Decision

Build first:

> TraceReady Audit: a service-led, software-assisted FSMA 204 readiness and proof-layer audit.

Updated interpretation after the 2026-06-15 FDA docket-comment analysis:

> The first MVP should validate whether existing records and system exports are complete, linked, interoperable, and export-ready. It should not become another traceability event-entry platform.

Do not build first:

- full traceability platform
- QR/label execution system
- ERP replacement
- WMS replacement
- full supplier portal
- complex integrations
- fully automated compliance decisions

## Source Context

Key sources and evidence:

- Jim White / ENSESO4Food call: expert validation for a digital FSMA 204 gap audit.
- Field discovery with produce operators: paper invoices, handwritten notes, Excel, DProduce Man, QuickBooks, and mixed digital/manual workflows.
- FDA FSMA 204 page: Food Traceability List, CTEs, KDEs, traceability lot code rules, traceability plan, sortable spreadsheet requirement, and current enforcement context.
- Existing competitive research in `outputs/food-traceability-startup-landscape.md`.
- FDA-2014-N-0053 docket-comment analysis: interoperability, TLC/lot-level ambiguity, supplier data quality, sortable exports, small-business burden, imported/multilingual records, and source-system readiness are repeated market problems.
- Synthesis note: `traceready/docs/strategy/2026-06-15-fda-docket-problems-and-long-term-scope.md`.

## Current FDA Context

FDA states the original compliance date was January 20, 2026. FDA also states it proposed a 30-month extension to July 20, 2028, and Congress directed FDA not to enforce before that date.

Product implication:

> The wedge is not panic compliance. The wedge is readiness: companies have time, but they do not know where their gaps are or how long remediation will take.

Sharper product implication:

> TraceReady should be the proof layer that shows whether Excel, EDI/ASN, ERP, WMS, traceability platform exports, supplier documents, and manual records can actually support FSMA 204 evidence.
