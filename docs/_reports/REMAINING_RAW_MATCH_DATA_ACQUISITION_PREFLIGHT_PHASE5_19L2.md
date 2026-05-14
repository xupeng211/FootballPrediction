# Remaining Raw Match Data Acquisition Preflight - Phase 5.19L2

## 1. Executive summary

Phase 5.19L2 is **preflight-only**: recaptures the 7 remaining seeded match detail
payloads via safe `html_hydration` route, computes canonical `raw_data` and
`data_hash` per target, SELECTs existing `raw_match_data` rows, and outputs
`would_insert` / `would_update` / `would_skip` per target.

This phase does NOT write the DB and does NOT write `raw_match_data`.

## 2. Baseline

| table                     | rows |
| ------------------------- | ---- |
| `matches`                 | 10   |
| `raw_match_data`          | 3    |
| `bookmaker_odds_history`  | 2    |
| `l3_features`             | 2    |
| `match_features_training` | 2    |
| `predictions`             | 2    |

- has_raw target: `53_20252026_4830746` (Angers vs Strasbourg)
- missing_raw targets: 7

## 3. Preflight input

- source: fotmob
- route: html_hydration
- remaining external IDs: 4830747, 4830748, 4830750, 4830751, 4830752, 4830753, 4830754
- concurrency: 1
- retry: 0
- no browser, no proxy
- no body print, no body save
- no DB write

## 4. Per-target recapture result

(Results from actual live preflight execution will be recorded here)

## 5. Summary decision

(Will be populated after live preflight)

## 6. Protected table baseline

Same as Section 2.

## 7. Raw-first / parse-later

- No parsing into features
- No training
- No prediction
- Parser deferred until training data design

## 8. Next phase

If all 7 targets have valid payloads and `would_insert=7`:

**Phase 5.20L2**: controlled remaining raw_match_data write

Requirements:

- final DB-write confirmation
- use preflight `raw_data_hashes` as baseline
- write only `raw_match_data`
- transaction with post-write verification
- `raw_match_data` 3 -> 10

If any failure/update/skip: do not enter write; report to user.

## 9. Explicit non-execution

Confirmed out of scope for this phase:

- no DB writes
- no raw_match_data writes
- no matches writes
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no file deletion
