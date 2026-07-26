# M3-D4F Candidate-to-Canonical Linkage and Real Import Readiness Review

- lifecycle: current-state
- scope: documentation-only static readiness review
- issue: #1793
- reviewed main baseline: 535e144cadc7019b8e86fc62e6e2bb1f4216a8c8
- database access: none
- Docker/Redis access: none
- real source payload access: none

## 1. Executive decision

**Decision: `READY_FOR_D4F_READ_ONLY_INVENTORY_AUTHORIZATION`.**

This narrowly permits the user to consider a separately authorized, bounded SELECT-only inventory of one explicitly named non-production canonical target. It does not authorize executing that inventory, implementation, migration, linkage write, `canonical_match_id` write, matches/canonical-odds write, real import, training, backtest, or prediction.

## 2. Scope and non-goals

Only Git-tracked source, SQL, tests, ordinary docs, Git metadata and Issue #1793 metadata were read. No .env, credential, runtime secret, external source payload, DB, Redis, Docker/Compose, browser, proxy, network fetch, migration, service test, or local Gatekeeper was used. Historical report counts are historical evidence, not current live truth.

## 3. Evidence reviewed

| Area | Files | Evidence class |
| --- | --- | --- |
| Staging DDL | V26.8/V26.9 migrations | current static |
| Persistence boundary | odds_staging persistenceContracts/persistenceRepository | current static |
| Candidate linker | odds_staging matchLinker/contracts/pipeline and unit tests | current static |
| Canonical matches | deploy/docker/init_db.sql, V6.5, V12.4, match_repository.py | current static |
| Identity workflows | FotMob exporter, controlled seed/readiness, Recon | current static |
| D4E state/counts | PROJECT_STATUS, D4D/runbook docs, Issue #1793 | historical only |
| Real source | tracked fixtures and test manifests only | not proven |

## 4. Current staging identity contract

V26.8 declares nullable TEXT `canonical_match_id` and `candidate_match_id`; it has no matches FK. `canonical_match_fk_status` allows only `unverified_database_fk` and `verified_database_fk`. The mapper sets accepted rows to `canonical_match_id: null`, copies local `match_link.matched_id` to `candidate_match_id`, and sets `unverified_database_fk`.

Required `historical_match_identity` preserves source/provider ID, competition, season, kickoff, ordered teams, local-link payload and kickoff interpretation evidence. Required `match_link_evidence`, unique `idempotency_key`, V26.9 `business_fingerprint`, raw SHA-256/locator, adapter/version and provenance retain replay evidence. Quarantine is separate with required reason codes/source payload; it is not accepted/canonical data.

The binary FK status cannot describe linkage outcomes. D4F needs `verified_unique`, `unmatched`, `ambiguous`, `conflict`, `invalid_identity`, and `manual_review_required`; `rejected`, `stale`, and `manually_verified` are audit dispositions. Unverified candidates can stage, but cannot enter canonical integration or training.

## 5. Candidate identity and canonical matches evidence

### Candidate identity

`matchLinker.js` consumes local candidate objects. Stable ID is `id`, falling back to `match_id`/`matchId`; it does not generate canonical database identity. It first tries exact provider-scoped `(source_provider, source_match_id)`, then exactly one ordered match of normalized home/away, competition, season and strict absolute kickoff. Normalization is NFKD, diacritic removal, lowercase, whitespace collapse and trim. Reversal/multiple candidates do not match. Output is deterministic for fixed inputs, but collision scope is the supplied candidate set. `source_match_id` is provider-scoped, not globally canonical.

Candidate ID is a **local deterministic candidate identity**, not proof that it equals `matches.match_id` merely because both are strings.

### Canonical matches and existing workflows

Tracked bootstrap DDL declares `matches.match_id VARCHAR(50) PRIMARY KEY`, nullable `external_id VARCHAR(100)`, `league_name`, `season`, ordered `home_team`/`away_team`, nullable `match_date TIMESTAMPTZ`, `status`, and `data_source`. Static indexes cover season/date/teams; V6.5 expresses lowercase status and `YYYY/YYYY` season constraints. Existing raw/L3/OddsPortal mappings show FK patterns to `matches(match_id)`.

MatchRepository, FotMob seed/discovery, raw-data preflight, Recon and legacy OddsPortal paths are not D4F executors: they are source-specific, DB/network/write-capable, or historical Phase paths. Reusable concepts only are external-ID provenance, ordered teams, normalized evidence, unique-candidate requirement and fail-closed conflict handling. Any earlier live observation is a **historical database observation; requires fresh read-only inventory**.

## 6. Proposed linkage contract

| Input | Class | Rule |
| --- | --- | --- |
| source_provider, candidate_match_id | required | Provider-scoped lineage only; not canonical proof. |
| competition, season, kickoff_at, source_timezone, home_team, away_team | required for non-external-ID automation | Approved mapping; kickoff must be absolute with interpretation. |
| source_match_id | optional/preferred | Auto-link only through proven provider-specific canonical external-ID mapping. |
| historical_match_identity, match_link_evidence | required evidence | Immutable evidence snapshot; not canonical assertion. |
| odds/bookmaker/market/selection/row order | forbidden for automation | Cannot establish match identity. |
| fuzzy name/date similarity | review evidence only | Never sets canonical_match_id. |

Automatic linkage requires exactly one candidate after reliable external-ID mapping (where present), exact approved competition/season, exact ordered teams, exact kickoff instant/timezone, and no conflict. Missing canonical match, uncertain timezone, reversal, unknown competition, multiple candidates or contradiction cannot auto-link.

`verified_unique` means one deterministic candidate; `unmatched` none; `ambiguous` multiple/orientation unresolved; `conflict` incompatible evidence or decision drift; `invalid_identity` malformed/missing evidence; `manual_review_required` has review evidence only. One observation maps to at most one canonical match. Candidate/source drift is conflict. Shared match evidence serves all bookmakers/selections. Ordinary writers cannot overwrite verified decisions; manual override needs separate authorization, actor/reason/time and superseding audit evidence.

## 7. Link audit storage options and FK strategy

| Option | Audit/replay/rollback | Assessment |
| --- | --- | --- |
| Mutable staging status only | Weak history; bookmaker rows may drift | Not recommended. |
| Append-only decision/audit table | Strong run scope, conflict and replay history | Viable. |
| Link table with FK plus audit history; staging snapshot retained | Strong integrity and separation | Recommended. |

Recommendation: **C — independent link table with FK to `matches(match_id)` plus append-only link-decision audit; staging retains candidate/evidence snapshots.** This is design only, not a migration request. It separates import from canonical decision and lets one decision serve many selections/bookmakers.

Do not add a staging FK until D4F-A proves target compatibility and D4F-B/C prove the decision model. Historical NULL stays NULL. A future FK should default to `ON DELETE RESTRICT`: correction needs audited supersession, not cascading evidence loss. Migration role owns DDL; linkage writer inserts bounded decisions; rollback is batch/run scoped, preserves audit, and never uses unconditional DELETE.

## 8. Recommended D4F phase decomposition

| Phase | Purpose | Reads | Writes | Separate authorization |
| --- | --- | --- | --- | --- |
| D4F-A — Read-only canonical identity inventory | Prove schema, constraints, coverage and overlap on one target | Metadata + minimal identity | None | Yes |
| D4F-B — Offline linkage contract | Pure function + synthetic fixtures | Code/synthetic | None | Yes |
| D4F-C — Controlled linkage persistence | Bounded decision/link persistence | Approved staging/link scope | Decision/link only | Yes |
| D4F-D — Real historical-data dry run | Hash-pinned source mapping/link report | Approved real files | None | Yes |
| D4F-E — Bounded real historical import | Small approved import after A–D | Approved source/evidence | Bounded staging/import only | Yes |

D4F-A requires a read-only role, `transaction_read_only=on`, statement timeout, fixed host/database/role allowlist, no temporary tables, no COPY/raw payload export, no credential output and no Docker/service start. Output is aggregated schema/types/constraints/indexes, coverage, duplicate external-ID and unique/ambiguous/unmatched counts only. D4F-B must test unique exact, unmatched, ambiguous, alias conflict, timezone conflict, reversal, replay idempotency and divergent decision conflict. D4F-C cannot write matches/canonical odds/import real data/training. D4F-E needs separately named target/hash/max files/max rows/expected accepted-quarantine/max verified links/transaction/backup/rollback/replay; no numeric cap is invented here.

## 9. Real-source readiness

Tracked CSV/JSONL files are fixtures; test code creates temporary sample manifests. The tracked local sample manifest says it is not externally licensed production data. The manifest contract requires local path, SHA-256, size, provider/provenance and rejects recovery/Git commit time as capture time. It does not prove an authoritative real file, location, hash, license, upstream provenance, fields or timezone semantics.

```text
REAL_SOURCE_LOCATION_NOT_PROVEN
REAL_SOURCE_HASHES_NOT_PROVEN
REAL_IMPORT_NOT_READY
```

The `38,616 accepted / 216 quarantined` and retained D4E `6 / 3` counts are historical evidence, not source inventory. Adapter policy does not infer opening/closing from ordinary/C columns or row order. Future sample: fixed hash, competition/season/time range and evidence-backed limits, including success/unmatched/ambiguous/quarantine examples; exact figures await inventory.

## 10. Roles, migration, rollback and training isolation

| Role | Allowed | Forbidden |
| --- | --- | --- |
| inventory_reader | Approved metadata/minimal identity SELECT | Writes, DDL, temp objects, COPY raw payload, quarantine. |
| linkage_writer | Bounded approved link/decision insert | matches, canonical odds, DELETE, DDL, verified/manual overwrite. |
| migration_role | Approved DDL window | Import/linkage business writes. |
| training_reader | Future approved accepted/canonical view | Quarantine, unresolved links, leaking closing odds. |

D4F-C must separately decide table/status/FK/index/partial-unique needs. Likely invariant: one active verified link per candidate/source identity with historical audit, not in-place update. Unexpected batch invariant failure rolls back its linkage transaction; valid row conflicts quarantine/audit. Existing staging docs prohibit training reads from quarantine. Legacy bookmaker readers demonstrate prematch leakage risk; training remains blocked until canonical linkage, provenance, snapshot-time semantics and quality acceptance are separately implemented/authorized.

## 11. Readiness matrix

| Domain | Current status | Evidence | Missing proof | Blocks which phase |
| ------ | -------------- | -------- | ------------- | ------------------ |
| candidate ID stability | bounded | Deterministic local linker | Canonical equivalence/collision scope | D4F-C/E |
| matches.match_id compatibility | not_proven | Static VARCHAR(50) PK | Live schema/value overlap | D4F-C/E |
| canonical schema freshness | historical_only | Init/migration SQL | Fresh inventory | D4F-C/E |
| team normalization | design_only | Local normalization/Recon concepts | Cross-source mapping | D4F-B/C/E |
| competition mapping | design_only | Fields exist | Canonical mapping | D4F-B/C/E |
| season mapping | bounded | Static format intent | Target format/coverage | D4F-A/C/E |
| kickoff/timezone semantics | bounded | Strict timestamp/evidence | Canonical-source mapping | D4F-B/C/E |
| home/away identity | bounded | Ordered/reversal rejection | Normalized canonical IDs | D4F-B/C/E |
| source external ID | bounded | Provider-scoped exact rule | Canonical mapping/uniqueness | D4F-A/C/E |
| link decision audit model | design_only | Existing evidence/replay | Approved model/migration | D4F-C |
| FK strategy | design_only | Existing FK/no-FK boundary | Inventory + migration design | D4F-C |
| role/grant | design_only | Static D4E/dev material | Target grants | D4F-A/C/E |
| migration need | design_only | Recommended separation | Approved DDL design | D4F-C |
| rollback | bounded | D4E transaction conflict | Target procedure | D4F-C/E |
| real source location | not_proven | Fixtures only | Approved location | D4F-D/E |
| source hashes | not_proven | Fixture hashes only | Immutable real manifest | D4F-D/E |
| provenance | not_proven | Manifest contract | License/upstream evidence | D4F-D/E |
| real sample envelope | blocked | No real inventory | Hash/scope/count evidence | D4F-D/E |
| training isolation | bounded | Quarantine separation/legacy risk | Quality/leakage gate | Training |
| explicit authorization | blocked | This review grants none | User phase approval | D4F-A–E |

## 12. Blocking conditions and exact next authorization package

Blocking conditions: no fresh canonical inventory; no approved team/competition/season/timezone mapping; no target grants; no link-audit migration; no real source location/hash/provenance; and no training quality/leakage acceptance.

Only this next package is proposed:

```text
M3-D4F-A — SELECT-only canonical identity inventory authorization
```

Future approval must name exact target; host/database/role; allowed SELECT objects/columns; statement timeout; maximum output; no raw payload; no temporary objects; no writes; and no Docker/service startup. It must require a read-only transaction, production exclusion, no COPY, no credential output and a stop condition. It is not executed by this review.

## 13. Explicit non-execution declaration

No database connection, Docker/Redis start, real source payload read, inventory, migration, canonical/staging/matches write, odds import, training, Issue #1793 comment change, PR-ready action or merge occurred. D4F implementation did not start.
