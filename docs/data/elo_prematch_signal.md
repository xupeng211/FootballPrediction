# Prematch Elo Signal Integration

lifecycle: permanent
scope: GOLD-AUDIT-2AH Elo signal capability

## Status

**Implemented: `PrematchEloComputer` module.**

The `src/feature_engine/elo/PrematchEloComputer.js` module provides
in-memory, no-DB-write prematch Elo computation using match history.
It wraps the existing `EloRatingExtractor` with explicit prematch-safety
guarantees.

## Problem

Before 2AH, all `elo_features` in `l3_features` contained default 1500
for every team. The `FeatureSmelter._loadEloCache()` reads from
`team_elo_ratings` table, which is empty. Since no Elo computation was
ever run against the data, `getTeamElo()` always falls back to
`DEFAULT_ELO_RATING = 1500`.

## Solution

`PrematchEloComputer` computes real prematch Elo from match history
entirely in memory:

1. Loads all historical matches (SELECT from `matches` where scores exist)
2. Sorts by `match_date ASC, match_id ASC` (deterministic)
3. For each match, records the **current** Elo state as prematch Elo
4. Updates Elo state with the match result (for subsequent matches)

This guarantees that match N's prematch Elo uses only matches 1..N-1.

## Prematch Safety Guarantees

| Guarantee | How |
|---|---|
| No future leakage | Matches sorted by date; only matches before target are processed |
| No target-match leakage | Elo recorded BEFORE the match result is applied |
| Same-time stability | Same-date matches sorted by match_id |
| Fallback metadata | `_is_default: true` for teams with no prior history |
| No DB write | Pure in-memory computation |

## Integration Path

### Current state (before integration)

FeatureSmelter loads `team_elo_ratings` → `eloCache` is empty → all Elo = 1500.

### Integration (after this module is wired in)

FeatureSmelter can use `PrematchEloComputer` as an in-memory fallback when
`eloCache` is empty:

```js
// In FeatureSmelter._loadEloCache() catch block or after:
if (this.eloCache.size === 0) {
    const history = await this._loadMatchHistory();  // SELECT-only
    const computer = new PrematchEloComputer();
    this.matchEloMap = computer.computeAll(history);
}
```

Then in `getTeamElo()` or `extractMatchFeatures()`:
```js
const prematchElo = this.matchEloMap?.get(matchId);
if (prematchElo) {
    eloFeatures = {
        home_elo: prematchElo.home_elo_pre,
        away_elo: prematchElo.away_elo_pre,
        elo_diff: prematchElo.elo_diff,
        elo_expected_home: prematchElo.expected_home_win,
        _is_default: prematchElo._is_default,
    };
}
```

Full integration requires a controlled smelt run (DB write to `l3_features`),
which is NOT part of 2AH. The capability module is ready; the write step
is deferred to a future authorized task.

## Test Coverage

`tests/unit/feature_engine/PrematchEloComputer.test.js` — 11 tests:

1. No-history teams → default 1500 + `_is_default: true`
2. History teams → real (non-default) Elo
3. Target match result does NOT affect own prematch Elo
4. Future matches do not leak
5. Same-date matches: stable ordering, no cross-contamination
6. Win/loss/draw Elo direction validated
7. Empty input → graceful fallback
8. Invalid match records → skipped, not crashed
9. `computeOne` correctly filters prior matches
10. Multi-team cross-validation
11. `importRatings` / `exportRatings` / `reset`

## Remaining Risks

- `team_elo_ratings` table remains empty; DB-level Elo cache not populated.
- Existing `l3_features` rows still contain old default 1500 Elo.
- FeatureSmelter integration requires a controlled smelt run (DB write).
- 58 rows remain insufficient for training regardless of Elo quality.
- Odds signal remains unavailable.

## Next

GOLD-AUDIT-2AI: Verify Elo PR diff and CI.
A future authorized task with DB-write permission can:
1. Integrate `PrematchEloComputer` into FeatureSmelter
2. Run a controlled smelt to update `l3_features.elo_features`
3. Run report-only to verify real Elo signal in the filtered matrix
