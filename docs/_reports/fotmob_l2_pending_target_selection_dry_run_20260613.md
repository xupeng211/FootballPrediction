# FotMob L2 Pending Target Selection Dry-Run - 2026-06-13

- lifecycle: phase-artifact
- scope: read-only dry-run selection only
- related contract: `docs/architecture/FOTMOB_L1_L2_HANDOFF_CONTRACT.md`

## 1. 本 PR 做了什么

- 新增 `scripts/ops/l2_pending_target_selection_dry_run.js`
- 基于 `matches + pipeline_status` 实现 FotMob L2 pending target selection dry-run
- 输出 summary、`by_league`、`by_season`、`sample_targets`
- 新增最小只读安全测试，验证脚本保持 `DRY-RUN` / `read-only`

## 2. 本 PR 没做什么

- 没有抓新数据
- 没有访问 FotMob live detail
- 没有运行 scraper / browser / proxy
- 没有写 `raw_match_data`
- 没有修改 `matches`
- 没有修改 `pipeline_status`
- 没有改 parser / feature / model / prediction
- 没有改 schema / migration

## 3. 如何运行 dry-run

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_pending_target_selection_dry_run.js --limit 10
```

可选过滤：

```bash
docker compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/l2_pending_target_selection_dry_run.js \
  --league "Premier League" \
  --season "2025/2026" \
  --status finished \
  --include-failed \
  --json
```

## 4. Dry-run selection rule

当前 contract carrier:

- `matches + pipeline_status`

默认选择规则:

- `external_id IS NOT NULL`
- `pipeline_status = pending`

可选过滤:

- `league_name ILIKE %<league>%`
- `season = <season>`
- `status = <status>`
- `--include-failed` 时，selection statuses 扩展为 `pending + failed`

## 5. 安全边界

- 脚本名、输出和帮助信息明确标记 `DRY-RUN` / `read-only`
- SQL 只允许 `BEGIN READ ONLY`、`SELECT`、`ROLLBACK`
- 不接入 FotMob live fetcher
- 不接入 raw write 脚本
- 不写文件、不写 JSON raw payload
- 不写数据库

## 6. 验证

- 新增单元/静态测试：`tests/unit/scripts/ops/l2_pending_target_selection_dry_run.test.js`
- 未执行 live DB dry-run，仅完成脚本和静态测试

## 7. 下一步建议

- 在用户确认后，先查看 dry-run 输出是否满足当前阶段 handoff 预期
- 如果 dry-run 输出可接受，再单独评审是否需要实现 guarded L2 pending consumer 或状态流转
- 不自动开始下一任务
