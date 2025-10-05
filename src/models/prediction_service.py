"""
模型预测服务 / Model Prediction Service

提供实时比赛预测功能，支持：
- 从MLflow加载最新生产模型
- 实时特征获取和预测
- 预测结果存储到数据库
- Prometheus指标导出
- 带TTL的缓存机制
- MLflow服务调用重试机制

Provides real-time match prediction functionality, including:
- Loading latest production model from MLflow
- Real-time feature retrieval and prediction
- Storing prediction results to database
- Prometheus metrics export
- TTL-based caching mechanism
- MLflow service call retry mechanism

主要类 / Main Classes:
    PredictionService: 核心预测服务类 / Core prediction service class
    PredictionResult: 预测结果数据类 / Prediction result data class

主要方法 / Main Methods:
    PredictionService.predict_match(): 对单场比赛进行预测 / Predict single match
    PredictionService.batch_predict_matches(): 批量预测比赛 / Batch predict matches
    PredictionService.verify_prediction(): 验证预测结果 / Verify prediction results

使用示例 / Usage Example:
    ```python
    from src.models.prediction_service import PredictionService

    service = PredictionService(mlflow_tracking_uri="http://localhost:5002")
    result = await service.predict_match(12345)
    print(f"预测结果: {result.predicted_result}")
    ```

环境变量 / Environment Variables:
    MLFLOW_TRACKING_URI: MLflow跟踪服务器URI，默认为http://localhost:5002
                     MLflow tracking server URI, defaults to http://localhost:5002
    MODEL_CACHE_TTL_HOURS: 模型缓存TTL小时数，默认为1
                      Model cache TTL in hours, defaults to 1
    PREDICTION_CACHE_TTL_MINUTES: 预测结果缓存TTL分钟数，默认为30
                              Prediction result cache TTL in minutes, defaults to 30
    MLFLOW_RETRY_MAX_ATTEMPTS: MLflow重试最大尝试次数，默认3
                          MLflow retry max attempts, default 3
    MLFLOW_RETRY_BASE_DELAY: MLflow重试基础延迟秒数，默认2.0
                         MLflow retry base delay in seconds, default 2.0

依赖 / Dependencies:
    - mlflow: 模型管理和跟踪 / Model management and tracking
    - scikit-learn: 机器学习模型加载 / Machine learning model loading
    - sqlalchemy: 数据库操作 / Database operations
    - src.cache.ttl_cache: TTL缓存管理 / TTL cache management
    - src.utils.retry: 重试机制 / Retry mechanism
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
import inspect
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select, text

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

        class sklearn:  # type: ignore
            @staticmethod
            def load_model(*args, **kwargs):
                raise MlflowException("MLflow is not installed; cannot load models.")

        @staticmethod
        def set_tracking_uri(*args, **kwargs) -> None:
            return None

    class MlflowClient:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            raise MlflowException("MLflow is not installed; client unavailable.")

        def get_latest_versions(self, *args, **kwargs):  # pragma: no cover - fallback
            return []

    mlflow = _MockMlflowModule()  # type: ignore

from src.cache.ttl_cache import TTLCache
from src.database.connection import DatabaseManager
from src.database.models import Match, MatchStatus, Prediction
from src.features.feature_store import FootballFeatureStore
from src.utils.retry import RetryConfig, retry

from .metrics_exporter import ModelMetricsExporter

logger = logging.getLogger(__name__)

# MLflow重试配置 / MLflow retry configuration
MLFLOW_RETRY_CONFIG = RetryConfig(
    max_attempts=int(os.getenv("MLFLOW_RETRY_MAX_ATTEMPTS", "3")),
    base_delay=float(os.getenv("MLFLOW_RETRY_BASE_DELAY", "2.0")),
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(MlflowException, ConnectionError, TimeoutError),
)


@dataclass
class PredictionResult:
    """
    预测结果数据类 / Prediction Result Data Class

    存储比赛预测的完整结果，包括概率、置信度和元数据。
    Stores complete match prediction results including probabilities, confidence scores and metadata.

    Attributes:
        match_id (int): 比赛唯一标识符 / Unique match identifier
        model_version (str): 使用的模型版本 / Model version used
        model_name (str): 模型名称，默认为"football_baseline_model" / Model name, defaults to "football_baseline_model"
        home_win_probability (float): 主队获胜概率，范围0-1 / Home win probability, range 0-1
        draw_probability (float): 平局概率，范围0-1 / Draw probability, range 0-1
        away_win_probability (float): 客队获胜概率，范围0-1 / Away win probability, range 0-1
        predicted_result (str): 预测结果，'home'/'draw'/'away' / Predicted result, 'home'/'draw'/'away'
        confidence_score (float): 预测置信度，范围0-1 / Prediction confidence score, range 0-1
        features_used (Optional[Dict[str, Any]]): 使用的特征字典 / Dictionary of features used
        prediction_metadata (Optional[Dict[str, Any]]): 预测元数据 / Prediction metadata
        created_at (Optional[datetime]): 预测创建时间 / Prediction creation time
        actual_result (Optional[str]): 实际比赛结果 / Actual match result
        is_correct (Optional[bool]): 预测是否正确 / Whether prediction is correct
        verified_at (Optional[datetime]): 验证时间 / Verification time
    """

    match_id: int
    model_version: str
    model_name: str = "football_baseline_model"

    # 预测概率 / Prediction probabilities
    home_win_probability: float = 0.0
    draw_probability: float = 0.0
    away_win_probability: float = 0.0

    # 预测结果 / Prediction result
    predicted_result: str = "draw"  # 'home', 'draw', 'away'
    confidence_score: float = 0.0

    # 元数据 / Metadata
    features_used: Optional[Dict[str, Any]] = None
    prediction_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    # 结果验证（比赛结束后更新） / Result verification (updated after match)
    actual_result: Optional[str] = None
    is_correct: Optional[bool] = None
    verified_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式 / Convert to dictionary format

        Returns:
            Dict[str, Any]: 包含所有预测结果属性的字典 / Dictionary containing all prediction result attributes
        """
        return {
            "match_id": self.match_id,
            "model_version": self.model_version,
            "model_name": self.model_name,
            "home_win_probability": self.home_win_probability,
            "draw_probability": self.draw_probability,
            "away_win_probability": self.away_win_probability,
            "predicted_result": self.predicted_result,
            "confidence_score": self.confidence_score,
            "features_used": self.features_used,
            "prediction_metadata": self.prediction_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "actual_result": self.actual_result,
            "is_correct": self.is_correct,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


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
            feature_store (FootballFeatureStore): 特征存储实例 / Feature store instance
            mlflow_tracking_uri (str): MLflow跟踪URI / MLflow tracking URI
            metrics_exporter (ModelMetricsExporter): 指标导出器实例 / Metrics exporter instance
            model_cache (TTLCache): 模型缓存 / Model cache with TTL
            prediction_cache (TTLCache): 预测结果缓存 / Prediction result cache with TTL
            model_metadata_cache (Dict[str, Dict[str, Any]]): 模型元数据缓存 / Model metadata cache
            feature_order (List[str]): 特征顺序列表 / Feature order list
            model_cache_ttl (timedelta): 模型缓存TTL / Model cache TTL
            prediction_cache_ttl (timedelta): 预测结果缓存TTL / Prediction result cache TTL
        """
        self.db_manager = DatabaseManager()
        self.feature_store = FootballFeatureStore()
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.metrics_exporter = ModelMetricsExporter()

        # 设置MLflow跟踪URI / Set MLflow tracking URI
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)

        # 初始化TTL缓存 / Initialize TTL caches
        self.model_cache = TTLCache(max_size=10)  # 最多缓存10个模型 / Max 10 models
        self.prediction_cache = TTLCache(
            max_size=1000
        )  # 最多缓存1000个预测结果 / Max 1000 predictions

        # 配置缓存TTL / Configure cache TTLs
        model_cache_ttl_hours = int(os.getenv("MODEL_CACHE_TTL_HOURS", "1"))
        self.model_cache_ttl = timedelta(hours=model_cache_ttl_hours)

        prediction_cache_ttl_minutes = int(
            os.getenv("PREDICTION_CACHE_TTL_MINUTES", "30")
        )
        self.prediction_cache_ttl = timedelta(minutes=prediction_cache_ttl_minutes)

        # 模型元数据缓存 / Model metadata cache
        self.model_metadata_cache: Dict[str, Dict[str, Any]] = {}

        # 定义模型预期的特征顺序 / Define expected feature order for model
        self.feature_order: List[str] = [
            "home_recent_wins",
            "home_recent_goals_for",
            "home_recent_goals_against",
            "away_recent_wins",
            "away_recent_goals_for",
            "away_recent_goals_against",
            "h2h_home_advantage",
            "home_implied_probability",
            "draw_implied_probability",
            "away_implied_probability",
        ]

    @retry(MLFLOW_RETRY_CONFIG)
    async def get_production_model_with_retry(
        self, model_name: str = "football_baseline_model"
    ) -> Tuple[Any, str]:
        """
        获取生产环境模型（带重试机制） / Get Production Model (with Retry Mechanism)

        从MLflow获取生产环境模型，包含重试机制以提高可靠性。
        Get production model from MLflow with retry mechanism for improved reliability.

        Args:
            model_name (str): 模型名称 / Model name
                Defaults to "football_baseline_model"

        Returns:
            Tuple[Any, str]: 包含模型对象和版本号的元组 / Tuple containing model object and version
                - model (Any): 加载的模型对象 / Loaded model object
                - version (str): 模型版本号 / Model version number

        Raises:
            ValueError: 当没有可用的模型版本时抛出 / Raised when no model versions are available
            Exception: 当模型加载过程发生错误时抛出 / Raised when model loading process fails

        Example:
            ```python
            service = PredictionService()
            model, version = await service.get_production_model_with_retry("football_baseline_model")
            print(f"加载模型版本: {version}")
            ```

        Note:
            该方法会按照以下优先级获取模型：
            1. Production环境模型
            2. Staging环境模型
            3. 最新版本模型
            方法会缓存已加载的模型以提高性能，并支持TTL过期机制。
            包含自动重试机制，最大尝试3次。

            This method retrieves models with the following priority:
            1. Production environment model
            2. Staging environment model
            3. Latest version model
            The method caches loaded models to improve performance and supports TTL expiration.
            Includes automatic retry mechanism with up to 3 attempts.
        """
        return await self._load_model_from_mlflow(model_name)

    async def _load_model_from_mlflow(
        self, model_name: str = "football_baseline_model"
    ) -> Tuple[Any, str]:
        """
        从MLflow加载模型 / Load model from MLflow

        私有方法，实际从MLflow加载模型的实现。
        Private method, actual implementation for loading model from MLflow.

        Args:
            model_name (str): 模型名称 / Model name

        Returns:
            Tuple[Any, str]: 包含模型对象和版本号的元组 / Tuple containing model object and version
        """
        client = MlflowClient(tracking_uri=self.mlflow_tracking_uri)

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

    async def get_production_model(
        self, model_name: str = "football_baseline_model"
    ) -> Tuple[Any, str]:
        """
        获取生产环境模型 / Get Production Model

        Args:
            model_name (str): 模型名称 / Model name
                Defaults to "football_baseline_model"

        Returns:
            Tuple[Any, str]: 包含模型对象和版本号的元组 / Tuple containing model object and version
                - model (Any): 加载的模型对象 / Loaded model object
                - version (str): 模型版本号 / Model version number

        Raises:
            ValueError: 当没有可用的模型版本时抛出 / Raised when no model versions are available
            Exception: 当模型加载过程发生错误时抛出 / Raised when model loading process fails

        Example:
            ```python
            service = PredictionService()
            model, version = await service.get_production_model("football_baseline_model")
            print(f"加载模型版本: {version}")
            ```

        Note:
            该方法会按照以下优先级获取模型：
            1. Production环境模型
            2. Staging环境模型
            3. 最新版本模型
            方法会缓存已加载的模型以提高性能，并支持TTL过期机制。

            This method retrieves models with the following priority:
            1. Production environment model
            2. Staging environment model
            3. Latest version model
            The method caches loaded models to improve performance and supports TTL expiration.
        """
        # 创建缓存键 / Create cache key
        cache_key = f"model:{model_name}"

        # 尝试从缓存获取 / Try to get from cache
        cached_result = await self.model_cache.get(cache_key)
        if cached_result:
            model, version = cached_result
            logger.debug(
                f"使用缓存的模型 {model_name} 版本 {version} / Using cached model {model_name} version {version}"
            )
            return model, version
        try:
            # 使用带重试机制的方法加载模型
            model, version = await self.get_production_model_with_retry(model_name)

            # 构建模型URI
            model_uri = f"models:/{model_name}/{version}"

            # 缓存模型（带TTL） / Cache model with TTL
            await self.model_cache.set(
                cache_key, (model, version), ttl=self.model_cache_ttl
            )

            self.model_metadata_cache[model_uri] = {
                "name": model_name,
                "version": version,
                "stage": "unknown",  # Stage信息需要从model_version_info获取
                "loaded_at": datetime.now(),
            }

            logger.info(
                f"成功加载模型 {model_name} 版本 {version} / Successfully loaded model {model_name} version {version}"
            )
            return model, version
        except Exception as e:
            logger.error(f"加载生产模型失败: {e}")
            raise

    async def predict_match(self, match_id: int) -> PredictionResult:
        """
        预测比赛结果 / Predict Match Result

        对指定比赛进行实时预测，包括特征获取、模型推理和结果存储。
        支持带TTL的预测结果缓存以提高性能。

        Performs real-time prediction for specified match, including feature retrieval,
        model inference, and result storage. Supports TTL-based prediction result caching
        to improve performance.

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            PredictionResult: 包含预测结果的预测对象 / Prediction object containing results
                - match_id (int): 比赛ID / Match ID
                - model_version (str): 模型版本 / Model version
                - model_name (str): 模型名称 / Model name
                - home_win_probability (float): 主队获胜概率 (0-1) / Home win probability (0-1)
                - draw_probability (float): 平局概率 (0-1) / Draw probability (0-1)
                - away_win_probability (float): 客队获胜概率 (0-1) / Away win probability (0-1)
                - predicted_result (str): 预测结果 ('home', 'draw', 'away') / Predicted result
                - confidence_score (float): 预测置信度 (0-1) / Prediction confidence score
                - features_used (Dict): 使用的特征 / Features used
                - prediction_metadata (Dict): 预测元数据 / Prediction metadata
                - created_at (datetime): 预测创建时间 / Prediction creation time

        Raises:
            ValueError: 当比赛不存在时抛出 / Raised when match does not exist
            Exception: 当预测过程发生错误时抛出 / Raised when prediction process fails

        Example:
            ```python
            service = PredictionService()
            result = await service.predict_match(12345)
            print(f"预测结果: {result.predicted_result}, 置信度: {result.confidence_score}")
            ```

        Note:
            该方法会自动从特征存储获取最新特征并使用生产模型进行预测。
            预测结果会存储到数据库并导出到Prometheus监控系统。
            预测结果会被缓存以提高重复请求的性能。

            This method automatically retrieves latest features from feature store and uses
            production model for prediction. Prediction results are stored to database and
            exported to Prometheus monitoring system. Prediction results are cached to
            improve performance for repeated requests.
        """
        start_time = datetime.now()

        # 创建预测缓存键 / Create prediction cache key
        prediction_cache_key = f"prediction:{match_id}"

        # 尝试从缓存获取预测结果 / Try to get prediction result from cache
        cached_result = await self.prediction_cache.get(prediction_cache_key)
        if cached_result:
            logger.info(
                f"使用缓存的预测结果：比赛 {match_id} / Using cached prediction result for match {match_id}"
            )
            return cached_result
        try:
            logger.info(f"开始预测比赛 {match_id}")

            # 获取生产模型
            model, model_version = await self.get_production_model()

            # 查询比赛信息
            match_info = await self._get_match_info(match_id)
            if not match_info:
                raise ValueError(f"比赛 {match_id} 不存在")

            # 从特征存储获取实时特征
            try:
                raw_features = self.feature_store.get_match_features_for_prediction(
                    match_id=match_id,
                    home_team_id=match_info["home_team_id"],
                    away_team_id=match_info["away_team_id"],
                )
                features = (
                    await raw_features
                    if inspect.isawaitable(raw_features)
                    else raw_features
                )
            except Exception as e:
                logger.warning(f"获取比赛 {match_id} 的特征失败: {e}，使用默认特征")
                features = self._get_default_features()

            if not features:
                logger.warning(f"比赛 {match_id} 无法获取特征，使用默认特征")
                features = self._get_default_features()

            # 准备特征数组
            features_array = self._prepare_features_for_prediction(features)

            # 进行预测
            prediction_proba = model.predict_proba(features_array)
            predicted_class = model.predict(features_array)[0]

            # 解析预测结果
            # XGBoost分类器的类别顺序通常是按字母顺序：['away', 'draw', 'home']
            class_labels = ["away", "draw", "home"]
            prob_dict = dict(zip(class_labels, prediction_proba[0]))

            # 创建预测结果
            result = PredictionResult(
                match_id=match_id,
                model_version=model_version,
                model_name="football_baseline_model",
                home_win_probability=float(prob_dict.get("home", 0.0)),
                draw_probability=float(prob_dict.get("draw", 0.0)),
                away_win_probability=float(prob_dict.get("away", 0.0)),
                predicted_result=predicted_class,
                confidence_score=float(max(prediction_proba[0])),
                features_used=features,
                prediction_metadata={
                    "model_uri": f"models:/football_baseline_model/{model_version}",
                    "prediction_time": datetime.now().isoformat(),
                    "feature_count": len(features) if features else 0,
                },
                created_at=datetime.now(),
            )

            # 存储预测结果
            await self._store_prediction(result)

            # 导出指标
            self.metrics_exporter.export_prediction_metrics(result)

            # 记录预测时间
            prediction_duration = (datetime.now() - start_time).total_seconds()
            self.metrics_exporter.prediction_duration.labels(
                model_name="football_baseline_model", model_version=model_version
            ).observe(prediction_duration)

            # 缓存预测结果（带TTL） / Cache prediction result with TTL
            await self.prediction_cache.set(
                prediction_cache_key, result, ttl=self.prediction_cache_ttl
            )

            logger.info(
                f"比赛 {match_id} 预测完成：{predicted_class} (置信度: {result.confidence_score:.3f}) / "
                f"Match {match_id} prediction completed: {predicted_class} (confidence: {result.confidence_score:.3f})"
            )
            return result
        except Exception as e:
            logger.error(f"预测比赛 {match_id} 失败: {e}")
            raise

    async def _get_match_info(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛信息 / Get Match Information

        从数据库查询指定比赛的详细信息。
        Query detailed information of specified match from database.

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            Optional[Dict[str, Any]]: 包含比赛信息的字典，如果比赛不存在则返回None
                                     / Dictionary containing match information, or None if match doesn't exist
                - id (int): 比赛ID / Match ID
                - home_team_id (int): 主队ID / Home team ID
                - away_team_id (int): 客队ID / Away team ID
                - league_id (int): 联赛ID / League ID
                - match_time (datetime): 比赛时间 / Match time
                - match_status (str): 比赛状态 / Match status
                - season (str): 赛季 / Season

        Note:
            这是一个内部方法，不应该直接调用。
            This is an internal method and should not be called directly.
        """
        try:
            async with self.db_manager.get_async_session() as session:
                query = select(
                    Match.id,
                    Match.home_team_id,
                    Match.away_team_id,
                    Match.league_id,
                    Match.match_time,
                    Match.match_status,
                    Match.season,
                ).where(Match.id == match_id)

                result = await session.execute(query)
                match = result.first()

                if match:
                    return {
                        "id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "league_id": match.league_id,
                        "match_time": match.match_time,
                        "match_status": match.match_status,
                        "season": match.season,
                    }
                return None
        except Exception as e:
            logger.error(f"获取比赛信息失败: {e}")
            return None

    def _get_default_features(self) -> Dict[str, Any]:
        """
        获取默认特征（当特征服务不可用时） / Get Default Features (when feature service is unavailable)

        当无法从特征存储获取实时特征时，返回一组默认特征用于预测。

        Return a set of default features for prediction when real-time features
        cannot be retrieved from feature store.

        Returns:
            Dict[str, Any]: 默认特征字典 / Default features dictionary
                - home_recent_wins (int): 主队近期胜场数 / Home team recent wins
                - home_recent_goals_for (int): 主队近期进球数 / Home team recent goals for
                - home_recent_goals_against (int): 主队近期失球数 / Home team recent goals against
                - away_recent_wins (int): 客队近期胜场数 / Away team recent wins
                - away_recent_goals_for (int): 客队近期进球数 / Away team recent goals for
                - away_recent_goals_against (int): 客队近期失球数 / Away team recent goals against
                - h2h_home_advantage (float): 历史交锋主队优势 (0-1) / Head-to-head home advantage (0-1)
                - home_implied_probability (float): 主队隐含概率 (0-1) / Home team implied probability (0-1)
                - draw_implied_probability (float): 平局隐含概率 (0-1) / Draw implied probability (0-1)
                - away_implied_probability (float): 客队隐含概率 (0-1) / Away team implied probability (0-1)

        Example:
            ```python
            service = PredictionService()
            default_features = service._get_default_features()
            print(f"默认特征数量: {len(default_features)}")
            ```

        Note:
            这是一个内部方法，不应该直接调用。
            This is an internal method and should not be called directly.
        """
        return {
            "home_recent_wins": 2,
            "home_recent_goals_for": 6,
            "home_recent_goals_against": 4,
            "away_recent_wins": 2,
            "away_recent_goals_for": 5,
            "away_recent_goals_against": 5,
            "h2h_home_advantage": 0.5,
            "home_implied_probability": 0.4,
            "draw_implied_probability": 0.3,
            "away_implied_probability": 0.3,
        }

    def _prepare_features_for_prediction(self, features: Dict[str, Any]) -> np.ndarray:
        """
        准备用于预测的特征数组 / Prepare Feature Array for Prediction

        将特征字典转换为模型预测所需的数值数组，并确保特征顺序正确。

        Convert feature dictionary to numerical array required by model prediction
        and ensure correct feature order.

        Args:
            features (Dict[str, Any]): 特征字典 / Feature dictionary

        Returns:
            np.ndarray: 用于预测的二维特征数组 / 2D feature array for prediction
                Shape: (1, n_features) where n_features is the number of features

        Example:
            ```python
            service = PredictionService()
            features = {"home_recent_wins": 3, "away_recent_wins": 2, ...}
            feature_array = service._prepare_features_for_prediction(features)
            print(f"特征数组形状: {feature_array.shape}")
            ```

        Note:
            特征顺序必须与模型训练时保持一致。
            Feature order must be consistent with model training.
        """
        # 使用类中定义的特征顺序，保持一致性
        feature_values = []
        for feature_name in self.feature_order:
            value = features.get(str(feature_name), 0.0)
            feature_values.append(float(value))

        return np.array([feature_values])

    async def _store_prediction(self, result: PredictionResult) -> None:
        """
        存储预测结果到数据库 / Store Prediction Result to Database

        将预测结果保存到数据库的predictions表中。

        Save prediction result to predictions table in database.

        Args:
            result (PredictionResult): 预测结果对象 / Prediction result object

        Raises:
            Exception: 当数据库存储过程发生错误时抛出 / Raised when database storage process fails

        Example:
            ```python
            service = PredictionService()
            # ... perform prediction ...
            await service._store_prediction(prediction_result)
            ```

        Note:
            这是一个内部方法，包含事务处理和错误回滚。
            This is an internal method with transaction handling and error rollback.
        """
        async with self.db_manager.get_async_session() as session:
            try:
                prediction = Prediction(
                    match_id=result.match_id,
                    model_version=result.model_version,
                    model_name=result.model_name,
                    home_win_probability=result.home_win_probability,
                    draw_probability=result.draw_probability,
                    away_win_probability=result.away_win_probability,
                    predicted_result=result.predicted_result,
                    confidence_score=result.confidence_score,
                    features_used=result.features_used,
                    prediction_metadata=result.prediction_metadata,
                    created_at=result.created_at or datetime.now(),
                )

                add_result = session.add(prediction)
                if inspect.isawaitable(add_result):
                    await add_result
                await session.commit()
                logger.debug(f"预测结果已存储到数据库：比赛 {result.match_id}")

            except Exception as e:
                await session.rollback()
                logger.error(f"存储预测结果失败: {e}")
                raise

    async def verify_prediction(self, match_id: int) -> bool:
        """
        验证预测结果（比赛结束后调用） / Verify Prediction Result (call after match ends)

        在比赛结束后，将实际比赛结果与预测结果进行对比，更新预测准确性。

        After match ends, compare actual match result with prediction result and
        update prediction accuracy.

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            bool: 验证是否成功 / Whether verification was successful

        Example:
            ```python
            service = PredictionService()
            success = await service.verify_prediction(12345)
            if success:
                print("预测结果验证成功")
            ```

        Note:
            该方法应在比赛状态变为"finished"后调用。
            This method should be called after match status becomes "finished".
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 获取比赛实际结果
                match_query = select(
                    Match.id, Match.home_score, Match.away_score, Match.match_status
                ).where(
                    Match.id == match_id, Match.match_status == MatchStatus.FINISHED
                )

                match_result = await session.execute(match_query)
                match = match_result.first()

                if not match:
                    logger.warning(f"比赛 {match_id} 未完成或不存在")
                    return False
                # 计算实际结果
                actual_result = self._calculate_actual_result(
                    match.home_score, match.away_score
                )

                # 更新预测记录
                update_query = text(
                    """
                    UPDATE predictions
                    SET actual_result = :actual_result,
                        is_correct = (predicted_result = :actual_result),
                        verified_at = :verified_at
                    WHERE match_id = :match_id
                      AND actual_result IS NULL
                """
                )

                await session.execute(
                    update_query,
                    {
                        "actual_result": actual_result,
                        "match_id": match_id,
                        "verified_at": datetime.now(),
                    },
                )

                await session.commit()
                logger.info(f"比赛 {match_id} 预测结果已验证：实际结果 {actual_result}")
                return True
        except Exception as e:
            logger.error(f"验证预测结果失败: {e}")
            return False

    def _calculate_actual_result(self, home_score: int, away_score: int) -> str:
        """
        计算实际比赛结果 / Calculate Actual Match Result

        根据比赛比分计算实际比赛结果。

        Calculate actual match result based on match scores.

        Args:
            home_score (int): 主队进球数 / Home team goals
            away_score (int): 客队进球数 / Away team goals

        Returns:
            str: 比赛结果 ('home', 'draw', 'away') / Match result ('home', 'draw', 'away')

        Example:
            ```python
            service = PredictionService()
            result = service._calculate_actual_result(2, 1)
            print(f"实际结果: {result}")  # 输出: home
            ```

        Note:
            这是一个内部方法，不应该直接调用。
            This is an internal method and should not be called directly.
        """
        if home_score > away_score:
            return "home"
        elif home_score < away_score:
            return "away"
        else:
            return "draw"

    async def get_model_accuracy(
        self, model_name: str = "football_baseline_model", days: int = 7
    ) -> Optional[float]:
        """
        获取模型准确率 / Get Model Accuracy

        计算指定模型在最近N天内的预测准确率。

        Calculate prediction accuracy of specified model in recent N days.

        Args:
            model_name (str): 模型名称 / Model name
                Defaults to "football_baseline_model"
            days (int): 计算天数 / Calculation days
                Defaults to 7

        Returns:
            Optional[float]: 准确率（0-1之间），如果没有验证数据则返回None /
                           Accuracy (0-1), or None if no verification data
                Range: 0.0 - 1.0

        Example:
            ```python
            service = PredictionService()
            accuracy = await service.get_model_accuracy("football_baseline_model", 7)
            if accuracy:
                print(f"模型7天准确率: {accuracy:.2%}")
            ```

        Note:
            只计算已验证的预测结果（is_correct字段不为NULL）。
            Only calculates verified prediction results (is_correct field is not NULL).
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 查询最近N天已验证的预测
                query = text(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct
                    FROM predictions
                    WHERE model_name = :model_name
                      AND is_correct IS NOT NULL
                      AND created_at >= NOW() - INTERVAL ':days days'
                """
                )

                result = await session.execute(
                    query, {"model_name": model_name, "days": days}
                )

                row = result.first()
                if row and row.total > 0:
                    accuracy = row.correct / row.total
                    logger.info(
                        f"模型 {model_name} 最近 {days} 天准确率: {accuracy:.3f} ({row.correct}/{row.total})"
                    )
                    return float(accuracy)
                return None
        except Exception as e:
            logger.error(f"获取模型准确率失败: {e}")
            return None

    async def batch_predict_matches(
        self, match_ids: List[int]
    ) -> List[PredictionResult]:
        """
        批量预测比赛结果 / Batch Predict Match Results

        对多个比赛进行批量预测，提高处理效率。
        支持带TTL的预测结果缓存以提高性能。

        Perform batch prediction for multiple matches to improve processing efficiency.
        Supports TTL-based prediction result caching to improve performance.

        Args:
            match_ids (List[int]): 比赛ID列表 / List of match IDs

        Returns:
            List[PredictionResult]: 预测结果列表 / List of prediction results

        Example:
            ```python
            service = PredictionService()
            match_ids = [12345, 12346, 12347]
            results = await service.batch_predict_matches(match_ids)
            print(f"成功预测 {len(results)} 场比赛")
            ```

        Note:
            该方法会复用同一个模型实例以提高性能。
            批量预测的结果也会被缓存以提高重复请求的性能。

            This method reuses the same model instance to improve performance.
            Batch prediction results are also cached to improve performance for repeated requests.
        """
        results = []

        # 获取生产模型（只加载一次）
        model, model_version = await self.get_production_model()

        for match_id in match_ids:
            try:
                # 为每个比赛创建缓存键并检查缓存
                prediction_cache_key = f"prediction:{match_id}"
                cached_result = await self.prediction_cache.get(prediction_cache_key)

                if cached_result:
                    # 使用缓存的结果
                    logger.info(f"使用缓存的预测结果：比赛 {match_id}")
                    results.append(cached_result)
                else:
                    # 执行预测
                    result = await self.predict_match(match_id)
                    results.append(result)
            except Exception as e:
                logger.error(f"批量预测中，比赛 {match_id} 预测失败: {e}")
                continue

        logger.info(
            f"批量预测完成：{len(results)}/{len(match_ids)} 场比赛预测成功 / Batch prediction completed: {len(results)}/{len(match_ids)} matches predicted successfully"
        )
        return results

    async def get_prediction_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取预测统计信息 / Get Prediction Statistics

        获取最近N天内的预测统计信息，包括准确率、置信度分布等。

        Get prediction statistics for recent N days, including accuracy, confidence distribution, etc.

        Args:
            days (int): 统计天数 / Statistics days
                Defaults to 30

        Returns:
            Dict[str, Any]: 统计信息字典 / Statistics dictionary
                - period_days (int): 统计周期天数 / Statistics period days
                - statistics (List[Dict]): 各模型统计信息列表 / Model statistics list
                    - model_version (str): 模型版本 / Model version
                    - total_predictions (int): 总预测数 / Total predictions
                    - avg_confidence (float): 平均置信度 / Average confidence
                    - predictions_by_result (Dict): 按结果分类的预测数 / Predictions by result
                    - accuracy (float): 准确率 / Accuracy
                    - verified_predictions (int): 已验证预测数 / Verified predictions

        Example:
            ```python
            service = PredictionService()
            stats = await service.get_prediction_statistics(30)
            print(f"统计周期: {stats['period_days']} 天")
            for stat in stats['statistics']:
                print(f"模型 {stat['model_version']} 准确率: {stat['accuracy']:.2%}")
            ```

        Note:
            只统计已验证的预测结果。
            Only statistics verified prediction results.
        """
        try:
            async with self.db_manager.get_async_session() as session:
                query = text(
                    """
                    SELECT
                        model_version,
                        COUNT(*) as total_predictions,
                        AVG(confidence_score) as avg_confidence,
                        COUNT(CASE WHEN predicted_result = 'home' THEN 1 END) as home_predictions,
                        COUNT(CASE WHEN predicted_result = 'draw' THEN 1 END) as draw_predictions,
                        COUNT(CASE WHEN predicted_result = 'away' THEN 1 END) as away_predictions,
                        SUM(CASE WHEN is_correct = true THEN 1 ELSE 0 END) as correct_predictions,
                        COUNT(CASE WHEN is_correct IS NOT NULL THEN 1 END) as verified_predictions
                    FROM predictions
                    WHERE created_at >= NOW() - INTERVAL ':days days'
                    GROUP BY model_version
                    ORDER BY model_version DESC
                """
                )

                result = await session.execute(query, {"days": days})
                stats = []

                for row in result:
                    accuracy = (
                        row.correct_predictions / row.verified_predictions
                        if row.verified_predictions > 0
                        else None
                    )

                    stats.append(
                        {
                            "model_version": row.model_version,
                            "total_predictions": row.total_predictions,
                            "avg_confidence": (
                                float(row.avg_confidence) if row.avg_confidence else 0.0
                            ),
                            "predictions_by_result": {
                                "home": row.home_predictions,
                                "draw": row.draw_predictions,
                                "away": row.away_predictions,
                            },
                            "accuracy": accuracy,
                            "verified_predictions": row.verified_predictions,
                        }
                    )

                return {"period_days": days, "statistics": stats}
        except Exception as e:
            logger.error(f"获取预测统计信息失败: {e}")
            return {"period_days": days, "statistics": []}
