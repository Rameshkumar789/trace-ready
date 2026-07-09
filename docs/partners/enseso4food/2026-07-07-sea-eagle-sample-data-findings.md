# Sea Eagle Sample Data — First Real-World Audit Findings

- **Analyzed:** 2026-07-07
- **Source:** `SeaEgle010125011025.xlsx`, emailed by Jim White after the 2026-07-03 demo call
  (the "Craig's" pilot dataset — contact on the Business Master is Craig Reaves).
- **What it is:** an ENSESO4Food / Trakkey CS sortable-spreadsheet export for **Sea Eagle
  Market** (Beaufort, SC) — a wild-caught-shrimp **first land-based receiver + processor +
  distributor**. 13 sheets in the ENSESO4Food template. Event data spans **2025-01-03 to
  2025-09-23**: 64 first-land-based-receiver rows, 551 shipping rows, 145 transformation
  produced rows, 118 transformation ingredient rows, 1 receiving row.
- **Raw file:** kept out of git (real customer/partner names and addresses). Local copy in the
  session scratchpad; the original is in Ramesh's email from Jim.
- **Method:** one-off analysis script (profiling, lot-lineage graph, mass balance, lot-format
  and date-plausibility checks, GTIN-14 check digits, destination/owner mapping). The engine's
  current workbook intake was NOT used — this template doesn't match it (see §4).

---

## 1. Structural gaps (template/plan level)

1. **Traceability plan sheet is completely empty.** No required-records description, no TLC
   assignment description, no point of contact. This is a core FSMA 204 traceability-plan
   obligation and the clearest must-fix in the file.
2. **LOT Assignment sheet is completely empty.** No documented method/format for how TLCs are
   assigned (they clearly have one — see §3.1 — but it is undocumented).
3. **Harvesting, Cooling, and Packing KDE sheets are empty — while all 64 FLR rows point at
   them** (`Harvesting KDEs = "See Harvesting KDEs sheet"`). The first-land-based-receiver
   records therefore carry **no harvest date range, harvest location, or vessel/harvester
   information at all** — the exact upstream KDEs an FLBR exists to capture. Broken reference,
   systematic (64/64 rows).
4. **Transformation ingredients cannot be joined to transformation outputs.** The Ingredients
   sheet has only 7 columns (product, qty, lot) — no date, no location, no reference-document
   column. The Produced sheet has TR reference numbers, but nothing on the ingredient side
   links an ingredient lot to a specific TR event. Ingredient→output lineage is unprovable
   *from this export* (it may exist inside Trakkey, but the sortable spreadsheet — the thing
   FDA actually asks for — can't demonstrate it).
5. **Contact KDEs are ~0% populated everywhere.** Phone/email columns: 0/551 shipping, 0/64
   FLR, 0/145 transformation. Business Master: contact person on 2/29 businesses, and the only
   email in the whole file is `jmoss@enseso4food.com` (the vendor, not the operator).
6. **Location Master is partly corrupt.** 16 of 49 rows are literally the string `undefined`
   in every field; 48/49 rows have `undefined` coordinates; 16 shipping rows point at
   destination location IDs that don't resolve in the Location Master.
7. **Shipping schema has no immediate-subsequent-recipient business field** — only destination
   *location* IDs/descriptions. Recipient identity is recoverable only by joining location →
   owner, and (per §1.6) that join breaks for 16 rows.

## 2. Record-level findings (the "deep validation" checks)

1. **6 shipped lots (8 rows, ~10,300 lb) have no origin record anywhere in the export** — not
   on FLR, not transformation-produced, not received. All six have lot-embedded dates of
   **Sep–Nov 2024**, i.e. before the export window opens (2025-01-01). Most likely export-window
   truncation (inventory landed in 2024, shipped in 2025) rather than fraud — but as submitted,
   backward lineage for those shipments is not demonstrable, and an FDA records request for
   those TLCs would need the 2024 records produced separately.
2. **40 of 93 transformation-produced lots share one TLC across two or more distinct
   products** (e.g. lot `2507240202` = both "White Shrimp PAD Tail-Off 21/25" and "White Shrimp
   PAD Fan Tail 21/25", same TR ref). Systematic pattern, flows through to 36 shipped lots. One
   transformation event producing multiple SKUs under a single lot makes a lot-level recall
   ambiguous — this is a real-world, milder version of Jim's "same lot code on every product"
   check, and their point-of-entry validation did not catch it.
3. **Mass-balance breach:** lot `2505130159` shipped **372 lb** against **322 lb** documented
   origin (+50 lb shipped that was never received/produced on paper).
4. **Date-plausibility breach:** lot `2502170105` was shipped **2025-02-15**, two days *before*
   its lot-embedded date (2025-02-17).
5. **The single Receiving row is a self-receive** (source location = destination location =
   their own facility) — and receiving is essentially unused as a CTE (1 receiving event vs 551
   shipments over ~9 months). Whatever they receive from others is not being recorded as
   receiving CTEs.
6. **Probable FTL misclassification (the "ham sandwich" tier, live):** 30/32 products are
   correctly FTL-grouped as Crustaceans, but 2 are classed **"General products"** (i.e. treated
   as non-FTL): `white 21/25 tails 25lb box` and `white Tails on 31/35 Frozen`. Both read as
   **shrimp** — and crustaceans (fresh *and frozen*) are on the FTL. If that read is right,
   every event on those SKUs is silently escaping KDE requirements. Exactly the
   definite/suspicious/not triage Jim asked for — flagged "suspicious, rule it out."

## 3. What's actually good in this data

1. **Lot code discipline is strong:** 100% of lots conform to a consistent `YYMMDD####` format;
   TLCs present on every event row; only 1 date-plausibility anomaly in 551 shipments.
2. **GTIN-14 check digits: 32/32 product IDs valid** — GS1-clean product identity.
3. Event rows have full quantity/UoM/reference-document coverage (SO/TR/FLR doc numbers on
   every row).
4. Clear trading-partner graph: 320 of 551 shipments go to 28 external customers
   (JJ McDonnell, C.J. Seafood Express, Plums Inc, ...); 215 are internal transfers between
   Sea Eagle locations.

So the story is *not* "crappy data" — it's **good event capture with empty plan/upstream layers,
a broken transformation join, dead contact fields, and a couple of genuine anomalies**. This is
exactly the "you think you're compliant, and your system is half intact" scoping result from the
call, produced from one file in one pass.

## 4. What this proves and what it forces (product implications)

1. **Our current intake cannot ingest this file.** It's the ENSESO4Food template (13 sheets,
   different headers, CTE-per-sheet layout), not our demo workbook. The receiving-records /
   flexible-workbook intake with header mapping is now blocking real-world use — this is the
   top build item.
2. **Every §2 finding came from checks the engine doesn't have yet:** lot-lineage orphan
   detection, multi-product TLC reuse, mass balance (accuracy-roadmap WS6.1), lot-format +
   embedded-date plausibility (WS6.2), GTIN validation, FTL reclassification of the product
   master (WS1). The one-off script is the spec for those rulepacks.
3. **Export-window awareness matters:** orphan-lot findings must distinguish "lineage broken"
   from "origin predates the export window" (lot-embedded dates make that inference possible).
   A naive checker would cry fraud on §2.1; a good one asks for the 2024 records.
4. **Even ENSESO4Food's hard-halt entry validation leaves these gaps** — reinforcing the
   complementarity story from the call rather than competition: they enforce field presence at
   entry; none of §1.3–§1.7 or §2 is a field-presence problem.

## 5. Next actions

1. **Ramesh reviews, then send Jim & John a cleaned-up version of §1–§3** (this is the proof
   point they asked for; lead with §2.2, §2.6 and the empty-plan findings).
   Open questions to include: is the 2024-origin explanation for §2.1 correct? Is the
   multi-product-lot pattern (§2.2) a Trakkey behavior or operator practice? Are the two
   "General products" SKUs actually shrimp (§2.6)?
2. **Build the flexible intake** (ENSESO4Food-template mapping first, since Jim can supply more
   of these) and port the §2 checks from the one-off script into cited rulepacks.
3. **Add this workbook (redacted) to the WS5 gold set** once findings are confirmed by
   Jim/John — it's the first real labeled example.
