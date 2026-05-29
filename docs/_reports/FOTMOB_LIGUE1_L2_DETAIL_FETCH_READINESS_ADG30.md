# ADG30 L2 Detail-Fetch Readiness

- Phase: Phase 5.21-ADG30
- candidates: 32
- l2_ready: 32
- l2_blocked: 0

## Contracts
- Input: corrected_detail_external_id + expected_home/away from ADG27
- Request: FotMob match detail page-route (html_hydration), bounded, stop on 403
- Response: detail_id must match, home/away must match, wrong-leg rejected
- Output: safe fields only, no full body/pageProps/raw_data

## Blocker
- direct API 403 risk documented; public page-route preferred
- raw_write remains false until post-fetch no-write ADG validation

## Next

32/32 L2 detail-fetch ready; recommend ADG31 bounded L2 detail-fetch execution planning; do not bypass 403; do not raw write
