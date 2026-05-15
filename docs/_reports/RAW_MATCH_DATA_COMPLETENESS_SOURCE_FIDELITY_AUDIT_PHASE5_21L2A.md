# Raw Match Data Completeness Source Fidelity Audit - Phase 5.21L2A

## 1. Executive summary

Phase 5.20L2F successfully moved `raw_match_data` from 3 rows to 10 rows.
Phase 5.21L2A does not enter training design. It performs a SELECT-only
completeness and source fidelity audit for the current raw payloads.

This audit confirms:

- `raw_match_data` has mixed provenance / heterogeneous schema.
- `fotmob_html_hyd_v1` rows are the FotMob source fidelity target.
- `PHASE4.43_SYNTHETIC` is a legacy/synthetic schema anomaly and is excluded
  from FotMob source fidelity conclusions.
- Current FotMob rows are transformed hydration payloads, not full
  `__NEXT_DATA__` documents.
- No network access and no DB writes were performed.

## 2. Current DB baseline

| table                   | rows |
| ----------------------- | ---: |
| matches                 |   10 |
| raw_match_data          |   10 |
| bookmaker_odds_history  |    2 |
| l3_features             |    2 |
| match_features_training |    2 |
| predictions             |    2 |

Protected tables remain unchanged.

## 3. Provenance inventory

| data_version        | provenance            | rows | has \_meta | has content | has general | has header | has matchId |
| ------------------- | --------------------- | ---: | ---------: | ----------: | ----------: | ---------: | ----------: |
| fotmob_html_hyd_v1  | fotmob_html_hydration |    8 |          8 |           8 |           8 |          8 |           8 |
| PHASE4.23           | unknown               |    1 |          1 |           1 |           1 |          1 |           1 |
| PHASE4.43_SYNTHETIC | legacy_synthetic      |    1 |          0 |           1 |           1 |          1 |           1 |

`PHASE4.43_SYNTHETIC / external_id=900002` lacks `_meta`. This is recorded as
`synthetic_missing__meta`. It does not invalidate the FotMob source fidelity
audit because it is a legacy/synthetic row, not a `fotmob_html_hyd_v1` row.

`PHASE4.23 / external_id=4837496` is classified as `unknown` provenance and
requires future governance before it is mixed into parser, feature, or training
workflows.

## 4. Raw inventory

| match_id             | external_id | data_version        | provenance            | top-level keys                              |  bytes | leaf paths | max depth | excluded from FotMob conclusion |
| -------------------- | ----------: | ------------------- | --------------------- | ------------------------------------------- | -----: | ---------: | --------: | ------------------------------- |
| 53_20252026_4830746  |     4830746 | fotmob_html_hyd_v1  | fotmob_html_hydration | \_meta, content, general, header, matchId   | 248702 |       4757 |        10 | no                              |
| 53_20252026_4830747  |     4830747 | fotmob_html_hyd_v1  | fotmob_html_hydration | \_meta, content, general, header, matchId   | 234856 |       4824 |        10 | no                              |
| 53_20252026_4830748  |     4830748 | fotmob_html_hyd_v1  | fotmob_html_hydration | \_meta, content, general, header, matchId   | 215448 |       4567 |        10 | no                              |
| 53_20252026_4830750  |     4830750 | fotmob_html_hyd_v1  | fotmob_html_hydration | \_meta, content, general, header, matchId   | 246336 |       4991 |        10 | no                              |
| 53_20252026_4830751  |     4830751 | fotmob_html_hyd_v1  | fotmob_html_hydration | \_meta, content, general, header, matchId   | 223887 |       4742 |        10 | no                              |
| 53_20252026_4830752  |     4830752 | fotmob_html_hyd_v1  | fotmob_html_hydration | \_meta, content, general, header, matchId   | 258396 |       4652 |        10 | no                              |
| 53_20252026_4830753  |     4830753 | fotmob_html_hyd_v1  | fotmob_html_hydration | \_meta, content, general, header, matchId   | 238984 |       4940 |        10 | no                              |
| 53_20252026_4830754  |     4830754 | fotmob_html_hyd_v1  | fotmob_html_hydration | \_meta, content, general, header, matchId   | 277014 |       4997 |        10 | no                              |
| 140_20252026_4837496 |     4837496 | PHASE4.23           | unknown               | \_meta, content, general, header, matchId   |   2505 |         64 |         7 | yes                             |
| 47_20242025_900002   |      900002 | PHASE4.43_SYNTHETIC | legacy_synthetic      | content, general, header, matchId, metadata |   1220 |         38 |         5 | yes                             |

Full `raw_data` was not printed or saved.

## 5. Seeded 8 match coverage

All 8 seeded Ligue 1 matches have `raw_data`, all are
`data_version=fotmob_html_hyd_v1`, and all have `_meta`, `content`, `general`,
`header`, and `matchId`.

| external_id | match                        | raw_data | data_version       | core modules |
| ----------: | ---------------------------- | -------- | ------------------ | ------------ |
|     4830746 | Angers vs Strasbourg         | yes      | fotmob_html_hyd_v1 | core present |
|     4830747 | Auxerre vs Nice              | yes      | fotmob_html_hyd_v1 | core present |
|     4830748 | Le Havre vs Marseille        | yes      | fotmob_html_hyd_v1 | core present |
|     4830750 | Metz vs Lorient              | yes      | fotmob_html_hyd_v1 | core present |
|     4830751 | Monaco vs Lille              | yes      | fotmob_html_hyd_v1 | core present |
|     4830752 | Paris Saint-Germain vs Brest | yes      | fotmob_html_hyd_v1 | core present |
|     4830753 | Rennes vs Paris FC           | yes      | fotmob_html_hyd_v1 | core present |
|     4830754 | Toulouse vs Lyon             | yes      | fotmob_html_hyd_v1 | core present |

## 6. Shape statistics for FotMob rows

Only `fotmob_html_hyd_v1` rows are included in this section.

| metric           |    min |    max | median |
| ---------------- | -----: | -----: | -----: |
| JSON byte length | 215448 | 277014 | 242660 |
| leaf_path_count  |   4567 |   4997 | 4790.5 |
| max_depth        |     10 |     10 |     10 |

Path coverage across the 8 FotMob rows:

- common_paths_count: 1016
- partial_paths_count: 48775
- completeness_outliers: none
- suspicious_small_payloads: none

Per-row shape details:

| external_id | object_count | array_count | scalar_count | distinct_path_count |
| ----------: | -----------: | ----------: | -----------: | ------------------: |
|     4830746 |         3380 |         358 |        10893 |                7088 |
|     4830747 |         3321 |         356 |        10333 |                7178 |
|     4830748 |         3163 |         349 |         9463 |                6827 |
|     4830750 |         3399 |         364 |        10766 |                7370 |
|     4830751 |         3409 |         353 |         9777 |                7107 |
|     4830752 |         3332 |         342 |        10862 |                6919 |
|     4830753 |         3302 |         357 |        10492 |                7331 |
|     4830754 |         3567 |         362 |        12186 |                7387 |

## 7. Module coverage matrix for FotMob rows

| module              | present / 8 | missing external_ids                                                   |
| ------------------- | ----------: | ---------------------------------------------------------------------- |
| \_meta              |           8 | none                                                                   |
| content             |           8 | none                                                                   |
| general             |           8 | none                                                                   |
| header              |           8 | none                                                                   |
| matchId             |           8 | none                                                                   |
| content.matchFacts  |           8 | none                                                                   |
| content.lineup      |           8 | none                                                                   |
| content.liveticker  |           8 | none                                                                   |
| content.playerStats |           8 | none                                                                   |
| content.shotmap     |           8 | none                                                                   |
| content.stats       |           8 | none                                                                   |
| content.h2h         |           8 | none                                                                   |
| content.table       |           8 | none                                                                   |
| content.momentum    |           8 | none                                                                   |
| content.teamForm    |           0 | 4830746, 4830747, 4830748, 4830750, 4830751, 4830752, 4830753, 4830754 |
| content.topPlayers  |           0 | 4830746, 4830747, 4830748, 4830750, 4830751, 4830752, 4830753, 4830754 |
| content.insights    |           0 | 4830746, 4830747, 4830748, 4830750, 4830751, 4830752, 4830753, 4830754 |
| content.highlights  |           0 | 4830746, 4830747, 4830748, 4830750, 4830751, 4830752, 4830753, 4830754 |

Missing modules are not interpreted as source loss by themselves because this
audit has no live source comparison. They are evidence for Phase 5.21L2B.

## 8. Block / error markers

The local audit found:

- error key: no
- captcha marker: no
- block marker: no
- placeholder-only shape: no
- suspicious small FotMob payload: no

The marker detector intentionally avoids treating normal football terms such as
blocked shots as server-side block signals.

## 9. Source fidelity assessment

Current `fotmob_html_hyd_v1` `raw_data` is more likely a transformed hydration
payload than a full original hydration JSON document.

Evidence:

- `src/parsers/fotmob/NextDataParser.js` extracts `__NEXT_DATA__`, then
  `transformToApiFormat` returns only `matchId`, `content`, `general`, `header`,
  and parser `_meta`.
- `src/infrastructure/services/FotMobRawDetailFetcher.js` builds the stable raw
  payload from transformed `content`, `general`, `header`, and normalized
  `matchId`.
- Stored FotMob rows have top-level keys:
  `_meta`, `content`, `general`, `header`, `matchId`.
- Stored FotMob rows do not have `props`, `pageProps`, full `__NEXT_DATA__`
  wrapper fields, SEO fields, breadcrumb fields, or the complete source
  container.

The deep `content` subtree is substantial and appears useful for future parsing,
but this audit cannot prove it is the full `pageProps.content` tree without a
live source comparison. `transformToApiFormat` may drop `pageProps` siblings or
other source-level fields because it explicitly constructs a narrower output.

Conclusion:

- table_has_mixed_provenance: true
- fotmob_rows_current_raw_data_is_full_next_data: false
- fotmob_rows_current_raw_data_is_transformed_payload: true
- transform_may_drop_fields: true
- full_hydration_source_not_stored: true
- legacy_synthetic_rows_excluded_from_fotmob_conclusion: true
- requires_live_source_compare: true
- recommended_storage_strategy_review: true

Current FotMob `raw_data` is not yet proven sufficient as the long-term raw data
warehouse. Parser/features/training must remain deferred.

Mixed provenance also means future parser/training pipelines must group by
`data_version` / source. Synthetic and unknown rows must not be mixed with
FotMob hydration rows without an explicit compatibility policy.

## 10. Recommendation

Recommended next phase:

`Phase 5.21L2B: HTML hydration source fidelity live compare`

Requirements:

- single target, preferably `4830747` or `4830746`
- no DB write
- no `raw_match_data` write
- no full body save or print
- compare live `__NEXT_DATA__.props.pageProps` path coverage with stored FotMob
  `raw_data`
- decide whether raw storage should keep a fuller hydration JSON structure

Do not enter parser/features/training until raw storage completeness is
confirmed.

## 11. Explicit non-execution

This phase performed:

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
