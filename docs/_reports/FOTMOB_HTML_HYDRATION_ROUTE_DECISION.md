<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 -->

# FotMob HTML Hydration Route Probe — Decision Report

## Route Templates Tested

- `https://www.fotmob.com/match/{match_id}` — html_hydration_match_page
- `https://www.fotmob.com/matches/{route_code}/{match_id}` — html_hydration_matches_page

| Route Template | Attempted | HTML Observed | Redirect | Blocked | Invalid | Decision |
|---|---:|---:|---:|---:|---:|---|
| `https://www.fotmob.com/match/{match_id}` | 3 | 3 | 0 | 0 | 0 | use — recommend for extraction plan |
| `https://www.fotmob.com/matches/{route_code}/{match_id}` | 3 | 3 | 0 | 0 | 0 | use — recommend for extraction plan |

## Recommendation

- 至少一个 HTML route 返回 200。
- 下一阶段建议：HTML hydration extraction plan no-write。
- 仍然不直接 raw write。

