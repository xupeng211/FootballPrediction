# V16.0 特征资产全谱清单
## Feature Asset Manifesto for V17.0 Rolling Feature Engineering

---

## 📊 执行摘要

| 项目 | 数值 |
|------|------|
| **总特征维度** | 223 维 |
| **基础指标数量** | 38 个 |
| **数据来源** | FotMob API (赛后统计数据) |
| **数据泄露状态** | ⚠️ 确认存在 - 全部为赛后统计 |
| **V17.0 策略** | 需改用滚动均值/历史特征 |

---

## E. 特征变换逻辑分析

### 数学变换架构

V16.0 的 223 维特征是通过以下 6 种变换类型，从 38 个基础指标演变而来：

| 变换类型 | 描述 | 特征数量 | 计算公式 |
|----------|------|----------|----------|
| `home_` | 主队原始值 | 74 | `home_value` |
| `away_` | 客队原始值 | 74 | `away_value` |
| `total_` | 总计 (主 + 客) | 38 | `home + away` |
| `diff_` | 差值 (主 - 客) | 37 | `home - away` |
| `home_ratio_` | 主队占比 (主/总计) | 36 | `home / (home + away)` |
| `away_ratio_` | 客队占比 (客/总计) | 36 | `away / (home + away)` |

### 变换逻辑示例

以 **`xg` (期望进球)** 为例：

```
基础指标: xg
├── home_xg              = 主队期望进球原始值
├── away_xg              = 客队期望进球原始值
├── total_xg             = home_xg + away_xg
├── diff_xg              = home_xg - away_xg
├── home_ratio_xg        = home_xg / total_xg
└── away_ratio_xg        = away_xg / total_xg
```

---

## A. 进攻维度 (Offensive Metrics)

### A.1 期望进球 (Expected Goals - xG)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_xg`, `home_xg_open_play`, `home_xg_set_piece`, `home_xg_non_penalty`, `home_xg_on_target` |
| away | `away_xg`, `away_xg_open_play`, `away_xg_set_piece`, `away_xg_non_penalty`, `away_xg_on_target` |
| total | `total_xg`, `total_xg_open_play`, `total_xg_set_piece`, `total_xg_non_penalty`, `total_xg_on_target` |
| diff | `diff_xg`, `diff_xg_open_play`, `diff_xg_set_piece`, `diff_xg_non_penalty`, `diff_xg_on_target` |

**小计**: 17 个特征 (5 基础指标 × 3.4 变换)

### A.2 射门统计 (Shots Statistics)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_shots_total`, `home_shots_on_target`, `home_shots_off_target`, `home_shots_blocked`, `home_shots_inside_box`, `home_shots_outside_box`, `home_shots_woodwork`, `home_shots_total_alt` |
| away | `away_shots_total`, `away_shots_on_target`, `away_shots_off_target`, `away_shots_blocked`, `away_shots_inside_box`, `away_shots_outside_box`, `away_shots_woodwork`, `away_shots_total_alt` |
| total | `total_shots_total`, `total_shots_inside_box`, `total_shots_outside_box`, `total_shots_woodwork`, `total_shots_total_alt` |
| diff | `diff_shots_total`, `diff_shots_on_target`, `diff_shots_off_target`, `diff_shots_blocked`, `diff_shots_inside_box`, `diff_shots_outside_box`, `diff_shots_woodwork` |

**小计**: 35 个特征 (8 基础指标 × 4.4 变换)

### A.3 机会创造 (Big Chances)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_big_chances_created` |
| away | `away_big_chances_created` |
| total | `total_big_chances_created` |
| diff | `diff_big_chances_created` |

**小计**: 4 个特征

### A.4 角球 (Corners)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_corners` |
| away | `away_corners` |
| total | `total_corners` |
| diff | `diff_corners` |

**小计**: 4 个特征

**进攻维度总计**: **60 个特征**

---

## B. 组织与传控 (Distribution & Control)

### B.1 传球统计 (Passing)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_passes_total`, `home_passes_accurate`, `home_passes_own_half`, `home_passes_opposition_half` |
| away | `away_passes_total`, `away_passes_accurate`, `away_passes_own_half`, `away_passes_opposition_half` |
| total | `total_passes_total`, `total_passes_accurate`, `total_passes_own_half`, `total_passes_opposition_half` |
| diff | `diff_passes_total`, `diff_passes_accurate`, `diff_passes_own_half`, `diff_passes_opposition_half` |
| home_ratio | `home_ratio_passes_total`, `home_ratio_passes_accurate`, `home_ratio_passes_own_half`, `home_ratio_passes_opposition_half` |
| away_ratio | `away_ratio_passes_total`, `away_ratio_passes_accurate`, `away_ratio_passes_own_half`, `away_ratio_passes_opposition_half` |

**小计**: 24 个特征 (4 基础指标 × 6 变换)

### B.2 长传与传中 (Long Balls & Crosses)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_long_balls_accurate`, `home_crosses_accurate` |
| away | `away_long_balls_accurate`, `away_crosses_accurate` |
| total | `total_long_balls_accurate`, `total_crosses_accurate` |
| diff | `diff_long_balls_accurate`, `diff_crosses_accurate` |
| home_ratio | `home_ratio_long_balls_accurate`, `home_ratio_crosses_accurate` |
| away_ratio | `away_ratio_long_balls_accurate`, `away_ratio_crosses_accurate` |

**小计**: 12 个特征 (2 基础指标 × 6 变换)

### B.3 界外球 (Throw Ins)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_throw_ins` |
| away | `away_throw_ins` |
| total | `total_throw_ins` |
| diff | `diff_throw_ins` |
| home_ratio | `home_ratio_throw_ins` |
| away_ratio | `away_ratio_throw_ins` |

**小计**: 6 个特征

### B.4 控球率 (Possession)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_possession` |
| away | `away_possession` |
| total | `total_possession` |
| diff | `diff_possession` |
| home_ratio | `home_ratio_possession` |
| away_ratio | `away_ratio_possession` |

**小计**: 6 个特征

**组织与传控总计**: **48 个特征**

---

## C. 防守与对抗 (Defensive & Duels)

### C.1 抢断与拦截 (Tackles & Interceptions)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_tackles`, `home_interceptions` |
| away | `away_tackles`, `away_interceptions` |
| total | `total_tackles`, `total_interceptions` |
| diff | `diff_tackles`, `diff_interceptions` |
| home_ratio | `home_ratio_tackles`, `home_ratio_interceptions` |
| away_ratio | `away_ratio_tackles`, `away_ratio_interceptions` |

**小计**: 12 个特征 (2 基础指标 × 6 变换)

### C.2 封堵与解围 (Blocks & Clearances)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_blocked_shots_def`, `home_clearances` |
| away | `away_blocked_shots_def`, `away_clearances` |
| total | `total_blocked_shots_def`, `total_clearances` |
| diff | `diff_blocked_shots_def`, `diff_clearances` |
| home_ratio | `home_ratio_blocked_shots_def`, `home_ratio_clearances` |
| away_ratio | `away_ratio_blocked_shots_def`, `away_ratio_clearances` |

**小计**: 12 个特征 (2 基础指标 × 6 变换)

### C.3 门将扑救 (Keeper Saves)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_keeper_saves` |
| away | `away_keeper_saves` |
| total | `total_keeper_saves` |
| diff | `diff_keeper_saves` |
| home_ratio | `home_ratio_keeper_saves` |
| away_ratio | `away_ratio_keeper_saves` |

**小计**: 6 个特征

### C.4 对抗成功 (Duels Won)

| 子类别 | 变换类型 | 特征名称 |
|--------|----------|----------|
| **总对抗** | home/away/total/diff/home_ratio/away_ratio | `duels_won` (6个) |
| **地面对抗** | home/away/total/diff/home_ratio/away_ratio | `ground_duels_won` (6个) |
| **空中对抗** | home/away/total/diff/home_ratio/away_ratio | `aerial_duels_won` (6个) |

**小计**: 18 个特征 (3 基础指标 × 6 变换)

### C.5 过人成功 (Dribbles)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_dribbles_success` |
| away | `away_dribbles_success` |
| total | `total_dribbles_success` |
| diff | `diff_dribbles_success` |
| home_ratio | `home_ratio_dribbles_success` |
| away_ratio | `away_ratio_dribbles_success` |

**小计**: 6 个特征

### C.6 犯规与越位 (Fouls & Offsides)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_fouls`, `home_offsides` |
| away | `away_fouls`, `away_offsides` |
| total | `total_fouls`, `total_offsides` |
| diff | `diff_fouls`, `diff_offsides` |
| home_ratio | `home_ratio_fouls`, `home_ratio_offsides` |
| away_ratio | `away_ratio_fouls`, `away_ratio_offsides` |

**小计**: 12 个特征 (2 基础指标 × 6 变换)

**防守与对抗总计**: **66 个特征**

---

## D. 球队与阵容 (Team & Lineup)

### D.1 球队评分 (Team Rating)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_team_rating` |
| away | `away_team_rating` |
| total | `total_team_rating` |
| diff | `diff_team_rating` |

**小计**: 4 个特征

### D.2 球员数量 (Player Count)

| 变换类型 | 特征名称 |
|----------|----------|
| home | `home_player_count` |
| away | `away_player_count` |
| total | `total_player_count` |

**小计**: 3 个特征

### D.3 纪律牌 (Cards)

| 纪律类型 | 变换类型 | 特征名称 |
|----------|----------|----------|
| **黄牌** | home/away/total/diff/home_ratio/away_ratio | `yellow_cards` (6个) |
| **红牌** | home/away/total/diff/home_ratio/away_ratio | `red_cards` (6个) |

**小计**: 12 个特征

### D.4 阵型 (Formation)

| 特征名称 | 类型 | 说明 |
|----------|------|------|
| `home_formation` | 字符串 | 主队阵型 (如 "4-3-3") |
| `away_formation` | 字符串 | 客队阵型 (如 "4-3-3") |

**小计**: 2 个特征 (字符串类型，未参与数值计算)

**球队与阵容总计**: **21 个特征** (19 数值 + 2 字符串)

---

## 📋 完整特征维度统计表

| 维度类别 | 基础指标数 | 生成特征数 | 占比 |
|----------|-----------|-----------|------|
| A. 进攻维度 | 13 | 60 | 26.9% |
| B. 组织与传控 | 8 | 48 | 21.5% |
| C. 防守与对抗 | 11 | 66 | 29.6% |
| D. 球队与阵容 | 6 | 21 | 9.4% |
| **总计** | **38** | **223** | **100%** |

---

## 🚨 数据泄露分析

### 问题根源

所有 223 个特征均来自 **FotMob API 赛后统计数据**，这些数据在比赛前不可用：

```
时间线:
赛前 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 比赛开始 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 赛后
   |                                                  |
   |                                                  V
可用特征: 历史数据                          不可用: 这些是赛后统计!
                                            ├─ home_shots_total
   V                                          ├─ away_xg
历史均值特征 (V17.0)                        ├─ home_possession
                                            ├─ home_corners
                                            └─ ... (223 个特征)
```

### V17.0 解决方案

#### 方案 1: 滚动均值 (Rolling Mean)

```python
# 计算每支球队过去 N 场的滚动平均
def get_rolling_features(team_id, match_date, window=10):
    """
    V17.0: 使用历史滚动均值代替实时统计

    Args:
        team_id: 球队 ID
        match_date: 比赛日期
        window: 滚动窗口大小

    Returns:
        滚动均值特征字典
    """
    past_matches = get_matches_before(team_id, match_date)
    rolling_stats = past_matches.tail(window).agg({
        'xg': 'mean',
        'shots_total': 'mean',
        'possession': 'mean',
        # ... 其他指标
    })
    return rolling_stats
```

#### 方案 2: 赛前特征 (Pre-Match Features)

| 特征类别 | 可用特征 | 说明 |
|----------|----------|------|
| 积分榜 | `home_table_position`, `away_table_position` | 联赛排名 |
| 历史战绩 | `home_last5_wins`, `away_last5_wins` | 近5场胜平负 |
| 主客场 | `home_home_form`, `away_away_form` | 主场/客场战绩 |
| 交锋记录 | `h2h_home_wins_last5` | 历史交锋 |
| 休息天数 | `days_since_last_match` | 休息时间 |
| 距离 | `travel_distance` | 客场旅行距离 |

---

## 📊 V17.0 特征工程路线图

### Phase 1: 数据重组 (Week 1)
- [ ] 提取 380 场比赛的历史序列
- [ ] 按时间顺序重建数据集
- [ ] 验证时间连续性

### Phase 2: 滚动特征开发 (Week 2)
- [ ] 实现滚动均值 (window=5, 10, 15)
- [ ] 实现滚动趋势 (slope, momentum)
- [ ] 实现指数加权移动平均 (EWMA)

### Phase 3: 赛前特征补充 (Week 3)
- [ ] 计算积分榜特征
- [ ] 计算历史战绩特征
- [ ] 计算主客场特征

### Phase 4: 特征验证 (Week 4)
- [ ] 时间序列交叉验证
- [ ] 特征重要性分析
- [ ] 数据泄露检测

---

## 📖 参考资料

### FotMob API 文档
- Base URL: `https://www.fotmob.com/api`
- Match Details: `/matchDetails?matchId={id}`
- 数据节点: `content.stats.Periods.All.stats`

### 相关代码
- 数据采集: `src/api/collectors/fotmob_core.py`
- 特征解析: `src/ml/features/l3_pre_match_extractor.py`
- 训练脚本: `v16_model_trainer.py`

---

**文档版本**: V16.0
**创建日期**: 2025-12-23
**维护团队**: Football Prediction Data Science Team
**状态**: ⚠️ 数据泄露已确认 - V17.0 重构中
