"""
XGBoost 超参数优化模块
XGBoost Hyperparameter Optimization Module

实现基于 GridSearchCV 的系统化超参数调优，符合 SRS 要求。
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

# 尝试导入所需库
try:
    from sklearn.metrics import accuracy_score, classification_report, f1_score
    from sklearn.model_selection import GridSearchCV, StratifiedKFold
    from sklearn.preprocessing import LabelEncoder
    import xgboost as xgb
    from xgboost import XGBClassifier

    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    logging.warning(f"Required dependencies not available: {e}")

# 配置日志
logger = logging.getLogger(__name__)


class XGBoostHyperparameterOptimizer:
    """XGBoost 超参数优化器."""

    def __init__(
        self,
        model_name: str = "xgboost_optimized",
        output_dir: str = "models",
        random_state: int = 42,
        cv_folds: int = 5,
        scoring_metric: str = "f1_weighted",
        n_jobs: int = -1,
        verbose: int = 1,
    ):
        """初始化超参数优化器.

        Args:
            model_name: 模型名称
            output_dir: 输出目录
            random_state: 随机种子
            cv_folds: 交叉验证折数
            scoring_metric: 评估指标
            n_jobs: 并行作业数
            verbose: 详细输出级别
        """
        if not HAS_DEPENDENCIES:
            raise ImportError(
                "Required dependencies not available. Please install scikit-learn and xgboost"
            )

        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.random_state = random_state
        self.cv_folds = cv_folds
        self.scoring_metric = scoring_metric
        self.n_jobs = n_jobs
        self.verbose = verbose

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化变量
        self.best_model = None
        self.best_params = None
        self.best_score = None
        self.optimization_history = []
        self.is_optimized = False

        logger.info(f"Initialized XGBoostHyperparameterOptimizer: {model_name}")

    def create_parameter_grid(self, debug_mode: bool = False) -> dict[str, list[Any]]:
        """创建参数搜索网格.

        Args:
            debug_mode: 调试模式，使用更小的参数网格

        Returns:
            参数搜索网格
        """
        if debug_mode:
            # 调试模式：较小的参数网格，用于快速测试
            param_grid = {
                "learning_rate": [0.05, 0.1],
                "max_depth": [3, 5],
                "n_estimators": [100, 200],
                "subsample": [0.8, 1.0],
            }
            logger.info("Using debug parameter grid (smaller search space)")
        else:
            # 生产模式：完整的参数网格，符合SRS要求
            param_grid = {
                "learning_rate": [0.01, 0.05, 0.1],
                "max_depth": [3, 5, 7],
                "n_estimators": [100, 200],
                "subsample": [0.8, 1.0],
                "colsample_bytree": [0.8, 0.9, 1.0],
                "reg_alpha": [0, 0.1],
                "reg_lambda": [1, 2],
                "min_child_weight": [1, 3],
            }
            logger.info("Using full parameter grid (comprehensive search)")

        return param_grid

    def validate_data(
        self, X: pd.DataFrame, y: pd.Series
    ) -> tuple[pd.DataFrame, pd.Series]:
        """验证和准备训练数据.

        Args:
            X: 特征数据
            y: 目标变量

        Returns:
            验证后的数据
        """
        logger.info(f"Input data shape: X={X.shape}, y={y.shape}")

        # 检查数据完整性
        if X.isnull().any().any():
            logger.warning("Found missing values in features, filling with median")
            X = X.fillna(X.median())

        if y.isnull().any():
            logger.warning("Found missing values in target, removing rows")
            valid_indices = ~y.isnull()
            X = X.loc[valid_indices]
            y = y.loc[valid_indices]

        # 编码类别标签
        if y.dtype == "object":
            logger.info("Encoding categorical target variable")
            label_encoder = LabelEncoder()
            y_encoded = pd.Series(label_encoder.fit_transform(y))
            self.label_encoder = label_encoder
        else:
            y_encoded = y
            self.label_encoder = None

        logger.info(f"Validated data shape: X={X.shape}, y={y_encoded.shape}")
        return X, y_encoded

    def optimize(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        param_grid: dict[str, list[Any]] | None = None,
        debug_mode: bool = False,
        save_best_model: bool = True,
    ) -> dict[str, Any]:
        """执行超参数优化.

        Args:
            X: 特征数据
            y: 目标变量
            param_grid: 自定义参数网格
            debug_mode: 调试模式
            save_best_model: 是否保存最佳模型

        Returns:
            优化结果
        """
        start_time = time.time()

        # 验证数据
        X_validated, y_validated = self.validate_data(X, y)

        # 创建参数网格
        if param_grid is None:
            param_grid = self.create_parameter_grid(debug_mode)

        # 基础 XGBoost 模型
        base_model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            use_label_encoder=False,
        )

        # 交叉验证策略
        cv_strategy = StratifiedKFold(
            n_splits=self.cv_folds, shuffle=True, random_state=self.random_state
        )

        logger.info(f"Starting GridSearchCV with {self.cv_folds}-fold cross validation")
        logger.info(
            f"Parameter grid size: {self._calculate_grid_size(param_grid)} combinations"
        )

        try:
            # GridSearchCV 优化
            grid_search = GridSearchCV(
                estimator=base_model,
                param_grid=param_grid,
                cv=cv_strategy,
                scoring=self.scoring_metric,
                n_jobs=self.n_jobs,
                verbose=self.verbose,
                return_train_score=True,
                refit=True,
            )

            # 执行搜索
            grid_search.fit(X_validated, y_validated)

            # 提取结果
            self.best_model = grid_search.best_estimator_
            self.best_params = grid_search.best_params_
            self.best_score = grid_search.best_score_

            # 记录优化历史
            self.optimization_history = self._extract_optimization_history(grid_search)

            optimization_time = time.time() - start_time
            logger.info(f"Optimization completed in {optimization_time:.2f} seconds")
            logger.info(f"Best {self.scoring_metric}: {self.best_score:.4f}")
            logger.info(f"Best parameters: {self.best_params}")

            # 设置为已优化（在保存之前）
            self.is_optimized = True

            # 保存最佳模型
            if save_best_model:
                self._save_optimization_results()

            return {
                "best_model": self.best_model,
                "best_params": self.best_params,
                "best_score": self.best_score,
                "optimization_time": optimization_time,
                "optimization_history": self.optimization_history,
                "cv_results": grid_search.cv_results_,
            }

        except Exception as e:
            logger.error(f"Hyperparameter optimization failed: {e}")
            raise

    def _calculate_grid_size(self, param_grid: dict[str, list[Any]]) -> int:
        """计算参数网格大小."""
        size = 1
        for param_values in param_grid.values():
            size *= len(param_values)
        return size

    def _extract_optimization_history(
        self, grid_search: GridSearchCV
    ) -> list[dict[str, Any]]:
        """提取优化历史记录."""
        cv_results = grid_search.cv_results_
        history = []

        for i in range(len(cv_results["params"])):
            record = {
                "rank": cv_results["rank_test_score"][i],
                "params": cv_results["params"][i],
                "mean_test_score": cv_results["mean_test_score"][i],
                "std_test_score": cv_results["std_test_score"][i],
                "mean_train_score": cv_results["mean_train_score"][i],
                "std_train_score": cv_results["std_train_score"][i],
                "fit_time": cv_results["mean_fit_time"][i],
                "score_time": cv_results["mean_score_time"][i],
            }
            history.append(record)

        # 按排名排序
        history.sort(key=lambda x: x["rank"])
        return history

    def _convert_history_for_json(self) -> list[dict[str, Any]]:
        """转换优化历史为JSON可序列化格式."""
        json_history = []
        for record in self.optimization_history:
            json_record = {}
            for key, value in record.items():
                if isinstance(value, np.integer):
                    json_record[key] = int(value)
                elif isinstance(value, np.floating):
                    json_record[key] = float(value)
                elif isinstance(value, np.ndarray):
                    json_record[key] = value.tolist()
                else:
                    json_record[key] = value
            json_history.append(json_record)
        return json_history

    def _save_optimization_results(self) -> None:
        """保存优化结果."""
        if not self.is_optimized:
            logger.warning("No optimization results to save")
            return

        try:
            # 保存最佳模型
            model_path = self.output_dir / f"{self.model_name}_best.pkl"
            import pickle

            with open(model_path, "wb") as f:
                pickle.dump(self.best_model, f)

            # 保存优化结果
            results = {
                "model_name": self.model_name,
                "best_params": self.best_params,
                "best_score": float(self.best_score),  # 确保JSON可序列化
                "scoring_metric": self.scoring_metric,
                "cv_folds": int(self.cv_folds),  # 确保JSON可序列化
                "optimization_history": self._convert_history_for_json(),
                "timestamp": datetime.now().isoformat(),
                "random_state": int(self.random_state),  # 确保JSON可序列化
            }

            results_path = (
                self.output_dir / f"{self.model_name}_optimization_results.json"
            )
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)

            # 保存详细历史到 CSV
            if self.optimization_history:
                history_df = pd.DataFrame(self.optimization_history)
                history_path = (
                    self.output_dir / f"{self.model_name}_optimization_history.csv"
                )
                history_df.to_csv(history_path, index=False)

            logger.info(f"Optimization results saved to {self.output_dir}")
            logger.info(f"Best model: {model_path}")
            logger.info(f"Results JSON: {results_path}")
            logger.info(f"History CSV: {history_path}")

        except Exception as e:
            logger.error(f"Failed to save optimization results: {e}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """使用最佳模型进行预测.

        Args:
            X: 特征数据

        Returns:
            预测结果
        """
        if not self.is_optimized:
            raise ValueError("Model must be optimized before making predictions")

        predictions = self.best_model.predict(X)

        # 如果有标签编码器，解码预测结果
        if self.label_encoder is not None:
            predictions = self.label_encoder.inverse_transform(predictions)

        return predictions

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """获取预测概率.

        Args:
            X: 特征数据

        Returns:
            预测概率
        """
        if not self.is_optimized:
            raise ValueError("Model must be optimized before making predictions")

        return self.best_model.predict_proba(X)

    def evaluate_model(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
        """评估最佳模型性能.

        Args:
            X_test: 测试特征数据
            y_test: 测试目标数据

        Returns:
            评估结果
        """
        if not self.is_optimized:
            raise ValueError("Model must be optimized before evaluation")

        # 预测
        y_pred = self.predict(X_test)
        y_pred_proba = self.predict_proba(X_test)

        # 计算评估指标
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")
        classification_rep = classification_report(y_test, y_pred, output_dict=True)

        results = {
            "accuracy": accuracy,
            "f1_weighted": f1,
            "classification_report": classification_rep,
            "predictions": y_pred.tolist(),
            "probabilities": y_pred_proba.tolist(),
        }

        logger.info(f"Model evaluation - Accuracy: {accuracy:.4f}, F1: {f1:.4f}")
        return results

    def get_feature_importance(self) -> np.ndarray | None:
        """获取特征重要性."""
        if not self.is_optimized:
            logger.warning("Model not optimized, no feature importance available")
            return None

        try:
            if hasattr(self.best_model, "feature_importances_"):
                return self.best_model.feature_importances_
            else:
                logger.warning("Model does not support feature importance")
                return None
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return None

    def load_optimization_results(
        self, results_path: str, model_path: str
    ) -> "XGBoostHyperparameterOptimizer":
        """加载优化结果.

        Args:
            results_path: 优化结果 JSON 文件路径
            model_path: 最佳模型 pickle 文件路径

        Returns:
            自身实例
        """
        try:
            # 加载优化结果
            with open(results_path) as f:
                results = json.load(f)

            self.best_params = results["best_params"]
            self.best_score = results["best_score"]
            self.optimization_history = results.get("optimization_history", [])
            self.label_encoder = None  # 初始化label_encoder属性

            # 加载最佳模型
            import pickle

            with open(model_path, "rb") as f:
                self.best_model = pickle.load(f)

            self.is_optimized = True
            logger.info(f"Optimization results loaded from {results_path}")
            logger.info(f"Best model loaded from {model_path}")

            return self

        except Exception as e:
            logger.error(f"Failed to load optimization results: {e}")
            raise

    @staticmethod
    def create_default_optimizer() -> "XGBoostHyperparameterOptimizer":
        """创建默认配置的优化器."""
        return XGBoostHyperparameterOptimizer(
            model_name="football_xgboost_v2",
            output_dir="models",
            cv_folds=5,
            scoring_metric="f1_weighted",
        )

    @staticmethod
    def create_debug_optimizer() -> "XGBoostHyperparameterOptimizer":
        """创建调试模式的优化器."""
        return XGBoostHyperparameterOptimizer(
            model_name="football_xgboost_debug",
            output_dir="models/debug",
            cv_folds=3,  # 更少的交叉验证折数
            scoring_metric="f1_weighted",
            verbose=2,  # 更详细的输出
        )


# 便捷函数
def optimize_xgboost_model(
    X: pd.DataFrame,
    y: pd.Series,
    model_name: str = "football_xgboost_optimized",
    debug_mode: bool = False,
    custom_param_grid: dict[str, list[Any]] | None = None,
) -> dict[str, Any]:
    """一键优化 XGBoost 模型的便捷函数.

    Args:
        X: 特征数据
        y: 目标变量
        model_name: 模型名称
        debug_mode: 调试模式
        custom_param_grid: 自定义参数网格

    Returns:
        优化结果
    """
    optimizer = XGBoostHyperparameterOptimizer(model_name=model_name)
    return optimizer.optimize(X, y, param_grid=custom_param_grid, debug_mode=debug_mode)


if __name__ == "__main__":
    # 示例用法
    logger.info("XGBoost 超参数优化模块示例")

    if HAS_DEPENDENCIES:
        # 创建模拟数据
        np.random.seed(42)
        n_samples = 1000
        n_features = 10

        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)],
        )
        y = pd.Series(np.random.randint(0, 2, n_samples))

        # 调试模式优化
        logger.info("Running debug mode optimization...")
        debug_results = optimize_xgboost_model(X, y, debug_mode=True)
        logger.info(f"Debug results: {debug_results['best_score']:.4f}")

    else:
        logger.warning("Dependencies not available, skipping example")
