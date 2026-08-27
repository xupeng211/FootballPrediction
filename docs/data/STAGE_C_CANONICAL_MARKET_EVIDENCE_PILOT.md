# Stage C — Canonical Market Evidence Pilot

## Objective and boundary

Stage C proves a provider-agnostic, immutable, versioned, replayable and auditable market-evidence spine for EPL pre-match 1X2 only. The Odds API is the **initial primary acquisition provider**, never the canonical provider. Canonical data is the FootballPrediction Market Contract. This pilot has no PostgreSQL persistence, scheduler, value/de-vig/CLV engine, backtest, training, second provider, betting automation or OddsPortal collector.

## Architecture

`Capture receipt → immutable raw object → versioned adapter projection → append-only JSONL observation ledger → derived as-of view`. Live acquisition is an explicitly separate boundary and never runs during offline replay.

Receipts hold sanitized endpoint/request metadata, timing, status, byte size and raw SHA-256. They must not contain secrets. Raw payloads are content-addressed by SHA-256 and are never changed. Multiple receipts may point to one raw object. Local live evidence is gitignored; fixtures are minimal synthetic schema-shaped data.

`MarketObservation` is factual evidence, not a strategy instruction: it deliberately has no `decision_target_at`. The machine-readable contract is [schemas/market_evidence/market_observation.schema.json](../../schemas/market_evidence/market_observation.schema.json), using the repository's Ajv 6-compatible draft-07 dialect. It includes canonical/provider event and bookmaker identities, ordered home/away event teams, competition/kickoff, `period/market_type/line`, `selection`, `price_side`, price/provenance, source timestamps and knowledge timestamps. Market identity supports `MATCH/1X2/null` now and represents `MATCH/ASIAN_HANDICAP/-0.25` without implementing handicap ingestion. Price sides are `BOOKMAKER`, `BACK`, and `LAY`. The schema binds the pilot's fixed and representative identity examples; the runtime contract's exact `period/market_type/line`-to-ID equality check is authoritative for arbitrary future numeric lines.

## Time and derived semantics

Source time (`bookmaker_last_update_at`, `source_snapshot_at`) is distinct from knowledge time (`capture_started_at`, `response_received_at`, `ingested_at`). All timestamps are UTC ISO-8601 with calendar validation. For decision/as-of time T, eligibility requires `response_received_at <= T` plus no quality flags. A prior source timestamp never makes later-received data visible. `deriveTimeline` requires an explicit UTC `decision_time`; every returned current/observation view is bounded by that knowledge-time cutoff.

The timeline is derived from the ledger, not a source of truth. `OPENING` defaults to `OUR_FIRST_SEEN` (earliest quality-valid pre-match observation); a provider-labelled opening remains separately identified as `PROVIDER_OPENING` and is never inferred from our first seen row. `CURRENT_AS_OF_T` is the latest eligible observation known by T. A Decision Snapshot applies the same query but belongs to the decision layer. `CLOSING` is the latest valid observation known strictly before kickoff; a provider “closing” label is provenance, not an unconditional sole truth. `close_age_seconds` may be derived later.

As-of views default to `price_side=BOOKMAKER`; exchange callers must query `BACK` or `LAY` explicitly so sides can never be mixed silently.

The four `acquisition_mode` values are explicit: `LIVE_CAPTURE` is forward collection, `HISTORICAL_API` and `HISTORICAL_FILE` are historical reconstruction, and `REPLAY` is offline re-projection. Historical reconstruction is never represented as a forward capture.

## Identity, versioning and replay

The adapter only parses The Odds API schema. The independently versioned registry maps provider event/bookmaker/market/selection IDs to canonical identities; unknown, ambiguous, semantically inconsistent or duplicate mappings fail closed. Event mappings bind provider home/away/kickoff facts to the existing FotMob/canonical-match ID, so a payload with swapped teams or kickoff cannot project. The pilot fixture records only the fixture mapping for `williamhill`; Pinnacle and Betfair Exchange have no live coverage because the provider smoke test is key-blocked, and no unavailable bookmaker is fabricated. `buildCoverageEvidence` emits a hashed, immutable coverage/quarantine record for observed and missing provider bookmaker IDs.

Each projection includes adapter, adapter version, identity-registry version and content hash, and projection version. Observation identity is additionally bound to the capture ID, response knowledge time, adapter version and registry content hash, so repeated identical payloads from distinct captures or mappings remain auditable observations. Reprojection of the same raw with a new version creates another appended record; it never updates the old projection. Replay is `raw + fixed capture metadata (including required provider and raw SHA-256) + adapter version + registry version`; deterministic semantic projection excludes only `ingested_at`, which is explicitly evidence metadata rather than semantic market fact. RAW, receipt, coverage and ledger files are created read-only; the ledger also has a read-only content-hash manifest and every read/append verifies the manifest before accepting new rows. Receipt request parameters, endpoint identity and quota metadata are structural allowlists, with a denylist and configured-key check as defense in depth. Coverage is `PARTIAL` whenever an expected bookmaker or requested `h2h` market is absent, including the case where a bookmaker is present with no requested market. The fixture registry is at `tests/fixtures/market_evidence/identity_registry.stage_c.v1.json` and is content-hash bound; production promotion requires a separately governed mapping artifact.

## Provider boundary and production blockers

The client boundary is limited to current pre-match EPL `h2h` and environment-only `THE_ODDS_API_KEY`; no key is hardcoded or logged. Its transport is injected by the repository's ProxyProvider-backed caller; the module does not import a low-level network client. Provider bookmaker keys must come from official definitions or real responses, never guesses. Before promotion to a long-term production provider, the Owner must confirm retention rights, analytical-use permission, redistribution restrictions and commercial-use boundaries. This pilot makes no legal conclusion.

Promotion remains blocked until the Owner confirms those provider terms, a governed identity registry binds real canonical events/bookmakers with auditable provenance, live capture coverage and quota evidence are observed, and production storage/operational controls are separately reviewed. Stage C does not authorize any of those production changes.

## Test evidence

`tests/unit/market_evidence/stage_c.test.js` covers contract rejects, schema-shaped fixture parsing, event identity binding, structural secret safety, immutable raw/SHA, coverage evidence, deterministic replay, projection version coexistence, append-only ledger and tamper detection, identity fail-closed, all acquisition modes, market/price extensibility, decision-target isolation and the strict source-time/knowledge-time look-ahead boundary. With the checked-in fixture (785 bytes), `RAW_SHA256=56cfff5c863a4a6fec1f506a293e3370b1ed96e87139282425912240aa24c01d`; the content-hash-bound registry is `IDENTITY_REGISTRY_SHA256=ab3ca435c51c87523ed4e41bf9e91b90db75de9800eefec5faadab49e7ad903e`; replaying the same raw with adapter `1.0.0`, registry `stage-c-fixture/v1` and fixed capture metadata yields `REPLAY_1_SHA256=f33dd80a8fb4e809332bda2141bb96c96ab4282149b33b980ace8e9425760056` and `REPLAY_2_SHA256=f33dd80a8fb4e809332bda2141bb96c96ab4282149b33b980ace8e9425760056`. Live smoke is `BLOCKED_MISSING_API_KEY` when `THE_ODDS_API_KEY` is absent; no live request or raw live evidence is committed.

Pilot evidence is recorded from the current worktree runs below; command exit codes and exact test counts are reported in the owner handoff rather than treated as source-of-truth state in this document.

Known limitations: no live EPL match was captured, so live coverage and provider credits are unknown; the synthetic fixture contains one EPL match and one fixture-only bookmaker key (`williamhill`) only. The identity registry fixture is not a production mapping authority. Production promotion additionally requires Owner confirmation of The Odds API retention/analytical-use/redistribution/commercial terms and a governed, independently evidenced event/bookmaker mapping.
