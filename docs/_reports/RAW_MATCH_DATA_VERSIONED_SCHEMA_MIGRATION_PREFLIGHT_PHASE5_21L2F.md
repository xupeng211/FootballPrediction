# Phase 5.21L2F: raw_match_data versioned schema migration preflight

## 1. Executive summary

Phase 5.21L2E recommended versioned coexistence for FotMob raw storage:
preserve current `fotmob_html_hyd_v1` rows and insert future
`fotmob_pageprops_v2` rows as additional versions. The blocker is the current
`raw_match_data` identity: `UNIQUE(match_id)`.

This phase performs schema migration planning/preflight only. The target
migration is:

- from `UNIQUE(match_id)`
- to `UNIQUE(match_id, data_version)`

No migration was executed. No `ALTER TABLE`, constraint drop/add, index creation,
DB write, raw row write, parser/features work, training, or prediction occurred.

## 2. Current DB baseline

Read-only baseline:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   10 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Protected tables remained at two rows each:

- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 3. Current schema

`raw_match_data` columns:

| column         | type / default                          | notes                               |
| -------------- | --------------------------------------- | ----------------------------------- |
| `id`           | `bigint`, `nextval(...)`                | primary key                         |
| `match_id`     | `varchar(50)`                           | not null, FK to `matches(match_id)` |
| `external_id`  | `varchar(100)`                          | nullable                            |
| `raw_data`     | `jsonb`                                 | not null                            |
| `collected_at` | `timestamptz default CURRENT_TIMESTAMP` | check-enforced not null             |
| `data_version` | `varchar(20) default 'V26.1'`           | version marker                      |
| `data_hash`    | `varchar(64)`                           | stable payload hash                 |

Constraints:

- `raw_match_data_pkey`: `PRIMARY KEY (id)`
- `raw_match_data_match_id_key`: `UNIQUE (match_id)`
- `raw_match_data_match_id_fkey`: `FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE`
- `collected_at_not_null`: `CHECK (collected_at IS NOT NULL)`
- `match_id_format`: allows legacy `{league}_{season}_{external}` and numeric FotMob IDs
- `raw_data_has_match_id`: `CHECK (raw_data ? 'matchId' OR raw_data ? 'general' OR raw_data ? 'header')`
- `raw_data_not_empty`: `CHECK (raw_data IS NOT NULL AND raw_data <> '{}'::jsonb)`

Indexes:

- `raw_match_data_pkey`: unique btree on `id`
- `raw_match_data_match_id_key`: unique btree on `match_id`
- `idx_raw_data_match_id`: btree on `match_id`
- `idx_raw_data_external_id`: btree on `external_id`
- `idx_raw_data_collected_at`: btree on `collected_at DESC`
- `idx_raw_data_version_collected`: btree on `(data_version, collected_at DESC)`
- `idx_raw_data_gin`: GIN on `raw_data`

Current unique constraint name:

- `raw_match_data_match_id_key`

## 4. Preflight findings

Data quality and migration safety checks:

| check                                     | result |
| ----------------------------------------- | -----: |
| `data_version IS NULL` rows               |      0 |
| duplicate `match_id` rows                 |      0 |
| duplicate `(match_id, data_version)` rows |      0 |
| `UNIQUE(match_id)` exists                 |   true |
| `UNIQUE(match_id, data_version)` exists   |  false |
| `safe_to_plan_migration`                  |   true |

Current data_version distribution:

| data_version          | rows |
| --------------------- | ---: |
| `PHASE4.23`           |    1 |
| `PHASE4.43_SYNTHETIC` |    1 |
| `fotmob_html_hyd_v1`  |    8 |

Target `4830747` current version state:

|  id | match_id              | external_id | data_version         | data_hash                                                          |
| --: | --------------------- | ----------- | -------------------- | ------------------------------------------------------------------ |
|   4 | `53_20252026_4830747` | `4830747`   | `fotmob_html_hyd_v1` | `8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25` |

Conclusion:

- `raw_match_data_match_id_key` exists.
- `UNIQUE(match_id)` exists.
- `UNIQUE(match_id, data_version)` does not exist.
- `data_version` NULL count is 0.
- duplicate `match_id` count is 0.
- duplicate `(match_id, data_version)` count is 0.
- target `4830747` currently has only `fotmob_html_hyd_v1`.

## 5. Migration and schema history

Migration locations / conventions found:

- `database/migrations/` contains versioned SQL migration files.
- `deploy/docker/init_db.sql` contains the Docker init baseline schema.
- `scripts/maintenance/migrations/` contains maintenance SQL migrations.
- `src/database/migrations/versions/001_initial_migration.py` exists for Python-side migration history.

Relevant `raw_match_data` schema history:

- `deploy/docker/init_db.sql`
    - creates `raw_match_data`
    - defines `UNIQUE(match_id)`
    - creates `idx_raw_data_match_id`, `idx_raw_data_collected_at`, and `idx_raw_data_gin`

- `database/migrations/V6.6__hardened_l2_raw_storage.sql`
    - adds `data_version`
    - fills NULL `data_version` values
    - adds `external_id`
    - adds JSON/check constraints
    - creates `idx_raw_data_version_collected`, `idx_raw_data_external_id`, and `idx_raw_data_gin`
    - creates the update timestamp trigger

- `database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql`
    - drops and recreates `match_id_format`
    - allows both legacy three-part IDs and numeric FotMob IDs

No existing migration was found that converts `UNIQUE(match_id)` to
`UNIQUE(match_id, data_version)`.

## 6. Code impact findings

Writers / legacy paths using `ON CONFLICT (match_id)` or match-id identity:

- `src/infrastructure/harvesters/components/Persistence.js`
- `src/infrastructure/harvesters/TitanSlimHarvester.js`
- `src/infrastructure/services/MarathonService.js`
- `scripts/ops/backfill_historical_raw_match_data.js`
- `scripts/ops/seed_fotmob_sample.js`
- `scripts/ops/bulk_import_matches.js`
- `src/database/sql_store.py`
- `scripts/test/end_to_end_test.js`

Controlled writers that later need versioned behavior:

- `scripts/ops/l2_raw_match_data_write.js`
    - currently plain `INSERT INTO raw_match_data`
    - existing-row lookup by `match_id OR external_id`, no `data_version` filter
- `scripts/ops/l2_remaining_raw_match_data_write.js`
    - currently plain `INSERT INTO raw_match_data`
    - existing-row lookup by match/external ids, no `data_version` filter
- future `fotmob_pageprops_v2` writer
    - should use conflict target `(match_id, data_version)`

Readers that need `data_version` filtering or a canonical selector:

- `src/feature_engine/smelter/components/DataFetcher.js`
- `src/feature_engine/smelter/FeatureSmelter.js`
- `scripts/ops/l3_stitch_worker.js`
- `scripts/ops/l3_stitch_pipeline.js`
- `src/services/inference_service.py`
- `src/ml/dataset/dataset_generator.py`
- `src/infrastructure/services/FixtureRepository.js`
- `src/infrastructure/harvesters/ProductionHarvester.js`
- `src/infrastructure/services/MarathonService.js`
- `src/infrastructure/services/recon/MatchCanonicalJanitor.js`
- ops/report scripts that join or query `raw_match_data` by `match_id`

Compatibility policy:

- Future writers must stop assuming `match_id` is unique.
- Future readers must select a `data_version` explicitly or use a canonical
  selector/helper.
- Recommended canonical selector order:
  `fotmob_pageprops_v2` first, then `fotmob_html_hyd_v1`.
- Synthetic / unknown data_versions should be excluded by default from FotMob v2
  fidelity and parser/training paths unless explicitly handled.

## 7. Exact forward migration plan

Planned SQL only; not executed in this phase:

```sql
ALTER TABLE raw_match_data DROP CONSTRAINT raw_match_data_match_id_key;
ALTER TABLE raw_match_data ADD CONSTRAINT raw_match_data_match_id_data_version_key UNIQUE (match_id, data_version);
```

Existing non-unique indexes should be retained:

- `idx_raw_data_match_id`
- `idx_raw_data_external_id`
- `idx_raw_data_collected_at`
- `idx_raw_data_version_collected`
- `idx_raw_data_gin`

No new helper index is required for the initial migration plan because
`idx_raw_data_version_collected` already supports version/time reads and
`idx_raw_data_match_id` already supports match-id lookups. Future reader
profiling may decide whether a helper index like `(match_id, data_version,
collected_at DESC)` is worth planning, but this phase does not execute
`CREATE INDEX`.

## 8. Exact rollback plan

Rollback precondition:

```sql
SELECT match_id
FROM raw_match_data
GROUP BY match_id
HAVING COUNT(*) > 1;
```

The query above must return 0 rows before restoring `UNIQUE(match_id)`. If v2
additional rows have already been written, rollback to single-version uniqueness
is blocked until the multi-version rows are explicitly handled under separate
authorization.

Planned rollback SQL only; not executed in this phase:

```sql
ALTER TABLE raw_match_data DROP CONSTRAINT raw_match_data_match_id_data_version_key;
ALTER TABLE raw_match_data ADD CONSTRAINT raw_match_data_match_id_key UNIQUE (match_id);
```

## 9. Recommended next phases

Recommended next phase:

1. Phase 5.21L2G: controlled schema migration execution
    - only after explicit authorization
    - execute only the constraint migration
    - no raw data writes
    - no parser/features/training

2. Phase 5.21L2H: pageProps v2 single-target write preflight
    - no DB write
    - recapture target `4830747`
    - compare stable hash with L2D preview baseline

3. Phase 5.21L2I: pageProps v2 single-target controlled write
    - only after explicit DB-write authorization
    - insert `fotmob_pageprops_v2` row as additional version
    - preserve existing v1 row

## 10. Explicit non-execution

This phase performed:

- no external FotMob access
- no live match detail request
- no network dry-run
- no DB writes
- no schema migration
- no `ALTER TABLE`
- no constraint drop/add execution
- no `CREATE INDEX` / `DROP INDEX`
- no `raw_match_data` writes
- no `matches` writes
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full raw_data print/save
- no file deletion
