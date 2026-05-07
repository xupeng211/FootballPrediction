# Football-Data Adapter Dry-Run Gate Phase 4.63C

## Current HEAD / Branch

- Starting main HEAD: `b5afdee34be668100fe2943a1bc51ba0c4da744b`
- Working branch: `feat/football-data-adapter-dry-run-phase463c`
- Phase: `4.63C`

## Why This PR Is One Cohesive Step

Phase 4.62C delivered the pure Football-Data CSV parser and kept the legacy downloader runtime blocked. Phase 4.63C is the next local-only integration step: it connects the parser to a local source manifest and local CSV dry-run gate. Keeping the script, fixture, Makefile entry, tests, AGENTS update, and report together is reasonable because they define one governed operator surface.

This phase still does not download external data, does not create staging files, does not read or write the database, and does not train or predict.

## New Files

- `scripts/ops/football_data_adapter_dry_run.js`
- `tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json`
- `tests/unit/football_data_adapter_dry_run.test.js`
- `docs/_reports/FOOTBALL_DATA_ADAPTER_DRY_RUN_PHASE4_63C.md`

Updated files:

- `Makefile`
- `AGENTS.md`

## Dry-Run Gate Design

The new gate is:

```bash
make data-football-data-csv-dry-run \
  SOURCE_MANIFEST=<local json> \
  LOCAL_CSV=<local csv>
```

The Makefile target runs inside the `dev` container:

```bash
node scripts/ops/football_data_adapter_dry_run.js \
  --source-manifest <path> \
  --local-csv <path>
```

The script only reads local files supplied by the caller and imports the pure parser:

- no network modules
- no `pg`
- no DB reads
- no DB writes
- no file writes
- no adapted CSV writes
- no staging writes
- no `child_process`
- no legacy `fetch_and_adapt_euro_leagues.js` runtime import

## Source Manifest Validation

Required manifest fields:

- `source_name`
- `approval_status`
- `sha256`
- `row_count`
- `local_csv_path`
- `mapping_version`

Allowed `approval_status` values:

- `dry_run_only`
- `approved_for_dry_run`

The fixture manifest is synthetic local test data only:

- `source_name=football_data_local_synthetic_fixture`
- `source_type=local_csv_fixture`
- `license_type=synthetic_test_fixture`
- `allowed_use=engineering_tests_only`
- `not_real_external_data=true`
- `not_for_training=true`
- `not_for_production=true`

## Integrity Checks

The gate computes the local CSV `sha256` and row count before parser execution.

Fixture values:

- CSV: `tests/fixtures/football_data/football_data_sample_phase462c.csv`
- sha256: `d6681446dc08f44987aa50fec79e50091b12ff18a6808e2b4d4b703ed806605d`
- row_count: `5`

If `sha256` does not match, the gate fails and does not call the parser.

If `row_count` does not match, the gate fails and does not call the parser.

## Parser Integration

The gate calls:

```js
parseFootballDataCsv(csvText, {
    sourceName: manifest.source_name,
    dataVersion: manifest.mapping_version,
    defaultSeason: manifest.default_season || manifest.season || '2024/2025',
    timezone: manifest.timezone || 'UTC',
});
```

Parser output is surfaced as dry-run summary and preview only:

- `total_rows`
- `parsed_rows`
- `row_classification`
- `candidate_preview`
- parser warnings
- parser non-execution confirmations

Odds columns remain preview only. `would_insert_matches=false` and `would_insert_odds=false` are emitted by both parser candidates and the dry-run gate summary.

## Local Dry-Run Output Summary

Command:

```bash
make data-football-data-csv-dry-run \
  SOURCE_MANIFEST=tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json \
  LOCAL_CSV=tests/fixtures/football_data/football_data_sample_phase462c.csv
```

Observed summary:

- `source_manifest_found=true`
- `local_csv_found=true`
- `sha256_match=true`
- `row_count_match=true`
- `parser_version=PHASE4.62C_FOOTBALL_DATA_LOCAL_CSV_PARSER`
- `total_rows=5`
- `trainable_label_rows=3`
- `skipped_rows=2`
- `invalid_date_rows=1`
- `missing_score_rows=1`
- `odds_preview_rows=3`
- `would_insert_matches=false`
- `would_insert_odds=false`
- `would_write_db=false`
- `would_access_network=false`
- `would_write_files=false`

Non-execution confirmations:

- `no_external_network`
- `no_db_reads`
- `no_db_writes`
- `no_file_writes`
- `no_legacy_runtime`
- `no_training`
- `no_prediction_execution`
- `no_model_artifact_load`
- `no_adapted_csv_writes`
- `no_staging_writes`

## Commit Gate

New commit target:

```bash
make data-football-data-csv-commit \
  SOURCE_MANIFEST=<path> \
  LOCAL_CSV=<path> \
  CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1
```

Phase 4.63C result:

- blocked
- not wired
- no DB writes
- no external network
- no staging or adapted CSV writes

Observed blocked output:

```text
BLOCKED: football-data CSV commit is not wired in Phase 4.63C.
```

## Unit Tests

New test:

```bash
docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/football_data_adapter_dry_run.test.js
```

Covered behavior:

- missing source manifest argument fails
- missing local CSV argument fails
- valid manifest + CSV succeeds
- CLI `--help`, `--source-manifest=<path>`, `--local-csv=<path>`, and text output work
- output safety flags are false
- `sha256` mismatch fails before parser execution
- `row_count` mismatch fails before parser execution
- disallowed `approval_status` fails
- missing CSV path fails
- malformed manifest JSON fails
- invalid manifest `row_count` fails
- unknown CLI argument fails
- `--commit` is blocked
- no legacy runtime import
- no network calls
- no DB imports
- no child process calls
- no file writes

Result:

- `pass 11`
- `fail 0`

## Validation Results

Targeted validation:

- `football_data_adapter_dry_run.test.js`: passed
- `football_data_local_csv_parser.test.js`: passed
- `fetch_and_adapt_euro_leagues_no_network.test.js`: passed
- `acquisition_engine_gate.test.js`: passed

Full validation:

- `npm test`: passed
- `npm run test:coverage`: passed
- `eslint`: passed
- `prettier`: passed
- `git diff --check`: passed

Coverage gate summary:

- lines: `87.76`
- statements: `87.76`
- functions: `80.32`
- branches: `80.06`

## Old Acquisition Gate Verification

Commands run:

- `make data-acquisition-engine-audit`
- `make data-single-target-network-dry-run ...`
- `make data-single-target-network-commit ...`

Observed safety posture remains:

- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`
- `fetch_and_adapt_euro_leagues` scaffold gate blocked
- commit gate blocked

## DB Before / After Statistics

Before Phase 4.63C implementation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

After Phase 4.63C validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## Next Steps

- Phase 4.64C: design a small DB write preflight / backup runbook, but still do not directly write DB.
- Or Phase 4.56A: if the user provides the complete real network dry-run parameters, first write a runbook rather than touching the network directly.

Without complete real network dry-run parameters and explicit authorization, Codex still must not access external football or odds data sources.

## Explicitly Not Executed

- DB writes
- DB reads from parser or dry-run gate
- parser / dry-run file writes
- external downloads
- `curl`
- `wget`
- `git clone`
- external football data source access
- external odds data source access
- scraping
- browser automation
- harvest
- ingest
- batch backfill
- real network dry-run execution
- bulk harvest
- adapted CSV / staging data writes
- model training
- real prediction execution
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
