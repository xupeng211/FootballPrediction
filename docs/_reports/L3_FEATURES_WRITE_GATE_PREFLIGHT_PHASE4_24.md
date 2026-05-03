# Phase 4.24 - L3 Features Write Gate Preflight

日期: `2026-05-03`

## 1. 当前 HEAD

- 分支: `feat/l3-features-write-gate-preflight`
- Base HEAD: `a559e9492640c042c51371eab9594e19f09acace`
- 基线提交: `a559e94 feat(data): add raw match data local ingest gate`

## 2. Phase 4.23 raw_match_data 写入状态摘要

Phase 4.23 完成一次人工授权的单条 `raw_match_data` 写入:

- `match_id`: `140_20252026_4837496`
- `external_id`: `4837496`
- `data_version`: `PHASE4.23`
- `data_hash`: `b13b7c2bf4f9b825e337124f51431d8594ef3a9af03e76dced88ee132addece1`
- returned `id`: `1`

Phase 4.23 报告:

- `docs/_reports/RAW_MATCH_DATA_SINGLE_INSERT_PHASE4_23.md`

## 3. 当前 DB 行数

只读统计:

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          1
l3_features             0
match_features_training 0
predictions             0
```

结论:

- `raw_match_data` 已有目标单条 fixture raw
- `l3_features` 仍为 0
- 未执行 L3 写入

## 4. l3_features 表结构摘要

只读审查结果:

- `match_id`: `varchar(50)`, `NOT NULL`, primary key
- `external_id`: `varchar(50)`, nullable
- `golden_features`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `tactical_features`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `odds_movement_features`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `odds_features`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `elo_features`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `rolling_features`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `efficiency_features`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `draw_features`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `market_sentiment`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `stitch_summary`: `jsonb`, `NOT NULL`, default `'{}'::jsonb`
- `computed_at`: `timestamptz`, `NOT NULL`, default `now()`
- `created_at`: `timestamptz`, `NOT NULL`, default `now()`
- `updated_at`: `timestamptz`, `NOT NULL`, default `now()`

约束:

- `l3_features_pkey`: primary key on `match_id`
- `l3_features_match_id_fkey`: `match_id` references `matches(match_id)` with `ON DELETE CASCADE`

## 5. l3_features 写入前置条件

未来人工授权单条写入至少需要:

- 明确 `match_id = 140_20252026_4837496`
- 确认 `matches` 目标行存在
- 确认 `raw_match_data` 目标行存在
- 确认 `l3_features` 目标行不存在
- 确认写入只触达 `l3_features`
- 明确 JSONB payload 来源和字段边界
- 明确是否允许 `elo_features` 为空占位
- 明确是否允许仅使用 dry-run preview 产物
- 执行前备份 DB
- 执行后验证主要表行数

本阶段不执行以上写入。

## 6. data-l3-dry-run 验证摘要

命令:

```bash
make data-l3-dry-run SAMPLE_RAW=tests/fixtures/l3/raw_match_data_phase419_sample.json MATCH_ID=140_20252026_4837496
```

结果摘要:

- `mode`: `dry-run`
- `match_found`: `true`
- `odds_history_rows`: `2`
- `would_write_l3_features`: `false`
- `would_update_matches`: `false`
- `would_trigger_elo`: `false`
- `would_create_index`: `false`
- `would_create_table`: `false`
- `no_db_writes`: present
- `no_l3_write`: present
- `no_elo`: present
- `no_external_network`: present

## 7. 新增 data-l3-commit blocked gate

新增 Makefile 目标:

```bash
make data-l3-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_L3_COMMIT=1
```

Phase 4.24 行为:

- 默认 blocked
- 即使提供 `CONFIRM_L3_COMMIT=1` 仍 blocked / not wired
- 不调用 `npm run smelt`
- 不调用 `npm run l3:stitch`
- 不调用 `scripts/ops/l3_stitch_pipeline.js`
- 不调用 `scripts/ops/smelt_all.js`
- 不写 DB
- 不触发 ELO

## 8. AGENTS.md 更新摘要

新增禁止项:

- `make data-l3-commit`
- `make data-l3-commit CONFIRM_L3_COMMIT=1`

继续禁止:

- `npm run smelt`
- `npm run l3:stitch`
- `scripts/ops/smelt_all.js`
- `scripts/ops/l3_stitch_pipeline.js`
- `scripts/ops/l3_stitch_worker.js`
- `npm run elo:recalc`

引用背景:

- `docs/_reports/L3_RAW_FIXTURE_PREFLIGHT_PHASE4_18.md`
- `docs/_reports/L3_LOCAL_DRY_RUN_GATE_PHASE4_19.md`
- `docs/_reports/RAW_MATCH_DATA_SINGLE_INSERT_PHASE4_23.md`

## 9. Blocked Commit 验证结果

默认命令:

```bash
make data-l3-commit
```

结果:

- blocked
- 输出: `BLOCKED: l3_features commit requires CONFIRM_L3_COMMIT=1 and is not wired in Phase 4.24.`

带确认变量:

```bash
make data-l3-commit SAMPLE_RAW=tests/fixtures/l3/raw_match_data_phase419_sample.json MATCH_ID=140_20252026_4837496 CONFIRM_L3_COMMIT=1
```

结果:

- blocked
- 输出: `BLOCKED: l3_features commit is not wired in Phase 4.24.`

## 10. DB 前后统计

执行 blocked gate 前:

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          1
l3_features             0
match_features_training 0
predictions             0
```

执行 blocked gate 后:

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          1
l3_features             0
match_features_training 0
predictions             0
```

结论:

- DB 行数无变化

## 11. 明确未执行事项

本阶段未执行:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- l3_features write
- `npm run smelt`
- `npm run l3:stitch`
- ELO recalculation
- L3 feature computation write
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
- `git fetch --all`
- `git pull`
- 删除文件

## 12. 下一步建议

- 后续可设计人工授权单条 `l3_features` 写入
- 仍禁止 `npm run smelt` / `npm run l3:stitch` / ELO
- 写入 runbook 应包含备份、单条范围、JSONB payload、post-write 验证和停止条件
