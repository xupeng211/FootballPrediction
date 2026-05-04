# Phase 4.53A Acquisition Engine Readiness Report

Date: 2026-05-05

## 1. Current Head / Branch

- Starting HEAD: `df354b1bcc10f360ee194f2cb5ae58cb476cf0b3`
- Working branch: `docs/acquisition-engine-readiness-phase453a`
- Base branch: `main`
- Base commit: `df354b1bcc10f360ee194f2cb5ae58cb476cf0b3`

## 2. Obsolete Phase 4.53 Branch Handling

The previous route expected user-provided CSV paths and left an empty local branch:

- Obsolete branch: `docs/real-staging-csv-dry-run-phase453`
- Verified clean before deletion: yes
- Verified branch HEAD matched base HEAD: yes, `df354b1bcc10f360ee194f2cb5ae58cb476cf0b3`
- Deleted with safe `git branch -d`: yes
- Forced deletion used: no

The Phase 4.53 CSV route was abandoned because project real data is expected to be captured through existing acquisition / harvest / ingest engines, then staged and audited before any DB write.

## 3. DB / Dataset Status

Read-only checks were run through the existing safety gates:

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

Dataset status remains:

- `trainable=false`
- `finished_matches=1`
- `trainable_label_rows=1`
- `full_feature_chain_rows=1`
- `baseline_prediction_rows=1`
- `prediction_rows_not_training_labels=2`

The synthetic chain is still useful only for engineering closure. It is not acceptable as real training data or production prediction input.

## 4. Phase 4.51 / 4.52 Summary

Phase 4.51 established the real finished match source strategy:

- Stop adding synthetic data to compensate for missing real samples.
- Require source, license, terms, provenance, schema mapping, and leakage controls before real data import.
- Keep actual result / final score as label only.
- Keep predictions out of training labels.

Phase 4.52 implemented the local real finished CSV staging dry-run gate:

- `make data-real-source-audit SOURCE_MANIFEST=<path>`
- `make data-real-finished-csv-dry-run SOURCE_MANIFEST=<path> SAMPLE_CSV=<path>`
- `make data-real-finished-csv-commit ... CONFIRM_REAL_CSV_COMMIT=1`, still blocked / not wired

Phase 4.53A extends that strategy upstream: acquisition engines must produce controlled local staging artifacts before any manifest audit or CSV / fixture dry-run gate.

## 5. Entrypoint Scan Summary

Read-only scans covered:

- `AGENTS.md`
- `Makefile`
- `package.json`
- `scripts/`
- `src/`
- `docs/`
- `tests/`

The scan found these high-risk acquisition families:

- Production L2 harvest: `run_production.js`, `npm start`, `make dev-harvest`
- L1 discovery: `titan_discovery.js`
- Recon / OddsPortal matching: `recon_scanner.js`
- Historical expansion orchestration: `batch_historical_backfill.js`
- Football-data CSV acquisition: `fetch_and_adapt_euro_leagues.js`
- Odds harvest: `odds_harvest_pipeline.js`, `npm run odds:harvest`
- Total War / Marathon orchestration: `total_war_pipeline.js`, `titan_marathon.js`
- Local ingest / loader utilities: `local_dom_ingestor.js`, `csv_bulk_loader.js`
- Safe local gates: `real_finished_csv_staging_dry_run.js`, `raw_match_data_local_ingest.js`, `finished_match_backfill_preflight.js`

No acquisition, harvest, scrape, browser automation, network dry-run, external download, DB write, training, or prediction command was executed.

## 6. High-Risk Entrypoint Findings

- `run_production.js` initializes `ProductionHarvester`, starts browser/network infrastructure, harvests FotMob targets, and writes `raw_match_data` plus local files unless `dryRun` is honored.
- `ProductionHarvester` inherits `AbstractHarvester`; `dryRun` suppresses `saveData`, but it still performs live network acquisition. It is not safe as an AI-default dry-run.
- `titan_discovery.js` advertises `--dry-run`, but the flag is only visible in CLI output and is not clearly passed into `DiscoveryService.discover`. Treat this as low-trust until fixed and tested.
- `DiscoveryService` uses FotMob HTTP/browser, proxy providers, and `FixtureRepository`; discovery can insert/update matches.
- `recon_scanner.js` delegates to `recon_scanner_impl.js`, which uses OddsPortal routes, browser/network sessions, Redis, proxies, and DB-backed recon stores.
- `batch_historical_backfill.js` is a bulk orchestrator. Its default dry-run still calls the football-data downloader and writes adapted CSV/log artifacts.
- `fetch_and_adapt_euro_leagues.js` always downloads football-data CSV from a configured URL and writes an adapted CSV. It has no safe no-network mode.
- `odds_harvest_pipeline.js` uses Playwright and direct fetches against OddsPortal, then upserts odds/mapping and may trigger L3.
- `total_war_pipeline.js` orchestrates discovery, harvest, recon, and smelt. Its `--dry-run` avoids child task execution, but it still initializes runtime state and DB metrics, so it is not an acquisition source dry-run.
- `titan_marathon.js` is a large harvest reconciler. Full mode uses Playwright/network and writes `raw_match_data` / `matches`; its `--dry-run` only previews DB pending count but is not an approved real source gate.
- `local_dom_ingestor.js` and `csv_bulk_loader.js` are local-only in dry-run, but their `--commit` paths write DB and must remain blocked for AI.

## 7. Acquisition Engine Classification Matrix

| entrypoint                          | command                                                                 | source / target                      | expected output                                           | writes_db                                         | accesses_network    | writes_files                        | supports_dry_run          | dry_run_trust_level                             | supports_commit                | bulk_risk           | ToS / license risk                    | provenance_required | safe_for_ai_default                     | required_user_authorization                                              | notes |
| ----------------------------------- | ----------------------------------------------------------------------- | ------------------------------------ | --------------------------------------------------------- | ------------------------------------------------- | ------------------- | ----------------------------------- | ------------------------- | ----------------------------------------------- | ------------------------------ | ------------------- | ------------------------------------- | ------------------- | --------------------------------------- | ------------------------------------------------------------------------ | ----- |
| `real_finished_csv_staging_dry_run` | `make data-real-source-audit`, `make data-real-finished-csv-dry-run`    | local manifest + local CSV           | manifest audit, CSV integrity, mapping, duplicate preview | no                                                | no                  | no                                  | yes                       | high                                            | commit flag exists but blocked | low                 | low if local provenance is complete   | yes                 | yes, with explicit user authorization   | Phase 4.52 safe gate; SELECT-only DB duplicate check                     |
| `raw_match_data_local_ingest`       | `make data-raw-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>`                 | local raw fixture                    | raw ingest preview                                        | no                                                | no                  | no                                  | yes                       | high                                            | commit flag exists but blocked | low                 | low if fixture provenance is complete | yes                 | yes, with explicit user authorization   | Local fixture only; commit blocked                                       |
| `finished_match_backfill_preflight` | `make data-finished-backfill-dry-run MATCH_ID=<id>`                     | local DB plus optional local fixture | chain readiness preview                                   | no                                                | no                  | no                                  | yes                       | high                                            | commit flag exists but blocked | low                 | depends on fixture                    | yes                 | yes, with explicit user authorization   | SELECT-only DB audit                                                     |
| `csv_bulk_loader`                   | `node scripts/ops/csv_bulk_loader.js --file <path>`                     | local adapted CSV                    | parsed match / odds preview, error log                    | no in dry-run; yes with `--commit`                | no                  | yes, error log                      | yes                       | medium-high                                     | yes                            | high with large CSV | medium; depends on CSV source         | yes                 | dry-run only through approved make gate | `--commit` updates `matches` and upserts `bookmaker_odds_history`        |
| `local_dom_ingestor`                | `node scripts/ops/local_dom_ingestor.js --file <path>`                  | local HTML / clipboard               | odds preview                                              | no in dry-run; yes with `--commit`                | no                  | no                                  | yes                       | medium-high for file; lower for clipboard       | yes                            | medium              | medium; copied DOM needs provenance   | yes                 | dry-run only through approved make gate | `--commit` writes `bookmaker_odds_history`; clipboard provenance is weak |
| `run_production`                    | `node scripts/ops/run_production.js` / `npm start` / `make dev-harvest` | FotMob / configured pending matches  | raw match JSON, DB raw data, local files                  | yes unless trusted dry-run                        | yes                 | yes                                 | yes                       | medium for no writes, unsafe for network        | no explicit commit flag        | high                | high                                  | yes                 | no                                      | `--dry-run` still performs live acquisition                              |
| `titan_discovery`                   | `node scripts/ops/titan_discovery.js`                                   | FotMob discovery                     | match seeds                                               | likely yes                                        | yes                 | no                                  | advertised                | low                                             | no                             | high                | high                                  | yes                 | no                                      | `--dry-run` is not clearly passed to service layer                       |
| `recon_scanner`                     | `node scripts/ops/recon_scanner.js --season ...`                        | OddsPortal results / standings       | mapping, recon status, dictionary updates                 | yes                                               | yes                 | runtime artifacts possible          | no safe default           | low                                             | no                             | high                | high                                  | yes                 | no                                      | Browser/network/Redis/proxy + DB status updates                          |
| `batch_historical_backfill`         | `node scripts/ops/batch_historical_backfill.js`                         | football-data + FotMob + local DB    | adapted CSV, loader output, ELO/L3 orchestration          | yes with `--commit`; downstream risk even dry-run | yes                 | yes                                 | yes                       | low                                             | yes                            | very high           | high                                  | yes                 | no                                      | Default dry-run still downloads and writes staging/log artifacts         |
| `fetch_and_adapt_euro_leagues`      | `node scripts/ops/fetch_and_adapt_euro_leagues.js`                      | football-data CSV URL                | adapted CSV                                               | reads DB only                                     | yes                 | yes                                 | no                        | none                                            | no                             | medium-high         | high                                  | yes                 | no                                      | Always downloads external CSV and writes output                          |
| `odds_harvest_pipeline`             | `npm run odds:harvest`                                                  | OddsPortal                           | odds snapshots, mapping, optional L3                      | yes                                               | yes                 | runtime artifacts possible          | not a safe source dry-run | low                                             | no                             | high                | high                                  | yes                 | no                                      | Uses Playwright, fetch, DB upserts, and optional L3 trigger              |
| `total_war_pipeline`                | `npm run titan:total-war`                                               | Discovery + Harvest + Recon + Smelt  | orchestrated pipeline progress                            | yes outside dry-run                               | yes outside dry-run | yes runtime state/logs              | yes                       | medium for scheduler only; not acquisition-safe | no                             | very high           | high                                  | yes                 | no                                      | `--dry-run` avoids child tasks but still reads DB/writes runtime state   |
| `titan_marathon`                    | `node scripts/ops/titan_marathon.js`                                    | FotMob pending matches               | raw data backfill                                         | yes outside dry-run                               | yes outside dry-run | possible dead-letter/runtime output | yes                       | medium for DB-count preview only                | no                             | very high           | high                                  | yes                 | no                                      | Full mode inserts `raw_match_data` and updates `matches`                 |
| `data-network-dry-run`              | `make data-network-dry-run`                                             | future runbook-defined source        | none in Phase 4.53A                                       | no default                                        | no default          | no default                          | blocked placeholder       | high because blocked                            | no                             | blocked             | depends on future source              | yes                 | no                                      | no, until a future phase wires a specific single-target gate             |
| `data-harvest`                      | `make data-harvest`                                                     | bulk harvest runbook                 | none unless authorized                                    | blocked by gate                                   | blocked by gate     | blocked by gate                     | no                        | high because blocked                            | runbook-dependent              | very high           | high                                  | yes                 | no                                      | Requires runbook, backup, monitoring, explicit authorization             |

## 8. Safe Entrypoints vs Dangerous Entrypoints

Safe AI-default or near-safe with explicit user authorization:

- `make data-help`
- `make data-check`
- `make data-schema-status`
- `make data-dataset-status`
- `make data-real-source-audit SOURCE_MANIFEST=<local json>`
- `make data-real-finished-csv-dry-run SOURCE_MANIFEST=<local json> SAMPLE_CSV=<local csv>`
- `make data-raw-dry-run SAMPLE_RAW=<local fixture> MATCH_ID=<id>`
- `make data-finished-backfill-dry-run MATCH_ID=<id>`

Dangerous or blocked for AI default:

- `npm start`
- `make dev-harvest`
- `make data-harvest`
- `make data-network-dry-run`
- `node scripts/ops/run_production.js`
- `node scripts/ops/titan_discovery.js`
- `node scripts/ops/recon_scanner.js --season ...`
- `node scripts/ops/batch_historical_backfill.js`
- `node scripts/ops/fetch_and_adapt_euro_leagues.js`
- `npm run odds:harvest`
- `npm run titan:total-war`
- `node scripts/ops/titan_marathon.js`
- any `--commit` acquisition / ingest command

## 9. Correct Data Flow Design

Recommended controlled flow:

```text
target source
  -> acquisition engine network dry-run
  -> local staging file
  -> source manifest
  -> data-real-source-audit
  -> data-real-finished-csv-dry-run / raw fixture dry-run
  -> manual approval
  -> pg_dump
  -> small DB write
  -> DB validation
  -> later feature dry-run
```

Explicitly forbidden direct flow:

```text
target source
  -> bulk harvest
  -> DB commit
  -> training
```

The staging artifact must be immutable for the report: record `sha256`, row count or object count, source URL, capture timestamp, engine version, requested target, and approval status.

## 10. Source Manifest / Provenance Requirements

Every real acquisition output must be paired with a source manifest before dry-run gates treat it as candidate real data.

Minimum manifest fields:

- `source_name`
- `source_type`
- `source_url`
- `license_url`
- `terms_url`
- `license_type`
- `allowed_use`
- `attribution_required`
- `commercial_use_allowed`
- `redistribution_allowed`
- `data_owner`
- `downloaded_by`
- `downloaded_at`
- `original_filename`
- `sha256`
- `row_count` or `object_count`
- `field_dictionary`
- `mapping_version`
- `approval_status`
- `human_approval_note`
- `engine_name`
- `engine_version`
- `target_scope`

Allowed Phase 4.54 statuses should be limited to `draft_for_network_dry_run`, `dry_run_only`, or `approved_for_dry_run`. None of these statuses may imply DB write permission.

## 11. ToS / License Risk Notes

- Public availability is not license clearance.
- Browser automation and scraping can violate terms even when rate-limited.
- Login, paywall, anti-bot, or technical access controls must not be bypassed.
- Redistribution, commercial use, and derived database use must be explicitly reviewed.
- Data collected for labels must not leak post-match features into pre-match training.
- A network dry-run authorization must name the target source and scope; generic permission is not enough.

## 12. Phase 4.54 Design

Recommended next phase name:

```text
Phase 4.54: single-target acquisition network dry-run gate
```

Recommended targets:

- Single `match_id`, or
- One very small date window, with explicit row / request cap

Required constraints:

- User explicitly authorizes the target source and target scope.
- User confirms ToS / license / terms have been reviewed enough for a dry-run.
- A source manifest draft exists before network access.
- Output goes only to local staging.
- No DB writes.
- No training.
- No prediction.
- No bulk acquisition.
- No browser automation unless separately authorized.
- No login / paywall / anti-bot bypass.
- Strict rate limit and request cap.
- Capture writes `sha256`, timestamp, `source_url`, engine version, and target scope.
- Report outputs `would_write_db=false`.

Suggested future gates, not implemented in Phase 4.53A:

```text
make data-acquisition-engine-audit
make data-single-target-network-dry-run SOURCE_MANIFEST=<path> TARGET_MATCH_ID=<id>
make data-single-target-network-commit ... CONFIRM_SINGLE_TARGET_NETWORK=1
```

The commit target should remain blocked until a later phase defines backup, pre/post DB stats, small-batch write logic, and rollback.

## 13. AGENTS.md Update Summary

`AGENTS.md` was updated with acquisition engine safety rules:

- AI / Codex default-forbids production harvest, discovery, recon, batch backfill, football-data fetch/adapt, odds harvest, total war, marathon, `data-harvest`, `data-network-dry-run`, and acquisition `--commit` commands.
- AI / Codex may only do source scans, local staging CSV dry-run, source manifest audit, and no-network preflight gates.
- Future network dry-run requires explicit user authorization, tiny target scope, source manifest draft, no DB writes, no bulk, no training, no prediction, no ToS / login / paywall / anti-bot bypass, and staging hash/provenance output.

## 14. Next Steps

Recommended Phase 4.54:

- Implement `single-target acquisition network dry-run gate`.
- Require user to name the target source and target match / date scope.
- Require source manifest draft before any network access.
- Save only local staging artifacts.
- Produce hash/provenance report.
- Keep DB writes blocked.
- Keep training and prediction blocked.

Before any later real write phase:

- Human approval must be separate.
- `pg_dump` backup must be completed.
- Scope must be small.
- Pre/post DB stats must be captured.
- No odds/raw/L3/training/prediction expansion should be bundled into the first write unless separately authorized.

## 15. Explicit Non-Execution Confirmations

Not executed in Phase 4.53A:

- `INSERT` / `UPDATE` / `DELETE` / `CREATE` / `ALTER` / `DROP` / `TRUNCATE`
- `COPY` / export
- DB writes
- external download
- `curl` / `wget` / `git clone`
- external football data source access
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
- network dry-run
- bulk harvest
- Docker volume cleanup
- `git push --force`
- `git push --mirror`
- `git fetch --all`
- `git pull`
- file deletion
