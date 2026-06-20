# Formal Training Cohort Inventory Dry-Run
- lifecycle: phase-artifact
- date: 2026-06-20
- branch: `data/formal-training-cohort-inventory-dry-run`
- script: `scripts/ops/formal_training_cohort_inventory_dry_run.js`
- test: `tests/unit/formal_training_cohort_inventory_dry_run.test.js`

## Baseline

- current main sha: `19fbcba2e9b2589ca1bc02379a8ae37d40289c73`
- previous task `#1563`: merged into `main`
- `#1563` merge commit: `19fbcba2e9b2589ca1bc02379a8ae37d40289c73`
- visible Production Gate on main: `success`
- visible run: `27868696948`, head sha `19fbcba2e9b2589ca1bc02379a8ae37d40289c73`
- visible jobs: `Environment / Proxy / Static / Unit Gate=success`, `Docker Build Validation=success`

## Safety

- Read-only only: `BEGIN READ ONLY` + SELECT/WITH queries + `ROLLBACK`.
- No DB write, no raw write, no schema migration, no live fetch, no new data capture.
- No model training, no model file generation, no prediction execution.
- No raw payload / full pageProps / full JSON output.
- Existing data governance conclusions were not changed.

## Inventory Result

| Metric | Count |
| --- | ---: |
| `matches` | 60 |
| finished + valid labeled | 59 |
| `is_training_eligible=true` | 58 |
| formal cohort candidates | 58 |
| `raw_match_data` rows / matches | 76 / 60 |
| `fotmob_pageprops_v2` rows / matches | 8 / 8 |
| odds rows / matches | 2 / 1 |
| formal candidates with odds | 0 |

Threshold gaps from current formal candidates:

| Target | Current | Gap |
| ---: | ---: | ---: |
| 1500 | 58 | 1442 |
| 3000 | 58 | 2942 |
| 5000 | 58 | 4942 |

## League / Season

| League | Season | Matches | Finished+labeled | Training eligible | Formal candidates |
| --- | --- | ---: | ---: | ---: | ---: |
| Ligue 1 | 2025/2026 | 58 | 58 | 58 | 58 |
| Segunda | 2024/2025 | 1 | 1 | 0 | 0 |
| Segunda División | 2025/2026 | 1 | 0 | 0 | 0 |

Finished + labeled distribution:
- Ligue 1 2025/2026: home_win=23, draw=17, away_win=18
- Segunda 2024/2025: home_win=1

Training eligible distribution:
- Ligue 1 2025/2026: home_win=23, draw=17, away_win=18

## Raw / Odds Coverage

`raw_match_data` raw/source versions:
- `fotmob_live_v1`, source_version=`unknown`, hash_strategy=`stable_raw_payload_v1`: 58 rows / 58 matches
- `fotmob_pageprops_v2`, source_version=`unknown`, hash_strategy=`stable_pageprops_payload_v1`: 8 rows / 8 matches
- `fotmob_html_hyd_v1`, source_version=`unknown`, hash_strategy=`stable_raw_payload_v1`: 7 rows / 7 matches
- `fotmob_html_hyd_v1`, source_version=`unknown`, hash_strategy=`unknown`: 1 row / 1 match
- `PHASE4.23`, source_version=`unknown`, hash_strategy=`unknown`: 1 row / 1 match
- `PHASE4.43_SYNTHETIC`, source_version=`unknown`, hash_strategy=`unknown`: 1 row / 1 match

Severe missing fields / coverage gaps:
- schema absent: `home_team_id`, `away_team_id`, `league_id`, `prediction_cutoff_time`, `feature_observed_at`
- `venue_missing=60/60`
- `referee_missing=60/60`
- formal candidate `fotmob_pageprops_v2` gap: `50/58`
- formal candidate odds gap: `58/58`

## Formal Candidate Matches

All 58 are Ligue 1 2025/2026 finished, valid-labeled, `is_training_eligible=true`, and not in explicit exclusions:

`53_20252026_4830466`, `53_20252026_4830461`, `53_20252026_4830463`, `53_20252026_4830465`, `53_20252026_4830460`, `53_20252026_4830458`, `53_20252026_4830459`, `53_20252026_4830462`, `53_20252026_4830464`, `53_20252026_4830473`
`53_20252026_4830471`, `53_20252026_4830472`, `53_20252026_4830470`, `53_20252026_4830469`, `53_20252026_4830467`, `53_20252026_4830474`, `53_20252026_4830475`, `53_20252026_4830468`, `53_20252026_4830478`, `53_20252026_4830479`
`53_20252026_4830482`, `53_20252026_4830484`, `53_20252026_4830476`, `53_20252026_4830477`, `53_20252026_4830481`, `53_20252026_4830483`, `53_20252026_4830480`, `53_20252026_4830488`, `53_20252026_4830490`, `53_20252026_4830485`
`53_20252026_4830487`, `53_20252026_4830486`, `53_20252026_4830489`, `53_20252026_4830491`, `53_20252026_4830493`, `53_20252026_4830492`, `53_20252026_4830498`, `53_20252026_4830501`, `53_20252026_4830495`, `53_20252026_4830497`
`53_20252026_4830502`, `53_20252026_4830494`, `53_20252026_4830496`, `53_20252026_4830500`, `53_20252026_4830499`, `53_20252026_4830510`, `53_20252026_4830505`, `53_20252026_4830511`, `53_20252026_4830508`, `53_20252026_4830507`
`53_20252026_4830746`, `53_20252026_4830747`, `53_20252026_4830748`, `53_20252026_4830750`, `53_20252026_4830751`, `53_20252026_4830752`, `53_20252026_4830753`, `53_20252026_4830754`

## Must Exclude

- `47_20242025_900002`: synthetic invalid legacy sample, not real FotMob evidence; keep excluded.
- `140_20252026_4837496`: scheduled/no valid outcome with synthetic invalid evidence; keep excluded.

## Conclusion

- Current 58 rows are only smoke/integration inventory. They cannot support formal training.
- Next step is not model training.
- Next step should be multi-league, multi-season data expansion planning.
- Actual new data fetch, DB write, raw write, raw payload capture, or real model training must stop and request explicit user authorization first.
