-- Plain-English explanations for approved FSMA 204 obligations.
--
-- These are AI-DRAFTED from each obligation's source chunk (support_text) in the ingestion
-- layer, then reviewer-approved — never hardcoded and never generated per audit at runtime.
-- The customer audit view looks these up by obligation_id (deterministic, reproducible:
-- the explanation is versioned and the audit pins its obligation version).
create table if not exists public.obligation_explanations (
  obligation_id text primary key,
  section_ref text,
  cte text,
  plain_requirement text not null,
  why_it_matters text not null,
  support_text text,
  source_chunk_id text,
  source_url text,
  generated_by text not null,
  model text,
  status text not null default 'ai_generated'
    check (status in ('ai_generated', 'approved', 'rejected')),
  version integer not null default 1,
  reviewed_by text,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists set_obligation_explanations_updated_at on public.obligation_explanations;

create trigger set_obligation_explanations_updated_at
before update on public.obligation_explanations
for each row
execute function public.set_updated_at();
