# ADG48 Correct-Orientation Route Hash Discovery Gate

- Phase: Phase 5.21-ADG48-GATE
- chosen_strategy: ssr_pageprops_correct_orientation_discovery
- future_probe_target_count: 3
- max_targets: 3, max_requests_per_target: 1
- confirmed_reverse: 1, remaining_unverified: 4, canonical_url_missing: 27
- requires_explicit_user_authorization: true
- probe_not_executed: true
- raw_write_ready_count: 0

## Strategy Basis
- ADG46 confirmed SSR viable (HTTP 200, __NEXT_DATA__ found)
- ADG47 confirmed 2o4ahb#4830473 is reverse fixture
- ADG40 model: same route_code serves both legs via different hash_ids

## Future Targets

### 53_20252026_4830473
- expected: Paris Saint-Germain vs Angers | 2025-08-22
- status: known_route_hash_pair_confirmed_reverse
- known pair: 2o4ahb#4830473
- goal: discover_correct_orientation_route_hash_pair
- why: Confirmed reverse fixture via ADG46 SSR probe. Same route_code 2o4ahb may serve both legs via different hash_ids (ADG40 model). Need to discover correct-orientation hash_id for PSG home vs Angers away.

### 53_20252026_4830472
- expected: Nice vs Auxerre | 2025-08-23
- status: route_hash_pair_unverified_needs_detail_verification
- known pair: 2sy6tc#4830472
- goal: verify_route_hash_pair_orientation
- why: One of 4 remaining unverified route_hash_pairs. Early season fixture. SSR safe summary can verify orientation against expected home/away.

### 53_20252026_4830499
- expected: Marseille vs Paris Saint-Germain | date TBD
- status: canonical_url_missing_needs_l1_discovery
- known pair: missing
- goal: discover_canonical_url_pair
- why: Highest-value missing canonical URL (Le Classique). SSR probe can search league schedule page for this fixture and discover canonical URL/route_hash_pair.

## Safety Boundary
- SSR/pageProps only; public match pages; in-memory parse
- Stop: 403/block/captcha/identity mismatch/reverse fixture
- No full HTML/__NEXT_DATA__/pageProps saved
- No DB/raw write; raw_write_ready_count=0

## Authorization Required
Probe requires separate explicit user authorization. This gate does NOT authorize execution.

## Next
User explicit authorization required; do NOT execute probe; do NOT raw write
