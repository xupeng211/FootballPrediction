# Phase 5.21L2G: raw_match_data versioned schema migration execution

## 1. Executive summary

Phase 5.21L2F confirmed the exact schema migration plan for versioned
`raw_match_data` coexistence:

- from `UNIQUE(match_id)`
- to `UNIQUE(match_id, data_version)`

This phase adds the controlled schema-only migration executor. It is authorized
only for the `raw_match_data` uniqueness constraint migration and must not write
raw data rows, touch FotMob, run parser/features, or run training/prediction.

The real migration is intentionally executed only after this PR is merged and
main push CI is green.

## 2. Pre-execution baseline

Read-only baseline before PR work:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   10 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Pre-execution schema/data checks:

| check                                                |               result |
| ---------------------------------------------------- | -------------------: |
| `raw_match_data_match_id_key` exists                 |                 true |
| `raw_match_data_match_id_data_version_key` exists    |                false |
| `data_version IS NULL` rows                          |                    0 |
| duplicate `(match_id, data_version)` rows            |                    0 |
| target `external_id=4830747` only has current v1 row |                 true |
| target `4830747` data_version                        | `fotmob_html_hyd_v1` |

## 3. Migration executed

Execution is performed post-merge only, after main push CI success, using:

```bash
make data-raw-match-data-versioned-schema-migration-execute \
  SOURCE=fotmob \
  TABLE=raw_match_data \
  CURRENT_UNIQUE=match_id \
  TARGET_UNIQUE=match_id,data_version \
  CURRENT_CONSTRAINT=raw_match_data_match_id_key \
  TARGET_CONSTRAINT=raw_match_data_match_id_data_version_key \
  FINAL_SCHEMA_MIGRATION_CONFIRMATION=yes \
  ALLOW_DB_WRITE=yes \
  ALLOW_SCHEMA_MIGRATION=yes \
  ALLOW_ALTER_TABLE=yes \
  ALLOW_RAW_MATCH_DATA_WRITE=no \
  ALLOW_MATCHES_WRITE=no \
  ALLOW_PARSER_FEATURES=no \
  ALLOW_TRAINING=no \
  ALLOW_PREDICTION=no
```

The executor is restricted to a single transaction:

```sql
BEGIN;
ALTER TABLE raw_match_data DROP CONSTRAINT raw_match_data_match_id_key;
ALTER TABLE raw_match_data ADD CONSTRAINT raw_match_data_match_id_data_version_key UNIQUE (match_id, data_version);
COMMIT;
```

The execution summary is expected to report:

- `schema_migration_executed=true`
- transaction began and committed
- `raw_match_data_write_executed=false`
- `matches_write_executed=false`
- `fotmob_access_executed=false`
- `parser_features_executed=false`
- `training_executed=false`
- `prediction_executed=false`

## 4. Post-migration verification

Post-migration verification must confirm:

- `raw_match_data_match_id_key` absent
- `raw_match_data_match_id_data_version_key` present
- `UNIQUE (match_id, data_version)` present
- FK/check constraints still present:
    - `raw_match_data_match_id_fkey`
    - `collected_at_not_null`
    - `match_id_format`
    - `raw_data_has_match_id`
    - `raw_data_not_empty`
- existing indexes still present:
    - `idx_raw_data_match_id`
    - `idx_raw_data_external_id`
    - `idx_raw_data_collected_at`
    - `idx_raw_data_version_collected`
    - `idx_raw_data_gin`
- row counts unchanged:
    - `matches=10`
    - `raw_match_data=10`
    - `bookmaker_odds_history=2`
    - `l3_features=2`
    - `match_features_training=2`
    - `predictions=2`
- target `4830747` still has only `fotmob_html_hyd_v1`

## 5. Compatibility warning

After the schema migration, legacy/admin writers that still use
`ON CONFLICT (match_id)` are risky and may fail because `match_id` is no longer a
unique conflict target.

Known follow-up requirements:

- controlled v2 writer must use conflict target `(match_id, data_version)`
- existing-row lookup must include `data_version`
- readers must filter `data_version` explicitly or use a canonical selector
- canonical selector is still needed:
    - prefer `fotmob_pageprops_v2`
    - fallback `fotmob_html_hyd_v1`
    - exclude synthetic/unknown versions by default
- parser/features/training remain deferred

## 6. Recommended next phases

Recommended next phase:

1. Phase 5.21L2H: version-aware `raw_match_data` writer/reader compatibility
   planning or implementation
    - no DB write
    - no FotMob access
    - update controlled writer/read existing-row lookup to include `data_version`
    - add canonical selector helper
    - no parser/features/training

Then:

2. Phase 5.21L2I: pageProps v2 single-target write preflight
    - no DB write
    - recapture `4830747` pageProps
    - compute stable hash
    - SELECT existing v1/v2 rows

Do not directly enter v2 write before the version-aware compatibility work or
preflight is complete.

## 7. Explicit non-execution

This phase does not authorize or perform:

- external FotMob access
- live match detail request
- `raw_match_data` row writes
- `matches` writes
- data row migration
- v1 rewrite
- parser/features
- harvest/ingest/backfill
- training/prediction
- browser/proxy
- full raw_data print/save
- file deletion
