# FotMob Detail Route Selector - Phase 5.12L2B

## 1. Executive summary

Phase 5.11L2 proved the safe preview boundary but the direct public API route returned `HTTP 403` for:

```text
https://www.fotmob.com/api/data/matchDetails?matchId=4830746
```

Phase 5.12L2A found existing project evidence for multiple FotMob detail access paths: API `matchDetails`, page HTML hydration through `__NEXT_DATA__`, and browser/session fallback in legacy harvest code.

Phase 5.12L2B adds a safe route selector to the L2 raw detail preview wrapper. The default route order now favors `html_hydration` before `api_match_details`, while `alternate_route` remains planning-only. This phase uses fake-fetch / fixture-backed unit tests only.

No live external FotMob request, DB write, `raw_match_data` write, full body save/print, browser/proxy runtime, harvest/ingest, training, prediction, or file deletion is performed.

## 2. Implemented files

| file                                                         | change                                                                                                                |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `scripts/ops/l2_raw_detail_preview.js`                       | Adds safe route selector, route summaries, plan-only default, existing-parser integration, and route metadata output. |
| `src/infrastructure/services/FotMobDetailRouteSelector.js`   | Extracts pure route selector execution and summary helpers from the CLI wrapper.                                      |
| `tests/unit/l2_raw_detail_preview.test.js`                   | Adds fake HTML hydration, fake API JSON, fake 403, plan-only, alternate route, and safety guard coverage.             |
| `Makefile`                                                   | Adds `data-l2-raw-detail-route-preview-plan` and updates L2 help text / preview parameters.                           |
| `AGENTS.md`                                                  | Adds Phase 5.12L2B route selector guardrails.                                                                         |
| `docs/_reports/FOTMOB_DETAIL_ROUTE_SELECTOR_PHASE5_12L2B.md` | Adds this implementation report.                                                                                      |

## 3. Route selector design

Supported input routes:

- `route=auto`
- `route=html_hydration`
- `route=api_match_details`

Default `route=auto` order:

1. `html_hydration`
    - Candidate URL: `https://www.fotmob.com/match/4830746`
    - Parses page HTML `__NEXT_DATA__`
    - Uses the existing pure `NextDataParser.extractFromHtml()` and `transformToApiFormat()` helpers
2. `api_match_details`
    - Candidate URL: `https://www.fotmob.com/api/data/matchDetails?matchId=4830746`
    - Uses a safe local request builder aligned with the existing API client route
3. `alternate_route`
    - Candidate URL: `https://www.fotmob.com/api/matchDetails?matchId=4830746`
    - Included in plan output only
    - Not executed by default

Execution boundary:

- CLI defaults to plan-only unless live preview authorization is explicitly supplied in a future phase.
- Unit tests execute route selector paths only with injected fake fetch.
- `allow_browser_runtime=yes`, `allow_proxy_runtime=yes`, `allow_db_write=yes`, `allow_raw_match_data_write=yes`, `print_body=yes`, `save_body=yes`, `concurrency>1`, and `retry>0` are blocked.

## 4. Existing client integration

What is reused or aligned:

- Reuses `src/parsers/fotmob/NextDataParser.js` pure HTML `__NEXT_DATA__` parser.
- Aligns `html_hydration` route ordering with `FotMobStrategy` compliance mode, which tries match page HTML before public JSON.
- Aligns `api_match_details` URL with `FotMobApiClient.fetchMatchDetails()`.
- Keeps `FotMobApiClient` import disabled because the current engine client can bootstrap browser cookies if no usable session exists.

What is intentionally not used:

- `ProductionHarvester` is not imported or executed.
- `FotMobStrategy` runtime harvest paths are not imported or executed.
- Legacy backfill, Marathon, raw ingest, browser/session/proxy fallback, and persistence paths are not used.

Engine-core components remain available for future controlled integration:

- `FotMobApiClient`
- `FotMobStrategy`
- `NextDataParser`
- `ProductionHarvester`
- raw persistence components

## 5. Test evidence

Unit tests cover:

- `route=auto` builds `html_hydration` before `api_match_details`.
- Fake HTML with `__NEXT_DATA__` parses through the existing parser and selects `html_hydration`.
- Fake hydration candidate contains `4830746`, `Angers`, and `Strasbourg`.
- Fake API JSON parses and selects `api_match_details`.
- Fake API `HTTP 403` returns controlled block summary.
- Auto route does not proceed past a controlled block.
- Auto route may fall back from missing hydration to fake API JSON.
- `alternate_route` is present as plan-only and not executed.
- `body_printed=false` and `body_saved=false`.
- DB/raw writes remain false.
- Browser/proxy flags remain false.
- Source audit guards block `pg`, file writes, child process, native HTTP clients, browser/proxy imports, ProductionHarvester, runtime FotMobStrategy harvest, raw ingest, and legacy backfill.

## 6. Safety boundary

This phase enforces:

- no live external FotMob access
- no live match detail request
- no retry
- no browser/proxy runtime
- no DB write
- no `raw_match_data` write
- no `matches` write
- no protected table write
- no full body save
- no full body print
- no harvest/ingest/backfill
- no training/prediction
- no model artifact loading
- no file deletion

## 7. Recommended next phase

Recommended:

`Phase 5.12L2C: controlled raw detail preview via audited route selector`

Requirements:

- user explicitly authorizes exactly one live request
- single target `53_20252026_4830746` / `external_id=4830746`
- `route=auto` or `route=html_hydration` first
- no DB write
- no `raw_match_data` write
- no full body save/print
- no browser/proxy
- no retry unless explicitly authorized
- if HTML hydration fails, report the failure; do not automatically add headers, cookies, browser, proxy, or alternate live routes without a new authorization boundary

## 8. Explicit non-execution

This phase does not execute:

- external FotMob access
- live match detail request
- retry
- browser/proxy
- DB writes
- `raw_match_data` writes
- harvest / ingest
- batch backfill
- bulk harvest
- training / prediction
- model artifact loading
- full body save/print
- file deletion

## 9. Validation

Validation commands:

- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/l2_raw_detail_preview.test.js`
- `docker compose -f docker-compose.dev.yml exec -T dev npm test`
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage`
- `docker compose -f docker-compose.dev.yml exec -T dev npx eslint scripts/ops/l2_raw_detail_preview.js tests/unit/l2_raw_detail_preview.test.js src/infrastructure/services/FotMobDetailRouteSelector.js --no-cache`
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile scripts/ops/l2_raw_detail_preview.js tests/unit/l2_raw_detail_preview.test.js src/infrastructure/services/FotMobDetailRouteSelector.js docs/_reports/FOTMOB_DETAIL_ROUTE_SELECTOR_PHASE5_12L2B.md`
- `git diff --check`
- `make data-l2-raw-detail-route-preview-plan`

Safety checks:

- DB row counts unchanged:
    - `matches=10`
    - `raw_match_data=2`
    - `bookmaker_odds_history=2`
    - `l3_features=2`
    - `match_features_training=2`
    - `predictions=2`
- `l1-config-*` residue absent
- `docs/_staging_preview` absent

Results:

- `node --test tests/unit/l2_raw_detail_preview.test.js`: passed, 64/64.
- `npm test`: passed.
- `npm run test:coverage`: passed with the existing 80/80/80 coverage gate.
- `eslint`: passed for the wrapper, unit test, and route selector helper.
- `prettier --check`: passed for all touched files.
- `git diff --check`: passed.
- `make data-l2-raw-detail-route-preview-plan`: passed and printed plan-only JSON.
- DB row counts remained unchanged:
    - `matches=10`
    - `raw_match_data=2`
    - `bookmaker_odds_history=2`
    - `l3_features=2`
    - `match_features_training=2`
    - `predictions=2`
- `l1-config-*` residue absent.
- `docs/_staging_preview` absent.
