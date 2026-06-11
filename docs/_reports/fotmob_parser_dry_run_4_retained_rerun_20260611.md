# FotMob Parser Dry-run Rerun — 4 Retained Rows

lifecycle: phase-artifact

- Date: 2026-06-11
- Branch: `data/fotmob-parser-dry-run-4-retained-rerun`
- Base main commit: `ca3e9810180bf89a14fa89e62a4695c55d0bcab6`
- Scope: rerun `FotMobRawParser` against 4 retained `raw_match_data` rows after `#1493`
- Safety: SELECT-only; no live fetch, no browser, no external network, no DB write, no raw write, no full raw/pageProps/HTML/raw_data saved or printed

## Targets

| external_id | data_version | row_found | parse_ok |
|---|---|---:|---:|
| `4830507` | `fotmob_live_v1` | 1 | 1 |
| `4830466` | `fotmob_live_v1` | 1 | 1 |
| `4830461` | `fotmob_live_v1` | 1 | 1 |
| `4830464` | `fotmob_live_v1` | 1 | 1 |

## Event Validation

| external_id | events | id_non_null | minute_non_null | teamSide_valid | type/card/score_valid |
|---|---:|---:|---:|---:|---:|
| `4830461` | 22 | 9 | 22 | 22 | 22 |
| `4830464` | 21 | 7 | 21 | 21 | 21 |
| `4830466` | 19 | 8 | 19 | 19 | 19 |
| `4830507` | 23 | 10 | 23 | 23 | 23 |

- `minute` mapping passed for `85/85` events.
- `teamSide` matched raw `isHome` whenever source provided it; marker rows without `isHome` stayed `null`.
- `playerId` / `playerName` matched source payload when source fields existed.
- `type` / `card` / `homeScore` / `awayScore` matched source payload for `85/85` events.
- `event.id` remained `null` for `51/85` events, so strict `event.id != null` acceptance did not pass.
- Null-id event types across the 4 retained rows: `Substitution=35`, `AddedTime=8`, `Half=8`.
- Those null-id rows also lacked both raw `eventId` and raw `id`; substitution rows additionally lacked player identity/name in the retained raw event object.

## Non-event Regression Check

- `match`: pass on 4/4
- `stats`: pass on 4/4
- `lineup`: pass on 4/4
- `shotmap`: pass on 4/4
- `playerStats`: pass on 4/4
- `meta`: pass on 4/4

## Conclusion

- `#1493` fixed the real-field mapping for events that carry `eventId` / `time|timeStr` / `isHome` / player fields.
- This rerun does **not** qualify as a full pass because `event.id` is still null on many timeline entries.
- Further parser handling/design is required before claiming the 4 retained rows events validation is fully green.
