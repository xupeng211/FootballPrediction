# FotMob L2 Raw-Exists Pending Anomaly Audit - 2026-06-14

- lifecycle: phase-artifact
- scope: read-only anomaly audit
- source script: `scripts/ops/l2_raw_exists_pending_anomaly_audit.js`
- related transition preview: `docs/_reports/fotmob_l2_pending_transition_preview_20260614.md`
- related design: `docs/architecture/FOTMOB_L2_GUARDED_PENDING_CONSUMER_DESIGN.md`

## 1. Purpose / 目的

本报告只读审计 `raw_match_data` 已存在、但 `matches.pipeline_status` 仍为 `pending` 的 anomaly，用来判断这批 target 更像历史 raw retained 后未同步状态，还是仍应被 future consumer 当作新 claim 目标。

## 2. Safety Boundary / 安全边界

- no FotMob live fetch
- no scraper
- no browser
- no DB write
- no raw_match_data write
- no matches update
- no pipeline_status update
- no parser/model/feature/schema change
- no raw payload output

## 3. Anomaly Rule / 异常规则

- `matches.pipeline_status = pending`
- `external_id` 非空
- `raw_match_data` 存在同 `match_id + data_version = fotmob_live_v1`
- 本 PR 不修复，不回填状态，不执行真实 claim

## 4. Command / 执行命令

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node --test tests/unit/scripts/ops/l2_raw_exists_pending_anomaly_audit.test.js
```

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_raw_exists_pending_anomaly_audit.js --limit 50 --json
```

## 5. Result / 结果

Audit 执行成功。

- anomaly_total: `58`
- raw_row_count: `58`
- duplicate_raw_count: `0`
- oldest_match_date: `2025-08-15T18:45:00.000Z`
- newest_match_date: `2026-05-10T19:00:00.000Z`
- by_league: `Ligue 1 = 58`
- by_season: `2025/2026 = 58`
- by_match_status: `finished = 58`
- raw_data_version_counts: `fotmob_live_v1 / anomaly_count=58 / raw_row_count=58`
- raw timestamp source:
  - `raw_created_at_source = collected_at`
  - `raw_updated_at_source = collected_at`
- observed `raw_match_data` columns:
  - `id`, `match_id`, `external_id`, `raw_data`, `collected_at`, `data_version`, `data_hash`

说明：

- 当前表结构里没有额外的 `ingestion_run_id`、`created_by`、`route` 一类列，所以 `raw_source_hint` 只能安全写成 `raw_match_data:data_version=fotmob_live_v1`。
- 本次 audit 没发现 `fotmob_live_v1` 同一 `match_id` 的重复 raw row。

sample anomalies（节选 10 条，完整 sample 运行时 limit=50）：

| match_id | external_id | league_name | season | home_team | away_team | match_date | match_status | pipeline_status | raw_data_version | raw_created_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `53_20252026_4830466` | `4830466` | `Ligue 1` | `2025/2026` | `Rennes` | `Marseille` | `2025-08-15T18:45:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-10T08:14:17.296Z` |
| `53_20252026_4830461` | `4830461` | `Ligue 1` | `2025/2026` | `Lens` | `Lyon` | `2025-08-16T15:00:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-10T08:14:24.149Z` |
| `53_20252026_4830463` | `4830463` | `Ligue 1` | `2025/2026` | `Monaco` | `Le Havre` | `2025-08-16T17:00:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-12T18:11:11.250Z` |
| `53_20252026_4830465` | `4830465` | `Ligue 1` | `2025/2026` | `Nice` | `Toulouse` | `2025-08-16T19:05:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-12T18:11:15.025Z` |
| `53_20252026_4830460` | `4830460` | `Ligue 1` | `2025/2026` | `Brest` | `Lille` | `2025-08-17T13:00:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-12T18:11:18.237Z` |
| `53_20252026_4830458` | `4830458` | `Ligue 1` | `2025/2026` | `Angers` | `Paris FC` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-12T18:11:24.488Z` |
| `53_20252026_4830459` | `4830459` | `Ligue 1` | `2025/2026` | `Auxerre` | `Lorient` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-12T18:11:28.401Z` |
| `53_20252026_4830462` | `4830462` | `Ligue 1` | `2025/2026` | `Metz` | `Strasbourg` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-12T18:11:32.647Z` |
| `53_20252026_4830464` | `4830464` | `Ligue 1` | `2025/2026` | `Nantes` | `Paris Saint-Germain` | `2025-08-17T18:45:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-10T08:14:31.389Z` |
| `53_20252026_4830473` | `4830473` | `Ligue 1` | `2025/2026` | `Paris Saint-Germain` | `Angers` | `2025-08-22T18:45:00.000Z` | `finished` | `pending` | `fotmob_live_v1` | `2026-06-12T18:11:38.045Z` |

## 6. Interpretation / 结果解读

- 这 `58` 条 anomaly 已被确认存在，而且全部集中在 `Ligue 1 / 2025/2026 / finished`。
- 从只读证据看，它们很像一批已经 retained raw 的比赛，但 `matches.pipeline_status` 没有同步离开 `pending`。这是推断，不是写库结论。
- 当前不能直接做 `pending -> processing`。如果直接 claim，这 `58` 条会被误认为“还没采集”的新目标，和已有 raw 事实冲突。
- 当前也不能直接批量改成 `harvested`。`raw exists` 只能证明本地存在 `fotmob_live_v1` row，不能自动证明当时预期状态机、失败恢复、或后续 reconciliation 语义已经满足。
- 更稳妥的方向是先做 reconciliation preview，先只读模拟“哪些 pending + raw_exists 可能建议转成 harvested”，而不是直接写状态。

## 7. Next Recommended Task / 下一步建议

- 建议下一 PR 先做 read-only reconciliation preview，模拟哪些 `pending + raw_exists(fotmob_live_v1)` rows 可以被建议标记为 `harvested`，但仍然不写 DB；只有 preview 口径稳定后，才讨论 guarded reconciliation write。
- Do not start automatically
- Recommended next task only after user confirmation
