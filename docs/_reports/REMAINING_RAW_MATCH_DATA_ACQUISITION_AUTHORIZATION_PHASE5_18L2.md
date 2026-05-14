# Remaining Raw Match Data Acquisition Authorization - Phase 5.18L2

## 1. Executive summary

Main has recovered from the Phase 5.17L2 coverage hotfix (PR #1237).

Phase 5.18L2 is **authorization-only**: the user authorizes the remaining 7 seeded
Ligue 1 2026-05-10 matches for future controlled `raw_match_data` acquisition
via the `html_hydration` route.

This phase does NOT touch the network, does NOT write the DB, and does NOT
write `raw_match_data`. Parser/features/training/prediction remain deferred.

## 2. Current DB baseline

| table                     | rows |
| ------------------------- | ---- |
| `matches`                 | 10   |
| `raw_match_data`          | 3    |
| `bookmaker_odds_history`  | 2    |
| `l3_features`             | 2    |
| `match_features_training` | 2    |
| `predictions`             | 2    |

## 3. Coverage status

| match_id              | external_id | home_team           | away_team  | raw_status    |
| --------------------- | ----------- | ------------------- | ---------- | ------------- |
| `53_20252026_4830746` | `4830746`   | Angers              | Strasbourg | `has_raw`     |
| `53_20252026_4830747` | `4830747`   | Auxerre             | Nice       | `missing_raw` |
| `53_20252026_4830748` | `4830748`   | Le Havre            | Marseille  | `missing_raw` |
| `53_20252026_4830750` | `4830750`   | Metz                | Lorient    | `missing_raw` |
| `53_20252026_4830751` | `4830751`   | Monaco              | Lille      | `missing_raw` |
| `53_20252026_4830752` | `4830752`   | Paris Saint-Germain | Brest      | `missing_raw` |
| `53_20252026_4830753` | `4830753`   | Rennes              | Paris FC   | `missing_raw` |
| `53_20252026_4830754` | `4830754`   | Toulouse            | Lyon       | `missing_raw` |

- seeded matches: 8
- has_raw: 1
- missing_raw: 7

## 4. Authorized remaining scope

The following 7 targets are authorized for future controlled
`raw_match_data` acquisition:

1. `53_20252026_4830747` / `4830747` / Auxerre vs Nice
2. `53_20252026_4830748` / `4830748` / Le Havre vs Marseille
3. `53_20252026_4830750` / `4830750` / Metz vs Lorient
4. `53_20252026_4830751` / `4830751` / Monaco vs Lille
5. `53_20252026_4830752` / `4830752` / Paris Saint-Germain vs Brest
6. `53_20252026_4830753` / `4830753` / Rennes vs Paris FC
7. `53_20252026_4830754` / `4830754` / Toulouse vs Lyon

## 5. Authorization boundary

- authorization does NOT equal network execution
- authorization does NOT equal DB write
- `network_allowed_this_phase=false`
- `raw_match_data_write_allowed_this_phase=false`
- next phase (preflight) is required before any controlled write
- final DB-write confirmation is required later
- only `raw_match_data` table is in scope for future write
- protected tables (matches, features, predictions) are not writable

## 6. Raw-first / parse-later policy

Policy remains as established in Phase 5.17L2:

- parser deferred until training data design
- no features extraction
- no training
- no prediction
- data leakage prevention: post-match fields must not flow into pre-match features

## 7. Next phase requirements

**Phase 5.19L2**: remaining `raw_match_data` acquisition preflight

Requirements:

- recapture exact payload for each of 7 authorized targets
- route: `html_hydration`
- concurrency: 1
- retry: 0
- compute canonical `raw_data` per target
- compute `data_hash` per target
- SELECT existing `raw_match_data` rows
- output `would_insert` / `would_update` / `would_skip`
- verify protected table baselines unchanged
- no DB write in preflight
- no parser/features/training/prediction

## 8. Validation

Validation performed for this phase:

- authorization unit tests
- Makefile authorization target
- `npm test`
- `npm run test:coverage`
- `eslint`
- `prettier`
- `git diff --check`
- DB row counts unchanged

## 9. Explicit non-execution

Confirmed out of scope for this phase:

- no external FotMob access
- no live match detail request
- no DB writes
- no `raw_match_data` writes
- no `matches` writes
- no parser or features work
- no harvest, ingest, or backfill
- no training or prediction
- no file deletion
