-- TraceReady parsed workbook record persistence.
--
-- Run this only after:
-- 001_initial_auth_and_storage.sql
-- 005_enterprise_audit_foundation.sql
--
-- Evidence rows remain the normalized signal layer. These tables preserve the
-- parsed sheet/row/cell reconstruction needed for audit review, lineage, and
-- deterministic reruns without relying on local JSON files.

do $$
begin
  if to_regclass('public.traceready_profiles') is null then
    raise exception 'Missing dependency: run 001_initial_auth_and_storage.sql before 008_parsed_workbook_records.sql';
  end if;

  if to_regclass('public.audit_projects') is null
    or to_regclass('public.audit_runs') is null
    or to_regclass('public.audit_files') is null
    or to_regclass('public.evidence_items') is null then
    raise exception 'Missing dependency: run 005_enterprise_audit_foundation.sql before 008_parsed_workbook_records.sql';
  end if;
end $$;

create table if not exists public.parsed_workbook_sheets (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  audit_file_id text not null references public.audit_files(id) on delete cascade,
  sheet_name text not null,
  sheet_index integer,
  header_row_number integer,
  row_count integer not null default 0,
  column_count integer not null default 0,
  parser_version text,
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  unique (audit_file_id, sheet_name)
);

create index if not exists parsed_workbook_sheets_project_sheet_idx
  on public.parsed_workbook_sheets (audit_project_id, sheet_name);

create index if not exists parsed_workbook_sheets_run_sheet_idx
  on public.parsed_workbook_sheets (audit_run_id, sheet_name);

create table if not exists public.parsed_workbook_rows (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  audit_file_id text not null references public.audit_files(id) on delete cascade,
  sheet_id text not null references public.parsed_workbook_sheets(id) on delete cascade,
  sheet_name text not null,
  source_row_number integer not null,
  source_row_key text not null,
  row_kind text not null default 'data',
  raw_row_json jsonb,
  normalized_row_json jsonb,
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  unique (audit_file_id, sheet_name, source_row_number)
);

create index if not exists parsed_workbook_rows_project_sheet_row_idx
  on public.parsed_workbook_rows (audit_project_id, sheet_name, source_row_number);

create index if not exists parsed_workbook_rows_run_sheet_row_idx
  on public.parsed_workbook_rows (audit_run_id, sheet_name, source_row_number);

create index if not exists parsed_workbook_rows_sheet_row_idx
  on public.parsed_workbook_rows (sheet_id, source_row_number);

create table if not exists public.parsed_workbook_cells (
  id text primary key,
  audit_project_id text not null references public.audit_projects(id) on delete cascade,
  audit_run_id text references public.audit_runs(id) on delete set null,
  audit_file_id text not null references public.audit_files(id) on delete cascade,
  sheet_id text not null references public.parsed_workbook_sheets(id) on delete cascade,
  row_id text not null references public.parsed_workbook_rows(id) on delete cascade,
  sheet_name text not null,
  source_row_number integer not null,
  source_column text not null,
  source_column_index integer,
  cell_address text,
  raw_value text,
  normalized_value text,
  canonical_field text,
  evidence_item_id text references public.evidence_items(id) on delete set null,
  parser_version text,
  metadata_json jsonb,
  created_at timestamptz not null default now(),
  unique (audit_file_id, sheet_name, source_row_number, source_column)
);

create index if not exists parsed_workbook_cells_project_field_idx
  on public.parsed_workbook_cells (audit_project_id, canonical_field);

create index if not exists parsed_workbook_cells_run_field_idx
  on public.parsed_workbook_cells (audit_run_id, canonical_field);

create index if not exists parsed_workbook_cells_row_idx
  on public.parsed_workbook_cells (row_id);

create index if not exists parsed_workbook_cells_evidence_idx
  on public.parsed_workbook_cells (evidence_item_id);

alter table public.parsed_workbook_sheets enable row level security;
alter table public.parsed_workbook_rows enable row level security;
alter table public.parsed_workbook_cells enable row level security;

drop policy if exists "TraceReady users can read accessible parsed workbook sheets" on public.parsed_workbook_sheets;
create policy "TraceReady users can read accessible parsed workbook sheets"
on public.parsed_workbook_sheets
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible parsed workbook rows" on public.parsed_workbook_rows;
create policy "TraceReady users can read accessible parsed workbook rows"
on public.parsed_workbook_rows
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

drop policy if exists "TraceReady users can read accessible parsed workbook cells" on public.parsed_workbook_cells;
create policy "TraceReady users can read accessible parsed workbook cells"
on public.parsed_workbook_cells
for select
to authenticated
using (public.traceready_can_access_audit_project(audit_project_id));

-- Insert/update/delete remain service-role controlled for this phase.
