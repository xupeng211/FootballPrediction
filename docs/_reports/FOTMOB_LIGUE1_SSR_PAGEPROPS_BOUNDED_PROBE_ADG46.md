# ADG46 SSR pageProps Bounded Probe Results

- lifecycle: phase-artifact
- Phase: Phase 5.21-ADG46-SSR-PROBE
- adg46_status: completed_with_partial_success
- user_authorization_confirmed: true
- attempted_request_count: 1
- successful_http_200_count: 1
- next_data_marker_found: 1
- pageprops_marker_found: 1
- canonical_url_pair_discovered: 0
- route_hash_pair_verified: 0
- reverse_fixture_rejected: 1
- raw_write_ready_count: 0

## Per-target Results

### 53_20252026_4830473
- expected: Paris Saint-Germain vs Angers
- classification: route_hash_pair_reverse_fixture_rejected
- request_attempted: true
- http_status: 200
- next_data_marker: true
- canonical_url_found: none
- route_hash_pair_found: none
- observed: Angers vs Paris Saint-Germain
- extraction_status: next_data_parsed_safe_summary_extracted
- full_payload_saved: false
- raw_write_ready: false

### 53_20252026_4830499
- expected: ? vs ?
- classification: not_attempted_due_to_prior_stop
- request_attempted: false
- http_status: N/A
- next_data_marker: false
- canonical_url_found: none
- route_hash_pair_found: none
- observed: ? vs ?
- extraction_status: N/A
- full_payload_saved: false
- raw_write_ready: false

## Safety
- full_html_saved: false
- full_next_data_saved: false
- full_pageProps_saved: false
- full_payload_saved: false
- db_write: false
- raw_write: false
- raw_write_ready_count: 0

## Next
ADG47 review SSR probe findings; do NOT raw write
