"""
MLflow 实验管理器

负责管理MLflow实验、运行和模型注册
"""

import logging
from typing import Any, Dict, Optional

# 处理可选依赖
try:
    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
    # 创建一个模拟的 mlflow 对象

    class MockMLflow:
        def start_run(self, **kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def log_metric(self, *args, **kwargs):
            pass

        def log_param(self, *args, **kwargs):
            pass

        def log_artifacts(self, *args, **kwargs):
            pass

        class sklearn:
            @staticmethod
            def log_model(*args, **kwargs):
                pass

    mlflow = MockMLflow()
    mlflow.sklearn = MockMLflow.sklearn()

    class MockMlflowClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_latest_versions(self, *args, **kwargs):
            return []

        def transition_model_version_stage(self, *args, **kwargs):
            pass

        def get_run(self, run_id):
            class MockRun:
                class MockInfo:
                    run_id = "mock-run-id"
                    status = "FINISHED"
                    start_time = 0
                    end_time = 0

                info = MockInfo()
                class MockData:
                    metrics = {}
                    params = {}
                    tags = {}

                data = MockData()

            return MockRun()

    MlflowClient = MockMlflowClient

logger = logging.getLogger(__name__)


class ExperimentManager:
    """MLflow实验管理器"""

    def __init__(self, tracking_uri: str):
        """
        初始化实验管理器

        Args:
            tracking_uri: MLflow跟踪服务器URI
        """
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(self.tracking_uri)
        self.mlflow_client = MlflowClient(tracking_uri=tracking_uri)

    async def get_or_create_experiment(self, experiment_name: str) -> str:
        """
        获取或创建实验

        Args:
            experiment_name: 实验名称

        Returns:
            实验ID
        """
        if not HAS_MLFLOW:
            logger.warning("MLflow不可用，使用模拟实验ID")
            return "0"

        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
                logger.info(f"创建新实验: {experiment_name}")
            else:
                experiment_id = experiment.experiment_id
                logger.info(f"使用现有实验: {experiment_name}")
            return experiment_id
        except Exception as e:
            logger.error(f"设置MLflow实验失败: {e}")
            return "0"

    async def start_run(self, experiment_id: str):
        """
        开始MLflow运行

        Args:
            experiment_id: 实验ID

        Returns:
            MLflow运行上下文
        """
        mlflow.set_experiment(experiment_id)
        return mlflow.start_run(experiment_id=experiment_id)

    async def log_params(self, params: Dict[str, Any]) -> None:
        """
        记录参数

        Args:
            params: 参数字典
        """
        for key, value in params.items():
            mlflow.log_param(key, value)

    async def log_param(self, key: str, value: Any) -> None:
        """
        记录单个参数

        Args:
            key: 参数名
            value: 参数值
        """
        mlflow.log_param(key, value)

    async def log_metrics(self, metrics: Dict[str, float]) -> None:
        """
        记录指标

        Args:
            metrics: 指标字典
        """
        for key, value in metrics.items():
            mlflow.log_metric(key, value)

    async def log_metric(self, key: str, value: float) -> None:
        """
        记录单个指标

        Args:
            key: 指标名
            value: 指标值
        """
        mlflow.log_metric(key, value)

    async def log_model(
        self, model, model_name: str, X_train, y_train_pred
    ) -> None:
        """
        记录模型到MLflow

        Args:
            model: 训练好的模型
            model_name: 模型名称
            X_train: 训练特征
            y_train_pred: 训练预测
        """
        if HAS_MLFLOW:
            mlflow.sklearn.log_model(
                model,
                "model",
                registered_model_name=model_name,
                signature=mlflow.models.infer_signature(X_train, y_train_pred),
            )
        else:
            logger.warning("MLflow不可用，跳过模型记录")

    async def set_tags(self, tags: Dict[str, str]) -> None:
        """
        设置标签

        Args:
            tags: 标签字典
        """
        mlflow.set_tags(tags)

    async def promote_model_to_production(
        self, model_name: str, version: Optional[str] = None
    ) -> bool:
        """
        将模型推广到生产环境

        Args:
            model_name: 模型名称
            version: 模型版本，如果为None则使用最新版本

        Returns:
            是否成功推广
        """
        try:
            if version is None:
                # 获取最新版本
                latest_versions = self.mlflow_client.get_latest_versions(
                    name=model_name, stages=["Staging"]
                )
                if not latest_versions:
                    logger.error(f"模型 {model_name} 在Staging阶段没有版本")
                    return False
                version = latest_versions[0].version

            # 推广到生产环境
            self.mlflow_client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage="Production",
                archive_existing_versions=True,
            )

            logger.info(f"模型 {model_name} 版本 {version} 已推广到生产环境")
            return True

        except Exception as e:
            logger.error(f"模型推广失败: {e}")
            return False

    async def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """
        获取运行摘要

        Args:
            run_id: 运行ID

        Returns:
            运行摘要字典
        """
        try:
            run = self.mlflow_client.get_run(run_id)

            return {
                "run_id": run_id,
                "status": run.info.status,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "metrics": run.data.metrics,
                "parameters": run.data.params,
                "tags": run.data.tags,
            }

        except Exception as e:
            logger.error(f"获取模型性能摘要失败: {e}")
            return {}