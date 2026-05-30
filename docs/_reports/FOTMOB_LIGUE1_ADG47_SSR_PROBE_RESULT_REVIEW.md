# ADG47 SSR Probe Result Review

- lifecycle: phase-artifact
- Phase: Phase 5.21-ADG47-REVIEW
- adg47_status: review_completed

## ADG46 SSR Viability Confirmed
- public_match_page_http_200: true
- next_data_marker_found: true
- pageprops_marker_found: true
- hydration_marker_found: true
- safe_summary_extracted: true
- extraction_method: in-memory __NEXT_DATA__ parse
- full_payload_saved: false

## Reverse Fixture Confirmation
- route_hash_pair: 2o4ahb#4830473
- expected: Paris Saint-Germain vs Angers
- observed: Angers vs Paris Saint-Germain
- conclusion: route_hash_pair corresponds to REVERSE fixture (away leg), not the expected home leg; date mismatch (Apr 2026 vs Aug 2025) confirms wrong fixture orientation

## Correct-Orientation Discovery Needs
- known_route_hash_pair_count: 5
- confirmed_reverse_fixture: 1
- remaining_unverified: 4
- canonical_url_missing: 27

## Revised Discovery Plan
- strategy: ssr_pageprops_correct_orientation_discovery
- Discover correct-orientation route_hash_pair for PSG vs Angers home leg
- The same route_code 2o4ahb may serve BOTH legs via different hash_ids (per ADG40 model)
- Need to find correct-orientation hash_id for PSG home vs Angers away under route_code 2o4ahb
- Verify remaining 4 route_hash_pair_unverified candidates via SSR safe summary
- Design bounded SSR probe for 27 canonical_url_missing candidates using league schedule page discovery
- requires_explicit_user_authorization: true

## Safety
- No live fetch / network in ADG47
- No DB write, no raw write
- raw_write_ready_count: 0

## Next
User authorization required for correct-orientation route_hash_pair discovery; do NOT execute; do NOT raw write
