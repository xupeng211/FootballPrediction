# FotMob Existing Pipeline Triage and Canonical Path Selection

- lifecycle: source-of-truth
- scope: docs-only, read-only inventory and canonical path selection for existing FotMob pipeline
- parent documents: DATA-L1A, DATA-L1B, DATA-L1C, DATA-L1D, DATA-L1E, DATA-L1E-1
- branch: `docs/data-l1f-existing-fotmob-pipeline-triage-canonical-path`

---

## 1. 背景

DATA-L1A 已经发现 FotMob 赛前/赛后字段边界风险。DATA-L1B 已经定义字段合同。DATA-L1C 已经定义 raw payload 保留与回放策略。DATA-L1D 已经设计 parser 字段来源与时间标签。DATA-L1E 已经规划 parser output envelope 怎么分阶段落地。DATA-L1E-1 已经新增 envelope schema（`FotMobParserOutputEnvelope.js`），但**没有接入 parser runtime**。

DATA-L1F 的目标不是继续写新代码，而是回到现有仓库，筛出真正的 FotMob 数据主线。

本文件是**只读审计和 canonical path selection**。本文件不是 parser 实现、scraper 实现、envelope adapter、DB/migration。本文件不运行任何采集，不运行 parser，不改变 runtime 行为。

---

## 2. 为什么现在必须做 DATA-L1F

仓库里已经有大量 FotMob 相关代码——10 个 parser 文件、6 个 infrastructure service 文件、1 个 API client、1 个 harvester strategy、150+ 个 ops scripts、140+ 个测试文件、400+ 个文档文件。如果不先确认哪条旧代码链路才是主线，就直接做 DATA-L1E-2 adapter，可能会把 envelope 接到错误的旧 parser 或实验代码上。这会导致后续代码越包越偏。

用大白话说：

- **DATA-L1E-1** = 做好了包装盒规格（envelope schema 文件存在，但不接 parser）
- **DATA-L1F** = 先去仓库里挑出真正要包装的零件（哪个 parser、哪个 fetcher 是主线）
- **DATA-L1E-2** = 等挑好零件以后，才尝试把旧输出装进盒子里（adapter dry-run）

**DATA-L1E-2 应该保持 blocked，直到 DATA-L1F 选出 canonical existing FotMob pipeline / parser path。**

---

## 3. 审计方法

本次只读用了以下搜索方法：

- `git ls-files` + `rg` — 按 FotMob / raw / pageProps / parser / payload 等关键词搜索
- `git grep` — 搜索 require/import 引用关系、类名、函数名
- `sed -n` / `cat` / `head` / `tail` — 只读查看文件内容
- `git log` — 查看 FotMob 相关文件的历史变更
- 只读查看 `src/parsers/fotmob/*`、`src/infrastructure/**`、`docs/data/*`、`tests/unit/**`

明确未做：

- 没有运行 FotMob 网络访问
- 没有运行 scraper / collector / browser
- 没有运行 parser
- 没有运行 DB / migration
- 没有写 raw payload
- 没有跑 training / backtest / feature engine
- 没有修改 src / tests / scripts 中的任何文件

---

## 4. FotMob 相关代码 inventory

### 4.1 src/parsers/fotmob/ — 解析器核心

| 文件路径 | 类别 | 可能角色 | 是否像 active path | 证据 | 风险 | 当前建议状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `FotMobRawParser.js` (436行) | parser | `fotmob_live_v1` raw payload 纯函数解析器 | **是，最像主线** | 有完整 contract（`FOTMOB_RAW_PARSER_CONTRACT.md`）；输出 match/teams/stats/lineup/events/shotmap/playerStats；被 `index.js` 正式导出；有独立单元测试 | 无字段级 timing label；能解析赛后字段（xG/shots/events）但不标注 | **canonical_candidate** |
| `NextDataParser.js` (223行) | pageProps / __NEXT_DATA__ extractor | 从 FotMob 网页 HTML / SSR 提取 __NEXT_DATA__ 并转为 API 兼容格式 | **是，关键支撑** | 被 `FotMobRawDetailFetcher`、多个 ops scripts、`MatchParser`、`LeagueParser`、`FotMobStrategy` 引用；`transformToApiFormat()` 是通用转换入口 | 依赖浏览器（Playwright）版本需要 page 对象；纯函数版 `extractFromHtml` 可用 | **active_supporting_candidate** |
| `MatchParser.js` (33行) | thin parser | 从 pageProps/API 数据中提取 match 信息 | **是，thin parser 一员** | 被 `FotMobThinParsers.test.js` 测试；通过 `index.js` 导出；使用 `NextDataParser.transformToApiFormat` | 极薄，主要做字段映射和 fallback | **active_supporting_candidate** |
| `PlayerParser.js` (40行) | thin parser | 从 lineup 中提取球员信息 | 是，thin parser | 被测试覆盖；通过 `index.js` 导出 | 薄，功能单一 | **active_supporting_candidate** |
| `TeamParser.js` (28行) | thin parser | 提取球队信息（home/away） | 是，thin parser | 被 `MatchParser` 引用；通过 `index.js` 导出 | 薄 | **active_supporting_candidate** |
| `LeagueParser.js` (31行) | thin parser | 提取联赛元数据 | 是，thin parser | 被测试覆盖；通过 `index.js` 导出 | 薄 | **active_supporting_candidate** |
| `MatchStatsParser.js` (46行) | stats extractor | 提取比赛统计数据 + xG/possession | 是，但有风险 | 被测试覆盖；通过 `index.js` 导出；内部调用 `XGExtractor.extractAllStats` | **提取 xG 等赛后字段，无 timing label** | **active_supporting_candidate（需 timing 标签后才能安全使用）** |
| `XGExtractor.js` (152行) | xG/post-match extractor | 提取 xG、possession、stats | 是，但高风险 | 被 `MatchStatsParser` 引用；有独立单元测试 | **提取的 xG/possession 是赛后数据，混入赛前模型直接泄露** | **active_supporting_candidate（只应在 envelope forbids 下使用）** |
| `FotMobParserOutputEnvelope.js` (381行) | envelope schema | 定义未来 parser output envelope 常量、工厂、校验函数 | **是，DATA-L1E-1 产物** | 最近合并（PR #1699），先于本 PR；有独立单元测试 | 目前是纯 schema，未接入任何 parser runtime | **canonical_candidate（schema 阶段）** |
| `index.js` (62行) | module entry | 统一导出所有 parser | 是 | 聚合所有 parser 导出；包含 optional require 的 CloudflareDetector、ApiSniffer、ResponseInterceptor | optional require 的模块可能不存在（V175 实验） | **active_supporting_candidate** |

### 4.2 src/infrastructure/ — 采集、路由、身份

| 文件路径 | 类别 | 可能角色 | 是否像 active path | 证据 | 风险 | 当前建议状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `FotMobRawDetailFetcher.js` (710行) | fetcher / raw payload builder | html_hydration raw detail 采集、stable raw payload 构建、hash 计算 | **是，核心采集入口** | 被 3+ 个 ops scripts 引用（n3_live_fotmob_raw_retain.js、single_live_fotmob_raw_ingest_smoke.js、l2_remaining_raw_match_data_acquisition_preflight.js）；构建 stable raw payload + hash；阻止 body save/print、browser、proxy、retry；有完整单元测试 | 需要注入 fetchFn 依赖；实际运行会访问 FotMob 网络 | **canonical_candidate** |
| `FotMobApiClient.js` (707行) | API client | matchDetails API / proxy agent / browser bootstrap | 是，但能力过大 | 被 `FotMobStrategy.js` 引用；含 browser/proxy/anti-bot 能力 | browser bootstrap、proxy agent、cookie/session 管理——这些是高风险能力 | **do_not_touch_for_now** |
| `FotMobStrategy.js` (956行) | harvester strategy | API-first → browser fallback → NextData → DOM fallback 多策略数据提取 | 是，但过于复杂 | 引用 `FotMobApiClient` 和 `NextDataParser`；含完整的 harvest pipeline | 等于把所有采集路径包在一个文件里；API-first 策略可能绕过 safe fetcher 的安全限制 | **do_not_touch_for_now** |
| `FotMobExtractor.js` (360行) | browser extractor | 浏览器自动化——访问 FotMob 赛程页、滚动加载、提取 __NEXT_DATA__、DOM 扫描 | **可能 legacy/experimental** | 代码内标注 V6.7.5/V6.7.8/V6.7.9；需要 browserProvider + makeStealthRequest + networkInterceptor；类名 HOUND-SOUL 暗示是实验性采集工具 | 依赖浏览器（Playwright）；全量 DOM 扫描可能不稳定 | **legacy_candidate / experimental_candidate** |
| `FotMobDetailRouteSelector.js` (346行) | route selector | 多路由策略选择器 | 是，但复杂 | 负责计划/执行 route、block signal、fallback route | 与 FotMobRawDetailFetcher 有重叠但不完全一致 | **active_supporting_candidate** |
| `FotMobRouteIdentityReconciler.js` (1355行) | identity reconciler | 比赛身份一致性验证（requested vs observed external_id） | 是 | 被 `FotMobRawDetailFetcher` 引用；含 fixture identity guard | 文件很大，逻辑复杂但不影响 parser 选择 | **active_supporting_candidate** |
| `FotMobSourceInventoryAdapter.js` (422行) | source inventory adapter | 源库存适配器 | unknown | 文件名显示用于 source inventory | 本次未深入审计 | **unknown** |
| `FotMobComplianceMode.js` (40行) | compliance | 合规模式解析 | 是 | 被 `FotMobStrategy` 引用 | 文件很小 | **active_supporting_candidate** |

### 4.3 src/feature_engine/ — 特征工程

| 文件路径 | 类别 | 可能角色 | 是否像 active path | 证据 | 风险 | 当前建议状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `FotMobSchemaGuard.js` (152行) | schema guard | key shape diff guard（检测 schema 变化） | 是，但辅助 | 被 `generate_fotmob_collection_report.js` 和 `smelter/index.js` 引用；有独立测试 | 只检测 key shape，不做 timing guard | **active_supporting_candidate** |

### 4.4 src/infrastructure/shared/helpers/

| 文件路径 | 类别 | 可能角色 | 是否像 active path | 证据 | 风险 | 当前建议状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `fotMobExtractionHelpers.js` | extraction helpers | DOM 扫描、league data 提取辅助 | 是 | 被 `FotMobExtractor.js` 引用 | 服务于 browser extractor | **legacy_candidate** |

### 4.5 数据版本选择器

| 文件路径 | 类别 | 可能角色 | 是否像 active path | 证据 | 风险 | 当前建议状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `RawMatchDataVersionSelector.js` (168行) | version selector | 按 `data_version` 选择 canonical raw | **是，关键枢纽** | 定义了 4 种 data_version；优先 `fotmob_pageprops_v2` > `fotmob_html_hyd_v1`；排除 synthetic/unknown | pageprops_v2 列为最高优先级但本次未找到对应的独立 parser | **canonical_candidate** |

### 4.6 测试文件摘要

| 类别 | 关键测试文件 | 说明 |
| --- | --- | --- |
| parser | `tests/unit/fotmob_raw_parser.test.js` | FotMobRawParser 解析测试，含 finished/score/xG 样例 |
| parser | `tests/unit/parsers/fotmob/FotMobParserOutputEnvelope.test.js` | Envelope schema 单元测试（最新） |
| parser | `tests/unit/XGExtractor.test.js` | xG/possession 提取测试 |
| parser | `tests/unit/collectors/fotmob/FotMobThinParsers.test.js` | Thin parsers 集成测试 |
| fetcher | `tests/unit/FotMobRawDetailFetcher.test.js` | Fetcher safety tests |
| guard | `tests/unit/collectors/fotmob/FotMobSchemaGuard.test.js` | Schema guard 测试 |
| legacy | `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/parsers/fotmob/CloudflareDetector.test.js.disabled` | 已禁用的旧测试 |

大量 ADG/ligue1 历史测试（100+ 个）不再逐一列出——它们是 Ligue 1 历史 ADG 操作的产物，不是当前 parser pipeline 的测试。

### 4.7 文档和配置摘要

| 类别 | 关键文件 | 说明 |
| --- | --- | --- |
| current-state | `docs/data/FOTMOB_CURRENT_STATE.md` | FotMob 当前状态 |
| current-state | `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md` | Retained raw 状态 |
| contract | `docs/data/FOTMOB_RAW_PARSER_CONTRACT.md` | `fotmob_live_v1` parser contract |
| contract | `docs/data/fotmob_prematch_field_contract.md` (DATA-L1B) | 字段合同 |
| design | `docs/data/fotmob_parser_field_provenance_timing_labels_design.md` (DATA-L1D) | 标签设计 |
| plan | `docs/data/fotmob_parser_output_envelope_implementation_plan.md` (DATA-L1E) | 分阶段实现计划 |
| policy | `docs/data/fotmob_raw_payload_retention_replay_policy.md` (DATA-L1C) | Raw payload 保留策略 |
| audit | `docs/_reports/data_l1a_fotmob_prematch_boundary_audit.md` (DATA-L1A) | 边界审计 |
| config | `configs/data/fotmob_n3_raw_retain_candidates.json` | Raw retain candidate 配置 |
| migration | `database/migrations/V26.5__create_fotmob_raw_match_payloads.sql` | DB schema（禁改禁跑） |
| migration | `database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql` | 旧 DB schema（禁改禁跑） |

### 4.8 脚本文件摘要

脚本文件数量很大（150+ 个），按类型分组：

| 类型 | 数量 | 代表文件 | 说明 |
| --- | --- | --- | --- |
| Ligue1 ADG 历史 | ~80 | `fotmob_ligue1_adg*` | Ligue 1 校正源库存、身份映射、probe、mutation 历史操作 |
| 端点探针 | ~15 | `fotmob_controlled_*_no_write*` | endpoint/json/hydration/match_detail 探针（no-write） |
| hydration/SSR 分析 | ~10 | `fotmob_*_hydration_*` | HTML hydration 结构分析 |
| raw 采集 | ~10 | `fotmob_*_raw_*` | raw payload capture/storage/review/audit |
| 身份/路由 | ~8 | `fotmob_*_identity_*`, `fotmob_*_route_*` | 身份映射、路由验证 |
| live fetch | ~6 | `fotmob_*_live_fetch_*` | 实时抓取（含 authorization gate） |
| 其他 | ~20 | `n3_live_fotmob_raw_retain.js`、`single_live_fotmob_raw_ingest_smoke.js` 等 | 采集入口、报告生成 |

**本次没有运行任何脚本。所有脚本均为只读参考。**

---

## 5. 现有 FotMob pipeline 候选链路

### 5.1 候选链路总览

仓库中存在**两条平行的 FotMob 数据采集链路**，加上一个**统一的 raw payload 存储层**和**两套 parser 系统**：

```text
链路 A（API 直连）:
FotMobApiClient（matchDetails API）
  → raw JSON response
    → FotMobRawParser（纯函数解析）
      → { match, homeTeam, awayTeam, stats, lineup, events, shotmap, playerStats, meta }
        → downstream feature engine / training / backtest

链路 B（Web hydration）:
FotMobRawDetailFetcher（HTML 页面抓取）
  → HTML body
    → NextDataParser.extractFromHtml()（提取 __NEXT_DATA__）
      → NextDataParser.transformToApiFormat()（转为 API-like）
        → stable raw payload（content + general + header + matchId + _meta）
          → 存入 raw_match_data（data_version=fotmob_html_hyd_v1）
            → Thin parsers（Match/Player/Team/League/MatchStats）
              → feature engine（当前？）
```

还有一个**第三条混合路径**：

```text
链路 C（Harvester 多策略）:
FotMobStrategy（API-first → browser fallback → NextData → DOM fallback）
  → 尝试 matchDetails API
  → 失败则启动 browser + __NEXT_DATA__ 提取
  → 再失败则 DOM 扫描
    → 最终输出到 collector pipeline
```

### 5.2 按阶段分解

#### A. acquisition / fetcher

| 项目 | 详情 |
| --- | --- |
| 候选文件 | `FotMobRawDetailFetcher.js`（主线候选）、`FotMobApiClient.js`（API 路径）、`FotMobStrategy.js`（多策略） |
| 证据 | `FotMobRawDetailFetcher` 是设计最干净、安全限制最多的采集入口（阻止 body save/print、browser、proxy、retry）。被多个 ops scripts 实际引用。 |
| 当前风险 | `FotMobRawDetailFetcher` 需要注入 fetchFn 依赖；`FotMobApiClient` 有 browser/proxy bootstrap 能力但无等同安全限制；`FotMobStrategy` 混合了所有策略 |
| confidence | **medium** — `FotMobRawDetailFetcher` 最像主线，但无法从只读代码确认哪个是生产使用 |
| canonical candidate | `FotMobRawDetailFetcher.js` **是 primary canonical candidate** |

#### B. raw payload retention

| 项目 | 详情 |
| --- | --- |
| 候选文件 | `FotMobRawDetailFetcher.js`（buildStableRawPayload/buildRawDataFromStablePayload）、`RawMatchDataVersionSelector.js` |
| 证据 | `FotMobRawDetailFetcher` 构建 stable raw payload（content/general/header/matchId）、计算 sha256 hash、附 _meta。DATA-L1C 定义了完整的 raw payload 保留策略。 |
| 当前风险 | stable raw payload 包含赛后字段（header.score、content.stats/shots 等），但这个阶段的职责是保留不是过滤 |
| confidence | **medium** |
| canonical candidate | `FotMobRawDetailFetcher.js` 的 stable raw payload 构建逻辑 **是 canonical candidate**

#### C. raw payload version selection

| 项目 | 详情 |
| --- | --- |
| 候选文件 | `RawMatchDataVersionSelector.js` |
| 证据 | 定义了 4 种 data_version 和优先级：`fotmob_pageprops_v2` > `fotmob_html_hyd_v1`；排除 `PHASE4.43_SYNTHETIC`、`PHASE4.23` |
| 当前风险 | `fotmob_pageprops_v2` 列为首选但本次未找到对应的独立 parser 实现。pageProps v2 相关代码在遗留 ADG/ops 脚本中有引用 |
| confidence | **low** — pageProps v2 parser 路径未在 src/ 中找到独立实现 |
| canonical candidate | `RawMatchDataVersionSelector.js` 本身 **是 canonical candidate**，但它指向的 pageProps_v2 parser path **需要进一步确认** |

#### D. pageProps / __NEXT_DATA__ normalization

| 项目 | 详情 |
| --- | --- |
| 候选文件 | `NextDataParser.js`（extractNextData、extractFromHtml、transformToApiFormat） |
| 证据 | 被 10+ 个 ops scripts 和多个 src 模块引用。`transformToApiFormat` 是标准化的 pageProps → API-like 转换入口 |
| 当前风险 | `transformToApiFormat` 输出的 metadata 字段（hasStats/hasLineup/hasShotmap）只是 boolean 标记，不含 timing 信息 |
| confidence | **high** — `NextDataParser` 是被广泛引用的核心模块 |
| canonical candidate | `NextDataParser.js` 的 `extractFromHtml` + `transformToApiFormat` **是 canonical candidate** |

#### E. parser

| 项目 | 详情 |
| --- | --- |
| 候选文件 | 主线：`FotMobRawParser.js`（fotmob_live_v1 parser）。Thin parsers：`MatchParser.js`、`PlayerParser.js`、`TeamParser.js`、`LeagueParser.js`、`MatchStatsParser.js` |
| 证据 | `FotMobRawParser` 有完整的 parser contract（`FOTMOB_RAW_PARSER_CONTRACT.md`），基于 4 个真实 retained raw payload 验证。Thin parsers 用于 pageProps/API-like 格式 |
| 当前风险 | `FotMobRawParser` 无字段级 timing label；thin parsers 的 `MatchStatsParser` 通过 `XGExtractor` 提取 xG |
| confidence | **medium** — `FotMobRawParser` 是最完整的 parser，但无法确认生产使用频率 |
| canonical candidate | `FotMobRawParser.js` **是 primary canonical parser candidate**。Thin parsers 是 **active supporting candidates** |

#### F. stats / xG / shotmap / lineup extraction

| 项目 | 详情 |
| --- | --- |
| 候选文件 | `XGExtractor.js`（xG/possession）、`MatchStatsParser.js`（stats + xG）、`FotMobRawParser.js`（内置 stats/lineup/events/shotmap/playerStats 提取） |
| 证据 | `FotMobRawParser` 原生提取 stats（Periods-aware）、lineup（starters+subs+coach）、events（timeline）、shotmap、playerStats。`XGExtractor` 提供独立的 xG/possession 提取 |
| 当前风险 | **全部高**——xG、shots、possession、shotmap、player stats 是当前比赛才产生的赛后数据，不应进入赛前模型 |
| confidence | **high** — 提取逻辑存在且完整，但需 envelope 标记阻止进入模型 |
| canonical candidate | `FotMobRawParser.js` 的内置提取 **是 canonical**。`XGExtractor.js` 是 **supporting**（为 envelope 提供提取能力，但输出需 forbids） |

#### G. downstream consumer

| 项目 | 详情 |
| --- | --- |
| 候选文件 | 本次审计未覆盖 feature engine / training / backtest 的具体消费代码 |
| 证据 | DATA-L1A 提到 `FeatureSmelter` 和 `train_baseline_v1.py` 是下游消费者，但本次未深入审计 |
| 当前风险 | 下游消费者可能直接使用 parser 输出的原始字段（含赛后数据），没有 cutoff 检查 |
| confidence | **low** — 需要专门的 feature/training audit |
| canonical candidate | **本次未确定** |

#### H. tests / validation

| 项目 | 详情 |
| --- | --- |
| 候选文件 | `tests/unit/fotmob_raw_parser.test.js`、`tests/unit/parsers/fotmob/FotMobParserOutputEnvelope.test.js`、`tests/unit/XGExtractor.test.js`、`tests/unit/collectors/fotmob/FotMobThinParsers.test.js`、`tests/unit/FotMobRawDetailFetcher.test.js` |
| 证据 | 每个核心模块都有对应测试文件 |
| 当前风险 | 测试用例可能使用赛后数据样例（finished=true, score 存在, xG 存在），但不能证明赛前安全性 |
| confidence | **medium** — 测试存在但需要审查测试数据的时间属性 |
| canonical candidate | 上述测试文件 **是 active supporting candidates** |

---

## 6. Canonical path selection

### 6.1 核心结论

当前最可能的 FotMob canonical path 是：

```text
FotMobRawDetailFetcher（html_hydration 采集）
  → NextDataParser.extractFromHtml()（提取 __NEXT_DATA__）
    → NextDataParser.transformToApiFormat()（转为 API 兼容格式）
      → stable raw payload（content/general/header/matchId/_meta）
        → RawMatchDataVersionSelector（选择 canonical data_version）
          → FotMobRawParser.parseFotMobRaw()（纯函数解析）
            ── 或 ──
          → Thin parsers（Match/Player/Team/League/MatchStats）
            → FotMobParserOutputEnvelope（未来接入点——给输出贴标签）
              → feature engine / training / backtest（下游消费）
```

### 6.2 Canonical candidates

**Primary canonical candidates（应作为主线骨架）：**

1. `src/parsers/fotmob/FotMobRawParser.js` — `fotmob_live_v1` raw payload 解析器，最完整的纯函数 parser，有 contract
2. `src/infrastructure/services/FotMobRawDetailFetcher.js` — html_hydration raw detail 采集器，最安全的 fetcher 入口
3. `src/parsers/fotmob/NextDataParser.js` — __NEXT_DATA__/pageProps 提取和转换，通用格式转换枢纽
4. `src/parsers/fotmob/FotMobParserOutputEnvelope.js` — 未来 envelope schema（DATA-L1E-1）
5. `src/infrastructure/services/RawMatchDataVersionSelector.js` — data_version 选择器

**Active supporting candidates（应保留但作为辅助）：**

6. `src/parsers/fotmob/MatchParser.js` — thin match parser
7. `src/parsers/fotmob/PlayerParser.js` — thin player parser
8. `src/parsers/fotmob/TeamParser.js` — thin team parser
9. `src/parsers/fotmob/LeagueParser.js` — thin league parser
10. `src/parsers/fotmob/MatchStatsParser.js` — stats + xG extractor
11. `src/parsers/fotmob/XGExtractor.js` — xG/possession extractor
12. `src/parsers/fotmob/index.js` — 统一导出入口
13. `src/feature_engine/smelter/components/FotMobSchemaGuard.js` — schema diff guard
14. `src/infrastructure/services/FotMobRouteIdentityReconciler.js` — 身份一致性验证
15. `src/infrastructure/compliance/FotMobComplianceMode.js` — 合规模式

**Legacy / experimental candidates（短期不要碰）：**

16. `src/infrastructure/services/FotMobExtractor.js` — 浏览器自动化提取（V6.7.x 系列，实验性质）
17. `src/infrastructure/harvesters/strategies/FotMobStrategy.js` — 多策略 harvester（混合所有路径，过度复杂）
18. `src/infrastructure/network/FotMobApiClient.js` — API client（含 browser/proxy 能力，能力过大）
19. `src/infrastructure/shared/helpers/fotMobExtractionHelpers.js` — 服务于 browser extractor 的辅助函数

### 6.3 Confidence

**confidence: medium**

Why:

- `FotMobRawParser.js` 有完整的 parser contract、4 个真实 retained raw payload 的验证、独立单元测试、git log 显示最近被维护——这些都是 strong evidence
- `FotMobRawDetailFetcher.js` 有最严格的安全限制设计、被多个 ops scripts 引用——也是 strong evidence
- `NextDataParser.js` 被 10+ 个模块引用——引用关系证明了它的枢纽地位
- `RawMatchDataVersionSelector.js` 明确定义了 version 优先级——但这个文件定义的 `fotmob_pageprops_v2` 最高优先级 path，在 src/ 中没有独立的 parser 实现。pageProps v2 相关代码可能在 DB 行中直接存储了已 parsed 结构，或通过遗留 ADG ops scripts 处理

Remaining uncertainty:

- **无法确认哪个 fetcher 是当前生产/主线使用**——只读代码不能证明运行时调用关系
- **pageProps v2 parser path 不清晰**——`RawMatchDataVersionSelector` 把 `fotmob_pageprops_v2` 放在最高优先级，但本次审计未找到处理 pageProps v2 的独立 parser。pageProps v2 可能是直接存储到 DB 的 JSON，没有经过 `FotMobRawParser`
- **thin parsers 和 FotMobRawParser 的关系不明确**——它们处理不同格式的输入（pageProps vs raw API payload），但不知道哪个是主力
- **下游消费代码未审计**——feature engine、training、backtest 的实际消费路径未在本次范围内

**如果无法确认主线，本次只能给出 canonical candidate，不足以确认 canonical path。**

---

## 7. Non-canonical / risky / duplicate code list

| 文件路径 | 原因 | 风险 | 后续处理建议 |
| --- | --- | --- | --- |
| `src/infrastructure/services/FotMobExtractor.js` | 浏览器自动化提取，代码内标注 V6.7.x 版本号，"HOUND-SOUL" 命名暗示实验性质。依赖 browserProvider + makeStealthRequest + networkInterceptor | 浏览器采集不稳定、可能被反爬、功耗大、结果受页面渲染影响 | 保留作为参考，不要作为 envelope 接入目标 |
| `src/infrastructure/harvesters/strategies/FotMobStrategy.js` | 混合 API-first → browser → NextData → DOM fallback 四种策略。等于把所有路径捆在一起，没有清晰边界 | 过度复杂、难以审计、可能绕过 safe fetcher 的限制 | 保留作为参考，不要作为 envelope 接入目标 |
| `src/infrastructure/network/FotMobApiClient.js` | 含 browser bootstrap、proxy agent、cookie/session 管理、anti-bot 能力。功能强大但能力过大 | browser/proxy 路径可能绕过安全限制、触发 rate limit、产生不稳定的 payload | 保留作为参考，不要直接用于 envelope pipeline |
| `src/infrastructure/shared/helpers/fotMobExtractionHelpers.js` | 服务于 `FotMobExtractor`（browser extractor） | 仅服务于 experimental 路径 | 保留作为参考 |
| `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/parsers/fotmob/CloudflareDetector.test.js.disabled` | 已禁用的旧测试 | 不与当前代码保持一致 | 保留，不删除 |
| 大量 ADG ligue1 历史 ops scripts（~80个） | Ligue 1 校正源库存操作的产物。非当前 parser pipeline | 可能包含过时的 URL 构造逻辑、过时的 route 假设 | 保留作为历史参考，不删除 |
| hydrate/endpoint probe scripts（~30个） | HTML hydration 结构分析、JSON endpoint 探针的 no-write 脚本 | 分析脚本，不是运行时代码 | 保留作为参考 |
| `configs/data/fotmob_n3_raw_retain_candidates.json` | raw retain candidate 配置 | 可能过期 | 保留，后续可能需要更新 |

**没有删除、移动、重命名任何文件。这是纯分类。**

---

## 8. Envelope schema 与现有代码的关系

### 8.1 当前状态

`FotMobParserOutputEnvelope.js`（DATA-L1E-1 产物，PR #1699）现在只是**被动 schema**：

- 定义了 `FIELD_CONTRACT_CLASSES`、`TIMING_CLASSES`、`MODEL_ELIGIBILITY`、`PAYLOAD_TYPES` 常量枚举
- 定义了 envelope shape：`match_id` / `source` / `payload.*` / `parser.*` / `fields[]` / `warnings[]`
- 提供了工厂函数（`createEmptyEnvelope`、`createFieldEntry`）和校验函数（`validateEnvelopeShape`、`isForbidden`、`isAllowed`）
- **完全没有接入 `FotMobRawParser` 或任何其他 parser runtime**
- 有独立单元测试，但不涉及真实 parser 输出

### 8.2 未来 envelope 最可能的接入点

基于本次审计，envelope 接入的推荐顺序：

1. **raw payload metadata handoff 来源**：
   - 最可能来自 `FotMobRawDetailFetcher` 构建的 `_meta` 对象（含 `fetched_at`、`data_version`、`data_hash`、`hash_strategy`）
   - 或者从 `FotMobRawParser` 输出的 `meta` 块（含 `dataVersion`、`hashStrategy`、`parserVersion`、`parsedAt`）
   - **建议**：envelope 的 `payload.*` 块从 `FotMobRawDetailFetcher` 的 `_meta` 映射；`parser.*` 块从 `FotMobRawParser` 的 `meta` 映射

2. **parser field entry 构建位置**：
   - 最可能在 `FotMobRawParser.parseFotMobRaw()` 的输出后做 post-processing
   - 或者在 thin parsers 的输出后统一包装
   - **建议**：先在 `FotMobRawParser` 输出外面包一层 adapter，因为它的输出结构最完整（match/teams/stats/lineup/events/shotmap/playerStats）

3. **legacy adapter 包在哪个输出外面**：
   - 第一候选：`FotMobRawParser.parseFotMobRaw()` 的返回结果 `{ ok, data: { match, homeTeam, awayTeam, stats, lineup, events, shotmap, playerStats, meta } }`
   - 第二候选：thin parsers 的组合输出（match + teams + players + stats）
   - **建议**：优先包 `FotMobRawParser` 输出，因为它是 contract-defined 的正式 parser

4. **哪些位置不能直接接**：
   - `FotMobApiClient`（API client，能力过大，不应该作为 envelope 的 payload 来源）
   - `FotMobExtractor`（浏览器提取，不稳定，不要在它上面建 envelope）
   - `FotMobStrategy`（混合策略，太复杂，不应该直接接 envelope）
   - 任何直接输出 raw HTML 或 pageProps 而未经过 `transformToApiFormat` 的地方

**本 PR 不实现接入。本 PR 不改 parser。本 PR 不改 feature。本 PR 只给出建议接入点。**

---

## 9. 赛前安全风险检查

从 DATA-L1A/B/C/D 的角度审计现有 pipeline 的风险：

| 字段/类别 | 现有代码是否可能提取？ | 是否可能是 postmatch / unknown_timing？ | 后续 envelope 应该怎么标记？ | 能否进入赛前模型？ |
| --- | --- | --- | --- | --- |
| xG | ✅ XGExtractor / MatchStatsParser / FotMobRawParser（stats 段） | **是，postmatch**——xG 是赛后统计 | `timing_class: POSTMATCH`, `model_eligibility: FORBIDDEN_POSTMATCH` | ❌ 绝对不能 |
| shots | ✅ FotMobRawParser（shotmap 段，含 shots[] 数组） | **是，postmatch**——射门数据赛后才有 | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 |
| score | ✅ FotMobRawParser（extractTeams 取 header.teams[i].score） | **是，postmatch**——最终比分是比赛结果 | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 |
| result (started/finished) | ✅ FotMobRawParser（extractMatch 取 general.started/finished） | **是，postmatch**——finished 状态赛后才有 | `FORBIDDEN_POSTMATCH`（finished），`LIVE_MATCH`（started） | ❌ 不能用于赛前预测 |
| events (timeline) | ✅ FotMobRawParser（extractEvents，含 goal/card/sub 等） | **是，postmatch/live_match** | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 |
| shotmap | ✅ FotMobRawParser（extractShotmap，投射门位置） | **是，postmatch** | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 |
| player stats (rating) | ✅ FotMobRawParser（extractPlayerStats） / PlayerParser（rating） | **是，postmatch**——球员评分赛后才有 | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 |
| lineup (formation/starters) | ✅ FotMobRawParser（extractLineup） / PlayerParser | **可能是 unknown_timing**——赛前 1 小时首发可能可变 | 需要 `observed_at` proof + cutoff check | ⚠️ 需要证据才能升级 |
| injury / suspension | 本次审计未在 parser 代码中找到明确的 injury 字段提取 | **可能是 unknown_timing** | 如存在，应标记为 `UNKNOWN_TIMING` | ⚠️ 需要证据 |
| odds | 本次审计中 odds 相关代码在 `scripts/odds_harvest_pipeline.js` 和 `train_baseline_v1.py`，不在 FotMob parser 中 | **取决于 odds type**——初盘可能赛前可用，临场/终盘不安全 | 需要按 odds type + captured_at 区分 | ⚠️ 需要专门的 odds 合同 |
| table / form | 本次审计未在 FotMob parser 中找到明确的 table/form 提取 | **可能是 DERIVED_FROM_HISTORY** | 如存在，需要 `table_snapshot_at <= cutoff` | ⚠️ 需要证明 |
| fixture metadata (league/season/round/kickoff) | ✅ FotMobRawParser（extractMatch 取 leagueId/leagueName/matchRound/matchTimeUTC） | **FIXTURE_METADATA**——赛前确定 | `timing_class: FIXTURE_METADATA`, `model_eligibility: ALLOWED_CANDIDATE`（join/filter）或 `CANDIDATE_IF_CUTOFF_VALID`（特征） | ✅ 可用于 join/filter；作为特征需 cutoff check |
| team names (home/away) | ✅ FotMobRawParser（extractTeams 取 name） / TeamParser | **FIXTURE_METADATA** | `ALLOWED_CANDIDATE`（join），`METADATA_ONLY`（不直接做特征） | ✅ 可用于 identity join |
| raw payload / pageProps / __NEXT_DATA__ | ✅ FotMobRawDetailFetcher（stable raw payload） / NextDataParser | **RAW_ONLY**——含全部赛后字段 | `RAW_ONLY`, `FORBIDDEN_RAW_ONLY` | ❌ 禁止直接进模型 |

**核心要点：**

- `FotMobRawParser` 目前能解析 stats、lineup、events、shotmap、playerStats——这些都是有价值的字段，但其中 stats/xG、events、shotmap、playerStats 默认是赛后数据
- parser 可以提取赛后字段，但必须贴 `forbidden_postmatch`
- raw payload 可以保留，但不能直接进模型
- `unknown_timing` 默认不能进模型
- fixture metadata 是唯一可以安全用于 join/filter 的字段类别

---

## 10. 后续 DATA-L1E-2 的进入条件

DATA-L1E-2 可以启动的前提：

1. **canonical FotMob parser path 已明确。** 本次 DATA-L1F 给出了 canonical candidates，但 confidence 是 medium。需要用户确认接受这条 canonical path，或者需要进一步的只读验证（DATA-L1F-1）。

2. **canonical raw payload metadata 来源已明确，或明确第一版允许 null/unknown。** `FotMobRawDetailFetcher` 已经产出 `_meta`（含 `fetched_at`、`data_hash`、`data_version`），`FotMobRawParser` 产出 `meta`（含 `dataVersion`、`parserVersion`、`parsedAt`）。第一版 adapter 可以把 `parsedAt` 留 null（纯函数不产生时间戳），但 `captured_at` 应该从 `_meta.fetched_at` 取。

3. **legacy output shape 已确认。** `FotMobRawParser.parseFotMobRaw()` 的输出结构 `{ ok, data: { match, homeTeam, awayTeam, stats, lineup, events, shotmap, playerStats, meta } }` 是已知的。thin parsers 的输出也已知。

4. **adapter 接入点不需要改现有 parser runtime。** Adapter 是 wrapper——接收现有 parser 输出，返回 envelope。不修改 `FotMobRawParser.js` 或 thin parsers 的内部逻辑。

5. **DATA-L1E-2 仍然只做 dry-run，不改变下游 feature/training/backtest。** 只输出 envelope 格式，验证 shape 正确，不实际改变任何下游消费代码。

**当前状态：DATA-L1E-2 remains blocked until the user accepts the canonical existing FotMob pipeline / parser path selected by this DATA-L1F triage.**

---

## 11. 需要后续确认的问题

以下问题本次只读审计无法解决，需要后续确认：

1. **哪个 fetcher 是当前生产/主线使用？** 只读代码不能确定运行时调用关系。`FotMobRawDetailFetcher`、`FotMobApiClient`、`FotMobStrategy` 都有被引用的证据，但无法确认哪个是主力。

2. **raw payload 是否真的有 `captured_at` / `payload_hash` / `data_version`？** `FotMobRawDetailFetcher` 的代码中构建了这些字段，但无法从只读代码确认这些字段在生产 DB 中真实存在。

3. **FotMobRawParser 当前输出 shape 是否有稳定 fixture？** 有 `tests/unit/fotmob_raw_parser.test.js` 测试，但测试用例是否覆盖真实场景不确定。

4. **pageProps v2 parser path 在哪里？** `RawMatchDataVersionSelector` 把 `fotmob_pageprops_v2` 放在最高优先级，但 src/ 中没有独立的 pageProps v2 parser。pageProps v2 数据可能直接存储在 DB 的 `raw_data` JSON 列中，通过 `NextDataParser` 在写入时转换过。

5. **哪些 tests 是可信的？** `FotMobRawParser` 的测试使用真实 payload 样例（含 finished=true、score、xG），但这些样例可能不保证 payload shape 的稳定性。

6. **哪些 docs 是过期文档？** 大量 ADG ligue1 历史文档记录了 Ligue 1 校正源库存操作，但这些操作的结论可能已被 `FOTMOB_CURRENT_STATE.md` 和 `FOTMOB_RETAINED_RAW_STAGE_STATUS.md` 取代。

7. **是否存在多个重复 parser？** Thin parsers（Match/Player/Team/League）和 `FotMobRawParser` 有功能重叠（都提取 match/team/player 信息），但它们处理不同输入格式。不是完全重复，但关系需要更清晰的文档。

8. **FotMobRawDetailFetcher 和 FotMobRawParser 的 data_version 对应关系？** `FotMobRawDetailFetcher` 默认 `dataVersion: fotmob_html_hyd_v1`，但 `FotMobRawParser` 的 meta 写的是 `dataVersion: fotmob_live_v1`。这两个 data_version 是否对应同一数据？如果不对应，parser 是否需要根据 data_version 做不同处理？

9. **生产 DB 中 `raw_match_data` 表的实际数据分布？** 本次未连接 DB，无法确认各 data_version 的实际行数、最新的 captured_at、是否有 pageProps v2 行。

**不要在本 PR 里解决这些问题。只列出。**

---

## 12. 本次明确不做事项

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
- 没有启动 DATA-L1F-1
- 没有启动 DATA-L2
- 没有启动 CLEANUP-L1A
- 没有启动 L3I / L4
- 没有删除 / 移动 / 重命名 legacy 文件
- 没有修改除本文档外的任何仓库文件

---

## 13. 下一步建议

Do not start automatically.

Recommended next task only after user confirmation:

**如果用户接受本次 DATA-L1F 的 canonical path selection：**

- **DATA-L1E-2: FotMob Parser Output Envelope Legacy Adapter Dry Run**
  - 前提：用户确认接受 DATA-L1F 选出的 canonical candidates
  - 目标：创建 adapter wrapper，接收 `FotMobRawParser.parseFotMobRaw()` 输出 → 返回 `FotMobParserOutputEnvelope` 格式
  - 风险：仍然低——dry-run 不改变下游消费
  - 仍需保持：不修改 parser runtime、不改变 feature/training/backtest

**如果 canonical path 证据不足，用户需要更确定的结论：**

- **DATA-L1F-1: Canonical FotMob Pipeline Verification Plan**
  - 目标：设计一个最小化的只读验证计划——通过 DB SELECT 确认 data_version 分布、通过 fixture 对比确认 parser 输出一致性、通过 git log 确认最近活跃的采集入口
  - 注意：仍然不运行采集、不写 DB、不访问 FotMob 网络

**DATA-L1E-2 remains blocked until the user accepts the canonical existing FotMob pipeline / parser path.**

---

## 附录 A：文件统计

| 类别 | 数量 | 说明 |
| --- | --- | --- |
| src/parsers/fotmob/ | 10个 .js 文件，共 1432 行 | 核心 parser |
| src/infrastructure/ (FotMob) | 8个 .js 文件，共 ~5048 行 | fetcher、route selector、identity、API client、strategy、extractor |
| src/feature_engine/ (FotMob) | 1个 .js 文件，152 行 | schema guard |
| tests/unit/ (FotMob 核心) | ~10个 关键测试文件 | parser、fetcher、envelope、thin parsers、xG |
| tests/unit/ (ADG 历史) | ~120+ 个测试文件 | Ligue 1 ADG 历史操作 |
| scripts/ops/ (FotMob) | ~150 个脚本文件 | 采集、probe、hydration、identity、raw、live fetch |
| docs/ (FotMob) | ~400 个文件 | 设计、合同、manifest、report、fixture、example |
| configs/ (FotMob) | 1个 | raw retain candidates |
| database/migrations/ (FotMob) | 2个 SQL 文件 | raw_match_data 相关 DDL |

## 附录 B：data_version 定义（来自 RawMatchDataVersionSelector.js）

| data_version | 分类 | 优先级 | 说明 |
| --- | --- | --- | --- |
| `fotmob_pageprops_v2` | canonical_fotmob_pageprops | **最高** | pageProps v2 直接存储 |
| `fotmob_html_hyd_v1` | canonical_fotmob_transformed | 第二 | HTML hydration → NextDataParser 转换后 |
| `PHASE4.43_SYNTHETIC` | legacy_synthetic | 排除 | 旧版合成数据 |
| `PHASE4.23` | legacy_unknown | 排除 | 旧版未知来源 |
