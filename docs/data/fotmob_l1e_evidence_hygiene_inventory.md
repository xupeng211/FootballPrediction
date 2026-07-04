# FotMob L1E Evidence Hygiene Inventory

**Task**: DATA-L1E-HYGIENE-1
**Date**: 2026-07-05
**Lifecycle**: current-state
**Scope**: docs-only / evidence hygiene inventory / no deletion / no move / no rename / no runtime behavior change
**Branch**: `docs/data-l1e-hygiene-1-fotmob-evidence-inventory`

---

## 1. 背景

DATA-L1E-1 到 DATA-L1E-9 为了安全推进 FotMob parser/envelope/replay 证据链，新增了多份 docs、fixtures、tests。

这些文件短期有价值，因为它们降低了以下风险：

- **postmatch leakage**：通过 envelope + model_eligibility 标签，赛后字段不再可能无声进入模型；
- **metadata 混淆**：通过 metadata handoff，`extractedAt` / `source` / `hasStats` 等元数据不再丢失或混用；
- **runtime 误接入**：所有 replay 证据都是 test-only，不接 runtime、不接 scraper、不接 browser；
- **真实网络误访问**：fixture-based 回放不访问 FotMob 网络，纯本地 JSON 回放；
- **0 safe fields 被破坏**：assertNoSafeFields 保护赛前安全字段 contract 不退化。

但如果继续每一步都新增 current-state doc、fixture、test，项目会出现：

- **文档蔓延 (document sprawl)**：DATA-L1E-10 之后的文档与已有文档重叠度上升；
- **权威不清 (canonical ambiguity)**：后续 AI agent 可能误读历史 phase evidence 为当前指令；
- **helper 重复**：`buildAdapterOptionsFromRawRecord`、`fieldByPath`、`readJsonFixture` 等 helper 在 3+ 个 test 文件中各自重复定义；
- **fixture 命名和数量膨胀**：每个 lane/phase 都新增 fixture pair，长期难维护。

**DATA-L1E-HYGIENE-1 本次只做 inventory，不删除、不移动、不重命名、不修改代码、不修改测试、不修改 fixture。**

---

## 2. Scope

```text
This is an inventory-only PR.

It does not delete files.
It does not move files.
It does not rename files.
It does not modify src/**.
It does not modify tests/**.
It does not modify tests/fixtures/**.
It does not run parser/replay/runtime.
It does not access FotMob.
It does not write DB/raw/data.
It does not start DATA-L1E-10.
```

---

## 3. Current DATA-L1E chain summary

### 3.1 Foundation (pre-DATA-L1E)

| Task | PR / Commit | Primary files | Purpose | Current classification |
| --- | --- | --- | --- | --- |
| DATA-L1A | #1694 / b09f6d9 | `docs/_reports/data_l1a_fotmob_prematch_boundary_audit.md` | FotMob 赛前/赛后字段边界风险发现 | historical phase evidence |
| DATA-L1B | #1695 / 1de44bb | `docs/data/fotmob_prematch_field_contract.md` | 5 类字段合同定义 | canonical source-of-truth |
| DATA-L1C | #1696 / a6f905d | `docs/data/fotmob_raw_payload_retention_replay_policy.md` | raw payload 保留与回放策略 | canonical source-of-truth |
| DATA-L1D | #1697 / c9b9da9 | `docs/data/fotmob_parser_field_provenance_timing_labels_design.md` | parser 字段来源与时间标签设计 | canonical source-of-truth |
| DATA-L1E | #1698 / 1729b4f | `docs/data/fotmob_parser_output_envelope_implementation_plan.md` | envelope 分阶段落地实现计划 | canonical source-of-truth |
| DATA-L1F | #1700 / 7c08feb | `docs/data/fotmob_existing_pipeline_triage_canonical_path.md` | 现有 FotMob pipeline 主线筛选 | canonical source-of-truth |
| DATA-L1F-1 | #1701 / 9234c5b | `docs/data/fotmob_canonical_pipeline_verification_plan.md` | canonical pipeline verification | implementation note |
| DATA-L1F-2A | #1702 / 5e6665d | `docs/data/fotmob_canonical_import_graph_verification.md` | canonical import graph verification | implementation note |
| DATA-L1F-2B | #1703 / c4b28a6 | `docs/data/fotmob_nextdata_thin_parsers_output_shape_audit.md` | NextDataParser + thin parsers 输出形态审计 | current-state evidence |

### 3.2 DATA-L1E implementation chain

| Task | PR / Commit | Primary files | Purpose | Current classification | Keep / consolidate later / archive later |
| --- | --- | --- | --- | --- | --- |
| DATA-L1E-1 | #1699 / a06c0a0 | `src/parsers/fotmob/FotMobParserOutputEnvelope.js` | envelope schema (永久性代码) | canonical source-of-truth (code) | Keep |
| DATA-L1E-2 | #1705 / f2ecedb | `src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js`, `docs/data/fotmob_parser_output_envelope_legacy_adapter_dry_run.md`, `tests/.../FotMobParserOutputEnvelopeLegacyAdapter.test.js` | legacy adapter dry-run 实现 + 文档 + 单元测试 | canonical source-of-truth (code) / current-state evidence (doc) | Keep |
| DATA-L1E-3 | #1707 / ed06108 | `docs/data/fotmob_fixture_based_envelope_dry_run_evidence.md`, `tests/fixtures/fotmob/nextdata_transform_output_boundary_a_*`, `tests/.../FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js` | static fixture 验证 adapter 兼容性 | current-state evidence | Keep; fixture 可未来 consolidation |
| DATA-L1E-4 | fc08b08 | `docs/data/fotmob_metadata_handoff_dry_run_plan.md` | metadata handoff 设计计划 | current-state evidence | Keep; 可未来合并入 canonical doc |
| DATA-L1E-5 | acd7728 | `docs/data/fotmob_metadata_handoff_fixture_test.md`, `tests/fixtures/fotmob/metadata_handoff_*`, `tests/.../FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js` | metadata handoff fixture test 证据 | current-state evidence | Keep; helper 可未来提取 |
| DATA-L1E-5A | #1710 / 7f872ad | `docs/data/fotmob_adapter_metadata_extension_design.md` | adapter metadata extension 设计 | current-state evidence | Keep; 可未来合并入 canonical doc |
| DATA-L1E-5B | #1711 / 26a871a | `docs/data/fotmob_adapter_metadata_extension_implementation.md` | adapter metadata extension 实现记录 | implementation note | Keep; 记录已合入 adapter code |
| DATA-L1E-6 | #1712 / a03288d | `docs/data/fotmob_local_raw_record_replay_dry_run_design.md` | local raw record replay 设计 (Lane B 蓝图) | current-state evidence | Keep |
| DATA-L1E-7 | #1713 / 5c008e1 | `docs/data/fotmob_local_raw_record_replay_fixture_test.md`, `tests/fixtures/fotmob/local_raw_record_replay_boundary_b_*`, `tests/.../FotMobLocalRawRecordReplay.fixture.test.js` | Lane B local raw record replay fixture test | current-state evidence | Keep; fixture 可未来 consolidation |
| DATA-L1E-8 | #1714 / bc23211 | `docs/data/fotmob_local_raw_html_nextdata_replay_design.md` | Lane A raw HTML / \_\_NEXT_DATA\_\_ replay 设计 | current-state evidence; 最长的设计文档 (845 lines) | Keep; 包含大量复用讨论 |
| DATA-L1E-9 | #1715 / 6418d26 | `docs/data/fotmob_local_nextdata_replay_fixture_test.md`, `tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_*`, `tests/.../FotMobLocalNextDataReplay.fixture.test.js` | Lane A2 \_\_NEXT_DATA\_\_ replay fixture test | current-state evidence | Keep; fixture 可未来 consolidation |

---

## 4. Canonical runtime boundary

### 4.1 Canonical code files (永久性、runtime 会直接/间接依赖的)

```text
src/parsers/fotmob/FotMobParserOutputEnvelope.js          — envelope schema, field contract, MODEL_ELIGIBILITY
src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js — transformToApiFormat → envelope adapter
src/parsers/fotmob/NextDataParser.js                        — __NEXT_DATA__ extraction + transformToApiFormat
src/parsers/fotmob/index.js                                 — 统一导出
```

这些文件 lifecycle 均为 `permanent`。它们是 canonical runtime boundary。

### 4.2 Current test-only evidence files

```text
tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.test.js           — adapter 单元测试
tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js  — adapter fixture 集成测试
tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js — metadata handoff 测试
tests/unit/parsers/fotmob/FotMobLocalRawRecordReplay.fixture.test.js               — Lane B replay 测试
tests/unit/parsers/fotmob/FotMobLocalNextDataReplay.fixture.test.js                — Lane A2 replay 测试
tests/unit/parsers/fotmob/FotMobParserOutputEnvelope.test.js                       — envelope schema 测试
```

这些文件保护现有契约和历史证据，但没有 runtime integration。

### 4.3 Not production integrated

以下能力当前仅限于 test fixture 环境：

```text
- Lane B replay (replayLocalRawRecordLaneB)
- Lane A2 replay (replayLocalNextDataLaneA2)
- local raw record replay helper
- local nextdata replay helper
```

### 4.4 Still not touched (DATA-L1E chain 未改动的运行时模块)

```text
- src/infrastructure/harvesters/strategies/FotMobStrategy.js   — 实时采集策略
- src/infrastructure/services/FotMobRawDetailFetcher.js        — 原始数据抓取
- src/infrastructure/services/RawMatchDataVersionSelector.js   — 数据版本选择
- src/parsers/fotmob/index.js                                  — 导出层
```

**关键声明：**

```text
The envelope/replay evidence is still test-only.
It is not runtime integration.
It is not DB backfill.
It is not model feature approval.
```

---

## 5. Document classification

### 5.1 Classification legend

| 分类 | 含义 |
| --- | --- |
| **canonical-source-of-truth** | 永久性权威文档，定义 contract/policy/runtime boundary。应长期保留且作为后续 agent 的主要参考。 |
| **current-state-evidence** | 描述当前已知状态，但不一定是永久 truth。可能被后续 canonical doc 取代。 |
| **implementation-note** | 描述某次 implementation 的具体内容，记录已合入代码的变更。 |
| **historical-phase-evidence** | 仅在某个 phase 中有价值的历史证据，当前参考价值有限。 |
| **future-cleanup-candidate** | 未来授权清理任务时可以归档或删除的文档。 |
| **missing-or-not-found** | inventory 中预期但未找到的文件。 |

### 5.2 Document table

| File | Observed purpose | Classification | Keep now? | Future action | Risk if deleted too early |
| --- | --- | --- | --- | --- | --- |
| `fotmob_parser_output_envelope_implementation_plan.md` | DATA-L1E envelope 分阶段落地总体计划 | canonical-source-of-truth | Yes | 保持；它是 L1E 系列的总入口文档 | 高：后续 agent 失去总体方向 |
| `fotmob_parser_output_envelope_legacy_adapter_dry_run.md` | DATA-L1E-2 adapter dry-run 实现记录 | current-state-evidence | Yes | 可未来合并入 canonical adapter doc | 中：丢失 adapter 设计理由和边界说明 |
| `fotmob_fixture_based_envelope_dry_run_evidence.md` | DATA-L1E-3 fixture-based envelope 证据 | current-state-evidence | Yes | 可未来合并入 replay policy doc | 低：fixture 本身已有测试覆盖 |
| `fotmob_metadata_handoff_dry_run_plan.md` | DATA-L1E-4 metadata handoff 设计计划 | current-state-evidence | Yes | 可未来合并入 canonical metadata/timing policy | 中：定义 metadata handoff contract |
| `fotmob_metadata_handoff_fixture_test.md` | DATA-L1E-5 metadata handoff 测试证据 | current-state-evidence | Yes | 可未来 merge 入 fixture policy doc | 低：测试文件本身是 regression guard |
| `fotmob_adapter_metadata_extension_design.md` | DATA-L1E-5A adapter metadata extension 设计 | current-state-evidence | Yes | 可未来合并入 canonical adapter doc | 中：设计理由在代码中不明显 |
| `fotmob_adapter_metadata_extension_implementation.md` | DATA-L1E-5B adapter metadata extension 实现记录 | implementation-note | Yes | 未来 code 已稳定后可 archive | 低：实现已合入 adapter 代码 |
| `fotmob_local_raw_record_replay_dry_run_design.md` | DATA-L1E-6 Lane B replay 设计 | current-state-evidence | Yes | 可未来合并入 canonical replay policy | 中：定义 Lane B 回放架构 |
| `fotmob_local_raw_record_replay_fixture_test.md` | DATA-L1E-7 Lane B 测试证据 | current-state-evidence | Yes | 可未来合并入 replay policy doc | 低：测试文件是 regression guard |
| `fotmob_local_raw_html_nextdata_replay_design.md` | DATA-L1E-8 Lane A 设计 (最长的设计文档, 845 lines) | current-state-evidence | Yes | 可未来合并入 canonical replay policy; 注意长度和重复讨论 | 中：定义 Lane A/A2 回放架构和复用规则 |
| `fotmob_local_nextdata_replay_fixture_test.md` | DATA-L1E-9 Lane A2 测试证据 | current-state-evidence | Yes | 可未来合并入 replay policy doc | 低：测试文件是 regression guard |
| `fotmob_nextdata_thin_parsers_output_shape_audit.md` | DATA-L1F-2B NextDataParser 输出形态审计 | current-state-evidence | Yes | 保持；定义 Boundary A 的准确形态 | 中：envelope adapter 依赖此审计定义的 boundary |
| `fotmob_parser_field_provenance_timing_labels_design.md` | DATA-L1D provenance/timing labels 设计 | canonical-source-of-truth | Yes | 保持；是 envelope field schema 的理论基础 | 高：envelope schema 的设计依据 |
| `fotmob_raw_payload_retention_replay_policy.md` | DATA-L1C raw payload 保留与回放策略 | canonical-source-of-truth | Yes | 保持；定义 raw 数据生命周期规则 | 高：所有 replay work 的策略依据 |
| `fotmob_existing_pipeline_triage_canonical_path.md` | DATA-L1F 现有 pipeline 主线筛选 | canonical-source-of-truth | Yes | 保持；定义现有 FotMob pipeline canonical path | 高：决定 adapter 接哪条旧链路 |

Note: 所有 15 个文档在 inventory 期间均已确认存在。无 missing 文档。

---

## 6. Fixture classification

### 6.1 Classification legend

| 分类 | 含义 |
| --- | --- |
| **canonical-regression-fixture** | 当前 regression guard 的 fixture。必须保持，直到有替代 fixture。 |
| **representative-boundary-fixture** | 代表某个 boundary (A/B/A2) 的数据形态。有参考价值。 |
| **local-replay-fixture** | 专用于本地 replay 的 fixture。不用于生产。 |
| **future-consolidation-candidate** | 未来可以在 consolidation 任务中合并到更少的 canonical fixture。 |

### 6.2 Fixture table

| Fixture | Used by | Purpose | Classification | Keep now? | Future action | Can be consolidated later? |
| --- | --- | --- | --- | --- | --- | --- |
| `nextdata_transform_output_boundary_a_rich_fixture.json` | FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js | 模拟完整 transformToApiFormat 输出 | canonical-regression-fixture | Yes | 保持；可用于任何 adapter/envelope fixture test | Yes — 可作为 canonical rich fixture |
| `nextdata_transform_output_boundary_a_minimal_fixture.json` | FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js | 模拟最简 transformToApiFormat 输出 | canonical-regression-fixture | Yes | 保持；配合 rich fixture 作为边界测试 | Yes — 可作为 canonical minimal fixture |
| `metadata_handoff_raw_record_boundary_a_fixture.json` | FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js | 模拟 raw record 输入 (含 metadata fields) | metadata-fixture | Yes | 保持 | Yes — 可合并为 unified raw record fixture |
| `metadata_handoff_transform_output_boundary_a_fixture.json` | FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js | 模拟 transformToApiFormat 输出 (含 metadata) | metadata-fixture | Yes | 保持 | Yes — 可合并为 unified transform output fixture |
| `local_raw_record_replay_boundary_b_raw_record_fixture.json` | FotMobLocalRawRecordReplay.fixture.test.js | Lane B raw record 回放输入 | local-replay-fixture | Yes | 保持 | Yes — 可合并到 canonical replay fixture set |
| `local_raw_record_replay_boundary_b_transform_output_fixture.json` | FotMobLocalRawRecordReplay.fixture.test.js | Lane B transform output 回放输入 | local-replay-fixture | Yes | 保持 | Yes — 可合并到 canonical replay fixture set |
| `local_raw_html_nextdata_replay_boundary_a2_raw_record_fixture.json` | FotMobLocalNextDataReplay.fixture.test.js | Lane A2 raw record 输入 | local-replay-fixture | Yes | 保持 | Yes — 可合并到 canonical replay fixture set |
| `local_raw_html_nextdata_replay_boundary_a2_next_data_fixture.json` | FotMobLocalNextDataReplay.fixture.test.js | Lane A2 \_\_NEXT_DATA\_\_ 输入 | local-replay-fixture | Yes | 保持 | Yes — 可合并到 canonical replay fixture set |

**重要约束：**

```text
不要建议现在删除任何 fixture。
所有 fixture 当前都有对应 test 依赖。
未来 consolidation 需要先更新 test 引用路径。
```

---

## 7. Test classification

### 7.1 Test table

| Test file | Purpose | What it protects | Classification | Keep now? | Potential future helper extraction? | Potential future consolidation? |
| --- | --- | --- | --- | --- | --- | --- |
| `FotMobParserOutputEnvelope.test.js` | envelope schema 纯单元测试 | FIELD_CONTRACT_CLASSES, MODEL_ELIGIBILITY, TIMING_CLASSES, createEmptyEnvelope, createFieldEntry | permanent regression guard | Yes | 不需要 | No — standalone |
| `FotMobParserOutputEnvelopeLegacyAdapter.test.js` | adapter 纯单元测试 (不依赖 fixture) | transformToApiFormat → envelope 转换逻辑 | permanent regression guard | Yes | 不需要 | No — standalone |
| `FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js` | adapter fixture 集成测试 | adapter 对 rich/minimal transformToApiFormat 输出的兼容性 | permanent regression guard | Yes | 可提取 shared `readJsonFixture` | No — standalone |
| `FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js` | metadata handoff fixture 测试 | metadata (extractedAt, source, hasStats 等) 正确传入 envelope | regression guard | Yes | 可提取 shared `buildAdapterOptionsFromRawRecord`, `fieldByPath` | No — standalone |
| `FotMobLocalRawRecordReplay.fixture.test.js` | Lane B local raw record replay 测试 | Lane B 回放链路的正确性 | regression guard | Yes | 可提取 shared `readJsonFixture`, `buildAdapterOptionsFromRawRecord`, `fieldByPath`, `replayLocalRawRecordLaneB` | No — 但 helper 重复明显 |
| `FotMobLocalNextDataReplay.fixture.test.js` | Lane A2 local nextdata replay 测试 | Lane A2 回放链路的正确性 + assertNoSafeFields | regression guard | Yes | 可提取 shared `readJsonFixture`, `resolveTransformToApiFormat`, `buildAdapterOptionsFromRawRecord`, `fieldByPath`, `countByEligibility` | No — 但 helper 重复明显 |

**明确声明：**

```text
这些 tests 当前仍然有价值，不建议立即删除。
所有 test 都承担 CI regression evidence 职责。
```

---

## 8. Duplicate helper inventory

### 8.1 Duplication summary

以下 helper 函数在多个 test 文件中各自独立定义，签名和功能几乎相同：

```text
readJsonFixture
    定义于:
      - FotMobLocalRawRecordReplay.fixture.test.js:35
      - FotMobLocalNextDataReplay.fixture.test.js:37
    重复次数: 2
    本质: path.join(__dirname, '../../fixtures/fotmob', relativePath) + JSON.parse

buildAdapterOptionsFromRawRecord
    定义于:
      - FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js:38
      - FotMobLocalRawRecordReplay.fixture.test.js:40
      - FotMobLocalNextDataReplay.fixture.test.js:60
    重复次数: 3 (3 个 test 文件中各有独立实现)
    本质: 从 rawRecord 提取 matchId + extractedAt + source + metadata flags

resolveTransformToApiFormat
    定义于:
      - FotMobLocalNextDataReplay.fixture.test.js:42
    重复次数: 1 (目前仅 A2 使用)
    本质: 从 NextDataParser module 获取 transformToApiFormat 函数引用

replayLocalRawRecordLaneB
    定义于:
      - FotMobLocalRawRecordReplay.fixture.test.js:90
    重复次数: 1 (目前仅 Lane B 使用)
    本质: rawRecord + transformOutput → options → createLegacyAdapterOutput → LegacyAdapter.adapt

replayLocalNextDataLaneA2
    定义于:
      - FotMobLocalNextDataReplay.fixture.test.js:104
    重复次数: 1 (目前仅 Lane A2 使用)
    本质: rawRecord + nextData → resolveTransformToApiFormat → transform → adapter → envelope

fieldByPath
    定义于:
      - FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js:36
      - FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js:82
      - FotMobLocalRawRecordReplay.fixture.test.js:96
      - FotMobLocalNextDataReplay.fixture.test.js:114
    重复次数: 4
    本质: 按 '.' 分割路径遍历 fields 对象

countByEligibility
    定义于:
      - FotMobLocalNextDataReplay.fixture.test.js:118
    重复次数: 1 (目前仅 A2 使用)
    本质: Object.values(fields).filter(e => e.model_eligibility === t).length
```

### 8.2 当前评估

```text
当前重复 helper 是可接受的，原因:
1. 每个 task 是小范围、test-only、低耦合的;
2. 每个 test 文件可以独立运行，不依赖外部 helper 文件;
3. 当前只有 2-4 处重复，还没有到不可维护的程度。

但长期如果继续新增 replay tests (Lane A1, Lane C, ...)，重复会达到临界点。
应该在首次超过 5 处时做一次 helper extraction。
```

### 8.3 建议 future helper 文件

```text
tests/unit/parsers/fotmob/helpers/localReplayTestHelpers.js
```

建议包含的函数：

```text
- readJsonFixture(relativePath)
- buildAdapterOptionsFromRawRecord(rawRecord)
- resolveTransformToApiFormat(nextDataParserModule)
- fieldByPath(fields, fieldPath)
- countByEligibility(envelope, eligibility)
- assertNoSafeFields(envelope)  — 如果未来多个 lane 都需要
```

**重要约束：**

```text
Do not create this helper file in DATA-L1E-HYGIENE-1.
Future helper extraction requires explicit authorization (DATA-L1E-HYGIENE-2).
```

---

## 9. Repository noise assessment

### 9.1 大白话判断

```text
当前 DATA-L1E evidence 文件数量开始增加，但仍处于可控范围。

统计:
- 15 个 DATA-L1E 相关文档 (docs/data/fotmob_*.md)
- 8 个 fixture 文件 (tests/fixtures/fotmob/*.json)
- 6 个 test 文件 (tests/unit/parsers/fotmob/*.test.js)
- 3 个核心代码文件 (src/parsers/fotmob/*.js)

主要风险不是代码污染，而是文档/fixture 命名和权威性不清。
短期不要删除，因为这些文件仍承担 CI regression evidence。
中期需要 consolidation，否则后续 AI agent 会误读历史文档为当前指令。
```

### 9.2 风险矩阵

| Risk | Current severity | Why | Mitigation |
| --- | --- | --- | --- |
| **document sprawl** | Medium | 15 个 fotmob_*.md，每个 task 新增 1-2 个。DATA-L1E-8 文档 845 行，包含大量讨论性内容。 | 本次 inventory 建立分类体系；未来 consolidation 合并 phase evidence 到 canonical doc。 |
| **fixture sprawl** | Low | 8 个 fixture，每个 lane 2 个。仍在可控范围。 | 未来 canonical fixture 策略：每个 boundary 只保留 rich + minimal 各 1 个 canonical fixture。 |
| **helper duplication** | Low-Medium | `fieldByPath` 重复 4 次，`buildAdapterOptionsFromRawRecord` 重复 3 次。逻辑简单、改动少。 | 未来提取 shared test helper 文件。当前不必立即处理。 |
| **canonical ambiguity** | Medium | 新 agent 可能不知道 `FOTMOB_CURRENT_STATE.md` 和 L1E 系列文档中哪个是当前 truth。 | 本次 inventory 明确标记 canonical-source-of-truth vs current-state-evidence。 |
| **AI agent confusion** | Medium | 15 个文档都标记为 `lifecycle: source-of-truth`，agent 无法区分哪些是永久性 policy、哪些是 phase evidence。 | 本次 inventory 建议未来将 phase evidence 文档 lifecycle 改为 `historical-phase-evidence` 或移入 `docs/data/_evidence/` 目录。 |
| **premature cleanup risk** | High | 如果现在删除任何文件，对应 CI test 会失败。 | 本 inventory 明确指出：现在不要删除任何文件。 |
| **runtime accidental integration risk** | Low | 当前 replay helpers 都是 test-only 且纯函数。但如果没有明确文档边界，未来可能有人尝试接 runtime。 | canonical boundary 已在 §4 明确；FotMobStrategy / RawDetailFetcher 均未接入。 |

---

## 10. Canonical map proposal

以下是一个 future canonical map。**本次不实现。**

### 10.1 Future canonical docs

```text
docs/data/fotmob_l1_parser_envelope_contract.md
  — 合并: fotmob_parser_output_envelope_implementation_plan.md 的 contract 部分
  — 合并: fotmob_parser_field_provenance_timing_labels_design.md 的核心设计
  — 定位: canonical, permanent

docs/data/fotmob_l1_replay_and_fixture_policy.md
  — 合并: fotmob_raw_payload_retention_replay_policy.md 的 replay 部分
  — 合并: fotmob_local_raw_record_replay_dry_run_design.md 的核心架构
  — 合并: fotmob_local_raw_html_nextdata_replay_design.md 的核心架构
  — 合并: fotmob_fixture_based_envelope_dry_run_evidence.md 的 fixture 策略
  — 定位: canonical, permanent

docs/data/fotmob_l1_metadata_timing_policy.md
  — 合并: fotmob_metadata_handoff_dry_run_plan.md 的核心 contract
  — 合并: fotmob_adapter_metadata_extension_design.md 的核心设计
  — 合并: fotmob_parser_field_provenance_timing_labels_design.md 的 timing 部分
  — 定位: canonical, permanent

docs/data/fotmob_l1_runtime_integration_blockers.md
  — 新文档: 明确列出哪些模块可以接 runtime、哪些被 blocked、blocker 解除条件
  — 定位: canonical, permanent
```

### 10.2 Future evidence archive

```text
docs/data/_evidence/fotmob_l1e_2_adapter_legacy_dry_run.md
docs/data/_evidence/fotmob_l1e_3_fixture_envelope_evidence.md
docs/data/_evidence/fotmob_l1e_4_metadata_handoff_plan.md
docs/data/_evidence/fotmob_l1e_5_metadata_handoff_test.md
docs/data/_evidence/fotmob_l1e_5a_adapter_metadata_extension_design.md
docs/data/_evidence/fotmob_l1e_5b_adapter_metadata_extension_impl.md
docs/data/_evidence/fotmob_l1e_6_local_raw_record_replay_design.md
docs/data/_evidence/fotmob_l1e_7_lane_b_replay_test.md
docs/data/_evidence/fotmob_l1e_8_lane_a_design.md
docs/data/_evidence/fotmob_l1e_9_lane_a2_replay_test.md
```

### 10.3 Future canonical fixtures

```text
tests/fixtures/fotmob/canonical_rich_transform_output_fixture.json
tests/fixtures/fotmob/canonical_minimal_transform_output_fixture.json
tests/fixtures/fotmob/canonical_raw_record_metadata_fixture.json
tests/fixtures/fotmob/canonical_lane_b_replay_raw_record_fixture.json
tests/fixtures/fotmob/canonical_lane_b_replay_transform_output_fixture.json
tests/fixtures/fotmob/canonical_lane_a2_raw_record_fixture.json
tests/fixtures/fotmob/canonical_lane_a2_next_data_fixture.json
```

### 10.4 Future shared test helper

```text
tests/unit/parsers/fotmob/helpers/localReplayTestHelpers.js
```

**声明：**

```text
This is a proposal only.
Do not implement in this PR.
Future consolidation (DATA-L1E-HYGIENE-2) requires explicit authorization.
```

---

## 11. Merge / cleanup recommendation

### 11.1 当前建议

```text
Do not delete or move current DATA-L1E files yet.

Recommended sequence:
1. Finish or defer DATA-L1E-10 decision (see §12).
2. Define URL sanitizer + fetched_at clock source policy if needed (DATA-L1E-7A).
3. Only then run a future authorized DATA-L1E-HYGIENE-2 consolidation task.

在 consolidation task 中:
- 合并 phase evidence docs 到 canonical docs (见 §10.1)
- 将纯 historical evidence docs 移入 _evidence/ 目录
- 提取 shared test helper (见 §8.3)
- 统一 fixture 命名
- 更新所有 test 引用路径
```

### 11.2 判断

```text
如果 DATA-L1E-10 是高风险或可能造成更多 HTML fixture sprawl，
优先选择 DATA-L1E-7A (URL Sanitizer and Clock Source Policy Design)，
再决定是否进入 Lane A1 (DATA-L1E-10)。
```

### 11.3 当前不应做的

```text
- 不要删除任何 DATA-L1E doc
- 不要移动任何 DATA-L1E doc 到 _evidence/
- 不要重命名任何 fixture
- 不要创建 shared test helper 文件
- 不要创建新的 canonical doc
- 不要修改现有 doc 的 lifecycle 标签
```

---

## 12. DATA-L1E-10 readiness assessment

### 12.1 问题

**Is DATA-L1E-10 ready?**

### 12.2 回答

```text
DATA-L1E-10 is technically possible but should not be automatic.

DATA-L1E-10 (Local Raw HTML __NEXT_DATA__ Extraction Fixture Test) 是 Lane A1:
- 它需要从 raw HTML fixture 中 extract __NEXT_DATA__
- 它需要调用 NextDataParser.extractFromHtml
- 它需要验证 extract 后的数据可以通过 Lane A2 相同的 replay pipeline

A1 raw HTML fixture 增加了比 A2 更高的 hygiene risk:
1. possible accidental real HTML copy
   - 如果 fixture 中包含了真实的 FotMob HTML 原文，可能包含 cookie/token/tracking ID
2. script tag parsing edge cases
   - __NEXT_DATA__ 在 HTML 中的位置、编码、特殊字符处理
3. tracking/ads/consent payload risk
   - 真实 HTML 中包含广告脚本、tracking pixel、consent banner 等第三方内容
4. false confidence from minimal HTML shell
   - 如果只构造极简 HTML shell (只包含 <script id="__NEXT_DATA__">...</script>)，
     测试通过不代表真实 HTML 能正确 extract
```

### 12.3 建议

```text
Prefer one of:
A. DATA-L1E-7A: URL Sanitizer and Clock Source Policy Design
   — 先定义 URL 清理规则和 fetched_at 时钟来源
   — 降低未来 fixture 中嵌入敏感 URL 的风险
   — 为所有 lane 的 raw record fixture 建立统一的 URL/时间戳 hygiene 标准

B. DATA-L1E-10: Local Raw HTML __NEXT_DATA__ Extraction Fixture Test
   — 仅当用户明确要求继续 Lane A1 时选择
   — 必须 strictly fixture-only, minimal HTML shell, no real FotMob HTML
   — 必须验证 extractFromHtml 而非真实 browser extraction
```

### 12.4 正式结论

```text
DATA-L1E-10 should not auto-start.
User must explicitly confirm which path to take:
- Option A (DATA-L1E-7A): safer, reduces fixture hygiene risk
- Option B (DATA-L1E-10): continues Lane A1, adds extraction test
Recommendation: prefer Option A first.
```

---

## 13. Deep flatten status

```text
deep flatten 仍未处理。

当前安全依赖 parent raw block forbidden 策略:
- 在 FotMobParserOutputEnvelopeLegacyAdapter 中，
  POSTMATCH_PATH_PREFIXES 包括 'content' 和 'general' 的顶层匹配
- 但不包括 deep flatten 后的子字段逐个检查

目前 envelope 的 model_eligibility 标签是逐字段的。
如果 raw payload 中存在深层嵌套对象:
  content.stats.ExpectedGoals.away → postmatch
  content.stats.ExpectedGoals → 可能被误标 (取决于路径匹配粒度)

不要在 hygiene task 中处理 deep flatten。
如果未来处理，应单独授权，例如 DATA-L1E-5C 或 DATA-L1E-3A。
```

---

## 14. What changed

```text
docs/data/fotmob_l1e_evidence_hygiene_inventory.md   (新增)
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

### Option A (Recommended)

```text
DATA-L1E-7A: URL Sanitizer and Clock Source Policy Design

Purpose:
- 定义 URL sanitizer 规则 (strip sensitive query params, hash, tracking IDs from URLs in raw records)
- 定义 fetched_at clock source policy (哪个时钟作为 canonical fetched_at，如何防止 clock skew)
- 为所有 lane 的 fixture 提供统一的 URL/时间戳 hygiene baseline
- 降低未来 HTML fixture 中嵌入敏感 URL 的风险

Reason for recommendation:
- 先定义 hygiene 基础策略，再继续新增 fixture
- 不对现有 fixture 产生 breaking change
- 不影响现有 CI
```

### Option B

```text
DATA-L1E-10: Local Raw HTML __NEXT_DATA__ Extraction Fixture Test

Purpose:
- Lane A1: 从 raw HTML fixture 中 extract __NEXT_DATA__
- 验证 NextDataParser.extractFromHtml (纯函数版本)
- 验证 extract 后的 nextData 可以通过 Lane A2 replay pipeline

Conditions if chosen:
- Must be strictly fixture-only
- Must use minimal HTML shell (only <script id="__NEXT_DATA__"> block)
- Must NOT include real FotMob HTML
- Must NOT include tracking/ads/consent payloads
```

**最终声明：**

```text
Do not start automatically.
Recommended next task only after user confirmation.
```

---

## Appendix A: Complete file inventory

### A.1 Documents (15 files)

```text
docs/data/fotmob_adapter_metadata_extension_design.md            (482 lines, lifecycle: current-state)
docs/data/fotmob_adapter_metadata_extension_implementation.md    (213 lines, lifecycle: current-state)
docs/data/fotmob_existing_pipeline_triage_canonical_path.md      (547 lines, lifecycle: source-of-truth)
docs/data/fotmob_fixture_based_envelope_dry_run_evidence.md      (167 lines, lifecycle: source-of-truth)
docs/data/fotmob_local_nextdata_replay_fixture_test.md           (150 lines, lifecycle: current-state)
docs/data/fotmob_local_raw_html_nextdata_replay_design.md        (845 lines, lifecycle: current-state)
docs/data/fotmob_local_raw_record_replay_dry_run_design.md       (575 lines, lifecycle: current-state)
docs/data/fotmob_local_raw_record_replay_fixture_test.md         (230 lines, lifecycle: current-state)
docs/data/fotmob_metadata_handoff_dry_run_plan.md                (220 lines, lifecycle: current-state)
docs/data/fotmob_metadata_handoff_fixture_test.md                (148 lines, lifecycle: current-state)
docs/data/fotmob_nextdata_thin_parsers_output_shape_audit.md     (661 lines, lifecycle: source-of-truth)
docs/data/fotmob_parser_field_provenance_timing_labels_design.md (702 lines, lifecycle: source-of-truth)
docs/data/fotmob_parser_output_envelope_implementation_plan.md   (596 lines, lifecycle: source-of-truth)
docs/data/fotmob_parser_output_envelope_legacy_adapter_dry_run.md(205 lines, lifecycle: current-state)
docs/data/fotmob_raw_payload_retention_replay_policy.md          (493 lines, lifecycle: source-of-truth)
```

### A.2 Fixtures (8 files)

```text
tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_next_data_fixture.json     (99 lines)
tests/fixtures/fotmob/local_raw_html_nextdata_replay_boundary_a2_raw_record_fixture.json     (30 lines)
tests/fixtures/fotmob/local_raw_record_replay_boundary_b_raw_record_fixture.json             (28 lines)
tests/fixtures/fotmob/local_raw_record_replay_boundary_b_transform_output_fixture.json       (69 lines)
tests/fixtures/fotmob/metadata_handoff_raw_record_boundary_a_fixture.json                    (26 lines)
tests/fixtures/fotmob/metadata_handoff_transform_output_boundary_a_fixture.json              (83 lines)
tests/fixtures/fotmob/nextdata_transform_output_boundary_a_minimal_fixture.json              (20 lines)
tests/fixtures/fotmob/nextdata_transform_output_boundary_a_rich_fixture.json                 (96 lines)
```

### A.3 Tests (6 files)

```text
tests/unit/parsers/fotmob/FotMobParserOutputEnvelope.test.js                              (320 lines)
tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.test.js                 (688 lines)
tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.fixture.test.js         (263 lines)
tests/unit/parsers/fotmob/FotMobParserOutputEnvelopeMetadataHandoff.fixture.test.js       (297 lines)
tests/unit/parsers/fotmob/FotMobLocalRawRecordReplay.fixture.test.js                      (388 lines)
tests/unit/parsers/fotmob/FotMobLocalNextDataReplay.fixture.test.js                       (349 lines)
```

### A.4 Core source files (4 files, not modified)

```text
src/parsers/fotmob/FotMobParserOutputEnvelope.js
src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter.js
src/parsers/fotmob/NextDataParser.js
src/parsers/fotmob/index.js
```

---

## Appendix B: Helper duplication quick reference

| Helper | Files with own definition | Defined in test | Referenced in docs |
| --- | --- | --- | --- |
| `readJsonFixture` | 2 | FotMobLocalRawRecordReplay, FotMobLocalNextDataReplay | — |
| `buildAdapterOptionsFromRawRecord` | 3 | MetadataHandoff, LaneB, LaneA2 | metadata_handoff_fixture_test, local_raw_record_replay_fixture_test, adapter_metadata_extension_implementation |
| `fieldByPath` | 4 | LegacyAdapter.fixture, MetadataHandoff, LaneB, LaneA2 | — |
| `replayLocalRawRecordLaneB` | 1 | FotMobLocalRawRecordReplay | local_raw_record_replay_fixture_test |
| `replayLocalNextDataLaneA2` | 1 | FotMobLocalNextDataReplay | — |
| `resolveTransformToApiFormat` | 1 | FotMobLocalNextDataReplay | — |
| `countByEligibility` | 1 | FotMobLocalNextDataReplay | — |
