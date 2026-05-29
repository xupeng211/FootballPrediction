# ADG31 Bounded L2 Detail-Fetch Planning

- Phase: Phase 5.21-ADG31
- total_candidates: 32
- planned_samples: 3
- ready: 3
- blocked: 0
- raw_write_ready: 0

## Planned Samples
| id | corrected_detail | expected | reason |
| --- | --- | --- | --- |
| 4830473 | 4830473 | Paris Saint-Germain vs Angers | first_corrected_candidate |
| 4830487 | 4830487 | Lille vs Toulouse | mid_range_sample |
| 4830507 | 4830507 | Nice vs Paris FC | last_corrected_candidate |

## Contract
- Request: html_hydration page-route, max 3 samples, 1 req/target, stop on 403
- Response: in-memory parse, no full HTML/pageProps/raw_data saved
- Validation: detail_id match, home/away match, wrong-leg rejected
- Output: safe fields only, raw_write_ready=false
- Risks: direct API 403 known, anti-bot/block risk, no browser/proxy bypass

## Authorization
ADG32 execution requires EXPLICIT user authorization. Do NOT fetch until authorized.

## Next

ADG32 bounded L2 detail-fetch execution for 3 planned samples; requires explicit user authorization; do not fetch until authorized; do not raw write
