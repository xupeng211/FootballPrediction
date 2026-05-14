# FotMob Raw Detail Fetcher Consolidation - Phase 5.20L2A

## 1. Executive summary

Phase 5.19L2A successfully ran the 7 remaining preflight targets but exposed
duplicated fetch+parse+hash logic. Phase 5.20L2A extracts a reusable
FotMobRawDetailFetcher component that can serve any external_id.

No network access. No DB writes.

## 2. Why consolidation now

- Project will handle more than 8 matches
- runFotMobDetailRouteSelector hardcodes TARGET=4830746
- fetchPreviewBody not exported
- Each script would duplicate fetch+parse+hash
- Component ensures consistent raw_data shape and hash strategy

## 3. Component design

**File**: `src/infrastructure/services/FotMobRawDetailFetcher.js`

**Input**: `{ externalId, matchId?, homeTeam?, awayTeam?, dataVersion? }`

**Dependencies**: `{ fetchFn, now?, parser? }`

**Output**: Unified result with http_status, body_sha256, hydration_parse_ok,
raw_data, raw_data_hash, looks_like_valid_match_detail

**Key functions**:
- buildFotMobMatchUrl(externalId)
- buildFotMobHtmlHydrationRequest(externalId)
- validateFetchInput / validateFetchDependencies
- canonicalizeJson / sha256Text / sha256CanonicalJson
- extractHydrationPayload / buildRawDataFromTransformedPayload / looksLikeValidRawDetail
- fetchFotMobRawDetail(input, dependencies)

**Safety**: No browser/proxy/retry/body-save/print allowed. fetchFn must be injected.

## 4. Integrated scripts

- `scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js` — recaptureTarget now delegates to fetchFotMobRawDetail
- Single-target scripts (l2_raw_detail_preview, l2_raw_match_data_ingest_preflight, l2_raw_match_data_write) — not yet refactored; listed for follow-up Phase 5.20L2A-followup

## 5. Validation

| check | result |
|---|---|
| FotMobRawDetailFetcher tests | 39/39 pass |
| remaining preflight tests | 48/48 pass |
| npm test | 48/48 pass |
| npm run test:coverage | pass |
| eslint / prettier | clean |
| DB | 10/3/2/2/2/2 (unchanged) |

## 6. Next phase

**Phase 5.20L2B**: remaining preflight using consolidated fetcher with real live data

Then **Phase 5.20L2C**: controlled remaining raw_match_data write (7 rows, raw_match_data 3→10)

## 7. Explicit non-execution

- no external FotMob access
- no DB writes / raw_match_data writes
- no parser/features
- no harvest/backfill
- no training/prediction
- no browser/proxy
- no file deletion
