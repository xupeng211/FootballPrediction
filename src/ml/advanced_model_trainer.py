#!/usr/bin/env python3
""""
Advanced Model Trainer
高级模型训练器,支持XGBoost和LightGBM集成

Enhanced with XGBoost and LightGBM integration for football prediction models
""""

import asyncio
import logging
import pickle
from datetime import datetime
from enum import Enum

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    mean_squared_error,
    precision_score,
    recall_score,
    f1_score,
)
GridSearchCV,
train_test_split,
    StratifiedKFold,
    cross_val_score,
)
        from sklearn.preprocessing import StandardScaler, LabelEncoder

# 尝试导入XGBoost和LightGBM
try:
    import xgboost as xgb

    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logging.warning("XGBoost not available. Install with: pip install xgboost")

try:
    import lightgbm as lgb

    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False
    logging.warning("LightGBM not available. Install with: pip install lightgbm")

        from src.core.logging_system import get_logger

logger = get_logger(__name__)


class ModelType(Enum):
    """支持的模型类型"""

    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    XGBOOST_CLASSIFIER = "xgboost_classifier"
    XGBOOST_REGRESSOR = "xgboost_regressor"
    LIGHTGBM_CLASSIFIER = "lightgbm_classifier"
    LIGHTGBM_REGRESSOR = "lightgbm_regressor"


class HyperparameterGrids:
    """超参数网格配置"""

    # XGBoost参数网格
    XGBOOST_CLASSIFIER_GRID = {
        "n_estimators": [100, 200, 500],
        "max_depth": [3, 5, 7, 9],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "subsample": [0.6, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "min_child_weight": [1, 3, 5],
        "gamma": [0, 0.1, 0.2],
        "reg_alpha": [0, 0.1, 0.5],
        "reg_lambda": [1, 1.5, 2],
    }

    XGBOOST_REGRESSOR_GRID = {
        "n_estimators": [100, 200, 500],
        "max_depth": [3, 5, 7, 9],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "subsample": [0.6, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "min_child_weight": [1, 3, 5],
        "gamma": [0, 0.1, 0.2],
    }

    # LightGBM参数网格
    LIGHTGBM_CLASSIFIER_GRID = {
        "n_estimators": [100, 200, 500],
        "max_depth": [3, 5, 7, 9, -1],  # -1表示无限制
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "num_leaves": [31, 63, 127],
        "subsample": [0.6, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "reg_alpha": [0, 0.1, 0.5],
        "reg_lambda": [0, 0.1, 0.5],
        "min_child_samples": [20, 50, 100],
    }

    LIGHTGBM_REGRESSOR_GRID = {
        "n_estimators": [100, 200, 500],
        "max_depth": [3, 5, 7, 9, -1],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "num_leaves": [31, 63, 127],
        "subsample": [0.6, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "reg_alpha": [0, 0.1, 0.5],
        "reg_lambda": [0, 0.1, 0.5],
    }


class AdvancedModelTrainer:
    """高级模型训练器,支持XGBoost和LightGBM"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.model = None
        self.is_trained = False
        self.training_history: list = []
        self.performance_metrics: dict = {}
            self.feature_importance: dict = {}
        self.scaler = None
        self.label_encoder = None
        self.best_params = {}
        self.best_score = 0.0

    def _validate_model_availability(self, model_type: str) -> bool:
        """验证模型可用性"""
        if model_type in [
            ModelType.XGBOOST_CLASSIFIER.value,
            ModelType.XGBOOST_REGRESSOR.value,
        ]:
            if not XGB_AVAILABLE:
                raise ImportError(
                    "XGBoost is not available. Install with: pip install xgboost"
                )

        if model_type in [
            ModelType.LIGHTGBM_CLASSIFIER.value,
            ModelType.LIGHTGBM_REGRESSOR.value,
        ]:
            if not LGB_AVAILABLE:
                raise ImportError(
                    "LightGBM is not available. Install with: pip install lightgbm"
                )

        return True

    def _create_model(self, model_type: str, params: Dict[str, Any] = None) -> Any:
        """创建模型实例"""
        params = params or {}

        if model_type == ModelType.RANDOM_FOREST.value:
            return RandomForestClassifier(random_state=42, **params)

        elif model_type == ModelType.GRADIENT_BOOSTING.value:
            return GradientBoostingRegressor(random_state=42, **params)

        elif model_type == ModelType.XGBOOST_CLASSIFIER.value:
            default_params = {
                "objective": "multi:softprob",
                "num_class": 3,
                "eval_metric": "mlogloss",
                "random_state": 42,
                "n_jobs": -1,
                "use_label_encoder": False,
            }
            default_params.update(params)
            return xgb.XGBClassifier(**default_params)

        elif model_type == ModelType.XGBOOST_REGRESSOR.value:
            default_params = {
                "objective": "reg:squarederror",
                "eval_metric": "rmse",
                "random_state": 42,
                "n_jobs": -1,
            }
            default_params.update(params)
            return xgb.XGBRegressor(**default_params)

        elif model_type == ModelType.LIGHTGBM_CLASSIFIER.value:
            default_params = {
                "objective": "multiclass",
                "num_class": 3,
                "metric": "multi_logloss",
                "random_state": 42,
                "n_jobs": -1,
                "verbose": -1,
            }
            default_params.update(params)
            return lgb.LGBMClassifier(**default_params)

        elif model_type == ModelType.LIGHTGBM_REGRESSOR.value:
            default_params = {
                "objective": "regression",
                "metric": "rmse",
                "random_state": 42,
                "n_jobs": -1,
                "verbose": -1,
            }
            default_params.update(params)
            return lgb.LGBMRegressor(**default_params)

        else:
            raise ValueError(f"Unsupported model type: {model_type}")

    def _get_param_grid(self, model_type: str) -> Dict[str, List]:
        """获取参数网格"""
        if model_type == ModelType.XGBOOST_CLASSIFIER.value:
            return HyperparameterGrids.XGBOOST_CLASSIFIER_GRID
        elif model_type == ModelType.XGBOOST_REGRESSOR.value:
            return HyperparameterGrids.XGBOOST_REGRESSOR_GRID
        elif model_type == ModelType.LIGHTGBM_CLASSIFIER.value:
            return HyperparameterGrids.LIGHTGBM_CLASSIFIER_GRID
        elif model_type == ModelType.LIGHTGBM_REGRESSOR.value:
            return HyperparameterGrids.LIGHTGBM_REGRESSOR_GRID
        elif model_type == ModelType.RANDOM_FOREST.value:
            return {
                "n_estimators": [50, 100, 200],
                "max_depth": [5, 10, None],
                "min_samples_split": [2, 5, 10],
            }
        elif model_type == ModelType.GRADIENT_BOOSTING.value:
            return {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.1, 0.2],
                "max_depth": [3, 5, 7],
            }
        else:
            return {}

    def _preprocess_data(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """预处理数据"""
        # 处理缺失值
        X = X.fillna(X.mean())

        # 标准化特征
        if self.scaler is None:
            self.scaler = StandardScaler()
            X_scaled = pd.DataFrame(
                self.scaler.fit_transform(X), columns=X.columns, index=X.index
            )
        else:
            X_scaled = pd.DataFrame(
                self.scaler.transform(X), columns=X.columns, index=X.index
            )

        # 对分类目标进行编码
        if y.dtype == "object" or y.nunique() > 2:
            if self.label_encoder is None:
                self.label_encoder = LabelEncoder()
                y_encoded = pd.Series(self.label_encoder.fit_transform(y))
            else:
                y_encoded = pd.Series(self.label_encoder.transform(y))
        else:
            y_encoded = y

        return X_scaled, y_encoded

    async def train_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_type: str = "random_forest",
        hyperparameter_tuning: bool = True,
        validation_split: float = 0.2,
    ) -> Dict[str, Any]:
        """训练模型"""
        try:
            logger.info(f"开始训练模型: {model_type}")

            # 验证模型可用性
            self._validate_model_availability(model_type)

            # 预处理数据
            X_processed, y_processed = self._preprocess_data(X, y)

            # 数据分割
            X_train, X_test, y_train, y_test = train_test_split(
                X_processed,
                y_processed,
                test_size=validation_split,
                random_state=42,
                stratify=y_processed,
            )

            # 创建模型
            model = self._create_model(model_type)

            # 超参数调优
            if hyperparameter_tuning:
                param_grid = self._get_param_grid(model_type)
                if param_grid:
                    logger.info("开始超参数调优...")
                    grid_search = GridSearchCV(
                        model,
                        param_grid,
                        cv=3,
                        scoring="accuracy",
                        n_jobs=-1,
                        verbose=0,
                    )
                    grid_search.fit(X_train, y_train)
                    self.model = grid_search.best_estimator_
                    self.best_params = grid_search.best_params_
                    self.best_score = grid_search.best_score_
                    logger.info(
                        f"最佳参数: {self.best_params}, 最佳分数: {self.best_score:.4f}"
                    )
                else:
                    self.model = model
                    self.model.fit(X_train, y_train)
                    self.best_params = model.get_params()
            else:
                self.model = model
                self.model.fit(X_train, y_train)
                self.best_params = model.get_params()

            # 获取特征重要性
                if hasattr(self.model, "feature_importances_"):
                feature_names = X_train.columns.tolist()
                    self.feature_importance = dict(
                        zip(feature_names, self.model.feature_importances_)
                )

            # 评估模型
            y_pred = self.model.predict(X_test)

            # 计算多种指标
            metrics = {}
            if hasattr(self.model, "predict_proba"):
                try:
                    self.model.predict_proba(X_test)
                    metrics.update(
                        {
                            "accuracy": accuracy_score(y_test, y_pred),
                            "precision": precision_score(
                                y_test, y_pred, average="weighted"
                            ),
                            "recall": recall_score(y_test, y_pred, average="weighted"),
                            "f1_score": f1_score(y_test, y_pred, average="weighted"),
                        }
                    )
                    metric_name = "accuracy"
                    metric_value = metrics["accuracy"]
                except Exception as e:
                    logger.warning(f"Could not calculate probability metrics: {e}")
                    metrics["accuracy"] = accuracy_score(y_test, y_pred)
                    metric_name = "accuracy"
                    metric_value = metrics["accuracy"]
            else:
                mse = mean_squared_error(y_test, y_pred)
                metrics["mse"] = mse
                metric_name = "mse"
                metric_value = mse

            # 保存训练历史
            training_record = {
                "timestamp": datetime.now().isoformat(),
                "model_type": model_type,
                "best_params": self.best_params,
                "best_cv_score": self.best_score,
                "metrics": metrics,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": len(X_train.columns),
                "feature_importance": dict(
                    sorted(
                            self.feature_importance.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:10]
                ),
            }

            self.training_history.append(training_record)
            self.is_trained = True
            self.performance_metrics.update(metrics)

            logger.info(f"模型训练完成,{metric_name}: {metric_value:.4f}")

            return {
                "success": True,
                "model_type": model_type,
                "metrics": metrics,
                "best_params": self.best_params,
                "best_cv_score": self.best_score,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_importance": self.feature_importance,
                "feature_count": len(X_train.columns),
            }

        except Exception as e:
            logger.error(f"模型训练失败: {e}")
            return {"success": False, "error": str(e)}

    async def predict(self, features: pd.DataFrame) -> Dict[str, Any]:
        """预测"""
        try:
            if not self.is_trained:
                raise ValueError("模型尚未训练")

            # 预处理特征
            features_processed, _ = self._preprocess_data(
                features, pd.Series([0] * len(features))
            )

            predictions = self.model.predict(features_processed)
            probabilities = None

            if hasattr(self.model, "predict_proba"):
                try:
                    probabilities = self.model.predict_proba(features_processed)
                except Exception as e:
                    logger.warning(f"Could not get prediction probabilities: {e}")

            result = {
                "success": True,
                "predictions": predictions.tolist(),
                "probabilities": (
                    probabilities.tolist() if probabilities is not None else None
                ),
                "timestamp": datetime.now().isoformat(),
                "model_type": self.model.__class__.__name__,
                "feature_count": len(features_processed.columns),
            }

            # 如果是分类模型,添加预测标签
            if (
                probabilities is not None
                and hasattr(self, "label_encoder")
                and self.label_encoder
            ):
                # 将数字标签转换回原始标签
                predicted_labels = self.label_encoder.inverse_transform(predictions)
                result["predicted_labels"] = predicted_labels.tolist()

                # 添加各类别概率
                if hasattr(self.label_encoder, "classes_"):
                    class_probabilities = {}
                    for i, class_name in enumerate(self.label_encoder.classes_):
                        class_probabilities[class_name] = probabilities[:, i].tolist()
                    result["class_probabilities"] = class_probabilities

            return result

        except Exception as e:
            logger.error(f"预测失败: {e}")
            return {"success": False, "error": str(e)}

    async def monitor_performance(
        self, test_data: pd.DataFrame, test_labels: pd.Series
    ) -> Dict[str, Any]:
        """监控模型性能"""
        try:
            if not self.is_trained:
                raise ValueError("模型尚未训练")

            predictions = self.model.predict(test_data)

            if hasattr(self.model, "predict_proba"):
                accuracy = accuracy_score(test_labels, predictions)
                metric_name = "accuracy"
                metric_value = accuracy
            else:
                mse = mean_squared_error(test_labels, predictions)
                metric_name = "mse"
                metric_value = mse

            # 检查性能下降
            performance_drop = 0.0
            if metric_name in self.performance_metrics:
                baseline = self.performance_metrics[metric_name]
                if metric_name == "accuracy":
                    performance_drop = baseline - metric_value
                else:  # mse
                    performance_drop = metric_value - baseline

            # 性能记录,用于可能的日志记录或监控
            performance_record = {
                "timestamp": datetime.now(),
                metric_name: metric_value,
                "performance_drop": performance_drop,
                "alert_threshold": 0.1,
                "needs_retraining": performance_drop > 0.1,
            }
            # 记录性能数据到历史记录
            self.performance_history.append(performance_record)

            return {
                "current_performance": metric_value,
                "baseline_performance": self.performance_metrics.get(metric_name),
                "performance_drop": performance_drop,
                "needs_retraining": performance_drop > 0.1,
                "recommendation": (
                    "重新训练模型" if performance_drop > 0.1 else "继续监控"
                ),
            }

        except Exception as e:
            logger.error(f"性能监控失败: {e}")
            return {"error": str(e), "needs_retraining": True}

    def save_model(self, filepath: str) -> bool:
        """保存模型"""
        try:
            model_data = {
                "model": self.model,
                "is_trained": self.is_trained,
                "training_history": self.training_history,
                "performance_metrics": self.performance_metrics,
                "config": self.config,
            }

            joblib.dump(model_data, filepath)
            logger.info(f"模型已保存到: {filepath}")
            return True

        except Exception as e:
            logger.error(f"模型保存失败: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """加载模型"""
        try:
            model_data = joblib.load(filepath)

            self.model = model_data["model"]
            self.is_trained = model_data["is_trained"]
            self.training_history = model_data["training_history"]
            self.performance_metrics = model_data["performance_metrics"]
            self.config = model_data["config"]

            logger.info(f"模型已从{filepath}加载")
            return True

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            return False


# 创建全局实例
advancedmodeltrainer_instance = AdvancedModelTrainer()


async def main():
    """主函数示例"""
    # 示例数据
    np.random.seed(42)
    X = pd.DataFrame(
        np.random.randn(100, 5), columns=[f"feature_{i}" for i in range(5)]
    )
    y = pd.Series(np.random.choice([0, 1], 100))

    trainer = AdvancedModelTrainer()

    # 训练模型
    training_result = await trainer.train_model(X, y)
    print("训练结果:", training_result)

    # 预测
    test_features = pd.DataFrame(
        np.random.randn(5, 5), columns=[f"feature_{i}" for i in range(5)]
    )
    prediction_result = await trainer.predict(test_features)
    print("预测结果:", prediction_result)

    # 性能监控
    monitoring_result = await trainer.monitor_performance(X, y)
    print("监控结果:", monitoring_result)


class EnsembleTrainer:
    """集成学习训练器,支持多种模型的集成"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.models: Dict[str, AdvancedModelTrainer] = {}
        self.weights: Dict[str, float] = {}
        self.ensemble_method = "weighted_voting"  # or "stacking"
        self.meta_model = None
        self.is_trained = False
        self.logger = get_logger(self.__class__.__name__)

    async def train_ensemble(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_types: List[str] = None,
        validation_split: float = 0.2,
        hyperparameter_tuning: bool = True,
    ) -> Dict[str, Any]:
        """训练集成模型"""
        try:
            self.logger.info("开始训练集成模型...")

            if model_types is None:
                model_types = [
                    ModelType.XGBOOST_CLASSIFIER.value,
                    ModelType.LIGHTGBM_CLASSIFIER.value,
                    ModelType.RANDOM_FOREST.value,
                ]

            # 过滤可用的模型类型
            available_models = []
            for model_type in model_types:
                try:
                    # 验证模型可用性
                    if model_type in [
                        ModelType.XGBOOST_CLASSIFIER.value,
                        ModelType.XGBOOST_REGRESSOR.value,
                    ]:
                        if not XGB_AVAILABLE:
                            continue
                    if model_type in [
                        ModelType.LIGHTGBM_CLASSIFIER.value,
                        ModelType.LIGHTGBM_REGRESSOR.value,
                    ]:
                        if not LGB_AVAILABLE:
                            continue
                    available_models.append(model_type)
            except Exception:
                    continue

            if not available_models:
                raise ValueError("没有可用的模型进行集成训练")

            # 数据预处理
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=validation_split, random_state=42, stratify=y
            )

            # 训练各个基础模型
            model_results = {}
            val_scores = []

            for model_type in available_models:
                self.logger.info(f"训练基础模型: {model_type}")
                trainer = AdvancedModelTrainer(self.config)
                result = await trainer.train_model(
                    X_train,
                    y_train,
                    model_type,
                    hyperparameter_tuning,
                    validation_split,
                )

                if result["success"]:
                    self.models[model_type] = trainer
                    model_results[model_type] = result

                    # 获取验证集分数用于权重计算
                    val_score = result.get("best_cv_score", 0)
                    if val_score > 0:
                        val_scores.append(val_score)
                    else:
                        # 如果没有CV分数,使用测试集准确率
                        metrics = result.get("metrics", {})
                        val_score = metrics.get("accuracy", 0)
                        val_scores.append(val_score)

                    self.logger.info(f"{model_type} 验证分数: {val_score:.4f}")
                else:
                    self.logger.warning(
                        f"模型 {model_type} 训练失败: {result.get('error')}"
                    )

            if not self.models:
                raise ValueError("所有基础模型训练失败")

            # 计算模型权重
            if len(val_scores) > 0:
                total_score = sum(val_scores)
                if total_score > 0:
                    for i, model_type in enumerate(self.models.keys()):
                        self.weights[model_type] = val_scores[i] / total_score
                else:
                    # 平均权重
                    weight = 1.0 / len(self.models)
                    for model_type in self.models.keys():
                        self.weights[model_type] = weight
            else:
                # 平均权重
                weight = 1.0 / len(self.models)
                for model_type in self.models.keys():
                    self.weights[model_type] = weight

            # 如果使用stacking方法,训练元模型
            if self.ensemble_method == "stacking":
                await self._train_meta_model(X_train, y_train, X_test, y_test)

            # 评估集成模型
            ensemble_result = await self.evaluate_ensemble(X_test, y_test)

            self.is_trained = True

            result = {
                "success": True,
                "ensemble_method": self.ensemble_method,
                "base_models": model_results,
                "model_weights": self.weights,
                "ensemble_metrics": ensemble_result,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_count": len(X.columns),
            }

            self.logger.info(f"集成模型训练完成,权重: {self.weights}")
            return result

        except Exception as e:
            self.logger.error(f"集成模型训练失败: {e}")
            return {"success": False, "error": str(e)}

    async def _train_meta_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
    ):
        """训练元模型（用于stacking）"""
        try:
            # 获取基础模型的预测结果作为元特征
            meta_features_train = []
            meta_features_val = []

            for model_type, trainer in self.models.items():
                train_pred = await trainer.predict(X_train)
                val_pred = await trainer.predict(X_val)

                if train_pred["success"] and val_pred["success"]:
                    # 使用概率作为元特征
                    if train_pred["probabilities"]:
                        meta_features_train.append(train_pred["probabilities"])
                        meta_features_val.append(val_pred["probabilities"])
                    else:
                        meta_features_train.append(
                            np.array(train_pred["predictions"]).reshape(-1, 1)
                        )
                        meta_features_val.append(
                            np.array(val_pred["predictions"]).reshape(-1, 1)
                        )

            if meta_features_train:
                # 组合元特征
                X_meta_train = np.hstack(meta_features_train)
                np.hstack(meta_features_val)

                # 训练元模型（使用简单的逻辑回归）
                        from sklearn.linear_model import LogisticRegression

                self.meta_model = LogisticRegression(random_state=42)
                self.meta_model.fit(X_meta_train, y_train)

                self.logger.info("元模型训练完成")
            else:
                self.logger.warning("无法训练元模型,回退到加权投票")
                self.ensemble_method = "weighted_voting"

        except Exception as e:
            self.logger.error(f"元模型训练失败: {e}")
            self.ensemble_method = "weighted_voting"

    async def predict_ensemble(self, features: pd.DataFrame) -> Dict[str, Any]:
        """集成预测"""
        try:
            if not self.is_trained:
                raise ValueError("集成模型尚未训练")

            if not self.models:
                raise ValueError("没有可用的基础模型")

            predictions = {}
            probabilities = {}

            # 获取各模型预测
            for model_type, trainer in self.models.items():
                result = await trainer.predict(features)
                if result["success"]:
                    predictions[model_type] = result["predictions"]
                    if result["probabilities"]:
                        probabilities[model_type] = np.array(result["probabilities"])

            if not predictions:
                raise ValueError("所有模型预测失败")

            # 集成预测
            if self.ensemble_method == "weighted_voting":
                ensemble_predictions = self._weighted_voting(predictions, probabilities)
            else:  # stacking
                ensemble_predictions = await self._stacking_predict(
                    features, probabilities
                )

            return {
                "success": True,
                "ensemble_method": self.ensemble_method,
                "predictions": ensemble_predictions["predictions"],
                "probabilities": ensemble_predictions.get("probabilities"),
                "model_weights": self.weights,
                "base_predictions": predictions,
                "timestamp": datetime.now().isoformat(),
                "feature_count": len(features.columns),
            }

        except Exception as e:
            self.logger.error(f"集成预测失败: {e}")
            return {"success": False, "error": str(e)}

    def _weighted_voting(
        self, predictions: Dict[str, List], probabilities: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        """加权投票"""
        try:
            # 如果有概率预测,使用加权平均概率
            if probabilities and len(probabilities) > 0:
                # 确保所有概率矩阵形状一致
                sample_count = len(list(probabilities.values())[0])
                num_classes = list(probabilities.values())[0].shape[1]

                weighted_proba = np.zeros((sample_count, num_classes))

                for model_type, proba in probabilities.items():
                    weight = self.weights.get(model_type, 0)
                    weighted_proba += proba * weight

                # 归一化
                weighted_proba = weighted_proba / np.sum(
                    weighted_proba, axis=1, keepdims=True
                )

                final_predictions = np.argmax(weighted_proba, axis=1)

                return {
                    "predictions": final_predictions.tolist(),
                    "probabilities": weighted_proba.tolist(),
                }
            else:
                # 基于预测类别的加权投票
                sample_count = len(list(predictions.values())[0])
                final_predictions = []

                for i in range(sample_count):
                    vote_counts = {}
                    for model_type, preds in predictions.items():
                        pred = preds[i]
                        weight = self.weights.get(model_type, 0)
                        vote_counts[pred] = vote_counts.get(pred, 0) + weight

                    # 选择得票最多的类别
                    final_prediction = max(
                        vote_counts.keys(), key=lambda k: vote_counts[k]
                    )
                    final_predictions.append(final_prediction)

                return {"predictions": final_predictions, "probabilities": None}

        except Exception as e:
            self.logger.error(f"加权投票失败: {e}")
            # 回退到简单平均
            avg_prediction = np.mean(list(predictions.values()), axis=0)
            return {"predictions": avg_prediction.tolist(), "probabilities": None}

    async def _stacking_predict(
        self, features: pd.DataFrame, probabilities: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        """Stacking预测"""
        try:
            if self.meta_model is None:
                # 回退到加权投票
                return self._weighted_voting(
                    {
                        model_type: await trainer.predict(features)
                        for model_type, trainer in self.models.items()
                    },
                    probabilities,
                )

            # 获取基础模型预测作为元特征
            meta_features = []
            for model_type, trainer in self.models.items():
                result = await trainer.predict(features)
                if result["success"] and result["probabilities"]:
                    meta_features.append(np.array(result["probabilities"]))

            if meta_features:
                X_meta = np.hstack(meta_features)
                meta_predictions = self.meta_model.predict(X_meta)

                if hasattr(self.meta_model, "predict_proba"):
                    meta_probabilities = self.meta_model.predict_proba(X_meta)
                    return {
                        "predictions": meta_predictions.tolist(),
                        "probabilities": meta_probabilities.tolist(),
                    }
                else:
                    return {
                        "predictions": meta_predictions.tolist(),
                        "probabilities": None,
                    }
            else:
                # 回退到加权投票
                return self._weighted_voting({}, probabilities)

        except Exception as e:
            self.logger.error(f"Stacking预测失败: {e}")
            # 回退到加权投票
            return self._weighted_voting({}, probabilities)

    async def evaluate_ensemble(
        self, X_test: pd.DataFrame, y_test: pd.Series
    ) -> Dict[str, float]:
        """评估集成模型"""
        try:
            result = await self.predict_ensemble(X_test)
            if not result["success"]:
                raise ValueError("集成预测失败")

            predictions = result["predictions"]

            metrics = {
                "accuracy": accuracy_score(y_test, predictions),
                "precision": precision_score(y_test, predictions, average="weighted"),
                "recall": recall_score(y_test, predictions, average="weighted"),
                "f1_score": f1_score(y_test, predictions, average="weighted"),
            }

            if result["probabilities"]:
                try:
                            from sklearn.metrics import log_loss

                    metrics["log_loss"] = log_loss(y_test, result["probabilities"])
                except Exception as e:
                    self.logger.warning(f"无法计算log_loss: {e}")

            return metrics

        except Exception as e:
            self.logger.error(f"集成模型评估失败: {e}")
            return {}

    def save_ensemble(self, filepath: str) -> bool:
        """保存集成模型"""
        try:
            ensemble_data = {
                "models": {},
                "weights": self.weights,
                "ensemble_method": self.ensemble_method,
                "meta_model": self.meta_model,
                "config": self.config,
                "is_trained": self.is_trained,
            }

            # 保存各个基础模型
            for model_type, trainer in self.models.items():
                model_path = filepath.replace(".pkl", f"_{model_type}.pkl")
                if trainer.save_model(model_path):
                    ensemble_data["models"][model_type] = model_path

            # 保存集成信息
            with open(filepath, "wb") as f:
                pickle.dump(ensemble_data, f)

            self.logger.info(f"集成模型已保存到: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"集成模型保存失败: {e}")
            return False

    def load_ensemble(self, filepath: str) -> bool:
        """加载集成模型"""
        try:
            with open(filepath, "rb") as f:
                ensemble_data = pickle.load(f)

            self.weights = ensemble_data["weights"]
            self.ensemble_method = ensemble_data["ensemble_method"]
            self.meta_model = ensemble_data["meta_model"]
            self.config = ensemble_data["config"]
            self.is_trained = ensemble_data["is_trained"]

            # 加载各个基础模型
            self.models = {}
            for model_type, model_path in ensemble_data["models"].items():
                trainer = AdvancedModelTrainer(self.config)
                if trainer.load_model(model_path):
                    self.models[model_type] = trainer

            self.logger.info(f"集成模型已从 {filepath} 加载")
            return True

        except Exception as e:
            self.logger.error(f"集成模型加载失败: {e}")
            return False


# 便捷函数
async def train_advanced_ensemble_model(
    X: pd.DataFrame,
    y: pd.Series,
    model_types: List[str] = None,
    ensemble_method: str = "weighted_voting",
    hyperparameter_tuning: bool = True,
) -> Dict[str, Any]:
    """训练高级集成模型的便捷函数"""
    trainer = EnsembleTrainer()
    trainer.ensemble_method = ensemble_method

    return await trainer.train_ensemble(X, y, model_types, 0.2, hyperparameter_tuning)


if __name__ == "__main__":
    asyncio.run(main())
