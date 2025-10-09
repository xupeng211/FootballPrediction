"""
from .statistics import PredictionStatistics
from src.cache.redis.core.key_manager import CacheKeyManager
from src.cache.redis_manager import RedisManager
from src.database.connection import DatabaseManager
from src.features.feature_store import FootballFeatureStore
from src.monitoring.metrics_exporter import MetricsExporter

足球预测引擎
Football Prediction Engine

提供完整的比赛预测功能。
"""




logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    足球预测引擎主类
    Football Prediction Engine Main Class

    提供完整的比赛预测功能，包括：
    - 实时比赛预测
    - 批量预测处理
    - 模型性能监控
    - 缓存优化
    - 数据收集管道

    Provides complete match prediction functionality, including:
    - Real-time match prediction
    - Batch prediction processing
    - Model performance monitoring
    - Cache optimization
    - Data collection pipeline
    """

    def __init__(
        self,
        config: Optional[PredictionConfig] = None,
        db_manager: Optional[DatabaseManager] = None,
        redis_manager: Optional[RedisManager] = None,
    ):
        """
        初始化预测引擎

        Args:
            config: 预测配置
            db_manager: 数据库管理器
            redis_manager: Redis缓存管理器
        """
        # 配置
        self.config = config or PredictionConfig.from_env()

        # 核心组件
        self.db_manager = db_manager or DatabaseManager()
        self.redis_manager = redis_manager or RedisManager()
        self.cache_key_manager = CacheKeyManager()

        # 初始化子模块
        self.cache_manager = PredictionCacheManager(
            self.redis_manager, self.cache_key_manager
        )
        self.data_loader = PredictionDataLoader(self.db_manager)
        self.model_loader = ModelLoader(self.config.mlflow_tracking_uri)
        self.feature_store = FootballFeatureStore()
        self.statistics = PredictionStatistics()

        # 指标导出器
        self.metrics_exporter = MetricsExporter()

        # 初始化模型
        self._model_initialized = False

    async def initialize(self):
        """初始化引擎"""
        try:
            # 加载默认模型
            success = await self.model_loader.load_model()
            if not success:
                logger.warning("加载默认模型失败，将在使用时重试")
            else:
                self._model_initialized = True

            # 预热缓存（如果启用）
            if self.config.cache_warmup_enabled:
                await self._warmup_cache()

            logger.info("预测引擎初始化完成")
        except Exception as e:
            logger.error(f"预测引擎初始化失败: {e}")
            raise

    async def _warmup_cache(self):
        """预热缓存"""
        try:
            # 获取即将到来的比赛
            upcoming_matches = await self.data_loader.get_upcoming_matches(
                hours=24, limit=50
            )

            if upcoming_matches:
                match_ids = [m["id"] for m in upcoming_matches]
                await self.cache_manager.warmup_cache(match_ids)
                logger.info(f"预热缓存完成，比赛数量: {len(match_ids)}")
        except Exception as e:
            logger.error(f"预热缓存失败: {e}")

    async def predict_match(
        self,
        match_id: int,
        force_refresh: bool = False,
        include_features: bool = False,
    ) -> Dict[str, Any]:
        """
        预测单场比赛结果

        Args:
            match_id: 比赛ID
            force_refresh: 是否强制刷新缓存
            include_features: 是否包含特征信息

        Returns:
            Dict[str, Any]: 预测结果
        """
        start_time = time.time()

        # 检查缓存
        if not force_refresh:
            cached_result = await self.cache_manager.get_prediction(match_id)
            if cached_result:
                self.statistics.record_cache_hit()
                if include_features and "features" not in cached_result:
                    cached_result["features"] = await self._get_match_features(
                        match_id
                    )
                return cached_result

        self.statistics.record_cache_miss()

        try:
            # 确保模型已加载
            if not self._model_initialized:
                await self.model_loader.load_model()
                self._model_initialized = True

            # 获取比赛信息
            match_info = await self.data_loader.get_match_info(match_id)
            if not match_info:
                raise ValueError(f"比赛 {match_id} 不存在")

            # 收集最新数据
            await self.data_loader.collect_latest_data(match_id, match_info)

            # 执行预测
            prediction_result = await self.model_loader.predict_match(match_id)
            if not prediction_result:
                raise RuntimeError("预测服务返回空结果")

            # 构建响应
            result = {
                "match_id": match_id,
                "prediction": prediction_result.predicted_result,
                "probabilities": {
                    "home_win": prediction_result.home_win_probability,
                    "draw": prediction_result.draw_probability,
                    "away_win": prediction_result.away_win_probability,
                },
                "confidence": prediction_result.confidence_score,
                "model_version": prediction_result.model_version,
                "model_name": prediction_result.model_name,
                "prediction_time": prediction_result.created_at.isoformat(),
                "match_info": match_info,
            }

            # 添加特征信息（如果需要）
            if include_features:
                result["features"] = await self._get_match_features(match_id)

            # 添加赔率信息
            odds_info = await self.data_loader.get_match_odds(match_id)
            if odds_info:
                result["odds"] = odds_info

            # 缓存结果
            await self.cache_manager.set_prediction(
                match_id, result, ttl=self.config.cache_ttl_predictions
            )

            # 更新统计
            prediction_time = time.time() - start_time
            self.statistics.record_prediction(prediction_time)

            # 导出指标
            self.metrics_exporter.increment_counter("predictions_total")
            self.metrics_exporter.record_histogram(
                "prediction_duration_seconds", prediction_time
            )
            self.metrics_exporter.set_gauge(
                "prediction_confidence", prediction_result.confidence_score
            )

            logger.info(
                f"比赛 {match_id} 预测完成: {prediction_result.predicted_result} "
                f"(置信度: {prediction_result.confidence_score:.3f}, "
                f"耗时: {prediction_time:.3f}s)"
            )

            return result

        except Exception as e:
            self.statistics.record_error()
            logger.error(f"预测比赛 {match_id} 失败: {e}")
            self.metrics_exporter.increment_counter("prediction_errors")
            raise

    async def batch_predict(
        self,
        match_ids: List[int],
        force_refresh: bool = False,
        include_features: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        批量预测比赛结果

        Args:
            match_ids: 比赛ID列表
            force_refresh: 是否强制刷新缓存
            include_features: 是否包含特征信息

        Returns:
            List[Dict[str, Any]]: 预测结果列表
        """
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(self.config.max_concurrent_predictions)

        async def predict_with_semaphore(match_id: int) -> Dict[str, Any]:
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self.predict_match(match_id, force_refresh, include_features),
                        timeout=self.config.prediction_timeout,
                    )
                except asyncio.TimeoutError:
                    logger.error(f"预测超时: 比赛 {match_id}")
                    self.statistics.record_error("timeout")
                    return {
                        "match_id": match_id,
                        "error": "prediction_timeout",
                        "message": "预测超时",
                    }
                except Exception as e:
                    logger.error(f"预测失败: 比赛 {match_id}, 错误: {e}")
                    self.statistics.record_error("unknown")
                    return {
                        "match_id": match_id,
                        "error": "prediction_failed",
                        "message": str(e),
                    }

        # 执行批量预测
        start_time = time.time()
        tasks = [predict_with_semaphore(mid) for mid in match_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        batch_time = time.time() - start_time

        # 统计结果
        successful = sum(1 for r in results if isinstance(r, dict) and "error" not in r)
        failed = len(results) - successful

        self.statistics.record_batch_prediction(len(match_ids))

        logger.info(
            f"批量预测完成: 总数 {len(match_ids)}, "
            f"成功 {successful}, 失败 {failed}, "
            f"耗时 {batch_time:.3f}s"
        )

        # 导出指标
        self.metrics_exporter.increment_counter("batch_predictions_total")
        self.metrics_exporter.set_gauge("batch_prediction_size", len(match_ids))
        self.metrics_exporter.set_gauge(
            "batch_prediction_success_rate", successful / len(match_ids)
        )

        return results

    async def _get_match_features(self, match_id: int) -> Optional[Dict[str, Any]]:
        """获取比赛特征"""
        try:
            # 先检查缓存
            cached_features = await self.cache_manager.get_features(match_id)
            if cached_features:
                return cached_features

            # 从特征存储获取
            features = await self.feature_store.get_match_features(match_id)
            if features:
                # 缓存特征
                await self.cache_manager.set_features(
                    match_id, features, ttl=self.config.cache_ttl_features
                )
            return features
        except Exception as e:
            logger.error(f"获取特征失败: {e}")
            return None

    async def get_statistics(self) -> Dict[str, Any]:
        """获取预测统计信息"""
        stats = self.statistics.to_dict()

        # 添加模型信息
        model_info = self.model_loader.get_model_info()
        stats["model"] = model_info

        # 添加配置信息
        stats["config"] = {
            "max_concurrent_predictions": self.config.max_concurrent_predictions,
            "prediction_timeout": self.config.prediction_timeout,
            "cache_warmup_enabled": self.config.cache_warmup_enabled,
        }

        return stats

    async def switch_model(
        self, model_name: str, version: Optional[str] = None
    ) -> bool:
        """
        切换预测模型

        Args:
            model_name: 模型名称
            version: 模型版本

        Returns:
            是否切换成功
        """
        try:
            success = await self.model_loader.switch_model(model_name, version)
            if success:
                self._model_initialized = True
                # 清除缓存以确保使用新模型
                await self.cache_manager.clear_all_predictions()
                logger.info(f"成功切换到模型: {model_name}:{version or 'latest'}")
            return success
        except Exception as e:
            logger.error(f"切换模型失败: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            "status": "healthy",
            "checks": {},
        }

        try:
            # 检查数据库连接
            async with self.db_manager.get_async_session() as session:
                await session.execute("SELECT 1")
            health["checks"]["database"] = "healthy"
        except Exception as e:
            health["checks"]["database"] = f"unhealthy: {e}"
            health["status"] = "degraded"



        try:
            # 检查Redis连接
            await self.redis_manager.aping()
            health["checks"]["redis"] = "healthy"
        except Exception as e:
            health["checks"]["redis"] = f"unhealthy: {e}"
            health["status"] = "degraded"

        # 检查模型状态
        if self._model_initialized:
            health["checks"]["model"] = "healthy"
        else:
            health["checks"]["model"] = "not_initialized"
            health["status"] = "degraded"

        # 检查性能指标
        if (
            self.statistics.avg_prediction_time
            > self.config.performance_error_threshold
        ):
            health["checks"]["performance"] = "poor"
            health["status"] = "degraded"
        elif (
            self.statistics.avg_prediction_time
            > self.config.performance_warning_threshold
        ):
            health["checks"]["performance"] = "warning"
        else:
            health["checks"]["performance"] = "good"

        return health