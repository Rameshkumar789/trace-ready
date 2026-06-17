-- TraceReady MVP Supabase setup
-- Run this once in Supabase Dashboard -> SQL Editor -> New query.
--
-- What this creates:
-- 1. TraceReady role profiles linked to Supabase Auth users.
-- 2. Role/status constraints for operator, reviewer, and founder admin.
--    New self-service signups should start as invited until email verification.
-- 3. Updated-at trigger.
-- 4. RLS policies so users can read their own profile only.
-- 5. Private storage bucket for uploaded pilot workbooks/artifacts.

create extension if not exists pgcrypto;

create table if not exists public.traceready_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  company_name text,
  role text not null check (role in ('operator', 'fsma_reviewer', 'founder_admin')),
  status text not null default 'invited' check (status in ('active', 'inactive', 'invited')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists traceready_profiles_email_idx
  on public.traceready_profiles (lower(email));

create index if not exists traceready_profiles_role_status_idx
  on public.traceready_profiles (role, status);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_traceready_profiles_updated_at on public.traceready_profiles;

create trigger set_traceready_profiles_updated_at
before update on public.traceready_profiles
for each row
execute function public.set_updated_at();

alter table public.traceready_profiles enable row level security;

drop policy if exists "Users can read their own TraceReady profile" on public.traceready_profiles;

create policy "Users can read their own TraceReady profile"
on public.traceready_profiles
for select
to authenticated
using (auth.uid() = user_id);

-- Do not create public insert/update/delete policies for profiles.
-- The Next.js server uses SUPABASE_SERVICE_ROLE_KEY to create and update
-- role profiles after Supabase Auth creates the user.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'traceready-pilot-private',
  'traceready-pilot-private',
  false,
  52428800,
  array[
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'application/pdf',
    'application/json',
    'text/csv',
    'text/plain'
  ]
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Storage access is intentionally service-role only for the MVP.
-- Uploaded workbooks and audit artifacts contain sensitive supply-chain data.
-- The app writes/reads objects from the server using SUPABASE_SERVICE_ROLE_KEY.

-- Optional seed after creating your own Supabase Auth user:
-- Replace USER_UUID_FROM_AUTH_USERS with the id from Authentication -> Users.
-- Use founder_admin + active for your own initial admin account.
--
-- insert into public.traceready_profiles
--   (user_id, email, full_name, company_name, role, status)
-- values
--   ('USER_UUID_FROM_AUTH_USERS', 'you@company.com', 'Your Name', 'Your Company', 'founder_admin', 'active')
-- on conflict (user_id) do update set
--   email = excluded.email,
--   full_name = excluded.full_name,
--   company_name = excluded.company_name,
--   role = excluded.role,
--   status = excluded.status,
--   updated_at = now();
