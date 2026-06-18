# TraceReady Accuracy Roadmap

A living tracker for raising audit accuracy. Update the **Status log** at the bottom whenever a
task moves. Check boxes as work completes. Keep task IDs stable so we can reference them.

Last updated: 2026-06-17

---

## North-star principle: separate Perception from Judgment

- **Judgment (the pass/fail verdict) stays deterministic and cited — never an LLM.**
  An auditor/FDA needs "missing TLC, per 21 CFR 1.1345", not a model's opinion. A hallucinated
  "you're compliant" is the catastrophic error. The rule-execution engine
  (`backend/traceready_backend/audit_engine/rule_execution.py`) keeps deciding compliance.
- **Perception (extraction, matching, classification) is where ML/LLM belongs.** This is the
  "hard to differentiate produce" layer that is currently hardcoded heuristics and causes the
  review noise.
- **A missed gap (false pass / false negative) is the worst error.** Optimize for **recall**;
  stay conservative on genuine uncertainty (route to human review). Confirmed-clear cases must
  NOT be routed to review.

## Architecture decisions (recorded)

- **FTL matching stack (AD-1):** LLM classifier verified against the approved FTL cards →
  cache every confirmed match (deterministic, reproducible lookup) → add embeddings later as a
  near-duplicate/retrieval optimization. No vector DB at current scale (~80 FTL items;
  in-memory cosine, vectors precomputed offline).
- **Embeddings model (AD-2, when needed):** API-based (OpenAI `text-embedding-3-small`; key
  already in `app/.env.example`) to avoid shipping torch into the Vercel serverless function.
  FTL commodity vectors precomputed offline and stored; runtime only embeds the few customer
  product names per upload. Revisit local models only if we move off serverless.
- **LLM (AD-3):** reuse the existing Anthropic client
  (`audit_engine`/`intelligence/anthropic_client.py`, Sonnet for classification).
- **Reproducibility (AD-4):** once a product→FTL match is confirmed it is cached; the LLM only
  fires for cold/novel products, so repeat workbooks give identical verdicts.

---

## Workstreams

### WS1 — FTL semantic matcher (fixes the cucumber/romaine over-deferral)
Goal: declared-and-listed foods auto-resolve; only genuinely-unknown scope goes to review.
- [ ] 1.1 LLM product→FTL classifier: input customer product (name, category, declared `is_ftl`,
      form/temperature) + the approved FTL cards; output `{on_ftl: yes|no|unknown, commodity,
      form, confidence, citation, reasoning}`.
- [ ] 1.2 Deterministic verification: the returned commodity MUST exist in the approved FTL
      cards; reject/hallucination-guard otherwise. Record match + confidence + source for audit.
- [ ] 1.3 Credit the customer's declared `is_ftl=yes` + a strong match toward scope confidence
      so it no longer trips the classifier's low-confidence "resolve food/form scope" prompt.
- [ ] 1.4 Cache confirmed matches in Supabase (product signature → FTL commodity) for
      deterministic reuse; LLM only on cache miss.
- [ ] 1.5 Route to human review ONLY when `on_ftl=unknown` / no verified match / form-sensitive.
- **Acceptance:** on `outputs/demo-customer-upload/...xlsx`, cucumber (EV-REC-0006, EV-SHP-0007)
  and salad-mix scope reviews disappear; `PRD-3001` (is_ftl=unknown) still routes to review;
  the 2 Cilantro TLC must-fixes and the plan finding are unchanged.

### WS2 — CTE / event-type normalization
Goal: messy event vocabulary stops dragging classifier confidence down.
- [ ] 2.1 Treat `receive`↔`receiving`, `ship`↔`shipping` (and other aliases) as full synonyms,
      defined as reviewable data (approved card), not code literals.
- [ ] 2.2 LLM fallback to map genuinely-novel event vocabulary → canonical CTE.
- **Acceptance:** the synonym events (EV-REC-0006, EV-SHP-0007) score the same as canonical
  ones and no longer dip below the review threshold purely due to the synonym.

### WS3 — De-hardcode remaining config into approved cards
Goal: no rule-data literals in code; everything reviewable. (KDE/exemption/plan already done.)
- [ ] 3.1 Classifier confidence thresholds, synonym lists, food-form rules → approved cards with
      bundled fallback (mirror the `bundled_rules/` + Supabase pattern).
- **Acceptance:** changing a threshold/synonym/form rule needs no code edit; loaded from cards.

### WS4 — Reviewer-feedback flywheel
Goal: every human decision makes the next audit smarter instead of being thrown away.
- [ ] 4.1 Persist each reviewer decision (this product IS/ISN'T FTL; this transfer IS/ISN'T
      reportable) as a labeled example.
- [ ] 4.2 Feed confirmed labels into WS1.4 cache + as few-shot context for the LLM matcher;
      use disagreements to tune thresholds.
- **Acceptance:** a product a reviewer confirmed once auto-resolves (no review) next time.

### WS5 — Ground-truth measurement (replace the circular evals)
Goal: be able to *state* accuracy honestly, not self-referentially.
- [ ] 5.1 Build a gold set: 30–50 realistic workbooks with findings labeled by an FSMA expert
      (cover clean, missing-TLC, broken-lineage, exemptions, form-change, non-FTL, unknown).
- [ ] 5.2 Precision/**recall** harness (recall-weighted; a missed gap is the dangerous error);
      wire as a regression gate.
- [ ] 5.3 Periodic job that re-validates the bundled FTL + rule text against the live FDA pages
      (Food Traceability List + Subpart S final rule). Manual baseline done 2026-06-17 below.
- **Acceptance:** published precision/recall on the gold set; CI fails on a recall regression.

### WS6 — Deeper value-correctness checks (later; new cited rules)
Goal: catch error classes the current engine structurally can't (still deterministic + cited).
- [ ] 6.1 Mass balance: shipped quantity ≤ received/produced for a lot.
- [ ] 6.2 TLC format validity + date plausibility (e.g., ship date ≥ receive date).
- [ ] 6.3 §1.1340(b) pass-forward: info provided to the immediate subsequent recipient.
- **Acceptance:** each is a deterministic rule with a citation and a gold-set case.

---

## Sequencing

- **Phase A (now — kill the review noise + start measuring):** WS1.1–1.5, WS2; start WS5.1 in
  parallel.
- **Phase B (compound accuracy):** WS3, WS4, finish WS5.
- **Phase C (depth):** WS6.

---

## Ground-truth validation log (WS5.3)

- **2026-06-17** — Manually verified against the live FDA Food Traceability List that
  cucumbers (all fresh), leafy greens (incl. Romaine), fresh herbs (incl. cilantro), and
  fresh-cut leafy greens are on the FTL. Confirms the demo workbook's verdicts are correct
  against real-world ground truth and that the cucumber scope-review is redundant.
  Sources: <https://www.fda.gov/food/food-safety-modernization-act-fsma/food-traceability-list>,
  <https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-final-rule-requirements-additional-traceability-records-certain-foods>

## Status log

- **2026-06-17** — Roadmap created. Architecture decisions AD-1..AD-4 recorded. No workstream
  tasks started yet (plan-first). Next: confirm Phase A scope, then begin WS1.1.
