# PageProps V2 No-Write Preview - Phase 5.21L2D

## 1. Executive summary

Phase 5.21L2C selected `fotmob_pageprops_v2` as the recommended future
canonical FotMob raw shape. The policy is to store full
`__NEXT_DATA__.props.pageProps` as raw v2, use
`stable_pageprops_payload_v1` for stable hashing, treat the current transformed
payload as derived/helper data, and keep parser/features/training deferred.

Phase 5.21L2D adds a single-target no-write preview for:

- match: `53_20252026_4830747`
- external_id: `4830747`
- teams: Auxerre vs Nice

The preview constructs a `fotmob_pageprops_v2` candidate in memory, computes the
stable pageProps hash, and compares it with the existing
`fotmob_html_hyd_v1` raw row. It does not write DB rows, create v2 rows, save or
print the full HTML body, save or print full JSON, implement parser/features,
train, or predict.

## 2. Baseline

Pre-implementation DB baseline:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |   10 |
| raw_match_data          |   10 |
| bookmaker_odds_history  |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    2 |

Stored target v1 raw row:

| field         | value                                                              |
| ------------- | ------------------------------------------------------------------ |
| match_id      | `53_20252026_4830747`                                              |
| external_id   | `4830747`                                                          |
| home_team     | `Auxerre`                                                          |
| away_team     | `Nice`                                                             |
| data_version  | `fotmob_html_hyd_v1`                                               |
| data_hash     | `8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25` |
| raw_data_type | `object`                                                           |
| required keys | `_meta`, `content`, `general`, `header`, `matchId`                 |

Protected tables were at two rows each before implementation.

## 3. Live request summary

The real no-write live preview is intentionally deferred until after:

- PR merge
- main push CI success
- local branch is `main`
- worktree is clean
- DB baseline remains `10 / 10 / 2 / 2 / 2 / 2`
- target stored v1 raw row still exists

The preview script emits these fields in stdout summary JSON after the
post-merge run:

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

No full body or full JSON is printed or saved by the script.

## 4. Candidate v2 summary

Candidate policy:

| field                | value                         |
| -------------------- | ----------------------------- |
| candidate_version    | `fotmob_pageprops_v2`         |
| hash_strategy        | `stable_pageprops_payload_v1` |
| stable hash basis    | canonical JSON of `pageProps` |
| wrapper              | `_meta` plus `pageProps`      |
| volatile metadata    | excluded from stable hash     |
| full HTML body       | not stored                    |
| full `__NEXT_DATA__` | not stored by default         |

The post-merge run emits:

- `stable_pageprops_hash`
- pageProps top-level keys
- v2 candidate JSON byte length
- v2 pageProps path count
- v2 content path count
- module coverage

## 5. V2 vs Existing V1 Comparison

The preview compares the current `fotmob_html_hyd_v1` transformed payload with
the in-memory `fotmob_pageprops_v2` candidate:

- `v1_json_byte_length`
- `v2_candidate_json_byte_length`
- `size_ratio_v2_candidate_to_v1`
- `v1_path_count`
- `v2_path_count`
- `v1_content_path_count`
- `v2_content_path_count`
- `v2_only_path_count`
- `v1_only_path_count`
- `content_missing_from_v2_count`
- `content_missing_from_v1_count`
- `content_diff_path_count`

Limited samples are capped at 50 paths each:

- v2-only paths
- v1-only paths
- content diff paths

Path names are emitted; field values are not.

## 6. Module comparison

The preview compares v1/v2 coverage for:

| module                 | expected role                      |
| ---------------------- | ---------------------------------- |
| `content.matchFacts`   | match facts and event-like content |
| `content.lineup`       | lineup tree                        |
| `content.liveticker`   | ticker/event tree                  |
| `content.playerStats`  | player/stat-level content          |
| `content.shotmap`      | shot-level content                 |
| `content.stats`        | team/stat-level content            |
| `content.h2h`          | head-to-head context               |
| `content.table`        | table context                      |
| `content.momentum`     | momentum timeline                  |
| `seo`                  | pageProps sibling absent from v1   |
| `seo.eventJSONLD`      | structured event metadata          |
| `seo.breadcrumbJSONLD` | breadcrumb metadata                |
| `translations`         | page-level translations            |
| `fallback`             | page-level fallback state          |
| `nav`                  | page-level navigation context      |
| `ongoing`              | page-level match state             |
| `ssr`                  | page-level rendering state         |

The expected hypothesis from Phase 5.21L2B is that deep `content` is preserved
for this target while pageProps siblings are present only in v2.

## 7. Assessment

The preview answers:

- whether the pageProps v2 candidate is valid
- whether it is more complete than v1
- whether it preserves v1 deep content
- whether it additionally preserves pageProps siblings
- whether the next phase should be pageProps v2 write planning
- whether parser/features/training must remain deferred

Success criteria:

- live HTML hydration parses successfully
- `props.pageProps` exists
- v2 candidate has `_meta` and `pageProps`
- stable hash is computed from canonical pageProps only
- no DB/raw write occurs
- no full body or full JSON is printed or saved

## 8. Next phase recommendation

If the post-merge preview succeeds, the recommended next phase is:

`Phase 5.21L2E: pageProps v2 controlled write planning`

Scope:

- no DB write
- review `raw_match_data` schema
- decide whether current `unique(match_id)` blocks multiple data versions per
  match
- decide between `unique(match_id, data_version)`, a new
  `raw_match_data_versions` table, or continued no-write planning
- plan version coexistence, migration, rollback, and upsert policy
- do not enter parser/features/training

If the preview fails, stop and diagnose route/parser issues. Do not write v2
rows or rewrite v1 rows.

## 9. Explicit non-execution

Before the controlled post-merge no-write preview, this phase performed:

- no DB writes
- no `raw_match_data` writes
- no `matches` writes
- no parser/features work
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no full JSON save/print
- no file deletion
