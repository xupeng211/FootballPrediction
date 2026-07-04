# FotMob URL Sanitizer and Clock Source Policy

- **lifecycle:** permanent / policy-reference
- **task:** DATA-L1E-7A
- **type:** docs-only / policy design
- **parent:** DATA-L1E-HYGIENE-1

---

## 1. 背景

```text
DATA-L1E-9 已经完成 Lane A2：
sanitized __NEXT_DATA__ JSON fixture → transformToApiFormat → adapter → envelope。

DATA-L1E-HYGIENE-1 已经指出，
继续做 DATA-L1E-10 之前需要降低 HTML fixture/document 风险。

DATA-L1E-10 如果执行，会涉及 local raw HTML / __NEXT_DATA__ extraction fixture。
HTML fixture 比 JSON fixture 更容易误带入真实 URL、tracking、consent、
cookie、token、session、browser fingerprint 或真实页面 payload。

所以 DATA-L1E-7A 先定义 URL sanitizer policy 和 clock source policy。
```

---

## 2. Scope

```text
This is a policy-only PR.

It does not implement sanitizer code.
It does not implement clock source code.
It does not modify src/**.
It does not modify tests/**.
It does not modify tests/fixtures/**.
It does not create HTML fixtures.
It does not call NextDataParser.
It does not call extractFromHtml.
It does not access FotMob.
It does not write DB/raw/data.
It does not start DATA-L1E-10.
```

---

## 3. URL Sanitizer Policy

### 3.1 Allowed in fixtures

```text
Allowed:
- example.invalid URLs
- fixture IDs (fixture-local-replay-a2-001, fixture-metadata-001 等)
- synthetic route paths (/fotmob/match/fixture-xxx)
- deterministic fake query values if necessary for test semantics
- synthetic fragment identifiers
```

### 3.2 Disallowed in fixtures

```text
Disallowed / forbidden:
- real fotmob.com URLs (www.fotmob.com / fotmob.com / api.fotmob.com 及任何子域名)
- real match URLs (包含真实 match hash 或 path)
- real query strings from live traffic
- cookies (Cookie header, set-cookie, document.cookie)
- tokens (JWT, bearer token, access_token, refresh_token, csrf_token, __Host-*, __Secure-*)
- session IDs (session_id, JSESSIONID, PHPSESSID, connect.sid)
- auth headers (Authorization, X-Auth-Token, X-API-Key, Proxy-Authorization)
- browser fingerprints (user-agent fingerprinting fields, canvas hash, WebGL hash, font list)
- tracking parameters (utm_source, utm_medium, utm_campaign, utm_content, utm_term, fbclid, gclid, msclkid, dclid, twclid)
- analytics payloads (gtag, ga, _ga, _gid, _gat, _gcl_*, amp_*, fp, fbc, fbp)
- ads payloads (google_ad_*, doubleclick, adsense, fbq, _fbp, _fbc, _et)
- consent / OneTrust payloads (OptanonConsent, OptanonAlertBoxClosed, OneTrust, consent, cmp, euconsent, gdpr)
- raw request headers (Host, Referer, Origin, User-Agent 含指纹, X-Forwarded-For, X-Real-IP, CF-Ray, CF-IPCountry, X-Cache)
- user-specific values (user_id, email, phone, ip address, device_id, advertising_id)
```

### 3.3 URL Sanitization Examples

```text
Real URL (禁止):
https://www.fotmob.com/matches/team-a-vs-team-b/abc123#123456

Sanitized URL (允许):
https://example.invalid/fotmob/match/fixture-a1-001
```

```text
Real URL with query params (禁止):
https://www.fotmob.com/matches/liverpool-vs-manchester-city/1abc2d#4830473?utm_source=fotmob&utm_medium=share

Sanitized URL (允许):
https://example.invalid/fotmob/match/fixture-a1-002
```

```text
Real API URL (禁止):
https://www.fotmob.com/api/matchDetails?matchId=4830473&ccode3=ENG_1

Sanitized URL (允许):
https://example.invalid/fotmob/api/match/fixture-a1-003
```

### 3.4 Fixture URL Principle

```text
Fixture URL is evidence-only.
It must not be usable as a real fetch target.
It must not preserve real FotMob match identifiers
unless explicitly authorized and proven safe.
```

---

## 4. URL Sanitizer Replacement Rules

| # | Input category | Policy | Replacement | Reason |
|---|---|---|---|---|
| 1 | `fotmob.com` host (any subdomain) | **forbidden** | `example.invalid` | 不能暴露真实 FotMob 访问目标 |
| 2 | real match path (`/matches/{team1}-vs-{team2}/{hash}`) | **forbidden** | `/fotmob/match/fixture-xxx-###` | 不能保留真实 match hash |
| 3 | real API path (`/api/matchDetails`, `/api/teams`, etc.) | **forbidden** | `/fotmob/api/match/fixture-xxx-###` | 不能暴露 API 调用模式 |
| 4 | query string (general) | **strip unless synthetic** | remove entirely | 真实 query string 可能含有 tracking/ID |
| 5 | `utm_*` params | **forbidden, strip** | remove | tracking parameters — 绝对不能 |
| 6 | `fbclid`, `gclid`, `msclkid`, `dclid`, `twclid` | **forbidden, strip** | remove | click tracking IDs — 绝对不能 |
| 7 | fragment/hash (`#123456`) | **strip unless synthetic** | remove or replace with `#fixture` | 真实 hash 可能含有 match ID |
| 8 | cookie / set-cookie | **forbidden, do not replace silently** | remove entire entry | 包含 session/token，不能静默替换 |
| 9 | session ID / token / JWT | **forbidden, do not replace silently** | remove entire entry | 认证凭据 — 绝对不能进入 fixture |
| 10 | authorization headers | **forbidden, do not replace silently** | remove entire entry | 认证凭据 — 绝对不能进入 fixture |
| 11 | OneTrust / consent identifiers | **forbidden, do not replace silently** | remove entire entry | 第三方 consent payload |
| 12 | browser fingerprint values | **forbidden, do not replace silently** | remove entire entry | 浏览器指纹 — 绝对不能 |
| 13 | raw request headers (full header block) | **forbidden** | remove entirely | 包含 Host/Referer/Cookie/IP 等敏感信息 |
| 14 | real team names in URL path | **replace if present** | `Fixture Home` / `Fixture Away` | 不能暴露真实球队关联 |

### 4.1 Forbidden Replacement Strategies

```text
以下 replacement 方式明确禁止：
- 把 real fotmob.com URL 缩短为相对路径（如 /match/4830473）— 保留真实 match ID 仍可用于重构 URL
- 把 cookie 值替换为 "REDACTED" — 值的模式可能仍然可逆
- 把 token 前缀保留（如 Bearer eyJ... → Bearer REDACTED）— 前缀本身可推断认证方案
- 把 query string 的 key 保留只抹 value — key 名称可能泄露 API 参数语义
- 把 host 替换但保留完整 path + query — 仍然暴露 API schema 和 match 关联

正确做法：
- host → example.invalid
- 完整 path → synthetic fixture path
- cookie/token/session/auth header → 整条删除，不替换
- query string → 整条删除，除非是测试需要的 synthetic 值
- 真实 match ID → fixture-local-match-NNN
- 真实 team name → Fixture Home / Fixture Away
```

---

## 5. HTML Fixture Sanitization Policy

```text
本任务（DATA-L1E-7A）不新增 HTML fixture，不处理 HTML。
以下规则约束未来的 DATA-L1E-10 或其他 HTML fixture 任务。
```

### 5.1 Future HTML Fixture Requirements

```text
Future HTML fixture must be minimal shell only:
- It must contain only the minimum script tag needed by extractFromHtml
  (i.e., <script id="__NEXT_DATA__" type="application/json">...</script>)
- It must NOT copy full live FotMob HTML
- It must NOT include CSS, ads, analytics, consent manager, tracking scripts,
  preload links, real headers, real URLs, or unrelated scripts
- It must use synthetic __NEXT_DATA__ payload
- It must use example.invalid only
- All URLs in the HTML (src, href, action, form action, link, meta) must be
  example.invalid or removed
```

### 5.2 HTML Fixture Mandatory Markers

```text
Every HTML fixture must contain these explicit markers:
- contains_live_fotmob_payload: false
- contains_sanitized_html: true
- contains_sanitized_next_data: true

If a fixture contains _meta with these fields (like raw record fixtures do),
their presence is mandatory in the fixture's metadata/comment block.
```

### 5.3 HTML Fixture Prohibitions

```text
HTML fixture must NOT contain:
- <script src="..."> pointing to real CDN or fotmob.com
- <link rel="preload" href="..."> pointing to real assets
- <img src="..."> pointing to real fotmob.com images
- <meta> tags with real tracking/analytics content
- inline <script> with gtag/ga/fbq/OneTrust/consent/tracking logic
- inline <style> or <link rel="stylesheet"> (unless needed for extraction)
- any form, iframe, or object with real URL
- real HTTP headers in HTML comments or meta
- real FotMob navigation/UI/footer/header markup
- <!-- --> comments containing real URL, timestamp, or server info
```

### 5.4 HTML Fixture Scope Note

```text
DATA-L1E-7A does not create this HTML fixture.
This policy only constrains a future DATA-L1E-10 task.

DATA-L1E-10 must check this policy before creating any HTML fixture.
If DATA-L1E-10 cannot satisfy these constraints, it must not proceed
until a revision to this policy is separately authorized.
```

---

## 6. Clock Source Policy

### 6.1 Field Definitions

| # | Field | Meaning (大白话) | Who sets it | Where it lives |
|---|---|---|---|---|
| 1 | `fetched_at` | fetch/browser/network action 完成的时间。数据从 FotMob 拿回来的那一刻。 | Fetcher / harvester | raw record top-level, `raw_data._meta.fetched_at`, `payload.fetched_at` |
| 2 | `captured_at` | raw payload 被确认捕获/保存的时间。数据从网络响应变成可持久化 raw record 的那一刻。 | Raw persistence layer / collector | raw record top-level, `payload.captured_at` |
| 3 | `parsed_at` | adapter/envelope 生成时间。raw data 被 parser 处理后变成 envelope 的那一刻。 | Adapter | `parser.parsed_at` in envelope |
| 4 | `_meta.extractedAt` | legacy NextDataParser 自己生成的解析执行时间。是 transformToApiFormat() 调用 `new Date().toISOString()` 的结果。 | NextDataParser | `transformOutput._meta.extractedAt` → envelope `fields[]._meta.extractedAt` |
| 5 | `matchTimeUTC` | 比赛开球时间（UTC）。FotMob 原始数据中 `general.matchTimeUTC`。 | FotMob source data | `transformOutput.general.matchTimeUTC` → envelope fields |
| 6 | `utcTime` | 比赛状态时间。FotMob 原始数据中 `header.status.utcTime`。通常也是开球时间。 | FotMob source data | `transformOutput.header.status.utcTime` → envelope fields |
| 7 | `data_version` | raw protocol / source 版本标识。不是时间。 | Fetcher / raw record | `payload.data_version` in envelope |
| 8 | `payload_hash` | raw payload 内容的 hash（sha256）。不是时间。 | Raw storage / adapter | `payload.payload_hash` in envelope |
| 9 | `storage_path` | raw payload 保存位置（文件路径 / key）。不是时间。 | Raw storage | `payload.storage_path` in envelope |

### 6.2 Detailed Semantics

#### 6.2.1 `fetched_at`（数据获取时间）

```text
fetched_at 回答的问题是："什么时候从 FotMob 拿到这条数据的？"

来源：
- FotMobRawDetailFetcher.fetchMatchDetail() 完成后记录的 now()
- FotMobStrategy 中 fetch 完成后记录的时间戳
- raw_data._meta.fetched_at（如果 raw record 包含此字段）

特征：
- 早于或等于 captured_at
- 如果 fetch 和 capture 是同一个操作的不同阶段，fetched_at <= captured_at
- 如果数据来自 static fixture，fetched_at 是 fixture 作者设定的
  确定性过去时间，不是 Date.now()
```

#### 6.2.2 `captured_at`（数据捕获确认时间）

```text
captured_at 回答的问题是："什么时候确认这条 raw payload 已经安全保存的？"

来源：
- raw record 写入/持久化完成后的时间戳
- 如果 raw record 来自 dry run，captured_at 可能为 null
- 如果 raw record 来自 fixture，captured_at 是 fixture 作者设定的确定性过去时间

特征：
- 大于或等于 fetched_at
- 如果 capture 失败，captured_at 为 null
- 和 fetched_at 不同：fetched_at 是网络完成时间，captured_at 是持久化确认时间
```

#### 6.2.3 `parsed_at`（Envelope 生成时间）

```text
parsed_at 回答的问题是："什么时候 adapter 把这条 transformOutput
变成 envelope 的？"

来源：
- adapter 调用时显式传入的 options.parsedAt
- 如果未传入，默认 null

特征：
- 晚于或等于 fetched_at / captured_at
- 在 static fixture pipeline 中通常为 null
  （因为 fixture 不经过真实 parser runtime，adapter 收到
  transformOutput 时没有"运行时刻"概念）
- parsed_at 不是 fetched_at，不是 captured_at，不是 extractedAt
```

#### 6.2.4 `_meta.extractedAt`（Legacy Parser 执行时间）

```text
_meta.extractedAt 回答的问题是：
"NextDataParser.transformToApiFormat() 是什么时候被调用的？"

来源：
- NextDataParser.js:138 — `extractedAt: new Date().toISOString()`
- 在 legacy code path 中，NextDataParser 一边提取字段一边打时间戳

特征：
- 这是 parser execution time，不是 data capture time
- 这是 parse-side 时间，不是 fetch-side 时间
- 在 fixture-based pipeline 中，extractedAt 是 fixture 中预置的确定性值
  （如 "2026-07-04T02:30:00.000Z"），不再反映真实的 new Date()
- adapter 的 _addExtractedAtField() 明确声明：
  "legacy extractedAt from NextDataParser._meta — this is parser execution time,
  not data capture time"
```

#### 6.2.5 `matchTimeUTC` / `utcTime`（比赛开球时间）

```text
matchTimeUTC 和 utcTime 回答的问题是："这场比赛什么时候开球的？"

来源：
- matchTimeUTC: FotMob general.matchTimeUTC（比赛基本信息中的开球时间）
- utcTime: FotMob header.status.utcTime（比赛状态中的时间戳）

特征：
- 这是 source data 的一部分
- 这是足球业务时间，不是数据工程时间
- 和 fetch/capture/parse 时间完全无关
- 一条数据可能在开球前 7 天被 fetch（fetched_at << matchTimeUTC）
- 也可能在开球后 3 小时被 fetch（fetched_at >> matchTimeUTC）
```

---

## 7. Clock Source Non-Substitution Rules

### 7.1 Absolute Prohibitions

```text
以下替换绝对禁止：

Never use matchTimeUTC as fetched_at.
  - 开球时间 ≠ 数据获取时间
  - 数据可能在开球前/后任何时间获取

Never use utcTime as fetched_at.
  - 同上

Never use _meta.extractedAt as fetched_at.
  - parser 执行时间 ≠ 网络获取时间
  - 在 fixture 中 extractedAt 甚至是 fixture 作者手写的时间

Never use parsed_at as fetched_at.
  - adapter 运行时间 ≠ 网络获取时间

Never use matchTimeUTC as captured_at.
  - 开球时间 ≠ 持久化确认时间

Never use utcTime as captured_at.
  - 同上

Never use _meta.extractedAt as captured_at.
  - parser 执行时间 ≠ 持久化确认时间

Never use parsed_at as captured_at.
  - adapter 运行时间 ≠ 持久化确认时间

Never fabricate fetched_at.
  - 如果没有 fetch 证据，fetched_at 必须是 null，不能是估计值

Never fabricate captured_at.
  - 如果没有 capture 证据，captured_at 必须是 null，不能是估计值
```

### 7.2 Missing Evidence Policy

```text
If fetched_at evidence is missing, keep fetched_at = null.
  Do not fallback to:
  - matchTimeUTC / utcTime（开球时间）
  - _meta.extractedAt（parser 执行时间）
  - parsed_at（adapter 执行时间）
  - current time（除非当前进程就是实际 fetch 进程，且 policy 显式授权）
  - Date.now()（同上）

If captured_at evidence is missing, keep captured_at = null.
  Do not fallback to:
  - matchTimeUTC / utcTime
  - _meta.extractedAt
  - parsed_at
  - fetched_at（fetch 成功 ≠ capture 确认）
  - current time
  - Date.now()

Null is the correct value for missing evidence.
Null is better than a wrong fallback.
Null means "we don't know" — which is honest and auditable.
```

### 7.3 Current Time as Fallback

```text
使用 current time / Date.now() 作为 fetched_at 或 captured_at 的
fallback 只在以下条件全部满足时允许：

1. 当前进程就是实际的 fetch/capture 进程
   （不是 fixture replay，不是 test，不是 dry run）
2. 代码路径中有明确注释说明当前时间被用作 fetched_at/captured_at
3. Policy 显式授权该代码路径使用 current time

在任何其他情况下——特别是 fixture、test、replay、dry run——
使用 current time / Date.now() 是禁止的。

Fixture 中的 fetched_at / captured_at 必须是确定性过去时间，
例如 "2026-07-04T01:00:00.000Z"，而不是动态生成的 Date.now()。
```

---

## 8. Clock Source Precedence

### 8.1 `fetched_at` Precedence

| Priority | Source | Condition |
|---|---|---|
| 1 | Explicit raw record `fetched_at` (top-level) | Present and non-null |
| 2 | `raw_data._meta.fetched_at` | Present and non-null, not equal to matchTimeUTC/utcTime |
| 3 | Future fetcher-provided `fetchCompletedAt` | If separately implemented and authorized |
| 4 | `null` | Fallback — no fetch evidence available |

### 8.2 `captured_at` Precedence

| Priority | Source | Condition |
|---|---|---|
| 1 | Explicit raw record `captured_at` (top-level) | Present and non-null |
| 2 | Raw storage/capture layer timestamp | If raw persistence layer records capture time |
| 3 | Future raw persistence confirmation timestamp | If separately implemented and authorized |
| 4 | `null` | Fallback — no capture evidence available |

### 8.3 `parsed_at` Precedence

| Priority | Source | Condition |
|---|---|---|
| 1 | Adapter/envelope creation time if explicitly passed | `options.parsedAt` is non-null |
| 2 | `null` | Default in static fixtures unless intentionally set |

### 8.4 `_meta.extractedAt` Precedence

| Priority | Source | Condition |
|---|---|---|
| 1 | NextDataParser / legacy parser output only | `transformOutput._meta.extractedAt` |
| — | **Audit-only.** Never source of fetched_at / captured_at / parsed_at | Always |

### 8.5 `matchTimeUTC` / `utcTime` Precedence

| Priority | Source | Condition |
|---|---|---|
| 1 | Source kickoff time only | FotMob `general.matchTimeUTC` / `header.status.utcTime` |
| — | **Never source of fetch / capture / parse time.** | Always |

---

## 9. Fixture Policy

### 9.1 Mandatory Fixture Fields

```text
Every future FotMob L1E fixture (raw record, transform output, next data)
must contain or explicitly declare:

Required in raw record fixtures:
- source_url (example.invalid)
- final_url (example.invalid)
- fetched_at (deterministic past timestamp or null)
- captured_at (deterministic past timestamp or null)
- data_version (deterministic version string)
- payload_hash or data_hash (deterministic hash string)
- storage_path (deterministic path or null)

Required in fixture metadata / comment / marker:
- contains_live_fotmob_payload: false
- contains_sanitized_next_data: true/false (as applicable)
- contains_sanitized_html: true/false (as applicable)
```

### 9.2 Fixture Determinism Rules

```text
Fixtures must use controlled deterministic values:
- Fixtures must NOT use real current time
- Fixtures must NOT use Date.now()
- Fixtures must NOT use Math.random()
- Fixtures must NOT contain real FotMob URLs
- Fixtures must NOT contain real request headers
- Fixtures must NOT contain cookies/tokens/sessions
- Fixtures must NOT contain real match IDs (unless explicitly authorized
  and proven safe)
- Fixture timestamps should use fixed past dates like
  "2026-07-04T01:00:00.000Z" — same value every test run

Rationale:
- Deterministic fixtures produce deterministic test results
- Date.now() in fixtures means every test run sees different values
- This breaks snapshot testing, hash comparison, and replay verification
```

---

## 10. Adapter / Envelope Handoff Policy

### 10.1 Metadata as Audit/Provenance

```text
source_url, final_url, fetched_at, captured_at, data_version,
payload_hash, storage_path are audit/provenance fields.

They must:
- Remain in envelope.payload / metadata
- Be accessible for audit, replay, joining, filtering, debugging

They must NOT:
- Become model-safe fields
- Be emitted as ALLOWED_CANDIDATE
- Be emitted as CANDIDATE_IF_CUTOFF_VALID
- Be promoted to feature inputs without separate authorization
```

### 10.2 Metadata Purpose Statement

```text
Metadata is for audit, replay, joining, filtering, debugging.
Metadata is not model feature approval.

payload.payload_hash exists so we know which raw payload was used.
payload.fetched_at exists so we know when the data was collected.
payload.captured_at exists so we know when the data was persisted.
payload.source_url exists so we know where the data came from.

None of these are football features.
None of these should enter the model.
None of these should affect prediction output.
```

### 10.3 Current Adapter Behavior (as of 2026-07-04)

```text
FotMobParserOutputEnvelopeLegacyAdapter._buildPayloadMeta():
- payload_hash: from options.payloadHash, default null
- captured_at: from options.capturedAt, default null
- data_version: from options.dataVersion, default 'unknown'
- storage_path: from options.storagePath, default null
- source_url: from options.sourceUrl, default null
- final_url: from options.finalUrl, default null
- fetched_at: from options.fetchedAt, default null

These fields are in envelope.payload and are NOT promoted to model fields.
The adapter's _addExtractedAtField() correctly labels _meta.extractedAt
as AUDIT_ONLY / DEBUG_OR_RAW_ONLY.

This behavior is correct and must not be changed by sanitizer/clock policy.
Future adapter changes must preserve this separation.
```

---

## 11. DATA-L1E-10 Readiness Rules

```text
DATA-L1E-10 may proceed only if it follows this policy.

DATA-L1E-10 must:
- use minimal sanitized HTML shell
- use example.invalid only
- avoid real FotMob HTML copy
- avoid real URL / token / cookie / tracking / consent / analytics
- keep A1 fixture test-only
- not modify runtime
- not access FotMob network
- not write DB/raw/data
- not approve model fields
- not promote metadata to feature inputs
- include contains_live_fotmob_payload: false marker
- include contains_sanitized_html: true marker
- verify no forbidden strings in fixture (see §3.2)
```

```text
DATA-L1E-10 should not start automatically.
It requires explicit user authorization.

Before authorizing DATA-L1E-10, confirm:
1. This policy (DATA-L1E-7A) is merged and documented
2. User explicitly chooses to proceed with Lane A1
3. All fixture requirements (§5, §9) are understood
4. Validation checklist (§12) is ready for use
```

---

## 12. Validation Checklist for Future PRs

```text
This checklist is for future Claude/Codex agents reviewing any PR
that creates or modifies FotMob HTML / raw record fixtures.

Copy and check each item:
```

```text
[ ] No real fotmob.com URL in fixture
[ ] No cookie/token/session/auth/header
[ ] No OneTrust/consent/tracking/analytics/ads payload
[ ] No full live HTML copy
[ ] Uses example.invalid
[ ] fetched_at has explicit source
[ ] captured_at has explicit source
[ ] fetched_at != matchTimeUTC / utcTime / extractedAt / parsed_at
[ ] captured_at != matchTimeUTC / utcTime / extractedAt / parsed_at
[ ] Missing fetch/capture evidence remains null (no fabricated fallback)
[ ] Fixture timestamps are deterministic (not Date.now())
[ ] metadata does not become model-safe field
[ ] contains_live_fotmob_payload: false
[ ] contains_sanitized_html: true (for HTML fixtures)
[ ] contains_sanitized_next_data: true (for next data fixtures)
[ ] no runtime integration
[ ] no DB/raw/data writes
[ ] no network access
[ ] no real match ID in URL path
[ ] no real team name in URL path
[ ] source_url and final_url are example.invalid
```

---

## 13. Deep Flatten Status

```text
deep flatten 仍未处理。

本政策不处理 deep flatten。

当前安全仍依赖 parent raw block forbidden 策略：
- FotMobParserOutputEnvelopeLegacyAdapter 使用 POSTMATCH_PATH_PREFIXES
  进行顶层路径匹配
- 不包括 deep flatten 后的子字段逐个检查

如果未来处理 deep flatten，必须单独授权。
本政策中的 URL / clock source 规则在 deep flatten 场景下仍然有效。

Deep flatten 授权需要一个独立的 policy 或 implementation task，
例如 DATA-L1E-5C 或 DATA-L1E-3A。
不在 DATA-L1E-7A scope 内。
```

---

## 14. What changed

```text
docs/data/fotmob_url_sanitizer_clock_source_policy.md   (新增)
```

---

## 15. What did not change

```text
没有改 src/**
没有改 tests/**
没有改 tests/fixtures/**
没有改 existing docs
没有删除文件
没有移动文件
没有重命名文件
没有改 adapter
没有改 envelope schema
没有改 NextDataParser
没有调用 NextDataParser
没有调用 extractFromHtml
没有处理 HTML
没有新增 fixture
没有新增 test
没有接 runtime
没有访问 FotMob 网络
没有运行采集
没有写 DB/raw/data
没有改 feature/training/backtest
没有启动 DATA-L1E-10
没有启动 DATA-L2
没有处理 deep flatten
```

---

## 16. Recommended next task

```text
Option A:
DATA-L1E-10: Local Raw HTML __NEXT_DATA__ Extraction Fixture Test
- 如果用户明确想验证 Lane A1
- 必须遵守本 policy 的所有约束
- 必须 minimal HTML shell，example.invalid only
- 必须通过 §12 的 validation checklist

Option B:
DATA-L1E-HYGIENE-2: Consolidate DATA-L1E Canonical Docs and Test Helpers
- 整理 DATA-L1E 相关的 docs 和 test helpers
- 减少重复，提取共享逻辑
- 需要 separate explicit authorization

Recommendation:
Proceed to DATA-L1E-10 only if user explicitly wants to validate Lane A1.
Otherwise defer DATA-L1E-10 and consider consolidation after policy stabilizes.
```

```text
Do not start automatically.
Recommended next task only after user confirmation.
```

---

## Appendix A: Current Fixture Inventory (as of 2026-07-04)

```text
Existing fixtures confirmed to use example.invalid and deterministic timestamps:

1. local_raw_html_nextdata_replay_boundary_a2_raw_record_fixture.json
   - source_url: example.invalid
   - final_url: example.invalid
   - fetched_at: 2026-07-04T01:00:00.000Z
   - captured_at: 2026-07-04T01:00:05.000Z
   - contains_sanitized_next_data: true

2. local_raw_html_nextdata_replay_boundary_a2_next_data_fixture.json
   - matchTimeUTC: 2026-07-04T12:00:00.000Z
   - utcTime: 2026-07-04T12:00:00.000Z
   - No URL fields (transform output, not raw record)

3. local_raw_record_replay_boundary_b_raw_record_fixture.json
   - source_url: example.invalid
   - final_url: example.invalid
   - fetched_at: 2026-07-04T01:00:00.000Z
   - captured_at: 2026-07-04T01:00:05.000Z

4. local_raw_record_replay_boundary_b_transform_output_fixture.json
   - matchTimeUTC: 2026-07-04T12:00:00.000Z
   - utcTime: 2026-07-04T12:00:00.000Z
   - extractedAt: 2026-07-04T02:30:00.000Z

5. metadata_handoff_raw_record_boundary_a_fixture.json
   - source_url: example.invalid
   - final_url: example.invalid
   - fetched_at: 2026-07-04T01:00:00.000Z
   - captured_at: 2026-07-04T01:00:05.000Z

6. metadata_handoff_transform_output_boundary_a_fixture.json
   - matchTimeUTC: 2026-07-04T12:00:00Z
   - utcTime: 2026-07-04T12:00:00Z
   - extractedAt: 2026-07-04T02:30:00.000Z

All existing fixtures comply with the sanitized URL policy (example.invalid only).
All existing fixtures use deterministic timestamps.
No fixture contains cookie/token/session/auth/header.
```

## Appendix B: Field Path Reference (Source Code)

```text
Key source locations for each field (read-only reference, as of 2026-07-04):

fetched_at:
  - FotMobRawDetailFetcher.js:524 — const fetchedAt = now()
  - FotMobRawDetailFetcher.js:633 — assign to raw record
  - FotMobParserOutputEnvelopeLegacyAdapter.js:276 — adapter reads options.fetchedAt

captured_at:
  - FotMobParserOutputEnvelope.js:193 — envelope.payload.captured_at default null
  - FotMobParserOutputEnvelopeLegacyAdapter.js:269 — adapter reads options.capturedAt

parsed_at:
  - FotMobParserOutputEnvelope.js:205 — parser.parsed_at default null
  - FotMobParserOutputEnvelopeLegacyAdapter.js:343 — adapter reads options.parsedAt

_meta.extractedAt:
  - NextDataParser.js:138 — extractedAt: new Date().toISOString()
  - FotMobParserOutputEnvelopeLegacyAdapter.js:297-315 — _addExtractedAtField()

matchTimeUTC:
  - FotMobRawParser.js:94 — general.matchTimeUTC
  - FotMobRouteIdentityReconciler.js:209-211 — used for identity reconciliation

utcTime:
  - FotMobRouteIdentityReconciler.js:212 — header.utcTime
  - FotMobRouteIdentityReconciler.js:213 — header.status.utcTime

source_url / final_url:
  - FotMobParserOutputEnvelope.js:196-197 — envelope.payload default null
  - FotMobParserOutputEnvelopeLegacyAdapter.js:274-275 — adapter reads options
  - FotMobRawDetailFetcher.js:598 — raw record build

payload_hash:
  - FotMobParserOutputEnvelope.js:192 — envelope.payload.payload_hash
  - FotMobParserOutputEnvelopeLegacyAdapter.js:268 — adapter reads options.payloadHash
```

## Appendix C: Example Invalid Usage (Anti-Patterns)

```text
以下是明确禁止的反模式，供 future PR review 参考：

Anti-pattern 1: 用 matchTimeUTC 填充 fetched_at
{
  "fetched_at": "2026-07-04T12:00:00.000Z",  // ← 这其实是 matchTimeUTC
  "matchTimeUTC": "2026-07-04T12:00:00.000Z"
}
问题：fetched_at 和 matchTimeUTC 相同，无法区分 fetch 时间和开球时间。

Anti-pattern 2: 用 extractedAt 填充 captured_at
{
  "captured_at": "2026-07-04T02:30:00.000Z",  // ← 这其实是 extractedAt
  "extractedAt": "2026-07-04T02:30:00.000Z"
}
问题：captured_at 变成了 parser 执行时间，不是数据捕获时间。

Anti-pattern 3: 用 Date.now() 写 fixture
{
  "fetched_at": "2026-07-05T09:23:41.123Z"  // ← Date.now() 每次不同
}
问题：fixture 不再 deterministic，每次 test run 值不同。

Anti-pattern 4: 保留真实 fotmob.com URL 但替换 host
{
  "source_url": "https://example.invalid/matches/liverpool-vs-manchester-city/1abc2d#4830473"
}
问题：保留了真实 match hash 和 team name 在 path 中。
正确：source_url: "https://example.invalid/fotmob/match/fixture-a1-001"

Anti-pattern 5: cookie 值替换为 REDACTED
{
  "headers": {
    "cookie": "session_id=REDACTED; token=REDACTED"
  }
}
问题：REDACTED 不能保护 session 模式信息。
正确：整条 cookie/headers 删除，不进入 fixture。
```
