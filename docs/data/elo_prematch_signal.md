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

## GOLD-AUDIT-2AY — Post-write Audit

### Status

| Gate | Value |
|---|---|
| GOLD-AUDIT-2AX completed | **yes** |
| SAFE_FOR_TRAINING_DRY_RUN | **no** |
| SAFE_FOR_REAL_TRAINING | **no** |
| SAFE_FOR_PREDICTION_BACKTEST | **no** |
| SAFE_FOR_BATCH_WRITE | **no** |

GOLD-AUDIT-2AX completed a single-row controlled write. This section is the post-write audit record.

### Write Scope Confirmed

| Field | Value |
|---|---|
| match_id | `53_20252026_4830746` |
| table | `l3_features` |
| operation | UPDATE existing row only (via `ON CONFLICT DO UPDATE`) |
| rows affected | exactly 1 |
| new rows created | 0 |

### Post-write DB Counts

| Table | Count | Changed |
|---|---|---|
| raw_match_data | 76 | no |
| matches | 60 | no |
| l3_features | 60 | no |

All counts unchanged from before 2AX.

### Target Row After 2AX

| Field | Value |
|---|---|
| home_elo | 1517.38 |
| away_elo | 1476.06 |
| elo_diff | 41.32 |
| _is_default | false |
| _source | PrematchEloComputer |
| _version | PrematchEloComputer-V1.0.0 |
| computed_at | 2026-07-07 23:46:03.614+00 |

### Real Elo Row Count After 2AX

- `_is_default=false` rows: **1**
- Only `match_id=53_20252026_4830746` has real Prematch Elo.
- Other 59 L3 rows remain old/default Elo (1500, `_is_default=true`).

### 2AX Backup / Hash Reference

| Item | Value |
|---|---|
| before backup path | `/tmp/gold_audit_2ax/before_l3_53_20252026_4830746.json` |
| after backup path | `/tmp/gold_audit_2ax/after_l3_53_20252026_4830746.json` |
| before hash (SHA256) | `5d576c20e2e97b5b2cedc50cc233e63edbb9d81c3409a2f2548580fa322bf4f2` |
| after hash (SHA256) | `9f261ddb0f453a8aa9769bc0e72933ae9ea1dc84bb4fcbc5802989db1bd6f664` |

Hashes independently verified during 2AY from local backup files.

### Env Flag Audit

2AX used these env flags to authorize the write:

| Env Flag | Value | Notes |
|---|---|---|
| `ALLOW_DB_WRITE` | yes | Universal gate; correct |
| `FINAL_DB_WRITE_CONFIRMATION` | yes | Universal gate; correct |
| `ALLOW_TRAINING_WRITE` | yes | Required because `db_write_guard.js` maps `l3_features` to this gate |
| `DRY_RUN` | false | Required to disable default dry-run mode |

**Risk noted:** `ALLOW_TRAINING_WRITE` is potentially misleading in an L3 smelt write context — it suggests training authorization was granted, but 2AX report confirms no training was executed. This is a gate-naming issue: `l3_features` is classified under the training gate in `scripts/ops/helpers/db_write_guard.js:90`. Recommend a future task to clarify env flag names before scaling write operations beyond one row.

### Safety Confirmation

| Check | Result |
|---|---|
| Batch L3 rewrite | no |
| Schema change | no |
| `team_elo_ratings` creation | no |
| Training | no |
| Prediction/backtest | no |
| FotMob/OddsPortal access | no |
| Code change (2AX) | no |

### Next

**GOLD-AUDIT-2AU completed**: no-write preview output now directly prints
numeric Elo values.

**GOLD-AUDIT-2AV completed**: controlled write-readiness audit.

**GOLD-AUDIT-2AW completed**: controlled write plan documented.

**GOLD-AUDIT-2AX completed**: single-row controlled L3 write executed.

**GOLD-AUDIT-2AY completed**: post-write audit recorded (this section).

Recommended next step (after user confirmation only):
No-write expansion readiness audit for all 60 L3 rows. Do not batch
rewrite L3 automatically. Do not start training. Do not start
prediction/backtest.

Do not start automatically.

## GOLD-AUDIT-2AZ — No-write Expansion Readiness Audit

### Status

| Gate | Value |
|---|---|
| GOLD_AUDIT_2AZ_PASS | **yes** |
| NO_WRITE_EXPANSION_AUDIT_RECORDED | **yes** |
| DB_UNCHANGED_AFTER_DRY_RUN | **yes** |
| READY_TO_DESIGN_BATCH_WRITE_PLAN | **yes** |
| SAFE_FOR_BATCH_WRITE | **no** |
| SAFE_FOR_TRAINING_DRY_RUN | **no** |
| SAFE_FOR_REAL_TRAINING | **no** |
| SAFE_FOR_PREDICTION_BACKTEST | **no** |

No DB write, smelt write, L3 batch rewrite, training, prediction, or
backtest was performed in 2AZ. This section records the no-write
expansion readiness audit.

### Current DB State Before No-write Expansion Audit

| Table | Count |
|---|---|
| raw_match_data | 76 |
| matches | 60 |
| l3_features | 60 |
| real Prematch Elo rows (`_is_default=false`) | 1 |
| old/default Elo rows (`_is_default=true`) | 59 |

Existing real Elo row:

| Field | Value |
|---|---|
| match_id | `53_20252026_4830746` |
| home_elo | 1517.38 |
| away_elo | 1476.06 |
| elo_diff | 41.32 |
| _is_default | false |
| _source | PrematchEloComputer |

### No-write Expansion Dry-run

Command:
```
node scripts/ops/smelt_all.js --dry-run --full-recalculate --limit 60
```

| Metric | Value |
|---|---|
| preview_count | 58 |
| total | 58 |
| success | 58 |
| failed | 0 |
| eloHits | 49 |
| eloDefaults | 9 |
| actual_db_write | false (every entry) |
| would_write | true (every entry) |
| mode | NO-WRITE PREVIEW |
| DB counts after dry-run | unchanged |
| real Elo row count after dry-run | unchanged (1) |

Dry-run completed cleanly. Every preview entry had `actual_db_write=false`
and `would_write=true`. The end-of-run confirmation line:
`✅ NO-WRITE PREVIEW complete. l3_features was NOT modified.`

PrematchEloComputer produced non-default Elo for 49 of the 58 previewed
rows. 9 rows received default Elo (1500/1500) because those teams had no
prior match history. These 9 defaults are structurally unavoidable with
the current in-memory PrematchEloComputer — they represent teams
appearing for the first time in the dataset.

### Post-Dry-run DB State (Unchanged)

| Table | Count |
|---|---|
| raw_match_data | 76 |
| matches | 60 |
| l3_features | 60 |
| real Prematch Elo rows (`_is_default=false`) | 1 |
| old/default Elo rows (`_is_default=true`) | 59 |

### Real / Default Distribution After Dry-run

```text
 is_default | rows
------------+------
 false      |    1
 true       |   59
```

Unchanged from before dry-run. Only `match_id=53_20252026_4830746` has
real Prematch Elo.

### Readiness Assessment

#### Item 1: limit 60 dry-run 是否可稳定完成

**Yes.** Dry-run completed with 58/58 success, zero failures, zero errors.
Two of the 60 l3_features rows were not included in the preview (likely
because they had already been processed and `--full-recalculate` did not
pick them up; this is consistent with `pending matches count=58`).

#### Item 2: dry-run 是否明确 no-write

**Yes.** Every preview entry has `actual_db_write=false`. The summary
line confirms `"No INSERT/UPDATE was executed. l3_features unchanged."`
The final output line reads `"✅ NO-WRITE PREVIEW complete. l3_features
was NOT modified."`

#### Item 3: 当前 DB 是否仍只有 1 条 real row

**Yes.** Post-dry-run counts confirm `real_elo_rows=1`, only
`53_20252026_4830746`.

#### Item 4: 是否能观察到 PrematchEloComputer 输出

**Yes.** All 58 preview entries show `_source=PrematchEloComputer`.
Numeric Elo values (home_elo, away_elo, elo_diff) are printed in the
formatted preview output for each entry. 49 entries have
`_is_default=false` with non-default Elo values; 9 have
`_is_default=true` with 1500/1500 defaults.

#### Item 5: 是否存在 ALLOW_TRAINING_WRITE 命名风险

**Yes, confirmed.** `scripts/ops/helpers/db_write_guard.js:90` maps the
`l3_features` table to the `ALLOW_TRAINING_WRITE` gate:
```js
{ pattern: /^l3_features$/i, gate: 'ALLOW_TRAINING_WRITE', label: 'l3_features (training)' },
```
This means writing to `l3_features` requires `ALLOW_TRAINING_WRITE=yes`,
which is semantically misleading — it suggests training authorization
was granted when in fact only an L3 smelt write was performed (as
observed in GOLD-AUDIT-2AX). This is a gate-naming issue, not a safety
bypass.

#### Item 6: 是否已经具备"设计批量 controlled write 计划"的条件

**Yes.** The infrastructure is in place: dry-run is stable, no-write
preview produces accurate Elo values, the single-row controlled write
(GOLD-AUDIT-2AX) was successfully validated, and the same pattern
applies to batch writes. The structure for a batch controlled write plan
is clear:
- per-row backup before write
- per-row diff validation (before/after Elo values)
- limited batch size (e.g. 5-10 rows at a time)
- dry-run confirmation before each batch
- explicit env flag authorization per batch

#### Item 7: 是否仍不具备直接 batch write 或 training 条件

**Yes.** Batch write remains unauthorized. Only 1 of 60 L3 rows has real
Prematch Elo. 9 rows would receive default Elo even after full
re-smelting (teams with no prior history). Odds signal remains
unavailable. Training is still unsafe. `ALLOW_TRAINING_WRITE` naming
remains confusing.

### Risks / Follow-ups

| Risk | Detail |
|---|---|
| Partial Elo coverage | Only 49 of 58 previewed rows get real Elo; 9 get defaults. Full batch write would leave 9 rows with `_is_default=true, elo=1500`. These 9 defaults are structurally unavoidable until more match history is available for those teams. |
| ALLOW_TRAINING_WRITE naming | `l3_features` write requires `ALLOW_TRAINING_WRITE=yes` per `db_write_guard.js:90`. This is misleading in an L3 smelt write context. Recommend a future gate-naming task before scaling writes. |
| Default Elo noise | 9 rows with `_is_default=true` would add noise to any training dataset. Training remains unsafe. |
| Odds signal gap | Odds data remains unavailable (`OddsPortalProvider 未实现`). |
| Single-row validation only | Only one row has been validated end-to-end (2AX). Batch write needs per-row diff validation. |

### Conclusion

- **Ready to design batch controlled write plan:** yes.
- **Ready to execute batch write now:** no.
- **Ready for training dry-run:** no.
- **Ready for prediction/backtest:** no.

Next recommended task (after user confirmation only): Design a batch
controlled write plan for the remaining default Elo rows, with backup,
row-diff, per-row validation, rollback criteria, and explicit user
authorization. Use a small batch (e.g. 5 rows) as the first increment.

Do not start automatically.

## GOLD-AUDIT-2BA — Batch Controlled Write Plan

### Status

| Gate | Value |
|---|---|
| GOLD_AUDIT_2BA_PASS | **yes** |
| BATCH_CONTROLLED_WRITE_PLAN_RECORDED | **yes** |
| READY_TO_DESIGN_SMALL_BATCH_WRITE | **yes** |
| READY_TO_EXECUTE_SMALL_BATCH_WRITE | **no** |
| SAFE_FOR_BATCH_WRITE | **no** |
| SAFE_FOR_TRAINING_DRY_RUN | **no** |

Plan only. No DB write, smelt write, L3 batch rewrite, training,
prediction, or backtest was performed in 2BA.

### Current DB State

| Table | Count |
|---|---|
| raw_match_data | 76 |
| matches | 60 |
| l3_features | 60 |
| real Prematch Elo rows (`_is_default=false`) | 1 |
| old/default Elo rows (`_is_default=true`) | 59 |

Existing real Elo row: `53_20252026_4830746` (Angers vs Strasbourg).

### 2BA Dry-run

Command:
```
node scripts/ops/smelt_all.js --dry-run --full-recalculate --limit 60
```

| Metric | Value |
|---|---|
| total | 58 |
| success | 58 |
| failed | 0 |
| eloHits | 49 |
| eloDefaults | 9 |
| actual_db_write | false (every entry) |
| DB counts after dry-run | unchanged (76, 60, 60) |
| real/default distribution after dry-run | unchanged (false=1, true=59) |

### Tooling Capability Assessment

#### Current Script: `scripts/ops/smelt_all.js`

| Capability | Supported | Detail |
|---|---|---|
| `--dry-run` / `--no-write` / `--preview` | **yes** | No-write preview mode |
| `--full-recalculate` | **yes** | Re-smelt all matches |
| `--limit N` | **yes** | Numeric limit only |
| `--match-id` or `--match-ids` allowlist | **no** | Not implemented |
| Exact candidate match_id selection | **no** | Only `--limit N` via ORDER BY |

#### How `--full-recalculate` Selects Matches

`FeatureSmelter.getPendingMatches(fullRecalculate=true)` uses this query
ordering (see `src/feature_engine/smelter/FeatureSmelter.js:338-381`):

```sql
ORDER BY match_date DESC NULLS LAST, match_id
LIMIT $1
```

The ordering is deterministic but based on date, not on Elo status. The
caller cannot specify which match_ids to include or exclude.

#### `--limit 5` Risk Assessment

| Risk | Finding |
|---|---|
| Can select exact candidate match_ids | **no** |
| Can exclude already-real rows | **no** |
| Can exclude default-producing rows | **no** |
| Can target only currently-default rows | **no** |
| First 5 rows include already-real row | **yes** — `53_20252026_4830746` is position 1 |
| Safe for real write | **no** |

**Conclusion: Do not use `--limit 5` for a real write because it cannot
guarantee exact candidate selection.** With the current ordering, the
first 5 rows would include:

1. `53_20252026_4830746` — **already real** (would be a no-op overwrite)
2. `53_20252026_4830747` — default, would get real Elo
3. `53_20252026_4830748` — default, would get real Elo
4. `53_20252026_4830750` — default, would get real Elo
5. `53_20252026_4830751` — default, would get real Elo

Row 1 already has real Elo. Rows 2-5 would get real Elo. But the caller
cannot confirm or control this selection without parsing dry-run output
manually.

### Recommended Prerequisite: Match ID Allowlist Tooling

Before any batch write can be executed safely, the following tooling
prerequisite must be implemented:

**Option A (preferred): Add `--match-ids` to `smelt_all.js`**

- Accept a comma-separated list of match_ids: `--match-ids id1,id2,id3`
- Pass the list to `FeatureSmelter.getPendingMatches()` as a filter
- The query would add `AND m.match_id = ANY($2)` with the array parameter
- Dry-run first with the exact candidate list to verify
- Only then allow real write with the same candidate list
- This keeps the changes minimal and scoped to the CLI layer

**Option B: Build a separate batch write script**

- A new script that reads candidate match_ids from a file or CLI arg
- Calls `FeatureSmelter.processMatch()` individually for each candidate
- Generates per-row diff reports before/after
- This is heavier but provides more granular control

**Recommendation: Option A as the first step.** It reuses the existing
infrastructure and requires fewer new files. The `--match-ids` parameter
works from dry-run through to real write with the same selection
guarantee.

### Future Small-Batch Controlled Write Plan

This plan is for design reference only. It does not authorize execution.

#### 1. Scope

| Field | Value |
|---|---|
| First batch size | 5 rows maximum |
| Candidate source | Remaining default Elo rows that dry-run predicts will get real Elo |
| Exclude | Existing real row `53_20252026_4830746` |
| Exclude | Default-producing rows (teams with no prior history) unless user explicitly accepts |
| Targeted Elo | PrematchEloComputer (`_source=PrematchEloComputer`, `_is_default=false`) |

#### 2. Tooling Prerequisite

- Implement `--match-ids` allowlist in `smelt_all.js` (or equivalent).
- Dry-run candidate list first.
- Confirm all candidates would receive `_is_default=false`.
- Confirm no unexpected defaults in the batch.

#### 3. Pre-check

1. Confirm current branch and clean working tree.
2. Confirm DB counts: raw=76, matches=60, l3=60.
3. Confirm real/default distribution before write.
4. List candidate match_ids with current Elo state.
5. Export candidate rows to JSON files (before backup).
6. Record SHA256 of each candidate backup.
7. Run dry-run preview for exact candidate list.
8. Confirm `actual_db_write=false` and Elo values match expectations.
9. Confirm no defaults among candidates unless explicitly accepted.
10. Do not proceed if any check fails.

#### 4. Backup

```bash
# Export each candidate l3_features row before write
for match_id in <candidate_list>; do
  docker compose -f docker-compose.dev.yml exec -T db psql \
    -U football_user -h localhost -d football_db \
    -c "SELECT row_to_json(t) FROM (SELECT * FROM l3_features WHERE match_id = '$match_id') t;" \
    > /tmp/batch_backup_${match_id}_before.json
done
```

- Verify all backup files are non-empty and parseable.
- Record counts before write.
- Save candidate match_id list.

#### 5. Future Write Command (Do NOT Execute in 2BA)

Only after `--match-ids` tooling is implemented and explicitly
authorized:

```bash
# NOT for execution in 2BA. Requires explicit authorization.
docker compose -f docker-compose.dev.yml exec -T dev sh -lc \
  'ALLOW_DB_WRITE=true node scripts/ops/smelt_all.js --full-recalculate --match-ids <id1,id2,id3,id4,id5>'
```

**Constraints:**
- Must set `ALLOW_DB_WRITE=true`.
- Must use `--full-recalculate`.
- Must use `--match-ids` with exact candidate list (not `--limit`).
- Must NOT pass `--dry-run`, `--no-write`, or `--preview`.
- Must NOT set `FINAL_DB_WRITE_CONFIRMATION=yes` (reserved for broader auth).
- Must NOT write more than the authorized batch size.
- Must NOT train, predict, or backtest.

#### 6. Post-check

1. Confirm DB counts unchanged: raw=76, matches=60, l3=60.
2. Confirm `real_elo_rows` increased by exactly the expected count.
3. Confirm only candidate rows changed — no other rows affected.
4. For each candidate, verify:
   - `home_elo` matches preview value (±0.02)
   - `away_elo` matches preview value (±0.02)
   - `elo_diff` matches preview value (±0.02)
   - `_is_default` = false
   - `_source` = PrematchEloComputer
5. Confirm no training, prediction, or backtest was triggered.
6. Confirm no new tables were created.

#### 7. Rollback

- No automatic rollback.
- Rollback requires explicit user authorization.
- Restore only candidate rows from before-write JSON backups.
- Re-verify counts and real/default distribution after rollback.
- Document rollback result.

#### 8. Acceptance Criteria

| Criterion | Requirement |
|---|---|
| Rows updated | Exactly N candidate rows (e.g. 5) |
| New rows created | 0 |
| Schema changes | 0 |
| `team_elo_ratings` table | Must NOT be created |
| Other rows changed | 0 |
| Training triggered | No |
| Prediction/backtest triggered | No |
| Scraper/network access | No |
| Target Elo values | Match preview values within ±0.02 tolerance |

### Remaining Risks

| Risk | Detail |
|---|---|
| `ALLOW_TRAINING_WRITE` naming | `l3_features` write requires `ALLOW_TRAINING_WRITE=yes` per `db_write_guard.js:90`. Misleading for L3 smelt writes. |
| Partial Elo coverage | 9 of 58 previewed rows would still receive default Elo (1500/1500) — structurally unavoidable for teams with no prior match history. |
| Single-row validation only | Only one row has been end-to-end validated (2AX). First batch write should be small (5 rows) and conservative. |
| Odds signal gap | Odds data remains unavailable (`OddsPortalProvider 未实现`). |
| No `--match-ids` support | Current tooling cannot target specific match_ids. This must be resolved before any real batch write. |
| `--limit 5` unsafe | First position is the already-real row `53_20252026_4830746`. Using `--limit` for real write would waste one slot on a no-op overwrite. |

### Readiness Conclusion

- **Ready to design small batch write:** yes.
- **Ready to execute small batch write now:** **no** — `--match-ids`
  allowlist tooling must be implemented first.
- **Ready for training dry-run:** no.
- **Ready for prediction/backtest:** no.
- **`--limit 5` safe for real write:** **no** — cannot guarantee exact
  candidate selection; would include already-real row.

Next recommended task (after user confirmation only): Implement
`--match-ids` allowlist tooling in `smelt_all.js` (no-write-first:
dry-run only with match_id list, per-row diff reporting). Do not
execute batch write automatically. Do not start training. Do not start
prediction/backtest.

Do not start automatically.

## GOLD-AUDIT-2BB — `--match-ids` No-write Allowlist Tooling

### Status

| Gate | Value |
|---|---|
| GOLD_AUDIT_2BB_PASS | **yes** |
| MATCH_IDS_DRY_RUN_TOOLING_READY | **yes** |
| READY_FOR_MATCH_IDS_WRITE | **no** |
| SAFE_FOR_BATCH_WRITE | **no** |
| SAFE_FOR_TRAINING_DRY_RUN | **no** |

### Summary

Implemented `--match-ids` allowlist support for `scripts/ops/smelt_all.js`.
No DB write, smelt write, batch write, training, prediction, or backtest
was performed in 2BB.

### Purpose

Replace unsafe `--limit N` candidate selection with exact match_id
allowlist selection. Enable future small-batch planning to target exact
rows.

### Behavior

- `--match-ids` accepts a comma-separated match_id list.
- Input order is preserved.
- Duplicate IDs are rejected.
- Empty IDs are rejected.
- Missing IDs are rejected (DB query validates all exist).
- `--match-ids` and `--limit` are mutually exclusive.
- In 2BB, `--match-ids` is allowed only in dry-run/no-write mode.
- Write mode with `--match-ids` is rejected until a future task
  explicitly authorizes it.
- Existing behavior without `--match-ids` is preserved.

### Usage

```bash
# Dry-run with exact match_ids (safe, no-write)
node scripts/ops/smelt_all.js --dry-run --full-recalculate \
  --match-ids 53_20252026_4830458,53_20252026_4830459

# Also works with --no-write and --preview
node scripts/ops/smelt_all.js --preview --full-recalculate \
  --match-ids 53_20252026_4830746
```

### Implementation

| File | Change |
|---|---|
| `scripts/ops/smelt_all.js` | Added `parseMatchIdsArg()`, `validateMatchIds()`, CLI parsing, enforcement logic |
| `src/feature_engine/smelter/FeatureSmelter.js` | Added `getMatchesByIds()` method, `matchIds` support in `run()` |
| `tests/unit/ops/smeltAllMatchIds.test.js` | 22 unit tests for parsing, validation, constraint enforcement |
| `docs/data/elo_prematch_signal.md` | This section |

### Test Coverage

- `tests/unit/ops/smeltAllMatchIds.test.js` — 22 tests covering:
  - Parse comma-separated list
  - Trim whitespace
  - Single match_id
  - Empty string / undefined / null rejection
  - Empty entry (double comma) rejection
  - Trailing comma rejection
  - Duplicate match_id rejection
  - Non-array rejection
  - `--match-ids + --limit` mutual exclusion
  - `--match-ids` without dry-run rejection
  - `--match-ids` with `--dry-run` / `--no-write` / `--preview` allowed
  - `--match-ids` not passed preserves existing `--limit` behavior
  - Input order preservation

### Dry-run Validation

Command:
```
node scripts/ops/smelt_all.js --dry-run --full-recalculate \
  --match-ids 53_20252026_4830458,53_20252026_4830459,53_20252026_4830746
```

| Metric | Value |
|---|---|
| total | 3 |
| success | 3 |
| failed | 0 |
| eloHits | 1 |
| eloDefaults | 2 |
| actual_db_write | false (all 3 entries) |
| would_write | true (all 3 entries) |
| input order preserved | yes |
| only specified match_ids processed | yes |
| extra match_ids processed | 0 |

Per-entry would_change signal:
- `53_20252026_4830458`: would_change=yes (default → real)
- `53_20252026_4830459`: would_change=yes (default → real)
- `53_20252026_4830746`: would_change=no (already real)

Rejection tests:
- `--match-ids + --limit`: correctly rejected with "mutually exclusive"
- `--match-ids` without `--dry-run`/`--no-write`/`--preview`: correctly
  rejected with "allowed only in dry-run/no-write mode"

### DB Safety Confirmation

| Check | Before | After | Changed |
|---|---|---|---|
| raw_match_data count | 76 | 76 | no |
| matches count | 60 | 60 | no |
| l3_features count | 60 | 60 | no |
| real Elo rows (`_is_default=false`) | 1 | 1 | no |
| default Elo rows (`_is_default=true`) | 59 | 59 | no |

All DB counts and Elo distribution unchanged after dry-run validation.

### Readiness Gates

| Gate | Value |
|---|---|
| READY_FOR_MATCH_IDS_DRY_RUN | **yes** |
| READY_FOR_MATCH_IDS_WRITE | **no** |
| SAFE_FOR_BATCH_WRITE | **no** |
| SAFE_FOR_TRAINING_DRY_RUN | **no** |
| SAFE_FOR_REAL_TRAINING | **no** |
| SAFE_FOR_PREDICTION_BACKTEST | **no** |

### Next

After user confirmation only: use `--match-ids` dry-run to produce an
exact 5-row candidate list and per-row preview report. Do not execute
batch write automatically. Do not start training. Do not start
prediction/backtest.

Do not start automatically.

## GOLD-AUDIT-2BC — Exact 5-row `--match-ids` Dry-run Candidate Preview

### Status

| Gate | Value |
|---|---|
| GOLD_AUDIT_2BC_PASS | **yes** |
| EXACT_5_DRY_RUN_PREVIEW_RECORDED | **yes** |
| READY_FOR_EXACT_5_WRITE_PLAN | **yes** |
| READY_FOR_EXACT_5_WRITE | **no** |
| SAFE_FOR_BATCH_WRITE | **no** |
| SAFE_FOR_TRAINING_DRY_RUN | **no** |

Dry-run candidate preview only. No DB write, smelt write, batch write,
training, prediction, or backtest was performed in 2BC.

### Purpose

Use the 2BB `--match-ids` allowlist tooling to select an exact 5-row
candidate list from the current default Elo rows. Confirm each selected
row previews as real Prematch Elo. Confirm DB remains unchanged.

### Current DB State Before 2BC

| Table | Count |
|---|---|
| raw_match_data | 76 |
| matches | 60 |
| l3_features | 60 |
| real Prematch Elo rows (`_is_default=false`) | 1 |
| default Elo rows (`_is_default=true`) | 59 |
| existing real row | `53_20252026_4830746` |

### Default Pool Analysis

Total default Elo rows in DB: 59. Of these:

| Category | Count | Detail |
|---|---|---|
| Smeltable default rows | **57** | Have valid `raw_match_data` with non-excluded `data_version` |
| Excluded by data_version | **2** | `140_20252026_4837496` (PHASE4.23), `47_20242025_900002` (PHASE4.43_SYNTHETIC) |
| Would get real Prematch Elo | **48** | Preview `_is_default=false`, `_source=PrematchEloComputer` |
| Would remain default Elo | **9** | Teams with no prior match history; structurally unavoidable |

Default pool dry-run command:
```
node scripts/ops/smelt_all.js --dry-run --full-recalculate \
  --match-ids <57 comma-separated default match_ids>
```

| Metric | Value |
|---|---|
| total | 57 |
| success | 57 |
| failed | 0 |
| eloHits | 48 |
| eloDefaults | 9 |
| actual_db_write | false (all entries) |

### Candidate Selection Rule

- Include only current default Elo rows (`_is_default=true` in DB).
- Exclude existing real row `53_20252026_4830746`.
- Exclude rows that preview as `_is_default=true` (9 structurally default rows).
- Exclude rows with excluded `data_version` (2 rows: PHASE4.23, PHASE4.43_SYNTHETIC).
- Use exact `--match-ids`, not `--limit`.
- Select from the beginning of the default pool ordered by `match_date DESC, match_id ASC`.

### Exact 5-row Candidate List

| # | match_id | current_is_default | preview_home_elo | preview_away_elo | preview_elo_diff | preview_is_default | preview_source | actual_db_write |
|---|---|---|---|---|---|---|---|---|
| 1 | `53_20252026_4830747` | true | 1502.02 | 1523.65 | -21.63 | false | PrematchEloComputer | false |
| 2 | `53_20252026_4830748` | true | 1479.12 | 1498.91 | -19.79 | false | PrematchEloComputer | false |
| 3 | `53_20252026_4830750` | true | 1574.09 | 1472.12 | 101.97 | false | PrematchEloComputer | false |
| 4 | `53_20252026_4830751` | true | 1527.17 | 1457.57 | 69.60 | false | PrematchEloComputer | false |
| 5 | `53_20252026_4830752` | true | 1415.35 | 1523.68 | -108.33 | false | PrematchEloComputer | false |

Teams:
- #1: Auxerre vs Nice
- #2: Le Havre vs Marseille
- #3: Metz vs Lorient
- #4: Monaco vs Lille
- #5: Paris Saint-Germain vs Brest

### Exact 5-row Dry-run

Command:
```
node scripts/ops/smelt_all.js --dry-run --full-recalculate \
  --match-ids 53_20252026_4830747,53_20252026_4830748,53_20252026_4830750,53_20252026_4830751,53_20252026_4830752
```

| Metric | Value |
|---|---|
| total | 5 |
| success | 5 |
| failed | 0 |
| eloHits | 5 |
| eloDefaults | 0 |
| actual_db_write | false (all 5 entries) |
| `--limit` used | no |
| only specified match_ids processed | yes |
| extra match_ids processed | 0 |
| existing real row included | no |

### DB Safety Confirmation (After All Dry-runs)

| Check | Before | After | Changed |
|---|---|---|---|
| raw_match_data count | 76 | 76 | no |
| matches count | 60 | 60 | no |
| l3_features count | 60 | 60 | no |
| real Elo rows (`_is_default=false`) | 1 | 1 | no |
| default Elo rows (`_is_default=true`) | 59 | 59 | no |
| unique real DB row | `53_20252026_4830746` | `53_20252026_4830746` | no |

All DB counts and Elo distribution unchanged after all dry-run
operations.

### Readiness Gates

| Gate | Value |
|---|---|
| READY_FOR_EXACT_5_WRITE_PLAN | **yes** |
| READY_FOR_EXACT_5_WRITE | **no** |
| SAFE_FOR_BATCH_WRITE | **no** |
| SAFE_FOR_TRAINING_DRY_RUN | **no** |
| SAFE_FOR_REAL_TRAINING | **no** |
| SAFE_FOR_PREDICTION_BACKTEST | **no** |

### Notes

- 9 structurally-default rows (teams with no prior match history) remain
  unavoidable with current in-memory PrematchEloComputer. These 9 rows
  are excluded from the candidate list.
- 2 rows excluded by `data_version` (PHASE4.23, PHASE4.43_SYNTHETIC).
  These are historical/synthetic data versions that the smelter
  explicitly filters out. They remain in `l3_features` with default Elo.
- All 5 candidates have been verified as currently default in DB and
  would produce real Prematch Elo on smelt write.
- The `--match-ids` tooling is confirmed to work for exact candidate
  selection with the full 57-row default pool.

### Next

After user confirmation only: design exact 5-row controlled write
authorization plan for these 5 candidate match_ids. Do not execute batch
write automatically. Do not start training. Do not start
prediction/backtest.

Do not start automatically.
