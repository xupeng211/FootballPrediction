# ADG45 ADG44 Probe Result Review

- lifecycle: phase-artifact
- Phase: Phase 5.21-ADG45-REVIEW
- adg45_status: review_completed
- review_performed: true

## ADG44 Probe Result Summary

- endpoint_http_request_count: 2
- endpoint_404_count: 2
- successful_http_200_count: 0
- target_classified_count: 5
- canonical_url_pair_discovered_count: 0
- route_hash_pair_verified_count: 0
- all_targets_blocked: true
- stop_reason: fotmob_api_endpoints_not_accessible: all returned non-200 status. Endpoints tried: league_api_id47=404, league_api_id53=404

## Root Cause

- simple_https_get_endpoint_strategy_failed: true
- FotMob /api/leagues?id=47 returns 404
- FotMob /api/leagues?id=53 returns 404
- FotMob web pages return 308 redirect with empty body (client-side rendered)
- Legacy FotMob API endpoints are no longer accessible via simple HTTPS GET

## L1 Discovery Strategy Revision

### fotmob_api_v2_endpoint
- description: Investigate whether FotMob has moved API to a new base path (e.g., /api/v2/, /_next/data/)
- risk: Endpoints may require authentication or session tokens
- requires_authorization: true

### fotmob_ssr_pageprops
- description: Fetch FotMob web page with SSR-friendly User-Agent; extract __NEXT_DATA__ inline script for safe summary fields
- risk: May trigger anti-bot protection; page structure may change
- requires_authorization: true

### fotmob_authenticated_api
- description: Determine if FotMob requires API key, session cookie, or app-specific header for API access
- risk: Authentication credentials may need to be obtained or managed
- requires_authorization: true

### alternative_data_source
- description: Evaluate alternative football data sources (SofaScore, FlashScore, etc.) for Ligue 1 canonical URLs
- risk: Different data model; may require new integration
- requires_authorization: true

## Safety Boundary

- No live fetch / network request in ADG45
- No DB write, no raw write, no raw_match_data insert
- No re-acceptance, no suspension reversal
- No full payload saved
- raw_write_ready_count: 0

## Next
User must select and explicitly authorize one revised L1 discovery strategy; do NOT execute without authorization; do NOT raw write
