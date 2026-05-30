# FotMob Current State

- lifecycle: current-state
- owner: data / ingestion workflow
- update rule: update when ingestion state, blockers, active guards, or next step changes
- do not use historical ADG reports as the primary current truth

## Current status

- latest completed phase: ADG43 L1 canonical URL pair discovery planning
- latest merged ADG PR: #1377
- active workflow PR: ADG43 L1 canonical URL pair discovery planning
- next data phase: ADG44 bounded diagnostic probe ONLY with explicit user authorization
- raw_write_ready_count: 0

## Confirmed facts

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

- 27 corrected candidates still lack canonical_detail_url and must not be guessed.
- 5 corrected candidates have route_hash_pair from source-controlled canonical URL evidence but remain detail-page unverified.
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

ADG44 bounded diagnostic probe for remaining missing canonical URLs; requires explicit user authorization; must NOT proceed to raw write; ADG44 must NOT be executed without authorization
