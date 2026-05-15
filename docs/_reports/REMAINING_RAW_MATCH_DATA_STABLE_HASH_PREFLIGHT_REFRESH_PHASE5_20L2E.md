# Remaining Raw Match Data Stable Hash Preflight Refresh - Phase 5.20L2E

## 1. Executive summary

Phase 5.20L2D has fixed the FotMob raw detail hash stability issue by moving
`data_hash` / `raw_data_hash` to `stable_raw_payload_v1`.

This Phase 5.20L2E report prepares the controlled stable-hash preflight refresh
for the 7 remaining seeded Ligue 1 targets:

- route: `html_hydration`
- hash strategy: `stable_raw_payload_v1`
- concurrency: `1`
- retry: `0`
- no DB write
- no `raw_match_data` write
- no parser/features
- no training/prediction
- no browser/proxy
- no full body print/save

The purpose is to generate new stable baseline hashes for the remaining 7
targets after PR merge and main CI success. The resulting hashes are intended to
be the only valid baseline input for a later Phase 5.20L2F controlled
`raw_match_data` write.

## 2. Baseline

Start state on `main`:

- start HEAD: `7ec6918 docs(reports): refresh Phase 5.20L2D audit report`
- Phase 5.20L2D implementation PR: `#1244`
- Phase 5.20L2D report refresh PR: `#1245`
- PR `#1245` merge commit:
  `7ec691878d288ec342bd6a0466bbbabf5a757a53`
- latest `main` push CI: `success`

Protected table baseline before this phase:

- `matches=10`
- `raw_match_data=3`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

Seeded Ligue 1 scope:

- seeded matches: `8`
- existing raw target count: `1`
- missing raw target count: `7`
- existing raw target:
  `53_20252026_4830746 / 4830746 / Angers vs Strasbourg`

Missing raw targets:

- `53_20252026_4830747 / 4830747 / Auxerre vs Nice`
- `53_20252026_4830748 / 4830748 / Le Havre vs Marseille`
- `53_20252026_4830750 / 4830750 / Metz vs Lorient`
- `53_20252026_4830751 / 4830751 / Monaco vs Lille`
- `53_20252026_4830752 / 4830752 / Paris Saint-Germain vs Brest`
- `53_20252026_4830753 / 4830753 / Rennes vs Paris FC`
- `53_20252026_4830754 / 4830754 / Toulouse vs Lyon`

## 3. Stable hash strategy confirmation

The stable hash strategy is confirmed before live preflight:

- `FotMobRawDetailFetcher` exports and emits
  `hash_strategy=stable_raw_payload_v1`.
- `stable_raw_payload` contains only stable match detail content:
  `content`, `general`, `header`, and normalized `matchId`.
- `data_hash`, `raw_data_hash`, and `stable_raw_payload_hash` are all computed
  as SHA-256 over canonical JSON of the stable payload.
- volatile `_meta` fields are excluded from `data_hash` / `raw_data_hash`,
  including `fetched_at`, request/final URL, HTTP status, content type, body byte
  length, and `fetch_body_sha256`.
- `raw_data` still keeps `_meta` for audit and future DB storage.
- `raw_data_with_meta_hash` remains audit/debug-only and is not a hash-gate
  baseline.
- `matchId` normalization is:
  `payload.matchId` -> `payload.general.matchId` -> validated
  `input_external_id_fallback`.
- fallback requires the external id plus expected target markers to be present
  in payload and/or request context.
- write validation blocks missing `baseline_hash_strategy`.
- write validation blocks any baseline strategy other than
  `stable_raw_payload_v1`.
- Phase 5.20L2B old hashes are not valid future write baselines.

## 4. Actual stable preflight result

Status before post-merge live preflight:

- attempted_target_count: `pending_post_merge_preflight`
- valid_payload_count: `pending_post_merge_preflight`
- failed_target_count: `pending_post_merge_preflight`
- would_insert_count: `pending_post_merge_preflight`
- would_update_count: `pending_post_merge_preflight`
- would_skip_count: `pending_post_merge_preflight`
- hash_strategy: `stable_raw_payload_v1`
- DB unchanged before live preflight: `yes`

The live preflight is intentionally deferred until all of the following are
true:

- this docs-only PR is merged
- `main` push CI is successful
- local branch is `main`
- local worktree is clean
- protected DB row counts still match the baseline above
- raw coverage remains `has_raw=1 / missing_raw=7`

The post-merge command must be:

```bash
make data-l2-remaining-raw-match-data-acquisition-preflight \
  SOURCE=fotmob \
  LEAGUE_ID=53 \
  SEASON=2025/2026 \
  DATE=2026-05-10 \
  ROUTE=html_hydration \
  REMAINING_EXTERNAL_IDS=4830747,4830748,4830750,4830751,4830752,4830753,4830754 \
  EXPECTED_TARGET_COUNT=7 \
  NETWORK_AUTHORIZATION=yes \
  LIVE_PREVIEW_AUTHORIZATION=yes \
  ALLOW_DB_WRITE=no \
  ALLOW_RAW_MATCH_DATA_WRITE=no \
  ALLOW_MATCHES_WRITE=no \
  ALLOW_PARSER_FEATURES=no \
  ALLOW_TRAINING=no \
  ALLOW_PREDICTION=no \
  CONCURRENCY=1 \
  RETRY=0 \
  PRINT_BODY=no \
  SAVE_BODY=no
```

## 5. New stable baseline hashes

Pending post-merge live preflight. The final Phase 5.20L2E operator report must
record the 7 stable hashes in this mapping format:

- `4830747 -> <stable_raw_payload_v1 raw_data_hash>`
- `4830748 -> <stable_raw_payload_v1 raw_data_hash>`
- `4830750 -> <stable_raw_payload_v1 raw_data_hash>`
- `4830751 -> <stable_raw_payload_v1 raw_data_hash>`
- `4830752 -> <stable_raw_payload_v1 raw_data_hash>`
- `4830753 -> <stable_raw_payload_v1 raw_data_hash>`
- `4830754 -> <stable_raw_payload_v1 raw_data_hash>`

These hashes must be generated by Phase 5.20L2E and used as the only baseline
for Phase 5.20L2F.

## 6. Next phase

If post-merge stable preflight returns:

- `attempted_target_count=7`
- `valid_payload_count=7`
- `failed_target_count=0`
- `would_insert_count=7`
- `would_update_count=0`
- `would_skip_count=0`
- every target uses `hash_strategy=stable_raw_payload_v1`

then recommend:

`Phase 5.20L2F: controlled remaining raw_match_data write using stable baselines`

Phase 5.20L2F must require:

- final user DB-write confirmation
- this Phase 5.20L2E stable baseline hash set
- write only `raw_match_data`
- exactly 7 rows
- single transaction
- post-write verification
- `raw_match_data` row count transition `3 -> 10`
- no parser/features/training/prediction

If any target fails, is invalid, would update, or would skip, do not enter
Phase 5.20L2F. Stop and report for user decision.

## 7. Explicit non-execution

This docs-only preflight refresh report phase performed no production data
mutation before post-merge preflight:

- no DB writes
- no `raw_match_data` writes
- no `matches` writes
- no `bookmaker_odds_history` writes
- no `l3_features` writes
- no `match_features_training` writes
- no `predictions` writes
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no file deletion
