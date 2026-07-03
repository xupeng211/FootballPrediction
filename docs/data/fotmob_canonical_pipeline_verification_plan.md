# FotMob Canonical Pipeline Verification Plan

- lifecycle: source-of-truth
- scope: docs-only, verification plan for FotMob canonical pipeline candidates
- parent document: DATA-L1F (`docs/data/fotmob_existing_pipeline_triage_canonical_path.md`)
- branch: `docs/data-l1f-1-fotmob-canonical-pipeline-verification-plan`

---

## 1. 背景

DATA-L1F（PR #1700）已经通过只读审计给出了 medium confidence 的 canonical candidate path：

```text
FotMobRawDetailFetcher（html_hydration 采集）
  → NextDataParser.extractFromHtml()（提取 __NEXT_DATA__）
    → NextDataParser.transformToApiFormat()（转为 API 兼容格式）
      → stable raw payload
        → RawMatchDataVersionSelector（选择 data_version）
          → FotMobRawParser.parseFotMobRaw()（纯函数解析）
            或 Thin parsers（Match/Player/Team/League/MatchStats）
              → FotMobParserOutputEnvelope（未来接入点）
```

但 medium confidence 不足以直接启动 DATA-L1E-2 adapter。DATA-L1F-1 的目标是把后续验证拆成明确清单、证据要求、通过标准和小任务边界。

本文件不是 parser 实现、scraper 实现、envelope adapter、DB/migration。本文件不运行任何采集，不运行 parser，不改变 runtime 行为。本文件只定义验证计划。

---

## 2. 当前 DATA-L1F canonical candidate path 摘要

Primary canonical candidates（来自 DATA-L1F §6）：

| # | 文件 | 角色 | DATA-L1F 状态 |
| --- | --- | --- | --- |
| 1 | `src/parsers/fotmob/FotMobRawParser.js` | fotmob_live_v1 纯函数解析器 | canonical_candidate |
| 2 | `src/infrastructure/services/FotMobRawDetailFetcher.js` | html_hydration 采集器 | canonical_candidate |
| 3 | `src/parsers/fotmob/NextDataParser.js` | pageProps/__NEXT_DATA__ 转换枢纽 | active_supporting_candidate |
| 4 | `src/parsers/fotmob/FotMobParserOutputEnvelope.js` | envelope schema (DATA-L1E-1) | canonical_candidate |
| 5 | `src/infrastructure/services/RawMatchDataVersionSelector.js` | data_version 选择器 | canonical_candidate |

当前 confidence: **medium**。

为什么只是 medium，不是 high：

- 只读证据能证明这些文件"像主线"——有 contract、有测试、被多处引用、被 parser index 导出——但还不能证明它们在生产 runtime 中一定被使用。
- `FotMobRawParser` 虽然被 `index.js` 导出，但没有任何下游 src 模块直接 import 它。下游的实际消费路径未经过本次审计。
- `FotMobParserOutputEnvelope` 目前是完全独立的 schema，没有任何模块 import 它。
- pageProps v2 路径（`RawMatchDataVersionSelector` 的最高优先级）在 src/ 中没有对应的独立 parser 实现。
- DB 中真实数据分布、data_version 比例、collect 时间分布均未确认。

---

## 3. 为什么 DATA-L1E-2 仍然 blocked

DATA-L1E-2 是 legacy adapter dry-run——它虽然还是 dry-run，但已经开始靠近旧 parser 输出。如果 canonical path 没确认，就可能把 envelope 接到错误的旧代码上。

具体风险：

1. **接错 parser**：如果 `FotMobRawParser` 不是真实被使用的 parser，而是 thin parsers 才是主线，adapter 就应该包在 thin parsers 外面而不是 `FotMobRawParser` 外面。
2. **metadata 来源不清**：如果 `FotMobRawDetailFetcher` 的 `_meta` 和 `FotMobRawParser` 的 `meta` 不在同一条采集链路上，envelope 的 `payload.*` 和 `parser.*` metadata 就会来自不同来源。
3. **data_version 对应关系模糊**：`FotMobRawParser` 声称处理 `fotmob_live_v1`，但 `FotMobRawDetailFetcher` 声称产出 `fotmob_html_hyd_v1`。adapter 必须知道 envelope 包的是哪个 data_version 的产物。

**DATA-L1E-2 remains blocked until:**

1. 用户接受 DATA-L1F / DATA-L1F-1 的 canonical path。
2. legacy parser output shape 明确（不仅是代码结构，还需要确认这是实际被使用的 parser）。
3. raw payload metadata handoff 来源明确（哪个模块提供 `captured_at`/`payload_hash`/`data_version`）。
4. adapter 接入点明确（具体包在哪个 parser 函数外面）。
5. 未来 adapter PR 仍然保持 dry-run，不改变 feature/training/backtest。

---

## 4. 验证目标

DATA-L1F-1 要达成的验证目标（按依赖排序）：

1. **import graph 验证** — 确认 canonical candidates 之间的真实引用关系，确认哪些是实际入口、哪些是已定义但未使用的。
2. **output shape 验证** — 确认每个 candidate parser 的实际输出结构，判断 envelope 应该包在哪里。
3. **metadata handoff 验证** — 确认 `captured_at`、`payload_hash`、`data_version` 的来源和传递路径。
4. **data_version 路径验证** — 确认 `fotmob_pageprops_v2`（最高优先级但无独立 parser）、`fotmob_html_hyd_v1`、`fotmob_live_v1` 三条版本的实际处理链路。
5. **prematch safety 验证** — 确认已有 parser 输出中哪些字段是赛后风险字段，envelope 应该如何处理。
6. **测试/fixture 验证** — 确认现有测试覆盖哪些输入形态，能否支撑 dry-run adapter 验证。
7. **高风险路径排除** — 确认 legacy/experimental 路径不会被误接入 envelope。

---

## 5. Candidate-by-candidate verification matrix

### 5.1 FotMobRawParser.js

| 项目 | 值 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/FotMobRawParser.js` (436行) |
| **DATA-L1F 状态** | canonical_candidate |
| **当前证据** | 有完整 parser contract（`FOTMOB_RAW_PARSER_CONTRACT.md`）；明确标注 `fotmob_live_v1`；有 842 行单元测试（`tests/unit/fotmob_raw_parser.test.js`）；被 `src/parsers/fotmob/index.js` 正式导出；有 `parseFotMobRaw` 公共入口；纯函数无副作用 |
| **缺失证据** | **没有任何下游 src 模块直接 import 它**（只有 `index.js` 和测试引用）。data_version 标注为 `fotmob_live_v1`，但 `FotMobRawDetailFetcher` 的默认 data_version 是 `fotmob_html_hyd_v1`——两者可能不是同一条链路。输出中的 `meta` 块（`dataVersion`/`parserVersion`/`parsedAt`）是 parser 侧 metadata，但 `captured_at`/`payload_hash`/`storage_path` 不是 parser 能提供的 |
| **验证问题** | 1. `FotMobRawParser` 是否真实被 runtime 使用？还是只被测试和 index.js 引用？2. 它处理的 `fotmob_live_v1` payload 从哪里来？是 API 直连还是 html_hydration 转换后？3. 它的输出 `meta.parsedAt=null`（因为纯函数不产生时间戳）——adapter 如何填充这个字段？ |
| **建议验证方法** | 只读：检查 `src/` 中是否有模块通过 `index.js` 间接引用 `parseFotMobRaw`。检查 git log 中 parser 被引入的 PR 上下文。检查 `FOTMOB_RAW_PARSER_CONTRACT.md` 中 N=4 的 retained raw 来源。 |
| **是否需要运行代码** | 否——只读 import graph + git log 即可 |
| **是否需要网络** | 否 |
| **是否需要 DB** | 否 |
| **通过标准** | 找到至少一个 src 模块（非 index.js、非测试）通过 import 或配置引用 `parseFotMobRaw` 或 `FotMobRawParser`；或找到 ops script 将其作为 canonical parser；或确认 contract 文档证明了 parser 设计目标是主线 |
| **失败标准** | 无法找到任何 downstream consumer 引用；parser 仅存在于导出和测试中 |
| **对 DATA-L1E-2 的影响** | 如果它是真实主线 parser → adapter 第一接入点。如果它未被实际使用 → 需要找真正的主线 parser（可能是 thin parsers） |
| **当前验证状态** | `needs_import_graph_check` |

### 5.2 FotMobRawDetailFetcher.js

| 项目 | 值 |
| --- | --- |
| **文件路径** | `src/infrastructure/services/FotMobRawDetailFetcher.js` (710行) |
| **DATA-L1F 状态** | canonical_candidate |
| **当前证据** | 被 10+ 个 ops scripts 直接 require（`n3_live_fotmob_raw_retain.js`、`single_live_fotmob_raw_ingest_smoke.js`、`l2_remaining_raw_match_data_acquisition_preflight.js`、`fotmob_raw_detail_hash_stability_audit.js` 等）；有 642 行单元测试；构建 stable raw payload + sha256 hash；阻止 body save/print、browser、proxy、retry；有完整的 `_meta` 结构（`fetched_at`/`data_hash`/`data_version`/`hash_strategy` 等） |
| **缺失证据** | 这些 ops scripts 是否代表生产入口？还是只是历史 ADG 的一次性脚本？fetcher 默认 `dataVersion: fotmob_html_hyd_v1`，但 `FotMobRawParser` 标注 `fotmob_live_v1`——这两个 data_version 的关系不明确。fetcher 的输出是 raw data（含 `_meta`/`content`/`general`/`header`/`matchId`），但它自己不调用 parser |
| **验证问题** | 1. ops scripts 中是哪个脚本最近被执行/维护？2. `fotmob_html_hyd_v1`（fetcher 产出）和 `fotmob_live_v1`（parser contract）是同一数据的不同版本标签，还是不同的 pipeline？3. fetcher 产出的 `_meta` 是否就是 envelope `payload.*` 的 metadata 来源？ |
| **建议验证方法** | 只读：检查引用 fetcher 的 ops scripts 中哪些是 `FOTMOB_CURRENT_STATE.md` 提到的当前活跃入口。检查 `RawMatchDataVersionSelector` 定义的 `fotmob_html_hyd_v1` 分类（canonical_fotmob_transformed）和 parser contract 的 `fotmob_live_v1` 之间的关系。 |
| **是否需要运行代码** | 否——只读引用分析 |
| **是否需要网络** | 否 |
| **是否需要 DB** | 否（但如果要确认 DB 内真实分布，未来可能需要 SELECT-only audit） |
| **通过标准** | 确认至少一个 ops script 是当前活跃入口（被 CURRENT_STATE 或近期 git log 支持）；确认 `_meta` 结构可以一对一映射到 envelope `payload.*` 块 |
| **失败标准** | 所有引用 fetcher 的 ops scripts 都是历史 ADG 产物，无近期维护证据；或者 `_meta` 结构与 envelope 需求不匹配 |
| **对 DATA-L1E-2 的影响** | 如果它是 real fetcher → envelope `payload.*` metadata 应该从它的 `_meta` 映射。如果它不是 → 需要找到真正的 raw payload metadata 来源 |
| **当前验证状态** | `needs_import_graph_check` + `needs_metadata_handoff_check` |

### 5.3 NextDataParser.js

| 项目 | 值 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/NextDataParser.js` (223行) |
| **DATA-L1F 状态** | active_supporting_candidate |
| **当前证据** | 被 10+ 个 ops scripts 和 3 个 src 模块引用（`FotMobRawDetailFetcher`、`FotMobStrategy`、`MatchParser`、`LeagueParser`）；提供 `extractFromHtml`（纯函数版）和 `transformToApiFormat`（pageProps → API-like）；被 `MatchParser` 和 `LeagueParser` 内部调用；被 fetcher 的 `extractHydrationPayload` 调用 |
| **缺失证据** | `transformToApiFormat` 输出的 `_meta` 包含 `source: 'web_infiltration'` 和 `extractedAt`，但这个 `_meta` 和 `FotMobRawDetailFetcher` 自己构建的 `_meta` 是什么关系（fetcher 在 `extractHydrationPayload` 后自己重新构建了 `_meta`） |
| **验证问题** | 1. `transformToApiFormat` 的输出是否就是 thin parsers 的输入？2. `NextDataParser` 的 `_meta` 和 `FotMobRawDetailFetcher` 的 `_meta` 是否冲突/重叠？ |
| **建议验证方法** | 只读：追踪 `FotMobRawDetailFetcher.extractHydrationPayload` → `NextDataParser.extractFromHtml` → `NextDataParser.transformToApiFormat` 的完整调用链。确认 `_meta` 不会被重复覆盖。 |
| **是否需要运行代码** | 否 |
| **是否需要网络** | 否 |
| **是否需要 DB** | 否 |
| **通过标准** | 确认 `NextDataParser` 在整个 chain 中的 role 是单一且明确的（转换 format，不产生/覆盖关键 metadata） |
| **失败标准** | `_meta` 被多个环节覆盖或冲突 |
| **对 DATA-L1E-2 的影响** | `NextDataParser` 本身不是 adapter 目标——它是中间的转换层。但它决定了 thin parsers 能拿到什么格式的输入 |
| **当前验证状态** | `accepted_if_verified`（证据已经很充分，只需确认 _meta 不冲突） |

### 5.4 FotMobParserOutputEnvelope.js

| 项目 | 值 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/FotMobParserOutputEnvelope.js` (381行) |
| **DATA-L1F 状态** | canonical_candidate（schema-only，DATA-L1E-1 产物） |
| **当前证据** | 有 320 行单元测试；定义了完整的常量枚举 + factory 函数 + 校验函数；有 DATA-L1D 设计文档支持；纯定义文件无副作用 |
| **缺失证据** | **没有任何 src 模块 import 它**。它只是一个被动 schema——还没接入任何 parser runtime。无法确认它的 `payload.*` 字段是否能从 `FotMobRawDetailFetcher._meta` 映射，因为没人试过 |
| **验证问题** | 1. `payload.payload_type` 应该标记为什么？（`raw_json` vs `html_hydration` vs `pageProps`）——这取决于上游采集链路。2. `parser.parsed_at` 如何填充？（`FotMobRawParser` 写的是 `null`） |
| **建议验证方法** | 只读：对照 envelope schema 字段和 `FotMobRawDetailFetcher._meta` 字段，检查一对一映射是否可能 |
| **是否需要运行代码** | 否——schema 对照即可 |
| **是否需要网络** | 否 |
| **是否需要 DB** | 否 |
| **通过标准** | 能完成 `_meta` → `payload.*` 的字段映射；确认至少 `payload_type`/`captured_at`/`data_version`/`payload_hash` 有来源 |
| **失败标准** | 多个关键 metadata 字段（如 `captured_at`、`storage_path`）在现有 fetcher 中根本不存在 |
| **对 DATA-L1E-2 的影响** | 直接决定 adapter 能否构造合法 envelope——如果 metadata handoff 不完整，adapter 必须显式标记 null/unknown |
| **当前验证状态** | `needs_metadata_handoff_check` |

### 5.5 RawMatchDataVersionSelector.js

| 项目 | 值 |
| --- | --- |
| **文件路径** | `src/infrastructure/services/RawMatchDataVersionSelector.js` (168行) |
| **DATA-L1F 状态** | canonical_candidate |
| **当前证据** | 定义了 4 种 data_version：`fotmob_pageprops_v2`（最高优先级）、`fotmob_html_hyd_v1`（第二）、`PHASE4.43_SYNTHETIC`（排除）、`PHASE4.23`（排除）；纯函数无副作用；被 `src/data_engineering/` 的 Python 代码通过 table schema 间接引用 |
| **缺失证据** | **最高优先级 `fotmob_pageprops_v2` 在 src/ 中没有对应的独立 parser 实现。** pageProps v2 数据可能直接存储为 DB JSON，不经 parser。`fotmob_live_v1`（`FotMobRawParser` 的 contract data_version）不在 version selector 的版本列表中——说明这个 version selector 和 parser contract 可能是在不同时期、为不同目的创建的 |
| **验证问题** | 1. `fotmob_pageprops_v2` 数据到底有没有经过 parser？如果没有，envelope 怎么包？2. `fotmob_live_v1` 为什么不在 version selector 中？3. 如果 adapter 要同时支持多种 data_version，需要几个 adapter variant？ |
| **建议验证方法** | 只读：对照 `RawMatchDataVersionSelector` 的版本列表和 `FOTMOB_RAW_PARSER_CONTRACT.md` 的 `fotmob_live_v1`。确认 `fotmob_pageprops_v2` 在 DB migration 和 data engineering 代码中的处理方式。 |
| **是否需要运行代码** | 否 |
| **是否需要网络** | 否 |
| **是否需要 DB** | 否（但确认 pageProps v2 的实际 parser 路径可能需要 SELECT-only audit） |
| **通过标准** | 确认所有 canonical data_version 都有一条可追踪的 parser 路径；或者确认 pageProps v2 不需要 parser（直接以 JSON 形式存在 DB 中） |
| **失败标准** | `fotmob_pageprops_v2` 的 parser 路径完全不可追踪，且没有文档说明为何它是最高优先级 |
| **对 DATA-L1E-2 的影响** | 如果 pageProps v2 是最高优先级但没有 parser，envelope adapter 需要先处理 `fotmob_html_hyd_v1`（第二优先级）或 `fotmob_live_v1` |
| **当前验证状态** | `needs_import_graph_check` + `needs_output_shape_check` |

---

## 6. High-risk / do-not-touch verification matrix

以下三个文件是 DATA-L1F 标记为短期不要碰的。这里做更详细的 do-not-touch 论证。

### 6.1 FotMobApiClient.js

| 项目 | 值 |
| --- | --- |
| **文件路径** | `src/infrastructure/network/FotMobApiClient.js` (707行) |
| **为什么短期不要碰** | 含 browser bootstrap、proxy agent、cookie/session 管理、anti-bot 能力。这些是高风险能力——触网、绕过反爬、写 session 文件、依赖外部代理 |
| **它可能有什么价值** | 可能是 API 直连路径的唯一入口。如果 html_hydration 路径不可用，这是 fallback。包含 matchDetails API endpoint 的实际调用逻辑 |
| **它有什么风险** | browser/proxy 路径可能绕过 safe fetcher 的限制；可能触发 rate limit 导致 IP ban；session 持久化可能引入状态污染；payload shape 可能和 html_hydration 路径不同 |
| **未来什么时候才允许重新评估** | 仅当 html_hydration 路径（FotMobRawDetailFetcher）被证明不可用，且用户单独授权 API 路径评估 |
| **是否能作为 DATA-L1E-2 接入点** | **否**——不得作为第一接入点。envelope 应该首先包在 `FotMobRawDetailFetcher`/`FotMobRawParser` 这条链路上 |
| **当前验证状态** | `do_not_touch_for_now` |

### 6.2 FotMobStrategy.js

| 项目 | 值 |
| --- | --- |
| **文件路径** | `src/infrastructure/harvesters/strategies/FotMobStrategy.js` (956行) |
| **为什么短期不要碰** | 混合 API-first → browser → NextData → DOM fallback 四种策略。等于把所有采集路径捆在一个文件里，没有清晰边界 |
| **它可能有什么价值** | 展示了采集策略的全貌——API 优先、浏览器备用、DOM 兜底。理解这段代码可以帮助理解 FotMob endpoint 的可用性历史 |
| **它有什么风险** | 过于复杂（956行），难以审计；可能绕过 safe fetcher 的安全限制（它直接调用 `FotMobApiClient`）；策略选择逻辑依赖运行时状态 |
| **未来什么时候才允许重新评估** | 仅当 canonical path 的所有候选都被证明不可用，且需要理解多策略 fallback 逻辑时 |
| **是否能作为 DATA-L1E-2 接入点** | **否**——策略层不是 parser 层。envelope 应该包在 parser 输出外，不是 strategy 输出外 |
| **当前验证状态** | `do_not_touch_for_now` |

### 6.3 FotMobExtractor.js

| 项目 | 值 |
| --- | --- |
| **文件路径** | `src/infrastructure/services/FotMobExtractor.js` (360行) |
| **为什么短期不要碰** | 浏览器自动化提取。代码内标注 V6.7.x 版本号，"HOUND-SOUL" 命名暗示实验性质。依赖 browserProvider + makeStealthRequest + networkInterceptor |
| **它可能有什么价值** | 展示了浏览器端 __NEXT_DATA__ 提取的完整流程（导航 → 滚动加载 → DOM 扫描） |
| **它有什么风险** | 浏览器采集不稳定、功耗大、结果受页面渲染影响；全量 DOM 扫描可能不稳定；"HOUND-SOUL" 显然不是 production-ready 的命名 |
| **未来什么时候才允许重新评估** | 仅当非浏览器路径全部不可用，且用户单独授权浏览器采集评估 |
| **是否能作为 DATA-L1E-2 接入点** | **否**——不是 parser，是浏览器采集器。envelope 不包采集逻辑 |
| **当前验证状态** | `do_not_touch_for_now` |

---

## 7. Output shape verification plan

### 7.1 FotMobRawParser 输出 shape

来自代码只读（`FotMobRawParser.js` line 398-416）：

```javascript
{
  ok: true,
  data: {
    match: { matchId, externalId, leagueId, leagueName, matchRound, matchTimeUTC, started, finished, cancelled },
    homeTeam: { id, name, score, formation },
    awayTeam: { id, name, score, formation },
    stats: [{ period, key, homeValue, awayValue }],
    lineup: { home: { starters[], subs[], coach{} }, away: { starters[], subs[], coach{} } },
    events: [{ id, type, minute, teamSide, teamId, playerId, playerName, card, homeScore, awayScore, ... }],
    shotmap: { shots[] },
    playerStats: { ... },  // 透传原始对象
    meta: { dataVersion, hashStrategy, parserVersion, parsedAt }
  }
}
```

| 需要确认 | 只读证据 | 是否需要 fixture dry-run |
| --- | --- | --- |
| matchId / externalId 一致性 | contract §7 要求 matchId 存在且可转数字 | 否——代码有明确校验 |
| stats 包含 xG/shots/possession | extractStats 遍历 Periods.All/FirstHalf/SecondHalf.stats[]，无字段过滤 | 否——代码明确 |
| events 含 goal/card/sub | extractEvents 遍历 content.matchFacts.events.events[] | 否 |
| score 可从 homeTeam.score/awayTeam.score 获取 | extractTeams 取 header.teams[i].score | 否 |
| `meta.parsedAt` 为 null | 代码 line 413: `parsedAt: null` | 否 |

### 7.2 NextDataParser.transformToApiFormat 输出 shape

来自代码只读（`NextDataParser.js` line 118-146）：

```javascript
{
  matchId: String,
  content: { ... },  // pageProps.content
  general: { ... },  // pageProps.general
  header:  { ... },  // pageProps.header
  _meta: { source: 'web_infiltration', extractedAt: ISO string, hasStats, hasLineup, hasShotmap }
}
```

| 需要确认 | 只读证据 | 注意 |
| --- | --- | --- |
| `_meta.source = 'web_infiltration'` | 代码 line 137 | 这个 source 标签和 envelope 的 `source: 'fotmob'` 不一致——envelope adapter 需要统一 |
| `_meta.extractedAt` | 代码 line 138: `new Date().toISOString()` | 这是 NextDataParser 产生的时间戳，和 `FotMobRawDetailFetcher._meta.fetched_at` 是不同的时间点 |

### 7.3 FotMobRawDetailFetcher stable raw payload shape

来自代码只读（`FotMobRawDetailFetcher.js` line 292-302, 304-328）：

```javascript
// stable raw payload
{ content, general, header, matchId }

// _meta（fetch metadata）
{
  source: 'fotmob', route: 'html_hydration', requested_route, request_url, final_url,
  http_status, content_type, body_byte_length, fetch_body_sha256,
  parser: 'NextDataParser', data_version: 'fotmob_html_hyd_v1', fetched_at,
  full_html_body_stored: false, http_response_string_stored: false,
  has_stats, has_lineup, has_shotmap,
  hash_strategy: 'stable_raw_payload_v1', data_hash, match_id_source,
  metadata_hash_excluded_fields: [...]
}
```

| 需要确认 | 只读证据 | envelope 映射 |
| --- | --- | --- |
| `fetched_at` | 存在（line 524: `now()` 返回值） | → `payload.captured_at` |
| `data_hash` | 存在（line 623: stableHash） | → `payload.payload_hash` |
| `data_version` | 存在（`fotmob_html_hyd_v1`） | → `payload.data_version` |
| `storage_path` | **不存在**——fetcher 不知道数据存在哪里 | → envelope 需要标记 null/unknown |
| `source_url` / `final_url` | 存在（`request_url`/`final_url`） | → `payload.source_url` / `payload.final_url` |
| `payload_type` | 可以推断为 `html_hydration` | → `PAYLOAD_TYPES.HTML_HYDRATION` 或 `PAGE_PROPS` |

### 7.4 关键发现：metadata handoff gaps

以下 envelope 字段在当前 fetcher/parser 中没有直接来源：

| Envelope 字段 | 是否有来源 | 说明 |
| --- | --- | --- |
| `payload.captured_at` | ✅ `_meta.fetched_at` | 来自 fetcher |
| `payload.payload_hash` | ✅ `_meta.data_hash` | 来自 fetcher |
| `payload.data_version` | ✅ `_meta.data_version` | 来自 fetcher（注意是 `fotmob_html_hyd_v1` 而非 `fotmob_live_v1`） |
| `payload.storage_path` | ❌ 缺失 | fetcher 不知道存储路径 |
| `payload.source_url` | ✅ `_meta.request_url` | 来自 fetcher |
| `payload.final_url` | ✅ `_meta.final_url` | 来自 fetcher |
| `payload.payload_type` | ⚠️ 可推断 | `html_hydration` → `PAGE_PROPS` 或 `HTML_HYDRATION` |
| `parser.parser_name` | ✅ 硬编码 `'FotMobRawParser'` | adapter 可以硬编码 |
| `parser.parser_version` | ✅ `meta.parserVersion` ('1.0.0') | 来自 FotMobRawParser |
| `parser.parsed_at` | ❌ null | `FotMobRawParser` 是纯函数，不产生时间戳 |

**第一版 adapter 必须显式标记 null/unknown 的字段：`storage_path`、`parsed_at`。不得伪造。**

---

## 8. Prematch safety verification plan

基于 DATA-L1A 的字段分类、DATA-L1B 的字段合同、DATA-L1D 的标签设计，以及本次对 parser 代码的复查：

| 字段类别 | 旧 parser 是否可能输出？ | 风险分类 | envelope timing_class | envelope model_eligibility | 能否进入赛前模型？ | 验证证据需求 |
| --- | --- | --- | --- | --- | --- | --- |
| xG | ✅ FotMobRawParser stats段 / XGExtractor | **unsafe_postmatch** | `POSTMATCH` | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 | 代码确认：stats 无字段过滤 |
| shots / shotmap | ✅ extractShotmap | **unsafe_postmatch** | `POSTMATCH` | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 | 代码确认：shotmap.shots[] |
| score | ✅ extractTeams (header.teams[i].score) | **unsafe_postmatch** | `POSTMATCH` | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 | 代码确认：score 从 header 取 |
| result (finished) | ✅ extractMatch (general.finished) | **unsafe_postmatch** | `POSTMATCH` | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 | 代码确认 |
| events (timeline) | ✅ extractEvents | **unsafe_postmatch** | `POSTMATCH` | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 | 代码确认：含 goal/card/sub |
| player stats / ratings | ✅ extractPlayerStats / PlayerParser.rating | **unsafe_postmatch** | `POSTMATCH` | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 | 代码确认 |
| possession | ✅ XGExtractor / stats 段 | **unsafe_postmatch** | `POSTMATCH` | `FORBIDDEN_POSTMATCH` | ❌ 绝对不能 | 代码确认 |
| lineup (formation/starters) | ✅ extractLineup | **unknown_timing** | `NEAR_KICKOFF_SNAPSHOT` 或 `UNKNOWN_TIMING` | `FORBIDDEN_UNKNOWN_TIMING`（默认） | ⚠️ 需要 observed_at + cutoff proof | 没有 observed_at 证据 |
| injury | 本次未在 parser 中找到提取代码 | **unknown_timing** | `UNKNOWN_TIMING` | `FORBIDDEN_UNKNOWN_TIMING` | ❌ 不能 | 字段不存在于 parser |
| odds | 不在 FotMob parser 中（在 odds pipeline） | **取决于 type** | 按 type 区分 | 需要 odds 专用合同 | ⚠️ 需要单独审计 | 不在本次范围 |
| table / form | 本次未在 FotMob parser 中找到 | **DERIVED_FROM_HISTORY** | 需要历史窗口证明 | `FORBIDDEN_UNKNOWN_TIMING`（默认） | ⚠️ 需要证明 | 不在本次范围 |
| fixture metadata (league/season/round/kickoff) | ✅ extractMatch | **safe_prematch_candidate** | `FIXTURE_METADATA` | `ALLOWED_CANDIDATE`（join/filter） | ✅ join/filter 安全 | 代码确认：赛前存在 |
| team names | ✅ extractTeams / TeamParser | **metadata_only** | `FIXTURE_METADATA` | `METADATA_ONLY`（不直接做特征） | ✅ identity join 安全 | 代码确认 |
| raw payload / __NEXT_DATA__ | ✅ FotMobRawDetailFetcher / NextDataParser | **debug_or_raw_only** | `RAW_ONLY` | `FORBIDDEN_RAW_ONLY` | ❌ 禁止直接进模型 | 含全部赛后字段 |

**核心结论：`FotMobRawParser` 目前会提取大量赛后危险字段（xG/shots/score/events/shotmap/playerStats），不做任何过滤。这不是 parser 的 bug——parser 的职责是解析，envelope 的职责是贴标签和阻止。adapter 需要在 envelope 层面给这些字段打 `FORBIDDEN_POSTMATCH`。**

---

## 9. DATA-L1E-2 entry criteria

### 必须条件（缺一不可）

1. **用户明确接受 DATA-L1F / DATA-L1F-1 的 canonical path。** 不能默认接受。
2. **明确 DATA-L1E-2 第一接入点。** 当前最可能的接入点：`FotMobRawParser.parseFotMobRaw()` 的输出 `{ ok, data }`。备选：thin parsers 的组合输出。
3. **明确 adapter 只做 dry-run。** 不改变现有 parser runtime。不修改 `FotMobRawParser.js`、`NextDataParser.js`、thin parsers 的任何内部逻辑。不改变 `FotMobRawDetailFetcher.js`。
4. **明确 adapter 不进入 feature/training/backtest。** Adapter 只是一个新模块，接收旧 parser 输出，返回 envelope。下游不改。
5. **明确 adapter 不访问 FotMob 网络。** Adapter 不调用 `fetchFotMobRawDetail()` 或任何网络函数。
6. **明确 adapter 不写 DB/raw/data/models/logs。** 只构造 envelope 对象，输出到 console 或测试断言。
7. **明确所有 unsafe_postmatch / unknown_timing 字段默认保守标记。** 不确定 → `FORBIDDEN_*`。
8. **明确旧 output shape 中缺失 metadata 时必须显式 null/unknown。** `storage_path`、`parsed_at` 不得伪造。

### 可选条件（有更好，但非 blocker）

1. 有最小 fixture 可用于 dry-run（如现有测试中的 mock payload）。
2. 有现有单元测试可读作 output shape 证据。
3. 有 import graph 证明 candidate parser 是当前导出主线。
4. 有 docs contract 支持 parser input/output。

**当前：必须条件 #1 和 #2 未满足（用户未明确接受 canonical path；接入点需要 DATA-L1F-2A import graph check 确认）。DATA-L1E-2 remains blocked。**

---

## 10. Proposed small follow-up tasks

以下任务不应该自动启动。每个任务都是独立的，按依赖顺序排列。

### 10.1 DATA-L1F-2A: FotMob Canonical Import Graph Verification

| 项目 | 值 |
| --- | --- |
| **目标** | 只读确认 `FotMobRawParser`、thin parsers、`FotMobRawDetailFetcher` 的完整 import graph——谁引用了谁、谁是实际入口、谁只是被定义但未使用 |
| **允许修改范围** | 仅限新增一个 docs 文件（verification report） |
| **禁止事项** | 不运行代码、不访问网络、不改 src/tests/scripts、不写 DB |
| **是否运行代码** | 否 |
| **是否访问网络** | 否 |
| **是否写 DB/raw** | 否 |
| **验收标准** | 给出明确的 import graph（带证据行号）；确认 `FotMobRawParser` 和 thin parsers 哪个是实际被下游引用的；确认最可能的 envelope 接入点 |
| **是否解锁 DATA-L1E-2** | 是——解决必须条件 #2 |

### 10.2 DATA-L1F-2B: FotMob Legacy Output Shape Fixture Audit

| 项目 | 值 |
| --- | --- |
| **目标** | 从现有测试 fixture 中提取 FotMobRawParser 和 thin parsers 的真实输出样例，不做 dry-run，只读记录 shape |
| **允许修改范围** | 仅限新增一个 docs 文件（fixture audit report） |
| **禁止事项** | 不运行测试（只读查看测试文件中的 mock 数据）；不修改测试；不运行 parser |
| **是否运行代码** | 否 |
| **是否访问网络** | 否 |
| **是否写 DB/raw** | 否 |
| **验收标准** | 列出每个 parser 在测试中使用的输入样例结构、期望输出结构；确认 thin parsers 和 FotMobRawParser 的输入格式差异 |
| **是否解锁 DATA-L1E-2** | 部分——提供 output shape 证据但不是 blocking |

### 10.3 DATA-L1F-2C: FotMob Raw Payload Metadata Handoff Audit

| 项目 | 值 |
| --- | --- |
| **目标** | 只读对照 `FotMobRawDetailFetcher._meta` 和 `FotMobParserOutputEnvelope.payload.*` 的字段映射，确认哪些可以直接映射、哪些缺失 |
| **允许修改范围** | 仅限新增一个 docs 文件（metadata mapping table） |
| **禁止事项** | 不运行代码、不访问网络、不写 DB |
| **是否运行代码** | 否 |
| **是否访问网络** | 否 |
| **是否写 DB/raw** | 否 |
| **验收标准** | 给出完整的 metadata 字段映射表；标记每个 envelope payload 字段的来源（fetcher _meta / parser meta / 缺失）；确认 adapter 需要处理多少个 null/unknown |
| **是否解锁 DATA-L1E-2** | 部分——解决必须条件 #8 的具体方案 |

### 10.4 DATA-L1F-2D: FotMob Unsafe Field Dry-Run Classification Plan

| 项目 | 值 |
| --- | --- |
| **目标** | 定义 adapter 如何对 `FotMobRawParser` 输出的每个字段进行 timing_class 和 model_eligibility 分类 |
| **允许修改范围** | 仅限新增一个 docs 文件（classification mapping） |
| **禁止事项** | 不运行 parser、不运行 training、不改变任何代码 |
| **是否运行代码** | 否 |
| **是否访问网络** | 否 |
| **是否写 DB/raw** | 否 |
| **验收标准** | 每个 parser 输出的字段路径 → 对应的 DATA-L1B 合同分类 → 对应的 envelope timing_class → 对应的 model_eligibility |
| **是否解锁 DATA-L1E-2** | 是——解决必须条件 #7 的具体方案 |

### 10.5 DATA-L1E-2: FotMob Parser Output Envelope Legacy Adapter Dry Run

| 项目 | 值 |
| --- | --- |
| **目标** | 创建 adapter wrapper，接收 `FotMobRawParser.parseFotMobRaw()` 输出 → 返回 `FotMobParserOutputEnvelope` 格式。只做 dry-run（console/test 输出），不改变 parser runtime |
| **前置条件** | DATA-L1F-2A 完成 + 用户接受 canonical path + 上面必须条件全部满足 |
| **允许修改范围** | 新增 adapter 文件 + 对应的单元测试；不改现有 parser/fetcher/feature/training 代码 |
| **禁止事项** | 不访问网络、不写 DB/raw、不改变现有 parser 输出结构、不进入 feature/training/backtest |
| **是否运行代码** | 是——但只运行 adapter 本身（不运行采集/parser runtime） |
| **是否访问网络** | 否 |
| **是否写 DB/raw** | 否 |
| **验收标准** | adapter 能接收 fixture payload → 输出合法 envelope → validateEnvelopeShape 通过 → 所有 postmatch/unknown 字段默认 forbidden |
| **是否解锁后续工作** | 是——DATA-L1E-2 成功后解锁 DATA-L1E-3 (contract mapper) |

---

## 11. Verification evidence checklist

- [ ] **C-1**: All 5 canonical candidate files exist on main.
- [ ] **C-2**: `FotMobRawParser.parseFotMobRaw` is exported by `src/parsers/fotmob/index.js`.
- [ ] **C-3**: `FotMobRawParser` has a documented parser contract (`FOTMOB_RAW_PARSER_CONTRACT.md`).
- [ ] **C-4**: `FotMobRawParser` has unit tests (`tests/unit/fotmob_raw_parser.test.js`, 842 lines).
- [ ] **C-5**: `FotMobRawDetailFetcher` has documented safety behavior (block body save/print, browser, proxy, retry).
- [ ] **C-6**: `FotMobRawDetailFetcher` has unit tests (`tests/unit/FotMobRawDetailFetcher.test.js`, 642 lines).
- [ ] **C-7**: `RawMatchDataVersionSelector` has documented version priority.
- [ ] **C-8**: `FotMobParserOutputEnvelope` has unit tests (`tests/unit/parsers/fotmob/FotMobParserOutputEnvelope.test.js`, 320 lines).
- [ ] **C-9**: Import graph confirms at least one downstream consumer references `FotMobRawParser` or thin parsers.
- [ ] **C-10**: Import graph confirms `FotMobRawDetailFetcher._meta` is the primary metadata source.
- [ ] **C-11**: Envelope `payload.*` fields have identifiable sources (fetcher `_meta` or parser `meta`).
- [ ] **C-12**: Missing metadata fields (`storage_path`, `parsed_at`) are identified and plan is to mark null/unknown.
- [ ] **C-13**: All unsafe postmatch fields (xG/shots/score/events/shotmap/playerStats/possession) are identified in parser output.
- [ ] **C-14**: Unknown timing fields (lineup/formation) default to forbidden in envelope plan.
- [ ] **C-15**: `FotMobApiClient` / `FotMobStrategy` / `FotMobExtractor` are excluded from envelope access path.
- [ ] **C-16**: `fotmob_pageprops_v2` handler path is documented or marked as "needs further investigation".
- [ ] **C-17**: DATA-L1E-2 entry criteria are reviewed and confirmed.
- [ ] **C-18**: User explicitly accepts canonical path before any adapter work begins.

---

## 12. Decision recommendation

当前 DATA-L1F confidence 是 medium。但经过本次复查，核心证据质量有所提升（找到了具体的 import graph 缺口、output shape 确认、metadata handoff gaps 识别）。但有一个关键 gap 仍然存在：

> `FotMobRawParser` 没有任何下游 consumer 直接引用它（除了 `index.js` 和测试）。我们不知道它是不是真实主线 parser。

**建议：B — Do not accept yet; run one more verification task first.**

推荐先做：

```text
DATA-L1F-2A: FotMob Canonical Import Graph Verification
```

原因：

1. DATA-L1F-2A 是风险最低、执行最快的验证——纯只读，一个 docs 文件，不需要运行任何代码。
2. 它能直接解决必须条件 #2（明确 DATA-L1E-2 第一接入点）。
3. 如果 DATA-L1F-2A 确认 `FotMobRawParser` 确实是主线，canonical path confidence 从 medium 提升到 high，DATA-L1E-2 可以安全启动。
4. 如果 DATA-L1F-2A 发现 `FotMobRawParser` 不被使用，我们需要在 thin parsers 和 `FotMobRawParser` 之间重新选择，或者接受 thin parsers 作为 adapter 第一接入点。

---

## 13. Explicit non-goals

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
- 没有启动 DATA-L1F-2
- 没有启动 DATA-L2
- 没有启动 CLEANUP-L1A
- 没有启动 L3I / L4
- 没有删除 / 移动 / 重命名 legacy 文件

---

## 14. 下一步建议

Do not start automatically.

Recommended next task only after user confirmation:

- **DATA-L1F-2A: FotMob Canonical Import Graph Verification**
  - 目标：只读确认 `FotMobRawParser` 和 thin parsers 的完整 import graph
  - 风险：最低——纯只读，不运行任何代码
  - 原因：这是当前 blocking DATA-L1E-2 的最关键 gap

- 或如果用户直接接受 DATA-L1F / DATA-L1F-1 的 canonical path：
  - **DATA-L1E-2: FotMob Parser Output Envelope Legacy Adapter Dry Run**
  - 前提：Only if the user explicitly accepts the DATA-L1F / DATA-L1F-1 canonical path.

**DATA-L1E-2 remains blocked until explicit user acceptance.**
