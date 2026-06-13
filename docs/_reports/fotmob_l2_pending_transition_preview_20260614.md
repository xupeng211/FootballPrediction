# FotMob L2 Pending Transition Preview - 2026-06-14

- lifecycle: phase-artifact
- scope: read-only transition preview
- source script: `scripts/ops/l2_pending_transition_preview.js`
- related design: `docs/architecture/FOTMOB_L2_GUARDED_PENDING_CONSUMER_DESIGN.md`
- related dry-run result: `docs/_reports/fotmob_l2_pending_target_selection_dry_run_result_20260613.md`

## 1. Purpose / 目的

本报告记录一次 read-only transition preview，用于模拟 future `pending -> processing` claim，但不写 DB。

## 2. Safety Boundary / 安全边界

- no FotMob live fetch
- no scraper
- no browser
- no DB write
- no raw_match_data write
- no matches update
- no pipeline_status update
- no parser/model/feature/schema change

## 3. Preview Rule / Preview 规则

- 基础候选：`external_id` 非空 + `pipeline_status = pending`
- preview transition：`pending -> processing`
- `raw_match_data` 已存在 `match_id + data_version=fotmob_live_v1` 且仍为 pending，会被标记为 `anomaly`
- `status != finished` 的 pending target 会被单独统计为 `non_finished_pending`
- 本 PR 不执行真实 claim

## 4. Command / 执行命令

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node --test tests/unit/scripts/ops/l2_pending_transition_preview.test.js
```

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_pending_transition_preview.js --limit 10 --json
```

## 5. Result / 结果

Preview 执行成功。

- pending_with_external_id: `60`
- would_claim_count: `1`
- anomaly_raw_exists_but_pending_count: `58`
- missing_external_id_count: `0`
- non_finished_pending_count: `1`

sample would_claim rows:

| match_id | external_id | league_name | season | home_team | away_team | match_date | status | pipeline_status | raw_exists | preview_decision | preview_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `47_20242025_900002` | `900002` | `Segunda` | `2024/2025` | `Burgos` | `Oviedo` | `2024-08-17T17:30:00.000Z` | `finished` | `pending` | `false` | `would_claim` | `pending_with_external_id_and_no_fotmob_live_v1_raw` |

sample anomaly rows:

| match_id | external_id | league_name | season | home_team | away_team | match_date | status | pipeline_status | raw_exists | preview_decision | preview_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `53_20252026_4830466` | `4830466` | `Ligue 1` | `2025/2026` | `Rennes` | `Marseille` | `2025-08-15T18:45:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830461` | `4830461` | `Ligue 1` | `2025/2026` | `Lens` | `Lyon` | `2025-08-16T15:00:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830463` | `4830463` | `Ligue 1` | `2025/2026` | `Monaco` | `Le Havre` | `2025-08-16T17:00:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830465` | `4830465` | `Ligue 1` | `2025/2026` | `Nice` | `Toulouse` | `2025-08-16T19:05:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830460` | `4830460` | `Ligue 1` | `2025/2026` | `Brest` | `Lille` | `2025-08-17T13:00:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830458` | `4830458` | `Ligue 1` | `2025/2026` | `Angers` | `Paris FC` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830459` | `4830459` | `Ligue 1` | `2025/2026` | `Auxerre` | `Lorient` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830462` | `4830462` | `Ligue 1` | `2025/2026` | `Metz` | `Strasbourg` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830464` | `4830464` | `Ligue 1` | `2025/2026` | `Nantes` | `Paris Saint-Germain` | `2025-08-17T18:45:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |
| `53_20252026_4830473` | `4830473` | `Ligue 1` | `2025/2026` | `Paris Saint-Germain` | `Angers` | `2025-08-22T18:45:00.000Z` | `finished` | `pending` | `true` | `anomaly` | `raw_exists_for_fotmob_live_v1_but_pipeline_status_pending` |

补充观察：

- non_finished_pending sample:
  - `140_20252026_4837496` / `4837496` / `Segunda División` / `status=scheduled`

## 6. Interpretation / 结果解读

- 当前 future claim 不会命中 60 条中的大多数；真实可直接 claim 的只有 `1` 条。
- 当前最大的信号不是“pending 很多”，而是 `58` 条出现 `raw exists but pending`。这说明 `pipeline_status` 与 `raw_match_data` 当前并不一致，不能把这批 rows 当成干净的 claim 目标直接推进。
- 当前还有 `1` 条 `non-finished pending`，说明 future guarded consumer 不能默认把所有 pending 都视为可安全领取的 finished target。
- 不能自动开始写库，也不能自动开始真实 `pending -> processing` 更新；仍然需要用户确认和单独 PR。

## 7. Next Recommended Task / 下一步建议

- 建议下一 PR 先做 read-only anomaly audit，专门解释为什么会出现 `raw exists but pending` 的 58 条异常，再决定是否实现 guarded state transition script；即便后续进入 state transition，也必须默认 no-op，写库必须 `--allow-write`，batch size `<= 3`。
- Do not start automatically
- Recommended next task only after user confirmation
