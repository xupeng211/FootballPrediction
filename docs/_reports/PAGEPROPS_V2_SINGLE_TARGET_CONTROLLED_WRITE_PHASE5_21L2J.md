# PageProps V2 Single-Target Controlled Write - Phase 5.21L2J

## 1. Executive summary

Phase 5.21L2I completed the no-write preflight for target `4830747`
(`53_20252026_4830747`, Auxerre vs Nice). The preflight produced the
`stable_pageprops_payload_v1` baseline:

`f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc`

This phase adds the controlled write entrypoint for exactly one
`fotmob_pageprops_v2` `raw_match_data` row. The write remains single-target,
keeps the existing `fotmob_html_hyd_v1` row, uses `(match_id, data_version)`
versioned uniqueness, and keeps parser/features/training deferred.

The real write is deferred until after PR merge and main push CI success.

## 2. Pre-write baseline

Expected baseline before the post-merge controlled write:

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
- `raw_data_has_match_id`: present
- `raw_data_not_empty`: present

Target `4830747` versions before write:

| version               | status |
| --------------------- | ------ |
| `fotmob_html_hyd_v1`  | exists |
| `fotmob_pageprops_v2` | absent |

Baseline hash:

`f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc`

## 3. Live recapture / hash gate

The controlled write script recaptures:

`https://www.fotmob.com/match/4830747`

It parses `__NEXT_DATA__`, extracts `props.pageProps`, builds the v2 `raw_data`
in memory, computes `stable_pageprops_payload_v1` from canonical pageProps JSON,
and writes only if the recaptured hash exactly equals the Phase 5.21L2I
baseline hash.

The post-merge execution records:

- `request_url`
- `final_url`
- `http_status`
- `content_type`
- `body_byte_length`
- `body_sha256`
- `next_data_parse_ok`
- `page_props_found`
- `recaptured_pageprops_hash`
- `hash_matches_baseline`

No full HTML body or full pageProps JSON is printed or saved.

## 4. Insert result

If the hash gate passes, the script performs one transaction:

- `BEGIN`
- re-check target versions
- `INSERT INTO raw_match_data (...) ON CONFLICT (match_id, data_version) DO NOTHING`
- verify `inserted_count=1`
- verify row counts and target versions
- `COMMIT`

Expected insert result:

| field           | value                                                              |
| --------------- | ------------------------------------------------------------------ |
| inserted_count  | `1`                                                                |
| updated_count   | `0`                                                                |
| skipped_count   | `0`                                                                |
| conflict target | `(match_id,data_version)`                                          |
| match_id        | `53_20252026_4830747`                                              |
| external_id     | `4830747`                                                          |
| data_version    | `fotmob_pageprops_v2`                                              |
| data_hash       | `f892b403fe6e420a745888ab31e825843c4fd5387a7518ce61c4b456bb980acc` |
| collected_at    | generated at write time                                            |

v2 `raw_data` shape:

- `_meta`
- top-level `matchId`
- `pageProps`

## 5. Post-write verification

Expected post-write row counts:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   11 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Expected target versions after write:

- `fotmob_html_hyd_v1`
- `fotmob_pageprops_v2`

Post-write checks:

- v1 row retained and unchanged
- v2 hash equals baseline
- v2 `raw_data` has `_meta`
- v2 `raw_data` has top-level `matchId`
- v2 `raw_data` has `pageProps`
- no parser/features/training executed

## 6. Safety notes

This phase is intentionally narrow:

- no `matches` writes
- no schema migration
- no v1 rewrite
- no multi-target write
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full body/json save or print

## 7. Next phase recommendation

Recommended next phase:

`Phase 5.21L2K: pageProps v2 post-write canonical read verification`

Scope:

- no DB write
- no FotMob access
- use `RawMatchDataVersionSelector`
- confirm canonical selector picks `fotmob_pageprops_v2` for `4830747`
- confirm fallback picks `fotmob_html_hyd_v1` for the remaining seeded matches
- confirm synthetic/unknown versions are excluded
- no parser/features/training

Do not directly expand to bulk v2 acquisition before canonical read behavior is
verified.

## 8. Explicit non-execution

Before post-merge controlled execution, this implementation phase performs:

- no `raw_match_data` writes
- no `matches` writes
- no schema migration
- no v1 rewrite
- no multi-target write
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no full JSON save/print
- no file deletion
