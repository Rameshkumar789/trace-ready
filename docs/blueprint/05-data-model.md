# Data Model

## MVP Data Model Principle

Model the audit first, not the whole food supply chain.

Also model the regulatory interpretation layer first. A customer finding is only credible if it can be traced back to:

- the source regulation/guidance/discussion material,
- a reviewed rule card,
- a customer evidence object,
- an audit-plan decision,
- a human review state.

The system should answer:

- What did the customer provide?
- What products are in scope?
- Which suppliers are tied to those products?
- Which events/records are missing KDEs?
- Was lot-code lineage preserved?
- What gaps and remediation actions exist?
- Which regulation source and rule-card version created the finding?
- Is the conclusion approved, uncertain, blocked by missing evidence, or based on non-final FDA flexibility?

## Core Entities

### RegulatorySource

Fields:

- id
- title
- source_type: ecfr / fda_page / federal_register / fda_pdf / faq / guidance / discussion_paper / public_meeting / internal_note
- source_status: codified_rule / final_rule / technical_amendment / proposed_rule / draft_guidance / guidance / faq / discussion_paper / public_meeting / internal_interpretation
- authority_rank
- url
- citation
- published_date
- effective_date
- compliance_date
- is_finalized
- supersedes_source_id
- superseded_by_source_id
- retrieved_at
- text_hash
- summary
- notes

Examples:

- 21 CFR Part 1 Subpart S.
- FDA Food Traceability List.
- FDA CTE/KDE page.
- FDA lot-level tracking discussion paper.
- Federal Register compliance-date extension.

Source rules:

- Current eCFR/CFR material should have the highest authority rank.
- Federal Register final rules and technical amendments outrank FDA guidance and explanatory pages.
- Proposed rules, including a proposed compliance-date extension, are not final and must have `is_finalized = false`.
- Discussion papers and public-meeting materials can create risk notes or scenario ideas, but not final compliance findings.

### RuleCard

Fields:

- id
- rule_code
- title
- regulatory_source_id
- source_section
- source_status
- authority_rank
- is_finalized_source
- effective_date
- compliance_date
- plain_english_interpretation
- applies_to
- does_not_apply_to
- evidence_required
- customer_question
- system_check
- possible_outcomes
- severity_mapping
- confidence
- requires_expert_review
- allowed_finding_states: approved_rule / needs_expert_review / customer_evidence_missing / cannot_determine / not_determined / proposed_change / discussion_flexibility / out_of_scope
- version
- status: draft / in_review / approved / deprecated
- reviewed_by
- reviewed_at
- change_notes

Rule cards must be approved before being used in customer-facing findings. Rule cards based only on proposed rules or discussion papers cannot produce `approved_rule` findings.

### RuleCardSourceQuote

Fields:

- id
- rule_card_id
- regulatory_source_id
- source_location
- short_quote
- paraphrase
- relevance_note

Purpose:

- preserve traceability from product logic back to authoritative source.

### ScenarioCase

Fields:

- id
- name
- customer_role
- scenario_group
- assumptions
- products
- suppliers
- events
- evidence_fixture
- expected_findings
- ambiguity_notes
- requires_expert_review
- status: draft / approved / deprecated

Scenario groups:

- business_scope
- product_scope
- harvesting
- cooling_before_initial_packing
- initial_packing
- first_land_based_receiving
- shipping
- receiving
- transformation
- tlc_preservation
- supplier_missing_kdes
- mixed_pallet
- inferred_tlc
- eaches_broken_cases
- returns_reclamation
- food_waste_recovery
- intracompany_shipment
- retail_transformation_shipping
- data_sharing
- traceability_plan
- twenty_four_hour_response
- evidence_quality
- unlabeled_cases
- overwritten_tlc
- uncertain_ftl_scope

### AuditPlan

Fields:

- id
- audit_project_id
- customer_role
- product_scope_status
- applicable_ctes
- required_kdes
- evidence_required
- checks_to_run
- checks_blocked
- expert_review_items
- planner_notes
- approved_by
- approved_at

### AuditPlanCheck

Fields:

- id
- audit_plan_id
- rule_card_id
- check_code
- applies_status: applies / does_not_apply / blocked_missing_evidence / needs_expert_review / cannot_determine
- reason
- evidence_required
- evidence_available
- reviewer_status

### EvidenceItem

Fields:

- id
- audit_project_id
- document_id
- evidence_type
- source_location
- extracted_value
- normalized_value
- confidence
- extraction_method: manual / spreadsheet_parser / ocr / llm / api_import
- reviewer_status
- notes

Evidence types:

- product_identity
- supplier_identity
- location_identity
- cte_event
- kde_field
- traceability_lot_code
- internal_lot_code
- transformation_input
- transformation_output
- customer_export
- traceability_plan
- label_or_barcode

### EvidenceMapping

Fields:

- id
- audit_plan_check_id
- evidence_item_id
- mapping_status: supports / contradicts / incomplete / unreadable / absent / irrelevant
- explanation
- reviewer_status

### Customer

Fields:

- id
- name
- segment
- headquarters_location
- notes
- created_at

### Site

Fields:

- id
- customer_id
- name
- address
- role: distributor / packer / repacker / food_hub / processor / commissary / other
- source_systems

### AuditProject

Fields:

- id
- customer_id
- site_id
- title
- status
- start_date
- delivered_date
- scope_notes
- reviewer
- overall_score

Statuses:

- draft
- files_uploaded
- extracting
- review_needed
- rules_ready
- report_drafted
- approved
- delivered

### Document

Fields:

- id
- audit_project_id
- file_name
- file_type
- document_type
- source_system
- uploaded_at
- text_extracted
- confidence
- notes

Document types:

- item_master
- supplier_list
- location_list
- receiving_record
- shipping_record
- transformation_record
- invoice
- bill_of_lading
- ASN
- label_photo
- packing_slip
- unknown

### Product

Fields:

- id
- audit_project_id
- internal_product_code
- supplier_product_code
- name
- description
- commodity
- variety
- pack_size
- unit
- gtin
- ftl_status
- ftl_confidence
- ftl_reason
- human_review_status

FTL statuses:

- likely_covered
- maybe_covered
- likely_not_covered
- needs_review

### Supplier

Fields:

- id
- audit_project_id
- name
- contact_name
- contact_email
- location_name
- address
- products_supplied
- readiness_score
- notes

### Location

Fields:

- id
- audit_project_id
- name
- address
- gln
- type: source / ship_from / receive_to / customer / field / facility / warehouse
- notes

### TraceabilityEvent

Fields:

- id
- audit_project_id
- event_type
- event_date
- source_system
- source_export_id
- source_event_id
- actor_location_id
- from_partner_id
- to_partner_id
- reference_record_type
- reference_record_number
- invoice_number
- bol_number
- asn_number
- po_number
- so_number
- event_status
- source_document_id optional
- confidence

Event types:

- harvest
- cooling
- initial_packing
- first_land_based_receiving
- shipping
- receiving
- transformation

Purpose:

- Represents the header of a CTE-style event already entered in ENSESO4Food, TrackKey, ERP/WMS, EDI/ASN, or an Excel export.
- One event can contain multiple product/lot lines, so product and lot detail belongs in `TraceabilityEventLine`, not only in the event header.

### TraceabilityEventLine

Fields:

- id
- audit_project_id
- traceability_event_id
- line_number
- product_id
- product_name
- ftl_category
- lot_or_tlc
- quantity
- unit
- originator_location_id
- tlc_generator_contact_name
- tlc_generator_contact_phone
- tlc_generator_contact_email
- source_lot_or_tlc
- output_lot_or_tlc
- line_status
- notes

Purpose:

- Represents each product/lot/quantity row inside a CTE event.
- Supports multi-product shipments, mixed lots, transformations with multiple inputs, and line-level findings.

### KDERequirement

Fields:

- id
- cte_type
- kde_name
- field_key
- required_status: required / conditional / not_applicable
- applies_when
- product_scope: all_ftl / produce / aquaculture / sprouts / seafood_from_fishing_vessel / exempt_supplier_case / other
- source_chunk_id
- rule_card_id
- example_value
- severity_if_missing
- expert_review_required
- status: draft / in_review / approved / deprecated
- reviewed_by
- reviewed_at
- version

Purpose:

- Stores the approved FSMA 204 KDE checklist for each CTE.
- Prevents TraceReady from using a generic checklist that misses event-specific KDEs such as harvest date, field/growing-area name, TLC source, or transformation output TLC.

Required MVP CTE requirement groups:

- Harvesting.
- Cooling before initial packing.
- Initial packing for RACs.
- Initial packing for sprouts.
- Initial packing when food is received from an exempt person.
- First land-based receiving for food obtained from a fishing vessel.
- Shipping.
- Receiving.
- Receiving from an exempt person.
- Transformation for FTL ingredients used.
- Transformation for new food produced.
- Traceability plan.

### EventKDEValue

Fields:

- id
- audit_project_id
- traceability_event_id
- traceability_event_line_id optional
- kde_requirement_id optional
- cte_type
- kde_name
- field_key
- observed_value
- normalized_value
- value_unit
- source_field
- source_system_confidence
- extraction_method: manual / spreadsheet_parser / ocr / llm / api_import
- status: present / missing / conflicting / not_applicable / unknown / conditional_pending
- evidence_document_id optional
- evidence_item_id optional
- reviewer_status
- notes

Purpose:

- Stores actual captured KDE values from event exports or source records.
- Allows TraceReady to compare `KDERequirement` rows against observed data and produce explainable findings.

### TransformationLink

Fields:

- id
- audit_project_id
- transformation_event_id
- input_product_id
- input_lot_code
- output_product_id
- output_lot_code
- quantity_in
- quantity_out
- linkage_status
- source_document_id

Statuses:

- linked
- missing_input_lot
- missing_output_lot
- missing_link
- quantity_mismatch
- cannot_determine

### LotLineageCheck

Fields:

- id
- audit_project_id
- product_id
- supplier_id
- incoming_lot_code
- internal_lot_code
- outgoing_lot_code
- transformation_event_id
- status
- risk_level
- explanation
- evidence_document_id

Statuses:

- preserved
- overwritten_without_transformation
- transformed_and_linked
- transformed_missing_link
- missing_lot
- cannot_determine

### KDECheck

Fields:

- id
- audit_project_id
- traceability_event_id
- kde_name
- expected
- observed_value
- status
- severity
- evidence_document_id

Statuses:

- present
- missing
- conflicting
- not_applicable
- unknown

### GapFinding

Fields:

- id
- audit_project_id
- category
- title
- severity
- description
- evidence
- recommended_action
- owner_type
- status
- rule_card_id
- rule_card_version
- audit_plan_check_id
- regulatory_source_id
- interpretation_status
- confidence
- expert_review_required
- reviewer
- reviewed_at

Categories:

- product_coverage
- supplier_obligation
- kde_completeness
- lot_code_lineage
- transformation_linkage
- data_sharing
- traceability_plan
- physical_labeling

Statuses:

- open
- needs_review
- accepted
- resolved
- dismissed

Interpretation statuses:

- approved_rule
- needs_expert_review
- customer_evidence_missing
- cannot_determine
- not_determined
- proposed_change
- discussion_flexibility
- out_of_scope

### SupplierScore

Fields:

- id
- audit_project_id
- supplier_id
- products_count
- covered_products_count
- records_reviewed
- missing_kde_count
- lot_code_gap_count
- label_gap_count
- score
- status

Statuses:

- green
- yellow
- red
- unknown

### RemediationTask

Fields:

- id
- audit_project_id
- gap_finding_id
- title
- description
- owner
- priority
- due_date
- status

Statuses:

- proposed
- accepted
- in_progress
- waiting_on_supplier
- completed
- blocked

## MVP Database Choice

Use PostgreSQL if building web app now.

Use SQLite if building a local prototype.

Avoid premature multi-tenant complexity until first paid pilots.
