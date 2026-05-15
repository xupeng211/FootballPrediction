# HTML Hydration Source Fidelity Live Compare - Phase 5.21L2B

## 1. Executive summary

Phase 5.21L2A found that stored FotMob `raw_data` is likely a transformed
hydration payload, not full `__NEXT_DATA__`.

Phase 5.21L2B adds a single-target live source fidelity compare for:

- match: `53_20252026_4830747`
- external_id: `4830747`
- teams: Auxerre vs Nice

The compare reads the stored `raw_match_data.raw_data`, performs one controlled
FotMob HTML hydration request, parses live `__NEXT_DATA__` in memory, and
compares live `__NEXT_DATA__.props.pageProps` path coverage against stored
`raw_data`.

No DB write, `raw_match_data` write, parser/features work, training, prediction,
browser/proxy, full body save/print, or full JSON save/print is part of this
phase.

## 2. Baseline

Pre-implementation baseline:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |   10 |
| raw_match_data          |   10 |
| bookmaker_odds_history  |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    2 |

Stored target raw row:

| field          | value                                                              |
| -------------- | ------------------------------------------------------------------ |
| match_id       | `53_20252026_4830747`                                              |
| external_id    | `4830747`                                                          |
| home_team      | `Auxerre`                                                          |
| away_team      | `Nice`                                                             |
| data_version   | `fotmob_html_hyd_v1`                                               |
| data_hash      | `8dfc7faaf236ee9f8090301cce9dede32a11ed5b66f2a89e1b3324064f788b25` |
| raw_data_type  | `object`                                                           |
| top-level keys | `_meta`, `content`, `general`, `header`, `matchId`                 |

Protected tables remained at 2 rows before implementation.

## 3. Live request summary

The real live request is intentionally deferred until after:

- PR merge
- main push CI success
- local branch is `main`
- worktree is clean
- DB baseline remains `10 / 10 / 2 / 2 / 2 / 2`

The live compare script emits these fields without printing or saving the full
body or full JSON:

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

If the live request returns `403`, has invalid hydration, or lacks
`props.pageProps`, the script exits non-zero with a controlled failure. It does
not retry.

## 4. Path coverage comparison

The script computes these path metrics in memory:

- `live_next_data_path_count`
- `live_page_props_path_count`
- `live_content_path_count`
- `stored_raw_data_path_count`
- `stored_content_path_count`
- `stored_vs_page_props_overlap_count`
- `stored_vs_page_props_missing_count`
- `stored_vs_content_overlap_count`
- `stored_vs_content_missing_count`

Missing path samples are capped:

- max 50 source-level missing paths
- max 50 content-level missing paths
- max 50 stored-only paths

The output contains path names only, not values. It does not print full
`__NEXT_DATA__`, full `pageProps`, full stored `raw_data`, or full HTML.

## 5. Module comparison

The module comparison covers:

| module                 | purpose                             |
| ---------------------- | ----------------------------------- |
| `content.matchFacts`   | match facts and event-like data     |
| `content.lineup`       | lineup and player availability tree |
| `content.liveticker`   | live ticker/event timeline tree     |
| `content.playerStats`  | player/stat-level data              |
| `content.shotmap`      | shot-level data                     |
| `content.stats`        | team/stat-level data                |
| `content.h2h`          | head-to-head data                   |
| `content.table`        | league table context                |
| `content.momentum`     | momentum timeline                   |
| `seo`                  | pageProps SEO sibling               |
| `seo.eventJSONLD`      | structured event metadata           |
| `seo.breadcrumbJSONLD` | breadcrumb metadata                 |

The expected pre-live hypothesis is:

- core `content.*` modules are likely present in both live and stored payloads.
- `seo`, `seo.eventJSONLD`, and `seo.breadcrumbJSONLD` are likely present in
  live `pageProps` and absent from stored `raw_data`.
- other `pageProps` siblings may be missing from stored `raw_data`.

## 6. Fidelity assessment

The script explicitly answers:

- whether stored `raw_data` is full `__NEXT_DATA__`
- whether stored `raw_data` is full `pageProps`
- whether stored `raw_data` is a transformed payload
- whether `pageProps` siblings are missing
- whether SEO/breadcrumb fields are missing
- whether deep `content` appears preserved
- whether raw storage strategy needs revision

Based on Phase 5.21L2A code review, stored `raw_data` is expected to be a
transformed payload because current storage keeps only:

- `_meta`
- `content`
- `general`
- `header`
- `matchId`

It does not store the full `props.pageProps` or full `__NEXT_DATA__` wrapper.
The post-merge live compare determines whether that transformation drops only
wrapper/SEO/page-level metadata or also deep match-detail content.

## 7. Next phase recommendation

If the live compare confirms transformed/lossy storage, the recommended next
phase is:

`Phase 5.21L2C: raw storage strategy revision planning`

Scope:

- no DB write
- no parser/features/training
- decide whether raw_data v2 should store full `pageProps` or full
  `__NEXT_DATA__`
- plan versioning, coexistence, and migration policy
- do not rewrite existing raw rows yet

If the live compare shows deep content is preserved and only wrapper/SEO fields
are missing, the next phase should still be:

`Phase 5.21L2C: raw storage policy decision`

Parser/features/training remain deferred until the raw storage policy is
explicitly settled.

## 8. Explicit non-execution

Before the controlled post-merge live compare, this phase performed:

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
