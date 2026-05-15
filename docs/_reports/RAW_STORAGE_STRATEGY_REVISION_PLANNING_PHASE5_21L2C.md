# Raw Storage Strategy Revision Planning - Phase 5.21L2C

## 1. Executive summary

Phase 5.21L2B confirmed that the current FotMob `fotmob_html_hyd_v1`
`raw_data` is a transformed hydration payload. For target `4830747` it preserved
the deep match `content` subtree, but it did not store full `pageProps`, full
`__NEXT_DATA__`, pageProps siblings, SEO, breadcrumb, or source wrapper fields.

Current v1 is rich enough to prove useful match-detail data exists, but it is
not the best long-term canonical raw warehouse shape. Phase 5.21L2C is a
planning and policy decision phase only. It does not access FotMob, write DB
rows, rewrite existing raw rows, implement parser/features, train, or predict.

The recommended future policy is:

- canonical FotMob raw v2: `fotmob_pageprops_v2`
- `raw_data` stores full `__NEXT_DATA__.props.pageProps`
- hash strategy: `stable_pageprops_payload_v1`
- transformed payload becomes derived/helper data, not canonical raw
- full `__NEXT_DATA__` is not the default storage shape
- existing v1 rows stay as-is until a separately authorized migration/backfill

## 2. Evidence from Phase 5.21L2A / L2B

Current DB baseline from Phase 5.21L2A:

| table                   | rows |
| ----------------------- | ---: |
| matches                 |   10 |
| raw_match_data          |   10 |
| bookmaker_odds_history  |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    2 |

Phase 5.21L2A provenance inventory:

| data_version          | rows | conclusion                                      |
| --------------------- | ---: | ----------------------------------------------- |
| `fotmob_html_hyd_v1`  |    8 | FotMob transformed hydration payload target     |
| `PHASE4.43_SYNTHETIC` |    1 | legacy/synthetic; excluded from FotMob fidelity |
| `PHASE4.23`           |    1 | unknown provenance; requires future governance  |

Phase 5.21L2B single-target live compare for `4830747`:

| metric                      | value |
| --------------------------- | ----: |
| live_next_data_path_count   | 11164 |
| live_page_props_path_count  |  9678 |
| live_content_path_count     |  6922 |
| stored_raw_data_path_count  |  7220 |
| stored_content_path_count   |  6922 |
| stored vs pageProps missing |  2482 |
| stored vs content missing   |     0 |
| deep content missing ratio  |     0 |

Missing pageProps siblings from stored v1:

- `fallback`
- `fetchingLeagueData`
- `hasPendingVAR`
- `nav`
- `ongoing`
- `seo`
- `ssr`
- `translations`

Stored v1 also lacks `seo.eventJSONLD`, `seo.breadcrumbJSONLD`, and source
wrapper fields such as `appGip`, `buildId`, `dynamicIds`, `gssp`,
`isExperimentalCompile`, `isFallback`, `page`, `props`, `query`, and
`scriptLoader`.

## 3. Policy decision

Recommended canonical raw v2:

| policy field         | decision                                          |
| -------------------- | ------------------------------------------------- |
| data_version         | `fotmob_pageprops_v2`                             |
| raw_data shape       | full `__NEXT_DATA__.props.pageProps` plus `_meta` |
| data_hash strategy   | `stable_pageprops_payload_v1`                     |
| full HTML body       | not stored                                        |
| full JSON print/save | forbidden by default                              |
| transformed payload  | derived/helper, not canonical raw                 |
| full `__NEXT_DATA__` | not default                                       |
| existing v1 rows     | keep, no immediate rewrite                        |

The `stable_pageprops_payload_v1` hash should be based on canonical JSON for the
pageProps payload, excluding volatile fetch metadata. `_meta` can record request
metadata, response metadata, body hash, parser version, and storage policy, but
volatile metadata should not participate in the stable payload hash.

## 4. Why full pageProps is preferred

Full `pageProps` is the best next canonical raw shape because it is more
source-faithful than the current transformed payload while staying cleaner than
full `__NEXT_DATA__`.

It preserves:

- `content`, including lineup/playerStats/shotmap/stats/event-like trees
- `general`
- `header`
- page-level siblings such as `fallback`, `nav`, `seo`, `ssr`, and translations
- future unknown factors that may not be obvious before parser design

This matters because the project will expand beyond a small Ligue 1 sample.
Lower-tier and colder leagues can have uneven coverage, different pageProps
siblings, missing modules, or different match status shapes. Storing full
pageProps gives future audits and parsers a better source baseline.

## 5. Why not transformed-only

The current transformed-only v1 path is not ideal as the sole long-term raw
source:

- `transformToApiFormat` explicitly selects `matchId`, `content`, `general`,
  `header`, and `_meta`.
- pageProps siblings are dropped.
- SEO/breadcrumb and other page-level context are dropped.
- future unknown factors cannot be recovered from v1 if the original pageProps
  were not stored.
- parser/training would be constrained by an early transform decision that
  happened before the feature target was known.

Transformed payload can remain useful as a normalized helper, but it should be
derived from canonical pageProps v2 rather than treated as the only raw source.

## 6. Why not full **NEXT_DATA** by default

Full `__NEXT_DATA__` is not recommended as the default canonical raw shape at
this point because it includes a large Next.js wrapper:

- build/runtime identifiers
- route and query wrapper fields
- app/runtime flags
- script loader and framework metadata
- source wrapper keys that are useful for forensic evidence but noisy for raw
  match-detail warehousing

`pageProps` captures the source payload more cleanly: it keeps match/page data
while avoiding most framework wrapper noise. Full `__NEXT_DATA__` can remain a
future optional evidence archive if later audits prove pageProps is insufficient.

## 7. Versioning / coexistence policy

`fotmob_html_hyd_v1` remains valid historical transformed raw. It should not be
deleted or rewritten in Phase 5.21L2C.

Future policy:

- `fotmob_pageprops_v2` becomes the recommended canonical raw version for new
  FotMob html hydration collection.
- v1 and v2 can coexist in `raw_match_data` by `data_version`.
- parser/training must branch by `data_version`, source, and provenance.
- synthetic and unknown rows are excluded unless explicitly handled.
- no automatic rewrite is allowed now.
- any backfill, migration, or v2 write requires separate authorization and
  no-write preflight before execution.

## 8. League expansion / low-tier league policy

Raw completeness can vary substantially across leagues, seasons, and match
statuses. Low-tier or cold leagues may lack:

- `content.lineup`
- `content.playerStats`
- `content.shotmap`
- `content.stats`
- `content.momentum`
- `content.liveticker`
- `content.matchFacts`
- `content.h2h`
- `content.table`

Before parser/features/training, each league / season / status / data_version
group needs a raw completeness profile. The profile should record module
coverage, path counts, size distributions, suspicious small payloads, block/error
markers, and coverage tiers.

Matches with missing modules must not be mixed blindly with high-coverage
matches. Parser/features/training must branch or stratify by coverage tier.

## 9. Recommended next phases

Recommended next phase:

`Phase 5.21L2D: single-target pageProps v2 no-write preview`

Scope:

- single target `4830747`
- live request only after explicit authorization
- no DB write
- construct pageProps v2 candidate in memory
- compute `stable_pageprops_payload_v1` hash
- compare v2 vs existing v1 size, path coverage, and module coverage
- no full body or full JSON print/save

Then:

- `Phase 5.21L2E: pageProps v2 controlled write planning`
    - decide version/upsert/coexistence policy
    - no DB write
- `Phase 5.21L2F: controlled pageProps v2 small sample write`
    - only after explicit authorization
    - likely version coexistence rather than v1 rewrite
    - no parser/features/training

Do not enter parser/features/training until the raw storage policy and first v2
preview/write strategy are settled.

## 10. Explicit non-execution

Phase 5.21L2C performed:

- no external FotMob access
- no live match detail request
- no DB writes
- no `raw_match_data` writes
- no `matches` writes
- no parser/features work
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full `raw_data` print/save
- no file deletion
