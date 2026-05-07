# Phase 4.64C Football-Data DB Write Preflight

## 当前状态

- 日期: 2026-05-07
- 起始 HEAD: `09dada71d9bf6422aa2b0ad15fba4210239c22b6`
- 起始提交: `09dada7 feat(data): add football-data CSV dry-run gate`
- 工作分支: `feat/football-data-db-write-preflight-phase464c`
- 主题: football-data 本地 CSV 从 dry-run 走向未来小批量 DB write 的前置安全机制

## PR 粒度说明

本阶段把 preflight script、Makefile gate、unit tests、AGENTS 规则和 runbook 报告放入同一个主题 PR 是合理的，因为它们共同定义同一个安全边界: 只预览未来小批量 DB write 的必备条件，不执行真实 DB write、`pg_dump`、network dry-run、staging write、training 或 prediction。

本 PR 没有引入真实写库实现，也没有接入 legacy downloader runtime。

## 新增和修改文件

- `scripts/ops/football_data_db_write_preflight.js`
- `tests/unit/football_data_db_write_preflight.test.js`
- `docs/_reports/FOOTBALL_DATA_DB_WRITE_PREFLIGHT_PHASE4_64C.md`
- `Makefile`
- `AGENTS.md`

## DB Write Preflight 设计

新增命令:

```bash
make data-football-data-db-write-preflight \
  SOURCE_MANIFEST=<path> \
  LOCAL_CSV=<path>
```

preflight 行为:

- 读取本地 source manifest。
- 读取本地 local CSV。
- 复用 Phase 4.63C `football_data_adapter_dry_run` 的 manifest、sha256、row_count 和 parser dry-run 结果。
- 输出 future DB write plan preview。
- 固定 `db_write_allowed=false`。
- 固定 `would_insert_matches=false`。
- 固定 `would_insert_odds=false`。
- 固定 `would_write_db=false`。
- 固定 `would_execute_pg_dump=false`。
- 固定 `would_access_network=false`。
- 固定 `would_write_files=false`。
- 固定 `commit_gate=blocked`。

preflight 不 import `fetch_and_adapt_euro_leagues.js`，不 import `pg`，不 spawn child process，不连接 DB，不写文件，不执行 `pg_dump`。

## Future Backup / Pg Dump Runbook

未来真实 DB write 前必须另开阶段并获得单独授权:

1. 确认 source manifest 已升级为 `approved_for_db_write`。
2. 确认 manifest 包含人工 approval note、license、terms、provenance。
3. 先完成 SELECT-only duplicate / existing match precheck。
4. 在写库前立即创建真实 `pg_dump` 备份。
5. 记录 backup path、sha256、timestamp、DB name 和 operator。
6. 仅写入显式批准的小批量 rows。
7. 写后用 SELECT-only row counts 和 inserted match IDs 验证。
8. training / prediction 继续保持 blocked，必须单独 gate 授权。

本阶段不执行 `pg_dump`，因为 Phase 4.64C 只允许 runbook preview。提前执行真实备份会越过“DB write 前立即备份”的时间点要求，也会把 preflight 从只读预览扩大成真实运维动作。

## Required Before DB Write

- approval_status must be approved_for_db_write
- source manifest must include human approval note
- deterministic match_id strategy must be finalized
- duplicate detection against DB must be SELECT-only prechecked
- pg_dump backup must be created immediately before write
- max rows must be small and explicit
- target tables must be declared
- rollback/restore plan must be written
- post-write row counts must be validated
- training/prediction must remain blocked

## 为什么本阶段不写 DB

本阶段的目标是把未来写库前的安全条件、备份要求、验证清单和 blocked commit gate 固化下来。真实 `INSERT` / odds write / staging write / DB duplicate check 都需要单独阶段、单独授权和新的验证证据。

preflight 自身不连接 DB，DB duplicate detection 仅进入 future checklist。真正 SELECT-only duplicate precheck 留到 Phase 4.65C。

## 验证结果

### New DB Write Gate

- `make data-football-data-db-write-preflight || true`: 缺参数失败。
- `make data-football-data-db-write-preflight SOURCE_MANIFEST=tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json LOCAL_CSV=tests/fixtures/football_data/football_data_sample_phase462c.csv`: 通过。
- 成功输出包含:
    - `dry_run_passed=true`
    - `sha256_match=true`
    - `row_count_match=true`
    - `candidate_rows=3`
    - `trainable_label_rows=3`
    - `odds_preview_rows=3`
    - `db_write_allowed=false`
    - `would_write_db=false`
    - `would_execute_pg_dump=false`
    - `no_external_network`
    - `no_db_writes`
    - `no_file_writes`
    - `no_pg_dump_execution`

### Commit Gate

- `make data-football-data-db-write-commit || true`: blocked。
- `make data-football-data-db-write-commit SOURCE_MANIFEST=tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json LOCAL_CSV=tests/fixtures/football_data/football_data_sample_phase462c.csv CONFIRM_FOOTBALL_DATA_DB_WRITE=1 || true`: blocked。

即使提供 `CONFIRM_FOOTBALL_DATA_DB_WRITE=1`，Phase 4.64C 仍保持 not wired。

### Old Gates

- `make data-football-data-csv-dry-run SOURCE_MANIFEST=tests/fixtures/football_data/source_manifests/football_data_sample_phase463c_manifest.json LOCAL_CSV=tests/fixtures/football_data/football_data_sample_phase462c.csv`: 通过。
- `make data-football-data-csv-commit ... CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1 || true`: blocked。
- `make data-acquisition-engine-audit`: 通过，`no_db_writes` / `no_external_network`。
- `make data-single-target-network-dry-run ENGINE=fetch_and_adapt_euro_leagues TARGET_MATCH_ID=47_20242025_900002 SOURCE_MANIFEST=tests/fixtures/real_source_manifests/local_sample_history_phase452.json || true`: scaffold-only blocked，`would_access_network=false` / `would_write_db=false` / `would_execute_engine=false`。
- `make data-single-target-network-commit ... CONFIRM_SINGLE_TARGET_NETWORK=1 || true`: blocked。

### Tests

- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/football_data_db_write_preflight.test.js`: 通过，11 tests。
- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/football_data_adapter_dry_run.test.js`: 通过，11 tests。
- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/football_data_local_csv_parser.test.js`: 通过，10 tests。
- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js`: 通过，4 tests。
- `docker compose -f docker-compose.dev.yml exec -T dev node --test tests/unit/acquisition_engine_gate.test.js`: 通过，8 tests。
- `docker compose -f docker-compose.dev.yml exec -T dev npm test`: 通过。
- `docker compose -f docker-compose.dev.yml exec -T dev npm run test:coverage`: 通过。

Coverage summary:

- lines: 87.79
- functions: 80.33
- branches: 80.00

## DB 前后统计

变更前基线:

- matches: 2
- bookmaker_odds_history: 2
- raw_match_data: 2
- l3_features: 2
- match_features_training: 2
- predictions: 2

变更后只读复核:

- matches: 2
- bookmaker_odds_history: 2
- raw_match_data: 2
- l3_features: 2
- match_features_training: 2
- predictions: 2

DB 行数未变化。

## 下一步建议

- Phase 4.65C: 实现 SELECT-only duplicate / existing match precheck，不写 DB。
- 或 Phase 4.56A: 用户给齐真实 network dry-run 参数后，仅做 runbook / manifest / target scope 预检。

## 未执行事项

- 未执行 DB writes。
- 未从 preflight 读取 DB。
- 未执行 `pg_dump`。
- 未写文件或 staging 数据。
- 未写 adapted CSV。
- 未执行 external download。
- 未执行 `curl` / `wget` / `git clone`。
- 未访问外部足球数据源。
- 未访问外部赔率数据源。
- 未执行 scraping / browser automation。
- 未执行 harvest / ingest。
- 未执行 batch backfill。
- 未执行 network dry-run 真执行。
- 未执行 bulk harvest。
- 未执行 model training。
- 未执行 real prediction execution。
- 未加载 model artifact。
- 未清理 Docker volume。
- 未 force push。
- 未执行 `git fetch --all`。
- 未执行 `git pull`。
- 未删除文件、旧引擎、报告或备份。
