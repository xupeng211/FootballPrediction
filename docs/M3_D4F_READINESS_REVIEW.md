# M3-D4F Candidate-to-Canonical Linkage and Real Import Readiness Review

- lifecycle: current-state
- scope: current-state D4F read-only Football-Data-to-FotMob-candidate compatibility audit
- issue: #1793
- reviewed main baseline: 28714730b4356c5001565175990a5d0a34e24253
- historical D4F-A database access: local development `football_prediction_db_dev` service / effective database `football_db` only; `claude_reader` executed aggregate and schema `SELECT` queries inside `BEGIN READ ONLY` with `statement_timeout=10s`
- D4F service lifecycle: existing `dev` and development `db` services observed only; no service started or stopped. The normal documentation commit hook separately used the authorized Gatekeeper temporary `gatekeeper_cold_start_*` create/probe/rollback/drop blueprint; it did not inspect or change a business schema, business row, canonical match or persistent M3 sandbox.
- D4F-A provider/FotMob payload export/access: none; D4F-A used only the local
  database inventory. The later 9B offline phase re-read the three Git-history
  CSVs and recovered candidate metadata from repository-external temporary
  directories; neither phase exported a full payload or made a provider request.

## 1. Executive decision

Historical static readiness assessment:

```text
READY_FOR_D4F_READ_ONLY_INVENTORY_AUTHORIZATION
```

This historical static conclusion only said that a separately authorized,
bounded SELECT-only inventory package could be designed and reviewed. It never
authorized executing that inventory, implementation, migration, linkage write,
`canonical_match_id` write, matches/canonical-odds write, real import,
training, backtest or prediction.

Retained D4F-A development-database inventory decision:

```text
BLOCKED_CANONICAL_MATCH_COVERAGE
```

The original D4F-A path distinguished the two comparison sides: the
`football-data-csv` adapter produces source observations and the supplied
`--candidates` file represents the canonical side. The three immutable
Git-history CSVs produced 38,832 source observations from 1,180 raw rows; the
existing `buildSemanticMatchIdentity` contract reduced them to 892 unique
`canonical_match_identity` units (2022/2023: 380; 2023/2024: 380;
2024/2025: 132). Run A and Run B had the same business hash
`07e579ed21224c354c6dbcf9d44913521d94ce6e48ce24c17cbbd9bfd6b98b8b`.

The strictly read-only canonical inventory found 60 total `matches` rows but
zero Premier League/E0 rows in the three requested seasons. Its actual
population is 58 Ligue 1 2025/2026 rows plus two unrelated Segunda rows. The
canonical candidate input is therefore deterministically empty, and all 892
source match candidates terminate as `unmatched`/`no_local_candidate`.
No source alias, fuzzy rule, timezone tolerance, synthetic candidate ID or
linkage write was introduced.

Codex review P1 corrected an earlier wording mistake: absence of a source-side
`candidate_match_id` export is not a D4F-A blocker, because the source semantic
identity comes from the adapter and canonical candidates supply `id` or
`match_id`. The blocker is the verified zero-row canonical target coverage.

Current active ingestion convergence state is recorded at three distinct
levels:

```text
Official Architecture Decision Gate direction = redo source inventory strategy
User-selected implementation approach = RECOVER_EXISTING_ACQUISITION_ARCHITECTURE
Evidence-backed inventory outcome = FOTMOB_IDENTITY_BASELINE_REUSE_RECOMMENDED
```

`redo source inventory strategy` is the repository-approved formal direction.
Here it means inventorying and confirming already-known providers, retained
assets, execution evidence and reusable components; it does not mean discarding
the existing architecture and discovering providers from zero.

That retained database finding does not authorize an unbounded legacy restart,
network acquisition, a database write, a migration, real import, or any
roadmap D4F-B through D4F-E write activity. The later candidate-artifact audit
below also does not mark those roadmap phases complete.

## Outcome-gate declaration

### Classification and user-confirmed corrective boundary

```text
Authorization task type = docs-only
Ingestion convergence classification = evidence-backed inventory
Local Docker DB inventory = explicitly authorized
Database target = football_prediction_db_dev / football_db
Database role = claude_reader
Role-level table posture = SELECT-only; no inherited role, no schema CREATE
Transaction enforcement = BEGIN READ ONLY, transaction_read_only=on
Network acquisition = no
Database writes = no
Consecutive no-progress ingestion PR count = 0
Official Architecture Decision Gate direction = redo source inventory strategy
User-selected implementation approach = RECOVER_EXISTING_ACQUISITION_ARCHITECTURE
Evidence-backed inventory outcome = FOTMOB_IDENTITY_BASELINE_REUSE_RECOMMENDED
```

`docs-only` is the machine-readable file/authorization type because this PR
changes only the six named current-state documents. The inventory classification records the
separately authorized local evidence read; it does not bypass any write or
network boundary.

The six current-state documents are `docs/DATA_SOURCE_STRATEGY.md`, this
review, `docs/PROJECT_STATUS.md`, `docs/data/FOTMOB_CURRENT_STATE.md`,
`docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md` and
`docs/data/FOTMOB_RAW_PARSER_CONTRACT.md`.

The user explicitly confirmed one corrective update inside the already-open PR
#1805 to close the Ready-triggered Codex P1 findings and enter the required
Architecture Decision Gate. The later explicit D4F cross-source authorization
permitted only recovery of an existing candidate artifact and this bounded
offline audit; it did not authorize a database write or identity-policy change.

### Historical and current convergence transitions

Historical governance-boundary record from PR #1804:

```text
D4F_AUTHORIZATION_BOUNDARY_UNDEFINED
->
D4F_PHASE_BOUNDARY_DEFINED_AND_REVIEWABLE
```

It did not resolve a database, identity, mapping, real-source or training
blocker. The current active convergence transition is:

```text
D4F_PHASE_BOUNDARY_DEFINED_AND_REVIEWABLE
->
EXISTING_ACQUISITION_ASSETS_INVENTORIED
```

This is evidence-backed progress for the bounded local asset targets. It is not
a new acquisition, import, linkage write, migration, feature run, training or
prediction result.

### Target-state delta

```text
target_state_delta:
- total_targets: 50
- moved_to_clean_candidate: 32
- moved_to_rejected_mapping: 0
- moved_to_superseded_mapping: 0
- moved_to_eligible_for_re_acceptance_review: 0
- moved_to_needs_new_evidence: 10
- remain_suspended: 8
- still_blocked_pending_review: 0
- abandon_current_batch_candidate: 0
- no_progress_count: 0
```

The counting unit is a concrete historical FotMob mapping target, keyed by
exact `match_id`/`target_match_id` or exact FotMob external ID. Retained
database asset packages are explicitly excluded. The terminal classifications
reconcile as `32 + 10 + 8 = 50`: 32 exact L2V3BC targets later received
ADG59A canonical promotion and ADG59B source-controlled accepted/resolved
state; ten have only the L2V3BC `needs_new_evidence` result; and eight retain
the L2V3AT suspension because no exact later resolution exists.

The prior L2V3BC result triggered the no-progress stop rule when all 42 of its
targets were `needs_new_evidence`. The chronology now proves 32 concrete target
state changes through later, same-identity ADG59A/ADG59B artifacts. That is
target-level evidence progress—not an inference from retained database rows—so
`no_progress_count` recomputes to zero. `abandon_current_batch_candidate` is
zero because this bounded reconciliation found 32 clean candidates, while
retaining the unresolved 18 targets as non-clean.

The 50-target reconciliation is **FotMob mapping governance only**. It neither
defines nor filters the M3 Football-Data candidate population: that population
must come from actual offline Football-Data candidates accepted by the existing
M3 identity contract.

### Blockers not resolved

The following remain unresolved:

* ten concrete FotMob targets that still need new evidence and eight mappings/
  baselines that remain suspended;
* M3 candidate-to-`matches.match_id` compatibility and value overlap;
* team, competition, season and kickoff/timezone mappings;
* real source location, immutable hashes and provenance;
* real import envelope;
* training quality and leakage controls.

### Why this evidence-backed correction is material

No runtime behavior or business-data was changed. The local inventory did
evaluate retained database assets and confirmed the development schema, the
non-production target and the `claude_reader` SELECT-only posture.

The correction is material because it stops the unsafe automatic D4F-A path
after the second no-progress ingestion governance PR and records the required
Architecture Decision Gate.

It prevents documentation review from being misread as database authorization,
canonical-write authorization, real-import readiness or training readiness.

### Architecture Decision Gate

```text
triggered = yes
reason = two consecutive no-progress ingestion governance/review PRs
automatic next planning/review = prohibited without separate authorization
automatic further D4F-A = prohibited
formal decision = redo source inventory strategy
decision pending = no
implementation approach = RECOVER_EXISTING_ACQUISITION_ARCHITECTURE
inventory execution completed = local read-only asset inventory only
evidence-backed outcome = FOTMOB_IDENTITY_BASELINE_REUSE_RECOMMENDED
automatic network acquisition = prohibited
automatic database write = prohibited
```

The user-authorized D4F-A inventory removed the exact local target/read-only-role
and canonical-schema-freshness blockers for
`football_prediction_db_dev/football_db`. It also established a reusable FotMob
identity/raw baseline, but D4F-A itself did not prove M3 candidate compatibility,
provider provenance, a real historical odds file, or any cross-source linkage.
The later 9B offline comparison resolved only the candidate-compatibility part:
it verified the 888 exact / 4 isolated-kickoff-conflict partition without
changing the provenance, import or write boundaries.

Bounded D4F-A evidence includes tracked schema/migration review; current staging
contracts; candidate identity/linkage code and tests; D4E synthetic
persistent-sandbox historical evidence; existing source-of-truth documentation;
and the local read-only inventory. No external source payload or external
historical-data acquisition occurred in D4F-A. Section 9B records the later
repository-external, offline source-CSV and candidate-artifact comparison
separately.

```text
affected local asset package count = 4
reconciled concrete FotMob mapping target count = 50
target-level clean candidate count = 32
FORMAL_ARCHITECTURE_DECISION_GATE_DIRECTION:
redo source inventory strategy
IMPLEMENTATION_APPROACH:
RECOVER_EXISTING_ACQUISITION_ARCHITECTURE
EVIDENCE_BACKED_OUTCOME:
FOTMOB_IDENTITY_BASELINE_REUSE_RECOMMENDED
```

The selected source-inventory strategy is executed by recovering existing
acquisition architecture rather than rebuilding it. It preserves D4E sandbox
evidence, deletes or closes nothing, and does not authorize a legacy bulk
pipeline restart.

The other formal directions were evaluated and not selected:

* `abandon current batch`: not selected because 32 exact historical FotMob
  mapping targets have later source-controlled accepted/resolved evidence.
* `rebuild canonical identity pipeline`: not selected because the retained
  `matches`/`external_id` baseline has real-data proof.
* `switch data source / compare alternative source`: not selected; this work
  did not choose to replace or compare providers.
* `redesign FotMob identity mapping strategy`: not selected because no evidence
  identifies the retained FotMob identity design as needing redesign.

The formal decision is no longer pending. The bounded inventory used the
already-running local `football_prediction_db_dev` container only; it did not
select a provider switch, identity rebuild, FotMob redesign, unbounded legacy
restart, network exception or write exception.

## 2. Scope and non-goals

### D4F-A historical local-database phase

Git-tracked source, SQL, tests, ordinary docs and Git metadata were read. The
only D4F-A runtime target was the already-running local Docker PostgreSQL 15
container `football_prediction_db_dev`, labelled as the repository's
`footballprediction` development `db` service. Connection used the container
Unix socket with the declared `claude_reader` role and no password. Every query
ran in an independent `BEGIN READ ONLY` transaction with a 10-second statement
timeout, a 2-second lock timeout and a 15-second idle-in-transaction timeout;
`transaction_read_only` returned `on`. Its output was limited to schema,
aggregate counts, safe identity fields and at most five metadata-only samples
per table. The M3 persistent-sandbox volume was observed but was not started,
mounted or inspected.

### 9B current offline cross-source phase

The later 9B phase did not access a business database. It restored three
immutable Football-Data CSV blobs and read the recovered FotMob candidate
artifacts only from repository-external temporary directories. The existing
formal dry-run and pure identity/linking contracts ran in temporary development
containers with those read-only inputs. It did not read `.env`, a container
environment, credentials, a remote endpoint, Redis, browser, proxy or a full
raw/source payload; it did not start or stop a service. Both phases prohibited
migration, business writes, canonical-linkage persistence and payload export.

## 3. Evidence reviewed

| Area | Files | Evidence class |
| --- | --- | --- |
| Staging DDL | V26.8/V26.9 migrations | current static |
| Persistence boundary | odds_staging persistenceContracts/persistenceRepository | current static |
| Candidate linker | odds_staging matchLinker/contracts/pipeline and unit tests | current static |
| Canonical matches | deploy/docker/init_db.sql, V6.5, V12.4, match_repository.py | current static |
| Identity workflows | FotMob exporter, controlled seed/readiness, Recon | current static |
| D4E state/counts | PROJECT_STATUS, D4D/runbook docs, Issue #1793 | historical only |
| Local Docker target | `football_prediction_db_dev` / `football_db`, `claude_reader` | current read-only inventory |
| FotMob retained baseline | 58 strong harvested FotMob matches; 76 linked raw rows; 32 retained full raw-payload records | retained local data |
| football-data.co.uk retained odds | 2 rows, both linked to a synthetic match and `test_sample.html` | synthetic-only retained evidence |
| OddsPortal retained mapping/odds | both tables exist but contain zero rows | no retained execution evidence |
| M3 staging tables | four V26.8 tables absent from this development DB | blocked local target |

This is an **asset inventory summary**, not a target-state delta. Its evidence
levels describe retained data, code or staging availability; none of its four
asset packages is counted as a FotMob mapping target below.

### Local database key-table inventory

The inventory found one non-system schema, `public`, and 19 base tables. Row
counts below are bounded exact `COUNT(*)` results; catalog `n_live_tup` was not
used as a substitute because it was stale for populated tables. Time ranges are
UTC and intentionally omit raw payload values.

| Table / asset | Rows | Source or data version | Retained time range | Classification and identity result |
| --- | ---: | --- | --- | --- |
| `matches` | 60 | 58 strong `fotmob_live_fetch`/`V25.1`; 2 synthetic rows | real FotMob match dates 2025-08-15–2026-05-10 | 60/60 have `external_id`; 58 are `harvested`; external-ID duplicate groups: 0 |
| `raw_match_data` | 76 | `fotmob_live_v1` 58; HTML hydration 8; page-props 8; synthetic 2 | real FotMob collection 2026-05-14–2026-06-12 | 76/76 have a hash and an enforced FK to `matches`; 60 distinct `match_id`; raw orphans: 0 |
| `fotmob_raw_match_payloads` | 32 | `source=fotmob`, `adg60_raw_json_v1` | captured/ingested 2026-06-02 | retained full raw-payload assets: V26.5 requires complete unparsed `__NEXT_DATA__` JSON in non-null `next_data_json`, with raw-file locators, SHA-256 values, byte sizes, capture and ingestion metadata; complete `page_props_json` is retained when present but is nullable. Their `match_id` values overlap the retained `matches` and `raw_match_data` sets at match level, not as record-level payload-to-raw lineage |
| `bookmaker_odds_history` | 2 | Bet365 1x2; Pinnacle Asian Handicap; basename `test_sample.html` | collected 2026-05-01 | synthetic-only: both FK-link to the `manual_html_seed` synthetic match; one distinct `match_id` |
| `odds` | 0 | — | — | no retained OddsPortal market evidence |
| `matches_oddsportal_mapping` | 0 | — | — | no retained Recon mapping evidence |
| M3 V26.8 staging tables | absent | — | — | no M3 import-run/source-file/accepted/quarantine target in this development DB |

The historical #1487 controlled audit explicitly covers four retained rows
(4/4 parseable, SHA-valid and inner-`matchId` valid). The current
`fotmob_live_v1=58` inventory does not extend that full audit result or a
unique writer/run attribution to all 58 rows.

`football_match_targets` has 14 FotMob targets, but only one is marked
`raw_json_stored`; this is supporting discovery state, not an additional
provider target. `football_source_identities` has ten FotMob competition/team
identity rows. Neither table proves a historical football-data.co.uk or
OddsPortal import.

### Reverse-proven component matrix

| Component or retained asset | Database/static evidence | Proof level | Recovery treatment |
| --- | --- | --- | --- |
| FotMob `matches` identity baseline | 58 strong, harvested FotMob match rows; all 60 matches have external IDs; raw FK coverage is 60/60 | `PROVEN_BY_RETAINED_REAL_DATA` for the retained identity asset; historic writer invocation is not uniquely attributable | Reuse `matches.match_id`/`external_id` baseline; do not recreate identities |
| FotMob retained raw asset | 58 retained `fotmob_live_v1` rows with hashes and FK linkage; the historical four-row audit is separate evidence | `PROVEN_BY_RETAINED_REAL_DATA` for the retained data/identity outcome | Preserve and reuse the data/identity evidence; it is not a writer surface |
| Historical writer provenance | Retained rows have no unique run-level attribution to one named writer | `LEGACY_DATA_PRESENT_WRITER_UNCERTAIN` | Do not attribute all retained rows to a named script |
| `n3_live_fotmob_raw_retain.js` | Historical bounded N=3 network/UPSERT path; it is a legacy acquisition script, not a README canonical surface | `HISTORICAL_EVIDENCE_ONLY` / legacy | Never make it a canonical dependency, recovery contract or automatic execution path |
| Future FotMob writer | README declares production acquisition `Not yet established` | `NOT_YET_ESTABLISHED` | Establish and test a canonical `data-*`-gated surface only in a future milestone with separate network/write authorization |
| `DiscoveryService` / `FixtureRepository` | Current code persists `matches`, but retained rows carry no run-level writer provenance | `IMPLEMENTED_NOT_EXECUTION_PROVEN` for the exact component execution | Preserve and assess as the controlled L1 route; do not rewrite it |
| FotMob raw parser/detail components | 32 retained full raw-payload records establish a collection/persistence asset outcome, not a named parser invocation or parser validation | `IMPLEMENTED_NOT_EXECUTION_PROVEN` | May support a future bounded no-write offline parser/schema verification; no parser or network run now |
| football-data CSV adapter / `ExistingFotMobMatchResolver` | `csv_bulk_loader.js` has a resolver and bookmaker writer, but the only two retained rows are synthetic HTML samples | `IMPLEMENTED_NOT_EXECUTION_PROVEN` | Do not rewrite parser/resolver; first obtain a bounded real-file, no-write verification authorization |
| OddsPortal Recon / harvest pipeline | Mapping and market tables exist; both counts are zero; legacy SQL writers exist in the codebase | `NO_EVIDENCE` of retained execution | Keep legacy browser/harvest routes blocked; only safely adapt after separate evidence/authorization |
| M3 historical persistence repository | Historical D4E sandbox record is a 1/1/6/3 controlled synthetic write; the tables are absent here | `PROVEN_BY_SYNTHETIC_CONTROLLED_WRITE` | Reuse contract only; it does not prove real-provider ingestion or canonical linkage |

### FotMob mapping-target chronology reconciliation

The retained database assets above and historical mapping targets are different
objects. This static reconciliation used no database data as a mapping-state
shortcut. It read and compared the following chronological evidence:

| Phase | Date | Concrete target result |
| --- | --- | --- |
| L2V3AT | 2026-05-26 | 8 accepted mappings/baselines suspended; 42 distinct targets blocked pending review |
| L2V3BC | 2026-05-27 | the same 42 exact external IDs moved from `blocked_pending_review` to `needs_new_evidence`; no clean/reject/supersede/re-acceptance result |
| ADG59A | 2026-05-31 | 32 exact targets promoted with confirmed orientation/date/competition and no duplicate conflict |
| ADG59B | 2026-06-01 | those 32 exact targets recorded `accepted_source_controlled_only` and `resolved_source_controlled_only`; no DB/raw write and no raw-write readiness |
| later ADG60 artifacts | 2026-06-01–02 | reuse the same 32 `accepted_suspension_resolved` identities for preflight/no-write evidence; no later mapping reversal, rejection or contradiction found |

Canonical keys were not inferred from order or fuzzy fixture similarity. Exact
link counts are: 42 L2V3AT blocked `schedule_external_id` → L2V3BC
`external_id`; 32 L2V3BC `external_id` → ADG59B `corrected_hash_id`; and 32
ADG59A → ADG59B `target_match_id`. Exact fixture-tuple matching was not needed;
`unreconciled_identity_count = 0`. The eight L2V3AT suspended schedule IDs have
zero exact ADG59B matches and therefore remain suspended rather than being
silently merged into the 32 later targets.

Evidence labels used in the table are exact tracked paths:

- **L2V3AT** — `docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.accepted_mapping_baseline_suspension_result.phase521l2v3at.json`
- **L2V3BC** — `docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.bounded_expanded_blocked_target_review_result.phase521l2v3bc.json`
- **ADG59B** — `docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json`

<details>
<summary>All 50 concrete FotMob mapping targets and latest authoritative state</summary>

| Target key | Earlier state | Later same-identity evidence | Final taxonomy | Latest evidence |
| --- | --- | --- | --- | --- |
| `53_20252026_4830458` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830459` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830460` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830461` | `accepted_active` → `suspended` | no exact ADG59 target | `remain_suspended` | L2V3AT |
| `53_20252026_4830462` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830463` | `accepted_active` → `suspended` | no exact ADG59 target | `remain_suspended` | L2V3AT |
| `53_20252026_4830464` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830465` | `accepted_active` → `suspended` | no exact ADG59 target | `remain_suspended` | L2V3AT |
| `53_20252026_4830466` | `accepted_active` → `suspended` | no exact ADG59 target | `remain_suspended` | L2V3AT |
| `53_20252026_4830467` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830468` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830469` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830470` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830471` | `blocked_pending_review` → `needs_new_evidence` | no exact ADG59 target | `needs_new_evidence` | L2V3BC |
| `53_20252026_4830472` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830473` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830474` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830475` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830476` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830477` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830478` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830479` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830480` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830481` | `accepted_active` → `suspended` | no exact ADG59 target | `remain_suspended` | L2V3AT |
| `53_20252026_4830482` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830483` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830484` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830485` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830486` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830487` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830488` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830489` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830490` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830491` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830492` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830493` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830494` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830495` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830496` | `accepted_active` → `suspended` | no exact ADG59 target | `remain_suspended` | L2V3AT |
| `53_20252026_4830497` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830498` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830499` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830500` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830501` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830502` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830505` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830507` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830508` | `accepted_active` → `suspended` | no exact ADG59 target | `remain_suspended` | L2V3AT |
| `53_20252026_4830510` | `blocked_pending_review` → `needs_new_evidence` | ADG59A promotion; ADG59B accepted/resolved | `clean_candidate` | ADG59B |
| `53_20252026_4830511` | `accepted_active` → `suspended` | no exact ADG59 target | `remain_suspended` | L2V3AT |

</details>

`clean_candidate` here means identity/source/baseline evidence is sufficient
for a later **FotMob mapping-governance** candidate pool only. It is neither
raw-write authorization nor M3 candidate-to-canonical compatibility proof. The
32 clean classifications are not double-counted as `superseded_mapping`: their
earlier state was blocked or needs-evidence, not an accepted mapping replaced
by a newer mapping.

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

The local inventory now confirms `matches.match_id` as the retained FotMob
identity baseline: all 60 rows have an `external_id`; 58 are
`fotmob_live_fetch` with `strong` evidence and `harvested` status. All 76
`raw_match_data` rows link to `matches` through the enforced FK, with 60
distinct match IDs and no raw orphan; `fotmob_live_v1` accounts for 58 rows.
The 32 `fotmob_raw_match_payloads` rows are retained full FotMob raw-payload
assets, not metadata-only rows. V26.5 declares non-null `next_data_json` as
complete, unparsed `__NEXT_DATA__` JSON and also retains raw-payload file
locators, SHA-256 values, byte sizes, capture timestamps and ingestion
metadata. It can retain complete `page_props_json` when present, but that
column is nullable; this inventory makes no 32/32 pageProps or parser-validation
claim. These offline assets may support a future separately authorized
no-write parser/schema verification without a new fetch; no parser execution,
raw JSON print or raw JSON export occurred here.

Their `match_id` values overlap the retained `matches` and `raw_match_data`
sets at match level. The payload table has neither a foreign key nor a unique
record identifier that points to a specific `raw_match_data` row; because
multiple raw versions may exist for one match, this inventory does not prove
one-to-one or record-level payload-to-raw lineage. This precision does not
change the retained FotMob identity baseline, the enforced
`raw_match_data`-to-`matches` FK linkage, or the separately reconciled
target-level classifications above. It does not authorize a fetch or write.
MatchRepository, FotMob seed/discovery, raw-data preflight, Recon and legacy
OddsPortal paths remain source-specific, DB/network/write-capable or historical
paths, not D4F executors.

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

The D4F-A preflight restored the following Git-history blobs byte-for-byte to a
repository-external temporary directory. No CSV was moved, normalized,
committed or emitted from the repository. Header checks found no empty or
duplicate names; all three files are ASCII CSV with LF endings. The table is a
safe metadata summary, not a source-data export.

| Git path | immutable source commit / blob | SHA-256 / bytes | raw CSV rows and scope |
| --- | --- | --- | --- |
| `data/external/odds/raw_odds_2223.csv` | `faa3f7ab031bb6428f0390b3f833ce16addb1f0a` / `d938f7b58fd92aafefa63effe3548afb27b17188` | `e51361323bcdcdcec2faf8f58e7bcfc4f5b193ed6017b284c71538ed70d98ea2` / 175,799 | 380; 106 columns; `Div=E0`; `Date`, `Time`, `HomeTeam`, `AwayTeam`; 2022/2023 by the current season rule. |
| `data/external/odds/raw_odds_2324.csv` | `faa3f7ab031bb6428f0390b3f833ce16addb1f0a` / `5bc9399ba12ef3ca732477dc207b52ca09edd00e` | `0b669038e94bf305603d841f02006c7d35ebd41c8722c76e479f2393079b995f` / 171,815 | 380; 106 columns; `Div=E0`; `Date`, `Time`, `HomeTeam`, `AwayTeam`; 2023/2024 by the current season rule. |
| `data/real_odds_raw.csv` | `c8e4be00bb13a1f3559f02696cb23720363ce2c0` / `97a199ffc44a030a632b06ca33f31c3b3904aa6a` | `045cb84f6a75dc947e5aa5c4170c844237c1dcd489ae3264a795f39a20114361` / 219,137 | 420; 133 columns; `Div=E0`; `match_date`, `Time`, `home_team`, `away_team`, `Season`; 132 / 156 / 132 rows for 22/23 / 23/24 / 24/25. |

This proves repository provenance, Git object identity and file integrity for
the bounded offline preflight inputs. It does not prove the original upstream
capture time, upstream provider provenance, license, source authority or a
real import envelope; those facts remain explicitly unverified under the
`historical_git_recovery` manifest contract.

```text
REPOSITORY_HISTORICAL_INPUTS_REVERIFIED
UPSTREAM_SOURCE_PROVENANCE_UNVERIFIED
REAL_IMPORT_NOT_READY
```

The `38,616 accepted / 216 quarantined` and retained D4E `6 / 3` counts are historical evidence, not the D4F audit population. Adapter policy does not infer opening/closing from ordinary/C columns or row order. The D4F-A development-database inventory used an empty canonical candidate set, which explains its historical `match_link_unmatched` result. It is not the later cross-source result recorded next.

## 9A. D4F-A read-only execution evidence

| Item | Verified result |
| --- | --- |
| formal source entrypoint | `npm run odds:staging:dry-run` with `football-data-csv@1.2.0`, historical-Git-recovery manifest, fixed E0/Premier League + three-season + exact-alias + Europe/London contract |
| input population | 1,180 raw CSV rows: 380 + 380 + 420; no extra competition or season |
| observation unit | 38,832 Football-Data odds observations: 13,680 + 12,546 + 12,606 |
| candidate deduplication unit | current `buildSemanticMatchIdentity` output where `identity_mode=canonical_match_identity`; no synthetic source ID |
| unique source candidates | 892: 2022/2023 380, 2023/2024 380, 2024/2025 132 |
| reproducibility | Run A = Run B: same source fingerprints, counts and SHA-256 business hash `07e579ed21224c354c6dbcf9d44913521d94ce6e48ce24c17cbbd9bfd6b98b8b` |
| source validity | 0 invalid semantic identities; no non-link quarantine reason; all 38,832 only have `match_link_unmatched` because the canonical candidate set is empty |
| database identity | service `football_prediction_db_dev`; database `football_db`; PostgreSQL 15.17; `current_user=session_user=claude_reader`; `transaction_read_only=on`; no superuser/create-role/create-db privilege; `CONNECT`, `public` `USAGE` and `matches` `SELECT` verified |
| inspected canonical schema | `matches.match_id`, `external_id`, `league_name`, `season`, `home_team`, `away_team`, `match_date`, status/source fields; `information_schema` and PostgreSQL role catalog only; no raw payload table queried |
| relevant canonical population | 0 Premier League/E0 rows for 2022/2023–2024/2025; consequently 0 with/without external identity, kickoff, team coverage, duplicate identity or status/time anomaly |
| terminal arithmetic | exact unique 0 + unmatched 892 + ambiguous 0 + team conflict 0 + kickoff conflict 0 + competition/season conflict 0 + incomplete canonical 0 + invalid source 0 = 892 |
| time-difference buckets | no candidate pair exists: exact timestamp 0; timezone-normalized exact 0; 15-minute 0; 30-minute 0; larger 0; missing-kickoff comparison 0 |

The audit used no `SELECT FOR UPDATE`, storage function, temporary table,
`raw_match_data`/payload read, migration or business-table write. Bounded
exception samples are empty because there are no relevant canonical rows; no
raw payload or large row dump was emitted.

## 9B. D4F offline Football-Data-to-FotMob candidate compatibility audit

This is a read-only extension of the evidence package, not a claim that the
empty local development `matches` inventory has changed. It reused the current
formal `football-data-csv@1.2.0` adapter, `buildSemanticMatchIdentity` and
`matchLinker` implementation without adding aliases, fuzzy matching, a time
tolerance, source-side candidate export, or linkage persistence.

### Candidate artifact provenance and population

The bounded artifact search found the two PR #1796 exporter outputs in the
repository-external current project data directory
`FootballPrediction.external-data/m3-d2b`. Both are ordinary files, not
symlinks; each has schema `candidate-match-identity/v1`, 1,140 candidates,
380 candidates in each requested season, 1,140 unique candidate IDs, 1,140
unique FotMob source IDs and zero missing critical fields. Current exporter
validation and `computeBusinessContentHash` reconfirmed the historical
business hash in both runs:

```text
eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f
```

| Artifact | Candidate JSON SHA-256 / bytes | Summary JSON SHA-256 / bytes |
| --- | --- | --- |
| recovered run1 | `262949ac986eab1cea0ae8830c9f495b24809724f4aff2f67f6746a43877833b` / 345,027 | `adafba212227010059f9f6ec7be283bc60de0d545c5056639e1ef09bbb9b51a2` / 416 |
| recovered run2 | `6d06078cef331516ee1bf909eed927b17958517aa382c70fd0a057b9c20e118a` / 345,027 | `4a20b24513363bfdef8d2363cae3fe49e98dbc7a9bf4eadb2a047d2bae33ef8e` / 416 |

The JSON byte hashes differ only because the exporter records different
`extracted_at` metadata; their candidate business content is identical. A
recovery was therefore sufficient and the bounded network exporter was not
run: FotMob/provider requests = 0, HTTP responses = 0, 403 = 0, 429 = 0,
captcha/access-wall events = 0 and retries = 0.

### Source population and reproducibility

The three immutable Football-Data Git blobs in section 9 were restored
byte-for-byte to a repository-external `mktemp` directory. Their current
fingerprints, byte sizes, ASCII/LF encoding, headers and 380 + 380 + 420 raw
row counts revalidated. No raw CSV was changed, committed or retained in the
repository.

| Source input unit | `raw_odds_2223` | `raw_odds_2324` | `real_odds_raw` (mixed seasons) | Total |
| --- | ---: | ---: | ---: | ---: |
| raw Football-Data CSV rows | 380 | 380 | 420 | 1,180 |
| Football-Data odds observations | 13,680 | 12,546 | 12,606 | 38,832 |

| Match-candidate unit | 2022/2023 | 2023/2024 | 2024/2025 | Total |
| --- | ---: | ---: | ---: | ---: |
| unique semantic match candidates | 380 | 380 | 132 | 892 |
| FotMob canonical candidates | 380 | 380 | 380 | 1,140 |

The semantic unit remains exactly the current
`buildSemanticMatchIdentity` value with
`identity_mode=canonical_match_identity`; no source `candidate_match_id` was
invented. The source business hash was recomputed as:

```text
07e579ed21224c354c6dbcf9d44913521d94ce6e48ce24c17cbbd9bfd6b98b8b
```

Independent offline runs A and B used the same three CSV SHA-256 inputs and
the same recovered run1 candidate file. They produced identical input hashes,
terminal classifications, matched FotMob IDs, bounded samples and result hash:

```text
fee4d02ae93d2370ba9a282ef546cafa097c8f350a402f19afab39dc2f2040fb
```

### Matching contract and terminal arithmetic

The source adapter applies only the existing 12 source-scoped exact
Football-Data aliases before comparison and derives an absolute kickoff under
the existing `Europe/London` interpretation. Across the 1,180 raw rows, 798
of 2,360 raw team fields used that approved alias contract (598 rows had at
least one such field); no alias was added. The linker then requires ordered
home/away, competition, season and identical absolute kickoff instants. Its
approved non-zero kickoff tolerance is therefore none.

| Terminal category | Count |
| --- | ---: |
| `exact_unique_match` | 888 |
| `kickoff_conflict` | 4 |
| `unmatched` | 0 |
| `ambiguous_multiple_matches` | 0 |
| `team_identity_conflict` | 0 |
| `competition_or_season_conflict` | 0 |
| `canonical_candidate_incomplete` | 0 |
| `source_candidate_invalid` | 0 |
| **terminal total** | **892** |

Per season, the result is 377 exact + 3 kickoff conflicts for 2022/2023,
379 exact + 1 kickoff conflict for 2023/2024, and 132 exact for 2024/2025.
The 888 exact candidates use 888 distinct FotMob IDs; 252 of the 1,140 FotMob
candidates are outside the 892-source audit population, and no FotMob
candidate is used by more than one source candidate.

Time buckets are 888 exact timestamps, zero timezone-normalized-only exact,
zero within a non-zero tolerance, three 15-minute conflicts, one 30-minute
conflict, zero larger conflicts and zero missing-kickoff comparisons. There is
no unapproved name difference, missing team identity or same-kickoff home/away
reversal evidence.

The four bounded, isolated conflict samples are all source-derived kickoff
times earlier than the corresponding canonical candidate; no candidate was
selected or written for them:

| Season | Ordered teams | Source semantic key | FotMob candidate ID | Delta |
| --- | --- | --- | --- | ---: |
| 2022/2023 | Tottenham Hotspur — AFC Bournemouth | `5960def80d753312601cc3f4835d9a7c1eca39bbff6a099a44a73484f0a0e430` | `47_20222023_3901239` | -15 min |
| 2023/2024 | Arsenal — Nottingham Forest | `412738104d78683b6df16ee852f2ca1bfe92313d41b1c9526957ef2020d9ccde` | `47_20232024_4193451` | -30 min |
| 2022/2023 | Fulham — Tottenham Hotspur | `1c415b70a945a704415e35c31106ce4c126450e3e7fdf32f3fd6444491f35d8a` | `47_20222023_3901135` | -15 min |
| 2022/2023 | Crystal Palace — West Ham United | `591296723603698c7bac5ba0036df8c03cfd8deffe2995c3c976dd57aa6bfd3b` | `47_20222023_3901266` | -15 min |

### Current decision

```text
SUPERSEDED_BY_2026_07_29_CANONICAL_INVENTORY_WRITE_DESIGN_REVIEW
```

This historical result authorized the completed design review recorded in
section 15. It did not authorize a canonical inventory, `matches`,
`external_id`, `canonical_match_id`, historical odds staging, migrations,
training, backtest or prediction. The current design still keeps the four
`kickoff_conflict` identities isolated from linkage until separate evidence
and an explicit authorization exist.

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
| source semantic identity | verified_for_read_only_audit | Current adapter + `buildSemanticMatchIdentity` produced 892 unique E0 match units reproducibly | None for this audit; real-import acceptance remains separate | D4F-D/E |
| canonical candidate coverage | verified_for_read_only_audit | Recovered FotMob artifact: 1,140 complete candidates; 888 exact + 4 isolated kickoff conflicts | Future writer design and separately authorized execution | Future canonical inventory write |
| local canonical database coverage | zero_for_scope | `matches` has zero Premier League/E0 rows in 2022/2023–2024/2025 | A separately authorized canonical database inventory/write decision | D4F-C/E |
| canonical schema freshness | bounded | Current local development schema inventory | Approved target-specific inventory elsewhere | D4F-C/E |
| team normalization | verified_for_offline_audit | Existing 12 source-scoped exact aliases; no unapproved difference | Future writer implementation must preserve this contract | Future canonical inventory write |
| competition mapping | verified_for_offline_audit | E0 → Premier League on both compared populations | Future writer implementation | Future canonical inventory write |
| season mapping | verified_for_offline_audit | Exact `2022/2023`–`2024/2025` scope on both populations | Future writer implementation | Future canonical inventory write |
| kickoff/timezone semantics | bounded_conflicts | Europe/London source interpretation; 888 exact, 4 isolated 15/30-minute conflicts | Conflict evidence or explicit policy decision; no tolerance expansion | Future canonical inventory write |
| home/away identity | verified_for_offline_audit | Ordered home/away; no same-kickoff reversal | Future writer implementation | Future canonical inventory write |
| source external ID | bounded | 60 populated `matches.external_id`; zero duplicate groups in this DB | M3 provider mapping/uniqueness | D4F-C/E |
| link decision audit model | design_only | Existing evidence/replay | Approved model/migration | D4F-C |
| FK strategy | design_only | Existing FK/no-FK boundary | Inventory + migration design | D4F-C |
| role/grant | bounded | `claude_reader` local socket access; SELECT-only listed grants; no membership/CREATE | Target grants outside this dev DB | D4F-C/E |
| migration need | design_only | Recommended separation | Approved DDL design | D4F-C |
| rollback | bounded | D4E transaction conflict | Target procedure | D4F-C/E |
| repository historical inputs | verified_for_read_only_audit | Three immutable Git-history blobs restored outside the repository with SHA-256, size, header, scope, two deterministic runs and 892 semantic units | Upstream capture/provider/license proof for real import | D4F-D/E |
| upstream provenance | not_proven | Git history cannot prove original capture/provider/license semantics | Approved upstream provenance and import envelope | D4F-D/E |
| provenance | not_proven | Manifest contract | License/upstream evidence | D4F-D/E |
| real sample envelope | blocked | No real inventory | Hash/scope/count evidence | D4F-D/E |
| training isolation | bounded | Quarantine separation/legacy risk | Quality/leakage gate | Training |
| explicit authorization | blocked | This review grants none | User phase approval | D4F-A–E |

## 12. Blocking conditions and current decision boundary

The local development database still contains zero Premier League/E0
`matches` rows for the requested seasons; that database fact has not changed.
It no longer blocks the read-only cross-source audit because the verified
FotMob candidate artifact supplied its canonical comparison side. Remaining
boundaries are the four isolated kickoff conflicts, unverified original
upstream provenance/import semantics, absent retained OddsPortal evidence,
unavailable M3 staging tables in this development DB, and training
quality/leakage acceptance.

The formal `redo source inventory strategy` permits recovery planning from the
retained FotMob baseline as canonical-match comparison evidence. It does not
make FotMob mapping targets the M3 candidate source: an M3 audit population
must instead come from actual offline Football-Data candidates under the
current Premier League `2022/2023`–`2024/2025` identity contract. Any next
network fetch, database write, M3 staging migration, linkage decision or real
import still needs a separate authorization.

## 13. Explicit non-execution declaration

The D4F-A database inventory opened a strictly read-only local PostgreSQL
session. The later cross-source audit did not access any business database at
all: business DB reads = 0 and business DB writes = 0. It ran the formal
offline staging CLI and current pure contracts in temporary containers with
repository-external inputs only. Neither audit ran a migration, wrote a
business row or schema, wrote `canonical_match_id`, accessed
`raw_match_data`/payloads, started or stopped a service, stored a raw payload,
or invoked a provider/browser request. The normal commit hook may use only the
separately authorized Gatekeeper `gatekeeper_cold_start_*` temporary
create/probe/rollback/drop blueprint; it does not target a persistent business
table or M3 sandbox. Roadmap D4F-B through D4F-E write activity has not
started.

## 14. Next recommended task

The planned design review is completed in section 15. Do not start
automatically. The next separately authorized task may be an implementation
review for the fail-closed writer, status-complete input contract and isolated
schema/lineage migration plan. It must not execute a canonical write, linkage
persistence, real import, migration, training, backtest or prediction.


## 15. Canonical inventory write design review — 2026-07-29

### Decision

~~~text
Design decision = READY_FOR_CANONICAL_INVENTORY_WRITER_IMPLEMENTATION_REVIEW
Recommended future canonical population = 1,140 FotMob Premier League candidates
Canonical inventory / Football-Data linkage / historical-odds staging = distinct stages and authorizations
Recovered candidate artifact v1 write eligibility = blocked (status absent)
~~~

Earlier current-state wording that described only the 888 exact links as a
possible inventory is superseded. These are three different objects:

| Object | Count | Current/future treatment |
| --- | ---: | --- |
| FotMob canonical candidates | 1,140 (380 / 380 / 380) | The bounded inventory population after write-input preflight. |
| Football-Data source identities | 892 (380 / 380 / 132) | Historical odds source identities; they do not create canonical rows. |
| Source-to-canonical links | 888 exact + 4 conflicts | A later, separately authorized linkage population. |

FotMob is the documented primary fixture and canonical-match-identity source.
Its stable ID, absolute kickoff, ordered home/away, competition, season and
provider status are canonical attributes. Football-Data is authoritative only
for historical source identity/observations; its timestamp never overwrites a
FotMob canonical kickoff.

The selected population is all 1,140 FotMob candidates, not 888 or 892:

| Option | Decision | Reason |
| --- | --- | --- |
| 888 exact only | Not selected | Couples canonical existence to one downstream source and excludes 252 in-scope FotMob fixtures. |
| 1,140 FotMob candidates; then 888 links | Selected | Implements the primary-source policy and separates canonical creation from linkage. |
| 888 then expansion | Not selected | Adds a second inventory campaign while preserving the same incorrect coupling. |

The 252 unused candidates are canonical-only/unlinked, not invalid. The four
conflicting candidates may enter inventory if their FotMob input is valid but
remain linkage-quarantine/no-link: Tottenham Hotspur—AFC Bournemouth
(47_20222023_3901239, 15m), Fulham—Tottenham Hotspur
(47_20222023_3901135, 15m), Crystal Palace—West Ham United
(47_20222023_3901266, 15m), and Arsenal—Nottingham Forest
(47_20232024_4193451, 30m). No alias, fuzzy comparison, home/away reversal,
timezone-policy or tolerance change is proposed. Resolving them requires
separately authorized, source-bound official scheduling evidence.

### Read-only schema and existing writer evidence

On 2026-07-29 the already-running development Compose db service was queried
only through Unix-socket football_db as claude_reader. Every query used BEGIN
READ ONLY, statement_timeout=10s, lock_timeout=2s and
idle_in_transaction_session_timeout=15s. PostgreSQL reported 15.17,
current_user=session_user=claude_reader and transaction_read_only=on. The role
has CONNECT, public USAGE and matches SELECT only; CREATE, INSERT, UPDATE and
DELETE are false. No FOR UPDATE, write-effect function, raw-payload read, DDL
or business write occurred.

matches has primary key match_id; nullable external_id/match_date/status and
required league_name/season/home_team/away_team. It has season, lowercase
status, pipeline/source/governance and score checks, but no provider-scoped
external-ID unique constraint, ordered business-identity constraint, import
lineage or foreign key. Its update triggers derive is_finished from status =
finished and update updated_at. It contains 60 rows (58 Ligue 1 2025/2026, one
Segunda 2024/2025, one Segunda División 2025/2026), no target EPL/E0 rows and
no current duplicate external/business identity. Existing values follow
match_id=<leagueId>_<seasonWithoutSlash>_<FotMobId> with numeric external_id,
but data_source is historically mixed (fotmob, manual_html_seed,
local_finished_csv); it cannot safely supply the provider namespace.

FixtureRepository.persist and the Python collector are not usable for M3:
they use INSERT ... ON CONFLICT DO UPDATE and can replace identity/business
fields or touch updated_at; recon code also has intentional arbitration/rebind
paths. The future path requires a new explicit, fail-closed writer that does
not call either generic repository. The D4E persistent sandbox is also not a
target: it is dedicated to V26.8/V26.9 and retains 1 / 1 / 6 / 3 synthetic
evidence. Development remains read-only evidence; the future persistent target
is a dedicated canonical sandbox after disposable PostgreSQL proof.

### Required input, schema and lineage contract

The recovered ordinary v1 artifact has SHA-256
262949ac986eab1cea0ae8830c9f495b24809724f4aff2f67f6746a43877833b and
business hash eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f.
Its 1,140 candidates have only id, source_provider, source_match_id,
competition, season, home_team, away_team and kickoff_at; status is absent
from 1,140/1,140. It remains valid identity evidence, but the writer must
reject it rather than guess finished/scheduled.

A future v2 artifact must be repository-external, an ordinary non-symlink,
immutable through the run, SHA-256/byte-size/business-hash bound, and include
schema version, provenance, authorization phrase, expected total/seasons and
provider/competition scope. Every candidate must include stable numeric FotMob
ID, deterministic candidate ID, provider, competition, season, ordered teams,
strict absolute kickoff, provider status and a versioned status mapping.
Population preflight requires exactly 1,140 and 380/380/380, target scope only,
unique candidate/provider/ordered-business identities, no incomplete or
abandoned candidate and no unknown semantic fields. FotMob supplies status; the
future implementation retains it and rejects unmapped values. A status-complete
artifact needs separate acquisition or equally immutable recovered evidence;
this design authorizes neither.

A separately authorized migration implementation/review is required and must
preflight old rows without rewriting them. Its minimum design is:
1. retain matches.match_id as candidate ID and numeric FotMob ID in external_id;
2. add nullable canonical_provider (initial value fotmob), not mixed data_source;
3. add partial unique constraints on (canonical_provider, external_id) and
   ordered (canonical_provider, league_name, season, home_team, away_team,
   match_date);
4. add import-run, source-artifact and match-lineage tables with artifact
   SHA-256/business hash, candidate/provider ID, immutable fingerprint, run and
   code revision; and
5. preserve provider status separately from application-status mapping.

### Idempotency, transaction, permission and recovery design

Every candidate must end exactly once as inserted, exact_duplicate,
already_present_equivalent, conflict_external_id, conflict_business_identity,
conflict_kickoff, conflict_home_away, conflict_competition, conflict_season,
invalid_candidate or out_of_scope. Equal provider ID and immutable fingerprint
is zero-delta. A changed same-provider field, different provider ID for one
ordered business identity, input duplicate, or scope/hash/status failure fails
closed: no update, no first-row-wins, no partial commit and at most 20 evidence
samples per class.

The recommended unit is one all-1,140 transaction: prove target/schema/role and
baseline fingerprint; set timeouts; obtain a fixed pg_try_advisory_xact_lock;
re-read and preflight; insert only proven-new canonical/lineage rows; verify
1,140 and 380/380/380, provider/business uniqueness and fingerprints; then
commit. Lock busy, conflict, count mismatch or unexpected ON CONFLICT DO
NOTHING rolls back. No temporary table, COPY, update-on-conflict or
input-changing retry is permitted.

The writer role needs only CONNECT, schema USAGE, explicit-table SELECT/INSERT
and required sequence USAGE. It receives no UPDATE, DELETE, DDL, CREATE,
TRUNCATE, broad schema privilege, role membership or implicit function
privilege. Separate owner/migrator and read-only verifier roles are required.
Before a real write: prove target/schema/ACL/baseline; make a custom-format
repository-external backup; restore it to a fresh disposable clone; verify it.
Transaction rollback is failure recovery before commit; a post-commit reversal
is an authorization-gated owner restore, not manual deletion by remembered IDs.

### Gates and authorization separation

| Gate | Future activity | Required proof | Excludes |
| --- | --- | --- | --- |
| 1 | Disposable PostgreSQL proof | Insert/replay zero delta, divergent rollback, lock and backup/restore. | Persistent DB, real write, provider request. |
| 2 | Dedicated canonical sandbox | Least privilege, lineage and restore rehearsal; synthetic then approved small real sample. | Development DB, D4E sandbox, linkage, odds staging. |
| 3 | Bounded real inventory | Hash-bound status-complete input, backup and post-write verification; begin with 1 or 10 then reassess. | Automatic 1,140 write, network expansion, linkage. |
| 4 | Full inventory verification | 1,140/380/380/380 and identity/kickoff/status/lineage completeness. | Linkage and odds import. |
| 5 | Separate linkage review | 888 exact only; four conflicts stay quarantine. | Canonical creation and staging. |

Canonical inventory, source linkage and historical odds staging use separate
transactions, executors, import-run identities, roles and authorization phrases.
D4E canonical_match_id remains NULL. FotMob recovered-file identity supports
this design but not current endpoint/capture/licence/write-status evidence;
Football-Data Git provenance is separately required for linkage/odds import.

No provider request, browser action, migration, database/schema/row write,
canonical/linkage/staging/import, persistent M3 sandbox action, raw-payload
storage, training, backtest or prediction occurred. A future separate task may
implement/test the writer, v2 artifact contract and isolated migration plan; it
may not execute a canonical or linkage write without another explicit
authorization.
