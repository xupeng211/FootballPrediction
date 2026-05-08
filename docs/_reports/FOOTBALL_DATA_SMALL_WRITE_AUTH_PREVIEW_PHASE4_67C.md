# Football-Data Small Write Authorization Preview - Phase 4.67C

## 当前状态

- HEAD: `984066e26a3c540ccd3c37d890c54e4769fb4182`
- 分支: `feat/football-data-small-write-auth-phase467c`
- 主题: future small DB write authorization checklist + `pg_dump` command preview。

本阶段适合做一个稍大的主题 PR，因为 future small DB write 不能只看单一 gate。授权条件、`pg_dump` 预案、post-write validation、rollback/restore preview、以及对 Phase 4.63C / 4.64C / 4.65C / 4.66C gate 的复用，必须一起固定下来，才能避免未来写库阶段临时拼 runbook。

## 新增 / 修改文件

新增:

- `scripts/ops/football_data_small_write_auth_preview.js`
- `tests/unit/football_data_small_write_auth_preview.test.js`
- `docs/_reports/FOOTBALL_DATA_SMALL_WRITE_AUTH_PREVIEW_PHASE4_67C.md`

修改:

- `Makefile`
- `AGENTS.md`

## Small Write Authorization Preview 设计

新增 gate:

```bash
make data-football-data-small-write-auth-preview \
  SOURCE_MANIFEST=<path> \
  LOCAL_CSV=<path>
```

它只做 preview，不写库。实现顺序:

1. 读取本地 source manifest。
2. 读取本地 CSV。
3. 复用 Phase 4.63C local CSV dry-run。
4. 复用 Phase 4.64C DB write preflight。
5. 复用 Phase 4.65C duplicate precheck。
6. 复用 Phase 4.66C insert policy precheck。
7. 对 DB 做 SELECT-only row count / schema preview。
8. 输出 future authorization checklist、`pg_dump` command preview、post-write validation checklist、rollback/restore preview。

输出强制保持:

- `db_write_allowed=false`
- `small_write_authorized=false`
- `would_execute_pg_dump=false`
- `would_execute_pg_restore=false`
- `would_insert_matches=false`
- `would_insert_odds=false`
- `would_write_db=false`
- `commit_gate=blocked`

## SELECT-only DB Inspection

本阶段允许:

- `BEGIN READ ONLY`
- `SELECT`
- `ROLLBACK`

preview 只读取:

- `matches`
- `bookmaker_odds_history`
- `raw_match_data`
- `l3_features`
- `match_features_training`
- `predictions`

并预览 `matches.match_id` 基本 schema 状态。没有 `INSERT` / `UPDATE` / `DELETE` / `CREATE` / `ALTER` / `DROP` / `TRUNCATE` / `COPY` / `\copy`。

## pg_dump Command Preview

本阶段输出 command preview string，但明确未执行:

```text
docker compose -f docker-compose.dev.yml exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > data/backups/<timestamp>_pre_football_data_small_write.dump
```

说明:

- 只是 preview string。
- 不执行 `pg_dump`。
- 不创建 `data/backups`。
- 不创建 backup 文件。
- 不校验 backup 文件存在性，因为本阶段没有真实 backup。

## pg_restore / Rollback Preview

本阶段同样只输出 preview:

- restore 不自动执行。
- backup path 必须由人工确认。
- restore 需要单独 restore authorization。
- restore command 必须被文档化，但本阶段不执行。

## Required Before Small DB Write

future small DB write 前必须满足:

- source manifest `approval_status` 必须为 `approved_for_db_write`
- human approval note 必须指向 exact source 和 exact CSV
- operator 必须在未来阶段提供 `CONFIRM_FOOTBALL_DATA_SMALL_WRITE=1`
- deterministic `match_id` strategy 必须被接受
- duplicate policy 必须被接受
- exact existing matches 不得插入
- manual review candidates 不得插入
- max insert rows 必须显式给出
- target tables 必须显式给出
- `pg_dump` 必须在写入前立即执行
- backup file 必须非空
- write transaction 必须 small and auditable
- post-write row counts 必须校验
- inserted `match_id` 列表必须记录
- downstream training / prediction 继续 blocked

## Post-write Validation Checklist

future post-write validation preview:

- compare before/after row counts
- verify inserted `match_id` only
- verify no odds insert unless explicitly authorized
- verify no raw / l3 / training / prediction writes
- rerun dataset status
- rerun duplicate precheck
- record backup path
- record commit hash / report path

## 为什么本阶段仍不写 DB

原因明确:

- 目前只有 authorization preview，没有真实 small write phase 授权。
- commit gate 仍 blocked。
- 本阶段目标是固定 checklist、backup preview、rollback preview，不是执行写入。
- 真实 write 仍需要单独阶段、单独授权、真实 `pg_dump`、small batch transaction 和 post-write validation。

## 为什么本阶段仍不执行 pg_dump

原因明确:

- `pg_dump` 属于真实 backup 动作，不是 preview。
- 本阶段只允许 command preview，不允许创建 backup 文件。
- 没有真实 write authorization，就不应制造“像执行过备份一样”的假状态。

## Commit Gate Blocked 结果

新增 blocked gate:

```bash
make data-football-data-small-write-commit \
  SOURCE_MANIFEST=<path> \
  LOCAL_CSV=<path> \
  CONFIRM_FOOTBALL_DATA_SMALL_WRITE=1
```

当前固定输出:

```text
BLOCKED: football-data small DB write commit is not wired in Phase 4.67C.
```

即使带确认变量也仍然 blocked。

## 复验结果

small write auth preview:

- 缺参数按预期失败。
- fixture preview 成功。
- `db_write_allowed=false`
- `small_write_authorized=false`
- `would_execute_pg_dump=false`
- `would_execute_pg_restore=false`
- `would_write_db=false`
- `no_external_network`
- `select_only_db_reads`
- `no_db_writes`
- `no_file_writes`
- `no_pg_dump_execution`
- `no_pg_restore_execution`

旧 gates 复验:

- `make data-football-data-csv-dry-run ...`: 通过。
- `make data-football-data-db-write-preflight ...`: 通过。
- `make data-football-data-duplicate-precheck ...`: 通过。
- `make data-football-data-insert-policy-precheck ...`: 通过。
- `make data-football-data-csv-commit ... CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1`: blocked。
- `make data-football-data-db-write-commit ... CONFIRM_FOOTBALL_DATA_DB_WRITE=1`: blocked。
- `make data-football-data-duplicate-precheck-commit ... CONFIRM_FOOTBALL_DATA_DUPLICATE_PRECHECK=1`: blocked。
- `make data-football-data-insert-policy-commit ... CONFIRM_FOOTBALL_DATA_INSERT_POLICY=1`: blocked。
- `make data-acquisition-engine-audit`: 通过。
- `make data-single-target-network-dry-run ...`: scaffold blocked，`would_access_network=false`、`would_write_db=false`、`would_execute_engine=false`。
- `make data-single-target-network-commit ... CONFIRM_SINGLE_TARGET_NETWORK=1`: blocked。

## Unit Tests

新增 `tests/unit/football_data_small_write_auth_preview.test.js`，覆盖:

- 缺 manifest 失败。
- 缺 CSV 失败。
- 正确 manifest + CSV + mock DB client 成功。
- `pg_dump` preview string 存在但不执行。
- required checklist 存在。
- post-write validation checklist 存在。
- rollback/restore preview 存在。
- `dry_run_only` 时 `small_write_authorized=false`。
- `approved_for_db_write` 时也仍然 `small_write_authorized=false`。
- `--commit` blocked。
- `sha256 mismatch` 时失败且不查 DB。
- `row_count mismatch` 时失败且不查 DB。
- SQL 只允许 `BEGIN READ ONLY` / `SELECT` / `ROLLBACK`。
- 不 import legacy runtime。
- 不触网。
- 不写文件。
- 不 spawn child process。
- 不执行 `pg_dump`。
- 不执行 `pg_restore`。

## npm test / coverage

本阶段要求:

- `npm test` 通过。
- `npm run test:coverage` 通过。
- coverage threshold 保持不变:
    - lines >= 80
    - functions >= 80
    - branches >= 80

## DB 前后统计

执行前预期:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

本阶段要求全部验证后仍保持:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

## 下一步建议

- Phase 4.68C: prepare real small DB write runbook template + approval form，不写 DB，不执行 `pg_dump`。
- 或 Phase 4.56A: 用户给齐真实 network dry-run 参数后再做 runbook。

## 明确未执行

- DB writes
- non-SELECT DB SQL
- `pg_dump` execution
- `pg_restore` execution
- backup file writes
- preview runtime file writes
- external download
- `curl` / `wget` / `git clone`
- 外部足球数据源访问
- 外部赔率数据源访问
- scraping / browser automation
- harvest / ingest
- batch backfill
- network dry-run 真执行
- bulk harvest
- adapted CSV / staging 数据写入
- model training
- real prediction execution
- model artifact loading
- Docker volume 清理
- force push
- `git fetch --all`
- `git pull`
- 删除文件
