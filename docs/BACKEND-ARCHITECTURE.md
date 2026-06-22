# Bellwether — Backend Architecture (lean rebuild)

_Target architecture for the ground-up backend rebuild. The legacy `bellwether_backend/backend`
+ regulatory pipeline stays intact until the new path reaches parity, then is retired._

## Design principles
1. **Reuse the validated engine.** `audit_engine/` (the deterministic rule logic, proven on
   Jim's Sea Eagle data) is the crown jewel — we rebuild the *architecture around it*, not the rules.
2. **The run is the snapshot unit.** Evidence and findings are scoped to an `audit_run`, not a
   file. A re-run is a new immutable snapshot.
3. **The rule package is a versioned artifact**, authored offline, pinned per run — not ~20
   live regulatory tables.
4. **Pure core, thin edges.** The pipeline + domain + engine are DB-agnostic and unit-testable.
   The database is a thin adapter at the boundary. The API is a thin handler.
5. **Synchronous until volume demands otherwise.** No lock-based job queue yet; add one only
   when load proves it's needed.

## The shape

```
 OFFLINE (build time, NOT in the request path)
 ┌───────────────────────────────────────────────────────────────┐
 │ Rule-package authoring (CLI / scripts)                         │
 │   bundled_rules + regulatory sources  ──►  approved-rule-      │
 │                                            package.json (vN)   │
 └───────────────────────────────┬───────────────────────────────┘
                                 │ pinned per run
                                 ▼
 RUNTIME (the request path)
   upload bytes ─► [API handler] ─► [pipeline.run_audit] ─► [audit_engine] (validated)
                       │                     │ returns
                       │                     ▼
                       │              [domain.AuditResult]  (clean Finding/Coverage/Scorecard/Anomaly)
                       │                     │
                       └────────────► [store adapter] ──► Postgres (lean ~10 tables)
                                                              │
                                          frontend reads clean shapes ─► UI panels + exports
```

## Components (new `bellwether_core/`)
| Layer | File | Responsibility | Status |
|---|---|---|---|
| Domain | `domain.py` | Clean models (`Finding`, `CoverageCell`, `SupplierScorecard`, `Anomaly`, `AuditResult`) | ✅ built |
| Pipeline | `pipeline.py` | `bytes\|file → AuditResult`; reuses `audit_engine`; **no DB** | ✅ built |
| Engine | `bellwether_backend/audit_engine/*` | Validated deterministic checks (P1–P5) | ✅ reused (unchanged) |
| Schema | `schema/001_core.sql` | Lean ~10-table Postgres schema | ✅ built |
| **Store adapter** | `store.py` | Persist `AuditResult` + run metadata → DB; read for UI | ⬜ next |
| **Entry/API** | `app.py` (or a route) | `upload → run_audit → persist → return ids`; synchronous | ⬜ next |
| Rule-package authoring | `scripts/` (quarantined regulatory pipeline) | Emit the versioned `approved-rule-package.json` | ⬜ quarantine |

## Lean schema (`schema/001_core.sql`) — ~10 tables
`customers`, `app_users`, `rule_packages`, `audit_projects`, `audit_files`, `audit_runs`,
`evidence_items` (run-scoped), `findings` (citation inline), `audit_events`.
Relationships: `project → run → {files, evidence, findings}`; `run` pins a `rule_package`.

## Legacy → new mapping
| Legacy | Disposition |
|---|---|
| `audit_engine/*` | **Keep & reuse** (the brains) |
| `backend/services/{audit_parse,rule_execution,audit_job_slice}_service.py` | **Replace** with `pipeline.py` + `store.py` (synchronous, no lock-queue) |
| `backend/repositories/supabase_tables.py` (~1,200 LOC) | **Replace** with a thin `store.py` against the lean schema |
| `normalized_*`, `parsed_workbook_*` tables/services | **Drop** (unused at runtime / UI-only) |
| `regulatory_* / obligation_* / rule_card_* / scenario_*` (~20 tables + `intelligence/` pipeline) | **Quarantine** as offline authoring → emits `approved-rule-package.json` |
| `audit_logs`, `field_mapping_governance`, lock columns on jobs | **Drop** |
| 9 legacy migrations / ~40 tables | **Replace** with `001_core.sql` (~10 tables) |

## Cutover plan (strangler — no big-bang delete)
1. ✅ Core spine (schema + domain + pipeline), parity-verified on Jim's data.
2. ⬜ `store.py` adapter + tests (persist/read against lean schema).
3. ⬜ Slim entry handler (`upload → run_audit → persist`).
4. ⬜ Point the frontend reads at the new shapes (UI panels already align).
5. ⬜ Shadow-run new path beside legacy; confirm parity end-to-end.
6. ⬜ Retire legacy backend + drop the ~30 unused tables.

## Locked decisions (confirmed)
- **Database:** **Keep Supabase Postgres** (reuse infra + auth); apply the new lean schema alongside, then drop legacy tables at cutover.
- **Processing:** **Synchronous** — the upload handler runs the audit inline and returns when done. No job queue until volume demands it.
- **Entry point:** a **new minimal FastAPI route** for `bellwether_core`, reusing the existing deploy; uncoupled from legacy `api/main.py`.
- **Regulatory pipeline:** **Quarantine** as an offline build tool that emits one versioned `approved-rule-package.json`; runtime only consumes the artifact.

## Build order (post-plan)
1. ✅ Core spine (schema + domain + pipeline), parity-verified.
2. `store.py` — Supabase adapter: persist `AuditResult` + run metadata into the lean schema; read back for the UI. Unit-tested with a fake client.
3. New minimal **FastAPI route**: `POST /v2/audits` (upload → `run_audit` → persist → return run id) + `GET /v2/audits/{run_id}` (read clean shapes). Synchronous.
4. Point frontend reads at the new shapes.
5. Quarantine the regulatory pipeline into `scripts/build_rule_package.py` (emits the artifact).
6. Shadow-run vs legacy → confirm parity → retire legacy + drop unused tables.
