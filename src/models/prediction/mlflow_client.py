"""

"""





        """Fallback异常：仅在缺失MLflow依赖时使用。"""

        """最小化的 MLflow 模拟实现。"""







    """

    """

        """

        """


        """


        """




        """

        """






        """


        """






        """


        """





        """


        """





    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

MLflow客户端封装
MLflow Client Wrapper
提供MLflow模型加载和管理功能。
logger = get_logger(__name__)
# 尝试导入MLflow
try:
    HAS_MLFLOW = True
except ImportError:  # pragma: no cover
    HAS_MLFLOW = False
    class MlflowException(Exception):
    class _MockMlflowModule:
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
        def get_latest_versions(self, *args, **kwargs):  # pragma: no cover
            return []
    mlflow = _MockMlflowModule()
class MLflowModelClient:
    MLflow模型客户端 / MLflow Model Client
    提供从MLflow加载模型、获取模型信息等功能。
    Provides functionality to load models from MLflow and get model information.
    def __init__(self, tracking_uri: str = "http://localhost:5002"):
        初始化MLflow客户端 / Initialize MLflow client
        Args:
            tracking_uri (str): MLflow跟踪服务器URI / MLflow tracking server URI
                Defaults to "http://localhost:5002"
        self.tracking_uri = tracking_uri
        self.client = None
        self.model_name = "football_baseline_model"
        if HAS_MLFLOW:
            try:
                mlflow.set_tracking_uri(tracking_uri)
                self.client = MlflowClient(tracking_uri=tracking_uri)
                logger.info(f"MLflow客户端初始化成功: {tracking_uri}")
            except Exception as e:
                logger.error(f"MLflow客户端初始化失败: {e}")
                raise
    async def get_latest_model_version(self, stage: str = "Production") -> Optional[str]:
        获取最新模型版本 / Get latest model version
        Args:
            stage (str): 模型阶段 / Model stage
                Defaults to "Production"
        Returns:
            Optional[str]: 最新版本号，如果不存在则返回None / Latest version number, None if not exists
        if not self.client:
            raise MlflowException("MLflow客户端未初始化")
        try:
            versions = self.client.get_latest_versions(
                name=self.model_name,
                stages=[stage]
            )
            if versions:
                return versions[0].version
            else:
                logger.warning(f"未找到阶段 {stage} 的模型: {self.model_name}")
                return None
        except Exception as e:
            logger.error(f"获取最新模型版本失败: {e}")
            raise
    async def get_production_model(self) -> Tuple[Any, str]:
        获取生产模型 / Get production model
        Returns:
            Tuple[Any, str]: (模型对象, 版本号) / (Model object, version number)
        if not HAS_MLFLOW:
            raise MlflowException("MLflow未安装，无法加载模型")
        try:
            # 获取最新生产版本
            version = await self.get_latest_model_version("Production")
            if not version:
                # 尝试获取Staging版本
                version = await self.get_latest_model_version("Staging")
                if not version:
                    raise MlflowException("没有可用的模型版本")
            # 构建模型URI
            model_uri = f"models:/{self.model_name}/{version}"
            logger.info(f"从MLflow加载模型: {model_uri}")
            # 加载模型
            model = mlflow.sklearn.load_model(model_uri)
            return model, version
        except Exception as e:
            logger.error(f"加载生产模型失败: {e}")
            raise
    async def get_model_info(self, model_version: Optional[str] = None) -> Dict[str, Any]:
        获取模型信息 / Get model information
        Args:
            model_version (Optional[str]): 模型版本，如果为None则获取最新版本 / Model version, if None gets latest
        Returns:
            Dict[str, Any]: 模型信息 / Model information
        if not self.client:
            raise MlflowException("MLflow客户端未初始化")
        try:
            if not model_version:
                model_version = await self.get_latest_model_version("Production")
            if not model_version:
                return {"error": "没有可用的模型版本"}
            # 获取模型详情
            model_details = self.client.get_model_version(
                name=self.model_name,
                version=model_version
            )
            return {
                "name": model_details.name,
                "version": model_details.version,
                "stage": model_details.current_stage,
                "description": model_details.description,
                "creation_timestamp": model_details.creation_timestamp,
                "last_updated_timestamp": model_details.last_updated_timestamp,
                "run_id": model_details.run_id,
            }
        except Exception as e:
            logger.error(f"获取模型信息失败: {e}")
            return {"error": str(e)}
    async def list_model_versions(self, stages: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        列出所有模型版本 / List all model versions
        Args:
            stages (Optional[List[str]]): 要筛选的阶段列表 / List of stages to filter
        Returns:
            List[Dict[str, Any]]: 模型版本列表 / List of model versions
        if not self.client:
            raise MlflowException("MLflow客户端未初始化")
        try:
            if not stages:
                stages = ["Production", "Staging", "Archived", "None"]
            versions = self.client.get_latest_versions(
                name=self.model_name,
                stages=stages
            )
            return [
                {
                    "version": v.version,
                    "stage": v.current_stage,
                    "run_id": v.run_id,
                    "description": v.description,
                }
                for v in versions
            ]
        except Exception as e:
            logger.error(f"列出模型版本失败: {e}")
            return []
    async def transition_model_stage(
        self,
        version: str,
        new_stage: str,
        archive_existing_versions: bool = False
    ) -> bool:
        转换模型阶段 / Transition model stage
        Args:
            version (str): 模型版本 / Model version
            new_stage (str): 新阶段 / New stage
            archive_existing_versions (bool): 是否归档现有版本 / Whether to archive existing versions
        Returns:
            bool: 是否成功 / Whether successful
        if not self.client:
            raise MlflowException("MLflow客户端未初始化")
        try:
            self.client.transition_model_version_stage(
                name=self.model_name, Dict, List, Optional, Tuple
                version=version,
                stage=new_stage,
                archive_existing_versions=archive_existing_versions
            )
            logger.info(f"模型 {self.model_name} 版本 {version} 已转换到阶段 {new_stage}")
            return True
        except Exception as e:
            logger.error(f"转换模型阶段失败: {e}")
            return False