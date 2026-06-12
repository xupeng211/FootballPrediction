# FotMob Parser Dry-run After Synthetic ID Policy

lifecycle: phase-artifact

- Date: 2026-06-12
- Branch: `data/fotmob-parser-dry-run-after-synthetic-id-policy`
- Base main commit: `9a9a29ae08327ba7a6d06eb6ebec94e29aceaae7`
- Scope: rerun latest `main` `FotMobRawParser` against 4 retained `fotmob_live_v1` rows to verify `#1496` synthetic-id / marker-event parser rule behavior
- Safety: SELECT-only; no live fetch; no network request; no DB write; no `raw_match_data` write; no `matches` write; no parser/test/code change; no full raw/pageProps/body saved or printed

## Target Rows

| external_id | db_id | data_version | row_found | parse_ok |
|---|---:|---|---:|---:|
| `4830507` | `33` | `fotmob_live_v1` | 1 | 1 |
| `4830466` | `35` | `fotmob_live_v1` | 1 | 1 |
| `4830461` | `37` | `fotmob_live_v1` | 1 | 1 |
| `4830464` | `39` | `fotmob_live_v1` | 1 | 1 |

## Rule Validation Summary

- `4/4` retained rows were found by SELECT and `4/4` parsed successfully.
- `source_has_native_id` matched raw `eventId/id` presence for `85/85` timeline events.
- `Substitution` rows needing synthetic keys passed `35/35`.
- `AddedTime` + `Half` marker rows passed `16/16` as `marker_event`.
- Non-event sections `match/stats/lineup/shotmap/playerStats/meta` passed `4/4` with no fallback signal.

## Per-row Detail

| external_id | events | Substitution synthetic key | AddedTime marker | Half marker | stats | lineup H/A starters | shots | playerStats keys |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| `4830461` | 22 | `9/9` | `2/2` | `2/2` | 21 | `11/11` | 30 | 40 |
| `4830464` | 21 | `10/10` | `2/2` | `2/2` | 21 | `11/11` | 25 | 40 |
| `4830466` | 19 | `7/7` | `2/2` | `2/2` | 21 | `11/11` | 54 | 40 |
| `4830507` | 23 | `9/9` | `2/2` | `2/2` | 21 | `11/11` | 27 | 40 |

## Non-event No-fallback Check

Validation rule for this rerun:

- `match`: parsed identity fields present and external ID matched the selected row
- `stats`: parsed stats count exactly matched raw `content.stats.Periods.*.stats[]`
- `lineup`: parsed starters/subs counts exactly matched raw lineup arrays on both sides
- `shotmap`: parsed shots count exactly matched raw `content.shotmap.shots`
- `playerStats`: parsed key count exactly matched raw `content.playerStats`
- `meta`: parser emitted expected `dataVersion/hashStrategy/parserVersion`

Result:

- `match`: `4/4`
- `stats`: `4/4`
- `lineup`: `4/4`
- `shotmap`: `4/4`
- `playerStats`: `4/4`
- `meta`: `4/4`

## Conclusion

- Within this retained 4-row sample, latest `main` confirms `#1496` resolved the previously failing parser rule path:
  substitution rows now emit `synthetic_event_key`, and `AddedTime` / `Half` rows are classified as `marker_event`.
- No new parser blocker was observed in this dry-run scope.
- This report does not prove behavior outside these 4 retained rows.
