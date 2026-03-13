# V35.0 建模模块技术文档

**版本**: V35.0 Production
**作者**: V35.0 Architecture Team
**日期**: 2025-12-28

---

## 目录

- [模块概述](#模块概述)
- [核心组件](#核心组件)
- [XGBoost + Platt Scaling 架构](#xgboost--platt-scaling-架构)
- [核心指标定义](#核心指标定义)
- [回测引擎](#回测引擎)
- [使用指南](#使用指南)
- [最佳实践](#最佳实践)

---

## 模块概述

V35.0 建模模块提供工业级机器学习流水线，整合了：

- **V35Trainer**: XGBoost 2.0+ 训练器 + Platt Scaling 概率校准
- **BacktestEngine**: 生产级回测引擎
- **ModelConfig**: 统一配置管理
- **TrainingMetrics**: 完整评估指标体系

**设计原则**:

- 时间序列分割（避免数据泄漏）
- 类别权重优化（提升平局识别）
- 概率校准（提高预测可靠性）
- 完整可观测性（日志 + 指标）

---

## 核心组件

### 1. V35Trainer

生产级训练器，支持完整的训练流程。

```python
from src.modeling import V35Trainer, create_trainer

# 创建训练器
trainer = create_trainer()

# 运行完整训练流程
report = trainer.run(data_path="path/to/data.parquet")

# 访问模型
model = trainer.model
calibrated_model = trainer.calibrated_model
```

### 2. BacktestEngine

回测引擎，用于验证模型的实战表现。

```python
from src.modeling import BacktestEngine, BacktestConfig

# 创建回测引擎
config = BacktestConfig(
    stake_per_bet=100.0,
    min_prob_threshold=0.55,
    max_prob_threshold=0.85,
)
engine = BacktestEngine(config)

# 运行回测
metrics = engine.run_backtest(df_test, y_pred, y_pred_proba)
```

### 3. ModelConfig

统一的模型配置管理。

```python
from src.modeling import ModelConfig

config = ModelConfig(
    xgb_params={
        "n_estimators": 500,
        "max_depth": 5,
        "learning_rate": 0.03,
        # ...
    },
    class_weights={0: 1.0, 1: 3.0, 2: 1.0},  # 强化平局学习
    train_size=0.8,
    calibration_method="sigmoid",  # Platt Scaling
)
```

---

## XGBoost + Platt Scaling 架构

### XGBoost 配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `n_estimators` | 500 | 树的数量 |
| `max_depth` | 5 | 树的最大深度 |
| `learning_rate` | 0.03 | 学习率（保守） |
| `min_child_weight` | 3 | 最小子节点权重 |
| `gamma` | 0.1 | 剪枝参数 |
| `subsample` | 0.8 | 行采样比例 |
| `colsample_bytree` | 0.8 | 列采样比例 |
| `reg_alpha` | 1.0 | L1 正则化 |
| `reg_lambda` | 2.0 | L2 正则化 |
| `tree_method` | "hist" | 直方图优化 |

### 类别权重优化

针对足球预测中平局难以识别的问题，使用加权策略：

```python
class_weights = {
    0: 1.0,   # 客胜（基础权重）
    1: 3.0,   # 平局（3倍权重强化）
    2: 1.0,   # 主胜（基础权重）
}
```

**原理**: 平局在自然分布中约占 25-30%，但模型往往容易忽视。3 倍权重强制模型更关注平局模式。

### Platt Scaling 概率校准

**目的**: 校准 XGBoost 输出的概率，使其更接近真实频率。

**公式** (Sigmoid 方法):

```
P calibrated = 1 / (1 + exp(-(A * z + B)))

其中:
- z = 原始模型输出的 log odds
- A, B = 通过交叉验证学习到的校准参数
```

**实现**:

```python
from sklearn.calibration import CalibratedClassifierCV

# 根据样本量自适应选择 cv 折数
if min_samples_per_class >= 5:
    cv_folds = 5
elif min_samples_per_class >= 3:
    cv_folds = 3
else:
    cv_folds = 2  # 最小值

calibrated_model = CalibratedClassifierCV(
    base_model,
    method="sigmoid",  # Platt Scaling
    cv=cv_folds,
)
calibrated_model.fit(X_test, y_test)
```

**效果**:

- 校准前：模型预测 70% 概率，实际命中可能只有 60%
- 校准后：模型预测 70% 概率，实际命中接近 70%

---

## 核心指标定义

### 分类性能指标

#### Accuracy (准确率)

```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
```

- **定义**: 正确预测的比例
- **目标**: ≥ 60%
- **基线**: 65.52% (V19.4.1)

#### AUC-ROC (曲线下面积)

```
AUC = ∫ TPR(FPR⁻¹) dFPR
```

- **定义**: ROC 曲线下的面积
- **范围**: 0.5 (随机) ~ 1.0 (完美)
- **目标**: ≥ 0.65
- **说明**: Macro 平均，OVR (One-vs-Rest) 方式

#### Log Loss (对数损失)

```
Log Loss = -Σ y_true * log(y_pred_proba) / N
```

- **定义**: 概率预测的对数损失
- **范围**: 0 ~ ∞ (越小越好)
- **目标**: ≤ 1.0
- **说明**: 对错误概率预测惩罚更重

#### Brier Score (布莱尔分数)

```
Brier = Σ (y_pred_proba - y_true)² / N
```

- **定义**: 概率预测的均方误差
- **范围**: 0 ~ 1 (越小越好)
- **目标**: ≤ 0.2

#### F1-Macro

```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

- **定义**: 精确率和召回率的调和平均
- **Macro**: 对所有类别求平均（忽略类别不平衡）
- **目标**: ≥ 0.50

### 分类别准确率

| 指标 | 说明 |
|------|------|
| `home_win_accuracy` | 主胜预测准确率 |
| `draw_accuracy` | 平局预测准确率 |
| `away_win_accuracy` | 客胜预测准确率 |

**注意**: 由于类别权重强化，`draw_accuracy` 通常会高于自然分布。

### 回测指标

#### ROI (投资回报率)

```
ROI (%) = (Total Return - Total Stake) / Total Stake * 100
```

- **定义**: 净利润占总下注金额的百分比
- **目标**: ≥ 5% (优秀), ≥ 0% (盈利)
- **风控线**: ROI < -5% 时应暂停策略

#### Win Rate (胜率)

```
Win Rate (%) = Winning Bets / Total Bets * 100
```

- **定义**: 中奖下注占总下注的比例
- **目标**: ≥ 55%
- **注意**: 高胜率不一定高 ROI

#### Sharpe Ratio (夏普比率)

```
Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
```

- **定义**: 单位风险的超额收益
- **目标**: ≥ 1.0 (良好), ≥ 2.0 (优秀)
- **说明**: 简化版，假设无风险利率 = 0

#### Max Drawdown (最大回撤)

```
Drawdown = (Peak - Equity) / Peak * 100
```

- **定义**: 从峰值到谷底的最大跌幅
- **目标**: < 20%
- **风控线**: ≥ 25% 时应暂停策略

---

## 回测引擎

### 下注策略

1. **概率阈值过滤**
   - 最小概率: 0.55 (55%)
   - 最大概率: 0.85 (避免过拟合)
   - 低于/高于阈值时不进行下注

2. **赔率计算**

   ```
   隐含赔率 = 1 / (模型概率 * (1 - 利润率))
   ```

   - 利润率默认 5% (bookmaker margin)

3. **Kelly 准则 (可选)**

   ```
   f* = (b * p - q) / b

   其中:
   - b = 赔率 - 1
   - p = 胜率
   - q = 1 - p
   ```

   - 使用保守 Kelly (f/4) 限制最大下注

### 风险指标

| 指标 | 计算方式 | 风控阈值 |
|------|----------|----------|
| `total_bets` | 总下注次数 | - |
| `win_rate` | 胜率 | ≥ 55% |
| `roi_pct` | ROI% | ≥ 5% |
| `max_drawdown` | 最大回撤 | < 20% |
| `sharpe_ratio` | 夏普比率 | ≥ 1.0 |

---

## 使用指南

### 快速开始

```python
from src.modeling import create_trainer, create_backtest_engine
from src.data import create_feature_factory
import pandas as pd

# 1. 准备数据
df_matches = pd.read_csv("matches.csv")

# 2. 生成特征
factory = create_feature_factory()
df_features = factory.build_all_features(df_matches)

# 3. 训练模型
trainer = create_trainer()
report = trainer.run("path/to/features.parquet")

# 4. 预测
y_pred = trainer.model.predict(X_test)
y_pred_proba = trainer.calibrated_model.predict_proba(X_test)

# 5. 回测
engine = create_backtest_engine()
metrics = engine.run_backtest(df_test, y_pred, y_pred_proba)

print(f"ROI: {metrics.roi_pct:.2f}%")
print(f"Win Rate: {metrics.win_rate:.2f}%")
```

### 高级配置

```python
from src.modeling import V35Trainer, ModelConfig, BacktestConfig

# 自定义训练配置
config = ModelConfig(
    xgb_params={
        "n_estimators": 1000,  # 更多树
        "learning_rate": 0.01,  # 更小学习率
    },
    class_weights={0: 1.0, 1: 5.0, 2: 1.0},  # 更强平局权重
    train_size=0.75,  # 更多训练数据
)

trainer = V35Trainer(config=config)
report = trainer.run(data_path)

# 自定义回测配置
backtest_config = BacktestConfig(
    stake_per_bet=50.0,  # 降低单注金额
    min_prob_threshold=0.60,  # 更严格阈值
    KellyCriterion=True,  # 启用 Kelly
    KellyFraction=0.25,  # 保守 Kelly
)

engine = BacktestEngine(backtest_config)
```

---

## 最佳实践

### 1. 数据准备

- ✅ **时间排序**: 确保数据按 `match_date` 排序
- ✅ **特征对齐**: 所有比赛的特征维度必须一致
- ✅ **缺失值处理**: 使用 `fillna(0)` 填充缺失值
- ❌ **避免**: 随机分割（会导致数据泄漏）

### 2. 模型训练

- ✅ **使用校准模型**: 预测时使用 `calibrated_model` 而非 `model`
- ✅ **监控 AUC**: AUC 比 Accuracy 更能反映概率质量
- ✅ **关注 LogLoss**: 概率预测的准确性比单一分类更重要
- ❌ **避免**: 在测试集上训练校准模型

### 3. 回测验证

- ✅ **时间序列分割**: 训练集必须早于测试集
- ✅ **概率阈值**: 设置合理的 min/max 概率阈值
- ✅ **风险监控**: 关注 max_drawdown 和 sharpe_ratio
- ❌ **避免**: 过度拟合历史数据

### 4. 生产部署

- ✅ **保存完整模型**: 使用 `save_model()` 保存模型和配置
- ✅ **版本控制**: 记录模型版本和训练数据时间戳
- ✅ **A/B 测试**: 新模型先与旧模型并行运行
- ❌ **避免**: 直接替换生产模型（无灰度）

---

## 附录

### V35.0 特征列表

特征工厂生成 21 维特征向量：

| 类别 | 特征 | 说明 |
|------|------|------|
| **ELO** | `home_elo_pre`, `away_elo_pre`, `elo_gap_pre` | ELO 评分和差距 |
| **积分榜** | `home_points_pre`, `away_points_pre`, `points_diff_pre` | 赛前积分和差距 |
| **排名** | `home_rank_pre`, `away_rank_pre`, `rank_diff_pre` | 赛前排名和差距 |
| **疲劳度** | `home_rest_days_pre`, `away_rest_days_pre`, `rest_days_diff_pre` | 休息天数 |
| **效率** | `home_scoring_efficiency`, `away_scoring_efficiency` | 进球效率 (G/xG) |
| **效率** | `home_save_efficiency`, `away_save_efficiency` | 门将效率 (xG/GA) |
| **动量** | `home_form_momentum`, `away_form_momentum`, `momentum_diff` | 近期状态 |

### 混淆矩阵示例

```
              预测 Away    预测 Draw    预测 Home
  实际 Away         15            5           2
  实际 Draw          3           10           8
  实际 Home          2            7          20
```

**解读**:

- 主胜识别最准确 (20/29 = 69%)
- 平局识别中等 (10/21 = 48%)，受权重强化影响
- 客胜识别良好 (15/22 = 68%)

---

**版本历史**:

- V35.0 (2025-12-28): 初始生产版本
- 后续版本将支持 LightGBM 集成

**维护者**: V35.0 Architecture Team
**许可证**: 内部使用
