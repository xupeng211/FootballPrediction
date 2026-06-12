# FotMob Parser 24 Retained Dry-run

lifecycle: phase-artifact

- Date: `2026-06-12`
- Branch: `data/fotmob-parser-24-retained-dry-run`
- Base main commit: `4ff8dc453a09cf9307a0774b9158309b4cbe0a1f`
- Scope: SELECT-only rerun latest `main` `FotMobRawParser` against all retained `raw_match_data` rows where `data_version='fotmob_live_v1'`
- Safety: no live fetch; no FotMob network; no DB write; no `raw_match_data` write; no `matches` write; no parser change; no test change; no full raw/pageProps/body saved or printed

## Dry-run Summary

- Retained rows found: `24/24`
- Parse success: `24/24`
- Parse failure: `0/24`
- Events parity: `24/24` rows; raw timeline events `446/446` preserved
- `source_has_native_id` alignment: `446/446`
- `Substitution` synthetic key: `197/197`; missing `reactKey`: `0`; duplicate-key rows: `0`
- `AddedTime` `marker_event`: `45/45`
- `Half` `marker_event`: `46/46`
- New null-id `real_event` types: none
- No-fallback sections: `match 24/24`, `stats 24/24`, `lineup 24/24`, `shotmap 24/24`, `playerStats 24/24`, `meta 24/24`
- New blocker: none in this read-only parser dry-run scope

## Row Detail

| external_id | db_id | events | Sub synth | AddedTime | Half | stats | lineup H/A | shots | playerStats |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| `4830461` | `37` | 22 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 30 | 40 |
| `4830464` | `39` | 21 | `10/10` | `2/2` | `2/2` | 21 | `11+9/11+9` | 25 | 40 |
| `4830466` | `35` | 19 | `7/7` | `2/2` | `2/2` | 21 | `11+9/11+9` | 54 | 40 |
| `4830494` | `67` | 15 | `7/7` | `2/2` | `2/2` | 21 | `11+9/11+9` | 20 | 40 |
| `4830495` | `77` | 24 | `8/8` | `2/2` | `2/2` | 21 | `11+10/11+9` | 27 | 40 |
| `4830496` | `69` | 20 | `10/10` | `2/2` | `2/2` | 21 | `11+9/11+9` | 20 | 40 |
| `4830497` | `75` | 22 | `10/10` | `2/2` | `2/2` | 21 | `11+9/11+9` | 18 | 40 |
| `4830499` | `65` | 21 | `8/8` | `2/2` | `2/2` | 21 | `11+9/11+9` | 32 | 40 |
| `4830500` | `71` | 17 | `9/9` | `1/1` | `2/2` | 21 | `11+9/11+9` | 28 | 40 |
| `4830501` | `79` | 22 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 38 | 40 |
| `4830502` | `73` | 13 | `7/7` | `2/2` | `2/2` | 21 | `11+9/11+9` | 23 | 40 |
| `4830505` | `61` | 18 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 28 | 40 |
| `4830507` | `33` | 23 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 27 | 40 |
| `4830508` | `57` | 13 | `7/7` | `2/2` | `2/2` | 21 | `11+9/11+7` | 24 | 38 |
| `4830510` | `63` | 22 | `8/8` | `2/2` | `2/2` | 21 | `11+9/11+9` | 22 | 40 |
| `4830511` | `59` | 0 | `0/0` | `0/0` | `0/0` | 14 | `11+9/11+9` | 4 | 40 |
| `4830746` | `41` | 22 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 26 | 40 |
| `4830747` | `43` | 17 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 22 | 40 |
| `4830748` | `45` | 21 | `8/8` | `2/2` | `2/2` | 21 | `11+9/11+9` | 18 | 40 |
| `4830750` | `47` | 21 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 22 | 40 |
| `4830751` | `49` | 20 | `10/10` | `2/2` | `2/2` | 21 | `11+9/11+9` | 15 | 40 |
| `4830752` | `51` | 12 | `7/7` | `2/2` | `2/2` | 21 | `11+9/11+9` | 26 | 40 |
| `4830753` | `53` | 17 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 25 | 40 |
| `4830754` | `55` | 24 | `9/9` | `2/2` | `2/2` | 21 | `11+9/11+9` | 32 | 40 |

## Notes

- `4830511` kept an empty raw timeline (`events=0`) and lower-cardinality stats/shotmap (`14` stats, `4` shots); parser preserved that shape without fallback.
- `4830495` home bench count `10` and `4830508` away bench count `7` / `playerStats=38` were preserved exactly from raw; these are shape variations, not parser regressions.
- This dry-run validates parser behavior only for the 24 retained `fotmob_live_v1` raws already stored locally. It does not authorize feature extraction, training, prediction, network access, or any DB/raw write.

## Validation

```bash
git diff --check
python3 scripts/ops/ai_workflow_gate.py --pr-body-file /tmp/pr_body_draft.md
```
