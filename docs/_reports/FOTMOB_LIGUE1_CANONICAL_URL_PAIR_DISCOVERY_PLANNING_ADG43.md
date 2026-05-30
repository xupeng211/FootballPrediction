# ADG43 L1 Canonical URL Pair Discovery Planning

- lifecycle: phase-artifact
- Phase: Phase 5.21-ADG43
- total_corrected_candidates: 32
- missing_canonical_url_targets: 27
- unverified_route_hash_pair_targets: 5
- alternate_hash_id_discovery_required_count: 5
- canonical_pair_probe_required_count: 27
- l2_guessing_blocked_count: 32
- raw_write_ready_count: 0

## Discovery Strategy

### For 27 missing canonical URLs
- Primary source: L1 FotMob league API source-controlled data (league_api_overview)
- Each match in L1 API response has pageUrl with route_code + hash_id
- Hash fragment in pageUrl === corrected_detail_external_id for correct match
- Search L1 response for matching hash_id per candidate
- Extract complete canonical_detail_url, route_code, hash_id, route_hash_pair
- Candidates NOT found in L1 source-controlled data → ADG44 probe required

### For 5 unverified route_hash_pairs
- All 5 have route_hash_pair from L1 but with reversed slug orientation
- route_code + hash_id may correspond to reverse-leg fixture
- Detail-page verification required: compare observed home/away/date/competition against expected
- Safe summary fields only (no full payload, no pageProps save)
- Alternate hash_id may exist for correct-orientation fixture under same route_code

### Alternate hash discovery
- Same route_code can serve different fixtures via different hash_ids
- Man City vs Bournemouth example: 2feiv3#4813735 (reverse) vs 2feiv3#4813470 (correct)
- L1 API typically returns one hash_id per fixture (the primary/featured one)
- Correct-orientation hash_id may differ from L1-returned hash_id
- Discovery method: L1 API may contain both home/away legs under same route_code
- Selection: prefer hash_id matching corrected_detail_external_id with correct home/away orientation

### ADG44 bounded diagnostic probe (NOT executed in ADG43)
- Max 5 targets for diagnostic only
- Single GET to L1 league API per target set
- Safe summary fields only; no full payload
- Stop on 403 / block / captcha / first identity mismatch
- No browser, proxy, or bypass
- Requires explicit user authorization

## Boundary
- No live fetch, no network, no DB write, no raw write
- No raw_match_data insert, no re-acceptance, no suspension reversal
- No full payload saved, no browser/proxy/captcha bypass
- L2 route-code guessing permanently blocked
- Detail ID as route code permanently blocked
- raw_write_ready_count=0

## Next
ADG44 bounded diagnostic probe for remaining missing canonical URLs; requires explicit user authorization; do not raw write
