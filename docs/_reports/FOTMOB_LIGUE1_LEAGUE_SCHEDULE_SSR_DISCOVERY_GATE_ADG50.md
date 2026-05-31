# ADG50 League Schedule SSR Discovery Gate

- Phase: Phase 5.21-ADG50-GATE
- chosen_strategy: league_schedule_ssr_discovery
- future_probe_source_count: 1
- max_requests_per_source: 1
- source_controlled_url_available: false
- confirmed_reverse: 2, still_unverified: 3, canonical_url_missing: 27
- requires_explicit_user_authorization: true
- probe_not_executed: true
- raw_write_ready_count: 0

## Strategy Basis
- ADG46 confirmed SSR viable (HTTP 200, __NEXT_DATA__ extractable)
- ADG48 confirmed 2 known route_hash_pairs are reverse fixtures
- ADG48 confirmed single match page pageProps does not expose alternate hash_ids
- ADG49 recommended league_schedule_ssr_discovery as next strategy
- League schedule page likely contains full season fixture list with all route/hash pairs

## Future Probe Source
- type: league_schedule_ssr_page
- competition: Ligue 1
- season: 2025/2026
- scope: season fixtures / match list / schedule hydration data
- goal: enumerate fixture-level canonical identities (route_code, hash_id, route_hash_pair, canonical_detail_url, home/away orientation)
- source_controlled_url_available: false
- note: No source-controlled league schedule page URL found in committed artifacts. ADG50 gate records need for URL seed. Future probe must not guess URL; must use source-controlled URL from authorized discovery.

## Probe Boundary
- public league schedule page only; SSR/hydration only
- stop: 403/block/captcha/unexpected large payload
- in-memory parse; no full HTML/__NEXT_DATA__/pageProps saved
- no DB/raw write; raw_write_ready_count=0

## Allowed Safe Summary (aggregate/bounded)
- 17 top-level fields
- matched_targets_summary: 12 fields per target
- 9 forbidden save types

## Authorization Required
Probe requires explicit user authorization + source-controlled URL seed. This gate does NOT authorize execution.

## Next
User must provide league schedule URL seed or authorize URL discovery; do NOT guess; do NOT raw write
