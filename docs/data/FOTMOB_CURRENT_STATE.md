# FotMob Current State

- lifecycle: current-state
- owner: data / ingestion workflow
- update rule: update when ingestion state, blockers, active guards, or next step changes
- do not use historical ADG reports as the primary current truth

## Current status

- latest completed phase: ADG36 detail ID assignment investigation
- latest merged ADG PR: #1354
- active workflow PR: #1355 repository hygiene guardrails
- next data phase after hygiene merge: ADG22 (oriented corrected candidates found from league API; recomme...)
- raw_write_ready_count: 0

## Confirmed facts

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

- 42 non-suspended Ligue 1 targets require corrected source inventory records.
- 32 targets require external corrected-source discovery or evidence acquisition.
- Current wrong-leg source records must not be raw-written.
- Current source-controlled artifacts are insufficient to propose corrected records.

## Forbidden without explicit authorization

- live fetch, network request, browser automation, direct API probing
- DB write, raw write, raw_match_data insert
- re-acceptance, suspension reversal / unsuspend
- source inventory production mutation, candidate production mutation
- Batch C/D evidence acquisition
- full HTML / pageProps / raw_data / source body save or print

## Recommended next step

Merge workflow hygiene / cross-agent alignment. Then ADG21 bounded corrected-source discovery under updated rules.
