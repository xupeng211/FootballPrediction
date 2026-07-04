# FotMob NextDataParser and Thin Parsers Output Shape Audit

- lifecycle: source-of-truth
- scope: docs-only, static output shape audit for NextDataParser and FotMob thin parsers
- parent documents: DATA-L1F (`docs/data/fotmob_existing_pipeline_triage_canonical_path.md`), DATA-L1F-1 (`docs/data/fotmob_canonical_pipeline_verification_plan.md`), DATA-L1F-2A (`docs/data/fotmob_canonical_import_graph_verification.md`)
- branch: `docs/data-l1f-2b-nextdata-thin-parsers-output-shape-audit`

---

## 1. 背景

DATA-L1F 给出了 medium confidence canonical candidate path。
DATA-L1F-1 要求进一步验证 canonical path。
DATA-L1F-2A 已确认 `FotMobRawParser` / `parseFotMobRaw` **没有 confirmed runtime consumer**——它有 contract、有测试、被 index.js 导出，但没有任何 `src/**` 或 `scripts/**` 代码在用它。

因此不能直接把 DATA-L1E-2 adapter 包在 FotMobRawParser 外面。DATA-L1F-2B 的目标是审计**真实被引用的** FotMob 解析链路——也就是 `NextDataParser` 和 thin parsers（`MatchParser` / `TeamParser` / `PlayerParser` / `LeagueParser` / `MatchStatsParser` / `XGExtractor`）的输入输出形态。

**本文件不是** parser 实现、scraper 实现、envelope adapter、DB/migration。本文件不运行任何采集，不运行 parser，不改变 runtime 行为。本文件只做静态 output shape audit。

---

## 2. 审计方法

本次只读用了以下方法：

- `git ls-files` — 确认目标文件存在
- `git grep` — 搜索 NextDataParser / thin parsers 的全仓库引用关系
- `sed -n` / `cat` / `head` — 只读查看 parser 源码
- `git log` — 查看相关文件的历史变更
- 只读查看 `src/parsers/fotmob/*`、`src/feature_engine/**`、`src/infrastructure/**`、`tests/unit/**`、`scripts/ops/**`

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

### 3.1 重点函数 / 模块

| 函数/模块 | 文件位置 | 角色 |
| --- | --- | --- |
| `extractFromHtml` | `NextDataParser.js:63` | 从 HTML 字符串提取 `__NEXT_DATA__` JSON |
| `transformToApiFormat` | `NextDataParser.js:118` | 将 `__NEXT_DATA__` 转为 API 兼容格式 |
| `validateNextDataStructure` | `NextDataParser.js:153` | 验证 `__NEXT_DATA__` 结构完整性 |
| `MatchParser.parseMatch` | `MatchParser.js:15` | 解析 match 信息（调用 TeamParser） |
| `TeamParser.parseTeams` | `TeamParser.js:18` | 解析主/客队信息 |
| `PlayerParser.parsePlayers` | `PlayerParser.js:19` | 解析球员列表（首发+替补） |
| `LeagueParser.parseFromHtml` | `LeagueParser.js:18` | 从 HTML 解析联赛元信息 |
| `LeagueParser.parseFromNextData` | `LeagueParser.js:6` | 从 nextData 解析联赛元信息 |
| `MatchStatsParser.parseStats` | `MatchStatsParser.js:24` | 解析比赛统计（含 xG/possession） |
| `XGExtractor.extractXG` | `XGExtractor.js:13` | 提取 xG 数据 |
| `XGExtractor.extractPossession` | `XGExtractor.js:79` | 提取控球率 |
| `XGExtractor.extractAllStats` | `XGExtractor.js:103` | 提取所有统计（xG + possession） |
| `FotMobStrategy` | `FotMobStrategy.js` | 唯一 runtime src consumer of NextDataParser |
| `FotMobRawDetailFetcher.extractHydrationPayload` | `FotMobRawDetailFetcher.js` | 构建 stable raw payload（调用 NextDataParser） |

### 3.2 重点路径

```text
src/parsers/fotmob/NextDataParser.js          ← 核心 parser（223 行）
src/parsers/fotmob/MatchParser.js              ← thin parser（33 行）
src/parsers/fotmob/TeamParser.js               ← thin parser（28 行）
src/parsers/fotmob/PlayerParser.js             ← thin parser（40 行）
src/parsers/fotmob/LeagueParser.js             ← thin parser（31 行）
src/parsers/fotmob/MatchStatsParser.js         ← thin parser（46 行）
src/parsers/fotmob/XGExtractor.js              ← 赛后数据提取器（152 行）
src/parsers/fotmob/index.js                    ← parser 索引
src/infrastructure/harvesters/strategies/FotMobStrategy.js  ← 唯一 runtime src consumer
src/infrastructure/services/FotMobRawDetailFetcher.js       ← 采集器（通过注入使用 NextDataParser）
src/infrastructure/services/RawMatchDataVersionSelector.js  ← 版本选择器
src/feature_engine/**                          ← 特征引擎（不 import 任何 parser）
tests/unit/collectors/fotmob/FotMobThinParsers.test.js      ← thin parsers 测试
tests/unit/XGExtractor.test.js                 ← XGExtractor 测试
```

---

## 4. NextDataParser output shape

### 4.1 extractFromHtml

| 项目 | 说明 |
| --- | --- |
| **函数名** | `extractFromHtml(html)` |
| **输入 shape** | `html: string` — 完整的 HTML 页面字符串 |
| **输出 shape** | `{ success: boolean, data?: object, error?: string }` |
| **成功输出** | `{ success: true, data: <__NEXT_DATA__ JSON 对象> }` |
| **失败输出** | `{ success: false, error: 'NO_NEXT_DATA:...' }` 或 `{ success: false, error: 'PARSE_ERROR:...' }` 或 `{ success: false, error: 'INVALID_INPUT:...' }` |
| **关键字段** | `success`, `data`, `error` |
| **是否包含 _meta** | **否** |
| **是否包含 data_version/source/extractedAt** | **否** |
| **是否包含赛后字段** | 取决于 HTML 内容——`extractFromHtml` 只是提取 JSON，不做字段过滤。HTML 可能包含 stats/lineup/shotmap 等赛后数据 |
| **是否适合作为 envelope payload 层输入** | **否**——不产生 metadata，输出是原始 __NEXT_DATA__ |
| **是否适合作为 envelope fields 层输入** | **否**——输出未被规范化 |
| **证据来源** | 只读查看 `NextDataParser.js:63-105` |
| **不确定点** | 无——纯文本提取函数，行为完全确定 |

### 4.2 transformToApiFormat

| 项目 | 说明 |
| --- | --- |
| **函数名** | `transformToApiFormat(nextData, matchId)` |
| **输入 shape** | `nextData: { props: { pageProps: { content, general, header, ... } } }` — `__NEXT_DATA__` 对象。`matchId: string` |
| **输出 shape** | `object` 或 `null` |
| **成功输出** | `{ matchId, content: {...}, general: {...}, header: {...}, _meta: {...} }` |
| **失败输出** | `null`（缺少 `props.pageProps` 或 `content` 时） |
| **_meta 内容** | `{ source: 'web_infiltration', extractedAt: <ISO timestamp>, hasStats: boolean, hasLineup: boolean, hasShotmap: boolean }` |
| **是否包含 data_version/source** | `source: 'web_infiltration'` — 有 source，但无 data_version |
| **是否包含 captured_at/fetched_at** | `extractedAt` — 有（但注意这是函数调用时的 `new Date()`，不是真实的采集时间） |
| **是否包含赛后字段** | **是**——`content` 包含原始 `stats`（含 xG/shots/possession）、`lineup`、`shotmap`。`_meta.hasStats/hasLineup/hasShotmap` 标记是否存在 |
| **是否适合作为 envelope payload 层输入** | **是**——这是最接近 "被标准化后的 parser output" 的形态。但 metadata 不够完整（缺 data_version/payload_hash/storage_path） |
| **是否适合作为 envelope fields 层输入** | **部分适合**——`content.stats/lineup/shotmap` 是原始嵌套对象，需要进一步展开。`general/header` 需要进一步提取 |
| **证据来源** | 只读查看 `NextDataParser.js:118-146` |
| **不确定点** | 无 |

### 4.3 validateNextDataStructure

| 项目 | 说明 |
| --- | --- |
| **函数名** | `validateNextDataStructure(nextData)` |
| **输入 shape** | `nextData: object` |
| **输出 shape** | `{ valid: boolean, missing: string[] }` |
| **行为** | 检查 `props` → `props.pageProps` → `props.pageProps.content` 的链是否存在 |
| **使用场景** | 在 `FotMobRawDetailFetcher` 和少数 ops scripts 中用于预检 |
| **证据来源** | 只读查看 `NextDataParser.js:153-175` |

### 4.4 transformToApiFormat 输出结构（关键字段展开）

```javascript
{
  matchId: "4193673",           // 来自参数
  content: {                    // 原始 pageProps.content
    stats: { ... },             // 赛后数据
    lineup: { ... },            // lineup 数据
    shotmap: { ... },           // shotmap 数据
    // ... 其他 FotMob 原始字段
  },
  general: { ... },             // 原始 pageProps.general（比赛基本信息）
  header: { ... },              // 原始 pageProps.header（头部信息）
  _meta: {
    source: 'web_infiltration', // 硬编码
    extractedAt: '2026-07-04T...', // 函数调用时的 new Date()
    hasStats: true/false,       // content.stats 是否存在
    hasLineup: true/false,      // content.lineup 是否存在
    hasShotmap: true/false      // content.shotmap 是否存在
  }
}
```

---

## 5. Thin parsers output shape

### 5.1 MatchParser

| 项目 | 说明 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/MatchParser.js` (33行) |
| **输入 shape** | `rawData: object`（可能是 `__NEXT_DATA__` 格式即 `{ props: { pageProps: {...} } }`，也可能是已转换的 API 格式），`context: { matchId, externalId }` |
| **输出 shape** | `{ matchId, externalId, status, startTime, teams: [...], raw: rawData }` |
| **关键字段** | `matchId`, `externalId`, `status`, `startTime`, `teams` (由 TeamParser 生成), `raw` (保留原始输入) |
| **是否依赖 NextDataParser.transformToApiFormat** | **是**——如果输入是 `__NEXT_DATA__` 格式（`rawData?.props?.pageProps`），内部调用 `transformToApiFormat` 转换后再解析 |
| **是否输出赛前字段** | `matchId`, `status`, `startTime` — 可能是赛前可知的 |
| **是否输出赛后字段** | `teams[x].score` — **赛后字段**（比赛结束后才知道比分） |
| **是否输出 timing/observed_at** | **否** |
| **是否输出 data_version/source/meta** | **否**（但 `raw` 保留原始输入，可能间接包含） |
| **测试证据** | `tests/unit/collectors/fotmob/FotMobThinParsers.test.js` — 有专门测试 match parser 的 header/context fallback |
| **consumer 证据** | **无 src runtime consumer**。只有 `FotMobThinParsers.test.js` 测试引用 |
| **风险** | 输出 `teams[x].score` 是赛后字段；无 timing 标签；无 consumer |
| **当前分类** | **test_only_parser** |

### 5.2 TeamParser

| 项目 | 说明 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/TeamParser.js` (28行) |
| **输入 shape** | `rawData: object`（从 `general.homeTeam/awayTeam` 或 `header.teams[i]` 提取） |
| **输出 shape** | `[{ side: 'home'|'away', id, name, score, raw }, ...]` — 过滤掉 null 项 |
| **关键字段** | `side`, `id`, `name`, `score`, `raw` |
| **是否依赖 NextDataParser.transformToApiFormat** | **否**——但被 MatchParser 内部调用 |
| **是否输出赛前字段** | `side`, `id`, `name` — 赛前可知 |
| **是否输出赛后字段** | `score` — **赛后字段** |
| **是否输出 timing/observed_at** | **否** |
| **是否输出 data_version/source/meta** | **否** |
| **测试证据** | `FotMobThinParsers.test.js` — 有 header.teams alias 测试 |
| **consumer 证据** | 只被 `MatchParser` 内部使用（`MatchParser.js:4,12`） |
| **风险** | 低——函数很薄，输出字段有限 |
| **当前分类** | **confirmed_supporting_parser**（被 MatchParser 内部使用，无直接 consumer） |

### 5.3 PlayerParser

| 项目 | 说明 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/PlayerParser.js` (40行) |
| **输入 shape** | `rawData: object`（从 `lineup.home/away` 或 `lineup.homeTeam/awayTeam` 或 `lineups` 提取） |
| **输出 shape** | `[{ id, name, side, position, rating, raw }, ...]` |
| **关键字段** | `id`, `name`, `side` (home/away), `position`, `rating`, `raw` |
| **是否依赖 NextDataParser.transformToApiFormat** | **否** |
| **是否输出赛前字段** | `side`, `position` — 可能是赛前可知的。`id`, `name` — 赛前可知 |
| **是否输出赛后字段** | `rating` — **赛后字段**（比赛结束后才产生评分） |
| **是否输出 timing/observed_at** | **否** |
| **是否输出 data_version/source/meta** | **否** |
| **测试证据** | `FotMobThinParsers.test.js` — 有 lineup/bench/substitutes/lineups alias 多个测试 |
| **consumer 证据** | **无 src runtime consumer**。只有测试引用 |
| **风险** | 低——函数很薄 |
| **当前分类** | **test_only_parser** |

### 5.4 LeagueParser

| 项目 | 说明 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/LeagueParser.js` (31行) |
| **输入 shape** | `nextData: object` 或 `html: string`（两个入口） |
| **输出 shape** | `{ leagueId, season, name, raw }` 或 `{ success: true/false, data: {...} }` |
| **关键字段** | `leagueId`, `season`, `name`, `raw` |
| **是否依赖 NextDataParser** | **是**——`parseFromHtml` 内部调用 `extractFromHtml` |
| **是否输出赛前字段** | 全部赛前可知（联赛元数据） |
| **是否输出赛后字段** | **否** |
| **是否输出 timing/observed_at** | **否** |
| **是否输出 data_version/source/meta** | **否** |
| **测试证据** | `FotMobThinParsers.test.js` — 有 `__NEXT_DATA__` HTML 解析测试 |
| **consumer 证据** | **无 src runtime consumer**。只有测试引用 |
| **风险** | 低——纯元数据 |
| **当前分类** | **test_only_parser** |

### 5.5 MatchStatsParser

| 项目 | 说明 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/MatchStatsParser.js` (46行) |
| **输入 shape** | `rawData: object`（从 `stats` 或 `content.stats` 或 `matchStats` 提取） |
| **输出 shape** | `{ stats: [{ key, title, home, away, raw }, ...], xg: { xg_home, xg_away, possession_home, possession_away, hasAnyStats } }` |
| **关键字段** | `stats` (统计列表), `xg` (xG + possession 聚合) |
| **是否依赖 NextDataParser.transformToApiFormat** | **否**——但依赖 `XGExtractor.extractAllStats` |
| **是否输出赛前字段** | **很少**——大部分统计（shots/possession/xG/corners/fouls 等）是比赛中或赛后产生的 |
| **是否输出赛后字段** | **大量**——`xg.xg_home/xg_away`、`xg.possession_home/possession_away`、stats 中的 shots/shotsOnTarget/corners/fouls 等 |
| **是否输出 timing/observed_at** | **否** |
| **是否输出 data_version/source/meta** | **否** |
| **测试证据** | `FotMobThinParsers.test.js` — 有 Ball possession 和缺失 xG 安全回退测试 |
| **consumer 证据** | **无 src runtime consumer**。只有测试引用 |
| **风险** | **高**——输出大量赛后字段且无任何 timing 标签；如果被错误接入赛前模型会导致严重数据泄露 |
| **当前分类** | **test_only_parser + postmatch risk** |

### 5.6 XGExtractor

| 项目 | 说明 |
| --- | --- |
| **文件路径** | `src/parsers/fotmob/XGExtractor.js` (152行) |
| **输入 shape** | `data: { content: { stats: { Periods: { All: { stats: [...] } } } } }` — API 格式 |
| **输出 shape** | `extractXG`: `{ xg_home, xg_away, hasXG }`. `extractPossession`: `{ possession_home, possession_away, hasPossession }`. `extractAllStats`: 合并以上两者 + `hasAnyStats` |
| **关键字段** | `xg_home`, `xg_away`, `possession_home`, `possession_away`, `hasXG`, `hasPossession`, `hasAnyStats` |
| **是否依赖 NextDataParser** | **否**——但输入格式与 `transformToApiFormat` 输出兼容 |
| **是否输出赛前字段** | **否**——xG 和 possession 都是典型的赛后/赛中数据 |
| **是否输出赛后字段** | **全部是**——`xg_home/xg_away`、`possession_home/possession_away` |
| **是否输出 timing/observed_at** | **否** |
| **是否输出 data_version/source/meta** | **否** |
| **测试证据** | `tests/unit/XGExtractor.test.js` — 有 extractXG/extractPossession/extractAllStats/validateXG 测试 |
| **consumer 证据** | 只被 `MatchStatsParser` 内部使用（`MatchStatsParser.js:3`）。**无 src runtime 或 tests 之外的 consumer** |
| **风险** | **高**——全部输出是赛后数据。`validateXG` 只检查值合理性（负数/异常高），不做 timing 判断 |
| **当前分类** | **postmatch_extractor** |

---

## 6. Consumer graph findings

### 6.1 Consumer 总表

| # | consumer 文件 | consumer 类型 | import/require 符号 | 消费函数 | 是否 runtime src | 是否 script | 是否 test | 是否 docs | 消费的 output shape | 判断 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `src/infrastructure/harvesters/strategies/FotMobStrategy.js:20` | direct_require | `extractFromHtml`, `transformToApiFormat` | 采集 pipeline 中第 429/434/710 行调用 | **是** | 否 | 否 | 否 | `transformToApiFormat` 输出 `{ matchId, content, general, header, _meta }` | **confirmed_runtime_consumer** |
| 2 | `src/infrastructure/services/FotMobRawDetailFetcher.js:204-205` | injected_deps | `extractFromHtml`, `transformToApiFormat` | `extractHydrationPayload` 中通过注入调用 | **是** | 否 | 否 | 否 | `transformToApiFormat` 输出 | **confirmed_runtime_consumer**（但通过依赖注入） |
| 3 | `src/parsers/fotmob/MatchParser.js:3` | direct_require | `transformToApiFormat` | `parseMatch` 内部调用 | **是**（但本身是 parser） | 否 | 否 | 否 | 自己消费自己 | **internal_parser_dep** |
| 4 | `src/parsers/fotmob/LeagueParser.js:3` | direct_require | `extractFromHtml` | `parseFromHtml` 内部调用 | **是**（但本身是 parser） | 否 | 否 | 否 | 自己消费自己 | **internal_parser_dep** |
| 5 | `scripts/ops/n3_live_fotmob_raw_retain.js:293` | dynamic_require | `extractFromHtml`, `transformToApiFormat` | N3 采集 pipeline | 否 | **是** | 否 | 否 | `transformToApiFormat` 输出 | **script_consumer** |
| 6 | `scripts/ops/single_live_fotmob_raw_ingest_smoke.js:333` | dynamic_require | `extractFromHtml`, `transformToApiFormat` | smoke test | 否 | **是** | 否 | 否 | `transformToApiFormat` 输出 | **script_consumer** |
| 7 | `scripts/ops/l2_raw_match_data_write.js:7` | direct_require | `extractFromHtml`, `transformToApiFormat` | L2 数据写入 | 否 | **是** | 否 | 否 | `transformToApiFormat` 输出 | **script_consumer** |
| 8 | `scripts/ops/l2_raw_match_data_ingest_preflight.js:6` | direct_require | `extractFromHtml`, `transformToApiFormat` | L2 ingest preflight | 否 | **是** | 否 | 否 | `transformToApiFormat` 输出 | **script_consumer** |
| 9 | 其他 ~7 个 ADG/legacy ops scripts | direct_require | `extractFromHtml`, `transformToApiFormat` | ADG 历史采集 | 否 | **是** | 否 | 否 | `transformToApiFormat` 输出 | **script_consumer**（legacy ADG） |
| 10 | `tests/unit/DataIntegrity.test.js` | direct_require | NextDataParser 全模块 | 测试 | 否 | 否 | **是** | 否 | 多场景 | **test_consumer** |
| 11 | `tests/unit/Parsing_Core.test.js` | direct_require | `extractFromHtml`, `transformToApiFormat` | 测试 | 否 | 否 | **是** | 否 | 多场景 | **test_consumer** |
| 12 | `tests/unit/TitanFullRegistry.test.js` | direct_require | `transformToApiFormat`, `validateNextDataStructure` | 测试 | 否 | 否 | **是** | 否 | 多场景 | **test_consumer** |
| 13 | `tests/unit/shared_helper_branch_margin.test.js` | direct_require | NextDataParser 全模块 | 测试 | 否 | 否 | **是** | 否 | branch coverage | **test_consumer** |
| 14 | `tests/unit/collectors/fotmob/FotMobThinParsers.test.js` | direct_require | MatchParser, TeamParser, PlayerParser, LeagueParser, MatchStatsParser | thin parser 集成测试 | 否 | 否 | **是** | 否 | 各 thin parser 输出 | **test_consumer** |

### 6.2 关键结论

1. **NextDataParser 有两个 confirmed runtime src consumer**：
   - `FotMobStrategy.js` — 采集策略中的 parser 使用（harvester pipeline）
   - `FotMobRawDetailFetcher.js` — 通过依赖注入使用（但不是直接 require，而是接受 parser deps）
   
2. **NextDataParser 是 10+ ops scripts 的实际使用 parser**。

3. **thin parsers（MatchParser、TeamParser、PlayerParser、LeagueParser、MatchStatsParser、XGExtractor）均无 src runtime consumer**。
   - MatchParser 和 LeagueParser 内部使用了 NextDataParser，但它们自己只被测试调用。
   - TeamParser 只被 MatchParser 内部使用（间接也无 consumer）。
   - PlayerParser、MatchStatsParser、XGExtractor 只被测试调用。

4. **parser index.js 把所有 parser 统一导出，但全仓库无代码引用 index.js**。所有引用方都是直接引用具体文件路径。

### 6.3 真正在跑的链路

```text
【采集链路】
FotMobRawDetailFetcher (html_hydration)
  → NextDataParser.extractFromHtml()        ← HTML → __NEXT_DATA__ JSON
    → NextDataParser.transformToApiFormat()  ← __NEXT_DATA__ → API-like format
      → raw_match_data.raw_data (DB 存储)

FotMobStrategy (harvester)
  → NextDataParser.extractFromHtml()
    → NextDataParser.transformToApiFormat()
      → (harvest pipeline 内消费)

【10+ ops scripts 链路】
  → NextDataParser.extractFromHtml()
    → NextDataParser.transformToApiFormat()
      → DB 写入或预览

【特征链路】
FeatureSmelter
  → SQL: SELECT ... FROM raw_match_data ...
    → GoldenFeatureExtractor.extractGoldenFeatures(rawData)  ← 直接读 raw_data JSON
      → TacticalMomentumExtractor (xG, possession, shots)
        → OddsMovementExtractor
```

---

## 7. Feature engine consumption check

### 7.1 是否直接引用 NextDataParser / thin parsers?

**否。**

```bash
grep -rn "require.*parsers/fotmob" -- src/feature_engine src/features
# → NO_DIRECT_PARSER_IMPORT_IN_FEATURE_ENGINE
```

`src/feature_engine/smelter/FeatureSmelter.js` 的 import 列表：

```javascript
const { getPool, withRetry, checkHealth, closePool, isRetryableError } = require('../../../config/database');
const { extractGoldenFeatures } = require('../extractors/GoldenFeatureExtractor');
const { extractTacticalFeatures } = require('../extractors/TacticalMomentumExtractor');
const { extractOddsMovementFeatures } = require('../extractors/OddsMovementExtractor');
```

没有任何 `src/parsers/fotmob/*` 的引用。

### 7.2 是否直接消费 FotMob output shape?

**不直接消费 parser 输出。** 特征引擎通过 SQL 直接从 `raw_match_data.raw_data` JSON 字段读取原始数据，然后用自己的 extractors 解析：

```javascript
// GoldenFeatureExtractor.js 中
const teamData = safeGet(rawData, `content.lineup.${teamKey}`, null);
```

特征引擎访问的路径（如 `content.lineup`）与 NextDataParser 输出的字段（如 `content.lineup`）在结构上一致，但这不是通过 parser import 实现的——是各自独立读取同一个 JSON 结构。

### 7.3 是否只是 FotMobSchemaGuard / smelter / schema diff?

`FotMobSchemaGuard.js` 位于 `src/feature_engine/`，但它是一个 key shape diff guard——只检测 schema 变化，不做 feature extraction。被 `generate_fotmob_collection_report.js` 和 `smelter/index.js` 引用。

`FeatureSmelter.js` 是真正的 feature pipeline 入口。它通过 SQL 读取 `raw_match_data`，不 import 任何 parser。

### 7.4 结论

**特征引擎和 parser 运行在两个独立的世界里：**
- Parser：HTML → `__NEXT_DATA__` → API-like format。消费方是采集器（FotMobRawDetailFetcher、FotMobStrategy）和 ops scripts。
- Feature engine：`raw_match_data.raw_data` JSON → 特征提取。消费方是 training/pipeline。

两者之间唯一的连接点是 `raw_match_data.raw_data` 字段——parser 处理后的数据被存储到 DB，feature engine 再从 DB 读取。但代码层面没有直接的 import 依赖。

---

## 8. Data version and metadata shape

### 8.1 NextDataParser 产生的 metadata

`transformToApiFormat` 输出中的 `_meta` 块：

```javascript
_meta: {
    source: 'web_infiltration',          // 硬编码，表示来自浏览器/HTML 采集
    extractedAt: '2026-07-04T04:17:...', // new Date().toISOString()
    hasStats: true/false,               // content.stats 是否存在
    hasLineup: true/false,              // content.lineup 是否存在
    hasShotmap: true/false              // content.shotmap 是否存在
}
```

**缺失的 metadata**：
- `data_version` — `transformToApiFormat` 不标注 data_version
- `payload_hash` — 不计算 hash
- `storage_path` — 不标注存储路径
- `captured_at` — 有 `extractedAt`，但语义不同（`extractedAt` 是 parser 调用时间，不是数据采集时间）
- `parser_version` — 无
- `parser_name` — 无

### 8.2 FotMobRawDetailFetcher 产生的 metadata

来自 `buildStableRawPayload` 和 hash 计算：

```javascript
_meta: {
    source: '...',
    route: '...',
    data_version: 'fotmob_html_hyd_v1',  // 推断
    fetched_at: '...',
    hash_strategy: 'stable_raw_payload_v1',
    data_hash: 'sha256...',
    parser: 'NextDataParser',
    // ...
}
```

FotMobRawDetailFetcher 的 metadata 比 NextDataParser 的 `_meta` 更完整——它有 `data_version`、`data_hash`、`parser`、`fetched_at`。

### 8.3 RawMatchDataVersionSelector 认可的 data_version

| data_version | 分类 | canonical? |
| --- | --- | --- |
| `fotmob_pageprops_v2` | `canonical_fotmob_pageprops` | **是**（最高优先级） |
| `fotmob_html_hyd_v1` | `canonical_fotmob_transformed` | **是** |
| `PHASE4.43_SYNTHETIC` | `legacy_synthetic` | 否 |
| `PHASE4.23` | `legacy_unknown` | 否 |

**注意：`fotmob_live_v1` 不在列表中，会被归为 `unknown`。**

### 8.4 thin parsers 是否保留 metadata

**不保留。** MatchParser、TeamParser、PlayerParser、LeagueParser、MatchStatsParser、XGExtractor 的输出均不包含 `_meta`、`data_version`、`source` 等 metadata 字段。

唯一近似的是 `MatchParser` 的 `raw` 字段保留了原始输入引用，可能间接包含 metadata——但这取决于输入来源。

### 8.5 缺失字段处理原则

如果旧代码没有 `captured_at` / `payload_hash` / `storage_path`，**不得在 adapter 中伪造可信值**。第一版 envelope dry-run 可以显式使用 `null` / `'unknown'`。

| 字段 | NextDataParser 有? | Fetcher 有? | 建议 adapter 如何处理 |
| --- | --- | --- | --- |
| `captured_at` | `extractedAt`（语义不同） | `fetched_at` | envelope 用 `fetched_at`，fallback `extractedAt`，再 fallback `null` |
| `payload_hash` | 无 | `data_hash` | envelope 用 `data_hash`，fallback `null` |
| `storage_path` | 无 | 可能有（取决于 fetch pipeline） | `null` |
| `data_version` | 无 | `fotmob_html_hyd_v1` | envelope 用 fetcher 的 `data_version` |
| `source` | `'web_infiltration'` | 可能有更准确来源 | 取最接近数据来源的值 |

---

## 9. Prematch safety risk mapping

| 字段/字段族 | 是否可能由 NextDataParser / thin parsers 输出 | 风险分类 | future timing_class | future model_eligibility | 是否可进入赛前模型 | 证据需求 |
| --- | --- | --- | --- | --- | --- | --- |
| **xG (xg_home, xg_away)** | **是** — XGExtractor / MatchStatsParser 输出 | **POSTMATCH** — 比赛结束后才知道 | `post_match_calculated` | `forbidden_postmatch` | **否** | 需要 cutoff 规则：xG 仅在 full_time+24h 后可用于复盘，不进入赛前预测 |
| **shots** | **是** — content.stats 包含 | **POSTMATCH** | `post_match_observed` | `forbidden_postmatch` | **否** | 同上 |
| **score / result** | **是** — MatchParser/TeamParser 输出 score 字段 | **POSTMATCH** — 比赛结果 | `post_match_outcome` | `forbidden_postmatch` | **否** | score 只能在赛后使用，赛前模型必须排除 |
| **events (timeline)** | 可能 — content 包含 events | **POSTMATCH** | `post_match_observed` | `forbidden_postmatch` | **否** | events 是比赛中产生的时间线 |
| **shotmap** | **是** — content.shotmap 存在于 pageProps | **POSTMATCH** | `post_match_observed` | `forbidden_postmatch` | **否** | shotmap 是比赛中产生的 |
| **player stats / ratings** | **是** — PlayerParser 输出 rating | **POSTMATCH** — 比赛后产生 | `post_match_calculated` | `forbidden_postmatch` | **否** | rating 是赛后评分 |
| **possession** | **是** — XGExtractor / MatchStatsParser 输出 | **POSTMATCH** — 比赛中的统计 | `post_match_observed` | `forbidden_postmatch` | **否** | possession 在比赛中变化，终值赛后才知道 |
| **lineup** | **是** — content.lineup 存在于 pageProps | **PREMIXED** — lineup 可能在开球前 1 小时公布，但也可能赛后更新 | `prematch_observed` 或 `post_match_observed`（取决于 observed_at） | `conditional_safe_prematch`（需要 cutoff 证据） | **需要 cutoff** | 需要 lineup observed_at 与 kickoff 的时间比较 |
| **injury** | 可能 — 在 lineup 或 stats 中 | **PREMIXED** — 赛前宣布 | `prematch_reported` | `conditional_safe_prematch` | **需要 cutoff** | 需要 injury 发布时间 |
| **odds** | **否** — FotMob 不提供赔率（FeatureSmelter 注释明确说"FotMob 不提供赔率数据，需实现 OddsPortalProvider"） | 不适用 | 不适用 | 不适用 | 不适用 | 来自 OddsPortal，非 FotMob |
| **table / form** | 可能 — general 中包含 | **PREMIXED** — 赛前已知 | `prematch_calculated` | `safe_prematch` | 可能是 | 需要确认 general 中是否包含实时排名 |
| **raw payload / pageProps / __NEXT_DATA__** | **是** — 这是所有字段的来源 | **MIXED** — 包含赛前和赛后字段 | N/A（raw 本身不进模型） | N/A | N/A | raw payload 只能作为证据，不能直接进模型 |

### 关键原则

- **Parser 可以提取赛后字段，但 envelope 必须贴 `forbidden_postmatch`。**
- **`raw payload/pageProps/__NEXT_DATA__` 只能作为数据来源证据，不能直接进模型。**
- **`unknown_timing` 默认不能进模型。**
- **`lineup/injury/odds/table/form` 在没有 `observed_at`/`cutoff` 证据前不能直接作为 `safe_prematch`。**

---

## 10. Envelope adapter candidate boundary

### 候选边界总览

| 边界 | 描述 |
| --- | --- |
| **A** | Wrap `NextDataParser.transformToApiFormat` 输出 |
| **B** | Wrap thin parser 输出（MatchParser/TeamParser 等） |
| **C** | Wrap `FotMobRawDetailFetcher` stable raw payload 输出 |
| **D** | 不 wrap 任何输出，需要 DATA-L1F-2C 进一步确认 |

### 边界 A: Wrap transformToApiFormat 输出

| 维度 | 评估 |
| --- | --- |
| **优点** | 1. 有 confirmed runtime consumer（FotMobStrategy、FotMobRawDetailFetcher）。2. 有 10+ ops scripts consumer。3. 输出结构明确（matchId/content/general/header/_meta）。4. `_meta` 已包含 source/extractedAt/hasStats/hasLineup/hasShotmap。5. 是标准化后的中间格式 |
| **缺点** | 1. `_meta` 不包含 data_version/payload_hash/storage_path。2. `content` 是原始嵌套对象，字段没有展开。3. `extractedAt` 语义不等于 `captured_at`。4. 是"中间格式"不是"最终输出" |
| **metadata 可用性** | **中等** — 有 source + extractedAt，缺 data_version + payload_hash |
| **field-level granularity** | **低** — content/stats/lineup/shotmap 都是嵌套原始对象 |
| **postmatch risk handling** | **低** — 没有字段级 timing 标记；需要 adapter 检查 `_meta.hasStats/hasLineup/hasShotmap` 并标记风险 |
| **是否需要改 runtime** | **否** — 只是包在现有函数输出外面 |
| **是否适合作为 DATA-L1E-2 dry-run** | **是** — 这是最清晰的现有接入点。adapter 接收 transformToApiFormat 输出，加上缺失的 metadata，标记 postmatch 风险字段 |
| **结论** | **推荐候选** |

### 边界 B: Wrap thin parser 输出

| 维度 | 评估 |
| --- | --- |
| **优点** | 1. 输出更具体（match/team/player/stats 各自独立）。2. 字段更结构化 |
| **缺点** | 1. **thin parsers 没有任何 runtime consumer**。2. 包一个没人调用的 thin parser 没有意义。3. 需要分别包 6 个不同的输出。4. metadata 更不完整 |
| **metadata 可用性** | **低** — thin parsers 不保留任何 _meta |
| **field-level granularity** | **高** — 字段已展开 |
| **postmatch risk handling** | **混淆** — score/rating/xg 与 matchId/teamName 混在一起 |
| **是否需要改 runtime** | 可能需要 — 需要先让 feature engine 或采集器改用 thin parsers |
| **是否适合作为 DATA-L1E-2 dry-run** | **否** — thin parsers 没有 runtime consumer，dry-run 没有验证对象 |
| **结论** | **不推荐** |

### 边界 C: Wrap FotMobRawDetailFetcher stable raw payload 输出

| 维度 | 评估 |
| --- | --- |
| **优点** | 1. metadata 最完整（data_version、data_hash、fetched_at、parser、hash_strategy）。2. 有 confirmed consumer（多个 ops scripts）。3. 是"最接近采集源"的层 |
| **缺点** | 1. 输出包含完整 HTML body——太大，不适合做 envelope。2. 不是在 parser 输出层。3. 需要 adapter 同时处理 HTML 和已解析数据 |
| **metadata 可用性** | **高** |
| **field-level granularity** | **最低** — 是 raw payload，字段未解析 |
| **postmatch risk handling** | 无法处理 —— 还没到 parser 层 |
| **是否需要改 runtime** | 可能 |
| **是否适合作为 DATA-L1E-2 dry-run** | **否** — 太底层，不适合 parser output envelope |
| **结论** | **不推荐** — Fetcher metadata 可以复用，但不是 envelope 的接入层 |

### 边界 D: Do not wrap yet; need DATA-L1F-2C

| 维度 | 评估 |
| --- | --- |
| **说明** | 如果以上边界都不够清楚，需要 DATA-L1F-2C 确认下游 consumer 具体消费什么格式 |
| **结论** | **不需要** — 边界 A 已足够清晰。NextDataParser.transformToApiFormat 是有 confirmed runtime consumer 的、标准化后的中间格式，适合作为 envelope adapter 的接入点 |

### 推荐边界

**推荐边界 A: Wrap `NextDataParser.transformToApiFormat` 输出。**

理由：
1. 这是唯一有 confirmed runtime src consumer（FotMobStrategy）的输出层。
2. 输出结构清晰（4 个顶层字段 + _meta）。
3. `_meta` 提供了基本的 metadata 锚点。
4. 不需要改任何 runtime 代码——adapter 只是在 `transformToApiFormat` 返回值外面多包一层。
5. 未来可以在 adapter 中补 metadata（来自 FotMobRawDetailFetcher 的 fetcher metadata）和 timing 标签。

---

## 11. Decision

### 总体结论

1. **NextDataParser.transformToApiFormat 是仓库中真正被使用的 FotMob parser 输出**。它有 2 个 runtime src consumer、10+ ops scripts consumer、6+ test consumer。

2. **thin parsers（MatchParser/TeamParser/PlayerParser/LeagueParser/MatchStatsParser/XGExtractor）虽然被 index.js 导出，但没有任何 runtime consumer**，只有测试在用。

3. **feature engine 不 import 任何 parser**。它通过 SQL 直接读取 `raw_match_data.raw_data`，用自己的 extractors 处理。Parser 和 feature engine 在代码层面互相独立。

4. **推荐 envelope adapter 包在 `NextDataParser.transformToApiFormat` 输出外面**（边界 A）。这是唯一有 runtime consumer 的标准化 parser 输出层。

### DATA-L1E-2 是否可以解锁?

**如果用户接受边界 A（transformToApiFormat），DATA-L1E-2 可以解锁。**

前提条件：
- 用户明确接受推荐边界
- DATA-L1E-2 仍为 dry-run
- adapter 不修改 feature/training/backtest
- adapter 显式标注已知的 metadata 缺失和 postmatch 风险字段
- fotmob_live_v1 / FotMobRawParser 路径不进入 adapter scope

### 是否还需要 DATA-L1F-2C?

**如果用户接受边界 A：不需要。** 边界 A 的 runtime consumer 和 output shape 都已确认。

**如果用户不接受边界 A：需要 DATA-L1F-2C**，追踪 FotMobStrategy 和 feature engine 的具体数据格式对接点。

---

## 12. Recommended next step

根据审计结果，推荐 **选项 A**：

**如果用户接受推荐边界（NextDataParser.transformToApiFormat），可以启动 DATA-L1E-2 dry-run adapter。**

DATA-L1E-2 应该在以下约束下执行：
1. 只包 `transformToApiFormat` 输出（不包 thin parsers、不包 FotMobRawParser）。
2. 从 FotMobRawDetailFetcher metadata 补 `data_version` / `data_hash` / `fetched_at`。
3. 显式标注已知 postmatch 风险字段（stats/xG/possession/shotmap/lineup events/score/rating）。
4. 保持 dry-run——不修改 feature/training/backtest。
5. 不访问 FotMob 网络、不写 DB。

**Do not start automatically.**

**Recommended next task only after user confirmation:**

- 如果用户接受边界 A：DATA-L1E-2: Legacy FotMob Adapter Dry-Run（基于 transformToApiFormat 输出）。
- 如果用户不接受：DATA-L1F-2C: Runtime Entry Point and Downstream Consumer Identification。

**DATA-L1E-2 remains blocked unless the user explicitly accepts the verified adapter boundary.**

---

## 13. Explicit non-goals

本次 DATA-L1F-2B 明确没有做以下任何事情：

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
- 没有启动 DATA-L1F-2C
- 没有启动 DATA-L2
- 没有启动 CLEANUP-L1A
- 没有启动 L3I / L4
- 没有删除 / 移动 / 重命名 legacy 文件

---

## 14. 关键证据索引

| 证据类别 | 搜索命令 | 关键发现 |
| --- | --- | --- |
| NextDataParser runtime src consumer | `git grep "NextDataParser" -- src` | FotMobStrategy.js + FotMobRawDetailFetcher.js |
| NextDataParser script consumer | `git grep "NextDataParser" -- scripts` | 10+ ops scripts |
| thin parser src consumer | `git grep "MatchParser\|TeamParser\|..." -- src` | 无 runtime consumer，只有内部互相引用 |
| feature engine parser import | `grep -rn "require.*parsers/fotmob" -- src/feature_engine` | **零匹配** |
| index.js consumer | `git grep "require.*parsers/fotmob['\"]" -- src` | 零匹配（全部直接引用具体文件） |
| transformToApiFormat 输出 | 只读查看 NextDataParser.js:118-146 | `{ matchId, content, general, header, _meta }` |
| 各 thin parser 源码 | 只读查看 6 个 parser 文件 | 各自 output shape 明确 |
| data_version canonical 列表 | 只读查看 RawMatchDataVersionSelector.js | `fotmob_pageprops_v2` > `fotmob_html_hyd_v1` |

---

## 15. NextDataParser 和 thin parsers 相关 git 历史

```text
# NextDataParser 已存在较长时间，是仓库最早的 FotMob parser 之一
# 具体历史提交可通过以下命令查看：
# git log --oneline --max-count=30 -- src/parsers/fotmob/NextDataParser.js
```

本次只读审计不依赖 git 历史细节——output shape 完全由当前源码确定。
