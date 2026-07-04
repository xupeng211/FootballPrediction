# FotMob Local __NEXT_DATA__ Replay Fixture Test

Lifecycle: current-state evidence document for DATA-L1E-9.

## 1. 背景

DATA-L1E-8 已设计 Lane A。DATA-L1E-9 本次实现 Lane A2 fixture test。

A2 使用 sanitized local `__NEXT_DATA__` JSON fixture + local raw record metadata fixture。本任务不实现 A1，不调用 `extractFromHtml`，不处理 HTML，不接 runtime，不访问 FotMob，不写 DB/raw/data，不修改 `src/**`。

## 2. What changed

- `tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_raw_record_fixture.json`
- `tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_next_data_fixture.json`
- `tests/unit/parsers/fotmob/FotMobLocalNextDataReplay.fixture.test.js`
- `docs/data/fotmob_local_nextdata_replay_fixture_test.md`

## 3. Replay lane

This PR implements Lane A2 only.

Lane A2:

```text
sanitized local __NEXT_DATA__ JSON fixture
  -> NextDataParser.transformToApiFormat
  -> adapter
  -> envelope
```

Lane A1 is not implemented.
extractFromHtml is not called.
HTML is not processed.

## 4. Safety guarantees

- No network.
- No browser.
- No scraper / collector.
- No DB read/write.
- No raw/data output write.
- No `src/**` changes.
- No NextDataParser source change.
- No `extractFromHtml` call.
- No HTML fixture.
- No runtime integration.
- No feature/training/backtest.
- No deep flatten.

## 5. Sanitized fixture guarantee

Fixtures are sanitized by construction.

- No real FotMob URL.
- No cookie/token/session/auth header.
- No real user information.
- No browser fingerprint.
- No tracking/analytics/ads/consent payload.
- No complete live FotMob payload.
- All teams/leagues/ids are fixture values.

## 6. Metadata validation

以下 raw record metadata 从 fixture 进入 adapter options，再进入 `envelope.payload`：

- `data_version`
- `payload_hash`
- `storage_path`
- `source_url`
- `final_url`
- `fetched_at`
- `captured_at`

本测试覆盖 `payload_hash` fallback：当 `rawRecord.payload_hash` 为 `null` 时，`envelope.payload.payload_hash` 使用 `rawRecord.data_hash`。

## 7. Time semantics

- `fetched_at` 不等于 `captured_at`。
- `fetched_at` 不等于 `_meta.extractedAt`。
- `fetched_at` 不等于 `matchTimeUTC` / `utcTime`。
- `captured_at` 不等于 `_meta.extractedAt`。
- `captured_at` 不等于 `matchTimeUTC` / `utcTime`。

## 8. Model safety

- 0 `ALLOWED_CANDIDATE`。
- 0 `CANDIDATE_IF_CUTOFF_VALID`。
- `payload.fetched_at` / `payload.source_url` / `payload.final_url` 不进入 `envelope.fields`。
- Local `__NEXT_DATA__` replay output is evidence, not model-ready data。

## 9. Tests

Targeted tests:

```bash
node --test tests/unit/parsers/fotmob/FotMobLocalNextDataReplay.fixture.test.js
node --test tests/unit/parsers/fotmob/FotMobLocalRawRecordReplay.fixture.test.js
node --test tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js
node --test tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js
```

Result: passed locally.

## 10. What did not change

- 没有改 `src/**`
- 没有改 adapter
- 没有改 envelope schema
- 没有改 NextDataParser
- 没有改 FotMobStrategy
- 没有改 FotMobRawDetailFetcher
- 没有改 RawMatchDataVersionSelector
- 没有改 `src/parsers/fotmob/index.js`
- 没有改已有 tests / fixtures
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集
- 没有写 DB/raw/data
- 没有改 feature/training/backtest
- 没有处理 HTML
- 没有调用 `extractFromHtml`
- 没有处理 Lane A1
- 没有处理 deep flatten

## 11. Remaining gaps

- Lane A1 未实现。
- local raw HTML / `extractFromHtml` 未验证。
- deep flatten 仍未处理。
- runtime integration 仍未实现。
- URL sanitizer policy 仍未最终定义。
- `fetched_at` clock source policy 仍未最终定义。

## 12. Recommended next task

默认推荐：

```text
DATA-L1E-10: Local Raw HTML __NEXT_DATA__ Extraction Fixture Test
```

如果不想碰 HTML：

```text
DATA-L1E-7A: URL Sanitizer and Clock Source Policy Design
```

Do not start automatically.

Recommended next task only after user confirmation.
