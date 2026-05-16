# PageProps V2 Single-Target Write Preflight - Phase 5.21L2I

## 1. Executive summary

Phase 5.21L2H completed version-aware `raw_match_data` compatibility after the
Phase 5.21L2G schema migration to `UNIQUE(match_id, data_version)`.

This phase adds a pageProps v2 single-target write preflight for:

- target: `4830747`
- match_id: `53_20252026_4830747`
- teams: Auxerre vs Nice
- candidate_version: `fotmob_pageprops_v2`
- hash_strategy: `stable_pageprops_payload_v1`

The preflight constructs the v2 candidate in memory, computes the stable
pageProps hash, SELECTs existing raw versions using `match_id + data_version`,
and reports the next-phase write decision. It does not write DB rows, create a
v2 row, run schema migration, run parser/features, train, or predict.

## 2. Current DB baseline

Read-only baseline before implementation:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   10 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Schema:

- `raw_match_data_match_id_key`: absent
- `raw_match_data_match_id_data_version_key`: present
- unique constraint: `UNIQUE(match_id, data_version)`

Target `4830747` existing versions:

| version               | status |
| --------------------- | ------ |
| `fotmob_html_hyd_v1`  | exists |
| `fotmob_pageprops_v2` | absent |

## 3. Live recapture summary

The real no-write live preflight is intentionally deferred until after:

- PR merge
- main push CI success
- local branch is `main`
- worktree is clean
- DB baseline remains `10 / 10 / 2 / 2 / 2 / 2`
- target `4830747` still has v1 and no v2

The post-merge run records:

| field              | status before post-merge run           |
| ------------------ | -------------------------------------- |
| request_url        | `https://www.fotmob.com/match/4830747` |
| final_url          | emitted by post-merge run              |
| http_status        | emitted by post-merge run              |
| content_type       | emitted by post-merge run              |
| body_byte_length   | emitted by post-merge run              |
| body_sha256        | emitted by post-merge run              |
| next_data_parse_ok | emitted by post-merge run              |
| page_props_found   | emitted by post-merge run              |
| browser/proxy used | `false`                                |
| retry used         | `false`                                |

No full HTML body or full pageProps JSON is printed or saved.

## 4. Candidate v2 summary

Candidate policy:

| field                 | value                                                               |
| --------------------- | ------------------------------------------------------------------- |
| candidate_version     | `fotmob_pageprops_v2`                                               |
| hash_strategy         | `stable_pageprops_payload_v1`                                       |
| stable hash basis     | canonical JSON of `__NEXT_DATA__.props.pageProps`; `_meta` excluded |
| previous_preview_hash | `f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc`  |
| wrapper               | `_meta` plus `pageProps`                                            |
| full HTML body        | not stored / not printed                                            |
| full JSON             | not stored / not printed                                            |

The post-merge run records:

- `stable_pageprops_hash`
- `hash_matches_previous_preview`
- `candidate_json_byte_length`
- pageProps top-level keys
- pageProps path count
- pageProps content path count
- module coverage booleans

## 5. Existing versions / write decision

Expected preflight decision before the post-merge live run:

| field                 | value                     |
| --------------------- | ------------------------- |
| available_versions    | `["fotmob_html_hyd_v1"]`  |
| v1 exists             | `true`                    |
| v2 exists             | `false`                   |
| would_insert_count    | `1`                       |
| would_update_count    | `0`                       |
| would_skip_count      | `0`                       |
| conflict target       | `match_id,data_version`   |
| proposed match_id     | `53_20252026_4830747`     |
| proposed external_id  | `4830747`                 |
| proposed data_version | `fotmob_pageprops_v2`     |
| proposed data_hash    | emitted by post-merge run |

## 6. v1 vs v2 comparison

The preflight reports:

- `v1_json_byte_length`
- `v2_candidate_json_byte_length`
- `v1_path_count`
- `v2_path_count`
- `v1_content_path_count`
- `v2_content_path_count`
- `v2_only_path_count`
- `v1_only_path_count`
- `content_diff_path_count`

Only limited path-name samples are emitted. Field values and full JSON are not
printed.

## 7. Protected tables

The preflight must preserve all row counts:

| table                     | expected rows |
| ------------------------- | ------------: |
| `matches`                 |            10 |
| `raw_match_data`          |            10 |
| `bookmaker_odds_history`  |             2 |
| `l3_features`             |             2 |
| `match_features_training` |             2 |
| `predictions`             |             2 |

## 8. Next phase recommendation

If the post-merge no-write preflight succeeds:

Recommended next phase:

`Phase 5.21L2J: pageProps v2 single-target controlled write`

Requirements:

- explicit final DB-write confirmation
- use the Phase 5.21L2I `stable_pageprops_hash` as the write baseline
- recapture before write and compare the stable hash
- insert exactly one `raw_match_data` row:
    - `match_id=53_20252026_4830747`
    - `external_id=4830747`
    - `data_version=fotmob_pageprops_v2`
    - `data_hash=<Phase 5.21L2I baseline hash>`
- keep existing v1 row
- `raw_match_data` row count should move from 10 to 11
- no parser/features/training

If the Phase 5.21L2I hash drifts from the Phase 5.21L2D preview hash but the
payload is valid, do not write in this phase. Treat the L2I hash as the next
baseline candidate only after user confirmation.

If preflight fails, stop and diagnose route/parser issues before any write.

## 9. Explicit non-execution

Before the controlled post-merge no-write preflight, this phase performs:

- no DB writes
- no `raw_match_data` writes
- no `matches` writes
- no schema migration
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no full JSON save/print
- no file deletion
