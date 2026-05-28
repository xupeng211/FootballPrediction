# FotMob Observed Identity Evidence Acquisition Plan ADG11

- Phase: Phase 5.21-ADG11
- Status: completed_bounded_observed_identity_evidence_acquisition_planning
- Type: planning-only / governance-only / no-execution

## Motivation

ADG10 strict fixture identity guard regression found 37 of 42 request-contract targets lack observed identity evidence.
Without observed_home_team / observed_away_team / observed_match_date / observed_detail_id, the guard cannot validate.
This plan defines how to safely acquire observed identity evidence for these targets in ADG12.

## Target Groups

| Group | Count | ADG12 Role |
|-------|-------|-----------|
| Missing observed identity | 37 | Primary evidence acquisition candidates |
| Known reverse fixture controls | 5 | Negative controls (known error, must stay blocked) |
| Suspended preservation controls | 8 | Preservation controls (must stay blocked) |
| Positive control #4813735 | 1 | Verify acquisition/parse logic |

## Batch A (Planned First Batch)

Sample count: 9

| ID | Role |
|----|------|
| 4813735 | Positive control (Premier League, correct_mapping) |
| 4830467 | Missing evidence target |
| 4830468 | Missing evidence target |
| 4830469 | Missing evidence target |
| 4830470 | Missing evidence target |
| 4830471 | Missing evidence target |
| 4830458 | Reverse control (known error: Angers vs Paris FC → reversed) |
| 4830464 | Reverse control (known error: Nantes vs PSG → reversed) |
| 4830466 | Suspended control (must stay blocked) |

Gate: If Batch A safe and all classifications valid, authorize subsequent batches B-D.

## Evidence Acquisition Strategy

- **Method**: Public page-route safe summary acquisition (one normal request per target)
- **Source**: Existing source_page_url from enriched targets / proposal manifest
- **Extract**: Only safe metadata fields (teams, date, external_id, status markers)
- **NO**: full HTML, full pageProps, raw_data, source body, cookies, tokens

## Planned Evidence Fields

target_match_id, source_page_url, page_http_status, page_content_type, hydration_marker_present,
safe_identity_marker_present, observed_detail_id_if_safely_available, observed_home_team_if_safely_available,
observed_away_team_if_safely_available, observed_date_if_safely_available, observed_competition_if_safely_available,
observed_status_or_score_if_safely_available, anti_bot_signs, evidence_acquisition_status,
strict_guard_status_after_evidence, no_full_body_saved=true, no_db_write=true, no_raw_write=true

## Planned Classifications

observed_identity_acquired, observed_identity_missing, anti_bot_or_access_block,
hydration_marker_missing, reverse_fixture_mapping_error, home_away_inversion,
same_team_pair_wrong_leg, date_mismatch, competition_mismatch,
strict_guard_passed_no_write, strict_guard_blocked, suspended_control_still_blocked,
insufficient_safe_evidence, network_unavailable_or_transient

## Safety

- live_fetch_performed=false (this phase only)
- network_request_performed=false
- db_write_performed=false
- raw_write_execution_performed=false
- re_acceptance_execution_performed=false
- suspension_reversal_performed=false
- source_inventory_mutation_performed=false
- candidate_mutation_performed=false
- full_payload_saved=false
- raw_write_execution_ready=false

## ADG12 Prerequisites

1. ADG11 plan merged and approved
2. Explicit authorization for Batch A execution
3. ADG9 strict guard runtime code available
4. ADG10 regression result available as reference
5. No pending raw_write or re-acceptance authorization

## Recommended Next Step

Phase 5.21-ADG12: bounded observed identity evidence acquisition execution (Batch A only, requires explicit authorization).
Do not proceed to raw write.
