# Stage C — Canonical Market Evidence Pilot

## Objective and boundary

Stage C proves a provider-agnostic, immutable, versioned, replayable and auditable market-evidence spine for EPL pre-match 1X2 only. The Odds API is the **initial primary acquisition provider**, never the canonical provider. Canonical data is the FootballPrediction Market Contract. This pilot has no PostgreSQL persistence, scheduler, value/de-vig/CLV engine, backtest, training, second provider, betting automation or OddsPortal collector.

## Architecture

`Capture receipt → immutable raw object → versioned adapter projection → append-only JSONL observation ledger → derived as-of view`. Live acquisition is an explicitly separate boundary and never runs during offline replay.

Receipts hold sanitized endpoint/request metadata, timing, status, byte size and raw SHA-256. They must not contain secrets. Raw payloads are content-addressed by SHA-256 and are never changed. Multiple receipts may point to one raw object. Local live evidence is gitignored; fixtures are minimal synthetic schema-shaped data.

`MarketObservation` is factual evidence, not a strategy instruction: it deliberately has no `decision_target_at`. The machine-readable contract is [schemas/market_evidence/market_observation.schema.json](../../schemas/market_evidence/market_observation.schema.json). It includes canonical/provider event and bookmaker identities, ordered home/away event teams, competition/kickoff, `period/market_type/line`, `selection`, `price_side`, price/provenance, source timestamps and knowledge timestamps. Market identity supports `MATCH/1X2/null` now and represents `MATCH/ASIAN_HANDICAP/-0.25` without implementing handicap ingestion. Price sides are `BOOKMAKER`, `BACK`, and `LAY`.

## Time and derived semantics

Source time (`bookmaker_last_update_at`, `source_snapshot_at`) is distinct from knowledge time (`capture_started_at`, `response_received_at`, `ingested_at`). All timestamps are UTC ISO-8601. For decision/as-of time T, eligibility requires `response_received_at <= T` plus no quality flags. A prior source timestamp never makes later-received data visible.

The timeline is derived from the ledger, not a source of truth. Opening means the earliest quality-valid pre-match observation (unless separately provider-labelled with provenance). Current as-of T is the latest eligible observation. A Decision Snapshot applies the same query but belongs to decision-layer code. Closing is the latest valid pre-kickoff observation known before kickoff; `close_age_seconds` may be derived later.

## Identity, versioning and replay

The adapter only parses The Odds API schema. The independently versioned registry maps provider event/bookmaker/market/selection IDs to canonical identities; unknown or duplicate mappings fail closed. Event mappings are intended to reference existing FotMob/canonical-match IDs, not create another event system.

Each projection includes adapter, adapter version, identity-registry version and projection version. Reprojection of the same raw with a new version creates another appended record; it never updates the old projection. Replay is `raw + fixed capture metadata + adapter version + registry version`; deterministic semantic projection excludes only `ingested_at`, which is explicitly evidence metadata rather than semantic market fact. The fixture registry is at `tests/fixtures/market_evidence/identity_registry.stage_c.v1.json`; production promotion requires a separately governed mapping artifact.

## Provider boundary and production blockers

The client boundary is limited to current pre-match EPL `h2h` and environment-only `THE_ODDS_API_KEY`; no key is hardcoded or logged. Its transport is injected by the repository's ProxyProvider-backed caller; the module does not import a low-level network client. Provider bookmaker keys must come from official definitions or real responses, never guesses. Before promotion to a long-term production provider, the Owner must confirm retention rights, analytical-use permission, redistribution restrictions and commercial-use boundaries. This pilot makes no legal conclusion.

## Test evidence

`tests/unit/market_evidence/stage_c.test.js` covers contract rejects, secret safety, immutable raw/SHA, fixture parsing, deterministic replay, projection version coexistence, append-only ledger, identity fail-closed, all acquisition modes, market/price extensibility, decision-target isolation and the strict source-time/knowledge-time look-ahead boundary. With the checked-in fixture (785 bytes), `RAW_SHA256=56cfff5c863a4a6fec1f506a293e3370b1ed96e87139282425912240aa24c01d`; replaying the same raw with adapter `1.0.0`, registry `stage-c-fixture/v1` and fixed capture metadata yields `REPLAY_1_SHA256=d7aea341c911e217e7c24418d1df1310653352b3745a44efffb574dcae592ca5` and `REPLAY_2_SHA256=d7aea341c911e217e7c24418d1df1310653352b3745a44efffb574dcae592ca5`. Live smoke is `BLOCKED_MISSING_API_KEY` when `THE_ODDS_API_KEY` is absent; no live request or raw live evidence is committed.

Pilot evidence on 2026-08-27: Stage C unit tests passed 10/10; affected JavaScript gate passed 73/73; the selected legacy odds-staging regression set passed 173/173; repository lint and changed-file formatting checks passed. `make verify-targeted` could not enter because the `dev` service was not running, while the same canonical dispatcher (`python3 scripts/devops/validation_profiles.py targeted`) completed successfully. The full repository unit runner was not used as a Stage C acceptance gate because its legacy 449-file process did not terminate in the available local environment; no Stage C or affected-test failure was observed.

Known limitations: no live EPL match was captured, so live coverage and provider credits are unknown; the fixture contains one EPL match and one response-sourced bookmaker key (`williamhill`) only. The identity registry fixture is not a production mapping authority. Production promotion additionally requires Owner confirmation of The Odds API retention/analytical-use/redistribution/commercial terms and a governed, independently evidenced event/bookmaker mapping.
