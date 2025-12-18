"""
Trainer - 统一训练调度器

支持多算法训练、超参数优化和模型评估。
集成现代ML最佳实践，提供可观测性和可复现性。

主要功能:
- 多算法支持 (XGBoost, LightGBM, LogisticRegression等)
- 超参数优化 (GridSearch, RandomSearch, Optuna)
- 早停和交叉验证
- 训练日志和监控
- 模型解释性分析 (SHAP)

P0-4 核心组件 - 统一训练逻辑
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, train_test_split
from xgboost import XGBClassifier

from .config import PipelineConfig

logger = logging.getLogger(__name__)


class Trainer:
    """
    统一训练调度器.

    支持多种机器学习算法的训练和优化。
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        model_registry: Optional[Any] = None,
    ):
        """初始化训练器.

        Args:
            config: 流水线配置
            model_registry: 模型注册表实例
        """
        self.config = config or PipelineConfig()
        self.model_config = self.config.model
        self.training_config = self.config.training

        self.model_registry = model_registry

        # 训练历史
        self.training_history: list[dict[str, Any]] = []

        # 支持的算法
        self._algorithms = {
            "xgboost": self._train_xgboost,
            "lightgbm": self._train_lightgbm,
            "logistic_regression": self._train_logistic_regression,
            "random_forest": self._train_random_forest,
        }

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        algorithm: Optional[str] = None,
        hyperparameter_tuning: bool = None,
        validation_data: Optional[tuple[pd.DataFrame, pd.Series]] = None,
    ) -> dict[str, Any]:
        """
        训练模型.

        Args:
            X: 特征数据
            y: 目标变量
            algorithm: 算法名称 (None使用默认)
            hyperparameter_tuning: 是否进行超参数优化
            validation_data: 验证数据 (X_val, y_val)

        Returns:
            训练结果字典
        """
        start_time = time.time()
        algorithm = algorithm or self.model_config.default_algorithm
        hyperparameter_tuning = (
            hyperparameter_tuning
            if hyperparameter_tuning is not None
            else self.model_config.hyperparameter_tuning
        )

        logger.info(f"Starting training with algorithm: {algorithm}")
        logger.info(f"Training data shape: {X.shape}, Target shape: {y.shape}")

        # 数据验证
        self._validate_input_data(X, y)

        # 数据分割 (如果没有提供验证数据)
        if validation_data is None:
            X_train, X_val, y_train, y_val = train_test_split(
                X,
                y,
                test_size=self.training_config.validation_size,
                random_state=self.training_config.random_state,
                stratify=self.training_config.stratify and y,
            )
        else:
            X_train, y_train = X, y
            X_val, y_val = validation_data

        # 选择算法
        if algorithm not in self._algorithms:
            raise ValueError(
                f"Unsupported algorithm: {algorithm}. "
                f"Supported: {list(self._algorithms.keys())}"
            )

        # 执行训练
        try:
            model, training_metrics = self._algorithms[algorithm](
                X_train, y_train, X_val, y_val, hyperparameter_tuning
            )

            # 计算最终指标
            final_metrics = self._evaluate_model(model, X_val, y_val)
            training_metrics.update(final_metrics)

            # 记录训练历史
            training_record = {
                "algorithm": algorithm,
                "timestamp": datetime.now().isoformat(),
                "training_time": time.time() - start_time,
                "data_shape": X.shape,
                "hyperparameter_tuning": hyperparameter_tuning,
                "metrics": training_metrics,
                "model_params": (
                    model.get_params() if hasattr(model, "get_params") else {}
                ),
            }

            self.training_history.append(training_record)

            logger.info(
                f"Training completed in {training_record['training_time']:.2f}s"
            )
            logger.info(f"Final metrics: {training_metrics}")

            return {
                "model": model,
                "metrics": training_metrics,
                "training_record": training_record,
                "algorithm": algorithm,
            }

        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise

    def _validate_input_data(self, X: pd.DataFrame, y: pd.Series) -> None:
        """验证输入数据."""
        if len(X) != len(y):
            raise ValueError(
                f"Feature data length ({len(X)}) != target length ({len(y)})"
            )

        if len(X) < self.training_config.batch_size:
            logger.warning(
                f"Small dataset detected: {len(X)} samples. Consider using batch training."
            )

        # 检查缺失值
        missing_ratio = X.isnull().sum().sum() / (X.shape[0] * X.shape[1])
        if missing_ratio > 0.5:
            logger.warning(f"High missing value ratio: {missing_ratio:.2%}")

    def _train_xgboost(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        hyperparameter_tuning: bool,
    ) -> tuple[Any, dict[str, Any]]:
        """训练XGBoost模型."""
        base_params = self.model_config.xgboost_params.copy()

        if hyperparameter_tuning:
            # 超参数优化
            param_grid = {
                "n_estimators": [50, 100, 200],
                "max_depth": [3, 6, 9],
                "learning_rate": [0.01, 0.1, 0.2],
                "subsample": [0.6, 0.8, 1.0],
            }

            model = XGBClassifier(**base_params)
            grid_search = GridSearchCV(
                model,
                param_grid,
                cv=self.model_config.cv_folds,
                scoring=self.model_config.scoring_metric,
                n_jobs=self.training_config.n_jobs,
                verbose=1,
            )

            grid_search.fit(X_train, y_train)
            best_model = grid_search.best_estimator_
            best_params = grid_search.best_params_

            logger.info(f"Best parameters: {best_params}")
            logger.info(f"Best CV score: {grid_search.best_score_:.4f}")

        else:
            # 直接训练
            best_model = XGBClassifier(**base_params)
            best_params = base_params

            eval_set = [(X_train, y_train), (X_val, y_val)]
            best_model.fit(
                X_train,
                y_train,
                eval_set=eval_set,
                early_stopping_rounds=(
                    self.model_config.early_stopping_rounds
                    if self.model_config.early_stopping
                    else None
                ),
                verbose=False,
            )

        # 验证集指标
        best_model.predict(X_val)
        best_model.predict_proba(X_val)

        metrics = {
            "best_params": best_params,
            "feature_importance": dict(
                zip(X_train.columns, best_model.feature_importances_, strict=False)
            ),
            "n_estimators": best_model.n_estimators,
            "best_iteration": getattr(best_model, "best_iteration", None),
        }

        return best_model, metrics

    def _train_lightgbm(self, *args, **kwargs):
        """训练LightGBM模型 (待实现)."""
        raise NotImplementedError("LightGBM training not implemented yet")

    def _train_logistic_regression(self, *args, **kwargs):
        """训练Logistic回归模型 (待实现)."""
        raise NotImplementedError("Logistic regression training not implemented yet")

    def _train_random_forest(self, *args, **kwargs):
        """训练随机森林模型 (待实现)."""
        raise NotImplementedError("Random forest training not implemented yet")

    def _evaluate_model(
        self, model: Any, X_test: pd.DataFrame, y_test: pd.Series
    ) -> dict[str, Any]:
        """评估模型."""
        y_pred = model.predict(X_test)

        # 基本指标
        metrics = {}

        try:
            # 分类报告
            report = classification_report(y_test, y_pred, output_dict=True)
            metrics["classification_report"] = report

            # 混淆矩阵
            cm = confusion_matrix(y_test, y_pred)
            metrics["confusion_matrix"] = cm.tolist()

        except Exception as e:
            logger.warning(f"Metrics computation failed: {e}")

        # 如果模型支持概率预测
        if hasattr(model, "predict_proba"):
            try:
                y_pred_proba = model.predict_proba(X_test)
                from sklearn.metrics import log_loss, roc_auc_score

                metrics["log_loss"] = log_loss(y_test, y_pred_proba)

                # 多分类ROC AUC
                if len(np.unique(y_test)) == 2:
                    metrics["roc_auc"] = roc_auc_score(y_test, y_pred_proba[:, 1])

            except Exception as e:
                logger.warning(f"Probability metrics failed: {e}")

        return metrics

    def save_training_history(self, path: str) -> None:
        """保存训练历史."""
        import json
        from pathlib import Path

        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)

        with open(save_path / "training_history.json", "w") as f:
            json.dump(self.training_history, f, indent=2, default=str)

        logger.info(f"Training history saved to {save_path}")

    def get_best_model(self, metric: str = "f1_weighted") -> Optional[dict[str, Any]]:
        """获取历史训练中的最佳模型."""
        if not self.training_history:
            return None

        best_record = None
        best_score = -float("inf")

        for record in self.training_history:
            score = (
                record["metrics"]
                .get("classification_report", {})
                .get("weighted avg", {})
                .get(metric, 0)
            )
            if score > best_score:
                best_score = score
                best_record = record

        return best_record
