# FotMob Local Raw HTML __NEXT_DATA__ Extraction Fixture Test

lifecycle: permanent

---

## 1. 背景

DATA-L1E-9 已验证 Lane A2：sanitized `__NEXT_DATA__` JSON fixture → `transformToApiFormat` → adapter → envelope。

DATA-L1E-7A 已定义 URL sanitizer and clock source policy。

DATA-L1E-10 在此基础上验证 Lane A1 的最小 HTML shell：

```text
minimal sanitized local HTML
  -> NextDataParser.extractFromHtml
  -> NextDataParser.transformToApiFormat
  -> adaptTransformToApiFormatOutputToEnvelope
  -> validateEnvelopeShape
  -> assert metadata handoff
  -> assert 0 safe fields
```

本任务是 test-only fixture evidence。只证明 `extractFromHtml` 可以从 minimal sanitized HTML shell 里抽出 `__NEXT_DATA__`，然后继续走到 envelope。

这不是生产接入、不是 scraper、不是浏览器采集、不是真实 FotMob 页面、不是 DB 回放、不是 runtime integration。

---

## 2. Scope

This is test-only fixture evidence.

- 不修改 `src/**`
- 不修改 existing tests
- 不修改 existing fixtures
- 不修改 existing docs
- 不删除文件
- 不移动文件
- 不重命名文件
- 不访问 FotMob 网络
- 不运行 scraper/collector/browser
- 不写 DB/raw/data
- 不接 runtime
- 不 approve model fields

---

## 3. Replay lane

Lane A1（本 PR 实现）:

```text
minimal sanitized local raw HTML
  -> NextDataParser.extractFromHtml
  -> NextDataParser.transformToApiFormat
  -> adapter
  -> envelope
```

Lane A2 已在 DATA-L1E-9 覆盖。

Lane B 已在 DATA-L1E-7 覆盖。

Lane 对比：

| Lane | 输入 | 第一个 parser 调用 | PR |
|------|------|-------------------|-----|
| A1 | minimal sanitized HTML shell | `extractFromHtml` | 本 PR (DATA-L1E-10) |
| A2 | sanitized `__NEXT_DATA__` JSON | `transformToApiFormat` | DATA-L1E-9 (PR #1715) |
| B | already-sanitized transformOutput | adapter only | DATA-L1E-7 (PR #1713) |

---

## 4. HTML sanitization

HTML fixture（`local_raw_html_nextdata_replay_boundary_a1_html_fixture.html`）:

- minimal HTML shell only
- 只有一个 `<script id="__NEXT_DATA__" type="application/json">` 标签
- 使用 synthetic fixture IDs：`fixture-local-replay-a1-001`, `home-fixture-a1`, `away-fixture-a1`
- 使用 synthetic 队伍名：`Home Fixture A1`, `Away Fixture A1`
- 使用 `https://example.invalid/` 作为 URL 域
- 使用 deterministic synthetic time：`2026-07-04T12:00:00.000Z`, `2026-07-04T01:00:00.000Z`

禁止包含：

- 真实 FotMob URL / match URL
- cookie / token / session / auth header
- tracking / analytics / ads / consent payload
- external script / CSS / browser fingerprint
- 完整 live FotMob HTML copy
- 导航/页脚/header markup

---

## 5. Clock policy compliance

遵循 DATA-L1E-7A URL Sanitizer and Clock Source Policy：

| 时间字段 | 来源 | 说明 |
|---------|------|------|
| `fetched_at` | raw record fixture metadata | deterministic fixture value |
| `captured_at` | raw record fixture metadata | deterministic fixture value |
| `parsed_at` | null | 不自动设置 |
| `_meta.extractedAt` | legacy parser `new Date()` | parser 执行时间，audit-only |
| `matchTimeUTC` | nextData fixture content | kickoff time |
| `utcTime` | nextData fixture header | status time |

规则：

- `fetched_at` 不从 `extractedAt` 回填
- `captured_at` 不从 `extractedAt` 回填
- `fetched_at` 不从 `matchTimeUTC` 回填
- `captured_at` 不从 `utcTime` 回填
- 测试必须验证这 4 个 clock 互相不相等

---

## 6. Model safety

- 0 `ALLOWED_CANDIDATE` fields
- 0 `CANDIDATE_IF_CUTOFF_VALID` fields
- payload metadata 留在 `envelope.payload`，不进入 `envelope.fields`
- HTML/nextData replay output 是 evidence，不是 model-ready data
- 所有 content 子字段（stats, shotmap, events, lineup）都被分为 forbidden
- header, general, content 作为 raw block 是 `FORBIDDEN_RAW_ONLY`

---

## 7. Tests

### 新增测试

```bash
node --test tests/unit/parsers/fotmob/FotMobLocalRawHtmlNextDataReplay.fixture.test.js
```

覆盖：

1. HTML fixture sanitation（forbidden keywords 扫描、`__NEXT_DATA__` 标签存在、synthetic IDs）
2. raw record metadata sanity（Lane A1 markers、example.invalid URLs、deterministic timestamps）
3. `extractFromHtml` 成功提取
4. 提取数据有 `props.pageProps.content/general/header`
5. `transformToApiFormat` 成功转换
6. `validateEnvelopeShape` 通过
7. metadata handoff（data_version, payload_hash, storage_path, source_url, final_url, fetched_at, captured_at）
8. clock non-substitution（4 个 clock 互不相等）
9. 0 safe fields
10. forbidden classification sanity（stats/shotmap/events=POSTMATCH, lineup=UNKNOWN_TIMING, content/general/header=RAW_ONLY）
11. no runtime integration

### Regression tests

```bash
node --test tests/unit/parsers/fotmob/FotMobLocalNextDataReplay.fixture.test.js
node --test tests/unit/parsers/fotmob/FotMobLocalRawRecordReplay.fixture.test.js
node --test tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js
node --test tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js
```

---

## 8. What changed

新增 4 个文件：

- `tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a1_raw_record_fixture.json`
- `tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a1_html_fixture.html`
- `tests/unit/parsers/fotmob/FotMobLocalRawHtmlNextDataReplay.fixture.test.js`
- `docs/data/fotmob_local_raw_html_nextdata_extraction_fixture_test.md`

---

## 9. What did not change

- 没有改 `src/**`
- 没有改 existing tests
- 没有改 existing fixtures
- 没有改 existing docs
- 没有删除文件
- 没有移动文件
- 没有重命名文件
- 没有改 adapter
- 没有改 envelope schema
- 没有改 NextDataParser 源码
- 没有改 FotMobStrategy
- 没有改 FotMobRawDetailFetcher
- 没有改 RawMatchDataVersionSelector
- 没有改 `src/parsers/fotmob/index.js`
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集
- 没有写 DB/raw/data
- 没有改 feature/training/backtest
- 没有处理 deep flatten

---

## 10. Remaining gaps

- 不证明真实 FotMob live HTML 稳定性
- 不证明 browser collection
- 不证明 production runtime integration
- 不写或不回放 DB/raw storage
- 不 approve model fields
- deep flatten 仍然未处理

---

## 11. Recommended next task

Do not start automatically.

Recommended next task only after user confirmation.

**Option A:**

DATA-L1E-HYGIENE-2: Consolidate DATA-L1E Canonical Docs and Test Helpers

**Option B:**

DATA-L1E-11: Runtime Integration Readiness Audit for FotMob Envelope Path

**Recommendation:** 如果当前 repo noise/helper duplication 是主要问题，推荐 Option A。如果用户明确要准备 runtime integration，再启动 Option B。
