# FotMob Parser Expanded Retained Dry-run

lifecycle: phase-artifact

- Date: 2026-06-12
- Branch: `data/fotmob-parser-expanded-retained-dry-run`
- Base main commit: `8e5374a7d81c2ce53e48209a32ef8932dfacb7f8`
- Scope: check whether `raw_match_data` contains enough existing `fotmob_live_v1` retained rows to expand the retained-sample `FotMobRawParser` dry-run beyond the original 4 rows
- Safety: SELECT-only; no live fetch; no FotMob network; no browser; no DB write; no `raw_match_data` write; no `matches` write; no parser/test/code change; no full raw/pageProps/body saved or printed

## Retained Inventory Result

- `raw_match_data` rows with `data_version = 'fotmob_live_v1'`: `4`
- Expanded retained sample target: `>4` rows, capped at `20`
- Outcome: current retained sample is insufficient, so expanded dry-run was **not executed**

## Current Retained Rows

| external_id | db_id | data_version | data_hash12 |
|---|---:|---|---|
| `4830507` | `33` | `fotmob_live_v1` | `ed2b29723006` |
| `4830466` | `35` | `fotmob_live_v1` | `3ecf1c7dd8bb` |
| `4830461` | `37` | `fotmob_live_v1` | `1f9dcc93dec6` |
| `4830464` | `39` | `fotmob_live_v1` | `38998bca35b6` |

## Required 4-row Inclusion Check

- Required legacy retained sample present: `4/4`
- Required IDs confirmed:
  `4830507`, `4830466`, `4830461`, `4830464`

## Expanded Dry-run Status

- Parser executed against expanded retained sample: `no`
- Reason: there are no additional retained `fotmob_live_v1` rows beyond the original 4-row sample
- Parse success rate: `n/a`
- Events success rate: `n/a`
- Substitution `synthetic_event_key` stability: `n/a`
- AddedTime / Half `marker_event` stability: `n/a`
- `source_has_native_id` reasonableness: `n/a`
- `match/stats/lineup/shotmap/playerStats/meta` no-fallback check: `n/a`
- New null-id `real_event` types: `n/a`
- Parser exceptions: `n/a`

## Conclusion

- The repository currently does **not** contain enough stored `fotmob_live_v1` retained rows to expand the retained parser dry-run sample.
- No new raw was fetched and no parser rerun was performed, because doing so would not satisfy the requested “expanded sample” goal.
- Any future expanded retained dry-run requires more already-stored retained rows first; this report does not authorize fetching or writing any new data.
