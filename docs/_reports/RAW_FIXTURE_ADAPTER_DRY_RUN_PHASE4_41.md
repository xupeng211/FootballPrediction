# Phase 4.41 - Raw Fixture Adapter Dry-Run Gate

## Current HEAD

- Base HEAD: `a280badf44552c9700d00f89871264a18cbf256f`
- Working branch: `feat/raw-fixture-adapter-dry-run-gate`
- Phase 4.40 report present: `docs/_reports/FINISHED_MATCH_BACKFILL_PREFLIGHT_PHASE4_40.md`
- Phase 4.39 report present: `docs/_reports/FINISHED_CSV_SINGLE_MATCH_INSERT_PHASE4_39.md`

## Current DB Row Counts

Row counts before and after the Phase 4.41 dry-run validations remained unchanged:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

`make data-dataset-status` remained SELECT-only and reported:

- `finished_matches = 1`
- `matches_with_actual_result = 1`
- `matches_with_scores = 1`
- `trainable_label_rows = 1`
- `full_feature_chain_rows = 1`
- `trainable = false`
- reason: current DB has only `1` trainable labeled row and `1` full feature-chain row; minimum pre-training discussion threshold is `200`

## Target Finished Match

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
| has_raw_match_data    | `false`                  |
| has_l3_features       | `false`                  |
| has_training_features | `false`                  |
| has_predictions       | `false`                  |

The match is a valid finished label row, but it still has no downstream raw/L3/training/prediction chain.

## raw_match_data Schema Summary

Read-only schema inspection showed:

| column         | type                       | nullable | default             |
| -------------- | -------------------------- | -------- | ------------------- |
| `id`           | `bigint`                   | `NO`     | sequence            |
| `match_id`     | `character varying`        | `NO`     | none                |
| `external_id`  | `character varying`        | `YES`    | none                |
| `raw_data`     | `jsonb`                    | `NO`     | none                |
| `collected_at` | `timestamp with time zone` | `YES`    | `CURRENT_TIMESTAMP` |
| `data_version` | `character varying`        | `YES`    | `V26.1`             |
| `data_hash`    | `character varying`        | `YES`    | none                |

Relevant constraints:

- primary key: `raw_match_data_pkey`
- unique match: `raw_match_data_match_id_key UNIQUE (match_id)`
- FK: `raw_match_data_match_id_fkey` references `matches(match_id)` with cascade delete
- `match_id_format`: match id must match numeric or league/season/external id format
- `raw_data_not_empty`: `raw_data IS NOT NULL` and not empty JSON
- `raw_data_has_match_id`: `raw_data` must contain `matchId`, `general`, or `header`
- `collected_at_not_null`: collected timestamp must not be null

Implication:

- a future raw write must provide exact target `match_id`
- raw JSON cannot be empty
- raw JSON must carry at least `matchId`, `general`, or `header`
- duplicate raw rows for the target are blocked by the unique constraint

## Raw Fixture Strategy

Path A: real local raw fixture

- fixture must come from a legal and documented source
- fixture must correspond to `47_20242025_900002`
- `match_id`, teams, score, and finished status must match the target
- only then can it become a future raw write candidate

Path B: synthetic local fixture

- must be explicitly marked synthetic
- engineering test only
- not real external data
- not production data
- not for training
- cannot be labeled as FotMob or another external data source
- must carry provenance in `data_source`, `data_version`, and metadata

No fixture file was created in this phase.

## New Script Behavior

Added:

```text
scripts/ops/raw_fixture_adapter_dry_run.js
```

Supported commands:

```bash
node scripts/ops/raw_fixture_adapter_dry_run.js --match-id <id> --fixture <path>
node scripts/ops/raw_fixture_adapter_dry_run.js --match-id <id> --fixture <path> --allow-synthetic
node scripts/ops/raw_fixture_adapter_dry_run.js --match-id <id> --fixture <path> --json
```

Behavior:

- reads target match via SELECT-only query
- reads one local JSON fixture
- extracts fixture match id, teams, score, status, and raw structure fields
- checks `general`, `header`, `content`, `stats`, `lineup`, `shotmap`, and `momentum` presence
- checks whether the fixture satisfies the raw JSON constraint shape
- emits `direct_fixture_match`
- emits `fixture_can_be_used_for_target`
- emits `synthetic_required`
- emits `would_insert_raw_match_data=false`
- emits `would_update_matches=false`
- emits `would_trigger_l3=false`
- does not call raw ingest, L3 write, training feature write, prediction write, training, prediction, model artifact loading, harvest, scrape, or external network

`--commit` behavior:

```text
BLOCKED: raw fixture adapter commit is not wired in Phase 4.41.
```

## Makefile Entrypoints

Added:

```text
make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<path>
make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<path> ALLOW_SYNTHETIC=1
make data-raw-fixture-commit MATCH_ID=<id> FIXTURE=<path> CONFIRM_RAW_FIXTURE_COMMIT=1  # blocked in Phase 4.41
```

`data-raw-fixture-dry-run` requires both `MATCH_ID` and `FIXTURE`.

`data-raw-fixture-commit` is intentionally blocked even when `CONFIRM_RAW_FIXTURE_COMMIT=1` is provided.

## AGENTS.md Update

Updated safety rules to allow only:

```text
make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<local json>
```

Only under these conditions:

- explicit user authorization
- SELECT-only DB checks
- local JSON read-only checks
- no DB writes
- no file creation
- no raw ingest
- no training
- no prediction
- no external network

Added explicit prohibitions for:

- `make data-raw-fixture-commit`
- `make data-raw-fixture-commit CONFIRM_RAW_FIXTURE_COMMIT=1`
- `node scripts/ops/raw_fixture_adapter_dry_run.js --commit`
- `node scripts/ops/raw_match_data_local_ingest.js --commit`

Added raw fixture rules:

- raw fixture must match target match id, teams, score, and status
- mismatched fixture cannot impersonate target match
- synthetic fixture is engineering-test-only and not for training
- synthetic raw data cannot be labeled as real external or FotMob data
- any real `raw_match_data` write requires separate authorization and pg_dump

## Mismatch Fixture Validation

Command:

```bash
make data-raw-fixture-dry-run \
  MATCH_ID=47_20242025_900002 \
  FIXTURE=tests/fixtures/match_success.json
```

Result:

- `match_found = true`
- `fixture.exists = true`
- fixture identity: `55_20242025_4803413`
- fixture teams: Chelsea vs Arsenal
- fixture score: `2-0`
- fixture status: `FINISHED`
- target identity: `47_20242025_900002`
- target teams: Burgos vs Oviedo
- target score: `1-0`
- `direct_fixture_match = false`
- `fixture_can_be_used_for_target = false`
- `synthetic_required = true`
- `would_insert_raw_match_data = false`
- `would_update_matches = false`
- `would_trigger_l3 = false`

Warnings:

- `fixture_mismatch:match_id`
- `fixture_mismatch:home_team`
- `fixture_mismatch:away_team`
- `fixture_mismatch:score`
- `cannot_use_this_fixture_as_raw_data_for_target_match`
- `do_not_impersonate_another_match`

Conclusion:

- `tests/fixtures/match_success.json` cannot be used as raw data for `47_20242025_900002`
- no direct fixture currently exists for the target

## Synthetic Preview Validation

Command:

```bash
make data-raw-fixture-dry-run \
  MATCH_ID=47_20242025_900002 \
  FIXTURE=tests/fixtures/match_success.json \
  ALLOW_SYNTHETIC=1
```

Result:

- synthetic preview only
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_production_data = true`
- `would_create_fixture_file = false`
- `would_insert_raw_match_data = false`

Required provenance preview:

- `data_source = synthetic_local_fixture`
- `data_version = PHASE4.41_SYNTHETIC_PREVIEW_ONLY`
- metadata must include:
    - `synthetic=true`
    - `engineering_test_only=true`
    - `not_real_external_data=true`
    - `not_for_training=true`

The synthetic preview did not create a fixture file and did not write DB.

## Commit Gate Validation

Commands:

```bash
make data-raw-fixture-commit || true
make data-raw-fixture-commit \
  MATCH_ID=47_20242025_900002 \
  FIXTURE=tests/fixtures/match_success.json \
  CONFIRM_RAW_FIXTURE_COMMIT=1 || true
```

Results:

- both commands were blocked
- commit remains not wired in Phase 4.41
- no DB writes occurred
- no file was created

## Next Step

Recommended Phase 4.42 options:

- prepare a synthetic local raw fixture runbook for engineering-chain validation only
- identify a legal real raw fixture source and document license / provenance before any local raw write

Any real raw write must be separately authorized, preceded by pg_dump, and scoped to `raw_match_data` only.

## Explicit Non-Execution

This phase did not execute:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `COPY / \copy`
- DB writes
- raw_match_data write
- raw ingest
- file creation
- l3_features write
- match_features_training write
- predictions write
- L3 stitch
- smelt
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
