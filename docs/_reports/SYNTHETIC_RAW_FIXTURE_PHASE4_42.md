# Phase 4.42 - Synthetic Raw Fixture For Finished Match

## Current HEAD

- Base HEAD: `78a95fed9d855813fe69295130617fcaa9f62215`
- Working branch: `feat/synthetic-raw-fixture-phase442`
- Phase 4.41 report present: `docs/_reports/RAW_FIXTURE_ADAPTER_DRY_RUN_PHASE4_41.md`
- Phase 4.40 report present: `docs/_reports/FINISHED_MATCH_BACKFILL_PREFLIGHT_PHASE4_40.md`

## Current DB Row Counts

Row counts before and after Phase 4.42 validation remained unchanged:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |    2 |
| bookmaker_odds_history  |    2 |
| raw_match_data          |    1 |
| l3_features             |    1 |
| match_features_training |    1 |
| predictions             |    1 |

`make data-dataset-status` remains SELECT-only and reports:

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

The match is a valid finished label row but still has no downstream raw/L3/training/prediction rows.

## Synthetic Fixture

Added:

```text
tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json
```

The fixture matches the target match shape:

- `matchId = 47_20242025_900002`
- home team: `Burgos`
- away team: `Oviedo`
- score: `1-0`
- status: `finished`
- includes `general`
- includes `header`
- includes `content`
- includes minimal `stats`, `lineup`, `shotmap`, and `momentum`

Synthetic metadata:

- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `source = phase4.42_synthetic_local_fixture`
- `target_match_id = 47_20242025_900002`
- provenance note explicitly says it is locally created synthetic data for engineering validation only

This fixture does not claim to come from FotMob, OddsPortal, or any external provider.

## Why This Is Synthetic Only

This fixture was created locally to validate adapter and pipeline shape behavior after Phase 4.41 confirmed there is no direct raw fixture for Burgos vs Oviedo.

It is not real match data because:

- it was not downloaded from an external source
- it was not harvested by the production pipeline
- its stats, lineup, shotmap, and momentum are minimal test-shape placeholders
- its metadata explicitly marks it synthetic and engineering-test-only

It cannot be used for real training because:

- synthetic values would contaminate model labels/features
- it does not represent real event, lineup, odds, or feature data
- Phase 4.35 and Phase 4.36 require real finished historical samples and feature timing proof before training
- the dataset remains far below training threshold

## Adapter Enhancement

Updated `scripts/ops/raw_fixture_adapter_dry_run.js` to recognize `metadata.synthetic`.

New synthetic behavior:

- synthetic fixtures are always `preview_only=true`
- synthetic fixtures do not become usable real raw fixtures
- without `ALLOW_SYNTHETIC=1`, the adapter emits explicit warnings
- with `ALLOW_SYNTHETIC=1`, the adapter emits preview-only synthetic metadata
- `would_insert_raw_match_data=false` in all cases
- `would_update_matches=false`
- `would_trigger_l3=false`
- `no_db_writes`
- `no_file_create`

Makefile already supported:

```text
make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<path> ALLOW_SYNTHETIC=1
```

so no Makefile change was required.

## AGENTS.md Update

Updated safety rules to allow synthetic raw fixture creation only when:

- user explicitly authorizes it
- fixture path is under `tests/fixtures/synthetic/`
- fixture marks `synthetic=true`
- fixture marks `engineering_test_only=true`
- fixture marks `not_real_external_data=true`
- fixture marks `not_for_training=true`
- fixture marks `not_for_production=true`
- fixture is only for engineering-chain tests
- no DB writes occur
- fixture is not used for real training

Added prohibitions:

- do not mark synthetic fixture as real external / FotMob / OddsPortal data
- do not train with synthetic fixture
- do not write synthetic fixture as production data
- do not write `raw_match_data` without separate authorization
- do not use mismatched fixtures to impersonate target matches

## Validation: Missing Args

Command:

```bash
make data-raw-fixture-dry-run || true
```

Result:

- failed as expected
- message: `ERROR: provide MATCH_ID=<id> and FIXTURE=<path>`

## Validation: Synthetic Fixture Without ALLOW_SYNTHETIC

Command:

```bash
make data-raw-fixture-dry-run \
  MATCH_ID=47_20242025_900002 \
  FIXTURE=tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json || true
```

Result:

- `match_found = true`
- `fixture.exists = true`
- `direct_fixture_match = true`
- `fixture_can_be_used_for_target = false`
- `synthetic = true`
- `preview_only = true`
- `synthetic_preview_allowed = false`
- `would_insert_raw_match_data = false`
- `would_update_matches = false`
- `would_trigger_l3 = false`

Warnings:

- `synthetic_fixture_requires_explicit_ALLOW_SYNTHETIC_1`
- `synthetic_fixture_not_for_training`

Conclusion:

- fixture identity matches target match
- fixture is synthetic and cannot be used as real raw data without explicit synthetic preview authorization
- no DB writes occurred

## Validation: Synthetic Fixture With ALLOW_SYNTHETIC

Command:

```bash
make data-raw-fixture-dry-run \
  MATCH_ID=47_20242025_900002 \
  FIXTURE=tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json \
  ALLOW_SYNTHETIC=1
```

Result:

- `match_found = true`
- `fixture.exists = true`
- `direct_fixture_match = true`
- `fixture_can_be_used_for_target = false`
- `synthetic = true`
- `engineering_test_only = true`
- `not_real_external_data = true`
- `not_for_training = true`
- `not_for_production = true`
- `preview_only = true`
- `synthetic_preview_allowed = true`
- `would_insert_raw_match_data = false`
- `would_update_matches = false`
- `would_trigger_l3 = false`
- no warnings

Non-execution confirmations included:

- `no_db_writes`
- `no_insert`
- `no_update`
- `no_delete`
- `no_raw_ingest`
- `no_l3_write`
- `no_training`
- `no_prediction_execution`
- `no_model_artifact_load`
- `no_external_network`
- `no_file_create`

## Validation: Mismatch Fixture Still Rejected

Command:

```bash
make data-raw-fixture-dry-run \
  MATCH_ID=47_20242025_900002 \
  FIXTURE=tests/fixtures/match_success.json || true
```

Result:

- fixture identity: `55_20242025_4803413`
- fixture teams: Chelsea vs Arsenal
- fixture score: `2-0`
- target teams: Burgos vs Oviedo
- target score: `1-0`
- `direct_fixture_match = false`
- `fixture_can_be_used_for_target = false`
- `would_insert_raw_match_data = false`

Warnings:

- `fixture_mismatch:match_id`
- `fixture_mismatch:home_team`
- `fixture_mismatch:away_team`
- `fixture_mismatch:score`
- `cannot_use_this_fixture_as_raw_data_for_target_match`
- `do_not_impersonate_another_match`

## Commit Gate Validation

Commands:

```bash
make data-raw-fixture-commit || true
make data-raw-fixture-commit \
  MATCH_ID=47_20242025_900002 \
  FIXTURE=tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json \
  CONFIRM_RAW_FIXTURE_COMMIT=1 || true
```

Results:

- both commands were blocked
- commit remains not wired
- no DB writes occurred
- no extra files were created

## Next Step

Recommended Phase 4.43 options:

- manually authorize one synthetic `raw_match_data` insert for engineering-chain validation only
- continue searching for a legal real raw fixture source before any real-data backfill

Any real DB write must be separately authorized, preceded by pg_dump, and must remain scoped to one table and one match.

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
