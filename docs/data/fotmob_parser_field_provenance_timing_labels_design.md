# FotMob Parser Field Provenance and Timing Labels Design

- lifecycle: source-of-truth
- scope: docs-only, FotMob parser 字段来源与时间标签设计
- parent audits/contracts: DATA-L1A, DATA-L1B, DATA-L1C
- branch: `docs/data-l1d-fotmob-parser-provenance-timing-design`

---

## 1. 背景

DATA-L1A（PR #1694）已完成并合并。它在仓库里发现 FotMob 字段存在赛前/赛后时间边界风险。

DATA-L1B（PR #1695）已完成并合并。它建立了 FotMob 赛前字段合同，把字段分成 5 类：safe_prematch_candidate、unsafe_postmatch、unknown_timing、metadata_only、debug_or_raw_only。

DATA-L1C（PR #1696）已完成并合并。它建立了 raw payload 保留与回放策略，定义了 raw payload 应该保留什么 metadata、如何支持 parser replay、schema drift 检测和 cutoff safety audit。

DATA-L1D 的目标不是继续写字段清单（那是 DATA-L1B 的工作），也不是实现 parser（那是代码 PR 的工作）。DATA-L1D 要设计的是：**parser 未来如何给每个字段打 provenance label（"从哪里来"）和 timing label（"什么时候可见"）**。

可以用一个类比来理解 DATA-L1 系列的关系：

```text
DATA-L1A = 体检报告——查出风险
DATA-L1B = 饮食禁忌表——规定什么能吃、什么不能吃、什么不确定
DATA-L1C = 食材进货小票和监控录像保存制度——原始证据怎么保留
DATA-L1D = 每道菜上桌前贴标签——来自哪、什么时候进货、能不能给病人吃
```

本文件是 parser 字段 provenance / timing labels 的设计文档。它不是 parser 改造，不是 scraper 改造，不是 DB / migration 改造，不是 feature 改造，不是 training。它不运行任何采集，不运行 parser，不改变任何现有 runtime 行为。它只立设计。

---

## 2. 为什么需要 provenance 和 timing labels

现在 FotMob 相关的问题是 **不是"parser 能不能解析字段"，而是"parser 解析出来的字段到底从哪里来、什么时候可见、能不能用于赛前模型"**。

举个例子。假设 FotMobRawParser 目前能输出：

```text
xG = 1.25
lineup = [{...}]
odds = 2.10
home_team = "Paris SG"
```

feature engine 或 training pipeline 看到这些字段，**完全不知道**：

- xG 是赛后字段还是赛前字段？
- lineup 是比赛开始前 1 小时就有的首发，还是赛后从 JSON 里拿的？
- odds 是初盘、临场盘、终盘，还是赛后补录的记录？
- 这个字段来自哪个 raw payload？
- 是哪个 parser version 解析的？
- 这个字段在 prediction_cutoff_time 之前存在吗？

没有这些信息，feature engine 无法做 cutoff 检查。training 无法知道哪些字段是泄露的。backtest 无法模拟真实赛前状态。

换句话说：

```text
字段值  = 食材
provenance label = 食材来自哪家供应商、哪张进货单、谁经手的
timing label = 食材什么时候进仓、有没有过期
model_eligibility = 这食材能不能给今天的病人吃

没有这些标签，厨房不知道什么能吃、什么不能吃。
```

---

## 3. 核心原则

这些原则是本设计文档的基石。优先级高于具体字段设计。

1. **parser output 不能只给 value，必须能携带 field-level metadata。** 裸字段值不说明任何问题。一个 `xG = 1.25` 和另一个 `xG = 1.25` 的差别在于：一个来自 live-match 时间、一个来自 postmatch 时间。标签是区分它们的关键。

2. **每个字段未来都应该有 provenance：source / payload_hash / parser_version / field_path。** 这四个值加起来可以唯一确定"这个字段值是从哪里、通过什么路径、在哪个 parser 版本下提取的"。

3. **每个字段未来都应该有 timing_class。** 没有 timing label 的字段，默认不能信任。

4. **每个字段未来都应该有 model_eligibility。** 这是 parser 根据 DATA-L1B 字段合同给字段打的"能不能用于赛前模型"的初步判定。最终 enforcement 由 feature engine / training / backtest 执行。

5. **unsafe_postmatch 字段即使被 parser 解析出来，也必须标记为 forbidden_for_prematch_model。** parser 可以解析 xG、score、shotmap 这些东西——这本身不是错误。错误是后续把它们送进赛前模型。parser 要做的是清楚地标记它们。

6. **unknown_timing 字段默认不能进入模型，直到有字段级 observed_at 证明它在 cutoff 前可用。**

7. **raw payload / pageProps / `__NEXT_DATA__` 只能作为来源证据，不能直接进入模型。** 这是 DATA-L1B 和 DATA-L1C 的共同要求。

8. **captured_at 是 payload 时间，不等于字段 observed_at。** 赛后抓取的 JSON 可能同时包含赛前字段和赛后字段。

9. **observed_at 是字段的可见时间，必须尽量做到字段级记录。** 如果一个字段无法确定 observed_at，它应该被标记为 unknown_timing。

10. **prediction_cutoff_time 是模型使用数据的截止时间。** 它不来自 parser，而来自 prediction task 的定义。parser 的角色是提供足够的信息让 feature engine 能判断 cutoff safety。

11. **parser 不应该自己决定最终能不能训练。** parser 只负责输出标签；feature engine / training / backtest 根据 DATA-L1B 合同和 cutoff 时间执行实际操作。

12. **DATA-L1B 决定字段能不能用；DATA-L1C 规定原始证据怎么保留；DATA-L1D 设计 parser 如何把证据传下去。** 三者是一套完整的数据信任链。

---

## 4. 术语定义

| 术语 | 含义 | 用途 | 与 DATA-L1B / DATA-L1C 的关系 | 风险 |
| --- | --- | --- | --- | --- |
| **provenance** | 字段的来源信息（从哪个 payload 的哪条路径提取） | 追溯字段来源、版本选择、事故复盘 | DATA-L1C 要求保留 raw payload 证据；provenance 是"把证据连到字段"的桥梁 | 如果 provenance 丢失或错误，后续审计全错 |
| **field provenance** | 单个字段的来源（source / payload_hash / field_path / parser_version） | 回答"xG=1.25 这个值从哪来" | 直接实现 DATA-L1C §5 的 metadata 要求 | 同名字段可能来自不同 payload/路径 |
| **payload provenance** | payload 本身的来源信息（captured_at / source_url / data_version / capture_method） | 回答"这个 payload 什么时候、怎么来的" | 与 DATA-L1C §4 的 capture metadata 对齐 | payload 的来源不等于字段的来源 |
| **field_path** | 字段在 raw payload 中的位置（如 `$.general.homeTeam.name`） | 用于 schema drift 检测、parser 回归、字段追溯 | 数据沿袭自 DATA-L1C §8 schema drift | FotMob 可能改字段路径，field_path 会过期 |
| **payload_hash** | 原始 payload 的 SHA-256 哈希值 | 去重、完整性校验、确定最终数据来源 | 与 DATA-L1C §5 的 payload_hash 对齐 | 如果 hash 算法不一致，hash 无用 |
| **parser_version** | 解析该字段的 parser 版本号 | 用于 parser 回归测试、已知 bug 追溯 | DATA-L1C §7 parser replay 依赖此字段 | 如果 parser version 记录不准，replay 无意义 |
| **payload_type** | payload 的类型：raw_json / pageProps / NEXT_DATA / html_hydration / parser_input | 不同 type 对应不同 parser 入口 | 与 DATA-L1C §4 的 payload_type 对齐 | 不同类型可能包含不同字段结构 |
| **captured_at** | raw payload 被采集的时间戳（ISO 8601） | 判断 payload 整体是否赛前存在 | 与 DATA-L1C §5 的 captured_at 对齐 | captured_at 早不代表每个字段早 |
| **observed_at** | 某个具体字段在数据中被"观察到"的时间点 | 判断字段是否在 cutoff 前已存在 | DATA-L1C §9 cutoff safety audit 的输入 | 很难做到字段级；如果没有则默认为 captured_at 但不安全 |
| **prediction_cutoff_time** | 模型预测的截止时间——此时间之后的信息不能用于预测 | 决定字段是否属于"未来信息" | 与 DATA-L1B 的 cutoff 概念一致 | 由 prediction task 定义，parser 不主动设置 |
| **timing_class** | 字段的时间分类标签（fixture_metadata / prematch / near_kickoff / live / postmatch / unknown / derived / raw_only） | 告诉 feature engine 字段可能在何时存现 | 直接实现 DATA-L1B 的时间边界规则 | 一个字段可能同时属于多个 timing_class？不应该，只取最保守的 |
| **model_eligibility** | 字段是否能用于赛前模型（allowed / candidate_if_cutoff / forbidden） | feature engine / training 按此过滤 | 直接实现 DATA-L1B 的模型使用规则 §5 | parser 只给初步标签，最终由 feature engine 执行 |
| **field_contract_class** | 该字段在 DATA-L1B 中的合同分类（safe_prematch_candidate / unsafe_postmatch / unknown_timing / metadata_only / debug_or_raw_only） | 与 DATA-L1B 一一对应，是所有标签的"根分类" | 直接引用 DATA-L1B 字段合同 | 新增字段需要更新 DATA-L1B 合同 |
| **parser output envelope** | parser 输出的顶层结构，包含 match-level 元数据 + payload 元数据 + parser 元数据 + fields 数组 | 统一 parser 与下游 interface | 不依赖 DATA-L1C 但受它的 metadata 要求启发 | 如果 envelope 太重会影响 parser 性能 |
| **parser replay fixture** | 用于 parser 回归测试的 raw payload + expected output | parser 版本升级后验证字段没有消失/改变 | 与 DATA-L1C §7 replay 策略一致 | replay fixture 不能代表真实线上 raw 质量 |
| **schema drift** | FotMob 页面结构随时间的自然变化（字段新增/删除/重命名/类型变化/路径变更） | 用于提前发现 parser 退化并重新评估字段合同 | 直接实现 DATA-L1C §8 schema drift 检测 | schema 变化不代表字段合同变化——前者结构、后者安全 |
| **cutoff safety check** | 对某个字段、某个 feature、某场比赛：检查 observed_at ≤ prediction_cutoff_time 且字段合同分类允许 | 训练/回测/线上预测的最后一道防线 | 组合 DATA-L1B 规则 + DATA-L1C 证据 + DATA-L1D 标签 | 字段级 observed_at 如果缺失，只能按 captured_at 近似，有风险 |

---

## 5. parser output envelope 设计

### 5.1 问题

目前 FotMobRawParser 的输出是一个嵌套结构（match → teams → stats → lineup → events → shotmap → playerStats 等），每个字段只有值，没有任何标签。下游完全不知道这些字段分别属于哪个分类、来自哪里、什么时候可见。

### 5.2 设计目标

parser output 未来应该有一个统一的 envelope，包含几个层次的信息：

```text
[envelope]
  └─ match_metadata:      比赛级别的上下文（match_id, league, season, cutoff 等）
  └─ payload_metadata:    payload 级别的来源信息（captured_at, payload_hash, data_version 等）
  └─ parser_metadata:     parser 自身信息（parser_name, parser_version, parsed_at）
  └─ fields:              字段数组，每个字段都有完整的 provenance + timing + contract + eligibility
```

### 5.3 envelope 示例结构（只作为文档说明，不实现）

```json
{
  "match_id": "123456",
  "external_id": "fotmob_123456",
  "prediction_cutoff_time": null,

  "payload": {
    "source": "fotmob",
    "payload_type": "pageProps",
    "payload_hash": "sha256:a1b2c3d4e5f6...",
    "captured_at": "2026-07-03T12:00:00Z",
    "source_url": "https://www.fotmob.com/api/matchDetails?matchId=123456",
    "final_url": "https://www.fotmob.com/en-us/matches/liverpool-vs-man-city/123456",
    "data_version": "pageprops_v2",
    "capture_method": "api_direct"
  },

  "parser": {
    "parser_name": "FotMobRawParser",
    "parser_version": "v-next-provenance",
    "parsed_at": "2026-07-03T12:01:00Z",
    "parser_rules_version": "DATA-L1B_v1.0"
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
      "notes": "stable fixture identity"
    },
    {
      "name": "kickoff_time",
      "value": "2026-07-10T20:00:00Z",
      "field_path": "$.general.matchTimeUTC",
      "field_contract_class": "safe_prematch_candidate",
      "timing_class": "fixture_metadata",
      "observed_at": null,
      "model_eligibility": "candidate_if_cutoff_valid",
      "notes": "cutoff calculation baseline"
    },
    {
      "name": "home_team_expected_goals",
      "value": 1.25,
      "field_path": "$.content.stats.xG",
      "field_contract_class": "unsafe_postmatch",
      "timing_class": "postmatch",
      "observed_at": null,
      "model_eligibility": "forbidden_postmatch",
      "notes": "Extracted via XGExtractor; must never enter prematch model"
    },
    {
      "name": "home_team_lineup",
      "value": [{ "name": "Player 1", "position": "GK" }],
      "field_path": "$.content.lineup.lineup",
      "field_contract_class": "unknown_timing",
      "timing_class": "near_kickoff_snapshot",
      "observed_at": null,
      "model_eligibility": "forbidden_unknown_timing",
      "notes": "May be safe for T-1H horizon with explicit observed_at; T-24H forbidden"
    },
    {
      "name": "opening_odds_1x2_home",
      "value": 2.10,
      "field_path": "$.content.odds.open.home",
      "field_contract_class": "safe_prematch_candidate",
      "timing_class": "prematch_snapshot",
      "observed_at": "2026-07-03T12:00:00Z",
      "model_eligibility": "candidate_if_cutoff_valid",
      "notes": "Only safe if captured_at <= prediction_cutoff_time"
    }
  ]
}
```

### 5.4 本 PR 不做什么

- 不实现上面这个结构。
- 不修改 FotMobRawParser、NextDataParser、XGExtractor 或任何 parser 代码。
- 不修改 src/parser/**。
- 不修改 src/feature_engine/**。
- 不修改 training / backtest。
- 只定义设计。未来实施 code PR 时才可以实现 envelope。

### 5.5 向后兼容说明

现有 parser 输出（裸值结构）在未来实施 envelope 之前保持不变。envelope 应该是一个渐进式升级：可以先加一个 flat metadata map，再逐步丰富到完整 envelope。不要求一次性重写所有 parser。

---

## 6. field provenance label 设计

provenance label 回答的问题是：**这个字段值是从哪里来的？**

### 6.1 必须包含的标签

| label | 是否必需 | 用途 | 示例 | 风险说明 |
| --- | --- | --- | --- | --- |
| `source` | ✅ 是 | 数据来源标识 | `"fotmob"` | 如果标错来源，后续所有追溯都错 |
| `payload_type` | ✅ 是 | payload 格式类型 | `"pageProps"` | 不同类型对应不同 parser 入口，混用会导致解析错误 |
| `payload_hash` | ✅ 是 | 原始 payload SHA-256 | `"sha256:a1b2c3..."` | 如果 hash 变了但 match_id 相同，说明 FotMob 数据更新了 |
| `data_version` | ✅ 是 | 数据版本标记 | `"pageprops_v2"` | 同一场比赛可能有多个 data_version 的 payload，不同 version 字段可能不同 |
| `parser_name` | ✅ 是 | 解析该字段的 parser 名称 | `"FotMobRawParser"` | 不同 parser 可能从不同路径提取同名字段 |
| `parser_version` | ✅ 是 | parser 版本号 | `"v-next-provenance"` | parser 升级后字段含义可能变化 |
| `field_path` | ✅ 是 | 字段在 raw payload 中的 JSON path | `"$.general.homeTeam.name"` | 同名字段可能来自不同位置；FotMob 结构变化后路径可能失效 |

### 6.2 强烈建议的标签

| label | 用途 | 风险说明 |
| --- | --- | --- |
| `capture_method` | 采集方式（api / ssr / browser / proxy） | 不同方式获取的 payload 结构可能不同；proxy 比 api 多 latency 但未必多字段 |
| `raw_storage_path` | raw payload 文件存储路径 | 如果文件被移动或删除，这个 path 就变成空指针 |
| `field_extraction_rule` | parser 中提取该字段的具体规则或代码路径 | 如果 parser 重构，这个 rule 可能不再适用 |
| `source_route` | FotMob API route 或页面 route | 不同 route 的字段结构不同（matchDetails vs matchStats vs 其他） |
| `language` / `locale` | payload 的语言/地区 | 不同 locale 的字段名称可能不同 |

### 6.3 为什么不直接用 payload 整体 metadata 替代字段级的 provenance

因为同一份 raw payload 里，不同字段可以有不同的 field_path。pageProps 里 xG 在 `$.content.stats.xG` 而 home_team 在 `$.general.homeTeam.name`。如果 FotMob 结构变了，xG 的路径变了但 home_team 没变——只有字段级的 field_path 才能检测这种差异。

### 6.4 data_version 的注意事项

DATA-L1A 发现 `raw_match_data` 存在 mixed provenance——不同的 data_version 的 payload 混在同一个 DB 表里，但解析出来的字段没有标记来自哪个 data_version。未来 parser 输出的每个字段都应该标记 data_version，方便追溯"这个字段值来自哪种 payload"。

---

## 7. timing label 设计

timing label 回答的问题是：**这个字段值在什么时候是可见的？**

### 7.1 必须包含的标签

| label | 用途 | 示例 | 风险说明 |
| --- | --- | --- | --- |
| `captured_at` | payload 的采集时间（来自 payload metadata） | `"2026-07-03T12:00:00Z"` | 不等于字段 observed_at |
| `observed_at` | 字段被观察到的时间。如果可以确定字段级时间，填字段级；如果不能确定，填 null | `null`（表示"无法确定字段级时间"） | null 不代表字段在 cutoff 前不存在，只是无法证明 |
| `match_kickoff_time` | 比赛开球时间 | `"2026-07-10T20:00:00Z"` | 用于判断 payload 抓取时比赛状态（赛前/赛中/赛后） |
| `match_status_at_capture` | 抓取 payload 时比赛处于什么状态 | `"pre_match"` / `"live"` / `"finished"` / `"unknown"` | 如果 payload 赛后抓的，里面混有比赛中/赛后字段 |
| `timing_class` | 字段时间分类标签（见 7.2） | `"fixture_metadata"` | 最关键的标签之一 |
| `timing_confidence` | 对 timing_class 的置信度 | `"high"` / `"medium"` / `"low"` / `"unknown"` | low 和 unknown 应该按保守策略处理 |
| `cutoff_relation` | 该字段相对于 prediction_cutoff_time 的关系（由 feature engine 在运行时计算，parser 不直接填） | `"before_cutoff"` / `"after_cutoff"` / `"unknown"` | parser 输出不带这个（它不知道 cutoff），但结构为 feature engine 预留 |

### 7.2 timing_class 分类定义

| timing_class | 含义 | 能否进入赛前模型 | 典型字段 | 使用条件 | 风险 |
| --- | --- | --- | --- | --- | --- |
| `fixture_metadata` | 赛程信息——赛前就确定的、不随时间变化的元数据 | ✅ 可以（if cutoff 合法） | league, season, round, kickoff_time, home_team, away_team, match_id | 需要确认不是赛后更新的（如延期后的 kickoff_time） | 一般安全，但 kickoff_time 在比赛延期时可能被修改 |
| `prematch_snapshot` | 赛前抓取的快照数据——采集时比赛尚未开始 | ✅ 可以（if captured_at ≤ cutoff） | opening_odds, venue（if known）, captain | captured_at 必须 ≤ cutoff | 快照不代表每个字段都是赛前字段——要确认 snapshot 内不包含 live/post 数据 |
| `near_kickoff_snapshot` | 接近开赛时才出现的数据 | ⚠️ 取决于 horizon | lineup, formation, squad, coach | T-1H / T-30min cutoff 可能安全；T-24H / T-7D 禁止 | 不同联赛 lineup 公布时间不同（通常开赛前 1 小时）；不同 prediction horizon 差异巨大 |
| `live_match` | 比赛进行中产生的实时数据 | **禁止** | possession, shots, live_score, 实时 odds 更新 | 无（禁止） | 被抓到时比赛正在进行中，数据不完整且赛后无法确定精确值 |
| `postmatch` | 比赛结束后才完全确定的指标 | **绝对禁止** | xG, xGOT, final_score, result, player_ratings, shotmap, events, match_stats, halftime_score | 无（绝对禁止） | 最危险的类别——直接泄露比赛结果；即使 captured_at 在 cutoff 前也不行（它们是另一场比赛的数据） |
| `unknown_timing` | 时间边界不清楚 | **默认禁止** | venue（if unknown）, referee（if unknown）, league_table（from FotMob snapshot）, team_form（from FotMob snapshot）, head_to_head（from FotMob snapshot） | 必须有 observed_at ≤ cutoff 且独立审计验证后方可开放 | 最常见的灰色区域——很多字段"看起来赛前但是不确定" |
| `derived_from_history` | 从 cutoff 前历史比赛数据自行计算得出 | ⚠️ 取决于输入比赛的时间范围 | table_from_history, form_from_history, h2h_from_history | 所有输入比赛必须早于 cutoff；必须可以追踪 max_source_match_time | 比直接用 FotMob 快照安全得多，但需要额外的"谁来计算"的职责分配 |
| `raw_only` | 原始 payload / 调试信息 / 中间产物 | **不允许进入模型** | pageProps、`__NEXT_DATA__`、HTML hydration、raw JSON、parser trace、debug logs | 无（禁止） | 同时包含赛前/赛后字段，整块喂模型 = 泄露 |

### 7.3 重要：captured_at ≠ observed_at

这是整个 DATA-L1 系列最核心的一个坑，必须反复强调：

```text
赛后抓取的 JSON 里 league 和 xG 同时存在。
captured_at 只告诉你 "这份 JSON 是赛后抓的"。
它不能告诉你 league 是不是赛后才知道的（显然不是），也不能告诉你 xG 是不是赛前就有的（显然不是）。

所以：
- league = fixture_metadata → safe_prematch_candidate（即使 captured_at 赛后，league 本身是赛程信息，与赛后无关）
- xG = postmatch → forbidden_postmatch（无论 captured_at 什么时候）
- captured_at 对 xG 的判断没有帮助——xG 永远是赛后字段，即使你在开赛前用神奇的方式拿到了它，也是"你拿到了未来的数据"。
```

---

## 8. model_eligibility 设计

model_eligibility 回答的问题是：**这个字段能不能用于赛前模型？** parser 给出初步判定，feature engine / training / backtest 执行最终 enforcement。

### 8.1 eligibility 分类

| model_eligibility | 含义 | 对应 DATA-L1B 分类 | 是否允许进入训练 | 说明 |
| --- | --- | --- | --- | --- |
| `allowed_candidate` | 明确安全，可以直接需要 cutoff 检查 | safe_prematch_candidate（with observed_at ≤ cutoff 或 fixture_metadata） | ✅ 如果 cutoff 检查通过 | 只有 league/season/kickoff 这类 fixture_metadata 才算 truly safe |
| `candidate_if_cutoff_valid` | 候选安全，但需要 cutoff 检查 + observed_at 存在 | safe_prematch_candidate（without observed_at guarantee） | ⚠️ 必须在 feature engine 过 cutoff_check | 大部分 safe_prematch_candidate 字段属于这一类 |
| `forbidden_postmatch` | 禁止——赛后数据 | unsafe_postmatch | ❌ | xG, shots, score, result, player_ratings, match_stats 等 |
| `forbidden_unknown_timing` | 禁止——时间不确定 | unknown_timing | ❌（除非后续 audit 升级） | 默认禁止；如果有 observed_at 证据可以升级为 candidate_if_cutoff_valid |
| `forbidden_raw_only` | 禁止——原始/调试数据 | debug_or_raw_only | ❌ | raw payload, pageProps, debug logs |
| `forbidden_metadata_only` | 禁止——metadata 不是特征 | metadata_only（when misused as feature） | ❌（作为特征时）；✅（作为 join/filter 元数据时） | match_id 不能做预测特征；league 可以是 feature + metadata 双重角色 |
| `forbidden_contract_violation` | 禁止——违反 DATA-L1B 合同 | 任何被 DATA-L1B 明确禁止后仍试图使用的字段 | ❌ | 预留标签——如果字段明明标记了 unsafe 但还是被试图喂给模型 |

### 8.2 谁说什么

| 角色 | 职责 |
| --- | --- |
| **parser** | 根据 DATA-L1B 字段合同 + payload metadata 给出字段级 model_eligibility。这是初步标签。 |
| **feature engine** | 根据 model_eligibility + prediction_cutoff_time + observed_at 做最终过滤。拒绝所有 forbidden_* 字段。对 candidate_if_cutoff_valid 字段做 cutoff 检查。 |
| **training / backtest** | 假设 feature engine 已经过滤完毕。但 backtest 应该独立再验证一次（特别是按 prediction horizon 分组时）。 |

### 8.3 parser 不应该做的事情

- parser 不知道 prediction_cutoff_time（那是 prediction task 层面的东西）。所以 parser 不应该给出 `allowed_after_cutoff_check` 之外的最终 allowed/forbidden 判定（除明确 forbidden_postmatch 类）。
- parser 不应该做 future prediction。
- parser 不应该假设"所有 safe_prematch_candidate 都安全"。它应该标记"候选安全"，最终由 feature engine 根据实际 cutoff 决定。

---

## 9. 与 DATA-L1B 字段合同的映射

| DATA-L1B classification | 建议的 parser timing_class | 建议的 parser model_eligibility | 处理方式 |
| --- | --- | --- | --- |
| `safe_prematch_candidate` | `fixture_metadata` 或 `prematch_snapshot` | `candidate_if_cutoff_valid` | feature engine 过 cutoff 检查 |
| `unsafe_postmatch` | `postmatch` | `forbidden_postmatch` | feature engine 直接拒绝 |
| `unknown_timing` | `unknown_timing` 或 `near_kickoff_snapshot` | `forbidden_unknown_timing` | 默认拒绝；后续有 observed_at 证据后才能升级 |
| `metadata_only` | `fixture_metadata` | `forbidden_metadata_only`（作为特征时）→ `candidate_if_cutoff_valid`（仅当同时是 safe_prematch_candidate 且使用合规时） | 用于 join/filter/audit/version selection，不作为预测特征 |
| `debug_or_raw_only` | `raw_only` | `forbidden_raw_only` | 只能用于 parser replay / debug / 审计 |

### 重要说明

- parser 解析出 `unsafe_postmatch` 字段不是错误。比如 FotMobRawParser 能解析 xG——这是它的能力，parser 层面不应该拒绝解析。**错误是后续把 xG 送进赛前模型。** parser 要做的是清晰地标记 `model_eligibility = forbidden_postmatch`，让 feature engine 能直接跳过。
- 如果未来 DATA-L1B 更新了字段合同（比如某个字段从 unknown_timing 升级为 safe_prematch_candidate），parser 需要更新它的分类映射。这就是 `parser_rules_version` 字段的作用。

---

## 10. cutoff safety flow 设计（未来数据流）

设计从 raw payload 到 feature 的完整 cutoff safety 流程。

### 10.1 流程图

```text
[1] raw payload (data/raw/fotmob/...)
      │
      ▼
[2] parser output with envelope
      ├── match_metadata (match_id, kickoff_time, ...)
      ├── payload_metadata (captured_at, payload_hash, ...)
      ├── parser_metadata (parser_name, version, ...)
      └── fields[]
           ├── field_contract_class
           ├── timing_class
           ├── model_eligibility
           └── observed_at / captured_at
      │
      ▼
[3] DATA-L1B field contract check
      │  拒绝 unsafe_postmatch / unknown_timing / debug_or_raw_only
      │  保留 safe_prematch_candidate
      │
      ▼
[4] cutoff safety check
      │  检查 feature_observed_at ≤ prediction_cutoff_time
      │  检查 captured_at ≤ prediction_cutoff_time
      │  如果 observed_at 缺失，用 captured_at 近似但有风险
      │  如果 captured_at 也缺失，拒绝
      │
      ▼
[5] feature eligibility filter
      │  只保留 model_eligibility = candidate_if_cutoff_valid AND cutoff 检查通过
      │  所有 forbidden_* 直接跳过
      │
      ▼
[6] training / backtest / prediction
      │  每个样本只包含 cutoff 前可用的字段
      │  每个样本都有 prediction_cutoff_time 作为参照
```

### 10.2 具体例子

同一份 raw payload（captured_at = 2026-07-10T18:00:00Z，赛后抓取），cutoff = T-1H（2026-07-10T19:00:00Z）：

| 字段 | raw 里有 | timing_class | captured_at ≤ cutoff? | 结论 |
| --- | --- | --- | --- | --- |
| home_team | ✅ | fixture_metadata | 18:00 ≤ 19:00 = ✅ | ✅ candidate_if_cutoff_valid → 可用 |
| opening_odds | ✅ | prematch_snapshot | 18:00 ≤ 19:00 = ✅ | ✅ candidate_if_cutoff_valid → 可用 |
| xG | ✅ | postmatch | 无关（绝对禁止） | ❌ forbidden_postmatch → 拒绝 |
| lineup | ✅ | near_kickoff_snapshot | 18:00 抓的不等于 lineup 在 18:00 公布 | ❌ forbidden_unknown_timing（除非有 lineup_timestamp ≤ 19:00） |
| score | ✅ | postmatch | 无关（绝对禁止） | ❌ forbidden_postmatch → 拒绝 |
| raw pageProps | ✅ | raw_only | 无关（禁止） | ❌ forbidden_raw_only → 拒绝 |

### 10.3 缺失 observed_at 时的默认策略

如果一个字段在 DATA-L1B 中是 safe_prematch_candidate，但没有 observed_at：

- 如果是 `fixture_metadata`：可以用 captured_at 近似（因为 fixture 本身不随时间变化）。保守策略：如果 captured_at > cutoff，也应该拒绝或标记为低置信度。
- 如果是 `prematch_snapshot`：用 captured_at 近似，前提是 confirmed captured_at ≤ cutoff。如果 captured_at > cutoff 或缺失，拒绝。
- 其他 timing_class：无法近似。拒绝。

### 10.4 多层防线设计

cutoff safety 不是一步检查就过了的。应该有多层防线：

1. **parser 层**：给字段打上 field_contract_class、timing_class、observed_at。这是第一道信息防线。
2. **feature engine 层**：拒绝所有 forbidden_*。过滤 candidate_if_cutoff_valid 中不满足 cutoff 的。这是第二道执行防线。
3. **backtest 层**：独立验证每个 feature 是否满足 cutoff。按 prediction horizon 分组检查。这是第三道验证防线。
4. **CI 层**：[未来] 可以增加 field-contract compliance check——parser 输出的每个字段必须在本合同中声明。

---

## 11. odds 字段特殊 label 设计

赔率是 DATA-L1B 中标为 `unknown_timing`（open_odds 除外）的高风险字段。parser 对 odds 的标签需要特别细致。

### 11.1 odds 必须拆成什么

笼统叫 "odds" 不够。未来 parser 输出 odds 时应该拆成：

| 字段 | 含义 | timing_class 建议 | model_eligibility 建议 |
| --- | --- | --- | --- |
| `opening_odds` | 博彩公司最早开出的赔率 | `prematch_snapshot` | `candidate_if_cutoff_valid`（需要 captured_at ≤ cutoff） |
| `current_odds` | 采集时刻的最新赔率 | `unknown_timing`→`prematch_snapshot`（如果 captured_at ≤ cutoff） | `candidate_if_cutoff_valid`（需要 captured_at ≤ cutoff + horizon 匹配） |
| `closing_odds` | 开赛前最后更新的赔率 | `unknown_timing`→`near_kickoff_snapshot`（如果 captured_at ≤ cutoff） | `candidate_if_cutoff_valid`（仅 T-1H cutoff；T-24H 视为 forbidden） |
| `odds_captured_at` | 这条赔率的采集时间 | `fixture_metadata` | 不作为特征（metadata_only） |
| `bookmaker` | 博彩公司名称 | `fixture_metadata` | 不作为特征（metadata_only） |
| `market` | 盘口类型（1X2 / Asian Handicap / OverUnder 等） | `fixture_metadata` | 不作为特征（metadata_only） |
| `return_rate` | 返水率 | `fixture_metadata` | 不作为特征（metadata_only） |
| `odds_type` | 赔率类型标记 | `fixture_metadata` | 不作为特征（metadata_only） |

### 11.2 odds 时间规则

| odds 类型 | 赛前模型能否用 | 条件 | parser 应给的 model_eligibility |
| --- | --- | --- | --- |
| 有 captured_at 的 opening_odds | ✅ | captured_at ≤ cutoff | `candidate_if_cutoff_valid` |
| 有 captured_at 的 current_odds | ⚠️ 取决于 horizon | captured_at ≤ cutoff + horizon 匹配 | `candidate_if_cutoff_valid` |
| closing_odds，T-1H cutoff | ⚠️ 可能 | captured_at ≤ cutoff | `candidate_if_cutoff_valid` |
| closing_odds，T-24H cutoff | ❌ | 终盘对早期预测是 future info | `forbidden_unknown_timing` |
| 无时间戳的 odds | ❌ | 无法判断 | `forbidden_unknown_timing` |
| 赛后补录 odds | ❌ | 即使有时间，它是 non-live 补的 | `forbidden_postmatch` |

---

## 12. lineup / injury / table / form 特殊 label 设计

这些字段在 DATA-L1B 中全部属于 `unknown_timing`。parser 对它们要做特殊处理。

### 12.1 lineup

- `timing_class = near_kickoff_snapshot`
- `model_eligibility = forbidden_unknown_timing`
- 额外需要：`lineup_timestamp`（如果 FotMob 提供了 lineup 确认时间）
- 如果 lineup 带有 `observed_at` 且能证明它在 cutoff 前存在，未来 audit 可以升级为 `candidate_if_cutoff_valid`

### 12.2 injury / suspension / unavailable_players

- `timing_class = unknown_timing`
- `model_eligibility = forbidden_unknown_timing`
- 额外需要：`source_timestamp`（伤病消息的来源时间）、`source_type`（官方确认 / 媒体传闻 / 博彩公司报告）

### 12.3 league_table / team_form / head_to_head（来自 FotMob 快照）

- `timing_class = unknown_timing`
- `model_eligibility = forbidden_unknown_timing`
- 风险：FotMob 快照里的 table/form 是当前快照状态，不一定代表 cutoff 时的状态
- 建议：**不用 FotMob 快照里的 table/form/h2h。** 改为从 cutoff 前历史比赛数据自行计算，标记为 `derived_from_history`

### 12.4 league_table / team_form / head_to_head（自行计算）

- `timing_class = derived_from_history`
- `model_eligibility = candidate_if_cutoff_valid`（需要 max_source_match_time ≤ cutoff）
- 额外需要：`derived_from_matches`（哪些比赛参与了计算）、`max_source_match_time`（这些比赛中最晚的结束时间）

---

## 13. unsafe_postmatch 字段处理设计

### 13.1 具体覆盖范围

以下字段都属于 `unsafe_postmatch`——parser 需要把它们全量标记为 `forbidden_postmatch`：

| 类别 | 具体字段 |
| --- | --- |
| 比分 | score, result, halftime_score, full_time_score, extra_time_score, penalty_score |
| xG | xG, xGOT, expected_goals, expected_goals_home, expected_goals_away, xG_by_minute, xG_accumulated |
| 射门 | shots, shots_on_target, shots_off_target, shots_blocked, shots_inside_box, shots_outside_box |
| 控球/传球 | possession, possession_by_minute, passes, pass_accuracy, pass_completion, long_balls, crosses |
| 对抗/角球/牌 | duels, aerial_duels, ground_duels, corners, corners_home, corners_away, yellow_cards, red_cards, fouls |
| 事件 | events, substitutions, goal_events, card_events, var_events |
| 射门图 | shotmap, shotmap_home, shotmap_away |
| 球员表现 | player_stats, player_ratings, player_rating_home, player_rating_away, man_of_the_match |
| 比赛统计 | match_stats, match_stats_home, match_stats_away, stats_block, info_box |

### 13.2 parser 应该做什么

- 继续解析这些字段。parser 的能力不因为标签制度而退化。
- 给每个字段打上 `field_contract_class = unsafe_postmatch`。
- 上 `timing_class = postmatch`。
- `model_eligibility = forbidden_postmatch`。
- 如果解析出来的字段不在上表中但在 FotMob "stats" 或 "shotmap" 或 "events" 或 "playerStats" 等模块中，默认假设为 `unsafe_postmatch`，除非 DATA-L1B 明确给了安全分类。

### 13.3 parser 不应该做什么

- 不应该隐藏或丢弃这些字段——它们对赛后分析、数据完整性审计、parser replay 有价值。
- 不应该试图 "translate" 这些字段到赛前上下文（比如用历史 xG 平均值代替当前场 xG——这是 feature engineering 的工作，不是 parser 的工作）。

---

## 14. raw payload / pageProps 处理设计

### 14.1 基本原则

raw payload / pageProps / `__NEXT_DATA__` / HTML hydration 属于 DATA-L1B 的 `debug_or_raw_only` 分类。

- parser 可以从中提取字段。
- raw 本身不能进入模型。
- 字段必须标注来自 raw 的哪个路径（field_path）。

### 14.2 与 DATA-L1C 的对接

parser output envelope 中 `payload` 部分的信息应该和 DATA-L1C 规定的 metadata 对齐。具体：

```text
DATA-L1C §5 必需字段:
  source, match_id, captured_at, payload_type, payload_hash, storage_path, is_replayable

envelope.payload 应该包含:
  source, payload_type, payload_hash, captured_at, source_url, final_url, data_version, capture_method
```

### 14.3 is_replayable 的判定

parser 尝试解析 raw payload 后应该能判断 is_replayable：

- ✅ 解析成功且字段完整 → `is_replayable = true`
- ⚠️ 解析部分成功但有些字段缺失 → `is_replayable = true`（with warnings）
- ❌ 解析完全失败（schema 不匹配、内容为空、损坏） → `is_replayable = false`

---

## 15. parser replay 与 regression 设计（只建议不实现）

### 15.1 未来可以检查什么

有了 provenance + timing labels 的 parser output，replay 可以检查：

1. **字段一致性**：同一 raw payload 用 old parser 和 new parser 解析，字段值是否一致？
2. **字段路径稳定性**：field_path 是否在 FotMob 结构变化后仍然有效？
3. **字段合同分类一致性**：field_contract_class 在 parser 升级后是否保持一致（不会把一个 safe_prematch 错误标记为 unknown_timing）？
4. **forbidden_postmatch 合规**：有没有不小心把 xG/score/shotmap 的 model_eligibility 从 forbidden 变成了 candidate？
5. **unknown_timing 不放行**：有没有 unknown_timing 字段被默默升级为 safe_prematch（没有审计支撑）？
6. **schema drift 影响范围**：FotMob 结构变了后，哪些字段的 field_path 失效了？

### 15.2 本 PR 不做什么

- 不创建 replay runner。
- 不新增测试。
- 不运行 parser。
- 不修改 parser 代码。
- 只定义 replay/regression 的设计需求。

---

## 16. 后续代码实现建议（不实现）

以下只写建议方向，不写任何代码。本 PR 是一份设计文档。

1. **DATA-L1E 或 DATA-L1D-code（未来）**：实现 parser output envelope。选择 FotMobRawParser 或重构 parsers 以生产带有 provenance + timing + contract + eligibility 标签的输出。

2. **DATA-L1F（未来）**：实现 field contract checker——一个独立模块，读 DATA-L1B 合同 + parser output，验证字段分类是否正确、是否有未在合同中登记的字段。

3. **DATA-L1G（未来）**：实现 feature eligibility filter——feature engine 层读取 parser output 中的 model_eligibility 和 timing_class，拒绝所有 forbidden_* 字段，对 candidate_if_cutoff_valid 做 cutoff 交叉检查。

4. **DATA-L1H（未来）**：实现 replay fixture runner——用 critical 等级的 raw payload 和对应的 parser version，验证 parser 输出字段是否稳定。

5. **DATA-L1I（未来）**：实现 training/backtest cutoff safety check——在训练和回测 pipeline 中独立执行 cutoff check，确保没有 postmatch / unknown_timing / raw_only 字段被使用。

**重要**：以上所有建议需要单独授权、单独 PR。**本 PR 不实现这些。**

---

## 17. 风险与开放问题

本设计文档定义的 label 体系是正确的方向，但在实际实施前存在以下已知风险和开放问题：

1. **现有 parser 是否已有部分 provenance 信息**：FotMobRawParser 当前输出结构（match/team/stats/lineup/events/shotmap/playerStats）中没有 field-level label。但 `_meta` 块可能有 captured_at、hash 等信息。本次未改代码，不能确认运行时真实行为。未来实施时需要以当前 parser 实际输出为准。

2. **observed_at 可能很难做到字段级**：不同字段在同一 payload 中可见的时间可能不同。目前大多数情况下缺乏字段级 timestamp。如果 observed_at 缺失，只能用 captured_at 近似——这不完美，但有 metadata 总比没有好。

3. **captured_at 与 observed_at 容易混淆**：这是整个 DATA-L1 系列最核心的坑。实施时必须明确区分两个概念。

4. **odds 时间戳来源可能不完整**：FotMob odds 不一定每条都有 captured_at。opening/current/closing 的区分可能依赖外部数据源。

5. **lineup / injury / table / form 的时间边界需要后续审计**：DATA-L1B 中的 unknown_timing 分类需要独立的 timing audit 来证明或升级。

6. **field_path 可能随 FotMob schema drift 改变**：FotMob 结构升级后，field_path 可能失效。需要 schema drift 检测工具及早发现。

7. **未来实施时需要防止把 metadata 或 raw 字段误当特征**：field_contract_class 是 metadata_only 的字段（如 match_id、data_version）如果被 feature engine 错误地 one-hot/embedding 并作为特征，是另一种泄露——不是时间泄露，是结构泄露。

8. **标签体系增加了 parser 复杂性**：parser 从"纯提取值"变为"提取值 + 打标签"。这会增加 parser 的代码量和维护成本。但和"没有标签导致模型泄露"的成本相比，这是值得的。

---

## 18. 与 DATA-L1A / DATA-L1B / DATA-L1C 的关系

```text
DATA-L1A (审计报告)     = 体检报告——查出风险
DATA-L1B (字段合同)     = 饮食禁忌表——规定什么能吃、什么不能吃、什么不确定
DATA-L1C (raw 保留策略) = 食材进货小票和监控录像保存制度——原始证据怎么保留
DATA-L1D (本设计)       = 每道菜上桌前贴标签——来自哪、什么时候进货、能不能给病人吃
```

具体关系表：

| 维度 | DATA-L1A | DATA-L1B | DATA-L1C | DATA-L1D（本合同） |
| --- | --- | --- | --- | --- |
| 类型 | 审计报告 | 字段合同 | 保留与回放策略 | parser 标签设计 |
| 产物 | `docs/_reports/data_l1a_...` | `docs/data/fotmob_prematch_field_contract.md` | `docs/data/fotmob_raw_payload_retention_replay_policy.md` | `docs/data/fotmob_parser_field_provenance_timing_labels_design.md` |
| 是否替代对方 | 不替代 | 不替代 | 不替代 | 不替代 |
| 被哪些后续工作引用 | FotMob 改造的起点 | parser/feature/training/backtest 的字段规则 | parser replay / schema drift / retention adapter / cutoff audit | 未来 parser output envelope / feature filter / training cutoff check 的实现 |
| 修改条件 | 发现新风险或风险过时 | 字段分类错误或新字段 | raw payload 生命周期调整 | 标签体系需要根据实施反馈调整 |

---

## 19. 本次明确不做事项

本 PR（DATA-L1D）只创建这一份 parser 字段来源与时间标签设计文档。以下全部不做：

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
- 没有启动 DATA-L1E
- 没有启动 DATA-L2
- 没有启动 CLEANUP-L1A
- 没有启动 L3I
- 没有启动 L4
- 没有做 legacy 删除 / 移动 / 重命名

---

## 20. 下一步建议

Do not start automatically.

Recommended next task only after user confirmation:

- **DATA-L1E: FotMob Parser Output Envelope Implementation Plan**
  - 目标：基于 DATA-L1D 的标签设计，规划 parser output envelope 的具体实现步骤。
  - 开始涉及 src/parsers/** 的改造设计和影响分析（但不是代码实现）。
  - 仍然首选 docs-only：写实施计划，不改代码。

如果用户认为 DATA-L1 系列文档已经足够，也可以选择：

- **CLEANUP-L1A: Repository File Usage Audit**
  - 目标：审计仓库中旧 FotMob 相关脚本/测试/文档的使用状态。

但以上建议只供参考，不应自动启动。DATA-L1D 合并后具体做什么，由用户决定。
