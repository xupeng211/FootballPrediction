# Matches Labeling Schema Migration Verification - 2026-06-19
- lifecycle: phase-artifact
- scope: additive nullable schema migration verification only
- branch: `db/add-matches-labeling-governance-columns`
- base: `1b1b54c9ba029f321854542da7d9c075c406576b`
- migration: `database/migrations/V26.7__add_matches_labeling_governance_columns.sql`

## Nature / 边界
- 这是 additive nullable schema migration。
- 只新增 `matches` 6 列；没有 backfill。
- 没有业务数据 `UPDATE/INSERT/DELETE`，没有处理 2 条 no-raw excluded。
- 没有 live fetch，没有 raw payload output。
- 没有改采集器 / parser / training / prediction。
- 没有改 writer / reader。
- 没有修改 `pipeline_status` 约束，没有新增 `needs_new_evidence` 到 `pipeline_status`。

## Added Columns
| column | type | nullable | default | CHECK | comment |
|---|---|---|---|---|---|
| `source_type` | `VARCHAR(32)` | yes | none | `NULL OR IN ('fotmob_live_fetch','fotmob_html_hydration','fotmob_pageprops','manual_seed','local_csv','synthetic','unknown')` | yes |
| `evidence_level` | `VARCHAR(24)` | yes | none | `NULL OR IN ('strong','medium','weak','synthetic_invalid','missing')` | yes |
| `is_production_scope` | `BOOLEAN` | yes | none | none | yes |
| `is_reconciliation_eligible` | `BOOLEAN` | yes | none | none | yes |
| `is_training_eligible` | `BOOLEAN` | yes | none | none | yes |
| `pipeline_status_reason` | `VARCHAR(64)` | yes | none | `NULL OR ~ '^[a-z][a-z0-9_]*$'` | yes |

Column comments added:
- `source_type`: match-level authoritative provenance class
- `evidence_level`: match-level evidence strength
- `is_production_scope`: whether match belongs to current production scope
- `is_reconciliation_eligible`: whether match may enter guarded reconciliation
- `is_training_eligible`: whether match may enter training datasets
- `pipeline_status_reason`: structured reason for current `pipeline_status`, especially pending/skipped/failed

## Validation
- Safety gate read-only checks executed: `make data-schema-help`, `make data-schema-status`, `make data-schema-plan`.
- Local/dev DB only: migration applied to `docker-compose.dev.yml` `db` service (`football_db`) via container `psql`; no production DB connection.
- `git diff --check`: pass.
- `information_schema.columns`: confirms 6 new columns exist on `matches`, all `is_nullable = YES`, all `column_default` empty.
- `pg_constraint`: confirms `matches_source_type_valid`, `matches_evidence_level_valid`, `matches_pipeline_status_reason_format` exist.
- `pg_description`: confirms all 6 column comments exist.
- `matches` logical fingerprint before migration: row count `60`, logical hash `2c5c0e7be92c58e487168424e68a7ceb`.
- `matches` logical fingerprint after migration: row count `60`, logical hash `2c5c0e7be92c58e487168424e68a7ceb`.
- Conclusion: no existing `matches` row content changed.
- `raw_match_data` row count before/after: `76 -> 76` unchanged.
- Read-only reconciliation preview after migration: `candidate_total = 0`, `excluded_no_raw_count = 2`.

## Outcome
- `matches` successfully gained 6 additive nullable governance columns.
- 6 columns are nullable.
- 6 columns have no default.
- CHECK constraints and column comments are present as designed.
- No backfill was executed.
- No business data was written.
- No no-raw excluded rows were processed.

## Next Step
Writer changes, backfill, eligibility labeling, or any `pipeline_status` semantic change still require separate user confirmation and a separate runtime behavior PR.
