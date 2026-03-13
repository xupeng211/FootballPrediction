# XGBoost 2.0+ 模型优化指南

## 概述

本指南详细说明了针对FootballPrediction项目的XGBoost 2.0+模型优化策略，目标是将10-Fold交叉验证准确率从当前水平提升至58%以上。

## 当前状况分析

### 数据特征

- **样本数量**: 517场真实比赛数据
- **特征维度**: 180+维（原始83列，经过特征工程扩展）
- **特征类别**:
  - xG相关特征（Expected Goals）
  - 控球率特征
  - 射门相关特征
  - 角球数据
  - 红黄牌数据
  - 传球成功率
  - 球员评分（新增）
  - 战术风格特征（新增）

### 主要挑战

1. **高维特征 vs 有限样本**: 180+维特征 vs 517样本，容易过拟合
2. **平局预测偏差**: 平局类别天然难以预测，需要特殊处理
3. **特征相关性**: 多个特征可能高度相关，影响模型性能

## 优化策略详解

### 1. XGBoost 2.0+ 最优超参数配置

#### 核心参数调优

```python
config = XGBoostOptimizedConfig(
    # 树的数量和深度（平衡复杂度和过拟合）
    n_estimators=600,          # 增加树的数量捕获复杂模式
    max_depth=5,               # 控制深度防止过拟合（特征数/10）
    learning_rate=0.04,        # 较小的学习率配合更多树

    # 采样策略（防止过拟合）
    subsample=0.8,             # 行采样
    colsample_bytree=0.65,     # 列采样（特征维度高，降低采样率）
    colsample_bylevel=0.75,    # 每层列采样

    # 正则化（关键！）
    reg_alpha=0.15,            # L1正则化，特征选择
    reg_lambda=1.8,            # L2正则化，权重平滑
    gamma=0.15,                # 最小分裂增益
    min_child_weight=4,        # 增加最小子节点权重

    # XGBoost 2.0+新特性
    max_bin=200,               # 减少分箱数防止过拟合
    grow_policy="lossguide",   # 按损失增长分裂，更智能

    # 早停策略
    early_stopping_rounds=100,
    eval_metric="mlogloss",
)
```

#### 参数选择原理

1. **n_estimators=600**: 样本量适中，可以承受更多树来捕获复杂模式
2. **max_depth=5**: 深度控制在特征数的1/10左右，防止过拟合
3. **learning_rate=0.04**: 较小的学习率确保收敛稳定
4. **colsample_bytree=0.65**: 特征维度高，需要更激进的列采样
5. **正则化组合**: L1和L2正则化结合，兼顾特征选择和权重平滑

### 2. 类别权重平衡策略

#### 问题分析

平局（Label=1）天然难以预测，因为：

- 平局通常由细微差别决定
- xG、控球率等指标在平局比赛中差异较小
- 传统方法倾向于预测胜负

#### 解决方案

```python
# 1. 计算平衡权重
class_weights = ClassWeightCalculator.calculate_balanced_weights(y)
# 输出示例: {0: 0.95, 1: 1.44, 2: 0.95}

# 2. 给平局类别额外20%权重
if 1 in class_weights:
    class_weights[1] *= 1.2

# 3. 转换为样本权重
sample_weights = np.array([class_weights[cls] for cls in y.values])
```

#### 替代方案：Focal Loss

```python
# 对于极端不平衡情况
sample_weights = ClassWeightCalculator.get_focal_loss_weights(
    y, alpha=0.25, gamma=2.0
)
```

### 3. 特征选择和正则化方案

#### 混合特征选择策略

```python
# 第一步：基于统计的初筛（SelectKBest + F-test）
selector_kbest = SelectKBest(
    score_func=f_classif,
    k=min(200, X.shape[1])
)

# 第二步：基于模型的递归消除（RFE）
rfe = RFE(
    estimator=XGBClassifier(n_estimators=200, max_depth=4),
    n_features_to_select=120,  # 目标特征数
    step=0.1  # 每次移除10%的特征
)
```

#### 特征选择理由

1. **降维**: 从180+降到120维，减少过拟合风险
2. **去噪**: 移除不相关和冗余特征
3. **提升效率**: 减少训练时间和预测时间

#### 特征类别分布建议

- xG相关: 30-40% (最重要)
- 控球相关: 15-20%
- 射门相关: 15-20%
- 战术特征: 10-15%
- 其他: 10-20%

### 4. 10-Fold交叉验证设计

#### 分层交叉验证

```python
skf = StratifiedKFold(
    n_splits=10,
    shuffle=True,
    random_state=42
)
```

#### 每折训练策略

1. **早停机制**: 使用验证集监控，防止过拟合
2. **类别权重**: 每折使用相同的权重计算
3. **特征选择**: 在训练集上进行，避免数据泄露
4. **性能监控**: 记录准确率和LogLoss

## 代码实现

### 1. 快速开始

```bash
# 运行优化训练
python src/ml/training/train_optimized_model_v2.py
```

### 2. 自定义配置

```python
from src.ml.training.xgboost_optimized_config_v2 import (
    OptimizedModelTrainer,
    XGBoostOptimizedConfig
)

# 创建自定义配置
config = XGBoostOptimizedConfig(
    n_estimators=800,
    max_depth=6,
    learning_rate=0.03
)

# 训练模型
trainer = OptimizedModelTrainer(config)
results = trainer.train_with_cv(X, y, cv_folds=10)
```

### 3. 模型保存和加载

```python
# 保存
trainer.save_model('my_optimized_model.joblib')

# 加载
trainer = OptimizedModelTrainer()
trainer.load_model('my_optimized_model.joblib')
```

## 性能监控

### 关键指标

1. **10-Fold CV准确率**: 目标 ≥ 58%
2. **CV标准差**: 目标 ≤ 0.05（稳定性）
3. **LogLoss**: 目标 ≤ 1.0
4. **各类别F1-score**: 目标 ≥ 0.50

### 深度分析

1. **特征重要性**: 监控xG特征占比
2. **混淆矩阵**: 检查平局预测效果
3. **学习曲线**: 分析偏差-方差权衡

## 故障排除

### 常见问题

#### 1. 过拟合

- **症状**: CV准确率高但标准差大
- **解决**: 增加正则化、减少特征、降低树深度

#### 2. 平局预测差

- **症状**: 平局类别召回率低
- **解决**: 增加平局权重、创建平局特定特征

#### 3. 训练慢

- **症状**: 单折训练时间过长
- **解决**: 减少特征数、降低max_bin、使用GPU

### 调优建议

#### 逐步调优流程

1. **基础配置**: 使用默认参数建立基线
2. **正则化调优**: 优先调整reg_alpha和reg_lambda
3. **采样调优**: 调整subsample和colsample_bytree
4. **权重调优**: 微调类别权重比例
5. **特征调优**: 调整特征选择数量

## 进阶优化

### 1. 集成学习

```python
# 多模型融合
from sklearn.ensemble import VotingClassifier

models = [
    ('xgb1', XGBClassifier(**config1)),
    ('xgb2', XGBClassifier(**config2)),
    ('xgb3', XGBClassifier(**config3))
]

ensemble = VotingClassifier(models, voting='soft')
```

### 2. 贝叶斯优化

```python
from hyperopt import fmin, tpe, hp

# 定义搜索空间
space = {
    'n_estimators': hp.quniform('n_estimators', 400, 1000, 50),
    'max_depth': hp.quniform('max_depth', 3, 8, 1),
    'learning_rate': hp.loguniform('learning_rate', -5, -2)
}
```

### 3. 自动特征工程

```python
# 使用FeatureTools自动生成特征
import featuretools as ft

# 自动生成衍生特征
feature_matrix, feature_defs = ft.dfs(
    entityset=es,
    target_entity='matches',
    max_depth=2
)
```

## 预期效果

### 优化前后对比

| 指标 | 优化前 | 优化后（预期） |
|-----|--------|----------------|
| 10-Fold CV准确率 | ~55% | ≥58% |
| 平局召回率 | ~30% | ≥45% |
| CV标准差 | ~0.06 | ≤0.05 |
| 训练时间 | 基准 | +20% |
| 预测时间 | 基准 | -15% |

### 业务价值

1. **提升预测准确性**: 58%的准确率带来更好的投注决策
2. **改善平局预测**: 解决传统模型的平局盲区
3. **稳定性能**: 更低的方差确保模型可靠性

## 总结

通过实施本优化指南中的策略，期望能够：

1. 将10-Fold CV准确率提升至58%以上
2. 显著改善平局预测能力
3. 保持模型的稳定性和泛化能力
4. 建立可复现的训练流程

记住，机器学习优化是一个迭代过程，需要持续监控和调整。建议定期重新评估模型性能并根据新数据更新配置。
