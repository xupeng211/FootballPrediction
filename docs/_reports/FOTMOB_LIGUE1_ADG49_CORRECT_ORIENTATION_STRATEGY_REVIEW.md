# ADG49 Correct-Orientation Strategy Review

- Phase: Phase 5.21-ADG49-REVIEW
- ssr_strategy_still_viable: true

## ADG48 Probe Summary
- attempted: 2, http_200: 2
- correct_orientation_discovered: 0, route_hash_pair_verified: 0, reverse_fixture_confirmed: 2

## Confirmed Reverse Pairs
- 2o4ahb#4830473: expected PSG vs Angers, observed Angers vs PSG, Apr 2026
- 2sy6tc#4830472: expected Nice vs Auxerre, observed Auxerre vs Nice, May 2026

## Remaining Problem
- 5 known pairs: 2 reverse, 3 unverified, 27 missing
- correct-orientation still missing
- pageProps no alternate hash_ids

## Revised Strategy Options
### league_schedule_ssr_discovery
- Probe FotMob league schedule/matchday page (SSR) to enumerate all fixtures and discover correct-orientation route_hash_pairs from full-season data
- risk: Requires authorized probe; league page may be large but safe summary extraction works
- requires_auth: true
- not_executed: true

### matchup_route_page_discovery
- Use same route_code matchup page to see if it lists both legs (home/away) with different hash_ids
- risk: May not expose both legs on single page
- requires_auth: true
- not_executed: true

### season_schedule_hydration_data
- Look for season-level __NEXT_DATA__ that contains all fixtures with full route/hash pairs
- risk: Requires finding correct league season page URL
- requires_auth: true
- not_executed: true

### manual_canonical_seed
- Accept user-provided browser-observed canonical URL examples as manual evidence only, not automated source
- risk: Manual process; may still yield reverse fixtures
- requires_auth: true
- not_executed: true

### alternate_public_source
- Evaluate other public football data sources if FotMob cannot expose correct pairs safely
- risk: Different data model; integration cost
- requires_auth: true
- not_executed: true

## Next
User must select and authorize revised strategy; recommended: league_schedule_ssr_discovery; do NOT raw write
