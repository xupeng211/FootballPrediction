# FotMob Current State

- lifecycle: current-state
- owner: data / ingestion workflow
- update rule: update when ingestion state, blockers, active guards, or next step changes
- do not use historical ADG reports as the primary current truth

## Current status

- latest completed phase: ADG55 acceptance/mutation planning completed
- latest merged ADG PR: #1393
- active workflow PR: ADG55 acceptance/mutation planning
- next data phase: user must authorize ADG56 date guard completion/acceptance eligibility review
- raw_write_ready_count: 0

## Confirmed facts

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

- FotMob legacy API endpoints not accessible (404) but SSR match pages ARE accessible (200, __NEXT_DATA__ present).
- 27 corrected candidates still lack canonical_detail_url and must not be guessed.
- 5 corrected candidates have route_hash_pair from source-controlled canonical URL evidence — 1 confirmed as reverse fixture via SSR probe.
- Correct-orientation route_hash_pairs need discovery; reverse fixture pairs should not be raw-written.
- Current wrong-leg source records must not be raw-written.
- Corrected artifacts are not raw-write-ready.

## Forbidden without explicit authorization

- live fetch, network request, browser automation, direct API probing
- DB write, raw write, raw_match_data insert
- re-acceptance, suspension reversal / unsuspend
- source inventory production mutation, candidate production mutation
- Batch C/D evidence acquisition
- full HTML / pageProps / raw_data / source body save or print

## Recommended next step

User must authorize ADG56 date guard completion/acceptance eligibility review; 32 targets ready; 10 date_pass/22 date_unknown; 0 blocked; do NOT raw write

User must authorize ADG55; 32/32 promotion preview ready; 0 blocked; ALL guards pass (orientation 32/32, canonical parse 32/32, zero duplicates); do NOT raw write before explicit authorization

User must authorize ADG54 no-write canonical identity promotion preview; 32 targets have canonical identities from league schedule SSR; do NOT raw write

ADG53 review ADG52 breakthrough: 32/32 targets matched, 306 fixtures, ALL have canonical route_hash_pairs; league schedule home/away data confirms correct orientation; do NOT raw write

User must select and authorize revised strategy; 5 options proposed; league_schedule_ssr_discovery recommended; do NOT raw write

ADG49 review ADG48 findings; 2/2 known pairs confirmed reverse; SSR data shows no alternate hash_ids in pageProps; correct-orientation discovery strategy needs revision; do NOT raw write
