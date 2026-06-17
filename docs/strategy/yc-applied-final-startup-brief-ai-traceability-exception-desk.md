# YC-Applied Final Startup Brief: AI Traceability Exception Desk

## 1. Final Startup Thesis

Build an **AI-native service company for food traceability operations**.

Start by selling a service-led outcome:

**"Send us your messy supplier and shipment records. We will find missing KDEs, resolve exceptions, chase suppliers, and return clean audit-ready traceability data."**

Then productize the repeated work into:

**AI Traceability Exception Desk**

The company should not begin as generic FSMA software.

It should begin as:

**Dirty Data Audit -> Managed Traceability Exception Desk -> Traceability Operations Platform**

## 2. YC Pattern Applied

Recent YC thinking points to a clear pattern:

**Pick a painful, expensive workflow in a boring or regulated industry. Use AI to do the work, not just assist the worker. Start narrow, do things that don't scale, capture proprietary workflow context, then productize into agents and infrastructure.**

Your idea fits this pattern well if you build it as an operations company, not only as software.

### YC Pattern 1: AI-Native Service Company

YC is pushing founders toward companies that do not merely sell tools. They sell the service.

For your startup:

- Do not sell "FSMA 204 software" first.
- Sell "traceability exception cleanup."
- Use AI internally to reduce labor.
- Give customers a simple readiness dashboard and clean outputs.

Hearth Property example:

- Hearth does not sell software to property managers.
- Hearth becomes the AI-native property manager.
- The customer buys the outcome.

Your equivalent:

- Do not sell software to traceability teams.
- Become the AI-native traceability operations desk.
- The customer buys clean records and audit readiness.

### YC Pattern 2: Company Brain

YC's "company brain" idea says the bottleneck for AI automation is scattered operational knowledge.

Food distributors have traceability knowledge scattered across:

- supplier emails
- invoices
- BOLs
- ASNs / EDI
- labels
- receiving records
- item masters
- supplier contacts
- QA notes
- EDI exceptions
- customer-specific requirements

Your system should become the **traceability brain** for a distributor.

It should know:

- which suppliers send bad data
- which fields are usually missing
- which SKUs map to which distributor items
- which document is the source of truth
- which exceptions go to QA vs EDI vs receiving
- which export format each downstream system needs

### YC Pattern 3: Closed-Loop System

YC is pushing founders beyond dashboards.

A dashboard shows a problem.

A closed-loop system:

1. detects the problem
2. determines the owner
3. drafts the fix
4. routes the work
5. tracks completion
6. exports the clean result
7. learns from the pattern

Your product should not stop at "missing KDE dashboard."

It should run the loop:

**ingest -> extract -> compare -> detect -> route -> supplier follow-up -> repair -> export -> prove -> learn**

### YC Pattern 4: Agent-First Software

YC says future software should be usable by agents, not only humans clicking dashboards.

For your product, every object should be machine-readable:

- shipment
- document
- supplier
- item
- KDE
- CTE
- exception
- evidence
- routing rule
- supplier request
- export job
- audit packet

This lets you build agent workflows reliably:

- intake agent
- extraction agent
- matching agent
- validation agent
- routing agent
- supplier follow-up agent
- export agent
- audit proof agent

### YC Pattern 5: Sell To Large Enterprises Earlier, But With A Narrow Wedge

YC notes that AI lets small teams build useful products for large enterprises faster than before.

But the wedge must be narrow.

Do not pitch Walmart or Sysco:

**"We are a new traceability platform."**

Pitch:

**"Give us 50 redacted shipment record sets. We will show missing KDEs, supplier gaps, mismatch patterns, and produce a clean FDA-style export."**

This is small enough to buy and concrete enough to evaluate.

## 3. Problem Statement

Food distributors are under pressure to produce complete traceability records for FSMA 204, customer requirements, recalls, and audits.

The problem is not that the industry has no software.

The problem is that the data needed by the software is messy.

Records arrive through:

- invoices
- bills of lading
- packing slips
- ASNs / EDI
- supplier emails
- spreadsheets
- label photos
- receiving records
- item masters
- supplier master data

The records often disagree:

- supplier SKU does not match distributor SKU
- invoice quantity does not match receiving quantity
- label lot does not match packing slip lot
- ASN is missing KDEs
- TLC source is missing
- ship-from location is incomplete
- broker email has information not present in EDI
- receiving captured partial data

The manual work sits across:

- QA
- compliance
- EDI
- receiving
- inventory
- purchasing
- supplier compliance
- traceability data teams

This creates a hidden operations desk inside every distributor.

Your company should make that hidden desk explicit, managed, and AI-native.

## 4. Final Category

Best category:

**AI Traceability Exception Desk**

Long-form category:

**AI-native traceability data operations for food distributors**

What it does:

**Turns messy supplier/shipment evidence into clean, audit-ready KDE/CTE data.**

What it is not:

- not another ERP
- not another WMS
- not another EDI network
- not another traceability repository
- not blockchain provenance
- not a generic document scanner

## 5. Why Now

Several forces are converging:

1. **FSMA 204 creates regulatory pressure.**
   - FDA originally set the compliance date for January 20, 2026.
   - FDA has extended enforcement timing and states it will not enforce the Food Traceability Rule before **July 20, 2028**.
   - The extension reduces immediate panic, but it creates a 24-month implementation window for distributors to clean data, align suppliers, and test mock traces.

2. **Retailers and distributors are moving before the final enforcement date.**
   - ReposiTrak has public adoption claims around thousands of suppliers sharing FSMA 204 data.
   - Walmart, Amazon, McLane, PFG, Sysco, Mondelez, Inspire, and others have job-market signals around traceability programs.

3. **Existing systems need clean input.**
   - ERP, WMS, EDI, ReposiTrak, TagOne, Starfish, iFoodDS, and FoodLogiQ all benefit from clean traceability records.
   - But messy pre-system evidence remains a labor problem.

4. **AI can now do the first-pass extraction, matching, classification, and follow-up drafting.**
   - The remaining work is workflow design, proof, exception routing, and trust.

5. **YC is pushing service-led AI companies.**
   - This lets you start without waiting for perfect software.

## 6. Data Points That Matter

These are the hard signals behind the startup thesis.

### Regulatory Data Points

| Signal | Data Point | Why It Matters |
|---|---|---|
| FSMA enforcement timing | FDA states it will not enforce the Food Traceability Rule before **July 20, 2028**. Original compliance date was **January 20, 2026**. | Buyers have time to adopt, but the implementation work is large and cross-company. |
| FDA response requirement | Covered entities must provide requested traceability information to FDA within **24 hours** or another reasonable time agreed by FDA. | Your product should measure recall/mock-trace response time and export readiness. |
| Output format | FDA provides an **electronic sortable spreadsheet** template for CTE/KDE submission. | Your MVP can produce a concrete audit artifact, not vague compliance advice. |
| Scope | The rule applies to entities that manufacture, process, pack, or hold foods on the Food Traceability List. | Distributors, wholesalers, processors, retailers, and suppliers all need data exchange. |

### YC Data Points

Local YC company data shows that your model fits current YC patterns.

| Signal | Data Point | Interpretation |
|---|---:|---|
| Recent YC companies analyzed | **1,516** from Winter 2024 through Spring 2026 | Large enough sample to see patterns. |
| B2B companies | **975** | YC's recent center of gravity is B2B workflows. |
| AI keyword/tag companies | **1,369+ batch-level AI hits across 2024-2026 counts** | AI is table stakes, not differentiation by itself. |
| Agent keyword companies | **671** in keyword bucket analysis | Agent/workforce language is a major pattern. |
| Supply chain / industrial / logistics bucket | **234** | Physical operations and supply-chain workflows are YC-relevant. |
| Legal / compliance / risk bucket | **280** | Regulated, proof-heavy workflows are strong AI startup territory. |

Conclusion:

**The YC-compatible version is not "AI for FSMA paperwork." It is an AI-native service/workflow company for regulated supply-chain operations.**

### Competitor Data Points

| Competitor | Data Point | What It Means For You |
|---|---|---|
| ReposiTrak | Public materials describe automated/no-scan FSMA 204 traceability KDE record creation, Touchless Traceability, AI-assisted error correction, and supplier/DC/store record creation. | ReposiTrak is the strongest incumbent. Do not claim "nobody solves this." Position before/around their network. |
| TagOne | Public site describes Supplier Link, Integration Engine, validation, FDA reports, exception reports such as TLC/Quantity/Item mismatch, APIs, EDI/AS2, and GS1/EPCIS support. | TagOne overlaps heavily with validation/reporting. Your wedge must be daily operational repair, supplier chase, and pre-repository evidence cleanup. |
| TraceWiseAI | Public site describes ERP/spreadsheet sync, AI tracing, FSMA gap detection, offline capture, audit-ready export, label printing, and compliance dashboard. | Close AI-native FSMA competitor. Differentiate by distributor-specific exception desk and service-led workflow. |
| Starfish | IFMA/Starfish materials describe connecting ERP, WMS, EDI, spreadsheets, traceability systems, and 100+ integrations across traceability/ERP/EDI/WMS/TMS/document platforms. | Starfish is the interoperability layer. You are the data-quality repair layer before exchange. |
| CDX / food ERP vendors | CDX and similar food distribution ERPs position FSMA 204 as built into operational transactions. | ERP vendors own internal records, but they still depend on supplier data quality and cross-document reconciliation. |

### Jobs Data Points

The strongest labor-demand signals:

| Company | Role Signal | Salary/Budget Signal | Product Implication |
|---|---|---:|---|
| Performance Food Group / Core-Mark | Product Traceability Data Specialist | **$60K-$95K + bonus** | Direct human equivalent of the Traceability Exception Desk. |
| Amazon | Senior Traceability Program Manager, North America Food Safety | **$119.9K-$198.3K + equity** | Enterprise buyers care about product features, supplier policies, outreach, data quality audits, KPIs, and ASN/EDI. |
| Walmart | Senior Manager, Food Safety & Traceability | **$90K-$180K** in job mirrors | Retailers are pushing supplier/DC/store traceability compliance and WMS/item catalog/supplier portal alignment. |
| RedCloud Consulting | Change Manager, FDA Traceability Project | **$153K-$187K** | Enterprises pay for change management, readiness, CTEs, supplier adoption, and ASN workflows. |
| Mondelez | Senior Manager, Traceability | **$140K-$193K** | Traceability is becoming enterprise data governance, not only QA paperwork. |

Product implication:

**The buyer is already paying humans and consultants to coordinate traceability data quality. The product should make one traceability operator 3-5x more productive.**

### Adoption Data Points

Food companies will adopt if the product avoids disruption.

| Adoption Constraint | Evidence / Market Signal | Product Response |
|---|---|---|
| Companies already have ERP/WMS/EDI/traceability systems | ReposiTrak, TagOne, Starfish, CDX, iFoodDS, FoodLogiQ all position around existing systems or low-disruption adoption. | Do not replace systems. Export clean data into them. |
| Supplier maturity varies widely | TagOne emphasizes multiple supplier data entry options; Starfish emphasizes partner connectivity. | Build supplier follow-up and flexible intake: email, PDF, spreadsheet, ASN, API later. |
| Retailer/distributor pressure arrives before FDA enforcement | ReposiTrak/Starfish/IFMA and job postings show adoption work already happening. | Sell readiness and data-quality audits now, not only "compliance by 2028." |
| Buyers need proof, not dashboards | FDA requires records and sortable spreadsheet under request. | Produce evidence-backed audit packets and clean spreadsheet outputs. |

## 7. Competition Landscape

There is competition.

The market is not empty.

Your opportunity is to choose a sharper job than the incumbents.

### ReposiTrak

What they do:

- traceability network
- supplier compliance
- structured FSMA 204 data exchange
- automated KDE record creation
- automated traceability error correction

Why they are dangerous:

ReposiTrak is the strongest incumbent threat because it already operates a large food traceability network and is pushing automation/error correction.

Your differentiation:

**ReposiTrak helps once data enters the network. We fix messy operational evidence before and around the network.**

Focus on:

- PDFs
- emails
- label photos
- BOLs
- packing slips
- incomplete ASNs
- receiving notes
- item master mismatches
- supplier follow-up

### TagOne

What they do:

- FSMA 204 compliance platform
- supplier integration
- TagOne Supplier Link
- Integration Engine
- validation
- exception reporting
- FDA reports
- regulatory repository

Why they are dangerous:

TagOne explicitly discusses exception management reports such as TLC/Quantity/Item mismatch, supplier collaboration, APIs, EDI/AS2, GS1/EPCIS, and repository workflows.

Your differentiation:

**TagOne can be the repository. We are the operational repair desk that gets the record ready.**

### TraceWiseAI

What they do:

- AI FSMA 204 compliance
- ERP/spreadsheet sync
- AI tracing
- gap detection
- offline capture
- audit-ready export
- label printing

Why they are dangerous:

They are close to the AI compliance narrative.

Your differentiation:

**TraceWiseAI is AI compliance software. We are daily traceability operations for distributors.**

Go deeper on:

- supplier chase
- cross-document proof
- QA/EDI/receiving routing
- item/SKU matching
- recurring supplier issue analytics

### Starfish

What they do:

- neutral interoperability
- data-sharing layer
- ERP/WMS/EDI/spreadsheet connectivity
- FSMA 204 exchange
- GS1/EPCIS-style data movement

Why they are relevant:

Starfish is close to "connect everything, replace nothing."

Your differentiation:

**Starfish moves standardized data. We fix incomplete, conflicting, non-standard data before it moves.**

### Solute / Anchr / Food Distributor AI OS

What they do:

- distributor operations automation
- order entry
- procurement
- inventory
- customer support
- finance/back-office workflows
- some traceability functionality

Why they are dangerous:

They can expand from order management into receiving, inventory, supplier records, and traceability exceptions.

Your differentiation:

**They are broad distributor OS. We are traceability-native and deeper on regulated data quality.**

## 8. Strategic Positioning

Do not position as:

**"We replace ReposiTrak / TagOne / FoodLogiQ / ERP."**

Position as:

**"We make those systems work by feeding them clean traceability data."**

Best positioning:

**AI Traceability Exception Desk**

Buyer-facing line:

**We fix broken supplier traceability records before they break your ERP, WMS, EDI, ReposiTrak, iFoodDS, FoodLogiQ, Starfish, TagOne, or FDA audit.**

Service-led version:

**Send us messy shipment records. We find missing KDEs, resolve exceptions, chase suppliers, and return clean audit-ready traceability data.**

## 9. Adoption Path For Food Companies

Food companies will not adopt this as a full replacement system first.

They will adopt it if it reduces immediate manual pain without disrupting existing systems.

### Step 1: Audit

Offer:

**FSMA 204 Dirty Data Audit**

Customer sends:

- 20-50 redacted shipment record sets
- invoice
- BOL
- ASN
- packing slip
- label photo
- receiving record
- item master sample

You return:

- KDE completeness score
- supplier issue report
- mismatch report
- exception types
- sample FDA-style sortable spreadsheet
- manual-hours estimate

### Step 2: Managed Exception Desk

Offer:

**Monthly Traceability Exception Desk**

You handle:

- recurring document intake
- exception detection
- supplier follow-up drafts
- QA/EDI/receiving routing
- clean exports
- weekly readiness reports

### Step 3: Embedded Workflow

Add:

- shared inbox
- SFTP intake
- ERP/WMS exports
- EDI/ASN repair files
- traceability-network output templates
- customer-specific FDA/customer audit formats

### Step 4: Supplier Portal

Add:

- supplier correction links
- supplier scorecards
- recurring issue reports
- required KDE checklists
- response SLAs

### Step 5: Enterprise Command Center

Add:

- facility readiness score
- supplier readiness score
- mock trace performance
- recall packet generation
- leadership dashboards
- predictive exception risk

## 10. MVP

### MVP Name

**FSMA 204 Dirty Data Audit**

### MVP Goal

Prove that traceability data cleanup is painful, measurable, and valuable.

### MVP Scope

Build the minimum product/service needed to process 20-50 shipment record sets.

Must handle:

- invoice
- BOL
- packing slip
- ASN / EDI
- label photo
- receiving record
- item master

### MVP Workflow

1. Upload or email documents.
2. Extract candidate KDEs.
3. Compare fields across documents.
4. Identify missing/conflicting values.
5. Map supplier SKU to distributor SKU.
6. Classify exception type.
7. Generate supplier follow-up draft.
8. Produce clean spreadsheet export.
9. Show field-level evidence.
10. Estimate manual time saved.

### MVP Output

Deliver a PDF/Markdown/spreadsheet-style audit packet:

- record completeness score
- missing KDE table
- exception table
- supplier issue ranking
- side-by-side document comparison
- clean FDA-style export
- field-level evidence links
- supplier follow-up drafts
- recommended next actions

### MVP Success Criteria

The MVP is successful if:

- customer recognizes the exceptions as real work
- customer confirms the workflow matches current manual pain
- at least 30-50% of manual review time can be reduced
- customer asks for recurring monitoring
- customer gives more records or introduces another facility/team

## 11. First Product After MVP

**Managed Traceability Exception Desk**

This is the first real business.

It should combine:

- software
- AI agents
- human review
- operational service

Do not force self-serve SaaS too early.

Customer buys:

**clean traceability output and fewer unresolved exceptions.**

They do not buy:

**AI magic.**

## 12. Internal Agent Architecture

The service should gradually become agent-driven.

### Intake Agent

Organizes documents by supplier, shipment, PO, ASN, date, and facility.

### Extraction Agent

Extracts product, GTIN, supplier SKU, distributor SKU, lot, quantity, UOM, dates, TLC/source, source/destination.

### Matching Agent

Matches invoice line to ASN line to BOL line to label evidence to receiving record.

### Validation Agent

Checks business rules and FSMA/customer requirements.

### Routing Agent

Determines owner:

- supplier
- QA
- EDI
- receiving
- purchasing
- compliance

### Supplier Follow-Up Agent

Drafts correction requests and missing-field emails.

### Export Agent

Exports to:

- spreadsheet
- ERP/WMS import
- EDI/ASN repair file
- ReposiTrak/iFoodDS/FoodLogiQ/Starfish/TagOne upload format

### Audit Agent

Creates:

- field-level proof
- source-document evidence
- before/after record
- mock trace packet
- recall packet

## 13. Metrics

Your north-star metric:

**exceptions resolved per traceability operator per week**

Core metrics:

- KDE completeness rate
- missing KDEs by supplier
- exception count by type
- exception aging
- supplier response SLA
- clean export success rate
- manual minutes saved per shipment
- mock trace completion time
- recall/traceback response time
- supplier readiness score
- auto-extraction accuracy
- auto-resolution rate

YC-style ROI claim:

**We make one traceability operator 3-5x more productive.**

## 14. GTM

### First Buyer

Best early buyer:

- FSQA leader
- traceability manager
- QA/compliance director
- EDI/operations leader
- supply chain compliance owner

### First Customer Profile

Ideal first customer:

- mid-market distributor
- many suppliers
- perishable/high-risk categories
- mixed EDI and PDF/email records
- has QA/EDI/receiving teams
- knows FSMA 204 is coming
- not fully satisfied with existing traceability process

### First Offer

**$5K Dirty Data Audit**

Alternative:

Free/low-cost audit for design partner if they commit to:

- real redacted data
- weekly feedback calls
- permission to use anonymized metrics
- paid pilot if threshold is met

### Paid Pilot

**$5K-$15K/month Managed Traceability Exception Desk**

Pilot duration:

- 8-12 weeks

Pilot deliverables:

- weekly exception report
- supplier issue report
- clean export
- manual time saved estimate
- readiness dashboard

## 15. Potential MVP Customers

### Foodservice Distributors

- Performance Food Group / Core-Mark
- Sysco
- US Foods
- McLane
- Gordon Food Service
- Shamrock Foods
- Ben E. Keith
- Cheney Brothers
- Nicholas and Company
- Baldor Specialty Foods
- The Chefs' Warehouse
- KeHE
- UNFI

### Produce / Perishable Distributors

- FreshPoint
- Produce Alliance members
- regional produce distributors
- terminal market wholesalers
- specialty produce importers
- fresh-cut processors

### Seafood / Meat / Protein

- Buckhead Meat / Seafood
- seafood distributors
- specialty meat distributors
- protein processors with distributor networks

### Restaurant / Foodservice Brands

- Inspire Brands
- Darden
- Yum Brands
- Chipotle
- Sweetgreen
- Cava
- Panera

### Retail / Grocery Discovery Targets

Harder first customers, but useful discovery:

- Walmart
- Amazon Grocery / Whole Foods
- Kroger
- Albertsons
- Costco
- H-E-B
- Publix
- Wegmans

### Channel Partners

- NSF
- Trustwell
- FoodReady
- FSMA 204 consultants
- food safety consultants
- EDI consultants serving food distributors
- ERP/WMS implementation consultants

## 16. Outreach Message

Use a narrow message.

Example:

> We are helping food distributors find and repair broken FSMA 204 traceability records before audit or recall pressure hits. Send us 20-50 redacted shipment record sets and we will return a KDE coverage report, supplier issue report, mismatch analysis, and FDA-style sortable export. The goal is to show how much manual QA/EDI/receiving work can be reduced.

Shorter:

> We run a Dirty Data Audit for food traceability records. We compare invoices, BOLs, ASNs, labels, and receiving records to find missing KDEs and supplier issues.

## 17. Competitive Strategy

### Do Not Fight Incumbents Directly

Do not say:

- replace ReposiTrak
- replace TagOne
- replace FoodLogiQ
- replace ERP/WMS/EDI

Say:

- feed them cleaner data
- reduce failed imports
- repair pre-network records
- lower supplier exception burden
- prepare audit-ready exports

### Compete On Workflow Depth

Your product must be deeper on:

- invoice vs ASN vs label vs receiving comparison
- supplier SKU to distributor SKU mapping
- missing TLC/source workflows
- supplier follow-up
- QA/EDI/receiving routing
- field-level proof
- recurring supplier error patterns

### Build A Data Moat

Your moat is not the model.

Your moat is:

- supplier document patterns
- item mapping history
- exception taxonomy
- routing rules
- supplier response behavior
- export templates
- facility-specific traceability brain

## 18. Roadmap

| Phase | Product | What It Proves |
|---|---|---|
| 1 | Dirty Data Audit | Pain exists and records are broken. |
| 2 | Managed Exception Desk | Customer pays for recurring cleanup. |
| 3 | Embedded Integrations | Workflow becomes operationally sticky. |
| 4 | Supplier Portal | Suppliers fix issues at the source. |
| 5 | Recall / Mock Trace Workspace | Product becomes mission-critical. |
| 6 | Risk Intelligence | Product predicts where traceability will fail. |
| 7 | Traceability Operations Platform | Product becomes system of action for traceability data quality. |

## 19. First 30 Days

Do not build a platform.

Build the audit machine.

### Build

- upload/email intake
- document parser
- field extraction
- comparison table
- exception classifier
- supplier follow-up drafts
- clean spreadsheet export
- basic evidence links

### Manually Do

- final QA review
- supplier issue classification
- some SKU mapping
- customer-facing report writing
- recommendations

### Learn

- most common missing fields
- hardest document types
- most painful supplier issues
- buyer willingness to pay
- recurring workflows to automate

## 20. Final YC-Style Pitch

> Food distributors are drowning in messy traceability records from suppliers. QA, EDI, receiving, and compliance teams manually compare invoices, BOLs, ASNs, labels, and receiving logs to find missing KDEs and resolve supplier exceptions. We run an AI Traceability Exception Desk that turns those messy records into clean, audit-ready outputs. We start with a Dirty Data Audit and become the recurring managed exception desk. Our goal is to make one traceability operator 3-5x more productive.

## 21. Final Recommendation

Pursue the idea.

But pursue this exact version:

**AI-native service company for food traceability data operations.**

Do not start as:

- generic FSMA SaaS
- document scanner
- traceability repository
- ERP/WMS replacement

Start as:

**Dirty Data Audit -> Managed Traceability Exception Desk -> Traceability Operations Platform**

This is the version that best matches:

- YC's AI-native service-company direction
- job-market evidence
- FSMA/customer pressure
- competitor gaps
- customer adoption reality
- operational workflow pain

## 22. Sources

- YC Requests for Startups: https://www.ycombinator.com/rfs
- YC Requests for Startups 2025: https://www.ycombinator.com/rfs?year=2025
- YC Spring 2025 batch announcement: https://www.ycombinator.com/blog/announcing-yc-x25/
- ReposiTrak automated FSMA 204/KDE record creation: https://www.refrigeratedfrozenfood.com/articles/102082-repositrak-marks-first-fully-automated-fsma-204-traceability-kde-record-creation
- ReposiTrak supplier adoption signal: https://www.businesswire.com/news/home/20240716486109/en/Traceability-Technology-Proves-FSMA-204-Works-Thousands-of-Suppliers-Adopting-Now
- TagOne FSMA 204 solution: https://www.tagone.com/
- TagOne FSMA 204 experts/integration engine: https://www.tagone.com/fsma-204
- TraceWiseAI: https://www.tracewiseai.com/
- Starfish FSMA 204 interoperability: https://www.starfish-network.com/blog/what-fsma204-really-requires
- Starfish IFMA members traceability platform: https://www.starfish-network.com/ifma-members
- IFMA / Starfish partnership and 100+ integrations: https://www.ifmaworld.com/Ifma/Resources/News/2025/Partnership-with-Starfish-to-Accelerate-Traceability-and-FSMA-204-Compliance-for-Members.aspx
- CDX food distribution ERP / FSMA 204 positioning: https://centraldataexchange.com/
- Performance Food Group Product Traceability Data Specialist: https://www.breakroom.cc/en-us/jobs/listing/34050267-performance-food-group-product-traceability-data-specialist
- Amazon Senior Traceability Program Manager job mirror: https://careers.wct-fct.com/companies/amazon-3-60ad394d-c673-4474-9694-344b0cae748f/jobs/46077472-senior-traceability-program-manager-north-america-food-safety
- Walmart Senior Manager Food Safety & Traceability: https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal/job/Senior-Manager--Specialty-Compliance-and-Ethics---Food-Safety---Traceability_R-2476658
- FDA FSMA Food Traceability Rule: https://www.fda.gov/food/food-safety-modernization-act-fsma/fsma-proposed-rule-food-traceability
