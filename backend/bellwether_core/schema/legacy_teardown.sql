-- ⚠️ DO NOT APPLY YET — cutover teardown (step 6).
--
-- Run this ONLY after:
--   1) the new /v2 path is live against Supabase and passes test_parity.py on real data,
--   2) the frontend reads exclusively from /v2,
--   3) you have a database backup.
--
-- It drops the legacy tables that the lean schema (001_core.sql) replaces. The lean schema
-- keeps: customers, app_users, rule_packages, audit_projects, audit_files, audit_runs,
-- evidence_items, findings, audit_events. Everything below is legacy and unused by v2.

begin;

-- Normalized-evidence layer (built, never used at runtime)
drop table if exists normalized_review_items cascade;
drop table if exists normalized_kde_values cascade;
drop table if exists normalized_event_evidence_refs cascade;
drop table if exists tlc_lineage_links cascade;
drop table if exists normalized_events cascade;
drop table if exists normalized_business_objects cascade;

-- Parsed-workbook materialization (UI optimization; derive on demand instead)
drop table if exists parsed_workbook_cells cascade;
drop table if exists parsed_workbook_rows cascade;
drop table if exists parsed_workbook_sheets cascade;

-- Lock-based job queue + legacy audit pipeline tables replaced by v2 audit_runs/findings
drop table if exists audit_job_events cascade;
drop table if exists audit_jobs cascade;
drop table if exists audit_artifacts cascade;
drop table if exists finding_traces cascade;
drop table if exists finding_evidence_refs cascade;
drop table if exists customer_review_actions cascade;
drop table if exists audit_logs cascade;
-- NOTE: legacy audit_findings is superseded by the new `findings` table.
drop table if exists audit_findings cascade;

-- Regulatory-intelligence subsystem (quarantined offline → emits approved-rule-package.json)
drop table if exists scenario_regression_results cascade;
drop table if exists scenario_regression_runs cascade;
drop table if exists scenario_cases cascade;
drop table if exists approved_rule_package_records cascade;
drop table if exists approved_rule_packages cascade;
drop table if exists approved_obligation_sets cascade;
drop table if exists obligation_inventory_records cascade;
drop table if exists obligation_explanations cascade;
drop table if exists approved_regulatory_records cascade;
drop table if exists regulatory_review_actions cascade;
drop table if exists regulatory_draft_records cascade;
drop table if exists kde_requirements cascade;
drop table if exists rule_card_versions cascade;
drop table if exists rule_card_reviews cascade;
drop table if exists rule_card_sources cascade;
drop table if exists rule_cards cascade;
drop table if exists source_chunks cascade;
drop table if exists regulatory_source_versions cascade;
drop table if exists regulatory_sources cascade;
drop table if exists source_ingestion_job_events cascade;
drop table if exists source_ingestion_jobs cascade;

commit;
