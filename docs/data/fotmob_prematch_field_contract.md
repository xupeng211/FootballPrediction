# FotMob Prematch Field Contract

- lifecycle: source-of-truth
- scope: docs-only, FotMob 字段使用规则合同
- parent audit: DATA-L1A（`docs/_reports/data_l1a_fotmob_prematch_boundary_audit.md`）
- branch: `docs/data-l1b-fotmob-prematch-field-contract`

---

## 1. 背景

DATA-L1A 已经完成并合并（PR #1694）。DATA-L1A 在仓库里做了只读审计，发现 FotMob 数据里有很多字段看起来有价值，但存在严重的赛前/赛后时间边界风险。

举个例子：一场比赛还没踢，FotMob 的快照里不会有 xG、不会有 shotmap、不会有实时比分。但如果你赛后抓了一份 JSON，里面同时包含了赛前的 league/season/round 和赛后的 xG/shots/score，直接把整份 JSON 喂给模型，模型就作弊了——它在预测历史比赛时，"提前"看到了比赛结果。

DATA-L1B 的目标就是把这件事说清楚：**哪些字段能吃、哪些不能吃、哪些不确定先别吃、哪些只能做记录、哪些只能调试用**。

这份文档是**字段合同**，不是 scraper 改造，不是 parser 改造，不是 feature 改造，不是 DB/migration 改造，不是 training。本合同不运行任何采集，不证明任何字段已经被代码强制拦截。它只负责立规则。

未来 parser、feature engine、training pipeline、backtest 都应该遵守这份合同。如果合同和代码不一致，以合同为准，直到合同被正式更新。

---

## 2. 核心原则

这些原则是本合同的基础，优先级高于具体字段分类：

1. **赛前模型只能使用 `prediction_cutoff_time` 之前可证明存在的数据。** 什么叫"可证明存在"？意思是这个字段有一个可信的时间戳，且时间戳早于或等于 cutoff time。

2. **字段"看起来像赛前字段"不等于它真的安全。** league、season 这种字段赛前肯定存在，但 venue、referee 可能到临场才公布。不能因为字段名字像赛前信息就默认它安全。

3. **时间边界不清楚的字段，默认归入 `unknown_timing`，禁止进入模型。** 这是一种保守策略：不确定就禁用，等有证据再开放。不急。

4. **current-match post-match stats 默认禁止用于赛前预测。** xG、shots、possession、events、shotmap、player match stats、score、result 这些是一场比赛进行中或结束后才产生的数据，用了就是泄露。

5. **xG、shots、possession、events、shotmap、player match stats、score、result 等默认是赛后或高度危险字段。** 哪怕 parser 能解析这些字段，也不代表它们可以用在赛前模型里。

6. **odds 必须有明确时间戳和 odds type，不能混用初盘、临场盘、终盘、赛后记录。** 笼统叫"赔率"不够。必须拆成 opening/current/closing，并且每条都有 captured_at。

7. **lineup / injury / suspension / table / form 只有在 `observed_at <= prediction_cutoff_time` 且来源可信时，才可能进入 `safe_prematch`。** 这条默认不通，除非有人专门证明了时间。

8. **raw payload / pageProps / debug trace 只能用于排查和回放，不能直接进入模型。** raw JSON 里混了赛前和赛后字段，直接喂模型等于开卷考试。

9. **metadata 可以用于 join、去重、审计、版本选择，但不能默认作为预测特征。** match_id 不能帮你预测比分，但能帮你找到正确的比赛。

10. **未来代码实现必须优先遵守本合同。** 如果代码和合同冲突，修代码，不是修合同——除非合同本身被发现错误且经过正式更新。

---

## 3. 字段分类定义

本合同把 FotMob 相关字段分成 5 类。每类有明确的含义、使用条件和风险说明。

### 3.1 `safe_prematch_candidate` — 赛前候选安全

**含义**：字段在赛前就应该存在，且时间来源可证明早于 `prediction_cutoff_time`。

**能否进入赛前模型**：可以，但必须满足使用条件。

**需要满足什么条件**：
- 字段有明确的时间戳（如 `observed_at`、`captured_at`、快照时间）或字段本身不随时间变化（如 match_id、league 名称）。
- 时间戳 ≤ `prediction_cutoff_time`。
- 对于有时效性的字段（如 lineup、form），必须证明在 cutoff 时已经可用。

**典型例子**：
- `league` / `season` / `round`（赛程确定后就固定了）
- `kickoff_time` / `matchTimeUTC`（赛程确定的开球时间）
- `home_team` / `away_team`（参赛队伍身份）
- opening odds（如果 captured_at ≤ cutoff）

**风险说明**：
- "候选安全" ≠ "代码已强制安全"。目前 parser 没有输出 timing label，feature engine 没有 cutoff 检查。这些是未来代码实现的工作。
- 有些字段在"赛前"存在，但"多早之前"不确定。如果 prediction horizon 是 T-7D，有些字段（如临近的 lineup）可能还不存在。

### 3.2 `unsafe_postmatch` — 赛后字段，禁止

**含义**：字段是一场比赛进行中或结束后才产生的数据。

**能否进入赛前模型**：**绝对禁止。** 不管什么 horizon，不管什么 cutoff，这些字段都不能用于赛前预测。

**需要满足什么条件**：没有条件。这类字段**不能**进入赛前模型，不需要"满足条件"来开放。

**典型例子**：
- `score` / `result` / `halftime_score`（比赛结果）
- `xG` / `expected_goals`（赛后或实时统计）
- `shots` / `shots_on_target` / `possession` / `passes` / `duels` / `corners` / `cards`（比赛技术统计）
- `events` / `shotmap`（比赛事件和射门分布）
- `player_stats` / `player_ratings` / `match_stats`（球员比赛表现）
- 赛后 `status.finished` / `status.reason` 等结果状态

**风险说明**：
- 这是泄露最严重的一类。xG 和 score 跟比赛结果高度相关，用了模型会虚高。
- 有些字段（如 possession）看起来"无害弱特征"，但它们仍然是赛后才知道的。不能因为"效果可能不大"就放松。

### 3.3 `unknown_timing` — 时间边界不清楚，默认禁用

**含义**：字段可能在赛前存在，但没有可信的时间戳证明它在 cutoff 之前可用。

**能否进入赛前模型**：**默认禁止。** 只有在后续任务中提供了 cutoff 前可用的时间证据后，才可能提升到 `safe_prematch_candidate`。

**需要满足什么条件**：
- 必须有 `observed_at` 或等效时间戳。
- `observed_at` ≤ `prediction_cutoff_time`。
- 必须通过独立的字段 timing audit 验证。

**典型例子**：
- `lineup` / `formation` / `squad` / `coach`（赛前 1 小时才公布首发）
- `injury` / `suspension` / `unavailable_players`（可能有赛前消息，但来源时间和准确性不确定）
- `league_table` / `team_form` / `head_to_head`（如果从 FotMob 快照直接取，没有 snapshot 时间）
- `venue` / `referee`（可能赛前公布，但时间不确定）
- current odds / closing odds（除非 captured_at ≤ cutoff 且 horizon 允许）
- 没有时间戳的 odds 记录

**风险说明**：
- 这是最常见的"看起来赛前可以用，但实际上不确定"的区域。
- lineup 接近开赛才出现，T-24H 预测不能用。
- FotMob 快照里的 table/form 是当前快照，不代表 cutoff 时的状态。

### 3.4 `metadata_only` — 只做元数据，不做特征

**含义**：字段可以用于 join、去重、审计、版本选择、cutoff 校验，但不能直接作为预测特征。

**能否进入赛前模型**：不能作为预测特征。可以用于数据管线中的 join key、去重 key、版本选择、时间校验。

**需要满足什么条件**：
- 用于 join/去重：字段值必须稳定（同一实体不变）。
- 用于 cutoff 校验：必须有时间戳。

**典型例子**：
- `match_id` / `external_id`（join key）
- `source` / `data_version`（版本选择）
- `captured_at`（时序审计）
- `prediction_cutoff_time`（安全判断）
- `feature_observed_at`（安全判断）
- `league` / `season` / `round`（同时也可能是 safe_prematch_candidate——取决于怎么用）

**风险说明**：
- metadata 本身不会泄露结果信息，但如果你不小心把 "data_version=postmatch" 当成特征，那就是间接泄露。
- 不要在 metadata 字段上做 one-hot 或者 embedding 然后把它们当预测信号。

### 3.5 `debug_or_raw_only` — 只能调试/回放，不进模型

**含义**：字段是原始数据采集/传输/解析过程的中间产物，只能用于 parser 调试、schema drift 检测、数据完整性审计、replay。不能进入模型。

**能否进入赛前模型**：**不允许。**

**需要满足什么条件**：没有条件。这类字段永远不进模型。

**典型例子**：
- `pageProps`（Next.js SSR 原始 props）
- `raw JSON` / `raw_match_data` / `raw_data`（完整原始 payload）
- `HTML hydration`（HTML 中的水合数据）
- `__NEXT_DATA__`（Next.js 内联数据）
- `parser trace` / `debug logs`
- `_meta` / `hash` / `request URL` / `final URL` / `body size`（采集元信息）

**风险说明**：
- raw payload 里同时包含赛前和赛后字段。把它整个喂给模型，等于把所有字段都开放了。
- 未来 parser 可以从 raw payload 里提取 safe_prematch 字段出来用，但 raw payload 本身不能进模型。

---

## 4. 字段合同总表

下表按字段或字段类别列出合同分类、使用条件、依据。分类采用最保守判断：不确定就标 `unknown_timing`。

| 字段 / 字段类别 | 合同分类 | 是否允许进入赛前模型 | 使用条件 | 为什么这样分类 | 证据 / 依据 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| `match_id` / `external_id` | `metadata_only` | 不作为预测特征 | 值稳定，用于 join/去重 | 不会泄露比赛结果，但没有预测能力 | DATA-L1A §5 | 不同 data_version 可能有不同 id 格式，join 时注意 |
| `source` / `data_version` | `metadata_only` | 不作为预测特征 | 用于版本选择 | 表示数据来源，不表示比赛结果 | DATA-L1A §3, §6 | `raw_match_data` mixed provenance 下非常重要 |
| `captured_at` | `metadata_only` | 不作为预测特征 | 可用于时序审计 | 采集时间不等于 feature 可用时间 | DATA-L1A §6 | 赛后抓取的 JSON 可能同时包含赛前和赛后字段 |
| `prediction_cutoff_time` | `metadata_only` | 必须参与安全判断 | 所有 feature 都要和它比 | 这是赛前/赛后的分界线 | DATA-L1A §6, formal training design | 必须存在，否则无法判断泄露 |
| `feature_observed_at` | `metadata_only` | 必须参与安全判断 | 每个 feature 都要有 | 证明这个 feature 在 cutoff 前已经存在 | DATA-L1A §6 | 目前 parser 没有输出这个字段 |
| `league` / `season` / `round` | `safe_prematch_candidate` + `metadata_only` | 可以作为特征 | 确认来源时间 | 赛程确定后基本不变；同时也用于数据集筛选 | DATA-L1A §5 | 双重角色：既做特征又做 filter |
| `kickoff_time` / `matchTimeUTC` | `safe_prematch_candidate` + `metadata_only` | 可以作为特征，也是 cutoff 计算基础 | 确认是赛程原始时间 | 赛程确定的开球时间，赛前已知 | DATA-L1A §5 | 如果比赛延期/改期，需要确认这个值是否更新 |
| `home_team` / `away_team` | `safe_prematch_candidate` + `metadata_only` | 可以作为特征（队名/ID） | 确认 team identity 已 normalization | 参赛队伍赛前确定 | DATA-L1A §5 | 队名 join 有 identity risk，需要 normalized team id |
| `team_identity` / `normalized_team_id` | `safe_prematch_candidate` + `metadata_only` | 可以作为特征 | 在 team identity normalization 之后 | 身份不随时间变化 | DATA-L1A §5 | 需要跨 league/season 的 team id mapping |
| `venue` | `unknown_timing` | 默认禁止 | 需要 observed_at ≤ cutoff | 场地可能赛前公布但时间不确定；不直接泄露结果 | DATA-L1A §5 | formal training 设计中列为可选直接字段，但当前缺失来源时间 |
| `referee` | `unknown_timing` | 默认禁止 | 需要 observed_at ≤ cutoff | 裁判可能赛前公布但时间不确定 | DATA-L1A §5 | 对预测价值有限 |
| `lineup` | `unknown_timing` | 默认禁止 | 需要 lineup_timestamp ≤ cutoff | 通常开赛前 1 小时才公布；T-24H 不能用 | DATA-L1A §5 | 不同联赛公布时间不同 |
| `formation` | `unknown_timing` | 默认禁止 | 需要 observed_at ≤ cutoff | 随 lineup 一起公布 | DATA-L1A §5 | |
| `coach` | `unknown_timing` | 默认禁止 | 需要 observed_at ≤ cutoff | 教练信息可能赛前可用，但不确定 | DATA-L1A §5 | |
| `squad` | `unknown_timing` | 默认禁止 | 需要 squad_timestamp ≤ cutoff | 大名单可能赛前公布，但时间和准确性不确定 | DATA-L1A §5 | |
| `injury` | `unknown_timing` | 默认禁止 | 需要来源时间戳 + 来源可信 | 可能有赛前消息，但 FotMob 数据不确定 | DATA-L1A §5 | 伤病消息来源复杂 |
| `suspension` | `unknown_timing` | 默认禁止 | 需要来源时间戳 | 停赛信息通常赛前已知，但需要确认 | DATA-L1A §5 | |
| `unavailable_players` | `unknown_timing` | 默认禁止 | 需要来源时间戳 | 汇总信息，包含伤停等多种原因 | DATA-L1A §5 | |
| `league_table` | `unknown_timing` | 默认禁止 | 只有从 cutoff 前历史比赛派生才安全；table_snapshot_at ≤ cutoff | FotMob 快照里的 table 是当前状态，不代表 cutoff 时的状态 | DATA-L1A §5 | 建议由历史比赛数据自行计算，不用 FotMob 快照 |
| `team_form` | `unknown_timing` | 默认禁止 | 只有从 cutoff 前历史比赛派生才安全 | FotMob payload 快照时间未证明 | DATA-L1A §5 | 建议由历史比赛数据自行计算 |
| `head_to_head` | `unknown_timing` | 默认禁止 | 必须过滤未来/当前比赛，且确认 snapshot 时间 | 可能包含当前对阵的历史版本 | DATA-L1A §5 | 同上，建议自行计算 |
| `odds`（笼统） | `unknown_timing` | 默认禁止 | 必须拆成 opening/current/closing + captured_at | 笼统叫 odds 无法判断时间 | DATA-L1A §5, §6 | 不同公司的 odds 结构不同 |
| `opening_odds` | `safe_prematch_candidate` | 可以（if captured_at ≤ cutoff） | captured_at ≤ prediction_cutoff_time | 初盘在赛前很早就存在 | DATA-L1A §5 | 需要确认 bookmaker、market、return rate |
| `current_odds` | `unknown_timing` | 默认禁止 | captured_at ≤ cutoff 且 horizon 适合 | "当前"赔率的时间点不确定 | DATA-L1A §5 | 要区分"采集时的当前"和"cutoff 时的当前" |
| `closing_odds` | `unknown_timing`（默认）/ 部分 `unsafe_postmatch` | 默认禁止 | 如果 T-1H cutoff 且 captured_at ≤ cutoff，可能可以用；T-24H 不能用 | 终盘接近开赛，对早期预测是未来信息 | DATA-L1A §5, §6 | 非常危险，需要明确的 horizon 策略 |
| `odds_captured_at` | `metadata_only` | 不作为预测特征，但必须参与 odds 判断 | 每条 odds 记录都要有 | 这是 odds 安全判断的关键时间戳 | DATA-L1A §6 | |
| `score` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛结果，最直接的泄露 | DATA-L1A §5 | 包括 full_time、half_time、extra_time 等所有 score |
| `result` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛结果（W/D/L） | DATA-L1A §5 | |
| `halftime_score` | `unsafe_postmatch` | **绝对禁止** | 无 | 半场比分也是赛后信息 | DATA-L1A §5 | |
| `xG` / `expected_goals` | `unsafe_postmatch` | **绝对禁止** | 无 | 赛后/实时统计，与比赛结果高度相关 | DATA-L1A §5, §6; XGExtractor.js | 包括 xG、xGOT、xG 累计等所有 xG 变体 |
| `shots` / `shots_on_target` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛技术统计 | DATA-L1A §5 | |
| `possession` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛技术统计 | DATA-L1A §5 | possession 看起来无害，但它仍然是赛后信息 |
| `passes` / `pass_accuracy` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛技术统计 | DATA-L1A §5 | |
| `duels` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛技术统计 | DATA-L1A §5 | |
| `corners` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛技术统计 | DATA-L1A §5 | |
| `cards` / `yellow_cards` / `red_cards` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛事件 | DATA-L1A §5 | |
| `events` | `unsafe_postmatch` | **绝对禁止** | 无 | 比赛事件流（进球、换人、红黄牌等） | DATA-L1A §5 | FotMobRawParser 能解析 events，但不能用于赛前 |
| `shotmap` | `unsafe_postmatch` | **绝对禁止** | 无 | 射门位置图，赛后/实时数据 | DATA-L1A §5, §6 | pageProps v2 泄露边界报告确认 |
| `player_stats` | `unsafe_postmatch` | **绝对禁止** | 无 | 球员本场比赛的技术统计 | DATA-L1A §5 | FotMobRawParser 输出 playerStats |
| `player_ratings` | `unsafe_postmatch` | **绝对禁止** | 无 | 球员赛后评分 | DATA-L1A §5 | |
| `match_stats`（笼统） | `unsafe_postmatch` | **绝对禁止** | 无 | 本场比赛的各项技术统计 | DATA-L1A §5 | FotMob "stats" 模块 |
| `pageProps` | `debug_or_raw_only` | **不允许** | 只能用于 parser 回放、schema drift 检测 | 完整 Next.js SSR props，混有赛前赛后字段 | DATA-L1A §3, §5 | pageProps v2 已有模块级分类（metadata/conditional/live/post-match） |
| `raw JSON` / `raw_match_data` / `raw_data` | `debug_or_raw_only` | **不允许** | 只能用于审计、replay、完整性检查 | 完整原始 payload，混合 provenance | DATA-L1A §3, §5, §6 | raw retention 已有 policy，不等于 DB write 授权 |
| `HTML hydration` | `debug_or_raw_only` | **不允许** | 只能用于 parser 调试 | HTML 中的水合数据，完整 payload | DATA-L1A §3 | FotMobRawDetailFetcher 构建 |
| `__NEXT_DATA__` | `debug_or_raw_only` | **不允许** | 只能用于 parser 调试 | Next.js 内联数据 | DATA-L1A §3 | NextDataParser 转换用 |
| `parser_trace` / `debug_logs` | `debug_or_raw_only` | **不允许** | 只能用于调试 | 解析过程的中间产物 | DATA-L1A §5 | |
| `_meta` / `hash` / `request_url` / `final_url` / `body_size` | `debug_or_raw_only` | **不允许** | 只能用于审计、hash gate、source fidelity | 采集元信息 | DATA-L1A §5 | |

### 重要备注

- 上表不是最终版。如果未来发现新字段，应加到表中。如果未来发现分类错误，应更新本合同。
- **"safe_prematch_candidate" 只是候选安全**，不等于代码已强制安全。目前 `FotMobRawParser` 没有输出每个字段的 timing label。
- **`unknown_timing` 不等于永远禁用。** 如果后续 audit 证明了字段的 cutoff 前可用性，可以提升为 `safe_prematch_candidate`。
- **`metadata_only` 字段可能同时有特征价值。** 比如 league 既是 metadata（筛选数据集），也是特征（不同联赛风格不同）。这种情况下标记为双重角色。

---

## 5. 模型使用规则

### 5.1 总规则

| 分类 | 训练模型 | 回测 | 线上预测 | parser 输出 | feature 生成 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `safe_prematch_candidate` | 允许（if observed_at ≤ cutoff） | 允许（if observed_at ≤ cutoff） | 允许（if observed_at ≤ cutoff） | 允许输出 | 允许生成 | 所有使用都要过 cutoff 检查 |
| `unsafe_postmatch` | **禁止** | **禁止** | **禁止** | 可以解析但不输出到 feature | **禁止** | parser 可以保留解析能力用于调试，但不能进 feature |
| `unknown_timing` | **默认禁止** | **默认禁止** | **默认禁止** | 允许输出（带 timing=unknown 标签） | **禁止** | 等证据充足后才能开放 |
| `metadata_only` | 不作为特征，可用于管线 | 不作为特征，可用于管线 | 不作为特征，可用于管线 | 允许输出 | 可用于 join/filter，不作为预测特征 | 不要 one-hot/embedding 当信号 |
| `debug_or_raw_only` | **不允许** | **不允许** | **不允许** | 可用于调试 | **不允许** | 永远不进模型 |

### 5.2 默认允许和默认禁止

**默认允许进入模型的只有**：`safe_prematch_candidate` 且满足 `observed_at ≤ prediction_cutoff_time` 的字段。

**默认禁止**：其他所有字段，包括所有 `unsafe_postmatch`、`unknown_timing`、`debug_or_raw_only` 以及没有 `observed_at` 的 `metadata_only`（用作特征时）。

**metadata_only 特例**：metadata 字段只允许用于 join、dedupe、audit、version selection、cutoff validation。不默认作为预测特征。如果你把 match_id 做 one-hot 当特征，那不是 metadata 的预期用法。

---

## 6. 回测使用规则

回测是验证模型历史表现的关键步骤，也是泄露最容易发生的地方。

### 必须满足的条件

1. **回测必须模拟真实赛前状态。** 对于历史上的每场比赛，模型只能看到 cutoff 之前存在的数据。

2. **每个 feature 必须有 `feature_observed_at`。** 没有这个字段，就无法判断 feature 是否在 cutoff 前存在。

3. **每场比赛必须有 `prediction_cutoff_time`。** 这是判断的基准线。

4. **如果 `feature_observed_at` 晚于 `prediction_cutoff_time`，该 feature 对此场比赛禁用。** 即使这个 feature 在分类上是 `safe_prematch_candidate`。

5. **如果字段没有 `observed_at`，默认禁用，除非属于稳定 metadata。** league、season 这种不随时间变化的 metadata 可以不要求 observed_at。

6. **不能用赛后 xG、shots、score、events、player ratings 来提升历史回测。** 这会让回测结果虚高，上线后必然跳水。

7. **chronological split 优先于 random split。** 训练集的所有比赛必须早于验证集和测试集，避免时间穿越。

8. **按 prediction horizon 分组评估。** T-24H 的模型和 T-1H 的模型能用的字段不同（比如 T-24H 不能用 lineup），不要混在一起回测。

---

## 7. odds 字段特殊规则

赔率是最重要的外部特征之一，也是最容易用错的特征。

### 7.1 不能笼统叫"odds"

"赔率"这个词太模糊了。同一场比赛，不同时间、不同博彩公司、不同盘口、不同返水率的赔率都不同。必须至少区分：

- **opening odds**（初盘）：博彩公司最早开出的赔率
- **current odds**（当前赔率）：采集时刻的最新赔率
- **closing odds**（终盘）：开赛前最后更新的赔率
- **captured_at**：这条赔率是什么时候抓到的
- **bookmaker**：哪家博彩公司
- **market**：什么盘口（1X2、亚盘、大小球等）
- **return rate**：返水率

### 7.2 时间规则

| odds 类型 | 赛前模型能否用 | 条件 |
| --- | --- | --- |
| opening odds | 可以 | `captured_at ≤ prediction_cutoff_time` |
| current odds | 不确定，默认禁止 | `captured_at ≤ prediction_cutoff_time` + horizon 匹配 |
| closing odds | 不确定，默认禁止 | 仅当 T-1H cutoff 且 `captured_at ≤ cutoff` 时可能允许；T-24H 禁止 |
| 没有时间戳的 odds | 禁止 | 无法判断时间，默认 `unknown_timing` |

### 7.3 重要警告

- **closing odds ≠ 对所有 horizon 都安全。** 如果预测目标是 T-24H（赛前 24 小时预测），终盘是未来信息——24 小时前你拿不到终盘。
- **赛后补录的赔率不能用于赛前回测。** 有些平台会在比赛结束后调整赔率记录，这种数据是绝对的事后信息。
- **odds 的时间戳是 `captured_at`，不是 `match_time - N hours` 的推算。** 不要用"比赛时间减去采集时间"来反推 horizon，应该用采集时间的绝对值。
- **不同博彩公司的 odds 不能混用。** 初盘用 Bet365 的、终盘用 Pinnacle 的，拼出一个"最佳赔率"，这在时间是上作弊。

### 7.4 当前代码线索

- `scripts/ops/odds_harvest_pipeline.shared.js` 有 open/current/close snapshot 能力
- `scripts/model_training/train_baseline_v1.py` 使用 open/current/close odds 字段
- 这些代码**没有**实施本合同的时间规则。未来 training 改造时必须加上。

---

## 8. lineup / injury / table / form 特殊规则

这些字段的特点是：它们可能是赛前信息，但"多早之前"非常不确定。

### 8.1 lineup（首发阵容）

- lineup 通常在开赛前约 1 小时公布。
- 对于 T-24H prediction horizon，lineup 是 **未来信息**，不能用。
- 对于 T-1H prediction horizon，如果有 `lineup_timestamp ≤ cutoff` 证明，可以放宽。
- 不同联赛、不同比赛的 lineup 公布时间不一样，不能一刀切。

### 8.2 injury / suspension（伤病/停赛）

- 伤病消息可能在赛前数天就出现，但也可能临场才确认。
- FotMob 的 injury 数据来源和更新时间不确定。
- 如果没有明确的来源时间戳，默认 `unknown_timing`。

### 8.3 league table / team form（积分榜/近期状态）

- 理想做法：用 cutoff 之前已完赛的历史比赛数据自行计算积分榜和近期状态。
- 危险做法：直接从 FotMob 快照里取 table/form 当特征——快照可能包含了本场比赛之后的数据（如果你赛后抓的）。
- 如果 table/form 带有 `snapshot_at` 时间戳，且 ≤ cutoff，可以考虑开放。否则默认 `unknown_timing`。

### 8.4 head-to-head（历史交锋）

- 必须排除当前对阵的历史版本（比如本赛季首回合如果还没踢，就不能用它）。
- 必须有 snapshot 时间戳。
- 建议自行计算，比依赖 FotMob 快照更可控。

---

## 9. raw payload / pageProps 使用规则

### 9.1 raw payload 是什么

FotMob 采集回来的原始数据有多种形态：
- `raw JSON`（API 返回的完整 JSON）
- `pageProps`（Next.js SSR 页面的 props 对象）
- `HTML hydration`（HTML 中的内联数据）
- `__NEXT_DATA__`（Next.js 内联的序列化数据）

这些原始数据**同时包含赛前和赛后字段**。

### 9.2 raw payload 可以做什么

1. **parser 回放**：用保存的 raw payload 重新跑 parser，验证解析结果不变。
2. **schema drift 检测**：对比不同时间采集的 raw payload，发现 FotMob API 的结构变化。
3. **字段来源审计**：追溯某个特征值的原始来源。
4. **数据完整性审计**：检查 raw payload 是否完整、是否有截断。

### 9.3 raw payload 不能做什么

1. **不能直接作为模型特征。** raw payload 里混了 safe/unsafe/unknown 字段，整块喂给模型等于把所有禁用的字段都开放了。
2. **不能在未经字段合同过滤的情况下进入 feature pipeline。**
3. **不能直接写入 DB 用于训练/回测。**

### 9.4 从 raw 到 feature 的正确路径

```text
raw payload (debug_or_raw_only)
    ↓
parser（按本合同分类提取字段）
    ↓
feature engine（拒绝 unsafe/unknown，保留 safe_prematch）
    ↓
training / backtest（过 cutoff 检查）
```

每一步都必须遵守本合同。parser 可以解析所有字段（包括赛后字段）用于调试，但 feature engine 必须过滤。

---

## 10. 后续代码实现建议（不实现）

以下只是建议，不是本 PR 的工作。本 PR 不实现任何代码。

1. **DATA-L1D（未来）**：让 `FotMobRawParser` 输出每个字段的 timing label（safe_prematch / unsafe_postmatch / unknown_timing / metadata_only / debug_or_raw_only）。

2. **feature engine 改造（未来）**：在 feature 生成阶段，拒绝 `unsafe_postmatch` 和 `unknown_timing` 的字段。只允许 `safe_prematch_candidate` 且 `observed_at ≤ cutoff` 的字段生成特征。

3. **training pipeline 改造（未来）**：训练脚本读取本合同，只使用 `safe_prematch_candidate` 字段。自动跳过标记为 `unsafe_postmatch` 或 `unknown_timing` 的列。

4. **backtest 改造（未来）**：回测框架强制检查 `feature_observed_at ≤ prediction_cutoff_time`。对每个 feature，如果时间条件不满足，自动置为 NaN 或跳过。

5. **CI field-contract compliance check（未来）**：在 CI 中增加检查，如果 parser 新增了字段但未在本合同中登记分类，CI 给出 warning。

**重要**：以上建议需要单独授权、单独 PR。**本 PR 不实现这些。**

---

## 11. 与 DATA-L1A 的关系

| 项目 | DATA-L1A | DATA-L1B（本合同） |
| --- | --- | --- |
| 类型 | 审计报告 | 字段合同 |
| 目的 | 发现风险 | 立规则 |
| 产出 | `docs/_reports/data_l1a_fotmob_prematch_boundary_audit.md` | `docs/data/fotmob_prematch_field_contract.md` |
| 是否替代对方 | 不替代 | 不替代 |
| 关系 | 是本合同的依据 | 是 DATA-L1A 的后续行动 |

- DATA-L1A 发现了字段边界风险，DATA-L1B（本合同）把这些风险转化成正式规则。
- 本合同依据 DATA-L1A，但不会替代 DATA-L1A。DATA-L1A 保留作为审计记录。
- 如果未来发现 DATA-L1A 中的字段判断过时，应更新本合同，而不是直接改模型代码。
- 如果未来发现本合同分类错误（比如某个字段被错误标为 unknown_timing 而实际已证明安全），应更新本合同并记录更新原因。

---

## 12. 本次明确不做事项

本 PR（DATA-L1B）只创建这一份字段合同文档。以下全部不做：

- 没有改代码
- 没有改测试
- 没有改 CI
- 没有改 Docker
- 没有改 DB / migration
- 没有改 scraper / collector
- 没有运行 FotMob 采集
- 没有访问真实 FotMob 网络接口
- 没有改 parser
- 没有改 feature
- 没有改 training
- 没有碰 staging server
- 没有启动 DATA-L1C
- 没有启动 DATA-L1D
- 没有启动 CLEANUP-L1A
- 没有启动 L3I
- 没有启动 L4
- 没有做 legacy 删除 / 移动 / 重命名

---

## 13. 下一步建议

Do not start automatically.

Recommended next task only after user confirmation:

- **DATA-L1C: FotMob Raw Payload Retention and Replay Policy**
  - 目标：基于 DATA-L1B 字段合同，明确 raw payload 的保留策略、replay 条件、DB 存储规则。
  - 仍然建议 docs-only，不改代码。

如果用户认为仓库里旧文件需要整理，也可以选择：

- **CLEANUP-L1A: Repository File Usage Audit**
  - 目标：审计仓库中旧脚本/测试/文档的使用状态，标记可清理项。

但以上建议只供参考，不应自动启动。DATA-L1B 合并后具体做什么，由用户决定。
