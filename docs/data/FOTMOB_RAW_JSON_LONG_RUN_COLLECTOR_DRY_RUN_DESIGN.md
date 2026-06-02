<!-- markdownlint-disable MD013 -->

# FotMob Raw JSON 长期采集器 Dry-run 设计

- lifecycle: permanent / governance
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN
- version: 1.0.0
- no network fetch / no DB write / no raw JSON write / no scheduler enable / no feature parse
- raw_write_ready remains false

## 1. 本阶段目标

本阶段实现一个长期采集器 dry-run。它只生成采集计划，不访问 FotMob 网络，不写数据库，不保存 raw JSON。

核心验证目标：

1. 如何从 football calendar target registry 选出 `pending_raw_fetch` 目标
2. 如何按球队还原全年比赛日历
3. 如何跨联赛、杯赛、欧战、国家队赛事生成目标队列
4. 如何控制请求预算
5. 如何设置 stop-on-block 策略
6. 如何生成 run manifest / dry-run report
7. 如何为未来真实采集器打基础

## 2. 为什么需要 dry-run

长期采集涉及全年赛事、杯赛、欧战、国家队、次级联赛等多维度目标。

直接 live fetch 风险太高：

- 可能触发 FotMob 反爬机制
- 可能消耗过多请求预算
- 可能采集错误目标（反向 fixture、已取消比赛）
- 可能遗漏跨赛事球队日历

因此需要先验证目标选择、队列排序、预算分配、失败策略和审计输出。

## 3. 输入来源

dry-run 可使用两类输入：

- **synthetic/sample target fixture**：手工构造的 metadata-only 目标列表
- **future read-only target registry query**：未来从数据库查询真实目标

本阶段优先用 synthetic fixture，不要求真实 DB seed。

## 4. Sample targets 覆盖范围

必须设计样例，至少覆盖以下场景：

### 4.1 Manchester United 跨赛事

- Premier League（联赛）
- FA Cup（国内杯赛）
- EFL Cup（国内杯赛）
- UEFA competition（洲际俱乐部赛事）

### 4.2 England national team

- World Cup qualifier（世界杯预选赛）
- UEFA Nations League（欧国联）
- Friendly（友谊赛）

### 4.3 Japanese club

- J1 League（日职联）
- Emperor's Cup 或 J.League Cup（国内杯赛）

### 4.4 Secondary league club

- English Championship（次级联赛）
- domestic cup（国内杯赛）

## 5. Dry-run 输出内容

每个 run 输出两个文件：

### 5.1 Manifest（JSON）

```json
{
  "schema_version": "fotmob_raw_json_long_run_collector_dry_run_v1",
  "phase": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN",
  "run_id": "...",
  "generated_at": "...",
  "planned_target_count": 0,
  "selected_target_count": 0,
  "skipped_target_count": 0,
  "input_target_count": 0,
  "request_budget": 0,
  "per_team_budget": 0,
  "per_competition_budget": 0,
  "selected_targets": [],
  "skipped_targets": [],
  "stop_policy": {},
  "coverage": {},
  "safety": {},
  "recommended_next_phase": "..."
}
```

### 5.2 Report（Markdown）

用中文说明：

- 本阶段没有 live fetch
- 本阶段没有 DB write
- 本阶段没有 raw JSON write
- 只是采集计划模拟
- 支持跨赛事球队全年赛程
- 下一阶段建议

## 6. Target selection 规则

选择逻辑：

- 选择 `target_state = pending_raw_fetch`
- `raw_json_status` 为 `missing`、`stale` 或 `failed`
- 跳过 `raw_json_status = stored`
- 跳过 `target_state = blocked`（默认不选 blocked）
- 按 `priority` 升序（数值越小越优先）
- 再按 `match_date` 升序（早的比赛先采）
- 应用 `request_budget`（总请求上限）
- 应用 `per_team_budget`（单队请求上限）
- 应用 `per_competition_budget`（单赛事请求上限）

## 7. Team full-calendar 规则

系统按 team 维度还原全年比赛：

1. 从 `football_teams` 找到目标球队
2. 通过 `football_team_competition_participation` 找到该队参加的所有赛事届次
3. 通过 `football_match_targets` + `football_match_target_teams` 找到该队所有比赛
4. 按 `match_date` 排序，覆盖所有赛事类型

例如 Manchester United 的最近比赛不只来自 Premier League，还包括 FA Cup、EFL Cup 和 UEFA competitions。

## 8. Stop policy

dry-run 明确未来真实采集器应遵守：

- `stop_on_403`: true — 立即停止整个 run
- `stop_on_429`: true — 立即停止整个 run
- `stop_on_captcha`: true — 立即停止整个 run
- `stop_on_unexpected_html`: true — 停止整个 run
- `stop_on_schema_shift`: true — 停止整个 run
- `no_retry_storm`: true — 不重试风暴
- `no_proxy_rotation`: true — 不轮换代理
- `no_anti_bot_bypass`: true — 不绕过反爬
- `no_browser_automation`: true — 不启用浏览器自动化（除非单独授权）

## 9. 安全边界

本阶段明确不做：

- no FotMob network fetch
- no HTTP request
- no browser automation
- no Playwright / Chromium
- no DB connection（除非未来单独授权）
- no DB write
- no INSERT / UPDATE / DELETE / TRUNCATE / DROP
- no migration creation
- no raw JSON write
- no fotmob_raw_match_payloads write
- no raw_match_data write
- no l3_features write
- no match_features_training write
- no predictions write
- no scheduler enable
- no parser / feature extraction
- no raw_write_ready marking

## 10. 下一阶段

推荐下一阶段：**FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW**

说明：dry-run 完成后建议先 review，通过后才允许进入 one-day controlled collection。

只有 dry-run review 通过后，才允许：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-NO-FEATURE-PARSE

该阶段仍应：

- 低频、单线程
- 限预算
- 无 feature parse
- 无 raw_match_data write
- 需单独授权

## 11. 与 Target Registry 的关系

本 dry-run 基于 football calendar target registry 设计（见 `docs/data/FOTMOB_FOOTBALL_CALENDAR_TARGET_REGISTRY_DESIGN.md`）。

dry-run 不要求 registry 有真实数据；它使用 synthetic fixture 模拟未来 collector 行为。

完整采集链（未来状态）：

```
football_teams
  → football_team_competition_participation
    → football_match_targets (target_state = pending_raw_fetch)
      → dry-run collector (本阶段：只生成计划)
        → live collector (未来阶段：真实 fetch)
          → fotmob_raw_match_payloads (raw JSON 持久化)
```

## 12. 验证清单

dry-run 完成后必须验证：

- [ ] fixture 存在且 schema_version 正确
- [ ] helper 存在且可执行
- [ ] manifest 生成且不含 raw JSON
- [ ] report 生成且声明 no-live-fetch
- [ ] selected targets 排除 stored 目标
- [ ] selected targets 排除 blocked 目标
- [ ] request budget 生效
- [ ] per-team budget 生效
- [ ] per-competition budget 生效
- [ ] Manchester United 跨赛事目标存在
- [ ] national team 目标存在
- [ ] J League / Japanese club 目标存在
- [ ] secondary league 目标存在
- [ ] 无网络 fetch 执行
- [ ] 无 DB write 执行
- [ ] 无 raw JSON write 执行
- [ ] 无 feature parse 执行
- [ ] raw_write_ready 标记为 false
- [ ] unit tests 全部通过
- [ ] markdownlint 通过
- [ ] static safety 通过
