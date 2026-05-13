# Raw Match Data Ingest Authorization - Phase 5.14L2

## 1. Executive summary

The user authorized entry into the `raw_match_data` ingest flow for target
`53_20252026_4830746` / external id `4830746`.

Phase 5.14L2 is authorization-only. It records the allowed future ingest scope
for one `raw_match_data` row, but it does not write DB, does not write
`raw_match_data`, does not run a live preview, and does not execute harvest,
ingest, training, or prediction.

Future write remains blocked until Phase 5.15L2 preflight and a later controlled
execution phase with final DB-write confirmation.

## 2. Baseline

Pre-authorization baseline:

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

Target `raw_match_data` existing status:

- no existing row for `match_id=53_20252026_4830746`
- no existing row for `external_id=4830746`

## 3. Authorized scope

Authorized future scope:

- `source=fotmob`
- `route=html_hydration`
- target table: `raw_match_data`
- `match_id=53_20252026_4830746`
- `external_id=4830746`
- `home_team=Angers`
- `away_team=Strasbourg`
- `rows_limit=1`
- `data_version=fotmob_html_hyd_v1`
- raw data policy: canonical transformed detail payload
- data hash policy: `SHA-256(canonical_json(raw_data))`

Protected tables:

- `matches`
- `bookmaker_odds_history`
- `l3_features`
- `match_features_training`
- `predictions`

No matches, features, training, or prediction writes are authorized by this
phase.

## 4. Authorization boundary

Authorization does not equal DB write.

Boundary:

- `raw_match_data_write_allowed_this_phase=false`
- `raw_match_data_write_allowed_next_phase=true`
- `db_write_allowed_this_phase=false`
- future preflight required
- future final DB-write confirmation required
- no live preview or network request is allowed in this authorization phase

The authorization-only script must only output an authorization JSON summary.
It must not access FotMob, load browser/proxy runtime, save body content, print
body content, write files, write DB, or run any legacy harvest/backfill/ingest
entrypoint.

## 5. Next phase requirements

Phase 5.15L2 must:

- reload or recapture the exact raw payload under explicit preview/write flow
- compute canonical `raw_data`
- compute `data_hash`
- SELECT existing `raw_match_data`
- output `would_insert` / `would_update` / `would_skip`
- verify protected table baselines
- not write DB yet

The later execution phase must require final DB-write confirmation and a
transaction touching only `raw_match_data`.

## 6. Validation

Local validation results:

| Check                                                                   | Result             |
| ----------------------------------------------------------------------- | ------------------ |
| `node --test tests/unit/l2_raw_match_data_ingest_authorization.test.js` | Passed, 48/48      |
| `make data-l2-raw-match-data-ingest-authorization ...`                  | Passed             |
| `npm test`                                                              | Passed             |
| `npm run test:coverage`                                                 | Passed             |
| `git diff --check`                                                      | Passed             |
| `eslint` on authorization script and unit test                          | Passed             |
| `prettier --check` on touched files                                     | Passed             |
| DB row-count safety check                                               | Passed, unchanged  |
| `tests/fixtures/l1-config-*` residue check                              | Passed, no residue |
| `docs/_staging_preview` residue check                                   | Passed, absent     |

Post-validation DB row counts remained unchanged:

| Table                     | Rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

## 7. Explicit non-execution

This phase does not execute:

- external FotMob access
- live match detail request
- network dry-run
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
- training / prediction
- full body save
- full body print
- file deletion
