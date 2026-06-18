# Ingestion Scripts

The production Python package lives under `traceready_backend/`.

These folders contain reproducibility and evaluation entrypoints:

- `intelligence/`: historical Phase 4-13 artifact builders and Phase 5 AI extraction runners.
- `intelligence/validate_intelligence_schemas.py`: schema smoke validation against registry citations.
- `evaluation/`: public-web eval dataset/workbook builders.

The root `backend/` folder keeps production-facing CLIs, source bootstrap/admin commands, and deployment files:

- `ingest.py`
- `build_regulatory_registry.py`
- `ingest_fda_fsma204_hub_sources.py`
- `ingest_local_fda_documents.py`
- `seed_regulatory_sources.py`
- `seed_regulatory_draft_records.py`
- `check_source_artifact_integrity.py`
- `api/index.py`
- `vercel.json`

`evaluation/node_modules` is a symlink to the bundled Codex Node runtime. It is used only by the `.mjs` workbook builders.
