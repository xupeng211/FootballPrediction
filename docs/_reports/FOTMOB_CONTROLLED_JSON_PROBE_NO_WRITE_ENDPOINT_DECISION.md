<!-- markdownlint-disable MD013 MD034 -->

# FotMob Controlled JSON Probe — Endpoint Decision Report

## Endpoint Templates Tested

- `https://www.fotmob.com/api/matchDetails?matchId={match_id}` — Standard FotMob matchDetails API without geo/locale params
- `https://www.fotmob.com/api/matchDetails?matchId={match_id}&ccode3=USA` — FotMob matchDetails API with USA country code for content negotiation
- `https://www.fotmob.com/api/matchDetails?matchId={match_id}&timezone=UTC` — FotMob matchDetails API with UTC timezone override

| Endpoint Template | Attempted | JSON OK | HTML | Blocked | Invalid | Decision |
|---|---:|---:|---:|---:|---:|---|
| `https://www.fotmob.com/api/matchDetails?matchId={match_id}` | 3 | 0 | 0 | 0 | 3 | invalid — investigate endpoint |
| `https://www.fotmob.com/api/matchDetails?matchId={match_id}&c` | 3 | 0 | 0 | 0 | 3 | invalid — investigate endpoint |
| `https://www.fotmob.com/api/matchDetails?matchId={match_id}&t` | 3 | 0 | 0 | 0 | 3 | invalid — investigate endpoint |

## Recommendation

- 当前无 endpoint 返回成功 JSON。
- 建议进入 endpoint review phase，检查 block/invalid 原因。
- 在确认可用 endpoint 前，不要进入 raw JSON write。
