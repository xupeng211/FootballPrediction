# Phase 5.21L2H: raw_match_data version-aware compatibility

## 1. Executive summary

Phase 5.21L2G completed the schema migration from `UNIQUE(match_id)` to
`UNIQUE(match_id, data_version)` for `raw_match_data`.

This phase adds version-aware writer/reader compatibility for the controlled L2
paths. It introduces a canonical selector helper, adds a SELECT-only
compatibility audit, and updates controlled preflight/write scripts to use
`match_id + data_version` when checking existing raw rows or planning conflict
targets.

This phase does not write DB rows, touch FotMob, run parser/features, or run
training/prediction.

## 2. Current DB baseline

Read-only baseline at phase start:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   10 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Protected downstream tables remain at 2 rows each:

- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

Schema baseline:

- `raw_match_data_match_id_key`: absent
- `raw_match_data_match_id_data_version_key`: present
- unique constraint: `UNIQUE (match_id, data_version)`

Data version distribution:

| data_version          | rows |
| --------------------- | ---: |
| `PHASE4.23`           |    1 |
| `PHASE4.43_SYNTHETIC` |    1 |
| `fotmob_html_hyd_v1`  |    8 |

Other findings:

- duplicate `(match_id, data_version)` rows: 0
- `external_id=4830747`: only `fotmob_html_hyd_v1` exists

## 3. Canonical selector policy

`RawMatchDataVersionSelector` defines canonical raw version selection:

1. Prefer `fotmob_pageprops_v2`.
2. Fallback to `fotmob_html_hyd_v1`.
3. Exclude `PHASE4.43_SYNTHETIC`, `PHASE4.23`, and unknown versions by default.
4. Treat duplicate rows for the same `(match_id, data_version)` as a controlled
   error.

The helper also exposes a version-aware lookup spec:

- where clause: `match_id = $1 AND data_version = $2`
- conflict target: `(match_id, data_version)`

## 4. Controlled writer/preflight updates

Updated controlled paths:

| file                                                               | update                                                                                                                                                                                     |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `scripts/ops/l2_raw_match_data_ingest_preflight.js`                | existing raw row lookup now filters by `match_id + data_version`; output includes `existing_raw_match_data_lookup` and affected preview includes `data_version`                            |
| `scripts/ops/l2_raw_match_data_write.js`                           | existing-row and verification lookups filter by `match_id + data_version`; insert uses `ON CONFLICT (match_id, data_version) DO NOTHING`                                                   |
| `scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js` | per-target existing lookup receives `match_id`, `external_id`, and `data_version`; output includes `data_version`                                                                          |
| `scripts/ops/l2_remaining_raw_match_data_write.js`                 | existing-row and post-write metadata lookups filter by `match_id + data_version`; insert uses `ON CONFLICT (match_id, data_version) DO NOTHING`; per-target output includes `data_version` |

No controlled write script is executed in this phase.

## 5. Remaining legacy risks

The following legacy/admin/high-risk paths are not broadly refactored in this
phase and remain deprecated or agent-blocked until upgraded:

- `src/infrastructure/harvesters/components/Persistence.js`
- `src/infrastructure/harvesters/TitanSlimHarvester.js`
- `src/infrastructure/services/MarathonService.js`
- `scripts/ops/backfill_historical_raw_match_data.js`
- `scripts/ops/seed_fotmob_sample.js`
- `scripts/ops/bulk_import_matches.js`
- `src/database/sql_store.py`
- `scripts/test/end_to_end_test.js`

Known risk pattern:

- `ON CONFLICT(match_id)` may fail after the Phase 5.21L2G schema migration.
- match_id-only raw row reads may return multiple versions after v2 rows exist.
- readers must filter `data_version` or use the canonical selector.

## 6. Verification

Required local validation for this phase:

- `tests/unit/RawMatchDataVersionSelector.test.js`
- `tests/unit/raw_match_data_version_compatibility_audit.test.js`
- `tests/unit/l2_raw_match_data_ingest_preflight.test.js`
- `tests/unit/l2_raw_match_data_write.test.js`
- `tests/unit/l2_remaining_raw_match_data_acquisition_preflight.test.js`
- `tests/unit/l2_remaining_raw_match_data_write.test.js`
- `make data-raw-match-data-version-compatibility-audit ...`
- `npm test`
- `npm run test:coverage`
- `eslint`
- `prettier --check`
- `git diff --check`

Safety verification:

- DB row counts must remain unchanged.
- `tests/fixtures/l1-config-*` residue must be absent.
- `docs/_staging_preview` must be absent.
- PR CI and main push CI must pass before the phase is considered complete.

## 7. Next phase recommendation

Recommended next phase:

Phase 5.21L2I: pageProps v2 single-target write preflight.

Required scope:

- no DB write
- no raw write
- live recapture `4830747` pageProps
- construct `fotmob_pageprops_v2` candidate
- compute `stable_pageprops_payload_v1` hash
- SELECT existing versions for `4830747`
- expect v1 exists and v2 absent
- output would_insert for the v2 row
- no parser/features/training

## 8. Explicit non-execution

This phase does not perform:

- external FotMob access
- live match detail request
- DB writes
- `raw_match_data` writes
- schema migration
- `matches` writes
- parser/features
- harvest/ingest/backfill
- training/prediction
- browser/proxy
- full raw_data print/save
- file deletion
