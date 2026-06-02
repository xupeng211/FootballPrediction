<!-- markdownlint-disable MD013 -->

# FotMob ADG60 Raw JSON DB Storage Review No Feature Parse

- lifecycle: phase-artifact
- phase: ADG60-RAW-JSON-DB-STORAGE-REVIEW-NO-FEATURE-PARSE
- scope: review only
- reviewed PR: #1420
- merge commit: `d3cb2460e307a7a6b10ac8015f18048ea71cec16`
- no new network fetch / DB write / feature parse / raw_match_data insert
- raw_write_ready remains false

## Reviewed Result

### Source

- reviewed PR: #1420
- reviewed table: `fotmob_raw_match_payloads`
- reviewed migration: `database/migrations/V26.5__create_fotmob_raw_match_payloads.sql`
- input: 32 gitignored raw payload files from PR #1418

### DB State

- db_row_count: 32
- distinct_match_id_count: 32
- json_present_count: 32
- inserted (first run): 32
- inserted (idempotent re-run): 0
- existing (idempotent re-run): 32
- jsonb structural integrity: confirmed (nd_struct_ok=true, pp_struct_ok=true)

## Migration Review

| Check | Result |
|---|---|
| Only creates `fotmob_raw_match_payloads` | yes |
| Uses JSONB for `next_data_json` and `page_props_json` | yes |
| Unique constraint on `(source, match_id, raw_payload_sha256)` | yes |
| Indexes for `source/match_id`, `competition/season`, `ingestion_run_id` | yes |
| GIN indexes on both JSONB columns | yes |
| No DROP / TRUNCATE / DELETE | yes |
| No ALTER on unrelated tables | yes |
| **verdict** | **pass** |

## Raw JSON Storage Review

| Check | Result |
|---|---|
| 32/32 raw payload input files found | yes |
| 32/32 `__NEXT_DATA__` successfully extracted and parsed | yes |
| 32/32 `pageProps` located at `props.pageProps` | yes |
| 32/32 `next_data_json` written to jsonb | yes |
| 32/32 `page_props_json` written to jsonb | yes |
| Raw Layer only — no feature extraction | yes |
| **verdict** | **pass** |

## Idempotency Review

| Check | Result |
|---|---|
| First run inserted_count=32 | yes |
| Re-run inserted_count=0, existing_count=32 | yes |
| No duplicate rows | yes |
| ON CONFLICT UPSERT behavior confirmed | yes |
| Old data not deleted/truncated | yes |
| **verdict** | **pass** |

## Safety Review

| Check | Result |
|---|---|
| No FotMob network fetch in helper | true |
| No browser automation | true |
| Raw payload files gitignored (zero committed) | true |
| Report/manifest contain no full JSON body | true |
| No feature parsing (xG, shots, players, events) | true |
| No raw_match_data insert | true |
| No l3_features write | true |
| No match_features_training write | true |
| No predictions write | true |
| raw_write_ready remains false | true |
| **verdict** | **pass** |

## Target Alignment Review

Aligned with the goal: "long-term stable raw JSON acquisition system".

| Aspect | Status |
|---|---|
| Raw Layer DB foundation established | done |
| 32 ADG60 samples in jsonb | done |
| 32/32 structural validation passed | done |
| `__NEXT_DATA__` + pageProps both stored | done |
| Can query raw JSON with `->` / `->>` / jsonb functions | done |
| Multi-league / multi-season target registry | not yet |
| Capture scheduler with retry/backoff | not yet |
| Daily incremental collection | not yet |
| Parser / Feature Layer (from raw jsonb) | deferred |
| Production scheduler integration | deferred |

## Remaining Gaps

- No long-run collection scheduler: targets must be manually selected.
- No multi-league / multi-season expansion yet.
- No retry policy for transient HTTP failures.
- No block detection escalation.
- No raw file cleanup / retention policy implementation.
- No parser from raw jsonb to structured match facts.

## Readiness Decision

- raw_layer_db_ready: true
- ready_for_expansion_planning: true
- ready_for_feature_parsing: false (Raw Layer expansion should come first)
- raw_write_ready remains false
- feature tables remain untouched

## Safety

- new_db_write_performed: false
- new_network_fetch_performed: false
- new_browser_automation_performed: false
- feature_parse_performed: false
- raw_match_data_insert_performed: false
- l3_features_write_performed: false
- match_features_training_write_performed: false
- predictions_write_performed: false
- raw_write_ready_marked: false

## Recommended Next Phase

```
FOTMOB-RAW-JSON-LONG-RUN-COLLECTION-DESIGN
```

Design the long-run collection system: multi-league target registry, capture scheduler, idempotent DB upsert, retry/backoff policy, block detection, and raw file retention — all still without feature parsing.
