<!-- markdownlint-disable MD013 -->

# FotMob Raw JSON 长期采集器 Dry-run Review

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW
- reviewed PR: #1425
- reviewed helper path: `scripts/ops/fotmob_raw_json_long_run_collector_dry_run.py`
- reviewed fixture path: `docs/_fixtures/fotmob_long_run_collector_dry_run_targets.json`
- reviewed manifest path: `docs/_manifests/fotmob_raw_json_long_run_collector_dry_run_manifest.json`
- reviewed report path: `docs/_reports/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN.md`
- reviewed design doc path: `docs/data/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN_DESIGN.md`
- reviewed test path: `tests/unit/fotmob_raw_json_long_run_collector_dry_run.test.py`
- dry_run_collector_status: `pass`

## 1. No-live-fetch Review

确认 dry-run collector 没有执行任何网络请求。

- helper 脚本不含 `requests`、`httpx`、`aiohttp`、`axios`、`fetch(`、`urllib` 等网络调用
- helper 脚本不含 `playwright`、`chromium`、`selenium`、`browser.launch` 等浏览器自动化调用
- 没有 FotMob live URL 构造或请求
- 没有代理轮换代码
- 没有反爬绕过逻辑
- manifest safety `network_fetch_performed=false`
- 59 个 unit tests 中有 2 个专门验证 helper 不含网络调用模式（`test_helper_no_network_fetch`、`test_helper_no_browser_automation`），全部通过

结论：**dry-run collector 严格 no-live-fetch，符合预期。**

## 2. No-write Review

确认 dry-run collector 没有执行任何数据库写入或 raw JSON 写入。

- helper 脚本不含 `INSERT`、`UPDATE`、`DELETE`、`TRUNCATE`、`DROP` 等 SQL 写操作
- helper 脚本不含 `psycopg2`、`asyncpg`、`sqlalchemy`、`engine.connect` 等数据库连接
- helper 脚本不含 `fotmob_raw_match_payloads`、`next_data_json`、`page_props_json`、`raw_payload_file` 等 raw JSON 写入引用
- 输出 manifest 不含 raw JSON 或 pageProps 内容
- 输出 report 不含 raw JSON 内容
- manifest safety `db_write_performed=false`、`raw_json_write_performed=false`、`feature_parse_performed=false`、`scheduler_enabled=false`、`raw_write_ready_marked=false`
- 59 个 unit tests 中有 3 个专门验证 no-DB/no-raw-JSON（`test_manifest_has_no_raw_json_body`、`test_helper_no_db_write`、`test_helper_no_raw_json_write`），全部通过

结论：**dry-run collector 严格 no-write，符合预期。**

## 3. Fixture Coverage Review

Fixture 包含 14 个 synthetic metadata-only targets，覆盖以下场景：

| 覆盖案例 | 数量 | 状态 |
|----------|------|------|
| Manchester United 跨赛事（Premier League, FA Cup, EFL Cup, UEFA Europa League） | 4 | ✅ |
| England 国家队（World Cup qualifier, Nations League, Friendly） | 3 | ✅ |
| 日本俱乐部（J1 League, Emperor's Cup） | 2 | ✅ |
| 次级联赛（EFL Championship, FA Cup for Championship team） | 2 | ✅ |
| 国内杯赛（FA Cup, EFL Cup, Emperor's Cup） | 跨案例 | ✅ |
| 洲际俱乐部赛事（UEFA Europa League） | 1 | ✅ |
| 国际预选赛（World Cup qualifier） | 1 | ✅ |
| blocked target（用于验证 skip 逻辑） | 1 | ✅ |
| raw_json_status=stored target（用于验证 skip 逻辑） | 1 | ✅ |
| raw_json_status=failed target（用于验证 retry 逻辑） | 1 | ✅ |

Fixture 不包含任何 raw JSON 或 `__NEXT_DATA__` 内容（`last_error_message` 字段已清理为不含 `__NEXT_DATA__` 的安全文本）。

结论：**Fixture 覆盖范围完整，满足 long-run collector dry-run 验证需求。**

## 4. Selection Logic Review

dry-run 选择逻辑验证：

- 输入 14 targets → 12 selectable（排除 1 blocked + 1 stored）
- 选中 10 targets（受 request_budget=10 限制）
- 跳过 4 targets：
  - `synthetic-mun-blocked-001`：`target_state=blocked（默认跳过）`
  - `synthetic-mun-stored-001`：`raw_json_status=stored（已存储）`
  - `synthetic-champ-facup-001`：`request_budget exhausted`
  - `synthetic-eng-friend-001`：`request_budget exhausted`
- 选中 targets 按 priority 升序排列（5→17），再按 match_date 排序
- 未选中 blocked targets（默认 skip）
- 未选中 raw_json_status=stored targets
- 包含 raw_json_status=failed target（correctly treated as eligible for retry：`synthetic-eng-failed-001`）
- 跳过原因明确记录在 manifest 中

被 budget 裁剪的 2 个 targets 分别是：

- `synthetic-champ-facup-001`（priority 18，secondary league FA Cup）
- `synthetic-eng-friend-001`（priority 20，England Friendly）

均为最低 priority 目标，裁剪合理。

结论：**Selection logic 正确，符合设计预期。**

## 5. Budget Review

| 预算类型 | 设定值 | 实际使用 | 状态 |
|----------|--------|----------|------|
| request_budget | 10 | 10（全部用完） | ✅ |
| per_team_budget | 5 | 各队均 ≤ 5 | ✅ |
| per_competition_budget | 4 | 各赛事均 ≤ 4 | ✅ |

详细验证：

- Manchester United（synthetic-team-mun）：selected 中出现次数 = 4（≤5）
- England（synthetic-team-eng）：selected 中出现次数 = 3（≤5）
- Kawasaki Frontale（synthetic-team-kaw）：selected 中出现次数 = 2（≤5）
- Leeds United（synthetic-team-lee）：selected 中出现次数 = 1（≤5）
- Premier League（synthetic-comp-epl）：selected 中出现次数 = 1（≤4）
- FA Cup（synthetic-comp-facup）：selected 中出现次数 = 1（≤4）
- Nations League（synthetic-comp-unl）：selected 中出现次数 = 2（≤4）

budget-exhausted 的 2 个 targets 在 manifest 中有明确的 `skip_reason`。

结论：**Budget 逻辑正确，多层预算职责清晰。**

## 6. Stop Policy Review

Manifest stop_policy 包含 9 项策略，全部为 `true`：

| 策略 | 值 | 说明 |
|------|----|------|
| stop_on_403 | true | FotMob 拒绝访问时停止 |
| stop_on_429 | true | 频率限制时停止 |
| stop_on_captcha | true | 验证码阻挡时停止 |
| stop_on_unexpected_html | true | HTML 结构异常时停止 |
| stop_on_schema_shift | true | JSON schema 变更时停止 |
| no_retry_storm | true | 不重试风暴 |
| no_proxy_rotation | true | 不轮换代理 |
| no_anti_bot_bypass | true | 不绕过反爬 |
| no_browser_automation | true | 不启用浏览器自动化 |

59 个 unit tests 中有 1 个专门验证所有 stop_policy 值为 true（`test_manifest_has_stop_policy`），全部通过。

结论：**Stop policy 完整，符合安全采集原则。**

## 7. Business Fit Review / 业务适配审查

这个 dry-run collector 是否符合"全年都有比赛分析和预测"的长期目标：

- **支持俱乐部跨赛事目标计划**：Manchester United 的 4 个 targets 跨 Premier League、FA Cup、EFL Cup、UEFA Europa League，验证了系统可以按球队还原跨赛事全年赛程，而不仅仅是某个联赛内。这与 football calendar target registry 的 `football_team_competition_participation` 跨赛事模型一致。

- **支持国家队目标计划**：England 国家队的 3 个 targets 跨 World Cup qualifier、Nations League 和 Friendly，验证了国家队赛事（国际预选赛、洲际联赛、友谊赛）可以进入同一采集目标队列。

- **支持杯赛、欧战、次级联赛、日职联**：Fixture 覆盖 domestic_cup（FA Cup、EFL Cup、Emperor's Cup）、continental_club（UEFA Europa League）、secondary league（EFL Championship）和 Japanese club（J1 League），验证了这些赛事的 target 都能经过相同的 selection/budget/priority 逻辑。

- **支持未来从 target registry 选择 pending_raw_fetch**：Selection 逻辑基于 `target_state=pending_raw_fetch` 和 `raw_json_status in (missing, stale, failed)`，与 football calendar target registry 设计的状态机一致。

- **只是计划模拟，还不是真实采集**：Dry-run 明确声明 no-live-fetch、no-DB-write、no-raw-JSON-write。所有 59 个 tests 通过的 manifest 和 report 都确认了这些安全边界。未来真实采集器需要单独的 explicit authorization。

结论：**这个 dry-run 满足"全年都有比赛分析和预测"的基础架构要求，是安全推进 one-day controlled collection 的前置基础。**

## 8. Remaining Gaps

- 没有真实 registry seed（synthetic targets 只是 fixture）
- 没有真实 DB query target selection（selection 基于 JSON fixture）
- 没有 live fetch（所有 target 均为 synthetic metadata）
- 没有 raw JSON write（raw JSON 存储未发生）
- 没有 scheduler（采集调度未启用）
- 没有 parser/feature layer（解析和特征工程尚未开始）
- 没有 production rollout（一切在 dry-run 阶段）
- 还不能说全年采集系统完成

## 9. Recommended Next Phase

推荐下一阶段：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN

理由：

1. 当前 football calendar target registry 有 7 张表，但没有 seed 任何真实数据
2. 直接进入 one-day live collection 风险太高
3. 应该先在 dev 环境中 seed 少量真实 club/national/competition 数据到 registry
4. 然后用 dry-run collector 读取这些真实 registry targets
5. 验证 target selection query 在真实数据上是否正确
6. 再进入 one-day controlled live collection

如果 registry seed dry-run 也通过，则下一步：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-NO-FEATURE-PARSE-PREFLIGHT

该阶段必须先 preflight authorization：

- 明确是否允许 live fetch
- 明确是否允许 raw JSON write（仅 dev/local？还是 production？）
- 明确 request budget
- 明确 stop-on-block 策略
- 明确 no feature parse
- 明确单线程、低频执行
- 明确单日采集后立即 review

当前阶段不允许直接 live fetch，也不允许直接 raw JSON write。
所有 live decision 需要单独 explicit authorization。
