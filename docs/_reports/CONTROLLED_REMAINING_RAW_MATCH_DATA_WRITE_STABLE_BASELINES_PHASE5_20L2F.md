# Controlled Remaining Raw Match Data Write Stable Baselines - Phase 5.20L2F

## 1. Executive summary

Phase 5.20L2F executes the controlled remaining `raw_match_data` write using
the Phase 5.20L2E stable baselines.

- target scope: remaining 7 seeded Ligue 1 matches on `2026-05-10`
- fetcher: `FotMobRawDetailFetcher`
- route: `html_hydration`
- hash strategy: `stable_raw_payload_v1`
- baseline source: Phase 5.20L2E stable preflight hashes
- write scope: `raw_match_data` only
- protected scope: no `matches`, bookmaker odds, features, training, or
  predictions writes

## 2. Baseline before write

Required DB baseline before post-merge execution:

- `matches=10`
- `raw_match_data=3`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

Raw coverage before execution:

- existing raw target: `4830746` / `53_20252026_4830746`
- remaining raw rows absent: `4830747`, `4830748`, `4830750`, `4830751`,
  `4830752`, `4830753`, `4830754`

## 3. Stable baselines

Phase 5.20L2E stable baseline hashes:

- `4830747 -> 8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25`
- `4830748 -> 538fc2c33281f65d56f5fc004378e5933c0d3bbabc81d8e640bcb7abb4ad9bc3`
- `4830750 -> c04915c0e972566f56bcb88a004f9e7e282777f9ca512c626a6acd4bd05e7304`
- `4830751 -> 5c603f83265887f223776941dde430e7abc8b8b9a9577d649cfd149339ffbd37`
- `4830752 -> 241e21be67a3f854d3320bbe86857a19c4bc357b6647d8b798df9b2dec6f56d6`
- `4830753 -> 358466958ec7b60b4dfa5e847537391b85153a564300804636497dd683311567`
- `4830754 -> 3a0832dc6bc16892491c11905ad8ab2fd80e4b29ea2f0aaa71d5659e57785c30`

These are the only accepted baseline hashes for the Phase 5.20L2F write gate.

## 4. Pre-write recapture and hash gate

Post-merge execution must recapture the 7 targets once, in order, with:

- `HASH_STRATEGY=stable_raw_payload_v1`
- `CONCURRENCY=1`
- `RETRY=0`
- `PRINT_BODY=no`
- `SAVE_BODY=no`
- no browser runtime
- no proxy runtime

For each target the controlled writer must record:

- `hash_strategy`
- selected route
- request URL and final URL
- body SHA-256
- `raw_data_hash` / `data_hash`
- baseline hash
- hash match result
- `match_id_source`

If any target has hash drift, missing hash output, or strategy mismatch, the
writer must stop before the DB transaction and must not write.

## 5. Transaction execution

Post-merge execution status:

- began: `pending_post_merge_execution`
- inserted_count: `pending_post_merge_execution`
- updated_count: `pending_post_merge_execution`
- skipped_count: `pending_post_merge_execution`
- committed: `pending_post_merge_execution`
- rolled_back: `pending_post_merge_execution`

The only allowed successful transaction is:

- `BEGIN`
- insert 7 rows into `raw_match_data`
- `COMMIT`

## 6. Post-write verification

Required post-write DB counts after success:

- `matches=10`
- `raw_match_data=10`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

Inserted row metadata must be selected without printing `raw_data`:

- `match_id`
- `external_id`
- `data_version`
- `data_hash`
- `collected_at`

Raw data key checks must confirm:

- `_meta`
- `content`
- `general`
- `header`
- `matchId`

## 7. Next phase

Recommended next phase after successful write:

`Phase 5.21L2: raw_match_data inventory and parser-deferred training design`

Phase 5.21L2 should be read-only:

- inventory `raw_match_data=10`
- no network access
- no feature writes
- no training or prediction
- design training target, labels, time split, and leakage policy first
- keep parser implementation deferred until training data design is explicit

## 8. Explicit non-execution

Before controlled post-merge execution, this PR performs:

- no `matches` writes
- no `bookmaker_odds_history` writes
- no `l3_features` writes
- no `match_features_training` writes
- no `predictions` writes
- no parser/features work
- no harvest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no file deletion
