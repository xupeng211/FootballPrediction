# Remaining Seeded PageProps V2 Controlled Write - Phase 5.21L2M

## 1. Executive summary

Phase 5.21L2L completed the no-write preflight for the remaining seven seeded
matches. It recaptured each target sequentially, computed
`stable_pageprops_payload_v1` hashes, and reported `would_insert_count=7` with no
DB write.

This phase adds the controlled write entrypoint for those seven
`fotmob_pageprops_v2` rows. The script recaptures each target again, requires
each recaptured pageProps hash to match the Phase 5.21L2L baseline, and then
inserts exactly seven `raw_match_data` rows in one transaction.

Parser/features/training/prediction remain deferred.

## 2. Pre-write baseline

Expected baseline before the post-merge controlled write:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   11 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Schema:

- `raw_match_data_match_id_key`: absent
- `raw_match_data_match_id_data_version_key`: present
- unique constraint: `UNIQUE(match_id, data_version)`
- `raw_data_has_match_id`: present
- `raw_data_not_empty`: present

`4830747` already has `fotmob_html_hyd_v1` and `fotmob_pageprops_v2`; it is
excluded from this write and must not be rewritten.

Remaining targets must have `fotmob_html_hyd_v1` and no
`fotmob_pageprops_v2` before write:

| match_id              | external_id | baseline hash                                                      |
| --------------------- | ----------- | ------------------------------------------------------------------ |
| `53_20252026_4830746` | `4830746`   | `7953562593a2ab57ed59741667ccf2fa628adf22eff76fdc7a499f559b3ac440` |
| `53_20252026_4830748` | `4830748`   | `fe664ebe76d4e0e9fda088d4d642fe98fe25c03b920f4f3d83531e6ea4c4ad04` |
| `53_20252026_4830750` | `4830750`   | `e5cada280a0b8d351181defd5605ded7ced091e86be3039439559aed1247b762` |
| `53_20252026_4830751` | `4830751`   | `de78dc67d69ffc22739e4cf648788fd6f50a6dfccae8518a9c1fa8def0eb16a5` |
| `53_20252026_4830752` | `4830752`   | `65564219fcb25c6369822a0082f43e96f59675f434208d45cb16ef6395f08c32` |
| `53_20252026_4830753` | `4830753`   | `4ab9fcb73465d00cc8bab7a6cb1a61b1b3370d466b15c2ace0092c8357ead413` |
| `53_20252026_4830754` | `4830754`   | `29be450e84a55fb56a8db4f1bf7a672adcd6c85e34a8cf06c98e99ac179532c6` |

## 3. Live recapture / hash gate

The post-merge controlled write must run only after PR CI and main push CI are
green. It must use `make data-remaining-seeded-pageprops-v2-controlled-write`
with final DB-write confirmation and the Phase 5.21L2L baseline hash JSON.

Post-merge execution records per target:

- `request_url`
- `final_url`
- `http_status`
- `content_type`
- `body_byte_length`
- `body_sha256`
- `recaptured_hash`
- `baseline_hash`
- `hash_matches_baseline`

No full HTML body or full pageProps JSON is printed or saved.

## 4. Insert result

If all seven hash gates pass, the script performs one transaction:

- `BEGIN`
- re-check all seven target versions and v2 absence
- `INSERT INTO raw_match_data (...) ON CONFLICT (match_id, data_version) DO NOTHING`
- require `inserted_count=7`
- verify `raw_match_data 11 -> 18`
- verify protected tables unchanged
- verify `4830747` unchanged
- `COMMIT`

Expected insert result:

| field            | value                     |
| ---------------- | ------------------------- |
| `inserted_count` | `7`                       |
| `updated_count`  | `0`                       |
| `skipped_count`  | `0`                       |
| conflict target  | `(match_id,data_version)` |

v2 `raw_data` shape:

- `_meta`
- top-level `matchId`
- `pageProps`

Post-merge execution will record inserted row metadata:

- `match_id`
- `external_id`
- `data_version=fotmob_pageprops_v2`
- `data_hash`
- `collected_at`

## 5. Post-write verification

Expected post-write row counts:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   18 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Required post-write checks:

- all eight seeded matches now have `fotmob_html_hyd_v1` and `fotmob_pageprops_v2`
- `4830747` retained and unchanged
- remaining seven v2 `data_hash` values equal baselines
- each remaining seven v2 `raw_data` has `_meta`
- each remaining seven v2 `raw_data` has top-level `matchId`
- each remaining seven v2 `raw_data` has `pageProps`
- duplicate `(match_id,data_version)` count is zero

## 6. Safety notes

This phase is intentionally narrow:

- no `matches` writes
- no schema migration
- no v1 rewrite
- no update of existing v2 rows
- no partial write
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no retry
- no full body/json save or print

## 7. Next phase recommendation

Recommended next phase:

`Phase 5.21L2N: post-write canonical read verification for all 8 seeded matches`

Scope:

- no DB write
- no FotMob access
- use `RawMatchDataVersionSelector`
- confirm all eight seeded matches canonical select `fotmob_pageprops_v2`
- confirm synthetic/unknown versions are excluded
- no parser/features/training

Do not proceed directly to parser/features/training.

## 8. Explicit non-execution

Before post-merge controlled execution, this implementation phase performs:

- no `raw_match_data` writes
- no `matches` writes
- no schema migration
- no v1 rewrite
- no partial write
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no retry
- no full body save/print
- no full JSON save/print
- no file deletion
