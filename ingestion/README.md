# TraceReady Ingestion Worker

Python worker for regulatory-source ingestion, legal-meaning chunking, citation anchoring, and draft rule-card generation.

This project is separate from the Next.js product app. The product app serves customers and reviewers. This worker prepares the regulatory intelligence layer that reviewers approve before rules become executable.

## Why This Exists

TraceReady should not ask an AI model to decide compliance directly.

The ingestion workflow is:

```text
FDA / eCFR / Federal Register / PDF source
-> versioned source snapshot
-> extracted sections and tables
-> source chunks with citations and hashes
-> AI-assisted draft rule cards / KDE requirements
-> schema validation
-> FSMA expert review in the app
-> approved executable rules
```

AI can help read and structure sources. Approved rule cards and deterministic checks decide audit findings.

## Current Status

Implemented now:

- HTML source fetch from URL.
- Raw source artifact writing.
- HTML section extraction.
- PDF URL and local-file ingestion with page extraction.
- XLSX URL and local-file ingestion with sheet extraction.
- Legal-meaning chunking.
- Citation-anchor generation.
- Source and chunk hashing.
- Local JSON artifact output.
- Local draft schemas for rule cards and KDE requirements.
- Deterministic placeholder draft generation.
- FastAPI backend with health/readiness checks, structured request logging, safe error responses, internal-token auth, and a Vercel-compatible ASGI import shim.
- Supabase table repository layer for audit jobs, files, artifacts, parsed workbook rows/cells, evidence, normalized facts, findings, traces, approved packages, source records, chunks, and source-ingestion jobs.
- Supabase object-storage abstraction for source snapshots, normalized artifacts, chunk packages, customer uploads, reports, exports, and package artifacts.
- Bounded audit job processor for workbook parsing and approved-rule execution.
- Regulatory source seed/import and production integrity-check tooling.
- Unit and integration tests for source extraction, chunking, storage, repositories, parsing, normalized evidence, approved-rule execution, job slicing, and API endpoints.

Future hardening / not MVP blockers:

- Generalized structured PDF table extraction into normalized tables. Current extraction is sufficient for the controlled FSMA source package and citation chunking; add this when onboarding broader table-heavy regulatory sources.
- Generalized typed XLSX schema extraction. Current code handles FDA sortable workbook extraction and customer evidence workbook parsing; add a reusable typed-table extraction layer when more workbook templates need first-class schemas.
- Regulatory change monitor. Needed for post-MVP governance so FDA/eCFR/source changes automatically create review tasks; not required for the first approved-package pilot if sources are manually refreshed and integrity-checked.
- Always-on long-running worker. Not needed for Vercel MVP because processing intentionally runs through bounded HTTP job slices triggered on demand (e.g. by the app on upload). Revisit only if workload volume requires a separate queue worker outside Vercel.

## Project Layout

```text
traceready/ingestion/
  pyproject.toml
  README.md
  scripts/                           # offline operational tooling (run with `python -m scripts.<...>`)
    ops/                             # build the knowledge base + seed Supabase
      ingest.py
      build_regulatory_registry.py
      ingest_fda_fsma204_hub_sources.py
      ingest_local_fda_documents.py
      seed_regulatory_sources.py
      seed_regulatory_draft_records.py
      seed_approved_rule_package.py
      check_source_artifact_integrity.py
    intelligence/
      build_phase*_*.py
      run_phase5_*.py
      validate_intelligence_schemas.py
    evaluation/
      build_phase12_web500_eval_data.py
      build_phase13_web2000_real_eval.py
      build_phase*_workbook.mjs
      node_modules -> bundled Codex Node runtime symlink, local-only
  tests/
    test_legal_chunker.py
    test_rule_card_drafter.py
    test_source_ingestion.py
  traceready_backend/
    fetchers/
      ecfr_fetcher.py
    extractors/
      ecfr_xml_extractor.py
      fda_fsma_rules_page_extractor.py
      html_extractor.py
      pdf_extractor.py
      xlsx_extractor.py
    chunking/
      legal_chunker.py
      citation_anchor.py
    drafting/
      schemas.py
      rule_card_drafter.py
      kde_drafter.py
    intelligence/                  # OFFLINE: build the approved rule package (run by hand)
      phase04_deterministic_extractors.py ... phase09_approved_rule_package.py
      phase12_generalization_evaluation.py, phase13_release_gates.py
      obligation_explanations.py, citations.py, anthropic_client.py, schemas.py
    audit_engine/                  # ONLINE: per-customer runtime the API executes
      customer_evidence.py         # parse the customer workbook
      field_mapping_governance.py  # field-mapping governance
      cte_classification.py        # classify CTEs
      rule_execution.py            # execute approved rules + emit findings
      bundled_rules/*.json         # offline fallback for the approved cards (ships in the wheel)
    api/
      main.py
      config.py
      readiness.py
      security.py
      observability.py
      errors.py
    backend/
      repositories/
      services/
      jobs/
      schemas/
    storage/
      artifacts.py
      db.py
    versioning/
      hashing.py
      source_versioning.py
  api/
    index.py
```

## Backend API Skeleton

The deployable backend entrypoint is:

```text
traceready_backend.api.main:app
```

The Vercel-compatible shim is:

```text
api/index.py
```

Current routes:

- `GET /health` returns service metadata and confirms the ASGI app is alive.
- `GET /ready` checks required environment configuration. Preview/production require database, Supabase, storage, and internal-token configuration.
- `GET /internal/ping` validates internal-token protection for internal job/admin endpoints.
- `POST /internal/jobs/audit/process-slice` claims and processes bounded audit jobs.
- `POST /internal/jobs/audit/slice` claims audit jobs for diagnostics without executing processors.
- `GET /internal/audits/{audit_project_id}/jobs` lists audit jobs for a project.
- `GET /internal/jobs/audit/{job_id}` returns job status and event history.
- `POST /internal/jobs/audit/{job_id}/retry` marks a retryable failed audit job for retry.
- `GET /internal/audits/{audit_project_id}/artifacts` lists generated audit artifact metadata.
- `POST /internal/regulatory/source-ingestion-jobs` queues a regulatory source ingestion job.
- `GET /internal/regulatory/source-ingestion-jobs` lists regulatory source ingestion jobs.
- `GET /internal/regulatory/source-ingestion-jobs/{job_id}` returns a regulatory source ingestion job and event history.
- `POST /internal/regulatory/source-integrity-check` verifies source DB rows and private source artifacts.

Configuration is loaded from environment variables:

```text
TRACEREADY_ENV
VERCEL_ENV
SUPABASE_DATABASE_URL
NEXT_PUBLIC_SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
TRACEREADY_STORAGE_BUCKET
TRACEREADY_OBJECT_STORE_MODE
TRACEREADY_INTERNAL_API_TOKEN
TRACEREADY_ALLOWED_ORIGINS
TRACEREADY_REQUIRE_CONFIGURED_DEPENDENCIES
```

Internal endpoints accept either:

```text
Authorization: Bearer <token>
x-traceready-internal-token: <token>
```

## Object Storage

Production object storage is Supabase Storage. The Python code uses the `ObjectStore` boundary in:

```text
traceready_backend.storage.artifacts
```

Runtime should use:

```text
TRACEREADY_OBJECT_STORE_MODE=supabase
NEXT_PUBLIC_SUPABASE_URL=<project-url>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
TRACEREADY_STORAGE_BUCKET=traceready-pilot-private
```

The local object store is test-only. Local development, preview, and production all use the configured Supabase project and private Supabase Storage bucket.

Current object key conventions:

```text
regulatory/sources/{source_id}/versions/{version}/raw/{filename}
regulatory/sources/{source_id}/versions/{version}/normalized/{filename}
regulatory/sources/{source_id}/versions/{version}/chunks/source-chunks.json
regulatory/packages/{package_id}/versions/{version}/{filename}
customers/{customer_id}/audits/{audit_project_id}/runs/{audit_run_id}/uploads/{filename}
customers/{customer_id}/audits/{audit_project_id}/runs/{audit_run_id}/artifacts/{artifact_type}/{filename}
```

Every upload returns bucket, key, content type, byte size, and SHA-256 hash so DB rows can reconstruct exactly which source/customer file/report was used.

## Practical Runbook

Use this section when you want to run the Python application and its main features.

### 1. Install Python Dependencies

From the ingestion folder:

```bash
cd /Users/ramesh/Documents/Codex/2026-06-07/https-www-ycombinator-com-companies-here/traceready/ingestion
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

For Codex-local runs, the bundled runtime also works for Supabase operations:

```bash
/Users/ramesh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
```

### 2. Configure Environment

For local API development against the Supabase project:

```bash
export TRACEREADY_ENV=local
export NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
export SUPABASE_DATABASE_URL=postgresql://...
export TRACEREADY_STORAGE_BUCKET=traceready-pilot-private
export TRACEREADY_OBJECT_STORE_MODE=supabase
export TRACEREADY_INTERNAL_API_TOKEN=dev-internal-token
```

For Supabase-backed development or production-like runs:

```bash
export TRACEREADY_ENV=production
export NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
export SUPABASE_DATABASE_URL=postgresql://...
export TRACEREADY_STORAGE_BUCKET=traceready-pilot-private
export TRACEREADY_OBJECT_STORE_MODE=supabase
export TRACEREADY_INTERNAL_API_TOKEN=<internal-token>
export TRACEREADY_REQUIRE_CONFIGURED_DEPENDENCIES=true
```

In the Python app, paste the Supabase connection URL into `ingestion/.env` as:

```text
SUPABASE_DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<host>:<port>/postgres?sslmode=require
```

`SUPABASE_DATABASE_URL` is required for Python worker jobs, regulatory seed/import commands, integrity checks, and reviewer-table writes. There is no Supabase REST fallback in the Python runtime.

### 3. Run The FastAPI App Locally

```bash
.venv/bin/python -m uvicorn traceready_backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

Use the venv Python explicitly. On some machines, plain `uvicorn` resolves to a global Python install and cannot see the ingestion dependencies installed in `.venv`, including the Supabase storage client.

Smoke checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl -H "x-traceready-internal-token: $TRACEREADY_INTERNAL_API_TOKEN" \
  http://127.0.0.1:8000/internal/ping
```

### 4. Process Customer Audit Jobs

The normal customer workflow is:

```text
Next.js upload
-> private object storage
-> audit_project / audit_run / audit_file / audit_job rows
-> Python process-slice
-> parsed workbook rows, evidence, normalized events
-> approved-rule execution job
-> findings, traces, reports, exports
```

Run one bounded processing slice:

```bash
curl -X POST http://127.0.0.1:8000/internal/jobs/audit/process-slice \
  -H "content-type: application/json" \
  -H "x-traceready-internal-token: $TRACEREADY_INTERNAL_API_TOKEN" \
  -d '{
    "worker_id": "local-worker",
    "job_types": ["parse_customer_workbook", "execute_approved_rules"],
    "max_jobs": 1,
    "stale_lock_minutes": 15
  }'
```

Check job status:

```bash
curl -H "x-traceready-internal-token: $TRACEREADY_INTERNAL_API_TOKEN" \
  http://127.0.0.1:8000/internal/jobs/audit/<job_id>
```

Retry a failed/retryable job:

```bash
curl -X POST http://127.0.0.1:8000/internal/jobs/audit/<job_id>/retry \
  -H "content-type: application/json" \
  -H "x-traceready-internal-token: $TRACEREADY_INTERNAL_API_TOKEN" \
  -d '{"requested_by":"local-ops","reason":"Retry after fixing config"}'
```

### 5. Seed Regulatory Source Library

This loads the current local source registry into Supabase tables and private object storage:

```bash
python -m scripts.ops.seed_regulatory_sources \
  --regulatory-dir ../data/regulatory \
  --bucket traceready-pilot-private \
  --source-version 1
```

Expected current result:

```text
source_count: 71
chunk_count: 1440
raw_artifact_count: 71
normalized_artifact_count: 71
chunk_package_count: 71
skipped_sources: []
```

What this seeds:

- raw source snapshots from `data/regulatory/*/raw/*`
- normalized extraction JSON from `data/regulatory/*/normalized/*.json`
- per-source chunk packages
- `regulatory_sources` rows
- `source_chunks` rows

It does not seed benchmark/evaluation workbooks, competitor audit files, or Phase 12/13 web eval outputs.

To seed local Phase 6 draft cards into the DB-backed reviewer queue:

```bash
python -m scripts.ops.seed_regulatory_draft_records \
  --phase6-review-package-file ../data/regulatory/intelligence/review/phase6-review-package.json
```

Expected current local package shape:

```text
package_draft_count: 550
ready_for_review_count: 534
rejected_count: 16
```

Use this when the reviewer UI should show local cards for approval. This command upserts `regulatory_draft_records`; it does not create approved records and does not publish an approved package.

For only approval-ready cards:

```bash
python -m scripts.ops.seed_regulatory_draft_records --only-ready-for-review
```

### 6. Verify Regulatory Source Integrity

After seeding, run:

```bash
python -m scripts.ops.check_source_artifact_integrity \
  --bucket traceready-pilot-private \
  --source-version 1
```

Expected current result:

```text
status: pass
sourceCount: 71
chunkCount: 1440
sourceObjectCount: 71
chunkPackageCount: 71
errorCount: 0
warningCount: 0
issues: []
```

The checker validates:

- every source has URL/hash metadata
- raw and normalized private objects are reachable
- raw artifact SHA-256 matches source hash when the source hash is a raw SHA-256
- every source has a chunk package
- chunk package counts match DB chunk rows
- DB chunk text/hash/citation metadata matches the seeded package
- chunks have citation/citation-anchor coverage

### 7. Regulatory Source Ingestion Job Endpoints

Queue a source-ingestion job:

```bash
curl -X POST http://127.0.0.1:8000/internal/regulatory/source-ingestion-jobs \
  -H "content-type: application/json" \
  -H "x-traceready-internal-token: $TRACEREADY_INTERNAL_API_TOKEN" \
  -d '{
    "source_type": "ecfr",
    "source_url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-S",
    "job_type": "ingest_regulatory_source",
    "created_by": "local-ops"
  }'
```

List jobs:

```bash
curl -H "x-traceready-internal-token: $TRACEREADY_INTERNAL_API_TOKEN" \
  http://127.0.0.1:8000/internal/regulatory/source-ingestion-jobs
```

Check one job:

```bash
curl -H "x-traceready-internal-token: $TRACEREADY_INTERNAL_API_TOKEN" \
  http://127.0.0.1:8000/internal/regulatory/source-ingestion-jobs/<job_id>
```

The job records and events exist now. Full automated source-ingestion job execution should be wired as the next operational increment; the current production-ready source-library path is the explicit seed/import command above.

### 8. Local Intelligence-Only Source Update Flow

Use this flow when adding a new regulatory source or refreshing an existing source before pushing anything to production.

Local intelligence execution does not require DB access. Local JSON artifacts are build artifacts, not production truth.

Recommended flow:

```text
new FDA/eCFR/PDF/XLSX/source URL
-> ingest raw source locally
-> normalize/extract text/tables
-> chunk into citation-safe source chunks
-> rebuild registry
-> dedupe source/chunks/cards
-> validate source health and citation coverage
-> generate or update draft cards
-> validate schema, citations, unsupported claims, and conflicts
-> load draft cards into review tables
-> reviewer approve/edit/reject in the app
-> publish a new immutable approved package version
```

For one-off local source ingestion:

```bash
python -m scripts.ops.ingest \
  --url "<official-source-url>" \
  --source-id "<stable-source-id>" \
  --output-dir ../data/regulatory
```

For local registry and intelligence artifact rebuilds:

```bash
python -m scripts.ops.build_regulatory_registry
python scripts/intelligence/validate_intelligence_schemas.py
python scripts/intelligence/build_phase4_drafts.py
python scripts/intelligence/build_phase5_prompt_pack.py
python scripts/intelligence/run_phase5_safety_checks.py
python scripts/intelligence/build_phase6_review_package.py
python scripts/intelligence/build_phase7_obligation_inventory.py
python scripts/intelligence/build_phase8_scenario_regressions.py
python scripts/intelligence/build_phase9_approved_rule_package.py
```

Run real AI-assisted extraction only when deterministic extraction is insufficient and an API key is configured:

```bash
python scripts/intelligence/run_phase5_anthropic_extraction.py --prompt-cache-ttl 1h
```

Do not push local generated cards directly into approved production records. Push them as draft/review records, then approve/edit/reject through the reviewer UI and publish a new immutable package.

### 9. Deduplication Policy For New Sources And Cards

Deduplication should not rely only on production approved cards. Approved cards are part of the check, but source and chunk identity must be checked first so source-version changes remain auditable.

Deduplication layers:

1. Source-level deduplication:
   - Compare `sourceId`, canonical URL, raw SHA-256 hash, normalized artifact hash, effective date, compliance date, and retrieved date.
   - Same URL and same hash means no source-content change.
   - Same URL and different hash means a new source version.
   - Different URL and same raw hash usually means duplicate content or a mirror.

2. Chunk-level deduplication:
   - Compare source ID/version, section reference, citation anchor, chunk text hash, and normalized chunk text.
   - Identical chunk hashes should not create duplicate executable evidence.
   - Changed chunk hashes should preserve the old version and create new reviewable source context.

3. Draft-card deduplication:
   - Compare semantic keys such as obligation subject/action/object, CTE type, KDE field key, TLC rule kind, exemption condition, traceability-plan component, and sortable export field.
   - Compare citation source/chunk anchors and support spans.
   - If the card meaning is unchanged but citations/source versions changed, create a reviewable update rather than silently overwriting the old card.

4. Production-approved-card deduplication:
   - Compare new draft cards against current approved records and active approved package records.
   - If the new draft matches an approved card exactly, no new approval is needed except source-version metadata refresh when applicable.
   - If the new draft changes meaning, condition, scope, citation, severity, applies-when logic, or executable checks, it must remain a draft until reviewer approval.

Production push rule:

```text
local source/chunk artifacts -> seed/import -> integrity check -> draft review records -> reviewer approval -> immutable approved package
```

Customer audits must read only the active approved package version, never raw local draft cards.

### 10. Run Tests

Focused backend tests:

```bash
python -m unittest \
  tests/test_api_skeleton.py \
  tests/test_backend_repositories.py \
  tests/test_storage_artifacts.py \
  tests/test_regulatory_seed_import_service.py \
  tests/test_source_artifact_integrity_service.py \
  tests/test_audit_job_slice_service.py \
  tests/test_audit_parse_job.py \
  tests/test_normalized_evidence_service.py \
  tests/test_rule_execution_service.py
```

Full test discovery:

```bash
python -m unittest discover -s tests
```

### 11. Deploy On Vercel

The Vercel entrypoint is:

```text
api/index.py
```

Audit jobs are processed by calling (e.g. from the app on upload):

```text
POST /internal/jobs/audit/process-slice
```

Required production env:

```text
TRACEREADY_ENV=production
NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY
SUPABASE_DATABASE_URL
TRACEREADY_STORAGE_BUCKET
TRACEREADY_OBJECT_STORE_MODE=supabase
TRACEREADY_INTERNAL_API_TOKEN
TRACEREADY_ALLOWED_ORIGINS
TRACEREADY_REQUIRE_CONFIGURED_DEPENDENCIES=true
```

Use the smoke checklist in:

```text
../docs/deployment/epy-018-python-vercel-smoke-checklist.md
```

## Install Locally

From this folder:

```bash
cd /Users/ramesh/Documents/Codex/2026-06-07/https-www-ycombinator-com-companies-here/traceready/ingestion
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

If you only want to run tests with the system Python and dependencies are already installed, you can skip the virtual environment.

## Run Tests

Built-in runner:

```bash
python -m unittest discover -s tests
```

If `pytest` is installed:

```bash
python -m pytest
```

The tests validate the current ingestion foundation:

- Section extraction from HTML.
- Legal chunk creation with citation anchors.
- Rejection of weak chunks that contain condition language without an obligation.
- Rule-card and KDE draft schema generation.

## Run HTML Ingestion

Example:

```bash
python -m scripts.ops.ingest \
  --url "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-S" \
  --source-id "ecfr-21-cfr-1-subpart-s" \
  --output-dir "../data/regulatory"
```

This writes:

```text
../data/regulatory/raw/ecfr-21-cfr-1-subpart-s.html
../data/regulatory/normalized/ecfr-21-cfr-1-subpart-s.json
```

The normalized JSON contains:

- `sourceId`
- `url`
- `rawArtifact`
- `rawTextHash`
- `chunks[]`

Each chunk includes:

- `chunk_id`
- `source_id`
- `section_label`
- `section`
- `text`
- `summary`
- `citation`
- `text_hash`
- `anchors[]`

## Run PDF Ingestion

PDF URLs and local PDF files are supported.

```bash
python -m scripts.ops.ingest \
  --url "https://www.fda.gov/media/163132/download?attachment" \
  --source-id "fda-cte-kde" \
  --output-dir "../data/regulatory/fda-cte-kde" \
  --include-traceready-context
```

For local PDFs:

```bash
python -m scripts.ops.ingest \
  --input-file "../data/regulatory/fda-cte-kde/raw/fda-cte-kde.pdf" \
  --url "https://www.fda.gov/media/163132/download?attachment" \
  --source-id "fda-cte-kde" \
  --output-dir "../data/regulatory/fda-cte-kde" \
  --include-traceready-context
```

The extractor uses `pdfplumber`, then `pypdf`, then PyMuPDF/fallback when available.

## Run XLSX Ingestion

XLSX URLs and local XLSX files are supported. Each workbook sheet becomes a source section.

```bash
python -m scripts.ops.ingest \
  --url "https://www.fda.gov/media/179617/download?attachment" \
  --source-id "fda-sortable-spreadsheet-xlsx" \
  --output-dir "../data/regulatory/fda-sortable-spreadsheet-xlsx" \
  --include-traceready-context
```

This is especially important for the FDA electronic sortable spreadsheet because the workbook tabs and columns define the practical export shape TraceReady must support.

## Run Local FDA Document Drop Ingestion

Use this for manually downloaded FDA/CFR/Federal Register PDFs and XLSX files.

```bash
/Users/ramesh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 ingest_local_fda_documents.py \
  --input-dir /Users/ramesh/Downloads/fda-documents \
  --output-dir ../data/regulatory \
  --manifest ../data/regulatory/local-fda-documents-ingestion-manifest.json \
  --include-traceready-context
```

The local batch importer:

- maps known downloaded filenames to stable TraceReady source IDs
- skips exact duplicate files by SHA-256
- uses semantic PDF sectioning for CFR/FDA PDFs
- uses layout-aware column ordering for Federal Register PDFs
- filters Subpart S and Subpart J PDFs to relevant CFR section ranges
- writes a manifest of ingested, skipped, and failed files

Federal Register PDFs require special handling because naive extraction can read across columns and scramble text. The extractor uses word coordinates to read down each column before moving to the next column, then applies legal-heading chunking.

The manifest is written to:

```text
../data/regulatory/local-fda-documents-ingestion-manifest.json
```

## Run eCFR XML Ingestion

For the real FSMA 204 Subpart S rule, prefer the official eCFR API XML over scraping the browser page.

Example after downloading Title 21 Part 1 XML:

```bash
python -m scripts.ops.ingest \
  --input-file /tmp/title-21-part-1-full.xml \
  --url "https://www.ecfr.gov/api/versioner/v1/full/YYYY-MM-DD/title-21.xml?part=1" \
  --source-id "ecfr-21-cfr-1-subpart-s" \
  --output-dir "../data/regulatory" \
  --min-section 1.1300 \
  --max-section 1.1465 \
  --include-traceready-context
```

This extracts the FSMA 204 Subpart S sections from 21 CFR 1.1300 through 21 CFR 1.1465.

The optional `--include-traceready-context` flag adds the FDA FSMA Rules & Guidance mapping:

- direct TraceReady core sources
- guidance sources
- adjacent customer rules
- rules outside the MVP
- ingestion policy for executable vs. support-only sources

## Source Priority

Use official sources first:

1. Current eCFR text for 21 CFR Part 1 Subpart S.
2. FDA Food Traceability List.
3. FDA FSMA 204 FAQ and guidance.
4. Federal Register final rules.
5. Federal Register proposed rules, marked as proposed and not executable for final findings.

Do not treat third-party explainers as regulatory truth. They can help with product research, but not source-backed rule execution.

## Accuracy Rules

The ingestion worker must preserve these controls:

- Every source snapshot gets a hash.
- Every chunk gets a hash.
- Every chunk keeps citation anchors.
- Chunking should follow legal meaning, not arbitrary token length.
- AI-generated drafts must remain drafts.
- Drafts must pass schema validation before they appear in reviewer workflows.
- No draft rule card should become executable without human approval.
- Proposed or non-final source material must not create final customer-facing findings.

## Drafting Model

Current code uses deterministic placeholder drafting:

```text
source chunks -> draft_rule_card(...)
source chunk -> draft_kde_requirement(...)
```

The next version should replace the placeholder drafter with an LLM-backed drafter that outputs the same Pydantic schemas:

- `RuleCardDraft`
- `KdeRequirementDraft`

The model should produce structured drafts only. It should not decide whether a customer is compliant.

## Database Direction

Production writes now use Supabase table repositories under:

```text
traceready_backend.backend.repositories
```

The old `storage/db.py` in-memory store remains local/test-only compatibility and should not be used as production state.

Important production tables include:

```text
regulatory_sources
regulatory_source_versions
source_chunks
source_ingestion_jobs
source_ingestion_job_events
regulatory_draft_records
regulatory_review_actions
approved_regulatory_records
approved_rule_packages
approved_rule_package_records
audit_projects
audit_runs
audit_files
audit_jobs
audit_job_events
parsed_workbook_sheets
parsed_workbook_rows
parsed_workbook_cells
evidence_items
normalized_events
normalized_kde_values
audit_findings
finding_traces
audit_artifacts
customer_review_actions
```

AI writes only to draft tables. Reviewer approval publishes to approved tables.

## Environment Variables

For local artifact-only ingestion, no environment variables are required.

For Supabase runtime support:

```bash
NEXT_PUBLIC_SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_DATABASE_URL=...
TRACEREADY_STORAGE_BUCKET=traceready-pilot-private
TRACEREADY_OBJECT_STORE_MODE=supabase
```

For Anthropic-backed Phase 5 extraction:

```bash
ANTHROPIC_API_KEY=...
TRACEREADY_ANTHROPIC_MODEL=claude-sonnet-4-6
TRACEREADY_ANTHROPIC_CONFLICT_MODEL=claude-opus-4-8
TRACEREADY_ANTHROPIC_MAX_TOKENS=12000
```

Keep service-role keys server-side only. Do not expose them to the Next.js browser client.

Model roles:

```text
Phase 5 extraction drafting: Claude Sonnet, cost-effective structured extraction.
Conflict reasoning/escalation: Claude Opus, deeper reasoning across contradictory records.
Citation span validation: no AI; deterministic source/chunk/support-text matching.
Reviewer summaries: lower-cost model later; not part of executable rule approval.
```

Run setup:

```bash
cd traceready/ingestion
python -m pip install -e .
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env or export it in your shell.
```

Run Phase 5 extraction:

```bash
cd traceready/ingestion
export ANTHROPIC_API_KEY=...
python scripts/intelligence/run_phase5_anthropic_extraction.py --prompt-cache-ttl 1h
```

The runner stores immutable raw responses and validated draft/rejected/conflict outputs under:

```text
traceready/data/regulatory/intelligence/phase5/anthropic-runs/
```

Each run stores human-readable artifacts:

```text
input/<collection>/system-prompt.md
input/<collection>/user-prompt.md
output/<collection>/raw-response.txt
output/<collection>/parsed-json.json
validated/<collection>-validation.json
raw/<collection>-raw-response.json
```

## Recommended Next Build Steps

1. Seed Phase 6 draft review records into `regulatory_draft_records` if the reviewer UI should show the 534 local draft cards that are ready for expert review.
2. Wire full automated regulatory source-ingestion job execution behind `source_ingestion_jobs`.
3. Add release/report publication jobs for final customer-facing audit packages.
4. Add CI checks that run source integrity validation before approved package publication.
5. Add richer PDF/XLSX table extraction where typed KDE/export tables are needed.

6. Connect reviewer console:
   - show source chunks
   - compare drafts to source citations
   - approve / reject / edit rule cards
   - publish approved rules for deterministic audit checks

## How This Connects To The App

The Next.js app should not run heavy ingestion inside customer upload flows.

Use two separate paths:

```text
Regulatory ingestion path:
Python worker -> source chunks -> draft rule cards -> reviewer approval -> approved rules

Customer audit path:
Upload workbook -> normalize events/KDEs/TLCs -> deterministic checks -> findings -> export package
```

The customer never waits for FDA source ingestion during an upload. They only use already-approved rules.

## Enterprise Guardrails

Before using this for pilots:

- Add run IDs to every ingestion execution.
- Store source hashes and artifact paths.
- Store model name and prompt version for every AI draft.
- Require reviewer approval before publishing.
- Keep an append-only review log.
- Add source-change detection before updating approved rules.
- Add golden scenario tests before changing executable rules.

This is the foundation for TraceReady's regulatory intelligence system, not a one-off scraper.
