<!-- markdownlint-disable MD013 -->

# FotMob Match ID Discovery Source Review No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-SOURCE-REVIEW-NO-WRITE
- run_id: fotmob_match_id_discovery_source_review_v1
- purpose: 审查 #1435 生成的 76 条 discovery candidates，评分并排序 6 种 discovery source
- 本阶段不访问 FotMob / 不联网 / 不写 DB / 不写 raw JSON

## Background

- #1435 从 14 个 registry DB match targets 生成了 76 条 discovery candidates
- 每条 candidate 标注了 discovery_source，但 candidate_match_id 全部为 null
- 本阶段评审哪条 discovery 路径最适合下一步 no-write route candidate validation

## #1435 Candidate Summary

- input_target_count: 14
- discovery_candidate_count: 76
- candidate_state: candidate (all 76)
- route_validated: 0
- json_validated: 0
- raw_write_eligible_count: 0

## Source Review Matrix

| source | count | coverage | confidence | complexity | risk | feasibility | priority | reason |
|--------|-------|----------|------------|------------|------|-------------|----------|--------|
| manual_seed | 6 | 2 | 10 | 10 | 10 | 10 | 1 | 极低风险；仅需人工确认 1-3 个已知 FotMob match ID；适合 bootstrap；不适合大规模 |
| known_match_page | 14 | 4 | 8 | 6 | 7 | 9 | 2 | 若能复用历史 ADG 数据中已知 match page URL，可直接提取 hash/match_id 做 route candidate；适合下一阶段首条 no-write 验证 |
| team_calendar | 14 | 7 | 7 | 5 | 7 | 8 | 3 | 覆盖所有 14 个 target 的主队；对 Manchester United/England 等全赛历最有价值；适合长期主路径 |
| competition_fixtures | 14 | 6 | 6 | 5 | 6 | 7 | 4 | 覆盖所有 14 个 target 的赛事维度；适合联赛/杯赛补全；依赖真实 FotMob competition ID |
| date_fixtures | 14 | 5 | 5 | 7 | 5 | 6 | 5 | 适合比赛日补漏；但候选量较大、噪声较高；HTML page 不是 JSON endpoint；风险中等 |
| historical_backfill | 14 | 3 | 9 | 3 | 9 | 4 | 6 | 若有历史 raw payload/manifest 则极高置信度；当前 repo 有 ADG46/48/52/53 历史数据可回填；但 Ligue 1 范围不匹配当前 target；暂 deferred |

## Source Priority Ranking

- bootstrap: **manual_seed**
- primary: **known_match_page**
- secondary: **team_calendar**
- fallback: **competition_fixtures**
- deferred: date_fixtures, historical_backfill

### Ranking Rationale

1. manual_seed 风险最低，适合 bootstrap 1-3 个 known-good match ID 作为后续验证的黄金标准。
2. known_match_page 可复用历史 ADG 数据中已知的 FotMob match page URL，直接提取 hash/match_id pair，无需猜测 route。
3. team_calendar 覆盖所有 target 的主队维度，是长期自动发现最稳的主路径。
4. competition_fixtures 覆盖赛事维度补全。
5. date_fixtures 作为比赛日补漏，但噪声较高。
6. historical_backfill 置信度极高但当前 repo 历史数据（Ligue 1）与当前 target（PL/FA/EFL/J1）范围不匹配，暂 deferred。

## Recommended Next-Stage Samples

| sample_id | target_id | team | competition | source | reason |
|-----------|-----------|------|-------------|--------|--------|
| sample-01 | 63 | England | International Friendly | manual_seed | bootstrap via manual_seed for England vs International Friendly |
| sample-02 | 64 | Kashima Antlers | J1 League | manual_seed | bootstrap via manual_seed for Kashima Antlers vs J1 League |
| sample-03 | 65 | Kashima Antlers | Emperor's Cup | manual_seed | bootstrap via manual_seed for Kashima Antlers vs Emperor's Cup |

## No-Write Safety Review

- network_fetch_performed: false
- db_read_performed: false
- db_write_performed: false
- raw_json_write_performed: false
- raw_response_body_saved: false
- scheduler_enabled: false
- feature_parse_performed: false
- raw_write_ready_marked: false

## Raw Write Readiness Gate

- raw_write_eligible_count: 0
- route_validated_count: 0
- json_validated_count: 0
- raw_write_blocked_until_json_validated: true

## Remaining Blockers

- 没有真实 FotMob match id
- 没有任何 route 被验证
- 没有任何 JSON payload 被确认
- L2 raw harvesting 仍 blocked

## Recommended Next Phase

- FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-NO-WRITE
- 下一阶段只做 no-write route candidate validation 或 controlled known match page parse
- 不可进入 raw JSON write
