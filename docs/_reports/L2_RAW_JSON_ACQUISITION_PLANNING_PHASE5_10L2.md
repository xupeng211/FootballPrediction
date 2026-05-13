# L2 Raw JSON Acquisition Planning - Phase 5.10L2

## 1. Executive summary

Phase 5.09L1 has completed controlled L1 matches seed execution for the 2026-05-10 Ligue 1 target date. `matches` now contains the 8 newly seeded FotMob matches plus the previous baseline rows. `raw_match_data` remains unchanged.

Phase 5.10L2 is only an audit and planning phase for controlled raw JSON acquisition. It does not collect FotMob match detail data, does not write `raw_match_data`, and does not run parser, feature, training, or prediction pipelines.

The correct L2 direction is:

- use seeded `matches` rows as the L2 input contract
- fetch remote FotMob match detail raw JSON only in a future explicitly authorized phase
- store raw JSON in `raw_match_data`
- make all later parsing read from local `raw_match_data`
- reuse existing L2 engine core where possible
- avoid legacy batch/backfill/production entrypoints for agent workflows

## 2. Current DB baseline

Baseline row counts confirmed by SELECT-only DB reads:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |    2 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

Newly seeded L2 input matches:

| match_id              | external_id | fixture                      | match_date             | status   |
| --------------------- | ----------- | ---------------------------- | ---------------------- | -------- |
| `53_20252026_4830746` | `4830746`   | Angers vs Strasbourg         | 2026-05-10 19:00:00+00 | finished |
| `53_20252026_4830747` | `4830747`   | Auxerre vs Nice              | 2026-05-10 19:00:00+00 | finished |
| `53_20252026_4830748` | `4830748`   | Le Havre vs Marseille        | 2026-05-10 19:00:00+00 | finished |
| `53_20252026_4830750` | `4830750`   | Metz vs Lorient              | 2026-05-10 19:00:00+00 | finished |
| `53_20252026_4830751` | `4830751`   | Monaco vs Lille              | 2026-05-10 19:00:00+00 | finished |
| `53_20252026_4830752` | `4830752`   | Paris Saint-Germain vs Brest | 2026-05-10 19:00:00+00 | finished |
| `53_20252026_4830753` | `4830753`   | Rennes vs Paris FC           | 2026-05-10 19:00:00+00 | finished |
| `53_20252026_4830754` | `4830754`   | Toulouse vs Lyon             | 2026-05-10 19:00:00+00 | finished |

## 3. Existing L2 code inventory

| component                                                | file                                                         | role                                  | network risk | DB write risk  | raw_match_data relation                                       | status                                | recommended action                                                                       |
| -------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------- | ------------ | -------------- | ------------------------------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------- |
| `FotMobApiClient`                                        | `src/infrastructure/network/FotMobApiClient.js`              | HTTP client for FotMob `matchDetails` | High         | None directly  | returns raw match detail payload                              | engine core                           | reuse behind future safe wrapper; disable browser bootstrap unless explicitly authorized |
| `FotMobStrategy`                                         | `src/infrastructure/harvesters/strategies/FotMobStrategy.js` | FotMob L2 extraction strategy         | High         | None directly  | normalizes raw detail payload before persistence              | engine core with risky fallback modes | reuse narrowly for single-target preview; block browser/proxy fallback by default        |
| `ProductionHarvester`                                    | `src/infrastructure/harvesters/ProductionHarvester.js`       | L2 harvest orchestrator               | High         | High           | calls `Persistence.dualSave()`                                | legacy risky runtime                  | do not run for agents; extract core behavior only if needed                              |
| `Persistence`                                            | `src/infrastructure/harvesters/components/Persistence.js`    | DB/file persistence helper            | None         | High           | writes `raw_match_data` and updates `matches`                 | write helper, not safe as-is          | keep engine code; future controlled write must avoid extra table writes                  |
| `AbstractHarvester`                                      | `src/infrastructure/harvesters/base/AbstractHarvester.js`    | browser/proxy/retry orchestration     | High         | Indirect       | calls `saveData()` unless `dryRun`                            | legacy risky runtime                  | do not use as safe L2 entrypoint                                                         |
| `backfill_historical_raw_match_data.js`                  | `scripts/ops/backfill_historical_raw_match_data.js`          | historical GSM backfill               | High         | High           | fetches GSM feed, writes `raw_match_data`, updates `matches`  | legacy risky entrypoint               | agent-blocked; not the 5.10L2 safe path                                                  |
| `raw_match_data_local_ingest.js`                         | `scripts/ops/raw_match_data_local_ingest.js`                 | local fixture preview                 | None         | Commit blocked | SELECT-only preview of local fixture against `raw_match_data` | safe existing helper                  | keep for local fixture dry-run; not remote acquisition                                   |
| `run_production.js` / `npm start` / `harvest:production` | `scripts/ops/run_production.js`, `package.json`              | production harvest launcher           | High         | High           | launches `ProductionHarvester`                                | legacy risky entrypoint               | agent-blocked/admin-only                                                                 |
| `batch_historical_backfill.js`                           | `scripts/ops/batch_historical_backfill.js`                   | batch historical orchestration        | High         | High           | may orchestrate raw/data backfill flows                       | legacy risky entrypoint               | agent-blocked                                                                            |
| `data-raw-dry-run`                                       | `Makefile`                                                   | local raw fixture preview target      | None         | None           | calls `raw_match_data_local_ingest.js` without commit         | safe helper                           | keep; not a remote detail acquisition path                                               |
| `data-raw-commit`                                        | `Makefile`                                                   | blocked raw commit gate               | None         | Blocked        | explicitly blocked                                            | blocked gate                          | keep blocked until future authorization                                                  |

## 4. raw_match_data schema analysis

Current table shape:

| column         | type           | nullable                  | role                                              |
| -------------- | -------------- | ------------------------- | ------------------------------------------------- |
| `id`           | `bigint`       | no                        | surrogate primary key                             |
| `match_id`     | `varchar(50)`  | no                        | FK to `matches(match_id)` and unique business key |
| `external_id`  | `varchar(100)` | yes                       | FotMob external match id                          |
| `raw_data`     | `jsonb`        | no                        | raw JSON payload storage                          |
| `collected_at` | `timestamptz`  | yes, constrained not null | fetch/write timestamp                             |
| `data_version` | `varchar(20)`  | yes                       | data contract/version marker                      |
| `data_hash`    | `varchar(64)`  | yes                       | checksum/hash value                               |

Indexes and constraints:

- primary key: `id`
- unique constraint: `raw_match_data_match_id_key` on `match_id`
- FK: `raw_match_data.match_id -> matches.match_id ON DELETE CASCADE`
- indexes: `match_id`, `external_id`, `collected_at DESC`, `data_version + collected_at`, GIN on `raw_data`
- checks:
    - `match_id_format`
    - `raw_data_not_empty`
    - `raw_data_has_match_id`
    - `collected_at_not_null`
- trigger: `trg_update_raw_data_timestamp`

Schema gaps for future controlled remote ingestion:

- no dedicated `source` column; source must currently live inside `raw_data` or `_meta`
- no dedicated `status` / `error` columns for failed attempts
- no dedicated `metadata` column separate from payload
- `data_hash` exists, but current code uses inconsistent hash policy: `Persistence` does not populate it, while historical GSM backfill uses `md5($3::text)`
- `collected_at` exists, but there is no separate `fetched_at` field

Recommended future mapping:

| desired field      | current storage option                             | recommendation                                                        |
| ------------------ | -------------------------------------------------- | --------------------------------------------------------------------- |
| `source`           | `_meta.source` inside `raw_data` or `data_version` | keep in metadata for 5.15L2; consider schema migration later          |
| `match_id`         | `match_id`                                         | required                                                              |
| `external_id`      | `external_id`                                      | required for FotMob rows                                              |
| `fetched_at`       | `collected_at` and `_meta.fetched_at`              | use `collected_at` for DB timestamp, include `fetched_at` in metadata |
| `payload/raw_json` | `raw_data`                                         | required                                                              |
| `hash/checksum`    | `data_hash`                                        | use stable SHA-256 policy in future controlled write                  |
| `metadata`         | `_meta` inside `raw_data`                          | include source URL, byte length, payload keys, fetch mode             |
| `status/error`     | no column                                          | do not persist failed fetches until schema/gate is planned            |

## 5. Existing raw detail acquisition path

The existing project has multiple ways to obtain FotMob match detail data:

- API path:
    - `FotMobApiClient.fetchMatchDetails()` builds `https://www.fotmob.com/api/data/matchDetails?matchId=<external_id>`.
    - `FotMobStrategy.fetchDataDirect()` uses this client and validates the returned payload.
- page hydration path:
    - `FotMobStrategy.extractData()` can read `__NEXT_DATA__` from a Playwright page and transform it through `NextDataParser`.
- browser/session fallback path:
    - `FotMobApiClient` can bootstrap cookies through `BrowserProvider`.
    - `AbstractHarvester` initializes browser/proxy runtime unless compliance mode disables it.
- historical GSM path:
    - `backfill_historical_raw_match_data.js` fetches `http://data.fotmob.com/webcl/ltc/gsm/<external_id>_en_gen.json.gz` and builds a pseudo-FotMob payload.

For Phase 5.11L2, the safest remote preview should start from the API path for a single seeded match, not from legacy production/batch entrypoints.

Current gaps:

- no dedicated `data-l2-*` safe target exists
- no remote no-write preview wrapper exists for seeded matches
- no safe wrapper proves `concurrency=1`, `MAX_TARGETS<=8`, no browser/proxy fallback, and no DB writes
- no future authorization packet exists for match detail fetch

## 6. Existing raw_match_data write path

Current write paths:

- `Persistence.saveToDatabase()`
    - inserts into `raw_match_data`
    - `ON CONFLICT (match_id) DO UPDATE`
    - writes `raw_data`, `collected_at`, `data_version`, `external_id`
    - does not populate `data_hash`
- `Persistence.dualSave()`
    - wraps raw save in a transaction
    - calls `_syncMatchPipelineState()`
    - therefore updates `matches` as well as writing `raw_match_data`
    - also writes a JSON file asynchronously through `saveToFile()`
- `backfill_historical_raw_match_data.js`
    - writes `raw_match_data`
    - updates `matches.pipeline_status='harvested'`
    - has a `--commit` flag
    - preview still fetches remote GSM data when not committed
- `raw_match_data_local_ingest.js`
    - local fixture only
    - SELECT-only DB checks
    - `--commit` explicitly blocked

Answers to the required safety questions:

| question                                    | answer                                                                                                                                                           |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| who fetches FotMob match detail raw JSON?   | `FotMobApiClient.fetchMatchDetails()` via `FotMobStrategy.fetchDataDirect()`; browser/page alternatives exist in `FotMobStrategy.extractData()`                  |
| API, page hydration, or browser extraction? | all three exist: API `matchDetails`, page `__NEXT_DATA__`, and browser/session fallback                                                                          |
| who writes `raw_match_data`?                | `Persistence.saveToDatabase()` / `dualSave()` and `backfill_historical_raw_match_data.js`; local ingest commit is blocked                                        |
| unique/FK/upsert?                           | unique `match_id`, FK to `matches`, upsert by `match_id` in existing write helpers                                                                               |
| coupled to batch/backfill/production?       | yes for production/backfill; current production persistence also updates `matches` and writes files                                                              |
| existing dry-run?                           | production has `dryRun`; raw local ingest has safe dry-run; historical GSM preview still touches network                                                         |
| dry-run trustworthy?                        | local fixture dry-run is trustworthy; production/backfill dry-run is not sufficient for agents because it can still initialize browser/proxy or touch network    |
| commit flag?                                | historical GSM has `--commit`; local raw ingest commit is blocked; production is effectively commit unless dry-run                                               |
| single match possible?                      | production `run(payload.match)` can single-target in code, but the CLI is not a safe agent entrypoint; future wrapper should select seeded `match_id` explicitly |
| concurrency=1 possible?                     | production/backfill can configure concurrency, but no safe L2 wrapper enforces it yet                                                                            |
| write only raw_match_data?                  | not with current production persistence; it updates `matches` and writes files                                                                                   |
| parser/features/training auto-trigger?      | not directly in `Persistence`, but batch/production orchestration entrypoints are too broad                                                                      |
| browser/proxy startup risk?                 | yes through `AbstractHarvester` and `FotMobApiClient` browser bootstrap                                                                                          |
| safe wrapper needed?                        | yes, a thin `data-l2-*` wrapper should isolate fetch preview, write preflight, and controlled write                                                              |

## 7. Recommended safe L2 path

Build a thin safe wrapper around existing engine core rather than a new collector.

Recommended design:

- input:
    - SELECT-only seeded matches from `matches`
    - exact allowed scope: first `53_20252026_4830746`, then max 8 seeded rows
    - source: `fotmob`
    - external id from `matches.external_id`
- network preview:
    - default no network
    - user authorization required for exactly one external FotMob match detail request
    - `CONCURRENCY=1`
    - `MAX_TARGETS<=8`
    - no browser/proxy fallback unless a later phase explicitly authorizes it
    - output only metadata: URL, byte length, hash, top-level keys, marker presence
    - no raw JSON file write, no DB write
- raw write:
    - separated from fetch
    - transaction
    - only `raw_match_data`
    - no `matches` update in the first controlled write phase
    - no features, no predictions, no training
    - pre/post row count verification for protected tables
- upsert/dedup:
    - target key: `match_id`
    - if no row exists: would insert
    - if row exists with same hash: would skip
    - if row exists with different hash: would update only after explicit overwrite authorization
    - hash policy: stable SHA-256 over canonicalized raw payload
- failure/retry/rate limit:
    - no automatic retry in first authorized preview
    - stop on 403 / 429 / captcha / block / HTML challenge
    - no downgrade to browser/proxy
    - record failure only in stdout during planning/preview phases

Protected tables for the controlled write phase:

- `matches`: SELECT-only during L2 raw write
- `bookmaker_odds_history`: no writes
- `l3_features`: no writes
- `match_features_training`: no writes
- `predictions`: no writes

## 8. Proposed Phase 5.11L2+

### Phase 5.11L2: controlled raw detail acquisition preview

- input: seeded matches
- first target: `53_20252026_4830746` / external id `4830746`
- user authorizes exactly one external FotMob match detail request
- no DB writes
- no file writes
- no browser/proxy fallback
- output raw detail metadata only

### Phase 5.12L2: raw_match_data ingest planning

- finalize field mapping
- finalize SHA-256 hash policy
- finalize metadata shape
- finalize no-write preflight output contract
- confirm protected table policy

### Phase 5.13L2: raw_match_data authorization

- user authorizes raw write separately from fetch
- scope max 8 rows
- write target only `raw_match_data`
- training/prediction remain explicitly forbidden

### Phase 5.14L2: raw_match_data preflight

- SELECT target `matches`
- SELECT existing `raw_match_data`
- compute would_insert / would_update / would_skip
- capture baseline row counts
- require final DB-write confirmation

### Phase 5.15L2: controlled raw_match_data write

- transaction
- rows <= 8
- only `raw_match_data`
- post-write count verification
- no parser/features/training/prediction

## 9. Legacy L2 entrypoint handling

Agent-blocked legacy entrypoints:

- `scripts/ops/run_production.js`
- `npm start`
- `npm run harvest:production`
- `make dev-harvest`
- `src/infrastructure/harvesters/ProductionHarvester.js` as a runtime entrypoint
- `scripts/ops/backfill_historical_raw_match_data.js`
- `scripts/ops/batch_historical_backfill.js`
- `node scripts/ops/raw_match_data_local_ingest.js --commit`
- any entrypoint that fetches FotMob detail and writes `raw_match_data` in the same run

Engine code to keep:

- `FotMobApiClient`
- `FotMobStrategy`
- `NextDataParser`
- `ProductionHarvester` internals as reference/core behavior
- `Persistence` as existing persistence reference
- `raw_match_data_local_ingest.js` as local SELECT-only fixture helper
- parser modules under `src/parsers/fotmob/`

References to migrate later:

- docs that recommend production harvest for agent workflows
- Makefile help that does not yet expose future `data-l2-*`
- npm scripts that point humans to production paths without warning
- tests that imply production dry-run is sufficient as an agent-safe raw detail preview

## 10. Validation

Validation results for this planning phase:

- no DB writes
- row counts unchanged:
    - `matches=10`
    - `raw_match_data=2`
    - `bookmaker_odds_history=2`
    - `l3_features=2`
    - `match_features_training=2`
    - `predictions=2`
- `l1-config-*` residue absent
- `docs/_staging_preview` absent
- `git diff --check` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm test` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage` passed
- `docker compose -f docker-compose.dev.yml exec -T dev npx prettier --check --ignore-unknown AGENTS.md Makefile docs/_reports/L2_RAW_JSON_ACQUISITION_PLANNING_PHASE5_10L2.md` passed

## 11. Explicit non-execution

This phase did not execute:

- external FotMob access
- FotMob match detail request
- network dry-run
- browser automation
- proxy runtime
- legacy raw backfill
- production harvest
- raw ingest commit
- `raw_match_data` write
- DB write
- harvest / ingest
- training / prediction
- file deletion
