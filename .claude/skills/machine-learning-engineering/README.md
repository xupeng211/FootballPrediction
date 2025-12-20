# Machine Learning Engineering Skill

## 📋 概述

这是一个专门为足球赛果预测系统设计的机器学习工程技能模块，提供全面的模型优化、特征工程和实验跟踪能力。

## 🎯 目标

- **提升模型准确率**: 从当前 58.69% 提升到 65%+
- **优化推理性能**: 达到 <100ms 响应时间
- **自动化流程**: 减少手动调参和特征工程工作量
- **模型解释性**: 提供SHAP分析和特征重要性
- **实验跟踪**: 使用MLflow记录所有实验

## 📁 文件结构

```
machine-learning-engineering/
├── SKILL.md                    # 技能定义和文档
├── README.md                   # 使用说明
├── scripts/
│   ├── xgboost_optimizer.py   # XGBoost模型优化器
│   └── feature_engineering_analyzer.py  # 特征工程分析器
├── templates/
│   └── model_training_pipeline.py       # 模型训练流水线模板
├── examples/
│   └── integration_example.py  # 集成到现有系统的示例
└── docs/
```

## 🚀 快速开始

### 1. 基础模型优化

```python
from scripts.xgboost_optimizer import FootballPredictionOptimizer

# 创建优化器
optimizer = FootballPredictionOptimizer(target_accuracy=0.65)

# 加载数据 (X_train, y_train, X_val, y_val)
best_params, best_score = optimizer.optimize_hyperparameters(
    X_train, y_train, X_val, y_val, n_trials=100
)

# 训练最终模型
model, accuracy = optimizer.train_final_model(X_train, y_train, X_val, y_val)
```

### 2. 特征工程分析

```python
from scripts.feature_engineering_analyzer import FootballFeatureAnalyzer

# 创建分析器
analyzer = FootballFeatureAnalyzer()

# 分析特征质量
results = analyzer.analyze_feature_quality(df, target_col='target')

# 获取优化建议
suggestions = analyzer.suggest_feature_engineering(results)

# 应用特征选择
X_selected, features = analyzer.optimize_features(X, y, k=20)
```

### 3. 完整流水线

```python
from templates.model_training_pipeline import FootballModelPipeline

# 创建流水线
pipeline = FootballModelPipeline(target_accuracy=0.65, target_latency_ms=100.0)

# 运行完整训练流程
model, results = pipeline.run_full_pipeline(
    data_path='your_data.csv',
    target_col='target'
)
```

## 🔧 集成到现有系统

### 方法1: 使用集成示例

```bash
cd .claude/skills/machine-learning-engineering
python examples/integration_example.py
```

### 方法2: 手动集成

1. **优化现有模型参数**:
```python
# 在 src/ml/models/xgboost_classifier.py 中应用优化参数
optimized_params = {
    'max_depth': 8,
    'learning_rate': 0.05,
    'n_estimators': 300,
    'subsample': 0.85,
    'colsample_bytree': 0.85,
    'min_child_weight': 3,
    'gamma': 0.1,
    'reg_alpha': 0.1,
    'reg_lambda': 0.9
}
```

2. **增强特征工程**:
```python
# 在 src/ml/features/advanced_feature_transformer.py 中添加
from scripts.feature_engineering_analyzer import FootballFeatureAnalyzer

def enhanced_feature_engineering(self, df):
    analyzer = FootballFeatureAnalyzer()

    # 分析现有特征
    analysis = analyzer.analyze_feature_quality(df)

    # 应用建议
    suggestions = analyzer.suggest_feature_engineering(analysis)

    # 创建新特征
    df_enhanced = analyzer.create_new_features(df)

    return df_enhanced
```

## 📊 性能基准

### 当前系统 vs 优化后系统

| 指标 | 当前系统 | 优化后系统 | 改进 |
|------|----------|------------|------|
| 模型准确率 | 58.69% | 65%+ | +6.31% |
| 推理延迟 | ~150ms | <100ms | -33% |
| 特征数量 | 12 | 20+ (优化选择) | +66% |
| 超参数优化 | 手动 | 自动化 | 100% |
| 模型解释性 | 基础 | SHAP分析 | 完整 |
| 实验跟踪 | 无 | MLflow | 完整 |

## 🛠️ 依赖项

```bash
pip install optuna xgboost scikit-learn shap mlflow pandas numpy matplotlib seaborn
```

## 📈 使用案例

### 案例1: 超参数优化

```python
# 快速优化 (30次试验)
best_params, score = optimizer.optimize_hyperparameters(
    X_train, y_train, X_val, y_val, n_trials=30
)

# 深度优化 (200次试验)
best_params, score = optimizer.optimize_hyperparameters(
    X_train, y_train, X_val, y_val, n_trials=200
)
```

### 案例2: 特征重要性分析

```python
# SHAP分析
shap_values = optimizer.analyze_with_shap(model, X_sample)

# 查看特征重要性
print(optimizer.feature_importance.head(10))
```

### 案例3: 性能验证

```python
# 延迟测试
latency_ms = optimizer.check_inference_latency(model, X_test, n_runs=1000)

# 全面评估
results = optimizer.evaluate_performance(model, X_test, y_test)
```

## 🔍 监控和日志

### MLflow集成

所有实验都会自动记录到MLflow：

- **参数**: 所有超参数配置
- **指标**: 准确率、延迟、损失等
- **模型**: 训练好的模型文件
- **图表**: SHAP图、混淆矩阵等

```bash
# 启动MLflow UI
mlflow ui
# 访问 http://localhost:5000
```

### 性能监控

```python
# 实时监控指标
with mlflow.start_run():
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("latency_ms", latency_ms)
    mlflow.log_metric("feature_count", len(features))
```

## 🚨 注意事项

1. **数据质量**: 确保输入数据无缺失值和异常值
2. **计算资源**: 超参数优化需要较多计算时间
3. **内存使用**: 大数据集建议使用分批处理
4. **版本兼容**: 确保XGBoost版本 >= 2.0

## 🆘 故障排除

### 常见问题

**Q: 优化过程中内存不足**
```python
# 减少试验次数或使用更小的数据集
best_params, score = optimizer.optimize_hyperparameters(
    X_train.sample(frac=0.5), y_train.sample(frac=0.5),
    X_val, y_val, n_trials=50
)
```

**Q: 模型过拟合**
```python
# 增加正则化
params = {
    'reg_alpha': 0.5,  # L1正则化
    'reg_lambda': 0.8,  # L2正则化
    'max_depth': 4      # 减少深度
}
```

**Q: 特征工程后性能下降**
```python
# 检查特征质量
analysis = analyzer.analyze_feature_quality(df_enhanced)
# 选择更保守的特征数量
X_selected, features = analyzer.optimize_features(X, y, k=15)
```

## 📚 扩展阅读

- [XGBoost官方文档](https://xgboost.readthedocs.io/)
- [Optuna超参数优化](https://optuna.org/)
- [SHAP模型解释](https://shap.readthedocs.io/)
- [MLflow实验跟踪](https://mlflow.org/)

## 🤝 贡献

欢迎提交改进建议和bug报告！

---

**最后更新**: 2025-12-18
**版本**: 1.0.0
**兼容系统**: 足球赛果预测系统 v2.0+