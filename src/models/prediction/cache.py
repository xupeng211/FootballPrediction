"""
预测缓存管理
Prediction Cache Management

提供预测结果的缓存功能。
"""




def get_ttl_cache(cache_key: str, ttl_seconds: float) -> TTLCache:
    """获取TTL缓存实例 / Get TTL cache instance"""
    return TTLCache(ttl_seconds=ttl_seconds)

logger = get_logger(__name__)


class PredictionCache:
    """
    预测缓存管理器 / Prediction Cache Manager

    管理预测结果的缓存，支持模型缓存和预测结果缓存。
    Manages prediction result caching, supports both model cache and prediction result cache.
    """

    def __init__(self, model_cache_ttl_hours: int = 1, prediction_cache_ttl_minutes: int = 30):
        """
        初始化缓存管理器 / Initialize cache manager

        Args:
            model_cache_ttl_hours (int): 模型缓存TTL小时数 / Model cache TTL in hours
            prediction_cache_ttl_minutes (int): 预测结果缓存TTL分钟数 / Prediction result cache TTL in minutes
        """
        self.model_cache = get_ttl_cache(
            cache_key="prediction_models",
            ttl_seconds=timedelta(hours=model_cache_ttl_hours).total_seconds()
        )

        self.prediction_cache = get_ttl_cache(
            cache_key="prediction_results",
            ttl_seconds=timedelta(minutes=prediction_cache_ttl_minutes).total_seconds()
        )

        self.feature_cache = get_ttl_cache(
            cache_key="match_features",
            ttl_seconds=timedelta(hours=2).total_seconds()  # 特征缓存2小时
        )

    async def get_model(self, model_name: str, model_version: str) -> Optional[Any]:
        """
        从缓存获取模型 / Get model from cache

        Args:
            model_name (str): 模型名称 / Model name
            model_version (str): 模型版本 / Model version

        Returns:
            Optional[Any]: 缓存的模型对象，如果不存在则返回None / Cached model object, None if not exists
        """
        try:
            cache_key = f"{model_name}:{model_version}"
            return await self.model_cache.get(cache_key)
        except Exception as e:
            logger.error(f"从缓存获取模型失败: {e}")
            return None

    async def set_model(self, model_name: str, model_version: str, model: Any) -> None:
        """
        将模型存入缓存 / Store model in cache

        Args:
            model_name (str): 模型名称 / Model name
            model_version (str): 模型版本 / Model version
            model (Any): 模型对象 / Model object
        """
        try:
            cache_key = f"{model_name}:{model_version}"
            await self.model_cache.set(cache_key, model)
            logger.info(f"模型已缓存: {model_name}:{model_version}")
        except Exception as e:
            logger.error(f"缓存模型失败: {e}")

    async def get_prediction(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        从缓存获取预测结果 / Get prediction result from cache

        Args:
            match_id (int): 比赛ID / Match ID

        Returns:
            Optional[Dict[str, Any]]: 缓存的预测结果，如果不存在则返回None / Cached prediction result, None if not exists
        """
        try:
            return await self.prediction_cache.get(str(match_id))
        except Exception as e:
            logger.error(f"从缓存获取预测结果失败: {e}")
            return None

    async def set_prediction(self, match_id: int, prediction: Dict[str, Any]) -> None:
        """
        将预测结果存入缓存 / Store prediction result in cache

        Args:
            match_id (int): 比赛ID / Match ID
            prediction (Dict[str, Any]): 预测结果 / Prediction result
        """
        try:
            await self.prediction_cache.set(str(match_id), prediction)
        except Exception as e:
            logger.error(f"缓存预测结果失败: {e}")

    async def get_features(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        从缓存获取特征 / Get features from cache

        Args:
            match_id (int): 比赛ID / Match ID

        Returns:
            Optional[Dict[str, Any]]: 缓存的特征，如果不存在则返回None / Cached features, None if not exists
        """
        try:
            return await self.feature_cache.get(str(match_id))
        except Exception as e:
            logger.error(f"从缓存获取特征失败: {e}")
            return None

    async def set_features(self, match_id: int, features: Dict[str, Any]) -> None:
        """
        将特征存入缓存 / Store features in cache

        Args:
            match_id (int): 比赛ID / Match ID
            features (Dict[str, Any]): 特征字典 / Feature dictionary
        """
        try:
            await self.feature_cache.set(str(match_id), features)
        except Exception as e:
            logger.error(f"缓存特征失败: {e}")

    async def invalidate_prediction(self, match_id: int) -> None:
        """
        使特定比赛的预测缓存失效 / Invalidate prediction cache for specific match

        Args:
            match_id (int): 比赛ID / Match ID
        """
        try:
            await self.prediction_cache.delete(str(match_id))
            await self.feature_cache.delete(str(match_id))
            logger.info(f"已使比赛 {match_id} 的缓存失效")
        except Exception as e:
            logger.error(f"使缓存失效失败: {e}")

    async def clear_all_caches(self) -> None:
        """
        清空所有缓存 / Clear all caches
        """
        try:
            await self.model_cache.clear()
            await self.prediction_cache.clear()
            await self.feature_cache.clear()
            logger.info("已清空所有预测缓存")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息 / Get cache statistics

        Returns:
            Dict[str, Any]: 缓存统计信息 / Cache statistics
        """
        try:
            stats = {
                "model_cache": await self.model_cache.get_stats(),
                "prediction_cache": await self.prediction_cache.get_stats(),
                "prediction_cache": await self.prediction_cache.get_stats(),)


                "timestamp": datetime.now().isoformat()
            }
            return stats
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }