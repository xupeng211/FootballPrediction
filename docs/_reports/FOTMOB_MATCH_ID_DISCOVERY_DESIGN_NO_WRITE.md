<!-- markdownlint-disable MD013 -->

# FotMob Match ID Discovery Design No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DESIGN-NO-WRITE
- run_id: fotmob_match_id_discovery_design_no_write_v1
- purpose: 设计真实 FotMob match ID 发现机制，不执行网络请求

---

## Background

本阶段是 #1432 / #1433 的直接后续。

- #1432: 首次 live fetch probe，HTTP 404，unexpected_html，json_parse_ok=0
- #1433: route/source identity review，确认所有 source_match_id 和 source_entity_id 均为 fixture-like

当前 blocker：**没有真实 FotMob match ID，无法拼出真实 route，无法进入 raw JSON dev write。**

本设计定义了 6 种 discovery source、9 个 validation state、state transition rules 和 candidate schema。

---

## Previous Blocker

从 #1433 manifest 继承：

- route_review_status: blocked
- reliable_route_candidate_found: false
- source_identity_quality: fixture_like
- source_match_id_realism: all_fixture_like
- match_id_discovery_required: true

---

## Design Result

### Discovery Source Matrix

| # | Source | Input | Confidence | Implemented |
|---|--------|-------|-----------|-------------|
| 1 | Team Calendar Discovery | team_id, season, date_range | high | false |
| 2 | Competition Fixtures Discovery | competition_id, season | high | false |
| 3 | Date Fixtures Discovery | calendar_date | medium | false |
| 4 | Known Match Page Parsing | known URL fragment | very_high | false |
| 5 | Historical Payload Backfill | existing manifests/logs | very_high | false |
| 6 | Manual Known-good Seed | manually verified ID | maximum | false |

### Source Identity Validation States

9 个状态覆盖从 unknown 到 json_validated 的全生命周期：

- `unknown` → `fixture_like` → `candidate` → `route_candidate` → `route_validated` → `json_validated`
- 异常路径：→ `blocked` (403/429/captcha) 或 → `invalid` (404/unexpected)
- 重新发现：`stale` → `candidate`

**所有状态均不允许 raw write。** 只有 json_validated + 显式授权后才能进入 controlled raw JSON dev write。

### Forward State Transition Rules

7 条规则定义所有允许的转换。

---

## No-Write Safety Review

| Guard | Status |
|-------|--------|
| network_fetch_performed | false |
| db_write_performed | false |
| raw_json_write_performed | false |
| raw_response_body_saved | false |
| scheduler_enabled | false |
| feature_parse_performed | false |
| raw_write_ready_marked | false |
| browser_automation_performed | false |
| captcha_bypass_performed | false |
| proxy_rotation_performed | false |

---

## Readiness Gates

- route_validation_required: true
- json_validation_required: true
- raw_write_blocked_until_json_validated: true
- explicit_authorization_required_for_raw_write: true

---

## Recommended Next Phase

FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DB-DRY-RUN-NO-WRITE

- 使用本设计定义的 candidate schema
- 从 DB registry targets 生成 candidate queue
- 不访问 FotMob / 不写 DB / 不写 raw JSON
