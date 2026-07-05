# L3 Prematch-Safe Feature Contract

- Status: source-of-truth
- Scope: `l3_features` / FeatureSmelter output / training input safety
- Parent contract: `docs/data/fotmob_prematch_field_contract.md`
- Last verified by: GOLD-AUDIT-2D, GOLD-AUDIT-2E
- Verification target: `match_id = 53_20252026_4830746`, `data_version = fotmob_live_v1`
- Verified at: `2026-07-05`
- Related PRs: #1719 (FeatureSmelter no-write preview)

---

## 1. 为什么需要这个合同

`raw_match_data → FeatureSmelter → l3_features` 这条技术链路已经跑通（GOLD-AUDIT-2C 证明可以真实写入 1 行）。

但 `l3_features` **不等于赛前安全特征集**。

GOLD-AUDIT-2D 对唯一真实 `l3_features` 行做了逐字段审计，结论：

- **golden_features**（57 keys）：34 个赛前安全（身价、年龄、伤病）+ 23 个赛后泄漏（本场球员评分）
- **tactical_features**（86 keys）：**全部**是赛后泄漏（射门、xG、控球、角球、动量等当前比赛统计）
- **odds_movement_features**（18 keys）：全部是 fallback 占位值（赔率数据缺失）
- **elo_features**（5 keys）：全部是默认值 1500（`team_elo_ratings` 表不存在）
- 其他 6 个 feature group：空

总共有 **109/166 个 key 是赛后泄漏字段**（占 65.7%）。

如果训练代码直接 `SELECT * FROM l3_features` 并展开所有 JSONB key，模型会"提前"看到本场比赛的技术统计和球员评分——这些数据在赛前预测时还不存在。这会造成严重的数据泄漏（data leakage），导致回测虚高、上线跳水。

本合同继承了 `docs/data/fotmob_prematch_field_contract.md` 的分类框架（`safe_prematch_candidate` / `unsafe_postmatch` / `unknown_timing` / `metadata_only` / `debug_or_raw_only`），并将其具体应用到 `l3_features` 的每个 feature group 和 key。

**核心信息：`l3_features` 目前不能用作文本白的赛前训练源。必须先 enforce allowlist/denylist。**

---

## 2. 分类定义

继承自 `fotmob_prematch_field_contract.md` §3，本合同使用相同的分类体系：

| 分类 | 含义 | 能否进入赛前模型 |
|---|---|---|
| `PREMATCH_SAFE` | 字段在 kickoff 前确定存在或可验证 | **可以**（需满足使用条件） |
| `CONDITIONAL_SAFE` | 理论上可用，但必须提供额外证据 | **默认禁止**，证据满足后才能进入 allowlist |
| `POSTMATCH_LEAKAGE` | 当前比赛进行中或结束后才知道 | **永久禁止**进入赛前训练 |
| `UNKNOWN` | 证据不足，无法判断 | **默认禁止**，直到重新审计 |

对应父合同的分类：

| 本合同 | 父合同 |
|---|---|
| `PREMATCH_SAFE` | `safe_prematch_candidate` |
| `CONDITIONAL_SAFE` | `unknown_timing`（有开放路径） |
| `POSTMATCH_LEAKAGE` | `unsafe_postmatch` |
| `UNKNOWN` | `unknown_timing`（无开放路径） |

**规则优先级：**

1. `POSTMATCH_LEAKAGE` 永久禁止进入赛前训练。没有例外，没有"效果可能不大"的豁免。
2. `UNKNOWN` 默认按禁止处理。不能因为"不确定"就"先用着"。
3. `CONDITIONAL_SAFE` 默认不能直接训练。必须满足每个 group 的特定证据条件后才能进入 allowlist。
4. 训练代码必须使用 explicit allowlist。不得 `SELECT *` 然后展开所有 JSONB key。
5. 如果代码和合同冲突，以本合同为准。代码必须修改，合同不迁就代码。

---

## 3. GOLD-AUDIT-2D 分类摘要

基于真实 `l3_features` 行（`match_id = 53_20252026_4830746`）的逐字段审计：

| Feature group | Total | PREMATCH_SAFE | POSTMATCH_LEAKAGE | CONDITIONAL_SAFE | UNKNOWN |
|---|---:|---:|---:|---:|---:|
| `golden_features` | 57 | 34 | 23 | 0 | 0 |
| `tactical_features` | 86 | 0 | 86 | 0 | 0 |
| `odds_movement_features` | 18 | 0 | 0 | 18 | 0 |
| `odds_features` | 0 | 0 | 0 | 0 | 0 |
| `elo_features` | 5 | 0 | 0 | 5 | 0 |
| `rolling_features` | 0 | 0 | 0 | 0 | 0 |
| `efficiency_features` | 0 | 0 | 0 | 0 | 0 |
| `draw_features` | 0 | 0 | 0 | 0 | 0 |
| `market_sentiment` | 0 | 0 | 0 | 0 | 0 |
| `stitch_summary` | 0 | 0 | 0 | 0 | 0 |
| **TOTAL** | **166** | **34** | **109** | **23** | **0** |

---

## 4. PREMATCH_SAFE allowlist v0

以下字段在 `l3_features` 中**已确认赛前安全**，使用条件满足后可以进入训练。

### 4.1 golden_features — allowed v0（34 keys）

所有以下字段源自 `content.lineup` 中的阵容快照（球员名单、市场价值、年龄、伤病）。数据本身是赛前可获得的静态信息。

#### metadata（审计用，不作为预测特征）

| Key | 说明 |
|---|---|
| `_source` | 数据来源标记（`"FotMob"`） |
| `_version` | FeatureSmelter 版本（`"V3.0.0-PRO"`） |

> `_extractedAt` 只能作为审计时间戳，**不能作为模型特征**（它是 smelt 执行时间，不是特征可用时间）。

#### age / squad（年龄和阵容构成）

| Key | 来源 | 示例值 |
|---|---|---|
| `home_age_avg` | `starters[].age` | `26.5` |
| `away_age_avg` | 同上 | `20.6` |
| `age_gap` | 衍生（home - away） | `5.9` |
| `home_starters_count` | `starters[]` 数组长度 | `11` |
| `away_starters_count` | 同上 | `11` |
| `home_u23_count` | 衍生（age < 23） | `3` |
| `away_u23_count` | 同上 | `9` |
| `home_veteran_count` | 衍生（age >= 30） | `4` |
| `away_veteran_count` | 同上 | `0` |

#### market value（身价）

| Key | 来源 | 示例值 |
|---|---|---|
| `home_market_value_total` | `totalStarterMarketValue` / `starters[].marketValue` | `22189037000000` |
| `away_market_value_total` | 同上 | `141443829000000` |
| `home_market_value_avg` | 衍生（total / starters_count） | `2017185181818` |
| `away_market_value_avg` | 同上 | `12858529909091` |
| `home_market_value_max` | 衍生 | `0` |
| `away_market_value_max` | 衍生 | `0` |
| `home_market_value_min` | 衍生 | `0` |
| `away_market_value_min` | 衍生 | `0` |
| `home_market_value_std` | 衍生 | `0` |
| `away_market_value_std` | 衍生 | `0` |
| `home_market_value_raw` | `totalStarterMarketValue`（百万欧元） | `22189037` |
| `away_market_value_raw` | 同上 | `141443829` |
| `home_market_value_source` | 提取器标记 | `"totalStarterMarketValue"` |
| `away_market_value_source` | 同上 | `"totalStarterMarketValue"` |
| `home_value_source` | 同上 | `"totalStarterMarketValue"` |
| `away_value_source` | 同上 | `"totalStarterMarketValue"` |
| `market_value_gap` | 衍生（home - away） | `-119254792000000` |
| `market_value_ratio` | 衍生（home / away） | `0.157` |

#### injury / suspension（伤停）

| Key | 来源 | 示例值 |
|---|---|---|
| `home_injury_count` | `lineup.unavailable[]` | `1` |
| `away_injury_count` | 同上 | `3` |
| `home_injury_doubtful_count` | `unavailable[].unavailability.type` | `0` |
| `away_injury_doubtful_count` | 同上 | `0` |
| `home_injury_injury_count` | 同上 | `0` |
| `away_injury_injury_count` | 同上 | `1` |
| `home_injury_suspension_count` | 同上 | `1` |
| `away_injury_suspension_count` | 同上 | `2` |
| `injury_count_gap` | 衍生（home - away） | `-2` |

> **注意**：上述 key 名以当前 DB/代码实际产出为准。如果 FeatureSmelter 变更导致 key 名变化，本合同必须同步更新。

### 4.2 其他 group — allowed v0

| Feature group | Status |
|---|---|
| `odds_features` | 空（0 keys）。无可用字段 |
| `odds_movement_features` | CONDITIONAL_SAFE（见 §6.1） |
| `elo_features` | CONDITIONAL_SAFE（见 §6.2） |
| `rolling_features` | 空（0 keys）。需要 SmelterOrchestrator |
| `efficiency_features` | 空（0 keys）。需要 SmelterOrchestrator |
| `draw_features` | 空（0 keys）。需要 SmelterOrchestrator |
| `market_sentiment` | 空（0 keys）。需要 OddsPortal |
| `stitch_summary` | 空（0 keys） |

**PREMATCH_SAFE 总计可用于 v0 训练的字段：34 个（全部来自 golden_features 中排除 rating 后的子集）。**

---

## 5. Explicit denylist v0

### 5.1 tactical_features.\* — 全部禁止

```
tactical_features 全部 86 个 key 禁止进入赛前训练。永久禁止，无例外。
```

**来源**：`content.stats.Periods.All.stats` + `content.momentum`

**具体禁止的字段类别**：

| 类别 | 示例 key | 有多少个 |
|---|---|---|
| 射门 | `home_shots`, `away_shots`, `home_shots_on_target`, `away_shots_on_target`, `home_shots_off_target`, `away_shots_off_target`, `home_shots_inside_box`, `away_shots_inside_box`, `home_shots_outside_box`, `away_shots_outside_box`, `home_blocked_shots`, `away_blocked_shots`, `home_shot_accuracy`, `away_shot_accuracy` | ~14 |
| xG | `home_xg`, `away_xg`, `home_xg_per_shot`, `away_xg_per_shot` | ~4 |
| 控球 | `home_possession`, `away_possession`, `home_possession_pct`, `away_possession_pct` | ~4 |
| 传球 | `home_passes`, `away_passes`, `home_accurate_passes`, `away_accurate_passes` | ~4 |
| 角球 | `home_corners`, `away_corners` | ~2 |
| 机会 | `home_big_chances`, `away_big_chances`, `home_hit_woodwork`, `away_hit_woodwork` | ~4 |
| 纪律 | `home_yellow_cards`, `away_yellow_cards`, `home_red_cards`, `away_red_cards`, `home_discipline_score`, `away_discipline_score`, `home_offsides`, `away_offsides` | ~8 |
| 强度 | `home_strength_index`, `away_strength_index` | ~2 |
| 动量 | `momentum_overall_mean`, `momentum_samples_count`, `momentum_direction`, `momentum_trend`, `momentum_seg1-6_*`, `has_momentum_data` | ~24 |
| 差值/比率 | `xg_diff`, `xg_ratio`, `total_xg`, `possession_diff`, `possession_ratio`, `shots_on_target_diff`, `big_chances_diff`, `corners_diff`, `strength_diff`, `discipline_diff`, `fouls_diff`, `total_corners`, `total_fouls` | ~13 |
| 元数据 | `_extractedAt`, `_version` | ~2 |

**为什么禁止**：这些全部是当前比赛的进行中/赛后统计数据。在赛前预测时这些数据还不存在。使用它们预测本场比赛结果 = 训练代码看到了答案。

**特别注意**：动量数据（`momentum_*`）虽然是时序数据，但它是**本场比赛过程中**的动量，不是历史动量。赛前你拿不到本场比赛的动量值。

### 5.2 golden_features rating fields — 全部禁止

```
golden_features 中任何来自 starters[].performance.rating 的字段禁止进入赛前训练。
```

**来源**：`content.lineup.homeTeam.starters[].performance.rating` / `awayTeam.starters[].performance.rating`

**禁止的字段**（23 个）：

| Key | 含义 | 为什么是泄漏 |
|---|---|---|
| `home_rating_avg` | 主队首发平均评分 | FotMob 赛后对每位球员的打分 |
| `away_rating_avg` | 客队首发平均评分 | 同上 |
| `home_rating_std` | 主队评分标准差 | 衍生自赛后评分 |
| `away_rating_std` | 客队评分标准差 | 同上 |
| `home_rating_max` | 主队最高评分 | 同上 |
| `away_rating_max` | 客队最高评分 | 同上 |
| `home_rating_min` | 主队最低评分 | 同上 |
| `away_rating_min` | 客队最低评分 | 同上 |
| `home_rating_available_count` | 有评分的球员数 | 同上 |
| `away_rating_available_count` | 有评分的球员数 | 同上 |
| `home_rating_average_count` | 衍生 | 同上 |
| `away_rating_average_count` | 衍生 | 同上 |
| `home_rating_excellent_count` | 评分 >= 7.5 的球员数 | 同上 |
| `away_rating_excellent_count` | 评分 >= 7.5 的球员数 | 同上 |
| `home_rating_good_count` | 评分 >= 6.5 的球员数 | 同上 |
| `away_rating_good_count` | 评分 >= 6.5 的球员数 | 同上 |
| `home_rating_poor_count` | 评分 < 6.0 的球员数 | 同上 |
| `away_rating_poor_count` | 评分 < 6.0 的球员数 | 同上 |
| `rating_gap` | home - away 评分差 | 衍生自赛后评分 |

> `performance.rating` 是 FotMob 在比赛结束后根据球员表现计算的分值。`fotmob_prematch_field_contract.md` §4 已将其分类为 `unsafe_postmatch`（绝对禁止）。

**匹配模式**：任何匹配 `*_rating_*` 或 `rating_gap` 的字段都应被 denylist 拦截。

---

## 6. CONDITIONAL_SAFE 规则

### 6.1 odds / odds_movement_features

**理论上**可用于赛前预测，但必须满足以下全部条件：

1. `has_odds_data = true`
2. `odds_source` 明确且可验证
3. 每条赔率记录有 `captured_at` 时间戳
4. `captured_at ≤ prediction_cutoff_time`
5. 非 fallback（`_error` 不为 `"No odds data available"`）
6. 区分 opening/closing/current 并各自标记 horizon 适用性

**当前状态**（2026-07-05）：

```
_data_quality: "INCOMPLETE_ODDS"
_error: "No odds data available"
has_odds_data: false
current_*_odds: 0
initial_*_odds: 0
implied_prob_*: 0.333（均匀分布 fallback）
odds_source: "none"
odds_anomaly_flag: false
steam_detected: false
steam_strength: 0
```

**结论**：当前全部 18 个 odds_movement_features key 是 fallback 占位，**不得作为训练特征**。等 OddsPortal 集成完成后重新审计。

**父合同对应**：`fotmob_prematch_field_contract.md` §7（odds 字段特殊规则）。

### 6.2 elo_features

**理论上**可用于赛前预测（Elo 是基于历史结果的实力评分），但必须满足：

1. 基于当前比赛**之前**的历史比赛计算
2. `home_elo` / `away_elo` 值反映真实历史实力差
3. `_is_default = false`（非 fallback 1500）

**当前状态**（2026-07-05）：

```
_is_default: true
home_elo: 1500
away_elo: 1500
elo_diff: 0
elo_expected_home: 0.571
```

**结论**：`team_elo_ratings` 表不存在，所有值都是默认 1500。虽然不会泄漏（信息量为零），但也**没有区分力**，不应作为有效训练信号。

### 6.3 rolling / efficiency / draw features

**理论上**可用于赛前预测（历史滚动特征），但必须满足：

1. 只使用 `match_date < current_match_date` 的历史比赛
2. 不包含当前比赛本身
3. 有明确的窗口边界（L3、L5 等）和 cutoff 证明

**当前状态**（2026-07-05）：这三个 feature group **都是空的**（0 keys）。

**原因**：当前使用的是 FeatureSmelter（Pipeline A），它不运行 RollingFeatureExtractor / EfficiencyFeatureExtractor / DrawPropensityExtractor。这些需要 SmelterOrchestrator（Pipeline B）。

### 6.4 market_sentiment

**理论上**可用于赛前预测，但需要真实赔率数据。

**当前状态**（2026-07-05）：空（0 keys）。

---

## 7. Training policy

### 7.1 禁止的操作

```
训练代码不得：
- SELECT * FROM l3_features 并展开所有 JSONB key
- 直接读取 tactical_features.* 用于赛前训练
- 直接读取 golden_features 中任何 *_rating_* / rating_gap 字段用于赛前训练
- 在没有 allowlist 保护的情况下从 l3_features 读取特征
```

### 7.2 当前代码中的 prematch guard

| 训练脚本 | 守卫机制 | 评估 |
|---|---|---|
| `scripts/model_training/train_baseline_v1.py` | `PREMATCH_JSON_FEATURES` allowlist（仅 elo + odds） + `POSTMATCH_DIAGNOSTIC_FEATURES` 诊断标记 | **有 conscious 设计**，但 key 名与 FeatureSmelter 产出不完全匹配（`home_elo_pre` vs `home_elo`） |
| `scripts/ops/train_model.py` | `extract_v5_features()` 从 golden（身价 3 维）+ elo（5 维）+ tactical（H2H 估算 3 维）合成 11 维 | **部分安全**——tactical 读取的 H2H 字段当前不存在（fallback 到估算），但没有显式 deny tactical 字段 |
| `src/database/repositories/prediction_repo.py` | 读取 `elo_features`, `golden_features`, `tactical_features` 用于未来比赛预测 | **无 allowlist**——预测 pipeline 直接读取所有三个 group |

### 7.3 要求的训练行为

1. **训练代码必须使用 explicit allowlist。** 默认只允许 `PREMATCH_SAFE` 字段。
2. **`POSTMATCH_DIAGNOSTIC_FEATURES`（`train_baseline_v1.py`）只能用于诊断，不能用于赛前训练。** 任何使用 `tactical_features` 的模型都必须标记为 postmatch diagnostic，不得宣称为 prematch predictor。
3. **训练代码读取 `l3_features` 时必须有 field-level filter。** 不能依赖"反正当前数据里没有"来确保安全。
4. **任何新训练脚本上线前必须先确认使用了本合同定义的 allowlist。**

---

## 8. Prediction policy

未来比赛的 prediction pipeline（如 `prediction_repo.py`）必须遵守：

1. **只能读取 PREMATCH_SAFE / verified CONDITIONAL_SAFE 字段**
2. **不得读取 tactical_features.\* 中的任何字段**
3. **不得读取 golden rating 字段（`*_rating_*` / `rating_gap`）**
4. **不得读取当前比赛 stats / momentum / xG / shotmap / events**
5. **如果从 golden_features 读取，只允许 §4.1 中列出的 PREMATCH_SAFE key**
6. **如果从 elo_features 读取，必须检查 `_is_default != true` 或忽略默认值**
7. **如果从 odds_movement_features 读取，必须检查 `has_odds_data = true`**

这些规则与 `fotmob_prematch_field_contract.md` §5（模型使用规则）一致。

---

## 9. Backtest policy

回测是验证模型质量的地方，也是泄漏最容易发生的地方。与 `fotmob_prematch_field_contract.md` §6 一致：

1. **回测必须模拟真实赛前 cutoff。** 每条样本只能用 kickoff 前已存在的数据。
2. **不能使用 `tactical_features.\*` 来提升回测分数。** 这会让回测虚高，上线后必然跳水。
3. **不能使用 rating 字段来提升回测分数。**
4. **chronological split 优先于 random split。** 训练集的所有比赛必须早于验证集和测试集。
5. **如果 feature 没有 timestamp 或 cutoff 证据，默认不可用于赛前回测。**

---

## 10. Implementation backlog

以下任务按优先级列出，但**本 PR 不执行任何代码实现**：

### P0：Critical（训练阻塞项）

- [ ] **Add machine-readable prematch allowlist/denylist**：将本合同的 allowlist/denylist 转化为代码可读取的配置文件（JSON/YAML）
- [ ] **Enforce allowlist in training entrypoints**：在 `train_baseline_v1.py` 和 `train_model.py` 中加载 allowlist 并过滤字段
- [ ] **Fix key name mismatch**：统一 FeatureSmelter 产出的 key 名与训练代码的 `PREMATCH_JSON_FEATURES`（如 `home_elo` vs `home_elo_pre`）

### P1：High（安全加固）

- [ ] **Split or exclude golden rating fields**：在 FeatureSmelter 中将 `starters[].performance.rating` 相关字段隔离到单独 group 或剔除
- [ ] **Mark tactical_features as postmatch diagnostic only**：在代码级阻止 tactical_features 被误用于赛前训练
- [ ] **Enforce allowlist in prediction_repo.py**：未来比赛预测 pipeline 必须过滤字段

### P2：Medium（数据质量）

- [ ] **Create prematch-safe DB view**：创建 `l3_prematch_safe_features` 视图，只暴露 PREMATCH_SAFE 字段
- [ ] **Add feature_tier metadata column**：在 `l3_features` 表添加 `feature_tier` 列标记每个 feature group 的安全等级
- [ ] **Populate team_elo_ratings table**：使 elo_features 从默认值升级为真实区分力
- [ ] **Integrate OddsPortal**：使 odds_features 和 odds_movement_features 从 fallback 升级为真实赔率数据

### P3：Later（批量数据）

- [ ] **Batch smelt remaining 57 matches only after P0 and P1 enforcements**
- [ ] **Training dry-run only after allowlist enforcement**

---

## 11. Current decision

基于 GOLD-AUDIT-2D 审计结论和本合同规则：

| 决策 | 结论 | 理由 |
|---|---|---|
| **是否批量 smelt 剩余 57 条？** | **否** | 当前 FeatureSmelter 产出包含 109 个赛后泄漏字段。批量 smelt 会制造 58 行充满泄漏的数据，而不是 58 行可用的赛前特征。必须先 enforce allowlist/denylist |
| **是否执行 training dry-run？** | **否** | `tactical_features` 全部泄漏，`elo_features` 全为默认值，`odds_features` 全部为空。当前训练只能拿到 golden 的 34 个 PREMATCH_SAFE 字段，质量不足以产生有意义的基线 |
| **是否可以使用 l3_features 作为通用训练源？** | **否** | l3_features 未经 allowlist 保护，直接使用等于开卷考试 |
| **下一步应该做什么？** | **先 enforce allowlist/denylist** | 代码级阻断比文档级约定更可靠。P0 任务（machine-readable allowlist + training enforcement）是后续所有工作的前提 |

---

## 12. 与父合同的关系

| 项目 | `fotmob_prematch_field_contract.md` | 本合同 |
|---|---|---|
| 层级 | FotMob raw 字段级别 | `l3_features` / FeatureSmelter 产出级别 |
| 回答什么问题 | "FotMob 数据里哪些字段能用？" | "FeatureSmelter 生成的特征哪些能训练？" |
| 分类体系 | `safe_prematch_candidate` / `unsafe_postmatch` / `unknown_timing` / `metadata_only` / `debug_or_raw_only` | `PREMATCH_SAFE` / `POSTMATCH_LEAKAGE` / `CONDITIONAL_SAFE` / `UNKNOWN`（映射到父合同分类） |
| 是否替代 | — | 不替代，是补充 |

- 父合同定义**通用原则**：哪些类别的数据安全/不安全。
- 本合同定义**具体映射**：FeatureSmelter 的每个 feature group 和每个 key 属于哪个类别。
- 如果父合同更新了分类规则，本合同必须重新审计并同步更新。
- 如果 FeatureSmelter 新增或重命名了 key，本合同必须重新审计并同步更新。

---

## 13. 本次明确不做事项

本 PR（GOLD-AUDIT-2E）只创建这份 L3 prematch-safe feature contract 文档。以下全部不做：

- 不修改 FeatureSmelter 代码
- 不修改 training / prediction / backtest 代码
- 不修改 `.github/**`
- 不修改 migrations
- 不修改 DB schema
- 不写数据库
- 不 smelt
- 不 batch smelt
- 不训练
- 不预测
- 不回测
- 不访问 FotMob 网络
- 不运行 scraper / collector / browser
- 不运行 OddsPortal pipeline
- 不删除 / 移动 / 重命名文件
- 不启动下一任务
