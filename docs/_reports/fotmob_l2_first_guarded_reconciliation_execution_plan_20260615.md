# FotMob L2 First Guarded Reconciliation Execution Plan - 2026-06-15
- lifecycle: phase-artifact
- scope: first guarded reconciliation execution plan only
- related write draft: `scripts/ops/l2_guarded_reconciliation_write.js`
- related design: `docs/architecture/FOTMOB_L2_GUARDED_RECONCILIATION_WRITE_DESIGN.md`
- no real write executed: yes
- no `--allow-write` executed: yes

## 1. Purpose / 目的
本报告只记录首次小批量 guarded reconciliation execution plan，用于未来最多 `3` 条 `pending -> harvested` 的真实执行前准备；本 PR 不执行真实写库。
## 2. Safety Boundary / 安全边界
- no FotMob live fetch
- no scraper
- no browser
- no raw_match_data write
- no raw payload output
- no real DB write
- no real matches update
- no real pipeline_status update
- no parser/model/feature/schema change
- no `--allow-write` command executed
## 3. Candidate Source / 候选来源
候选来自以下 dry-run：
```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_guarded_reconciliation_write.js --limit 3 --json
```
- candidate_total: `58`
- selected_count: `3`
- would_update_count: `3`
- actual_update_executed: `false`
## 4. First Batch Candidates / 首批候选
| order | match_id | external_id | league_name | season | home_team | away_team | match_date | before_status | planned_after_status | raw_data_version | raw_row_count | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `53_20252026_4830466` | `4830466` | `Ligue 1` | `2025/2026` | `Rennes` | `Marseille` | `2025-08-15T18:45:00.000Z` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `pending_with_single_complete_fotmob_live_v1_raw` |
| 2 | `53_20252026_4830461` | `4830461` | `Ligue 1` | `2025/2026` | `Lens` | `Lyon` | `2025-08-16T15:00:00.000Z` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `pending_with_single_complete_fotmob_live_v1_raw` |
| 3 | `53_20252026_4830463` | `4830463` | `Ligue 1` | `2025/2026` | `Monaco` | `Le Havre` | `2025-08-16T17:00:00.000Z` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `pending_with_single_complete_fotmob_live_v1_raw` |
## 5. Eligibility Checklist / 执行资格检查
这 3 条在本次 dry-run 中都满足：
- `pipeline_status = pending`
- `external_id` 非空
- `match_status = finished`
- `raw_match_data.data_version = fotmob_live_v1`
- `raw_row_count = 1`
- `raw_data` / `data_hash` 信号存在
- no external_id mismatch
- `decision = would_update`
## 6. Proposed Execution Command Draft / 未来执行命令草稿
```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_guarded_reconciliation_write.js \
  --limit 3 \
  --expected-count 3 \
  --allow-write \
  --json
```
This command was NOT executed in this PR.
## 7. Stop Gates / 停止条件
未来真实执行前，只要出现以下任一情况，必须停止：
- `candidate_total` 不是预期值
- `selected_count` 不是 `3`
- 任意 `match_id` 与本计划不一致
- 任意 `before_status` 不是 `pending`
- 任意 `raw_row_count` 不是 `1`
- 任意 hold reason 出现
- CI 不绿
- 用户没有明确授权
- 命令中缺少 `--expected-count`
- 执行前无法生成 before snapshot
## 8. Rollback Plan / 回滚方案
未来如果真实执行后发现问题，回滚范围只能限于本批 `3` 条：
```sql
UPDATE matches
SET pipeline_status = 'pending'
WHERE match_id IN (
  '53_20252026_4830466',
  '53_20252026_4830461',
  '53_20252026_4830463'
)
  AND pipeline_status = 'harvested';
```
Rollback SQL is documented only and was NOT executed.
## 9. Verification Plan / 执行后验证方案
未来真实执行后必须立刻做 read-only verification：
- 查询这 `3` 条 `matches.pipeline_status` 是否为 `harvested`
- 查询对应 `raw_match_data` 是否仍存在
- 确认 `raw_match_data` 未被改动
- 确认没有额外 `match_id` 被更新
- 生成 verification report
- 不抓 FotMob
- 不输出 raw payload
## 10. Risk Assessment / 风险评估
- 真实写库虽然只改状态，但仍会改变系统后续调度行为
- 首次最多只能执行 `3` 条
- 首批成功后也不能立刻全量推进 `58` 条
- 必须先完成首批执行后的只读 verification
## 11. Next Recommended Task / 下一步建议
- 用户明确授权后，才允许执行首批 `<=3` 条 guarded reconciliation write。
- 执行后必须生成 read-only verification report。
- Do not start automatically
- Recommended next task only after user confirmation
