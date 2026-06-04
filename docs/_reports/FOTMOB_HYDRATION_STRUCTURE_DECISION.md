<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 -->

# FotMob Hydration Structure — Decision Report

| Route Template | Attempted | Marker | Structure | Missing | Blocked | Invalid | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `https://www.fotmob.com/match/{match_id}` | 2 | 0 | 0 | 2 | 0 | 0 | review |
| `https://www.fotmob.com/matches/{route_code}/{match_id}` | 2 | 2 | 2 | 0 | 0 | 0 | use — viable for extraction |

## Recommendation

- 发现 hydration marker。
- 下一阶段建议：hydration structure validation no-write。
- 仍然不直接 raw write。

