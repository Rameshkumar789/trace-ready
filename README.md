# TraceReady

TraceReady is an AI-native FSMA 204 readiness and remediation system for food traceability.

The first product is **TraceReady Audit**:

> A digital FSMA 204 readiness audit that shows whether a food operator's products, suppliers, records, lot-code workflows, transformations, and data-sharing processes are actually traceability-ready.

## Product Sequence

1. **TraceReady Audit**  
   Digital FSMA 204 gap report.

2. **TraceReady Remediation**  
   Ongoing workflow to fix supplier KDE gaps, lot-code lineage issues, transformation linkage, and data-sharing readiness.

3. **TraceReady Integrations**  
   Export clean data into ERP, WMS, EDI, ENSESO4Food, ReposiTrak, Starfish, TagOne, FoodLogiQ, and similar systems.

## Project Structure

- `docs/blueprint/`  
  Strategy, PRD, architecture, data model, report spec, website spec, roadmap, engineering backlog, and customer pilot plan.

- `docs/chat-history/`  
  Raw pasted notes, transcript material, and working analysis from customer/market conversations.

- `docs/research/`, `docs/market/`, `docs/strategy/`, `docs/partners/`, `docs/outreach/`  
  Moved research and conversation artifacts from the original `outputs/` folder.

- `app/`  
  Future internal audit workbench.

- `website/`  
  Future public marketing website.

- `data/samples/`  
  Future fake/redacted sample input records.

- `reports/samples/`  
  Future sample TraceReady Audit outputs.

## Start Here

Read these first:

1. [Blueprint Index](docs/blueprint/00-index.md)
2. [Company And Product Strategy](docs/blueprint/01-company-product-strategy.md)
3. [MVP PRD](docs/blueprint/02-mvp-prd.md)
4. [Engineering Backlog](docs/blueprint/10-engineering-backlog.md)
5. [Website Build Spec](docs/blueprint/11-website-build-spec.md)
6. [Granular Implementation Task Plan](docs/blueprint/12-granular-implementation-task-plan.md) - includes technology choices, public deployment plan, sprint sequencing, and agent-ready tasks.

## Current Build Decision

Build first:

> A service-led, software-assisted TraceReady Audit report.

Do not build first:

- full traceability platform
- ERP/WMS replacement
- QR/label execution system
- supplier portal
- deep integrations
- fully automated compliance certification
