-- TraceReady regulatory intelligence Phase 7 obligation inventory.
--
-- Stores linked, confidence-scored obligation inventory records and immutable
-- approved obligation packages. Product audit engines should consume approved
-- obligation packages, not draft extraction records.

create table if not exists public.obligation_inventory_records (
  id text primary key,
  obligation_id text not null,
  review_status text not null check (
    review_status in ('draft', 'needs_review', 'approved', 'rejected', 'superseded', 'conflict_detected')
  ),
  confidence_score numeric(4, 2) not null,
  confidence_level text not null check (confidence_level in ('high', 'medium', 'low', 'unsupported', 'conflict')),
  approval_ready boolean not null default false,
  obligation jsonb not null,
  links jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists obligation_inventory_records_obligation_idx
  on public.obligation_inventory_records (obligation_id);

create index if not exists obligation_inventory_records_status_ready_idx
  on public.obligation_inventory_records (review_status, approval_ready);

drop trigger if exists set_obligation_inventory_records_updated_at on public.obligation_inventory_records;

create trigger set_obligation_inventory_records_updated_at
before update on public.obligation_inventory_records
for each row
execute function public.set_updated_at();

create table if not exists public.approved_obligation_sets (
  id text primary key,
  version integer not null unique,
  status text not null check (status in ('approved', 'superseded', 'rolled_back')),
  approved_at timestamptz not null,
  approved_by text not null,
  approval_role text not null,
  approval_reason text not null,
  immutable boolean not null default true,
  source_review_package text not null,
  records jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists approved_obligation_sets_status_approved_idx
  on public.approved_obligation_sets (status, approved_at);

alter table public.obligation_inventory_records enable row level security;
alter table public.approved_obligation_sets enable row level security;

drop policy if exists "Reviewers can read obligation inventory records" on public.obligation_inventory_records;
drop policy if exists "Reviewers can read approved obligation sets" on public.approved_obligation_sets;

create policy "Reviewers can read obligation inventory records"
on public.obligation_inventory_records
for select
to authenticated
using (
  exists (
    select 1 from public.traceready_profiles profile
    where profile.user_id = auth.uid()
      and profile.status = 'active'
      and profile.role in ('fsma_reviewer', 'founder_admin')
  )
);

create policy "Reviewers can read approved obligation sets"
on public.approved_obligation_sets
for select
to authenticated
using (
  exists (
    select 1 from public.traceready_profiles profile
    where profile.user_id = auth.uid()
      and profile.status = 'active'
      and profile.role in ('fsma_reviewer', 'founder_admin')
  )
);

-- Writes remain service-role controlled. The ingestion worker imports
-- inventory records; reviewer server actions publish immutable approved sets.
