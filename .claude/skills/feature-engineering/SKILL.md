---
name: feature-engineering
description: Professional feature engineering for football prediction. Use when extracting features, selecting important features, transforming data, or implementing V25.1 adaptive extraction engine (48→12061 dimensions).
---

# 特征工程技能

## 技能概述
专业的特征工程技能模块，专注于足球预测系统的特征提取、选择、变换和优化。

## 核心能力
- **V25.1 自适应提取**: 零硬编码、递归打平、全量吞噬（48维→12061维）
- **特征选择**: 互信息、特征重要性、递归消除
- **特征变换**: 标准化、归一化、对数变换
- **特征创建**: 交互特征、多项式特征、滚动统计
- **特征对齐**: 跨比赛特征一致性、NaN 填充

## 当前版本特征体系
- **V25.1 自适应引擎**: 48维 → 12061维（251倍增长）
- **V17.0 滚动特征**: 16维基础特征
- **V18.0 赛前特征**: +8维积分榜特征
- **V19.0 高级特征**: +13维 ELO和疲劳度
- **V19.4 平局敏感度**: +3维平局预测

## V25.1 万能自适应特征提取引擎

### 核心突破
- **零硬编码**: 自动发现并提取所有数值型特征
- **递归打平**: 处理任意深度的嵌套 JSON 结构
- **全量吞噬**: 48维 → 12061维（251倍增长）
- **动态类型发现**: 自动转换 int/float/百分比/布尔值
- **特征对齐**: NaN 填充确保特征矩阵一致性
- **命名规范**: 路径式命名保证唯一性和可读性

### 核心文件
- `src/processors/v25_production_extractor.py` - V25.1 自适应提取器
- `src/processors/base_extractor.py` - 基础提取器抽象类
- `src/processors/exceptions.py` - 异常定义

### 使用方式
```bash
# L2 特征解析（使用 V25.1 自适应引擎）
python main_production.py l2-parse --extractor-version V25.1

# 批量处理
python main_production.py l2-parse --batch --limit 50

# 单场比赛
python main_production.py l2-parse --match-id 123456

# 跳过验证
python main_production.py l2-parse --batch --skip-validation

# 输出特征
python main_production.py l2-parse --match-id 123456 --output-features
```

### 提取器注册
```python
from src.processors import ExtractorRegistry

# 创建指定版本的提取器
extractor = ExtractorRegistry.create("V25.1")

# 列出可用版本
versions = ExtractorRegistry.list_versions()
# ['V25.1', 'V24.0', 'V23.0']
```

## 特征层级体系

### V17.0 滚动特征（16维）
主队/客队各 8 维:
- `rolling_xg`, `rolling_xg_std`
- `rolling_shots_on_target`, `rolling_shots_on_target_std`
- `rolling_possession`, `rolling_possession_std`
- `rolling_team_rating`, `rolling_team_rating_std`

### V18.0 赛前特征（+8维）
- `home_table_position`, `away_table_position`, `table_position_diff`
- `home_points`, `away_points`, `points_diff`
- `home_recent_form_points`, `away_recent_form_points`

### V19.0 高级动态特征（+13维）
ELO 相对差距:
- `raw_elo_gap`, `adjusted_elo_gap`, `fatigue_impact`, `schedule_impact`

疲劳度指数:
- `home_fatigue_index`, `away_fatigue_index`, `fatigue_diff`
- `home_rest_days`, `away_rest_days`

保级战意:
- `home_relegation_incentive`, `away_relegation_incentive`
- `incentive_diff`, `home_desperation`

### V19.4 平局敏感度特征（+3维）
- `table_proximity`: 积分榜接近度
- `low_scoring_tendency`: 低得分倾向
- `elo_diff_cluster`: ELO 差距聚类

## 特征提取流程

### 方式一：使用 main_production.py
```bash
# 完整流程
python main_production.py --full-pipeline

# 分步执行
python main_production.py l1-harvest --season 2425 --target 100
python main_production.py l2-parse --extractor-version V25.1
python main_production.py train --train-size 600 --test-size 160
```

### 方式二：使用 V26.1 收割流水线
```bash
# 自动分批收割（推荐）
python scripts/auto_harvest_batches.py

# 全量收割
python scripts/run_v26_full_harvest.py --limit 100
```

### 方式三：编程方式
```python
from src.processors import ExtractorRegistry, ExtractionResult
from src.config_unified import get_settings
import json

# 创建 V25.1 提取器
extractor = ExtractorRegistry.create("V25.1")

# 加载数据
with open("match_data.json") as f:
    raw_data = json.load(f)

# 提取特征
result: ExtractionResult = extractor.extract_with_validation(
    raw_data,
    skip_validation=False
)

# 检查结果
if result.is_success:
    print(f"特征数量: {result.feature_count}")
    print(f"状态: {result.status.value}")
    print(f"特征: {result.features}")
else:
    print(f"错误: {result.errors}")
```

## 特征选择与优化

### 特征重要性分析
```python
import xgboost as xgb
from sklearn.datasets import load_iris

# 训练模型
model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=3,
    learning_rate=0.01
)
model.fit(X_train, y_train)

# 获取特征重要性
importance = model.feature_importances_

# 排序
feature_importance = sorted(
    zip(X.columns, importance),
    key=lambda x: x[1],
    reverse=True
)

# 打印 Top 10
for feature, score in feature_importance[:10]:
    print(f"{feature}: {score:.4f}")
```

### 递归特征消除
```python
from sklearn.feature_selection import RFE
from xgboost import XGBClassifier

# 创建 RFE 选择器
rfe = RFE(
    estimator=XGBClassifier(n_estimators=100),
    n_features_to_select=50,
    step=0.2
)

# 拟合
rfe.fit(X_train, y_train)

# 获取选中的特征
selected_features = X_train.columns[rfe.support_]
print(f"选中特征: {list(selected_features)}")
```

### SHAP 特征解释
```python
import shap

# 创建解释器
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# 可视化
shap.summary_plot(shap_values, X_test)
shap.dependence_plot("feature_name", shap_values, X_test)
```

## 特征变换

### 标准化
```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
```

### 归一化
```python
from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler(feature_range=(0, 1))
X_normalized = scaler.fit_transform(X)
```

### 对数变换
```python
import numpy as np

# 对偏态数据应用对数变换
X_log = np.log1p(X)  # log(1 + x) 避免 log(0)
```

## 特征对齐与处理

### 全局特征注册表
```python
from src.processors.v25_production_extractor import (
    get_global_feature_keys,
    register_feature_keys
)

# 获取全局特征键
all_features = get_global_feature_keys()

# 注册新特征
register_feature_keys({"new_feature_1", "new_feature_2"})
```

### NaN 填充策略
```python
import pandas as pd

# 数值型特征：填充 0
df["numeric_feature"].fillna(0, inplace=True)

# 数值型特征：填充均值
df["numeric_feature"].fillna(df["numeric_feature"].mean(), inplace=True)

# 分类特征：填充众数
df["categorical_feature"].fillna(df["categorical_feature"].mode()[0], inplace=True)

# 前向填充
df.fillna(method="ffill", inplace=True)
```

## 特征监控

### 特征分布可视化
```python
import matplotlib.pyplot as plt

# 直方图
df["feature_name"].hist(bins=50)
plt.title("Feature Distribution")
plt.show()

# 箱线图
df.boxplot(column="feature_name")
plt.title("Feature Boxplot")
plt.show()
```

### 特征统计
```python
# 描述性统计
stats = df.describe()

# 缺失值统计
missing = df.isnull().sum()

# 特征类型统计
dtypes = df.dtypes
```

## 相关技能
- `v26-harvest`: V26.1 收割流水线
- `machine-learning-engineering`: ML 模型优化
- `data-engineering`: ETL 数据管道
- `football-prediction`: 足球预测系统

## 最佳实践

1. **特征提取**: 优先使用 V25.1 自适应引擎
2. **特征对齐**: 使用全局特征注册表确保一致性
3. **特征选择**: 基于特征重要性进行筛选
4. **特征变换**: 根据数据分布选择合适的变换方法
5. **特征监控**: 定期检查特征分布和统计特性

---
*Last updated: 2025-12-28*
*Target: 足球预测系统特征工程优化*
