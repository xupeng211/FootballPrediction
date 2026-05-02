# Phase 4.21 - raw_match_data Local Ingest Gate

日期: `2026-05-02`

## 1. 当前 HEAD

- 分支: `feat/raw-match-data-local-ingest-gate`
- Base HEAD: `3adb15161e2fe079e52fe5503ac6deeb4c15ca28`
- 基线提交: `3adb151 feat(l3): add safe local dry-run gate`

## 2. 本阶段新增文件

- `scripts/ops/raw_match_data_local_ingest.js`
- `docs/_reports/RAW_MATCH_DATA_LOCAL_INGEST_GATE_PHASE4_21.md`

修改文件:

- `Makefile`
- `AGENTS.md`

复用文件:

- `tests/fixtures/l3/raw_match_data_phase419_sample.json`

## 3. raw_match_data 表结构摘要

只读审查结果:

- `id`: `bigint`, `NOT NULL`, default `nextval('raw_match_data_id_seq'::regclass)`
- `match_id`: `varchar(50)`, `NOT NULL`
- `external_id`: `varchar(100)`, nullable
- `raw_data`: `jsonb`, `NOT NULL`
- `collected_at`: `timestamptz`, nullable, default `CURRENT_TIMESTAMP`
- `data_version`: `varchar(20)`, nullable, default `'V26.1'`
- `data_hash`: `varchar(64)`, nullable

约束摘要:

- `raw_match_data_match_id_fkey`: `match_id` references `matches(match_id)` with `ON DELETE CASCADE`
- `raw_match_data_match_id_key`: unique `match_id`
- `raw_data_not_empty`: `raw_data IS NOT NULL` and not empty JSONB
- `raw_data_has_match_id`: `raw_data` must contain `matchId`, `general`, or `header`
- `match_id_format`: supports composite `league_season_external` style or numeric IDs
- `data_hash` is optional in current schema

## 4. Fixture 审查结果

Fixture:

- `tests/fixtures/l3/raw_match_data_phase419_sample.json`

审查结果:

- `match_id`: `140_20252026_4837496`
- `external_id`: `4837496`
- `raw_data.matchId`: `4837496`
- `raw_data.general`: present
- `raw_data.header`: present
- `raw_data.content`: present
- 符合 `raw_data_has_match_id` 与 `raw_data_not_empty` 约束的 dry-run 预览要求
- 本阶段未修改 fixture

## 5. Dry-Run 脚本行为

新增脚本:

- `scripts/ops/raw_match_data_local_ingest.js`

dry-run 行为:

- 读取本地 fixture JSON
- 校验 fixture `match_id` 与 `--match-id` 一致
- 校验 `raw_data` 存在且为对象
- 校验 `raw_data.matchId` 存在
- 校验 `raw_data.general` 或 `raw_data.header` 至少一个存在
- 只读查询目标 `matches`
- 只读查询目标 `raw_match_data`
- 只读查询目标 `bookmaker_odds_history`
- 使用稳定 JSON 字符串和 `sha256` 生成 `data_hash`
- 打印 raw ingest preview

禁止行为:

- 不执行 `INSERT`
- 不执行 `UPDATE`
- 不执行 `DELETE`
- 不执行 `CREATE`
- 不执行 `ALTER`
- 不执行 `DROP`
- 不执行 `TRUNCATE`
- 不执行 `CREATE INDEX`
- 不调用 L3
- 不调用 ELO
- 不访问外网

`--commit` 行为:

- 立即失败
- 输出 `BLOCKED: raw_match_data commit is not wired in Phase 4.21.`
- 在建立 DB 连接前结束

## 6. Makefile 入口

新增 dry-run 入口:

```bash
make data-raw-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>
```

新增 blocked commit 入口:

```bash
make data-raw-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_RAW_COMMIT=1
```

Phase 4.21 中 `data-raw-commit` 不接真实写库命令。

`data-help` 已加入:

- `make data-raw-dry-run SAMPLE_RAW=<path> MATCH_ID=<id>`
- `make data-raw-commit SAMPLE_RAW=<path> MATCH_ID=<id> CONFIRM_RAW_COMMIT=1  # blocked in Phase 4.21`

## 7. AGENTS.md 更新

新增默认允许项:

- 用户明确授权且仅使用本地 fixture 的 `make data-raw-dry-run SAMPLE_RAW=<local fixture> MATCH_ID=<id>`

新增禁止项:

- `make data-raw-commit`
- `node scripts/ops/raw_match_data_local_ingest.js --commit`

继续禁止:

- `npm run smelt`
- `npm run l3:stitch`
- `npm run elo:recalc`

引用背景:

- `docs/_reports/L3_RAW_FIXTURE_PREFLIGHT_PHASE4_18.md`
- `docs/_reports/L3_LOCAL_DRY_RUN_GATE_PHASE4_19.md`

## 8. Dry-Run 输出摘要

缺参数验证:

- `make data-raw-dry-run` -> 失败，输出 `ERROR: provide SAMPLE_RAW=<path> and MATCH_ID=<id>`

正常 dry-run:

- `mode`: `dry-run`
- `match_found`: `true`
- `raw_match_data_exists`: `false`
- `raw_match_data_rows`: `0`
- `odds_history_rows`: `2`
- `would_insert_raw_match_data`: `false`
- `target_table`: `raw_match_data`
- `data_version`: `PHASE4.21_DRY_RUN`
- `data_hash`: `b13b7c2bf4f9b825e337124f51431d8594ef3a9af03e76dced88ee132addece1`

非执行确认:

- `no_db_writes`
- `no_insert`
- `no_update`
- `no_delete`
- `no_create_index`
- `no_l3`
- `no_elo`
- `no_external_network`

## 9. Commit Gate Blocked 结果

默认 commit:

- `make data-raw-commit` -> blocked
- 输出: `BLOCKED: raw_match_data commit requires CONFIRM_RAW_COMMIT=1 and is not wired in Phase 4.21.`

带确认变量:

- `make data-raw-commit SAMPLE_RAW=tests/fixtures/l3/raw_match_data_phase419_sample.json MATCH_ID=140_20252026_4837496 CONFIRM_RAW_COMMIT=1` -> blocked
- 输出: `BLOCKED: raw_match_data commit is not wired in Phase 4.21.`

结论:

- Phase 4.21 未接真实 raw_match_data 写入路径

## 10. DB 前后统计

执行前:

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          0
l3_features             0
match_features_training 0
predictions             0
```

执行后:

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          0
l3_features             0
match_features_training 0
predictions             0
```

结论:

- dry-run 与 blocked commit 前后 DB 行数无变化

## 11. 明确未执行事项

本阶段未执行:

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- raw_match_data commit
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
- `git push`
- `git pull`
- `git fetch --all`

## 12. 下一步建议

- Phase 4.22: push 当前分支、创建 PR、等待 CI
- 后续: 人工授权 raw_match_data 单条写入 gate
- 再后续: 基于 raw_match_data 执行 L3 dry-run
