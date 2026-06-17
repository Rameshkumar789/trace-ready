# EPY-018 Python Vercel Deployment Smoke Checklist

## Required Environment

- `TRACEREADY_ENV=production`
- `DATABASE_URL` or `POSTGRES_URL`
- `SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TRACEREADY_STORAGE_BUCKET`
- `TRACEREADY_OBJECT_STORE_MODE=supabase`
- `TRACEREADY_INTERNAL_API_TOKEN`
- `TRACEREADY_ALLOWED_ORIGINS`
- `TRACEREADY_REQUIRE_CONFIGURED_DEPENDENCIES=true`

## Smoke Steps

1. `GET /health` returns `status: ok`.
2. `GET /ready` returns `status: ready`.
3. `GET /internal/ping` rejects without the internal token.
4. `GET /internal/ping` succeeds with `Authorization: Bearer <token>`.
5. Upload a workbook from Next.js and confirm an `audit_jobs` row is queued.
6. `POST /internal/jobs/audit/slice` with the internal token claims at most the requested `max_jobs`.
7. Confirm `audit_job_events` contains `job_claimed`.
8. Confirm `/audits/[auditId]/status` shows the claimed job/event stream.
9. Confirm generated artifacts download from object storage after the worker completes.
