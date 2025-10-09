"""
预测缓存管理器
Prediction Cache Manager

管理预测结果的缓存。
"""

import logging
from typing import Any, Dict, Optional

from src.cache.redis_manager import RedisManager
from src.cache.redis.core.key_manager import CacheKeyManager

logger = logging.getLogger(__name__)


class PredictionCacheManager:
    """预测缓存管理器"""

    def __init__(
        self,
        redis_manager: RedisManager,
        cache_key_manager: Optional[CacheKeyManager] = None,
    ):
        """
        初始化缓存管理器

        Args:
            redis_manager: Redis管理器
            cache_key_manager: 缓存键管理器
        """
        self.redis_manager = redis_manager
        self.cache_key_manager = cache_key_manager or CacheKeyManager()

    async def get_prediction(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取预测结果缓存

        Args:
            match_id: 比赛ID

        Returns:
            预测结果或None
        """
        cache_key = self.cache_key_manager.prediction_key(match_id)
        try:
            result = await self.redis_manager.aget(cache_key)
            if result:
                logger.debug(f"缓存命中: 比赛 {match_id}")
            return result
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    async def set_prediction(
        self,
        match_id: int,
        prediction: Dict[str, Any],
        ttl: Optional[int] = None,
    ):
        """
        设置预测结果缓存

        Args:
            match_id: 比赛ID
            prediction: 预测结果
            ttl: 过期时间（秒）
        """
        cache_key = self.cache_key_manager.prediction_key(match_id)
        if ttl is None:
            ttl = self.cache_key_manager.get_ttl("predictions")

        try:
            await self.redis_manager.aset(cache_key, prediction, ttl=ttl)
            logger.debug(f"缓存设置: 比赛 {match_id}, TTL: {ttl}s")
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")

    async def get_features(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取特征缓存

        Args:
            match_id: 比赛ID

        Returns:
            特征数据或None
        """
        cache_key = self.cache_key_manager.features_key(match_id)
        try:
            result = await self.redis_manager.aget(cache_key)
            if result:
                logger.debug(f"特征缓存命中: 比赛 {match_id}")
            return result
        except Exception as e:
            logger.error(f"获取特征缓存失败: {e}")
            return None

    async def set_features(
        self,
        match_id: int,
        features: Dict[str, Any],
        ttl: Optional[int] = None,
    ):
        """
        设置特征缓存

        Args:
            match_id: 比赛ID
            features: 特征数据
            ttl: 过期时间（秒）
        """
        cache_key = self.cache_key_manager.features_key(match_id)
        if ttl is None:
            ttl = self.cache_key_manager.get_ttl("features")

        try:
            await self.redis_manager.aset(cache_key, features, ttl=ttl)
            logger.debug(f"特征缓存设置: 比赛 {match_id}, TTL: {ttl}s")
        except Exception as e:
            logger.error(f"设置特征缓存失败: {e}")

    async def get_odds(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取赔率缓存

        Args:
            match_id: 比赛ID

        Returns:
            赔率数据或None
        """
        cache_key = f"odds:match:{match_id}"
        try:
            result = await self.redis_manager.aget(cache_key)
            if result:
                logger.debug(f"赔率缓存命中: 比赛 {match_id}")
            return result
        except Exception as e:
            logger.error(f"获取赔率缓存失败: {e}")
            return None

    async def set_odds(
        self,
        match_id: int,
        odds: Dict[str, Any],
        ttl: Optional[int] = None,
    ):
        """
        设置赔率缓存

        Args:
            match_id: 比赛ID
            odds: 赔率数据
            ttl: 过期时间（秒）
        """
        cache_key = f"odds:match:{match_id}"
        if ttl is None:
            ttl = 300  # 赔率缓存5分钟

        try:
            await self.redis_manager.aset(cache_key, odds, ttl=ttl)
            logger.debug(f"赔率缓存设置: 比赛 {match_id}, TTL: {ttl}s")
        except Exception as e:
            logger.error(f"设置赔率缓存失败: {e}")

    async def invalidate_match(self, match_id: int):
        """
        使比赛相关的缓存失效

        Args:
            match_id: 比赛ID
        """
        keys_to_delete = [
            self.cache_key_manager.prediction_key(match_id),
            self.cache_key_manager.features_key(match_id),
            f"odds:match:{match_id}",
        ]

        for key in keys_to_delete:
            try:
                await self.redis_manager.adelete(key)
                logger.debug(f"缓存失效: {key}")
            except Exception as e:
                logger.error(f"缓存失效失败: {key}, 错误: {e}")

    async def warmup_cache(self, match_ids: list[int]):
        """
        预热缓存

        Args:
            match_ids: 比赛ID列表
        """
        logger.info(f"开始预热缓存，比赛数量: {len(match_ids)}")
        for match_id in match_ids:
            try:
                # 检查是否已有缓存
                if not await self.get_prediction(match_id):
                    # 触发预测以生成缓存
                    logger.debug(f"预热缓存: 比赛 {match_id}")
                    # 这里应该调用预测服务，但为了避免循环依赖
                    # 我们只记录日志，实际预热由引擎处理
            except Exception as e:
                logger.error(f"预热缓存失败: 比赛 {match_id}, 错误: {e}")

    async def clear_all_predictions(self):
        """清除所有预测缓存"""
        try:
            # 使用Redis模式匹配删除所有预测相关键
            pattern = "prediction:*"
            keys = await self.redis_manager.keys(pattern)
            if keys:
                await self.redis_manager.delete(*keys)
                logger.info(f"清除预测缓存: {len(keys)} 个键")
        except Exception as e:
            logger.error(f"清除预测缓存失败: {e}")