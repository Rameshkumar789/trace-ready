# TraceReady Pilot Deployment

The pilot app is designed for a Vercel-first deployment with managed Postgres and private object storage.

The production shape is:

- Next.js app on Vercel.
- Python FastAPI/job-slice endpoints on Vercel Python runtime.
- Supabase Postgres as the source of truth.
- Supabase Storage or equivalent private object storage for workbooks, source snapshots, and generated reports.
- Vercel Cron or explicit internal calls to process bounded job slices.

Python should not run as an always-on in-memory worker on Vercel. Long work must be persisted as database jobs and processed in resumable slices.

## Required Environment

- `NEXT_PUBLIC_APP_URL`
- `TRACEREADY_AUTH_MODE`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_PRIVATE_BUCKET`
- `DATABASE_URL`
- `OPENAI_API_KEY`

## Pilot Rules

- Do not store customer workbooks in public buckets.
- Do not expose uploaded values in logs.
- Run audits in draft mode until rule cards, KDE requirements, scenario coverage, evidence mappings, and human review pass the readiness gate.
- Customer reports must say `readiness audit`; they must not say `certified compliant`.
- Use `TRACEREADY_AUTH_MODE=local` only for local development.
- In production, connect Supabase Auth and private storage before accepting real customer files.

## Initial Deploy Path

1. Install dependencies in `app`.
2. Run `npm test`.
3. Run `npm run build`.
4. Configure private storage and auth.
5. Deploy the Next.js app to Vercel.
6. Deploy Python FastAPI endpoints to Vercel as a colocated service/function boundary.
7. Configure Vercel Cron or internal trigger routes for audit and regulatory job slices.
8. Smoke test `/upload`, `/audits/demo`, `/audits/demo/review`, `/audits/demo/report`, `/admin/regulatory/coverage`, Python `/health`, and Python `/ready`.

## Current MVP Persistence

The current implementation stores local development audit JSON under `app/storage/audits/{auditId}/audit.json`.

Before production pilots:

1. Replace local audit storage with managed Postgres rows.
2. Store original workbooks and generated artifacts in a private bucket.
3. Enable Supabase Auth for protected routes.
4. Configure backup/export for pilot data.
5. Store job checkpoints, parse results, findings, review actions, and report metadata in Postgres.
