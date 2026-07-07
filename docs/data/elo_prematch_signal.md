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

## Next

**GOLD-AUDIT-2AU completed**: no-write preview output now directly prints
numeric Elo values.

Recommended next step (after user confirmation): review whether a
controlled write-readiness audit is appropriate before any DB writes.
Do not start automatically.
