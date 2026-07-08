# TraceReady Backend — Teaching Guide

*A single document to explain the backend to a co-founder/partner and to demo it to Jim & John.
Read top to bottom once; after that use it as a lookup. No code knowledge required.*

---

## 0. The 60-second pitch

**TraceReady is the readiness audit you run BEFORE you buy a traceability platform.**

A food business (grower, processor, distributor, seafood dock) will have to comply with the
FDA's new food-traceability rule (FSMA 204) by **July 20, 2028**, and retailers like Walmart
and Kroger are already demanding the same data *today*. Most of these businesses keep their
records in Excel exports from their ERP. They have no idea whether those records would survive
an FDA request or a recall.

You upload that messy Excel file (or an EDI/ASN or a BOL PDF). TraceReady:

1. **Reads it** — any layout, no setup — using AI to understand each sheet and column.
2. **Reconstructs the supply-chain events** (who shipped/received/transformed what lot, when).
3. **Audits every event against the actual FDA rule text**, and tells you exactly what's
   missing, with the regulation quoted.
4. **Grades your trading partners** on data quality, flags recall-readiness problems, and
   exports clean data in the industry-standard format.

The output is one JSON report (and artifacts) that says: **ready / needs review / blocked**,
with a cited reason for every finding.

---

## 1. Why these features exist — Jim & John's feedback, mapped to what we built

Everything in the backend traces to a specific point the advisors raised. Use this table when
someone asks *"why did you build that?"*

| Advisor point | What we built | Where it shows up in the report |
|---|---|---|
| "It has to understand **any Excel**, not just one template. No hardcoding." | **Universal AI intake** — an LLM maps each sheet & column to a canonical meaning, verified deterministically. Works on layouts we've never seen. | `summary.intake.sheetKinds` |
| "They use **EDI integrations** / ASNs between partners." | **EDI X12 856 (ASN) parser** — reads the electronic shipping notices suppliers send. | Pre-receipt endpoint + `inbound_erp_mismatch` findings |
| "Suppliers send data the receiver's system **silently drops**." (John's caution) | **Door-vs-database diff** — compares what the supplier sent against what survived into the system. | `inbound_erp_mismatch` findings |
| "Can you **bounce a bad shipment before you accept it**?" | **Pre-receipt validation** — validate an incoming ASN/BOL and return accept/hold *before* the truck is unloaded. | `/internal/inbound/validate` endpoint |
| "Which of my **partners** are the problem?" | **Partner scorecard** — every trading partner graded A–D on data completeness. | `partnerScorecard` |
| "Scanned paper **BOLs** are a reality." | **BOL PDF extraction** (incl. Claude vision for scanned docs). | Pre-receipt + door-vs-db |
| "Does the data actually let you **run a recall**?" | **Lot-integrity rulepack** — backward lineage, mass balance, duplicate lots, date plausibility. | `lotIntegrityChecks` |
| "Retailers (Walmart/Kroger) want **GS1 barcodes/GTINs**." | **GS1 validation + retailer overlays.** | `gs1Checks` |
| "Give them a way to **get clean data into a platform**." | **EPCIS 2.0 export** — the GS1 industry-standard interchange format. | `epcisStats` |
| "The corrective-action loop — **what got fixed since last time**." | **Audit delta** (re-audit comparison). | (roadmap; scaffolding built) |
| "You've just **scoped my whole project** for me." | **Scoping report + plain-English narrative.** | `scopingReport` |

**The one-line positioning to remember:** *nobody else audits the export before you buy a
platform, and nobody else gives deterministic, FDA-cited verdicts.*

---

## 2. Glossary A — FSMA 204 regulatory terms (the words Jim will use)

These are the regulator's terms. Learn these five acronyms cold: **FTL, CTE, KDE, TLC,
Traceability Plan.**

- **FSMA 204** — Section 204 of the Food Safety Modernization Act. The law behind the rule.
  The actual regulation is **21 CFR Part 1, Subpart S** (§ 1.1300–1.1455). Compliance date:
  **July 20, 2028** (now statutory — set by Congress, not just proposed).

- **FTL — Food Traceability List.** The FDA's list of ~23 higher-risk food categories the
  rule applies to (leafy greens, shell eggs, nut butters, fresh herbs, cheeses, **crustaceans/
  shrimp**, finfish, molluscan shellfish, cucumbers, melons, sprouts, tomatoes, tropical fruit,
  ready-to-eat deli salads, etc.). If your food isn't on the FTL, the rule mostly doesn't apply.
  *This is why Sea Eagle's shrimp is in scope and why "declared General products" that are
  actually shrimp is a finding.*

- **CTE — Critical Tracking Event.** A point in the supply chain where the rule requires you to
  keep records. There are seven, each with its own CFR section:
  - **Harvesting** (§ 1.1325) — a farm harvests a crop.
  - **Cooling** (§ 1.1325) — pre-packing cooling of produce.
  - **Initial Packing** (§ 1.1330) — first packing of a raw agricultural commodity.
  - **First Land-Based Receiving** (§ 1.1335) — the dock that first receives seafood off a
    fishing vessel (the seafood chain's anchor point).
  - **Shipping** (§ 1.1340) — food leaves you toward a customer.
  - **Receiving** (§ 1.1345) — food arrives from a supplier.
  - **Transformation** (§ 1.1350) — you turn input lots into a new product/lot (e.g. peel &
    devein shrimp, make a salad kit).

- **KDE — Key Data Element.** The specific fields the rule requires you to record **for each
  CTE**. Example: a shipping event must record the TLC, the product description, quantity,
  ship-to location, ship-from location, ship date, reference document, and the TLC source.
  *A "gap" in our report = a required KDE is missing.*

- **TLC — Traceability Lot Code.** The lot identifier that ties a batch of food together
  through the whole chain. The single most important field — it's how the FDA pivots from "this
  shipment" to "where did this lot come from."
  - **TLC source** — the location where the lot code was assigned (where the lot was created).
  - **TLC source reference** — a document reference for that.

- **Traceability Plan** (§ 1.1315) — a written plan every covered business must keep. Five
  required components: (1) how you maintain records, (2) how you identify FTL foods, (3) how
  you assign TLCs, (4) a point of contact, (5) a farm map (growers only). *Our report checks
  all five.*

- **Exemptions** (§ 1.1305) — carve-outs (very small farms under $25k, some retail/restaurant
  cases, certain commingled commodities, an IMS Grade "A" cottage-cheese partial exemption as
  of Feb 2026, etc.). We surface exemption *questions* but never auto-clear a business.

- **Backward / forward traceability** — the ability to trace a lot one step back (where it came
  from) and one step forward (where it went). A recall needs both.

---

## 3. Glossary B — TraceReady product & engineering terms (the words your partner needs)

These are *our* terms — the vocabulary of how the backend works. **The most important concept
is the first one; if your partner learns only one thing, make it this.**

- **Perception vs. Judgment** — the core design principle, and our whole credibility story.
  - **Perception** = *reading* the messy input: which sheet is a shipping log, which column is
    the lot code, is "White Tails 31/35" a shrimp product, write the plain-English summary.
    This is fuzzy, so we use an **LLM (AI)** — but only here.
  - **Judgment** = *deciding* whether a record complies: is a required KDE missing? does this
    lot trace back? This is **100% deterministic code checking against reviewable rule files**,
    with a CFR citation. **The AI never decides compliance.** It can misread a column, but it
    can never invent a value or a verdict.
  - Why it matters: when Jim asks "how do I know the AI didn't make this up?" — the answer is
    *the AI didn't judge anything; a rule file did, and here's the regulation quote.*

- **`requirement_source`** — stamped on every finding. Tells you **who requires this**:
  - `fda_rule` — the FDA actually requires it; carries a real 21 CFR citation.
  - `customer_requirement` — a retailer mandate (Walmart/Kroger GS1), not the FDA.
  - `best_practice` — **our own** recall-readiness / data-quality check, *not* a legal
    requirement. These say so in plain text and carry no CFR citation.
  - *This field is the honesty layer. It stops us from ever claiming the FDA requires something
    it doesn't — the fastest way to lose credibility with an expert like Jim.*

- **`basis`** — the same idea (`regulation` vs `best_practice`) on lot-integrity checks.

- **Canonical field / mapping** — our internal standard name for a piece of data (e.g.
  `traceability_lot_code`). The AI's job is to map the customer's column ("Lot Assigned",
  "LOT #", "New Lot") to the canonical name. Everything downstream speaks canonical.

- **Universal intake** — the property that we can ingest *any* workbook layout without
  pre-configuration, because the mapping is learned per-file, not hardcoded.

- **Systemic gap / rollup** — when the *same* gap appears on many rows (e.g. 145 transformation
  records all missing the source lot), we collapse them into **one** finding ("Systemic gap
  across 145 records…") instead of 145 copies. It signals the problem is the *template/system*,
  not data entry.

- **Export window** — the date range your file covers. If a shipped lot's code shows a date
  *before* the window starts, we say "the origin record is probably in a prior period — request
  it" (`records_predate_window`) instead of falsely calling the chain broken.

- **Pre-receipt validation ("door bounce")** — validating an incoming shipment's paperwork
  (ASN/BOL) and returning **accept / hold / not-in-scope** *before* you take the product in.

- **Door-vs-database diff** — comparing what the supplier's document carried against what
  actually landed in the system of record, to catch fields the ERP silently dropped.

- **FTL three-tier classification** — every product is sorted into:
  - `definite_on` — clearly on the Food Traceability List.
  - `suspicious` — might be; needs a human to confirm (e.g. a composite/prepared food).
  - `definite_off` — clearly not (shelf-stable canned tuna, frozen cheese, dried herbs).

- **Partner scorecard bands (A–D)** — a trading partner's data-quality grade. A = complete,
  D = recurring gaps or received bad-lineage lots.

- **EPCIS 2.0** — the GS1 industry-standard event format. Exporting to it is the bridge that
  lets a customer take clean data into a real platform (iFoodDS, ReposiTrak, etc.).

- **GS1 / GTIN / SSCC / GS1-128** — the barcode/identifier standards retailers require. GTIN =
  the product number; SSCC = the pallet number; GS1-128 = the barcode that carries them plus
  the lot and date. We validate the check digits.

- **llm-cache (the AI cache)** — the AI's *verified* answers, stored by an exact hash of the
  input. Two things to know: (1) a cache hit only happens for a **byte-identical** input — a
  new customer can never reuse another customer's answers; (2) **nothing is stored unless it
  first passed our deterministic verifier.** So the cache makes demos fast and repeatable
  without weakening correctness. (`generatedBy: "llm_cached"` in the report just means "served
  from that verified cache.")

- **Recall harness / gold set** — our test suite. A "gold" file lists the findings a known
  workbook *must* produce; the harness fails if a code change would miss any. This is how we
  keep accuracy from regressing.

---

## 4. The complete backend feature list

Grouped by what they do. Every one is live and running today.

### A. Intake & understanding (getting messy data in)
1. **Universal workbook intake** — ingest any `.xlsx`/`.csv`, any layout; AI sheet & column
   mapping with deterministic verification; per-file learned, no templates.
2. **Robust parsing** — handles merged banner rows, junk/notes rows, DD/MM vs MM/DD dates,
   multi-line events, native Excel dates, formula cells.
3. **EDI X12 856 (ASN) parser** — electronic advance shipping notices.
4. **BOL (Bill of Lading) PDF extraction** — text PDFs and, for scanned images, Claude vision.

### B. Reconstruction (turning rows into a supply chain)
5. **Event graph** — every row becomes a Critical Tracking Event tied to a lot.
6. **Entity graph** — businesses, locations, products, trading partners resolved from the data.
7. **CTE classification** — each event labeled shipping/receiving/transformation/etc.
8. **FTL three-tier product classification** — on-list / suspicious / off-list, with reasoning.

### C. The audit (the deterministic, cited judgment)
9. **KDE completeness checks** — every required Key Data Element per CTE, against reviewable
   rule contracts, with CFR citations.
10. **TLC lineage checks** — does every lot trace back to an origin record?
11. **Traceability-plan check** — the five § 1.1315 components.
12. **Scope & exemption review** — surfaces products/claims that need a scoping decision.
13. **Lot-integrity rulepack** (recall-readiness, labeled best-practice):
    backward lineage · forward linkage · duplicate-TLC-across-products · mass balance
    (shipped vs originated) · date plausibility · self-receive detection · transformation
    input↔output linkage.
14. **Systemic-gap rollup** — collapses repeated identical gaps into one template-level finding.
15. **Export-window awareness** — pre-window lots flagged "request prior records," not "broken."

### D. Partner & retailer layer
16. **Partner scorecard** — every trading partner graded A–D with per-product breakdown.
17. **GS1 validation** — GTIN/GLN/SSCC check digits, GS1-128 barcode parsing.
18. **Retailer overlays** — Walmart / Kroger / Albertsons GS1 mandates as `customer_requirement`.

### E. Pre-receipt & reconciliation (Jim & John's asks)
19. **Pre-receipt validation endpoint** — accept/hold/not-in-scope on an incoming ASN/BOL
    before receipt.
20. **Door-vs-database diff** — supplier-sent vs system-of-record, catches dropped fields and
    quantity conflicts.

### F. Outputs & reporting
21. **Readiness rollup** — ready / needs_review / blocked.
22. **Scoping report + AI narrative** — plain-English executive summary, every number verified
    against the computed stats.
23. **EPCIS 2.0 JSON-LD export** — clean-data bridge into platforms.
24. **19 downloadable artifacts** — the full evidence package (obligation mappings, KDE
    results, export package, exception queue, etc.).

### G. Quality & governance (why it stays correct)
25. **Recall harness + gold sets** — regression suite; 100% must-find recall on both golds.
26. **Dress-rehearsal script** — one-command go/no-go for the demo.
27. **Corpus integrity checks** — the CFR text we cite is verified against source.
28. **Reviewer-label flywheel** — human confirm/reject decisions outrank the AI and feed back
    in as ground truth.
29. **Verified AI cache** — fast, repeatable, verify-before-store.

---

## 5. How to read the API response (the teaching walkthrough)

This is the section to practice out loud. The report is one JSON object with three layers.

### Layer 1 — The verdict (glance)
```json
"fileName": "SeaEgle-010125-011025.xlsx",
"readiness": "blocked"
```
- **`readiness`** is the traffic light:
  - `ready` — nothing blocking.
  - `needs_review` — only soft issues a human should eyeball.
  - `blocked` — at least one **high-severity FDA gap** (a real missing required field).

### Layer 2 — The summary (the dashboard numbers)
```json
"summary": {
  "events":    { "total": 761, "byCte": { "shipping": 551, "transformation": 145, ... } },
  "products":  { "total": 32, "byFtlTier": { "definite_on": 32, ... }, "mismatchCount": 2 },
  "partners":  { "external": 29, "bandCounts": { "A": 29, ... } },
  "kdeCoverage": { "rate": 0.9692, "presentCount": 6576, "missingCount": 209 },
  "findingsBySeverity": { "high": 5, "medium": 8 },
  "findingsByType": { ... },
  "intake": { "generatedBy": "llm_cached", "sheetKinds": { "Shipping KDEs": "cte_shipping", ... } }
}
```
Teach these in order:
- **`events.byCte`** — how many supply-chain events we reconstructed, by type. "761 events" is
  the proof we understood the whole file.
- **`products.byFtlTier` + `mismatchCount`** — how many products are on the FTL, and how many
  were *declared* one thing but *detected* as another (the "you labeled shrimp as General
  products" catch).
- **`kdeCoverage.rate`** — the completeness score. 0.9692 = 96.92% of required fields present.
- **`intake`** — **the "how the AI read your file" receipt.** `sheetKinds` shows every tab and
  how it was classified. `generatedBy: llm_cached` = served from the verified AI cache. *This is
  where you'd catch a misread before trusting anything else.*

### Layer 3 — The evidence (the detailed lists)

**`findings[]` — the heart.** Each finding decoded:
```json
{
  "severity": "high",                    // high | medium
  "status": "gap",                       // gap = real miss; needs_review = human check
  "cte": "transformation",               // which event type
  "finding_type": "tlc_lineage",         // the category
  "message": "Systemic gap across 145 transformation records: ... missing its TLC.",
  "requirement_source": "fda_rule",      // ← WHO requires it (see §3)
  "source_citation": { "section_ref": "21 CFR 1.1350", "support_text": "(a) ... you must
                        maintain records containing ... the traceability lot code ..." },
  "affected_fields": ["source_lot_or_tlc"],
  "sub_issues": [ "Missing source Traceability Lot Code ...", "..." ],
  "customer_evidence_ids": [ "ev-...-r10-c1", ... ]   // exact cells this came from
}
```
The three fields to read every time: **`status`** (real gap vs review), **`requirement_source`**
(FDA vs best-practice — never oversell), **`source_citation`** (the actual rule quote for FDA
findings).

**`lotIntegrityChecks[]`** — the lot-level recall-readiness detail (backward lineage, duplicate
lots, mass balance…). Each carries `basis` (`regulation` vs `best_practice`). Many `findings`
are rollups of these.

**`ftlTierResults{}`** — per product: tier, matched commodity, `mismatch`, the AI's `reasoning`,
and `method`. Where the shrimp-vs-"General products" logic lives.

**`partnerScorecard{}`** — each partner's A–D band, fill rate, event count, per-product
breakdown. Your "which suppliers/customers have clean data" deliverable.

**`gs1Checks[]`** — barcode/GTIN check-digit validation (empty when the data uses no GS1 IDs).

**`scopingReport{}`** — `stats` + a `narrative`: the plain-English executive summary, with every
number verified to come from the stats (the AI can't invent a figure here).

**`epcisStats{}`** — how many events exported to the EPCIS 2.0 industry format.

### The one mental model
> Every list item = **a verdict** (status/tier/band) + **why** (message/reasoning) + **proof**
> (citation or evidence IDs) + **provenance** (requirement_source / basis / method).
>
> Nothing is an unsourced assertion. That's the whole product.

---

## 6. The demos nobody else has (talking points)

When you want to show *differentiation*, show these five — incumbents don't do any of them:

1. **Audit the export before any platform** — upload messy Excel, get a cited readiness verdict
   in seconds.
2. **Deterministic, FDA-cited verdicts** — every "you're missing X" quotes the regulation;
   competitors' AI tools *judge* with the AI (unciteable).
3. **Partner scorecard** — a first-class deliverable, not a byproduct.
4. **Pre-receipt bounce** — reject a non-compliant shipment at the door.
5. **Door-vs-database diff** — prove the ERP is silently dropping supplier data.

---

## 7. What's verified vs. what's next (be honest with Jim)

**Verified end-to-end on real data:** universal intake on 3 very different workbooks (the demo
template, Jim's Sea Eagle export, and an adversarial multi-category fixture we built to stress
it), all seven CTEs, KDE/lot/FTL/partner/GS1/EDI/BOL paths, pre-receipt, door-vs-db, EPCIS
export, scoping narrative. Recall harness: 100% must-find on both gold sets. The Sea Eagle
Postman run you validated is the proof.

**Known next steps (roadmap, already scoped):** a handful of remaining template-specific
assumptions to remove (we found them with the adversarial fixture and have a phased plan), full
exemption-threshold cards, cache-governance tooling, and the re-audit "what got fixed" delta.
None of these block the demo; all are documented.

---

## Appendix — one finding traced end-to-end (the story to tell)

*How a single empty spreadsheet cell becomes a "blocked" verdict with FDA rule text behind it.*

Take Sea Eagle's finding-0002 ("145 transformation records missing their source TLC"):

1. **The cell.** Row 10 of the "Transformation KDEs Produced Fo" tab has a *new* lot code but
   **no column naming the input lot** it came from. Every cell is stored as an evidence record
   with an ID like `ev-...-r10-c1` — a pointer back to the exact cell.
2. **The mapping (AI perception).** The AI labeled that sheet `cte_transformation_output` and
   mapped its columns — and found no column that means "source lot." It did **not** invent one.
3. **Event minting.** The row becomes a transformation event with the source-lot field empty.
4. **The KDE check (deterministic judgment).** A reviewable rule contract says
   `source_lot_or_tlc` is **required, high severity** for transformation. Code sees it's empty
   → `gap`. The AI had no vote here.
5. **The rollup.** All 145 rows have the identical gap → one "systemic" finding, not 145.
6. **The citation.** The finding attaches the § 1.1350 obligation with the **verbatim** rule
   text and stamps `requirement_source: fda_rule`. Because a real CFR duty backs it, the whole
   file is `readiness: blocked`.

The point for Jim: *the only subjective step is reading your column headers, and it's fenced —
it can't manufacture a value or a verdict. Every "you're missing X" is deterministic code
against a reviewable rule, with a cell reference and a regulation quote attached.*
