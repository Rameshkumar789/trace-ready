# Thursday Demo Backend Build Plan (2026-07-07 → 2026-07-10)

Goal: by **Thursday morning (2026-07-10)**, the backend implements every capability Jim and
John asked for on the 2026-07-03 call, working end-to-end on **Jim's real Sea Eagle file** and
the existing demo workbook, demoed from a **local machine**.

Scope decisions for this sprint: backend only (the frontend already renders whatever findings
the backend persists), no new tests, security deferred. Verdicts stay deterministic and cited;
LLMs are used for perception only (header mapping, FTL interpretation, report narrative) —
never to decide compliance.

## How the backend flows today (for orientation)

Upload (Next.js app) → synchronous call to the Python FastAPI backend
(`BELLWETHER_PYTHON_API_URL`) → **parse job** (`audit_engine/customer_evidence.py::
read_spreadsheet_evidence` → generic per-cell evidence records via `FIELD_ALIASES`) →
**rule execution job** (`audit_engine/rule_execution.py` builds entity/event graphs and runs
cited checks against approved rule cards) → **findings persisted to Supabase** → app renders
them. New checks = new findings = they appear in the UI automatically.

---

## Workstream 1 — Flexible intake: ingest the ENSESO4Food/Trakkey template (Mon)

New `audit_engine/intake_mapping.py` + extensions to `customer_evidence.py`.

- Expand `FIELD_ALIASES` for the ENSESO4Food vocabulary (`LOT Assigned`, `LOT Number`,
  `Landing date`, `Ref. Document Type/Number`, `Source/Destination Location ID/Description`,
  `FTL Group`, `Quantity Packed Food`, …).
- **Sheet-name → CTE inference**: their template is one-CTE-per-sheet with no event-type
  column (`Shipping KDEs` → shipping, `First Land based Rec. KDEs` →
  first_land_based_receiving, `Transformation KDEs Ingredients/Produced Fo` → transformation
  ingredient/output sides, `LOT Assignment`/`Traceability plan` → plan-level).
- **LLM header-mapping fallback**: unmatched headers go to Sonnet with the canonical KDE slug
  list; result must map to a known slug (deterministic verification); cached per header
  string so repeat uploads are LLM-free; unmappable headers become "unrecognized field"
  notes, never crashes.
- Edge cases handled (seen in the Sea Eagle file or likely): fully-`undefined` junk rows;
  empty and header-only sheets; cross-sheet pointer values ("See Harvesting KDEs sheet");
  dates as `MM/DD/YYYY`, ISO, and Excel serials; numeric IDs mangled to floats
  (`4598767.0`); leading zeros lost on GTINs; trailing/inconsistent whitespace in names;
  duplicate headers in one sheet; merged/blank header cells; CSV variants; same lot value
  with different padding/case.

**Exit criterion (Mon):** Sea Eagle file parses, builds the event graph, and runs all
existing checks with sane results through the real upload path.

## Workstream 2 — Lot & lineage integrity rulepack (Tue)

New `audit_engine/lot_integrity.py`, cited checks integrated into `rule_execution.py`.

- **Backward lineage:** every shipped lot must have an origin (received / transformed / FLR /
  initial pack). **Export-window awareness:** lot whose inferred date predates the earliest
  record in the file → "origin predates provided window — request those records", not
  "broken lineage" (the Sea Eagle Sep–Nov 2024 lots).
- **Forward linkage:** originated lots that never ship/transform → inventory-or-gap note.
- **Lot-format profiler:** learn dominant lot pattern(s) from the data; flag outliers; if the
  pattern embeds a date, check lot date vs event date (catches "shipped before its own lot
  date").
- **Duplicate/static TLC detection:** same lot across distinct products (Jim's counterfeit
  check), with the transformation carve-out — multi-SKU outputs of one transformation event
  get `review` severity plus an explicit reviewer question, not `must_fix`.
- **Mass balance:** shipped ≤ originated per lot, only when units are comparable; mixed units
  → "cannot verify" note, not a false finding. Handles multiple origins per lot, partial
  shipments, zero/negative quantities.
- **Date ordering:** ship ≥ transform ≥ receive/landing per lot; tolerant of same-day events
  and missing timestamps.

## Workstream 3 — FTL three-tier classifier (Wed)

New `audit_engine/ftl_classifier.py` (accuracy-roadmap WS1, built now).

- LLM classifies each product against approved FTL cards (already in `data/regulatory/`) →
  `{tier: definite_on | suspicious | definite_off, commodity, reasoning, citation}`.
- **Deterministic verification:** returned commodity must exist on the FTL (hallucination
  guard); confirmed matches cached → reproducible verdicts, LLM only on cache miss.
- **Declared-vs-inferred cross-check:** customer says non-FTL, classifier says on/suspicious
  (the frozen-shrimp-as-"General products" case) → headline finding: "product may be escaping
  traceability requirements."
- Edge cases: composite descriptions (salad mix, sandwich) → suspicious by default; form/
  kill-step qualifiers (frozen, cooked, canned) evaluated against FTL forms; obvious non-food
  → definite_off via cheap heuristic without an LLM call; empty/gibberish names; conflicting
  duplicate products.

## Workstream 4 — Trading-partner scorecard (Wed)

New `audit_engine/partner_scorecard.py` + scorecard artifact + findings.

- Resolve every event's counterparty (location→owner join, partner master, business master;
  whitespace/fuzzy tolerant), classify internal transfer vs external partner, infer
  supplier-vs-customer direction per CTE.
- Per partner × product × KDE field: fill rate, quality flags, lot-integrity hits → ranked
  scorecard + per-partner worst findings ("the list of people who don't give me the
  information I need").
- Edge cases: unresolvable destinations get their own bucket; partners under multiple
  spellings merged; zero/single-partner files.

## Workstream 5 — GS1 + retailer-overlay rulepack (Tue)

New `audit_engine/gs1_rules.py`.

- GTIN-8/12/13/14 and GLN check-digit + structure validation, applied only to values that
  claim to be or look like GS1 identifiers; Excel-float/leading-zero tolerant.
- Findings carry `requirement_source`: `fda_rule` vs `customer_requirement`; Walmart overlay
  ("must use GS1 identifiers") ships as the first bundled overlay card.

## Workstream 6 — Scoping report (Wed)

New `audit_engine/scoping_report.py` + artifact (+ API route if needed).

- Deterministic aggregates: products by FTL tier, partners by score band, events by CTE, KDE
  coverage %, top gaps, window covered, per-sheet data-quality grade.
- **LLM executive narrative generated from the deterministic stats only** (numbers/citations
  injected, never invented) — the one-page "magnitude of your problem" summary.

---

## Schedule

| Day | Deliverable |
|---|---|
| Mon 07-07 | WS1: Sea Eagle file runs end-to-end through the real pipeline |
| Tue 07-08 | WS2 + WS5: lot/lineage/mass-balance/GS1 findings live |
| Wed 07-09 | WS3 + WS4 + WS6, full dress rehearsal on Sea Eagle + demo workbook |
| Thu 07-10 | Buffer + demo (local machine) |

## Demo environment (local)

- Run Python backend + Next.js app locally; exact run steps to be written Wed.
- Required env: `ANTHROPIC_API_KEY` (backend `.env`), Supabase keys as today,
  `BELLWETHER_PYTHON_API_URL=http://127.0.0.1:8000` in the app.
- Dress-rehearsal inputs: Jim's Sea Eagle export + `data/samples/fsma204-full-audit-sample.xlsx`.

## Risks

- **Biggest risk is WS1** (real-world parsing) — that's why it's first and alone on Monday.
- LLM calls during a live demo: all classification results are cached from the dress
  rehearsal, so Thursday's run hits caches and cannot stall or change verdicts.
- If Wednesday overruns, the drop order is: WS6 narrative polish → WS4 fuzzy partner merge →
  WS3 composite-food nuance. Findings from WS1/WS2/WS5 are already demo-worthy.
