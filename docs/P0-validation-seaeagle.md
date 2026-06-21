# P0 — Real-dataset validation (issue #2)

**Dataset:** Sea Eagle Market (Craig Reaves, Beaufort SC) — a real Trakkey export,
~Jan–Oct 2025, 13 sheets (Business/Location/Product Master, LOT Assignment, Harvesting/
Cooling/Packing/First-Land-Based-Receiving/Shipping/Receiving/Transformation KDEs,
Traceability plan). Seafood operation (shrimp). `LOT Source = "Trakkey CS"`.

**How run:** `python3 scripts/ops/run_scope_validation.py --input <file>` (full Phase-11 engine).

## Result (after schema adaptation)
- **63** supplier×product coverage cells, **921** findings, **41** data-quality anomalies, **3** supplier scorecards.
- **FTL scope resolves correctly:** every shrimp SKU classifies **`on`** the Food Traceability List (FTL Group = Crustaceans), once we mapped the export's columns.

## The differentiated finding (the headline)
The engine flagged **41 cases of one lot code appearing across multiple distinct product SKUs**
— e.g. lot `2503040120` on 4 products; `2503030119`, `2503100123`, `2503140126` on 3 each.
This is **exactly the "same lot code on everything" pattern Jim raised — surfaced in his own
real data.** A file-cleaning/error-correction tool (e.g. ReposiTrak Touchless) would not raise
this; it's a *plausibility/verification* signal, which is our wedge.

**Honest interpretation:** in seafood this may be **legitimate** — one shrimp landing/lot is
size-graded into many SKUs, so they share a lot. That's why we surface it as **`needs_review`,
not fraud** (matching the research caveat that "same lot = fraud" is unproven). The real value:
it tells an auditor exactly where lot granularity is coarse and worth confirming.

## What this validation exposed (the over/under-flag documentation)
1. **Schema mismatch was the biggest gap** — Jim's Trakkey export uses different sheet/column
   names than our assumed workbook. Before adapting, everything was "unknown_supplier /
   investigate" with product IDs instead of names. **Fixed:** added Trakkey column aliases
   (`Product title`, `FTL Group`, `LOT Number`/`Assigned`, `Source Location ID`, the date
   columns) → product names, FTL tiers, and per-location suppliers now resolve.
2. **Under-flagging on transformation lineage (still open):** the `Transformation KDEs
   Ingredients` sheet (input lots) and `Transformation KDEs Produced` sheet (output lots) both
   use a generic `LOT Number` column, so the engine can't yet link input→output lots across the
   two sheets. Result: **P2 TLC retain/reassign + UoM = 0 issues** on this file (under-fires).
   Fix needed: **sheet-aware mapping** (ingredients `LOT Number` → source lot; produced
   `LOT Number` → output lot). This is the top follow-up.
3. **Fire-drill one-up gaps:** some lots show "no one-up source" — partly real (shipping-only
   rows) and partly the transformation-linkage gap above.

## Decision
**Proceed.** The engine produced a real, differentiated signal on real data (lot-granularity
reuse) that an incumbent file-cleaner would not, and the FTL/scope/scorecard outputs are
correct once the export schema is understood. **Next build:** sheet-aware transformation
lineage so P2 (integrity/mass-balance) fires on Trakkey-shaped exports.
