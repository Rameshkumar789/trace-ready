-- TraceReady enterprise audit foundation.
--
-- This migration moves customer audit state toward durable Postgres rows.
-- It does not remove local demo fixtures. Production writes are intentionally
-- service-role controlled until route-level repositories and job handlers are
-- wired.

create table if not exists public.customers (
  id text primary key,
  name text not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists customers_status_idx
  on public.customers (status);

create table if not exists public.customer_sites (
  id text primary key,
  customer_id text not null references public.customers(id) on delete cascade,
  name text not null,
  site_type text,
  address_json jsonb,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists customer_sites_customer_status_idx
  on public.customer_sites (customer_id, status);

create table if not exists public.customer_memberships (
  id text primary key default gen_random_uuid()::text,
  customer_id text not null references public.customers(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (customer_id, user_id)
);

create index if not exists customer_memberships_user_status_idx
  on public.customer_memberships (user_id, status);

create table if not exists public.audit_projects (
  id text primary key,
  customer_id text references public.customers(id),
  customer_name text,
  file_name text not null,
  mode text not null default 'draft',
  status text not null,
  created_by_user_id uuid references auth.users(id),
  raw_workbook_key text,
  dataset_json jsonb,
  parse_errors jsonb,
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists audit_projects_customer_created_idx
  on public.audit_projects (customer_id, created_at desc);

create index if not exists audit_projects_status_created_idx
  on public.audit_projects (status, created_at desc);

create table if not exists public.audit_runs (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  run_number integer not null,
  status text not null,
  mode text not null default 'draft',
  parser_version text,
  classifier_version text,
  rule_package_id text,
  rule_package_version integer,
  rule_package_hash text,
  model_policy_json jsonb,
  summary_json jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (audit_project_id, run_number)
);

create index if not exists audit_runs_project_status_idx
  on public.audit_runs (audit_project_id, status);

create index if not exists audit_runs_rule_package_idx
  on public.audit_runs (rule_package_id, rule_package_version);

create table if not exists public.audit_files (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  file_name text not null,
  file_type text not null,
  content_type text,
  storage_bucket text not null,
  storage_key text not null,
  file_hash text,
  size_bytes integer,
  uploaded_by_user_id uuid references auth.users(id),
  uploaded_at timestamptz not null default now(),
  status text not null default 'uploaded',
  metadata_json jsonb
);

create index if not exists audit_files_project_uploaded_idx
  on public.audit_files (audit_project_id, uploaded_at desc);

create index if not exists audit_files_run_idx
  on public.audit_files (audit_run_id);

create index if not exists audit_files_storage_idx
  on public.audit_files (storage_bucket, storage_key);

create table if not exists public.audit_jobs (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  audit_file_id text references public.audit_files(id) on delete set null,
  job_type text not null,
  status text not null,
  priority integer not null default 100,
  attempt_count integer not null default 0,
  max_attempts integer not null default 3,
  locked_by text,
  locked_at timestamptz,
  available_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  failure_category text,
  error_json jsonb,
  checkpoint_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists audit_jobs_status_claim_idx
  on public.audit_jobs (status, available_at, priority);

create index if not exists audit_jobs_project_created_idx
  on public.audit_jobs (audit_project_id, created_at desc);

create index if not exists audit_jobs_run_idx
  on public.audit_jobs (audit_run_id);

create table if not exists public.audit_job_events (
  id text primary key default gen_random_uuid()::text,
  audit_job_id text not null references public.audit_jobs(id) on delete cascade,
  audit_project_id text references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  event_type text not null,
  message text,
  payload_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_job_events_job_created_idx
  on public.audit_job_events (audit_job_id, created_at);

create index if not exists audit_job_events_project_created_idx
  on public.audit_job_events (audit_project_id, created_at);

create index if not exists audit_job_events_run_created_idx
  on public.audit_job_events (audit_run_id, created_at);

create table if not exists public.audit_artifacts (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  artifact_type text not null,
  file_name text not null,
  content_type text not null,
  storage_bucket text not null,
  storage_key text not null,
  size_bytes integer,
  artifact_hash text,
  status text not null default 'available',
  metadata_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_artifacts_project_type_idx
  on public.audit_artifacts (audit_project_id, artifact_type);

create index if not exists audit_artifacts_run_type_idx
  on public.audit_artifacts (audit_run_id, artifact_type);

create index if not exists audit_artifacts_storage_idx
  on public.audit_artifacts (storage_bucket, storage_key);

create table if not exists public.evidence_items (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  audit_file_id text references public.audit_files(id) on delete set null,
  evidence_type text not null,
  canonical_field text,
  source_sheet text,
  source_row_number integer,
  source_column text,
  raw_value text,
  normalized_value text,
  confidence double precision,
  review_status text not null default 'unreviewed',
  metadata_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists evidence_items_project_field_idx
  on public.evidence_items (audit_project_id, canonical_field);

create index if not exists evidence_items_run_idx
  on public.evidence_items (audit_run_id);

create index if not exists evidence_items_file_idx
  on public.evidence_items (audit_file_id);

create table if not exists public.audit_findings (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  title text not null,
  status text not null,
  severity text not null,
  finding_type text not null,
  event_id text,
  event_line_id text,
  field_or_kde text,
  observed_value text,
  expected_or_required text,
  recommendation text not null,
  rule_card_id text,
  rule_card_version integer,
  approved_record_id text,
  approved_obligation_id text,
  source_chunk_id text,
  kde_requirement_id text,
  rule_package_id text,
  rule_package_version integer,
  check_code text,
  check_version text,
  evidence_refs_json jsonb,
  metadata_json jsonb,
  review_state text not null,
  created_at timestamptz not null default now()
);

create index if not exists audit_findings_project_status_idx
  on public.audit_findings (audit_project_id, status);

create index if not exists audit_findings_run_status_idx
  on public.audit_findings (audit_run_id, status);

create index if not exists audit_findings_review_created_idx
  on public.audit_findings (review_state, created_at desc);

create index if not exists audit_findings_rule_package_idx
  on public.audit_findings (rule_package_id, rule_package_version);

create table if not exists public.finding_evidence_refs (
  id text primary key default gen_random_uuid()::text,
  finding_id text not null references public.audit_findings(id) on delete cascade,
  evidence_item_id text not null references public.evidence_items(id) on delete cascade,
  role text not null,
  created_at timestamptz not null default now(),
  unique (finding_id, evidence_item_id, role)
);

create index if not exists finding_evidence_refs_evidence_idx
  on public.finding_evidence_refs (evidence_item_id);

create table if not exists public.finding_traces (
  id text primary key default gen_random_uuid()::text,
  finding_id text not null references public.audit_findings(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  sequence integer not null,
  trace_type text not null,
  title text not null,
  payload_json jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists finding_traces_finding_sequence_idx
  on public.finding_traces (finding_id, sequence);

create index if not exists finding_traces_run_idx
  on public.finding_traces (audit_run_id);

create table if not exists public.customer_review_actions (
  id text primary key default gen_random_uuid()::text,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  finding_id text references public.audit_findings(id) on delete set null,
  action text not null,
  actor_user_id uuid references auth.users(id),
  actor_email text,
  actor_role text not null,
  reason text not null,
  comment text,
  before_json jsonb,
  after_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists customer_review_actions_project_created_idx
  on public.customer_review_actions (audit_project_id, created_at desc);

create index if not exists customer_review_actions_run_created_idx
  on public.customer_review_actions (audit_run_id, created_at desc);

create index if not exists customer_review_actions_finding_created_idx
  on public.customer_review_actions (finding_id, created_at desc);

create index if not exists customer_review_actions_action_created_idx
  on public.customer_review_actions (action, created_at desc);

create table if not exists public.audit_logs (
  id text primary key default gen_random_uuid()::text,
  audit_project_id text references public.audit_projects(id) on delete set null,
  actor text not null,
  action text not null,
  before_json jsonb,
  after_json jsonb,
  reason text,
  created_at timestamptz not null default now()
);

create index if not exists audit_logs_project_created_idx
  on public.audit_logs (audit_project_id, created_at desc);

create index if not exists audit_logs_action_created_idx
  on public.audit_logs (action, created_at desc);

drop trigger if exists set_customers_updated_at on public.customers;
create trigger set_customers_updated_at
before update on public.customers
for each row execute function public.set_updated_at();

drop trigger if exists set_customer_sites_updated_at on public.customer_sites;
create trigger set_customer_sites_updated_at
before update on public.customer_sites
for each row execute function public.set_updated_at();

drop trigger if exists set_customer_memberships_updated_at on public.customer_memberships;
create trigger set_customer_memberships_updated_at
before update on public.customer_memberships
for each row execute function public.set_updated_at();

drop trigger if exists set_audit_projects_updated_at on public.audit_projects;
create trigger set_audit_projects_updated_at
before update on public.audit_projects
for each row execute function public.set_updated_at();

drop trigger if exists set_audit_runs_updated_at on public.audit_runs;
create trigger set_audit_runs_updated_at
before update on public.audit_runs
for each row execute function public.set_updated_at();

drop trigger if exists set_audit_jobs_updated_at on public.audit_jobs;
create trigger set_audit_jobs_updated_at
before update on public.audit_jobs
for each row execute function public.set_updated_at();

create or replace function public.traceready_is_reviewer_or_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.traceready_profiles profile
    where profile.user_id = auth.uid()
      and profile.status = 'active'
      and profile.role in ('fsma_reviewer', 'founder_admin')
  );
$$;

create or replace function public.traceready_can_access_customer(target_customer_id text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.traceready_is_reviewer_or_admin()
    or exists (
      select 1
      from public.customer_memberships membership
      join public.traceready_profiles profile
        on profile.user_id = membership.user_id
      where membership.customer_id = target_customer_id
        and membership.user_id = auth.uid()
        and membership.status = 'active'
        and profile.status = 'active'
    );
$$;

create or replace function public.traceready_can_access_audit_project(target_audit_project_id text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.audit_projects project
    where project.id = target_audit_project_id
      and public.traceready_can_access_customer(project.customer_id)
  );
$$;

alter table public.customers enable row level security;
alter table public.customer_sites enable row level security;
alter table public.customer_memberships enable row level security;
alter table public.audit_projects enable row level security;
alter table public.audit_runs enable row level security;
alter table public.audit_files enable row level security;
alter table public.audit_jobs enable row level security;
alter table public.audit_job_events enable row level security;
alter table public.audit_artifacts enable row level security;
alter table public.evidence_items enable row level security;
alter table public.audit_findings enable row level security;
alter table public.finding_evidence_refs enable row level security;
alter table public.finding_traces enable row level security;
alter table public.customer_review_actions enable row level security;
alter table public.audit_logs enable row level security;

drop policy if exists "TraceReady users can read accessible customers" on public.customers;
create policy "TraceReady users can read accessible customers"
on public.customers
for select
to authenticated
using (public.traceready_can_access_customer(id));

drop policy if exists "TraceReady users can read accessible customer sites" on public.customer_sites;
create policy "TraceReady users can read accessible customer sites"
on public.customer_sites
for select
to authenticated
using (public.traceready_can_access_customer(customer_id));

drop policy if exists "TraceReady users can read accessible memberships" on public.customer_memberships;
create policy "TraceReady users can read accessible memberships"
on public.customer_memberships
for select
to authenticated
using (
  public.traceready_is_reviewer_or_admin()
  or user_id = auth.uid()
  or public.traceready_can_access_customer(customer_id)
);

drop policy if exists "TraceReady users can read accessible audit projects" on public.audit_projects;
create policy "TraceReady users can read accessible audit projects"
on public.audit_projects
for select
to authenticated
using (public.traceready_can_access_customer(customer_id));

drop policy if exists "TraceReady users can read accessible audit runs" on public.audit_runs;
create policy "TraceReady users can read accessible audit runs"
on public.audit_runs
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible audit files" on public.audit_files;
create policy "TraceReady users can read accessible audit files"
on public.audit_files
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible audit jobs" on public.audit_jobs;
create policy "TraceReady users can read accessible audit jobs"
on public.audit_jobs
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible audit job events" on public.audit_job_events;
create policy "TraceReady users can read accessible audit job events"
on public.audit_job_events
for select
to authenticated
using (
  public.traceready_can_access_audit_project(audit_project_id)
  or exists (
    select 1 from public.audit_jobs job
    where job.id = audit_job_id
      and public.traceready_can_access_audit_project(job.audit_project_id)
  )
);

drop policy if exists "TraceReady users can read accessible audit artifacts" on public.audit_artifacts;
create policy "TraceReady users can read accessible audit artifacts"
on public.audit_artifacts
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible evidence items" on public.evidence_items;
create policy "TraceReady users can read accessible evidence items"
on public.evidence_items
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible audit findings" on public.audit_findings;
create policy "TraceReady users can read accessible audit findings"
on public.audit_findings
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible finding evidence refs" on public.finding_evidence_refs;
create policy "TraceReady users can read accessible finding evidence refs"
on public.finding_evidence_refs
for select
to authenticated
using (
  exists (
    select 1 from public.audit_findings finding
    where finding.id = finding_id
      and public.traceready_can_access_audit_project(finding.audit_project_id)
  )
);

drop policy if exists "TraceReady users can read accessible finding traces" on public.finding_traces;
create policy "TraceReady users can read accessible finding traces"
on public.finding_traces
for select
to authenticated
using (
  exists (
    select 1 from public.audit_findings finding
    where finding.id = finding_id
      and public.traceready_can_access_audit_project(finding.audit_project_id)
  )
);

drop policy if exists "TraceReady users can read accessible customer review actions" on public.customer_review_actions;
create policy "TraceReady users can read accessible customer review actions"
on public.customer_review_actions
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible audit logs" on public.audit_logs;
create policy "TraceReady users can read accessible audit logs"
on public.audit_logs
for select
to authenticated
using (
  audit_project_id is null
  or public.traceready_can_access_audit_project(audit_project_id)
);

-- Insert/update/delete remain service-role controlled for this phase.
