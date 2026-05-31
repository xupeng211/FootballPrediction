# ADG51 League Schedule URL Seed Gate

- Phase: Phase 5.21-ADG51-SEED-GATE
- url_seed_recorded: true
- source_controlled_url_available: true
- url: https://www.fotmob.com/zh-Hans/leagues/53/fixtures/ligue-1?group=by-date

## Static URL Validation
- protocol: https
- hostname: www.fotmob.com
- locale: zh-Hans
- league_id: 53
- league_slug: ligue-1
- tab: fixtures
- query_group: by-date
- season_param_present: false
- validation: PASS

## Browser Observation
- competition: Ligue 1 / France
- league_id: 53
- season: 2025/2026
- tab: fixtures
- season_param_present: false
- note: User observed current-season page normally does not include explicit season param; historical seasons may include season=YYYY-YYYY

## Future ADG52 Probe Contract
- source_url: https://www.fotmob.com/zh-Hans/leagues/53/fixtures/ligue-1?group=by-date
- stop: 403/block/captcha/season_mismatch/wrong_competition
- in-memory parse; safe summary only
- no full HTML/__NEXT_DATA__/pageProps saved
- no DB/raw write; raw_write_ready_count=0

## Next
User must explicitly authorize ADG52 bounded league schedule SSR probe; do NOT execute without authorization
