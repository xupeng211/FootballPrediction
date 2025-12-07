"""统一缓存管理器
Unified Cache Manager.

提供统一的多级缓存管理，包括本地缓存和Redis缓存。
Provides unified multi-level cache management including local cache and Redis cache.
"""

import hashlib
import logging
import pickle
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class UnifiedCacheManager:
    """统一缓存管理器 - 多级缓存实现."""

    def __init__(self, redis_client=None, local_cache_size: int = 1000):
        self.redis_client = redis_client
        self.local_cache = {}  # L1本地缓存
        self.local_cache_size = local_cache_size
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "local_hits": 0,
            "redis_hits": 0,
            "sets": 0,
            "deletes": 0,
        }
        self.cache_config = self._get_cache_config()

    def _get_cache_config(self) -> dict[str, int]:
        """获取统一的缓存配置."""
        return {
            # 预测相关缓存 - 高频访问
            "prediction_result": 3600,  # 1小时
            "prediction_model": 86400,  # 24小时
            "team_stats": 1800,  # 30分钟
            "match_data": 900,  # 15分钟
            "odds_data": 300,  # 5分钟
            # API响应缓存 - 中频访问
            "api_response": 300,  # 5分钟
            "user_session": 1800,  # 30分钟
            "auth_token": 1800,  # 30分钟
            "user_preferences": 3600,  # 1小时
            # 数据缓存 - 低频访问
            "league_data": 3600,  # 1小时
            "team_data": 7200,  # 2小时
            "season_data": 86400,  # 24小时
            # 功能性缓存
            "feature_calculation": 600,  # 10分钟
            "model_training": 86400,  # 24小时
            "analytics": 1800,  # 30分钟
            # 默认缓存
            "default": 300,  # 5分钟
        }

    def _generate_cache_key(self, key: str, cache_type: str) -> str:
        """生成缓存键."""
        return f"{cache_type}:{key}"

    def _update_local_cache(self, key: str, value: Any, ttl: int | None = None):
        """更新本地缓存（LRU实现 + TTL支持）."""
        if len(self.local_cache) >= self.local_cache_size:
            # 简单的LRU实现：删除最旧的条目
            oldest_key = min(
                self.local_cache.keys(), key=lambda k: self.local_cache[k]["timestamp"]
            )
            del self.local_cache[oldest_key]

        # 计算过期时间
        expire_time = None
        if ttl is not None:
            expire_time = time.time() + ttl

        self.local_cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "expire_time": expire_time,
        }

    def _serialize_data(self, data: Any) -> bytes:
        """序列化数据."""
        try:
            if isinstance(data, str | int | float | bool):
                return str(data).encode("utf-8")
            else:
                return pickle.dumps(data)
        except Exception as e:
            logger.error(f"Data serialization error: {e}")
            # 返回空字典的序列化结果，避免递归调用
            return b"{}"

    def _deserialize_data(self, data: bytes) -> Any:
        """反序列化数据."""
        try:
            # 尝试反序列化为字符串
            return data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                # 尝试pickle反序列化
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Data deserialization error: {e}")
                return None

    async def get(self, key: str, cache_type: str = "default") -> Any | None:
        """获取缓存数据 - 多级缓存."""
        time.time()

        # 生成缓存键
        cache_key = self._generate_cache_key(key, cache_type)

        # L1: 本地缓存检查
        if cache_key in self.local_cache:
            cache_entry = self.local_cache[cache_key]

            # 检查TTL过期
            if cache_entry.get("expire_time") is not None:
                if time.time() > cache_entry["expire_time"]:
                    # 缓存已过期，删除并继续
                    del self.local_cache[cache_key]
                    logger.debug(f"Cache expired (L1): {key}")
                else:
                    # 缓存未过期，返回值
                    self.cache_stats["hits"] += 1
                    self.cache_stats["local_hits"] += 1
                    logger.debug(f"Cache hit (L1): {key}")
                    return cache_entry["value"]
            else:
                # 没有过期时间，直接返回
                self.cache_stats["hits"] += 1
                self.cache_stats["local_hits"] += 1
                logger.debug(f"Cache hit (L1): {key}")
                return cache_entry["value"]

        # L2: Redis缓存检查（如果可用）
        if self.redis_client:
            try:
                redis_key = f"cache:{cache_key}"
                cached_data = await self.redis_client.get(redis_key)

                if cached_data:
                    # 反序列化数据
                    data = self._deserialize_data(cached_data)
                    if data is not None:
                        # 更新本地缓存
                        self._update_local_cache(cache_key, data)
                        self.cache_stats["hits"] += 1
                        self.cache_stats["redis_hits"] += 1
                        logger.debug(f"Cache hit (L2): {key}")
                        return data

            except Exception as e:
                logger.error(f"Redis cache get error for {key}: {e}")

        # 缓存未命中
        self.cache_stats["misses"] += 1
        logger.debug(f"Cache miss: {key}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        cache_type: str = "default",
        ttl: int | None = None,
    ) -> bool:
        """设置缓存数据."""
        time.time()

        try:
            # 获取TTL
            if ttl is None:
                ttl = self.cache_config.get(cache_type, 300)

            # 生成缓存键
            cache_key = self._generate_cache_key(key, cache_type)

            # 更新本地缓存
            self._update_local_cache(cache_key, value, ttl)

            # 设置Redis缓存（如果可用）
            if self.redis_client:
                try:
                    serialized_data = self._serialize_data(value)
                    redis_key = f"cache:{cache_key}"
                    await self.redis_client.setex(redis_key, ttl, serialized_data)
                    logger.debug(f"Cache set (L1+L2): {key} (TTL: {ttl}s)")
                except Exception as e:
                    logger.error(f"Redis cache set error for {key}: {e}")
            else:
                logger.debug(f"Cache set (L1 only): {key} (TTL: {ttl}s)")

            self.cache_stats["sets"] += 1
            return True

        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    async def delete(self, key: str, cache_type: str = "default") -> bool:
        """删除缓存数据."""
        try:
            cache_key = self._generate_cache_key(key, cache_type)

            # 删除本地缓存
            if cache_key in self.local_cache:
                del self.local_cache[cache_key]

            # 删除Redis缓存
            if self.redis_client:
                try:
                    redis_key = f"cache:{cache_key}"
                    await self.redis_client.delete(redis_key)
                    logger.debug(f"Cache deleted (L1+L2): {key}")
                except Exception as e:
                    logger.error(f"Redis cache delete error for {key}: {e}")
            else:
                logger.debug(f"Cache deleted (L1 only): {key}")

            self.cache_stats["deletes"] += 1
            return True

        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str, cache_type: str = None):
        """批量删除匹配模式的缓存."""
        try:
            # 删除本地缓存匹配项
            if cache_type:
                # 匹配格式为 cache_type:key，且key以pattern开头
                keys_to_remove = [
                    k
                    for k in self.local_cache.keys()
                    if k.startswith(f"{cache_type}:")
                    and len(k.split(":")) > 1
                    and k.split(":", 1)[1].startswith(pattern)
                ]
            else:
                keys_to_remove = [k for k in self.local_cache.keys() if pattern in k]

            for key in keys_to_remove:
                del self.local_cache[key]
                logger.debug(f"Local cache deleted: {key}")

            # 删除Redis缓存匹配项
            if self.redis_client:
                try:
                    if cache_type:
                        redis_pattern = f"cache:{cache_type}:*{pattern}*"
                    else:
                        redis_pattern = f"cache:*{pattern}*"

                    keys = await self.redis_client.keys(redis_pattern)
                    if keys:
                        await self.redis_client.delete(*keys)
                        logger.info(
                            f"Invalidated {len(keys)} Redis cache entries matching: {pattern}"
                        )
                except Exception as e:
                    logger.error(f"Redis cache invalidation error: {e}")

            logger.info(
                f"Cache invalidation completed: pattern='{pattern}', type='{cache_type}'"
            )

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息."""
        stats = self.cache_stats.copy()

        # 计算命中率
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_rate"] = stats["hits"] / total_requests
            stats["local_hit_rate"] = stats["local_hits"] / total_requests
            stats["redis_hit_rate"] = stats["redis_hits"] / total_requests
        else:
            stats["hit_rate"] = 0.0
            stats["local_hit_rate"] = 0.0
            stats["redis_hit_rate"] = 0.0

        stats["local_cache_size"] = len(self.local_cache)
        stats["config"] = self.cache_config

        return stats

    async def cleanup_expired_entries(self):
        """清理过期的本地缓存条目."""
        try:
            current_time = time.time()
            expired_keys = []

            for key, entry in self.local_cache.items():
                # 检查是否过期（简单的5分钟过期策略）
                if current_time - entry["timestamp"] > 300:  # 5分钟
                    expired_keys.append(key)

            for key in expired_keys:
                del self.local_cache[key]

            if expired_keys:
                logger.info(
                    f"Cleaned up {len(expired_keys)} expired local cache entries"
                )

        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")


# 全局缓存管理器实例
_cache_manager: UnifiedCacheManager | None = None


def get_cache_manager() -> UnifiedCacheManager:
    """获取全局缓存管理器实例."""
    global _cache_manager
    if _cache_manager is None:
        # 尝试初始化Redis客户端
        try:
            import redis.asyncio as redis

            redis_client = redis.Redis(
                host="localhost", port=6379, db=0, decode_responses=False
            )
        except Exception as e:
            logger.warning(
                f"Redis client initialization failed: {e}, using local cache only"
            )
            redis_client = None

        _cache_manager = UnifiedCacheManager(redis_client)
    return _cache_manager


# 缓存装饰器
def cached(
    cache_type: str = "default",
    ttl: int | None = None,
    key_func: Callable | None = None,
):
    """缓存装饰器."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 使用函数名和参数生成哈希键
                param_str = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                cache_key = hashlib.md5(
                    param_str.encode(), usedforsecurity=False
                ).hexdigest()

            # 尝试从缓存获取
            cache_manager = get_cache_manager()
            cached_result = await cache_manager.get(cache_key, cache_type)

            if cached_result is not None:
                logger.debug(f"Cache hit for function {func.__name__}")
                return cached_result

            # 执行函数并缓存结果
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # 缓存结果
            await cache_manager.set(cache_key, result, cache_type, ttl)

            logger.debug(
                f"Function {func.__name__} executed in {execution_time:.3f}s, cached for {ttl or 'default'}s"
            )
            return result

        return wrapper

    return decorator


# 性能监控装饰器
def performance_monitor(threshold: float = 1.0):
    """性能监控装饰器."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                if execution_time > threshold:
                    logger.warning(
                        f"Slow function detected: {func.__name__} took {execution_time:.3f}s (threshold: {threshold}s)"
                    )

                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function {func.__name__} failed after {execution_time:.3f}s: {e}"
                )
                raise

        return wrapper

    return decorator
