-- TraceReady regulatory source and approved package foundation.
--
-- Run this only after these prerequisite migrations succeed:
-- 001_initial_auth_and_storage.sql
-- 003_regulatory_intelligence_review.sql
-- 004_obligation_inventory.sql
-- 005_enterprise_audit_foundation.sql
-- This migration turns regulatory sources/chunks/package publication into
-- first-class database records. Writes remain service-role controlled until
-- reviewer/admin mutations are wired through server actions.

do $$
begin
  if to_regclass('public.traceready_profiles') is null then
    raise exception 'Missing dependency: run 001_initial_auth_and_storage.sql before 006_regulatory_source_foundation.sql';
  end if;

  if to_regclass('public.regulatory_draft_records') is null
    or to_regclass('public.approved_regulatory_records') is null
    or to_regclass('public.regulatory_review_actions') is null then
    raise exception 'Missing dependency: run 003_regulatory_intelligence_review.sql before 006_regulatory_source_foundation.sql';
  end if;

  if to_regclass('public.obligation_inventory_records') is null
    or to_regclass('public.approved_obligation_sets') is null then
    raise exception 'Missing dependency: run 004_obligation_inventory.sql before 006_regulatory_source_foundation.sql';
  end if;
end $$;

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

create table if not exists public.regulatory_sources (
  id text primary key,
  title text not null,
  source_type text not null,
  source_status text not null,
  authority_rank text not null,
  url text not null,
  citation text not null,
  published_date timestamptz,
  effective_date timestamptz,
  compliance_date timestamptz,
  is_finalized boolean not null default false,
  retrieved_at timestamptz not null,
  text_hash text not null,
  raw_artifact_bucket text,
  raw_artifact_key text,
  normalized_artifact_bucket text,
  normalized_artifact_key text,
  summary text,
  notes text
);

create index if not exists regulatory_sources_type_status_idx
  on public.regulatory_sources (source_type, source_status);

create index if not exists regulatory_sources_authority_idx
  on public.regulatory_sources (authority_rank);

create table if not exists public.regulatory_source_versions (
  id text primary key,
  regulatory_source_id text not null references public.regulatory_sources(id) on delete cascade,
  version integer not null,
  source_url text not null,
  retrieved_at timestamptz not null,
  effective_date timestamptz,
  compliance_date timestamptz,
  raw_hash text,
  normalized_hash text,
  raw_artifact_bucket text,
  raw_artifact_key text,
  normalized_artifact_bucket text,
  normalized_artifact_key text,
  status text not null,
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  unique (regulatory_source_id, version)
);

create index if not exists regulatory_source_versions_source_retrieved_idx
  on public.regulatory_source_versions (regulatory_source_id, retrieved_at desc);

create table if not exists public.source_chunks (
  id text primary key,
  regulatory_source_id text not null references public.regulatory_sources(id) on delete cascade,
  source_version_id text references public.regulatory_source_versions(id) on delete set null,
  chunk_code text not null unique,
  section_label text not null,
  source_location text not null,
  section_ref text,
  page_number integer,
  text text not null,
  summary text not null,
  citation text not null,
  citation_anchor text,
  text_hash text not null,
  authority_rank text,
  source_url text,
  source_type text,
  raw_artifact_bucket text,
  raw_artifact_key text,
  normalized_artifact_bucket text,
  normalized_artifact_key text,
  status text not null,
  usage_role text not null default 'extraction',
  quality_flags_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists source_chunks_source_status_idx
  on public.source_chunks (regulatory_source_id, status);

create index if not exists source_chunks_source_version_idx
  on public.source_chunks (source_version_id);

create index if not exists source_chunks_citation_idx
  on public.source_chunks (citation);

drop trigger if exists set_source_chunks_updated_at on public.source_chunks;
create trigger set_source_chunks_updated_at
before update on public.source_chunks
for each row execute function public.set_updated_at();

create table if not exists public.source_ingestion_jobs (
  id text primary key,
  regulatory_source_id text references public.regulatory_sources(id) on delete set null,
  source_url text,
  source_type text not null,
  job_type text not null,
  status text not null,
  attempt_count integer not null default 0,
  max_attempts integer not null default 3,
  locked_by text,
  locked_at timestamptz,
  available_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  error_json jsonb,
  checkpoint_json jsonb,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists source_ingestion_jobs_status_available_idx
  on public.source_ingestion_jobs (status, available_at);

create index if not exists source_ingestion_jobs_source_created_idx
  on public.source_ingestion_jobs (regulatory_source_id, created_at desc);

drop trigger if exists set_source_ingestion_jobs_updated_at on public.source_ingestion_jobs;
create trigger set_source_ingestion_jobs_updated_at
before update on public.source_ingestion_jobs
for each row execute function public.set_updated_at();

create table if not exists public.source_ingestion_job_events (
  id text primary key default gen_random_uuid()::text,
  job_id text not null references public.source_ingestion_jobs(id) on delete cascade,
  event_type text not null,
  message text,
  payload_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists source_ingestion_job_events_job_created_idx
  on public.source_ingestion_job_events (job_id, created_at);

create table if not exists public.rule_cards (
  id text primary key,
  rule_code text not null unique,
  title text not null,
  rule_area text not null,
  cte_type text,
  decision_question text not null,
  authority_rank integer not null,
  is_finalized_source boolean not null default false,
  effective_date timestamptz,
  compliance_date timestamptz,
  conditions_json jsonb not null,
  logic_key text not null,
  allowed_states_json jsonb not null,
  status text not null,
  reviewed_by text,
  reviewed_at timestamptz,
  version integer not null,
  regulatory_source_id text references public.regulatory_sources(id) on delete set null
);

create index if not exists rule_cards_status_area_idx
  on public.rule_cards (status, rule_area);

create table if not exists public.rule_card_sources (
  id text primary key default gen_random_uuid()::text,
  rule_card_id text not null references public.rule_cards(id) on delete cascade,
  source_chunk_id text not null references public.source_chunks(id) on delete cascade,
  relevance_note text,
  unique (rule_card_id, source_chunk_id)
);

create table if not exists public.rule_card_reviews (
  id text primary key default gen_random_uuid()::text,
  rule_card_id text not null references public.rule_cards(id) on delete cascade,
  reviewer text not null,
  status_before text not null,
  status_after text not null,
  review_decision text not null,
  notes text not null,
  created_at timestamptz not null default now()
);

create index if not exists rule_card_reviews_rule_created_idx
  on public.rule_card_reviews (rule_card_id, created_at);

create table if not exists public.rule_card_versions (
  id text primary key default gen_random_uuid()::text,
  rule_card_id text not null references public.rule_cards(id) on delete cascade,
  version integer not null,
  snapshot_json jsonb not null,
  change_reason text not null,
  changed_by text not null,
  created_at timestamptz not null default now(),
  unique (rule_card_id, version)
);

create table if not exists public.kde_requirements (
  id text primary key,
  cte_type text not null,
  kde_name text not null,
  field_key text not null,
  required_status text not null,
  applies_when text not null,
  product_scope text,
  source_chunk_id text not null references public.source_chunks(id) on delete restrict,
  rule_card_id text not null references public.rule_cards(id) on delete cascade,
  example_value text,
  severity_if_missing text not null,
  status text not null,
  reviewed_by text,
  reviewed_at timestamptz,
  version integer not null
);

create index if not exists kde_requirements_cte_status_idx
  on public.kde_requirements (cte_type, status);

create index if not exists kde_requirements_rule_idx
  on public.kde_requirements (rule_card_id);

create index if not exists kde_requirements_chunk_idx
  on public.kde_requirements (source_chunk_id);

create table if not exists public.scenario_cases (
  id text primary key,
  name text not null,
  scenario_group text not null,
  source_citations_json jsonb not null,
  linked_rule_card_ids_json jsonb not null,
  evidence_fixture_json jsonb not null,
  expected_findings_json jsonb not null,
  expected_status text not null,
  requires_expert_review boolean not null default false,
  status text not null,
  created_at timestamptz not null default now()
);

create index if not exists scenario_cases_group_status_idx
  on public.scenario_cases (scenario_group, status);

create table if not exists public.approved_rule_packages (
  id text primary key,
  package_id text not null,
  version integer not null,
  status text not null,
  immutable boolean not null default true,
  package_hash text not null,
  generated_at timestamptz not null,
  approved_at timestamptz not null,
  approved_by text not null,
  approval_role text not null,
  approval_reason text not null,
  approved_obligation_set_id text references public.approved_obligation_sets(id) on delete set null,
  scenario_gate_status text,
  source_versions jsonb,
  rollback jsonb,
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  unique (package_id, version)
);

create index if not exists approved_rule_packages_status_approved_idx
  on public.approved_rule_packages (status, approved_at);

create index if not exists approved_rule_packages_hash_idx
  on public.approved_rule_packages (package_hash);

create table if not exists public.approved_rule_package_records (
  id text primary key default gen_random_uuid()::text,
  approved_rule_package_id text not null references public.approved_rule_packages(id) on delete cascade,
  collection text not null,
  record_id text not null,
  record_version integer,
  approved_regulatory_record_id text references public.approved_regulatory_records(id) on delete set null,
  payload jsonb not null,
  source_chunk_ids jsonb,
  record_hash text,
  created_at timestamptz not null default now(),
  unique (approved_rule_package_id, collection, record_id, record_version)
);

create index if not exists approved_rule_package_records_collection_record_idx
  on public.approved_rule_package_records (collection, record_id);

create table if not exists public.scenario_regression_runs (
  id text primary key,
  approved_rule_package_id text references public.approved_rule_packages(id) on delete set null,
  run_type text not null,
  status text not null,
  benchmark_count integer not null,
  pass_count integer not null,
  fail_count integer not null,
  result_hash text,
  summary_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists scenario_regression_runs_package_status_idx
  on public.scenario_regression_runs (approved_rule_package_id, status);

create index if not exists scenario_regression_runs_type_created_idx
  on public.scenario_regression_runs (run_type, created_at);

create table if not exists public.scenario_regression_results (
  id text primary key default gen_random_uuid()::text,
  scenario_regression_run_id text not null references public.scenario_regression_runs(id) on delete cascade,
  scenario_case_id text references public.scenario_cases(id) on delete set null,
  expected_status text,
  actual_status text,
  passed boolean not null,
  failure_reason text,
  result_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists scenario_regression_results_run_passed_idx
  on public.scenario_regression_results (scenario_regression_run_id, passed);

create index if not exists scenario_regression_results_case_idx
  on public.scenario_regression_results (scenario_case_id);

alter table public.regulatory_sources enable row level security;
alter table public.regulatory_source_versions enable row level security;
alter table public.source_chunks enable row level security;
alter table public.source_ingestion_jobs enable row level security;
alter table public.source_ingestion_job_events enable row level security;
alter table public.rule_cards enable row level security;
alter table public.rule_card_sources enable row level security;
alter table public.rule_card_reviews enable row level security;
alter table public.rule_card_versions enable row level security;
alter table public.kde_requirements enable row level security;
alter table public.scenario_cases enable row level security;
alter table public.approved_rule_packages enable row level security;
alter table public.approved_rule_package_records enable row level security;
alter table public.scenario_regression_runs enable row level security;
alter table public.scenario_regression_results enable row level security;

drop policy if exists "Reviewers can read regulatory sources" on public.regulatory_sources;
create policy "Reviewers can read regulatory sources"
on public.regulatory_sources for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read regulatory source versions" on public.regulatory_source_versions;
create policy "Reviewers can read regulatory source versions"
on public.regulatory_source_versions for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read source chunks" on public.source_chunks;
create policy "Reviewers can read source chunks"
on public.source_chunks for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read source ingestion jobs" on public.source_ingestion_jobs;
create policy "Reviewers can read source ingestion jobs"
on public.source_ingestion_jobs for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read source ingestion job events" on public.source_ingestion_job_events;
create policy "Reviewers can read source ingestion job events"
on public.source_ingestion_job_events for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read rule cards" on public.rule_cards;
create policy "Reviewers can read rule cards"
on public.rule_cards for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read rule card sources" on public.rule_card_sources;
create policy "Reviewers can read rule card sources"
on public.rule_card_sources for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read rule card reviews" on public.rule_card_reviews;
create policy "Reviewers can read rule card reviews"
on public.rule_card_reviews for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read rule card versions" on public.rule_card_versions;
create policy "Reviewers can read rule card versions"
on public.rule_card_versions for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read KDE requirements" on public.kde_requirements;
create policy "Reviewers can read KDE requirements"
on public.kde_requirements for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read scenario cases" on public.scenario_cases;
create policy "Reviewers can read scenario cases"
on public.scenario_cases for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read approved rule packages" on public.approved_rule_packages;
create policy "Reviewers can read approved rule packages"
on public.approved_rule_packages for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read approved rule package records" on public.approved_rule_package_records;
create policy "Reviewers can read approved rule package records"
on public.approved_rule_package_records for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read scenario regression runs" on public.scenario_regression_runs;
create policy "Reviewers can read scenario regression runs"
on public.scenario_regression_runs for select to authenticated
using (public.traceready_is_reviewer_or_admin());

drop policy if exists "Reviewers can read scenario regression results" on public.scenario_regression_results;
create policy "Reviewers can read scenario regression results"
on public.scenario_regression_results for select to authenticated
using (public.traceready_is_reviewer_or_admin());

-- Insert/update/delete remain service-role controlled for this phase.
