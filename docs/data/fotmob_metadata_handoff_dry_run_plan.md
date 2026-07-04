# FotMob Metadata Handoff Dry Run Plan

- lifecycle: source-of-truth
- scope: DATA-L1E-4 docs-only metadata handoff dry-run plan
- parent documents: DATA-L1E-2, DATA-L1E-3, DATA-L1F-2B
- runtime behavior change: no

---

## 1. 背景

DATA-L1E-2 已实现 dry-run adapter：`src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js`。

DATA-L1E-3 已用 static fixtures 证明 adapter 可以处理 richer/minimal `NextDataParser.transformToApiFormat` output，并保持 0 safe fields。

但 adapter 的 options metadata 仍然依赖调用方提供。当前 adapter 不主动读取 `FotMobRawDetailFetcher`、`raw_match_data`、`RawMatchDataVersionSelector` 或 DB。因此 DATA-L1E-4 只设计 metadata 从旧 FotMob raw/fetcher/storage/version-selector 侧传到 adapter options 的方式。

本任务 docs-only，不接 runtime、不改 adapter、不访问 FotMob、不写 DB/raw/data。

## 2. 当前 adapter options 入口

静态审计文件：`src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js`。

| 字段名 | 当前 adapter 中的位置 | 进入 envelope 后的位置 | 默认值 | 是否允许 null | 是否会被伪造 | 风险 |
| --- | --- | --- | --- | --- | --- | --- |
| `source` | `adaptTransformToApiFormatOutputToEnvelope` 调用 `createEmptyEnvelope` 时读取 `safeOpts.source` | `envelope.source` | `'fotmob'` | 不建议传 null | No | 只能标识来源，不证明 capture route |
| `dataVersion` | `_buildPayloadMeta(safeOpts)` | `payload.data_version` | `'unknown'` | Yes，显式传 null 会保留 null | No | `'unknown'` 表示 canonical version 未确认 |
| `payloadHash` | `_buildPayloadMeta(safeOpts)` | `payload.payload_hash` | `null` | Yes | No | hash strategy 不一致会导致不可比较 |
| `storagePath` | `_buildPayloadMeta(safeOpts)` | `payload.storage_path` | `null` | Yes | No | 当前 raw DB row 不稳定提供 file path |
| `capturedAt` | `_buildPayloadMeta(safeOpts)` | `payload.captured_at` | `null` | Yes | No | 不得由 `fetchedAt`、`parsedAt` 或 `_meta.extractedAt` 自动冒充 |
| `fetchedAt` | `_buildEnvelopeWarnings` 和 `_addExtractedAtField` 的 warning context | 不进入当前 envelope schema | `null` | Yes | No | 当前 adapter 只用它区分 warning，不保存为 payload 字段 |
| `parsedAt` | `createEmptyEnvelope({ parser })` | `parser.parsed_at` | `null` | Yes | No | parser dry-run 时间和 fetch/capture 时间不能混用 |
| `parserName` | `createEmptyEnvelope({ parser })` | `parser.parser_name` | `'NextDataParser.transformToApiFormat'` | 不建议传 null | No | 只能描述 boundary，不证明真实 runtime parser |
| `parserVersion` | `createEmptyEnvelope({ parser })` | `parser.parser_version` | `'legacy-static'` | 不建议传 null | No | 静态 adapter 版本标签，不等于 production parser release |

当前 adapter 的 `payload.source_url` 和 `payload.final_url` 固定为 `null`，没有 `sourceUrl` / `finalUrl` options。未来如果需要把 URL 进入 envelope，需要单独 adapter code change；DATA-L1E-4 不实现。

_missing metadata must stay null / unknown._

## 3. Raw/fetcher metadata inventory

静态审计文件：

- `src/infrastructure/services/FotMobRawDetailFetcher.js`
- `src/infrastructure/services/RawMatchDataVersionSelector.js`
- `src/infrastructure/harvesters/strategies/FotMobStrategy.js`
- 只读参考：`src/infrastructure/harvesters/components/Persistence.js`

| metadata | 是否找到明确来源 | 来源文件/函数 | 当前字段名 | 目标 adapter options 字段名 | 可信度 | 是否可用于 envelope | 是否可用于模型字段 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `data_version` / `dataVersion` | Yes | `FotMobRawDetailFetcher.validateFetchInput`, `buildFetchMetadata`; `RawMatchDataVersionSelector` | input `dataVersion`, `_meta.data_version`, row `data_version` | `dataVersion` | confirmed | Yes, maps to `payload.data_version` | No, audit/version selection only |
| `data_hash` / `payload_hash` / hash | Yes for `data_hash`; no `payload_hash` name in fetcher | `computeRawDetailHashes`, `buildFetchMetadata`, `fetchFotMobRawDetail` | `data_hash`, `raw_data_hash`, `stable_raw_payload_hash` | `payloadHash` | confirmed | Yes, prefer canonical `data_hash` / `raw_data_hash` with hash strategy noted | No, audit/integrity only |
| `fetched_at` / `fetchedAt` | Yes | `fetchFotMobRawDetail` sets `fetchedAt = now()`; `buildFetchMetadata` writes `_meta.fetched_at` | `_meta.fetched_at` | `fetchedAt` | confirmed | Yes as warning/context only in current adapter | No, timing audit only |
| `captured_at` / `capturedAt` | No stable source found | Not present in audited fetcher output or selector | missing; DB has `collected_at`, not `captured_at` | `capturedAt` | missing | Keep null unless a future caller has explicit capture timestamp | No |
| `storage_path` / `storagePath` | Not in canonical fetcher raw result | Legacy `Persistence.saveToFile` returns `filePath`, but raw DB path is not stable | `filePath` in legacy file save; no raw row `storage_path` | `storagePath` | unknown | Keep null unless local fixture/raw-record pair explicitly has a path | No |
| `source_url` / `sourceUrl` | Partially, as request URL | `FotMobRawDetailFetcher.buildFetchMetadata`, `fetchFotMobRawDetail`; source inventory docs/manifests use `source_url` | `_meta.request_url`, top-level `request_url`; not named `source_url` | no current adapter option | inferred | Current adapter cannot store it; future `sourceUrl` option required | No |
| `final_url` / `finalUrl` | Yes | `FotMobRawDetailFetcher.buildFetchMetadata`, `fetchFotMobRawDetail`; `FotMobDetailRouteSelector` also returns `final_url` | `_meta.final_url`, top-level `final_url` | no current adapter option | confirmed | Current adapter cannot store it; future `finalUrl` option required | No |
| `match_id` / `matchId` | Yes | `normalizeMatchId`, `buildStableRawPayload`, `buildRawDataFromStablePayload`; selector rows | `matchId`, `match_id`, row `match_id` | transform output `matchId`, not options | confirmed | Yes, adapter requires transform output `matchId` and emits `envelope.match_id` | No, join/filter only |
| `parser_name` | Yes, but inferred from boundary | `FotMobRawDetailFetcher.buildFetchMetadata` stores `_meta.parser = 'NextDataParser'`; adapter default uses full function name | `_meta.parser`, default parser name | `parserName` | confirmed/inferred | Yes | No |
| `parser_version` | No stable runtime source found for this boundary | Adapter default only | `legacy-static` default | `parserVersion` | missing | Use dry-run label only until real parser version exists | No |
| `parsed_at` / `parsedAt` | No stable source for dry-run | Adapter option only; `NextDataParser.transformToApiFormat` has `_meta.extractedAt` | `parsedAt` option | `parsedAt` | missing | Keep null unless the dry-run invocation explicitly records parser execution time | No |
| `_meta.extractedAt` | Yes | `NextDataParser.transformToApiFormat` | `_meta.extractedAt` | not an option; adapter adds field entry | confirmed | Yes, audit-only field | No |
| `matchTimeUTC` / `utcTime` | Yes in transform output examples | `NextDataParser.transformToApiFormat` output `general` / `header` blocks | `general.matchTimeUTC`, `header.status.utcTime` | none | confirmed | As raw/audit field only under current adapter | No by default; not capture timing |

Raw storage note: current DB/storage evidence commonly exposes `match_id`, `external_id`, `raw_data`, `collected_at`, `data_version`, and sometimes `data_hash`. It does not prove a stable `storage_path`, separate `fetched_at`, or separate `captured_at` column. `collected_at` is storage/write time, not automatically `captured_at`.

## 4. 时间字段语义区分

| 字段 | 语义 | 当前结论 |
| --- | --- | --- |
| `fetched_at` / `fetchedAt` | 抓取动作发生的时间 | `FotMobRawDetailFetcher` 明确生成 `_meta.fetched_at`，可作为 fetch action evidence |
| `captured_at` / `capturedAt` | 数据快照被确认捕获的时间，可能和 `fetched_at` 一致，也可能不同 | 当前审计未找到稳定字段；没有真实 capture evidence 时保持 null |
| `parsed_at` / `parsedAt` | adapter/parser 处理数据的时间 | 当前 adapter 默认 null；只有明确记录 parser dry-run execution time 时才可传 |
| `_meta.extractedAt` | 旧 `NextDataParser.transformToApiFormat` 自己记录的处理时间 | 只能作为 audit-only，不能冒充 fetch/capture time |
| `matchTimeUTC` / `utcTime` | 比赛开球时间 | 这是 fixture/kickoff time，不是数据抓取时间 |

规则：

- 不要用 `extractedAt` 覆盖 `fetched_at`。
- 不要用 `extractedAt` 覆盖 `captured_at`。
- 不要用 `matchTimeUTC` 当 `captured_at`。
- 不要用 `parsed_at` 当 `fetched_at`。
- 如果没有真实抓取时间，保持 null。
- 如果只有 DB `collected_at`，必须标注为 storage/write timestamp；除非 writer contract 证明它等同 capture time，否则不要自动映射到 `capturedAt`。

## 5. Recommended handoff contract

未来 dry-run 可以使用一个显式 metadata sidecar，把 raw record / fetcher result / selector row 的证据传给 adapter。以下只是设计，不要在本 PR 中实现，不要把这段代码接到 runtime。

```javascript
const envelope = adaptTransformToApiFormatOutputToEnvelope(transformOutput, {
  source: 'fotmob',
  dataVersion: rawRecord.data_version ?? rawRecord.raw_data?._meta?.data_version ?? 'unknown',
  payloadHash:
    rawRecord.data_hash
    ?? rawRecord.payload_hash
    ?? rawRecord.raw_data_hash
    ?? rawRecord.raw_data?._meta?.data_hash
    ?? null,
  storagePath: rawRecord.storage_path ?? null,
  capturedAt: rawRecord.captured_at ?? null,
  fetchedAt: rawRecord.fetched_at ?? rawRecord.raw_data?._meta?.fetched_at ?? null,
  parsedAt: null,
  parserName: 'NextDataParser.transformToApiFormat',
  parserVersion: 'legacy-static'
});
```

URL handoff 的当前结论：

```javascript
// Future adapter extension only. DATA-L1E-4 does not implement this.
{
  sourceUrl: rawRecord.source_url ?? rawRecord.raw_data?._meta?.request_url ?? null,
  finalUrl: rawRecord.final_url ?? rawRecord.raw_data?._meta?.final_url ?? null
}
```

Implementation required later. DATA-L1E-4 remains docs-only.

## 6. Field mapping table

| Source side field | Source meaning | Adapter option | Envelope target | Default if missing | Can be fabricated? | Can be model feature? | Risk note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `data_version` | raw payload version / selector version | `dataVersion` | `payload.data_version` | `'unknown'` or explicit null | No | No, audit only | Unknown version must not be treated canonical |
| `data_hash` / `payload_hash` | stable payload integrity hash | `payloadHash` | `payload.payload_hash` | `null` | No | No, audit only | Must preserve hash strategy |
| `storage_path` | file/object storage location | `storagePath` | `payload.storage_path` | `null` | No | No, audit only | Current raw DB row may not have this |
| `fetched_at` | fetch action timestamp | `fetchedAt` | current adapter warning context only | `null` | No | No, audit only | Not persisted by current envelope schema |
| `captured_at` | confirmed payload capture timestamp | `capturedAt` | `payload.captured_at` | `null` | No | No, audit only | Missing must stay null |
| `parsed_at` | parser/adapter processing timestamp | `parsedAt` | `parser.parsed_at` | `null` | No | No, audit only | Do not reuse fetch/capture time |
| `source_url` / `_meta.request_url` | requested source URL | no current option | currently `payload.source_url = null` | `null` | No | No, audit only | Future adapter option required |
| `final_url` / `_meta.final_url` | redirect-final URL | no current option | currently `payload.final_url = null` | `null` | No | No, audit only | Future adapter option required |
| `match_id` / `matchId` | match identity / join key | transform output `matchId` | `envelope.match_id`; field `matchId` | adapter throws if missing | No | No, join/filter only | Can join data, not predict outcome |
| `_meta.extractedAt` | transform processing time | none | audit-only field entry | absent if missing | No | No, audit only | Never fetch/capture evidence |
| `matchTimeUTC` / `utcTime` | kickoff time | none | raw block only in current adapter | raw/null | No | No under current adapter | Kickoff time is not capture time |

## 7. Dry-run implementation boundary

Future work must remain phased:

| Phase | Scope | Boundary |
| --- | --- | --- |
| Phase A | docs-only handoff plan | 当前 DATA-L1E-4 |
| Phase B | fixture-level metadata handoff test | 使用 static fixture/raw-record pair，不接 runtime |
| Phase C | dry-run script or test using local fixture/raw record | 不写 DB，不访问 FotMob |
| Phase D | user review before any runtime integration | 用户确认前不接 production path |

No runtime integration in DATA-L1E-4.

No adapter code change in DATA-L1E-4.

No DB write in DATA-L1E-4.

No FotMob network access in DATA-L1E-4.

## 8. Risk controls

- 不要伪造 metadata。
- 不要把比赛时间当抓取时间。
- 不要把 parser `extractedAt` 当真实抓取时间。
- 不要把 `parsed_at` 当 `fetched_at`。
- 不要把 DB `collected_at` 自动当 `captured_at`，除非 writer contract 明确证明。
- 不要把 raw block 当模型字段。
- unknown timing 默认 forbidden。
- metadata 只做 audit/join/filter/version selection，不做 model feature。
- `source_url` / `final_url` 当前 adapter 不能保存；缺失或未实现时必须保持 null。
- deep flatten 仍是单独问题，不在 DATA-L1E-4 解决。

## 9. Open questions

| 问题 | 状态 | 当前答案 |
| --- | --- | --- |
| 真实 raw record 里 `data_version` 字段名是否稳定？ | answered static | selector、fetcher、storage paths 都使用 `data_version` / `dataVersion`，但真实 DB 分布未查 |
| 真实 raw record 里 `data_hash` / `payload_hash` 哪个才是 canonical？ | partially answered | 当前 fetcher和 raw storage 更明确的是 `data_hash` / `raw_data_hash`；`payload_hash` 是 envelope 命名 |
| `fetched_at` 和 `captured_at` 是否同时存在？ | open | fetcher 有 `_meta.fetched_at`；未找到稳定 `captured_at` |
| `storage_path` 是否一直可用？ | open | canonical fetcher/DB row 未确认稳定提供；legacy file save 有 `filePath` 但不是当前 dry-run boundary |
| `FotMobRawDetailFetcher` 是否已经稳定返回 `source_url` / `final_url`？ | partially answered | 返回 `request_url` / `final_url`，但不是 `source_url` 命名；adapter 当前无法保存 |
| 当前 production scheduler 是否保存这些 metadata？ | open | `Persistence.saveToDatabase` 保存 `raw_data/collected_at/data_version/external_id`；是否保存 fetcher `_meta` 取决于调用方 raw_data 内容，本任务不查 DB |
| feature engine 未来是否消费 envelope，还是继续 SQL 读 `raw_match_data`？ | open | 当前审计没有发现 feature engine 消费 envelope；未来需要单独任务确认 |

## 10. What changed

- `docs/data/fotmob_metadata_handoff_dry_run_plan.md`

## 11. What did not change

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

## 12. Recommended next task

默认推荐：

```text
DATA-L1E-5: Metadata Handoff Fixture Test
```

下一步可以用静态 fixture/raw-record pair 验证 metadata options 能不能正确传给 adapter，但仍然不接 runtime。

如果用户优先处理 nested high-risk field flattening，也可以改为：

```text
DATA-L1E-3A: Deep Flatten Coverage Design
```

Do not start automatically.

Recommended next task only after user confirmation.
