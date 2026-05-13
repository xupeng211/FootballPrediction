# L2 Controlled Raw Detail Live Preview - Phase 5.12L2C

## 1. Executive summary

Phase 5.12L2C authorizes one controlled live raw detail preview for
FotMob target `53_20252026_4830746` / external id `4830746`.

The preview must use the audited Phase 5.12L2B route selector with
`route=auto`, which attempts `html_hydration` before the direct
`api_match_details` route. This phase does not authorize DB writes,
`raw_match_data` writes, full body save/print, browser runtime, proxy
runtime, harvest, ingest, training, or prediction.

The live preview is intentionally deferred until after this authorization
report is merged and the `main` push CI is green.

## 2. Baseline

Pre-preview baseline confirmed before this report:

| Table                     | Rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Target seed confirmed:

| Field         | Value                    |
| ------------- | ------------------------ |
| `match_id`    | `53_20252026_4830746`    |
| `external_id` | `4830746`                |
| `home_team`   | `Angers`                 |
| `away_team`   | `Strasbourg`             |
| `match_date`  | `2026-05-10 19:00:00+00` |
| `status`      | `finished`               |

No existing `raw_match_data` row was found for `53_20252026_4830746` /
`4830746`.

## 3. Route selector readiness

The Phase 5.12L2B route selector is ready for a single authorized live
preview:

- `route=auto` is supported.
- `auto` route order is `html_hydration`, then `api_match_details`.
- `alternate_route` remains plan-only and is not executed by default.
- Live execution requires both `NETWORK_AUTHORIZATION=yes` and
  `LIVE_PREVIEW_AUTHORIZATION=yes`.
- The target must remain locked to `SOURCE=fotmob`,
  `MATCH_ID=53_20252026_4830746`, `EXTERNAL_ID=4830746`,
  `HOME_TEAM=Angers`, and `AWAY_TEAM=Strasbourg`.
- `ALLOW_DB_WRITE` must be `no`.
- `ALLOW_RAW_MATCH_DATA_WRITE` must be `no`.
- `ALLOW_BROWSER_RUNTIME` must be `no`.
- `ALLOW_PROXY_RUNTIME` must be `no`.
- `CONCURRENCY` must be `1`.
- `RETRY` must be `0`.
- `PRINT_BODY` must be `no`.
- `SAVE_BODY` must be `no`.

## 4. Local validation

Validation commands for the pre-preview authorization change:

- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/l2_raw_detail_preview.test.js`
- `docker compose -f docker-compose.dev.yml exec -T dev npm test`
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage`
- `git diff --check`
- `docker compose -f docker-compose.dev.yml exec -T dev npx eslint scripts/ops/l2_raw_detail_preview.js src/infrastructure/services/FotMobDetailRouteSelector.js tests/unit/l2_raw_detail_preview.test.js --no-cache`
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile scripts/ops/l2_raw_detail_preview.js src/infrastructure/services/FotMobDetailRouteSelector.js tests/unit/l2_raw_detail_preview.test.js docs/_reports/L2_CONTROLLED_RAW_DETAIL_LIVE_PREVIEW_PHASE5_12L2C.md`

Validation results before commit:

| Check                                                  | Result              |
| ------------------------------------------------------ | ------------------- |
| `node --test tests/unit/l2_raw_detail_preview.test.js` | Passed, 64/64 tests |
| `npm test`                                             | Passed              |
| `npm run test:coverage`                                | Passed              |
| `git diff --check`                                     | Passed              |
| `eslint` on preview script, selector, and unit test    | Passed              |
| `prettier --check` on touched/report files             | Passed              |

## 5. Actual live preview result

The actual live preview must run only after:

- this report is merged;
- `main` push CI is green;
- the local branch is `main`;
- the local worktree is clean;
- DB row counts remain unchanged;
- the target seed still exists; and
- the user authorization remains valid.

Planned command:

```bash
make data-l2-raw-detail-preview \
  SOURCE=fotmob \
  MATCH_ID=53_20252026_4830746 \
  EXTERNAL_ID=4830746 \
  HOME_TEAM=Angers \
  AWAY_TEAM=Strasbourg \
  ROUTE=auto \
  NETWORK_AUTHORIZATION=yes \
  LIVE_PREVIEW_AUTHORIZATION=yes \
  ALLOW_DB_WRITE=no \
  ALLOW_RAW_MATCH_DATA_WRITE=no \
  ALLOW_BROWSER_RUNTIME=no \
  ALLOW_PROXY_RUNTIME=no \
  CONCURRENCY=1 \
  RETRY=0 \
  PRINT_BODY=no \
  SAVE_BODY=no
```

Post-merge live preview summary fields to capture in the final operator
report:

| Field                           | Result                          |
| ------------------------------- | ------------------------------- |
| `selected_route`                | Pending post-merge live preview |
| `attempted_routes`              | Pending post-merge live preview |
| `request_url`                   | Pending post-merge live preview |
| `final_url`                     | Pending post-merge live preview |
| `http_status`                   | Pending post-merge live preview |
| `content_type`                  | Pending post-merge live preview |
| `body_byte_length`              | Pending post-merge live preview |
| `body_sha256`                   | Pending post-merge live preview |
| `hydration_parse_ok`            | Pending post-merge live preview |
| `json_parse_ok`                 | Pending post-merge live preview |
| `top_level_keys`                | Pending post-merge live preview |
| `candidate_raw_data_paths`      | Pending post-merge live preview |
| `contains_4830746`              | Pending post-merge live preview |
| `contains_Angers`               | Pending post-merge live preview |
| `contains_Strasbourg`           | Pending post-merge live preview |
| `looks_like_valid_match_detail` | Pending post-merge live preview |
| `body_printed`                  | Must remain `false`             |
| `body_saved`                    | Must remain `false`             |
| `browser_used`                  | Must remain `false`             |
| `proxy_used`                    | Must remain `false`             |
| DB row counts                   | Must remain unchanged           |

If the live preview returns 403, 429, another block signal, or invalid
hydration, execution must stop without retry, browser/proxy fallback,
header bypass, alternate route probing, DB write, or body save/print.

## 6. Next phase

If the live preview returns a valid match detail payload, the recommended
next phase is `Phase 5.13L2: raw_match_data ingest planning`.

That planning phase must define:

- exact `raw_data` shape;
- `data_hash` calculation;
- `data_version` value;
- `collected_at` policy;
- upsert or insert policy;
- protected table boundaries; and
- a no-write validation path before any DB authorization.

If the live preview fails, stop and decide whether the next phase should
adjust the route selector, request explicit browser authorization, or stop
the FotMob detail route.

## 7. Explicit non-execution

This pre-preview authorization phase does not execute:

- DB writes;
- `raw_match_data` writes;
- `matches` writes;
- `bookmaker_odds_history` writes;
- `l3_features` writes;
- `match_features_training` writes;
- `predictions` writes;
- harvest / ingest;
- batch backfill;
- bulk harvest;
- training / prediction;
- browser / proxy runtime;
- full body save;
- full body print;
- file deletion; or
- model artifact loading.
