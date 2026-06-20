# P0 DB Write Safety Gate — Dry Run Audit Report

**Date:** 2026-06-20
**Phase:** P0_DB_WRITE_SAFETY_GATE_DRY_RUN
**Branch:** chore/p0-db-write-safety-gate-dry-run
**Type:** READ-ONLY — no network, no DB connection, no script execution

---

## Executive Summary

专项审计了 5 个目录，扫描了 122 个文件，发现 **122 个生产脚本存在数据库写入操作**。

- 额外发现 0 个测试文件包含 DB 写入模式（不列为生产风险）
- 上一轮审计报告的 34 个脚本已确认复现（当前发现 122 个）

### 关键数字

| 指标 | 数量 |
|------|------|
| P0 — 必须立即修复 | 66 |
| P1 — 数据扩容前修复 | 49 |
| P2 — 可排期 | 7 |
| 完全无安全闸门 | 110 |
| 有部分闸门 | 7 |
| 有完整闸门 | 5 |
| raw_match_data 写入 | 25 |
| matches 写入 | 38 |
| UPDATE/DELETE/DROP | 21 |
| Schema 变更 | 29 |

### 核心结论

**本 PR 未修复 SC-002。** 本 PR 只是专项审计和修复方案。
不允许因为本 PR 合并就认为写库风险已消除。
下一步真实修改写库脚本前，必须再次请求用户确认。

---

## 统一安全闸门契约 (Unified Gate Contract)

| Gate | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| `ALLOW_DB_WRITE` | any database write (INSERT / UPDATE / DELETE / DDL) | unset (blocked) | Master kill-switch. Must be explicitly set to "yes" for any write to proceed. |
| `FINAL_DB_WRITE_CONFIRMATION` | transactional write confirmation | unset (blocked) | Second-factor confirmation. Even with ALLOW_DB_WRITE=yes, this must also be yes. |
| `ALLOW_RAW_MATCH_DATA_WRITE` | INSERT / UPDATE / DELETE on raw_match_data table | unset (blocked) | Specific gate for raw_match_data writes. Must be yes IN ADDITION to the two above. |
| `ALLOW_MATCHES_WRITE` | INSERT / UPDATE / DELETE on matches table | unset (blocked) | Specific gate for matches writes. |
| `ALLOW_SCHEMA_WRITE` | CREATE / ALTER / DROP / TRUNCATE — any DDL | unset (blocked) | Schema mutations require this gate. Highest risk category. |
| `ALLOW_TRAINING_WRITE` | INSERT / UPDATE on match_features_training, predictions, training artifacts | unset (blocked) | Training data and prediction writes require this gate. |
| `ALLOW_ODDS_WRITE` | INSERT / UPDATE on bookmaker_odds_history, matches_oddsportal_mapping, odds | unset (blocked) | Odds data writes require this gate. |
| `DRY_RUN` | all scripts | true | Scripts default to dry-run mode. Must explicitly set to false for real writes. |
| `REQUIRE_EXPLICIT_USER_AUTHORIZATION` | all write scripts | true | User must provide explicit authorization before any write. No automated writes. |
| *(minimum)* | — | — | At minimum, every DB-write script must check: ALLOW_DB_WRITE + FINAL_DB_WRITE_CONFIRMATION. Additional table-specific gates required for raw_match_data, matches, schema, training, odds. |

### 最小门槛

**每个 DB 写入脚本至少检查：**
1. `ALLOW_DB_WRITE=yes` — 主开关
2. `FINAL_DB_WRITE_CONFIRMATION=yes` — 二次确认

**表级附加门槛：**
- `raw_match_data` → 额外要求 `ALLOW_RAW_MATCH_DATA_WRITE=yes`
- `matches` → 额外要求 `ALLOW_MATCHES_WRITE=yes`
- DDL 操作 → 额外要求 `ALLOW_SCHEMA_WRITE=yes`
- `predictions` / `match_features_training` → 额外要求 `ALLOW_TRAINING_WRITE=yes`
- `bookmaker_odds_history` 等 → 额外要求 `ALLOW_ODDS_WRITE=yes`

### Dry-Run vs Write-Run 行为区别

| 模式 | DRY_RUN | ALLOW_DB_WRITE | 行为 |
|------|---------|---------------|------|
| dry-run (默认) | true | any | 只输出 would-write / would-skip summary，不写库 |
| write-run | false | yes | 实际执行 SQL 写入事务 |
| blocked | false | unset/no | 打印错误并退出，不写库 |

### 生产库保护策略

1. `NODE_ENV=production` 时 DRY_RUN 必须强制为 true（除非显式 override）
2. `DB_HOST` 包含生产标识时额外打印红色警告
3. 写入前必须打印 affected rows preview
4. 写入必须在显式事务中执行，失败自动回滚

---

## P0 文件清单（必须立即修复）

| 文件 | 操作 | 表 | 缺失闸门 | raw | matches | DELETE/DROP |
|------|------|-----|----------|-----|---------|-------------|
| scripts/ops/ai_workflow_gate.py | TRUNCATE | match | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_SCHEMA_WRITE | - | - | YES |
| scripts/ops/backfill_historical_raw_match_data.js | INSERT, UPDATE | raw_match_data, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | YES | - |
| scripts/ops/bulk_import_matches.js | INSERT | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/cleanup_csv_bulk_loader_import.js | DELETE, SQL_VIA_QUERY | bookmaker_odds_history, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_ODDS_WRITE | - | YES | YES |
| scripts/ops/controlled_matches_identity_seed_execute.js | INSERT, UPDATE | matches, result | none | - | YES | - |
| scripts/ops/csv_bulk_loader.js | INSERT, UPDATE | bookmaker_odds_history, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_ODDS_WRITE | - | YES | - |
| scripts/ops/db_vault.js | UPDATE, TRUNCATE | matches, matches_oddsportal_mapping | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| scripts/ops/fixture_harvester_l1.js | INSERT | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/ops/fotmob_safe_parser_schema_reuse_plan_no_write.py | CREATE_TABLE, ALTER | fotmob_raw_match_payloads, raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/generate_bundesliga_fixtures.js | INSERT | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/ops/helpers/dbBlueprint.js | INSERT | matches, raw_match_data, matches_oddsportal_mapping | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | YES | YES | - |
| scripts/ops/l1_matches_seed_commit_execute.js | INSERT | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/ops/l2_guarded_reconciliation_write.js | UPDATE | matches, count | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/ops/l2_raw_match_data_write.js | INSERT, UPDATE | raw_match_data, is | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/l2_remaining_raw_match_data_write.js | INSERT, UPDATE | raw_match_data, is | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/l3_stitch_pipeline.js | UPDATE, CREATE_TABLE | matches, l3_features | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/ops/matches_labeling_backfill_dry_run.js | UPDATE, SQL_VIA_QUERY | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/ops/n3_live_fotmob_raw_retain.js | INSERT, DELETE | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | YES |
| scripts/ops/pageprops_v2_raw_write_input_source_investigation.js | INSERT | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/pageprops_v2_single_target_controlled_write.js | INSERT | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/purge_orphans.js | DELETE, SQL_VIA_QUERY | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| scripts/ops/raw_match_data_versioned_schema_migration_execute.js | ALTER | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/raw_match_data_versioned_schema_migration_preflight.js | ALTER | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/remaining_seeded_pageprops_v2_controlled_write.js | INSERT | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| scripts/ops/score_backfill_write.js | UPDATE | matches, count | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/ops/seed_fotmob_sample.js | INSERT | matches, raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | YES | YES | - |
| scripts/ops/single_league_pageprops_v2_controlled_write_execute.js | INSERT, UPDATE | raw_match_data, result | none | YES | - | - |
| scripts/ops/single_live_fotmob_raw_ingest_smoke.js | INSERT, DELETE | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | YES |
| scripts/ops/single_raw_match_data_ingest.js | INSERT, DELETE | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | YES |
| scripts/ops/technical_debt_workflow_audit_dry_run.js | INSERT, UPDATE | raw_match_data, matches, pattern, counts, init_dbsql | ALLOW_MATCHES_WRITE | YES | YES | - |
| scripts/ops/titan_seeder.js | INSERT | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/ops/training_eligibility_write.js | UPDATE | matches, count | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/maintenance/clean_corrupt_l2.py | UPDATE | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/maintenance/database_detox.py | UPDATE, ALTER | prematch_features | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_SCHEMA_WRITE | - | - | - |
| scripts/maintenance/fix_zombie_matches.py | UPDATE | in, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/maintenance/migrations/V6_0_add_market_sentiment.sql | ALTER | l3_features | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_SCHEMA_WRITE | - | - | - |
| scripts/maintenance/odds_integrity_guard.py | DELETE | match_odds | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION | - | - | YES |
| scripts/maintenance/reprocess_failed_matches.py | UPDATE | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/maintenance/reprocess_from_local.py | UPDATE | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| scripts/maintenance/reset_l2_collection.py | TRUNCATE | raw_match_data, collection_audit_logs | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | YES |
| src/core/database/odds_injector.py | UPDATE | data, matches, complete | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| src/database/collector_repository.py | INSERT | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| src/database/migrations/versions/003_v145_l2_data_version.py | DROP, ALTER | idx_matches_l2_collected, idx_matches_l2_raw_json_gin, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| src/database/schema_manager.py | INSERT, UPDATE, CREATE_TABLE, ALTER | matches, cascade, on, match_features_training, raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | YES | YES | - |
| src/database/sql_store.py | INSERT, UPDATE | matches, matches_mapping, raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | YES | YES | - |
| src/feature_engine/smelter/components/L3Writer.js | INSERT, DELETE | l3_features | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION | - | - | YES |
| src/infrastructure/harvesters/Checkpointer.js | INSERT, UPDATE, DELETE | backfill_progress | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION | - | - | YES |
| src/infrastructure/harvesters/TitanSlimHarvester.js | INSERT | raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |
| src/infrastructure/harvesters/components/Persistence.js | INSERT, UPDATE, ALTER | raw_match_data, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | YES | - |
| src/infrastructure/services/FixtureRepository.js | INSERT, UPDATE, DELETE | recon_league_dictionary, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| src/infrastructure/services/MarathonService.js | INSERT, UPDATE | raw_match_data, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | YES | - |
| src/infrastructure/services/migrations/dedupeMappings.js | UPDATE, DELETE, SQL_VIA_QUERY | matches, matches_oddsportal_mapping | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| src/infrastructure/services/recon/MatchCanonicalJanitor.js | UPDATE, DELETE, SQL_VIA_QUERY | matches, matches_oddsportal_mapping | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| src/infrastructure/services/recon/ReconMappingPersistence.js | UPDATE, DELETE, SQL_VIA_QUERY | matches_oddsportal_mapping | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_ODDS_WRITE | - | - | YES |
| src/infrastructure/services/recon/ReconSchemaJanitor.js | DROP, CREATE_TABLE, ALTER, SQL_VIA_QUERY | valid_method, idx_recon_league_dictionary_unique, idx_recon_league_dictionary_team, recon_league_dictionary, matches_oddsportal_mapping | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_ODDS_WRITE | - | - | YES |
| src/infrastructure/shared/helpers/reconMappingSqlBuilders.js | INSERT, UPDATE | matches_oddsportal_mapping, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_ODDS_WRITE | - | YES | - |
| src/ml/inference/multi_model_validator.py | INSERT | predictions | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_TRAINING_WRITE | - | - | - |
| src/utils/typed_matcher.py | INSERT | predictions | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_TRAINING_WRITE | - | - | - |
| database/migrations/V12.2__add_matches_pipeline_status.sql | UPDATE, DROP, ALTER | matches, matches_pipeline_status_valid, column | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| database/migrations/V12.3__expand_matches_pipeline_status_for_recon.sql | DROP, ALTER | matches_pipeline_status_valid, matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql | DROP, ALTER | match_id_format, raw_match_data | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | YES |
| database/migrations/V12.7__add_tactical_stats_to_matches.sql | ALTER | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| database/migrations/V12.8__add_alignment_meta_to_bookmaker_odds_history.sql | ALTER | bookmaker_odds_history | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_ODDS_WRITE | - | - | - |
| database/migrations/V26.7__add_matches_labeling_governance_columns.sql | ALTER | matches | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | - |
| database/migrations/V6.5__hardened_matches_schema.sql | INSERT, UPDATE, DELETE, DROP, ALTER | matches, on, status_lowercase, season_format | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE | - | YES | YES |
| database/migrations/V6.6__hardened_l2_raw_storage.sql | UPDATE, ALTER | raw_match_data, on | ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE | YES | - | - |

---

## 最高风险表

| 表名 | 写入脚本数 |
|------|-----------|
| `matches` | 38 |
| `raw_match_data` | 25 |
| `l3_features` | 13 |
| `matches_oddsportal_mapping` | 10 |
| `on` | 7 |
| `result` | 6 |
| `bookmaker_odds_history` | 5 |
| `fotmob_raw_match_payloads` | 4 |
| `count` | 4 |
| `is` | 4 |

---

## 第一批修复建议 (First Batch)

64 个脚本建议第一批修复：

- **scripts/ops/ai_workflow_gate.py** — TRUNCATE → match — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_SCHEMA_WRITE
- **scripts/ops/backfill_historical_raw_match_data.js** — INSERT, UPDATE → raw_match_data, matches — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE, ALLOW_MATCHES_WRITE
- **scripts/ops/bulk_import_matches.js** — INSERT → raw_match_data — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE
- **scripts/ops/cleanup_csv_bulk_loader_import.js** — DELETE, SQL_VIA_QUERY → bookmaker_odds_history, matches — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_ODDS_WRITE, ALLOW_MATCHES_WRITE
- **scripts/ops/csv_bulk_loader.js** — INSERT, UPDATE → bookmaker_odds_history, matches — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_ODDS_WRITE, ALLOW_MATCHES_WRITE
- **scripts/ops/db_vault.js** — UPDATE, TRUNCATE → matches, matches_oddsportal_mapping — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE, ALLOW_ODDS_WRITE, ALLOW_SCHEMA_WRITE
- **scripts/ops/fixture_harvester_l1.js** — INSERT → matches — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE
- **scripts/ops/fotmob_safe_parser_schema_reuse_plan_no_write.py** — CREATE_TABLE, ALTER → fotmob_raw_match_payloads, raw_match_data — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE, ALLOW_SCHEMA_WRITE
- **scripts/ops/generate_bundesliga_fixtures.js** — INSERT → matches — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE
- **scripts/ops/helpers/dbBlueprint.js** — INSERT → matches, raw_match_data, matches_oddsportal_mapping — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE, ALLOW_RAW_MATCH_DATA_WRITE, ALLOW_ODDS_WRITE
- **scripts/ops/l1_matches_seed_commit_execute.js** — INSERT → matches — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE
- **scripts/ops/l2_guarded_reconciliation_write.js** — UPDATE → matches, count — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE
- **scripts/ops/l2_raw_match_data_write.js** — INSERT, UPDATE → raw_match_data, is — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE
- **scripts/ops/l2_remaining_raw_match_data_write.js** — INSERT, UPDATE → raw_match_data, is — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_RAW_MATCH_DATA_WRITE
- **scripts/ops/l3_stitch_pipeline.js** — UPDATE, CREATE_TABLE → matches, l3_features — 缺失: ALLOW_DB_WRITE, FINAL_DB_WRITE_CONFIRMATION, ALLOW_MATCHES_WRITE, ALLOW_SCHEMA_WRITE
- ... 还有 49 个

---

## 关键问题回答

1. **上一轮 34 个能否复现？** 是。当前发现 122 个（更多，因为覆盖了 src/ 和 database/）
2. **实际扫描发现多少个？** 122 个生产脚本 + 0 个测试文件
3. **最高风险？** 66 个 P0：涉及 DELETE/DROP/TRUNCATE 或 raw_match_data/matches 写入且无闸门
4. **测试/fixture 误伤？** 0 个测试文件被识别但标记为 TEST_FIXTURE_NO_FIX
5. **已有安全闸门？** 5 个脚本有完整闸门
6. **完全无闸门？** 110 个生产脚本完全没有任何安全闸门
7. **最容易被误写的表？** `matches` (38个脚本), `raw_match_data` (25个脚本), `l3_features` (13个脚本)
8. **raw_match_data 重复写入模式？** 存在。25 个脚本写入 raw_match_data，多数是独立实现的重复 INSERT 模式
9. **matches 重复写入模式？** 存在。38 个脚本写入 matches
10. **UPDATE/DELETE 高危脚本？** 21 个脚本存在 UPDATE/DELETE/DROP 操作
11. **第一批修哪些？** 64 个 FIRST_BATCH 脚本（P0 + 无闸门 + 非测试文件）
12. **下一步？** 见下文结论

---

## 结论

### 本 PR 状态

- **本 PR 没有修复 SC-002**
- **本 PR 只是专项审计和修复方案**
- **不允许因为本 PR 合并就认为写库风险已消除**

### 是否建议进入 p0_db_write_safety_gate_fix_phase1

**是。** 64 个 FIRST_BATCH 脚本需要立即添加安全闸门。建议下一步执行 `p0_db_write_safety_gate_fix_phase1`，只修改 FIRST_BATCH 脚本，每个脚本添加最小安全闸门（ALLOW_DB_WRITE + FINAL_DB_WRITE_CONFIRMATION），不改变业务逻辑。

### 修复前置条件

1. 用户必须明确授权进入 fix phase
2. 每次修复一个脚本，确保幂等
3. 修复后必须运行对应测试
4. 任何真实写库、真实抓取、真实训练必须先停下并请求授权

---

## 审计方法

- 纯静态文件扫描，读取文件内容进行正则匹配
- 未执行任何被扫描脚本
- 未连接任何数据库
- 未访问外部网络
- 扫描覆盖 5 个目录，`.js` / `.py` / `.sh` / `.sql` 四种扩展名

**报告路径:** docs/_reports/p0_db_write_safety_gate_dry_run_20260620.md
**扫描脚本:** scripts/ops/p0_db_write_safety_gate_dry_run.js (permanent)
**测试文件:** tests/unit/p0_db_write_safety_gate_dry_run.test.js (permanent)