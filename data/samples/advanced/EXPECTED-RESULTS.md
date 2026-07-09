# Advanced adversarial test fixture — answer key

Fictional operator **Bluegrass Provisions LLC** (produce + dairy + seafood + ready-to-eat
processor). The template shares nothing with the demo workbook or the Sea Eagle export:
different sheet names/headers, DD/MM/YYYY text dates, merged banner rows, ERP junk rows,
one GTIN with a broken check digit, and ~18 planted defects plus false-positive traps the
engine must NOT flag. Regenerate with `python backend/scripts/demo/make_advanced_fixture.py`.

## How to test (Postman, against local uvicorn)

1. **Full audit + door-vs-DB diff** — `POST /internal/audit/run`
   - Header `x-bellwether-internal-token: <your token>`
   - Body form-data: `file` = `bluegrass-provisions-export.xlsx`,
     `inbound_file` = `advanced-asn-856.edi`
2. **Pre-receipt ASN** — `POST /internal/inbound/validate` with the EDI (base64 JSON body)
3. **Pre-receipt BOL** — `POST /internal/inbound/validate` with `advanced-bol.pdf`

All LLM perception (sheet mapping, FTL tiers, narrative) is pre-warmed in
`data/llm-cache/` — expect `llm_cached` everywhere; a live key also works.

## Expected audit response (verified in-engine 2026-07-08)

**Top level:** `readiness: "blocked"` · 48 events · 41 findings (8 high / 33 medium) ·
export window 2025-02-05 → 2025-06-15 (DD/MM dates parsed day-first — if the window reads
May→Dec 2025, locale parsing regressed).

**Events by CTE (exact):** shipping 19, receiving 6, harvesting 6, initial_packing 6,
transformation 5, cooling 3, first_land_based_receiving 3.

**Sheet kinds (all 12 must resolve):** Company Register→master_business, Facility
Register→master_locations, Item Catalog→master_products, Harvest Log→cte_harvesting,
Cooling Register→cte_cooling, Pack Out→cte_initial_packing, Dock
Landings→cte_first_land_based_receiving, Goods In→cte_receiving, Batch
Inputs→cte_transformation_input, Production Batches→cte_transformation_output, Dispatch
Log→cte_shipping, Trace Plan→traceability_plan.

### Findings checklist (by type → count)

| # | finding_type | count | what it is |
|---|---|---|---|
| W1 | kde_completeness (harvest) | 1 systemic | "Systemic gap across 4 harvest records" — missing field/growing area (H-03..H-06) |
| W2 | kde_completeness (packing) | 1 systemic | "Systemic gap across 6 initial packing records" — missing received quantity (no such column) |
| W3 | kde_completeness (FLR) | 1 individual | Dock landing LD-03 missing harvest range and locations |
| W4 | kde_completeness (receiving) | 1 systemic | "Systemic gap across 4 receiving records" — missing Doc No (R-101..R-104), 2 fields (ref doc number + TLC source) |
| W13 | tlc_lineage | 2 individual | Production rows B-0522-A / B-0529-A missing the source (input) lot |
| W14 | traceability_plan | 1 | exactly **2** missing components: point of contact (row present, answer blank) + plan update/retention (row absent). Record-maintenance, FTL-identification, TLC-assignment, farm-map must read **present** |
| W5 | lot_self_receive | 1 | lot 2504010030, LOC-01 → LOC-01 (best_practice, needs_review) |
| W6 | lot_mass_balance | 1 | lot DL2503050071 shipped 55 case vs 40 received (best_practice). **Only this lot** — see trap T2 |
| W7 | lot_date_ordering | 2 | lot BP2504100033: embeds 2025-04-10 but shipped 2025-04-08 (two angles: vs origin record, vs embedded date). Proves DD/MM parsing |
| W8 | lot_duplicate_tlc | 1 high | lot 2505200160 on 2 products (tomatoes + romaine) with no transformation |
| W9 | lot_duplicate_tlc | 1 medium | lot BP2503150041 on 2 SKUs from the **same batch** — "permitted, but…" wording, NOT the high variant |
| W10 | lot_backward_lineage | 1 needs_review | lot 2411250099 pre-window (embeds 2024-11-25) — "request prior records", not broken chain |
| W11 | lot_backward_lineage | 2 gap/high | lots 2505120150 and 2506010161 — in-window, truly no origin (drives readiness=blocked) |
| W12 | lot_forward_linkage | 1 | 2 unmoved lots: 2502140012 (packed 14/02, never moved) + LK2503200023 (landed 20/03, never shipped) |
| W15 | gs1_identifier + gs1_requirement | 1 + 3 | wrap GTIN 10860004520113 fails check digit; Walmart/Kroger/Albertsons overlay findings carry requirement_source=customer_requirement |
| W16 | ftl_declared_mismatch | 4 | declared "General grocery" but on/possibly-on FTL: smoked salmon (definite_on), mahi-mahi (definite_on), salad kit (suspicious), wrap (suspicious) |
| W19 | scope_or_exemption_uncertainty | 8 | wrap events ×4, mahi landings ×3, "Asst. Deli Cups 12ct" ×1 (not in catalog) |
| — | evidence_conflicts | 1 | rollup: conflicting values ("From Partner" vs "From Site" on the same slug) |
| — | partner_data_quality | 2 | Metro Grocers + Sunbelt band D (see scorecard) |
| — | inbound_erp_mismatch | 5 | see EDI section |

### FTL tiers (12 catalog items + 2 external ingredients + 1 uncataloged)

- definite_on (5): Romaine Hearts, Peanut Butter, Vine Tomatoes, **Cold Smoked Salmon**
  (mismatch), **Mahi-Mahi IQF Frozen** (mismatch — frozen must NOT clear seafood, trap T5)
- suspicious (6): Salad Kit (composite, mismatch), Wrap (mismatch), **Cottage Cheese Grade A**
  (W18: cottage guard — never definite_on without the IMS check), Caesar Dressing ×2, Deli Cups
- definite_off (3): **Frozen Brie** (W17: frozen-cheese guard overrides the declared
  soft-cheese category), Dried Oregano (herbs must be fresh), Canned Tuna (shelf-stable)

### Partner scorecard

- Metro Grocers Inc — **D** (fill 100%; D because it received integrity-gap lots)
- Sunbelt Restaurants Group — **D** (same driver)
- Dairyland Creamery — **B** (missing reference_record_no ×2)
- NutWorks Ingredients — **B**, GreenAcre Farms — **B** (missing doc no ×1 each)
- Bluegrass Provisions LLC — A (the self-receive counterparty; operator inference by
  location-owner doesn't resolve name-keyed actors — known nuance, internalTransferEvents=0)

### KDE coverage

~95.3% — 429 present / 21 missing / 450 graded (48 not_applicable).

### False-positive traps — these must NOT appear

- **T1**: NO `lot_transformation_linkage` finding (outputs carry Primary Input Lot)
- **T2**: NO mass-balance finding for 2502140011 (partially consumed → not reconcilable)
  or BP2503150041 (120+80 produced ≥ 110 shipped)
- **T3**: BP2505220055, BP2505290056, DL2506150090 NOT in the forward-linkage unmoved list
  (originated within 30 days of window end)
- **T4**: zero cooling findings (sheet is fully compliant)
- **T5**: frozen mahi/smoked salmon stay ON the FTL (frozen guard removes only cheeses)
- **T6**: export window starts 2025-02-05 (not mis-parsed as US-locale)

## Expected EDI results

**Pre-receipt (`/internal/inbound/validate`):** `overall: "reject"`,
`verdict_counts: {accept: 3, hold: 1, not_in_scope: 1}` —
- line 4 (peanut butter, **no lot**) holds with "Missing required KDE: Traceability Lot Code"
- line 2 (Frozen Brie) reads **not_in_scope** — the frozen-cheese guard classifies it
  definite_off, so FSMA 204 KDEs aren't demanded of it at the door
- lines 1/3/5 (cottage cheese) accept.

**Door-vs-DB diff (audit run with `inbound_file`): 5 inbound_erp_mismatch findings**
1. DL2503050071 — supplier sends data elements the system dropped (needs_review)
2. DL2503050072 — same dropped-fields pattern (needs_review)
3. DL2503050072 — **quantity conflict: ASN 70 vs system 60 (high, gap)**
4. DL2506150090 — dropped-fields (system has Doc No, ASN adds phone/email/BOL ref)
5. DL2503990099 — lot on the ASN has **no matching record in the system at all**

## Expected BOL results

`overall: "accept"`, 3 lines extracted (lots DL2503050071 / DL2503050072 / DL2503990099),
`verdict_counts: {accept: 2, not_in_scope: 1}` (line 2 Frozen Brie is off-FTL per the
frozen-cheese guard).

## EPCIS

`epcisStats.exportedEvents: 39` of 48 (harvest/cooling rows without lot codes are skipped
by design; `skippedEvents: 9`).

## Engine fixes this fixture drove (2026-07-08)

1. Plan components matched by canonical field + plain-English terms (was: hardcoded demo
   sheet name + template tokens → false "all components missing" on real workbooks).
2. Merged banner rows no longer win header detection.
3. `event_type` derivation no longer suppressed by an event-id column (was: stranded
   whole sheets unclassified).
4. Rows sharing an event id (multi-SKU batches) mint one event per line (was: silent
   row loss + false mass-balance/duplicate signals).
5. Partner links derived from `*_location_name` columns; site names promoted to satisfy
   location KDEs; display form preserved (was: "METROGROCERSINC").
6. Self-receive detected on location names, set-intersection semantics.
7. `declared_negative` matches the "General …" category family (was: only "General products").
8. Contracts v4/v5: cooling_location + harvester_name/phone satisfy their KDEs.

Regression after all fixes: dress rehearsal GO (demo + Sea Eagle unchanged), recall
harness 100% must-find on both golds.
