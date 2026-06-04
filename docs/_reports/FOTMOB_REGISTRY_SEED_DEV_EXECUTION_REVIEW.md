<!-- markdownlint-disable MD013 -->

# FotMob Registry Seed Dev Execution Review

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-REVIEW
- reviewed PR: #1429
- reviewed helper path: `scripts/ops/fotmob_registry_seed_dev_execution.py`
- reviewed manifest path: `docs/_manifests/fotmob_registry_seed_dev_execution_manifest.json`
- reviewed report path: `docs/_reports/FOTMOB_REGISTRY_SEED_DEV_EXECUTION.md`
- reviewed test path: `tests/unit/fotmob_registry_seed_dev_execution.test.py`
- registry_seed_dev_execution_status: `pass`

## 1. DB Environment Review

- db_environment: `docker_dev`
- production_db_guard: `pass`
- 脚本检测 `ENV`、`APP_ENV`、`NODE_ENV` 等环境变量，拒绝 `production/prod/live/prd` 标识
- 检测 DB_HOST 模式 `rds.amazonaws.com`、`.production.`、`cloudsql.google` 等 production URL pattern
- 未检测到 safe env vars 或 docker/localhost 时会拒绝执行
- `--require-dev-db` 默认为 true
- 17 个 tests 中有 3 个专门验证 production guard (`test_helper_production_guard_blocked`、`test_helper_production_guard_dev_pass`、`test_manifest_environment`)
- `production_db_write_performed=false` 确认

结论：**Production DB guard 充分，DB 环境安全。**

## 2. DB Write Scope Review

确认写入范围只限 7 张 football calendar registry 表：

| 表 | 写入 |
|----|------|
| football_teams | ✅ ON CONFLICT DO NOTHING |
| football_competitions | ✅ ON CONFLICT DO NOTHING |
| football_competition_editions | ✅ ON CONFLICT DO NOTHING |
| football_team_competition_participation | ✅ ON CONFLICT DO NOTHING |
| football_match_targets | ✅ ON CONFLICT DO NOTHING |
| football_match_target_teams | ✅ ON CONFLICT DO NOTHING |
| football_source_identities | ✅ ON CONFLICT DO NOTHING |

确认没有写入以下表：

- fotmob_raw_match_payloads ✅
- raw_match_data ✅
- l3_features ✅
- match_features_training ✅
- predictions ✅
- odds ✅
- model ✅
- feature tables ✅

- db_write_scope 明确为 `registry_tables_only`
- `fotmob_raw_match_payloads_write_performed=false`
- `raw_match_data_write_performed=false`

结论：**DB 写入范围严格限定于 registry tables，安全。**

## 3. Idempotency Review

- first_run_inserted_total: 101（全部 7 表）
- second_run_inserted_total: 0
- 所有表使用 `ON CONFLICT ... DO NOTHING` 策略
- unique constraints 生效：`(source, source_team_id)`、`(source, source_competition_id)`、`(source, source_match_id)` 等
- 重复执行不产生重复行
- 17 个 tests 中有 1 个专门验证 idempotency (`test_manifest_idempotency`)

结论：**Idempotency 正确，可安全重复执行。**

## 4. Seed Counts Review

| 表 | 最终行数 | 预期 | 状态 |
|----|---------|------|------|
| football_teams | 18 | 18 | ✅ |
| football_competitions | 10 | 10 | ✅ |
| football_competition_editions | 10 | 10 | ✅ |
| football_team_competition_participation | 11 | 11 | ✅ |
| football_match_targets | 14 | 14 | ✅ |
| football_match_target_teams | 28 | 28 | ✅ |
| football_source_identities | 10 | 10 | ✅ |
| **total** | **101** | **101** | ✅ |

结论：**所有 seed counts 与 dry-run plan 一致。**

## 5. Target Selection Query Review

- selected_target_count: 10
- skipped_target_count: 4
- skip_reasons 包含: `target_state=blocked`、`raw_json_status=stored`、`request_budget exhausted`
- request_budget=10 respected: selected(10) ≤ budget(10)
- per_team_budget=5 respected
- per_competition_budget=4 respected

结论：**Target selection 查询逻辑正确，预算约束生效。**

## 6. Team Full-calendar Query Review

| 球队 | 目标数 | 预期 | 状态 |
|------|--------|------|------|
| Manchester United | 6 | ≥4 | ✅ |
| England | 4 | ≥3 | ✅ |
| Kashima Antlers | 2 | ≥2 | ✅ |
| Leeds United | 2 | ≥2 | ✅ |

查询使用 `football_match_target_teams JOIN football_match_targets JOIN football_competitions` 路径，验证了 registry 表间 JOIN 能正确还原球队跨赛事日历。

结论：**Team full-calendar 查询正确。**

## 7. SQL / Write Operation Safety Review

- 所有写入使用 `ON CONFLICT DO NOTHING`（幂等）
- 无 DROP ✅
- 无 TRUNCATE ✅
- 无 DELETE ✅
- 无 UPDATE ✅
- 脚本在 execute_seed 中使用 `conn.commit()` 进行事务提交
- 错误通过 `try/except/finally` 捕获，`conn.close()` 在 finally 块中确保连接关闭
- 在异常情况下显式 `conn.rollback()` 防止半写入

结论：**SQL 操作安全。**

## 8. Safety Flags Review

| 标志 | 预期 | 实际 | 状态 |
|-----|------|------|------|
| network_fetch_performed | false | false | ✅ |
| raw_json_write_performed | false | false | ✅ |
| fotmob_raw_match_payloads_write_performed | false | false | ✅ |
| raw_match_data_write_performed | false | false | ✅ |
| feature_parse_performed | false | false | ✅ |
| scheduler_enabled | false | false | ✅ |
| raw_write_ready_marked | false | false | ✅ |

- helper 脚本不含 `requests.get`、`httpx.get`、`playwright`、`chromium` 等网络调用
- helper 脚本不含 `fotmob_raw_match_payloads`、`raw_match_data` 等 raw JSON 表名
- tests 验证了以上所有安全边界

结论：**所有 safety flags 正确。**

## 9. Business Fit Review / 业务适配审查

PR #1429 把系统从 "registry seed dry-run"（只有 JSON 预览）推进到了 "dev/local registry seed execution"（真正写 DB）。

这对全年比赛分析的重要性：

- **registry 表终于有数据了**：7 张 registry 表不再是空表，而是承载了 18 支球队、10 个赛事、14 个 match target 和 28 条 match_target_teams 记录
- **可以查出跨赛事日历**：从 registry DB 用 JOIN 查询，验证了 Manchester United 全年 6 场跨 4 赛事、England 国家队的 4 场跨 3 赛事类型
- **target selection 从 DB 正确执行**：从 football_match_targets 表选中 10 个 pending_raw_fetch 目标，跳过 blocked/stored/budget-exhausted
- **为 raw JSON 采集做准备**：registry 中的 match_targets 是未来 collector 的目标来源
- **仍未进入 live fetch**：所有操作限定在 dev/local DB，没有访问 FotMob，没有写 raw JSON

结论：**这次执行成功验证了 registry DB 能承载长期采集的元数据层，风险可控。**

## 10. Remaining Gaps

- 还没有 production DB seed
- 还没有真实 FotMob live fetch
- 还没有 raw JSON write
- 还没有 scheduler
- 还没有 parser/feature layer
- 还没有 production rollout
- 还没有大规模 registry seed（只有 18 队/10 赛事）
- 还没有真实 source_match_id discovery

## 11. Recommended Next Phase

推荐下一阶段：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-TARGET-SELECTION-DB-DRY-RUN

说明：

- 从 dev/local registry DB 查询 pending_raw_fetch targets
- **不访问 FotMob**
- **不写 raw JSON**
- 只验证从真实 registry DB 中生成 collector queue
- 验证排序、预算、skip reason、stop policy
- 为未来 one-day controlled no-feature raw JSON collection 做前置准备

不要推荐直接 live fetch。不要推荐 production rollout。
