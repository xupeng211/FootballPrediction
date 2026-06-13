# FotMob L2 Pending Target Selection Dry-Run Result - 2026-06-13

- lifecycle: phase-artifact
- scope: read-only dry-run result
- source script: `scripts/ops/l2_pending_target_selection_dry_run.js`
- related PR: #1505
- related contract: `docs/architecture/FOTMOB_L1_L2_HANDOFF_CONTRACT.md`

## 1. Purpose / 目的

本报告只记录一次默认 read-only dry-run 和一次可选 `--include-failed` dry-run 结果，用于验证当前 `matches + pipeline_status` contract 下 L2 会选中哪些目标。

## 2. Safety Boundary / 安全边界

- no FotMob live fetch
- no scraper
- no browser
- no DB write
- no raw_match_data write
- no matches update
- no pipeline_status update
- no parser/model/feature/schema change

## 3. Command / 执行命令

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_pending_target_selection_dry_run.js --limit 10 --json
```

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_pending_target_selection_dry_run.js --limit 10 --include-failed --json
```

## 4. Default Dry-Run Result / 默认 dry-run 结果

- selected_count: `60`
- total_pending_candidates: `60`
- missing_external_id_count: `0`
- already_processing_count: `0`
- already_harvested_count: `0`
- failed_count: `0`
- skipped_count: `0`
- oldest_match_date: `2024-08-17T17:30:00.000Z`
- newest_match_date: `2026-05-24T17:00:00.000Z`

by_league:

- `Ligue 1`: `58`
- `Segunda`: `1`
- `Segunda División`: `1`

by_season:

- `2025/2026`: `59`
- `2024/2025`: `1`

sample_targets:

| match_id | external_id | league_name | season | home_team | away_team | match_date | status | pipeline_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `47_20242025_900002` | `900002` | `Segunda` | `2024/2025` | `Burgos` | `Oviedo` | `2024-08-17T17:30:00.000Z` | `finished` | `pending` |
| `53_20252026_4830466` | `4830466` | `Ligue 1` | `2025/2026` | `Rennes` | `Marseille` | `2025-08-15T18:45:00.000Z` | `finished` | `pending` |
| `53_20252026_4830461` | `4830461` | `Ligue 1` | `2025/2026` | `Lens` | `Lyon` | `2025-08-16T15:00:00.000Z` | `finished` | `pending` |
| `53_20252026_4830463` | `4830463` | `Ligue 1` | `2025/2026` | `Monaco` | `Le Havre` | `2025-08-16T17:00:00.000Z` | `finished` | `pending` |
| `53_20252026_4830465` | `4830465` | `Ligue 1` | `2025/2026` | `Nice` | `Toulouse` | `2025-08-16T19:05:00.000Z` | `finished` | `pending` |
| `53_20252026_4830460` | `4830460` | `Ligue 1` | `2025/2026` | `Brest` | `Lille` | `2025-08-17T13:00:00.000Z` | `finished` | `pending` |
| `53_20252026_4830458` | `4830458` | `Ligue 1` | `2025/2026` | `Angers` | `Paris FC` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` |
| `53_20252026_4830459` | `4830459` | `Ligue 1` | `2025/2026` | `Auxerre` | `Lorient` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` |
| `53_20252026_4830462` | `4830462` | `Ligue 1` | `2025/2026` | `Metz` | `Strasbourg` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` |
| `53_20252026_4830464` | `4830464` | `Ligue 1` | `2025/2026` | `Nantes` | `Paris Saint-Germain` | `2025-08-17T18:45:00.000Z` | `finished` | `pending` |

## 5. Include-Failed Dry-Run Result / include-failed dry-run 结果

- 已运行 `--include-failed`
- selected_count: `60`
- total_pending_candidates: `60`
- failed_count: `0`
- 结果与默认 dry-run 一致，说明当前 dev DB 中没有额外 `pipeline_status = failed` 且可被本规则扩展选中的目标

## 6. Interpretation / 结果解读

- 当前 dev DB 里存在 L2 可消费 pending targets，而且数量不是 0；按当前 contract 和默认 rule，会选中 `60` 条候选。
- 从样本看，当前被选中的目标几乎都处于 `status=finished`、`pipeline_status=pending`，说明当前 `matches` 中已经存在一批等待 L2 消费但尚未进入 processing/harvested 的记录。
- `Segunda` 和 `Segunda División` 同时出现，说明当前 dev DB 里存在 league naming 不完全收敛的现象；这不阻止 dry-run 选中目标，但值得后续只读审视。
- selection dry-run 证明当前规则能选出候选，但 live fetch / raw retention 仍需单独 PR 和用户确认，不自动开始。

## 7. Next Recommended Task / 下一步建议

- 建议下一 PR 只做 guarded L2 pending consumer 或 state transition workflow design，先明确如何安全消费这 `60` 条 pending targets，不直接 live fetch。
- Do not start automatically
- Recommended next task only after user confirmation
