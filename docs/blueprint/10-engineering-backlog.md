# Engineering Backlog

## Goal

Translate the TraceReady Audit blueprint into buildable engineering tasks.

This backlog assumes the first build is an internal audit workbench, not a full customer-facing SaaS platform.

## Epic 1: Project Setup

Tasks:

- choose stack: Next.js + TypeScript + PostgreSQL, or Python/FastAPI + React,
- create repo,
- add README,
- add environment config,
- add basic lint/format,
- add local database setup,
- add seed data,
- add basic auth or admin-only password gate.

Definition of done:

- app runs locally,
- database connects,
- admin can open dashboard.

## Epic 2: Audit Project Management

User story:

> As a TraceReady operator, I can create an audit project for a customer/site.

Tasks:

- create Customer model,
- create Site model,
- create AuditProject model,
- create project list page,
- create project detail page,
- support audit status changes.

Definition of done:

- operator can create and edit an audit project.

## Epic 3: File Intake

User story:

> As an operator, I can upload or register customer files for an audit.

Tasks:

- file upload UI,
- file metadata model,
- local file storage,
- document type selector,
- notes field,
- upload status.

Supported MVP file types:

- CSV,
- XLSX,
- PDF,
- PNG/JPG.

Definition of done:

- files can be attached to an audit project and tagged by type.

## Epic 4: Structured Data Import

User story:

> As an operator, I can import rows from CSV/XLSX files into reviewable tables.

Tasks:

- parse CSV,
- parse XLSX,
- map columns manually,
- save imported rows,
- show raw rows,
- allow correction.

First import targets:

- item master,
- supplier list,
- receiving records,
- shipping records.

Definition of done:

- operator can map a spreadsheet into normalized audit records.

## Epic 5: Document Text Extraction

User story:

> As an operator, I can extract text from PDFs and simple images for review.

Tasks:

- PDF text extraction,
- OCR placeholder or manual text entry for images,
- store extracted text,
- show extracted text beside document.

Definition of done:

- operator can view extracted document text in the audit project.

## Epic 6: AI-Assisted Extraction

User story:

> As an operator, I can ask AI to extract likely product, supplier, lot, quantity, and date fields from a document.

Tasks:

- design extraction prompt,
- return structured JSON,
- validate JSON schema,
- store confidence,
- allow human correction,
- preserve evidence text.

Definition of done:

- AI extraction creates draft fields, but human approval is required.

## Epic 7: Product Coverage Review

User story:

> As an operator, I can classify products as likely covered, maybe covered, likely not covered, or needs review.

Tasks:

- product table,
- FTL status field,
- confidence field,
- reason field,
- AI-assisted suggestion,
- human approval.

Definition of done:

- product coverage table can be included in report.

## Epic 8: KDE Completeness Checks

User story:

> As an operator, I can run checks for missing fields in receiving/shipping records.

Tasks:

- define required fields by event type,
- run field presence rules,
- create KDECheck records,
- display missing/conflicting fields,
- create gap findings.

Definition of done:

- system can identify missing lot code, quantity, date, source/destination, and reference document fields.

## Epic 9: Lot-Code Lineage Checks

User story:

> As an operator, I can detect when incoming lot codes appear overwritten or disconnected.

Tasks:

- compare incoming supplier lot, internal lot, outgoing lot,
- detect missing lot,
- detect possible overwrite,
- mark cannot determine,
- generate finding with evidence.

Definition of done:

- system produces lot-code lineage risk table.

## Epic 10: Transformation Linkage Checks

User story:

> As an operator, I can check whether transformed products link input lots to output lots.

Tasks:

- transformation record model,
- input lot field,
- output lot field,
- quantity in/out,
- linkage status,
- gap finding generation.

Definition of done:

- system can flag missing input-output lot linkage.

## Epic 11: Scoring Engine

User story:

> As an operator, I can generate red/yellow/green category scores.

Tasks:

- define score categories,
- calculate counts,
- map severity to red/yellow/green,
- allow manual override,
- store score explanation.

Definition of done:

- audit project has category scores and overall score.

## Epic 12: Report Generator

User story:

> As an operator, I can generate the customer-facing TraceReady Audit report.

Tasks:

- Markdown report template,
- report data serializer,
- findings table,
- supplier scorecard,
- remediation checklist,
- PDF export.

Definition of done:

- operator can generate a report from one audit project.

## Epic 13: Exception Backlog

User story:

> As an operator, I can convert audit findings into remediation tasks.

Tasks:

- RemediationTask model,
- task list,
- owner,
- status,
- priority,
- supplier follow-up draft.

Definition of done:

- each gap can become a task for remediation.

## Epic 14: Website

User story:

> As a potential customer, I can understand TraceReady and request a sample audit.

Tasks:

- homepage,
- what we check page,
- sample report page,
- partner page,
- request audit form,
- basic analytics.

Definition of done:

- website is live and can capture leads.

## MVP Cut Line

Build for first demo:

- Epic 1
- Epic 2
- Epic 3
- Epic 4 basic
- Epic 7 manual
- Epic 8 basic
- Epic 11 basic
- Epic 12 Markdown report
- Epic 14 static website

Defer:

- full OCR,
- full AI extraction,
- customer portal,
- direct integrations,
- supplier portal,
- automated email sending.

