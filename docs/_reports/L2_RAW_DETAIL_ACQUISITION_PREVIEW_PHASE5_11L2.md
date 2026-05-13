# L2 Raw Detail Acquisition Preview - Phase 5.11L2

## 1. Executive summary

Phase 5.11L2 adds a controlled raw detail acquisition preview for one already seeded FotMob match:

- `match_id=53_20252026_4830746`
- `external_id=4830746`
- Angers vs Strasbourg

This phase is preview-only. It can perform one explicitly authorized external FotMob match detail request after merge and green main CI, then prints only response metadata, hash, markers, and structural signals to stdout.

It does not write `raw_match_data`, does not write any DB table, does not save or print the full body, does not use browser/proxy runtime, and does not run parser, feature, training, or prediction pipelines.

## 2. Background

Phase 5.09L1 seeded 8 Ligue 1 matches for 2026-05-10 into `matches`. Phase 5.10L2 confirmed that `raw_match_data` has an FK to `matches(match_id)` and that the next safe step should be a single-target raw detail preview before any ingest planning or DB write.

The current preview target exists in `matches`:

| match_id              | external_id | fixture              | status   |
| --------------------- | ----------- | -------------------- | -------- |
| `53_20252026_4830746` | `4830746`   | Angers vs Strasbourg | finished |

`raw_match_data` had no existing row for this target before implementation.

## 3. Implemented files

| file                                                             | purpose                                         |
| ---------------------------------------------------------------- | ----------------------------------------------- |
| `scripts/ops/l2_raw_detail_preview.js`                           | Phase 5.11L2 safe preview wrapper               |
| `tests/unit/l2_raw_detail_preview.test.js`                       | Unit tests with fake fetch and execution guards |
| `Makefile`                                                       | Adds `data-l2-raw-detail-preview` and help text |
| `AGENTS.md`                                                      | Adds Phase 5.11L2 agent safety rules            |
| `docs/_reports/L2_RAW_DETAIL_ACQUISITION_PREVIEW_PHASE5_11L2.md` | This report                                     |

## 4. Safety boundary

The wrapper enforces:

- exact source: `fotmob`
- exact match: `53_20252026_4830746`
- exact external id: `4830746`
- `NETWORK_AUTHORIZATION=yes`
- `ALLOW_DB_WRITE=no`
- `ALLOW_RAW_MATCH_DATA_WRITE=no`
- `ALLOW_BROWSER_RUNTIME=no`
- `ALLOW_PROXY_RUNTIME=no`
- `CONCURRENCY=1`
- `RETRY=0`
- `PRINT_BODY=no`
- `SAVE_BODY=no`
- `bulk=yes` blocked

The wrapper does not import `ProductionHarvester`, `FotMobStrategy`, raw ingest scripts, `pg`, Playwright, proxy runtime, or child process modules. It does not call file write APIs.

## 5. Local validation

Local validation completed for this phase:

- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/l2_raw_detail_preview.test.js` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm test` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage` passed
- `git diff --check` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npx eslint scripts/ops/l2_raw_detail_preview.js tests/unit/l2_raw_detail_preview.test.js --no-cache` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile scripts/ops/l2_raw_detail_preview.js tests/unit/l2_raw_detail_preview.test.js docs/_reports/L2_RAW_DETAIL_ACQUISITION_PREVIEW_PHASE5_11L2.md` passed
- DB row counts unchanged before commit:
    - `matches=10`
    - `raw_match_data=2`
    - `bookmaker_odds_history=2`
    - `l3_features=2`
    - `match_features_training=2`
    - `predictions=2`
- `l1-config-*` residue absent
- `docs/_staging_preview` absent

Integration browser automation is intentionally not run in this phase.

## 6. Actual controlled preview result

To be recorded after PR merge, green main CI, and final local safety baseline:

| field                              | result  |
| ---------------------------------- | ------- |
| request_url                        | pending |
| final_url                          | pending |
| http_status                        | pending |
| content_type                       | pending |
| body_byte_length                   | pending |
| body_sha256                        | pending |
| contains `4830746`                 | pending |
| contains `Angers`                  | pending |
| contains `Strasbourg`              | pending |
| json_parse_ok / hydration_parse_ok | pending |
| top_level_keys                     | pending |
| candidate_raw_data_paths           | pending |
| looks_like_valid_match_detail      | pending |
| body_printed                       | `false` |
| body_saved                         | `false` |
| DB unchanged                       | pending |

If FotMob returns 403, 429, captcha, or another block signal, the wrapper must stop, not retry, not launch browser/proxy, and report only the controlled error summary.

## 7. Recommended next phase

Recommended next phase:

Phase 5.12L2: raw_match_data ingest planning.

That phase should use the preview result to define:

- `raw_data` storage shape
- `data_hash` SHA-256 policy
- `data_version`
- `collected_at` / fetched-at mapping
- upsert and dedup policy
- protected table verification
- no features / predictions / training

It should remain no-write unless a later authorization phase explicitly permits `raw_match_data` writes.

## 8. Explicit non-execution

During implementation and local validation, this phase does not execute:

- `raw_match_data` writes
- DB writes
- harvest / ingest
- production harvester
- legacy raw backfill
- training / prediction
- browser / proxy runtime
- full body save / print
- file deletion
