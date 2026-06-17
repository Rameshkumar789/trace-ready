# MVP PRD: TraceReady Audit

## Product

TraceReady Audit

## MVP Goal

Produce a professional FSMA 204 readiness gap report from customer traceability records.

After the FDA docket-comment analysis on 2026-06-15, the MVP should be interpreted as a **record-readiness and proof-layer product**, not as a generic document-scanning product and not as a full traceability platform.

The first pilot workflow should prioritize:

1. structured customer exports/workbooks from Excel, ERP, WMS, EDI/ASN, ENSESO4Food/TrackKey, DProduce Man, or internal systems;
2. supporting evidence such as invoices, BOLs, labels, ASNs, packing slips, and PDFs;
3. deterministic checks that show whether existing records are complete, linked, interoperable, and export-ready.

The MVP should prove:

1. Customers will share redacted operational records.
2. TraceReady can identify meaningful gaps.
3. The output is useful enough that customers ask for next steps.
4. The workflow can become repeatable.
5. TraceReady can explain whether the customer's current systems can produce evidence that holds up.

## MVP Promise

Do promise:

> We show where your current products, suppliers, records, lot-code workflows, transformations, and sharing process may fail FSMA 204 readiness.

Also promise:

> We check whether your current Excel, EDI/ASN, ERP, WMS, supplier, and document records are complete, linked, and export-ready.

Do not promise:

> We certify compliance.

Do not promise:

> We can reconstruct traceability from missing physical data.

## MVP Inputs

Required:

- company name
- facility/site name
- product/item list
- supplier list
- structured traceability workbook or export
- receiving event records
- shipping event records, if available
- transformation event records, if applicable
- source document references for the reviewed records

Optional:

- invoices, BOLs, packing slips, ASNs, labels, or photos for sampled records
- transformation/production records
- customer list
- item-supplier mapping
- location list
- ERP/WMS/DProduce Man/Famous/QuickBooks export
- EDI 856 / ASN sample
- GS1/EPCIS or partner traceability export, if available
- existing traceability plan
- imported/non-English source records

## MVP Outputs

Customer receives:

1. Executive summary
2. Overall red/yellow/green readiness score
3. Product coverage assessment
4. Supplier obligation map
5. Missing KDE report
6. Lot-code lineage risk report
7. Transformation linkage review
8. Data-sharing readiness review
9. Supplier scorecard
10. Source-system readiness matrix
11. FDA-style sortable export readiness check
12. Imported/multilingual record review flags, if applicable
13. Remediation checklist
14. Recommended next step

## User Roles

Internal user:

- TraceReady operator/founder

Customer user:

- FSQA/compliance/operations stakeholder

Later users:

- supplier contact
- partner reviewer
- auditor/consultant

## MVP Workflow

1. Customer submits records through a simple upload form or secure shared folder.
2. TraceReady stores files and metadata.
3. System classifies file types.
4. System extracts structured fields where possible.
5. Internal operator reviews extracted data.
6. System runs rule checks.
7. Internal operator approves audit findings.
8. System generates report.
9. Customer receives PDF/Excel/Markdown report.
10. TraceReady asks: "Do you want us to help fix these gaps?"

## Functional Requirements

### FR1: Intake

The system must allow an internal operator to create an audit project.

Fields:

- customer name
- site name
- segment
- contact
- source system
- audit date range
- notes

### FR2: File Upload

The MVP must support upload or registration of:

- CSV
- XLSX
- PDF
- PNG/JPG
- TXT/MD notes

Primary MVP input should be structured CSV/XLSX records. PDF/image extraction is supporting evidence and review assistance, not the primary product wedge.

### FR3: Document Classification

Each file should be tagged as:

- item master
- supplier list
- receiving record
- shipping record
- CTE event export
- event line item export
- KDE value export
- TLC lineage export
- invoice
- BOL
- ASN
- EDI 856
- ERP/WMS export
- traceability platform export
- label/photo
- transformation record
- traceability plan
- imported/non-English record
- unknown

### FR4: Data Extraction

Extract or manually enter:

- product name
- product code
- supplier name
- lot code
- quantity
- unit
- ship date
- receive date
- source location
- destination location
- reference document number
- event type

### FR5: Product Coverage Assessment

Classify products:

- likely FTL covered
- possibly covered
- likely not covered
- needs review

Human review required for borderline categories.

### FR6: Supplier Obligation Mapping

Map covered/possibly covered products to suppliers.

Output:

- supplier
- products supplied
- required information likely needed
- readiness status

### FR7: KDE Completeness

For event-specific records, check:

- traceability lot code
- product description
- quantity
- unit of measure
- source location
- destination location
- event date
- reference document
- ship/receive relationship

The check must be CTE-specific. Do not use one generic field checklist across harvest, cooling, initial packing, first land-based receiving, shipping, receiving, and transformation.

### FR8: Lot-Code Lineage Check

Detect:

- incoming lot present and preserved,
- incoming lot overwritten,
- outgoing lot missing,
- lot unknown,
- transformation lot link missing,
- exact TLC present,
- TLC missing,
- inferred TLC,
- TLC range,
- commingled pallet or mixed-lot uncertainty,
- case-level vs pallet-level ambiguity,
- cannot determine.

### FR9: Transformation Linkage Check

For transformation records, detect:

- source lot present,
- output lot present,
- input-output link present,
- quantity relationship present,
- missing linkage.

### FR10: Data Sharing Readiness

Check whether customer can produce:

- FDA-style sortable export,
- customer-specific export,
- spreadsheet of KDEs,
- traceability plan evidence.
- EDI 856 / ASN data with required KDE/TLC fields,
- ERP/WMS export carrying required event and line-item fields,
- supplier-provided records that pass required KDEs forward,
- GS1/EPCIS-ready mapped fields where available.

### FR10.1: Source-System Readiness Matrix

For each source system or evidence type, show what it can and cannot prove.

Sources:

- Excel / CSV
- EDI 856 / ASN
- ERP export
- WMS export
- traceability platform export
- invoice / BOL / packing slip
- label / photo
- supplier-provided document
- imported or non-English document

Output:

- available fields
- missing required fields
- supported CTEs
- TLC support
- KDE completeness
- evidence confidence
- manual review status

### FR10.2: Supplier Data Quality Score

For each supplier represented in the audit, calculate or manually assign:

- missing KDE count
- missing TLC count
- inconsistent product/location/date fields
- response/follow-up status
- repeated issue flag
- readiness status

### FR10.3: Imported / Multilingual Record Flags

For imported or non-English records, MVP does not need full certified translation. It must flag:

- source language, if known
- fields that require translation/review
- whether English evidence is available
- whether human review is required before findings are customer-facing

### FR11: Report Generation

Generate:

- PDF or Markdown report,
- CSV/XLSX findings table,
- supplier scorecard table.

## Non-Functional Requirements

Trust:

- all AI extraction must be reviewable,
- every finding should link to evidence,
- audit report should say "preliminary readiness review," not certification.

Security:

- support redacted records,
- store files in restricted workspace,
- avoid unnecessary sensitive data,
- add deletion policy later.

Cost:

- use low-cost stack,
- manual review allowed,
- avoid expensive integrations.

Speed:

- first audit can take 1-2 days manually,
- target later: under 2 hours per small audit.

## MVP Success Metrics

Pilot success:

- customer shares real/redacted records,
- report identifies at least 3 meaningful gaps,
- customer says the output is useful,
- customer asks for remediation or next batch,
- customer pays or commits to paid follow-up.

Operational metrics:

- time to produce audit,
- number of extracted records,
- number of human corrections,
- number of repeatable rules identified,
- number of supplier gaps found.
