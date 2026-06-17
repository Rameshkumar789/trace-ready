# AI Agents And Rules Design

## Core Principle

AI should accelerate evidence review. Rules should make compliance checks repeatable. Humans should approve sensitive findings.

Do not let an LLM be the final compliance authority.

FSMA 204 interpretation must be handled as a governed workflow:

1. authoritative source is captured,
2. rule card is drafted,
3. expert/founder reviews interpretation,
4. scenario cases test the interpretation,
5. deterministic checks run against customer evidence,
6. human approves final finding.

AI can assist each step, but cannot skip the chain.

## System Modes

### Audit Mode

Purpose:

- diagnose FSMA 204 readiness,
- produce red/yellow/green report,
- create remediation checklist.

### Operations Mode

Purpose:

- track recurring gaps,
- follow up with suppliers,
- manage exception backlog,
- prepare clean export data.

## Agent List

### 0. Regulatory Source Librarian

Job:

- ingest FDA/eCFR/Federal Register source references,
- summarize source purpose,
- identify affected sections,
- detect whether the source is final rule, proposed rule, guidance, discussion paper, FAQ, or internal interpretation,
- link source text to candidate rule cards.

Outputs:

- source record,
- affected CFR/FDA section list,
- proposed rule-card candidates,
- source status,
- effective/compliance dates,
- uncertainty notes.

Guardrail:

- source summaries are not rules until reviewed and converted into approved rule cards.

### 0a. Regulatory Interpretation Agent

Job:

- convert source material into draft rule cards,
- identify applicability questions,
- identify required evidence,
- identify "cannot determine without expert review" conditions,
- map rule cards to Jim's three audit modules: product scope, lot-code integrity, data-sharing readiness.

Outputs:

- draft rule card,
- cited source links,
- plain-English interpretation,
- applicability boundaries,
- scenario test suggestions.

Guardrail:

- every draft rule card must be reviewed before use in customer-facing findings.

### 0b. Scenario Builder Agent

Job:

- create scenario fixtures from real discovery, Jim's examples, FDA discussion papers, and customer pilots,
- represent messy operational cases such as mixed pallets, inferred TLCs, unlabeled cases, returns, transformations, and intracompany shipments.

Outputs:

- scenario name,
- assumptions,
- customer role,
- products,
- CTEs,
- required KDEs,
- evidence set,
- expected findings,
- expert-review flags.

Guardrail:

- scenario expected outcomes must be reviewed by a human before becoming regression tests.

### 1. Intake Agent

Job:

- identify document type,
- summarize file contents,
- detect likely source system,
- flag unreadable or irrelevant files.

Inputs:

- PDFs,
- spreadsheets,
- images,
- text notes,
- CSV exports.

Outputs:

- document type,
- confidence,
- extracted text,
- processing route.

### 2. Product Coverage Agent

Job:

- classify products against Food Traceability List categories.

Outputs:

- likely covered,
- maybe covered,
- likely not covered,
- needs human review,
- explanation.

Guardrail:

- uncertain classifications must go to human review.

### 3. Supplier Obligation Agent

Job:

- map products to suppliers,
- identify which suppliers likely need to send KDEs,
- build supplier obligation table.

Outputs:

- supplier-product map,
- required KDE expectations,
- supplier readiness status.

### 4. KDE Completeness Agent

Job:

- compare records against required fields for event type.

Outputs:

- complete,
- missing,
- conflicting,
- not applicable,
- unknown.

### 5. Lot-Code Lineage Agent

Job:

- check whether incoming traceability lot codes are preserved,
- detect overwritten lots,
- detect missing source/output links.

Key rule:

If no transformation occurred, do not create a new traceability lot code for an FTL food that already has one.

Outputs:

- preserved,
- overwritten,
- transformation-linked,
- missing link,
- cannot determine.

### 6. Transformation Linkage Agent

Job:

- detect whether input lots connect to output lots during transformation.

Works for:

- packers,
- processors,
- repackers,
- food hubs,
- commissary kitchens,
- fresh-cut produce.

### 7. Data-Sharing Readiness Agent

Job:

- assess whether customer can generate required downstream/FDA/customer records.

Checks:

- FDA-style sortable spreadsheet,
- customer template readiness,
- EDI/ASN readiness,
- traceability plan evidence.

### 8. Gap Scoring Agent

Job:

- turn findings into red/yellow/green score.

Score categories:

- product coverage,
- supplier readiness,
- receiving KDE completeness,
- lot-code integrity,
- transformation linkage,
- shipping/customer sharing,
- system readiness,
- physical label/scanning readiness.

### 9. Remediation Agent

Job:

- convert findings into specific next steps.

Examples:

- request harvest KDEs from Supplier A,
- stop overwriting source lot codes,
- add receiving template fields,
- add transformation linkage record,
- create customer export.

### 10. Supplier Follow-Up Agent

Job:

- draft supplier emails,
- explain missing fields,
- attach evidence,
- propose next-step requirements.

Human approval required before sending.

### 11. Audit Planner Agent

Job:

- decide which audit checks apply to a customer before rules run,
- explain why each check applies, does not apply, is blocked, or needs expert review.

Inputs:

- customer role,
- products,
- suppliers,
- transformations,
- documents,
- systems,
- physical workflow notes,
- approved rule cards,
- scenario library.

Outputs:

- audit plan,
- applicable CTE list,
- required KDE checklist,
- missing evidence checklist,
- blocked checks,
- expert-review queue.

Guardrail:

- planner output is advisory until accepted by the internal operator.

### 12. Evidence Mapper Agent

Job:

- map extracted document fields to required evidence for each rule card.

Outputs:

- evidence matrix,
- source document/page/row,
- field confidence,
- conflict notes,
- absent-data versus unreadable-data distinction.

Guardrail:

- missing evidence must not be inferred from similar records.

## Rules Versus AI

Rules should handle:

- source-approved rule-card execution,
- required field checks,
- date normalization,
- quantity/unit normalization,
- event type logic,
- lot code comparisons,
- transformation link checks,
- score thresholds,
- scenario regression tests.

AI should handle:

- source summarization for internal review,
- draft rule-card creation,
- scenario drafting,
- messy document understanding,
- product description interpretation,
- supplier/item matching,
- natural-language explanations,
- remediation wording,
- email drafting.

Human should handle:

- rule-card approval,
- scenario expected-outcome approval,
- final audit approval,
- borderline product coverage,
- legal/compliance-sensitive interpretation,
- exemptions and partial exemptions,
- FDA discussion-paper/flexibility interpretation,
- supplier disputes,
- high-risk findings.

## Finding Severity

Red:

- likely non-readiness for critical workflow,
- missing lot-code lineage,
- transformation link absent,
- no way to share required data,
- supplier missing repeated required KDEs.

Yellow:

- partial data,
- uncertain product coverage,
- manual workaround exists,
- low confidence extraction.

Green:

- evidence present,
- field complete,
- workflow appears ready.

Gray:

- not enough evidence.

## Evidence Requirement

Every finding should include:

- source document,
- source row/page if available,
- extracted field,
- confidence,
- rule triggered,
- regulatory source citation,
- rule-card version,
- audit-plan check ID,
- human reviewer status.

## Interpretation Statuses

Every rule-card-backed finding must carry one of these interpretation statuses:

- `approved_rule`: based on reviewed rule card and enough evidence,
- `needs_expert_review`: source/evidence is sensitive or ambiguous,
- `customer_evidence_missing`: required evidence was not provided,
- `cannot_determine`: evidence exists but does not support a reliable conclusion,
- `discussion_flexibility`: based on FDA discussion paper or non-final flexibility, not final compliance rule,
- `out_of_scope`: not applicable to this audit based on reviewed assumptions.

Customer-facing reports must make these statuses visible in plain English.

## Do Not Automate First

Do not automate:

- compliance certification,
- legal interpretation,
- final pass/fail claims,
- supplier enforcement,
- sending external emails without approval,
- use of unreviewed rule cards in customer-facing reports,
- definitive conclusions from FDA discussion papers or proposed rules.
