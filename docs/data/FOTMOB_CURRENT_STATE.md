<!-- markdownlint-disable MD013 -->

# FotMob Current State

- lifecycle: current-state
- owner: data / ingestion workflow
- update rule: update when ingestion state, blockers, active guards, or next step changes
- do not use historical ADG reports as the primary current truth
- retained raw storage state and historical audit scope are recorded below and
  in `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md`

## Current authoritative status — 2026-07-29

```text
Official Architecture Decision Gate direction = redo source inventory strategy
Implementation approach = RECOVER_EXISTING_ACQUISITION_ARCHITECTURE
Evidence-backed outcome = FOTMOB_IDENTITY_BASELINE_REUSE_RECOMMENDED
```

### Current read-only retained inventory

- `matches=60`; 58 are strong/harvested FotMob matches and 60/60 have
  `external_id`.
- `raw_match_data=76`: `fotmob_live_v1=58`, hydration=8, page-props=8 and
  synthetic=2. All 76 rows are FK-linked to `matches`; there are 60 distinct
  `match_id` values and zero raw orphans.
- `fotmob_raw_match_payloads=32` are retained full raw-payload records, not
  metadata-only rows. V26.5 requires complete, unparsed `__NEXT_DATA__` JSON
  in non-null `next_data_json`, together with raw-file locators, SHA-256
  values, byte sizes, capture timestamps and ingestion metadata. Complete
  `page_props_json` can be retained when present, but the column is nullable.
  Their `match_id` values overlap retained match/raw assets at match level
  only; record-level payload-to-raw lineage, 32/32 pageProps presence and
  32/32 parser validation are not proven.
- The retained data and `matches.match_id`/`external_id` identity baseline are
  evidence assets; they do not establish a future writer entrypoint.
- The 2026-07-29 read-only schema review found no provider-scoped external-ID
  or business-identity uniqueness, no canonical import lineage and an
  update-on-conflict generic writer. These are implementation requirements,
  not permission to reuse a legacy writer.

### Current mapping-target chronology (separate from retained rows)

The retained database rows above are asset evidence, not a classification of
historical mapping targets. A static exact-ID reconciliation covers 50 concrete
Ligue 1 mapping targets:

- 32 are `clean_candidate`: L2V3BC's earlier `needs_new_evidence` targets have
  exact ADG59A promotion and ADG59B
  `accepted_source_controlled_only`/`resolved_source_controlled_only` evidence,
  with confirmed orientation/date/competition and no duplicate conflict.
- 10 remain `needs_new_evidence`: they have an exact L2V3BC identity but no
  exact ADG59A/ADG59B successor or later mapping-state mutation.
- 8 remain `remain_suspended`: L2V3AT suspended their accepted
  mapping/baseline after reverse-fixture contradictions, and no exact later
  resolution exists.

The terminal counts are `32 + 10 + 8 = 50`. No target was fuzzy-matched,
re-accepted, unsuspended, written to the database or made raw-write ready by
this reconciliation. These are not M3 Football-Data candidates and do not
define its population. The separate M3 2026-07-28 offline audit has now
compared 892 Football-Data Premier League candidates with 1,140 recovered
FotMob canonical candidates: 888 are exact unique and four are isolated
kickoff conflicts. The design selects all 1,140 for future inventory, treats
888 as linkage-only, keeps four linkage-quarantine, and treats the remaining
248 as canonical-only/unlinked. The four plus 248 are the 252 candidates
without an exact Football-Data link. That result does not reclassify any
32/10/8 Ligue 1 mapping target or validate a raw writer/import.

### Historical controlled audit milestone

Four retained rows were explicitly audited under #1487: 4/4 parseable, 4/4
SHA-valid, 4/4 inner-`matchId` valid, zero errors and zero warnings. This
historical four-row audit does not extend a full parser/audit result to all 58
current `fotmob_live_v1` retained rows. Exact named-writer/run provenance for
all 58 rows is not uniquely attributable.

### Current safety and documentation status

- This file is the active FotMob current-state source of truth; historical ADG
  reports are context, not current execution instructions.
- Legacy acquisition scripts, including the N=3 `n3_live_fotmob_raw_retain.js`
  network/UPSERT path, are historical evidence only and must not become new
  dependencies, canonical writers or recovery contracts.
- README declares FotMob production acquisition `Not yet established`. A future
  canonical writer requires a separately authorized, tested `data-*` milestone.
- Browser, session, cookie, captcha, proxy, network and database-write paths
  remain blocked unless separately authorized.

## Historical legacy ADG context (not current retained-raw status)

- ADG48 correct-orientation probe: 2 targets probed (PSG-Angers, Nice-Auxerre), both HTTP 200. Both confirmed reverse fixtures. 2o4ahb#4830473 = Angers-PSG (reverse observed again). 2sy6tc#4830472 = Auxerre-Nice (newly confirmed reverse). No correct-orientation pairs discovered. No alternate hash candidates found in pageProps. 5 known pairs: 2 confirmed reverse, 3 unverified. 27 missing canonical URLs.
- ADG46 SSR probe: FotMob match page IS accessible (HTTP 200). __NEXT_DATA__ marker FOUND. Safe summary extracted in-memory. Critical finding: route_hash_pair 2o4ahb#4830473 corresponds to REVERSE fixture (Angers home vs PSG away, Apr 2026). Expected orientation (PSG home vs Angers away, Aug 2025) needs different route_hash_pair.
- ADG44 probe result: all 5 targets attempted; FotMob API endpoints (league API id=47, id=53) return 404 via simple HTTPS GET. API architecture has changed. No canonical URLs discovered, no route_hash_pairs verified. No full payload saved. No raw write. 0/5 canonical URL found. Endpoint access requires revised strategy.
- ADG43 result: planning completed for 32 corrected candidates. 27 missing canonical_url targets require L1 discovery. 5 unverified route_hash_pair targets require detail-page verification. ADG44 bounded diagnostic probe designed but NOT executed.
- ADG42 result: total_corrected_candidates=32, canonical_url_atomic_identity_valid_count=5, canonical_url_missing_count=27, route_hash_pair_unverified_count=5, raw_write_ready_count=0.

- URL hash fragment can be detail identity evidence, but alone is insufficient for candidate acceptance.
- Ligue 1 current source inventory / candidate records show systematic home/away inversion.
- ADG12 + ADG16 combined: 17/17 Ligue 1 samples = reverse_fixture_mapping_error.
- ADG20: existing source-controlled artifacts cannot generate corrected Ligue 1 records.
- ADG20 result: proposed_corrected=0, rejected_current_reverse=10, requires_external_discovery=32, suspended_blocked=8, positive_control=1.

## Active runtime guards

- validateStrictFixtureIdentity() — strict home/away/date/competition validation
- classifyDetailCandidateIdentity() — generation-time candidate classification
- selectOrientedFixtureRecord() — oriented fixture selection from ambiguous team-pair records

## Current blockers

- A production FotMob acquisition entrypoint and current external endpoint
  availability are not proven.
- Full parser/audit coverage for all 58 retained `fotmob_live_v1` rows is not
  proven; only the historical four-row audit is complete.
- `fotmob_raw_match_payloads` stores retained offline full raw-payload assets,
  but establishes match-level overlap only, not record-level payload-to-raw
  lineage; 32/32 parser validation is not proven.
- Ten concrete historical mapping targets still need new evidence and eight
  remain suspended; retained row counts do not make the whole historical batch
  clean.
- M3 candidate-to-recovered-FotMob-candidate compatibility is proven only for
  the bounded 2022/2023–2024/2025 Premier League audit: 888 exact unique and
  four isolated kickoff conflicts out of 892 source candidates. The local
  development `matches` inventory remains zero for that scope. The recovered
  1,140-candidate `candidate-match-identity/v1` artifact has no status field,
  so it cannot pass future writer preflight; no inventory writer, link or
  import has been authorized.
- No network, database write, migration, new identity generation or legacy
  writer execution is authorized.

## Forbidden without explicit authorization

- live fetch, network request, browser automation, direct API probing
- DB write, raw write, raw_match_data insert
- re-acceptance, suspension reversal / unsuspend
- source inventory production mutation, candidate production mutation
- Batch C/D evidence acquisition
- full HTML / pageProps / raw_data / source body save or print

## Recommended next step

Do not start automatically. Recommended next task only after user confirmation:
an implementation review for a new fail-closed canonical writer, its
status-complete hash-bound FotMob artifact contract, and isolated
provider-scoped uniqueness/import-lineage migration plan. Future inventory is
1,140 candidates; linkage remains separately authorized for 888 exact
identities and the four conflicts remain quarantine. The 32/10/8 Ligue 1
states remain independent. No network, database write, migration,
canonical-linkage persistence or legacy-writer execution is authorized here.

The future canonical FotMob writer is a separate `data-*`-gated business
milestone, not an automatic follow-up or a legacy-script restart.
