<!-- markdownlint-disable MD013 -->

# FotMob Live Fetch Route Review No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE
- run_id: fotmob_live_fetch_route_review_no_write_v1
- purpose: 审查 FotMob live fetch route 和 source identity，诊断 #1432 失败原因
- explicit_allow_flag_present: true
- DB target source: db_backed_registry (read-only)
- 本阶段没有保存 raw response body
- 本阶段没有写 raw JSON
- 本阶段没有写 DB
- 本阶段没有 parser
- 本阶段没有 scheduler
- 本阶段不是大规模采集

## Background

- PR #1432 执行了首次受控 FotMob live fetch probe
- 结果：attempted=1, completed=1, stopped_early=true
- stop_reason=unexpected_html
- status_code=404
- content_type=text/html; charset=utf-8
- json_parse_ok_count=0
- 目标 URL: `https://www.fotmob.com/matches/fixture-eng-friend-001` 返回 HTML 404
- 本阶段审查失败原因，不做 raw write

## Why #1432 Failed

### 直接原因

- `source_match_id = fixture-eng-friend-001` 是 synthetic/fixture-only 占位符
- URL 拼接结果 `https://www.fotmob.com/matches/fixture-eng-friend-001` 指向不存在的页面
- FotMob 使用数字 match ID（如 `4830473`）或 hash_id 对（如 `2o4ahb#4830473`）
- `fixture-eng-friend-001` 不符合任何已知 FotMob match ID 格式

### 根本原因

- Registry seed phase 明确声明所有 source_match_id 是 `synthetic/fixture-only`
- 所有 source_entity_id（team/competition）也是 `fixture-*` 占位符
- target_selection_db_dry_run 虽然正确选择了 targets，但 targets 持有的是 fixture ID
- 在 fixture ID 被替换为真实 FotMob ID 之前，任何 live fetch 都会得到 404

## Source Identity Review

- total_identities: 10
- fixture_like_count: 10
- numeric_count: 0
- quality: fixture_like

### 分析

- 所有 source_identity 的 source_entity_id 均以 `fixture-` 开头
- 例如: `fixture-mun-01` (Manchester United), `fixture-comp-epl` (Premier League)
- FotMob 真实 team ID 和 competition ID 是数字（如 team_id=9825, league_id=47）
- 当前 fixture ID 只能用于 DB schema 验证和 pipeline 演练
- **不能** 用于真实 FotMob live fetch

## Route Candidate Review

- reliable_route_candidate_found: false
- match_id_discovery_required: true
- endpoint_route_realism: invalid_when_fixture_like

### Known FotMob Route Patterns (from historical ADG data)

| pattern | example | status |
|---------|---------|--------|
| match detail page (SSR) | `/matches/{hash}/{match_id}` | ADG46 confirmed 200 with `__NEXT_DATA__` |
| match detail page (hash) | `/matches/{hash}#{match_id}` | redirect pattern |
| match detail API | `/api/matchDetails?matchId={id}` | ADG44 returned 404 |
| league fixtures API | `/api/leagues?id={id}` | ADG44 returned 404 |
| team page | `/teams?id={id}` | not tested |
| date fixtures | `/fixtures?date={date}` | HTML only |

### Current Route Candidates

| candidate | source | confidence | probed | status_code | content_type | json_ok | error |
|-----------|--------|------------|--------|-------------|--------------|---------|-------|
| none (no reliable route candidate) | n/a | n/a | false | none | none | false | none |

## Match ID Discovery Gap

### 缺失的能力

- **Match ID Discovery**：从 FotMob 公开页面发现真实 match ID 的能力
- 当前 pipeline 在设计上假设已有真实 source_match_id
- Registry seed 明确只是 metadata/calendar 验证，不含真实 FotMob ID
- 需要新增 match ID discovery 阶段来填充真实 source_match_id

### 建议的 Discovery 方法（设计，不执行）

1. **Team Calendar Discovery**
   - 从 FotMob team page 获取该队的 fixtures 列表
   - 从 `__NEXT_DATA__` 或 API 中提取真实 match ID
2. **League Fixtures Discovery**
   - 从 FotMob league page 获取 fixtures 列表
   - 提取 match ID 和 route_hash_pair
3. **Date Fixtures Discovery**
   - 从 FotMob date fixtures page 获取当日所有比赛
4. **Source Identity Validation States**
   - unknown → candidate → route_validated → json_validated → blocked → invalid

## Optional Probe Result

| candidate | attempted | status_code | content_type | size | json_ok | error | stop |
|-----------|-----------|-------------|--------------|------|---------|-------|------|
| none (no probe executed) | false | none | none | 0 | false | none | false |

## Stop Policy Result

- route_review_status: blocked
- detailed_reason: blocked_no_reliable_route_candidate
- network_fetch_performed: false
- probes_attempted: 0
- probes_remaining: 3

## Safety Review

- network_fetch_performed: false
- raw_response_body_saved: false
- db_write_performed: false
- raw_json_write_performed: false
- fotmob_raw_match_payloads_write_performed: false
- raw_match_data_write_performed: false
- feature_parse_performed: false
- scheduler_enabled: false
- raw_write_ready_marked: false
- browser_automation_performed: false
- captcha_bypass_performed: false
- proxy_rotation_performed: false
- retry_storm_performed: false

## Remaining Gaps

- 所有 source_match_id 仍然是 fixture-like 占位符
- 没有真实 FotMob match ID
- 没有 match ID discovery 能力
- 没有 route validation confirmation
- 尚未授权 raw JSON dev write
- 尚未启用 scheduler
- 尚未实现 parser/features/training/prediction

## Recommended Next Phase

- FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DESIGN-NO-WRITE
- 若 source_match_id 仍为 fixture-like，推荐 match ID discovery design no-write
- 不得在 fixture ID 状态下直接 raw write
- 若后续获得真实 match ID，仍需先做极小规模 controlled route validation no-write
