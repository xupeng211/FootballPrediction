"""足球预测完整管道
Football Prediction Complete Pipeline.

结合特征工程管道和 XGBoost 模型训练的完整示例。
"""

import logging
from pathlib import Path
from typing import Any

# 尝试导入所需库
try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import train_test_split

    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False

# 导入项目模块
try:
    from src.features.feature_engineer import (
        FeaturePipelineBuilder,
        create_default_football_pipeline,
    )
    from src.models.model_training import HAS_XGB, BaselineModelTrainer
    from src.ml.feature_selector import FeatureSelector

    HAS_PROJECT_MODULES = True
except ImportError:
    HAS_PROJECT_MODULES = False

logger = logging.getLogger(__name__)


class FootballPredictionPipeline:
    """足球预测完整管道.

    整合特征工程、模型训练和预测的端到端解决方案。
    """

    def __init__(
        self,
        model_name: str = "football_xgboost",
        output_dir: str = "models",
        use_mlflow: bool = True,
        random_state: int = 42,
        enable_feature_selection: bool = True,
        feature_selection_params: dict = None,
    ):
        """初始化预测管道.

        Args:
            model_name: 模型名称
            output_dir: 模型输出目录
            use_mlflow: 是否使用 MLflow
            random_state: 随机种子
            enable_feature_selection: 是否启用特征选择
            feature_selection_params: 特征选择参数
        """
        if not HAS_DEPENDENCIES:
            raise ImportError(
                "Required dependencies not available. Please install pandas, numpy, scikit-learn"
            )

        if not HAS_PROJECT_MODULES:
            raise ImportError("Required project modules not available")

        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.use_mlflow = use_mlflow
        self.random_state = random_state
        self.enable_feature_selection = enable_feature_selection

        # 初始化组件
        self.feature_pipeline = None
        self.model_trainer = None
        self.feature_selector = None
        self.is_fitted = False

        # 特征选择参数
        default_feature_selection_params = {
            "task_type": "classification",
            "correlation_threshold": 0.95,
            "min_features": 5,
            "max_features": 50,
            "random_state": random_state,
        }
        self.feature_selection_params = {
            **default_feature_selection_params,
            **(feature_selection_params or {}),
        }

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized FootballPredictionPipeline: {model_name}")
        if self.enable_feature_selection:
            logger.info(
                f"Feature selection enabled with params: {self.feature_selection_params}"
            )

    def build_feature_pipeline(
        self,
        numeric_features: list = None,
        categorical_features: list = None,
        custom_features: list = None,
        numeric_strategy: str = "standard",
        categorical_strategy: str = "onehot",
        include_football_features: bool = True,
    ) -> "FootballPredictionPipeline":
        """构建特征工程管道.

        Args:
            numeric_features: 数值特征列表
            categorical_features: 类别特征列表
            custom_features: 自定义特征列表
            numeric_strategy: 数值特征处理策略
            categorical_strategy: 类别特征处理策略
            include_football_features: 是否包含足球特定特征

        Returns:
            自身实例，支持链式调用
        """
        # 创建特征管道构建器
        builder = FeaturePipelineBuilder()

        # 添加自定义特征
        if numeric_features:
            for feature in numeric_features:
                builder.add_numeric_feature(feature)

        if categorical_features:
            for feature in categorical_features:
                builder.add_categorical_feature(feature)

        if custom_features:
            for feature in custom_features:
                builder.add_custom_feature(feature)

        # 构建管道
        self.feature_pipeline = builder.build_pipeline(
            numeric_strategy=numeric_strategy,
            categorical_strategy=categorical_strategy,
            include_football_features=include_football_features,
            handle_missing=True,
        )

        logger.info("Feature pipeline built successfully")
        return self

    def prepare_data(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2,
        validate_features: bool = True,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """准备训练和测试数据.

        Args:
            X: 特征数据
            y: 标签数据
            test_size: 测试集比例
            validate_features: 是否验证特征

        Returns:
            训练和测试数据的元组
        """
        if validate_features and self.feature_pipeline:
            is_valid, missing_features = self.feature_pipeline.validate_features(X)
            if not is_valid:
                logger.warning(f"Missing features in data: {missing_features}")

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=y
        )

        logger.info(f"Data prepared - Train: {len(X_train)}, Test: {len(X_test)}")
        return X_train, X_test, y_train, y_test

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None,
        model_type: str = "xgboost",
        xgboost_params: dict[str, Any] = None,
        optimize_hyperparameters: bool = False,
        n_trials: int = 50,
        feature_selection_top_k: int = 20,
    ) -> dict[str, Any]:
        """训练预测模型.

        Args:
            X_train: 训练特征数据
            y_train: 训练标签数据
            X_val: 验证特征数据
            y_val: 验证标签数据
            model_type: 模型类型
            xgboost_params: XGBoost 参数
            optimize_hyperparameters: 是否优化超参数
            n_trials: 优化试验次数
            feature_selection_top_k: 特征选择保留的top_k特征数

        Returns:
            训练结果字典
        """
        # 特征工程
        if self.feature_pipeline:
            X_train_processed = self.feature_pipeline.fit_transform(X_train, y_train)
            if X_val is not None:
                X_val_processed = self.feature_pipeline.transform(X_val)
            else:
                X_val_processed = None
        else:
            X_train_processed = X_train
            X_val_processed = X_val

        # 特征选择
        if self.enable_feature_selection:
            logger.info("开始特征选择...")

            # 确定任务类型
            task_type = "classification" if len(y_train.unique()) < 20 else "regression"

            # 初始化特征选择器
            self.feature_selector = FeatureSelector(
                task_type=task_type, **self.feature_selection_params
            )

            # 执行特征选择
            selected_features = self.feature_selector.select_features(
                X_train_processed,
                y_train,
                top_k=feature_selection_top_k,
                remove_collinear=True,
            )

            # 应用特征选择
            X_train_processed = X_train_processed[selected_features]
            if X_val_processed is not None:
                X_val_processed = X_val_processed[selected_features]

            # 保存选择的特征列表
            selected_features_path = self.output_dir / "selected_features.json"
            with open(selected_features_path, "w", encoding="utf-8") as f:
                import json

                json.dump(
                    {
                        "selected_features": selected_features,
                        "removed_features": self.feature_selector.removed_features,
                        "selection_params": self.feature_selection_params,
                        "task_type": task_type,
                        "selection_time": pd.Timestamp.now().isoformat(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            logger.info(
                f"特征选择完成: 从 {X_train.shape[1]} 个特征中选择 {len(selected_features)} 个"
            )
            logger.info(f"选择的特征: {selected_features}")

            # 保存特征选择结果
            feature_selection_path = self.output_dir / "feature_selection_results.json"
            self.feature_selector.save_selection_results(str(feature_selection_path))

        # 创建模型训练器
        self.model_trainer = BaselineModelTrainer(
            model_name=self.model_name,
            model_type=model_type,
            output_dir=str(self.output_dir),
            use_mlflow=self.use_mlflow,
        )

        # 训练模型
        if model_type == "xgboost" and HAS_XGB:
            if optimize_hyperparameters and X_val is not None and y_val is not None:
                # 超参数优化
                optimization_result = (
                    self.model_trainer.optimize_xgboost_hyperparameters(
                        X_train_processed,
                        y_train,
                        X_val_processed,
                        y_val,
                        n_trials=n_trials,
                    )
                )

                # 使用最佳参数训练
                best_params = optimization_result["best_params"]
                logger.info(f"Using optimized parameters: {best_params}")

                training_result = self.model_trainer.train_xgboost(
                    X_train_processed,
                    y_train,
                    X_val_processed,
                    y_val,
                    params=best_params,
                )
            else:
                # 使用默认或指定参数训练
                training_result = self.model_trainer.train_xgboost(
                    X_train_processed,
                    y_train,
                    X_val_processed,
                    y_val,
                    params=xgboost_params,
                )
        else:
            # 使用其他模型类型
            training_result = self.model_trainer.train(
                X_train_processed, y_train, X_val_processed, y_val
            )

        # 在训练结果中添加特征选择信息
        if self.enable_feature_selection and self.feature_selector:
            training_result["feature_selection"] = {
                "enabled": True,
                "original_features": (
                    X_train.shape[1] if self.feature_pipeline else X_train.shape[1]
                ),
                "selected_features": len(selected_features),
                "selected_feature_names": selected_features,
                "removed_features": len(self.feature_selector.removed_features),
                "feature_importance_available": self.feature_selector.feature_importance_df
                is not None,
            }
        else:
            training_result["feature_selection"] = {"enabled": False}

        self.is_fitted = True
        return training_result

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """进行预测.

        Args:
            X: 特征数据

        Returns:
            预测结果
        """
        if not self.is_fitted:
            raise ValueError("Pipeline must be fitted before making predictions")

        # 特征工程
        if self.feature_pipeline:
            X_processed = self.feature_pipeline.transform(X)
        else:
            X_processed = X

        # 应用特征选择
        if (
            self.enable_feature_selection
            and self.feature_selector
            and self.feature_selector.selected_features
        ):
            X_processed = X_processed[self.feature_selector.selected_features]

        # 模型预测
        return self.model_trainer.predict(X_processed)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """获取预测概率.

        Args:
            X: 特征数据

        Returns:
            预测概率
        """
        if not self.is_fitted:
            raise ValueError("Pipeline must be fitted before making predictions")

        # 特征工程
        if self.feature_pipeline:
            X_processed = self.feature_pipeline.transform(X)
        else:
            X_processed = X

        # 应用特征选择
        if (
            self.enable_feature_selection
            and self.feature_selector
            and self.feature_selector.selected_features
        ):
            X_processed = X_processed[self.feature_selector.selected_features]

        # 模型预测概率
        return self.model_trainer.predict_proba(X_processed)

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
        """评估模型性能.

        Args:
            X_test: 测试特征数据
            y_test: 测试标签数据

        Returns:
            评估结果字典
        """
        if not HAS_DEPENDENCIES:
            return {"error": "Required dependencies not available"}

        # 预测
        y_pred = self.predict(X_test)
        y_pred_proba = self.predict_proba(X_test)

        # 计算评估指标
        try:
            classification_rep = classification_report(y_test, y_pred, output_dict=True)
            confusion_mat = confusion_matrix(y_test, y_pred)

            # 计算准确率
            accuracy = (y_pred == y_test).mean()

            return {
                "accuracy": accuracy,
                "classification_report": classification_rep,
                "confusion_matrix": confusion_mat.tolist(),
                "predictions": y_pred.tolist(),
                "probabilities": y_pred_proba.tolist(),
            }
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"error": str(e)}

    def save_pipeline(self, filepath: str = None) -> str:
        """保存完整管道.

        Args:
            filepath: 保存路径

        Returns:
            保存路径
        """
        if filepath is None:
            filepath = self.output_dir / f"{self.model_name}_pipeline.pkl"

        import pickle

        pipeline_data = {
            "feature_pipeline": self.feature_pipeline,
            "model_trainer": self.model_trainer,
            "is_fitted": self.is_fitted,
            "model_name": self.model_name,
            "metadata": {
                "created_at": pd.Timestamp.now().isoformat(),
                "model_type": "xgboost" if self.model_trainer else "unknown",
                "has_xgboost": HAS_XGB,
            },
        }

        with open(filepath, "wb") as f:
            pickle.dump(pipeline_data, f)

        logger.info(f"Pipeline saved to {filepath}")
        return str(filepath)

    def load_pipeline(self, filepath: str) -> "FootballPredictionPipeline":
        """加载完整管道.

        Args:
            filepath: 文件路径

        Returns:
            自身实例
        """
        import pickle

        with open(filepath, "rb") as f:
            pipeline_data = pickle.load(f)

        self.feature_pipeline = pipeline_data["feature_pipeline"]
        self.model_trainer = pipeline_data["model_trainer"]
        self.is_fitted = pipeline_data["is_fitted"]
        self.model_name = pipeline_data["model_name"]

        logger.info(f"Pipeline loaded from {filepath}")
        return self


# 便捷函数
def create_simple_prediction_pipeline() -> FootballPredictionPipeline:
    """创建简单的足球预测管道."""
    return FootballPredictionPipeline(
        model_name="simple_football_predictor", use_mlflow=False
    ).build_feature_pipeline()


def create_advanced_prediction_pipeline() -> FootballPredictionPipeline:
    """创建高级的足球预测管道."""
    return FootballPredictionPipeline(
        model_name="advanced_football_predictor", use_mlflow=True
    ).build_feature_pipeline(
        numeric_strategy="robust",
        categorical_strategy="onehot",
        include_football_features=True,
    )


# 使用示例
def example_usage():
    """使用示例."""
    if not HAS_DEPENDENCIES:
        return

    # 创建模拟数据
    np.random.seed(42)
    n_samples = 1000

    data = {
        "home_team": np.random.choice(["Team_A", "Team_B", "Team_C"], n_samples),
        "away_team": np.random.choice(["Team_X", "Team_Y", "Team_Z"], n_samples),
        "home_team_score": np.random.randint(0, 5, n_samples),
        "away_team_score": np.random.randint(0, 5, n_samples),
        "home_team_shots": np.random.randint(5, 25, n_samples),
        "away_team_shots": np.random.randint(5, 25, n_samples),
        "odds_home_win": np.random.uniform(1.5, 5.0, n_samples),
        "odds_draw": np.random.uniform(3.0, 4.5, n_samples),
        "odds_away_win": np.random.uniform(1.8, 6.0, n_samples),
    }

    # 创建目标变量（主队是否获胜）
    y = (data["home_team_score"] > data["away_team_score"]).astype(int)

    X = pd.DataFrame(data)

    # 创建并训练管道
    pipeline = create_advanced_prediction_pipeline()

    # 准备数据
    X_train, X_test, y_train, y_test = pipeline.prepare_data(X, pd.Series(y))

    # 训练模型
    if HAS_XGB:
        pipeline.train_model(
            X_train,
            y_train,
            X_test,
            y_test,
            optimize_hyperparameters=True,
            n_trials=20,  # 示例中使用较少的试验次数
        )
    else:
        pass

    # 评估模型
    if pipeline.is_fitted:
        pipeline.evaluate(X_test, y_test)


if __name__ == "__main__":
    example_usage()
