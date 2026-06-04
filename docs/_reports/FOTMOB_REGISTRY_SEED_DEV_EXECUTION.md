<!-- markdownlint-disable MD013 -->

# FotMob Registry Seed Dev Execution 报告

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH
- run_id: fotmob_registry_seed_dev_execution_v1
- generated_at: 2026-06-04T02:34:09Z

## 1. DB Environment

- db_environment: docker_dev
- production_db_guard: pass

## 2. Seed Result

| 表 | 第一次插入 | 第二次插入 | 最终行数 |
|----|-----------|-----------|---------|
| football_teams | 0 | 0 | 18 |
| football_competitions | 0 | 0 | 10 |
| football_competition_editions | 0 | 0 | 10 |
| football_team_competition_participation | 0 | 0 | 11 |
| football_match_targets | 0 | 0 | 14 |
| football_match_target_teams | 0 | 0 | 28 |
| football_source_identities | 0 | 0 | 10 |

- idempotency: pass (第二次执行全部 0 inserted)

## 3. 安全声明

- **本 PR 只在 dev/local DB 执行**
- **本 PR 没有访问 FotMob**
- **本 PR 没有写 raw JSON**
- **本 PR 没有写 fotmob_raw_match_payloads**
- **本 PR 没有写 raw_match_data**
- **本 PR 没有启用 scheduler**
- **本 PR 没有 feature parse**
- production_db_write_performed=false
- db_write_scope=registry_tables_only

## 4. Target Selection Query

- 选中: 10
- 跳过: 4
- request_budget=10, per_team_budget=5, per_competition_budget=4

跳过明细：

- fixture-mun-stored-001: raw_json_status=stored
- fixture-mun-blocked-001: target_state=blocked
- fixture-champ-facup-001: request_budget exhausted
- fixture-eng-friend-001: request_budget exhausted

## 5. 球队全年赛程

- Man United: 6 场
- England: 4 场
- Kashima Antlers: 2 场
- Leeds United: 2 场

## 6. Remaining Gaps

- 只有少量 metadata seed，不覆盖所有联赛
- 还没有 live fetch
- 还没有 raw JSON 采集和存储
- 还没有 scheduler
- 还没有 parser/feature layer
- 还没有 production rollout
- 不能连接到 production DB

## 7. Recommended Next Phase

推荐下一阶段：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-REVIEW

审查通过后，进入：

### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-NO-FEATURE-PARSE-PREFLIGHT

当前阶段仍不允许 live fetch。
