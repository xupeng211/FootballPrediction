# FotMob Current State

- lifecycle: current-state
- owner: data / ingestion workflow
- update rule: update when ingestion state, blockers, active guards, or next step changes
- do not use historical ADG reports as the primary current truth

## Current status

- latest completed phase: ADG42 corrected artifacts canonical contract migration preview
- latest merged ADG PR: #1376
- active workflow PR: ADG42 corrected artifacts canonical contract migration preview
- next data phase: ADG43 planning only; design L1 canonical URL pair discovery for missing candidates
- raw_write_ready_count: 0

## Confirmed facts

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

ADG43 design L1 canonical URL pair discovery for missing candidates; no fetch/write in ADG42
