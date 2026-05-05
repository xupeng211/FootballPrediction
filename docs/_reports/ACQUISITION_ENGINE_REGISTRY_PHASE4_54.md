# Phase 4.54 Acquisition Engine Registry Report

Date: 2026-05-05

## 1. Current Head / Branch

- Starting HEAD: `8b6ec702a325f545c86b31b273944c19b5c8c5c7`
- Working branch: `feat/acquisition-engine-registry-phase454`
- Base branch: `main`
- Base commit: `8b6ec702a325f545c86b31b273944c19b5c8c5c7`

## 2. Current DB / Dataset Status

Read-only checks executed:

- `make dev-ps`
- `make data-check`
- `make data-schema-status`
- `make data-dataset-status`
- SELECT-only row count query

Current DB row counts:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Current dataset status:

- `trainable=false`
- `finished_matches=1`
- `trainable_label_rows=1`
- `full_feature_chain_rows=1`
- `baseline_prediction_rows=1`

The DB remains below any real training threshold. Synthetic closure still does not qualify as real training readiness.

## 3. Phase 4.53A Summary

Phase 4.53A established that:

- Real data is expected to come from internal acquisition / harvest / ingest engines, not primarily from user-provided CSV.
- The project contains multiple high-risk entrypoints with different network, DB write, and bulk execution behavior.
- A future single-target network dry-run must be explicitly authorized, small in scope, staged locally, and separated from any DB write phase.

## 4. Why the Entrypoints Needed Cleanup

Before Phase 4.54, the repo had mixed data entrypoints with overlapping names and inconsistent safety meaning:

- some were safe local preflight gates
- some were local loaders with real commit paths
- some advertised dry-run while still touching network
- some were bulk orchestrators that can trigger downstream stages
- some were production runners whose names do not clearly signal DB write risk

This made accidental AI execution riskier than it should be.

## 5. Acquisition Engine Registry Design

Phase 4.54 adds a registry file:

- [config/acquisition_engines.phase454.json](/home/xupeng/FootballPrediction.clean-dev/config/acquisition_engines.phase454.json)

It is a risk registry, not an executor.

Each engine entry records:

- `id`
- `category`
- `entrypoint`
- `commands`
- `accesses_network`
- `writes_db`
- `writes_files`
- `supports_dry_run`
- `dry_run_trust_level`
- `supports_commit`
- `bulk_risk`
- `tos_license_risk`
- `provenance_required`
- `safe_for_ai_default`
- `requires_user_authorization`
- `phase454_policy`
- `notes`

Extra Phase 4.54 scaffold metadata was also recorded:

- `source_manifest_required`
- `target_scope_required`

## 6. Registry Coverage

The registry currently covers 13 engines:

1. `real_finished_csv_staging_dry_run`
2. `raw_match_data_local_ingest`
3. `finished_match_backfill_preflight`
4. `csv_bulk_loader`
5. `local_dom_ingestor`
6. `run_production`
7. `titan_discovery`
8. `recon_scanner`
9. `batch_historical_backfill`
10. `fetch_and_adapt_euro_leagues`
11. `odds_harvest_pipeline`
12. `total_war_pipeline`
13. `titan_marathon`

Registry validation result:

- `registry_found=true`
- `registry_valid=true`
- `total_engines=13`

## 7. High-Risk Engines

The registry classifies these engines as high-risk and blocked in Phase 4.54:

- `csv_bulk_loader`
- `local_dom_ingestor`
- `run_production`
- `titan_discovery`
- `recon_scanner`
- `batch_historical_backfill`
- `fetch_and_adapt_euro_leagues`
- `odds_harvest_pipeline`
- `total_war_pipeline`
- `titan_marathon`

High-risk means one or more of:

- accesses external network
- writes DB
- writes files as part of live staging or runtime state
- supports bulk execution
- has non-trivial ToS / license / provenance risk

## 8. Safe Read-Only Gates

The registry marks these engines as `allowed_read_only` in Phase 4.54:

- `real_finished_csv_staging_dry_run`
- `raw_match_data_local_ingest`
- `finished_match_backfill_preflight`

These are still authorization-gated, but they are local-only or SELECT-only and do not execute real external acquisition.

## 9. acquisition_engine_gate.js Behavior

Phase 4.54 adds:

- [scripts/ops/acquisition_engine_gate.js](/home/xupeng/FootballPrediction.clean-dev/scripts/ops/acquisition_engine_gate.js)

This script:

- reads the Phase 4.54 registry
- lists engines
- audits engine risk classification
- scaffolds future single-target network dry-run preflight
- does not require, spawn, or execute any real acquisition engine
- does not access network
- does not write DB
- does not write staging files

Supported modes:

- `--list`
- `--audit`
- `--engine <id> --target-match-id <id> --source-manifest <path>`
- `--commit`, blocked immediately

For engine mode, the script always emits:

- engine lookup result
- registry policy
- declared network / DB risk
- source manifest requirement
- target scope requirement
- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`

## 10. New Makefile Entrypoints

Phase 4.54 adds:

- `make data-acquisition-engines`
- `make data-acquisition-engine-audit`
- `make data-single-target-network-dry-run ENGINE=<engine> TARGET_MATCH_ID=<id> SOURCE_MANIFEST=<path>`
- `make data-single-target-network-commit ENGINE=<engine> TARGET_MATCH_ID=<id> SOURCE_MANIFEST=<path> CONFIRM_SINGLE_TARGET_NETWORK=1`

Behavior:

- `data-acquisition-engines`: safe registry listing
- `data-acquisition-engine-audit`: safe registry audit
- `data-single-target-network-dry-run`: scaffold-only and blocked in Phase 4.54
- `data-single-target-network-commit`: blocked / not wired even with confirmation

## 11. AGENTS.md Update Summary

`AGENTS.md` now explicitly states:

- AI / Codex may run `make data-acquisition-engines` and `make data-acquisition-engine-audit`.
- AI / Codex may only run `make data-single-target-network-dry-run ...` after explicit user authorization.
- Even with that authorization, the Phase 4.54 command remains scaffold-only and does not touch network.
- AI / Codex must not directly execute `run_production`, `titan_discovery`, `recon_scanner`, `batch_historical_backfill`, `fetch_and_adapt_euro_leagues`, `odds_harvest_pipeline`, `total_war_pipeline`, `titan_marathon`, `npm start`, `make dev-harvest`, `make data-harvest`, or `make data-network-dry-run`.

## 12. Scaffold-Only Validation Results

Validation commands completed:

- registry JSON parse: passed
- `make data-acquisition-engines`: passed
- `make data-acquisition-engine-audit`: passed
- `make data-single-target-network-dry-run` without args: failed as expected
- `make data-single-target-network-dry-run ENGINE=run_production TARGET_MATCH_ID=47_20242025_900002 SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json`: blocked as expected

Observed registry list result:

- `total_engines=13`
- `safe_for_ai_default_count=3`
- `blocked_count=10`
- `no_db_writes`
- `no_external_network`

Observed audit result:

- `registry_found=true`
- `registry_valid=true`
- `high_risk_engines=csv_bulk_loader,local_dom_ingestor,run_production,titan_discovery,recon_scanner,batch_historical_backfill,fetch_and_adapt_euro_leagues,odds_harvest_pipeline,total_war_pipeline,titan_marathon`
- `allowed_read_only_engines=real_finished_csv_staging_dry_run,raw_match_data_local_ingest,finished_match_backfill_preflight`
- `blocked_engines=csv_bulk_loader,local_dom_ingestor,run_production,titan_discovery,recon_scanner,batch_historical_backfill,fetch_and_adapt_euro_leagues,odds_harvest_pipeline,total_war_pipeline,titan_marathon`

Observed scaffold dry-run result:

- `engine_found=true`
- `engine_id=run_production`
- `phase454_policy=blocked`
- `accesses_network=true`
- `writes_db=true`
- `bulk_risk=high`
- `dry_run_trust_level=medium`
- `source_manifest_required=true`
- `target_scope_required=true`
- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`
- blocked reason confirmed: `Phase 4.54 is scaffold-only`

## 13. Commit Gate Blocked Validation

Both commit checks were blocked as required:

- `make data-single-target-network-commit`
- `make data-single-target-network-commit ... CONFIRM_SINGLE_TARGET_NETWORK=1`

Observed behavior:

- no engine execution
- no network access
- no DB writes

## 14. DB Before / After

DB row counts before validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

DB row counts after validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

No DB changes occurred.

## 15. Next Step Recommendation

Recommended Phase 4.55 options:

1. Choose one real target source and one explicit target match, then request a separately authorized real single-target network dry-run.
2. Improve no-network / no-db test coverage for a specific high-risk engine before authorizing any future network contact.

Any future real network dry-run must:

- be explicitly authorized by the user
- name the exact target source
- name the exact target match or very small window
- save only local staging
- avoid DB writes
- avoid training
- avoid prediction
- avoid any ToS / login / paywall / anti-bot bypass

## 16. Explicit Non-Execution Confirmations

Not executed in Phase 4.54:

- `INSERT` / `UPDATE` / `DELETE` / `CREATE` / `ALTER` / `DROP` / `TRUNCATE`
- `COPY` / export
- DB writes
- external download
- `curl` / `wget` / `git clone`
- external football data access
- scraping / browser automation
- harvest / ingest
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- `raw_match_data_local_ingest --commit`
- `smelt`
- `l3:stitch`
- ELO recalculation
- model training
- real prediction execution
- model artifact loading
- `npm run train`
- `npm run predict`
- `npm run predict:dry`
- `npm run predict:json`
- batch backfill
- real network dry-run execution
- bulk harvest
- Docker volume cleanup
- `git push --force`
- `git push --mirror`
- `git fetch --all`
- `git pull`
- file deletion
