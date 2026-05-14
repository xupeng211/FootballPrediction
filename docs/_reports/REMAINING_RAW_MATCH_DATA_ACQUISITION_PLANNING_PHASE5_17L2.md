# Remaining Raw Match Data Acquisition Planning - Phase 5.17L2

## 1. Executive summary

Phase 5.16L2 already completed one controlled `raw_match_data` write for
`53_20252026_4830746` / `external_id=4830746`.

After that successful write, the user explicitly chose:

- raw first
- parse later
- train-driven parsing

This phase therefore plans the remaining seeded Ligue 1 `2026-05-10` raw
acquisition scope only. It does not touch the network and does not write the DB.

## 2. Current DB baseline

Current expected read-only baseline:

- `matches=10`
- `raw_match_data=3`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

## 3. Seeded matches coverage

| match_id              | external_id | home_team           | away_team  | raw_status    | data_hash                                                          |
| --------------------- | ----------- | ------------------- | ---------- | ------------- | ------------------------------------------------------------------ |
| `53_20252026_4830746` | `4830746`   | Angers              | Strasbourg | `has_raw`     | `d40f757adccf5be96d107188196efa905b6b573b62d7b4428014d7ce4f39a1f6` |
| `53_20252026_4830747` | `4830747`   | Auxerre             | Nice       | `missing_raw` |                                                                    |
| `53_20252026_4830748` | `4830748`   | Le Havre            | Marseille  | `missing_raw` |                                                                    |
| `53_20252026_4830750` | `4830750`   | Metz                | Lorient    | `missing_raw` |                                                                    |
| `53_20252026_4830751` | `4830751`   | Monaco              | Lille      | `missing_raw` |                                                                    |
| `53_20252026_4830752` | `4830752`   | Paris Saint-Germain | Brest      | `missing_raw` |                                                                    |
| `53_20252026_4830753` | `4830753`   | Rennes              | Paris FC   | `missing_raw` |                                                                    |
| `53_20252026_4830754` | `4830754`   | Toulouse            | Lyon       | `missing_raw` |                                                                    |

Coverage conclusion:

- seeded matches: `8`
- existing raw rows: `1`
- missing raw rows: `7`

## 4. Remaining raw targets

Remaining controlled raw acquisition targets are:

1. `53_20252026_4830747` / `4830747` / Auxerre vs Nice
2. `53_20252026_4830748` / `4830748` / Le Havre vs Marseille
3. `53_20252026_4830750` / `4830750` / Metz vs Lorient
4. `53_20252026_4830751` / `4830751` / Monaco vs Lille
5. `53_20252026_4830752` / `4830752` / Paris Saint-Germain vs Brest
6. `53_20252026_4830753` / `4830753` / Rennes vs Paris FC
7. `53_20252026_4830754` / `4830754` / Toulouse vs Lyon

## 5. Why parser is deferred

Parser planning is intentionally deferred because:

- training target design is not settled
- required fields are not yet fixed
- early parsing would likely collect unused fields
- leakage policy is not yet defined
- post-match fields must not accidentally flow into pre-match prediction features

The intended future direction is train-driven parsing:

1. define the training objective
2. define leakage boundaries
3. derive the parser scope from those constraints

## 6. Recommended acquisition strategy

Recommended next acquisition mode:

- controlled small batch
- rows `<= 7`
- route `html_hydration`
- concurrency `= 1`
- retry `= 0`
- no browser
- no proxy
- no full body save
- no full body print
- write target limited to `raw_match_data`
- no parser
- no features
- no training
- no prediction

## 7. Proposed next phases

Recommended sequencing:

1. `Phase 5.18L2`: remaining `raw_match_data` acquisition authorization
2. `Phase 5.19L2`: remaining `raw_match_data` acquisition preflight
3. `Phase 5.20L2`: controlled remaining `raw_match_data` write
4. later: training target design
5. later: local parser planning derived from the training target

## 8. Protected tables

Protected table policy remains:

- `matches`: read-only
- `bookmaker_odds_history`: unchanged
- `l3_features`: unchanged
- `match_features_training`: unchanged
- `predictions`: unchanged

## 9. Validation

Validation required for this phase:

- new planning unit tests
- Makefile planning target
- `npm test`
- `npm run test:coverage`
- `eslint`
- `prettier`
- `git diff --check`
- DB row counts unchanged before and after planning validation

## 10. Explicit non-execution

Confirmed out of scope for this phase:

- no external FotMob access
- no live match detail request
- no DB writes
- no `raw_match_data` writes
- no `matches` writes
- no parser or features work
- no harvest, ingest, or backfill
- no training or prediction
- no full body save
- no full body print
- no file deletion
