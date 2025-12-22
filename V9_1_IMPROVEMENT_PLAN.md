# FootballPrediction V9.1 技术改进计划

## 🎯 目标

将 V9.0 的 -32.58% ROI 提升到 **+15-20% ROI**，解决概率校准问题。

---

## 📋 问题清单 (基于 V9.0 真实回测)

### 🚨 严重问题
1. **概率校准失败** - Brier Score: 0.5535 (目标: <0.20)
2. **模型过度自信** - 高概率交易胜率仅 15.2%
3. **Edge 计算错误** - 使用隐含概率而非真实概率
4. **特征维度不足** - 仅 15 维，可能欠拟合

### ⚠️ 中等问题
1. **数据量不足** - 134 场比赛 (建议: >500 场)
2. **缺少概率校准层** - 无温度缩放或 Platt Scaling
3. **风险参数过严** - 8% 最小边缘可能过滤掉好机会

---

## 🛠️ 技术改进方案

### Phase 1: 概率校准 (Priority: CRITICAL)

#### 1.1 实施 Platt Scaling
```python
# 在模型输出后添加校准层
from sklearn.calibration import CalibratedClassifierCV

# 使用 Platt Scaling 校准概率
calibrated_model = CalibratedClassifierCV(base_model, method='sigmoid', cv=5)
calibrated_model.fit(X_val, y_val)

# 校准后的概率
calibrated_probs = calibrated_model.predict_proba(X_test)[:, 1]
```

**预期改进**: Brier Score 0.5535 → 0.25-0.30

#### 1.2 修正 Edge 计算
```python
def calculate_true_edge(our_prob: float, market_odds: float, margin_rate: float = 0.045) -> float:
    """
    修正的 Edge 计算
    1. 从市场赔率中移除庄家抽水
    2. 计算真实的 fair probability
    3. 与我们的概率比较
    """
    # 移除抽水 (4.5%)
    fair_prob = 1 / (market_odds * (1 - margin_rate))
    
    # Edge = 我们的概率 - 真实概率
    edge = our_prob - fair_prob
    
    return edge
```

**预期改进**: 减少高估的 Edge，筛选更优质机会

#### 1.3 温度缩放 (Temperature Scaling)
```python
class TemperatureScaler:
    def __init__(self):
        self.temperature = 1.0
    
    def fit(self, logits, labels):
        # 优化温度参数
        from scipy.optimize import minimize
        
        def loss(T):
            scaled_probs = 1 / (1 + np.exp(-logits / T))
            return torch.nn.functional.binary_cross_entropy(scaled_probs, labels)
        
        result = minimize(loss, [1.0])
        self.temperature = result.x[0]
    
    def predict(self, logits):
        return 1 / (1 + np.exp(-logits / self.temperature))
```

### Phase 2: 特征工程增强 (Priority: HIGH)

#### 2.1 扩展到 50 维特征
```python
FEATURE_SET_V91 = {
    # 基础统计 (15 维) - 保持
    'basic_stats': [
        'home_avg_xg', 'away_avg_xg', 'home_avg_goals', 'away_avg_goals',
        'home_avg_shots', 'away_avg_shots', 'home_avg_possession', 'away_avg_possession',
        'home_avg_rating', 'away_avg_rating', 'home_win_rate', 'away_win_rate',
        'xg_diff', 'rating_diff', 'form_diff'
    ],
    
    # 高级统计 (15 维)
    'advanced_stats': [
        'home_xg_per_shot', 'away_xg_per_shot',
        'home_shot_accuracy', 'away_shot_accuracy',
        'home_pass_accuracy', 'away_pass_accuracy',
        'home_aerial_duels_won', 'away_aerial_duels_won',
        'home_tackles_won', 'away_tackles_won',
        'home_interceptions', 'away_interceptions',
        'home_clean_sheets', 'away_clean_sheets',
        'home_conceded_goals', 'away_conceded_goals'
    ],
    
    # 市场特征 (10 维)
    'market_features': [
        'home_odds', 'draw_odds', 'away_odds',
        'odds_movement_home', 'odds_movement_draw', 'odds_movement_away',
        'market_consensus_home', 'market_consensus_draw', 'market_consensus_away',
        'odds_volatility'
    ],
    
    # 上下文特征 (10 维)
    'context_features': [
        'rest_days_home', 'rest_days_away',
        'home_form_last_5', 'away_form_last_5',
        'home_head_to_head', 'away_head_to_head',
        'home Motivation_factor', 'away_motivation_factor',
        'referee_bias_home', 'referee_bias_away'
    ]
}
```

#### 2.2 添加时间序列特征
```python
def add_time_series_features(df):
    """添加时间序列特征"""
    # 滚动统计 (5 场窗口)
    for team in ['home', 'away']:
        df[f'{team}_rolling_xg_5'] = df.groupby(f'{team}_team')['avg_xg'].transform(
            lambda x: x.rolling(5, min_periods=1).mean()
        )
        df[f'{team}_rolling_goals_5'] = df.groupby(f'{team}_team')['avg_goals'].transform(
            lambda x: x.rolling(5, min_periods=1).mean()
        )
    
    # 趋势特征
    df['home_xg_trend'] = df['home_rolling_xg_5'] - df['home_rolling_xg_5'].shift(5)
    df['away_xg_trend'] = df['away_rolling_xg_5'] - df['away_rolling_xg_5'].shift(5)
    
    return df
```

### Phase 3: 模型架构升级 (Priority: MEDIUM)

#### 3.1 集成学习 (Ensemble)
```python
from sklearn.ensemble import VotingClassifier
import lightgbm as lgb
import xgboost as xgb
from sklearn.neural_network import MLPClassifier

# 创建集成模型
lgb_model = lgb.LGBMClassifier(**lgb_params)
xgb_model = xgb.XGBClassifier(**xgb_params)
mlp_model = MLPClassifier(**mlp_params)

ensemble = VotingClassifier(
    estimators=[
        ('lightgbm', lgb_model),
        ('xgboost', xgb_model),
        ('mlp', mlp_model)
    ],
    voting='soft'  # 软投票，使用概率
)
```

#### 3.2 贝叶斯优化超参数
```python
from optuna import create_study

def objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'num_leaves': trial.suggest_int('num_leaves', 10, 300),
    }
    
    model = lgb.LGBMClassifier(**params)
    score = cross_val_score(model, X, y, cv=5, scoring='neg_brier_score').mean()
    return score

study = create_study(direction='maximize')
study.optimize(objective, n_trials=100)
```

### Phase 4: 数据增强 (Priority: MEDIUM)

#### 4.1 扩大数据集
- **目标**: 收集 500+ 场比赛
- **数据源**: 
  - 英超 22/23, 23/24, 24/25 赛季
  - 西甲、德甲、意甲数据
  - 历史赔率数据

#### 4.2 数据质量验证
```python
def validate_data_quality(df):
    """数据质量检查"""
    checks = {
        'missing_values': df.isnull().sum(),
        'duplicate_matches': df.duplicated(['home_team', 'away_team', 'date']).sum(),
        'invalid_odds': (df[['home_odds', 'draw_odds', 'away_odds']] < 1.0).sum(),
        'probability_sum': (df[['home_prob', 'draw_prob', 'away_prob']].sum(axis=1) - 1).abs().mean()
    }
    return checks
```

---

## 📊 预期改进指标

### 校准指标
| 指标 | V9.0 | V9.1 目标 | 改进幅度 |
|------|------|----------|----------|
| **Brier Score** | 0.5535 | <0.25 | -55% |
| **胜率** | 23.21% | 45-50% | +100% |
| **概率校准误差** | 50.63% | <15% | -70% |
| **高概率胜率** | 15.2% | 60-70% | +300% |

### 交易指标
| 指标 | V9.0 | V9.1 目标 | 改进幅度 |
|------|------|----------|----------|
| **ROI** | -32.58% | +15-20% | +47% |
| **最大回撤** | 58.53% | <25% | -57% |
| **胜出次数** | 26/112 | 50/112 | +92% |
| **交易质量** | 低 | 高 | 显著 |

---

## 🗓️ 实施时间表

### Week 1-2: 概率校准
- [ ] 实施 Platt Scaling
- [ ] 修正 Edge 计算
- [ ] 添加温度缩放
- [ ] 回测验证

### Week 3-4: 特征工程
- [ ] 扩展到 50 维特征
- [ ] 添加时间序列特征
- [ ] 实现市场特征
- [ ] 重新训练模型

### Week 5-6: 模型优化
- [ ] 集成学习
- [ ] 贝叶斯优化
- [ ] 超参数调优
- [ ] 交叉验证

### Week 7-8: 数据与验证
- [ ] 扩大数据集
- [ ] 数据质量验证
- [ ] 真实赔率回测
- [ ] 性能评估

---

## 💰 ROI 预测

基于改进方案，我们预期：

**保守估计**:
- ROI: +15%
- 胜率: 45%
- 最大回撤: 25%

**乐观估计**:
- ROI: +20%
- 胜率: 50%
- 最大回撤: 20%

**关键成功因素**:
1. 概率校准成功 (Brier Score < 0.25)
2. 特征工程有效 (50 维特征)
3. 数据质量保证 (500+ 场比赛)

---

## 🚀 立即行动项

1. **今天**: 开始实施 Platt Scaling
2. **明天**: 修正 Edge 计算方法
3. **本周**: 扩展特征工程到 30 维
4. **下周**: 收集更多历史数据

**目标**: 在 4 周内将 ROI 从 -32.58% 提升到 +15%

---

**文档版本**: V9.1 Improvement Plan  
**创建日期**: 2025-12-22  
**预计完成**: 2026-01-19  
**负责人**: FootballPrediction Dev Team
