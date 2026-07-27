# M3-D4F Candidate-to-Canonical Linkage and Real Import Readiness Review

- lifecycle: current-state
- scope: documentation-only evidence-backed local inventory review
- issue: #1793
- reviewed main baseline: 535e144cadc7019b8e86fc62e6e2bb1f4216a8c8
- database access: one explicitly authorized local Docker PostgreSQL read-only inventory
- Docker/Redis access: Docker metadata and the running local PostgreSQL container only; Redis not accessed
- full real source payload export/access: none

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

This does not authorize an unbounded legacy restart, network acquisition, a
database write, a migration, a real import, or D4F-B through D4F-E. It only
authorized the bounded local inventory recorded below.

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
changes only the five named current-state documents. The inventory classification records the
separately authorized local evidence read; it does not bypass any write or
network boundary.

The user explicitly confirmed one corrective update inside the already-open PR
#1805 to close the Ready-triggered Codex P1 findings and enter the required
Architecture Decision Gate. The user did not authorize an exception to continue
D4F-A after two no-progress ingestion governance PRs.

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

The user-authorized inventory removed the exact local target/read-only-role and
canonical-schema-freshness blockers for `football_prediction_db_dev/football_db`.
It also established a reusable FotMob identity/raw baseline, but it did not
prove M3 candidate compatibility, provider provenance, a real historical odds
file, or any cross-source linkage.

Bounded evidence includes tracked schema/migration review; current staging
contracts; candidate identity/linkage code and tests; D4E synthetic
persistent-sandbox historical evidence; existing source-of-truth documentation;
and this local read-only inventory. No external source payload or external
historical-data acquisition occurred.

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

Git-tracked source, SQL, tests, ordinary docs and Git metadata were read. The
only runtime target was the already-running local Docker PostgreSQL 15 container
`football_prediction_db_dev`, labelled as the repository's `footballprediction`
development `db` service. Connection used the container Unix socket with the
declared `claude_reader` role and no password. Every query ran in an independent
`BEGIN READ ONLY` transaction with a 10-second statement timeout, a 2-second
lock timeout and a 15-second idle-in-transaction timeout; `transaction_read_only`
returned `on`. No `.env`, container environment, credential, remote endpoint,
Redis, browser, proxy, migration, write or full raw/source payload was
read/exported. Output was limited to schema, aggregate counts, safe identity
fields and at most five metadata-only samples per table. The M3 persistent-sandbox volume was observed
but has no running container and was not started, mounted or inspected.

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
| matches.match_id compatibility | bounded | Local `matches` PK/external-ID/raw-FK inventory | M3 candidate equivalence | D4F-C/E |
| canonical schema freshness | bounded | Current local development schema inventory | Approved target-specific inventory elsewhere | D4F-C/E |
| team normalization | design_only | Local normalization/Recon concepts | Cross-source mapping | D4F-B/C/E |
| competition mapping | design_only | Fields exist | Canonical mapping | D4F-B/C/E |
| season mapping | bounded | Static format intent | Target format/coverage | D4F-A/C/E |
| kickoff/timezone semantics | bounded | Strict timestamp/evidence | Canonical-source mapping | D4F-B/C/E |
| home/away identity | bounded | Ordered/reversal rejection | Normalized canonical IDs | D4F-B/C/E |
| source external ID | bounded | 60 populated `matches.external_id`; zero duplicate groups in this DB | M3 provider mapping/uniqueness | D4F-C/E |
| link decision audit model | design_only | Existing evidence/replay | Approved model/migration | D4F-C |
| FK strategy | design_only | Existing FK/no-FK boundary | Inventory + migration design | D4F-C |
| role/grant | bounded | `claude_reader` local socket access; SELECT-only listed grants; no membership/CREATE | Target grants outside this dev DB | D4F-C/E |
| migration need | design_only | Recommended separation | Approved DDL design | D4F-C |
| rollback | bounded | D4E transaction conflict | Target procedure | D4F-C/E |
| real source location | not_proven | Retained FotMob data/payload records do not identify an approved historical-odds input package | Approved real historical odds location | D4F-D/E |
| source hashes | not_proven | Retained FotMob raw/payload hashes establish integrity only for those FotMob match-detail assets, not a historical-odds input package | Immutable approved historical-odds manifest | D4F-D/E |
| provenance | not_proven | Manifest contract | License/upstream evidence | D4F-D/E |
| real sample envelope | blocked | No real inventory | Hash/scope/count evidence | D4F-D/E |
| training isolation | bounded | Quarantine separation/legacy risk | Quality/leakage gate | Training |
| explicit authorization | blocked | This review grants none | User phase approval | D4F-A–E |

## 12. Blocking conditions and current decision boundary

Blocking conditions: M3 candidate-to-canonical equivalence has not been proven;
there is no approved real historical-odds location/hash/provenance; football-data
retained evidence is synthetic only; retained OddsPortal mapping/odds evidence is
absent; the M3 staging tables are not present in this development DB; and no
training quality/leakage acceptance exists.

The formal `redo source inventory strategy` permits recovery planning from the
retained FotMob baseline as canonical-match comparison evidence. It does not
make FotMob mapping targets the M3 candidate source: an M3 audit population
must instead come from actual offline Football-Data candidates under the
current Premier League `2022/2023`–`2024/2025` identity contract. Any next
network fetch, database write, M3 staging migration, linkage decision or real
import still needs a separate authorization.

## 13. Explicit non-execution declaration

One authorized local database inventory occurred. No Docker daemon/container was
started, stopped or restarted; no volume changed; no remote or production
database was connected; no source network request, migration, canonical/staging
write, odds import, training, Issue #1793 change, PR-ready action or merge
occurred. D4F-B through D4F-E did not start.

## 14. Next recommended task

Do not start automatically. Recommended next task only after user confirmation:
construct one bounded offline audit population from actual Football-Data
candidates accepted by the existing M3 identity contract:

- competition: `Premier League` only (`E0`);
- seasons: `2022/2023`, `2023/2024`, `2024/2025`;
- candidate source: existing offline Football-Data fixture/input only; and
- candidate identity: produced by the existing M3 candidate-generation code.

Only under a separate read-only database authorization, compare those candidate
identities with relevant existing canonical/FotMob `matches.match_id` records.
The 32 Ligue 1 ADG59 clean candidates, ten `needs_new_evidence` targets and
eight `remain_suspended` targets are independent FotMob mapping-governance
states; none defines or is included by implication in this M3 candidate set.
No network, database write, migration, new identity generation,
canonical-linkage persistence, training, backtest or prediction is authorized.
