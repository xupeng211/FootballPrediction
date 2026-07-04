# FotMob Local Raw Record Replay Dry-Run Design

- lifecycle: source-of-truth
- scope: DATA-L1E-6 docs-only local raw record replay dry-run design
- parent documents: DATA-L1E-5B, DATA-L1E-5A, DATA-L1E-5, DATA-L1E-4, DATA-L1E-3, DATA-L1E-2, DATA-L1E-1, DATA-L1C
- runtime behavior change: no
- adapter code change: no
- envelope schema change: no
- parser code change: no
- replay implementation: no (DATA-L1E-6 is design-only)

---

## 1. 背景

DATA-L1E-5B（PR #1711, merge commit `26a871a13d81c318d7b2831138fcf6e01211ac0a`）已让 envelope / adapter 支持以下 metadata 字段：

- `payload.fetched_at` — 抓取动作发生时间
- `payload.source_url` — 请求 URL
- `payload.final_url` — redirect 后最终 URL

这些字段加上之前 DATA-L1E-1 已定义的 `payload.captured_at`、`payload.data_version`、`payload.payload_hash`、`payload.storage_path`，现在 envelope 已经具备 replay 所需的完整 metadata 承载能力。

当前已完成背景总览：

| 任务 | 说明 | 状态 |
| --- | --- | --- |
| DATA-L1E-1 | `FotMobParserOutputEnvelope` schema 落地 | merged |
| DATA-L1E-2 | dry-run-only adapter 实现 | merged |
| DATA-L1E-3 | static fixtures 验证 adapter 兼容性（0 safe fields） | merged |
| DATA-L1E-4 | metadata handoff dry-run plan（docs-only） | merged |
| DATA-L1E-5 | fixture-level metadata handoff test | merged |
| DATA-L1E-5A | adapter metadata extension design（docs-only） | merged |
| DATA-L1E-5B | adapter metadata extension implementation | merged |

DATA-L1E-6 是 DATA-L1 系列的下一步设计任务。本任务只设计 local raw record replay dry-run 的流程、contract、safety invariants 和未来实现边界。

**本任务不实现 replay，不接 runtime，不访问 FotMob，不写 DB/raw/data。**

---

## 2. Goal

定义未来如何在 **完全离线、本地、无网络、无 DB 写入、无 runtime integration** 的条件下，把一个 local raw record dry-run replay 成 `FotMobParserOutputEnvelope`。

必须明确：local raw record replay dry-run 的目的不是：

- 不是生产采集
- 不是从 FotMob 拉新数据
- 不是写 `raw_match_data`
- 不是喂 feature engine
- 不是训练模型
- 不是回测
- 不是 DB backfill
- 不是 production integration
- 不是 runtime parser path 接入
- 不是 FotMobStrategy / FotMobRawDetailFetcher / RawMatchDataVersionSelector 集成

它是 **纯离线、纯本地、纯内存的证据链验证**。它的唯一产出是一个 valid envelope object（in-memory）或 test assertion target。

---

## 3. Definition of local replay

### 3.1 正式定义

Local replay means:

- **input** comes from local file / local fixture / local sanitized raw record object;
- **no network access** — 不访问 FotMob、不走 HTTP/HTTPS、不走任何远程服务;
- **no browser** — 不启动 Playwright / Puppeteer / headless browser;
- **no scraper / collector** — 不调用任何采集器;
- **no DB read/write by default** — 不读 `raw_match_data` 表，不写任何 DB 行;
- **no raw/data output write by default** — 不产出 `data/`、`raw/`、`models/`、`logs/` 文件;
- **the output is an in-memory envelope or test assertion target** — `FotMobParserOutputEnvelope` 对象;
- **any optional output file in future must be explicitly authorized and remain outside `data/`/`raw/`/`models/`/`logs/`.**

### 3.2 关键区分

| 概念 | 是否等于 local replay | 说明 |
| --- | --- | --- |
| production runtime | **No** | local replay 不 import `FotMobStrategy`、不 import `FotMobRawDetailFetcher`、不 import `RawMatchDataVersionSelector` |
| live fetch | **No** | local replay 不使用网络——输入完全来自本地文件/对象 |
| DB backfill | **No** | local replay 不写 `raw_match_data` 表 |
| feature generation | **No** | local replay 不调用 feature engine |
| model input approval | **No** | local replay 不声明哪些字段可进入模型——envelope 的 0 safe fields 策略继续 |
| production integration | **No** | local replay 是隔离的离线验证，不接入任何 production path |

### 3.3 为什么需要 local replay

即使不接 production runtime，local replay 也解决了一个关键信任问题：

1. **证据链完整性**：raw record → parser output → adapter → envelope 这条链是否端到端可行？不跑一遍没法确认。
2. **metadata 正确传递**：`source_url` / `final_url` / `fetched_at` / `captured_at` 是否能从 raw record 正确进入 envelope payload？
3. **parser 输入兼容性**：如果 input 是 local sanitized HTML / `__NEXT_DATA__`，`NextDataParser.extractFromHtml` 或 `transformToApiFormat` 能否正常处理？
4. **安全边界不变**：local replay 之后，0 safe fields 策略是否仍然保持？postmatch / unknown timing 字段是否仍然 forbidden？

---

## 4. Proposed replay pipeline

### 4.1 主流程

未来 DATA-L1E-7 或后续任务的 local replay driver 建议遵循以下 pipeline：

```text
local raw record (file or object)
  │
  ├─ 1. validate local raw record metadata
  │     ├─ 确认 match_id / external_id 存在
  │     ├─ 确认 source 为 'fotmob'
  │     ├─ 确认 data_version 有值或明确为 'unknown'
  │     └─ 确认 raw_data 块存在（或 HTML/__NEXT_DATA__ 存在）
  │
  ├─ 2. derive replay input
  │     ├─ Lane A: 如果有 raw HTML → 提取为 __NEXT_DATA__ 字符串
  │     │         如果有 __NEXT_DATA__ JSON → 直接使用
  │     └─ Lane B: 如果只有 transformToApiFormat output → 直接使用
  │
  ├─ 3. parse to NextDataParser-compatible output
  │     ├─ Lane A: 调用 NextDataParser.extractFromHtml(html) → 得到 __NEXT_DATA__
  │     │         调用 NextDataParser.transformToApiFormat(nextData, matchId) → 得到 transform output
  │     └─ Lane B: 跳过此步骤，已有 sanitized transform output fixture
  │
  ├─ 4. transformToApiFormat output (in-memory object)
  │     └─ { matchId, content, general, header, _meta }
  │
  ├─ 5. derive adapter options from raw record metadata
  │     └─ { source, dataVersion, payloadHash, storagePath, sourceUrl, finalUrl, fetchedAt, capturedAt, parsedAt, parserName, parserVersion }
  │
  ├─ 6. adaptTransformToApiFormatOutputToEnvelope(transformOutput, adapterOptions)
  │     └─ 调用现有 adapter（不修改）→ 得到 envelope
  │
  ├─ 7. validateEnvelopeShape(envelope)
  │     └─ envelope shape 必须 valid
  │
  ├─ 8. assert 0 safe fields
  │     ├─ 0 个 ALLOWED_CANDIDATE
  │     ├─ 0 个 CANDIDATE_IF_CUTOFF_VALID
  │     └─ postmatch / unknown timing / raw-only 全部 forbidden
  │
  └─ 9. return envelope in memory
        └─ (或用于 test assertion)
```

### 4.2 两个 Lane

#### Lane A: raw HTML / `__NEXT_DATA__` local replay

- **输入**：sanitized local HTML 文件 或 local raw_data 包含 `__NEXT_DATA__` / `pageProps`
- **解析链**：raw HTML → `NextDataParser.extractFromHtml` → `__NEXT_DATA__` → `NextDataParser.transformToApiFormat` → transform output → adapter → envelope
- **无网络**、**无浏览器**、**无 DB**
- **优势**：端到端证明 raw record → parser → adapter → envelope 链路可行
- **劣势**：需要已有 sanitized HTML / `__NEXT_DATA__` fixture；如果没有，需要先用 sanitized 方式生成一份（不在 DATA-L1E-6/7 scope）
- **证据强度**：最强——证明 parser extraction 和 transformation 两段都通

#### Lane B: transformToApiFormat output replay

- **输入**：已 sanitized 的 `transformToApiFormat` output fixture
- **解析链**：transform output → adapter → envelope（跳过 parser extraction）
- **无网络**、**无浏览器**、**无 DB**
- **优势**：实现最简单，adapter 已有 dry-run 验证基础（DATA-L1E-3 已覆盖）
- **劣势**：不证明 raw parser extraction（`extractFromHtml` + `transformToApiFormat`）环节
- **证据强度**：中等——只验证 adapter 端，parser extraction 端未验证

#### 推荐顺序

DATA-L1E-7 应该 **优先从 Lane B 开始**，因为：

1. Lane B 的 adapter 部分已被 DATA-L1E-3 / DATA-L1E-5 验证过（fixture → adapter → envelope）
2. Lane B 的 metadata handoff 已被 DATA-L1E-5 验证过（raw record → options → envelope）
3. Lane B 实现风险最低——只需要把 raw record 的 metadata 转为 adapter options 并调用 adapter
4. Lane A 需要额外的 sanitized HTML / `__NEXT_DATA__` fixture——可能需要先确认是否存在可用的 sanitized local raw record

如果用户已有 sanited raw HTML / `__NEXT_DATA__` fixture，Lane A 也可以同时做。但默认建议 Lane B 先行。

**Do not start automatically. Lane selection must be confirmed by user before DATA-L1E-7.**

---

## 5. Input contract

### 5.1 未来 local raw record 的最小输入结构

以下结构是设计建议，不在 DATA-L1E-6 中实现：

```javascript
{
  // === 比赛标识 ===
  "match_id": "fixture-local-replay-001",
  "external_id": "fixture-local-replay-001",
  "source": "fotmob",

  // === 版本与 hash ===
  "data_version": "fotmob_html_hyd_v1",
  "payload_hash": "sha256:a1b2c3d4e5f6...",
  "data_hash": "sha256:a1b2c3d4e5f6...",

  // === 存储路径 ===
  "storage_path": null,

  // === URL metadata ===
  "source_url": "https://example.invalid/fotmob/match/fixture-local-replay-001",
  "final_url": "https://example.invalid/fotmob/match/fixture-local-replay-001#final",

  // === 时间 metadata ===
  "fetched_at": "2026-07-04T01:00:00.000Z",
  "captured_at": "2026-07-04T01:00:05.000Z",

  // === raw data 块 ===
  "raw_data": {
    "_meta": {
      "request_url": "https://example.invalid/fotmob/match/fixture-local-replay-001",
      "final_url": "https://example.invalid/fotmob/match/fixture-local-replay-001#final",
      "fetched_at": "2026-07-04T01:00:00.000Z",
      "data_version": "fotmob_html_hyd_v1"
    },
    "sanitized_payload_note": "static representative local replay fixture"
  }
}
```

### 5.2 字段语义规则

以下规则不可违反，且已在 DATA-L1E-5B 的 adapter 中实现：

| 字段 | 语义 | 规则 |
| --- | --- | --- |
| `source_url` / `final_url` | 请求 URL / redirect 后 URL | metadata，不是模型特征。缺失时保持 `null`。不伪造。 |
| `fetched_at` | 抓取动作发生时间 | metadata，不是模型特征。缺失时保持 `null`。不伪造。 |
| `captured_at` | 数据快照捕获/持久化时间 | metadata，不是模型特征。缺失时保持 `null`。不伪造。 |
| `payload_hash` / `data_hash` | payload 完整性 hash | 不能从 transform output 随便伪造。缺失时保持 `null`。 |
| `matchTimeUTC` / `utcTime` | 比赛开球时间（来自 `general.matchTimeUTC` / `header.status.utcTime`） | 这是比赛时间，**不是** `fetched_at` / `captured_at`。不能混淆。 |
| `_meta.extractedAt` | NextDataParser 执行时间 | parser 执行时间，**不是** `fetched_at` / `captured_at`。只用 audit_only。 |
| `parsed_at` | adapter/parser 处理时间 | parser 处理时间，**不是** `fetched_at`。 |

### 5.3 时间字段严格区分

```text
fetched_at     ≠ _meta.extractedAt   （抓取 ≠ 解析）
fetched_at     ≠ matchTimeUTC        （抓取 ≠ 开球）
fetched_at     ≠ utcTime             （抓取 ≠ 开球）
fetched_at     ≠ parsed_at           （抓取 ≠ adapter 处理）
captured_at    ≠ _meta.extractedAt   （捕获 ≠ 解析）
captured_at    ≠ matchTimeUTC        （捕获 ≠ 开球）
captured_at    ≠ utcTime             （捕获 ≠ 开球）
captured_at    ≠ parsed_at           （捕获 ≠ adapter 处理）
parsed_at      ≠ extractedAt         （adapter 处理 ≠ NextDataParser 处理——语义不同但都是 parser time）
```

---

## 6. Adapter options handoff

### 6.1 设计

未来 local replay driver 应把 raw record metadata 转换为 adapter options。以下是设计建议（参考 DATA-L1E-4 §5 和 DATA-L1E-5B §3）：

```javascript
const adapterOptions = {
  source: rawRecord.source ?? 'fotmob',

  dataVersion:
    rawRecord.data_version
    ?? rawRecord.dataVersion
    ?? rawRecord.raw_data?._meta?.data_version
    ?? 'unknown',

  payloadHash:
    rawRecord.payload_hash
    ?? rawRecord.data_hash
    ?? rawRecord.raw_data_hash
    ?? rawRecord.stable_raw_payload_hash
    ?? rawRecord.raw_data?._meta?.data_hash
    ?? null,

  storagePath:
    rawRecord.storage_path
    ?? rawRecord.storagePath
    ?? null,

  sourceUrl:
    rawRecord.source_url
    ?? rawRecord.sourceUrl
    ?? rawRecord.raw_data?._meta?.request_url
    ?? null,

  finalUrl:
    rawRecord.final_url
    ?? rawRecord.finalUrl
    ?? rawRecord.raw_data?._meta?.final_url
    ?? null,

  fetchedAt:
    rawRecord.fetched_at
    ?? rawRecord.fetchedAt
    ?? rawRecord.raw_data?._meta?.fetched_at
    ?? null,

  capturedAt:
    rawRecord.captured_at
    ?? rawRecord.capturedAt
    ?? null,

  parsedAt: null,

  parserName: 'NextDataParser.transformToApiFormat',
  parserVersion: 'legacy-static'
};
```

### 6.2 Fallback chain 设计原则

- 优先使用顶层 raw record 字段（`rawRecord.source_url`）
- 其次使用驼峰变体（`rawRecord.sourceUrl`）
- 再次从 `raw_data._meta` 中提取（`rawRecord.raw_data?._meta?.request_url`）
- 全部缺失时保持 `null`
- **不伪造**：不从 `_meta.extractedAt` 推导 `fetchedAt`
- **不伪造**：不从 `matchTimeUTC` 推导 `fetchedAt` 或 `capturedAt`

### 6.3 重要说明

- 这是设计示例，**不在 DATA-L1E-6 中实现**
- adapter 本身已支持所有 options（DATA-L1E-5B 完成）
- local replay driver 的职责是把 raw record 字段映射为 adapter options
- `parsedAt` 保持 `null`（local replay 是 dry-run，不记录真实的 parser 执行时间，除非 future driver 显式记录）

---

## 7. Output contract

### 7.1 未来 dry-run 输出 envelope 的要求

未来 DATA-L1E-7 实现后，local replay 产出的 envelope 必须满足以下全部条件：

1. `validateEnvelopeShape(envelope).valid === true`
2. `envelope.source === 'fotmob'`
3. `envelope.match_id` 来自 `rawRecord.match_id` 或 `transformOutput.matchId`
4. `envelope.payload.data_version` 正确保留（来自 `rawRecord.data_version`，缺失为 `'unknown'`）
5. `envelope.payload.payload_hash` 正确保留（来自 `rawRecord.data_hash` 或等价字段，缺失为 `null`）
6. `envelope.payload.storage_path` 正确保留或 `null`
7. `envelope.payload.source_url` 正确保留或 `null`
8. `envelope.payload.final_url` 正确保留或 `null`
9. `envelope.payload.fetched_at` 正确保留或 `null`
10. `envelope.payload.captured_at` 正确保留或 `null`
11. `envelope.parser.parser_name` / `parser_version` / `parsed_at` 有清晰语义
12. `envelope.fields` **不产生** 任何 `ALLOWED_CANDIDATE` 字段
13. `envelope.fields` **不产生** 任何 `CANDIDATE_IF_CUTOFF_VALID` 字段
14. `postmatch` / `unknown_timing` / `raw_only` 字段继续 `forbidden`

### 7.2 输出定位

Local replay output is **evidence**, not model-ready data.

- envelope 不替代 raw payload —— 它是 parser 处理后的结构化视图
- envelope 不替代 feature vector —— 0 safe fields 策略继续
- envelope 不替代 model input —— 所有字段 forbidden
- envelope 是 replay 证据 —— 它证明 raw record → envelope 链路可行、metadata 正确传递、安全边界不变

---

## 8. Safety invariants

以下安全规则是 local replay dry-run 的不可违反底线。所有规则继承自 DATA-L1 系列前序任务：

1. **No network.** 不访问任何远程服务。
2. **No browser.** 不启动 Playwright / Puppeteer / headless browser。
3. **No scraper / collector.** 不调用任何采集器。
4. **No DB read/write by default.** 不读 `raw_match_data`，不写任何 DB 行。如果未来需要 DB read（比如读已有 raw record），需要单独授权。
5. **No writes to `data/`/`raw/`/`models/`/`logs/`.** 输出只在内存或 test assertion 中。
6. **No feature engine.** 不 import、不调用 feature engine。
7. **No training.** 不运行模型训练。
8. **No backtest.** 不运行回测。
9. **No production runtime import.** 不 import `FotMobStrategy`、`FotMobRawDetailFetcher`、`RawMatchDataVersionSelector`。
10. **No NextDataParser runtime path integration.** 如果 Lane A 调用 `extractFromHtml` / `transformToApiFormat`，这只是纯函数调用，不意味着接入了 production runtime path。
11. **No FotMobStrategy integration.** 不创建 strategy 实例。
12. **No FotMobRawDetailFetcher integration.** 不创建 fetcher 实例。
13. **No RawMatchDataVersionSelector integration.** 不创建 selector 实例。
14. **No schema migration.** 不执行任何 DB migration。
15. **No `source_url`/`final_url`/`fetched_at` as model features.** 这些是 audit/provenance/replay metadata。
16. **No `_meta.extractedAt` as `fetched_at`/`captured_at`.** `extractedAt` 是 parser 执行时间。
17. **No `matchTimeUTC`/`utcTime` as `fetched_at`/`captured_at`.** 这是比赛开球时间。
18. **No `parsed_at` as `fetched_at`.** `parsed_at` 是 adapter 处理时间。
19. **Missing metadata stays `null`/`unknown`.** 不伪造。
20. **Unknown timing stays `forbidden`.** 0 safe fields 策略不变。

---

## 9. Proposed DATA-L1E-7 implementation scope

### 9.1 任务名

```text
DATA-L1E-7: Local Raw Record Replay Dry-Run Fixture Test
```

### 9.2 建议允许修改

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `tests/fixtures/fotmob/local_raw_record_replay_boundary_a_fixture.json` | 新增 fixture | local raw record fixture（包含完整 metadata） |
| `tests/unit/parsers/fotmob/FotMobLocalRawRecordReplay.fixture.test.js` | 新增测试 | local replay fixture test |
| `docs/data/fotmob_local_raw_record_replay_fixture_test.md` | 新增文档 | replay fixture test 证据文档 |

如必须新增 helper（例如 `buildAdapterOptionsFromRawRecord` 逻辑与已有 metadata handoff test 明显重复），建议限制为 test-only helper：

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `tests/unit/parsers/fotmob/helpers/localRawRecordReplayHelper.js` | 新增 test helper | 仅在 test 中使用，不进 `src/` |

但默认优先 **不要新增 helper 文件**，除非测试中重复逻辑明显。可优先复用现有 metadata handoff test 中已定义的 helper 逻辑。

### 9.3 DATA-L1E-7 明确禁止修改

```text
src/**                                     — 不改任何 src 文件
src/parsers/fotmob/NextDataParser.js       — 不改
src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js  — 不改
src/parsers/fotmob/FotMobParserOutputEnvelope.js               — 不改
src/parsers/fotmob/index.js                — 不改
src/infrastructure/harvesters/strategies/FotMobStrategy.js     — 不改
src/infrastructure/services/FotMobRawDetailFetcher.js          — 不改
src/infrastructure/services/RawMatchDataVersionSelector.js     — 不改
src/feature_engine/**                      — 不改
src/features/**                            — 不改
src/ml/**                                  — 不改
src/pipeline/**                            — 不改
src/training/**                            — 不改
src/backtest/**                            — 不改
scripts/**                                 — 不改
.github/**                                 — 不改
Dockerfile / docker-compose*               — 不改
migrations/**                              — 不改
data/** / raw/** / models/** / logs/**     — 不写
```

如果 DATA-L1E-7 必须触碰 `src/`（例如 adapter 需要新增一个 helper 函数才能支持 local replay），则 **必须先另开设计任务**，不要直接在 DATA-L1E-7 中实现。

---

## 10. Future production integration boundary

### 10.1 当前状态

Local replay dry-run 仍然 **不是** production integration。

即使 DATA-L1E-7 实现了 fixture test（Lane B 或 Lane A），也 **不能说明可以接 production runtime**。

真正接 runtime 至少需要后续独立任务，例如：

- `DATA-L2` — Production Runtime Integration Plan
- `DATA-L1E-8` — Staging-only Runtime Integration Plan

### 10.2 Production integration 之前还需要

在任何人开始接 production runtime 之前，以下前提条件必须满足：

1. **local replay fixture test 通过** — Lane A 或 Lane B 至少有一条链路被 fixture 验证过
2. **raw parser extraction lane 明确** — 如果走 Lane A，确认 `extractFromHtml` / `transformToApiFormat` 调用不会引入副作用
3. **DB read/write policy 明确** — 确认是否允许读 `raw_match_data` 表取 raw record，是否允许写 envelope 回 DB
4. **URL sanitizer policy 明确** — `source_url` / `final_url` 是否需要移除敏感 query params、是否需要截断
5. **fetched_at clock source policy 明确** — `fetched_at` 使用 `Date.now()` 还是 `new Date().toISOString()`，时区是否强制 UTC
6. **staging-only plan 明确** — runtime integration 必须先在 staging 环境验证，不能直接上 production
7. **rollback plan 明确** — 如果 runtime integration 出问题，必须有明确的回滚路径
8. **feature/training/backtest 隔离仍然保持** — envelope 仍然不能直接喂给 feature engine / training / backtest
9. **postmatch leakage checks 仍然通过** — 0 safe fields 策略不变

---

## 11. Deep flatten status

**Deep flatten 仍未处理。它是独立问题。**

当前状态：
- adapter 的 `flattenTransformOutputFields` 只展开顶层和高风险区块（`content.stats`、`content.shotmap`、`content.events`、`content.lineup`）
- 嵌套字段（如 `content.stats.expectedGoals`、`content.playerStats[*].rating`）没有被单独展平
- 这些字段被包裹在 parent raw block（`content`、`general`、`header`）中，标记为 `FORBIDDEN_RAW_ONLY`
- 安全由 parent block 的 forbidden 标签保证，不需要 adapter 单独展开

DATA-L1E-6 **不处理** deep flatten。

Local replay 可以继续依赖现有 parent raw block forbidden 策略保持安全。

如果未来需要 deep flatten（例如将 `content.stats.expectedGoals` 从 `FORBIDDEN_RAW_ONLY` 升级为 `FORBIDDEN_POSTMATCH`），应另开任务：

```text
DATA-L1E-5C: Deep Flatten Coverage Design
或
DATA-L1E-3A: Deep Flatten Coverage Design
```

**Do not start automatically.**

---

## 12. Open questions

以下问题在 DATA-L1E-6 设计阶段提出。部分可以从已有源码/文档回答，部分保持 open。

| # | 问题 | 状态 | 当前答案/备注 |
| --- | --- | --- | --- |
| 1 | Future DATA-L1E-7 应优先做 Lane A 还是 Lane B？ | **open** | 建议默认 Lane B（风险最低）; 如果已有 sanitized raw HTML fixture，Lane A 也可同时做。用户确认后再决定。 |
| 2 | 是否已有足够 sanitized local raw record 可以作为 Lane A fixture？ | **open** | 当前 fixtures 目录中没有包含 raw HTML / `__NEXT_DATA__` 的 fixture。需要确认是否需要新建 sanitized fixture。 |
| 3 | local raw record 是否应包含 HTML、`__NEXT_DATA__` JSON、还是 already-extracted `pageProps`？ | **open** | 取决于 Lane 选择。Lane A 需要 HTML 或 `__NEXT_DATA__` JSON。Lane B 只需要 transform output + metadata sidecar。 |
| 4 | replay helper 是否应只放在 test 文件中，还是允许 test-only helper 文件？ | **open** | 建议默认优先 inline test helper; 如果多个 test 共享同一 handoff 逻辑，才考虑 `tests/unit/parsers/fotmob/helpers/localRawRecordReplayHelper.js` |
| 5 | 是否允许 dry-run 输出临时 envelope JSON，还是只允许内存断言？ | **open** | 建议默认只允许内存断言; 如果需要输出临时 JSON 便于人工检查，应限制输出路径（如 `tests/fixtures/fotmob/replay_output_envelope_sample.json`），且不在 `data/`/`raw/`/`models/`/`logs/` 下 |
| 6 | URL sanitizer policy 是否需要先定义？ | **open** | 当前设计使用 `example.invalid` 域名作为 fixture 占位。真实 URL policy 应在 DATA-L2 或单独任务中定义 |
| 7 | fetched_at clock source 是否需要先定义？ | **answered** | DATA-L1E-5B adapter 不强制 clock source。local replay fixture 中的 `fetched_at` 是 static value。Production clock source 应在 DATA-L2 中定义 |
| 8 | payload_hash/data_hash 优先级是否要固定为统一 helper？ | **answered** | DATA-L1E-4 §5 和 DATA-L1E-5B §3 已定义 fallback chain：`data_hash` > `payload_hash` > `raw_data_hash` > `stable_raw_payload_hash` > `raw_data._meta.data_hash` > `null`。如果多个 test 重复此逻辑，可提取为 test helper |
| 9 | local replay 是否需要覆盖 parser error path？ | **open** | 建议 DATA-L1E-7 至少覆盖：raw record 缺失 match_id、raw_data 为空/null、html 不包含 `__NEXT_DATA__`。完整的 error path coverage 可以留给后续任务 |
| 10 | local replay 是否需要覆盖 missing metadata path？ | **open** | 建议 DATA-L1E-7 覆盖 minimal metadata（只给 match_id + source）→ envelope 的 `data_version` 为 `'unknown'`、其他 metadata 为 `null` |

---

## 13. What changed

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `docs/data/fotmob_local_raw_record_replay_dry_run_design.md` | 新增 | DATA-L1E-6 design document |

---

## 14. What did not change

- 没有改 adapter（`FotMobParserOutputEnvelopeLegacyAdapter.js`）
- 没有改 envelope schema（`FotMobParserOutputEnvelope.js`）
- 没有改 NextDataParser（`NextDataParser.js`）
- 没有改 FotMobStrategy
- 没有改 FotMobRawDetailFetcher
- 没有改 RawMatchDataVersionSelector
- 没有改 `src/parsers/fotmob/index.js`
- 没有改 tests
- 没有改 fixtures
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集（scraper / collector / browser）
- 没有运行 replay
- 没有写 DB / raw / data
- 没有改 feature engine
- 没有改 training / backtest
- 没有改 pipeline
- 没有改 `.github/**` / CI workflows
- 没有改 Docker / compose / migrations
- 没有启动 DATA-L1E-7
- 没有启动 DATA-L2
- 没有启动 CLEANUP-L1A
- 没有启动 L3I
- 没有启动 L4
- 没有处理 deep flatten
- 没有删除 / 移动 / 重命名 legacy 文件

---

## 15. Recommended next task

默认推荐：

```text
DATA-L1E-7: Local Raw Record Replay Dry-Run Fixture Test
```

DATA-L1E-7 应该：

1. 创建 local raw record fixture（包含完整 metadata）
2. 如果走 Lane B：使用已有 transform output fixture + raw record fixture，调用 adapter，验证 envelope
3. 如果走 Lane A：使用 sanitized HTML / `__NEXT_DATA__` fixture，调用 `NextDataParser.extractFromHtml` + `transformToApiFormat` + adapter，验证 envelope
4. 验证所有 metadata 正确传递到 envelope payload
5. 验证 0 safe fields 策略不变
6. 验证 postmatch / unknown timing 字段仍然 forbidden

**Do not start automatically.**

**Recommended next task only after user confirmation.**

Lane 选择（A/B）也需要用户确认后再决定。
