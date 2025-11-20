"""
增强版 XGBoost 训练器
Enhanced XGBoost Trainer

集成 GridSearchCV 超参数优化的完整训练流程，符合 SRS 要求。
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.ml.xgboost_hyperparameter_optimization import (
    XGBoostHyperparameterOptimizer,
    optimize_xgboost_model,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnhancedXGBoostTrainer:
    """增强版 XGBoost 训练器."""

    def __init__(
        self,
        model_name: str = "enhanced_xgboost",
        output_dir: str = "models",
        debug_mode: bool = False,
        cv_folds: int = 5,
        scoring_metric: str = "f1_weighted",
    ):
        """初始化训练器.

        Args:
            model_name: 模型名称
            output_dir: 输出目录
            debug_mode: 调试模式
            cv_folds: 交叉验证折数
            scoring_metric: 评估指标
        """
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.debug_mode = debug_mode
        self.cv_folds = cv_folds
        self.scoring_metric = scoring_metric

        # 创建优化器
        if debug_mode:
            self.optimizer = XGBoostHyperparameterOptimizer.create_debug_optimizer()
            logger.info("Created debug optimizer")
        else:
            self.optimizer = XGBoostHyperparameterOptimizer.create_default_optimizer()
            logger.info("Created default optimizer")

        logger.info(f"Initialized EnhancedXGBoostTrainer: {model_name}")

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        custom_param_grid: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """训练 XGBoost 模型.

        Args:
            X_train: 训练特征数据
            y_train: 训练目标数据
            X_val: 验证特征数据（可选）
            y_val: 验证目标数据（可选）
            custom_param_grid: 自定义参数网格

        Returns:
            训练结果
        """
        logger.info(f"Starting enhanced XGBoost training for {self.model_name}")
        logger.info(
            f"Training data shape: {X_train.shape}, Target shape: {y_train.shape}"
        )

        if X_val is not None:
            logger.info(
                f"Validation data shape: {X_val.shape}, Target shape: {y_val.shape}"
            )

        try:
            # 执行超参数优化
            optimization_results = self.optimizer.optimize(
                X_train,
                y_train,
                param_grid=custom_param_grid,
                debug_mode=self.debug_mode,
                save_best_model=True,
            )

            # 验证集评估（如果提供）
            validation_metrics = {}
            if X_val is not None and y_val is not None:
                logger.info("Evaluating on validation set...")
                validation_metrics = self.optimizer.evaluate_model(X_val, y_val)

            # 汇总结果
            training_results = {
                "model_name": self.model_name,
                "optimization_results": optimization_results,
                "validation_metrics": validation_metrics,
                "debug_mode": self.debug_mode,
                "cv_folds": self.cv_folds,
                "scoring_metric": self.scoring_metric,
            }

            logger.info("Enhanced XGBoost training completed successfully")
            logger.info(f"Best CV score: {optimization_results['best_score']:.4f}")

            if validation_metrics:
                logger.info(
                    f"Validation accuracy: {validation_metrics['accuracy']:.4f}"
                )
                logger.info(f"Validation F1: {validation_metrics['f1_weighted']:.4f}")

            return training_results

        except Exception as e:
            logger.error(f"Enhanced XGBoost training failed: {e}")
            raise

    def predict(self, X: pd.DataFrame) -> Any:
        """使用训练好的模型进行预测.

        Args:
            X: 特征数据

        Returns:
            预测结果
        """
        return self.optimizer.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> Any:
        """获取预测概率.

        Args:
            X: 特征数据

        Returns:
            预测概率
        """
        return self.optimizer.predict_proba(X)

    def get_feature_importance(self) -> Any | None:
        """获取特征重要性."""
        return self.optimizer.get_feature_importance()

    def save_training_report(self, results: dict[str, Any]) -> str:
        """保存训练报告.

        Args:
            results: 训练结果

        Returns:
            报告文件路径
        """
        import json
        from datetime import datetime

        report = {
            "training_summary": {
                "model_name": self.model_name,
                "timestamp": datetime.now().isoformat(),
                "debug_mode": self.debug_mode,
                "cv_folds": self.cv_folds,
                "scoring_metric": self.scoring_metric,
            },
            "optimization_summary": {
                "best_score": results["optimization_results"]["best_score"],
                "best_params": results["optimization_results"]["best_params"],
                "optimization_time": results["optimization_results"][
                    "optimization_time"
                ],
            },
            "validation_summary": results.get("validation_metrics", {}),
            "feature_importance": (
                self.get_feature_importance().tolist()
                if self.get_feature_importance() is not None
                else None
            ),
        }

        report_path = self.output_dir / f"{self.model_name}_training_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Training report saved to {report_path}")
        return str(report_path)


def create_sample_data(n_samples: int = 1000, n_features: int = 10) -> tuple:
    """创建示例训练数据.

    Args:
        n_samples: 样本数量
        n_features: 特征数量

    Returns:
        特征数据和目标数据
    """
    import numpy as np

    np.random.seed(42)

    # 创建特征数据
    feature_names = [f"feature_{i}" for i in range(n_features)]
    X = pd.DataFrame(np.random.randn(n_samples, n_features), columns=feature_names)

    # 创建具有一定规律的目标变量
    # 前几个特征对目标有更强的影响
    weights = np.array([2.0, 1.5, 1.0, 0.5] + [0.1] * (n_features - 4))
    linear_combination = X.dot(weights)
    probabilities = 1 / (1 + np.exp(-linear_combination))
    y = pd.Series((probabilities > 0.5).astype(int))

    logger.info(
        f"Created sample data: {X.shape}, Target distribution: {y.value_counts().to_dict()}"
    )
    return X, y


def main():
    """主函数 - 演示增强版训练器."""
    logger.info("=== 增强版 XGBoost 训练器演示 ===")

    # 创建示例数据
    X, y = create_sample_data(n_samples=500, n_features=8)

    # 分割训练和验证数据
    from sklearn.model_selection import train_test_split

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 调试模式训练
    logger.info("\n--- 调试模式训练 ---")
    debug_trainer = EnhancedXGBoostTrainer(
        model_name="debug_xgboost_demo",
        output_dir="models/demo",
        debug_mode=True,
        cv_folds=3,
    )

    debug_results = debug_trainer.train_model(X_train, y_train, X_val, y_val)
    debug_report_path = debug_trainer.save_training_report(debug_results)

    # 生产模式训练（如果数据量足够）
    if len(X_train) >= 100:  # 只有数据量足够时才运行完整训练
        logger.info("\n--- 生产模式训练 ---")
        prod_trainer = EnhancedXGBoostTrainer(
            model_name="production_xgboost_demo",
            output_dir="models/demo",
            debug_mode=False,
            cv_folds=5,
        )

        # 自定义参数网格（符合SRS要求）
        custom_param_grid = {
            "learning_rate": [0.01, 0.05, 0.1],
            "max_depth": [3, 5, 7],
            "n_estimators": [100, 200],
            "subsample": [0.8, 1.0],
        }

        prod_results = prod_trainer.train_model(
            X_train, y_train, X_val, y_val, custom_param_grid=custom_param_grid
        )
        prod_report_path = prod_trainer.save_training_report(prod_results)

        logger.info("\n=== 训练完成 ===")
        logger.info(f"调试模式报告: {debug_report_path}")
        logger.info(f"生产模式报告: {prod_report_path}")
        logger.info(
            f"最佳调试模型得分: {debug_results['optimization_results']['best_score']:.4f}"
        )
        logger.info(
            f"最佳生产模型得分: {prod_results['optimization_results']['best_score']:.4f}"
        )
    else:
        logger.info("数据量不足，跳过生产模式训练")


if __name__ == "__main__":
    main()
