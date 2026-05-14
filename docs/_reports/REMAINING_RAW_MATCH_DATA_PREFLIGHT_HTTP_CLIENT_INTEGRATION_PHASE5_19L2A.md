# Remaining Raw Match Data Preflight HttpClient Integration - Phase 5.19L2A

## 1. Executive summary

Phase 5.19L2 script was merged but returned plan-only results during actual execution.
Phase 5.19L2A fixes the HttpClient dependency integration so the preflight uses
direct `global.fetch` with `html_hydration` URL pattern, bypassing the
hardcoded single-target route selector.

All 7 targets successfully recaptured with real FotMob data.

## 2. Root cause

`runFotMobDetailRouteSelector` has hardcoded TARGET=4830746 and its
`fetchPreviewBody` dependency is not exported. The preflight script's import
failed silently, causing all 7 recaptures to return error responses.

## 3. Fix

- Replaced `runFotMobDetailRouteSelector` import with direct `global.fetch`
- Built `html_hydration` request directly: `https://www.fotmob.com/match/${external_id}`
- Used `extractFromHtml` + `transformToApiFormat` from NextDataParser
- Fixed `looksLikeValid` boolean coercion

## 4. Validation

| check | result |
|---|---|
| target unit tests | 48/48 pass |
| npm test | 48/48 pass |
| npm run test:coverage | pass |
| eslint | clean |
| prettier | clean |
| DB row counts | 10/3/2/2/2/2 (unchanged) |

## 5. Actual post-merge preflight result

| metric | value |
|---|---|
| attempted | 7 |
| valid_payload | 7 |
| failed | 0 |
| would_insert | 7 |
| would_update | 0 |
| would_skip | 0 |
| plan_only | false |
| live_preflight_used | true |

Per-target:

| external_id | home_team | away_team | http_status | raw_data_hash |
|---|---|---|---|---|
| 4830747 | Auxerre | Nice | 200 | ebce5a39cf468facb73a... |
| 4830748 | Le Havre | Marseille | 200 | d9c937ce84ff80ab1ea2... |
| 4830750 | Metz | Lorient | 200 | 62f07323da3101447752... |
| 4830751 | Monaco | Lille | 200 | 6441951cf9291d3e9bcc... |
| 4830752 | Paris Saint-Germain | Brest | 200 | 3c3475929c889f6e56a0... |
| 4830753 | Rennes | Paris FC | 200 | 0ebf496e7dbd93608619... |
| 4830754 | Toulouse | Lyon | 200 | 3eab01076a0347b03b08... |

All decisions: would_insert (no existing raw rows).

## 6. Next phase

**Phase 5.20L2**: controlled remaining raw_match_data write

- final DB-write confirmation
- use preflight raw_data_hashes as baseline
- write only raw_match_data
- rows=7, transaction
- raw_match_data 3 -> 10
- no parser/features/training/prediction

## 7. Explicit non-execution

- no DB writes
- no raw_match_data writes
- no matches writes
- no parser/features
- no harvest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no file deletion
