# ADG46 SSR pageProps Discovery Authorization Gate

- lifecycle: phase-artifact
- Phase: Phase 5.21-ADG46-SSR-GATE
- chosen_strategy: fotmob_ssr_pageprops
- future_probe_target_count: 2
- max_targets: 2
- max_requests_per_target: 1
- requires_explicit_user_authorization: true
- ssr_probe_not_executed: true
- raw_write_ready_count: 0

## Chosen Strategy: fotmob_ssr_pageprops

Why this strategy:
- Public FotMob match pages use Next.js SSR with __NEXT_DATA__ inline script
- No authentication required for public match pages
- No API key needed
- No browser automation needed — simple HTTPS GET with SSR-friendly User-Agent
- pageProps contains match identity fields extractable as safe summary
- Aligned with ADG40 model: route_code + hash_id are embedded in page data

## Selected Future SSR Probe Targets

### Target 1: 53_20252026_4830473
- expected: Paris Saint-Germain vs Angers | 2025-08-22T18:45:00.000Z
- status: route_hash_pair_unverified_needs_detail_verification
- route_hash_pair_known: 2o4ahb#4830473
- why selected: Known reversed slug in L1 API URL; high diagnostic value for SSR pageProps orientation verification
- expected page URL: https://www.fotmob.com/matches/angers-vs-paris-saint-germain/2o4ahb#4830473
- probe method: Single GET to FotMob match page URL; in-memory parse of __NEXT_DATA__ script tag; extract safe summary only
- max requests: 1

### Target 2: 53_20252026_4830499
- expected: Marseille vs Paris Saint-Germain | date TBD
- status: canonical_url_missing_needs_l1_discovery
- route_hash_pair_known: missing
- why selected: High-value missing canonical URL (Le Classique); SSR probe may discover route_code + hash_id from page
- expected page URL: to be discovered via league page search
- probe method: SSR page discovery via league page listing or match search; extract match pageUrl from pageProps
- max requests: 1

## SSR pageProps Extraction Contract

### Allowed safe summary fields (22 fields)
- `target_match_id`
- `request_url`
- `http_status`
- `redirect_summary`
- `content_type`
- `next_data_marker_present`
- `pageprops_marker_present`
- `hydration_marker_present`
- `canonical_detail_url_found`
- `route_code_found`
- `hash_id_found`
- `route_hash_pair_found`
- `observed_home`
- `observed_away`
- `observed_date`
- `observed_competition`
- `identity_status`
- `orientation_status`
- `extraction_status`
- `blocker_reason`

### Forbidden in save
- `full_html`
- `full_next_data`
- `full_pageprops`
- `full_raw_data`
- `full_source_body`
- `cookies`
- `sensitive_headers`
- `session_tokens`
- `api_keys`

### Extraction process
1. GET match page URL with SSR-friendly User-Agent
2. Search response for `id="__NEXT_DATA__"` script tag
3. Parse JSON in-memory; extract only allowed fields
4. Discard full HTML, full __NEXT_DATA__, full pageProps immediately
5. Save only safe summary fields to manifest

## Probe Safety Boundary

- Stop on 403 / block / captcha / first identity mismatch
- No retry on any block signal
- No browser, no proxy, no bypass
- In-memory parse only; no full payload saved
- No DB write, no raw write, no raw_match_data insert
- No re-acceptance, no suspension reversal
- raw_write_ready_count=0

## Authorization Required

SSR/pageProps probe execution requires explicit user authorization.
This gate document records the boundary; it does NOT authorize execution.

## Not Executed

- No live fetch performed
- No network request performed
- No page fetched
- No HTML saved

## Next
User explicit authorization required; do NOT execute SSR probe without it; do NOT raw write
