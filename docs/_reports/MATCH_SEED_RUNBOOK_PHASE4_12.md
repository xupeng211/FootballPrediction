# Phase 4.12 Single Match Seed Runbook Draft

> Status: draft only. Do not execute the SQL in this document without explicit human approval.
>
> Scope: preflight for seeding one `matches` parent row required by local HTML odds ingestion.
>
> Generated on: 2026-04-30

## 1. Current DB State

Repository state during this preflight:

- Branch at start: `main`
- HEAD: `a95808e254c69bcf2f1008b769ef441b681cee4f`
- Working tree before writing this report: clean
- Dev stack: healthy
- DB schema migration: Phase 4.11B completed

Relevant row counts after schema migration:

```text
matches                    0
raw_match_data             0
bookmaker_odds_history     0
matches_oddsportal_mapping 0
l3_features                0
```

Target odds-history parent requirement:

- `bookmaker_odds_history.match_id` has a foreign key to `matches(match_id)`.
- `matches` is currently empty.
- `match_id = 140_20252026_4837496` is not present in `matches`.
- `local_dom_ingestor --commit` must not be run until the parent `matches` row exists.

## 2. `matches` Table Structure Summary

Current `matches` columns:

```text
match_id          varchar(50)    NOT NULL
external_id       varchar(100)   NULL
league_name       varchar(100)   NOT NULL DEFAULT 'Premier League'
season            varchar(20)    NOT NULL DEFAULT '2324'
home_team         varchar(200)   NOT NULL
away_team         varchar(200)   NOT NULL
home_score        integer        NULL
away_score        integer        NULL
actual_result     varchar(10)    NULL
match_date        timestamptz    NULL
venue             varchar(200)   NULL
status            varchar(50)    NULL DEFAULT 'Scheduled'
is_finished       boolean        NULL DEFAULT false
collection_date   timestamptz    NULL DEFAULT CURRENT_TIMESTAMP
created_at        timestamptz    NULL DEFAULT CURRENT_TIMESTAMP
updated_at        timestamptz    NULL DEFAULT CURRENT_TIMESTAMP
data_version      varchar(20)    NULL DEFAULT 'V25.1'
data_source       varchar(50)    NULL DEFAULT 'FotMob'
pipeline_status   varchar(20)    NULL DEFAULT 'pending'
home_corners      integer        NULL
away_corners      integer        NULL
home_yellow_cards integer        NULL
away_yellow_cards integer        NULL
home_red_cards    integer        NULL
away_red_cards    integer        NULL
referee           varchar(100)   NULL
```

Required by `NOT NULL`:

```text
match_id
league_name
season
home_team
away_team
```

Important default caveat:

- `season` default is `'2324'`, but the active `season_format` constraint requires `YYYY/YYYY`.
- `status` default is `'Scheduled'`, but the active `status_lowercase` constraint requires lowercase.
- A safe seed should explicitly set both `season` and `status`.

## 3. `matches` Constraint Summary

Primary key:

```text
matches_pkey PRIMARY KEY (match_id)
```

CHECK constraints:

```text
season_format:
  season must match ^\d{4}/\d{4}$

status_lowercase:
  status must equal lower(status)

matches_pipeline_status_valid:
  pipeline_status must be one of:
  pending, processing, harvested, failed, skipped, RECON_LINKED, RECON_MISMATCH

valid_scores:
  scores are both NULL, or both non-negative
```

Triggers:

```text
trg_sync_is_finished:
  BEFORE INSERT OR UPDATE, sets is_finished from status = 'finished'

update_matches_updated_at:
  BEFORE UPDATE, updates updated_at
```

Referenced by:

```text
bookmaker_odds_history(match_id)
l3_features(match_id)
match_features_training(match_id)
matches_oddsportal_mapping(match_id)
odds(match_id)
predictions(match_id)
raw_match_data(match_id)
```

## 4. Target Match Information

Phase 4.5 local HTML dry-run parsed:

```text
sample file: data/manual_html/test_sample.html
match_id:    140_20252026_4837496
league:      Segunda División
home:        Cultural Leonesa
away:        Burgos CF
kickoff:     2026-05-24T17:00:00Z
```

Derived fields:

```text
external_id: 4837496
season:      2025/2026
status:      scheduled
is_finished: false
```

Notes:

- The local HTML file contains `data-match-id`, kickoff, participants, and odds rows.
- The HTML header text shows `Segunda`; Phase 4.5 dry-run normalized this to `Segunda División`.
- The sample is sufficient to draft a single parent `matches` row.
- It is not a complete official L1 fixture record, so the row should be clearly marked as a local/manual seed unless a stronger source is approved.

## 5. Target Match Existence

Read-only query result:

```text
SELECT * FROM matches
WHERE match_id = '140_20252026_4837496'
LIMIT 5;

0 rows
```

The target parent row does not currently exist.

## 6. Available Seed Entrypoint Analysis

### `scripts/ops/seed_fixtures.js`

Assessment:

- Purpose: L1 discovery/fixture seed through `DiscoveryService`.
- Local-only: no.
- External network risk: yes, because discovery uses upstream fixture discovery.
- DB write: yes, through `FixtureRepository.persist()`.
- `--commit` gate: no.
- `--dry-run`: no.
- `--limit` / single `match_id`: no.
- Recommendation: do not use for Phase 4.13 single local seed.

### `src/infrastructure/services/FixtureRepository.js`

Assessment:

- Purpose: library-level `persist(fixtures)` upsert into `matches`.
- DB write: yes.
- `--commit` gate: not applicable; it is not a CLI.
- Fields used by repository persist:
  `match_id`, `external_id`, `league_name`, `season`, `home_team`, `away_team`, `match_date`, `home_score`, `away_score`, `status`, `is_finished`, `data_source`.
- Recommendation: usable as an implementation building block only after adding a safety-gated wrapper; do not call directly in this phase.

### `scripts/ops/local_dom_ingestor.js`

Assessment:

- Purpose: local HTML odds preview and optional commit to `bookmaker_odds_history`.
- Default: dry-run.
- `--commit` gate: yes.
- Local-only with `--file`: yes.
- Parent seed: no.
- It explicitly checks that referenced `match_id` exists in `matches` before commit.
- Recommendation: safe for preview; not sufficient for seeding `matches`.

### `scripts/ops/csv_bulk_loader.js`

Assessment:

- Purpose: local CSV dry-run and optional DB write for tactical fields and `bookmaker_odds_history`.
- Default: dry-run.
- `--commit` gate: yes.
- Local-only with `--file`: yes.
- Parent seed: no. It resolves against existing FotMob/base `matches` rows and updates matched rows.
- It can read DB during dry-run and writes an error log.
- Recommendation: not a parent seed mechanism.

### Historical/test scripts

Examples found:

- `scripts/ops/generate_bundesliga_fixtures.js`
- `scripts/ops/fixture_harvester_l1.js`
- `scripts/test/end_to_end_test.js`
- tests/stress mocks around `FixtureRepository.persist`

Assessment:

- Not suitable for this single local seed.
- Some are hard-coded, league-specific, test-only, or scrape/write real DB by default.

## 7. Local Sample Suitability

Local sample count found under `data` and `tests`:

```text
HTML: 2
CSV:  1
JSON: 14
```

Observed caveat:

- `find data tests ...` hit a permission warning under `data/postgres/pgdata`; listed sample files were still collected.

Primary local sample:

```text
data/manual_html/test_sample.html
```

This HTML sample is sufficient to draft a minimal `matches` parent row because it contains:

- target `match_id`
- kickoff timestamp
- home team
- away team
- local odds rows referencing the match

It does not contain a full official L1 payload. If stricter provenance is required, Phase 4.13 should first create or approve a small local seed fixture JSON, for example:

```text
data/manual_seed/phase413_match_140_20252026_4837496.json
```

Do not download external data just to fill the fixture.

## 8. Seed INSERT Draft

This SQL is a draft only. It was not executed in Phase 4.12.

```sql
-- Draft only. Execute only after explicit Phase 4.13 authorization.
BEGIN;

INSERT INTO matches (
  match_id,
  external_id,
  league_name,
  season,
  home_team,
  away_team,
  match_date,
  status,
  is_finished,
  data_source,
  data_version,
  pipeline_status
)
VALUES (
  '140_20252026_4837496',
  '4837496',
  'Segunda División',
  '2025/2026',
  'Cultural Leonesa',
  'Burgos CF',
  '2026-05-24T17:00:00Z'::timestamptz,
  'scheduled',
  false,
  'manual_html_seed',
  'PHASE4.12_DRAFT',
  'pending'
)
ON CONFLICT (match_id) DO NOTHING
RETURNING match_id, league_name, season, home_team, away_team, match_date, status, pipeline_status;

-- Verify one row returned before COMMIT.
COMMIT;
```

Rationale:

- `season = '2025/2026'` satisfies `season_format`.
- `status = 'scheduled'` satisfies `status_lowercase`.
- `pipeline_status = 'pending'` satisfies `matches_pipeline_status_valid`.
- Scores are left `NULL`, satisfying `valid_scores`.
- `external_id = '4837496'` is derived from the match_id suffix and helps later local CSV alignment.
- `data_source = 'manual_html_seed'` preserves auditability that this was not discovered through live L1.

Open decision before execution:

- Confirm whether `data_source` should remain `manual_html_seed` or use an existing project source label such as `FotMob`.
- Confirm whether `data_version` should be a Phase label or omitted to use the table default.

## 9. Missing Fields And Risk Points

No `NOT NULL` field is missing for a minimal seed.

Known values:

```text
match_id
external_id
league_name
season
home_team
away_team
match_date
status
is_finished
pipeline_status
```

Intentionally omitted / NULL:

```text
venue
home_score
away_score
actual_result
tactical stat columns
referee
```

Risks:

- This is a local/manual parent seed, not an official discovery result.
- `ON CONFLICT DO NOTHING` makes the insert idempotent, but it will not update a stale existing row.
- Deleting this row later can cascade to child rows because multiple tables reference `matches(match_id) ON DELETE CASCADE`.
- A future `local_dom_ingestor --commit` will still need separate authorization and before/after row counts.

## 10. Execution Preconditions For Phase 4.13

Before any seed is executed:

1. Human explicitly authorizes a single-row `matches` seed.
2. DB backup exists or a new pre-seed `pg_dump` is approved.
3. Confirm target `match_id` still does not exist.
4. Confirm related child tables still have zero rows for this `match_id`.
5. Confirm the exact seed SQL and source labels.
6. Execute inside a transaction.
7. Verify returned row and post-seed row counts before proceeding to any odds-history commit.

## 11. Post-Seed Verification SQL

Draft only:

```sql
SELECT match_id, external_id, league_name, season, home_team, away_team,
       match_date, status, is_finished, data_source, data_version, pipeline_status
FROM matches
WHERE match_id = '140_20252026_4837496';

SELECT 'matches' AS table_name, COUNT(*) AS rows
FROM matches
UNION ALL
SELECT 'bookmaker_odds_history', COUNT(*)
FROM bookmaker_odds_history
WHERE match_id = '140_20252026_4837496';
```

Expected immediately after seed and before odds commit:

```text
matches row for target match_id: 1
bookmaker_odds_history rows for target match_id: 0
```

## 12. Rollback Plan

Preferred rollback before child writes:

```sql
-- Draft only. Execute only with explicit rollback authorization.
BEGIN;
DELETE FROM matches
WHERE match_id = '140_20252026_4837496';
COMMIT;
```

Rollback caution:

- After odds/history rows exist, deleting the `matches` row can cascade to child rows.
- If any child data has been written, prefer restoring from the pre-seed backup or use a separately approved rollback runbook.

## 13. Recommendation

It is reasonable to enter Phase 4.13 only if the user explicitly authorizes:

- one-row `matches` seed for `match_id = 140_20252026_4837496`
- either reuse of the Phase 4.11B backup or a fresh pre-seed `pg_dump`
- execution of the exact SQL after confirming source labels
- no odds-history commit in the same phase unless separately authorized

Do not use `seed_fixtures.js`, `npm run seed`, or discovery/harvest entrypoints for this local parent seed.

## 14. Phase 4.12 Non-Execution Confirmation

Phase 4.12 did not execute:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- seed commit
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- external network access
- real harvest / scrape / ingest
- `git push`, `git pull`, or `git fetch --all`
- Docker volume cleanup
