<!-- markdownlint-disable MD013 -->

# FotMob Match ID Discovery Design No Write

- lifecycle: current-state
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DESIGN-NO-WRITE
- run_id: fotmob_match_id_discovery_design_no_write_v1
- purpose: 设计真实 FotMob match ID 发现机制，解决 fixture-like source_match_id 无法 raw write 的问题
- 本阶段不访问 FotMob
- 本阶段不 live fetch
- 本阶段不写 DB
- 本阶段不写 raw JSON

---

## 1. 背景

### 1.1 当前状态

- PR #1432 执行了首次受控 FotMob live fetch probe。
  - 结果：HTTP 404, content-type: text/html, json_parse_ok=0, stop_reason=unexpected_html。
- PR #1433 执行了 route/source identity review。
  - 结论：**all source_match_ids are fixture-like synthetics**。
  - 10/10 source_entity_ids 使用 `fixture-*` 前缀。
  - 14/14 source_match_ids 使用 `fixture-*` 前缀。
  - route_review_status=blocked, reliable_route_candidate_found=false。

### 1.2 核心问题

系统目前可以从 dev/local registry DB 生成 "应该抓哪些比赛" 的 target queue（V26.6 表结构已验证）。
但是 target queue 中的 `source_match_id` 全部是 `fixture-eng-friend-001`、`fixture-mun-epl-001` 这样的占位符，
不包含真实 FotMob match id。

FotMob 的 match detail 页面使用以下路由模式：

- `/matches/{slug}/{hash}#{match_id}` — 完整 SEO URL
- `/matches/{hash}/{match_id}` — 短路由形式
- 其中 `match_id` 是 **数字 ID**（如 `4830473`），`hash` 是 **alphanumeric 短哈希**（如 `2o4ahb`）

当前 `fixture-eng-friend-001` 不符合任何已知 FotMob match ID 格式，直接拼接 URL 必然返回 404。

### 1.3 设计目标

本阶段设计一套可执行、可验证、可审计的 Match ID Discovery 机制，为未来真实 live fetch 做准备。

---

## 2. Discovery 来源设计

本设计定义 6 种 discovery source。**本阶段只做设计，不执行。**

### 2.1 Team Calendar Discovery

- **输入**：FotMob team page（通过已知 team ID 或从 team fixtures 页面获取）
- **输出**：该队在某赛季内所有比赛的 match ID 列表
- **适用**：曼联、利兹联、鹿岛鹿角等已注册球队的全赛程发现

已知 FotMob team page 路由模式（来自历史 ADG 数据）：

- `/teams?id={team_id}`
- `/teams/{team_name}/{team_id}`

当前 fixture 使用 `fixture-*` source_team_id，需要替换为真实数字 team_id。

### 2.2 Competition Fixtures Discovery

- **输入**：FotMob league/competition page（通过已知 competition ID + season）
- **输出**：该赛事在该赛季内所有比赛的 match ID 列表
- **适用**：英超（league_id=47）、足总杯、欧联、J1 League 等已注册赛事

已知 FotMob league page 路由模式（来自历史 ADG 数据如 ADG52/ADG53）：

- `/leagues?id={league_id}&season={season}`
- `/leagues/{league_name}/{league_id}`

### 2.3 Date Fixtures Discovery

- **输入**：Calendar date (YYYY-MM-DD)
- **输出**：当日所有比赛的 match ID 列表
- **适用**：补全跨赛事比赛日，或当 team/competition discovery 不完整时作为补充

已知 FotMob date fixtures 路由：

- `/fixtures?date={YYYY-MM-DD}`

### 2.4 Known Match Page Parsing

- **输入**：已知人工核验过的 FotMob match page URL 片段
- **输出**：match ID、hash ID、team mapping、date 验证
- **注意**：本阶段只设计解析 schema，不执行抓取

历史 ADG 数据中已有的已知 match page pattern：

- `https://www.fotmob.com/matches/{team1}-vs-{team2}/{hash}#{match_id}`
- 例如：`/matches/angers-vs-paris-saint-germain/2o4ahb#4830473`

### 2.5 Historical Raw Payload / Manifest Backfill

- **输入**：已有 raw JSON payload manifest、旧 collector log、过往 ADG 成功样本
- **输出**：known-good source identities
- **目的**：逐步把 `fixture-*` 占位符替换为真实 FotMob ID

仓库中已有：

- ADG46 SSR probe（Ligue 1, 2025/2026）
- ADG48 correct-orientation probe
- ADG52/ADG53 league schedule SSR
- 这些历史数据包含真实 match ID、hash ID、route_hash_pair

### 2.6 Manual Known-good Seed

- **输入**：人工审核过的 known-good FotMob match ID
- **输出**：route_validated / json_validated source identity
- **用途**：最小 bootstrap，为 discovery 流程提供一个已验证的种子

手动录入示例字段：

```json
{
  "target_id": null,
  "source": "fotmob",
  "source_match_id": "4830473",
  "source_url": "https://www.fotmob.com/matches/2o4ahb/4830473",
  "home_team_name": "Angers",
  "away_team_name": "Paris Saint-Germain",
  "competition_name": "Ligue 1",
  "match_date": "2026-04-01",
  "validation_state": "json_validated",
  "discovery_source": "manual_known_good_seed",
  "confidence_score": 1.0
}
```

---

## 3. Source Identity Validation State Machine

### 3.1 状态定义

| State | 含义 | 允许 live raw write? |
|-------|------|---------------------|
| `unknown` | 尚未验证 | ❌ |
| `fixture_like` | 当前 ID 是 fixture/placeholder/synthetic | ❌ |
| `candidate` | 从 discovery source 发现，尚未 probe | ❌ |
| `route_candidate` | 可以拼出 route，尚未确认响应形态 | ❌ |
| `route_validated` | no-write probe 返回非 HTML、非 404、非 blocked | ❌ |
| `json_validated` | no-write probe json_parse_ok=true, top-level keys 合理 | ❌ (仍需授权) |
| `blocked` | 403/429/captcha/bot challenge/policy stop | ❌ |
| `invalid` | 404/unexpected_html/impossible mapping | ❌ |
| `stale` | 旧 ID 可能过期，需重新 discovery | ❌ |

### 3.2 状态转换规则

```
fixture_like  ──[discovery]──→  candidate
candidate     ──[route built]─→  route_candidate
route_candidate ──[200 probe]─→ route_validated
route_validated  ──[json ok]──→ json_validated
json_validated   ──[authorize]─→ (future raw JSON dev write)

any           ──[403/429/captcha]──→ blocked
any           ──[404/unexpected]───→ invalid
stale         ──[re-discovery]─────→ candidate
```

### 3.3 禁止的转换

以下转换在此设计中是禁止的：

- `fixture_like` → `json_validated`（跳过 discovery）
- `candidate` → `json_validated`（跳过 route probe）
- 任何状态 → raw write（除非 json_validated 且经显式授权）

---

## 4. Candidate Artifact Schema

### 4.1 单条 candidate 记录

```json
{
  "candidate_id": "uuid",
  "target_id": 63,
  "source": "fotmob",
  "discovery_source": "team_calendar",
  "team_id": 1,
  "team_name": "Manchester United",
  "competition_id": 5,
  "competition_name": "Premier League",
  "match_date": "2026-08-15T14:00:00Z",
  "home_team_name": "Manchester United",
  "away_team_name": "Liverpool",
  "candidate_match_id": null,
  "candidate_hash_id": null,
  "candidate_url_pattern_label": "team_calendar_discovery",
  "candidate_url_pattern_redacted": "https://www.fotmob.com/teams?id=<team_id>",
  "confidence_score": 0.0,
  "validation_state": "fixture_like",
  "rejection_reason": null,
  "created_at": "2026-06-04T00:00:00Z",
  "reviewed_by": null
}
```

### 4.2 Candidate Queue 输出

Discovery 流程输出一个 candidate queue（JSON array），每条记录符合上述 schema。
只有当 `validation_state` 达到 `route_candidate` 或更高时，才能进入后续 live route validation no-write。

---

## 5. No-Write Safety Gates

本设计阶段明确以下 gates 全部为 hard block：

| Gate | Value |
|------|-------|
| network_fetch_performed | false |
| db_write_performed | false |
| production_db_write_performed | false |
| raw_json_write_performed | false |
| fotmob_raw_match_payloads_write_performed | false |
| raw_match_data_write_performed | false |
| raw_response_body_saved | false |
| feature_parse_performed | false |
| scheduler_enabled | false |
| raw_write_ready_marked | false |
| browser_automation_performed | false |
| captcha_bypass_performed | false |
| proxy_rotation_performed | false |

---

## 6. Future Readiness Gates

以下条件全部满足后，才能进入 `FOTMOB-RAG-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ROUTE-VALIDATION-NO-WRITE`：

1. match ID discovery DB dry-run 完成（有 candidate queue）
2. 至少 1 条 candidate 的 validation_state >= `route_candidate`
3. route/source identity 已被 review 确认
4. 用户显式授权 live route validation

以下条件全部满足后，才能进入 `FOTMOB-RAG-JSON-LONG-RUN-COLLECTOR-CONTROLLED-RAW-JSON-DEV-WRITE`：

1. route validation no-write 完成
2. 至少 1 条 candidate 的 validation_state >= `json_validated`
3. raw_write_ready_marked = true（由授权阶段设置）
4. 用户显式授权 raw JSON dev write

---

## 7. Remaining Gaps

- 所有 source_match_id 仍然是 fixture-like
- 没有真实 FotMob team ID / competition ID / match ID
- 没有 discovery agent 实现
- 没有 candidate queue DB 表（如需要）
- 没有 route validation 确认
- 尚未授权 raw JSON dev write

---

## 8. Recommended Next Phase

FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DB-DRY-RUN-NO-WRITE

- 使用本设计定义的 candidate schema
- 从 DB registry targets + seed plan 生成 candidate queue
- 不访问 FotMob / 不写 DB / 不写 raw JSON
- 验证 target → candidate 映射流程的正确性
