# Website Build Spec

## Website Type

Static marketing website with a lead form.

Do not build a login portal yet.

## Brand Direction

Tone:

- calm,
- credible,
- practical,
- compliance-aware,
- not hype-driven.

Visual style:

- clean B2B operations software,
- restrained color palette,
- white/light background,
- green/teal accent acceptable,
- avoid heavy AI visual language,
- avoid blockchain/provenance imagery,
- avoid generic dashboard stock visuals.

## Site Map

1. Home
2. What We Check
3. Sample Report
4. For Partners
5. Request Audit

## Page 1: Home

Sections:

1. Hero
2. Problem
3. What TraceReady Audit checks
4. How it works
5. Built for produce/fresh-food operators
6. Partner-friendly positioning
7. CTA

Hero copy:

Headline:

> Find your FSMA 204 traceability gaps before an audit, recall, or platform onboarding.

Subheadline:

> TraceReady Audit reviews your products, suppliers, shipment records, lot-code workflows, and transformation data to show where your current process is not yet traceability-ready.

CTA:

> Request a sample audit

## Page 2: What We Check

Sections:

1. Covered product scope
2. Supplier KDE flow
3. Lot-code lineage
4. Transformation linkage
5. Data-sharing readiness
6. Remediation plan

Each section should answer:

- what we check,
- why it matters,
- what evidence we review.

## Page 3: Sample Report

Sections:

1. Report preview
2. Scorecard preview
3. Supplier scorecard preview
4. Remediation checklist preview
5. Disclaimer

Important:

Use fake/sample data.

Do not expose real customer data.

## Page 4: For Partners

Audience:

- traceability platforms,
- food safety consultants,
- auditors,
- ERP/WMS implementers.

Message:

> TraceReady can help prospects understand their readiness gaps before platform onboarding or onsite audit work.

Sections:

1. Why readiness matters
2. How the pre-audit helps partners
3. What TraceReady does not replace
4. Partner CTA

## Page 5: Request Audit

Form fields:

- full name
- company
- role
- email
- company type
- current systems
- biggest traceability concern
- optional file upload later

MVP form destination:

- email notification,
- Google Sheet,
- CRM later.

## Component List

Components:

- Header
- Footer
- Hero
- CTAButton
- FeatureCheckCard
- WorkflowSteps
- ScorecardPreview
- ReportPreview
- LeadForm
- DisclaimerBlock

## Technical Recommendation

Use:

- Next.js,
- static pages,
- Tailwind CSS,
- no database for website v1,
- form submit to email/API route,
- Vercel or similar hosting.

## Website Success Metrics

Track:

- visitors,
- request audit clicks,
- form submits,
- partner inquiries,
- sample report downloads.

## Copy Guardrails

Use:

- "preliminary readiness review"
- "gap report"
- "sample records"
- "remediation checklist"
- "partner-friendly"

Avoid:

- "certified compliant"
- "guaranteed FDA readiness"
- "fully automated audit"
- "replace your ERP"
- "replace traceability platforms"

