# FotMob Local Raw HTML / `__NEXT_DATA__` Replay Design

- lifecycle: source-of-truth
- scope: DATA-L1E-8 docs-only Lane A local raw HTML / `__NEXT_DATA__` replay design
- parent documents: DATA-L1E-7 (`docs/data/fotmob_local_raw_record_replay_fixture_test.md`), DATA-L1E-6 (`docs/data/fotmob_local_raw_record_replay_dry_run_design.md`)
- runtime behavior change: no
- adapter code change: no
- envelope schema change: no
- parser code change: no
- NextDataParser execution: no
- replay implementation: no (DATA-L1E-8 is design-only)

---

## 1. 背景

DATA-L1E-7 已完成 Lane B fixture test 并合并到 main（PR #1713, merge commit `5c008e11588df057a1a2d0b2a5d82dabbc53bb57`）：

```text
Lane B:
local raw record metadata fixture
  + already-sanitized transformToApiFormat output fixture
  → buildAdapterOptionsFromRawRecord(rawRecord)
  → adaptTransformToApiFormatOutputToEnvelope(transformOutput, options)
  → validateEnvelopeShape(envelope)
  → assert 0 safe fields
```

Lane B 不调用 `NextDataParser`，也不验证 raw HTML / `__NEXT_DATA__` extraction 环节。它证明了 adapter → envelope 链路可行，但没有证明从 raw HTML 或 `__NEXT_DATA__` JSON 出发的完整链路。

DATA-L1E-8 本次 **只设计 Lane A**：

```text
Lane A (design only, NOT implemented):
sanitized local raw HTML / sanitized local __NEXT_DATA__ JSON
  → NextDataParser.extractFromHtml(html) — A1 only
  → NextDataParser.transformToApiFormat(nextData, matchId)
  → adaptTransformToApiFormatOutputToEnvelope(transformOutput, adapterOptions)
  → validateEnvelopeShape(envelope)
  → assert 0 safe fields
```

本任务不实现 Lane A，不新增 fixture，不调用 `NextDataParser`，不接入 runtime，不访问 FotMob，不写 DB/raw/data。

---

## 2. Goal

定义未来如何在 **完全离线、本地、无网络、无浏览器、无 DB 写入、无 runtime integration** 的条件下，用 sanitized local raw HTML 或 sanitized local `__NEXT_DATA__` fixture 验证 Lane A replay 链路。

必须明确：Lane A replay 的目的不是：

- 不是生产采集
- 不是从 FotMob 拉新数据
- 不是保存 raw HTML
- 不是写 `raw_match_data`
- 不是喂 feature engine
- 不是训练模型
- 不是回测
- 不是 DB backfill
- 不是 production integration
- 不是 runtime parser path 接入

它是 **纯离线、纯本地、纯内存的证据链验证**。唯一产出是一个 valid envelope object（in-memory）或 test assertion target。

---

## 3. Definition of Lane A

### 3.1 正式定义

Lane A means:

- **input** comes from sanitized local raw HTML fixture OR sanitized local `__NEXT_DATA__` JSON fixture;
- **no network access** — 不访问 FotMob、不走 HTTP/HTTPS、不走任何远程服务;
- **no browser** — 不启动 Playwright / Puppeteer / headless browser;
- **no scraper / collector** — 不调用任何采集器;
- **no DB read/write by default** — 不读 `raw_match_data` 表，不写任何 DB 行;
- **no raw/data/models/logs output write** — 不产出 `data/`、`raw/`、`models/`、`logs/` 文件;
- **parser execution is local-only and test-only in a future task** — `NextDataParser.extractFromHtml` / `transformToApiFormat` 只在 test 上下文中调用;
- **output is in-memory transformToApiFormat output and envelope assertion target** — 不落地文件;
- **any future output file must be explicitly authorized and stay outside `data/`/`raw/`/`models/`/`logs/`**.

### 3.2 关键区分

| 概念 | 是否等于 Lane A | 说明 |
| --- | --- | --- |
| live fetch | **No** | Lane A 不访问网络，输入完全来自本地 fixture |
| production runtime | **No** | Lane A 不 import `FotMobStrategy`、`FotMobRawDetailFetcher`、`RawMatchDataVersionSelector`、`src/parsers/fotmob/index.js` |
| DB backfill | **No** | Lane A 不写 `raw_match_data` 表 |
| feature generation | **No** | Lane A 不调用 feature engine |
| model input approval | **No** | Lane A 不声明哪些字段可进入模型 — 0 safe fields 策略继续 |
| staging integration | **No** | Lane A 是隔离的离线验证，不接入任何 staging path |
| production integration | **No** | 即使 Lane A 完成，也不等于 production integration |

---

## 4. Proposed Lane A pipeline

### 4.1 主流程

未来 Lane A replay driver（test-only）建议遵循以下 pipeline：

```text
sanitized local raw record fixture (file or object)
  │
  ├─ 1. 验证 raw record 元数据完整
  │     ├─ match_id / external_id 存在
  │     ├─ source 为 'fotmob'
  │     ├─ data_version 有值或明确为 'unknown'
  │     └─ 确认 raw_data 块存在
  │
  ├─ 2. 选择 replay 输入
  │     ├─ Lane A1: 如果 raw_html 存在 → 传入 NextDataParser.extractFromHtml(raw_html)
  │     │          → 得到 { success: true, data: nextData }
  │     │          → 传入 transformToApiFormat(nextData, matchId)
  │     └─ Lane A2: 如果 next_data_json 存在 → 跳过 extractFromHtml
  │                → 直接传入 transformToApiFormat(nextData, matchId)
  │
  ├─ 3. transformToApiFormat output (in-memory object)
  │     └─ { matchId, content, general, header, _meta }
  │
  ├─ 4. buildAdapterOptionsFromRawRecord(rawRecord)
  │     └─ { source, dataVersion, payloadHash, storagePath, sourceUrl, finalUrl, fetchedAt, capturedAt, parsedAt, parserName, parserVersion }
  │
  ├─ 5. adaptTransformToApiFormatOutputToEnvelope(transformOutput, adapterOptions)
  │     └─ 调用现有 adapter（不修改）→ 得到 envelope
  │
  ├─ 6. validateEnvelopeShape(envelope)
  │     └─ valid === true
  │
  ├─ 7. assert 0 safe fields
  │     ├─ 0 个 ALLOWED_CANDIDATE
  │     ├─ 0 个 CANDIDATE_IF_CUTOFF_VALID
  │     └─ postmatch / unknown timing / raw-only 全部 forbidden
  │
  └─ 8. return envelope in memory
        └─（或用于 test assertion）
```

### 4.2 两个 Sub-Lane

#### Lane A1: Sanitized Raw HTML Replay

- **输入**：minimal sanitized HTML 文档，包含 `<script id="__NEXT_DATA__" type="application/json">` 标签，内含 sanitized nextData JSON
- **解析链**：raw HTML → `NextDataParser.extractFromHtml(html)` → `{ success, data }` → `NextDataParser.transformToApiFormat(data, matchId)` → transform output → adapter → envelope
- **证据强度**：最强 — 证明 parser extraction 和 transformation 两段都通
- **fixture hygiene 风险**：更高 — HTML fixture 可能隐含真实页面结构（CSS/JS/ads/trackers），需要更严格的 sanitization

#### Lane A2: Sanitized `__NEXT_DATA__` JSON Replay

- **输入**：已提取的 sanitized `__NEXT_DATA__` JSON 对象（不需要 HTML shell）
- **解析链**：nextData JSON → `NextDataParser.transformToApiFormat(nextData, matchId)` → transform output → adapter → envelope
- **证据强度**：中等 — 只验证 `transformToApiFormat` 端，不验证 `extractFromHtml` 端
- **fixture hygiene 风险**：更低 — 只包含 JSON 结构，不涉及 HTML 页面

### 4.3 推荐顺序

DATA-L1E-9 应该 **优先从 Lane A2 开始**，然后再做 Lane A1，理由：

1. Lane A2 实现风险更低 — 只需要 sanitized `__NEXT_DATA__` JSON fixture + `transformToApiFormat` 调用
2. Lane A2 不需要处理 HTML 正则解析、script tag sanitization 等额外复杂度
3. Lane A2 验证的是 `transformToApiFormat` 是否能处理 `__NEXT_DATA__` 结构 — 这是无论 A1 还是 A2 都需要验证的
4. Lane A1 需要额外确认 minimal HTML shell 是否足够触发 `extractFromHtml` — 这可以后续单独验证
5. Lane A1 的 fixture hygiene 风险更高 — 需要更谨慎的设计

```
Do not start automatically.
Recommended next task only after user confirmation.
```

---

## 5. Future fixture contract

以下文件是 **未来 DATA-L1E-9 / DATA-L1E-10 才创建** 的 fixture。DATA-L1E-8 不创建这些文件。

### 5.1 Lane A2 `__NEXT_DATA__` fixtures（DATA-L1E-9 建议）

```text
tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_raw_record_fixture.json
tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_next_data_fixture.json
```

### 5.2 Lane A1 raw HTML fixtures（DATA-L1E-10 建议，可选）

```text
tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a1_raw_record_fixture.json
tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a1_html_fixture.html
```

### 5.3 Future test file

```text
tests/unit/parsers/fotmob/FotMobLocalNextDataReplay.fixture.test.js
```

DATA-L1E-8 不创建上述任何文件。

---

## 6. Sanitization policy

所有 Lane A fixture（HTML / `__NEXT_DATA__` JSON / raw record）必须遵循以下 sanitization 规则：

1. **不得包含真实 FotMob URL。** 例如 `www.fotmob.com`、`api.fotmob.com` 等。
2. **URL 必须使用 `example.invalid`。** 例如 `https://example.invalid/fotmob/match/{matchId}`。
3. **不得包含 cookie / token / session / auth header。**
4. **不得包含真实用户信息。** 例如 user ID、email、subscription tier。
5. **不得包含真实浏览器指纹。** 例如 user-agent、screen resolution、timezone offset。
6. **不得包含真实响应 header。** 例如 `x-cache`、`cf-ray`、`set-cookie`。
7. **不得包含真实 tracking / analytics / ads / OneTrust / consent payload。** 例如 `gtag`、`ga`、`fbq`、`_et`、`oneTrust`、`consent`、`cmp`。
8. **不得包含完整 live FotMob payload。** 不能 copy-paste 真实 FotMob 页面的完整 HTML 或 `__NEXT_DATA__`。
9. **只保留能触发 `NextDataParser` 最小路径的代表性字段。** 例如 `pageProps.content.stats`、`pageProps.general.matchTimeUTC` 等。
10. **所有球队、球员、联赛、match id 都使用 fixture 值。** 例如 `"Home Fixture"`、`"Away Fixture"`、`"fixture-local-replay-a2-001"`。
11. **时间字段必须可控，并且不混淆：**
    - `fetched_at` — 抓取动作发生时间（metadata，不是比赛时间）
    - `captured_at` — 数据被捕获/存储的时间（metadata，不是比赛时间）
    - `_meta.extractedAt` — parser 执行时间（parser metadata，不是采集时间）
    - `general.matchTimeUTC` — 比赛 UTC 开球时间（比赛时间）
    - `header.status.utcTime` — FotMob 页面 header 中的比赛 UTC 时间（比赛时间）
    - 这 5 个时间字段必须使用不同的值，互不混淆
12. **如果 raw HTML fixture 需要 script tag，只保留最小 `__NEXT_DATA__` 脚本。** 不放真实页面的 `_next/static/chunks/`、`_buildManifest.js` 等构建产物。

核心原则：

```text
Future fixture must be sanitized by construction, not by "copy live payload then hope no secrets".
```

即 fixture 必须从零构造，不能从真实 FotMob 页面 copy-paste 然后尝试"清洗"。构造性 sanitized 是唯一可信的方式。

---

## 7. Input contract

### 7.1 未来 Lane A2 raw record 最小结构（建议）

基于 DATA-L1E-7 Lane B raw record 结构扩展，在 `raw_data` 块中增加 `__NEXT_DATA__` 相关字段：

```javascript
{
  "match_id": "fixture-local-replay-a2-001",
  "external_id": "fixture-local-replay-a2-001",
  "source": "fotmob",
  "data_version": "fotmob_nextdata_local_fixture_v1",
  "payload_hash": null,
  "data_hash": "sha256:fixture-local-replay-a2-data-hash-001",
  "storage_path": null,
  "source_url": "https://example.invalid/fotmob/match/fixture-local-replay-a2-001",
  "final_url": "https://example.invalid/fotmob/match/fixture-local-replay-a2-001#final",
  "fetched_at": "2026-07-04T01:00:00.000Z",
  "captured_at": "2026-07-04T01:00:05.000Z",
  "raw_data": {
    "_meta": {
      "request_url": "https://example.invalid/fotmob/match/fixture-local-replay-a2-001",
      "final_url": "https://example.invalid/fotmob/match/fixture-local-replay-a2-001#final",
      "fetched_at": "2026-07-04T01:00:00.000Z",
      "data_version": "fotmob_nextdata_local_fixture_v1",
      "data_hash": "sha256:fixture-local-replay-a2-data-hash-001"
    },
    "replay_lane": "A2",
    "contains_sanitized_next_data": true,
    "contains_sanitized_html": false,
    "contains_live_fotmob_payload": false
  }
}
```

### 7.2 重要说明

- `source_url` / `final_url` / `fetched_at` / `captured_at` 都是 **metadata**，不是模型特征。它们用于审计追踪，不进入 `envelope.fields` 的分类逻辑。
- 缺失时保持 `null` / `'unknown'`，不伪造。
- `payload_hash` 不能从 transform output 随便伪造 — Lane A2 fixture 中的 `payload_hash` 应该留 `null`（因为 raw record 不是真实的 payload digest），或者如果有 `data_hash` 就通过 fallback 传递。
- `general.matchTimeUTC` / `header.status.utcTime` 是比赛时间，不是 `fetched_at` / `captured_at`。Fixture 中应使用不同值来验证不混淆。
- `_meta.extractedAt` 是 parser 执行时间，不是 `fetched_at` / `captured_at`。不会在 raw record 中预填 — 由 `transformToApiFormat` 在调用时生成。

---

## 8. Minimal `__NEXT_DATA__` contract

### 8.1 基于 `NextDataParser.js` 只读审计的结果

通过只读审计 `src/parsers/fotmob/NextDataParser.js`（commit `5c008e1`），确认以下事实：

#### `transformToApiFormat(nextData, matchId)` 需要的结构

```javascript
// 源码行 118–146
function transformToApiFormat(nextData, matchId) {
    // 第 119 行：必须存在 nextData.props.pageProps
    if (!nextData || !nextData.props || !nextData.props.pageProps) {
        return null;
    }

    const pageProps = nextData.props.pageProps;

    // 第 126 行：必须存在 pageProps.content
    if (!pageProps.content) {
        return null;
    }

    // 第 130–146 行：返回结构
    const apiFormat = {
        matchId: matchId,
        content: pageProps.content || {},
        general: pageProps.general || {},
        header: pageProps.header || {},
        _meta: {
            source: 'web_infiltration',
            extractedAt: new Date().toISOString(),
            hasStats: !!(pageProps.content?.stats),
            hasLineup: !!(pageProps.content?.lineup),
            hasShotmap: !!(pageProps.content?.shotmap)
        }
    };
    return apiFormat;
}
```

#### `validateNextDataStructure(nextData)` 的检查顺序

```javascript
// 源码行 153–175
function validateNextDataStructure(nextData) {
    // 检查 1: nextData 存在
    // 检查 2: nextData.props 存在
    // 检查 3: nextData.props.pageProps 存在
    // 检查 4: nextData.props.pageProps.content 存在
}
```

#### `extractFromHtml(html)` 的解析逻辑

```javascript
// 源码行 63–105
function extractFromHtml(html) {
    // Primary match（第 72 行）：
    // /<script\s+id="__NEXT_DATA__"\s+type="application\/json"[^>]*>([\s\S]*?)<\/script>/i
    //
    // Alt match（第 76 行），如果 primary 不匹配：
    // /<script[^>]*id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i
    //
    // 两者都 JSON.parse 提取的内容
}
```

### 8.2 Required minimal nextData paths

根据源码审计，一个能通过 `transformToApiFormat` 的 A2 fixture 最小需要满足：

```javascript
{
  "props": {
    "pageProps": {
      "content": { /* 至少是 {} — 但不能是 undefined */ },
      "general": { /* 可选 — 缺失时 adapter 用 {} */ },
      "header": { /* 可选 — 缺失时 adapter 用 {} */ }
    }
  }
}
```

如果 `pageProps.content` 缺失或 undefined，`transformToApiFormat` 返回 `null`。这是 parser 的硬约束。

### 8.3 Optional representative postmatch-risk paths

为了在 Lane A 回放中验证 adapter 的 postmatch 风险分类仍然正确，建议 A2 fixture 的 `content` 块包含以下代表性字段（值使用 fixture 值，非真实数据）：

```javascript
{
  "props": {
    "pageProps": {
      "content": {
        "stats": { "expectedGoals": { "home": 1.23, "away": 0.98 } },
        "shotmap": [ { "id": "shot-001", "xG": 0.12 } ],
        "events": [ { "id": "event-001", "type": "Goal" } ],
        "playerStats": { "home": [], "away": [] },
        "lineup": { "home": { "players": [] }, "away": { "players": [] } }
      },
      "general": {
        "matchTimeUTC": "2026-07-04T12:00:00.000Z",
        "league": "Fixture League"
      },
      "header": {
        "status": { "utcTime": "2026-07-04T12:00:00.000Z", "scoreStr": "2 - 1" },
        "teams": [
          { "id": "home-fixture", "name": "Home Fixture", "score": 2 },
          { "id": "away-fixture", "name": "Away Fixture", "score": 1 }
        ]
      }
    }
  }
}
```

### 8.4 Known parser output shape

`transformToApiFormat` 的输出形状为（无论输入来自 A1 还是 A2）：

```javascript
{
  "matchId": "<string>",
  "content": { /* pageProps.content 的浅拷贝 */ },
  "general": { /* pageProps.general 的浅拷贝，缺失时为 {} */ },
  "header": { /* pageProps.header 的浅拷贝，缺失时为 {} */ },
  "_meta": {
    "source": "web_infiltration",
    "extractedAt": "<ISO 8601 string — parser 执行时的当前时间>",
    "hasStats": true/false,
    "hasLineup": true/false,
    "hasShotmap": true/false
  }
}
```

### 8.5 Known failure modes

| 失败模式 | 触发条件 | `transformToApiFormat` 返回 |
| --- | --- | --- |
| `nextData` 为 null/undefined | 输入无效 | `null` |
| `nextData.props` 缺失 | nextData 不是 FotMob nextData 结构 | `null` |
| `nextData.props.pageProps` 缺失 | nextData.props 存在但结构异常 | `null` |
| `pageProps.content` 缺失 | 页面没有内容数据（如 error page） | `null` |

### 8.6 重要声明

```
DATA-L1E-8 只记录 contract，不创建 nextData fixture。
Future fixture must be sanitized by construction — 不建议从真实 FotMob 页面复制 nextData。
A2 fixture 不需要 pageProps 中的所有字段，只需要最小触发路径即可。
```

---

## 9. Minimal raw HTML contract

### 9.1 基于 `NextDataParser.extractFromHtml` 源码审计

`extractFromHtml(html)` 使用正则表达式匹配 `<script>` 标签，两种匹配模式：

**Primary match（第 72 行）：**
```javascript
/<script\s+id="__NEXT_DATA__"\s+type="application\/json"[^>]*>([\s\S]*?)<\/script>/i
```

要求：
- `<script` — 开始标签
- `\s+` — 至少一个空白字符
- `id="__NEXT_DATA__"` — 精确 id
- `\s+` — 至少一个空白字符
- `type="application/json"` — 精确 type
- `[^>]*>` — 可选的额外属性 + 闭合 `>`
- `([\s\S]*?)` — 捕获内容（lazy，非贪婪）
- `<\/script>` — 结束标签

**Alt match（第 76 行），如果 primary 不匹配：**
```javascript
/<script[^>]*id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/i
```

要求：
- `<script` — 开始标签
- `[^>]*` — 任意属性（不包括 `>`）
- `id="__NEXT_DATA__"` — 精确 id（可以在任意位置）
- `[^>]*>` — 其余属性 + 闭合 `>`
- `([\s\S]*?)` — 捕获内容
- `<\/script>` — 结束标签

### 9.2 最小能触发 `extractFromHtml` 的 HTML

基于以上正则，最小 HTML shell 为：

```html
<html>
  <head></head>
  <body>
    <script id="__NEXT_DATA__" type="application/json">
      { "props": { "pageProps": { "content": {} } } }
    </script>
  </body>
</html>
```

这个 HTML：
- 有 `<script id="__NEXT_DATA__" type="application/json">` — 匹配 primary regex
- 包含最小 valid JSON（至少满足 `transformToApiFormat` 的 `content` 要求）
- 无任何真实 FotMob 内容
- 无 CSS / JS / ads / trackers / OneTrust

### 9.3 A1 HTML fixture 约束

- **A1 比 A2 更接近真实页面**，但 fixture hygiene 风险更高
- **A1 仍然不允许真实 FotMob HTML** — 不允许 `_next/static/chunks/`、`_buildManifest.js`、真实 CSS、真实 inline JS
- **A1 只允许 minimal sanitized HTML shell** — 只包含 `script#__NEXT_DATA__` 标签 + 最小 JSON 内容
- **A1 不包含 `<link>`、`<style>`、inline `<script>`（除 `__NEXT_DATA__` 外）、`<meta>` tags 中可能泄露真实源的信息**

### 9.4 A1 已知风险

- `extractFromHtml` 的 alt regex 非常宽松 — 几乎任何包含 `id="__NEXT_DATA__"` 的 `<script>` 标签都会被匹配。这既是优点（兼容性好）也是风险（可能意外匹配非 FotMob JSON）
- JSON.parse 不会做 FotMob 特有的 schema 验证 — 任何 valid JSON 都会通过
- 如果 HTML fixture 中包含多个 `<script id="__NEXT_DATA__">` 标签（不应该出现，但如果不小心），regex 只匹配第一个

---

## 10. Adapter options handoff

### 10.1 复用 DATA-L1E-7 的 `buildAdapterOptionsFromRawRecord`

DATA-L1E-7 已经在 `FotMobLocalRawRecordReplay.fixture.test.js` 中实现并验证了 `buildAdapterOptionsFromRawRecord` helper。Lane A 应该 **完全复用** 这个 helper，不做修改。

### 10.2 设计（已在 DATA-L1E-7 test 中实现）

```javascript
function buildAdapterOptionsFromRawRecord(rawRecord) {
  return {
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
    parserVersion: 'legacy-static',
  };
}
```

### 10.3 说明

- 这是未来 DATA-L1E-9 的 test-only helper — Lane A replay test 应该直接复用 Lane B 中已验证的 helper
- 如果 Lane A raw record 结构与 Lane B 相同，则 helper 无需任何修改
- 如果 Lane A raw record 需要新增字段（如 `raw_data.next_data` 或 `raw_data.html_content`），helper 不需要修改 — helper 只从 raw record metadata（非 raw_data 内部）提取 adapter options
- 如果未来需要对 `raw_data` 块做更细粒度的 adapter options 传递，应通过扩展 `raw_data._meta` 实现，而不是修改 helper 的 key fallback 逻辑

```
这是未来 DATA-L1E-9 的 test-only helper 设计，不在 DATA-L1E-8 中实现。
```

---

## 11. Output contract

未来 Lane A dry-run 输出的 envelope 必须满足以下所有条件：

### 11.1 Shape 校验

1. `validateEnvelopeShape(envelope).valid === true`
2. envelope 的 `payload`、`parser`、`fields` 三个顶层块都存在且类型正确

### 11.2 Metadata 正确传递

3. `envelope.source === 'fotmob'`
4. `envelope.match_id` 来自 `rawRecord.match_id`（字符串类型）
5. `envelope.payload.data_version` 正确保留 raw record 中的 `data_version`（或 `'unknown'`）
6. `envelope.payload.payload_hash` 正确保留 raw record 中的 hash（或 `null`）
7. `envelope.payload.storage_path` 正确保留（或 `null`）
8. `envelope.payload.source_url` 正确保留（或 `null`）
9. `envelope.payload.final_url` 正确保留（或 `null`）
10. `envelope.payload.fetched_at` 正确保留（或 `null`）
11. `envelope.payload.captured_at` 正确保留（或 `null`）

### 11.3 Parser metadata

12. `envelope.parser.parser_name` 为 `'NextDataParser.transformToApiFormat'`（或未来明确声明的其他值）
13. `envelope.parser.parser_version` 为 `'legacy-static'`（或未来明确声明的其他值）
14. `envelope.parser.parsed_at` 为 `null`（或未来显式覆盖的值 — 但默认 test context 下保持 `null`）

### 11.4 Safety

15. `envelope.fields` 不产生 `ALLOWED_CANDIDATE` — 数量为 0
16. `envelope.fields` 不产生 `CANDIDATE_IF_CUTOFF_VALID` — 数量为 0
17. postmatch 字段继续 `forbidden_postmatch`
18. unknown timing 字段继续 `forbidden_unknown_timing`
19. raw-only 字段继续 `forbidden_raw_only`
20. metadata-only 字段继续 `audit_only`

### 11.5 澄清

```text
Lane A output is evidence, not model-ready data.
```

Envelope 中的字段全部是 forbidden，output 的目的是证明链路可行，不是产生可用于模型的字段。

---

## 12. Safety invariants

以下规则在任何 Lane A 实现中不可违反：

| # | Invariant | 说明 |
| --- | --- | --- |
| 1 | No network | 不访问 FotMob / HTTP / HTTPS / 任何远程服务 |
| 2 | No browser | 不启动 Playwright / Puppeteer / headless browser |
| 3 | No scraper / collector | 不调用任何采集器 |
| 4 | No DB read/write | 不读 `raw_match_data` 表，不写任何 DB 行 |
| 5 | No writes to `data/`/`raw/`/`models/`/`logs/` | 不产出这些目录下的任何文件 |
| 6 | No feature engine | 不调用 feature engine |
| 7 | No training | 不运行 ML 训练 |
| 8 | No backtest | 不运行回测 |
| 9 | No production runtime import | 不 import `FotMobStrategy`、`FotMobRawDetailFetcher`、`RawMatchDataVersionSelector`、`src/parsers/fotmob/index.js` |
| 10 | No FotMobStrategy integration | 不接入采集策略 |
| 11 | No FotMobRawDetailFetcher integration | 不接入 raw fetcher |
| 12 | No RawMatchDataVersionSelector integration | 不接入版本选择器 |
| 13 | No `src/parsers/fotmob/index.js` integration | 不通过 index 模块接入 |
| 14 | No schema migration | 不运行 `alembic` / `flyway` / `ALTER TABLE` |
| 15 | No `source_url`/`final_url`/`fetched_at` as model features | metadata 只用于审计 |
| 16 | No `_meta.extractedAt` as `fetched_at`/`captured_at` | parser 执行时间 ≠ 数据采集时间 |
| 17 | No `matchTimeUTC`/`utcTime` as `fetched_at`/`captured_at` | 比赛时间 ≠ 数据采集时间 |
| 18 | No `parsed_at` as `fetched_at` | parser 执行时间 ≠ 数据采集时间 |
| 19 | Missing metadata stays `null`/`'unknown'` | 不伪造缺失的 metadata |
| 20 | Unknown timing stays forbidden | 没有 observed_at 证据的字段不能进入模型 |
| 21 | A1/A2 fixtures must be sanitized by construction | 构造性 sanitized，不能从真实页面 copy-paste |
| 22 | Lane A test must remain test-only until separately authorized | 即使 test 通过，也不是 production authorization |

---

## 13. Proposed DATA-L1E-9 implementation scope

### 13.1 建议任务名

```text
DATA-L1E-9: Local __NEXT_DATA__ Replay Fixture Test
```

### 13.2 建议优先 A2

```text
A2: sanitized __NEXT_DATA__ JSON → transformToApiFormat → adapter → envelope
```

### 13.3 建议允许修改的文件

```text
tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_raw_record_fixture.json    (新增)
tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_next_data_fixture.json     (新增)
tests/unit/parsers/fotmob/FotMobLocalNextDataReplay.fixture.test.js                         (新增)
docs/data/fotmob_local_nextdata_replay_fixture_test.md                                      (新增)
```

### 13.4 如果必须新增 helper

建议放 test-only helper：

```text
tests/unit/parsers/fotmob/helpers/localNextDataReplayHelper.js
```

但默认优先不要新增 helper 文件 — 直接在 test 文件内部定义 helper 函数（与 DATA-L1E-7 风格保持一致）。

### 13.5 DATA-L1E-9 默认禁止修改

```text
src/**
adapter (FotMobParserOutputEnvelopeLegacyAdapter.js)
envelope schema (FotMobParserOutputEnvelope.js)
NextDataParser (NextDataParser.js)
FotMobStrategy
FotMobRawDetailFetcher
RawMatchDataVersionSelector
src/parsers/fotmob/index.js
feature / training / backtest
DB / migrations
scraper / collector
.github/**
Docker
```

### 13.6 Escalation path

```text
If DATA-L1E-9 requires modifying src/** (包括 NextDataParser、adapter、envelope schema),
stop and create a separate design/implementation task.
Do not expand scope in DATA-L1E-9.
```

---

## 14. Future A1 implementation boundary

### 14.1 建议任务名

```text
DATA-L1E-10: Local Raw HTML __NEXT_DATA__ Extraction Fixture Test
```

### 14.2 A1 要额外确认的事项

1. minimal sanitized HTML shell 是否足够触发 `extractFromHtml` 的 primary regex？
2. `extractFromHtml` 是否只依赖 `script#__NEXT_DATA__`，不访问 DOM 之外的资源？
3. HTML fixture 不包含真实页面 — 不含 `_next/static/`、CSS、inline JS、`<link>`、`<style>`
4. 不包含 OneTrust / ads / trackers / cookies / headers / 任何第三方脚本
5. 不访问网络 — `extractFromHtml` 是纯字符串正则解析，不发起 HTTP 请求
6. 仍然只允许 test-only — 不接入 production runtime
7. A1 的 fixture 文件（`.html`）需要额外的 sanitization review（不同于 `.json` fixture）
8. A1 的 fixture 禁止放在 `data/`/`raw/` 目录下 — 只允许放在 `tests/fixtures/fotmob/` 目录

### 14.3 A1 的已知额外风险

- `.html` 文件比 `.json` 更容易被误认为是"真实页面"，sanitization review 需要更严格
- `extractFromHtml` 的 alt regex 非常宽松 — 如果 fixture 中有多个 `id="__NEXT_DATA__"` 的 script tag（不应出现但可能被误写），行为取决于 regex 的第一个匹配

---

## 15. Production integration boundary

### 15.1 即使 Lane A 完成也不等于 production integration

```text
即使 DATA-L1E-9 (A2) 和 DATA-L1E-10 (A1) 都完成，
也仍然不是 production integration。
真正接 runtime 至少需要后续独立任务，
例如 DATA-L1E-11 Staging-only Runtime Integration Plan 或 DATA-L2。
```

### 15.2 Production integration 前至少还需要

| # | Pre-requisite | Status |
| --- | --- | --- |
| 1 | Lane B fixture test (DATA-L1E-7) 已合并 | ✅ merged (PR #1713) |
| 2 | Lane A2 `__NEXT_DATA__` fixture test (DATA-L1E-9) 通过 | ⬜ future |
| 3 | Lane A1 minimal HTML fixture test (DATA-L1E-10) 通过 | ⬜ future / optional |
| 4 | URL sanitizer policy 明确 | ⬜ future |
| 5 | `fetched_at` clock source policy 明确 | ⬜ future |
| 6 | raw storage / DB read-write policy 明确 | ⬜ future |
| 7 | staging-only plan 明确 | ⬜ future |
| 8 | rollback plan 明确 | ⬜ future |
| 9 | feature/training/backtest 隔离仍然保持 | ✅ 当前保持 |
| 10 | postmatch leakage checks 仍然通过 | ✅ 当前保持 |

---

## 16. Deep flatten status

```text
deep flatten 仍未处理。
它是独立问题。
DATA-L1E-8 不处理 deep flatten。
Lane A replay 可以继续依赖现有 parent raw block forbidden 策略保持安全。
如果未来需要 deep flatten，应另开 DATA-L1E-5C 或 DATA-L1E-3A。
Do not start automatically.
```

当前 adapter 的 `flattenTransformOutputFields` 把 `content`、`general`、`header` 作为整块 raw block 标记为 `FORBIDDEN_RAW_ONLY`，只展开 `_meta.hasStats` / `_meta.hasShotmap` / `_meta.hasLineup` 标记的子字段。这种策略在 Lane A 回放中同样有效 — deep flatten 不是 Lane A 的前置条件。

---

## 17. Open questions

以下问题在设计阶段需要明确。能根据现有源码/文档回答的标为 `answered`，不能的标 `open`。

| # | Question | Status | Answer/Note |
| --- | --- | --- | --- |
| 1 | DATA-L1E-9 是否优先 A2，而不是 A1？ | **answered** | 是。A2 风险更低、fixture 更简单、不涉及 HTML regex parsing。见 §4.3。 |
| 2 | 是否已有足够 sanitized `__NEXT_DATA__` JSON 可以作为 A2 fixture？ | **open** | 需要构造新的 fixture。现有 Lane B transform output fixture 是 `transformToApiFormat` 的输出，不是 `__NEXT_DATA__` 输入。A2 需要的是 `__NEXT_DATA__` 格式的输入 fixture。 |
| 3 | A2 fixture 应该保留哪些最小 `pageProps.content` / `general` / `header` 字段？ | **answered** | 至少 `content: {}`（非空对象但可以只有代表性字段）。建议包含 `content.stats`、`content.lineup`、`content.shotmap`、`general.matchTimeUTC`、`header.teams`、`header.status.scoreStr`，以验证 adapter 的 postmatch 分类正确。见 §8.3。 |
| 4 | 是否需要先定义 URL sanitizer policy？ | **answered（在当前文档中）** | §6 已定义 sanitization policy，包括 URL 必须使用 `example.invalid`。但更完整的 URL sanitizer policy（如允许的 TLD、path 规则、多源 URL 规范）可以后续单独成文。 |
| 5 | 是否需要先定义 `fetched_at` clock source policy？ | **open** | Fixture 中的 `fetched_at` 是手动设置的固定值。但 production 环境中 `fetched_at` 应该以哪个 clock 为准（NTP / server time / container time / FotMob 响应 header 中的 Date）尚未定义。这不阻塞 fixture test，但 production integration 前需要明确。 |
| 6 | A1 minimal HTML shell 是否足够触发 `extractFromHtml`？ | **answered（基于源码审计）** | 是。`extractFromHtml` 是纯字符串正则匹配，不依赖 DOM、CSS、JS、或页面结构。`<script id="__NEXT_DATA__" type="application/json">...</script>` 就足够触发 primary regex。见 §9.1。 |
| 7 | 是否需要覆盖 parser failure path？ | **open** | 当前 Lane B 测试只覆盖 happy path。Lane A 可能也需要覆盖 `extractFromHtml` 返回 `{success: false, error: ...}` 的场景（如 HTML 无 `__NEXT_DATA__` script、JSON 解析失败）。建议 DATA-L1E-9 至少覆盖 `transformToApiFormat` 返回 `null` 的场景（如 `content` 缺失）。 |
| 8 | 是否需要覆盖 missing metadata path？ | **answered** | DATA-L1E-7 已验证 minimal raw record metadata（全部 null/unknown）。Lane A 可以复用同样的 minimal raw record，只需在 `raw_data` 中添加 `contains_sanitized_next_data: true` 标记。 |
| 9 | 是否需要覆盖 malformed `__NEXT_DATA__` path？ | **open** | 例如 `__NEXT_DATA__` JSON 中 `pageProps` 缺失或 `content` 为 `null`。`transformToApiFormat` 在源码中有明确的 null 返回，可以覆盖。但这增加了 fixture 数量和测试复杂度。建议至少覆盖 `content` 缺失这一种失败模式。 |
| 10 | 是否允许 future test helper 文件，还是必须全部放 test 文件内部？ | **answered** | DATA-L1E-7 的做法是把 helper 函数（`buildAdapterOptionsFromRawRecord`、`replayLocalRawRecordLaneB`、`assertNoSafeFields` 等）直接放在 test 文件内部，不单独建 helper 文件。Lane A 建议保持同样风格。见 §13.4。 |

---

## 18. What changed

| 文件 | 操作 |
| --- | --- |
| `docs/data/fotmob_local_raw_html_nextdata_replay_design.md` | 新增（本文档） |

---

## 19. What did not change

- 没有改 `src/**`
- 没有改 adapter（`FotMobParserOutputEnvelopeLegacyAdapter.js`）
- 没有改 envelope schema（`FotMobParserOutputEnvelope.js`）
- 没有改 NextDataParser（`NextDataParser.js`）
- 没有改 FotMobStrategy
- 没有改 FotMobRawDetailFetcher
- 没有改 RawMatchDataVersionSelector
- 没有改 `src/parsers/fotmob/index.js`
- 没有改 tests
- 没有改 fixtures
- 没有新增 fixture
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集（scraper / collector / browser）
- 没有运行 parser
- 没有运行 replay
- 没有写 DB / raw / data
- 没有改 feature / training / backtest
- 没有启动 DATA-L1E-9
- 没有启动 DATA-L2
- 没有处理 deep flatten

---

## 20. Recommended next task

```text
DATA-L1E-9: Local __NEXT_DATA__ Replay Fixture Test
```

建议优先实现 Lane A2（sanitized `__NEXT_DATA__` JSON → `transformToApiFormat` → adapter → envelope），理由见 §4.3。

```text
Do not start automatically.

Recommended next task only after user confirmation.
```
