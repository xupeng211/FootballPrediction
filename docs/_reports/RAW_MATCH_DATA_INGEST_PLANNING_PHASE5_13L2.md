# Raw Match Data Ingest Planning - Phase 5.13L2

## 1. Executive summary

Phase 5.12L2C successfully obtained a valid FotMob match detail payload through
the audited `html_hydration` route selector for target
`53_20252026_4830746` / external id `4830746`.

Phase 5.13L2 plans the future `raw_match_data` ingest boundary. This phase does
not access FotMob, does not run another live match detail request, does not write
DB, does not write `raw_match_data`, does not save a full body, and does not run
parser, feature, training, or prediction pipelines.

The goal is to define the storage shape, hash, version, collected timestamp,
upsert, protected-table, authorization, and preflight policies before any future
write phase.

## 2. Baseline

Pre-planning baseline:

| Table                     | Rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Target match:

| Field         | Value                    |
| ------------- | ------------------------ |
| `match_id`    | `53_20252026_4830746`    |
| `external_id` | `4830746`                |
| `home_team`   | `Angers`                 |
| `away_team`   | `Strasbourg`             |
| `match_date`  | `2026-05-10 19:00:00+00` |
| `status`      | `finished`               |

Target `raw_match_data` status:

- no existing row for `match_id=53_20252026_4830746`
- no existing row for `external_id=4830746`

`raw_match_data` schema summary:

- `match_id varchar(50) NOT NULL`
- `external_id varchar(100)`
- `raw_data jsonb NOT NULL`
- `collected_at timestamptz`, default `CURRENT_TIMESTAMP`
- `data_version varchar(20)`, default `V26.1`
- `data_hash varchar(64)`
- unique constraint: `raw_match_data_match_id_key`
- FK: `match_id -> matches(match_id) ON DELETE CASCADE`
- check: `raw_data` must contain `matchId`, `general`, or `header`

## 3. Preview result used as input

Phase 5.12L2C controlled preview:

| Field                           | Value                                                              |
| ------------------------------- | ------------------------------------------------------------------ |
| `selected_route`                | `html_hydration`                                                   |
| `request_url`                   | `https://www.fotmob.com/match/4830746`                             |
| `final_url`                     | `https://www.fotmob.com/matches/angers-vs-strasbourg/2o4och`       |
| `http_status`                   | `200`                                                              |
| `content_type`                  | `text/html; charset=utf-8`                                         |
| `body_byte_length`              | `1037598`                                                          |
| `body_sha256`                   | `8710a3524807d4682ab3c66386f9cd6b4d374fb6eee4f98a29d7f4a6683a162c` |
| `hydration_parse_ok`            | `true`                                                             |
| `json_parse_ok`                 | `false`                                                            |
| `looks_like_valid_match_detail` | `true`                                                             |
| `body_printed`                  | `false`                                                            |
| `body_saved`                    | `false`                                                            |
| `browser_used`                  | `false`                                                            |
| `proxy_used`                    | `false`                                                            |

Top-level transformed payload keys:

- `_meta`
- `content`
- `general`
- `header`
- `matchId`

Candidate raw data paths:

- `__NEXT_DATA__.props.pageProps.content`
- `content.lineup`
- `content.matchFacts`
- `content.liveticker.teams`
- `content.playerStats.*.shotmap`
- `content.playerStats.*.stats`

## 4. raw_data storage policy

Future ingest should store the canonical transformed detail payload produced by
the audited route selector, not the full page HTML.

Recommended `raw_data` shape:

- source object: `FotMobDetailRouteSelector` `html_hydration`
  `transformed_api_format`
- top-level keys: `_meta`, `content`, `general`, `header`, `matchId`
- `raw_data._meta` should include source, route, request URL, final URL, fetch
  body SHA-256, fetch body byte length, hydration parse status, parser name, and
  collection timestamp metadata
- parser-needed paths should be preserved:
    - `content.matchFacts`
    - `content.lineup`
    - `content.liveticker.teams`
    - `content.playerStats.*.shotmap`
    - `content.playerStats.*.stats`
    - `general`
    - `header`
    - `matchId`

Explicit exclusions:

- do not store the complete HTML body
- do not store the complete HTTP response string
- do not store screenshots
- do not store local file paths as the raw payload
- do not treat the page body hash as the DB `data_hash`

## 5. data_hash policy

`data_hash` should be:

```text
SHA-256(canonical_json(raw_data))
```

Policy:

- canonical JSON must use stable key ordering
- hash input is the exact `raw_data` object that will be written
- the Phase 5.12L2C HTML body SHA-256 is fetch metadata only
- body SHA-256 can be stored at `raw_data._meta.fetch_body_sha256`
- future write phase must recompute `data_hash` from exact `raw_data` before DB
  write
- do not use legacy `md5($3::text)` for this controlled path

## 6. data_version / collected_at policy

Recommended semantic label:

- `fotmob_html_hydration_v1`

Current DB column is `raw_match_data.data_version varchar(20)`, so the planned
DB-safe value is:

- `fotmob_html_hyd_v1`

`collected_at` policy:

- generated by the future controlled write script
- UTC timestamp
- should represent the actual raw payload capture/write time
- preview time can be recorded separately as `raw_data._meta.preview_at`

## 7. Upsert policy

Conflict key:

- `match_id`

Rules:

- if no row exists: `would_insert`
- if a row exists and `data_hash` is identical: `would_skip`
- if a row exists and `data_hash` differs: `would_update` only after explicit
  user authorization
- no delete
- no truncate
- no overwrite without preflight
- first write must be limited to rows `<= 1`
- later controlled batch writes must be limited to rows `<= 8`
- transaction required

## 8. Protected tables

Future raw ingest authorization may only allow `raw_match_data`.

Protected table policy:

- `matches`: read-only
- `bookmaker_odds_history`: unchanged
- `l3_features`: unchanged
- `match_features_training`: unchanged
- `predictions`: unchanged

No parser, feature, training, prediction, harvest, backfill, or recon pipeline
may be triggered by raw ingest.

## 9. Recommended next phase

Recommended next phase:

`Phase 5.14L2: raw_match_data ingest authorization`

Requirements:

- user authorizes only `raw_match_data` write
- target only `53_20252026_4830746` / `external_id=4830746`
- no `matches` write
- no `bookmaker_odds_history` write
- no `l3_features` write
- no `match_features_training` write
- no `predictions` write
- no training
- no prediction
- no DB write until a later preflight/execution phase defines the exact row and
  transaction plan

## 10. Explicit non-execution

This phase does not execute:

- external FotMob access
- live match detail request
- retry
- browser/proxy runtime
- DB writes
- `raw_match_data` writes
- `matches` writes
- `bookmaker_odds_history` writes
- `l3_features` writes
- `match_features_training` writes
- `predictions` writes
- harvest / ingest
- batch backfill
- bulk harvest
- parser / feature pipeline
- training / prediction
- full body save
- full body print
- file deletion
