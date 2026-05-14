# Controlled Raw Match Data Write - Phase 5.16L2

## 1. Executive summary

Phase 5.16L2 defines the only approved controlled `raw_match_data` write path for
target match `53_20252026_4830746` / `external_id=4830746`.

This phase:

- recaptures the exact FotMob detail payload via the safe route selector
- rebuilds canonical transformed `raw_data`
- compares `raw_data_hash` against the Phase 5.15L2 baseline
- writes only `raw_match_data` inside a transaction when the hash gate matches

This phase does not write `matches`, `bookmaker_odds_history`, `l3_features`,
`match_features_training`, or `predictions`.

## 2. Baseline before write

Expected baseline before real execution:

- `matches=10`
- `raw_match_data=2`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`
- target `matches` row exists for `53_20252026_4830746`
- target `raw_match_data` row does not yet exist

## 3. Pre-write recapture and hash gate

The controlled writer must perform one live recapture via the safe route selector:

- `selected_route=html_hydration`
- `request_url=https://www.fotmob.com/match/4830746`
- `final_url=https://www.fotmob.com/matches/angers-vs-strasbourg/2o4och`
- `http_status=200`
- `hydration_parse_ok=true`
- `looks_like_valid_match_detail=true`

Hash gate:

- baseline `raw_data_hash`:
  `d40f757adccf5be96d107188196efa905b6b573b62d7b4428014d7ce4f39a1f6`
- computed `raw_data_hash` must exactly match the baseline before any DB write
- if the recaptured hash drifts, the script must stop and write nothing

## 4. Transaction execution

The controlled write transaction is intentionally narrow:

1. `BEGIN`
2. `SELECT` target `matches` row
3. `SELECT` target `raw_match_data` row
4. verify protected-table baseline
5. `INSERT INTO raw_match_data (...)` when no row exists
6. `SELECT` inserted-row metadata and protected-table counts
7. `COMMIT`

On any failure the script must `ROLLBACK` and exit non-zero.

## 5. Post-write verification

Expected post-write state after successful real execution:

- `raw_match_data=3`
- `matches=10`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

Expected inserted-row metadata preview:

- `match_id=53_20252026_4830746`
- `external_id=4830746`
- `data_version=fotmob_html_hyd_v1`
- `data_hash=d40f757adccf5be96d107188196efa905b6b573b62d7b4428014d7ce4f39a1f6`
- `collected_at=<UTC timestamp generated during write>`

The script verifies raw-data shape by keys only and must not print the full
`raw_data` payload.

## 6. Next phase

Recommended next phase:

`Phase 5.17L2: raw_match_data local parser planning`

Scope for the next phase:

- read local `raw_match_data` only
- no additional live network access
- no features write yet
- no training
- no prediction
- plan how to extract `matchFacts`, `lineup`, `stats`, `shotmap`, and related detail sections

## 7. Explicit non-execution

Confirmed out of scope for this phase:

- no `matches` writes
- no `bookmaker_odds_history` writes
- no `l3_features` writes
- no `match_features_training` writes
- no `predictions` writes
- no harvest or backfill
- no training or prediction
- no browser or proxy runtime
- no full HTML body save
- no full HTML body print
- no file deletion
