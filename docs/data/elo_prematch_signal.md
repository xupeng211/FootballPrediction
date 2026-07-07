# Prematch Elo Signal Integration

lifecycle: permanent
scope: Elo signal computation, FeatureSmelter wiring, no-write preview

## Status

**Implemented and verified on main.**

- `PrematchEloComputer` module (PR #1727) — in-memory, no-DB-write prematch Elo computation.
- FeatureSmelter wiring (PR #1728, merge commit `6be2cdf`) — in-memory fallback when `team_elo_ratings` cache/table is empty or unavailable.
- No-write preview path exposes actual prematch Elo in `_buildPreviewEntry` (home_elo, away_elo, elo_diff, _is_default, _source).
- `team_elo_ratings` table is NOT required for the current no-write preview path.
- Existing `l3_features` rows remain unchanged (still contain old default 1500 Elo from prior smelt runs).

## Problem

Before 2AH, all `elo_features` in `l3_features` contained default 1500
for every team. The `FeatureSmelter._loadEloCache()` reads from
`team_elo_ratings` table, which does not exist in this environment.
Since no Elo computation was ever run against the data, `getTeamElo()`
always fell back to `DEFAULT_ELO_RATING = 1500`.

## Solution

`PrematchEloComputer` computes real prematch Elo from match history
entirely in memory:

1. Loads all historical matches (SELECT from `matches` where scores exist)
2. Sorts by `match_date ASC, match_id ASC` (deterministic)
3. For each match, records the **current** Elo state as prematch Elo
4. Updates Elo state with the match result (for subsequent matches)

This guarantees that match N's prematch Elo uses only matches 1..N-1.

When `team_elo_ratings` cache is empty or the table does not exist,
FeatureSmelter's `init()` calls `_loadPrematchEloHistory()` which
computes prematch Elo via `PrematchEloComputer.computeAll()` and
stores results in `this.matchEloMap`. During `processMatch()`, the
per-match prematch Elo is looked up from `matchEloMap`.

## Prematch Safety Guarantees

| Guarantee | How |
|---|---|
| No future leakage | Matches sorted by date; only matches before target are processed |
| No target-match leakage | Elo recorded BEFORE the match result is applied |
| Same-time stability | Same-date matches sorted by match_id |
| Fallback metadata | `_is_default: true` for teams with no prior history; `_source: "PrematchEloComputer"` |
| No DB write | Pure in-memory computation; SELECT-only history loading |

## Verified No-write Preview Milestones

### 2AP — First no-write preview with in-memory Elo

Command: `node scripts/ops/smelt_all.js --dry-run --limit 1`

| Metric | Value |
|---|---|
| pending matches | 0 (all 60 matches already have l3_features) |
| preview entries | 0 |
| computedMatches | 59 |
| eloHits | 49 (non-default Elo) |
| eloDefaults | 10 |
| DB counts unchanged | yes (raw=76, matches=60, l3=60) |
| actual_db_write | false |

Confirmed: in-memory PrematchEloComputer fallback initialized successfully
on real DB data and produced non-default Elo for 49 of 59 matches.

### 2AS — No-write full-recalculate preview with --limit 1

Command: `node scripts/ops/smelt_all.js --dry-run --full-recalculate --limit 1`

| Metric | Value |
|---|---|
| preview entries | 1 |
| match_id | `53_20252026_4830746` |
| teams | Angers vs Strasbourg |
| data_version | fotmob_live_v1 |
| elo_features | data_keys=4/4 |
| actual_db_write | false |
| would_write | true (would write if not no-write) |
| eloHits | 1 |
| eloDefaults | 0 |
| DB counts unchanged | yes (raw=76, matches=60, l3=60) |

Confirmed: end-to-end pipeline produces a preview entry with real prematch
Elo, zero DB writes, and no artifact creation.

## Current Display Gap

- `_buildPreviewEntry` populates numeric Elo fields in the preview entry
  object: `home_elo`, `away_elo`, `elo_diff`, `_is_default`, `_source`.
- **GOLD-AUDIT-2AU (completed):** The `printPreview` formatter in `smelt_all.js`
  now renders numeric Elo values directly in the formatted output:
  ```
  │  ✅  elo_features: data_keys=4/4
  │     home_elo=1517.38
  │     away_elo=1476.06
  │     elo_diff=41.32
  │     _is_default=false
  │     _source=PrematchEloComputer
  ```
- This display gap is now resolved. No-write preview output is
  self-documenting for Elo values.

## Integration Path

FeatureSmelter uses `PrematchEloComputer` as an in-memory fallback when
`eloCache` is empty:

```js
// In FeatureSmelter.init(), after _loadEloCache():
if (this.eloCache.size === 0) {
    await this._loadPrematchEloHistory();
}

// In processMatch(), per-match Elo lookup:
const cachedPrematch = this.matchEloMap?.get(match_id);
if (cachedPrematch) {
    homeElo = cachedPrematch.home_elo_pre;
    awayElo = cachedPrematch.away_elo_pre;
    // ... with _is_default, _source metadata
}
```

## Test Coverage

- `tests/unit/feature_engine/PrematchEloComputer.test.js` — 11 tests
- `tests/unit/feature_engine/FeatureSmelterEloWiring.test.js` — 6 tests

## Current Safety Boundaries

| Gate | Status |
|---|---|
| SAFE_FOR_DB_WRITE | **no** |
| SAFE_FOR_SMELT_WRITE | **no** |
| SAFE_FOR_TRAINING_DRY_RUN | **no** |
| SAFE_FOR_REAL_TRAINING | **no** |
| SAFE_FOR_REAL_PREDICTION | **no** |
| SAFE_FOR_BACKTEST | **no** |

- No controlled L3 rewrite is authorized.
- No `team_elo_ratings` migration is authorized.
- Existing `l3_features` rows remain unchanged.
- 58 rows remain insufficient for training.
- Odds signal remains unavailable.

## GOLD-AUDIT-2AW — Controlled Write Plan

### Status

| Gate | Value |
|---|---|
| READY_FOR_CONTROLLED_WRITE_PLAN | **yes** |
| READY_FOR_ACTUAL_DB_WRITE | **no** |
| READY_FOR_SMELT_WRITE | **no** |
| READY_FOR_TRAINING_DRY_RUN | **no** |
| SAFE_FOR_REAL_TRAINING | **no** |
| SAFE_FOR_REAL_PREDICTION | **no** |
| SAFE_FOR_BACKTEST | **no** |

This section is a **plan only**. It does not authorize execution.

### Target

| Field | Value |
|---|---|
| match_id | `53_20252026_4830746` |
| operation | UPDATE existing `l3_features` row via `ON CONFLICT DO UPDATE` |
| table affected | `l3_features` only |
| teams | Angers vs Strasbourg |
| data_version | `fotmob_live_v1` |

### Expected Change

| Field | Before | After |
|---|---|---|
| `home_elo` | 1500 | 1517.38 |
| `away_elo` | 1500 | 1476.06 |
| `elo_diff` | 0 | 41.32 |
| `_is_default` | true | false |
| `_source` | absent | `PrematchEloComputer` |

All other `l3_features` columns (`golden_features`, `tactical_features`, `odds_movement_features`, `external_id`, `computed_at`) should remain unchanged unless the smelt pipeline naturally recomputes them.

### Pre-checks (Before Any DB Write)

1. Confirm current branch is `main` and working tree is clean.
2. Confirm latest `main` includes GOLD-AUDIT-2AV merge commit (`bdf7e8f`).
3. Confirm DB counts:
   - `raw_match_data` = 76
   - `matches` = 60
   - `l3_features` = 60
4. Confirm target row exists: `SELECT match_id, elo_features FROM l3_features WHERE match_id = '53_20252026_4830746'`.
5. Confirm target row currently has old/default Elo: `home_elo=1500, away_elo=1500, _is_default=true`.
6. Confirm dry-run preview still produces real Elo: `node scripts/ops/smelt_all.js --dry-run --full-recalculate --limit 1`.
7. Confirm dry-run output has `actual_db_write=false` and numeric Elo values match expected.

### Backup Plan

Before executing the write:

1. Export target `l3_features` row to a local JSON file:
   ```bash
   docker compose -f docker-compose.dev.yml exec -T db psql -U football_user -d football_db \
     -c "SELECT row_to_json(t) FROM (SELECT * FROM l3_features WHERE match_id = '53_20252026_4830746') t;" \
     > /tmp/l3_features_53_20252026_4830746_before.json
   ```
2. Record before counts (raw_match_data, matches, l3_features).
3. Verify the backup JSON file is non-empty and parseable.
4. Do not proceed if backup cannot be captured.

### Future Write Command (Do NOT Execute in 2AW)

The write must be executed only in a later explicitly authorized task (e.g. GOLD-AUDIT-2AX). The command must be limited to one match / one row and must require explicit DB write env confirmation.

**Expected command:**

```bash
# NOT for execution in 2AW. Requires GOLD-AUDIT-2AX authorization.
docker compose -f docker-compose.dev.yml exec -T dev sh -lc \
  'ALLOW_DB_WRITE=true node scripts/ops/smelt_all.js --full-recalculate --limit 1'
```

**Constraints:**

- Must set `ALLOW_DB_WRITE=true` in the dev container environment.
- Must use `--full-recalculate` to force re-smelting of the target match.
- Must use `--limit 1` to restrict to exactly one match.
- Must NOT pass `--dry-run`, `--no-write`, or `--preview`.
- Must NOT set `FINAL_DB_WRITE_CONFIRMATION=yes` (reserved for broader authorization).
- Must NOT use `smelt_all.js` with `--limit > 1` or without `--limit`.

**What the write path does:**

1. `FeatureSmelter.run({ fullRecalculate: true, limit: 1 })` with `isNoWrite=false`.
2. `processMatch()` recomputes all feature extractors (golden, tactical, odds_movement, elo) for the target match.
3. Elo comes from `PrematchEloComputer` in-memory cache (same values as preview).
4. `saveFeatures()` executes `INSERT INTO l3_features ... ON CONFLICT (match_id) DO UPDATE SET ...`.
5. Exactly one row is UPSERT-ed; no new rows are created (target match already has a row).

### Post-write Validation

After the write completes:

1. Confirm DB counts unchanged:
   - `raw_match_data` = 76
   - `matches` = 60
   - `l3_features` = 60
2. Confirm only the target `match_id` row changed:
   ```sql
   SELECT match_id, elo_features FROM l3_features
   WHERE match_id = '53_20252026_4830746';
   ```
3. Confirm numeric Elo fields changed to expected values:
   - `home_elo` = 1517.38 (±0.01)
   - `away_elo` = 1476.06 (±0.01)
   - `elo_diff` = 41.32 (±0.02)
   - `_is_default` = false
   - `_source` = `PrematchEloComputer`
4. Confirm `actual_db_write=true` was logged in the write task output.
5. Confirm no training, prediction, or backtest was triggered.
6. Confirm no new tables (e.g. `team_elo_ratings`) were created.

### Rollback Plan

If post-write validation fails:

1. Stop immediately. Do not attempt further writes.
2. Restore target row from the before-write JSON backup:
   ```bash
   # Requires separate explicit rollback authorization
   docker compose -f docker-compose.dev.yml exec -T db psql -U football_user -d football_db \
     -c "UPDATE l3_features SET
       external_id = '<from_backup>',
       golden_features = '<from_backup>',
       tactical_features = '<from_backup>',
       odds_movement_features = '<from_backup>',
       elo_features = '<from_backup>',
       computed_at = '<from_backup>'
       WHERE match_id = '53_20252026_4830746';"
   ```
3. Re-check counts and target row after rollback.
4. Document rollback result in a follow-up task.

### Acceptance Criteria

| Criterion | Requirement |
|---|---|
| Rows updated | Exactly 1 `l3_features` row |
| New rows created | 0 (unless explicitly expected and documented) |
| Schema changes | 0 |
| `team_elo_ratings` table | Must NOT be created |
| Training triggered | No |
| Prediction triggered | No |
| Backtest triggered | No |
| Scraper/network access | No |
| Target Elo values | Match preview values within ±0.02 tolerance |
| Other rows unchanged | All 59 other `l3_features` rows unchanged |

### Next

**GOLD-AUDIT-2AU completed**: no-write preview output now directly prints
numeric Elo values.

**GOLD-AUDIT-2AV completed**: controlled write-readiness audit.

**GOLD-AUDIT-2AW completed**: controlled write plan documented (this section).

Recommended next step (after explicit user authorization only):
**GOLD-AUDIT-2AX-SINGLE-ROW-CONTROLLED-WRITE** — execute exactly one
controlled `l3_features` row update for match `53_20252026_4830746`,
following all pre-checks, backup, post-write validation, and acceptance
criteria defined above. Do not expand beyond one row.

Do not start automatically.
