# FotMob Adapter Metadata Extension Design

- lifecycle: source-of-truth
- scope: DATA-L1E-5A docs-only adapter metadata extension design
- parent documents: DATA-L1E-4, DATA-L1E-5
- runtime behavior change: no
- adapter code change: no
- envelope schema change: no

---

## 1. 背景

DATA-L1E-5 已用 static raw-record fixture + transform output fixture 验证 metadata handoff。
该测试确认 `data_version`、`payload_hash`、`captured_at` 可以正确进入 envelope。
该测试也确认当前 adapter gap：

- `fetched_at` 没有持久化到 `payload`；
- `source_url` / `final_url` 当前 adapter 没有 `sourceUrl` / `finalUrl` options，所以 envelope payload 中继续为 null；
- deep flatten 仍是独立问题。

DATA-L1E-5A 只设计前两个 metadata gap 的扩展方案。

本任务 docs-only，不改 adapter、不改 schema、不改 tests、不接 runtime。

---

## 2. Current state

### 2.1 当前 envelope payload 字段

源码审计 `src/parsers/fotmob/FotMobParserOutputEnvelope.js` 第 190-198 行 `createEmptyEnvelope` 函数：

```javascript
payload: {
    payload_type: PAYLOAD_TYPES.UNKNOWN,
    payload_hash: null,
    captured_at: null,
    data_version: null,
    storage_path: null,
    source_url: null,   // ← 已存在，默认 null
    final_url: null,    // ← 已存在，默认 null
}
```

**结论：`source_url` 和 `final_url` 已在 schema 中，但始终为 null。`fetched_at` 不在 schema 中。**

### 2.2 当前 adapter options

源码审计 `src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js`：

`adaptTransformToApiFormatOutputToEnvelope(transformOutput, options)` 接受以下 options：

| Option | 是否支持 | 写入 envelope 位置 | 默认值 |
| --- | --- | --- | --- |
| `source` | Yes | `envelope.source` | `'fotmob'` |
| `dataVersion` | Yes | `payload.data_version` | `'unknown'` |
| `payloadHash` | Yes | `payload.payload_hash` | `null` |
| `storagePath` | Yes | `payload.storage_path` | `null` |
| `capturedAt` | Yes | `payload.captured_at` | `null` |
| **`fetchedAt`** | Partial（仅 warning context） | **不进入 payload** | `null` |
| **`sourceUrl`** | **No** | — | — |
| **`finalUrl`** | **No** | — | — |
| `parsedAt` | Yes | `parser.parsed_at` | `null` |
| `parserName` | Yes | `parser.parser_name` | `'NextDataParser.transformToApiFormat'` |
| `parserVersion` | Yes | `parser.parser_version` | `'legacy-static'` |

### 2.3 `_buildPayloadMeta` 当前实现

源码第 265-277 行：

```javascript
function _buildPayloadMeta(safeOpts) {
    return {
        payload_type: PAYLOAD_TYPES.PARSER_INPUT,
        payload_hash: safeOpts.payloadHash !== undefined ? safeOpts.payloadHash : null,
        captured_at: safeOpts.capturedAt !== undefined ? safeOpts.capturedAt : null,
        data_version: safeOpts.dataVersion !== undefined
            ? (safeOpts.dataVersion === null ? null : String(safeOpts.dataVersion))
            : 'unknown',
        storage_path: safeOpts.storagePath !== undefined ? safeOpts.storagePath : null,
        source_url: null,   // ← 硬编码 null，没有读取 safeOpts.sourceUrl
        final_url: null,    // ← 硬编码 null，没有读取 safeOpts.finalUrl
    };
}
```

**结论：`source_url` 和 `final_url` 被硬编码为 null。`fetched_at` 完全没有出现在 payload 构建中。**

### 2.4 `fetchedAt` 当前处理方式

源码第 279-294 行 `_buildEnvelopeWarnings` 和第 321-352 行主入口：

- `fetchedAt` 被传入 `_buildEnvelopeWarnings` 仅用于判断 warning（第 287 行：`capturedAt === null && fetchedAt === null` 时生成 warning）。
- `fetchedAt` 被传入 `_addExtractedAtField` 仅用于 warning 上下文（第 301-305 行）。
- **`fetchedAt` 从未被写入 `payload` 对象。**

### 2.5 测试确认

`FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js` 第 135-166 行明确验证：

```javascript
// 第 138 行：fetched_at 不在 payload 上
assert.equal(Object.prototype.hasOwnProperty.call(envelope.payload, 'fetched_at'), false);

// 第 159-166 行：source_url/final_url 保持 null
assert.ok(rawRecord.source_url);
assert.ok(rawRecord.final_url);
// Current adapter has no sourceUrl/finalUrl options.
assert.equal(envelope.payload.source_url, null);
assert.equal(envelope.payload.final_url, null);
```

---

## 3. Problem statement

### 3.1 为什么需要扩展

`fetched_at` 是抓取动作发生的时间，不等于 `captured_at`（捕获/持久化时间）。两者语义不同：

- `fetched_at`：HTTP 请求发出并收到响应的时刻。
- `captured_at`：数据快照被确认写入/持久化的时刻，可能和 `fetched_at` 一致也可能不同。

`source_url` 是请求 URL。
`final_url` 是最终 URL（redirect 后的实际请求 URL）。

这三者是 audit / provenance / replay evidence，不是模型特征。如果 envelope 不保存它们：

- 后续 local raw record replay dry-run 的证据链不完整。
- 无法追溯数据来源和抓取时间线。
- 无法验证 replay 使用的是正确的 URL 和时间窗口。

### 3.2 严格语义规则

以下规则不可违反：

- **不允许**用 `_meta.extractedAt` 冒充 `fetched_at`（`extractedAt` 是 parser 执行时间，不是 fetch 时间）。
- **不允许**用 `matchTimeUTC` / `utcTime` 冒充 `fetched_at` 或 `captured_at`（这些是比赛开球时间，不是数据时间）。
- **不允许**用 `parsed_at` 冒充 `fetched_at`（`parsed_at` 是 adapter/parser 处理时间）。
- **缺失证据必须保持 null**，不伪造。

---

## 4. Design decision

### 4.1 推荐设计

本设计推荐以下扩展方案（DATA-L1E-5B 实现，不在本任务中实现）：

1. **`source_url` / `final_url` 不需要新增 schema 字段**。当前 `createEmptyEnvelope` 已定义 `payload.source_url` 和 `payload.final_url`（默认 `null`）。只需要 adapter options handoff。

2. **`fetched_at` 需要 schema extension**。当前 `payload` 对象中没有 `fetched_at` 字段。需要在 `createEmptyEnvelope` 的 `payload` 块中新增 `fetched_at: null`。

3. **让 adapter options 支持 `sourceUrl` / `finalUrl`**，并将它们写入 `payload.source_url` / `payload.final_url`。

4. **让 adapter options 的 `fetchedAt` 不仅用于 warning context，也写入 `payload.fetched_at`**。

5. **保持 `capturedAt` → `payload.captured_at` 不变**。

6. **所有新增 options 保持 optional**。如果 `sourceUrl` / `finalUrl` / `fetchedAt` 缺失，继续为 null。

7. **所有这些字段只允许 audit/provenance/replay**，不允许成为模型字段。

### 4.2 设计不实现

DATA-L1E-5A 不实现该设计。实现留给 DATA-L1E-5B。

---

## 5. Proposed envelope payload contract

### 5.1 目标 payload 结构

```javascript
payload: {
    payload_type: 'parser_input',
    payload_hash: 'sha256:...',
    captured_at: '2026-07-04T01:00:05.000Z',
    data_version: 'fotmob_html_hyd_v1',
    storage_path: null,
    source_url: 'https://example.invalid/fotmob/match/4830507',
    final_url: 'https://example.invalid/fotmob/match/4830507#final',
    fetched_at: '2026-07-04T01:00:00.000Z',   // ← 新增字段
}
```

### 5.2 字段语义

| 字段 | 语义 | 来源 | 可为 null | 可作模型特征 |
| --- | --- | --- | --- | --- |
| `payload_type` | payload 格式类型 | adapter 推断 | No | No |
| `payload_hash` | payload 完整性 hash | `rawRecord.data_hash` 或等价字段 | Yes | No |
| `captured_at` | 数据快照捕获/持久化时间 | `rawRecord.captured_at` | Yes | No |
| `data_version` | 数据版本标识 | `rawRecord.data_version` | No | No |
| `storage_path` | 文件/对象存储路径 | `rawRecord.storage_path` | Yes | No |
| `source_url` | 请求 URL | `rawRecord.source_url` 或 `rawRecord.raw_data._meta.request_url` | Yes | No |
| `final_url` | 最终 URL（redirect 后） | `rawRecord.final_url` 或 `rawRecord.raw_data._meta.final_url` | Yes | No |
| `fetched_at` | 抓取动作发生时间 | `rawRecord.fetched_at` 或 `rawRecord.raw_data._meta.fetched_at` | Yes | No |

### 5.3 模型边界

payload metadata 不是 model field。

payload metadata 不进入 `envelope.fields` 的 `ALLOWED_CANDIDATE`。

payload metadata 不进入 `envelope.fields` 的 `CANDIDATE_IF_CUTOFF_VALID`。

payload metadata 只能用于 audit / replay / provenance / debugging。

---

## 6. Proposed adapter options contract

### 6.1 未来 DATA-L1E-5B 的 options contract

```javascript
adaptTransformToApiFormatOutputToEnvelope(transformOutput, {
    source: 'fotmob',
    dataVersion: rawRecord.data_version ?? 'unknown',
    payloadHash: rawRecord.data_hash ?? rawRecord.payload_hash ?? null,
    storagePath: rawRecord.storage_path ?? null,
    // ↓ 新增 options
    sourceUrl: rawRecord.source_url ?? rawRecord.raw_data?._meta?.request_url ?? null,
    finalUrl: rawRecord.final_url ?? rawRecord.raw_data?._meta?.final_url ?? null,
    fetchedAt: rawRecord.fetched_at ?? rawRecord.raw_data?._meta?.fetched_at ?? null,
    // ↑ 新增 options
    capturedAt: rawRecord.captured_at ?? null,
    parsedAt: null,
    parserName: 'NextDataParser.transformToApiFormat',
    parserVersion: 'legacy-static'
});
```

### 6.2 对应的 `_buildPayloadMeta` 变更

```javascript
function _buildPayloadMeta(safeOpts) {
    return {
        payload_type: PAYLOAD_TYPES.PARSER_INPUT,
        payload_hash: safeOpts.payloadHash !== undefined ? safeOpts.payloadHash : null,
        captured_at: safeOpts.capturedAt !== undefined ? safeOpts.capturedAt : null,
        data_version: safeOpts.dataVersion !== undefined
            ? (safeOpts.dataVersion === null ? null : String(safeOpts.dataVersion))
            : 'unknown',
        storage_path: safeOpts.storagePath !== undefined ? safeOpts.storagePath : null,
        source_url: safeOpts.sourceUrl !== undefined ? safeOpts.sourceUrl : null,   // ← 改为从 options 读取
        final_url: safeOpts.finalUrl !== undefined ? safeOpts.finalUrl : null,      // ← 改为从 options 读取
        fetched_at: safeOpts.fetchedAt !== undefined ? safeOpts.fetchedAt : null,   // ← 新增
    };
}
```

**注意：这是设计示例，不在 DATA-L1E-5A 中实现。**

### 6.3 对应的 `createEmptyEnvelope` schema 变更

```javascript
payload: {
    payload_type: PAYLOAD_TYPES.UNKNOWN,
    payload_hash: null,
    captured_at: null,
    data_version: null,
    storage_path: null,
    source_url: null,      // ← 已有，不变
    final_url: null,       // ← 已有，不变
    fetched_at: null,      // ← 新增
}
```

**注意：这是设计示例，不在 DATA-L1E-5A 中实现。**

---

## 7. Backward compatibility

### 7.1 现有测试

现有 `FotMobParserOutputEnvelopeLegacyAdapter.test.js` 和 fixture test **不会破坏**，因为：

- 旧调用方不传 `sourceUrl` / `finalUrl` / `fetchedAt` 时，这些字段仍为 null（保持当前行为）。
- 旧调用方不传 `fetchedAt` 时，`payload.fetched_at` 为 null，adapter 行为不变。
- `_buildEnvelopeWarnings` 中 `capturedAt === null && fetchedAt === null` 的判断逻辑不变。

### 7.2 现有 fixture

现有 fixture 不需要立即更新。它们使用 null 作为默认值即可。如果未来测试需要覆盖 URL/fetched_at 路径，可以新增 fixture 或扩展已有 fixture，但 DATA-L1E-5B 不应默认修改已有 fixture。

### 7.3 validateEnvelopeShape

`payload.fetched_at` 如果新增为 schema 字段，`validateEnvelopeShape` **不需要更新**：当前校验只检查 `payload` 是否为 object 和 `payload_type` 是否存在（第 301-307 行），不检查具体 payload 字段。

但建议在 DATA-L1E-5B 验证：缺失 `fetched_at`（null）时仍然通过 shape validation。

### 7.4 兼容性总结

| 场景 | 当前行为 | 扩展后行为 | 是否破坏 |
| --- | --- | --- | --- |
| 不传 `sourceUrl` | `source_url = null` | `source_url = null` | No |
| 不传 `finalUrl` | `final_url = null` | `final_url = null` | No |
| 不传 `fetchedAt` | `fetched_at` 不在 payload 上 | `payload.fetched_at = null` | No（null 是合理默认值） |
| 传 `sourceUrl` | 被忽略 | 写入 `payload.source_url` | No（新功能） |
| 传 `finalUrl` | 被忽略 | 写入 `payload.final_url` | No（新功能） |
| 传 `fetchedAt` | 仅 warning context | 写入 `payload.fetched_at` + warning context | No（增强现有功能） |

默认 null，保持 backward compatible。

所有新增 metadata options 都 optional。

不改变已有 field classification。

不改变 0 safe fields 策略。

---

## 8. Testing plan for DATA-L1E-5B

DATA-L1E-5B 实现时应新增或更新以下测试：

1. **Adapter unit test: `sourceUrl` / `finalUrl` options handoff** — 验证 `sourceUrl` → `payload.source_url`，`finalUrl` → `payload.final_url`。
2. **Adapter unit test: `fetchedAt` handoff** — 验证 `fetchedAt` → `payload.fetched_at`。
3. **Adapter unit test: `fetchedAt` 不影响 `captured_at`** — 验证两个字段独立，`fetchedAt` 不覆盖 `capturedAt`。
4. **Metadata handoff fixture test: rawRecord `source_url` / `final_url` / `fetched_at` 能正确进入 envelope** — 扩展或新增 fixture test case。
5. **Missing metadata test: `sourceUrl` / `finalUrl` / `fetchedAt` 缺失时仍为 null** — 验证 minimal raw record 场景。
6. **Safety test: `fetched_at` / `source_url` / `final_url` 不产生 `ALLOWED_CANDIDATE`** — 验证 `assertNoSafeFields` 仍然通过。
7. **Safety test: `fetched_at` / `source_url` / `final_url` 不产生 `CANDIDATE_IF_CUTOFF_VALID`** — 同上。
8. **Regression test: `_meta.extractedAt` 不覆盖 `fetched_at` / `captured_at`** — 验证 audit-only 字段边界。
9. **Regression test: `matchTimeUTC` / `utcTime` 不覆盖 `fetched_at` / `captured_at`** — 验证比赛时间不混入 metadata 时间。
10. **Shape validation test: `payload.fetched_at` 为 null 时通过 shape validation** — 确认 `validateEnvelopeShape` 不拒绝 null。

---

## 9. Allowed files for DATA-L1E-5B

### 9.1 建议允许修改

```text
src/parsers/fotmob/FotMobParserOutputEnvelope.js
src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js
tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.test.js
tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js
docs/data/fotmob_adapter_metadata_extension_implementation.md
```

### 9.2 建议可选修改（仅在测试需要补充字段时）

```text
tests/fixtures/fotmob/metadata_handoff_raw_record_boundary_a_fixture.json
```

默认不建议修改 fixtures，除非测试需要覆盖 URL/fetched_at 路径且当前 fixture 数据不足。

### 9.3 明确禁止 DATA-L1E-5B 修改

```text
src/parsers/fotmob/NextDataParser.js
src/parsers/fotmob/index.js
src/infrastructure/harvesters/strategies/FotMobStrategy.js
src/infrastructure/services/FotMobRawDetailFetcher.js
src/infrastructure/services/RawMatchDataVersionSelector.js
src/feature_engine/**
src/features/**
src/ml/**
src/pipeline/**
src/training/**
src/backtest/**
scripts/**
.github/**
Dockerfile
docker-compose*
migrations/**
data/**
raw/**
models/**
logs/**
```

---

## 10. Risk controls

- 不要伪造 `fetched_at`。
- 不要伪造 `source_url` / `final_url`。
- 不要把 `_meta.extractedAt` 当 `fetched_at`。
- 不要把 `matchTimeUTC` / `utcTime` 当 `fetched_at` / `captured_at`。
- 不要把 `parsed_at` 当 `fetched_at`。
- 不要让 metadata 进入模型特征（保持 `AUDIT_ONLY` / `FORBIDDEN_RAW_ONLY` 语义）。
- 不要改变 field classification。
- 不要引入 runtime import。
- 不要接 production path。
- 缺失 metadata 必须保持 null（missing → null，不伪造）。

---

## 11. Out of scope

以下所有内容均不在 DATA-L1E-5A 范围内：

- **不实现** adapter 修改。
- **不实现** schema 修改。
- **不改** tests。
- **不改** fixtures。
- **不接** runtime。
- **不访问** FotMob 网络。
- **不运行** 采集（scraper / collector / browser）。
- **不写** DB / raw / data。
- **不做** local replay。
- **不做** DATA-L1E-6。
- **不做** DATA-L2。
- **不处理** deep flatten（deep flatten 是独立问题，DATA-L1E-5A 不涉及）。

---

## 12. Open questions

| 问题 | 状态 | 当前答案 |
| --- | --- | --- |
| `payload.fetched_at` 是否应作为 schema 必填但 nullable 字段，还是 optional field？ | **open** | 建议 nullable 必填字段（始终出现在 payload 对象上，但值可为 null），与 `payload_hash` / `captured_at` 等字段风格一致 |
| `source_url` / `final_url` 是否应保留在 `payload`，还是未来 provenance 子对象？ | **open** | 当前已在 `payload` 下，保持现有结构即可；如有更复杂的 provenance 需求，可在未来单独设计 provenance 子对象并迁移 |
| 是否需要同时保留 `request_url` 和 `source_url`，还是统一为 `source_url`？ | **answered** | 统一为 `source_url`。fetcher 侧有 `_meta.request_url`，但在 envelope 层面统一命名为 `source_url`，由 adapter options 做映射 |
| `final_url` 来自 route selector 还是 fetcher metadata？ | **partially answered** | 当前 `FotMobRawDetailFetcher.buildFetchMetadata` 和 `fetchFotMobRawDetail` 都记录 `final_url`；`FotMobDetailRouteSelector` 也返回 `final_url`。adapter 应从 `rawRecord.final_url` 或 `rawRecord.raw_data._meta.final_url` 读取 |
| 是否需要记录 URL sanitizer policy？ | **open** | 建议在 DATA-L1E-5B 实现时记录：URL 中是否移除敏感 query params、是否截断、是否保存完整 URL |
| 是否需要记录 `fetched_at` 的 clock source？ | **open** | 建议在 DATA-L1E-5B 实现时记录：`fetched_at` 的时钟来源（`Date.now()` 还是 `new Date().toISOString()`）、时区（UTC 还是 local） |
| deep flatten 是否应该在 DATA-L1E-5B 之后再单独设计？ | **answered** | 是的。deep flatten 是独立的 adapter gap，与 metadata extension（`fetched_at` / `source_url` / `final_url`）无关，应在 DATA-L1E-5B 之后单独设计 |

---

## 13. Recommended next task

默认推荐：

```text
DATA-L1E-5B: Adapter Metadata Extension Implementation
```

目标：

```text
在不接 runtime 的前提下，让 adapter/envelope 支持 fetched_at / source_url / final_url metadata，
并用现有 fixture test 验证。具体 scope：

1. 在 createEmptyEnvelope 的 payload 中新增 fetched_at: null。
2. 在 _buildPayloadMeta 中支持 sourceUrl / finalUrl / fetchedAt options。
3. 新增 adapter unit test 覆盖 sourceUrl / finalUrl / fetchedAt handoff。
4. 扩展 metadata handoff fixture test 覆盖 source_url / final_url / fetched_at path。
5. 验证 backward compatibility（旧调用不传新 options 时仍然 null）。
6. 验证 0 safe fields 策略不变。
```

Do not start automatically.

Recommended next task only after user confirmation.

---

## 14. What changed

```text
docs/data/fotmob_adapter_metadata_extension_design.md
```

---

## 15. What did not change

- 没有改 adapter
- 没有改 envelope schema
- 没有改 NextDataParser
- 没有改 FotMobStrategy
- 没有改 FotMobRawDetailFetcher
- 没有改 RawMatchDataVersionSelector
- 没有改 index.js
- 没有改 tests
- 没有改 fixtures
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集
- 没有写 DB/raw/data
- 没有改 feature/training/backtest
- 没有启动 DATA-L1E-5B
- 没有启动 DATA-L1E-6
- 没有启动 DATA-L2
