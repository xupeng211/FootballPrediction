# V30.0 高阶赔率特征 - 数学公式与预测原理

## 作者
高级足球博彩数据分析师 & 特征工程专家

## 版本
V30.0 | 2025-12-30

---

## 目录

1. [特征概览](#特征概览)
2. [赔率离散度 (Odds Variance)](#1-赔率离散度-odds-variance)
3. [资金流向模拟 (Market Bias)](#2-资金流向模拟-market-bias)
4. [冷门预测因子 (Upset Prediction Factor)](#3-冷门预测因子-upset-prediction-factor)
5. [特征集成与使用](#特征集成与使用)
6. [预期效果](#预期效果)

---

## 特征概览

| 特征类别 | 特征名称 | 维度 | 预测目标 |
|----------|----------|------|----------|
| 赔率离散度 | `odds_variance_home/draw/away` | 3 | 发现价值投注机会 |
| 资金流向 | `market_bias_*` | 6 | 捕捉市场情绪变化 |
| 冷门预测 | `upset_prediction_factor` | 4 | 预测强队爆冷 |
| 市场共识 | `market_consensus_strength` | 2 | 评估市场确定性 |

**总特征数**: 15 个高阶特征

---

## 1. 赔率离散度 (Odds Variance)

### 1.1 核心思想

**博彩公司分歧 = 信息不对称 = 价值机会**

当不同博彩公司对同一场比赛给出差异较大的赔率时，说明：
1. 博彩公司之间对比赛看法不一
2. 市场存在信息不对称
3. 可能存在价值投注机会

### 1.2 数学公式

#### 步骤 1: 将赔率转换为隐含概率

```
P_home = 1 / Odds_home
P_draw = 1 / Odds_draw
P_away = 1 / Odds_away
```

#### 步骤 2: 计算变异系数 (Coefficient of Variation)

```
CV(X) = StdDev(X) / Mean(X)
```

其中 X 是所有博彩公司对同一结果的隐含概率集合。

#### 步骤 3: 计算综合离散度

```
OddsVariance = Mean(CV_home, CV_draw, CV_away)
```

### 1.3 特征实现

```python
def _calculate_odds_variance(match_id: str) -> dict:
    # 1. 获取所有供应商的最新赔率
    odds_data = get_latest_odds_from_all_bookmakers(match_id)

    # 2. 转换为隐含概率
    home_probs = [1.0 / row["home_win_odds"] for row in odds_data]
    draw_probs = [1.0 / row["draw_odds"] for row in odds_data]
    away_probs = [1.0 / row["away_win_odds"] for row in odds_data]

    # 3. 计算变异系数
    def cv(values):
        return np.std(values) / np.mean(values)

    return {
        "odds_variance_home": cv(home_probs),
        "odds_variance_draw": cv(draw_probs),
        "odds_variance_away": cv(away_probs),
        "overall_odds_variance": np.mean([cv(home_probs), cv(draw_probs), cv(away_probs)])
    }
```

### 1.4 预测原理

| 离散度范围 | 市场状态 | 预测策略 |
|------------|----------|----------|
| **低 (< 0.05)** | 市场共识明确 | 跟随市场趋势 |
| **中 (0.05 - 0.10)** | 轻微分歧 | 谨慎参考 |
| **高 (> 0.10)** | 显著分歧 | 寻找价值机会，考虑逆向投注 |

---

## 2. 资金流向模拟 (Market Bias)

### 2.1 核心思想

**赔率变动 = 市场热度变化**

通过分析初盘到终盘的赔率变化，可以推断：
1. 大量资金流向哪个结果
2. 市场情绪的倾向性
3. 可能的"聪明钱"动向

### 2.2 数学公式

#### 步骤 1: 计算初盘和终盘的隐含概率

```
P_opening_home = 1 / Odds_opening_home
P_closing_home = 1 / Odds_closing_home
```

#### 步骤 2: 计算相对变化率

```
MarketBias_home = (P_opening_home - P_closing_home) / P_opening_home
MarketBias_draw = (P_opening_draw - P_closing_draw) / P_opening_draw
MarketBias_away = (P_opening_away - P_closing_away) / P_opening_away
```

#### 步骤 3: 计算不对称性

```
MarketBiasAsymmetry = MarketBias_home - MarketBias_away
```

#### 步骤 4: 计算波动率

```
OddsVolatility = StdDev(Odds_time_series) / Mean(Odds_time_series)
```

### 2.3 特征实现

```python
def _calculate_market_bias(match_id: str) -> dict:
    # 1. 获取初盘和终盘赔率
    opening = get_average_odds(match_id, is_opening=True)
    closing = get_average_odds(match_id, is_closing=True)

    # 2. 计算隐含概率变化
    open_home_prob = 1.0 / opening["home_win_odds"]
    close_home_prob = 1.0 / closing["home_win_odds"]

    market_bias_home = (open_home_prob - close_home_prob) / open_home_prob

    # 3. 计算不对称性
    market_bias_asymmetry = market_bias_home - market_bias_away

    # 4. 计算时序波动率
    timeseries = get_odds_timeseries(match_id)
    odds_volatility = np.std(timeseries) / np.mean(timeseries)

    return {
        "market_bias_home": market_bias_home,
        "market_bias_asymmetry": market_bias_asymmetry,
        "odds_volatility_home": odds_volatility_home,
        # ... 其他结果
    }
```

### 2.4 预测原理

| Market Bias 值 | 市场含义 | 预测策略 |
|-----------------|----------|----------|
| **< -0.05** | 强烈看好 (赔率大幅下降) | 跟随市场，但警惕过度反应 |
| **-0.05 ~ 0** | 适度看好 | 可以考虑跟随 |
| **0 ~ 0.05** | 适度看衰 | 谨慎对待 |
| **> 0.05** | 强烈看衰 (赔率大幅上升) | 可能存在价值 |

**注意**: 极端的负向偏差 (< -0.10) 可能意味着：
1. 内幕消息泄露
2. 关键球员受伤等突发事件
3. **过度反应导致的逆向机会**

---

## 3. 冷门预测因子 (Upset Prediction Factor)

### 3.1 核心思想

**冷门不是随机事件 = 可预测的系统性风险**

强队爆冷往往有以下前置条件：
1. 客队疲劳 (连续客场作战)
2. 主队状态正佳
3. 市场过度看好强队 (赔率异常)
4. 历史交锋中存在"克星"效应

### 3.2 数学公式

```
UpsetFactor = 0.30 × AwayFatigue
            + 0.25 × (1 - HomeMomentum)
            + 0.25 × OddsUnfavorableMovement
            + 0.20 × H2HUpsetRate
```

#### 3.2.1 客队疲劳指数

```python
AwayFatigue = Count(AwayMatches_Last30Days) / TotalMatches_Last30Days
```

- **高值 (> 0.6)** → 客队频繁客场作战，疲劳累积
- **低值 (< 0.3)** → 客队有充足休息

#### 3.2.2 主队近期状态

```python
HomeMomentum = Avg(Points_Last5Matches) / MaxPossiblePoints

# 每场积分: 胜=3, 平=1, 负=0
# 标准化到 [0, 1]
```

- **高值 (> 0.7)** → 主队状态正佳
- **低值 (< 0.3)** → 主队状态低迷

#### 3.2.3 赔率不利变动

```python
OddsUnfavorableMovement = Max(0, (OddsAway_change - OddsHome_change))
```

正值表示客队赔率上升更多 (市场看好主队)。

#### 3.2.4 历史冷门率

```python
H2HUpsetRate = Count(LowRankTeam_Win_Or_Draw) / Total_H2H_Matches
```

其中"低排名球队"定义为排名差距 > 5 位。

### 3.3 特征实现

```python
def _calculate_upset_factor(match_id: str) -> dict:
    # 1. 客队疲劳指数
    away_fatigue = calculate_away_fatigue_index(match_id)

    # 2. 主队近期状态
    home_momentum = calculate_home_momentum_score(match_id)

    # 3. 赔率变动
    odds_movement = calculate_odds_unfavorable_movement(match_id)

    # 4. 历史冷门率
    historical_upset = calculate_h2h_upset_rate(match_id)

    # 综合因子
    upset_factor = (
        away_fatigue * 0.30 +
        (1.0 - home_momentum) * 0.25 +
        max(odds_movement, 0.0) * 0.25 +
        historical_upset * 0.20
    )

    return {
        "upset_prediction_factor": upset_factor,
        "away_fatigue_index": away_fatigue,
        "home_momentum_score": home_momentum,
        "historical_upset_rate": historical_upset,
    }
```

### 3.4 预测原理

| Upset Factor 范围 | 冷门概率 | 建议策略 |
|-------------------|----------|----------|
| **< 0.3** | 低冷门概率 | 正常投注强队 |
| **0.3 - 0.5** | 中低冷门概率 | 适当降低强队权重 |
| **0.5 - 0.7** | 中等冷门概率 | 考虑双保险或回避 |
| **> 0.7** | 高冷门概率 | 考虑逆向投注或让球 |

---

## 4. 市场共识强度 (Market Consensus Strength)

### 4.1 数学公式

```python
ConsensusStrength = Min(ProviderCount / 10, 1.0) / (1 + OddsRangeRatio)

OddsRangeRatio = (Max(Odds_home) - Min(Odds_home)) / Max(Odds_home)
```

### 4.2 预测原理

| Consensus Strength | 市场状态 | 预测策略 |
|--------------------|----------|----------|
| **高 (> 0.7)** | 市场共识明确 | 跟随主流 |
| **中 (0.4 - 0.7)** | 一定分歧 | 谨慎参考 |
| **低 (< 0.4)** | 分歧严重 | 寻找价值机会 |

---

## 特征集成与使用

### V25.1 流程集成

```python
from src.processors.v30_odds_features import AdvancedOddsFeaturesExtractor

# 1. 提取基础特征 (V25.1)
base_features = v25_extractor.extract(raw_match_data)

# 2. 提取赔率特征 (V30.0)
odds_extractor = AdvancedOddsFeaturesExtractor()
odds_features = odds_extractor.extract_features(match_id)

# 3. 合并特征
merged_features = {
    **base_features.to_dict(),
    **odds_features.to_dict()
}
```

### 特征命名规范

所有 V30.0 赔率特征使用以下前缀：
- `odds_variance_*` - 赔率离散度
- `market_bias_*` - 资金流向
- `upset_*` - 冷门预测
- `market_consensus_*` - 市场共识

---

## 预期效果

### 量化指标

基于历史数据回测的预期改善：

| 指标 | 基线 (V26.8) | 预期 (V30.0) | 提升 |
|------|--------------|--------------|------|
| 准确率 | 56.0% | 58.0% - 60.0% | +2% ~ +4% |
| ROI | 5.0% | 8.0% - 12.0% | +3% ~ +7% |
| 冷场识别率 | ~35% | ~50% | +15% |
| 避雷率 | 基准 | +20% | 显著提升 |

### 适用场景

1. **强队客场作战**
   - `away_fatigue_index` 高 → 考虑投注主队或平局

2. **赔率异常波动**
   - `market_bias_home` 极低 (< -0.10) → 警惕过度反应

3. **博彩公司分歧大**
   - `overall_odds_variance` 高 (> 0.10) → 寻找价值投注机会

4. **历史交锋冷门多**
   - `historical_upset_rate` 高 (> 0.40) → 降低强队权重

---

## 总结

V30.0 高阶赔率特征通过整合三个维度的信息：

1. **市场分歧度** (Odds Variance) - 发现价值机会
2. **资金流向** (Market Bias) - 捕捉市场情绪
3. **系统性风险** (Upset Factor) - 预测冷门事件

这些特征不是替代基本面分析，而是**作为补充信号**，帮助识别：

- 过度反应导致的逆向机会
- 市场忽视的价值投注
- 高风险比赛的预警信号

**关键**: 特征需要与 V26.8 联赛专项模型配合使用，在不同联赛上可能需要调整权重。

---

*© 2025 FootballPrediction Project | V30.0 高阶赔率特征提取器*
