# TraceReady Audit Report Spec

## Report Name

TraceReady FSMA 204 Readiness Audit

## Report Positioning

Use:

> Preliminary digital readiness review.

Avoid:

> Certification.

Avoid:

> Legal opinion.

## Report Sections

### 1. Cover Page

Fields:

- customer name
- site/facility
- date
- audit scope
- reviewed records count
- prepared by TraceReady

### 2. Executive Summary

Include:

- overall readiness score: red/yellow/green
- top 3 high-risk gaps
- top 3 remediation actions
- recommended next step

Example:

> Overall readiness: Yellow. The reviewed sample shows partial traceability readiness, but supplier KDE flow and lot-code lineage need remediation before platform onboarding or audit readiness.

### 3. Audit Scope

Include:

- record date range
- products reviewed
- suppliers reviewed
- documents reviewed
- event types reviewed
- excluded areas

### 4. Product Coverage Assessment

Purpose:

Identify which products appear to fall under the Food Traceability List.

Table columns:

- product code
- product name
- supplier
- FTL status
- confidence
- notes

Statuses:

- likely covered
- maybe covered
- likely not covered
- needs review

### 5. Supplier Obligation Map

Purpose:

Show which suppliers are connected to covered or possibly covered products.

Table columns:

- supplier
- covered products
- sample records reviewed
- missing KDE count
- readiness status
- next action

### 6. KDE Completeness Report

Purpose:

Identify missing or conflicting fields.

Table columns:

- record ID
- event type
- product
- supplier/customer
- missing fields
- conflicting fields
- severity
- evidence

KDE examples:

- traceability lot code
- quantity
- unit
- source location
- destination location
- event date
- reference document
- ship-from / receive-to information

### 7. Lot-Code Lineage Risk

Purpose:

Check whether lot-code lineage appears preserved.

Table columns:

- product
- incoming supplier lot
- internal lot
- outgoing lot
- transformation event
- status
- risk
- explanation

Statuses:

- preserved
- overwritten without transformation
- transformed and linked
- transformation link missing
- lot unknown
- cannot determine

### 8. Transformation Linkage Review

Purpose:

Check whether input lots connect to output lots.

Applies to:

- packers
- processors
- food hubs
- commissary kitchens
- repackers
- fresh-cut operations

Table columns:

- transformation record
- input product/lot
- output product/lot
- quantity relationship
- linkage status
- gap

### 9. Data-Sharing Readiness

Purpose:

Assess whether the customer can provide traceability data downstream.

Checks:

- FDA-style sortable spreadsheet readiness
- customer-specific data readiness
- EDI/ASN completeness
- traceability platform onboarding readiness
- traceability plan evidence

### 10. Red/Yellow/Green Scorecard

Categories:

- product coverage
- supplier obligations
- receiving KDEs
- lot-code lineage
- transformation linkage
- shipping/customer sharing
- traceability plan
- physical labeling/case scanning

### 11. Remediation Checklist

Split into:

Immediate:

- fix critical gaps,
- identify covered products,
- request missing supplier KDEs,
- stop lot overwrite workflow.

Next 30 days:

- update receiving templates,
- create supplier communication plan,
- add transformation linkage fields,
- define customer export process.

Next 90 days:

- platform onboarding,
- ERP/WMS changes,
- supplier scorecard,
- recurring monitoring.

### 12. Appendix

Include:

- documents reviewed
- extracted fields
- confidence notes
- open questions
- assumptions
- source references

## Report Tone

Use direct, practical language.

Avoid scare tactics.

Do not overstate compliance.

Say:

> Based on the sample reviewed, this area appears incomplete.

Do not say:

> You are noncompliant.

## Deliverables

For MVP:

- Markdown report
- PDF report
- CSV/XLSX findings table
- supplier scorecard CSV/XLSX

Later:

- web dashboard
- recurring score history
- supplier email packet
- platform-ready export

