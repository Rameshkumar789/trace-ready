# Jim White / John Demo Call — Insights And Action Items

- **Call date:** approx. 2026-07-02/03 (just before the July 4 weekend)
- **Archived:** 2026-07-07
- **Participants:** Ramesh (TraceReady), co-founder (cloud infra/SRE, Paramount), Jim White (ENSESO4Food), John
- **Raw transcript:** [`../../chat-history/2026-07-03-jim-john-demo-feedback-call-transcript.txt`](../../chat-history/2026-07-03-jim-john-demo-feedback-call-transcript.txt)
- **Verdict from Jim:** "You're fishing in the right pond." The digital audit is the product. But re-aim the engine: from validating the customer's own aggregated spreadsheet to auditing what their **trading partners** send them.

---

## 1. What we demoed

The current TraceReady Audit flow: a multi-sheet Excel workbook (business profile,
product master, locations, partner master, traceability plan, CTE events, event line
items, KDEs, TLCs, source documents, exemption claims) uploaded through the operator
dashboard, run through the rules engine, producing flagged gaps ("2 must-fix gaps, 5
items to review") with plain-language explanations **plus FSMA 204 rule citations** and
exact sheet/row provenance. Seeded intentional gaps (missing TLC, missing exemption,
missing evidence ID) fired correctly, and the non-FTL item (cracker) was correctly not
flagged while FTL produce was.

What landed well:
- Citation-backed findings (user-friendly message + cited FSMA rule + how to fix).
- FTL-aware scoping (cracker ignored, veggies flagged) — Jim engaged deeply on this.
- Sheet/row-level provenance for every finding.

What got challenged:
- "Where did this spreadsheet come from?" We aggregate it from the customer's ERPs/WMS.
  Jim's core critique: **that focus points at a system that may already be intact.**

## 2. The strategic redirect (most important takeaway)

> "What you have, I would point towards all the trading partners."

The customer's own records being clean is not the scarce insight. The scarce insight is:
**"I have 100 suppliers — which of them are not sending me the data I need, and for
which products?"** That is the gap analysis buyers need *now*, because supplier
remediation takes months-to-years — which is exactly why the July 2028 deadline means
starting today (a distributor doesn't create TLCs; he has to push the requirement back
to the shipper, who may have to push it back to 20 companies behind one pallet).

Two concrete product motions fall out of this:

1. **Inbound supplier gap analysis (retro):** take 30–90 days of receiving records and
   report which suppliers / which products / which KDE fields are missing or bad.
   Output: "Here's the list of people who don't give me the information I need, and the
   products I don't get the information I need for."
2. **Pre-receipt validation (future):** supplier sends what they *intend* to ship (EDI/
   ASN/BOL); the engine says "this won't go through my system, here's exactly what's
   missing" — **before** the truck arrives. John: "You're shipping me stuff I'm not
   going to be able to put through my system, and we want to know about that before it
   happens."

Also flippable: the same audit in a **supplier's** hands ("send me what you're going to
send me and we'll tell you whether it's acceptable") — same engine, both sides of the
dock.

## 3. The digital audit = a scoping/sizing product

Jim's framing of the customer value: **"You have just scoped my FSMA 204 project."**

- Some companies think they have a gigantic problem and don't; others think they have
  none and have a gigantic one. Nobody knows until someone measures.
- Positioning: a fast, inexpensive **precursor to a full SGS-style on-site audit**.
- The magnitude report: how many foods on the FTL come into my system (10 or 10,000?),
  from how many suppliers (10 or 10,000? — i.e., how many people do I have to train/
  chase?), and which internal processes touch FTL data.
- Sizing changes the whole remediation strategy: a convenience-store chain with 150
  FTL SKUs out of 10,000 hires one person and manages it off-shelf; a food processor
  has to build traceability into every process. Same rule, completely different
  projects — the audit tells them which one they are.
- Jim explicitly said "descope it, start really small": *"give me samples of your
  receiving records for 30–90 days and we will give you a report of which products and
  which suppliers you should be paying attention to. I think you could sell that."*

## 4. FTL classification: interpretation, not lookup

Corrects an assumption in our pitch: the FTL is **not** going to churn ("probably won't
change it for five years"). The hard problem is **interpretation of product
descriptions**:

- Easy: "tomato" → on the list. "Box of cereal", "can of soup" → not.
- Hard: "ham sandwich" — not on the FTL until someone puts sliced tomato or lettuce on
  it, and the description may not tell you.

Jim's asked-for output is a **three-tier classification** of the product list:

| Tier | Meaning | Action |
|---|---|---|
| Definitely on FTL | Description conclusively matches an FTL category | In scope, full KDE/CTE checks |
| Suspicious / potentially on FTL | Can't be ruled in or out from the description (composite foods, vague names) | Route to human investigation; must be ruled out explicitly |
| Definitely not on FTL | Conclusively out (cereal, paper towels, canned soup) | Out of scope, don't worry |

This maps directly onto the accuracy roadmap's north star (recall-first, route genuine
uncertainty to review, never LLM-decide the verdict) and the AD-1 FTL matching stack in
`docs/accuracy-roadmap.md`. The "suspicious" tier is the product feature name for what
that architecture already produces.

## 5. Data quality and fraud signals nobody checks today

Presence checks are table stakes (ENSESO4Food already hard-blocks entry on missing lot
codes). The differentiating checks Jim called out:

- **Duplicate / static lot codes:** "I see the same lot code for every product. Nothing's
  ever different. Nobody's checking for that right now." Could be laziness, duplication,
  or actual counterfeit/fraud — all detectable statistically.
- **Unreadable lot codes:** present but unusable.
- **Field-level quality scoring:** consistency of formats within a field, not just
  presence ("half of it is shit data, which they don't even know yet").
- **Cross-system conflicts:** two versions of the same record in different systems —
  which is authoritative, do they disagree? (Raised at the very top of the call.)
- **Made-up data risk:** entities missing upstream data "guess and stick it in fields" —
  audits will surface confidently-wrong data, not just missing data.

## 6. Retailer overlays: the rule isn't only the FDA's

Big buyers have issued their own FSMA 204 instructions to supply partners that go
**beyond** the regulation — e.g., mandatory **GS1 formats (GTIN for products, GLN for
locations)**. GTIN/GLN check-digit and format validation is mechanically checkable
against any database export.

- Jim shared **Walmart's supplier instructions** (public) on the call; similar documents
  exist from **Kroger** and **Safeway/Albertsons**; likely **Costco**, **Trader Joe's**;
  Jim is still looking for **Publix**.
- New finding class: *"non-compliant with the requirements of one of your customers,
  which happens to be Walmart"* — distinct from FDA non-compliance.
- Team note: co-founder works at Walmart (not on FSMA directly, but knows the supply
  chain folks who are) — a warm channel for validating the overlay rules and possibly
  for discovery conversations.

## 7. Look at what comes through the door, not what's in the ERP

John's cautionary note: a fully compliant supplier may ship **all** the KDEs on the
EDI/ASN, but the customer's ERP only ingests the fields it has columns for and silently
drops the rest. Paper BOLs carry fields that were never digitized.

Implication for the audit method: **parse the raw inbound artifacts (EDI, ASN, BOL —
paper included), not just database exports.** Otherwise we'd blame a compliant supplier
for the customer's own field-mapping gap. This also measures true remediation cost —
"maybe everybody just has to add one field," which is a very different project than
"start over."

## 8. Ongoing wedge: new-supplier onboarding + repeat assessments

- Even a compliant operation with good systems will onboard **new suppliers** who start
  out non-compliant. The traceability plan must document how such a "bogey" is detected
  and treated ("here's how we detected it, here's what we did, here are the results") —
  that is exactly what a human auditor looks for, because auditors know nothing is 100%.
- The compliance-ready assessment is a **corrective-action trigger machine**: find the
  systemic misses (WMS never captures the date, field never mapped), fix, **re-run the
  audit and show the improvement**. Less an ongoing subscription at first, more a
  ramp-up product for "people who think they are already there, and they're not" —
  repeatable per corrective-action cycle.
- Market timing: "people are sitting on their hands right now… waiting around so AI can
  solve this problem." An audit that opens eyes ("oh shit, we have crappy data") gets
  the market moving — which ENSESO4Food explicitly wants, because it drives demand for
  everyone.
- Jim's reframe worth keeping verbatim: **"The problem isn't really a data problem as
  much as it is a supply chain management problem"** — knowing whom to tell "you have to
  give me something."

## 9. ENSESO4Food product intel (partnership relevance)

- Their forms validate field-by-field with mandatory-field kickback and **hard-halt** on
  missing data (e.g., no lot code → can't enter the record at all).
- They acknowledge the halt is a workflow problem and are building a
  placeholder-and-return flow; today there's no way to continue and fix later.
- Complementarity for TraceReady: they enforce at the point of entry going forward; we
  audit the historical/aggregated/inbound data they never see, plus FTL interpretation
  and cross-system checks they don't attempt. No collision on the demoed scope.

## 10. Action items

**Immediate**
1. **Craig's dataset:** Jim emailed a real pilot-customer receiving dataset during the
   call (real, complete data; pilot stopped ~Aug–Sep last year when their computer
   died). Run it through the audit engine, produce a supplier/product gap report, and
   send the results back to Jim and John. This is the single best next proof point and
   directly exercises the Section 2/3 repositioning.
2. **Retailer instruction corpus:** collect the Walmart supplier instructions Jim linked,
   plus Kroger and Safeway/Albertsons equivalents (hunt for Costco, Trader Joe's,
   Publix). Add to `data/regulatory/` sourcing and the regulatory ingestion tracker.
3. **Follow-up with Jim:** touch base to validate the re-scoped direction; possible
   in-person meeting next month (~August) if travel lines up.

**Product/backlog candidates** (to merge into `docs/blueprint/10-engineering-backlog.md`
and `docs/accuracy-roadmap.md` on the next planning pass)
1. **Supplier scorecard report** — per-supplier × per-product × per-KDE completeness and
   quality ("only 20% of your supplier data arrives with all KDEs"). The headline output
   of the descoped MVP Jim said he could sell.
2. **Receiving-records intake mode** — accept 30–90 days of receiving records alone (no
   full multi-sheet workbook required) and emit the scoping report: FTL product count,
   supplier count, products/suppliers to pay attention to.
3. **FTL three-tier classifier surface** — expose definite / suspicious / not-on-FTL as
   the product-list deliverable (engine work already covered by accuracy-roadmap AD-1).
4. **Lot-code anomaly detection** — duplicate/static lot codes across products or time,
   unreadable codes, counterfeit heuristics.
5. **GS1 validation rulepack** — GTIN/GLN format + check-digit validation.
6. **Retailer overlay rulepacks** — findings keyed to a specific customer's requirements
   (Walmart/Kroger/Albertsons), distinct finding class from FDA citations.
7. **Raw inbound-artifact parsing** — EDI/ASN/BOL field inventory vs. what the ERP
   actually ingested ("what comes through the door vs. what goes into their system").
8. **Pre-receipt validation API** (post-MVP) — supplier-submitted ASN/BOL scored before
   shipment; the "don't ship me what I can't accept" product.
