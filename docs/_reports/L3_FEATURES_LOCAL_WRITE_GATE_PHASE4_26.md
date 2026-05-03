# Phase 4.26 - L3 Features Local Write Gate

## Current HEAD

- Base HEAD: `1a0ef9c4a4e474f27dccecf8ab90a195f24a794a`
- Working branch: `feat/l3-features-local-write-gate`
- Target match: `140_20252026_4837496`
- Fixture: `tests/fixtures/l3/raw_match_data_phase419_sample.json`

## Current DB State

Read-only row counts before and after validation:

| table                   | before | after |
| ----------------------- | -----: | ----: |
| matches                 |      1 |     1 |
| bookmaker_odds_history  |      2 |     2 |
| raw_match_data          |      1 |     1 |
| l3_features             |      0 |     0 |
| match_features_training |      0 |     0 |
| predictions             |      0 |     0 |

## l3_features Table Summary

- Primary key: `match_id`
- Foreign key: `match_id` references `matches(match_id)` with `ON DELETE CASCADE`
- Optional scalar field: `external_id`
- JSONB fields with default `{}`: `golden_features`, `tactical_features`, `odds_movement_features`, `odds_features`, `elo_features`, `rolling_features`, `efficiency_features`, `draw_features`, `market_sentiment`, `stitch_summary`
- Timestamp fields with default `now()`: `computed_at`, `created_at`, `updated_at`
- Future minimal single-row insert can provide `match_id`, optional `external_id`, and selected JSONB feature payloads while relying on JSONB and timestamp defaults.

## Preconditions

- Target match exists in `matches`
- `bookmaker_odds_history` has 2 rows for the target match
- `raw_match_data` has 1 row for the target match
- `l3_features` has 0 rows for the target match

## Added Script

Added `scripts/ops/l3_features_local_write_gate.js`.

Behavior:

- Default mode is dry-run.
- Reads only a local fixture.
- Validates fixture match id against `--match-id`.
- Performs SELECT-only DB checks for `matches`, `bookmaker_odds_history`, `raw_match_data`, and `l3_features`.
- Builds a future `l3_features` preview record with `golden_features`, `tactical_features`, `odds_movement_features`, `odds_features`, `elo_features`, `stitch_summary`, and empty default-compatible JSONB groups.
- Does not call `npm run smelt`, `npm run l3:stitch`, `l3_stitch_pipeline`, `l3_stitch_worker`, or ELO code.
- Does not write DB state.

Commit behavior:

- `--commit` returns `BLOCKED: l3_features commit is not wired in Phase 4.26.`
- `CONFIRM_L3_WRITE=1` does not enable writes in this phase.

## Makefile Entrypoints

Added:

```bash
make data-l3-write-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>
make data-l3-write-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_L3_WRITE=1
```

`data-l3-write-commit` remains blocked / not wired in Phase 4.26.

## AGENTS.md Update

Updated AI / Codex data safety rules:

- Allow `make data-l3-write-dry-run SAMPLE_RAW=<local fixture> MATCH_ID=<id>` only with explicit user authorization, local fixture input, no DB writes, and no external network access.
- Forbid `make data-l3-write-commit`, `make data-l3-write-commit CONFIRM_L3_WRITE=1`, and `node scripts/ops/l3_features_local_write_gate.js --commit` unless a future phase separately authorizes a new workflow.
- Continue forbidding `npm run smelt`, `npm run l3:stitch`, `scripts/ops/smelt_all.js`, `scripts/ops/l3_stitch_pipeline.js`, `scripts/ops/l3_stitch_worker.js`, and `npm run elo:recalc`.

Related reports:

- `docs/_reports/L3_RAW_FIXTURE_PREFLIGHT_PHASE4_18.md`
- `docs/_reports/L3_LOCAL_DRY_RUN_GATE_PHASE4_19.md`
- `docs/_reports/RAW_MATCH_DATA_SINGLE_INSERT_PHASE4_23.md`
- `docs/_reports/L3_FEATURES_WRITE_GATE_PREFLIGHT_PHASE4_24.md`

## Dry-Run Validation

`make data-l3-write-dry-run` without arguments failed as expected.

Normal dry-run:

```bash
make data-l3-write-dry-run \
  SAMPLE_RAW=tests/fixtures/l3/raw_match_data_phase419_sample.json \
  MATCH_ID=140_20252026_4837496
```

Result summary:

- `mode`: `dry-run`
- `match_found`: `true`
- `raw_match_data_found`: `true`
- `odds_history_rows`: `2`
- `l3_features_exists`: `false`
- `would_insert_l3_features`: `false`
- `would_update_matches`: `false`
- `would_trigger_elo`: `false`
- Non-execution confirmations include `no_db_writes`, `no_insert`, `no_update`, `no_delete`, `no_create_index`, `no_smelt`, `no_l3_stitch`, `no_l3_write`, `no_elo`, and `no_external_network`

## Commit Gate Validation

Both commands remained blocked:

```bash
make data-l3-write-commit
make data-l3-write-commit \
  SAMPLE_RAW=tests/fixtures/l3/raw_match_data_phase419_sample.json \
  MATCH_ID=140_20252026_4837496 \
  CONFIRM_L3_WRITE=1
```

No DB writes were performed.

## Explicit Non-Execution

The phase did not execute:

- `INSERT / UPDATE / DELETE / CREATE / ALTER / DROP / TRUNCATE`
- `l3_features` write
- `raw_match_data` commit
- `npm run smelt`
- `npm run l3:stitch`
- ELO recalculation
- L3 feature computation write
- model training
- prediction write
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- external network access
- real harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume cleanup

## Next Steps

- A future real `l3_features` write must be separately authorized.
- Before any real write, create a DB backup and restrict execution to one explicit `match_id`.
- Continue forbidding `npm run smelt`, `npm run l3:stitch`, and ELO execution unless a future phase explicitly authorizes them.
