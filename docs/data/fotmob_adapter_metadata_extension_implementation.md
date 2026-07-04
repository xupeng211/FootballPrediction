# FotMob Adapter Metadata Extension Implementation

- lifecycle: source-of-truth
- scope: DATA-L1E-5B adapter metadata extension implementation
- parent document: DATA-L1E-5A docs-only design
- runtime behavior change: no (no production runtime integration)

---

## 1. 背景

DATA-L1E-5A 已设计 `fetched_at` / `source_url` / `final_url` metadata extension。
DATA-L1E-5B 本次实现最小 adapter/envelope 扩展。

本任务不接 runtime、不访问 FotMob、不写 DB/raw/data。

当前已完成背景：

- DATA-L1E-1: `FotMobParserOutputEnvelope` schema 已落地
- DATA-L1E-2: `FotMobParserOutputEnvelopeLegacyAdapter` dry-run-only adapter 已实现
- DATA-L1E-3: static fixtures 已验证 adapter 兼容性，保持 0 safe fields
- DATA-L1E-4: metadata handoff dry-run plan 已完成
- DATA-L1E-5: fixture-level metadata handoff test 已完成
- DATA-L1E-5A: docs-only adapter metadata extension design 已完成并合并（PR #1710）

本任务实现 DATA-L1E-5A 设计中的以下 3 个 metadata 字段的 adapter 和 envelope 支持：

1. `fetched_at` — 抓取动作发生时间
2. `source_url` — 请求 URL
3. `final_url` — 重定向后的最终 URL

---

## 2. What changed

| 文件 | 变更类型 | 说明 |
| --- | --- | --- |
| `src/parsers/fotmob/FotMobParserOutputEnvelope.js` | 修改 | `createEmptyEnvelope` payload 新增 `fetched_at: null` |
| `src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js` | 修改 | `_buildPayloadMeta` 支持 `sourceUrl`/`finalUrl`/`fetchedAt` options |
| `tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.test.js` | 修改 | 新增 11 个 metadata extension 测试 |
| `tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js` | 修改 | 更新 `buildAdapterOptionsFromRawRecord` 和所有相关断言 |
| `docs/data/fotmob_adapter_metadata_extension_implementation.md` | 新增 | 本文档 |

未修改的文件：

- `tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js` — 无需修改，自动兼容

---

## 3. Metadata mapping

| Adapter option | Envelope payload 字段 | 类型 | 默认值 |
| --- | --- | --- | --- |
| `options.sourceUrl` | `payload.source_url` | `string \| null` | `null` |
| `options.finalUrl` | `payload.final_url` | `string \| null` | `null` |
| `options.fetchedAt` | `payload.fetched_at` | `string \| null` | `null` |
| `options.capturedAt` | `payload.captured_at` | `string \| null` | `null` |

映射规则：

- 所有字段都是 optional。未传 option 时，对应 payload 字段保持 `null`。
- `fetchedAt` 之前只用于 warning context，现在也同时写入 `payload.fetched_at`。
- `sourceUrl` 和 `finalUrl` 之前硬编码为 `null`，现在从 options 读取。
- `capturedAt` → `payload.captured_at` 逻辑保持不变。

`buildAdapterOptionsFromRawRecord` 中的 fallback chain：

```javascript
sourceUrl: rawRecord.source_url ?? rawRecord.sourceUrl ?? rawRecord.raw_data?._meta?.request_url ?? null,
finalUrl: rawRecord.final_url ?? rawRecord.finalUrl ?? rawRecord.raw_data?._meta?.final_url ?? null,
fetchedAt: rawRecord.fetched_at ?? rawRecord.fetchedAt ?? rawRecord.raw_data?._meta?.fetched_at ?? null,
```

---

## 4. Safety guarantees

- `fetched_at` / `source_url` / `final_url` 是 audit/provenance/replay metadata。
- 它们不是 model fields。
- 它们不进入 `ALLOWED_CANDIDATE`。
- 它们不进入 `CANDIDATE_IF_CUTOFF_VALID`。
- 不从 `_meta.extractedAt` 推导 `fetched_at`。
- 不从 `matchTimeUTC` / `utcTime` 推导 `fetched_at`。
- 不从 `parsedAt` 推导 `fetched_at`。
- 缺失时保持 `null`，不伪造。
- 不改 `PAYLOAD_TYPES` / `MODEL_ELIGIBILITY` / field classification。
- `validateEnvelopeShape` 不受影响（只检查 `payload` 是否为 object 和 `payload_type` 是否存在）。
- 0 safe fields 策略不变。

---

## 5. Tests

### 5.1 运行命令

```bash
node --test tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.test.js
node --test tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js
node --test tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js
```

### 5.2 结果

| 测试文件 | 测试数 | 通过 | 失败 |
| --- | --- | --- | --- |
| `FotMobParserOutputEnvelopeLegacyAdapter.test.js` | 68 | 68 | 0 |
| `FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js` | 15 | 15 | 0 |
| `FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js` | 27 | 27 | 0 |

总计：110 tests, 110 pass, 0 fail.

### 5.3 测试覆盖

**Adapter unit test 新增覆盖：**

- `sourceUrl` → `payload.source_url`
- `finalUrl` → `payload.final_url`
- `fetchedAt` → `payload.fetched_at`
- 缺失 `sourceUrl`/`finalUrl`/`fetchedAt` → `null`
- `fetchedAt` 不覆盖 `captured_at`（两个独立字段）
- `_meta.extractedAt` 不覆盖 `fetched_at`
- `matchTimeUTC`/`utcTime` 不覆盖 `fetched_at`
- 所有 metadata 字段不产生 `ALLOWED_CANDIDATE` / `CANDIDATE_IF_CUTOFF_VALID`
- `fetched_at`/`source_url`/`final_url` 不出现在 `envelope.fields` 中

**Metadata handoff fixture test 更新覆盖：**

- `options.sourceUrl` === `rawRecord.source_url`
- `options.finalUrl` === `rawRecord.final_url`
- `options.fetchedAt` === `rawRecord.fetched_at`
- `envelope.payload.source_url` === `rawRecord.source_url`
- `envelope.payload.final_url` === `rawRecord.final_url`
- `envelope.payload.fetched_at` === `rawRecord.fetched_at`
- `envelope.payload.captured_at` === `rawRecord.captured_at`
- `envelope.payload.fetched_at` ≠ `envelope.payload.captured_at`
- `envelope.payload.fetched_at` ≠ `transformOutput._meta.extractedAt`
- `envelope.payload.fetched_at` ≠ `transformOutput.general.matchTimeUTC`
- `envelope.payload.fetched_at` ≠ `transformOutput.header.status.utcTime`
- minimal record 缺失 metadata → 全部 `null`
- minimal matchTimeUTC/utcTime 不当 captured_at 或 fetched_at
- 0 safe fields

---

## 6. What did not change

- 没有改 `NextDataParser`
- 没有改 `FotMobStrategy`
- 没有改 `FotMobRawDetailFetcher`
- 没有改 `RawMatchDataVersionSelector`
- 没有改 `src/parsers/fotmob/index.js`
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集（scraper / collector / browser）
- 没有写 DB / raw / data
- 没有改 feature engine
- 没有改 training / backtest
- 没有改 pipeline
- 没有改 `.github/**` / CI workflows
- 没有改 Docker / compose / migrations
- 没有启动 DATA-L1E-6
- 没有启动 DATA-L2
- 没有处理 deep flatten
- 没有删除 / 移动 / 重命名任何文件

---

## 7. Remaining gaps

- **deep flatten 仍未处理**，是独立问题（非 DATA-L1E-5B scope）。
- **local raw record replay dry-run 仍未实现**，需要 DATA-L1E-6。
- **runtime integration 仍未实现**，需要 DATA-L2 或类似任务。
- **URL sanitizer policy**（是否移除敏感 query params、是否截断、是否保存完整 URL）未定义。
- **`fetched_at` clock source**（`Date.now()` vs `new Date().toISOString()`、时区 UTC vs local）未在 adapter 层面强制。

---

## 8. Recommended next task

默认推荐：

```text
DATA-L1E-6: Local Raw Record Replay Dry-Run Design
```

也可以考虑：

```text
Deep flatten 可作为独立 DATA-L1E-5C 或 DATA-L1E-3A，但不要自动启动。
```

Do not start automatically.

Recommended next task only after user confirmation.

---

## 9. Envelope payload contract (post-DATA-L1E-5B)

```javascript
payload: {
    payload_type: 'parser_input',
    payload_hash: 'sha256:...' | null,
    captured_at: '2026-07-04T01:00:05.000Z' | null,
    data_version: 'fotmob_html_hyd_v1' | 'unknown',
    storage_path: null,
    source_url: 'https://...' | null,
    final_url: 'https://...' | null,
    fetched_at: '2026-07-04T01:00:00.000Z' | null,
}
```

所有新增字段都是 nullable metadata，不是模型字段。
