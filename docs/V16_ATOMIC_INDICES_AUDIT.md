# V16.0 原子级指标清单审计报告
## Atomic Metrics Audit for V16.0 Feature System

---

## 📊 执行摘要

| 项目 | 数值 |
|------|------|
| **基础指标总数** | **39 个** |
| stat_mapping 指标 | 36 个 |
| lineup 指标 | 3 个 |
| 数据来源 | FotMob API + lineup |

### 维度分布

| 维度 | 指标数 | 占比 |
|------|--------|------|
| 进攻维度 | 15 | 38.5% |
| 传控维度 | 8 | 20.5% |
| 防守维度 | 9 | 23.1% |
| 纪律维度 | 4 | 10.3% |
| 阵营维度 | 3 | 7.7% |

---

## A. 进攻维度 (Offensive Metrics) - 15 个指标

| API Key | 内部名称 | 中文含义 | 数据类型 | 业务说明 |
|---------|----------|----------|----------|----------|
| `expected_goals` | `xg` | 期望进球 | 数值 | 预期进球数（基于射门质量计算） |
| `expected_goals_open_play` | `xg_open_play` | 运动战期望进球 | 数值 | 非定位球方式的期望进球 |
| `expected_goals_set_play` | `xg_set_piece` | 定位球期望进球 | 数值 | 角球、任意球等定位球的期望进球 |
| `expected_goals_non_penalty` | `xg_non_penalty` | 非点球期望进球 | 数值 | 不含点球的期望进球 |
| `expected_goals_on_target` | `xg_on_target` | 射正期望进球 | 数值 | 射在门框范围内的期望进球 |
| `total_shots` | `shots_total` | 总射门次数 | 次数 | 所有射门尝试次数 |
| `shots` | `shots_total_alt` | 总射门次数(备用) | 次数 | 另一个射门统计源 |
| `ShotsOnTarget` | `shots_on_target` | 射正次数 | 次数 | 射在门框范围内的次数 |
| `ShotsOffTarget` | `shots_off_target` | 射偏次数 | 次数 | 未射中门框的次数 |
| `blocked_shots` | `shots_blocked` | 被封堵射门 | 次数 | 被防守球员封堵的射门 |
| `shots_woodwork` | `shots_woodwork` | 击中门框 | 次数 | 射中门柱或横梁的次数 |
| `shots_inside_box` | `shots_inside_box` | 禁区内射门 | 次数 | 在禁区内完成的射门 |
| `shots_outside_box` | `shots_outside_box` | 禁区外射门 | 次数 | 在禁区外完成的射门 |
| `big_chance` | `big_chances_created` | 创造良机次数 | 次数 | 创造的高质量得分机会 |
| `corners` | `corners` | 角球次数 | 次数 | 获得的角球数量 |

### 关键发现：进攻维度

1. **xG 体系完整** - 包含 5 个 xG 细分指标，覆盖运动战、定位球、射中等场景
2. **射门统计全面** - 8 个射门相关指标，覆盖位置、结果、方式
3. **机会质量跟踪** - `big_chances_created` 捕捉高质量机会

---

## B. 传控维度 (Distribution & Control) - 8 个指标

| API Key | 内部名称 | 中文含义 | 数据类型 | 业务说明 |
|---------|----------|----------|----------|----------|
| `BallPossesion` | `possession` | 控球率 | 百分比 | 控球时间占比 |
| `passes` | `passes_total` | 总传球次数 | 次数 | 完成传球的总数 |
| `accurate_passes` | `passes_accurate` | 成功传球次数 | 次数 | 准确传球的次数 |
| `own_half_passes` | `passes_own_half` | 本方半场传球 | 次数 | 在本方半场完成的传球 |
| `opposition_half_passes` | `passes_opposition_half` | 对方半场传球 | 次数 | 在对方半场完成的传球 |
| `long_balls_accurate` | `long_balls_accurate` | 成功长传次数 | 次数 | 准确的长距离传球 |
| `accurate_crosses` | `crosses_accurate` | 成功传中次数 | 次数 | 准确的传中球 |
| `player_throws` | `throw_ins` | 界外球次数 | 次数 | 掷界外球的次数 |

### 关键发现：传控维度

1. **控球权核心** - `possession` 是基础中的基础
2. **传球层次清晰** - 区分总传球、成功传球、区域传球
3. **战术元素** - 长传、传中反映战术风格

---

## C. 防守维度 (Defensive & Duels) - 9 个指标

| API Key | 内部名称 | 中文含义 | 数据类型 | 业务说明 |
|---------|----------|----------|----------|----------|
| `matchstats.headers.tackles` | `tackles` | 抢断次数 | 次数 | 成功抢回球权的次数 |
| `interceptions` | `interceptions` | 拦截次数 | 次数 | 拦截对方传球的成功次数 |
| `shot_blocks` | `blocked_shots_def` | 封堵射门 | 次数 | 封堵对方射门的次数 |
| `clearances` | `clearances` | 解围次数 | 次数 | 将球解围出危险区域的次数 |
| `keeper_saves` | `keeper_saves` | 门将扑救 | 次数 | 门将成功扑救的次数 |
| `duel_won` | `duels_won` | 对抗获胜 | 次数 | 赢得所有对抗的次数 |
| `ground_duels_won` | `ground_duels_won` | 地面对抗获胜 | 次数 | 赢得地面对抗的次数 |
| `aerials_won` | `aerial_duels_won` | 空中对抗获胜 | 次数 | 赢得空中争顶的次数 |
| `dribbles_succeeded` | `dribbles_success` | 过人成功 | 次数 | 成功突破过人的次数 |

### 关键发现：防守维度

1. **防守动作完整** - 抢断、拦截、封堵、解围全覆盖
2. **门将独立** - `keeper_saves` 单独追踪门将表现
3. **对抗细分** - 区分总对抗、地面对抗、空中对抗
4. **个人能力** - `dribbles_success` 反映个人突破能力

---

## D. 纪律维度 (Discipline) - 4 个指标

| API Key | 内部名称 | 中文含义 | 数据类型 | 业务说明 |
|---------|----------|----------|----------|----------|
| `fouls` | `fouls` | 犯规次数 | 次数 | 被判罚犯规的次数 |
| `Offsides` | `offsides` | 越位次数 | 次数 | 被判罚越位的次数 |
| `yellow_cards` | `yellow_cards` | 黄牌数量 | 次数 | 被出示黄牌的数量 |
| `red_cards` | `red_cards` | 红牌数量 | 次数 | 被出示红牌的数量 |

### 关键发现：纪律维度

1. **简洁有效** - 4 个指标覆盖纪律全貌
2. **红黄牌分离** - 单独追踪不同纪律级别
3. **战术纪律** - `offsides` 反映进攻战术执行

---

## E. 阵营维度 (Lineup) - 3 个指标

| 数据源 | 内部名称 | 中文含义 | 数据类型 | 业务说明 |
|--------|----------|----------|----------|----------|
| `lineup.homeTeam.rating` | `team_rating` | 球队评分 | 评分 | 球队整体表现评分（1-10分） |
| `lineup.*.starters + subs` | `player_count` | 球员数量 | 次数 | 参与比赛的球员总数 |
| `lineup.*.formation` | `formation` | 阵型 | 字符串 | 球队阵型（如 4-3-3） |

### 关键发现：阵营维度

1. **评分主观性** - `team_rating` 是赛后评分，存在主观性
2. **阵容完整性** - `player_count` 反映阵容是否完整
3. **战术配置** - `formation` 字符串特征，未参与数值计算

---

## 📋 完整 39 指标汇总表

| # | API Key | 内部名称 | 分类 | 数据类型 |
|---|---------|----------|------|----------|
| 1 | `expected_goals` | `xg` | 进攻 | 数值 |
| 2 | `expected_goals_open_play` | `xg_open_play` | 进攻 | 数值 |
| 3 | `expected_goals_set_play` | `xg_set_piece` | 进攻 | 数值 |
| 4 | `expected_goals_non_penalty` | `xg_non_penalty` | 进攻 | 数值 |
| 5 | `expected_goals_on_target` | `xg_on_target` | 进攻 | 数值 |
| 6 | `total_shots` | `shots_total` | 进攻 | 次数 |
| 7 | `shots` | `shots_total_alt` | 进攻 | 次数 |
| 8 | `ShotsOnTarget` | `shots_on_target` | 进攻 | 次数 |
| 9 | `ShotsOffTarget` | `shots_off_target` | 进攻 | 次数 |
| 10 | `blocked_shots` | `shots_blocked` | 进攻 | 次数 |
| 11 | `shots_woodwork` | `shots_woodwork` | 进攻 | 次数 |
| 12 | `shots_inside_box` | `shots_inside_box` | 进攻 | 次数 |
| 13 | `shots_outside_box` | `shots_outside_box` | 进攻 | 次数 |
| 14 | `big_chance` | `big_chances_created` | 进攻 | 次数 |
| 15 | `corners` | `corners` | 进攻 | 次数 |
| 16 | `BallPossesion` | `possession` | 传控 | 百分比 |
| 17 | `passes` | `passes_total` | 传控 | 次数 |
| 18 | `accurate_passes` | `passes_accurate` | 传控 | 次数 |
| 19 | `own_half_passes` | `passes_own_half` | 传控 | 次数 |
| 20 | `opposition_half_passes` | `passes_opposition_half` | 传控 | 次数 |
| 21 | `long_balls_accurate` | `long_balls_accurate` | 传控 | 次数 |
| 22 | `accurate_crosses` | `crosses_accurate` | 传控 | 次数 |
| 23 | `player_throws` | `throw_ins` | 传控 | 次数 |
| 24 | `matchstats.headers.tackles` | `tackles` | 防守 | 次数 |
| 25 | `interceptions` | `interceptions` | 防守 | 次数 |
| 26 | `shot_blocks` | `blocked_shots_def` | 防守 | 次数 |
| 27 | `clearances` | `clearances` | 防守 | 次数 |
| 28 | `keeper_saves` | `keeper_saves` | 防守 | 次数 |
| 29 | `duel_won` | `duels_won` | 防守 | 次数 |
| 30 | `ground_duels_won` | `ground_duels_won` | 防守 | 次数 |
| 31 | `aerials_won` | `aerial_duels_won` | 防守 | 次数 |
| 32 | `dribbles_succeeded` | `dribbles_success` | 防守 | 次数 |
| 33 | `fouls` | `fouls` | 纪律 | 次数 |
| 34 | `Offsides` | `offsides` | 纪律 | 次数 |
| 35 | `yellow_cards` | `yellow_cards` | 纪律 | 次数 |
| 36 | `red_cards` | `red_cards` | 纪律 | 次数 |
| 37 | `team_rating` | `team_rating` | 阵营 | 评分 |
| 38 | `player_count` | `player_count` | 阵营 | 次数 |
| 39 | `formation` | `formation` | 阵营 | 字符串 |

---

## 🚨 数据泄露风险评估

### 高风险指标 (赛后统计)

| 风险等级 | 指标类别 | 说明 |
|----------|----------|------|
| 🔴 极高 | 所有 39 个指标 | **全部为赛后统计数据** |
| 🔴 极高 | 进攻维度 (15个) | 射门、xG、角球等都是比赛结束后统计 |
| 🔴 极高 | 传控维度 (8个) | 控球率、传球次数等是赛后累计数据 |
| 🔴 极高 | 防守维度 (9个) | 抢断、拦截、扑救等是赛后统计 |
| 🟡 中等 | 纪律维度 (4个) | 红黄牌、越位在比赛中累积 |
| 🟡 中等 | 阵营维度 (3个) | 评分是赛后，阵型是赛前已知 |

### V17.0 滚动特征可用性评估

| 原子指标 | 可用性评估 | V17.0 替代方案 |
|----------|------------|----------------|
| xG 系列 | ❌ 不可用 | 使用历史 xG 滚动均值 |
| 射门系列 | ❌ 不可用 | 使用历史射门数据滚动均值 |
| 控球率 | ❌ 不可用 | 使用历史控球率滚动均值 |
| 传球系列 | ❌ 不可用 | 使用历史传球数据滚动均值 |
| 红黄牌 | ✅ 部分可用 | 累计赛季数据（不含本场） |
| 阵型 | ✅ 可用 | 赛前已知 |
| 球员数量 | ✅ 可用 | 赛前已知（首发预测） |

---

## 📊 矿石质量评估

### 数据质量维度

| 维度 | 评分 | 说明 |
|------|------|------|
| **覆盖面** | ⭐⭐⭐⭐⭐ | 5/5 - 进攻、防守、传控、纪律全覆盖 |
| **颗粒度** | ⭐⭐⭐⭐⭐ | 5/5 - 指标细分程度极高 |
| **准确性** | ⭐⭐⭐⭐⭐ | 5/5 - FotMob 数据质量高 |
| **时效性** | ⭐☆☆☆☆ | 1/5 - **全部为赛后数据** |
| **可用性** | ⭐☆☆☆☆ | 1/5 - **无法直接用于赛前预测** |

### 综合结论

**矿石质量：高质量但不可用**

- ✅ 数据本身是优质的（FotMob 提供详细的赛后统计）
- ❌ 但全部为赛后数据，无法用于赛前预测
- ⚠️ V16.0 的 96.25% 准确率是"虚高"，实际上是在预测已知的比赛结果

---

## 🎯 V17.0 滚动特征工程建议

### 可用数据源

1. **历史滚动均值** (Rolling Mean)
   - window=5, 10, 15 场
   - 指标：xG、射门、控球率、传球等

2. **赛前特征** (Pre-Match Features)
   - 积分榜排名
   - 近期战绩 (W/D/L)
   - 主客场战绩
   - 历史交锋 (H2H)
   - 休息天数
   - 伤病情况

3. **赛季累计** (Season Cumulative)
   - 累计红黄牌
   - 累计积分
   - 累计进球/失球

---

**文档版本**: V16.0 Atomic Audit
**创建日期**: 2025-12-23
**审计范围**: 39 个基础指标 (stat_mapping 36 + lineup 3)
**状态**: ⚠️ 数据泄露确认 - 需 V17.0 重构
