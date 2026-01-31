# Phase 5 Design: Advanced Feature Engineering

## 📅 Status
* **Date**: 2025-12-16
* **Phase**: Phase 5 - Advanced Features
* **Branch**: feat/phase-5-advanced-features
* **Status**: 🚧 In Progress

## 🎯 Goal

通过引入更复杂的高级特征，将模型准确率从 **58.69%** 提升至 **65%+**，解决 Phase 4 中发现的关键预测问题，特别是 Napoli vs Juventus 案例中的主客场偏见问题。

## 🔍 Phase 4 问题分析

### 核心问题识别
通过 Napoli vs Juventus (ID: 2421) 的预测失误分析，我们发现了以下关键问题：

1. **主客场混淆**: 模型将主客场比赛混合计算滚动统计
2. **缺乏历史交锋**: 没有考虑两队之间的历史对战记录
3. **单一指标偏重**: 过度依赖进球数，忽略了积分等更稳定的指标
4. **上下文缺失**: 缺少联赛排名、主客场优势等上下文信息

## 🛠️ Phase 5 高级特征策略

### 1. 场馆分离滚动统计 (The "Napoli Fix")

**问题**: Phase 4 中 Napoli 主场0进球导致被严重低估

**解决方案**: 将主客场比赛完全分离计算滚动统计

#### 1.1 主场专用滚动特征
```python
# 主队在主场的表现
df['home_team_home_goals_rolling_3'] = (
    df[df['venue'] == 'home']
    .groupby('home_team_id')['home_score']
    .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))
)

df['home_team_home_goals_rolling_5'] = (
    df[df['venue'] == 'home']
    .groupby('home_team_id')['home_score']
    .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
)
```

#### 1.2 客场专用滚动特征
```python
# 客队在客场的表现
df['away_team_away_goals_rolling_3'] = (
    df[df['venue'] == 'away']
    .groupby('away_team_id')['away_score']
    .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))
)

df['away_team_away_goals_rolling_5'] = (
    df[df['venue'] == 'away']
    .groupby('away_team_id')['away_score']
    .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
)
```

#### 1.3 主客场对比特征
```python
# 主客场比赛表现差异
df['home_vs_away_goal_diff_rolling_3'] = df['home_team_home_goals_rolling_3'] - df['away_team_away_goals_rolling_3']
df['home_vs_away_goal_diff_rolling_5'] = df['home_team_home_goals_rolling_5'] - df['away_team_away_goals_rolling_5']
```

### 2. 历史交锋统计 (Head-to-Head Stats)

**问题**: 缺乏两队之间的历史对战信息，无法捕捉"克星"效应

#### 2.1 H2H 胜率和积分统计
```python
def calculate_h2h_stats(df):
    """计算两队历史交锋统计"""
    # 为每场比赛计算历史交锋记录
    h2h_stats = []

    for _, match in df.iterrows():
        home_id, away_id = match['home_team_id'], match['away_team_id']
        match_date = match['match_date']

        # 获取两队历史交锋记录（排除当前比赛）
        past_matches = df[
            ((df['home_team_id'] == home_id) & (df['away_team_id'] == away_id) |
             (df['home_team_id'] == away_id) & (df['away_team_id'] == home_id)) &
            (df['match_date'] < match_date)
        ].sort_values('match_date')

        if len(past_matches) > 0:
            # 计算主队胜率
            home_wins = past_matches[
                ((past_matches['home_team_id'] == home_id) &
                 (past_matches['home_score'] > past_matches['away_score'])) |
                ((past_matches['home_team_id'] == away_id) &
                 (past_matches['away_score'] > past_matches['home_score']))
            ]
            h2h_home_win_rate = len(home_wins) / len(past_matches)

            # 计算平均进球差
            goal_diffs = past_matches.apply(
                lambda x: x['home_score'] - x['away_score']
                if x['home_team_id'] == home_id
                else x['away_score'] - x['home_score']
            )
            h2h_avg_goal_diff = goal_diffs.mean()

            # 计算平均总进球
            total_goals = past_matches['home_score'] + past_matches['away_score']
            h2h_avg_total_goals = total_goals.mean()

            h2h_stats.append({
                'h2h_home_win_rate': h2h_home_win_rate,
                'h2h_avg_goal_diff': h2h_avg_goal_diff,
                'h2h_avg_total_goals': h2h_avg_total_goals,
                'h2h_matches_count': len(past_matches)
            })
        else:
            h2h_stats.append({
                'h2h_home_win_rate': 0.5,  # 默认值
                'h2h_avg_goal_diff': 0.0,
                'h2h_avg_total_goals': 2.5,  # 默认值
                'h2h_matches_count': 0
            })

    return pd.DataFrame(h2h_stats)
```

### 3. 联赛形态特征 (Season Form)

**问题**: 进球数噪音大，积分更能反映真实表现

#### 3.1 积分滚动统计
```python
def calculate_points(df):
    """计算比赛积分：胜3分，平1分，负0分"""
    points = []
    for _, match in df.iterrows():
        if match['home_score'] > match['away_score']:
            # 主队胜
            if match['home_team_id'] == match['favored_team_id']:
                points.append(3)  # 主队是热门队且获胜
            else:
                points.append(3)  # 主队获胜但不是热门
        elif match['home_score'] < match['away_score']:
            # 客队胜
            points.append(0)
        else:
            # 平局
            points.append(1)
    return df.assign(points=points)

# 应用积分计算
df = calculate_points(df)

# 积分滚动特征
df['home_team_points_rolling_3'] = (
    df.groupby('home_team_id')['points']
    .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))
)

df['home_team_points_rolling_5'] = (
    df.groupby('home_team_id')['points']
    .transform(lambda x: x.rolling(5, min_periods=1).mean().shift(1))
)
```

#### 3.2 主客场积分差异
```python
# 主队主场积分 - 客队客场积分
df['points_advantage_home_rolling_3'] = (
    df[df['venue'] == 'home']
    .groupby('home_team_id')['points']
    .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1)) -
    df[df['venue'] == 'away']
    .groupby('home_team_id')['points']
    .transform(lambda x: x.rolling(3, min_periods=1).mean().shift(1))
)
```

## 🏗️ 实现计划

### Phase 5.1: 高级特征转换器开发
1. **创建 `AdvancedFeatureTransformer` 类**
   - 继承或替换现有的 `RollingAverageTransformer`
   - 实现上述3类特征的生成逻辑
   - 确保与现有训练流水线兼容

### Phase 5.2: 数据预处理增强
1. **场馆信息推断**
   - 基于 `home_team_id` 和 `away_team_id` 推断比赛主场/客场
   - 确保特征计算的正确性

2. **时间窗口优化**
   - 根据比赛频率调整滚动窗口大小
   - 考虑季节性因素的影响

### Phase 5.3: 模型训练和评估
1. **使用新特征重新训练模型**
   - 比较新模型与基线模型的性能
   - 分析特征重要性的变化

2. **验证改进效果**
   - 特别关注 Napoli vs Juventus 案例的改进
   - 验证主客场偏见问题的解决

## 🧮 特征工程实现细节

### 数据结构要求
```python
# 输入数据必需字段
required_columns = [
    'home_team_id', 'away_team_id', 'home_score', 'away_score',
    'match_date', 'venue', 'favored_team_id', 'league_id'
]

# 新增特征字段
new_features = [
    'home_team_home_goals_rolling_3', 'home_team_home_goals_rolling_5',
    'away_team_away_goals_rolling_3', 'away_team_away_goals_rolling_5',
    'home_vs_away_goal_diff_rolling_3', 'home_vs_away_goal_diff_rolling_5',
    'h2h_home_win_rate', 'h2h_avg_goal_diff', 'h2h_avg_total_goals',
    'home_team_points_rolling_3', 'home_team_points_rolling_5',
    'points_advantage_home_rolling_3'
]
```

### 性能优化考虑
1. **向量化操作**: 使用 Pandas 的 `groupby` + `transform` 进行高效计算
2. **内存管理**: 避免重复计算和临时数据存储
3. **时间复杂度**: 确保特征计算的时间复杂度合理

### 防数据泄露机制
```python
# 严格的时间顺序处理
df = df.sort_values(['team_id', 'match_date'])

# 使用 shift(1) 确保特征不包含未来信息
df['rolling_feature'] = (
    df.groupby('team_id')['value']
    .transform(lambda x: x.rolling(window).mean().shift(1))
)
```

## 📊 预期性能提升

### 基于特征工程理论的改进

1. **主客场分离**
   - 解决 Napoli 案例中的主客场偏见
   - 预期准确率提升: **5-8%**

2. **历史交锋统计**
   - 捕捉"克星"效应和心理优势
   - 预期准确率提升: **3-5%**

3. **积分替代进球数**
   - 减少进球数的噪音影响
   - 预期准确率提升: **2-4%**

### 总体预期
- **目标准确率**: **65%+** (相比 58.69% 提升 6.3%+)
- **精确率提升**: 预期提升至 65%+
- **召回率提升**: 预期提升至 60%+
- **F1 分数提升**: 预期提升至 62%+

## 🎯 成功指标

### Phase 5 完成标准
1. **✅ 高级特征实现**: 完成3类核心特征的工程实现
2. **✅ 模型性能验证**: 新模型准确率达到 65%+
3. **✅ 问题修复验证**: Napoli vs Juventus 案例预测正确
4. **✅ 特征重要性分析**: 新特征在模型中占据重要位置
5. **✅ 生产集成**: 新特征工程流水线集成到预测服务

### 关键验证点
- ✅ Napoli 主场0进球问题得到解决
- ✅ 模型不再过度依赖单一球队ID特征
- ✅ 历史交锋特征对预测有明显贡献
- ✅ 特征计算性能满足实时预测需求

## 📁 文件结构规划

### 新增文件
```
src/ml/features/
├── advanced_feature_transformer.py    # 高级特征转换器
├── h2h_calculator.py                  # H2H统计计算
└── venue_analyzer.py                  # 场馆分析器

scripts/
├── train_phase5_advanced.py           # Phase 5 训练脚本
├── test_phase5_features.py          # 特征验证脚本
└── compare_phase4_vs_phase5.py       # 性能对比脚本

docs/
└── PHASE_5_DESIGN.md                # 本设计文档
└── PHASE_5_RESULTS.md               # (待创建)结果报告
```

## 🚀 实施路线图

```
Phase 5.1: 特征工程开发
├── 实现 AdvancedFeatureTransformer
├── 实现 H2H 统计计算
├── 实现积分滚动特征
└── 单元测试验证

Phase 5.2: 模型训练与验证
├── 使用新特征训练模型
├── 性能评估与对比
├── 特征重要性分析
└── 案例验证（Napoli vs Juventus）

Phase 5.3: 生产集成
├── 更新预测服务
├── 性能测试
├── 文档更新
└── 分支合并
```

## 🎉 Phase 5 设计完成

**高级特征工程设计已完成！**

通过引入主客场分离滚动统计、历史交锋记录和联赛形态特征，我们有信心将模型准确率从 58.69% 提升至 65%+，同时解决 Phase 4 中发现的关键问题。

**下一步**: 开始实施 Phase 5.1 特征工程开发阶段。

**🚀 准备好开始 Phase 5: Advanced Features 的实现！**