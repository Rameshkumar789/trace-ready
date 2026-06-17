-- TraceReady normalized customer evidence foundation.
--
-- Run this only after:
-- 001_initial_auth_and_storage.sql
-- 005_enterprise_audit_foundation.sql
--
-- This migration adds first-class normalized customer evidence rows used by
-- Python parsing/normalization jobs and later deterministic approved-rule
-- execution. Writes remain service-role controlled.

do $$
begin
  if to_regclass('public.traceready_profiles') is null then
    raise exception 'Missing dependency: run 001_initial_auth_and_storage.sql before 007_normalized_customer_evidence.sql';
  end if;

  if to_regclass('public.audit_projects') is null
    or to_regclass('public.audit_runs') is null
    or to_regclass('public.audit_files') is null
    or to_regclass('public.evidence_items') is null then
    raise exception 'Missing dependency: run 005_enterprise_audit_foundation.sql before 007_normalized_customer_evidence.sql';
  end if;
end $$;

create table if not exists public.normalized_business_objects (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  object_type text not null,
  object_key text not null,
  name text not null,
  normalized_name text,
  confidence double precision,
  review_status text not null default 'unreviewed',
  attributes_json jsonb,
  evidence_ids_json jsonb,
  created_at timestamptz not null default now(),
  unique (audit_project_id, audit_run_id, object_type, object_key)
);

create index if not exists normalized_business_objects_project_type_idx
  on public.normalized_business_objects (audit_project_id, object_type);

create index if not exists normalized_business_objects_run_type_idx
  on public.normalized_business_objects (audit_run_id, object_type);

create index if not exists normalized_business_objects_review_idx
  on public.normalized_business_objects (review_status, created_at desc);

create table if not exists public.normalized_events (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  audit_file_id text references public.audit_files(id) on delete set null,
  source_row_key text not null,
  event_type_claim text,
  event_datetime timestamptz,
  event_datetime_raw text,
  actor_object_id text references public.normalized_business_objects(id) on delete set null,
  product_object_id text references public.normalized_business_objects(id) on delete set null,
  lot_object_id text references public.normalized_business_objects(id) on delete set null,
  source_lot_object_id text references public.normalized_business_objects(id) on delete set null,
  output_lot_object_id text references public.normalized_business_objects(id) on delete set null,
  from_object_id text references public.normalized_business_objects(id) on delete set null,
  to_object_id text references public.normalized_business_objects(id) on delete set null,
  document_object_id text references public.normalized_business_objects(id) on delete set null,
  destination_type text,
  action_terms_json jsonb,
  classified_ctes_json jsonb,
  suppressed_ctes_json jsonb,
  reviewer_questions_json jsonb,
  confidence double precision,
  review_status text not null default 'unreviewed',
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  unique (audit_project_id, audit_run_id, source_row_key)
);

create index if not exists normalized_events_project_review_idx
  on public.normalized_events (audit_project_id, review_status);

create index if not exists normalized_events_run_review_idx
  on public.normalized_events (audit_run_id, review_status);

create index if not exists normalized_events_file_idx
  on public.normalized_events (audit_file_id);

create table if not exists public.normalized_event_evidence_refs (
  id text primary key default gen_random_uuid()::text,
  normalized_event_id text not null references public.normalized_events(id) on delete cascade,
  evidence_item_id text not null references public.evidence_items(id) on delete cascade,
  role text not null,
  created_at timestamptz not null default now(),
  unique (normalized_event_id, evidence_item_id, role)
);

create index if not exists normalized_event_evidence_refs_evidence_idx
  on public.normalized_event_evidence_refs (evidence_item_id);

create table if not exists public.normalized_kde_values (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  normalized_event_id text references public.normalized_events(id) on delete cascade,
  evidence_item_id text references public.evidence_items(id) on delete set null,
  kde_key text not null,
  kde_label text,
  raw_value text,
  normalized_value text,
  confidence double precision,
  review_status text not null default 'unreviewed',
  metadata_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists normalized_kde_values_project_key_idx
  on public.normalized_kde_values (audit_project_id, kde_key);

create index if not exists normalized_kde_values_run_key_idx
  on public.normalized_kde_values (audit_run_id, kde_key);

create index if not exists normalized_kde_values_event_idx
  on public.normalized_kde_values (normalized_event_id);

create index if not exists normalized_kde_values_evidence_idx
  on public.normalized_kde_values (evidence_item_id);

create index if not exists normalized_kde_values_review_idx
  on public.normalized_kde_values (review_status, created_at desc);

create table if not exists public.tlc_lineage_links (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  normalized_event_id text references public.normalized_events(id) on delete set null,
  source_tlc text,
  output_tlc text,
  link_type text not null,
  confidence double precision,
  review_status text not null default 'unreviewed',
  evidence_ids_json jsonb,
  metadata_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists tlc_lineage_links_project_source_idx
  on public.tlc_lineage_links (audit_project_id, source_tlc);

create index if not exists tlc_lineage_links_project_output_idx
  on public.tlc_lineage_links (audit_project_id, output_tlc);

create index if not exists tlc_lineage_links_run_idx
  on public.tlc_lineage_links (audit_run_id);

create index if not exists tlc_lineage_links_review_idx
  on public.tlc_lineage_links (review_status, created_at desc);

create table if not exists public.normalized_review_items (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  normalized_event_id text references public.normalized_events(id) on delete cascade,
  normalized_kde_value_id text references public.normalized_kde_values(id) on delete cascade,
  business_object_id text references public.normalized_business_objects(id) on delete set null,
  review_type text not null,
  question text not null,
  reason text not null,
  severity text not null,
  status text not null default 'needs_review',
  evidence_ids_json jsonb,
  metadata_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists normalized_review_items_project_status_idx
  on public.normalized_review_items (audit_project_id, status);

create index if not exists normalized_review_items_run_status_idx
  on public.normalized_review_items (audit_run_id, status);

create index if not exists normalized_review_items_event_idx
  on public.normalized_review_items (normalized_event_id);

create index if not exists normalized_review_items_kde_idx
  on public.normalized_review_items (normalized_kde_value_id);

create index if not exists normalized_review_items_object_idx
  on public.normalized_review_items (business_object_id);

alter table public.normalized_business_objects enable row level security;
alter table public.normalized_events enable row level security;
alter table public.normalized_event_evidence_refs enable row level security;
alter table public.normalized_kde_values enable row level security;
alter table public.tlc_lineage_links enable row level security;
alter table public.normalized_review_items enable row level security;

drop policy if exists "TraceReady users can read accessible normalized business objects" on public.normalized_business_objects;
create policy "TraceReady users can read accessible normalized business objects"
on public.normalized_business_objects
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible normalized events" on public.normalized_events;
create policy "TraceReady users can read accessible normalized events"
on public.normalized_events
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible normalized event evidence refs" on public.normalized_event_evidence_refs;
create policy "TraceReady users can read accessible normalized event evidence refs"
on public.normalized_event_evidence_refs
for select
to authenticated
using (
  exists (
    select 1
    from public.normalized_events event
    where event.id = normalized_event_id
      and public.traceready_can_access_audit_project(event.audit_project_id)
  )
);

drop policy if exists "TraceReady users can read accessible normalized KDE values" on public.normalized_kde_values;
create policy "TraceReady users can read accessible normalized KDE values"
on public.normalized_kde_values
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible TLC lineage links" on public.tlc_lineage_links;
create policy "TraceReady users can read accessible TLC lineage links"
on public.tlc_lineage_links
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible normalized review items" on public.normalized_review_items;
create policy "TraceReady users can read accessible normalized review items"
on public.normalized_review_items
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

-- Insert/update/delete remain service-role controlled for this phase.
