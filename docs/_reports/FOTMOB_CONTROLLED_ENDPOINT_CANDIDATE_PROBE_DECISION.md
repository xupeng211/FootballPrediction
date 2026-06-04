<!-- markdownlint-disable MD013 MD034 -->

# FotMob Controlled Endpoint Candidate Probe — Decision Report

## Endpoint Templates Tested

- `https://www.fotmob.com/api/data/matchDetails?matchId={match_id}` — Canonical /api/data/matchDetails from production FotMobApiClient.js
- `https://www.fotmob.com/match/{match_id}` — HTML hydration route from FotMobRawDetailFetcher.js, known HTTP 200
- `https://www.fotmob.com/matches/{route_code}/{match_id}` — SSR page route, ADG60 validated, uses route_code from user seeds

| Endpoint Template | Attempted | JSON Observed | HTML | Blocked | Invalid | Decision |
|---|---:|---:|---:|---:|---:|---|
| `https://www.fotmob.com/api/data/matchDetails?matchId={match_` | 3 | 0 | 0 | 1 | 0 | reject — blocked by anti-bot |
| `https://www.fotmob.com/match/{match_id}` | 3 | 0 | 0 | 0 | 0 | review |
| `https://www.fotmob.com/matches/{route_code}/{match_id}` | 3 | 0 | 0 | 0 | 0 | review |

## Recommendation

- 当前无 endpoint 返回成功 JSON。
- 建议进入 endpoint candidate review followup。
- 在确认可用 endpoint 前，不要进入 raw JSON write。
