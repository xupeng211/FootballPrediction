# Phase 4.56C Acquisition Registry Governance

Date: 2026-05-05

## 1. Current Head / Branch

- Starting HEAD: `2df6dc548707efbe1bb2e833426b148e6c10447a`
- Working branch: `feat/acquisition-registry-governance-phase456c`
- Base branch: `main`

## 2. Why the Registry Needed Governance Fields

Phase 4.54 made the acquisition registry good enough for risk gating, and Phase 4.55C made the architectural direction explicit. What was still missing was lifecycle governance:

- who owns an engine
- whether the engine is canonical or legacy
- which layer it belongs to
- what replaces it
- whether it is under watch, quarantine, or deprecation
- whether Codex can move it to the next phase
- whether it already has enough test protection

Phase 4.56C upgrades the registry from a risk list into a governance table.

## 3. New Governance Fields

Each engine now carries:

- `owner`
- `status`
- `intended_layer`
- `replacement_plan`
- `deprecation_status`
- `canonical_entrypoint`
- `allowed_next_phase`
- `test_coverage`

## 4. Status Meaning

- `canonical`: recommended mainline engine
- `gate_only`: usable only through explicit gate / authorization
- `quarantine`: isolated high-risk engine, not for default use
- `deprecation_candidate`: likely to be retired after replacement matures
- `adapter_candidate`: possible source for future narrow adapter extraction
- `legacy_blocked`: legacy path that must remain blocked

## 5. Intended Layer Meaning

- `layer_0_registry_policy`
- `layer_1_source_manifest`
- `layer_2_discovery`
- `layer_3_single_target_acquisition`
- `layer_4_local_staging_normalization`
- `layer_5_local_staging_dry_run`
- `layer_6_small_db_write`
- `layer_7_feature_dry_run`
- `layer_8_training_prediction`
- `legacy_bulk_pipeline`
- `legacy_production_path`
- `unknown`

These values let the registry describe where an engine belongs in the future canonical chain.

## 6. Registry Classification Result

Canonical:

- `real_finished_csv_staging_dry_run`
- `raw_match_data_local_ingest`
- `finished_match_backfill_preflight`

Gate-only:

- `csv_bulk_loader`
- `local_dom_ingestor`

Quarantine:

- `recon_scanner`

Deprecation candidate:

- none by `status`

Adapter candidate:

- `titan_discovery`
- `fetch_and_adapt_euro_leagues`
- `odds_harvest_pipeline`

Legacy blocked:

- `run_production`
- `batch_historical_backfill`
- `total_war_pipeline`
- `titan_marathon`

Additional deprecation watchlist via `deprecation_status`:

- `total_war_pipeline`
- `titan_marathon`

## 7. Gate Audit Upgrade

`scripts/ops/acquisition_engine_gate.js --audit` now reports:

- governance field requirements
- governance completeness
- missing governance fields
- canonical / gate_only / quarantine / deprecation_candidate / adapter_candidate / legacy_blocked groups
- engines requiring user authorization
- engines requiring future network authorization
- engines requiring future DB write authorization
- engines needing unit tests

The audit remains read-only and still does not execute any engine.

## 8. Unit Test Upgrade

`tests/unit/acquisition_engine_gate.test.js` now verifies:

- every engine has all governance fields
- every governance enum is in the allowed value set
- `canonical_entrypoint` is boolean
- audit returns `governance_fields_complete=true`
- audit returns the expected engine category groups
- high-risk blocked behavior still holds
- no-network / no-db / no-engine-execution behavior still holds

## 9. No-Network / No-DB Validation

Validation completed:

- registry JSON parse: passed
- `make data-acquisition-engines`: passed
- `make data-acquisition-engine-audit`: passed with governance completeness
- scaffold dry-run stayed blocked
- `node --test tests/unit/acquisition_engine_gate.test.js`: passed
- `npm test`: passed

Observed scaffold guarantees still hold:

- `would_access_network=false`
- `would_write_db=false`
- `would_execute_engine=false`

## 10. DB Before / After

Before validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

After validation:

- `matches=2`
- `bookmaker_odds_history=2`
- `raw_match_data=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 11. Next Step Recommendation

Two clean next steps remain:

1. Phase 4.57C: choose one `adapter_candidate`, such as `titan_discovery` or `fetch_and_adapt_euro_leagues`, and repair dry-run trust plus no-network tests before any future real-data use.
2. Phase 4.56A: only after the user provides the six real network dry-run parameters, prepare a runbook without immediately touching the network.

## 12. Explicit Non-Execution

Not executed in Phase 4.56C:

- DB writes
- external download
- `curl` / `wget` / `git clone`
- external football data access
- scraping / browser automation
- harvest / ingest
- batch backfill
- real network dry-run execution
- bulk harvest
- model training
- real prediction execution
- model artifact loading
- Docker volume cleanup
- force push
- `git fetch --all`
- `git pull`
- file deletion
