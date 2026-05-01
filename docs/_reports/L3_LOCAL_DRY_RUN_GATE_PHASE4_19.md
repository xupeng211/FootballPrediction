# Phase 4.19 - L3 Local Dry-Run Gate

日期: `2026-05-02`

## 1. 当前 HEAD

- 分支: `feat/l3-local-dry-run-gate`
- Base HEAD: `6ac6ee23b4193a866d5959b506bf7ba1518eb1e2`
- 基线提交: `6ac6ee2 docs(l3): add raw fixture preflight report`

## 2. 新增文件

- `scripts/ops/l3_local_dry_run.js`
- `tests/fixtures/l3/raw_match_data_phase419_sample.json`
- `docs/_reports/L3_LOCAL_DRY_RUN_GATE_PHASE4_19.md`

修改文件：

- `Makefile`
- `AGENTS.md`

## 3. Fixture 摘要

- 本地 fixture 路径: `tests/fixtures/l3/raw_match_data_phase419_sample.json`
- `match_id`: `140_20252026_4837496`
- `external_id`: `4837496`
- 数据源: 本地脱敏样本，不含 secret，不访问外网
- 结构覆盖:
  - `raw_data.general`
  - `raw_data.header`
  - `raw_data.content.stats`
  - `raw_data.content.lineup`
  - `raw_data.content.shotmap`
  - `raw_data.content.momentum`

## 4. Dry-Run 脚本行为

新增脚本：`scripts/ops/l3_local_dry_run.js`

行为边界：

- 只读取本地 fixture JSON
- 校验 `--fixture` 与 `--match-id`
- 只对数据库执行 `SELECT`
- 只读取 `matches` 与 `bookmaker_odds_history`
- 生成并打印 L3 preview JSON
- 不调用 `smelt_all`
- 不调用 `l3_stitch_pipeline`
- 不调用 ELO
- 不执行任何写库或 schema 语句
- 不访问外网

输出包含：

- `golden_features`
- `tactical_features`
- `odds_features`
- `elo_features`
- `stitch_summary`
- `missing_fields`
- `non_execution_confirmations`

## 5. Makefile 入口

新增安全门禁：

```bash
make data-l3-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>
```

入口行为：

- 缺少 `SAMPLE_RAW` 或 `MATCH_ID` 时直接失败
- 在 `dev` 容器内执行只读脚本
- 不接旧 L3 入口
- 不触发 ELO
- 不执行写库命令

## 6. AGENTS.md 更新

新增允许项：

- 用户明确授权时，可执行 `make data-l3-dry-run SAMPLE_RAW=<local fixture> MATCH_ID=<id>`

新增禁止项：

- `npm run smelt`
- `npm run l3:stitch`
- `scripts/ops/smelt_all.js`
- `scripts/ops/l3_stitch_pipeline.js`
- `scripts/ops/l3_stitch_worker.js`
- `npm run elo:recalc`

背景引用：

- `docs/_reports/L3_RAW_FIXTURE_PREFLIGHT_PHASE4_18.md`

## 7. Dry-Run 输出摘要

缺参数验证：

- `make data-l3-dry-run` -> 失败，输出 `ERROR: provide SAMPLE_RAW=<path> and MATCH_ID=<id>`

安全 dry-run 验证：

- `match_found`: `true`
- `odds_history_rows`: `2`
- `bookmakers`: `["Bet365", "Pinnacle"]`
- `markets`: `["1x2", "Asian Handicap"]`
- `would_write_l3_features`: `false`
- `would_update_matches`: `false`
- `would_trigger_elo`: `false`
- `would_create_index`: `false`
- `would_create_table`: `false`
- `missing_fields`: `[]`

非执行确认：

- `no_db_writes`
- `no_insert`
- `no_update`
- `no_delete`
- `no_create_index`
- `no_create_table`
- `no_upsert`
- `no_l3_write`
- `no_elo`
- `no_external_network`

## 8. DB 前后统计

执行前：

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          0
l3_features             0
match_features_training 0
predictions             0
```

执行后：

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          0
l3_features             0
match_features_training 0
predictions             0
```

结论：

- dry-run 前后 DB 行数无变化

## 9. 明确未执行事项

本阶段未执行：

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `npm run smelt`
- `npm run l3:stitch`
- ELO recalculation
- L3 feature write
- model training
- prediction write
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- 外网访问
- 真实 harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume 清理
- `git push`
- `git pull`
- `git fetch --all`

## 10. 下一步建议

- push 当前分支
- 创建 PR
- 等 CI 绿灯后合并
- 后续再评估 `raw_match_data` 小范围写入 gate
- 后续再评估 `l3_features` 小范围写入 gate
