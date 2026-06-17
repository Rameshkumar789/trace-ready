# TraceReady Audit App

Pilot implementation for the full FSMA 204 regulatory-intelligence audit task list.

## Commands

- `npm run dev`
- `npm test`
- `npm run typecheck`
- `npm run build`
- `npm audit --omit=dev`

## Pilot Flow

1. Sign in from `/login/operator` or `/login/reviewer`.
2. Operators open `/operator`; reviewers open `/reviewer`.
3. Operators upload `../data/samples/fsma204-full-audit-sample.xlsx`.
4. Review the generated audit workspace.
5. Open review and report pages.
6. Download the draft artifact package.

## Supabase Auth

TraceReady uses Supabase email/password Auth only. There is no local-auth fallback.

Required environment variables:

```bash
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
TRACEREADY_AUTH_SECRET=at-least-32-random-characters
```

Run this SQL migration after creating the Supabase project:

[`supabase/migrations/001_initial_auth_and_storage.sql`](./supabase/migrations/001_initial_auth_and_storage.sql)

If you already ran the first migration before the email-verification lifecycle was added, also run:

[`supabase/migrations/002_profile_email_verification_lifecycle.sql`](./supabase/migrations/002_profile_email_verification_lifecycle.sql)

Supabase Dashboard steps:

1. Open your Supabase project.
2. Go to SQL Editor.
3. Create a new query.
4. Paste the contents of `supabase/migrations/001_initial_auth_and_storage.sql`.
5. Run it.
6. Go to Authentication -> Providers -> Email and make sure email/password sign-in is enabled.
7. Copy the project URL, publishable key, and service role key into `.env.local`.

For each invited Supabase user, add one profile row:

```sql
insert into public.traceready_profiles (user_id, email, full_name, company_name, role, status)
values ('USER_UUID_FROM_AUTH_USERS', 'name@company.com', 'Full Name', 'Company Name', 'operator', 'active');
```

Use `fsma_reviewer` for consultants/rule reviewers and `founder_admin` when one account needs both workspaces.

Signup lifecycle:

1. Supabase creates the Auth user.
2. TraceReady creates `public.traceready_profiles.status = 'invited'`.
3. User verifies email through Supabase.
4. First verified password login activates the profile.
5. TraceReady creates the signed HTTP-only app session and redirects to the correct workspace.

Self-service signup pages:

- `/signup/operator`
- `/signup/reviewer`

Login pages:

- `/login/operator`
- `/login/reviewer`

## Pilot Audit Flow

1. Open `/upload`.
2. Upload `../data/samples/fsma204-full-audit-sample.xlsx`.
3. Review the generated audit workspace.
4. Open review and report pages.
5. Download the draft artifact package.

## Security Boundary

Supabase validates identity. TraceReady reads `public.traceready_profiles` to decide whether the user is an operator, FSMA reviewer, or founder admin. The app then creates a short-lived, signed, HTTP-only session cookie for server-rendered route protection.

Uploaded files are parsed server-side and audit results are stored locally under `storage/audits` in development. Production deployment should use private object storage and database persistence.
