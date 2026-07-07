# Product Accuracy Audit — Findings & Remediation Record (2026-07-07)

Three parallel research passes were run against the just-built backend: (A) an adversarial
regulatory review of every engine check against the actual rule text in
`data/regulatory/ecfr-21-cfr-1-subpart-s/` (post-2023-amendment eCFR), (B) an
execution-grounded engineering stress-test on the demo workbook and the Sea Eagle export,
and (C) external research on FDA's 2026 state of play, standards, competitors, and
technology. This document records what was found, what the rule actually says, and what was
changed. Every item marked **[FIXED]** was remediated and verified the same day (see the
commits of 2026-07-07 on this branch); remaining items carry their disposition.

## A. Regulatory accuracy (engine vs 21 CFR Part 1 Subpart S)

### A1. Under-enforcement — false passes (worst error class)

| Defect | Rule | Disposition |
|---|---|---|
| `tlc_source` graded "conditional" on shipping AND receiving | 1.1340(a)(7), 1.1345(a)(7) make the TLC-source location/reference **required** — it's the KDE that pivots a shipment back to where the lot was created | **[FIXED]** required in `kde-check-contracts.json` v2 |
| Initial packing missing: packing location/TLC source, harvest date, received date/qty, cooling loc/date | 1.1330(a)(14), (a)(8), (a)(2), (a)(3), (a)(9)/(10) | **[FIXED]** added |
| FLR missing the receiver-location TLC source | 1.1335(e) — the seafood chain anchor | **[FIXED]** added |
| Cooling missing the harvest-farm location | 1.1325(b)(1)(vi) | **[FIXED]** added |
| Field/growing-area (produce) / container (aquaculture) name "conditional" | 1.1325(a)(1)(v)/(vi), 1.1330(a)(5)/(6) make it required — the KDE that localizes an outbreak to a field | **[FIXED]** required |
| Harvester business name + phone absent from harvesting | 1.1325(a)(2). NB: the 2023 technical amendment did **not** remove phone requirements — verified against the current eCFR | **[FIXED]** added |
| Sprouts seed KDEs (7 fields) unrepresented | 1.1330(b) | **[FIXED]** added as conditional (credited when present); commodity-conditional *enforcement* is follow-up work |
| Transformation per-input description/quantity collapsed | 1.1350(a)(1)(ii)/(iii) | **[ADDRESSED]** enforced via the systemic `lot_transformation_linkage` check (cited 1.1350) rather than per-event KDEs — a two-sheet export without a join key cannot demonstrate the linkage, and that is reported as one finding, honestly |
| ~14 of the 1.1305(a)–(r) exemptions missing; no numeric thresholds | $25k produce (3-yr avg, 2020 dollars), $250k RFE, <3,000 hens, NSSP shellfish (f), commingled RAC (h), kill-step written agreement (d)(6), farm-to-school (l)... | **[FIXED]** 26 exemption cards with thresholds and conditions |
| Farm-map required of shell-egg-only farms | 1.1315(a)(5) excludes eggs | **[OPEN]** minor; needs commodity awareness in `check_traceability_plan` |

### A2. Over-enforcement — false CFR claims (credibility killers)

The lot-integrity checks are the product's value-add, but four of them asserted CFR duties
that do not exist. FSMA 204 imposes record-content and linkage duties — **no** uniqueness-
per-product, reconciliation, chronology, or format-conformity duties.

| Check | Reality | Disposition |
|---|---|---|
| `duplicate_tlc` cited 1.1320/1.1350 | 1.1310 defines TLC uniqueness per **lot**, not per product | **[FIXED]** `requirement_source="best_practice"`, needs_review, no CFR citation, honest wording |
| `mass_balance` cited 1.1340 | no reconciliation duty exists anywhere in Subpart S | **[FIXED]** best-practice label; also now skipped for lots consumed by transformation (not reconcilable) |
| `date_ordering` cited 1.1340/1.1320 | no chronology duty | **[FIXED]** best-practice label |
| `lot_format` cited 1.1315 | 1.1315(a)(3) requires *describing* TLC assignment, not format conformity | **[FIXED]** best-practice label |
| `backward_lineage` cited 1.1345 alone | origin can equally be 1.1330/1.1335/1.1350; the provide-forward duty is 1.1340(b) | **[FIXED]** composite citation |
| `self_receive` implied a 1.1345 violation | a same-address transfer simply isn't a receiving CTE (1.1310 definition) | **[FIXED]** reworded, best-practice |

### A3. FTL data defects

- FTL file had 20 items vs ~23 real commodity rows; **smoked finfish missing entirely**;
  the three finfish species groups collapsed into one malformed commodity string; no IMS
  Grade "A" cottage-cheese carve-out (exemption effective 2026-02-20); frozen handling left
  entirely to the LLM. **[FIXED]** 23 items, finfish split, smoked finfish added, cottage
  cheese encoded (partial carve-out — source/recipient records still required), plus
  deterministic frozen-cheese and cottage-cheese classifier guards.

### A4. Corpus integrity

- 4 normalized regulatory files were wrong documents or paywall stubs (the "2023 technical
  amendment" file contained sea-lamprey notices; the "2026 public meeting" a USITC hearing;
  the 2025 extension + 2026 cottage-cheese files were "Request Access" stubs).
  **[FIXED]** the two stubs re-normalized from their local raw PDFs;
  `scripts/regulatory/check_corpus_integrity.py` now gates content-token expectations for
  all 10 tracked sources (passes). federalregister.gov and fda.gov bot-block programmatic
  fetch — re-ingestion must go through raw-artifact download.

## B. Engineering / real-data defects (Sea Eagle grounded)

| Defect | Impact | Disposition |
|---|---|---|
| Transformation ingredient rows minted as events | 118 fabricated events (263 vs 145 real), fake KDE gaps, ~1.8x artifact bloat | **[FIXED]** input sheets gated; lots feed lineage via row facts; explicit linkage finding |
| Partner scorecard graded phone/email per event | ALL 29 partners pinned at 78% → manufactured C/D bands | **[FIXED]** graded on genuine per-event KDEs only (partners now honestly band A); contact coverage informational |
| All 64 FLR events counted as "unknown counterparty" | false undocumented-source alarm on the highest-scrutiny seafood CTE | **[FIXED]** landings handled as own-operations; vessel documentation graded by the FLR KDE contract |
| US-hardcoded date order | silent DD/MM corruption for non-US exports | **[FIXED]** per-column locale vote |
| Fallback intake lost non-shipping dates | "universal intake" was cache-dependent offline | **[FIXED]** registry-example aliases + any-date-slug derivation |
| Mass balance ignored consumption | false alarms/misses on transformed lots | **[FIXED]** scoped to non-consumed lots |
| No tenant salt on the mapping cache | cross-customer mapping reuse | **[FIXED]** BELLWETHER_TENANT_ID salt |
| EDI ignored ISA16 component separator | composite LIN elements unparsed | **[FIXED]** |
| Workbook loaded fully twice; O(cells×ranges) merged lookup; unbatched LLM calls; O(events×obligations) mapping; uncapped sync endpoint | ~350s projected at 100k rows; silent wholesale degradation at 10k SKUs | **[FIXED]** single load + ZIP formula sniff, merged-anchor map, 40-product/6-sheet batching, obligation pre-index, 2000-row cap |
| Forward-linkage lacked window-END carve-out | month-boundary noise | **[FIXED]** 30-day carve-out |
| Cache timestamps churned committed files; warning-level degradation logs; dict-order operator ties | reproducibility/observability | **[FIXED]** |
| Hardcoded confidence literals presented as calibrated | reviewer trust | **[OPEN]** cosmetic relabeling pending |

## C. External landscape (full report: research pass C, 2026-07-07)

- **July 20, 2028** is the statutory compliance date (Congress, Continuing Appropriations
  Act 2026). The demand driver is **retailers, enforcing now, beyond the FTL**: Walmart
  (ASN + SSCC-18/GS1-128, eff. 2025-08-01, holds the original timeline), Kroger (856 for
  ALL foods, label must match ASN), Albertsons (GTIN+lot+voice-pick+date per case).
- **Feb 2026 FDA package** encoded into the engine: cottage-cheese partial exemption + the
  Q&A applicability layer (tracked for ingestion).
- **Whitespace confirmed:** incumbents gap-spot only after data enters their platform;
  SGS/DNV sell human gap analyses; AI newcomers let the model judge. Nobody else does
  audit-the-export-as-is + deterministic cited verdicts + partner scorecard + pre-receipt
  bounce + door-vs-database.
- **Technology adopted now:** gold set + recall-first harness (WS5 — live, 100% on both
  golds), reviewer-label flywheel (WS4 — live), Claude multimodal for scanned BOLs (live),
  regulatory watch job (live). **At pilot:** EPCIS 2.0 export (shipped early — already an
  artifact), Splink entity resolution if fuzzy rules thrash. **Deferred:** ML lot-fraud
  scoring (conflicts with cited-verdict positioning), GDST 1.2 unless seafood becomes the
  vertical.

## Verification state (end of day)

- Recall harness: **100% must-find recall** on both gold sets; forbidden-finding guards
  pass; event counts pinned (761 on Sea Eagle).
- Demo workbook golden findings unchanged through every fix.
- Corpus integrity: 10/10 tracked sources pass.
- Remaining before Thursday: regenerate perception caches with the live model
  (`run_dress_rehearsal.py --regenerate-perception`) once ANTHROPIC_API_KEY is available,
  then commit `data/llm-cache/`.
