# FotMob Metadata Handoff Fixture Test

- lifecycle: source-of-truth
- scope: DATA-L1E-5 fixture-level metadata handoff test
- parent document: `docs/data/fotmob_metadata_handoff_dry_run_plan.md`
- runtime behavior change: no

---

## 1. 背景

DATA-L1E-4 已完成 metadata handoff dry-run plan。

DATA-L1E-5 使用 static raw-record fixture + `transformToApiFormat` output fixture 验证 metadata options handoff。

本任务不改 adapter、不接 runtime、不访问 FotMob、不写 DB/raw/data。

## 2. Fixtures

本 PR 新增两个 fixture：

- `tests/fixtures/fotmob/metadata_handoff_raw_record_boundary_a_fixture.json`
- `tests/fixtures/fotmob/metadata_handoff_transform_output_boundary_a_fixture.json`

这些是 sanitized representative fixtures。

它们不是 HTML。

它们不是 `__NEXT_DATA__` 原始页面。

它们不是本任务现场抓取 FotMob 生成。

它们不包含 cookie/token/secret。

## 3. Handoff helper

测试文件内定义 local helper：

```text
buildAdapterOptionsFromRawRecord(rawRecord)
```

这个 helper 只存在于 test 文件中。

没有进入 `src`。

没有被 runtime import。

不是 production integration。

它只表达 DATA-L1E-4 文档中的 fixture-level dry-run handoff contract。

## 4. Verified mapping

| Source | Adapter option | Envelope / result | 结论 |
| --- | --- | --- | --- |
| `rawRecord.data_version` | `options.dataVersion` | `envelope.payload.data_version` | verified |
| `rawRecord.data_hash` | `options.payloadHash` | `envelope.payload.payload_hash` | verified, priority over fallback hashes |
| `rawRecord.storage_path` | `options.storagePath` | `envelope.payload.storage_path` | missing stays null |
| `rawRecord.captured_at` | `options.capturedAt` | `envelope.payload.captured_at` | verified |
| `rawRecord.fetched_at` | `options.fetchedAt` | warning/context only, not payload field | verified |
| `transformOutput._meta.extractedAt` | no option | audit-only field | verified |
| `transformOutput.general.matchTimeUTC` | no option | raw block only, not `captured_at` | verified |
| `transformOutput.header.status.utcTime` | no option | raw block only, not `captured_at` | verified |
| `rawRecord.source_url/final_url` | no current option | `envelope.payload.source_url/final_url` remain null | verified |

## 5. Findings

metadata handoff fixture test passed。

`data_version` 被正确保留。

`payload_hash` 优先选择 `rawRecord.data_hash`。

`captured_at` 被正确保留。

`fetched_at` 没有冒充 `captured_at`。

`_meta.extractedAt` 没有覆盖 `captured_at`。

`matchTimeUTC` / `utcTime` 没有被当作 `captured_at`。

`source_url` / `final_url` 当前 adapter 不支持，保持 null。

缺失 metadata 保持 null / unknown。

没有产生 `ALLOWED_CANDIDATE`。

没有产生 `CANDIDATE_IF_CUTOFF_VALID`。

postmatch / unknown timing 字段仍然 forbidden。

## 6. Confirmed adapter gaps

Current adapter does not persist `fetched_at` as payload field.

Current adapter does not support `sourceUrl`/`finalUrl` options.

Current adapter does not deep-flatten every nested FotMob field.

These are not fixed in DATA-L1E-5.

Future adapter extension requires separate authorization.

Current adapter gap confirmed. Future adapter extension requires separate authorization.

## 7. What changed

- `tests/fixtures/fotmob/metadata_handoff_raw_record_boundary_a_fixture.json`
- `tests/fixtures/fotmob/metadata_handoff_transform_output_boundary_a_fixture.json`
- `tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js`
- `docs/data/fotmob_metadata_handoff_fixture_test.md`

## 8. What did not change

- 没有改 adapter
- 没有改 envelope schema
- 没有改 NextDataParser
- 没有改 FotMobStrategy
- 没有改 FotMobRawDetailFetcher
- 没有改 RawMatchDataVersionSelector
- 没有改 index.js
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集
- 没有写 DB/raw/data
- 没有改 feature/training/backtest
- 没有启动 DATA-L2

## 9. Recommended next task

默认推荐：

```text
DATA-L1E-6: Local Raw Record Replay Dry-Run Design
```

下一步可以设计一个本地 raw record replay dry-run，但仍然不接 production runtime、不访问 FotMob、不写 DB。

如果用户优先处理 adapter metadata gap，也可以改为：

```text
DATA-L1E-5A: Adapter Metadata Extension Design
```

Do not start automatically.

Recommended next task only after user confirmation.
