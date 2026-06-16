# FotMob L2 `--limit 10` Selection Investigation - 2026-06-16
- lifecycle: phase-artifact
- scope: read-only investigation for `--limit 10` selecting only 3 rows
- no `--allow-write` executed: yes
- no DB write: yes
- no sixth batch execution: yes
- no sixth batch planning: yes
- no FotMob live fetch: yes
- no raw payload output: yes
- no code/test/schema/migration change: yes
- no next task started: yes

## Conclusion / 结论
- `candidate_total`: `43`
- `--limit 10 selected_count`: `3`
- `would_update_count`: `3`
- `actual_update_executed`: `false`
- returned `match_id`s: `53_20252026_4830474`, `53_20252026_4830475`, `53_20252026_4830468`

## Root Cause / 根因
- 根因是脚本在参数解析阶段把请求值截断为 `MAX_LIMIT`，而 `MAX_LIMIT` 当前写死为 `3`。
- `scripts/ops/l2_guarded_reconciliation_write.js` 中 `const MAX_LIMIT = 3;`。
- `parseArgs()` 中执行 `options.limit = Math.min(parsedLimit, MAX_LIMIT);`，所以传入 `--limit 10` 后实际生效值仍然是 `3`。
- dry-run JSON 也直接返回 `safety.max_batch_size = 3`，与脚本常量一致。

## Non-Causes / 非根因确认
- `--limit` 不是完全没生效；它生效了，但被 `MAX_LIMIT = 3` 上限裁剪。
- SQL 没有固定 `LIMIT 3`；候选 SQL 只做 `ORDER BY`，没有 `LIMIT` 子句。
- eligibility 当前不是只有 3 条；dry-run `candidate_total = 43` 说明当前有 43 条 `would_update` 候选。
- 未发现控制 batch size 的环境变量；脚本里的 `process.env` 仅用于数据库连接配置。
- 未发现其他安全阈值覆盖这个行为；主限制来自脚本常量 `MAX_LIMIT`。

## Recommendation / 建议下一步
- 若未来确实要支持 `10` 条一批，需要代码修改，至少把 `MAX_LIMIT` 从 `3` 调整到 `10`，并同步检查 usage 文案、默认值与相关治理边界。
- 本次 PR 只做只读调查，不执行第六批，不计划第六批。
