-- Bellwether — lean core schema (ground-up rebuild)
--
-- ~10 tables vs. the legacy ~40. Principles:
--   * The AUDIT RUN is the snapshot unit. Everything (evidence, findings) is scoped to a
--     run, not to a file — fixes the legacy file-vs-run scoping smell.
--   * The rule package is ONE versioned row (payload_json), not ~20 regulatory tables.
--     It's authored offline and pinned per run.
--   * No normalized_* layer, no parsed_workbook_* layer, no lock-based job queue. Parsing is
--     synchronous; if async is ever needed, add a minimal jobs table then — not before.
--   * One audit trail (audit_events), JSON only where the shape is genuinely open.

create extension if not exists "uuid-ossp";

-- ── Tenancy & identity ─────────────────────────────────────────────────────
create table customers (
  id          text primary key,
  name        text not null,
  created_at  timestamptz not null default now()
);

create table app_users (
  id           uuid primary key,                 -- mirrors auth.users
  email        text not null unique,
  role         text not null check (role in ('operator','reviewer','admin')),
  customer_id  text references customers(id) on delete set null,
  created_at   timestamptz not null default now()
);

-- ── Rule package (authored offline, pinned per run) ────────────────────────
create table rule_packages (
  id            text primary key,
  package_id    text not null,
  version       int  not null,
  status        text not null default 'approved' check (status in ('approved','superseded')),
  package_hash  text not null,
  payload_json  jsonb not null,                  -- the whole approved package
  approved_at   timestamptz not null default now(),
  unique (package_id, version)
);

-- ── Audit pipeline ─────────────────────────────────────────────────────────
create table audit_projects (
  id              text primary key,
  customer_id     text references customers(id) on delete cascade,
  name            text not null,
  status          text not null default 'active' check (status in ('active','archived')),
  created_by       uuid references app_users(id) on delete set null,
  created_at      timestamptz not null default now()
);

create table audit_files (
  id                 text primary key,
  audit_project_id   text not null references audit_projects(id) on delete cascade,
  file_name          text not null,
  file_type          text not null,              -- xlsx | csv | edi | epcis | gdsn
  storage_key        text not null,
  file_hash          text,
  size_bytes         bigint,
  uploaded_by        uuid references app_users(id) on delete set null,
  created_at         timestamptz not null default now()
);

create table audit_runs (
  id                    text primary key,
  audit_project_id      text not null references audit_projects(id) on delete cascade,
  audit_file_id         text references audit_files(id) on delete set null,
  run_number            int  not null,
  status                text not null default 'pending'
                          check (status in ('pending','parsing','executing','succeeded','failed')),
  rule_package_id       text references rule_packages(id) on delete restrict,
  readiness_passed      boolean,
  summary_json          jsonb not null default '{}'::jsonb,
  error                 text,
  started_at            timestamptz,
  completed_at          timestamptz,
  created_at            timestamptz not null default now(),
  unique (audit_project_id, run_number)
);

-- Evidence is the parsed cells, scoped to the RUN (the snapshot).
create table evidence_items (
  id               text primary key,
  audit_run_id     text not null references audit_runs(id) on delete cascade,
  sheet_name       text,
  row_number       int,
  column_name      text,
  cell             text,
  field_key        text,
  raw_value        text,
  normalized_value text,
  confidence       real,
  created_at       timestamptz not null default now()
);
create index on evidence_items (audit_run_id, field_key);

-- Findings — includes the engine citation (section / flexibility scenario / note) inline,
-- so P2/P5 + flexibility findings carry their citation without a join.
create table findings (
  id                 text primary key,
  audit_run_id       text not null references audit_runs(id) on delete cascade,
  severity           text not null check (severity in ('low','medium','high','critical')),
  status             text not null,              -- gap | operational_anomaly | needs_review | pass | ...
  finding_type       text not null,
  title              text not null,
  message            text,
  event_id           text,
  cte                text,
  field_or_kde       text,
  recommendation     text,
  citation_section   text,
  citation_scenario  text,
  citation_note      text,
  confidence         real,
  evidence_ids_json  jsonb not null default '[]'::jsonb,
  review_state       text not null default 'pending',
  created_at         timestamptz not null default now()
);
create index on findings (audit_run_id, severity);

-- Single audit trail for user/system actions.
create table audit_events (
  id                text primary key,
  audit_project_id  text references audit_projects(id) on delete cascade,
  audit_run_id      text references audit_runs(id) on delete cascade,
  actor             text,
  action            text not null,
  payload_json      jsonb not null default '{}'::jsonb,
  created_at        timestamptz not null default now()
);
create index on audit_events (audit_project_id, created_at);
