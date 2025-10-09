"""
MLflow模型提供者

负责从MLflow加载和管理模型
"""

import logging
from datetime import datetime
from typing import Any, Dict, Tuple

try:
    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    HAS_MLFLOW = True
except ImportError:  # pragma: no cover - optional dependency path
    HAS_MLFLOW = False

    class MlflowException(Exception):
        """Fallback异常：仅在缺失MLflow依赖时使用。"""

    class _MockMlflowModule:
        """最小化的 MLflow 模拟实现。"""

        class sklearn:
            @staticmethod
            def load_model(*args, **kwargs):
                raise MlflowException("MLflow is not installed; cannot load models.")

        @staticmethod
        def set_tracking_uri(*args, **kwargs) -> None:
            return None

    class MlflowClient:
        def __init__(self, *args, **kwargs) -> None:
            raise MlflowException("MLflow is not installed; client unavailable.")

        def get_latest_versions(self, *args, **kwargs):  # pragma: no cover - fallback
            return []

    mlflow = _MockMlflowModule()

from src.cache.ttl_cache import TTLCache
from src.models.metrics_exporter import ModelMetricsExporter

logger = logging.getLogger(__name__)


class MlflowModelProvider:
    """
    MLflow模型提供者

    负责从MLflow获取、加载和缓存模型
    """

    def __init__(
        self,
        tracking_uri: str,
        cache_ttl,
        metrics_exporter: ModelMetricsExporter,
        max_cache_size: int = 10
    ):
        """
        初始化MLflow模型提供者

        Args:
            tracking_uri: MLflow跟踪服务器URI
            cache_ttl: 模型缓存TTL
            metrics_exporter: 指标导出器
            max_cache_size: 最大缓存数量
        """
        self.tracking_uri = tracking_uri
        self.metrics_exporter = metrics_exporter

        # 设置MLflow跟踪URI
        mlflow.set_tracking_uri(self.tracking_uri)

        # 初始化缓存
        self.model_cache = TTLCache(max_size=max_cache_size)
        self.cache_ttl = cache_ttl

        # 模型元数据缓存
        self.model_metadata_cache: Dict[str, Dict[str, Any]] = {}

    async def get_production_model(
        self, model_name: str = "football_baseline_model"
    ) -> Tuple[Any, str]:
        """
        获取生产环境模型

        Args:
            model_name: 模型名称

        Returns:
            Tuple[Any, str]: 包含模型对象和版本号的元组
        """
        # 创建缓存键
        cache_key = f"model:{model_name}"

        # 尝试从缓存获取
        cached_result = await self.model_cache.get_async(cache_key)
        if cached_result:
            model, version = cached_result
            logger.debug(f"使用缓存的模型 {model_name} 版本 {version}")
            return model, version

        try:
            # 加载模型
            model, version = await self._load_model_from_mlflow(model_name)

            # 缓存模型（带TTL）
            await self.model_cache.set_async(
                cache_key, (model, version), ttl=self.cache_ttl
            )

            # 更新元数据缓存
            model_uri = f"models:/{model_name}/{version}"
            self.model_metadata_cache[model_uri] = {
                "name": model_name,
                "version": version,
                "loaded_at": datetime.now(),
            }

            logger.info(f"成功加载模型 {model_name} 版本 {version}")
            return model, version
        except Exception as e:
            logger.error(f"加载生产模型失败: {e}")
            raise

    async def _load_model_from_mlflow(
        self, model_name: str = "football_baseline_model"
    ) -> Tuple[Any, str]:
        """
        从MLflow加载模型

        Args:
            model_name: 模型名称

        Returns:
            Tuple[Any, str]: 包含模型对象和版本号的元组
        """
        if not HAS_MLFLOW:
            raise MlflowException("MLflow is not installed")

        client = MlflowClient(tracking_uri=self.tracking_uri)

        # 获取生产阶段的最新模型
        production_versions = client.get_latest_versions(
            name=model_name, stages=["Production"]
        )

        if not production_versions:
            # 如果没有生产版本，尝试获取Staging版本
            staging_versions = client.get_latest_versions(
                name=model_name, stages=["Staging"]
            )
            if not staging_versions:
                # 如果也没有Staging版本，获取最新版本
                all_versions = client.get_latest_versions(name=model_name)
                if not all_versions:
                    raise ValueError(f"模型 {model_name} 没有可用版本")
                model_version_info = all_versions[0]
                logger.warning(
                    f"使用最新版本 {model_version_info.version}，建议推广模型到生产环境"
                )
            else:
                model_version_info = staging_versions[0]
                logger.warning(
                    f"使用Staging版本 {model_version_info.version}，建议推广到生产环境"
                )
        else:
            model_version_info = production_versions[0]
            logger.info(f"使用生产版本 {model_version_info.version}")

        version = model_version_info.version

        # 构建模型URI
        model_uri = f"models:/{model_name}/{version}"

        # 加载模型
        start_time = datetime.now()
        model = mlflow.sklearn.load_model(model_uri)
        load_duration = (datetime.now() - start_time).total_seconds()

        # 记录加载时间
        self.metrics_exporter.model_load_duration.labels(
            model_name=model_name, model_version=version
        ).observe(load_duration)

        return model, version