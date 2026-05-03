# Phase 4.44 - Synthetic Raw To L3 Preflight Gate

## Current HEAD

- Base HEAD: `80ecb30266e56644d66a4170178d4fb434cbd61f`
- Working branch: `feat/synthetic-l3-preflight-gate`
- Phase 4.43 report preserved: `docs/_reports/SYNTHETIC_RAW_MATCH_DATA_SINGLE_INSERT_PHASE4_43.md`

## Phase 4.43 Synthetic Raw Status

Phase 4.43 had already inserted one human-authorized synthetic `raw_match_data` row for:

- `match_id = 47_20242025_900002`
- `external_id = 900002`
- `data_version = PHASE4.43_SYNTHETIC`

The stored `raw_data.metadata` remains:

- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`

This row is engineering-test-only synthetic input, not real external raw data, not suitable for production, and not suitable for real training.

## Current DB Row Counts

Row counts before and after Phase 4.44 validation remained unchanged:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    2 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

## Target Match Status

Target:

| field                 | value                    |
| --------------------- | ------------------------ |
| match_id              | `47_20242025_900002`     |
| league_name           | `Segunda`                |
| season                | `2024/2025`              |
| home_team             | `Burgos`                 |
| away_team             | `Oviedo`                 |
| home_score            | `1`                      |
| away_score            | `0`                      |
| actual_result         | `home_win`               |
| match_date            | `2024-08-17 17:30:00+00` |
| status                | `finished`               |
| is_finished           | `true`                   |
| has_raw_match_data    | `true`                   |
| has_l3_features       | `false`                  |
| has_training_features | `false`                  |
| has_predictions       | `false`                  |

Conclusion:

- the target finished match exists
- it has one synthetic raw row
- it still has no downstream `l3_features`
- training features and predictions remain absent

## Synthetic raw_match_data Metadata Summary

Read-only verification of the existing target raw row confirmed:

- `id = 2`
- `external_id = 900002`
- `data_version = PHASE4.43_SYNTHETIC`
- `data_hash = f679933712fd826e8f8785a4866e8f3d841b9a1653caea3bb733c8efbde5921e`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- raw JSON contains `matchId`
- raw JSON contains `general`
- raw JSON contains `header`
- raw JSON contains `content`

## l3_features Schema Summary

Read-only schema inspection confirmed:

- primary key: `PRIMARY KEY (match_id)`
- foreign key: `FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE`
- JSONB columns default to `{}`:
    - `golden_features`
    - `tactical_features`
    - `odds_movement_features`
    - `odds_features`
    - `elo_features`
    - `rolling_features`
    - `efficiency_features`
    - `draw_features`
    - `market_sentiment`
    - `stitch_summary`
- timestamps default to `now()`:
    - `computed_at`
    - `created_at`
    - `updated_at`

Implication:

- the target match currently has no `l3_features`
- a future write would be one row per `match_id`
- Phase 4.44 intentionally does not perform that write

## Existing L3 Entrypoint Risk Audit

Relevant existing entrypoints were audited read-only:

| entrypoint                                                   | current behavior                  | write risk   |
| ------------------------------------------------------------ | --------------------------------- | ------------ |
| `make data-l3-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>`       | local fixture dry-run             | dry-run only |
| `make data-l3-write-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>` | local `l3_features` write preview | dry-run only |
| `make data-l3-commit ... CONFIRM_L3_COMMIT=1`                | blocked                           | not wired    |
| `make data-l3-write-commit ... CONFIRM_L3_WRITE=1`           | blocked                           | not wired    |
| `npm run smelt`                                              | real L3 pipeline                  | prohibited   |
| `npm run l3:stitch`                                          | real L3 pipeline                  | prohibited   |
| `npm run elo:recalc`                                         | real ELO path                     | prohibited   |

Decision:

- the new synthetic gate must not call `smelt`
- the new synthetic gate must not call `l3:stitch`
- the new synthetic gate must not call ELO
- the new synthetic gate must stay SELECT-only and preview-only

## New Script Behavior

Added:

```text
scripts/ops/synthetic_l3_preflight.js
```

Supported commands:

```bash
node scripts/ops/synthetic_l3_preflight.js --match-id 47_20242025_900002
node scripts/ops/synthetic_l3_preflight.js --match-id 47_20242025_900002 --json
node scripts/ops/synthetic_l3_preflight.js --match-id 47_20242025_900002 --commit
```

Behavior:

- performs SELECT-only DB checks
- reads the target match row
- reads the existing target `raw_match_data` row from DB
- checks synthetic metadata and required raw JSON shape
- checks existing downstream presence for `l3_features`, `match_features_training`, and `predictions`
- emits a preview-only `l3_features` shape
- marks synthetic provenance on all preview JSONB payloads
- emits `would_insert_l3_features=false`
- emits `would_update_matches=false`
- emits `would_trigger_elo=false`
- emits `preview_only=true`
- emits `can_write_l3_now=false`
- emits `real_training_allowed=false`
- does not call `smelt`
- does not call `l3:stitch`
- does not call ELO
- does not write `l3_features`
- does not write `match_features_training`
- does not write `predictions`
- does not access external network

`--commit` behavior:

```text
BLOCKED: synthetic L3 commit is not wired in Phase 4.44.
```

## Makefile Entrypoints

Added:

```text
make data-synthetic-l3-dry-run MATCH_ID=<id>
make data-synthetic-l3-commit MATCH_ID=<id> CONFIRM_SYNTHETIC_L3=1  # blocked in Phase 4.44
```

Behavior:

- `data-synthetic-l3-dry-run` requires `MATCH_ID`
- `data-synthetic-l3-dry-run` runs `scripts/ops/synthetic_l3_preflight.js`
- `data-synthetic-l3-commit` is blocked by default
- `data-synthetic-l3-commit` remains blocked even with `CONFIRM_SYNTHETIC_L3=1`

`data-help` was updated to list both entries.

## AGENTS.md Update

Added synthetic L3 safety rules:

- `make data-synthetic-l3-dry-run MATCH_ID=<id>` is only allowed with explicit user authorization
- input raw row must already be marked synthetic and engineering-test-only
- the gate must remain SELECT-only
- no DB writes
- no `smelt`
- no `l3:stitch`
- no ELO
- no training
- no prediction
- no external network

Added explicit prohibitions for:

- `make data-synthetic-l3-commit`
- `make data-synthetic-l3-commit CONFIRM_SYNTHETIC_L3=1`
- `node scripts/ops/synthetic_l3_preflight.js --commit`
- `npm run smelt`
- `npm run l3:stitch`
- `node scripts/ops/l3_features_local_write_gate.js --commit`

Added policy statement:

- synthetic L3 preview is engineering-only
- synthetic L3 preview is not for real training
- synthetic L3 preview must not enter production
- real `l3_features` write still requires separate authorization and `pg_dump`

## Dry-Run Validation

Missing argument gate:

```bash
make data-synthetic-l3-dry-run || true
```

Result:

- failed as expected
- message: `ERROR: provide MATCH_ID=<id>`

Target synthetic L3 dry-run:

```bash
make data-synthetic-l3-dry-run MATCH_ID=47_20242025_900002
```

Result:

- `mode = dry-run`
- `phase = 4.44`
- `match_found = true`
- `is_finished = true`
- `has_actual_result = true`
- `has_score = true`
- `raw_match_data_found = true`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `l3_features_exists = false`
- `match_features_training_exists = false`
- `predictions_exists = false`
- `would_insert_l3_features = false`
- `would_update_matches = false`
- `would_trigger_elo = false`
- `preview_only = true`
- `can_write_l3_now = false`
- `real_training_allowed = false`
- `no_db_writes`
- `no_l3_write`
- `no_smelt`
- `no_l3_stitch`
- `no_elo`
- `no_training`
- `no_prediction_execution`
- `no_external_network`

## L3 Preview Summary

The new preview emits a conservative future-shape payload for:

- `golden_features`
- `tactical_features`
- `odds_features`
- `elo_features`
- `stitch_summary`

Each preview object includes:

```json
{
    "synthetic": true,
    "source": "PHASE4.43_SYNTHETIC",
    "engineering_test_only": true,
    "not_for_training": true,
    "not_for_production": true
}
```

Additional preview notes:

- `golden_features.match_identity_only = true`
- `tactical_features.extraction_not_run = true`
- `odds_features.odds_extraction_not_run = true`
- `elo_features.elo_not_run = true`
- `stitch_summary.stitch_not_run = true`

This makes the preview useful for engineering-shape validation without pretending real feature extraction occurred.

## Commit Gate Validation

Validated:

```bash
make data-synthetic-l3-commit || true
make data-synthetic-l3-commit MATCH_ID=47_20242025_900002 CONFIRM_SYNTHETIC_L3=1 || true
```

Result:

- both commands were blocked
- no DB writes occurred
- no L3 write path was invoked

## Existing Backfill Gate Recheck

`make data-finished-backfill-dry-run MATCH_ID=47_20242025_900002` remained read-only and reported:

- `has_raw_match_data = true`
- `has_l3_features = false`
- `has_training_features = false`
- `has_predictions = false`
- `no_db_writes`

## DB Before/After Summary

DB row counts were unchanged across all Phase 4.44 validations:

| table                   | rows before | rows after |
| ----------------------- | ----------: | ---------: |
| matches                 |           2 |          2 |
| bookmaker_odds_history  |           2 |          2 |
| raw_match_data          |           2 |          2 |
| l3_features             |           1 |          1 |
| match_features_training |           1 |          1 |
| predictions             |           1 |          1 |

## Recommended Next Phase

Recommended next step:

```text
Phase 4.45: artificial authorization for one synthetic l3_features write
```

Alternative:

```text
continue searching for a legal real raw source before any downstream feature write
```

## Explicit Non-Execution

This phase did not execute:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `COPY`
- export
- DB writes
- `raw_match_data` write
- `l3_features` write
- `match_features_training` write
- `predictions` write
- `smelt`
- `l3:stitch`
- ELO recalculation
- model training
- real prediction execution
- model artifact loading
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- `raw_match_data_local_ingest --commit`
- external download
- `curl`
- `wget`
- `git clone`
- external network access
- real harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume cleanup
- `git push --force`
- `git push --mirror`
- `git fetch --all`
- `git pull`
- file deletion
