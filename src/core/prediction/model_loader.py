"""
模型加载器
Model Loader

管理预测模型的加载和版本控制。
"""

import logging
from typing import Optional

from src.models.prediction_service import PredictionService

logger = logging.getLogger(__name__)


class ModelLoader:
    """模型加载器"""

    def __init__(
        self,
        mlflow_tracking_uri: str,
        default_model_name: str = "football_prediction_model",
    ):
        """
        初始化模型加载器

        Args:
            mlflow_tracking_uri: MLflow跟踪URI
            default_model_name: 默认模型名称
        """
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.default_model_name = default_model_name
        self.prediction_service = PredictionService(mlflow_tracking_uri)
        self._current_model = None
        self._current_version = None

    async def load_model(
        self, model_name: Optional[str] = None, stage: str = "Production"
    ) -> bool:
        """
        加载模型

        Args:
            model_name: 模型名称
            stage: 模型阶段（Production, Staging）

        Returns:
            是否加载成功
        """
        model_name = model_name or self.default_model_name

        try:
            # 获取最新版本
            latest_versions = self.prediction_service.mlflow_client.get_latest_versions(
                name=model_name, stages=[stage]
            )

            if not latest_versions:
                logger.error(f"没有找到 {stage} 阶段的模型: {model_name}")
                return False

            latest_version = latest_versions[0]
            model_version = latest_version.version

            # 加载模型
            success = await self.prediction_service.load_model(
                model_name, model_version
            )

            if success:
                self._current_model = model_name
                self._current_version = model_version
                logger.info(
                    f"成功加载模型: {model_name}:{model_version} ({stage})"
                )
                return True
            else:
                logger.error(f"加载模型失败: {model_name}:{model_version}")
                return False

        except Exception as e:
            logger.error(f"加载模型时发生错误: {e}")
            return False

    async def predict_match(self, match_id: int) -> Optional[object]:
        """
        使用当前模型预测比赛

        Args:
            match_id: 比赛ID

        Returns:
            预测结果或None
        """
        if not self._current_model:
            logger.error("没有加载模型")
            return None

        try:
            return await self.prediction_service.predict_match(match_id)
        except Exception as e:
            logger.error(f"预测失败: {e}")
            return None

    async def predict_batch(self, match_ids: list[int]) -> list[object]:
        """
        批量预测

        Args:
            match_ids: 比赛ID列表

        Returns:
            预测结果列表
        """
        if not self._current_model:
            logger.error("没有加载模型")
            return []

        try:
            return await self.prediction_service.predict_batch(match_ids)
        except Exception as e:
            logger.error(f"批量预测失败: {e}")
            return []

    def get_model_info(self) -> dict:
        """
        获取当前模型信息

        Returns:
            模型信息字典
        """
        return {
            "model_name": self._current_model,
            "model_version": self._current_version,
            "mlflow_tracking_uri": self.mlflow_tracking_uri,
        }

    async def switch_model(
        self, model_name: str, version: Optional[str] = None
    ) -> bool:
        """
        切换模型

        Args:
            model_name: 新模型名称
            version: 模型版本

        Returns:
            是否切换成功
        """
        try:
            if version:
                success = await self.prediction_service.load_model(model_name, version)
            else:
                success = await self.load_model(model_name)

            if success:
                self._current_model = model_name
                self._current_version = version
                logger.info(f"成功切换到模型: {model_name}:{version or 'latest'}")
                return True
            else:
                logger.error(f"切换模型失败: {model_name}:{version}")
                return False

        except Exception as e:
            logger.error(f"切换模型时发生错误: {e}")
            return False

    async def validate_model(self, model_name: str, version: str) -> bool:
        """
        验证模型

        Args:
            model_name: 模型名称
            version: 模型版本

        Returns:
            是否有效
        """
        try:
            # 尝试获取模型信息
            model_version = self.prediction_service.mlflow_client.get_model_version(
                name=model_name, version=version
            )

            if model_version:
                # 检查运行状态
                if model_version.run_id:
                    run = self.prediction_service.mlflow_client.get_run(
                        model_version.run_id
                    )
                    if run and run.info.status == "FINISHED":
                        logger.info(f"模型验证通过: {model_name}:{version}")
                        return True

            logger.warning(f"模型验证失败: {model_name}:{version}")
            return False

        except Exception as e:
            logger.error(f"验证模型时发生错误: {e}")
            return False

    def list_available_models(self, stage: str = "Production") -> list[dict]:
        """
        列出可用模型

        Args:
            stage: 模型阶段

        Returns:
            模型列表
        """
        try:
            models = self.prediction_service.mlflow_client.search_registered_models()
            available_models = []

            for model in models:
                versions = self.prediction_service.mlflow_client.get_latest_versions(
                    name=model.name, stages=[stage]
                )
                for version in versions:
                    available_models.append(
                        {
                            "name": model.name,
                            "version": version.version,
                            "stage": version.current_stage,
                            "creation_timestamp": version.creation_timestamp,
                            "description": version.description,
                        }
                    )

            return available_models

        except Exception as e:
            logger.error(f"列出模型时发生错误: {e}")
            return []