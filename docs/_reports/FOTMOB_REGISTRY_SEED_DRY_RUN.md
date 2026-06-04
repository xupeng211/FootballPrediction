<!-- markdownlint-disable MD013 -->

# FotMob Registry Seed Dry-run 报告

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN
- run_id: fotmob_registry_seed_dry_run_v1
- generated_at: 2026-06-04T01:56:21Z

## 1. 概要

- teams: 18
- competitions: 10
- competition_editions: 10
- team_competition_participation: 11
- match_targets: 14
- match_target_teams: 28
- source_identities: 10

## 2. 阶段安全声明

- **本 PR 没有执行 SQL**
- **本 PR 没有写 DB**
- **本 PR 没有访问 FotMob**
- **本 PR 没有写 raw JSON**
- **本 PR 没有启用 scheduler**
- **本 PR 没有 feature parse**
- SQL preview 文件顶部已标注 DO NOT EXECUTE
- 所有 INSERT statements 已注释
- 这只是 registry seed plan dry-run

## 3. 生成实体统计

| 表 | 数量 |
|----|------|
| football_teams | 18 |
| football_competitions | 10 |
| football_competition_editions | 10 |
| football_team_competition_participation | 11 |
| football_match_targets | 14 |
| football_match_target_teams | 28 |
| football_source_identities | 10 |

## 4. 验证结果

- 全部通过 ✓

## 5. 覆盖范围

- club teams: 是
- national teams: 是
- league: 是
- domestic_cup: 是
- continental_club: 是
- international_qualifier: 是
- nations_league: 是
- friendly: 是

## 6. Target Selection Dry-run

- 输入 match_targets: 14
- 选中: 10
- 跳过: 4
- request_budget: 10
- per_team_budget: 5
- per_competition_budget: 4

### 跳过明细

| source_match_id | skip_reason |
|-----------------|-------------|
| fixture-mun-blocked-001 | target_state=blocked (默认跳过) |
| fixture-mun-stored-001 | raw_json_status=stored (已存储) |
| fixture-champ-facup-001 | request_budget exhausted |
| fixture-eng-friend-001 | request_budget exhausted |

## 7. 球队全年赛程 Dry-run

### 7.1 Manchester United

Man United 全年赛程有 6 场比赛：

- Premier League (league) — 2026-08-01T14:00:00Z [state=raw_json_stored, raw=stored]
- Premier League (league) — 2026-08-08T14:00:00Z [state=blocked, raw=missing]
- Premier League (league) — 2026-08-15T14:00:00Z [state=pending_raw_fetch, raw=missing]
- UEFA Europa League (continental_club) — 2026-09-19T19:00:00Z [state=pending_raw_fetch, raw=missing]
- FA Cup (domestic_cup) — 2026-08-22T14:00:00Z [state=pending_raw_fetch, raw=missing]
- EFL Cup (domestic_cup) — 2026-09-12T18:45:00Z [state=pending_raw_fetch, raw=missing]

### 7.2 England 国家队

England 全年赛程有 4 场比赛：

- FIFA World Cup Qualifier (international_qualifier) — 2026-09-05T18:00:00Z [state=pending_raw_fetch]
- UEFA Nations League (nations_league) — 2026-09-09T18:00:00Z [state=pending_raw_fetch]
- UEFA Nations League (nations_league) — 2026-09-06T18:00:00Z [state=pending_raw_fetch]
- International Friendly (friendly) — 2026-10-14T19:00:00Z [state=pending_raw_fetch]

### 7.3 Kashima Antlers (Japanese club)

Kashima Antlers 全年赛程有 2 场比赛：

- J1 League (league) — 2026-08-16T10:00:00Z [state=pending_raw_fetch]
- Emperor's Cup (domestic_cup) — 2026-09-26T10:00:00Z [state=pending_raw_fetch]

### 7.4 Leeds United (Secondary league)

Leeds United 全年赛程有 2 场比赛：

- EFL Championship (league) — 2026-08-15T14:00:00Z [state=pending_raw_fetch]
- FA Cup (domestic_cup) — 2026-08-29T14:00:00Z [state=pending_raw_fetch]

## 8. Skip Logic

- blocked target skipped: 是
- stored target skipped: 是
- budget_exhausted present: 是

## 9. Safety Review

| 检查项 | 状态 |
|--------|------|
| network_fetch_performed | false ✅ |
| db_write_performed | false ✅ |
| sql_executed | false ✅ |
| raw_json_write_performed | false ✅ |
| feature_parse_performed | false ✅ |
| scheduler_enabled | false ✅ |
| raw_write_ready_marked | false ✅ |

## 10. Remaining Gaps

- SQL preview 生成但未执行
- 没有真实 DB seed
- 没有真实 FotMob live fetch
- 没有 raw JSON write
- 没有 scheduler
- 没有 parser/feature
- 没有 production rollout

## 11. Recommended Next Phase

推荐下一阶段：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN-REVIEW

审查通过后再：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH

当前阶段不允许 live fetch。
