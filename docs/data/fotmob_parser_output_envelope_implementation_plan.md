# FotMob Parser Output Envelope Implementation Plan

- lifecycle: source-of-truth
- scope: docs-only, FotMob parser output envelope 实现计划
- parent documents: DATA-L1A, DATA-L1B, DATA-L1C, DATA-L1D
- branch: `docs/data-l1e-fotmob-parser-output-envelope-implementation-plan`

---

## 1. 背景

DATA-L1A 已完成并合并（PR #1694）：发现 FotMob 字段存在赛前/赛后边界风险。

DATA-L1B 已完成并合并（PR #1695）：建立了 FotMob 赛前字段合同——safe_prematch_candidate / unsafe_postmatch / unknown_timing / metadata_only / debug_or_raw_only。

DATA-L1C 已完成并合并（PR #1696）：建立了 raw payload 保留与回放策略——规定原始证据怎么保留、怎么回放、怎么用于 cutoff audit。

DATA-L1D 已完成并合并（PR #1697）：设计了 parser 字段来源与时间标签体系——provenance / timing_class / model_eligibility / parser output envelope。

DATA-L1E 的目标不是实现 parser，也不是写新的字段合同。DATA-L1E 要做的是：**把 DATA-L1D 的设计转化为一份可执行的、分阶段的、每步都可回滚的实现计划**。

可以用一个工程类比来理解 DATA-L1 系列的角色转换：

```text
DATA-L1A = 体检报告——查出风险
DATA-L1B = 饮食禁忌表——规定什么能吃
DATA-L1C = 食材进货小票保存制度——原始证据怎么留
DATA-L1D = 每道菜上桌前贴标签——设计标签应该怎么写
DATA-L1E = 真正施工前的施工计划和分工表——先画图，不直接开挖
```

本文件是 parser output envelope 实现计划。它不改造 parser，不改造 feature，不改造 training。它不运行任何采集，不运行 parser，不改变任何现有 runtime 行为。它只规划"怎么落地"。

---

## 2. 为什么要先写 implementation plan

DATA-L1D 已经有完整的设计——parser output envelope 的结构、每个字段需要什么标签、tag 的分类体系都很清楚。但设计不等于可以直接开改代码。原因如下：

1. **parser 是数据入口，直接大改风险很高。** FotMobRawParser 目前输出被下游的 feature engine、smelter、training 等模块间接或直接依赖。如果一次性改 parser 输出结构，下游全崩。

2. **如果一次性改 parser + feature + training + backtest，出问题很难定位。** 是 parser 输出变了？是 feature engine 过滤错了？是 training 用了不该用的字段？还是 backtest 的 cutoff 设置错了？分不清。

3. **从"裸字段值"到"带标签的 envelope"是一个结构性变化。** 它改变了 parser 与 feature engine 之间的接口契约。这种变化需要先用 schema / adapter / dry-run 逐渐过渡，不能一步到位。

4. **很多 metadata 当前可能不存在。** DATA-L1C 要求的 captured_at、payload_hash、is_replayable 等字段，parser 现在可能还没输出。第一版 envelope 可能需要用 null 或 unknown 做占位符，之后再逐步补全。

所以 DATA-L1E 先把施工顺序写清楚：

```text
先定义 envelope schema → 再做兼容 wrapper → 再做字段标签 → 
再做 feature 过滤 → 再做训练/回测 enforcement → 最后再考虑 CI 检查。

每一步都是一个小 PR。每一步都有明确的验收标准和回滚方案。
不跳步。不一步到位。
```

---

## 3. 核心原则

这些原则约束后续所有代码 PR 的行为：

1. **先兼容，后替换。** 旧 parser 输出不能在第一版就被删掉。新 envelope 和旧输出必须可以并存。

2. **先 envelope schema，后 runtime enforcement。** 第一步只定义数据结构。不要在第一版就改 parser runtime、feature engine 或 training。

3. **先 docs/design，后 small code PR。** 每个代码 PR 之前都应该有对应的设计说明或至少一个明确的 issue/PR body。

4. **不一次性改 parser + feature + training + backtest。** 每个模块单独 PR，每个 PR 独立可回滚。

5. **parser output envelope 必须保留原始 parser 输出兼容路径。** feature engine 在第一阶段仍然读旧输出；envelope 只是额外输出，用于审计和验证。

6. **parser 可以解析 unsafe_postmatch 字段，但必须标记 forbidden_postmatch。** 解析能力不因标签制度而退化。标签只是标记，不删除字段。

7. **unknown_timing 默认不允许进入赛前模型。** parser 可以标记 timing_class，但 feature engine 必须拒绝。

8. **raw payload / pageProps / `__NEXT_DATA__` 只能作为来源证据，不能直接进入模型。** 这是 DATA-L1B 和 DATA-L1C 的共同红线。

9. **captured_at 是 payload 时间，不等于字段 observed_at。** parser 不应该混淆这两个概念。

10. **implementation plan 必须能服务 DATA-L1B / DATA-L1C / DATA-L1D。** 如果计划中的某一步与这些文档冲突，以文档为准。

11. **每一步实现都必须有明确回滚路径。** 如果某个 PR 导致 CI 失败或下游断裂，应该能通过 revert 该 PR 恢复。

12. **每一步 PR 必须小范围、可审计、可回退。** 一个 PR 改 20 个文件的时代结束了。

---

## 4. 当前状态梳理（只读，未运行）

以下基于对仓库文件的只读审计。所有"未确认"项表示本次只读 grep 没有找到或不能确定，不代表不存在。

### 4.1 当前 FotMob parser 相关文件线索

| 文件/路径 | 描述 | 当前是否有 timing/provenance 标签 | 备注 |
| --- | --- | --- | --- |
| `src/parsers/fotmob/FotMobRawParser.js` | 主 parser，输出 match/team/stats/lineup/events/shotmap/playerStats | **没有。** 输出裸结构字段值，无字段级 tag | 这是 envelope 未来的主要接入目标 |
| `src/parsers/fotmob/NextDataParser.js` | 从 `__NEXT_DATA__` / HTML 提取并转成 API-like payload | **未确认。** 只读线索显示它做 transform，不是 timing | |
| `src/parsers/fotmob/XGExtractor.js` | 提取 xG | **没有。** 提取纯值 | 未来必须标记为 forbidden_postmatch |
| `src/parsers/fotmob/MatchStatsParser.js` | 提取 match stats | **没有。** | 同上 |
| `src/parsers/fotmob/FotMobSchemaGuard.js` | key shape diff guard | **没有。** 做结构比较，不是 timing guard | schema 稳定性线索 |
| `src/infrastructure/services/FotMobRawDetailFetcher.js` | 构建 stable raw payload | 可能有 `_meta.fetched_at` 等元信息 | 可能提供 captured_at 等 payload metadata |
| `src/infrastructure/services/RawMatchDataVersionSelector.js` | 按 data_version 选择 canonical raw | 有 data_version 概念 | 关键——envelope 需要 data_version |
| `docs/data/FOTMOB_RAW_PARSER_CONTRACT.md` | parser 合同文档 | 有 general/header/content/stats/lineup 等模块划分 | 不含字段级 timing/provenance |

### 4.2 当前已有字段线索

| 线索 | 已确认/未确认 | 备注 |
| --- | --- | --- |
| `captured_at` | **未确认 parser 当前是否输出到字段级。** `_meta.fetched_at` 可能存在 | DATA-L1A §6 提到 raw capture time 不等于 feature observed time |
| `payload_hash` | **未确认。** DATA-L1C 要求但 parser 当前可能没有 | |
| `data_version` | **已确认存在概念。** RawMatchDataVersionSelector 使用它 | 但 parser 是否把 data_version 带到输出里——未确认 |
| `parser_version` | **未确认。** 可能只在 docs/commit log 中隐含 | |
| `observed_at`（字段级） | **未确认。当前 parser 不可能输出。** | DATA-L1D 设计要求字段级，但实现需要额外工作 |
| `prediction_cutoff_time` | **未确认。** 这是 prediction task 的概念，parser 当前不知道 cutoff | |

### 4.3 当前未确认但可能有关的项

- FotMobRawDetailFetcher 的 `_meta` 块是否包含 captured_at、hash 等信息——**本次未运行，不能确认。**
- `raw_match_data` 表当前是否有 captured_at、payload_hash、data_version 列——**本次不查 DB，不能确认。**
- 现有测试 fixture 是否可用于 parser regression——**本次不运行测试，不能确认。**
- 当前 feature engine 是否已经依赖 parser 输出的特定结构——**本次不改代码，不能确认。**

### 4.4 对本计划的影响

- 第一版 envelope 的 payload metadata 可能大部分是 null/unknown。这不可怕——有占位符比没有好。
- 需要先确认 FotMobRawDetailFetcher 的 `_meta` 输出，再决定 captured_at/payload_hash 的数据来源。这个确认本身可能就是 DATA-L1E-1 或 L1E-2 的一个子任务。
- 当前 parser 可能没有 parser_version 的概念。第一版可以从 `"v-next"` 或 git commit hash 手工标注。

---

## 5. 目标 envelope 最小形态

以下定义第一个代码 PR 应该实现的最小 envelope 形态——不完美但足以开启整个改造。

### 5.1 最小 schema

```json
{
  "match_id": "123456",
  "source": "fotmob",

  "payload": {
    "payload_type": "pageProps",
    "payload_hash": "sha256:a1b2c3...",
    "captured_at": "2026-07-03T12:00:00Z",
    "data_version": "pageprops_v2",
    "storage_path": null,
    "source_url": null,
    "final_url": null
  },

  "parser": {
    "parser_name": "FotMobRawParser",
    "parser_version": "v-next",
    "parsed_at": "2026-07-03T12:01:00Z"
  },

  "fields": [
    {
      "name": "home_team",
      "value": "Paris SG",
      "field_path": "$.general.homeTeam.name",
      "field_contract_class": "safe_prematch_candidate",
      "timing_class": "fixture_metadata",
      "observed_at": null,
      "model_eligibility": "candidate_if_cutoff_valid",
      "warnings": []
    },
    {
      "name": "home_xg",
      "value": 1.25,
      "field_path": "$.content.stats.xG",
      "field_contract_class": "unsafe_postmatch",
      "timing_class": "postmatch",
      "observed_at": null,
      "model_eligibility": "forbidden_postmatch",
      "warnings": []
    }
  ]
}
```

### 5.2 设计决策

- **不要一开始追求完美大而全。** 第一版只要有 match_metadata + payload_metadata + parser_metadata + fields 就够了。
- **不需要一次覆盖所有 FotMob 字段。** 第一版可以只覆盖 FotMobRawParser 输出的顶级字段类别（general/header/content/stats/lineup/events），不要求全部叶子字段独立标签。
- **null 是可接受的 placeholder。** storage_path、source_url、observed_at 等字段如果当前不存在，用 null 标记。不要假装存在。
- **warnings 数组预留。** 如果某个字段有已知风险（比如 field_path 不确定、timing_class 可能过时），放入 warnings。

### 5.3 本 PR 不实现这个结构

本 PR 只定义第一版实现的目标形态。实现本身需要单独的 DATA-L1E-1 PR。

---

## 6. 分阶段 implementation roadmap

以下将后续 implementation 分成 9 个阶段，每个阶段一个独立 PR。每个 PR 小范围、可审计、可回退。

| 阶段 | PR 名称 | 一句话目标 | 允许改什么 | 禁止做什么 | 验收标准 | 回滚方式 | 是否需测试 | 是否需 FotMob 网络 | 风险等级 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **L1E-1** | Envelope Schema | 定义 envelope 数据结构（不接入 parser） | 仅新文件：envelope schema / dataclass / type definition | 不改 parser、feature、training、backtest | schema 文件存在且通过静态检查；本地 AI Workflow Gate 通过 | 删除新增文件 | 建议有 unit test（对 schema 做字段验证） | 否 | 低 |
| **L1E-2** | Legacy Adapter | 把旧 parser 输出包装成 envelope 格式（不改变原输出） | adapter 文件 + 可选 envelope schema 微调 | 不改 parser runtime、不改 feature engine 输入 | adapter 在 dry-run 模式下能正确包装旧输出；无 runtime 影响 | 删除 adapter 文件 | 建议有 unit test（用 fixture） | 否 | 低-中 |
| **L1E-3** | Contract Mapper | 实现 field_contract_class mapper（DATA-L1B → parser output） | mapper 文件 + DATA-L1B 合同参考文件（只读引用） | 不改 parser runtime、不改 feature engine | 所有已知 FotMob 字段都有 field_contract_class；缺的字段标记 unknown 并 warnings | 删除 mapper 文件 | unit test | 否 | 低 |
| **L1E-4** | Timing Mapper | 实现 timing_class mapper（字段 → timing_class） | mapper 文件 | 不改 parser runtime | 所有已知字段都有 timing_class；xG=postmatch 无误；fixture 字段=fixture_metadata | 删除 mapper 文件 | unit test | 否 | 中 |
| **L1E-5** | Eligibility Dry-Run | 实现 model_eligibility mapper + dry-run 输出（不阻断任何 runtime） | mapper 文件 + dry-run 审计输出 | 不改 feature engine、training、backtest | dry-run 输出能显示哪些字段 forbidden、哪些 candidate；不改变现有 feature pipeline | 删除 mapper 文件 | unit test + dry-run diff 检查 | 否 | 中 |
| **L1E-6** | Feature Eligibility Checker | feature engine 侧读取 envelope 的 model_eligibility 并做 dry-run 过滤 | feature engine 部分（forbidden 字段记录 warning 但不阻断） | 不改 training、backtest；不删除/修改旧 parser 输出 | feature engine 能读取 envelope 并输出哪些字段被跳过；旧行为不受影响 | feature engine 回滚到旧逻辑 | unit test + integration test（dry-run） | 否 | 中-高 |
| **L1E-7** | Training Cutoff Check | training pipeline 侧接入 cutoff safety check | training 相关代码 | 不改 backtest、CI；不删除旧逻辑 | training 能读取 envelope 的 model_eligibility + cutoff 信息；dry-run 无 regression | 回滚 training 改动 | unit test + dry-run training | 否 | 高 |
| **L1E-8** | Replay Fixture Runner | 创建轻量级 replay runner（不做 CI 集成） | 新工具/脚本（runner + fixture） | 不改 parser runtime；不改 CI pipeline | 能用 critical raw payload fixture 跑 parser 并对比 envelope 输出 | 删除 runner 和 fixture | 有（runner 本身是验证工具） | 否（用本地 fixture） | 中 |
| **L1E-9** | CI Compliance Check | CI 增加 field-contract compliance check（dry-run，不阻断 merge） | CI workflow 或 CI 脚本 | 不改 CODEOWNERS、branch protection、Gatekeeper | CI 能检测 "parser 新增字段未在 DATA-L1B 中登记"并发出 warning | 删除 CI check | 不需要（CI 本身是检查） | 否 | 中 |

### 6.1 关键约束

- **L1E-1 ∼ L1E-5 是纯 schema / mapper / dry-run 阶段。** 不改变任何 runtime 行为。不回破坏现有 system。
- **L1E-6 开始影响 feature engine。** 这一步是"从不阻断到阻断"的转折点，需要最严格的 review。
- **L1E-7 是 training 侧的转折点。** 可能暴露过去训练中用了赛后字段的历史问题，需要心理准备。
- **L1E-8 和 L1E-9 是基础设施。** 它们服务和验证前面的工作，不引入新的字段规则。

### 6.2 本 PR 不启动任何阶段

以上所有阶段都需要用户单独授权。**本 PR 只定义 roadmap。**

---

## 7. 第一阶段最小实现建议：schema only

以下重点规划 L1E-1 的细节，因为它是整个实现计划的起点。

### 7.1 为什么第一步不应该直接改 FotMobRawParser

- FotMobRawParser 当前输出被多处下游依赖。直接改输出结构→下游全崩。
- FotMobRawParser 没有 parser_version（或者版本概念只在文档层面存在）。需要先定义版本管理方式。
- 当前不确定 FotMobRawDetailFetcher 的 `_meta` 提供哪些 payload metadata。需要在 schema 定义之前先确认。
- 先定义 schema，可以让大家对齐"我们最终要什么"。不是所有人都先读了 DATA-L1D 的 702 行设计文档。

### 7.2 为什么先有 schema，后有 adapter

- schema 定义"目标长什么样"。
- adapter 负责"把旧东西映射成新东西"。
- 先定义 schema 可以减少 adapter 的设计返工——adapter 不需要"猜"目标结构。

### 7.3 为什么要保留旧 parser 输出

- feature engine 仍然在消费旧输出。
- training pipeline 仍然在消费旧输出。
- 在 feature eligibility checker（L1E-6）和 training cutoff check（L1E-7）准备就绪之前，旧输出是唯一的 runtime 输入。
- 双轨运行（旧输出 + envelope 并行）是安全的过渡策略。

### 7.4 L1E-1 的具体建议

```text
任务：创建 envelope schema 文件

建议文件路径：
  src/parsers/fotmob/envelope_schema.js （或 .ts / .py，取决于项目技术栈）
  或 docs/data/envelope_schema.example.json （如果第一步只想做文档）

建议包含：
  - 完整的 JSON Schema 或 typed structure
  - 每个字段的类型、是否必填、默认值（如果有的话）
  - 对 null 字段的处理方式
  - 与 DATA-L1B / DATA-L1C / DATA-L1D 的交叉引用注释

验收标准：
  - 文件存在
  - 与 DATA-L1D §5 的 envelope 结构一致
  - 包含 field_contract_class, timing_class, model_eligibility 的所有枚举值
  - 包含 DATA-L1C §5 的必需 metadata 字段
  - 通过本地 AI Workflow Gate
  - 如果创建了代码文件，通过 lint

不要做的事：
  - 不修改 FotMobRawParser.js
  - 不修改 NextDataParser.js
  - 不修改 XGExtractor.js
  - 不访问 FotMob 网络
  - 不运行 parser
```

---

## 8. 兼容策略

这是整个 implementation 中最关键的部分。parser 是数据入口，没有一个安全的兼容策略，all in 就是灾难。

### 8.1 双输出过渡期

```text
[旧接口]                [新接口]
FotMobRawParser        FotMobRawParser (modified)
  ↓                       ↓
legacy_output          envelope_output
  ↓                       ↓
feature engine         [audit only — 不消费]
  ↓                       ↓
training               [dry-run checker]
```

过渡期至少应该持续到 L1E-6（feature eligibility checker ready）之前。

### 8.2 adapter 模式

```text
legacy_output
    ↓
legacy → envelope adapter
    ↓
envelope_output (for audit / validation)
```

adapter 是一个薄层，把旧 parser 输出（嵌套结构）转换为 envelope（flat fields 数组 + metadata）。adapter 不做解析——只做格式映射。

### 8.3 渐进式迁移路径

1. **L1E-1**：envelope schema 存在，只有文档。
2. **L1E-2**：adapter 存在，能把 legacy output 转成 envelope。（parser 本身不改。）
3. **L1E-3 ∼ L1E-5**：mapper 逐步添加 contract/timing/eligibility 标签。adapter 调用这些 mapper。
4. **L1E-6**：feature engine 开始读 envelope 的 model_eligibility（但仍然是 dry-run，不阻断）。此时旧输出仍然可以消费。
5. **L1E-7 ∼ L1E-9**：training/backtest/CI 逐步接入。旧输出逐步退出（但不是删除）。
6. **未来**：旧输出标记为 deprecated，仅保留用于 CI replay（不是模型输入）。具体时间待定。

### 8.4 不要做的事情

- 不要在第一版就让 training 依赖 envelope。
- 不要在第一版就删除旧 parser 输出。
- 不要删除 legacy 文件。
- 不要在一次 PR 里同时改 parser + adapter + feature engine。

---

## 9. 字段合同映射落地计划

未来 L1E-3 负责接管 DATA-L1B 的字段分类，并映射到 parser output 的 field_contract_class。

### 9.1 映射表

| DATA-L1B field_contract_class | parser model_eligibility | 说明 |
| --- | --- | --- |
| `safe_prematch_candidate` | `candidate_if_cutoff_valid` | 必须经过 cutoff 检查后才能放行 |
| `unsafe_postmatch` | `forbidden_postmatch` | 绝对禁止进入赛前模型 |
| `unknown_timing` | `forbidden_unknown_timing` | 默认禁止，除非后续 audit 提供 observed_at 证据并升级 |
| `metadata_only` | `forbidden_metadata_only` | 作为特征时禁止；用于 join/filter 时允许（但不作为特征） |
| `debug_or_raw_only` | `forbidden_raw_only` | 永远不进模型 |

### 9.2 第一版实现建议

- **hardcoded mapping table / table-driven mapping。** 一个简单的 JS/Python object 把 field_name → field_contract_class。不用外部 YAML/config 系统。
- **不要一开始做复杂配置系统。** 配置系统会增加复杂度和出错的表面积。先 hardcoded，等确认 mapping 逻辑正确后再考虑外部化。
- **不知道分类的字段标记为 unknown。** 用 `field_contract_class = "unknown"` + `warnings = ["field not found in DATA-L1B contract"]`。不猜测。

---

## 10. raw payload metadata handoff 落地计划

未来 L1E-2（adapter）或 L1E-4（timing mapper）需要把 DATA-L1C 的 metadata 接入 envelope.payload。

### 10.1 需要从 raw payload 获取的字段

| envelope.payload 字段 | 数据来源 | 当前是否存在（本次未运行，不能确认） | 如果不存在怎么办 |
| --- | --- | --- | --- |
| `payload_type` | 采集逻辑或 `_meta` | **未确认** | 第一版可以 hardcoded 为 `"pageProps"` 或 `"unknown"` |
| `payload_hash` | SHA-256(raw_payload) | **未确认。** DATA-L1C 要求但 parser 可能没有 | 第一版可以用 null；后续 PR 由采集逻辑计算 |
| `captured_at` | `_meta.fetched_at` 或采集时间戳 | **未确认。** FotMobRawDetailFetcher 可能有 `_meta` | 第一版可以是 null 或 `new Date().toISOString()`（近似，但标记 warnings） |
| `source_url` | FotMobRawDetailFetcher 构造的 URL | **未确认** | null |
| `final_url` | 同上 | **未确认** | null |
| `storage_path` | raw payload 文件路径 | **未确认。** DATA-L1C 建议路径 | null |
| `data_version` | RawMatchDataVersionSelector 或采集入口 | **已确认有概念但不确认 parser 是否输出** | null 或固定的版本号 |
| `is_replayable` | parser 是否能成功解析此 payload | **未确认** | 第一版可以在 adapter 中根据解析结果设 true/false |

### 10.2 原则

- **如果 metadata 不存在，第一版 envelope 可以允许 null。**
- **但 null 必须显式标记。** 不能假装存在。在 field 级别的 warnings 里说明 "payload metadata missing: payload_hash / captured_at"。
- **随着后续 DATA-L1C retention adapter 的实现（不在本计划中），metadata 会逐步补齐。** envelope 的设计要能容纳渐进式 metadata 丰富。

---

## 11. timing labels 落地计划

未来 L1E-4 timing mapper 负责把 DATA-L1D 的 timing_class 接入 parser output。

### 11.1 保守的第一版映射

| 字段/字段类别 | timing_class | 为什么 |
| --- | --- | --- |
| league, season, round, kickoff_time, home_team, away_team | `fixture_metadata` | 赛程信息，赛前确定 |
| opening_odds (if captured_at exists) | `prematch_snapshot` | 初盘在赛前很早存在 |
| venue, referee | `unknown_timing` | 没有来源时间证据 |
| lineup, formation, squad, coach | `near_kickoff_snapshot` → `unknown_timing` | 接近开赛才公布，但没有 lineup_timestamp |
| injury, suspension, unavailable | `unknown_timing` | 来源时间和可信度不确定 |
| league_table, team_form, head_to_head (from FotMob snapshot) | `unknown_timing` | FotMob 快照时间未证明 |
| xG, shots, possession, passes, duels, corners, cards, events, shotmap, player_stats, player_ratings, match_stats | `postmatch` | 赛后数据，绝对禁止 |
| score, result, halftime_score, status.finished | `postmatch` | 比赛结果 |
| current_odds (no timestamp) | `unknown_timing` | 无时间戳 |
| closing_odds | `unknown_timing` → `near_kickoff_snapshot`（取决于 horizon） | 对早期预测是 unknown |
| pageProps, raw JSON, `__NEXT_DATA__`, HTML hydration, debug trace | `raw_only` | 永远不进模型 |

### 11.2 保守策略说明

- **没有证据的字段默认 unknown_timing。**
- **xG / shots / score / events / player stats 默认 postmatch——不可翻案。**
- **raw payload / pageProps / `__NEXT_DATA__` 默认 raw_only。**
- **lineup / injury / odds / table / form 默认 unknown_timing，除非后续字段级 observed_at 证明它在 cutoff 前可用。**

---

## 12. model eligibility 落地计划

未来 L1E-5 eligibility dry-run 负责建立 model_eligibility 映射并在 dry-run 模式下输出审计信息。

### 12.1 eligibility 分类落地

| model_eligibility | 触发条件 | 后续处理 |
| --- | --- | --- |
| `allowed_candidate` | DATA-L1B 标记为 safe_prematch_candidate + observed_at ≤ cutoff + fixture_metadata | feature engine 放行 |
| `candidate_if_cutoff_valid` | DATA-L1B 标记为 safe_prematch_candidate 但没有 observed_at proof | feature engine 需要额外 cutoff 检查 |
| `forbidden_postmatch` | DATA-L1B 标记为 unsafe_postmatch | feature engine 直接拒绝 |
| `forbidden_unknown_timing` | DATA-L1B 标记为 unknown_timing | feature engine 拒绝，但可被升级 |
| `forbidden_raw_only` | DATA-L1B 标记为 debug_or_raw_only | feature engine 拒绝 |
| `forbidden_metadata_only` | DATA-L1B 标记为 metadata_only 但被当作特征 | feature engine 拒绝（作为特征时） |
| `forbidden_contract_violation` | 任何被明确禁止但仍试图进入模型的字段 | feature engine 拒绝 + warnings + 审计日志 |

### 12.2 处理方式

- **parser（L1E-3 ∼ L1E-5）只给初步 eligibility。** 最终 enforcement 由 feature engine（L1E-6）执行。
- **第一版可以只输出标签，不阻断任何 runtime。** 阻断行为必须另开 PR（L1E-6 是 dry-run, L1E-7 开始真正阻断）。
- **dry-run 输出可以使用 console.warn / structured log / audit file。** 不改变 parser 返回值结构。

---

## 13. feature / training / backtest 后续接入计划

### 13.1 接入时序

| 模块 | 接入阶段 | 做什么 | 不做什么 |
| --- | --- | --- | --- |
| **feature engine** | L1E-6 (dry-run) → 后续 PR (real enforcement) | 读取 envelope.model_eligibility，拒绝 forbidden_*；对 candidate_if_cutoff_valid 做 cutoff check | L1E-6 只 dry-run，不改变 feature 输出 |
| **training** | L1E-7 | 只使用 candidate_if_cutoff_valid 且通过 cutoff safety check 的字段 | 不改 backtest logic |
| **backtest** | 在 L1E-7 之后（可能是 L1E-7 的 part 2 或独立 PR） | 模拟 prediction_cutoff_time；验证每个 feature 的 observed_at ≤ cutoff；按 prediction horizon 分组评估 | 不回填历史 backtest 结果 |
| **线上 prediction** | L1E-7 之后（独立 PR） | 拒绝 forbidden_* 字段；确保 cutoff 检查在 runtime 执行 | 不暗改 prediction 结果 |

### 13.2 强调

- **本 PR 不改 feature。**
- **本 PR 不改 training。**
- **本 PR 不跑 backtest。**
- **本 PR 只做计划。**

---

## 14. 测试策略计划

虽然本 PR 不写测试，但需要为未来代码 PR 规划测试策略。

### 14.1 按阶段需要的测试

| 阶段 | 建议的测试类型 | 测试数据来源 | 是否依赖 FotMob 网络 |
| --- | --- | --- | --- |
| L1E-1 (schema) | unit：验证 schema 结构完整、枚举值正确 | fixture JSON / static example | 否 |
| L1E-2 (adapter) | unit：验证 adapter 对已知旧输出能正确生成 envelope | 旧 parser 输出 fixture（从现有 tests/fixtures 取） | 否 |
| L1E-3 (contract mapper) | unit：验证所有已知字段有正确的 field_contract_class | DATA-L1B 合同中的字段清单（手动维护的测试 fixture） | 否 |
| L1E-4 (timing mapper) | unit：验证 timing_class 分配正确；xG=postmatch, league=fixture_metadata | 同上 | 否 |
| L1E-5 (eligibility dry-run) | unit + integration：dry-run 输出中 forbidden 和 candidate 的比例合理 | 真实历史 envelope（如果有）或手工构造 | 否 |
| L1E-6 (feature checker) | unit + integration + regression：验证 feature engine 行为不变 | 旧 feature engine 输出 fixture | 否 |
| L1E-7 (training cutoff) | unit + dry-run training：验证训练数据集不包含 forbidden 字段 | small fixture dataset（已知 cutoff 的比赛子集） | 否 |
| L1E-8 (replay runner) | runner 本身就是验证工具 | critical raw payload fixture | 否 |
| L1E-9 (CI check) | CI 本身就是检查 | repo 中已有的 fixture 或 schema 文件 | 否 |

### 14.2 测试原则

- **第一批测试应使用小型静态 fixture，不访问真实 FotMob 网络。**
- **不依赖 DB。** 除非团队已经有 CI 中的冷启动 DB。
- **不依赖 Docker。** 除非测试框架已经需要容器。
- **xfail 测试用于标记已知风险。** 比如："parser 当前输出中 xG 没有被标记为 forbidden_postmatch——xfail 直到 L1E-3 修复"。

---

## 15. 风险控制与回滚计划

### 15.1 风险清单

| 风险 | 发生概率 | 影响 | 缓解方式 |
| --- | --- | --- | --- |
| parser 输出结构变化导致下游 broken | 中 | 高——feature engine / training 可能停止工作 | 先 dry-run，先 dual output，先不删除旧输出 |
| envelope 太重导致开发复杂度上升 | 中 | 中——改每个 parser 字段都要同时更新 envelope | 从最小 envelope 开始；大部分字段可以映射而不是重写 |
| metadata 缺失导致大量字段 unknown_timing | 高 | 中——短期可用字段变少，模型性能可能下降 | 这是**故意的保守策略**。短期变少是好事——证明以前可能有用泄露字段的问题 |
| mapping 过于激进导致误放行字段 | 中 | 高——相当于给模型开后门 | 保守 mapping；双层 review；CI compliance check 作为最后一道防线 |
| mapping 过于保守导致短期可用字段变少 | 高 | 低-中——模型短期性能下降，但不导致泄露 | 这是可接受的；模型性能下降比数据泄露好 |
| 旧 parser 输出与新 envelope 双轨维护带来复杂度 | 中 | 中——维护者需要理解两套接口 | 设定明确的 deprecated timeline；不永久保留双轨 |
| training/backtest 迁移时暴露过去数据泄露问题 | 高 | 中——历史回测结果可能变差 | 这是**预期的发现**。不应该掩盖。文档记录以前可能存在的泄露问题 |
| FotMobRawParser 当前没有版本管理，parser_version 难以定义 | 中 | 低——版本号只是字符串 | 第一版用 git commit hash 或 `"v-next"` |
| observed_at 几乎不可能做到字段级 | 高 | 中——大部分字段只能用 captured_at 近似 | DATA-L1D §10.3 已定义默认策略：fixture_metadata 可用 captured_at 近似；prematch_snapshot 需要 captured_at ≤ cutoff；其他拒绝 |
| adapter 性能过差导致 parser runtime 变慢 | 低 | 中 | adapter 只是格式转换，通常不会产生显著 overhead；但仍需在 L1E-2 做性能 smoke test |

### 15.2 全局回滚策略

如果 implementation 中途发现严重问题（比如 envelope 设计本身有缺陷），可以：

1. **回滚到旧 parser 输出。** 因为旧输出一直保留，feature engine 仍然可以消费旧输出。
2. **暂停 envelope 相关代码 PR。** 所有 L1E-1 ∼ L1E-9 都是独立的、可暂停的。
3. **重新评估 DATA-L1D 设计。** 如果 envelope 结构本身有问题，应该先修 DATA-L1D，再继续代码实现。
4. **不硬删文件。** 旧 legacy parser 代码、旧测试、旧 fixture 保留到 CLEANUP 任务明确授权。

---

## 16. 后续 PR 拆分建议

以下建议后续 PR 的拆分。每个 PR 都需要用户单独授权。**本 PR 不启动其中任何一个。**

### 16.1 建议的 PR 序列

| 顺序 | PR 名称 | 目标 | 允许路径 | 禁止路径 | 验收标准 | CI 预期 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | DATA-L1E-1: Envelope Schema | 定义 envelope 数据结构 | 新文件（envelope_schema.js 或 envelope_schema.json） | src/parsers/**, docs/data/**（不新写 data 文档）, tests/** | schema 文件存在，与 DATA-L1D §5 一致，通过 lint | 和 docs-only 类似的轻量 CI |
| 2 | DATA-L1E-2: Legacy Adapter Dry-Run | 旧输出 → envelope 格式（不改变 parser runtime） | adapter 文件 + 可选 schema 微调 | src/parsers/*Parser.js 的逻辑层 | adapter 在 dry-run 下能包装 fixture | unit test CI |
| 3 | DATA-L1E-3: Contract Mapper | field_contract_class mapper | mapper 文件 | feature engine, training, backtest | 所有已知字段都有 contract class | unit test CI |
| 4 | DATA-L1E-4: Timing Mapper | timing_class mapper | mapper 文件 | 同上 | 所有已知字段都有 timing class | unit test CI |
| 5 | DATA-L1E-5: Eligibility Dry-Run | model_eligibility mapper + dry-run audit | mapper + audit output | 同上 | dry-run 输出显示 eligibility distribution | unit test CI |
| 6 | DATA-L1E-6: Feature Eligibility Checker | feature engine 读 envelope 并 dry-run | feature engine 相关代码 | training, backtest, 旧 parser 输出删除 | feature engine 不改变行为但对 forbidden 字段输出 warnings | integration test + regression test CI |
| 7 | DATA-L1E-7: Training Cutoff Check | training 侧接入 cutoff safety | training 相关代码 | backtest 独立逻辑, 线上 prediction | training 不对 forbidden 字段拟合；无 regression | dry-run training CI |
| 8 | DATA-L1E-8: Replay Fixture Runner | 轻量级 replay runner | 新工具/脚本 | CI pipeline, src/parsers/**（不改 parser 逻辑） | runner 在 fixture 上跑 parser 并比较 envelope | 工具/脚本 CI |
| 9 | DATA-L1E-9: CI Compliance Check | CI 中增加 field-contract check | CI workflow 或 CI 脚本 | CODEOWNERS, branch protection, Gatekeeper | CI 检测未登记字段并 warning | 新增 CI job |

### 16.2 关键提醒

- **L1E-1 ∼ L1E-5 是安全区——只定义结构，不改变行为。**
- **L1E-6 是第一个"危险"PR——它会读取 feature engine 的输入并可能输出 warning。**
- **L1E-7 是第二个"危险"PR——它可能改变训练行为或发现历史泄露问题。**
- **L1E-8 ∼ L1E-9 是"验证/armor"PR——它们服务和验证前面 7 个 PR。**

---

## 17. 与 DATA-L1A / L1B / L1C / L1D 的关系

| 文档 | 角色 | 替代关系 | 本 PR 如何引用 |
| --- | --- | --- | --- |
| DATA-L1A | 审计报告——发现风险 | 不替代 | 引用其字段分类线索和 file inventory |
| DATA-L1B | 字段合同——规定能不能进模型 | 不替代 | implementation 直接映射 DATA-L1B 的 5 类到 envelope 的 field_contract_class |
| DATA-L1C | raw payload 保留策略——原始证据 | 不替代 | envelope.payload 信息与 DATA-L1C §5 metadata 对齐 |
| DATA-L1D | parser 标签设计——provenance + timing + eligibility | 不替代 | 本 PR 是实现 DATA-L1D 设计的施工计划 |
| DATA-L1E（本 PR） | implementation plan——施工计划 | 不替代以上任何文档 | 规划如何把设计转化为代码的每一步 |

```text
DATA-L1A → DATA-L1B → DATA-L1C → DATA-L1D → DATA-L1E
  审计       合同       保留策略     标签设计    施工计划

前 4 个文档定义了"要做什么"。
DATA-L1E 定义了"怎么做、分几步做、每一步验收什么"。
```

---

## 18. 本次明确不做事项

本 PR（DATA-L1E）只创建这一份 parser output envelope 实现计划文档。以下全部不做：

- 没有改代码
- 没有改测试
- 没有改 CI
- 没有改 Docker
- 没有改 DB / migration
- 没有改 scraper / collector
- 没有运行 FotMob 采集
- 没有访问真实 FotMob 网络接口
- 没有生成 raw payload 样本
- 没有写入数据目录
- 没有改 parser
- 没有运行 parser
- 没有改 feature
- 没有改 training
- 没有跑 backtest
- 没有碰 staging server
- 没有启动 DATA-L1E-code（即 L1E-1）
- 没有启动 DATA-L1F
- 没有启动 DATA-L2
- 没有启动 CLEANUP-L1A
- 没有启动 L3I
- 没有启动 L4
- 没有做 legacy 删除 / 移动 / 重命名

---

## 19. 下一步建议

Do not start automatically.

Recommended next task only after user confirmation:

- **DATA-L1E-1: FotMob Parser Output Envelope Schema**
  - 目标：创建 envelope 数据结构定义（不接入 parser runtime）。
  - 这是从 docs-only 到代码的第一小步。仍然是低风险——只定义 schema，不改变 parser 行为。
  - 如果用户希望先整理仓库文档，也可以在 DATA-L1E 合并后选择 CLEANUP-L1A。

但以上建议只供参考，不应自动启动。DATA-L1E 合并后具体做什么，由用户决定。
