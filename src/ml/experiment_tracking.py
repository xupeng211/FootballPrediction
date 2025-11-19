"""
MLflow实验跟踪模块
MLflow Experiment Tracking Module

这个模块提供了与MLflow集成的实验跟踪功能，用于记录
模型训练过程中的参数、指标和工件。

主要功能：
- 实验管理和创建
- 参数记录
- 指标跟踪
- 模型版本控制
- 工件管理
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime

try:
    import mlflow
    import mlflow.sklearn
    import mlflow.pytorch
    import numpy as np
    from mlflow.entities import RunStatus

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logging.warning("MLflow not available. Experiment tracking will be disabled.")

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLflowExperimentTracker:
    """MLflow实验跟踪器类"""

    def __init__(self, experiment_name: str = "football-prediction"):
        """
        初始化实验跟踪器

        Args:
            experiment_name: 实验名称
        """
        self.experiment_name = experiment_name
        self.tracking_uri = self._get_tracking_uri()
        self.experiment_id = None

        if MLFLOW_AVAILABLE:
            self._setup_mlflow()
        else:
            logger.warning("MLflow is not available. Tracking will be disabled.")

    def _get_tracking_uri(self) -> str:
        """获取MLflow跟踪URI"""
        # 优先使用环境变量
        if "MLFLOW_TRACKING_URI" in os.environ:
            return os.environ["MLFLOW_TRACKING_URI"]

        # 使用本地默认位置
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        mlruns_dir = os.path.join(project_root, "mlruns")

        # 确保目录存在
        os.makedirs(mlruns_dir, exist_ok=True)

        return f"file://{mlruns_dir}"

    def _setup_mlflow(self):
        """设置MLflow配置"""
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            logger.info(f"MLflow tracking URI: {self.tracking_uri}")

            # 创建或获取实验
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(self.experiment_name)
                logger.info(
                    f"Created new experiment: {self.experiment_name} (ID: {experiment_id})"
                )
            else:
                experiment_id = experiment.experiment_id
                logger.info(
                    f"Using existing experiment: {self.experiment_name} (ID: {experiment_id})"
                )

            self.experiment_id = experiment_id

        except Exception as e:
            logger.error(f"Failed to setup MLflow: {e}")
            raise

    def start_run(self, run_name: str | None = None) -> str | None:
        """
        开始新的实验运行

        Args:
            run_name: 运行名称

        Returns:
            run_id: 运行ID
        """
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not available, skipping run start")
            return None

        try:
            if run_name is None:
                run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            run = mlflow.start_run(
                run_name=run_name,
                experiment_id=self.experiment_id,
                tags={
                    "project": "football-prediction",
                    "version": "1.0.0",
                    "author": "ml-team",
                },
            )

            logger.info(f"Started MLflow run: {run.info.run_id}")
            return run.info.run_id

        except Exception as e:
            logger.error(f"Failed to start MLflow run: {e}")
            return None

    def log_params(self, params: dict[str, Any]):
        """
        记录参数

        Args:
            params: 参数字典
        """
        if not MLFLOW_AVAILABLE:
            return

        try:
            for key, value in params.items():
                mlflow.log_param(key, value)
            logger.info(f"Logged {len(params)} parameters")
        except Exception as e:
            logger.error(f"Failed to log parameters: {e}")

    def log_metrics(
        self, metrics: dict[str, int | float], step: int | None = None
    ):
        """
        记录指标

        Args:
            metrics: 指标字典
            step: 步骤数（可选）
        """
        if not MLFLOW_AVAILABLE:
            return

        try:
            for key, value in metrics.items():
                mlflow.log_metric(key, value, step=step)
            logger.info(f"Logged {len(metrics)} metrics at step {step}")
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")

    def log_artifact(self, local_path: str, artifact_path: str | None = None):
        """
        记录工件

        Args:
            local_path: 本地文件路径
            artifact_path: 工件路径（可选）
        """
        if not MLFLOW_AVAILABLE:
            return

        try:
            mlflow.log_artifact(local_path, artifact_path)
            logger.info(f"Logged artifact: {local_path}")
        except Exception as e:
            logger.error(f"Failed to log artifact: {e}")

    def log_model(self, model: Any, artifact_path: str = "model"):
        """
        记录模型

        Args:
            model: 模型对象
            artifact_path: 工件路径
        """
        if not MLFLOW_AVAILABLE:
            return

        try:
            # 根据模型类型使用不同的日志记录方法
            model_type = type(model).__name__

            if "sklearn" in str(type(model)).lower():
                mlflow.sklearn.log_model(model, artifact_path)
            elif "torch" in str(type(model)).lower():
                mlflow.pytorch.log_model(model, artifact_path)
            else:
                # 通用方法：先保存模型，然后记录
                import joblib

                model_path = f"{artifact_path}.pkl"
                joblib.dump(model, model_path)
                mlflow.log_artifact(model_path, artifact_path)

            logger.info(f"Logged {model_type} model as {artifact_path}")

        except Exception as e:
            logger.error(f"Failed to log model: {e}")

    def set_tags(self, tags: dict[str, str]):
        """
        设置标签

        Args:
            tags: 标签字典
        """
        if not MLFLOW_AVAILABLE:
            return

        try:
            mlflow.set_tags(tags)
            logger.info(f"Set {len(tags)} tags")
        except Exception as e:
            logger.error(f"Failed to set tags: {e}")

    def end_run(self, status: str = "FINISHED"):
        """
        结束运行

        Args:
            status: 运行状态
        """
        if not MLFLOW_AVAILABLE:
            return

        try:
            mlflow.end_run()
            logger.info(f"Ended MLflow run with status: {status}")
        except Exception as e:
            logger.error(f"Failed to end run: {e}")

    def run_experiment(self, experiment_func, params: dict[str, Any] = None):
        """
        运行实验的便捷方法

        Args:
            experiment_func: 实验函数
            params: 实验参数

        Returns:
            实验结果
        """
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not available, running without tracking")
            return experiment_func(params or {})

        run_id = self.start_run()
        if run_id is None:
            return experiment_func(params or {})

        try:
            # 记录参数
            if params:
                self.log_params(params)

            # 设置标签
            self.set_tags(
                {"start_time": datetime.now().isoformat(), "environment": "development"}
            )

            # 运行实验
            start_time = time.time()
            result = experiment_func(params or {})
            execution_time = time.time() - start_time

            # 记录执行时间
            self.log_metrics({"execution_time": execution_time})

            # 记录结果摘要
            if isinstance(result, dict):
                self.log_metrics(
                    {
                        "result_size": len(result) if hasattr(result, "__len__") else 0,
                        "success": True,
                    }
                )

            return result

        except Exception as e:
            # 记录错误
            self.log_metrics({"error": 1, "success": False})
            logger.error(f"Experiment failed: {e}")
            raise

        finally:
            self.end_run()


def dummy_football_prediction_experiment(params: dict[str, Any]) -> dict[str, Any]:
    """
    模拟足球预测实验

    Args:
        params: 实验参数

    Returns:
        实验结果
    """
    # 模拟训练过程
    import random

    learning_rate = params.get("learning_rate", 0.001)
    epochs = params.get("epochs", 100)
    model_type = params.get("model_type", "lstm")

    # 模拟训练指标
    train_losses = []
    val_accuracies = []

    for epoch in range(epochs):
        # 模拟训练损失（递减）
        train_loss = 1.0 * (0.95**epoch) + random.uniform(-0.05, 0.05)
        train_losses.append(train_loss)

        # 模拟验证准确率（递增）
        val_acc = 0.5 + 0.4 * (1 - 0.99**epoch) + random.uniform(-0.02, 0.02)
        val_accuracies.append(min(val_acc, 1.0))

    # 返回结果
    return {
        "final_train_loss": train_losses[-1],
        "final_val_accuracy": val_accuracies[-1],
        "best_val_accuracy": max(val_accuracies),
        "train_losses": train_losses,
        "val_accuracies": val_accuracies,
        "epochs_trained": epochs,
        "model_parameters": f"{model_type}_lr_{learning_rate}",
    }


def main():
    """主函数 - 演示MLflow集成"""
    print("🚀 Starting MLflow Integration Test")
    print("=" * 50)

    # 创建实验跟踪器
    try:
        tracker = MLflowExperimentTracker("football-prediction-demo")
        print("✅ MLflow experiment tracker initialized")
        print(f"📊 Tracking URI: {tracker.tracking_uri}")
        print(f"🏷️  Experiment: {tracker.experiment_name}")

        # 定义实验参数
        experiment_params = {
            "learning_rate": 0.001,
            "epochs": 50,
            "batch_size": 32,
            "model_type": "lstm",
            "dropout_rate": 0.2,
            "optimizer": "adam",
        }

        print("\n🎯 Running experiment with parameters:")
        for key, value in experiment_params.items():
            print(f"  {key}: {value}")

        # 运行实验
        print("\n🧪 Running experiment...")
        result = tracker.run_experiment(
            dummy_football_prediction_experiment, experiment_params
        )

        # 记录结果指标
        metrics = {
            "final_train_loss": result["final_train_loss"],
            "final_val_accuracy": result["final_val_accuracy"],
            "best_val_accuracy": result["best_val_accuracy"],
        }

        tracker.log_metrics(metrics)

        # 记录额外工件
        results_json = {
            "experiment_id": tracker.experiment_id,
            "parameters": experiment_params,
            "results": result,
            "timestamp": datetime.now().isoformat(),
        }

        # 保存结果到文件并记录为工件
        import json

        results_file = "experiment_results.json"
        with open(results_file, "w") as f:
            json.dump(results_json, f, indent=2)

        tracker.log_artifact(results_file, "results")

        # 清理临时文件
        os.remove(results_file)

        print("\n✅ Experiment completed successfully!")
        print(f"📊 Final validation accuracy: {metrics['final_val_accuracy']:.4f}")
        print(f"🏆 Best validation accuracy: {metrics['best_val_accuracy']:.4f}")
        print("📁 Results logged to MLflow experiment")

        return result

    except Exception as e:
        print(f"❌ Failed to run experiment: {e}")
        return None


if __name__ == "__main__":
    # 直接运行演示
    main()
