# FotMob Fixture-Based Envelope Dry Run Evidence

- lifecycle: source-of-truth
- scope: fixture-based dry-run evidence for DATA-L1E-3
- parent documents: DATA-L1E-2 (`docs/data/fotmob_parser_output_envelope_legacy_adapter_dry_run.md`)
- branch: `test/data-l1e-3-fotmob-envelope-fixture-dry-run-evidence`

---

## 1. 背景

DATA-L1E-2 已实现 dry-run-only adapter：`FotMobParserOutputEnvelopeLegacyAdapter.js`。

DATA-L1E-3 使用静态 fixture 验证 adapter 对更像真实 `transformToApiFormat` 输出的兼容性。本任务仍然不接 runtime、不访问 FotMob、不写 DB/raw/data、不进 feature/training/backtest。

**FotMobParserOutputEnvelopeLegacyAdapter.js was not modified in DATA-L1E-3.**

---

## 2. Fixture source

fixtures 是 static representative `NextDataParser.transformToApiFormat` output——不是 HTML，不是 `__NEXT_DATA__` 原始页面，不是本任务现场抓取 FotMob 生成，不包含 cookie/token/secret。

| fixture | 文件 | 用途 |
| --- | --- | --- |
| Rich | `tests/fixtures/fotmob/nextdata_transform_output_boundary_a_rich_fixture.json` | 模拟包含完整 stats/lineup/shotmap/events/playerStats/momentum/form/table 的输出 |
| Minimal | `tests/fixtures/fotmob/nextdata_transform_output_boundary_a_minimal_fixture.json` | 模拟只有 matchId + team name + status 的最简输出 |

---

## 3. Evidence test

| 文件 | 测试数 |
| --- | --- |
| `tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js` | 27 tests |

测试覆盖：
- rich fixture envelope shape 验证
- minimal fixture envelope shape 验证
- postmatch 字段 forbidden 验证
- unknown timing 字段 forbidden 验证
- raw block 不能作为模型字段
- 不产生任何 `ALLOWED_CANDIDATE` / `CANDIDATE_IF_CUTOFF_VALID` 字段
- metadata options 保留验证
- `_meta.extractedAt` 不覆盖 `captured_at` 验证

所有 27 个 fixture 测试通过。现有 57 个 adapter 测试也继续通过（84 个测试全部 green）。

---

## 4. Findings

### 4.1 Rich fixture

- **envelope shape**: 通过 `validateEnvelopeShape`
- **postmatch 字段 forbidden**:
  - `content.stats` → `FORBIDDEN_POSTMATCH` ✓
  - `content.shotmap` → `FORBIDDEN_POSTMATCH` ✓
  - `content.events` → `FORBIDDEN_POSTMATCH` ✓
- **unknown timing 字段 forbidden**:
  - `content.lineup` → `FORBIDDEN_UNKNOWN_TIMING` ✓
- **raw blocks forbidden**:
  - `content` → `FORBIDDEN_RAW_ONLY` ✓
  - `general` → `FORBIDDEN_RAW_ONLY` ✓
  - `header` → `FORBIDDEN_RAW_ONLY` ✓
- **metadata**:
  - `matchId` 正确保留 ✓
  - `_meta.source` / `_meta.hasStats` / `_meta.hasLineup` / `_meta.hasShotmap` 均存在且 audit_only ✓
  - `_meta.extractedAt` 作为 audit_only 保留，warnings 正确 ✓
- **no safe fields**: 0 个 `ALLOWED_CANDIDATE`，0 个 `CANDIDATE_IF_CUTOFF_VALID` ✓

### 4.2 Rich fixture with options metadata

- `data_version: 'fotmob_html_hyd_v1'` 被保留 ✓
- `payload_hash: 'fixture-hash-001'` 被保留 ✓
- `storage_path: null` 被保留 ✓
- `captured_at` 被保留 ✓
- `parsed_at: null` 被保留 ✓
- `_meta.extractedAt` 仍只是 audit field，不覆盖 `captured_at` ✓

### 4.3 Minimal fixture

- **envelope shape**: 通过 `validateEnvelopeShape` ✓
- **payload metadata**: 全部 default/null ✓
- **no safe fields**: 0 个 `ALLOWED_CANDIDATE`，0 个 `CANDIDATE_IF_CUTOFF_VALID` ✓
- **empty content**: 不崩溃，不产生虚假的 stats/lineup/shotmap entries ✓
- **missing extractedAt**: 不伪造 ✓

---

## 5. Gaps

以下字段存在于 rich fixture 中，但当前 adapter 未单独 flatten。它们的值包含在 `content` raw block（`FORBIDDEN_RAW_ONLY`）或 `general`/`header` raw blocks 中，未被暴露为独立 field entry：

| 未单独 flatten 的字段路径 | 位置 | 状态 |
| --- | --- | --- |
| `content.playerStats` | rich fixture | 在 `content` raw block 中（`FORBIDDEN_RAW_ONLY`），未被单独 flatten |
| `content.momentum` | rich fixture | 同上 |
| `content.form` | rich fixture | 同上 |
| `content.table` | rich fixture | 同上 |
| `header.teams[*].score` | rich fixture | 在 `header` raw block 中（`FORBIDDEN_RAW_ONLY`），未被单独 flatten |
| `header.status.scoreStr` | rich fixture | 同上 |
| `header.status.winner` | rich fixture | 同上 |

**风险评估**：这些字段因被包裹在 `content`/`header` raw blocks 中（均标记 `FORBIDDEN_RAW_ONLY`），不会被模型消费。风险由 parent block 的 forbidden 标签控制，不需要 adapter 单独展开。

如果需要深度展开这些字段（例如将 `playerStats` 标记为 `FORBIDDEN_POSTMATCH`），应在后续单独授权的深展任务中进行。

其他 gaps（与 DATA-L1E-2 相同的通用 gaps）：

- 没有运行真实 FotMob parser
- 没有访问真实 FotMob
- 没有验证 DB 中所有 raw_match_data
- 没有验证 production scheduler
- 没有验证 feature engine 消费 envelope

---

## 6. What changed

| 文件 | 操作 |
| --- | --- |
| `tests/fixtures/fotmob/nextdata_transform_output_boundary_a_rich_fixture.json` | 新增 |
| `tests/fixtures/fotmob/nextdata_transform_output_boundary_a_minimal_fixture.json` | 新增 |
| `tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js` | 新增 |
| `docs/data/fotmob_fixture_based_envelope_dry_run_evidence.md` | 新增（本文档） |

---

## 7. What did not change

- 没有改 `FotMobParserOutputEnvelopeLegacyAdapter.js` ⬅ **adapter unchanged**
- 没有改 `FotMobParserOutputEnvelope.js`
- 没有改 `NextDataParser.js`
- 没有改 `FotMobStrategy.js`
- 没有改 `FotMobRawDetailFetcher.js`
- 没有改 `src/parsers/fotmob/index.js`
- 没有接 runtime
- 没有访问 FotMob 网络
- 没有运行采集
- 没有写 DB/raw/data
- 没有改 feature/training/backtest

---

## 8. Next recommended task

推荐：

```text
DATA-L1E-4: Metadata Handoff Dry-Run Plan
```

DATA-L1E-4 应该：
1. 确认 FotMobRawDetailFetcher 产出的 metadata（`data_version`/`data_hash`/`fetched_at`）如何传递到 adapter 的 options 参数。
2. 设计 metadata handoff 的调用链（fetcher → adapter），但仍然 dry-run。
3. 不修改 runtime。

如果用户认为 deep-flatten 未覆盖字段的优先级更高，也可以先做：

```text
DATA-L1E-3A: Deep Flatten Coverage Design
```

**Do not start automatically.**

**Recommended next task only after user confirmation.**
