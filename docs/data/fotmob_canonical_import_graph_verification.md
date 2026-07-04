# FotMob Canonical Import Graph Verification

- lifecycle: source-of-truth
- scope: docs-only, static import graph verification for FotMobRawParser
- parent documents: DATA-L1F (`docs/data/fotmob_existing_pipeline_triage_canonical_path.md`), DATA-L1F-1 (`docs/data/fotmob_canonical_pipeline_verification_plan.md`)
- branch: `docs/data-l1f-2a-fotmob-canonical-import-graph-verification`

---

## 1. 背景

DATA-L1F（PR #1700）通过只读审计给出了 medium confidence 的 canonical candidate path。
DATA-L1F-1（PR #1701）进一步拆解了验证清单，并明确指出 FotMobRawParser 是最大 gap：

> FotMobRawParser 有 contract、有测试、被 index.js 导出，但尚未确认有真实下游 consumer。

DATA-L1F-2A 的目标就是只读验证 FotMobRawParser 的 import graph——到底有没有 runtime 代码在用这个 parser。

**本文件不是** parser 实现、scraper 实现、envelope adapter、DB/migration。本文件不运行任何采集，不运行 parser，不改变 runtime 行为。本文件只做静态 import graph verification。

---

## 2. 审计方法

本次只读用了以下方法：

- `git ls-files` — 确认目标文件存在
- `git grep` — 搜索 FotMobRawParser / parseFotMobRaw / fotmob_live_v1 等关键符号的全仓库引用
- `git grep` — 搜索 require/import 引用关系（CommonJS / ESM 变体）
- `sed -n` / `cat` / `head` — 只读查看关键文件内容
- `git log` — 查看相关文件的历史变更
- 只读查看 `src/**`、`tests/**`、`scripts/**`、`docs/**`、`package.json`

明确未做：

- 没有运行 FotMob 网络访问
- 没有运行 scraper / collector / browser
- 没有运行 parser
- 没有运行 DB / migration
- 没有写 raw payload
- 没有跑 training / backtest / feature engine
- 没有修改 src / tests / scripts 中的任何文件

---

## 3. 审计范围

### 3.1 重点符号

| 符号 | 说明 |
| --- | --- |
| `FotMobRawParser` | 类/模块名（CommonJS 导出） |
| `parseFotMobRaw` | 公共入口函数名 |
| `src/parsers/fotmob/index.js` | parser 模块统一入口 |
| `fotmob_live_v1` | FotMobRawParser 声称处理的 data_version |
| `fotmob_html_hyd_v1` | FotMobRawDetailFetcher 产出的 data_version |
| `fotmob_pageprops_v2` | RawMatchDataVersionSelector 最高优先级 data_version |

### 3.2 重点路径

| 路径 | 角色 |
| --- | --- |
| `src/parsers/fotmob/FotMobRawParser.js` | 被审计主体 |
| `src/parsers/fotmob/index.js` | parser 统一导出入口 |
| `src/parsers/fotmob/NextDataParser.js` | 广泛使用的主线 parser（对比参照） |
| `src/infrastructure/services/FotMobRawDetailFetcher.js` | 采集器 |
| `src/infrastructure/services/RawMatchDataVersionSelector.js` | data_version 优先级选择器 |
| `tests/unit/fotmob_raw_parser.test.js` | FotMobRawParser 单元测试 |
| `docs/data/FOTMOB_RAW_PARSER_CONTRACT.md` | parser contract |
| `scripts/**` | ops 脚本 |

---

## 4. Direct import graph findings

### 4.1 证据表格

| # | 引用方文件 | 引用类型 | 引用符号 | 引用上下文 | 是否 runtime src | 是否 test | 是否 script | 是否 docs | 证据摘要 | 判断 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `src/parsers/fotmob/index.js:15` | direct_require_file | `parseFotMobRaw` | `const { parseFotMobRaw } = require('./FotMobRawParser')` | **否**（这是导出方自己） | 否 | 否 | 否 | index.js 是 parser 模块入口，它 require 了 FotMobRawParser 并导出 parseFotMobRaw | **index_export_only** |
| 2 | `tests/unit/fotmob_raw_parser.test.js:16` | direct_require_file | `parseFotMobRaw`, `_internals` | `const { parseFotMobRaw, _internals } = require('../../src/parsers/fotmob/FotMobRawParser')` | 否 | **是** | 否 | 否 | 单元测试文件，842 行，验证 parser 行为 | **test_only** |
| 3 | `docs/data/FOTMOB_RAW_PARSER_CONTRACT.md` 等多份文档 | docs_only | `FotMobRawParser` | 文档中提到 FotMobRawParser 作为 canonical candidate | 否 | 否 | 否 | **是** | 10+ 份文档引用此文件名/模块名，用于审计和规划 | **docs_only** |
| 4 | `docs/_reports/fotmob_parser_dry_run_*.md` 等报告 | docs_only | `FotMobRawParser` | 历史 dry-run 报告中提到 FotMobRawParser | 否 | 否 | 否 | **是** | 历史 dry-run 报告（2026-06），记录了 parser 在 dry-run 环境下的行为 | **docs_only** |
| 5 | `src/infrastructure/harvesters/strategies/FotMobStrategy.js:20` | direct_require_file | `extractFromHtml`, `transformToApiFormat` (来自 NextDataParser) | `const { extractFromHtml, transformToApiFormat } = require('../../../parsers/fotmob/NextDataParser')` | **是** | 否 | 否 | 否 | 这是 src/ 中唯一引用 parsers/fotmob 的 runtime 模块，但它只引用 NextDataParser，**不引用 FotMobRawParser** | **引用了别的 parser，与本审计无关** |

### 4.2 关键结论

**在 `src/**` 中，没有任何 runtime 模块直接 import/require FotMobRawParser 或 parseFotMobRaw。**

唯一的 `src/` 引用是 `FotMobStrategy.js` 引用 `NextDataParser`——它和 FotMobRawParser 是完全不同的两个 parser，处理不同的 data_version。

### 4.3 区分说明

必须明确区分以下概念：

- **`src/parsers/fotmob/index.js` 导出 `parseFotMobRaw`** ≠ 下游 runtime 使用 FotMobRawParser。导出只表示"这个函数被公开了"，不表示"有代码在用它"。
- **tests 引用** ≠ runtime 使用。测试能证明 parser 行为正确，但不能证明它在生产中被调用。
- **docs 提到** ≠ runtime 使用。文档中的引用是规划和审计的产物，不是执行路径。
- **scripts 引用** ≠ 一定是生产主线。需要判断脚本是否是当前活跃入口。

---

## 5. Indirect import graph findings

### 5.1 索引文件引用链

`src/parsers/fotmob/index.js` 是 parser 模块的统一入口，它导出了：

```javascript
module.exports = {
    ...NextDataParser,       // extractFromHtml, transformToApiFormat, validateNextDataStructure
    ...XGExtractor,          // extractXG, extractPossession, extractAllStats, validateXG
    LeagueParser,
    TeamParser,
    MatchParser,
    PlayerParser,
    MatchStatsParser,
    parseFotMobRaw,          // ← FotMobRawParser 的唯一公共入口
    ApiSniffer,              // optional
    ResponseInterceptor,     // optional
    interceptMatchDetails,   // optional
    TARGET_PATTERNS,         // optional
    HTML_PATTERNS            // optional
};
```

### 5.2 谁引用了 index.js？

**全仓库范围搜索：没有任何 `src/**` 或 `tests/**` 或 `scripts/**` 模块通过 `require('../../src/parsers/fotmob')` 或类似路径引用 index.js。**

实际使用的模式是直接引用具体文件：

| 引用方 | 引用路径 | 引用符号 |
| --- | --- | --- |
| `src/infrastructure/harvesters/strategies/FotMobStrategy.js` | `require('../../../parsers/fotmob/NextDataParser')` | `extractFromHtml`, `transformToApiFormat` |
| 10+ 个 ops scripts | `require('../../src/parsers/fotmob/NextDataParser')` | `extractFromHtml`, `transformToApiFormat` |
| `tests/unit/fotmob_raw_parser.test.js` | `require('../../src/parsers/fotmob/FotMobRawParser')` | `parseFotMobRaw`, `_internals` |
| 多个测试文件 | `require('../../src/parsers/fotmob/NextDataParser')` | 各种 NextDataParser 导出 |
| `tests/unit/collectors/fotmob/FotMobThinParsers.test.js` | `require('../../../../src/parsers/fotmob/{League,Match,MatchStats,Player,Team}Parser')` | 各 thin parser |

### 5.3 间接使用结论

**是否存在 confirmed indirect consumer of FotMobRawParser?**

**回答：NO。**

没有模块通过 index.js 间接引用 `parseFotMobRaw`。索引文件确实导出了这个函数，但没有任何代码通过索引文件来使用它。所有引用方都是直接引用自己需要的具体文件（主要是 NextDataParser）。

**是否存在 destructuring import 但未用 FotMobRawParser?**

不适用——因为根本没有任何代码 destructuring import index.js。

---

## 6. Script / ops consumer findings

### 6.1 是否有 scripts/** 使用 FotMobRawParser / parseFotMobRaw?

**没有。**

全仓库搜索 `FotMobRawParser` 和 `parseFotMobRaw` 在 `scripts/` 中：零匹配。

所有 ops scripts 中引用 `parsers/fotmob` 的都是引用 `NextDataParser`（`extractFromHtml`、`transformToApiFormat`）。

### 6.2 scripts 中 `fotmob_live_v1` 的使用方式

多个 scripts 中出现了 `fotmob_live_v1`，但全部作为 **DB 查询中的 data_version 字符串**，不是作为 parser import：

| 脚本 | 使用方式 |
| --- | --- |
| `scripts/ops/audit_fotmob_retained_raw_quality.js` | `data_version='fotmob_live_v1'` — 只读审计 |
| `scripts/ops/l2_guarded_reconciliation_write.js` | `data_version='fotmob_live_v1'` — L2 reconciliation |
| `scripts/ops/l2_pending_transition_preview.js` | `data_version='fotmob_live_v1'` — transition preview |
| `scripts/ops/l2_raw_exists_pending_anomaly_audit.js` | `data_version='fotmob_live_v1'` — anomaly audit |
| `scripts/ops/l2_reconciliation_preview.js` | `data_version='fotmob_live_v1'` — reconciliation preview |
| `scripts/ops/matches_labeling_backfill_dry_run.js` | `data_version='fotmob_live_v1'` — backfill dry-run |
| `scripts/ops/score_backfill_dry_run.js` | `data_version='fotmob_live_v1'` — score backfill |
| `scripts/ops/n3_live_fotmob_raw_retain.js` | `dataVersion: 'fotmob_live_v1'` — 采集配置，但也 import NextDataParser |

**关键观察：这些脚本知道 DB 里有 `fotmob_live_v1` 的 raw 数据，但它们处理这些数据时用的是 SQL 查询 + NextDataParser，而不是 FotMobRawParser。**

### 6.3 这些 scripts 是否是当前活跃入口?

大部分 script 是 L2 / reconciliation / backfill / audit 类——它们是运维和审计脚本，不是生产 pipeline 入口。

- `n3_live_fotmob_raw_retain.js` 是 N3 live 采集脚本（较接近运行时采集），但它使用 `NextDataParser`，不使用 `FotMobRawParser`。
- `single_live_fotmob_raw_ingest_smoke.js` 是 smoke test 脚本，同样使用 `NextDataParser`。

### 6.4 Script consumer 结论

**ops script consumer 不能作为 FotMobRawParser 的 runtime 使用证据。** 没有任何 script 使用 FotMobRawParser 或 parseFotMobRaw。scripts 中使用的 parser 是 NextDataParser（用于 extractFromHtml + transformToApiFormat），和 FotMobRawParser 是不同的模块。

---

## 7. Test / docs evidence

### 7.1 测试证据

| 测试文件 | 能证明什么 | 不能证明什么 |
| --- | --- | --- |
| `tests/unit/fotmob_raw_parser.test.js` (842行) | 1. `parseFotMobRaw` 函数存在且行为可验证。2. 测试覆盖了 match/team/stats/lineup/events/shotmap/playerStats 各段提取。3. 测试使用了基于真实 retained raw payload 的 fixture。4. `_internals` 的辅助函数也可测试。 | 1. 不能证明 parser 在生产中被调用。2. 不能证明 parser 的下游有 feature/training/backtest 消费者。3. 不能证明 parser 输出的数据进入了任何模型。 |

### 7.2 文档/contract 证据

| 文档 | 能证明什么 | 不能证明什么 |
| --- | --- | --- |
| `docs/data/FOTMOB_RAW_PARSER_CONTRACT.md` | 1. `fotmob_live_v1` parser 的输入/输出 shape 有明确定义。2. 基于 N=4 个真实 retained raw payload 验证。3. 定义了 8 个输出段（general/header/content/stats/lineup/events/shotmap/playerStats）。 | 1. 不能证明 parser 在生产中被调用。2. contract 定义的是"设计目标"，不是"实际使用"。3. N=4 的 retained raw 只能证明 parser 对这 4 条数据有效。 |

### 7.3 关键声明

**测试和 contract 能证明 parser shape/contract 存在。测试和 contract 不能单独证明 parser 已被 runtime 使用。**

---

## 8. Data version relationship check

### 8.1 各模块的 data_version 标注

| 模块 | data_version | 角色 |
| --- | --- | --- |
| `FotMobRawParser.js` | `fotmob_live_v1` | 解析器声称处理的版本。硬编码在 `meta.dataVersion` 输出中（第 410 行）。 |
| `FotMobRawDetailFetcher.js` | `fotmob_html_hyd_v1`（推断） | 采集器。虽然代码中没有直接硬编码 data_version 字符串在显眼位置，但其 metadata 字段命名（`_meta.data_version`）和 hash strategy（`stable_raw_payload_v1`）表明它产出 html_hydration 格式的 raw payload。 |
| `RawMatchDataVersionSelector.js` | 优先级：`fotmob_pageprops_v2` > `fotmob_html_hyd_v1` | 版本选择器。**注意：`fotmob_live_v1` 不在 canonical 优先级列表中。** 如果输入 `fotmob_live_v1`，`classifyRawDataVersion()` 返回 `'unknown'`，`isCanonicalFotMobVersion()` 返回 `false`。 |

### 8.2 版本关系图

```text
RawMatchDataVersionSelector 优先级:
  fotmob_pageprops_v2 (canonical, 最高优先级) → 无独立 parser 实现
  fotmob_html_hyd_v1 (canonical)               → FotMobRawDetailFetcher 产出，NextDataParser 处理
  PHASE4.43_SYNTHETIC (legacy, 排除)
  PHASE4.23 (legacy, 排除)

不在优先级列表中的版本:
  fotmob_live_v1 → FotMobRawParser 声称处理，但被 version selector 归为 unknown
```

### 8.3 版本 mismatch 结论

**存在明确的 data_version mismatch：**

1. `FotMobRawParser` 处理的 `fotmob_live_v1` **不在** `RawMatchDataVersionSelector` 的 canonical 优先级中。
2. `RawMatchDataVersionSelector` 把 `fotmob_live_v1` 归类为 `unknown`（非 canonical）。
3. `FotMobRawDetailFetcher` 产出 `fotmob_html_hyd_v1`，这与 `FotMobRawParser` 的输入版本 `fotmob_live_v1` **不是同一个版本**。

**这意味着 FotMobRawParser 和 FotMobRawDetailFetcher 不是同一条链路：**
- Fetcher 产出 `html_hyd_v1` → 被 NextDataParser 处理 → 这条链路有大量证据（scripts + runtime src 引用）。
- FotMobRawParser 处理 `live_v1` → 这条链路的输入来源和下游消费者都不明确。

**是否存在 data_version mismatch / unresolved mapping?**

**YES。** `fotmob_live_v1`（FotMobRawParser 的输入版本）和 `fotmob_html_hyd_v1`（FotMobRawDetailFetcher 的输出版本）是不同的版本，且 version selector 不把 `fotmob_live_v1` 视为 canonical。这三者之间的映射关系未在静态代码中解决。

---

## 9. Classification of FotMobRawParser

### 9.1 分类

**`exported_but_no_downstream_consumer`**

FotMobRawParser 是一个完整实现的、有 contract 的、有测试的、被 index.js 导出的 parser 模块。但在本次只读 import graph 审计中，没有在 `src/**` 中找到任何 runtime 模块直接或间接使用它。

### 9.2 判断依据

| 条件 | 满足? | 证据 |
| --- | --- | --- |
| 有 runtime src direct consumer | **NO** | `git grep` 在 `src/` 中搜索 `FotMobRawParser\|parseFotMobRaw`：只有 `index.js`（导出方自己）匹配 |
| 有 runtime src indirect consumer | **NO** | 没有任何 `src/` 模块 require index.js 来间接使用 parseFotMobRaw |
| 有 script consumer | **NO** | 没有任何 script 导入 FotMobRawParser。scripts 使用的 parser 是 NextDataParser |
| 被 index.js 导出 | **YES** | `src/parsers/fotmob/index.js:15,52` |
| 有单元测试 | **YES** | `tests/unit/fotmob_raw_parser.test.js` (842行) |
| 有 contract 文档 | **YES** | `docs/data/FOTMOB_RAW_PARSER_CONTRACT.md` |
| 有 dry-run 验证 | **YES** | 多次 historical dry-run 报告（2026-06） |

### 9.3 当前 confidence

**medium**（维持 DATA-L1F 的评级，不能提升到 high）

判断逻辑：

- 如果找到 src runtime direct/indirect consumer → confidence 可以提升到 high。
- 现在只有 index.js + tests + docs → confidence 不能提升，仍然是 medium。
- 没有 scripts 使用 → 不能提供 supporting evidence。
- data_version 与 version selector 不匹配 → 降低了这条链路是当前主线的可能性。

---

## 10. Impact on DATA-L1E-2

### 10.1 当前状态

**FotMobRawParser 没有 confirmed runtime consumer。**

因此：

- **DATA-L1E-2 不应直接包 FotMobRawParser。**
- 真实被使用的 parser 是 `NextDataParser`（被 src runtime 和 10+ ops scripts 引用）。
- 如果要做 adapter，应该先确认 NextDataParser 或其他 thin parsers 的输出 shape，而不是 FotMobRawParser。
- **DATA-L1E-2 remains blocked.**

### 10.2 为什么不建议直接包 FotMobRawParser

1. FotMobRawParser 处理的 `fotmob_live_v1` 是一个不被 version selector 视为 canonical 的版本。
2. 没有任何 runtime 代码调用 `parseFotMobRaw()`。包一个没人调用的函数没有意义。
3. 真实在跑的 parser 链路是 `NextDataParser.extractFromHtml() → transformToApiFormat()`，这条链路有 confirmed runtime consumer（`FotMobStrategy.js`）和 10+ ops scripts。
4. 如果 envelope 要接真实链路，应该研究 NextDataParser 的输出 shape，而不是 FotMobRawParser。

### 10.3 重要声明

**本 PR 不启动 DATA-L1E-2。**

---

## 11. Recommended next step

根据审计结果，推荐 **选项 B**：

```text
DATA-L1F-2B: FotMob Legacy Output Shape Fixture Audit
或
DATA-L1F-2C: FotMob Runtime Entry Point Identification
```

理由：

- FotMobRawParser 没有 runtime consumer，不能作为 envelope 接入点。
- 真实被使用的 parser 是 NextDataParser（有 confirmed runtime consumer 在 `FotMobStrategy.js`）。
- 下一步应该确认 NextDataParser + thin parsers（Match/Team/Player/League/MatchStats）的实际输出 shape，或者确认 feature engine 到底消费哪种 parser 输出。
- 只有确认了真实的下游 consumer 和 parser 输出 shape，才能确定 envelope adapter 应该包在哪里。

**Do not start automatically.**

**Recommended next task only after user confirmation:**

- **DATA-L1F-2B**: 对 NextDataParser + thin parsers 的实际输出做 static shape audit（只读查看代码，确认哪些字段是实际输出的，哪些 parser 被 feature engine 实际引用）。
- **DATA-L1F-2C**: 如果 DATA-L1F-2B 无法确认 runtime entry point，需要专门追踪 feature engine 的 import graph，确认 feature 层实际消费的 parser 输出格式。

**DATA-L1E-2 remains blocked unless the user explicitly accepts the verified canonical path.**

---

## 12. Explicit non-goals

本次 DATA-L1F-2A 明确没有做以下任何事情：

- 没有改 `src/**`
- 没有改 `tests/**`
- 没有改 `scripts/**`
- 没有改 `.github/**`
- 没有改 Docker
- 没有改 DB / migration
- 没有运行 FotMob 网络访问
- 没有运行采集
- 没有运行 parser
- 没有写 raw payload
- 没有改 feature
- 没有改 training
- 没有跑 backtest
- 没有接 envelope
- 没有启动 DATA-L1E-2
- 没有启动 DATA-L1F-2B
- 没有启动 DATA-L2
- 没有启动 CLEANUP-L1A
- 没有启动 L3I / L4
- 没有删除 / 移动 / 重命名 legacy 文件

---

## 13. 审计证据清单

以下是本次审计使用的全部只读命令及其关键发现摘要：

| 命令 | 关键发现 |
| --- | --- |
| `git grep "FotMobRawParser\|parseFotMobRaw" -- src` | 只在 `index.js` 中找到（导出方自己），无 runtime consumer |
| `git grep "require.*parsers/fotmob" -- src` | 只在 `FotMobStrategy.js:20` 中找到，引用的是 `NextDataParser` |
| `git grep "FotMobRawParser\|parseFotMobRaw" -- scripts` | **零匹配** |
| `git grep "FotMobRawParser\|parseFotMobRaw" -- tests` | 只在 `fotmob_raw_parser.test.js:16` 中找到 |
| `git grep "FotMobRawParser\|parseFotMobRaw" -- docs` | 10+ 份文档引用，全部是规划和审计文档 |
| `git grep "parsers/fotmob" -- scripts` | 10+ scripts 引用，全部引用 `NextDataParser`（`extractFromHtml`/`transformToApiFormat`） |
| `git grep "fotmob_live_v1" -- src` | 在 `Persistence.js`、`MarathonService.js`、`MatchLabelingGovernance.js`、`FotMobRawParser.js` 中作为 data_version 字符串出现 |
| `git log --oneline --max-count=30 -- src/parsers/fotmob/FotMobRawParser.js` | 6 个提交：初始实现 (#1491/#1492)、ESLint fix、events mapping fix、synthetic-id policy fix |
| 只读查看 `RawMatchDataVersionSelector.js` | `fotmob_live_v1` 不在 canonical 优先级中，会被归为 unknown |
| 只读查看 `FotMobRawParser.js` | 标注 `dataVersion: 'fotmob_live_v1'`，纯函数，输出 8 段结构 |
| 只读查看 `index.js` | 导出 `parseFotMobRaw`，但全仓库无消费者 |

---

## 14. FotMobRawParser 相关 git 历史

```
3e0ef66 fix(data): handle FotMob events without native ids
4c40986 fix(data): map FotMob raw event fields from real payloads
3c4dfd3 fix(data): resolve ESLint errors in FotMobRawParser.js (#1492)
a3e13e4 feat(data): implement FotMobRawParser for fotmob_live_v1 pure function parsing (#1492)
36f42c4 docs(data): define FotMob raw parser contract for fotmob_live_v1 (#1491)
```

FotMobRawParser 的最后一次修改是 `3e0ef66`（synthetic-id policy fix），之后没有再被修改。这些提交都是 parser 自身的实现和完善，没有引入下游 consumer。

---

## 15. 与 NextDataParser 的对比

作为参照，`NextDataParser.js` 的 import graph 截然不同：

| 维度 | FotMobRawParser | NextDataParser |
| --- | --- | --- |
| runtime src consumer | **0** | **1** (`FotMobStrategy.js`) |
| ops script consumer | **0** | **10+** |
| test consumer | 1 | 5+ |
| 被 index.js 导出 | 是 | 是 |
| data_version | `fotmob_live_v1` | 处理 `fotmob_html_hyd_v1`（通过 transformToApiFormat） |
| version selector 认可 | **否**（归为 unknown） | 是（`fotmob_html_hyd_v1` 是 canonical） |
| confidence | medium | **high** |

这说明：**本仓库里真正在被使用的 FotMob parser 主线是 NextDataParser，不是 FotMobRawParser。**
