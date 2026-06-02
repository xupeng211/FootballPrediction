<!-- markdownlint-disable MD013 MD024 -->

# FotMob Raw JSON 长期采集系统设计

- lifecycle: permanent / governance
- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTION-DESIGN
- version: 1.0.0
- no network fetch / no DB write / no migration / no scheduler enable / no feature parse
- raw_write_ready remains false

## 1. 目标

打造一个长期稳定采集 FotMob 每场比赛详情原始 JSON 的系统。

核心原则：

- 原始 JSON 写入 PostgreSQL jsonb raw table
- 后续需要哪些数据因子，再从 raw_json 解析
- 采集层和解析层解耦
- **Raw Layer 优先于 Feature Layer**

## 2. 当前已完成能力

基于 ADG60 32 个样本的 proof：

| 能力 | 状态 |
|------|------|
| FotMob detail page HTTP 200 可达 | 32/32 |
| raw payload 本地落盘 (gitignored) | 32/32 |
| `__NEXT_DATA__` 提取 | 32/32 |
| JSON parse 成功 | 32/32 |
| pageProps 定位 (`props.pageProps`) | 32/32 |
| raw JSON 写入 PostgreSQL jsonb | 32/32 |
| table: `fotmob_raw_match_payloads` | 32 rows |
| distinct match_id | 32 |
| json_present | 32 |
| 幂等性 (0 inserted on re-run) | pass |
| feature parsing | 0 performed |
| downstream writes | 0 performed |
| raw_write_ready | false |

## 3. 长期采集分层架构

```
  Target Registry Layer    — 管理要采集哪些比赛
        |
  Raw Fetch Layer          — 控制 FotMob detail 请求
        |
  Raw File Storage Layer   — 本地 gitignored payload 备份
        |
  Raw JSON DB Layer        — PostgreSQL jsonb 持久化
        |
  Audit / Manifest Layer   — 可审计的 manifests
        |
  ------ 以下为未来阶段 ------
        |
  Parser Layer             — 从 raw_json 解析字段
        |
  Feature Layer            — xG/阵容/球员/shotmap/momentum
```

### 3.1 Target Registry Layer

管理要采集哪些比赛。

未来表 `fotmob_match_targets` (本阶段不创建 migration)：

建议字段：

- `source`, `competition`, `season`, `match_id`, `source_url`
- `fixture_date`, `home_team`, `away_team`
- `match_status` (scheduled / live / finished / postponed / cancelled)
- `priority` (1-5)
- `discovery_source` (manual / league_schedule / search / related_matches)
- `target_state` (discovered / pending_raw_fetch / raw_fetched / raw_json_stored / blocked / failed / retired)
- `last_attempt_at`, `last_success_at`, `attempt_count`
- `last_error_code`, `last_error_message`
- `created_at`, `updated_at`

target_state 状态机:

```

  discovered → pending_raw_fetch → raw_fetched → raw_json_stored
                  ↓                    ↓
               blocked              failed → (retry) → pending_raw_fetch
```

本阶段只设计，后续 PR 创建匹配 target registry migration。

### 3.2 Raw Fetch Layer

控制 FotMob detail 请求：

- sequential fetch only (no parallel)
- 20-60 seconds delay between requests
- timeout <= 20s per request
- stop-on-403, stop-on-429
- stop-on-captcha, stop-on-anti-bot
- stop-on-unexpected-redirect
- stop-on-missing `__NEXT_DATA__`
- stop-on-identity-mismatch
- no browser automation (Playwright/Chromium)
- no proxy rotation
- no stealth
- no captcha bypass
- no anti-bot bypass
- no retry storm
- request budget per run and per day
- dry-run mode first

### 3.3 Raw File Storage Layer

本地原始 payload 备份：

- path: `data/raw/fotmob/match_detail/{match_id}.payload.html`
- gitignored (confirmed)
- sha256 checksum recorded in manifest
- deterministic path, no random filename
- retention policy: keep all historical snapshots by default
- future: configurable retention (e.g., keep latest N snapshots per match)
- raw files are backup only — primary source is DB jsonb

### 3.4 Raw JSON DB Layer

将 raw JSON 写入 PostgreSQL：

- table: `fotmob_raw_match_payloads` (already migrated via V26.5)
- on conflict (source, match_id, raw_payload_sha256) → update `ingested_at`
- immutabile snapshots (historical versions preserved)
- `is_active_snapshot` flag for latest version
- `next_data_json` jsonb — complete `__NEXT_DATA__` object
- `page_props_json` jsonb — complete `props.pageProps` object
- idempotent: same sha256 = no re-insert, same row returned

### 3.5 Audit / Manifest Layer

每一次 ingestion run 生成可审计的 manifest：

- `ingestion_run_id` — unique per run
- `request_count_total`, `success_count`, `blocked_count`, `failed_count`
- `db_row_count`, `distinct_match_id_count`, `json_present_count`
- per-target: `match_id`, `sha256`, `inserted_or_existing`
- manifest stored under `docs/_manifests/`
- manifest includes metadata only — no full JSON body

### 3.6 Parser Layer (未来)

从 `fotmob_raw_match_payloads.next_data_json` 和 `page_props_json` 中解析结构化字段。

**不属于当前阶段。** 必须等 Raw Layer 采集稳定后再进入。

### 3.7 Feature Layer (未来)

xG、阵容、球员、shotmap、momentum、match_features_training、predictions。

**不属于当前阶段。**

## 4. 幂等策略

- unique key: `(source, match_id, raw_payload_sha256)`
- 同一个 match_id 可以有多个 snapshot (不同 sha256)
- 默认保留所有历史 snapshot
- `is_active_snapshot` 标记当前活跃版本
- 不删除旧 JSON
- 不覆盖旧 JSON
- 同一个 payload sha256 的重复写入返回 existing row (0 inserted)

## 5. 失败处理策略

| 失败类型 | 策略 |
|----------|------|
| HTTP 403 | stop run, mark target blocked, block league for this run |
| HTTP 429 | stop run, cooldown league for 20 min, do not retry in this run |
| captcha / anti-bot detected | stop run, mark target blocked, escalate |
| missing `__NEXT_DATA__` | mark failed, skip target, continue to next |
| missing pageProps | mark failed, skip target, continue to next |
| JSON parse failure | mark failed, skip target, continue to next |
| identity mismatch | mark failed, skip target, continue to next |
| DB unavailable | stop run, do not retry in this run |
| raw file write failure | mark failed, skip target (DB is primary) |
| checksum mismatch | mark failed, do not insert, continue to next |

all failures recorded in manifest with `stop_reason` and `error` fields.

## 6. 请求频率策略

- one request per match detail page
- sequential only (no parallel fetch)
- 20-60 seconds delay (cautious mode)
- exponential backoff only after explicit review/authorization
- per-run max request budget (configurable, default 50)
- per-day max request budget (configurable, default 200)
- per-competition max request budget (configurable, default 100)
- dry-run first for any new competition/season
- maintain request log for auditing

## 7. 数据保留策略

- raw HTML/payload files: local disk, gitignored, backup only
- raw JSON jsonb: PostgreSQL, long-term, primary source
- manifest/report: committed to git under `docs/_manifests/` and `docs/_reports/`
- raw body: never committed to git
- 未来: migrate raw files to object storage (S3/MinIO)
- 本地容量监控: alert when `data/raw/` exceeds threshold
- 历史版本: all snapshots retained unless explicit cleanup authorized

## 8. 监控指标

监控但不实现 (future Prometheus metrics):

- `fotmob_targets_discovered`
- `fotmob_targets_pending`
- `fotmob_fetch_success_count`
- `fotmob_fetch_blocked_count`
- `fotmob_fetch_failed_count`
- `fotmob_raw_json_inserted_count`
- `fotmob_raw_json_existing_count`
- `fotmob_json_parse_error_count`
- `fotmob_schema_shift_count`
- `fotmob_last_success_at`
- `fotmob_daily_request_count`

## 9. Scheduler 设计

未来长期调度 (本阶段不启用):

- daily discovery job — find new matches from source data
- pending target fetch job — fetch raw payload for pending targets
- raw json db storage job — ingest fetched payloads into jsonb
- audit report job — generate daily/weekly collection report

调度约束:

- 默认低频 (daily or less frequent)
- 默认单线程
- 每日请求预算硬限制
- stop-on-block (403/429/captcha)
- 不绕过反爬
- 不轮换代理
- 不启用 browser automation

## 10. 安全边界

本阶段明确不做：

- no FotMob network fetch
- no DB write
- no migration creation
- no scheduler enable
- no parser execution
- no feature extraction
- no raw_match_data insert
- no l3_features write
- no match_features_training write
- no predictions write
- no raw_write_ready marking
- no browser automation
- no production collector modification

## 11. 下一阶段路线图

建议按以下顺序推进：

| PR | 名称 | 说明 |
|----|------|------|
| A | FOTMOB-MATCH-TARGET-REGISTRY-DESIGN-AND-MIGRATION | 创建 `fotmob_match_targets` 表 |
| B | FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN | collector dry-run (no DB, no fetch) |
| C | FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-NO-FEATURE-PARSE | 单日采集 50 targets max |
| D | FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REVIEW | review collector results |
| E | FOTMOB-RAW-JSON-PARSER-DISCOVERY-NO-DB-WRITE | parser structure discovery (no write) |

Parser Discovery 放在 Raw Layer 长期采集稳定之后。
Feature Layer 在 Parser Discovery 稳定之后。
