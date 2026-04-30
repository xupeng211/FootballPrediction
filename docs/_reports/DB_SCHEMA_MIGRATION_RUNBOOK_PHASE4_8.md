# Phase 4.8 DB Schema Migration Runbook Draft

> Status: draft only. Do not execute this runbook without explicit human approval.
>
> Scope: PostgreSQL schema preparation for local sample DB writes after Phase 4.5-4.7.
>
> Generated on: 2026-04-30

## 1. Current DB Schema State

Current repository state at reconnaissance time:

- Branch: `main`
- HEAD: `ca20bb5 chore(data): add safety-gated data entrypoints`
- Working tree: clean before this draft was created
- Dev stack: healthy
- DB service: `db`, PostgreSQL via `docker-compose.dev.yml`

Current public tables:

```text
data_collection_log
feature_registry
league_config
match_features_training
matches
odds
predictions
raw_match_data
```

Current row counts:

```text
matches                 0
raw_match_data          0
odds                    0
match_features_training 0
predictions             0
league_config           5
feature_registry        0
data_collection_log     0
```

Missing target tables:

```text
bookmaker_odds_history
matches_oddsportal_mapping
l3_features
```

No visible migration tracking table was found:

```text
alembic_version
schema_migrations
knex_migrations
```

## 2. `init_db.sql` And Migration Relationship

`deploy/docker/init_db.sql` is the Docker bootstrap schema. It creates the base development database shape:

- `matches`
- `raw_match_data`
- `match_features_training`
- `league_config`
- `odds`
- `predictions`
- `feature_registry`
- `data_collection_log`
- update timestamp trigger function and triggers
- default `league_config` seed rows

`database/migrations/` contains later SQL migrations that are not currently reflected in the dev DB. This explains why the DB has the init tables but does not yet have `bookmaker_odds_history`, `matches_oddsportal_mapping`, or `l3_features`.

Important operational point: do not apply `database/migrations/*.sql` through shell glob order. Lexicographic order can place `V12.*` before `V6.*`. Apply files in explicit semantic version order.

## 3. Target Table Migrations

### `matches_oddsportal_mapping`

Migration:

```text
database/migrations/V12.4__create_matches_oddsportal_mapping.sql
```

Creates:

- table `matches_oddsportal_mapping`
- FK: `match_id REFERENCES matches(match_id) ON DELETE CASCADE`
- unique constraint: `(match_id, season)`
- unique index: `(season, oddsportal_hash)`
- indexes on `season`, `status`, `league_name`, `oddsportal_hash`, `is_evidence_only`
- partial pending index
- update timestamp function/trigger
- view `v_mapping_stats`

### `bookmaker_odds_history`

Migration:

```text
database/migrations/V12.5__create_bookmaker_odds_history.sql
```

Creates:

- table `bookmaker_odds_history`
- FK: `match_id REFERENCES matches(match_id) ON DELETE CASCADE`
- unique constraint: `(match_id, bookmaker_name, market_type)`
- JSONB checks for `open_odds`, `close_odds`, `movement_trajectory`, `alignment_meta`
- indexes on `match_id`, `bookmaker_name`, `market_type`, `collected_at`
- update timestamp function/trigger

Follow-up:

```text
database/migrations/V12.8__add_alignment_meta_to_bookmaker_odds_history.sql
```

Current `V12.5` already includes `alignment_meta`, so `V12.8` should be idempotent if applied after `V12.5`.

### `l3_features`

Migration:

```text
database/migrations/V26.4__create_l3_features_table.sql
```

Creates:

- table `l3_features`
- PK/FK: `match_id VARCHAR(50) PRIMARY KEY REFERENCES matches(match_id) ON DELETE CASCADE`
- JSONB feature buckets
- indexes on `external_id`, `computed_at`, and GIN `tactical_features`

## 4. Recommended Migration File List And Order

Recommended explicit order for bringing the current dev DB closer to the SQL blueprint:

```text
database/migrations/V6.5__hardened_matches_schema.sql
database/migrations/V6.6__hardened_l2_raw_storage.sql
database/migrations/V12.2__add_matches_pipeline_status.sql
database/migrations/V12.3__expand_matches_pipeline_status_for_recon.sql
database/migrations/V12.4__create_matches_oddsportal_mapping.sql
database/migrations/V12.5__create_bookmaker_odds_history.sql
database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql
database/migrations/V12.7__add_tactical_stats_to_matches.sql
database/migrations/V12.8__add_alignment_meta_to_bookmaker_odds_history.sql
database/migrations/V26.4__create_l3_features_table.sql
```

Minimum target-table set:

```text
database/migrations/V12.2__add_matches_pipeline_status.sql
database/migrations/V12.3__expand_matches_pipeline_status_for_recon.sql
database/migrations/V12.4__create_matches_oddsportal_mapping.sql
database/migrations/V12.5__create_bookmaker_odds_history.sql
database/migrations/V12.7__add_tactical_stats_to_matches.sql
database/migrations/V12.8__add_alignment_meta_to_bookmaker_odds_history.sql
database/migrations/V26.4__create_l3_features_table.sql
```

For full blueprint compatibility, prefer the full list. For the immediate `local_dom_ingestor --commit` path, `bookmaker_odds_history` is the core table, but the schema should still be migrated under a runbook rather than relying on `local_dom_ingestor` to create the table as a side effect.

## 5. Pre-Apply Backup Plan

Do not run these commands until the migration phase is explicitly approved.

Create a backup directory:

```bash
mkdir -p data/backups
```

Recommended logical backup:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > data/backups/phase48_pre_migration_$(date +%Y%m%d_%H%M%S).dump
```

Optional schema-only backup:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only' \
  > data/backups/phase48_pre_migration_schema_$(date +%Y%m%d_%H%M%S).sql
```

Backup verification:

```bash
ls -lh data/backups/phase48_pre_migration_*.dump
```

## 6. Pre-Apply Read-Only Statistics

Run these before applying migrations.

Table list:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc '
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"
'
```

Target table existence:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc '
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = '\''public'\''
  AND table_name IN (
    '\''bookmaker_odds_history'\'',
    '\''matches_oddsportal_mapping'\'',
    '\''l3_features'\''
  )
ORDER BY table_name;
"
'
```

Baseline counts:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc '
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT '\''matches'\'' AS table_name, COUNT(*) AS rows FROM matches
UNION ALL
SELECT '\''raw_match_data'\'', COUNT(*) FROM raw_match_data
UNION ALL
SELECT '\''odds'\'', COUNT(*) FROM odds
UNION ALL
SELECT '\''match_features_training'\'', COUNT(*) FROM match_features_training
UNION ALL
SELECT '\''predictions'\'', COUNT(*) FROM predictions
UNION ALL
SELECT '\''league_config'\'', COUNT(*) FROM league_config
UNION ALL
SELECT '\''feature_registry'\'', COUNT(*) FROM feature_registry
UNION ALL
SELECT '\''data_collection_log'\'', COUNT(*) FROM data_collection_log;
"
'
```

Target match precondition:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc '
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT COUNT(*) AS target_match_rows
FROM matches
WHERE match_id = '\''140_20252026_4837496'\'';
"
'
```

Expected current result: `0`. That means schema migration alone is not enough for `local_dom_ingestor --commit`; a parent `matches` row is still required.

## 7. Apply Command Draft

Do not execute in Phase 4.8. This is a future command draft only.

Use explicit file order and stop on first error:

```bash
for file in \
  database/migrations/V6.5__hardened_matches_schema.sql \
  database/migrations/V6.6__hardened_l2_raw_storage.sql \
  database/migrations/V12.2__add_matches_pipeline_status.sql \
  database/migrations/V12.3__expand_matches_pipeline_status_for_recon.sql \
  database/migrations/V12.4__create_matches_oddsportal_mapping.sql \
  database/migrations/V12.5__create_bookmaker_odds_history.sql \
  database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql \
  database/migrations/V12.7__add_tactical_stats_to_matches.sql \
  database/migrations/V12.8__add_alignment_meta_to_bookmaker_odds_history.sql \
  database/migrations/V26.4__create_l3_features_table.sql
do
  echo "Applying $file"
  docker compose -f docker-compose.dev.yml exec -T db sh -lc \
    'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$file"
done
```

Do not run:

```bash
node -e "require('./scripts/ops/helpers/dbBlueprint').ensureBlueprintOnCurrentDatabase()"
npm run seed
alembic upgrade head
```

Those are not approved migration commands for this runbook.

## 8. Post-Apply Verification SQL

Run only after a human-approved migration apply.

Verify tables:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc '
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = '\''public'\''
  AND table_name IN (
    '\''bookmaker_odds_history'\'',
    '\''matches_oddsportal_mapping'\'',
    '\''l3_features'\''
  )
ORDER BY table_name;
"
'
```

Verify key columns:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc '
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = '\''public'\''
  AND table_name IN (
    '\''bookmaker_odds_history'\'',
    '\''matches_oddsportal_mapping'\'',
    '\''l3_features'\'',
    '\''matches'\''
  )
  AND column_name IN (
    '\''match_id'\'',
    '\''bookmaker_name'\'',
    '\''market_type'\'',
    '\''alignment_meta'\'',
    '\''pipeline_status'\'',
    '\''home_corners'\'',
    '\''referee'\''
  )
ORDER BY table_name, column_name;
"
'
```

Verify constraints:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc '
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT conrelid::regclass AS table_name, conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid IN (
  '\''bookmaker_odds_history'\''::regclass,
  '\''matches_oddsportal_mapping'\''::regclass,
  '\''l3_features'\''::regclass,
  '\''matches'\''::regclass
)
ORDER BY table_name::text, conname;
"
'
```

Verify row counts did not unexpectedly change:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc '
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT '\''matches'\'' AS table_name, COUNT(*) AS rows FROM matches
UNION ALL
SELECT '\''raw_match_data'\'', COUNT(*) FROM raw_match_data
UNION ALL
SELECT '\''bookmaker_odds_history'\'', COUNT(*) FROM bookmaker_odds_history
UNION ALL
SELECT '\''matches_oddsportal_mapping'\'', COUNT(*) FROM matches_oddsportal_mapping
UNION ALL
SELECT '\''l3_features'\'', COUNT(*) FROM l3_features;
"
'
```

## 9. Rollback Plan

Preferred rollback: restore from the pre-migration backup after explicit approval.

Draft command:

```bash
docker compose -f docker-compose.dev.yml exec -T db sh -lc \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' \
  < data/backups/<approved-pre-migration-backup>.dump
```

Rollback risks:

- `--clean` can drop objects before restore.
- Restore must be treated as a destructive DB operation.
- Do not run rollback unless the user explicitly approves it.

Avoid ad hoc rollback by manually dropping individual tables unless a separate rollback runbook is written and approved.

## 10. Risk Points

- Current DB has no migration tracking table, so applied SQL files cannot be audited by DB state.
- `V6.5` adds stricter `matches` constraints; future inserts must provide lowercase `status` and `YYYY/YYYY` season.
- `V6.6` adds `raw_match_data` constraints; `V12.6` should follow it to allow both legacy and numeric FotMob IDs.
- `bookmaker_odds_history` has a hard FK to `matches(match_id)`. The Phase 4.5 sample match does not currently exist in `matches`.
- `local_dom_ingestor --commit` can create `bookmaker_odds_history` as a side effect, but that is not desirable for controlled schema management.
- `dbBlueprint.ensureBlueprintOnCurrentDatabase()` writes schema to the current DB and is not a read-only status command.
- Cold-start blueprint check creates and drops a temporary database. It is not suitable for this no-write phase.
- `database/migrations/` SQL and Alembic migrations are separate mechanisms; mixing them without a tracking strategy is risky.

## 11. Migration Tracking Recommendation

Yes, implement migration tracking before or during the migration phase.

Minimum recommended design:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  file_name TEXT NOT NULL,
  checksum TEXT NOT NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Then each migration apply should:

1. Compute checksum outside DB.
2. Check `schema_migrations` for the version.
3. Apply the SQL only if absent.
4. Insert the tracking row in the same transaction where possible.
5. Stop if an existing version has a different checksum.

This repository currently has no safe `make data-schema-status` or `make data-schema-migrate` gate. Add those before routine migration use.

## 12. Recommendation For Next Phase

Do not proceed directly to data write commit.

It is reasonable to proceed to a human-authorized migration phase only if the user approves all of:

- Backup location and restore method.
- Exact migration list and order.
- Whether to add `schema_migrations` first.
- Whether stricter V6.5/V6.6 constraints are acceptable in the current dev DB.
- Post-apply verification SQL.

After schema migration succeeds, the next blocker remains the parent match row:

```text
matches.match_id = 140_20252026_4837496
```

That row must be inserted through a separate, explicitly authorized small DB write runbook before `local_dom_ingestor --commit` can safely write odds history for the sample.

## 13. Explicit Non-Execution Confirmation

Phase 4.8 is documentation only. During this phase do not execute:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- migration apply
- seed commit
- `local_dom_ingestor --commit`
- `ensureBlueprintOnCurrentDatabase`
- cold-start blueprint check
- `alembic upgrade`
- external network access
- real harvest / scrape / ingest
- `git push`
- `git pull`
- `git fetch --all`
- Docker volume cleanup
