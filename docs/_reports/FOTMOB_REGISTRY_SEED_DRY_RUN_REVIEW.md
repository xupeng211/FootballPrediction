<!-- markdownlint-disable MD013 -->

# FotMob Registry Seed Dry-run Review

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN-REVIEW
- reviewed PR: #1427
- reviewed plan path: `docs/_fixtures/fotmob_registry_seed_dry_run_plan.json`
- reviewed helper path: `scripts/ops/fotmob_registry_seed_dry_run.py`
- reviewed sql preview path: `docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_SQL_PREVIEW.sql`
- reviewed manifest path: `docs/_manifests/fotmob_registry_seed_dry_run_manifest.json`
- reviewed report path: `docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN.md`
- reviewed test path: `tests/unit/fotmob_registry_seed_dry_run.test.py`
- registry_seed_dry_run_status: `pass`

## 1. Registry Seed Structure Review

Fixture 结构完整，能表达 7 张 registry 表：

| 表 | 数量 | 状态 |
|----|------|------|
| football_teams | 18 | ✅ 覆盖 club + national |
| football_competitions | 10 | ✅ 覆盖 6 种 competition_type |
| football_competition_editions | 10 | ✅ 每赛事 1 届次 |
| football_team_competition_participation | 11 | ✅ 4 队跨赛事参与 |
| football_match_targets | 14 | ✅ 含 pending/blocked/stored/failed |
| football_match_target_teams | 28 | ✅ 每 target home+away |
| football_source_identities | 10 | ✅ 跨 team/competition |

FK-like references 在 fixture 内可解析（通过 fixture_id 交叉引用）。所有 source_match_id 均为 synthetic/fixture-only 前缀。无真实 FotMob ID。

## 2. Full-calendar Coverage Review

| 球队 | 目标数 | 覆盖赛事 | 状态 |
|------|--------|----------|------|
| Manchester United | 6 | Premier League, FA Cup, EFL Cup, UEFA Europa League | ✅ |
| England | 4 | WC Qualifier, Nations League, Friendly | ✅ |
| Kashima Antlers | 2 | J1 League, Emperor's Cup | ✅ |
| Leeds United | 2 | EFL Championship, FA Cup | ✅ |

全部 10 个 competition_type 通过 competition 表表达，覆盖：

- league (Premier League, J1 League, EFL Championship)
- domestic_cup (FA Cup, EFL Cup, Emperor's Cup)
- continental_club (UEFA Europa League)
- international_qualifier (World Cup Qualifier)
- nations_league (UEFA Nations League)
- friendly (International Friendly)

## 3. Target Selection Review

Target selection 逻辑正确：

- 输入 14 → 12 selectable（排除 1 blocked + 1 stored）→ 10 selected（受 budget=10 限制）
- 跳过 4 targets：
  - `fixture-mun-blocked-001`：target_state=blocked
  - `fixture-mun-stored-001`：raw_json_status=stored
  - 2 targets：request_budget exhausted（最低 priority）
- 选中 targets 按 priority 升序排列
- per_team_budget=5 和 per_competition_budget=4 均遵守
- failed target（fixture-eng-failed-001）正确处理为可重试

结论：**Target selection 正确，预算逻辑完整。**

## 4. SQL Preview Safety Review

SQL preview 文件安全：

- 文件顶部包含 `DRY-RUN SQL PREVIEW ONLY` 注释头
- 包含 `DO NOT EXECUTE` 注释
- 所有 INSERT 语句均已注释（以 SQL comment 前缀开头）
- 不包含可执行 INSERT/UPDATE/DELETE/TRUNCATE/DROP
- helper 脚本不含数据库连接代码
- manifest safety `sql_executed=false`
- 39 个 tests 中有 3 个专门验证 SQL preview 安全（`test_sql_preview_has_dry_run_header`、`test_sql_preview_all_inserts_are_commented`、`test_sql_preview_has_tables`），全部通过

结论：**SQL preview 严格安全，不可执行。**

## 5. Safety Review

| 检查项 | 状态 |
|--------|------|
| network_fetch_performed | false ✅ |
| db_write_performed | false ✅ |
| sql_executed | false ✅ |
| raw_json_write_performed | false ✅ |
| feature_parse_performed | false ✅ |
| scheduler_enabled | false ✅ |
| raw_write_ready_marked | false ✅ |

- helper 脚本不含 `requests.get`、`httpx.get`、`playwright`、`chromium` 等网络调用
- helper 脚本不含 `psycopg2`、`sqlalchemy`、`engine.execute` 等数据库连接
- SQL preview 完全是注释
- manifest 不含 `__NEXT_DATA__` 或 `pageProps`
- tests 验证了以上所有安全边界

## 6. Business Fit Review / 业务适配审查

这个 registry seed dry-run 能支撑用户"全年都有比赛分析和预测"的目标：

- **俱乐部跨赛事**：Manchester United 的 6 个 targets 跨 4 个赛事，验证了 `football_team_competition_participation` 能还原俱乐部全年赛程
- **国家队**：England 的 4 个 targets 跨 3 个赛事类型（预选赛、欧国联、友谊赛），验证了国家队赛程能纳入同一采集体系
- **杯赛**：FA Cup、EFL Cup、Emperor's Cup 均在 fixture 中
- **欧战**：UEFA Europa League 作为 continental_club 类型
- **日职联**：J1 League + Emperor's Cup 覆盖日本俱乐部赛程
- **次级联赛**：EFL Championship + FA Cup 覆盖次级联赛俱乐部赛程
- **未来 raw JSON 长期采集**：14 个 match_targets 中有 12 个 pending_raw_fetch 状态，足以展示 future collector 如何从 registry 选择目标

结论：**Registry seed plan 结构能支撑全年多维度赛事采集。**

## 7. Remaining Gaps

- 还没有真实 DB seed execution
- 还没有真实 registry 数据落库
- 还没有 live fetch
- 还没有 raw JSON write
- 还没有 scheduler
- 还没有 parser/feature layer
- 还没有 production rollout

## 8. Recommended Next Phase

推荐下一阶段：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH

约束：

- 只允许 dev/local DB
- 不允许 production DB
- 不允许 live fetch
- 不允许 raw JSON write
- 不允许 feature parse
- 只执行 registry seed 数据
- 必须可回滚或可重建
- 必须 idempotent（重复执行不产生重复行）
- 执行后立即 review
