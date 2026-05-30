# ADG44 Bounded Diagnostic Probe Results

- lifecycle: phase-artifact
- Phase: Phase 5.21-ADG44-PROBE
- adg44_status: completed_with_stop
- user_authorization_confirmed: true
- planned_probe_target_count: 5
- attempted_request_count: 5
- canonical_url_pair_discovered_count: 0
- route_hash_pair_verified_count: 0
- reverse_fixture_rejected_count: 0
- canonical_url_not_found_count: 0
- blocked_403_count: 0
- identity_mismatch_count: 0
- raw_write_ready_count: 0

## Per-target Results

### Target 1: 53_20252026_4830480
- expected: Lyon vs Marseille
- status before: canonical_url_missing_needs_l1_discovery
- route_hash_pair before: missing
- classification: blocked_api_endpoint_not_found
- request_attempted: true
- http_status: 404
- blocker_reason: fotmob_api_endpoints_not_accessible: all returned non-200 status. Endpoints tried: league_api_id47=404, league_api_id53=404

- raw_write_ready: false

### Target 2: 53_20252026_4830499
- expected: Marseille vs Paris Saint-Germain
- status before: canonical_url_missing_needs_l1_discovery
- route_hash_pair before: missing
- classification: blocked_api_endpoint_not_found
- request_attempted: true
- http_status: 404
- blocker_reason: fotmob_api_endpoints_not_accessible: all returned non-200 status. Endpoints tried: league_api_id47=404, league_api_id53=404

- raw_write_ready: false

### Target 3: 53_20252026_4830473
- expected: Paris Saint-Germain vs Angers
- status before: route_hash_pair_unverified_needs_detail_verification
- route_hash_pair before: 2o4ahb#4830473
- classification: blocked_api_endpoint_not_found
- request_attempted: true
- http_status: 404
- blocker_reason: fotmob_api_endpoints_not_accessible: all returned non-200 status. Endpoints tried: league_api_id47=404, league_api_id53=404

- raw_write_ready: false

### Target 4: 53_20252026_4830474
- expected: Strasbourg vs Nantes
- status before: route_hash_pair_unverified_needs_detail_verification
- route_hash_pair before: 37a71l#4830474
- classification: blocked_api_endpoint_not_found
- request_attempted: true
- http_status: 404
- blocker_reason: fotmob_api_endpoints_not_accessible: all returned non-200 status. Endpoints tried: league_api_id47=404, league_api_id53=404

- raw_write_ready: false

### Target 5: 53_20252026_4830478
- expected: Lens vs Brest
- status before: route_hash_pair_unverified_needs_detail_verification
- route_hash_pair before: 2f5cib#4830478
- classification: blocked_api_endpoint_not_found
- request_attempted: true
- http_status: 404
- blocker_reason: fotmob_api_endpoints_not_accessible: all returned non-200 status. Endpoints tried: league_api_id47=404, league_api_id53=404

- raw_write_ready: false

## Safety

- live_fetch_performed: true
- network_request_performed: true
- full_payload_saved: false
- db_write_performed: false
- raw_write_execution_performed: false
- raw_match_data_insert_performed: false
- raw_write_ready_count: 0

## Stop: fotmob_api_endpoints_not_accessible: all returned non-200 status. Endpoints tried: league_api_id47=404, league_api_id53=404

## Next
ADG45 review probe results; still no raw write; do not proceed to raw write without separate authorization
