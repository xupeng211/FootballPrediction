# ADG39 Canonical Detail URL Discovery

- Phase: Phase 5.21-ADG39
- total: 32
- canonical_url_found: 5
- route_code_found: 5
- route_code_from_l1_api: true

## Key finding
L1 league API page_url already contains canonical route codes.
But these route codes may belong to reverse-leg detail pages.
L2 must consume L1 canonical URL, not guess route codes.

## Handoff contract
L1 delivers: canonical_detail_url, route_code, detail_hash_id, home/away
L2 must NOT: guess route code, use detail ID as route code, use historical enriched URL

## Next
ADG40: bounded diagnostic probe for alternate detail ID with correct-orientation route code from L1 API; do not raw write
