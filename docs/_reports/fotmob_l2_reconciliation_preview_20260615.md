# FotMob L2 Reconciliation Preview - 2026-06-15

- lifecycle: phase-artifact
- scope: read-only reconciliation preview
- source script: `scripts/ops/l2_reconciliation_preview.js`
- related anomaly audit: `docs/_reports/fotmob_l2_raw_exists_pending_anomaly_audit_20260614.md`
- related transition preview: `docs/_reports/fotmob_l2_pending_transition_preview_20260614.md`
- related design: `docs/architecture/FOTMOB_L2_GUARDED_PENDING_CONSUMER_DESIGN.md`

## 1. Purpose / 目的

本报告只读模拟哪些 `pending + raw_exists(fotmob_live_v1)` rows 可以被建议转成 `harvested`，但不写 DB。

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

## 3. Preview Rule / Preview 规则

- `matches.pipeline_status = pending`
- `external_id` 非空
- `raw_match_data` 存在同 `match_id + data_version=fotmob_live_v1`
- `status = finished`
- 无重复 raw
- `raw_data` 与 `data_hash` 基础完整性信号存在
- 本 PR 不修复，不回填状态，不执行真实 `harvested` update

## 4. Command / 执行命令

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node --test tests/unit/scripts/ops/l2_reconciliation_preview.test.js
```

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_reconciliation_preview.js --limit 58 --json
```

## 5. Result / 结果

Preview 执行成功。

- candidate_total: `58`
- suggest_harvested_count: `58`
- hold_duplicate_raw_count: `0`
- hold_non_finished_count: `0`
- hold_missing_hash_or_payload_count: `0`
- hold_external_id_mismatch_count: `0`
- excluded_no_raw_count: `2`
- raw_row_count: `58`
- duplicate_raw_count: `0`
- by_league: `Ligue 1 = 58`
- by_season: `2025/2026 = 58`
- by_match_status: `finished = 58`
- raw_data_version_counts: `fotmob_live_v1 / candidate_count=58 / raw_row_count=58`
- raw signal columns:
  - `external_id_available = true`
  - `raw_data_available = true`
  - `data_hash_available = true`

sample suggest_harvested rows（节选 10 条）：

| match_id | external_id | raw_external_id | league_name | season | home_team | away_team | match_date | match_status | raw_row_count | has_raw_data | has_data_hash | reconciliation_decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `53_20252026_4830466` | `4830466` | `4830466` | `Ligue 1` | `2025/2026` | `Rennes` | `Marseille` | `2025-08-15T18:45:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830461` | `4830461` | `4830461` | `Ligue 1` | `2025/2026` | `Lens` | `Lyon` | `2025-08-16T15:00:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830463` | `4830463` | `4830463` | `Ligue 1` | `2025/2026` | `Monaco` | `Le Havre` | `2025-08-16T17:00:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830465` | `4830465` | `4830465` | `Ligue 1` | `2025/2026` | `Nice` | `Toulouse` | `2025-08-16T19:05:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830460` | `4830460` | `4830460` | `Ligue 1` | `2025/2026` | `Brest` | `Lille` | `2025-08-17T13:00:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830458` | `4830458` | `4830458` | `Ligue 1` | `2025/2026` | `Angers` | `Paris FC` | `2025-08-17T15:15:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830459` | `4830459` | `4830459` | `Ligue 1` | `2025/2026` | `Auxerre` | `Lorient` | `2025-08-17T15:15:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830462` | `4830462` | `4830462` | `Ligue 1` | `2025/2026` | `Metz` | `Strasbourg` | `2025-08-17T15:15:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830464` | `4830464` | `4830464` | `Ligue 1` | `2025/2026` | `Nantes` | `Paris Saint-Germain` | `2025-08-17T18:45:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |
| `53_20252026_4830473` | `4830473` | `4830473` | `Ligue 1` | `2025/2026` | `Paris Saint-Germain` | `Angers` | `2025-08-22T18:45:00.000Z` | `finished` | `1` | `true` | `true` | `suggest_harvested` |

补充观察：

- `hold_sample` 为空，本次 preview 没发现 duplicate raw、non-finished、external_id mismatch 或缺失 `raw_data/data_hash` 的候选。
- `excluded_no_raw_count = 2`，说明还有 `2` 条 `pending + external_id` 记录不属于本次 reconciliation candidate，因为它们没有 `fotmob_live_v1` raw。

## 6. Interpretation / 结果解读

- 当前有 `58` 条 rows 可以被建议标为 `harvested`，而且仍然全部集中在 `Ligue 1 / 2025/2026 / finished`。
- 这只是 read-only 建议，不是写库授权。它证明的是“如果未来做 reconciliation，这 58 条看起来像干净候选”，不是“现在就可以直接批量改状态”。
- 如果未来进入写库阶段，至少要加这些 guard：
  - `WHERE pipeline_status = 'pending'`
  - `EXISTS raw_match_data(match_id, data_version = 'fotmob_live_v1')`
  - batch size `<= 3`
  - explicit `--allow-write`
  - no live fetch
  - per-row audit log / before-after output

## 7. Next Recommended Task / 下一步建议

- 建议下一 PR 做 guarded reconciliation write design，或 no-op-by-default write script draft，但默认仍不写 DB；真正写库必须 `--allow-write`、batch size `<= 3`、且继续禁止 live fetch。
- Do not start automatically
- Recommended next task only after user confirmation
