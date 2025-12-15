# 🤖 机器学习模块指南

**版本**: v1.0.0
**最后更新**: 2025-10-24
**维护者**: Claude AI Assistant

---

## 📚 文档导航

### 相关文档
- **[📊 数据采集配置](../data/DATA_COLLECTION_SETUP.md)** - 数据收集和预处理
- **[🏗️ 系统架构](../architecture/ARCHITECTURE.md)** - 系统整体架构
- **[📋 API参考](../reference/API_REFERENCE.md)** - API接口文档
- **[🧪 测试策略](../testing/TEST_IMPROVEMENT_GUIDE.md)** - 测试方法

### 国际化说明
本文档提供中文版本（推荐），英文版本作为参考：
- 🇨🇳 **中文版本** (主要) - 当前文档
- 🇺🇸 **English Version** (计划中)

---

## 📑 目录

- [📊 模块概述](#-模块概述)
- [🏗️ 架构设计](#️-架构设计)
- [🤖 模型类型](#-模型类型)
- [📊 特征工程](#-特征工程)
- [🚀 模型训练](#-模型训练)
- [📈 模型评估](#-模型评估)
- [💾 模型管理](#-模型管理)
- [🔧 配置说明](#-配置说明)
- [🚀 快速开始](#-快速开始)
- [📚 使用示例](#-使用示例)
- [🔍 监控和日志](#-监控和日志)
- [⚠️ 故障排除](#️-故障排除)
- [📈 性能优化](#-性能优化)
- [🔗 相关资源](#-相关资源)

---

## 📊 模块概述

### 🎯 核心功能

机器学习模块是足球预测系统的核心组件，负责：

- **模型训练**: 支持多种机器学习算法的训练
- **预测推理**: 实时预测足球比赛结果
- **特征工程**: 数据预处理和特征生成
- **模型评估**: 全面的模型性能评估
- **模型管理**: 模型版本管理和部署

### 🔧 技术栈

- **核心框架**: Python 3.11+, scikit-learn, pandas, numpy
- **深度学习**: TensorFlow/PyTorch (计划中)
- **模型序列化**: pickle, joblib
- **数据处理**: pandas, numpy
- **特征工程**: scikit-learn preprocessing
- **模型评估**: scikit-learn metrics

### 📈 性能指标

- **支持模型类型**: 8种主要算法
- **训练数据规模**: 支持百万级样本
- **预测延迟**: < 10ms (单次预测)
- **模型准确率**: 目标 > 80%
- **并发支持**: 1000+ QPS

## 🏗️ ML架构概览

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        ML Pipeline                               │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   数据预处理      │   模型训练        │        模型部署               │
│  (Preprocessing) │  (Training)     │     (Deployment)            │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • 特征工程        │ • 模型选择        │ • 模型服务化                 │
│ • 数据清洗        │ • 超参数调优      │ • API接口                   │
│ • 特征选择        │ • 交叉验证        │ • 批量预测                   │
│ • 数据分割        │ • 模型评估        │ • 实时预测                   │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      MLOps层                                   │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   模型监控        │   实验管理        │        模型版本               │
│  (Monitoring)    │ (Experiments)   │    (Versioning)             │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ • 性能监控        │ • MLflow         │ • 模型注册表                 │
│ • 漂移检测        │ • 实验跟踪        │ • 版本控制                   │
│ • 告警通知        │ • 参数记录        │ • 回滚机制                   │
│ • 自动重训练      │ • 结果对比        │ • A/B测试                   │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

### 核心组件

| 组件 | 功能 | 技术栈 | 状态 |
|------|------|--------|------|
| **PredictionModel** | 预测模型基类 | Python, scikit-learn | ✅ 运行中 |
| **FootballPredictionModel** | 足球专用预测模型 | 随机森林, XGBoost | ✅ 运行中 |
| **BaselineModelTrainer** | 基准模型训练器 | MLflow, Optuna | 🚧 开发中 |
| **FeatureProcessor** | 特征处理器 | pandas, numpy | ✅ 运行中 |
| **ModelMonitor** | 模型监控 | Prometheus, Grafana | ✅ 运行中 |

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+
- **机器学习库**: scikit-learn, XGBoost
- **实验跟踪**: MLflow (可选)
- **数据存储**: PostgreSQL, Redis

### 5分钟快速上手

```bash
# 1. 安装ML依赖
pip install scikit-learn xgboost pandas numpy

# 2. 使用预训练模型进行预测
python -c "
from src.models.prediction_model import FootballPredictionModel
model = FootballPredictionModel()
result = model.predict_match('Team A', 'Team B', {})
print(result)
"

# 3. 训练自定义模型
python -c "
from src.models.prediction_model import FootballPredictionModel
import pandas as pd

# 准备训练数据
X = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [4, 5, 6]})
y = pd.Series([0, 1, 0])

model = FootballPredictionModel('my_model')
metrics = model.train(X, y)
print(f'训练完成，准确率: {metrics[\"accuracy\"]:.3f}')
"

# 4. 启动ML实验跟踪 (可选)
mlflow server --host 0.0.0.0 --port 5000
```

## 🧠 模型设计

### 1. 预测模型基类

```python
# src/models/prediction_model.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import logging

class PredictionModel(ABC):
    """预测模型抽象基类"""

    def __init__(
        self,
        model_name: str,
        model_type: str = "classification",
        **kwargs
    ):
        """
        初始化预测模型

        Args:
            model_name: 模型名称
            model_type: 模型类型 (classification/regression)
            **kwargs: 其他参数
        """
        self.model_name = model_name
        self.model_type = model_type
        self.logger = logging.getLogger(f"ml.{self.__class__.__name__}")

        # 模型状态
        self.is_trained = False
        self.model = None
        self.feature_columns = []
        self.target_column = "result"

        # 元数据
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "description": f"{model_name} prediction model",
            "hyperparameters": kwargs,
        }

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> Dict[str, Any]:
        """
        训练模型

        Args:
            X: 特征数据
            y: 目标变量
            **kwargs: 训练参数

        Returns:
            训练结果指标
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        进行预测

        Args:
            X: 特征数据

        Returns:
            预测结果
        """
        pass

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        预测概率 (仅分类模型)

        Args:
            X: 特征数据

        Returns:
            预测概率
        """
        if self.model_type != "classification":
            raise ValueError("predict_proba only available for classification models")

        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        return self.model.predict_proba(X)

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        评估模型性能

        Args:
            X: 特征数据
            y: 真实标签

        Returns:
            评估指标字典
        """
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

        if not self.is_trained:
            raise ValueError("Model must be trained before evaluation")

        # 获取预测结果
        y_pred = self.predict(X)

        # 计算评估指标
        metrics = {}

        if self.model_type == "classification":
            metrics["accuracy"] = accuracy_score(y, y_pred)
            metrics["precision"] = precision_score(y, y_pred, average="weighted", zero_division=0)
            metrics["recall"] = recall_score(y, y_pred, average="weighted", zero_division=0)
            metrics["f1_score"] = f1_score(y, y_pred, average="weighted", zero_division=0)

            # 如果是二分类或多分类，计算AUC
            try:
                y_proba = self.predict_proba(X)
                if len(np.unique(y)) == 2:  # 二分类
                    metrics["auc"] = roc_auc_score(y, y_proba[:, 1])
                else:  # 多分类
                    metrics["auc"] = roc_auc_score(y, y_proba, multi_class="ovr", average="weighted")
            except Exception:
                self.logger.warning("Could not calculate AUC score")

        return metrics

    def get_feature_importance(self) -> Dict[str, float]:
        """
        获取特征重要性

        Returns:
            特征重要性字典
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before getting feature importance")

        importance = {}

        if hasattr(self.model, "feature_importances_"):
            # 树模型等支持特征重要性
            for feature, importance_score in zip(self.feature_columns, self.model.feature_importances_):
                importance[feature] = float(importance_score)
        elif hasattr(self.model, "coef_"):
            # 线性模型等
            coef = self.model.coef_
            if coef.ndim > 1:
                coef = np.abs(coef).mean(axis=0)

            for feature, coef_score in zip(self.feature_columns, coef):
                importance[feature] = float(coef_score)
        else:
            # 使用SHAP值或其他方法 (简化实现)
            for feature in self.feature_columns:
                importance[feature] = 1.0 / len(self.feature_columns)

        return importance

    def save_model(self, file_path: str) -> bool:
        """
        保存模型到文件

        Args:
            file_path: 保存路径

        Returns:
            是否保存成功
        """
        try:
            import joblib

            model_data = {
                "model": self.model,
                "model_name": self.model_name,
                "model_type": self.model_type,
                "is_trained": self.is_trained,
                "feature_columns": self.feature_columns,
                "target_column": self.target_column,
                "metadata": self.metadata,
            }

            joblib.dump(model_data, file_path)
            self.logger.info(f"Model saved to: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            return False

    def load_model(self, file_path: str) -> bool:
        """
        从文件加载模型

        Args:
            file_path: 模型文件路径

        Returns:
            是否加载成功
        """
        try:
            import joblib

            model_data = joblib.load(file_path)

            self.model = model_data["model"]
            self.model_name = model_data["model_name"]
            self.model_type = model_data["model_type"]
            self.is_trained = model_data["is_trained"]
            self.feature_columns = model_data["feature_columns"]
            self.target_column = model_data["target_column"]
            self.metadata = model_data["metadata"]

            self.logger.info(f"Model loaded from: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return False
```

### 2. 足球预测模型实现

```python
# src/models/football_prediction_model.py

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import logging

from .prediction_model import PredictionModel

class PredictionType(Enum):
    """预测类型枚举"""
    MATCH_RESULT = "match_result"           # 比赛结果
    OVER_UNDER = "over_under"              # 大小球
    CORRECT_SCORE = "correct_score"        # 正确比分
    BOTH_TEAMS_SCORE = "both_teams_score"  # 双方都进球

class FootballPredictionModel(PredictionModel):
    """足球比赛预测模型"""

    def __init__(
        self,
        model_name: str = "football_predictor",
        prediction_type: PredictionType = PredictionType.MATCH_RESULT,
        **kwargs
    ):
        """
        初始化足球预测模型

        Args:
            model_name: 模型名称
            prediction_type: 预测类型
            **kwargs: 其他参数
        """
        super().__init__(model_name, "classification", **kwargs)
        self.prediction_type = prediction_type

        # 根据预测类型设置目标类别
        self._setup_target_classes()

        # 模型超参数
        self.hyperparameters = {
            "n_estimators": kwargs.get("n_estimators", 100),
            "max_depth": kwargs.get("max_depth", 10),
            "min_samples_split": kwargs.get("min_samples_split", 5),
            "min_samples_leaf": kwargs.get("min_samples_leaf", 2),
            "random_state": kwargs.get("random_state", 42),
        }

    def _setup_target_classes(self):
        """设置目标类别"""
        if self.prediction_type == PredictionType.MATCH_RESULT:
            self.target_classes = ["home_win", "draw", "away_win"]
        elif self.prediction_type == PredictionType.OVER_UNDER:
            self.target_classes = ["under", "over"]
        elif self.prediction_type == PredictionType.BOTH_TEAMS_SCORE:
            self.target_classes = ["no", "yes"]
        elif self.prediction_type == PredictionType.CORRECT_SCORE:
            # 常见比分
            self.target_classes = [
                "1-0", "2-0", "2-1", "1-1", "0-0",
                "0-1", "0-2", "1-2", "3-0", "0-3"
            ]
        else:
            raise ValueError(f"Unsupported prediction type: {self.prediction_type}")

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> Dict[str, Any]:
        """
        训练足球预测模型

        Args:
            X: 特征数据
            y: 目标变量
            **kwargs: 训练参数

        Returns:
            训练结果指标
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import LabelEncoder

        self.logger.info(f"Training {self.prediction_type.value} model with {len(X)} samples")

        # 特征处理
        self.feature_columns = list(X.columns)

        # 标签编码
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)

        # 保存标签编码器
        self.label_encoder = label_encoder
        self.label_mapping = dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))
        self.reverse_label_mapping = dict(zip(label_encoder.transform(label_encoder.classes_), label_encoder.classes_))

        # 创建并训练模型
        self.model = RandomForestClassifier(**self.hyperparameters)

        # 交叉验证评估
        cv_scores = cross_val_score(self.model, X, y_encoded, cv=5, scoring='accuracy')

        # 训练最终模型
        self.model.fit(X, y_encoded)
        self.is_trained = True

        # 计算训练指标
        train_metrics = self.evaluate(X, y)

        # 添加交叉验证结果
        train_metrics["cv_mean_accuracy"] = float(cv_scores.mean())
        train_metrics["cv_std_accuracy"] = float(cv_scores.std())

        # 更新元数据
        self.metadata.update({
            "last_trained": datetime.now().isoformat(),
            "training_samples": len(X),
            "feature_count": len(self.feature_columns),
            "prediction_type": self.prediction_type.value,
            "label_mapping": self.label_mapping,
            "metrics": train_metrics,
        })

        self.logger.info(
            f"Model trained successfully. "
            f"Accuracy: {train_metrics['accuracy']:.3f}, "
            f"CV Accuracy: {train_metrics['cv_mean_accuracy']:.3f} ± {train_metrics['cv_std_accuracy']:.3f}"
        )

        return train_metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        预测比赛结果

        Args:
            X: 特征数据

        Returns:
            预测结果
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        predictions_encoded = self.model.predict(X)

        # 转换回原始标签
        predictions = [self.reverse_label_mapping[pred] for pred in predictions_encoded]

        return np.array(predictions)

    def predict_match(
        self,
        home_team: str,
        away_team: str,
        features: Dict[str, Any],
        return_probabilities: bool = True
    ) -> Dict[str, Any]:
        """
        预测单场比赛结果

        Args:
            home_team: 主队名称
            away_team: 客队名称
            features: 特征字典
            return_probabilities: 是否返回概率

        Returns:
            预测结果字典
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        # 转换特征为DataFrame
        feature_df = pd.DataFrame([features])

        # 确保特征列顺序正确
        feature_df = feature_df[self.feature_columns]

        # 预测
        prediction_encoded = self.model.predict(feature_df)[0]
        prediction = self.reverse_label_mapping[prediction_encoded]

        result = {
            "home_team": home_team,
            "away_team": away_team,
            "prediction": prediction,
            "prediction_type": self.prediction_type.value,
            "features_used": list(features.keys()),
            "model_name": self.model_name,
            "prediction_time": datetime.now().isoformat(),
        }

        # 添加概率信息
        if return_probabilities:
            probabilities = self.model.predict_proba(feature_df)[0]

            # 构建概率字典
            prob_dict = {}
            for i, class_name in enumerate(self.label_encoder.classes_):
                prob_dict[class_name] = float(probabilities[i])

            result["probabilities"] = prob_dict
            result["confidence"] = float(np.max(probabilities))

        return result

    def batch_predict(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量预测比赛结果

        Args:
            matches: 比赛列表，每个元素包含 home_team, away_team, features

        Returns:
            预测结果列表
        """
        results = []

        for match in matches:
            try:
                result = self.predict_match(
                    home_team=match.get("home_team", ""),
                    away_team=match.get("away_team", ""),
                    features=match.get("features", {}),
                    return_probabilities=True
                )
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to predict match: {e}")
                # 添加错误结果
                error_result = {
                    "home_team": match.get("home_team", ""),
                    "away_team": match.get("away_team", ""),
                    "error": str(e),
                    "prediction": None,
                }
                results.append(error_result)

        return results

    def explain_prediction(
        self,
        home_team: str,
        away_team: str,
        features: Dict[str, Any],
        top_features: int = 5
    ) -> Dict[str, Any]:
        """
        解释预测结果

        Args:
            home_team: 主队名称
            away_team: 客队名称
            features: 特征字典
            top_features: 返回最重要的特征数量

        Returns:
            解释结果
        """
        # 获取预测结果
        prediction_result = self.predict_match(home_team, away_team, features)

        # 获取特征重要性
        feature_importance = self.get_feature_importance()

        # 获取当前特征的重要性
        current_features_importance = {}
        for feature, value in features.items():
            if feature in feature_importance:
                current_features_importance[feature] = {
                    "value": value,
                    "importance": feature_importance[feature],
                }

        # 排序并取前N个最重要的特征
        sorted_features = sorted(
            current_features_importance.items(),
            key=lambda x: x[1]["importance"],
            reverse=True
        )[:top_features]

        explanation = {
            "match": f"{home_team} vs {away_team}",
            "prediction": prediction_result["prediction"],
            "confidence": prediction_result.get("confidence", 0),
            "top_features": [
                {
                    "name": feature,
                    "value": info["value"],
                    "importance": info["importance"],
                    "impact": self._calculate_feature_impact(feature, info["value"])
                }
                for feature, info in sorted_features
            ],
            "model_info": {
                "model_name": self.model_name,
                "prediction_type": self.prediction_type.value,
                "feature_count": len(self.feature_columns),
            }
        }

        return explanation

    def _calculate_feature_impact(self, feature: str, value: Any) -> str:
        """计算特征对预测的影响"""
        if value > 0:
            return f"正向影响 (+{value:.2f})"
        elif value < 0:
            return f"负向影响 ({value:.2f})"
        else:
            return "中性影响 (0.00)"
```

## 🔧 模型训练

### 1. 训练数据准备

```python
# src/ml/data_preparation.py

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import logging

class FootballDataPreparer:
    """足球数据预处理器"""

    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = []
        self.logger = logging.getLogger(__name__)

    def prepare_match_data(
        self,
        matches_df: pd.DataFrame,
        target_column: str = "result",
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """
        准备比赛数据用于训练

        Args:
            matches_df: 比赛数据DataFrame
            target_column: 目标列名
            test_size: 测试集比例
            random_state: 随机种子

        Returns:
            (X_train, y_train, X_test, y_test)
        """
        self.logger.info(f"Preparing data with {len(matches_df)} matches")

        # 数据清洗
        cleaned_df = self._clean_data(matches_df)

        # 特征工程
        features_df = self._engineer_features(cleaned_df)

        # 准备特征和目标
        X = features_df.drop(columns=[target_column])
        y = features_df[target_column]

        # 编码分类变量
        X_encoded = self._encode_categorical_features(X)

        # 特征标准化
        X_scaled = self._scale_features(X_encoded)

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=random_state, stratify=y
        )

        self.feature_columns = list(X_train.columns)
        self.logger.info(f"Data prepared: {len(X_train)} training, {len(X_test)} testing samples")

        return X_train, y_train, X_test, y_test

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        # 移除缺失值过多的行
        df_clean = df.dropna(thresh=len(df.columns) * 0.7)

        # 填充缺失值
        numeric_columns = df_clean.select_dtypes(include=[np.number]).columns
        df_clean[numeric_columns] = df_clean[numeric_columns].fillna(df_clean[numeric_columns].median())

        categorical_columns = df_clean.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            df_clean[col] = df_clean[col].fillna('unknown')

        return df_clean

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征工程"""
        df_features = df.copy()

        # 主场优势特征
        if 'home_team' in df_features.columns and 'away_team' in df_features.columns:
            df_features['is_home_favorite'] = (
                df_features['home_team_rating'] > df_features['away_team_rating']
            ).astype(int)

        # 最近表现特征
        if 'home_team_recent_form' in df_features.columns:
            df_features['home_team_form_trend'] = (
                df_features['home_team_recent_form'].rolling(window=3).mean()
            )

        # 历史交锋特征
        if 'head_to_head_wins' in df_features.columns:
            df_features['head_to_head_win_rate'] = (
                df_features['head_to_head_wins'] / df_features['head_to_head_matches']
            )

        return df_features

    def _encode_categorical_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """编码分类特征"""
        X_encoded = X.copy()

        categorical_columns = X_encoded.select_dtypes(include=['object']).columns

        for col in categorical_columns:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                X_encoded[col] = self.label_encoders[col].fit_transform(X_encoded[col])
            else:
                # 处理未见过的类别
                known_classes = set(self.label_encoders[col].classes_)
                X_encoded[col] = X_encoded[col].apply(
                    lambda x: x if x in known_classes else 'unknown'
                )

                # 如果有新类别，重新拟合编码器
                if not set(X_encoded[col]).issubset(known_classes):
                    self.label_encoders[col].classes_ = np.append(
                        self.label_encoders[col].classes_, 'unknown'
                    )

                X_encoded[col] = self.label_encoders[col].transform(X_encoded[col])

        return X_encoded

    def _scale_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """特征标准化"""
        X_scaled = X.copy()
        numeric_columns = X_scaled.select_dtypes(include=[np.number]).columns

        if len(self.feature_columns) == 0:  # 首次拟合
            X_scaled[numeric_columns] = self.scaler.fit_transform(X_scaled[numeric_columns])
        else:
            X_scaled[numeric_columns] = self.scaler.transform(X_scaled[numeric_columns])

        return X_scaled

    def prepare_prediction_features(self, match_data: Dict[str, Any]) -> pd.DataFrame:
        """
        为单场比赛预测准备特征

        Args:
            match_data: 比赛数据字典

        Returns:
            预处理后的特征DataFrame
        """
        df = pd.DataFrame([match_data])
        df_features = self._engineer_features(df)
        df_encoded = self._encode_categorical_features(df_features)
        df_scaled = self._scale_features(df_encoded)

        # 确保特征顺序一致
        if self.feature_columns:
            for col in self.feature_columns:
                if col not in df_scaled.columns:
                    df_scaled[col] = 0

            df_scaled = df_scaled[self.feature_columns]

        return df_scaled
```

### 2. 模型训练器

```python
# src/ml/model_trainer.py

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
import os

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import mlflow
import mlflow.sklearn

from ..models.football_prediction_model import FootballPredictionModel, PredictionType
from .data_preparation import FootballDataPreparer

class FootballModelTrainer:
    """足球模型训练器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化训练器

        Args:
            config: 训练配置
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.data_preparer = FootballDataPreparer()

        # MLflow配置
        self.mlflow_enabled = self.config.get("mlflow_enabled", False)
        if self.mlflow_enabled:
            mlflow.set_tracking_uri(self.config.get("mlflow_tracking_uri", "http://localhost:5000"))
            mlflow.set_experiment(self.config.get("mlflow_experiment", "football-prediction"))

    def train_match_result_model(
        self,
        matches_df: pd.DataFrame,
        target_column: str = "result",
        hyperparameter_tuning: bool = True
    ) -> FootballPredictionModel:
        """
        训练比赛结果预测模型

        Args:
            matches_df: 比赛数据
            target_column: 目标列名
            hyperparameter_tuning: 是否进行超参数调优

        Returns:
            训练好的模型
        """
        self.logger.info("Starting match result model training")

        # 准备数据
        X_train, y_train, X_test, y_test = self.data_preparer.prepare_match_data(
            matches_df, target_column
        )

        # 创建模型
        model = FootballPredictionModel(
            model_name="match_result_predictor",
            prediction_type=PredictionType.MATCH_RESULT
        )

        if self.mlflow_enabled:
            with mlflow.start_run(run_name=f"match_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                return self._train_with_mlflow(model, X_train, y_train, X_test, y_test, hyperparameter_tuning)
        else:
            return self._train_model(model, X_train, y_train, X_test, y_test, hyperparameter_tuning)

    def _train_model(
        self,
        model: FootballPredictionModel,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        hyperparameter_tuning: bool
    ) -> FootballPredictionModel:
        """训练模型"""

        if hyperparameter_tuning:
            # 超参数调优
            best_params = self._hyperparameter_tuning(X_train, y_train)
            model.hyperparameters.update(best_params)

        # 训练模型
        train_metrics = model.train(X_train, y_train)

        # 评估模型
        test_metrics = model.evaluate(X_test, y_test)

        # 记录结果
        self.logger.info(f"Training completed. Test accuracy: {test_metrics['accuracy']:.3f}")

        # 生成详细报告
        self._generate_training_report(model, train_metrics, test_metrics, X_test, y_test)

        return model

    def _train_with_mlflow(
        self,
        model: FootballPredictionModel,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        hyperparameter_tuning: bool
    ) -> FootballPredictionModel:
        """使用MLflow训练模型"""

        if hyperparameter_tuning:
            best_params = self._hyperparameter_tuning(X_train, y_train)
            model.hyperparameters.update(best_params)
            mlflow.log_params(best_params)

        # 记录参数
        mlflow.log_params({
            "model_type": model.model_type,
            "prediction_type": model.prediction_type.value,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": len(X_train.columns),
        })

        # 训练模型
        train_metrics = model.train(X_train, y_train)

        # 评估模型
        test_metrics = model.evaluate(X_test, y_test)

        # 记录指标
        for metric_name, metric_value in train_metrics.items():
            if isinstance(metric_value, (int, float)):
                mlflow.log_metric(f"train_{metric_name}", metric_value)

        for metric_name, metric_value in test_metrics.items():
            if isinstance(metric_value, (int, float)):
                mlflow.log_metric(f"test_{metric_name}", metric_value)

        # 记录模型
        mlflow.sklearn.log_model(model.model, "model")

        # 记录特征重要性
        feature_importance = model.get_feature_importance()
        mlflow.log_dict(feature_importance, "feature_importance.json")

        self.logger.info(f"Training completed with MLflow. Test accuracy: {test_metrics['accuracy']:.3f}")

        return model

    def _hyperparameter_tuning(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, Any]:
        """超参数调优"""

        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [5, 10, 15, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', None]
        }

        rf = RandomForestClassifier(random_state=42)
        grid_search = GridSearchCV(
            rf, param_grid, cv=5, scoring='accuracy', n_jobs=-1, verbose=1
        )

        grid_search.fit(X, y)

        self.logger.info(f"Best parameters: {grid_search.best_params_}")
        self.logger.info(f"Best CV score: {grid_search.best_score_:.3f}")

        return grid_search.best_params_

    def _generate_training_report(
        self,
        model: FootballPredictionModel,
        train_metrics: Dict[str, float],
        test_metrics: Dict[str, float],
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> None:
        """生成训练报告"""

        # 预测测试集
        y_pred = model.predict(X_test)

        # 生成分类报告
        class_report = classification_report(y_test, y_pred, output_dict=True)

        # 生成混淆矩阵
        conf_matrix = confusion_matrix(y_test, y_pred)

        # 获取特征重要性
        feature_importance = model.get_feature_importance()

        # 创建报告
        report = {
            "model_info": {
                "model_name": model.model_name,
                "prediction_type": model.prediction_type.value,
                "training_time": model.metadata.get("last_trained"),
                "model_version": model.metadata.get("version"),
            },
            "data_info": {
                "training_samples": len(X_test) * 4 // 3,  # 估算训练集大小
                "test_samples": len(X_test),
                "feature_count": len(model.feature_columns),
                "target_classes": list(model.label_mapping.keys()) if hasattr(model, 'label_mapping') else [],
            },
            "performance": {
                "train_metrics": train_metrics,
                "test_metrics": test_metrics,
            },
            "classification_report": class_report,
            "confusion_matrix": conf_matrix.tolist(),
            "feature_importance": dict(
                sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }

        # 保存报告
        reports_dir = self.config.get("reports_dir", "ml_reports")
        os.makedirs(reports_dir, exist_ok=True)

        report_path = os.path.join(
            reports_dir,
            f"training_report_{model.model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Training report saved to: {report_path}")
```

## 📊 模型评估

### 1. 评估指标

```python
# src/ml/model_evaluation.py

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    precision_recall_curve, roc_curve
)
import logging

class ModelEvaluator:
    """模型评估器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def comprehensive_evaluation(
        self,
        model,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        target_classes: List[str] = None
    ) -> Dict[str, Any]:
        """
        综合模型评估

        Args:
            model: 训练好的模型
            X_test: 测试特征
            y_test: 测试标签
            target_classes: 目标类别列表

        Returns:
            评估结果字典
        """
        self.logger.info(f"Evaluating model with {len(X_test)} test samples")

        # 获取预测结果
        y_pred = model.predict(X_test)
        y_proba = None

        try:
            y_proba = model.predict_proba(X_test)
        except Exception:
            self.logger.warning("Model does not support probability prediction")

        # 基础指标
        basic_metrics = self._calculate_basic_metrics(y_test, y_pred, y_proba)

        # 详细分类报告
        class_report = classification_report(y_test, y_pred, target_names=target_classes, output_dict=True)

        # 混淆矩阵
        conf_matrix = confusion_matrix(y_test, y_pred)

        # ROC曲线数据 (如果是二分类)
        roc_data = None
        if y_proba is not None and len(np.unique(y_test)) == 2:
            roc_data = self._calculate_roc_curve(y_test, y_proba[:, 1])

        # 特征重要性
        feature_importance = model.get_feature_importance()

        # 预测分布分析
        prediction_distribution = self._analyze_prediction_distribution(y_test, y_pred)

        # 错误分析
        error_analysis = self._analyze_predictions(X_test, y_test, y_pred, y_proba)

        evaluation_results = {
            "basic_metrics": basic_metrics,
            "classification_report": class_report,
            "confusion_matrix": conf_matrix.tolist(),
            "feature_importance": feature_importance,
            "prediction_distribution": prediction_distribution,
            "error_analysis": error_analysis,
            "roc_curve": roc_data,
            "evaluation_time": pd.Timestamp.now().isoformat(),
        }

        return evaluation_results

    def _calculate_basic_metrics(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """计算基础评估指标"""

        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, average="weighted", zero_division=0),
            "recall": recall_score(y_true, y_pred, average="weighted", zero_division=0),
            "f1_score": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        }

        # AUC (如果支持概率预测)
        if y_proba is not None:
            try:
                if len(np.unique(y_true)) == 2:  # 二分类
                    metrics["auc"] = roc_auc_score(y_true, y_proba[:, 1])
                else:  # 多分类
                    metrics["auc"] = roc_auc_score(y_true, y_proba, multi_class="ovr", average="weighted")
            except Exception:
                self.logger.warning("Could not calculate AUC score")

        return metrics

    def _calculate_roc_curve(self, y_true: pd.Series, y_scores: np.ndarray) -> Dict[str, List]:
        """计算ROC曲线数据"""
        fpr, tpr, thresholds = roc_curve(y_true, y_scores)
        auc_score = roc_auc_score(y_true, y_scores)

        return {
            "false_positive_rate": fpr.tolist(),
            "true_positive_rate": tpr.tolist(),
            "thresholds": thresholds.tolist(),
            "auc": auc_score,
        }

    def _analyze_prediction_distribution(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray
    ) -> Dict[str, Any]:
        """分析预测分布"""

        # 实际分布
        actual_distribution = y_true.value_counts().to_dict()

        # 预测分布
        pred_series = pd.Series(y_pred)
        predicted_distribution = pred_series.value_counts().to_dict()

        # 按类别的准确性
        class_accuracy = {}
        for class_name in np.unique(y_true):
            class_mask = (y_true == class_name)
            if class_mask.sum() > 0:
                class_accuracy[class_name] = accuracy_score(
                    y_true[class_mask], y_pred[class_mask]
                )

        return {
            "actual_distribution": actual_distribution,
            "predicted_distribution": predicted_distribution,
            "class_accuracy": class_accuracy,
        }

    def _analyze_predictions(
        self,
        X_test: pd.DataFrame,
        y_true: pd.Series,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """分析预测结果"""

        # 错误预测的样本
        incorrect_mask = (y_true != y_pred)
        incorrect_indices = np.where(incorrect_mask)[0]

        # 置信度分析 (如果有概率)
        confidence_analysis = None
        if y_proba is not None:
            predicted_confidence = np.max(y_proba, axis=1)

            confidence_analysis = {
                "mean_confidence": float(np.mean(predicted_confidence)),
                "correct_predictions_mean_confidence": float(
                    np.mean(predicted_confidence[~incorrect_mask])
                ),
                "incorrect_predictions_mean_confidence": float(
                    np.mean(predicted_confidence[incorrect_mask])
                ),
            }

        # 错误样本分析
        error_samples = []
        for idx in incorrect_indices[:10]:  # 只分析前10个错误样本
            error_info = {
                "index": int(idx),
                "true_label": str(y_true.iloc[idx]),
                "predicted_label": str(y_pred[idx]),
                "features": X_test.iloc[idx].to_dict(),
            }

            if y_proba is not None:
                error_info["predicted_probabilities"] = y_proba[idx].tolist()
                error_info["confidence"] = float(np.max(y_proba[idx]))

            error_samples.append(error_info)

        return {
            "total_errors": int(len(incorrect_indices)),
            "error_rate": float(len(incorrect_indices) / len(y_true)),
            "confidence_analysis": confidence_analysis,
            "error_samples": error_samples,
        }

    def generate_evaluation_report(
        self,
        evaluation_results: Dict[str, Any],
        model_name: str,
        save_path: Optional[str] = None
    ) -> str:
        """生成评估报告"""

        report = f"""
# 模型评估报告

## 模型信息
- **模型名称**: {model_name}
- **评估时间**: {evaluation_results['evaluation_time']}

## 基础性能指标
"""

        # 添加基础指标
        metrics = evaluation_results['basic_metrics']
        for metric_name, metric_value in metrics.items():
            report += f"- **{metric_name.upper()}**: {metric_value:.4f}\n"

        # 添加预测分布
        pred_dist = evaluation_results['prediction_distribution']
        report += f"""
## 预测分布分析

### 实际分布
"""
        for class_name, count in pred_dist['actual_distribution'].items():
            report += f"- {class_name}: {count}\n"

        report += "\n### 预测分布\n"
        for class_name, count in pred_dist['predicted_distribution'].items():
            report += f"- {class_name}: {count}\n"

        report += "\n### 各类别准确率\n"
        for class_name, accuracy in pred_dist['class_accuracy'].items():
            report += f"- {class_name}: {accuracy:.4f}\n"

        # 添加错误分析
        error_analysis = evaluation_results['error_analysis']
        report += f"""
## 错误分析
- **总错误数**: {error_analysis['total_errors']}
- **错误率**: {error_analysis['error_rate']:.4f}
"""

        if error_analysis.get('confidence_analysis'):
            conf_analysis = error_analysis['confidence_analysis']
            report += f"""
### 置信度分析
- **平均置信度**: {conf_analysis['mean_confidence']:.4f}
- **正确预测平均置信度**: {conf_analysis['correct_predictions_mean_confidence']:.4f}
- **错误预测平均置信度**: {conf_analysis['incorrect_predictions_mean_confidence']:.4f}
"""

        # 添加特征重要性
        feature_importance = evaluation_results['feature_importance']
        report += f"""
## 特征重要性 (Top 10)
"""
        for i, (feature, importance) in enumerate(
            sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
        ):
            report += f"{i+1}. **{feature}**: {importance:.4f}\n"

        # 保存报告
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report)
            self.logger.info(f"Evaluation report saved to: {save_path}")

        return report
```

## 🚀 模型部署

### 1. 模型服务化

```python
# src/ml/model_service.py

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import asyncio
import logging
from datetime import datetime
import uuid

from ..models.football_prediction_model import FootballPredictionModel

class PredictionRequest(BaseModel):
    """预测请求模型"""
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    features: Dict[str, Any] = Field(..., description="特征数据")
    include_explanation: bool = Field(False, description="是否包含解释")

class BatchPredictionRequest(BaseModel):
    """批量预测请求模型"""
    matches: List[Dict[str, Any]] = Field(..., description="比赛列表")
    include_explanations: bool = Field(False, description="是否包含解释")

class PredictionResponse(BaseModel):
    """预测响应模型"""
    request_id: str = Field(..., description="请求ID")
    prediction: Dict[str, Any] = Field(..., description="预测结果")
    explanation: Optional[Dict[str, Any]] = Field(None, description="预测解释")
    timestamp: str = Field(..., description="预测时间")

class ModelService:
    """模型服务"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models: Dict[str, FootballPredictionModel] = {}
        self.prediction_cache = {}
        self.request_queue = asyncio.Queue()
        self.is_processing = False

    def register_model(self, model: FootballPredictionModel) -> None:
        """注册模型"""
        self.models[model.model_name] = model
        self.logger.info(f"Model registered: {model.model_name}")

    def get_model(self, model_name: str) -> Optional[FootballPredictionModel]:
        """获取模型"""
        return self.models.get(model_name)

    async def predict_match(
        self,
        request: PredictionRequest,
        model_name: str = "football_predictor"
    ) -> PredictionResponse:
        """
        预测单场比赛

        Args:
            request: 预测请求
            model_name: 模型名称

        Returns:
            预测响应
        """
        request_id = str(uuid.uuid4())

        try:
            model = self.get_model(model_name)
            if not model:
                raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

            if not model.is_trained:
                raise HTTPException(status_code=400, detail="Model is not trained")

            # 检查缓存
            cache_key = self._generate_cache_key(request, model_name)
            if cache_key in self.prediction_cache:
                cached_result = self.prediction_cache[cache_key]
                self.logger.debug(f"Cache hit for request: {request_id}")
                return PredictionResponse(
                    request_id=request_id,
                    prediction=cached_result["prediction"],
                    explanation=cached_result.get("explanation"),
                    timestamp=cached_result["timestamp"]
                )

            # 执行预测
            prediction = model.predict_match(
                home_team=request.home_team,
                away_team=request.away_team,
                features=request.features,
                return_probabilities=True
            )

            # 生成解释 (如果需要)
            explanation = None
            if request.include_explanation:
                explanation = model.explain_prediction(
                    home_team=request.home_team,
                    away_team=request.away_team,
                    features=request.features
                )

            # 缓存结果
            result = {
                "prediction": prediction,
                "explanation": explanation,
                "timestamp": datetime.now().isoformat()
            }
            self.prediction_cache[cache_key] = result

            self.logger.info(f"Prediction completed: {request_id}")

            return PredictionResponse(
                request_id=request_id,
                prediction=prediction,
                explanation=explanation,
                timestamp=result["timestamp"]
            )

        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def batch_predict(
        self,
        request: BatchPredictionRequest,
        model_name: str = "football_predictor"
    ) -> List[PredictionResponse]:
        """
        批量预测

        Args:
            request: 批量预测请求
            model_name: 模型名称

        Returns:
            预测响应列表
        """
        model = self.get_model(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

        if not model.is_trained:
            raise HTTPException(status_code=400, detail="Model is not trained")

        # 准备批量预测数据
        matches = []
        for match in request.matches:
            matches.append({
                "home_team": match.get("home_team", ""),
                "away_team": match.get("away_team", ""),
                "features": match.get("features", {})
            })

        # 执行批量预测
        batch_results = model.batch_predict(matches)

        # 生成响应
        responses = []
        for i, result in enumerate(batch_results):
            if "error" in result:
                # 错误响应
                responses.append(PredictionResponse(
                    request_id=f"batch_{i}_{str(uuid.uuid4())[:8]}",
                    prediction=result,
                    explanation=None,
                    timestamp=datetime.now().isoformat()
                ))
            else:
                # 成功响应
                explanation = None
                if request.include_explanations:
                    explanation = model.explain_prediction(
                        home_team=result["home_team"],
                        away_team=result["away_team"],
                        features=matches[i]["features"]
                    )

                responses.append(PredictionResponse(
                    request_id=f"batch_{i}_{str(uuid.uuid4())[:8]}",
                    prediction=result,
                    explanation=explanation,
                    timestamp=result["prediction_time"]
                ))

        return responses

    def _generate_cache_key(self, request: PredictionRequest, model_name: str) -> str:
        """生成缓存键"""
        import hashlib

        key_data = f"{model_name}:{request.home_team}:{request.away_team}:{sorted(request.features.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def clear_cache(self) -> None:
        """清空缓存"""
        self.prediction_cache.clear()
        self.logger.info("Prediction cache cleared")

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息"""
        model = self.get_model(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")

        return {
            "model_name": model.model_name,
            "model_type": model.model_type,
            "prediction_type": model.prediction_type.value,
            "is_trained": model.is_trained,
            "feature_count": len(model.feature_columns),
            "target_classes": model.target_classes,
            "metadata": model.metadata,
        }

# 创建FastAPI应用
app = FastAPI(title="Football Prediction API", version="1.0.0")
model_service = ModelService()

# 注册默认模型
from ..models.prediction_model import default_model
model_service.register_model(default_model)

# API端点
@app.post("/predict", response_model=PredictionResponse)
async def predict_match(request: PredictionRequest):
    """预测单场比赛"""
    return await model_service.predict_match(request)

@app.post("/predict/batch", response_model=List[PredictionResponse])
async def batch_predict(request: BatchPredictionRequest):
    """批量预测比赛"""
    return await model_service.batch_predict(request)

@app.get("/models")
async def list_models():
    """列出所有模型"""
    return {"models": list(model_service.models.keys())}

@app.get("/models/{model_name}")
async def get_model_info(model_name: str):
    """获取模型信息"""
    return model_service.get_model_info(model_name)

@app.post("/models/{model_name}/register")
async def register_model(model_name: str, model_path: str):
    """注册新模型"""
    model = FootballPredictionModel(model_name)
    if model.load_model(model_path):
        model_service.register_model(model)
        return {"message": f"Model {model_name} registered successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to load model")

@app.delete("/cache")
async def clear_cache():
    """清空预测缓存"""
    model_service.clear_cache()
    return {"message": "Cache cleared"}
```

## 📈 模型监控

### 1. 性能监控

```python
# src/ml/model_monitor.py

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from prometheus_client import Counter, Histogram, Gauge
import asyncio

class ModelMonitor:
    """模型监控器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Prometheus指标
        self.prediction_requests_total = Counter(
            'model_prediction_requests_total',
            'Total number of prediction requests',
            ['model_name', 'status']
        )

        self.prediction_duration = Histogram(
            'model_prediction_duration_seconds',
            'Time spent making predictions',
            ['model_name'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )

        self.prediction_accuracy = Gauge(
            'model_prediction_accuracy',
            'Current model accuracy',
            ['model_name']
        )

        self.data_drift_score = Gauge(
            'model_data_drift_score',
            'Data drift score',
            ['model_name', 'feature']
        )

        # 监控数据存储
        self.monitoring_data = {}
        self.alert_thresholds = {
            "accuracy_drop": 0.1,      # 准确率下降10%
            "prediction_latency": 2.0, # 预测延迟超过2秒
            "error_rate": 0.05,        # 错误率超过5%
            "data_drift": 0.2,         # 数据漂移超过20%
        }

    async def record_prediction(
        self,
        model_name: str,
        prediction_time: float,
        success: bool,
        prediction_result: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录预测请求"""

        status = "success" if success else "error"
        self.prediction_requests_total.labels(
            model_name=model_name,
            status=status
        ).inc()

        self.prediction_duration.labels(
            model_name=model_name
        ).observe(prediction_time)

    async def update_model_accuracy(
        self,
        model_name: str,
        accuracy: float
    ) -> None:
        """更新模型准确率"""

        self.prediction_accuracy.labels(
            model_name=model_name
        ).set(accuracy)

        # 检查是否需要告警
        await self._check_accuracy_drop(model_name, accuracy)

    async def detect_data_drift(
        self,
        model_name: str,
        current_features: pd.DataFrame,
        reference_features: pd.DataFrame
    ) -> Dict[str, float]:
        """检测数据漂移"""

        drift_scores = {}

        for feature in current_features.columns:
            if feature in reference_features.columns:
                # 计算分布差异 (简化实现)
                current_mean = current_features[feature].mean()
                ref_mean = reference_features[feature].mean()
                current_std = current_features[feature].std()
                ref_std = reference_features[feature].std()

                # 计算漂移分数
                mean_diff = abs(current_mean - ref_mean) / (ref_std + 1e-8)
                std_ratio = current_std / (ref_std + 1e-8)

                drift_score = max(mean_diff, abs(std_ratio - 1))
                drift_scores[feature] = drift_score

                # 更新Prometheus指标
                self.data_drift_score.labels(
                    model_name=model_name,
                    feature=feature
                ).set(drift_score)

        # 检查是否需要告警
        await self._check_data_drift_alert(model_name, drift_scores)

        return drift_scores

    async def _check_accuracy_drop(self, model_name: str, current_accuracy: float) -> None:
        """检查准确率下降告警"""

        if model_name not in self.monitoring_data:
            self.monitoring_data[model_name] = {}

        last_accuracy = self.monitoring_data[model_name].get("last_accuracy")

        if last_accuracy is not None:
            accuracy_drop = last_accuracy - current_accuracy

            if accuracy_drop > self.alert_thresholds["accuracy_drop"]:
                await self._send_alert(
                    "accuracy_drop",
                    f"Model {model_name} accuracy dropped by {accuracy_drop:.3f}",
                    {
                        "model_name": model_name,
                        "last_accuracy": last_accuracy,
                        "current_accuracy": current_accuracy,
                        "drop": accuracy_drop,
                    }
                )

        self.monitoring_data[model_name]["last_accuracy"] = current_accuracy

    async def _check_data_drift_alert(
        self,
        model_name: str,
        drift_scores: Dict[str, float]
    ) -> None:
        """检查数据漂移告警"""

        max_drift = max(drift_scores.values())

        if max_drift > self.alert_thresholds["data_drift"]:
            # 找到漂移最大的特征
            max_drift_feature = max(drift_scores.items(), key=lambda x: x[1])

            await self._send_alert(
                "data_drift",
                f"Significant data drift detected in model {model_name}",
                {
                    "model_name": model_name,
                    "max_drift": max_drift,
                    "max_drift_feature": max_drift_feature[0],
                    "drift_scores": drift_scores,
                }
            )

    async def _send_alert(
        self,
        alert_type: str,
        message: str,
        details: Dict[str, Any]
    ) -> None:
        """发送告警"""

        alert = {
            "alert_type": alert_type,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "severity": self._get_alert_severity(alert_type),
        }

        self.logger.warning(f"ALERT: {message}")

        # 这里可以集成实际的告警系统 (邮件、Slack等)
        # await self.alert_sender.send_alert(alert)

    def _get_alert_severity(self, alert_type: str) -> str:
        """获取告警严重程度"""

        severity_map = {
            "accuracy_drop": "warning",
            "data_drift": "warning",
            "high_latency": "critical",
            "high_error_rate": "critical",
        }

        return severity_map.get(alert_type, "info")

    async def generate_monitoring_report(
        self,
        model_name: str,
        time_range: timedelta = timedelta(hours=24)
    ) -> Dict[str, Any]:
        """生成监控报告"""

        end_time = datetime.now()
        start_time = end_time - time_range

        report = {
            "model_name": model_name,
            "report_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_hours": time_range.total_seconds() / 3600,
            },
            "performance_metrics": {
                "total_requests": 0,
                "success_rate": 0,
                "average_latency": 0,
                "current_accuracy": 0,
            },
            "data_drift": {},
            "alerts": [],
            "recommendations": [],
        }

        # 收集监控数据 (简化实现)
        if model_name in self.monitoring_data:
            model_data = self.monitoring_data[model_name]

            report["performance_metrics"]["current_accuracy"] = model_data.get("last_accuracy", 0)

            # 生成建议
            if model_data.get("last_accuracy", 1.0) < 0.7:
                report["recommendations"].append("考虑重新训练模型以提高准确率")

            if len(model_data.get("recent_drift_scores", {})) > 0:
                report["recommendations"].append("检测到数据漂移，建议更新训练数据")

        return report
```

## 📚 最佳实践

### 1. 模型开发最佳实践

1. **数据质量**
   - 确保训练数据的完整性和准确性
   - 进行适当的数据清洗和预处理
   - 处理缺失值和异常值

2. **特征工程**
   - 选择与预测目标相关的特征
   - 避免数据泄露 (feature leakage)
   - 进行特征标准化和归一化

3. **模型选择**
   - 从简单的基线模型开始
   - 根据问题特点选择合适的算法
   - 考虑模型的解释性需求

4. **验证策略**
   - 使用时间序列分割避免未来数据泄露
   - 进行交叉验证确保模型稳定性
   - 保留独立的测试集进行最终评估

### 2. 部署最佳实践

1. **模型版本管理**
   - 使用MLflow等工具跟踪模型版本
   - 保存完整的模型元数据
   - 建立模型回滚机制

2. **性能监控**
   - 监控预测延迟和吞吐量
   - 跟踪模型性能指标变化
   - 设置合理的告警阈值

3. **安全考虑**
   - 保护模型文件和训练数据
   - 实现API访问控制
   - 记录预测请求日志

4. **可扩展性**
   - 设计水平扩展的架构
   - 实现模型负载均衡
   - 优化预测服务性能

## 📋 相关文档

- [数据库架构文档](../reference/DATABASE_SCHEMA.md)
- [开发指南](../reference/DEVELOPMENT_GUIDE.md)
- [数据采集配置指南](../reference/DATA_COLLECTION_SETUP.md)
- [API文档](../reference/API_REFERENCE.md)
- [术语表](../reference/glossary.md)

---

**文档版本**: 1.0
**最后更新**: 2025-10-23
**维护者**: 开发团队
