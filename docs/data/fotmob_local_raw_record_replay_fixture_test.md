# FotMob Local Raw Record Replay Fixture Test

- lifecycle: source-of-truth
- scope: DATA-L1E-7 Lane B local raw record replay fixture test
- parent document: `docs/data/fotmob_local_raw_record_replay_dry_run_design.md` (DATA-L1E-6)
- runtime behavior change: no
- adapter code change: no
- envelope schema change: no
- Lane A: not implemented

---

## 1. 背景

DATA-L1E-6 已设计 local raw record replay dry-run。

DATA-L1E-7 本次实现 Lane B fixture test：

```text
local raw record metadata fixture
  + already-sanitized transformToApiFormat output fixture
  → adapter
  → envelope
  → validateEnvelopeShape
  → assert 0 safe fields
```

本任务不实现 Lane A，不调用 NextDataParser，不接 runtime，不访问 FotMob，不写 DB/raw/data。

只做 test-only Lane B fixture evidence：证明 raw record metadata 能通过 adapter options 正确进入 envelope payload，且安全边界（0 safe fields）不变。

---

## 2. What changed

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `tests/fixtures/fotmob/local_raw_record_replay_boundary_b_raw_record_fixture.json` | 新增 | Lane B raw record metadata fixture（sanitized static） |
| `tests/fixtures/fotmob/local_raw_record_replay_boundary_b_transform_output_fixture.json` | 新增 | Lane B transformToApiFormat output fixture（sanitized static） |
| `tests/unit/parsers/fotmob/FotMobLocalRawRecordReplay.fixture.test.js` | 新增 | Lane B fixture test（36 tests） |
| `docs/data/fotmob_local_raw_record_replay_fixture_test.md` | 新增 | 本文档 |

---

## 3. Replay lane

This PR implements Lane B only.

```text
Lane B:
local raw record metadata fixture
  + already-sanitized transformToApiFormat output fixture
  → buildAdapterOptionsFromRawRecord(rawRecord)
  → adaptTransformToApiFormatOutputToEnvelope(transformOutput, options)
  → envelope
```

Lane A is not implemented:

```text
Lane A (NOT in this PR):
raw HTML / __NEXT_DATA__
  → NextDataParser.extractFromHtml
  → NextDataParser.transformToApiFormat
  → adapter
  → envelope
```

---

## 4. Safety guarantees

- No network.
- No browser.
- No scraper / collector.
- No DB read/write.
- No raw/data output write.
- No `src/**` changes.
- No NextDataParser import.
- No runtime integration.
- No feature/training/backtest.
- No deep flatten.

All test helpers are test-only and Lane B only. The `replayLocalRawRecordLaneB` helper is a pure function that only calls existing adapter/envelope exports.

---

## 5. Metadata validation

已验证从 raw record metadata fixture 进入 envelope.payload 的映射：

| Metadata | rawRecord source | Adapter option | envelope.payload | Verified |
| --- | --- | --- | --- | --- |
| `data_version` | `rawRecord.data_version` | `dataVersion` | `payload.data_version` | yes |
| `payload_hash` | `rawRecord.data_hash` (fallback from `payload_hash=null`) | `payloadHash` | `payload.payload_hash` | yes |
| `storage_path` | `rawRecord.storage_path` | `storagePath` | `payload.storage_path` | yes |
| `source_url` | `rawRecord.source_url` | `sourceUrl` | `payload.source_url` | yes |
| `final_url` | `rawRecord.final_url` | `finalUrl` | `payload.final_url` | yes |
| `fetched_at` | `rawRecord.fetched_at` | `fetchedAt` | `payload.fetched_at` | yes |
| `captured_at` | `rawRecord.captured_at` | `capturedAt` | `payload.captured_at` | yes |

Missing metadata stays `null` / `'unknown'` — verified with minimal raw record replay.

---

## 6. Time semantics

已验证以下时间字段互不混淆：

- `fetched_at` ≠ `captured_at`
- `fetched_at` ≠ `_meta.extractedAt`
- `fetched_at` ≠ `general.matchTimeUTC`
- `fetched_at` ≠ `header.status.utcTime`
- `captured_at` ≠ `_meta.extractedAt`
- `captured_at` ≠ `general.matchTimeUTC`
- `captured_at` ≠ `header.status.utcTime`

Minimal raw record (missing all timestamps) 也验证：
- `fetched_at` / `captured_at` 保持 `null`
- `matchTimeUTC` / `utcTime` 不被误映射

---

## 7. Model safety

- 0 `ALLOWED_CANDIDATE` — verified
- 0 `CANDIDATE_IF_CUTOFF_VALID` — verified
- `payload.fetched_at` / `source_url` / `final_url` 不进入 `envelope.fields` — verified
- `content.stats` / `content.shotmap` / `content.events` → `FORBIDDEN_POSTMATCH` — verified
- `content.lineup` → `FORBIDDEN_UNKNOWN_TIMING` — verified
- `content` / `general` / `header` raw blocks → `FORBIDDEN_RAW_ONLY` — verified

Local replay output is evidence, not model-ready data.

---

## 8. Tests

### 8.1 运行命令

```bash
node --test tests/unit/parsers/fotmob/FotMobLocalRawRecordReplay.fixture.test.js
```

### 8.2 结果

| 测试文件 | 测试数 | 通过 | 失败 |
| --- | --- | --- | --- |
| `FotMobLocalRawRecordReplay.fixture.test.js` | 36 | 36 | 0 |

### 8.3 Regression

| 测试文件 | 测试数 | 通过 | 失败 |
| --- | --- | --- | --- |
| `FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js` | 15 | 15 | 0 |
| `FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js` | 27 | 27 | 0 |

总计: 78 tests, 78 pass, 0 fail.

### 8.4 测试覆盖

**Lane B local replay fixture tests:**

- fixture sanity: rawRecord 和 transformOutput 对齐（matchId/source/example.invalid/no-html/no-next-data/no-live）
- replay returns valid envelope (validateEnvelopeShape pass, source, match_id)
- metadata handoff: data_version/payload_hash/storage_path/source_url/final_url/fetched_at/captured_at
- time semantics: 7 distinct time-semantic assertions (fetched_at/captured_at/extractedAt/matchTimeUTC/utcTime)
- 0 safe fields: ALLOWED_CANDIDATE count, CANDIDATE_IF_CUTOFF_VALID count, payload metadata not in fields
- forbidden classification: stats/shotmap/events/lineup/header raw blocks
- Lane B only: no NextDataParser import, helpers are pure functions

**Missing metadata minimal replay:**

- dataVersion = unknown, all others null
- matchTimeUTC/utcTime not used as capture timestamps
- 0 safe fields

---

## 9. What did not change

- 没有改 `src/**`
- 没有改 adapter（`FotMobParserOutputEnvelopeLegacyAdapter.js`）
- 没有改 envelope schema（`FotMobParserOutputEnvelope.js`）
- 没有改 NextDataParser（`NextDataParser.js`）
- 没有改 FotMobStrategy
- 没有改 FotMobRawDetailFetcher
- 没有改 RawMatchDataVersionSelector
- 没有改 `src/parsers/fotmob/index.js`
- 没有改已有 tests / fixtures
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集（scraper / collector / browser）
- 没有写 DB / raw / data
- 没有改 feature / training / backtest
- 没有处理 Lane A
- 没有处理 deep flatten
- 没有启动 DATA-L1E-8
- 没有启动 DATA-L2

---

## 10. Remaining gaps

- Lane A 未实现（raw HTML / `__NEXT_DATA__` extraction 未验证）
- NextDataParser 的 `extractFromHtml` / `transformToApiFormat` 未在 local replay 中调用
- deep flatten 仍未处理（独立问题）
- runtime integration 仍未实现
- URL sanitizer policy 仍未最终定义
- fetched_at clock source policy 仍未最终定义

---

## 11. Recommended next task

默认推荐：

```text
DATA-L1E-8: Local Raw HTML / __NEXT_DATA__ Replay Design
```

或者如果不想碰 Lane A：

```text
DATA-L1E-7A: URL Sanitizer and Clock Source Policy Design
```

Do not start automatically.

Recommended next task only after user confirmation.
