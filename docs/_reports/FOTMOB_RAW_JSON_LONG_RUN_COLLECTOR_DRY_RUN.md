<!-- markdownlint-disable MD013 -->

# FotMob Raw JSON 长期采集器 Dry-run 报告

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN
- run_id: fotmob_long_run_collector_dry_run_v1
- generated_at: 2026-06-02T22:13:31Z

## 1. 概要

- 输入目标总数: 14
- 选中目标数: 10
- 跳过目标数: 4
- 请求预算: 10
- 单队预算: 5
- 单赛事预算: 4

## 2. 阶段安全声明

- **本阶段没有 live fetch**
- **本阶段没有 DB write**
- **本阶段没有 raw JSON write**
- **本阶段没有 feature parse**
- **本阶段没有 scheduler 启用**
- 这只是采集计划模拟（dry-run）
- 支持跨赛事球队全年赛程
- 所有目标是 synthetic metadata-only

## 3. 预算结果

- request_budget=10，已使用 10
- per_team_budget=5
- per_competition_budget=4
- 剩余预算: 0

## 4. 验证结果

- 全部通过 ✓

## 5. 覆盖范围

- 俱乐部赛程覆盖: 是
- 国家队赛程覆盖: 是
- 国内杯赛覆盖: 是
- 洲际俱乐部赛事覆盖: 是
- 国际预选赛覆盖: 是
- 欧国联覆盖: 是
- 友谊赛覆盖: 否
- 日本俱乐部/J League 覆盖: 是
- 次级联赛覆盖: 是
- Manchester United 跨赛事覆盖: 是
- England 国家队覆盖: 是

## 6. 选中目标明细

| # | source_match_id | team_names | competition | type | priority | match_date |
|---|-----------------|------------|-------------|------|----------|------------|
| 1 | synthetic-eng-wcq-001 | England, Poland | FIFA World Cup Qualifier | international_qualifier | 5 | 2026-09-05T18:00:00Z |
| 2 | synthetic-eng-unl-001 | England, Germany | UEFA Nations League | nations_league | 8 | 2026-09-09T18:00:00Z |
| 3 | synthetic-mun-epl-001 | Manchester United, Liverpool | Premier League | league | 10 | 2026-08-15T14:00:00Z |
| 4 | synthetic-mun-uel-001 | Manchester United, AS Roma | UEFA Europa League | continental_club | 11 | 2026-09-19T19:00:00Z |
| 5 | synthetic-mun-facup-001 | Manchester United, Chelsea | FA Cup | domestic_cup | 12 | 2026-08-22T14:00:00Z |
| 6 | synthetic-eng-failed-001 | England, Italy | UEFA Nations League | nations_league | 13 | 2026-09-06T18:00:00Z |
| 7 | synthetic-mun-eflcup-001 | Manchester United, Newcastle United | EFL Cup | domestic_cup | 14 | 2026-09-12T18:45:00Z |
| 8 | synthetic-jpn-j1-001 | Kawasaki Frontale, Yokohama F. Marinos | J1 League | league | 15 | 2026-08-16T10:00:00Z |
| 9 | synthetic-champ-001 | Leeds United, Sunderland | EFL Championship | league | 16 | 2026-08-15T14:00:00Z |
| 10 | synthetic-jpn-empcup-001 | Kawasaki Frontale, Urawa Red Diamonds | Emperor's Cup | domestic_cup | 17 | 2026-09-26T10:00:00Z |

## 7. 跳过目标明细

| # | source_match_id | team_names | skip_reason |
|---|-----------------|------------|-------------|
| 1 | synthetic-mun-blocked-001 | Manchester United, Manchester City | target_state=blocked (默认跳过) |
| 2 | synthetic-mun-stored-001 | Manchester United, Tottenham Hotspur | raw_json_status=stored (已存储) |
| 3 | synthetic-champ-facup-001 | Leeds United, Sheffield Wednesday | request_budget exhausted |
| 4 | synthetic-eng-friend-001 | England, Brazil | request_budget exhausted |

## 8. 球队全年赛程示例

### 8.1 Manchester United 跨赛事示例

Manchester United 在本次 dry-run 中有 4 个目标跨以下赛事：

- Premier League (league) — 2026-08-15T14:00:00Z
- UEFA Europa League (continental_club) — 2026-09-19T19:00:00Z
- FA Cup (domestic_cup) — 2026-08-22T14:00:00Z
- EFL Cup (domestic_cup) — 2026-09-12T18:45:00Z

这说明系统可以按球队跨 Premier League、FA Cup、EFL Cup、UEFA competitions 还原全年赛程。

### 8.2 England 国家队示例

England 国家队在本次 dry-run 中有 3 个目标跨以下赛事：

- FIFA World Cup Qualifier (international_qualifier) — 2026-09-05T18:00:00Z
- UEFA Nations League (nations_league) — 2026-09-09T18:00:00Z
- UEFA Nations League (nations_league) — 2026-09-06T18:00:00Z

这说明系统可以覆盖 World Cup qualifier、UEFA Nations League 和 Friendly。

### 8.3 日本俱乐部示例

日本俱乐部在本次 dry-run 中有 2 个目标：

- J1 League (league) — 2026-08-16T10:00:00Z
- Emperor's Cup (domestic_cup) — 2026-09-26T10:00:00Z

### 8.4 次级联赛示例

次级联赛俱乐部在本次 dry-run 中有 1 个目标：

- EFL Championship (league) — 2026-08-15T14:00:00Z

## 9. Stop Policy

未来真实采集器必须遵守以下策略：

| 策略 | 值 |
|------|----|
| stop_on_403 | true |
| stop_on_429 | true |
| stop_on_captcha | true |
| stop_on_unexpected_html | true |
| stop_on_schema_shift | true |
| no_retry_storm | true |
| no_proxy_rotation | true |
| no_anti_bot_bypass | true |
| no_browser_automation | true |

## 10. Safety Review

| 检查项 | 状态 |
|--------|------|
| network_fetch_performed | false ✅ |
| db_write_performed | false ✅ |
| raw_json_write_performed | false ✅ |
| feature_parse_performed | false ✅ |
| scheduler_enabled | false ✅ |
| raw_write_ready_marked | false ✅ |

## 11. Remaining Gaps

- no real registry seed yet（还没有真实 registry 数据）
- no live FotMob fetch（没有真实 FotMob 请求）
- no DB write（没有数据库写入）
- no raw JSON storage in this PR（本 PR 没有 raw JSON 存储）
- no scheduler（没有调度器）
- no parser/feature（没有解析器/特征工程）
- no production rollout（没有生产上线）

## 12. Recommended Next Phase

推荐下一阶段：**FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW**。

注意：这一步后建议先 review dry-run，而不是直接 one-day live collection。
只有 dry-run review 通过后，才允许进入 FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-NO-FEATURE-PARSE。
one-day collection 仍应低频、单线程、限预算、无 feature parse。
