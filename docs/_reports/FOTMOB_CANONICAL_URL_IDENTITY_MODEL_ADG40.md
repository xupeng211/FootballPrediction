# ADG40 Canonical URL Identity Model

- Phase: Phase 5.21-ADG40

## User-provided observation
URL A: https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735 → AFC Bournemouth 1-1 Manchester City, venue: Vitality Stadium
URL B: https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813470 → Manchester City 3-1 AFC Bournemouth, venue: Etihad Stadium
Same route_code 2feiv3, different hash IDs (4813735 vs 4813470), different fixtures.

## FotMob URL component model
- slug: display/SEO only — not authoritative for home/away orientation
- route_code: matchup route / team-pair entry point — NOT unique fixture identity
- hash_id: fixture selector within the route — determines which concrete fixture is displayed
- canonical identity: atomic tuple = {route_code, hash_id} — must be preserved as unit

## L2 URL rewriting blocked
- rewrite slug based on expected home/away
- replace route_code with detail_id
- treat route_code alone as unique fixture identity
- treat hash_id alone as unique fixture identity
- use historical enriched URL as primary L2 URL source
- guess route_code when L1 has not provided one

## ADG32-38 retrospective
L1 API provided route_code + hash_id for reverse fixture; correct-orientation hash_id was not discovered

## Next
ADG41: implement canonical URL atomic handoff contract; block L2 URL rewriting; do not raw write
