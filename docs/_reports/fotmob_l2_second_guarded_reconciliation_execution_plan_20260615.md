# FotMob L2 Second Guarded Reconciliation Execution Plan - 2026-06-15
- lifecycle: phase-artifact
- scope: second guarded reconciliation execution plan
- related execution PRs: #1514, #1515
- no real write executed in this PR: yes
- no `--allow-write` executed in this PR: yes
- no FotMob live fetch: yes
- no raw_match_data write: yes
- no raw payload output: yes
## 1. Purpose / 目的
本报告只制定第二批最多 `3` 条 `matches.pipeline_status: pending -> harvested` 的 guarded reconciliation 执行计划；本 PR 不执行真实写库。
## 2. Background / 背景
- #1514 已真实执行首批 `3` 条
- #1515 已完成只读审计
- 首批稳定：`first batch stable = yes`
- 剩余候选池：`55`
- 本 PR 只做第二批计划
## 3. Safety Boundary / 安全边界
- no `--allow-write`
- no DB write
- no UPDATE / INSERT / DELETE
- no FotMob live fetch
- no scraper/browser
- no raw_match_data write
- no raw payload output
- no parser/model/feature/schema change
- no second batch execution in this PR
## 4. Dry-run Result / dry-run 结果
- candidate_total: `55`
- selected_count: `3`
- would_update_count: `3`
- actual_update_executed: `false`
- selected match_ids: `53_20252026_4830465`, `53_20252026_4830460`, `53_20252026_4830458`
## 5. Planned Second Batch / 计划第二批
| order | match_id | external_id | league_name | season | home_team | away_team | match_date | status | current_pipeline_status | planned_pipeline_status | raw_data_version | raw_row_count | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | `53_20252026_4830465` | `4830465` | `Ligue 1` | `2025/2026` | `Nice` | `Toulouse` | `2025-08-16T19:05:00.000Z` | `finished` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `would_update` |
| 2 | `53_20252026_4830460` | `4830460` | `Ligue 1` | `2025/2026` | `Brest` | `Lille` | `2025-08-17T13:00:00.000Z` | `finished` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `would_update` |
| 3 | `53_20252026_4830458` | `4830458` | `Ligue 1` | `2025/2026` | `Angers` | `Paris FC` | `2025-08-17T15:15:00.000Z` | `finished` | `pending` | `harvested` | `fotmob_live_v1` | `1` | `would_update` |
## 6. Guard Conditions / 守卫条件
- `3/3` match exists
- `3/3` external_id exists
- `3/3` status = `finished`
- `3/3` current pipeline_status = `pending`
- `3/3` raw_match_data exists
- `3/3` data_version = `fotmob_live_v1`
- `3/3` raw_row_count = `1`
- `3/3` raw_data / data_hash signal exists
- no external_id mismatch
- no duplicate raw
- no raw payload output
## 7. Future Execution Command Draft / 未来执行命令草稿
```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_guarded_reconciliation_write.js \
  --limit 3 \
  --expected-count 3 \
  --allow-write \
  --json
```
This command was NOT executed in this PR.
## 8. Verification Plan / 验证计划
未来执行后必须验证：
- 这 `3` 条变为 `harvested`
- `raw_match_data` 仍存在
- `raw_row_count` 仍为 `1`
- no raw payload output
- `candidate_total` 应从 `55` 降到 `52`
- 没有额外 `match_id` 被误更新
- 不执行第三批
## 9. Rollback Plan / 回滚预案
本节只记录文档预案，不执行回滚 SQL。未来如需回滚，必须另开任务并由用户明确授权。
```sql
UPDATE matches
SET pipeline_status = 'pending'
WHERE match_id IN (
  '53_20252026_4830465',
  '53_20252026_4830460',
  '53_20252026_4830458'
)
  AND pipeline_status = 'harvested';
```
`NOT EXECUTED`
## 10. Risk / 风险
- 第二批如果未来执行，会真实改变 `3` 条 `matches.pipeline_status`
- 不得全量推进剩余 `55` 条
- 每批都要遵循 `plan -> execute -> verify -> audit`
- 本 PR 不执行任何写库
## 11. Conclusion / 结论
- second batch plan ready: `yes`
- selected_count: `3`
- safe to request user authorization for second batch execution: `yes`
- no real write executed: `yes`
## 12. Next Recommended Task / 下一步建议
- 用户确认后，可以执行第二批 `<=3` 条 guarded reconciliation write
- 不要自动开始
- Recommended next task only after user confirmation
