-- TraceReady profile lifecycle update
-- Run this if 001_initial_auth_and_storage.sql was already applied before
-- the email-verification lifecycle was added.

alter table public.traceready_profiles
  alter column status set default 'invited';

-- Optional: mark existing unreviewed active self-service test users as invited
-- if they should not have app access before email verification.
--
-- update public.traceready_profiles
-- set status = 'invited', updated_at = now()
-- where status = 'active'
--   and role in ('operator', 'fsma_reviewer')
--   and email not in ('YOUR_CONFIRMED_ADMIN_EMAIL');
