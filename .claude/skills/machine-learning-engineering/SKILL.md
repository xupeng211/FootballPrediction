---
name: machine-learning-engineering
description: Optimize and maintain XGBoost machine learning models for football predictions. Use when tuning hyperparameters, implementing feature engineering, analyzing model performance, or deploying ML models to production.
---

# Machine Learning Engineering Skill

## 技能概述
专业的机器学习工程技能模块，专注于模型优化、特征工程和模型部署的最佳实践。

## 核心能力
- **模型优化**: XGBoost 2.0+ 超参数调优、模型融合、性能提升
- **特征工程**: 高级特征选择、特征变换、特征重要性分析
- **模型解释**: SHAP分析、特征贡献度、可解释性可视化
- **模型评估**: 交叉验证、性能指标计算、模型比较
- **部署优化**: 模型压缩、推理加速、内存优化

## 当前应用场景：足球赛果预测系统
- **目标**: 提升模型准确率（当前 V19.4.1 基线：65.52%）
- **模型**: XGBoost 2.0+ classifier
- **当前特征**: 48 维生产特征（V25.1 自适应引擎可扩展至 12061 维）
- **响应时间目标**: <100ms
- **数据量**: 13,129+ 场历史比赛数据

## 工具和库
- **XGBoost 2.0+**: 高性能梯度提升框架
- **SHAP 0.50+**: 模型解释性分析
- **scikit-learn**: 模型评估和特征选择
- **pandas/numpy**: 数据处理和分析
- **optuna**: 超参数优化
- **mlflow**: 实验跟踪和模型版本管理

## 快速开始（第一层）
```python
# 模型快速优化示例
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score

# 基础优化配置
params = {
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 100,
    'subsample': 0.8,
    'colsample_bytree': 0.8
}

model = XGBClassifier(**params)
scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
```

## 深入优化（第二层）
```python
# 高级超参数优化
import optuna
from sklearn.metrics import accuracy_score

def objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_loguniform('learning_rate', 0.01, 0.3),
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'subsample': trial.suggest_uniform('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_uniform('colsample_bytree', 0.6, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10)
    }

    model = XGBClassifier(**params)
    model.fit(X_train, y_train)
    predictions = model.predict(X_val)
    return accuracy_score(y_val, predictions)

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100)
```

## 高级应用（第三层）
```python
# 模型融合和集成
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

# 创建异构集成
xgb_model = XGBClassifier(**study.best_params)
rf_model = RandomForestClassifier(n_estimators=200)
lr_model = LogisticRegression()

ensemble_model = VotingClassifier(
    estimators=[
        ('xgb', xgb_model),
        ('rf', rf_model),
        ('lr', lr_model)
    ],
    voting='soft'
)
```

## 特征工程最佳实践
1. **特征选择**: 使用互信息和特征重要性排序
2. **特征变换**: 标准化、归一化、对数变换
3. **特征创建**: 交互特征、多项式特征
4. **特征评估**: 递归特征消除(RFE)、稳定性分析

## 模型解释性分析
```python
import shap

# SHAP分析
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# 可视化特征重要性
shap.summary_plot(shap_values, X_test)
shap.dependence_plot("feature_name", shap_values, X_test)
```

## 性能优化策略
1. **内存优化**: 使用`max_bin`参数减少内存使用
2. **推理加速**: 使用`tree_method='hist'`或'gpu_hist'
3. **并行化**: 设置`n_jobs=-1`利用多核CPU
4. **模型压缩**: 使用early_stopping和剪枝

## 常见问题解决
- **过拟合**: 增加正则化参数(lambda, alpha)
- **欠拟合**: 增加模型复杂度(max_depth, n_estimators)
- **训练速度慢**: 使用近似算法或GPU加速
- **预测延迟**: 模型蒸馏或使用更小的模型

## 实验跟踪
```python
import mlflow
import mlflow.xgboost

with mlflow.start_run():
    # 记录参数
    mlflow.log_params(params)

    # 训练模型
    model.fit(X_train, y_train)

    # 记录指标
    mlflow.log_metric("accuracy", accuracy)

    # 保存模型
    mlflow.xgboost.log_model(model, "model")
```

## 超参数优化配置
```yaml
optuna_config:
  n_trials: 200
  timeout: 3600
  direction: maximize
  sampler:
    type: TPE
  pruner:
    type: Median
    n_startup_trials: 10

param_space:
  max_depth: [3, 10]
  learning_rate: [0.01, 0.3]
  n_estimators: [50, 500]
  subsample: [0.6, 1.0]
  colsample_bytree: [0.6, 1.0]
  min_child_weight: [1, 10]
  gamma: [0, 5]
  reg_alpha: [0, 1]
  reg_lambda: [0, 1]
```

## 性能基准测试
- **训练时间**: < 5分钟 (10万样本)
- **预测延迟**: < 10ms (单样本)
- **模型大小**: < 100MB
- **内存使用**: < 1GB

## 集成部署建议
1. **模型版本控制**: 使用Git LFS或DVC
2. **自动化流水线**: MLflow + GitHub Actions
3. **容器化部署**: Docker + Kubernetes
4. **监控告警**: Prometheus + Grafana

## 相关技能
- `feature-engineering`: 特征工程专项（V25.1 自适应引擎）
- `football-prediction`: 足球预测系统
- `v26-harvest`: V26.1 收割流水线
- `data-engineering`: 数据管道工程

---
*Last updated: 2025-12-28*
*Target: 足球赛果预测系统优化*