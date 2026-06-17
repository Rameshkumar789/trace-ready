-- TraceReady regulatory intelligence Phase 6 review workflow.
--
-- This separates extracted draft records from reviewer-approved records.
-- Product audit engines must consume approved records only.

create table if not exists public.regulatory_draft_records (
  id text primary key,
  collection text not null,
  record_id text not null,
  source_phase text not null,
  extraction_method text not null,
  confidence text not null,
  review_status text not null check (
    review_status in ('draft', 'needs_review', 'approved', 'rejected', 'superseded', 'conflict_detected')
  ),
  source_chunk_ids jsonb not null default '[]'::jsonb,
  citation_count integer not null default 0,
  citation_coverage_status text not null,
  schema_valid boolean not null default false,
  citation_valid boolean not null default false,
  validation_errors jsonb not null default '[]'::jsonb,
  reviewer_blockers jsonb not null default '[]'::jsonb,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists regulatory_draft_records_collection_status_idx
  on public.regulatory_draft_records (collection, review_status);

create index if not exists regulatory_draft_records_record_id_idx
  on public.regulatory_draft_records (record_id);

drop trigger if exists set_regulatory_draft_records_updated_at on public.regulatory_draft_records;

create trigger set_regulatory_draft_records_updated_at
before update on public.regulatory_draft_records
for each row
execute function public.set_updated_at();

create table if not exists public.approved_regulatory_records (
  id text primary key,
  draft_record_id text not null references public.regulatory_draft_records(id),
  collection text not null,
  record_id text not null,
  version integer not null,
  approved_by text not null,
  approved_at timestamptz not null default now(),
  approval_reason text not null,
  source_chunk_ids jsonb not null default '[]'::jsonb,
  payload jsonb not null,
  superseded_by_id text references public.approved_regulatory_records(id),
  created_at timestamptz not null default now(),
  unique (collection, record_id, version)
);

create index if not exists approved_regulatory_records_collection_record_idx
  on public.approved_regulatory_records (collection, record_id);

create table if not exists public.regulatory_review_actions (
  id text primary key,
  draft_record_id text references public.regulatory_draft_records(id),
  approved_record_id text references public.approved_regulatory_records(id),
  action text not null,
  actor text not null,
  actor_role text not null,
  reason text not null,
  before_json jsonb,
  after_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists regulatory_review_actions_draft_idx
  on public.regulatory_review_actions (draft_record_id);

create index if not exists regulatory_review_actions_approved_idx
  on public.regulatory_review_actions (approved_record_id);

create index if not exists regulatory_review_actions_action_created_idx
  on public.regulatory_review_actions (action, created_at);

alter table public.regulatory_draft_records enable row level security;
alter table public.approved_regulatory_records enable row level security;
alter table public.regulatory_review_actions enable row level security;

drop policy if exists "Reviewers can read regulatory draft records" on public.regulatory_draft_records;
drop policy if exists "Reviewers can read approved regulatory records" on public.approved_regulatory_records;
drop policy if exists "Reviewers can read regulatory review actions" on public.regulatory_review_actions;

create policy "Reviewers can read regulatory draft records"
on public.regulatory_draft_records
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

create policy "Reviewers can read approved regulatory records"
on public.approved_regulatory_records
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

create policy "Reviewers can read regulatory review actions"
on public.regulatory_review_actions
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

-- Writes are intentionally service-role controlled for Phase 6.
-- The ingestion worker creates draft rows; the Next.js reviewer server actions
-- create approval and action rows after authenticated reviewer checks.
