# FDA Docket Problems and TraceReady Long-Term Scope

Date: 2026-06-15

Source context:
- Regulations.gov docket: `FDA-2014-N-0053`
- Analysis workbook: `outputs/regulations-comments-analysis/fda-fsma-204-docket-comment-analysis.xlsx`
- Structured analysis: `outputs/regulations-comments-analysis/comment_analysis_data.json`

## Founder-Level Conclusion

TraceReady still makes sense, but the wedge should be sharpened.

The market is not primarily asking for another full traceability platform. The repeated pain is whether existing records from suppliers, Excel, EDI 856/ASN, WMS, ERP, BOLs, invoices, labels, and partner portals are complete, linked, interoperable, and export-ready.

The strongest positioning is:

> TraceReady audits traceability records before they fail. It checks whether FSMA 204 records are complete, linked, and export-ready across Excel, EDI, WMS, ERP, and supplier data.

Do not position TraceReady as an ERP, WMS, supplier portal, or generic FSMA dashboard. Position it as the readiness, validation, and proof layer that can sit before or beside ReposiTrak, Trustwell, Wholechain, FoodLogiQ, TrackKey/ENSESO, WMS, ERP, and internal spreadsheets.

## Problems Repeatedly Pointed Out

### 1. Records exist, but they are not reliably usable

Companies often already have invoices, ASNs, BOLs, WMS records, ERP exports, supplier documents, labels, and spreadsheets. The problem is whether those records contain the right KDEs, TLCs, CTE links, source references, and sortable export structure.

TraceReady implication:
- Validate evidence quality, not just record presence.
- Show ready, missing, uncertain, conflicting, and not-determined states.
- Link every finding to the evidence row/document and approved rule card.

### 2. Interoperability is a major pain

Dot Foods, FMI, NGA, Trustwell, AIM, Partnership for Food Traceability, and others point to the same problem: Excel, EDI 856/ASN, GS1, EPCIS, WMS, ERP, supplier portals, and paper workflows do not naturally line up.

TraceReady implication:
- Start Excel-first for pilots.
- Design mappings toward EDI 856/ASN, GS1/EPCIS, WMS, ERP, and API flows.
- Build an evidence matrix that maps source documents/systems to KDE, CTE, TLC, and traceability-plan fields.

### 3. TLC and lot-level tracking are the hard core

The hardest questions are exact TLC vs missing TLC vs inferred TLC vs TLC range vs commingled pallet vs case-level/pallet-level assumptions.

TraceReady implication:
- Treat TLC handling as a first-class rules domain.
- Scenario-test mixed pallets, commingled pallets, missing TLC, inferred TLC, TLC ranges, transformation, and broken lineage.
- Avoid vague AI judgments; use deterministic checks and human-review states.

### 4. Small and mid-sized operators are stuck

Many operators cannot immediately buy or implement a full enterprise traceability platform. Comments repeatedly mention small-business burden, limited resources, training gaps, and non-ERP workflows.

TraceReady implication:
- Keep the MVP low-friction: workbook upload in, audit package out.
- Do not require full ERP/WMS integration for the first pilot.
- Offer a readiness audit that proves the gap before asking for deeper integration.

### 5. FDA-style sortable export is not optional

Many comments mention sortable spreadsheets, proof-of-process pilots, FDA request readiness, and audit packages.

TraceReady implication:
- The MVP output must include a sortable readiness report.
- Reports should include evidence links, missing KDEs, TLC/linkage issues, source citations, and review status.
- "Export proof" should be a core workflow, not a secondary feature.

### 6. Supplier data quality is a bottleneck

Distributors, retailers, and restaurants depend on data passed forward by suppliers. If suppliers send incomplete or inconsistent records, downstream operators cannot comply cleanly.

TraceReady implication:
- Build supplier exception tracking.
- Add supplier response SLA, repeated error patterns, and supplier risk scorecards after MVP.
- Make supplier readiness measurable.

### 7. Rule ambiguity requires review and citations

Exemptions, FTL scope, TLC source reference, intracompany shipments, transformation, commingled pallets, restaurants, DCs, cold-chain workflows, and imported records create interpretation problems.

TraceReady implication:
- Keep the rules-first architecture.
- AI can extract and map records, but approved rule cards and deterministic checks decide findings.
- Add human-review states for ambiguous scope, exemption, and low-confidence evidence.

### 8. Imported and multilingual records are a real gap

Produce/import workflows can involve Spanish-language records and changing supplier lists. Translation requirements create operational burden for non-ERP operators.

TraceReady implication:
- Add multilingual evidence intake and translation workflow as a future differentiated module.
- Track original-language evidence, translated fields, reviewer approval, and citation links.

### 9. Public-health pressure matters

Several comments oppose delay because traceability is tied to consumer safety, outbreak response, and equity. The buyer cares about cost, but the market pressure is not only cost.

TraceReady implication:
- Do not market only "compliance paperwork."
- Show faster recall readiness, fewer blind spots, and stronger evidence quality.

## Long-Term Scope

TraceReady can become the traceability intelligence layer for food supply chains.

Not ERP. Not WMS. Not a supplier portal.

It should become the layer that answers:

> Can this company prove where food came from, what happened to it, who touched it, and whether the records hold up?

### Phase 1: MVP FSMA 204 Readiness Audit

Start with upload-based audits.

Core scope:
- Upload shipment, receiving, transformation, and traceability-plan records.
- Check FTL scope.
- Check CTE/KDE completeness.
- Validate TLC presence and linkage.
- Flag missing, conflicting, uncertain, and not-determined records.
- Export FDA-style sortable report.
- Generate evidence-backed readiness score.

### Phase 2: Exception Desk

After audits, customers will ask whether TraceReady can help fix the gaps.

Add:
- Exception queue.
- Supplier follow-up tracking.
- Missing KDE requests.
- Supplier risk scorecards.
- Human reviewer workflow.
- Before/after readiness reports.

### Phase 3: Integrations Layer

Once pilots show repeated workflows, connect to systems.

Add:
- EDI 856 / ASN intake.
- ERP exports.
- WMS exports.
- Supplier spreadsheets.
- BOL / invoice document parsing.
- API ingestion.
- GS1 / EPCIS mapping.

### Phase 4: Rules Intelligence Platform

This is the defensibility layer.

Add:
- FDA/eCFR source library.
- Versioned source chunks.
- AI-drafted rule cards.
- FSMA expert approval.
- Approved KDE/CTE requirements.
- Scenario tests.
- Change monitoring.
- Citation-backed findings.

### Phase 5: Traceability Control Tower

Longer term, customers should see live readiness.

Add:
- Real-time data quality monitoring.
- Supplier readiness scores.
- Product/category risk dashboards.
- Recall simulation.
- Broken lineage alerts.
- Audit history.
- Multi-location compliance views.

### Phase 6: Beyond FSMA 204

Once the platform works, expand into adjacent traceability and compliance needs:
- Seafood traceability.
- Imported food documentation.
- Organic/certification records.
- Allergen traceability.
- Recall readiness.
- Supplier compliance.
- Sustainability/origin claims.
- Retail customer traceability requirements.
- Private-label supplier audits.

## Strategic Expansion Path

```text
Audit records
-> Fix exceptions
-> Monitor live data
-> Integrate systems
-> Become proof layer for food traceability
-> Expand into broader food compliance intelligence
```

## Simple Positioning

Short term:

> TraceReady checks if food traceability records are complete, linked, and export-ready.

Medium term:

> TraceReady helps teams fix missing KDEs, TLC gaps, supplier exceptions, and audit-readiness issues.

Long term:

> TraceReady is the proof layer for food traceability.

