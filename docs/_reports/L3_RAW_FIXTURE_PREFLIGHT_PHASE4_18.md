# Phase 4.18 L3 Raw Fixture Preflight

## Current Status

- Branch: `docs/l3-raw-fixture-preflight-phase418`
- Base HEAD: `353270ba0958521dbbc300c994b569c8f60a6f2b`
- Dev stack: `db`, `dev`, `redis`, `prometheus`, and `grafana` healthy.
- `make data-check`: passed.
- `make data-schema-status`: passed.

Current DB row counts:

| table | rows |
|---|---:|
| matches | 1 |
| bookmaker_odds_history | 2 |
| raw_match_data | 0 |
| l3_features | 0 |
| match_features_training | 0 |
| predictions | 0 |

Target match exists:

- `match_id`: `140_20252026_4837496`
- `league_name`: `Segunda Division`
- `season`: `2025/2026`
- `home_team`: `Cultural Leonesa`
- `away_team`: `Burgos CF`
- `match_date`: `2026-05-24T17:00:00Z`
- `status`: `scheduled`
- `pipeline_status`: `pending`

Target odds exist in `bookmaker_odds_history`:

- `Bet365 / 1x2`
- `Pinnacle / Asian Handicap`

## raw_match_data Schema

Columns:

| column | type | nullable | default |
|---|---|---:|---|
| id | bigint | no | `nextval('raw_match_data_id_seq')` |
| match_id | varchar(50) | no | none |
| external_id | varchar(100) | yes | none |
| raw_data | jsonb | no | none |
| collected_at | timestamptz | yes, but check requires non-null | `CURRENT_TIMESTAMP` |
| data_version | varchar(20) | yes | `V26.1` |
| data_hash | varchar(64) | yes | none |

Constraints:

- Primary key: `id`
- Unique: `match_id`
- Foreign key: `match_id` references `matches(match_id)` with `ON DELETE CASCADE`
- Check: `collected_at IS NOT NULL`
- Check: `match_id` must match either numeric ID or canonical `league_season_external` format
- Check: `raw_data` is non-empty JSONB
- Check: `raw_data` must contain at least one of `matchId`, `general`, or `header`

There are no `source`, `data_type`, or `payload` columns in the current table. Those concepts must live inside `raw_data` or in a separate runbook if needed.

## L3 Tables

`l3_features` exists and is empty. Required columns are:

- `match_id`
- `golden_features`
- `tactical_features`
- `odds_movement_features`
- `odds_features`
- `elo_features`
- `rolling_features`
- `efficiency_features`
- `draw_features`
- `market_sentiment`
- `stitch_summary`
- `computed_at`
- `created_at`
- `updated_at`

Most JSONB columns default to `{}`. `match_id` is both primary key and FK to `matches(match_id)`.

`match_features_training` exists and is empty. Required columns are:

- `match_id`
- `season`
- `match_date`
- `home_team`
- `away_team`

## L3 Source Reads

The active `npm run smelt` path is:

- `scripts/ops/smelt_all.js`
- `src/feature_engine/smelter/FeatureSmelter.js`
- extractor functions:
  - `src/feature_engine/extractors/GoldenFeatureExtractor.js`
  - `src/feature_engine/extractors/TacticalMomentumExtractor.js`
  - `src/feature_engine/extractors/OddsMovementExtractor.js`

`FeatureSmelter.getPendingMatches()` reads:

- `matches.match_id`
- `matches.external_id`
- `matches.home_team`
- `matches.away_team`
- `matches.match_date`
- `matches.home_score`
- `matches.away_score`
- `raw_match_data.raw_data`

Required join condition:

- `matches INNER JOIN raw_match_data ON match_id`
- incremental mode also requires no existing `l3_features` row.

Main `raw_data` paths used by extractors:

- `content.lineup.homeTeam`
- `content.lineup.awayTeam`
- `content.lineup.*.totalStarterMarketValue`
- `content.lineup.*.starters[].marketValue`
- `content.lineup.*.starters[].performance.rating`
- `content.lineup.*.subs[].marketValue`
- `content.lineup.*.unavailable[]`
- `content.stats.Periods.All.stats` or `content.stats` as an array
- `content.momentum.main.data` or `content.momentum.data`
- `content.odds.initial/current/history`
- `general.betting.odds1X2`
- `header.homeMarketValue` / `header.awayMarketValue` as fallback

The `l3_stitch` path also reads:

- `content.shotmap.shots`
- `content.lineup`
- `bookmaker_odds_history` for `market_type = '1x2'`
- `odds` table as first choice for canonical 1x2 odds

## Existing L3 Entry Risk

| entry | path / command | writes DB | CREATE / ALTER | UPDATE matches | triggers ELO | dry-run trustworthy | risk |
|---|---|---:|---:|---:|---:|---:|---|
| smelt | `npm run smelt` / `scripts/ops/smelt_all.js` | yes | yes, `CREATE INDEX IF NOT EXISTS` during init | no | no direct recalculation | no; `dryRun` is parsed but not used by `FeatureSmelter.run()` | high |
| l3 stitch | `npm run l3:stitch` / `scripts/ops/l3_stitch_pipeline.js` | yes | yes, `CREATE TABLE` and `CREATE INDEX` | yes, score backfill from raw header | yes, runs incremental Elo | no safe dry-run found | high |
| l3 stitch worker | `scripts/ops/l3_stitch_worker.js` | yes | no direct schema DDL | no | no direct recalculation | no CLI dry-run | high |
| modular smelter | `SmelterOrchestrator` / `L3Writer` | yes if invoked | no obvious DDL in orchestrator | no | no direct recalculation | no active safe CLI found | medium-high |

No L3 help command was executed. `smelt_all.js --help` is unsafe because the script does not implement help handling and would run initialization. `l3_stitch_pipeline.js` also has no safe help path.

## Why Current Data Is Not Enough

Current DB has:

- 1 `matches` row
- 2 `bookmaker_odds_history` rows
- 0 `raw_match_data` rows

L3 cannot run safely because both active L3 paths require `raw_match_data.raw_data`. The 2 odds rows are useful only for odds feature extraction in a stitch-style path, where 1x2 bookmaker history can be read as an odds source. They do not replace the missing FotMob-style raw payload needed for lineup, stats, momentum, shotmap, and tactical features.

## Fixture Candidates

Observed local candidates:

- `tests/fixtures/match_success.json`: useful as a small synthetic sample, but its stats shape is not ideal for current `TacticalMomentumExtractor`, and player ratings are under `rating` rather than `performance.rating`.
- `tests/fixtures/malformed_data.json`: useful negative fixture for missing stats/shotmap behavior.
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/premium_match_sample.json`: closest to real FotMob raw structure; contains `l2_raw_json` with `general`, `header`, `content`, `lineup`, stats, momentum, and shotmap. It is in legacy archive, so should be copied or sanitized into a current fixture path before relying on it.
- `scripts/ops/backfill_historical_raw_match_data.js`: contains a useful pseudo-FotMob payload builder shape: `general`, `header`, `content.stats`, `content.lineup`, `content.shotmap.shots`, `content.momentum.data`, and `_meta`.

## Recommended Fixture Plan

Use JSON, not SQL, for the first fixture. A JSON fixture supports a true no-write dry-run and avoids creating an executable DB-write artifact.

Recommended path:

```text
tests/fixtures/l3/raw_match_data_phase418_sample.json
```

Recommended top-level shape:

```json
{
  "match_id": "140_20252026_4837496",
  "external_id": "4837496",
  "raw_data": {
    "matchId": "4837496",
    "general": {},
    "header": {},
    "content": {}
  }
}
```

Recommended `raw_data` content:

- `matchId`: `"4837496"`
- `general.matchId`: `"4837496"`
- `general.leagueId`: `140`
- `general.leagueName`: `"Segunda Division"`
- `general.matchTimeUTCDate`: `"2026-05-24T17:00:00Z"`
- `general.finished`: `false`
- `general.started`: `false`
- `general.homeTeam.name`: `"Cultural Leonesa"`
- `general.awayTeam.name`: `"Burgos CF"`
- `header.teams`: home and away team entries; scores should be absent or null for scheduled match
- `header.status.utcTime`: `"2026-05-24T17:00:00Z"`
- `header.status.started`: `false`
- `header.status.finished`: `false`
- `content.stats`: array of FotMob-style stat rows such as `Expected goals (xG)`, `Ball possession`, `Total shots`, `Shots on target`, `Corner kicks`, cards, and fouls
- `content.lineup.homeTeam` and `content.lineup.awayTeam`: `starters`, `subs`, `unavailable`, and `totalStarterMarketValue`
- starter entries should include `marketValue` and `performance.rating` if the dry-run is meant to test non-zero golden features
- `content.shotmap.shots`: may be empty for a scheduled match, but include the object shape so the dry-run can report `shotmap_shots=0` rather than missing shape
- `content.momentum.data`: optional array of `{ "minute": n, "value": n }`
- `content.odds`: optional. For this target, prefer reading existing `bookmaker_odds_history` in a read-only dry-run because those two rows are the verified local odds source.

For a future DB seed stage, the executable SQL should be generated later under explicit authorization. It should not be the primary fixture format.

## Trusted L3 Dry-Run Design

Recommended future command shape:

```text
node scripts/ops/l3_local_dry_run.js --fixture tests/fixtures/l3/raw_match_data_phase418_sample.json --match-id 140_20252026_4837496
```

Optional Makefile wrapper:

```text
make data-l3-dry-run SAMPLE_RAW=tests/fixtures/l3/raw_match_data_phase418_sample.json MATCH_ID=140_20252026_4837496
```

Required safety properties:

- Default behavior must be read-only.
- Must not create indexes.
- Must not create tables.
- Must not insert or upsert `l3_features`.
- Must not update `matches`.
- Must not trigger Elo recalculation.
- Must not access external network resources.
- Must support explicit `--fixture`.
- Must support explicit `--match-id`.
- Must validate that fixture `match_id` equals CLI `--match-id`.
- Must optionally read `matches` and `bookmaker_odds_history` with SELECT only.
- Must print generated `golden_features`, `tactical_features`, `odds_features` / `odds_movement_features`, and `stitch_summary` preview.
- Must print missing-field warnings such as `missing_lineup`, `missing_shotmap`, `invalid_xg`, `zero_ratings`, and `no_odds_data`.
- Must exit non-zero if fixture is malformed or would not satisfy raw_match_data constraints.

Implementation should reuse pure extractor functions directly instead of invoking `FeatureSmelter.init()`, `L3Writer`, `l3_stitch_pipeline`, or `l3_stitch_worker.run()`.

## Recommendation

Proceed to a Phase 4.19 implementation stage only after explicit authorization.

Recommended scope for Phase 4.19:

1. Add `tests/fixtures/l3/raw_match_data_phase418_sample.json`.
2. Add a safe `scripts/ops/l3_local_dry_run.js` that imports only pure extractor functions and read-only helpers.
3. Add a Makefile target such as `data-l3-dry-run`.
4. Add tests proving no SQL write verbs are issued by the dry-run path.

Do not use `npm run smelt` or `npm run l3:stitch` as the basis for the first dry-run gate without refactoring their write paths.

## Non-Execution Confirmation

This phase did not execute:

- `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, or `TRUNCATE`
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- seed commit
- `npm run smelt`
- `npm run l3:stitch`
- Elo recalculation
- L3 feature computation
- model training
- prediction write
- external network access
- real harvest, scrape, or ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume cleanup
- `git push`, `git pull`, or `git fetch --all`
- code changes
- commit
