# Thursday Demo Backend Build Plan — v2 (2026-07-07 → 2026-07-10)

Goal: by **Thursday morning (2026-07-10)**, the backend implements everything from the
2026-07-03 Jim/John call, working end-to-end, demoed locally. No MVP cuts. No hardcoded
per-template mappings. Tests and security explicitly deferred.

Principle carried over from the accuracy roadmap: **verdicts stay deterministic and cited;
AI/LLM does perception** — document understanding, field mapping, FTL interpretation,
narrative. An LLM never decides compliance.

---

## WS-A — Universal document understanding (NO hardcoding)

`audit_engine/intake/` package.

**Any spreadsheet, any layout.** For every uploaded xlsx/csv:
1. **Profile** each sheet mechanically: headers, sample rows, fill rates, value patterns
   (dates, quantities, codes) — no assumptions about template.
2. **LLM mapping** (Sonnet, temperature 0): given the profile + the canonical FSMA schema
   (CTE types + KDE field registry), the model returns per-sheet semantics (which CTE or
   master-data type the sheet represents, or "not traceability data") and per-column mapping
   to canonical KDE slugs with confidence + reasoning.
3. **Deterministic verification:** every returned slug must exist in the canonical registry;
   every returned sheet type must be a known record type; anything else is rejected and
   retried once, then marked unmapped (finding: "unrecognized data — human mapping needed").
   The LLM cannot invent fields.
4. **Mapping cache** keyed by (sheet-name + header-set) hash: repeat uploads and the live
   demo never re-call the LLM and always produce identical mappings. Cached mappings are
   stored as reviewable artifacts (field-mapping governance already exists in the engine).
5. Mechanical normalization behind the mapping: dates in any format (US/ISO/Excel serial),
   floats-as-IDs, lost leading zeros, whitespace, `undefined`/junk rows, empty sheets,
   cross-sheet pointer values, duplicate headers, merged cells, multi-file uploads.

This replaces template aliases entirely — the ENSESO4Food file, our demo workbook, and any
ERP/WMS export a prospect sends all go through the same path. (The existing FIELD_ALIASES
stays only as a zero-cost fast path when a header already *is* the canonical name.)

## WS-B — EDI / ASN / BOL inbound-document intake ("what comes through the door")

`audit_engine/inbound/` package.

1. **X12 EDI parser** (deterministic): segment/element parser with envelope handling
   (ISA/GS/ST), transaction sets **856 (ASN)** first-class; 850/810/940/945 parsed
   structurally and mapped opportunistically. Extracts shipment hierarchy (HL loops),
   lot numbers (LIN/SN1/REF), dates (DTM), parties (N1), quantities.
2. **BOL / paper-doc extraction:** PDFs and images of BOLs run through the existing
   `extractors/pdf_extractor.py` + LLM extraction into the same canonical KDE records
   (with per-field confidence and source pointers).
3. **Door-vs-database comparison:** when both an inbound doc set and a system export are
   provided, diff the KDEs: fields the supplier actually sent vs fields that survived into
   the ERP/WMS export → "your system is dropping KDEs your suppliers already send" findings
   (John's cautionary note, as a feature).

## WS-C — Pre-receipt / trading-partner validation API ("don't ship me what I can't accept")

- New endpoint: `POST /v1/inbound/validate` — accepts an ASN/EDI file, BOL, or spreadsheet
  of intended shipments; returns per-line verdicts immediately: missing/invalid KDEs, FTL
  scope of each product, lot-code validity, with citations. Synchronous, no job queue —
  built for the live demo moment ("supplier sends this, we bounce it with exact reasons").
- The same engine run in reverse: an operator can validate what they're *about to ship* to a
  customer (Walmart-overlay aware, see WS-F).

## WS-D — Lot & lineage integrity rulepack

`audit_engine/lot_integrity.py`.

- Backward lineage for every shipped lot (origin must exist: received/transformed/FLR/
  initial-pack), with **export-window awareness** (origin predates the file's window →
  "request those records", not "broken chain").
- Forward linkage (originated lots that vanish), orphan detection.
- **Lot-format profiler:** learns the operator's dominant lot pattern(s) from the data
  itself (no hardcoded formats); flags outliers; if the pattern embeds a date, checks lot
  date vs event date.
- **Duplicate/static/counterfeit TLC signals:** same lot across distinct products, one lot
  everywhere, reused lots across time — with the transformation carve-out (multi-SKU outputs
  of one transformation event → `review`, not `must_fix`).
- **Mass balance** per lot (shipped ≤ originated, unit-aware; mixed units → "cannot verify"
  note, never a false finding). Multiple origins, partial shipments, zero/negative
  quantities handled.
- **Date ordering** (ship ≥ transform ≥ receive/landing), same-day tolerant.

## WS-E — FTL three-tier classifier (interpretation, not lookup)

`audit_engine/ftl_classifier.py`.

- LLM classification of every product against the approved FTL cards →
  `definite_on | suspicious | definite_off` + commodity + citation + reasoning.
- Deterministic verification (returned commodity must exist on the FTL), result cache for
  reproducibility, LLM only on cache miss.
- **Declared-vs-inferred cross-check:** customer marks a product non-FTL but the classifier
  disagrees (Sea Eagle's frozen shrimp as "General products") → headline finding.
- Composite foods (salad mix, sandwiches) → suspicious by default; kill-step/form qualifiers
  (frozen/cooked/canned) applied from the FTL's own form rules; obvious non-food short-
  circuited without an LLM call; empty/gibberish names; conflicting duplicates.

## WS-F — GS1 + retailer-overlay rulepack

`audit_engine/gs1_rules.py`.

- GTIN-8/12/13/14 + GLN check-digit and structure validation (only on values that claim or
  appear to be GS1 identifiers; Excel-float/leading-zero tolerant).
- **`requirement_source` dimension on findings:** `fda_rule` vs `customer_requirement`.
  Walmart GS1 mandate ships as the first bundled overlay card; overlay cards are data, so
  Kroger/Albertsons drop in without code changes.

## WS-G — Trading-partner scorecard (the supplier gap analysis)

`audit_engine/partner_scorecard.py`.

- Counterparty resolution across location→owner joins, partner master, business master, and
  inbound docs (WS-B); whitespace/fuzzy tolerant; internal-transfer vs external-partner;
  supplier-vs-customer direction per CTE.
- Per partner × product × KDE: fill rate, quality flags, integrity hits → ranked scorecard
  ("here's the list of people who don't give me the information I need"), persisted as an
  artifact + summary findings for the worst offenders.
- Unresolvable destinations bucketed explicitly; zero/single-partner files handled.

## WS-H — Scoping report + corrective-action delta

`audit_engine/scoping_report.py`.

- Deterministic aggregates: products by FTL tier, partners by score band, events by CTE, KDE
  coverage %, top gaps, window covered, per-sheet/per-source data-quality grades — "you have
  just scoped my FSMA 204 project."
- **LLM executive narrative from deterministic stats only** (numbers/citations injected,
  never invented).
- **Re-audit delta:** compare two runs of the same customer → "what got fixed / what's new"
  (the corrective-action loop John described: assess → fix → re-run → show improvement).

---

## Schedule

| Day | Deliverable |
|---|---|
| Mon 07-07 | WS-A universal intake working on Sea Eagle + demo workbook end-to-end |
| Tue 07-08 | WS-D + WS-F rulepacks; WS-B EDI/BOL parsing |
| Wed 07-09 | WS-E + WS-G + WS-C + WS-H; full dress rehearsal locally on all inputs |
| Thu 07-10 | Buffer + demo |

## Demo environment (local)

- Python backend + Next.js app locally; `ANTHROPIC_API_KEY` in backend env; Supabase as
  today; `BELLWETHER_PYTHON_API_URL=http://127.0.0.1:8000`.
- Dress-rehearsal inputs: Sea Eagle export, demo workbook
  (`data/samples/fsma204-full-audit-sample.xlsx`), a synthetic X12 856 ASN + BOL PDF pair
  (to demo WS-B/WS-C live), and a deliberately-broken shipment file for the bounce demo.
- All LLM mappings/classifications cached during rehearsal → Thursday's run is cache-hits
  only: fast, deterministic, no live-API risk mid-demo.

## Risk & drop order (only if a day overruns)

WS-H delta → WS-B 850/810/940/945 breadth (856+BOL stay) → WS-G fuzzy merge. The core story
(universal AI intake → deep findings → scorecard → pre-receipt bounce) is not droppable.
