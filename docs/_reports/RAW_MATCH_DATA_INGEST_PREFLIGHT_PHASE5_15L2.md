# Raw Match Data Ingest Preflight - Phase 5.15L2

## 1. Executive summary

Phase 5.15L2 defines the `raw_match_data` ingest preflight boundary for target
`53_20252026_4830746` / external id `4830746`.

This phase is designed to recapture the exact FotMob raw payload through the
safe route selector, canonicalize the raw payload, compute `data_hash`, SELECT
the existing `raw_match_data` row, and preview `would_insert` /
`would_update` / `would_skip`.

It does not write DB and does not write `raw_match_data`.

## 2. Baseline

Current baseline confirmed before preflight execution:

| Table                     | Rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Target match exists:

| Field         | Value                    |
| ------------- | ------------------------ |
| `match_id`    | `53_20252026_4830746`    |
| `external_id` | `4830746`                |
| `home_team`   | `Angers`                 |
| `away_team`   | `Strasbourg`             |
| `match_date`  | `2026-05-10 19:00:00+00` |
| `status`      | `finished`               |

Target `raw_match_data` status before preflight:

- no existing row for `match_id=53_20252026_4830746`
- no existing row for `external_id=4830746`

## 3. Preflight input

Fixed preflight scope:

- `source=fotmob`
- `route=html_hydration` or `auto` with `html_hydration` first
- `match_id=53_20252026_4830746`
- `external_id=4830746`
- `home_team=Angers`
- `away_team=Strasbourg`
- `data_version=fotmob_html_hyd_v1`
- `network_authorization=yes`
- `live_preview_authorization=yes`
- `allow_db_write=no`
- `allow_raw_match_data_write=no`
- `allow_matches_write=no`
- `allow_training=no`
- `allow_prediction=no`
- `concurrency=1`
- `retry=0`
- `print_body=no`
- `save_body=no`

## 4. Exact payload recapture

This section is reserved for the actual post-merge controlled preflight result.

Expected capture fields:

- `selected_route`
- `request_url`
- `final_url`
- `http_status`
- `content_type`
- `body_byte_length`
- `body_sha256`
- `hydration_parse_ok`
- `looks_like_valid_match_detail`

## 5. Canonical raw_data / data_hash

Expected canonical shape:

- top-level `_meta`
- top-level `content`
- top-level `general`
- top-level `header`
- top-level `matchId`

Policy:

- do not store the full HTML body
- do not store the HTTP response string
- `data_hash = SHA-256(canonical_json(raw_data))`
- `body_sha256` remains metadata only

Actual computed `raw_data_hash` will be recorded after the controlled preflight
run.

## 6. Affected row preview

Expected preview fields:

- `existing_raw_match_data_found`
- `would_insert`
- `would_update`
- `would_skip`
- `affected_preview.match_id`
- `affected_preview.external_id`
- `affected_preview.decision`

Current expectation is `would_insert=1`, because no `raw_match_data` row exists
for the target match.

## 7. Protected table baseline

Protected tables remain at baseline:

| Table                     | Rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

## 8. Next phase

Recommended next phase:

`Phase 5.16L2: controlled raw_match_data write`

Requirements:

- final DB-write confirmation from the user
- use exact preflight payload/hash or recapture and compare
- write only `raw_match_data`
- no `matches` / features / predictions writes
- transaction required
- post-write verification required

## 9. Explicit non-execution

This phase does not execute:

- DB writes
- `raw_match_data` writes
- `matches` writes
- `bookmaker_odds_history` writes
- `l3_features` writes
- `match_features_training` writes
- `predictions` writes
- harvest / ingest / backfill
- training / prediction
- full body save
- full body print
- file deletion
