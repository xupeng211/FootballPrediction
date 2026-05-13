# FotMob Raw Detail Access Route Audit - Phase 5.12L2A

## 1. Executive summary

Phase 5.11L2 added a safe single-target raw detail preview wrapper and proved the control boundary: it made one authorized request for `external_id=4830746`, did not write `raw_match_data`, did not write DB, did not save or print the full body, and did not use browser/proxy. The direct endpoint returned `HTTP 403`, so no valid raw detail payload was obtained.

Phase 5.12L2A is a read-only reconciliation audit. It reviews the existing L2 FotMob fetch code, raw persistence code, tests, fixtures, and docs to determine how the original project intended to access FotMob match detail data and how a future safe wrapper should reconnect to that path.

No external FotMob access, match detail request, retry, browser/proxy runtime, DB write, raw ingest, harvest, training, prediction, or file deletion is performed in this phase.

## 2. Current baseline

SELECT-only baseline at phase start:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |    2 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Target match seed exists:

| match_id              | external_id | fixture              | match_date             | status   |
| --------------------- | ----------- | -------------------- | ---------------------- | -------- |
| `53_20252026_4830746` | `4830746`   | Angers vs Strasbourg | 2026-05-10 19:00:00+00 | finished |

No existing `raw_match_data` row was found for `match_id=53_20252026_4830746` or `external_id=4830746`.

## 3. Phase 5.11L2 direct route result

The Phase 5.11L2 wrapper constructed:

```text
https://www.fotmob.com/api/data/matchDetails?matchId=4830746
```

Actual controlled preview result:

| field                         | result                                                             |
| ----------------------------- | ------------------------------------------------------------------ |
| request_url                   | `https://www.fotmob.com/api/data/matchDetails?matchId=4830746`     |
| final_url                     | `https://www.fotmob.com/api/data/matchDetails?matchId=4830746`     |
| http_status                   | `403`                                                              |
| content_type                  | `application/json`                                                 |
| body_byte_length              | `61`                                                               |
| body_sha256                   | `9f36e31930368263ca03ccd40f8ad36ddc178b25211d7b4bf0cbc2c1f6fa7558` |
| top_level_keys                | `code`, `error`                                                    |
| contains `4830746`            | `false`                                                            |
| contains `Angers`             | `false`                                                            |
| contains `Strasbourg`         | `false`                                                            |
| looks_like_valid_match_detail | `false`                                                            |
| controlled_error              | `CONTROLLED_BLOCK_SIGNAL:HTTP_403`                                 |
| retry/browser/proxy           | not used                                                           |
| DB/raw write                  | not performed                                                      |

Wrapper audit:

| question                                              | answer                                                                                                                                                                                                                                                                                                            |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Current request URL                                   | Fixed to `https://www.fotmob.com/api/data/matchDetails?matchId=4830746`.                                                                                                                                                                                                                                          |
| Why fixed to `/api/data/matchDetails?matchId=4830746` | `scripts/ops/l2_raw_detail_preview.js` defines `FOTMOB_DETAIL_URL='https://www.fotmob.com/api/data/matchDetails'`, locks `externalId='4830746'`, then appends `matchId=<externalId>`.                                                                                                                             |
| Uses existing `FotMobApiClient` / `FotMobStrategy`?   | No. The wrapper is a thin isolated preview client using `global.fetch` or injected fake fetch in tests. It deliberately does not import `ProductionHarvester`, `FotMobStrategy`, raw ingest scripts, `pg`, Playwright, proxy runtime, or child process modules.                                                   |
| Headers / request builder / locale / referer?         | Yes, but only a local request builder: `accept`, `accept-language=en-US,en;q=0.9`, `accept-encoding=identity`, `referer=https://www.fotmob.com/match/4830746`, a Chrome-like `user-agent`, and `x-requested-with=XMLHttpRequest`. No cookies, session manager, route selector, or locale selection are available. |
| Route selector support?                               | No. Only one direct public JSON route is implemented.                                                                                                                                                                                                                                                             |
| 403 handling?                                         | Yes. `HTTP 403` and `HTTP 429` are treated as block signals and returned as controlled error summaries; no retry or browser/proxy fallback is attempted.                                                                                                                                                          |

## 4. Existing L2 fetch code inventory

| component                                   | file                                                                                    | role                                            | detail route evidence                                                                                               | uses API/page/browser?                                             | can be single-target?                      | can be no-write?                                                                                       | risk                                                                                                        | recommendation                                                                                                                              |
| ------------------------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `FotMobApiClient.fetchMatchDetails()`       | `src/infrastructure/network/FotMobApiClient.js`                                         | Engine HTTP client for FotMob match detail JSON | Builds `/api/data/matchDetails?matchId=<external_id>` and sends JSON/XHR headers plus optional cookies              | API; may bootstrap browser cookies if no usable session is present | Yes, takes a `match` with `external_id`    | Yes only if called directly by a safe wrapper and browser bootstrap is disabled or explicitly injected | High if used as-is: default session bootstrap can create `BrowserProvider`; proxy/session path can activate | Keep as engine core. Future safe adapter may reuse request/header logic, but must add a hard no-browser/no-proxy mode and no-write wrapper. |
| `FotMobStrategy.fetchDataDirect()`          | `src/infrastructure/harvesters/strategies/FotMobStrategy.js`                            | API-first L2 strategy around `FotMobApiClient`  | Calls `apiClient.fetchMatchDetails()` and validates `content` / payload size                                        | API first; marks 403/404/429/incomplete data as browser fallback   | Yes                                        | Yes if used outside harvester persistence                                                              | Medium-high: fallback semantics are unsafe for agents unless blocked                                        | Reuse validation/normalization rules, but future preview must disable fallback and inject a safe fetch/client.                              |
| `FotMobStrategy` compliance mode            | `src/infrastructure/harvesters/strategies/FotMobStrategy.js`                            | Low-frequency no-browser direct path            | First fetches match page HTML `/match/<id>` and parses `__NEXT_DATA__`; then tries public JSON route                | Page HTML hydration, then API JSON; no browser in the direct calls | Yes                                        | Yes if extracted into a preview adapter                                                                | Medium: still external network and currently private method flow; direct 403 is possible                    | Best candidate for Phase 5.12L2B: route selector should test page hydration route before public JSON, but only with explicit authorization. |
| `FotMobStrategy.extractData()`              | `src/infrastructure/harvesters/strategies/FotMobStrategy.js`                            | Browser page extractor                          | Uses intercepted `matchfacts` / `matchDetails`, session-cookie API from page context, `__NEXT_DATA__`, DOM fallback | Browser page + API interception + hydration + DOM                  | Yes                                        | The extractor itself can return data, but normally sits inside harvest runtime                         | High: requires Playwright page and may use cookies/session; not allowed in this phase                       | Keep as engine core. Do not run for agents without a separate browser/proxy authorization phase.                                            |
| `NextDataParser`                            | `src/parsers/fotmob/NextDataParser.js`                                                  | Pure parser for `__NEXT_DATA__`                 | Extracts `<script id="__NEXT_DATA__">` and transforms `pageProps.content/general/header`                            | Parser only                                                        | Yes, if HTML is already fetched            | Yes                                                                                                    | Low: pure local parsing                                                                                     | Reuse for future HTML hydration preview adapter.                                                                                            |
| `MarathonService`                           | `src/infrastructure/services/MarathonService.js`                                        | Legacy long-running L2 harvester service        | Builds two API candidates: `/api/data/matchDetails?matchId=<id>` and `/api/matchDetails?matchId=<id>`               | Browser `page.goto()` to API URLs                                  | Yes                                        | Not safely: service also persists raw data                                                             | High: browser, proxy, long-running harvest, DB writes                                                       | Treat as route evidence only. Do not use as agent entrypoint.                                                                               |
| `backfill_historical_raw_match_data.js`     | `scripts/ops/backfill_historical_raw_match_data.js`                                     | Historical GSM backfill                         | Fetches `http://data.fotmob.com/webcl/ltc/gsm/<external_id>_en_gen.json.gz` and builds pseudo-FotMob payload        | API-like historical GSM endpoint                                   | In code, but defaults are broad            | Preview mode still fetches remote data                                                                 | High: remote network, workers, broad league defaults, writes with `--commit`                                | Not a raw match detail replacement. Keep blocked for agents; route is useful only as historical fallback evidence.                          |
| `FotMobExtractor`                           | `src/infrastructure/services/FotMobExtractor.js`                                        | L1/league webpage extractor                     | Uses league fixtures pages and `__NEXT_DATA__`; DOM scan fallback                                                   | Browser page / league hydration                                    | Not match-detail oriented                  | N/A                                                                                                    | High if executed: browser/runtime                                                                           | Not the L2 match detail path, but confirms project has established hydration parsing patterns.                                              |
| `ProductionHarvester` / `run_production.js` | `src/infrastructure/harvesters/ProductionHarvester.js`, `scripts/ops/run_production.js` | Production L2 orchestration                     | Calls `FotMobStrategy`, then persists through `Persistence.dualSave()`                                              | API-first then browser fallback                                    | Yes in code, bulk by default if no payload | `dryRun` exists, but entrypoint still initializes DB/browser/proxy paths                               | High: production, browser/proxy, retry, DB/file persistence, bulk                                           | Agent-blocked/admin-only. Do not use as safe preview or write path.                                                                         |

## 5. Existing raw_match_data write code inventory

| component                               | file                                                      | role                                     | writes `raw_match_data`? | upsert/hash/version behavior                                                                                                                      | coupled to legacy entrypoint?            | safe for agents?           | recommendation                                                                                           |
| --------------------------------------- | --------------------------------------------------------- | ---------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------- |
| `Persistence.saveToDatabase()`          | `src/infrastructure/harvesters/components/Persistence.js` | Production persistence helper            | Yes                      | `ON CONFLICT (match_id) DO UPDATE`; writes `raw_data`, `collected_at=NOW()`, `data_version='V26.1'`, `external_id`; does not populate `data_hash` | Used by `ProductionHarvester.saveData()` | No                         | Keep as engine code; not the controlled writer because hash is missing and `dualSave()` updates matches. |
| `Persistence.dualSave()`                | `src/infrastructure/harvesters/components/Persistence.js` | DB + file dual persistence               | Yes                      | wraps DB save in transaction, then writes a JSON file asynchronously                                                                              | Production harvester                     | No                         | Not suitable for controlled raw-only write because it also syncs `matches` and writes files.             |
| `Persistence._syncMatchPipelineState()` | `src/infrastructure/harvesters/components/Persistence.js` | Keeps match pipeline state in sync       | No raw row itself        | Updates `matches` status/pipeline columns; can auto-run schema sync if missing                                                                    | Production persistence                   | No                         | Future safe writer must avoid this path for first raw-only write.                                        |
| `backfill_historical_raw_match_data.js` | `scripts/ops/backfill_historical_raw_match_data.js`       | Historical GSM write path                | Yes with `--commit`      | `ON CONFLICT (match_id) DO UPDATE`; sets `data_version='FOTMOB_GSM_L2_V1'`; computes `data_hash=md5($3::text)`                                    | Legacy backfill CLI                      | No                         | Keep blocked for agents. It writes `matches.pipeline_status` too.                                        |
| `MarathonService._saveToDatabase()`     | `src/infrastructure/services/MarathonService.js`          | Long-running L2 service persistence      | Yes                      | `ON CONFLICT (match_id) DO UPDATE`; sets `data_version='V26.1-MARATHON'`; computes `md5($3)`                                                      | Marathon/browser service                 | No                         | Route evidence only; not a safe write path.                                                              |
| `raw_match_data_local_ingest.js`        | `scripts/ops/raw_match_data_local_ingest.js`              | Local fixture SELECT-only ingest preview | No; `--commit` blocked   | Calculates stable SHA-256 preview over canonicalized local raw fixture; SELECT-only DB checks                                                     | Safe local helper; no remote fetch       | Yes for local dry-run only | Reuse hash/preview ideas for future controlled writer planning.                                          |
| `raw_fixture_adapter_dry_run.js`        | `scripts/ops/raw_fixture_adapter_dry_run.js`              | Local fixture shape/identity preview     | No; commit blocked       | Produces SHA-256 preview and target match checks                                                                                                  | Safe local helper; no remote fetch       | Yes for local dry-run only | Useful for field mapping and payload-shape validation, not for remote acquisition.                       |

Raw write answers:

| question                            | answer                                                                                                                                                  |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Which code writes `raw_match_data`? | `Persistence.saveToDatabase()` / `dualSave()`, `backfill_historical_raw_match_data.js`, and `MarathonService._saveToDatabase()`.                        |
| Field mapping                       | `match_id`, `external_id`, `raw_data`, `collected_at`, `data_version`, sometimes `data_hash`.                                                           |
| `data_hash` policy                  | Inconsistent: production `Persistence` does not set it; GSM and Marathon use MD5; safe local helpers preview SHA-256 over stable JSON.                  |
| `data_version`                      | `V26.1` in production persistence, `FOTMOB_GSM_L2_V1` in historical GSM, `V26.1-MARATHON` in Marathon, local dry-run uses preview-only phase version.   |
| `collected_at`                      | Existing writers use `NOW()` / DB defaults; local previews only report would-be behavior.                                                               |
| `raw_data` shape                    | Usually normalized FotMob-like JSON with `general`, `header`, `content`; GSM path stores derived pseudo-FotMob JSON, not full public matchDetails raw.  |
| Upsert by `match_id`                | Yes in existing write helpers.                                                                                                                          |
| Transaction                         | `Persistence.dualSave()` and GSM commit wrap DB writes in transactions; `saveToDatabase()` alone assumes caller context.                                |
| FK check before write               | Existing DB FK enforces it; safe local helpers SELECT the target match first.                                                                           |
| Writes other tables                 | Existing production/GSM/Marathon paths update `matches` after raw write.                                                                                |
| Only raw_match_data write support   | Not in legacy production paths. A future safe writer must be separate and raw-only.                                                                     |
| Rows <= 1 / rows <= 8               | Possible in code by selection, but no current safe remote writer enforces it.                                                                           |
| No parser / feature / prediction    | Raw write helpers do not directly train/predict, but batch orchestration can chain later phases.                                                        |
| Safe writer split                   | Build a new controlled writer using SELECT target match, canonical SHA-256, `ON CONFLICT (match_id)`, raw-only transaction, and protected table checks. |

## 6. Fixtures/tests evidence

| evidence                                   | file                                                                             | finding                                                                                                                                                     |
| ------------------------------------------ | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API client route + cookie/session behavior | `tests/unit/FotMobApiClient.test.js`                                             | Confirms `fetchMatchDetails()` requests `/api/data/matchDetails?matchId=<id>` and carries `cf_clearance` / `_cfuvid` cookies when session bootstrap exists. |
| Compliance HTML route                      | `tests/unit/collectors/fotmob/FotMobComplianceMode.test.js`                      | Confirms compliance mode first requests `/match/<id>` HTML, expects no cookie / `x-requested-with`, and parses `__NEXT_DATA__`.                             |
| Compliance 403 behavior                    | `tests/unit/collectors/fotmob/FotMobComplianceMode.test.js`                      | Confirms 403 becomes `COMPLIANCE_HTTP_403`; no browser/proxy should be inferred from this path.                                                             |
| API-first strategy fallback                | `tests/unit/DataIntegrity.test.js`                                               | Confirms `fetchDataDirect()` returns API data when client succeeds, and marks 403 as `fallbackToBrowser=true`.                                              |
| Raw detail parser shape                    | `tests/unit/collectors/fotmob/FotMobThinParsers.test.js`                         | Confirms parsers expect `matchId`, `general`, `header`, and `content` including `stats` / `lineup`.                                                         |
| `__NEXT_DATA__` parser                     | `src/parsers/fotmob/NextDataParser.js`                                           | Pure parser can extract and transform `pageProps.content`, `pageProps.general`, `pageProps.header` from already-fetched HTML.                               |
| Local raw fixture                          | `tests/fixtures/l3/raw_match_data_phase419_sample.json`                          | Shows canonical local raw fixture shape with `matchId`, `general`, `header`, `content.stats`, `content.lineup`, `content.shotmap`, `content.momentum`.      |
| Synthetic raw fixture                      | `tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json`       | Shows local engineering-only raw shape; not real external data.                                                                                             |
| Legacy mock response                       | `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/mock_responses/fotmob_success.json` | Shows older mock success under `data.match`, not the current canonical `raw_match_data.raw_data` shape.                                                     |
| Collection report                          | `docs/_reports/FOTMOB_COLLECTION_REPORT.md`                                      | Historical local DB report indicates previous raw rows averaged about 205 KB and used `general.*` / `header.status` keys. No network in that report.        |

Fixture gaps:

- No current committed fixture was found for exact target `4830746`.
- No exact captured successful Phase 5.11L2 body exists because the live direct endpoint returned 403 and the wrapper does not save bodies.
- Existing raw fixtures demonstrate expected storage shape, but they are local/synthetic or legacy samples, not proof that the public direct endpoint is currently accessible.

## 7. 403 interpretation

Confirmed facts:

- Direct endpoint `/api/data/matchDetails?matchId=4830746` returned HTTP 403 in Phase 5.11L2.
- The response was JSON with top-level `code` / `error`.
- The response body did not contain `4830746`, `Angers`, or `Strasbourg`.
- The wrapper did not retry.
- The wrapper did not start browser/proxy.
- The wrapper did not write DB or `raw_match_data`.
- The wrapper used a local fixed route builder, not `FotMobApiClient` / `FotMobStrategy`.
- Existing project code also knows the `/api/data/matchDetails` route, but usually pairs it with session/cookie/bootstrap behavior or browser fallback.

Probable causes:

- The direct endpoint may require valid session cookies such as `cf_clearance`, `_cfuvid`, or `__cf_bm`.
- The endpoint may reject bare or low-context requests even when ordinary request headers are present.
- A page HTML hydration route may be the safer no-browser candidate, because `FotMobStrategy` compliance mode explicitly tries `/match/<id>` HTML before public JSON.
- The endpoint could have changed or could behave differently by region, locale, user agent, or date.
- Existing production success may have depended on browser/session/proxy infrastructure, not on raw unauthenticated direct HTTP.

Unknowns:

- Whether `/match/4830746` HTML currently returns usable `__NEXT_DATA__` without browser or cookies.
- Whether an explicitly supplied valid session cookie would make `/api/data/matchDetails` work.
- Whether the alternate `/api/matchDetails?matchId=<id>` path in `MarathonService` still works.
- Whether the target match has a slugged page URL that differs from `/match/4830746`.
- Whether FotMob currently requires browser execution or challenge handling for this target.

## 8. Recommended reconciliation path

### Option A: reuse existing API client path

Use when:

- `FotMobApiClient.fetchMatchDetails()` can be called with an explicitly injected no-browser/no-proxy session policy.
- Browser bootstrap is disabled by construction.
- A safe wrapper can enforce single target, no retry, no DB write, no full-body print/save.

Current fit: partial. The client has the right route and headers, but as-is it can bootstrap browser cookies if no usable session is available. It needs a hard `allowBrowserBootstrap=false` or dependency-injected safe session provider before agents can use it.

### Option B: reuse page hydration path

Use when:

- Match page HTML `/match/<id>` can be fetched without browser/proxy.
- `__NEXT_DATA__` is present and transformable via `NextDataParser`.
- Output remains metadata-only and no body is saved.

Current fit: best next candidate. `FotMobStrategy` compliance mode already implements this order: HTML hydration first, public JSON second. It is no-browser/no-proxy in the direct calls and has unit coverage. It still requires a separately authorized external request in a future phase.

### Option C: safe browser-disabled extractor split

Use when:

- Already-fetched HTML exists.
- Only the parser/transformer is needed.
- No Playwright page, browser context, proxy, session, or file write is involved.

Current fit: strong local implementation choice for Option B. Extract pure parser and request summary behavior, not browser runtime.

### Option D: browser/proxy requires separate future authorization

Use when:

- API and HTML hydration routes both fail or are blocked.
- Existing engine can only access detail via Playwright interception/session cookies/proxy.

Current fit: possible but not authorized. This must be a separate future phase with explicit user approval and a new safety envelope.

### Option E: stop FotMob detail route

Use when:

- No safe route succeeds.
- 403 cannot be reconciled with existing code without browser/proxy or challenge handling.

Current fit: fallback. Do not keep probing endpoints blindly.

Recommended next phase:

`Phase 5.12L2B: safe FotMob detail route selector / existing client integration`

Goals:

- no DB write
- no `raw_match_data` write
- no body save or full-body print
- no browser/proxy
- single target `53_20252026_4830746` / `4830746`
- no retry unless explicitly authorized
- implement a route selector backed by existing code evidence:
    - candidate 1: page HTML hydration `/match/4830746` using `NextDataParser.extractFromHtml()` / `transformToApiFormat()`
    - candidate 2: public JSON `/api/data/matchDetails?matchId=4830746` through a safe, browser-disabled request builder
    - candidate 3: alternate `/api/matchDetails?matchId=4830746` only as a planned option, not executed unless authorized
- use fake-fetch unit tests first, then request a separate user authorization before any live external request.

## 9. Guardrails for next phase

The next phase must enforce:

- target locked to `53_20252026_4830746` / `external_id=4830746`
- no DB write
- no `raw_match_data` write
- no full body save
- no full body print
- no browser/proxy unless separately authorized in a later phase
- no `ProductionHarvester`
- no `run_production.js`
- no `backfill_historical_raw_match_data.js`
- no `raw_match_data_local_ingest.js --commit`
- no harvest/backfill/bulk loop
- no training/prediction
- no retry unless explicitly authorized
- stdout metadata only: status, content-type, byte length, hash, markers, top-level keys, candidate paths, and controlled error summary.

## 10. Validation

Validation commands for this documentation-only phase:

- `git diff --check` - passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm test` - passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage` - passed
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile docs/_reports/FOTMOB_RAW_DETAIL_ACCESS_ROUTE_AUDIT_PHASE5_12L2A.md` - passed

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

## 11. Explicit non-execution

This phase does not execute:

- external FotMob access
- match detail request
- retry
- browser/proxy
- DB writes
- `raw_match_data` writes
- `matches` writes
- harvest / ingest
- batch backfill
- bulk harvest
- training / prediction
- model artifact loading
- file deletion
