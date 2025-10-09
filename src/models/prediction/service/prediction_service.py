"""
预测服务核心模块
Core Prediction Service Module

提供实时比赛预测的主要功能。
"""




logger = get_logger(__name__)


class PredictionService:
    """
    预测服务 / Prediction Service

    提供实时比赛预测功能，支持：
    - 从MLflow加载最新生产模型
    - 实时特征获取和预测
    - 预测结果存储到数据库
    - Prometheus指标导出

    Provides real-time match prediction functionality, including:
    - Loading latest production model from MLflow
    - Real-time feature retrieval and prediction
    - Storing prediction results to database
    - Prometheus metrics export
    """

    def __init__(self, mlflow_tracking_uri: str = "http://localhost:5002"):
        """
        初始化预测服务 / Initialize Prediction Service

        Args:
            mlflow_tracking_uri (str): MLflow跟踪服务器URI / MLflow tracking server URI
                Defaults to "http://localhost:5002"

        Attributes:
            db_manager (DatabaseManager): 数据库管理器实例 / Database manager instance
            model_loader (ModelLoader): 模型加载器 / Model loader
            cache_manager (PredictionCacheManager): 缓存管理器 / Cache manager
            predictor (MatchPredictor): 比赛预测器 / Match predictor
            batch_predictor (BatchPredictor): 批量预测器 / Batch predictor
        """
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()

        # 初始化模型加载器
        self.model_loader = ModelLoader(mlflow_tracking_uri)

        # 初始化缓存管理器
        self.cache_manager = PredictionCacheManager()

        # 初始化预测器
        self.predictor = MatchPredictor(
            db_manager=self.db_manager,
            model_loader=self.model_loader,
            cache_manager=self.cache_manager
        )

        # 初始化批量预测器
        self.batch_predictor = BatchPredictor(
            predictor=self.predictor
        )

        logger.info("预测服务初始化完成")

    async def predict_match(self, match_id: int) -> Any:
        """
        预测比赛结果 / Predict Match Result

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            Any: 预测结果 / Prediction result
        """
        return await self.predictor.predict_match(match_id)

    async def verify_prediction(self, match_id: int) -> bool:
        """
        验证预测结果 / Verify Prediction Result

        Args:
            match_id (int): 比赛ID / Match ID

        Returns:
            bool: 预测是否正确 / Whether prediction is correct
        """
        return await self.predictor.verify_prediction(match_id)

    async def batch_predict_matches(self, match_ids: list) -> list:
        """
        批量预测比赛 / Batch Predict Matches

        Args:
            match_ids (list): 比赛ID列表 / List of match IDs

        Returns:
            list: 预测结果列表 / List of prediction results
        """
        return await self.batch_predictor.predict_matches(match_ids)

    async def get_prediction_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取预测统计信息 / Get Prediction Statistics

        Args:
            days (int): 统计天数 / Statistics days

        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        """
        return await self.predictor.get_statistics(days)

    async def get_production_model(self) -> tuple:
        """
        获取生产模型 / Get Production Model

        Returns:
            tuple: (模型对象, 版本号) / (Model object, version number)
        """
        return await self.model_loader.get_production_model()

from .batch_predictor import BatchPredictor
from .cache_manager import PredictionCacheManager
from .model_loader import ModelLoader
from .predictors import MatchPredictor
from src.database.connection import DatabaseManager

