# Football-Data Insert Policy Precheck - Phase 4.66C

## 当前状态

- HEAD: `c2dfa6932030f942f59155b571df45e0b30f9f45`
- 分支: `feat/football-data-insert-policy-phase466c`
- 主题: deterministic `match_id` strategy + future insert candidate policy。

本阶段适合做一个稍大的主题 PR，因为 `match_id` 稳定生成和 insert eligibility 必须一起审查。只有 deterministic ID 但没有 duplicate policy 不安全；只有 duplicate policy 但没有稳定 proposed ID，也不足以进入未来写库授权。

## 新增 / 修改文件

新增:

- `scripts/ops/football_data_insert_policy_precheck.js`
- `tests/unit/football_data_insert_policy_precheck.test.js`
- `docs/_reports/FOOTBALL_DATA_INSERT_POLICY_PHASE4_66C.md`

修改:

- `Makefile`
- `AGENTS.md`

## Deterministic Match ID Strategy

预览策略:

```text
fd_<league>_<season>_<date>_<home>_<away>_<hash8>
```

规则:

- prefix 固定为 `fd`。
- `league_slug` 从 `league_name` / `Div` 派生，小写、去重音，仅保留 `[a-z0-9]`。
- `season_slug` 将 `2024/2025` 转成 `20242025`。
- `date_slug` 使用 `YYYYMMDD`。
- 主客队 slug 小写、去重音、空白转 `_`，仅保留 `[a-z0-9_]`，必要时 deterministic truncation。
- `hash8 = sha256(candidate_identity_key).slice(0, 8)`。
- 不使用随机数、当前时间、DB sequence、行顺序、比分、结果、赔率、parser version、训练或预测输出。
- 如果 proposed ID 无法适配 schema 最大长度，precheck 失败，不输出非法 ID。
- `match_id_strategy_finalized=false`: 本阶段只做策略预览，不授权写库。

## Candidate Identity Key

```text
football_data|<source_name>|<league_name>|<season>|<match_date_date>|<normalized_home_team>|<normalized_away_team>
```

identity key 明确不包含 score、`actual_result`、odds、`row_number`、parser version 和当前时间，避免同一场比赛因为标签、赔率或 CSV 行号变化而改变身份。

## Schema / Constraint 只读检查

对 `matches` 的 SELECT-only inspection 结果:

- `matches.match_id`: `character varying(50)`
- `is_nullable`: `NO`
- constraint: `matches_pkey`
- `match_id_primary_key=true`
- `match_id_unique=true`
- proposed ID 有效最大长度: `50`

precheck 只通过 `information_schema` 读取，并使用 read-only transaction 语义包裹 DB 查询。

## Insert Candidate Policy

每行 candidate 输出 `insert_policy`:

- `blocked_by_manifest_policy`: manifest `approval_status` 不是 `approved_for_db_write`。
- `skip_existing_match`: duplicate precheck 发现 `exact_existing_match`。
- `manual_review_required`: duplicate precheck 发现 reversed teams 或 nearby date possible duplicate。
- `invalid_candidate`: 必需 identity / label 字段无效，或 proposed ID 无法适配 schema 长度。
- `future_insert_candidate`: candidate 有效、无 duplicate risk、manifest 为 `approved_for_db_write`、proposed ID 合法。

即使是 `future_insert_candidate`，Phase 4.66C 仍然只是 preview:

- `would_insert_match=false`
- `would_insert_odds=false`
- `would_write_db=false`
- `db_write_allowed=false`

当前 fixture manifest 是 `dry_run_only`，真实本地 precheck 输出:

- `candidate_rows=3`
- `future_insert_candidates=0`
- `blocked_by_manifest_policy=3`
- `skip_existing_matches=0`
- `manual_review_required=0`
- `invalid_candidates=0`

## 安全机制

新 precheck:

- 读取本地 source manifest 和本地 CSV。
- 复用 football-data dry-run / parser 链路。
- 复用 SELECT-only duplicate precheck。
- 执行 SELECT-only `matches` schema / constraint inspection。
- 不 import `fetch_and_adapt_euro_leagues.js`。
- 不 spawn child process。
- 不执行 `pg_dump`。
- 不访问外网。
- 不写 DB。
- 不写业务数据文件。
- 不训练、不预测、不加载 model artifact。

commit target 继续 blocked:

```text
BLOCKED: football-data insert policy commit is not wired in Phase 4.66C.
```

## 验证结果

precheck 验证:

- 缺参数 precheck 按预期失败。
- 本地 fixture precheck 通过。
- `select_only_db_reads=true`
- `no_db_writes=true`
- `would_write_db=false`
- `match_id_strategy_finalized=false`
- `db_write_allowed=false`

旧 gate 复验:

- `make data-football-data-csv-dry-run ...`: 通过。
- `make data-football-data-db-write-preflight ...`: 通过。
- `make data-football-data-duplicate-precheck ...`: 通过。
- `make data-football-data-csv-commit ... CONFIRM_FOOTBALL_DATA_CSV_COMMIT=1`: blocked。
- `make data-football-data-db-write-commit ... CONFIRM_FOOTBALL_DATA_DB_WRITE=1`: blocked。
- `make data-football-data-duplicate-precheck-commit ... CONFIRM_FOOTBALL_DATA_DUPLICATE_PRECHECK=1`: blocked。
- `make data-acquisition-engine-audit`: 通过，no DB writes / no external network。
- `make data-single-target-network-dry-run ...`: scaffold blocked，`would_access_network=false`、`would_write_db=false`、`would_execute_engine=false`。
- `make data-single-target-network-commit ... CONFIRM_SINGLE_TARGET_NETWORK=1`: blocked。

测试:

- `node --test tests/unit/football_data_insert_policy_precheck.test.js`: 通过，23 tests。
- `node --test tests/unit/football_data_duplicate_precheck.test.js`: 通过。
- `node --test tests/unit/football_data_db_write_preflight.test.js`: 通过。
- `node --test tests/unit/football_data_adapter_dry_run.test.js`: 通过。
- `node --test tests/unit/football_data_local_csv_parser.test.js`: 通过。
- `node --test tests/unit/fetch_and_adapt_euro_leagues_no_network.test.js`: 通过。
- `node --test tests/unit/acquisition_engine_gate.test.js`: 通过。
- `npm test`: 通过。
- `npm run test:coverage`: 通过。

coverage:

- lines: `87.99`
- functions: `80.54`
- branches: `80.01`

第一次 coverage 运行报告 `branches=79.96 < 80`；随后只补了 Phase 4.66C 相关分支测试，最终 coverage gate 通过，没有修改 coverage 阈值。

## DB 前后统计

实施前:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

全部验证后:

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

## 下一步建议

- Phase 4.67C: small DB write authorization checklist + `pg_dump` command preview；仍不执行 `pg_dump`，不写 DB。
- 或 Phase 4.56A: 用户给齐真实 network dry-run 参数并单独授权后，再做 runbook。

## 明确未执行

- DB writes。
- non-SELECT DB SQL。
- `pg_dump` / `pg_restore`。
- external download。
- `curl` / `wget` / `git clone`。
- 外部足球数据源访问。
- 外部赔率数据源访问。
- scraping / browser automation。
- harvest / ingest / batch backfill / bulk harvest。
- network dry-run 真执行。
- adapted CSV 或 staging 数据写入。
- model training。
- real prediction execution。
- model artifact loading。
- Docker volume 清理。
- force push。
- `git fetch --all`。
- `git pull`。
- 删除文件。

除允许的代码、测试、Makefile、AGENTS 和本报告文件修改外，未执行任何业务数据文件写入。
