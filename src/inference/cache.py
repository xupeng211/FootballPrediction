"""
Prediction Cache
Redis缓存层

提供高性能的预测结果缓存功能，支持TTL、序列化和监控。
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from pathlib import Path

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from .errors import CacheError, ErrorCode

logger = logging.getLogger(__name__)


class PredictionCache:
    """
    预测结果缓存

    功能：
    1. Redis连接管理
    2. 自动序列化/反序列化
    3. TTL管理
    4. 缓存统计
    5. 健康检查
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 300,  # 5分钟默认TTL
        key_prefix: str = "football_prediction:",
        max_connections: int = 10
    ):
        """
        初始化缓存

        Args:
            redis_url: Redis连接URL
            default_ttl: 默认TTL（秒）
            key_prefix: 键前缀
            max_connections: 最大连接数
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.max_connections = max_connections

        # Redis连接池
        self._pool: Optional[ConnectionPool] = None
        self._redis_client: Optional[redis.Redis] = None

        # 缓存统计
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
            "last_operation": None,
            "created_at": datetime.utcnow()
        }

        # 健康检查
        self._last_health_check = None
        self._is_healthy = False

    async def initialize(self):
        """初始化Redis连接"""
        try:
            # 创建连接池
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )

            # 创建Redis客户端
            self._redis_client = redis.Redis(connection_pool=self._pool)

            # 测试连接
            await self._redis_client.ping()
            self._is_healthy = True
            self._last_health_check = datetime.utcnow()

            logger.info(f"PredictionCache initialized: {self.redis_url}")

        except Exception as e:
            self._is_healthy = False
            raise CacheError(f"Failed to initialize Redis cache: {str(e)}")

    async def get_prediction(self, cache_key: str) -> Optional[dict[str, Any]]:
        """
        获取缓存的预测结果

        Args:
            cache_key: 缓存键

        Returns:
            Optional[]: 缓存的预测数据，如果不存在返回None

        Raises:
            CacheError: 缓存操作失败
        """
        full_key = self._make_key(cache_key)

        try:
            # 获取缓存值
            cached_data = await self._redis_client.get(full_key)

            if cached_data is None:
                self._stats["misses"] += 1
                self._update_last_operation("get_miss", cache_key)
                return None

            # 反序列化
            try:
                data = json.loads(cached_data.decode('utf-8'))
                self._stats["hits"] += 1
                self._update_last_operation("get_hit", cache_key)
                logger.debug(f"Cache hit for key: {cache_key}")
                return data

            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to deserialize cached data for key {cache_key}: {e}")
                # 删除损坏的缓存
                await self._redis_client.delete(full_key)
                self._stats["misses"] += 1
                return None

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Cache get error for key {cache_key}: {e}")
            raise CacheError(f"Failed to get cached prediction: {str(e)}", cache_key=cache_key)

    async def set_prediction(
        self,
        cache_key: str,
        data: dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        缓存预测结果

        Args:
            cache_key: 缓存键
            data: 要缓存的数据
            ttl: 生存时间（秒），None表示使用默认TTL

        Returns:
            bool: 是否成功缓存

        Raises:
            CacheError: 缓存操作失败
        """
        full_key = self._make_key(cache_key)
        ttl = ttl or self.default_ttl

        try:
            # 序列化数据
            json_data = json.dumps(data, default=str, ensure_ascii=False)

            # 设置缓存
            success = await self._redis_client.setex(
                full_key,
                ttl,
                json_data
            )

            if success:
                self._stats["sets"] += 1
                self._update_last_operation("set", cache_key)
                logger.debug(f"Cached data for key: {cache_key}, TTL: {ttl}s")
            else:
                self._stats["errors"] += 1
                logger.warning(f"Failed to cache data for key: {cache_key}")

            return bool(success)

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Cache set error for key {cache_key}: {e}")
            raise CacheError(f"Failed to cache prediction: {str(e)}", cache_key=cache_key)

    async def delete_prediction(self, cache_key: str) -> bool:
        """
        删除缓存的预测结果

        Args:
            cache_key: 缓存键

        Returns:
            bool: 是否成功删除

        Raises:
            CacheError: 缓存操作失败
        """
        full_key = self._make_key(cache_key)

        try:
            result = await self._redis_client.delete(full_key)

            if result > 0:
                self._stats["deletes"] += 1
                self._update_last_operation("delete", cache_key)
                logger.debug(f"Deleted cached data for key: {cache_key}")
            else:
                logger.debug(f"No cached data found to delete for key: {cache_key}")

            return bool(result)

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Cache delete error for key {cache_key}: {e}")
            raise CacheError(f"Failed to delete cached prediction: {str(e)}", cache_key=cache_key)

    async def exists(self, cache_key: str) -> bool:
        """检查缓存是否存在"""
        full_key = self._make_key(cache_key)

        try:
            return bool(await self._redis_client.exists(full_key))
        except Exception as e:
            logger.error(f"Cache exists check error for key {cache_key}: {e}")
            return False

    async def get_ttl(self, cache_key: str) -> int:
        """获取缓存TTL"""
        full_key = self._make_key(cache_key)

        try:
            ttl = await self._redis_client.ttl(full_key)
            return ttl if ttl >= 0 else -1
        except Exception as e:
            logger.error(f"Cache TTL check error for key {cache_key}: {e}")
            return -1

    async def increment(self, cache_key: str, amount: int = 1) -> int:
        """递增缓存值（用于计数器）"""
        full_key = self._make_key(cache_key)

        try:
            return await self._redis_client.incrby(full_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {cache_key}: {e}")
            raise CacheError(f"Failed to increment cache: {str(e)}", cache_key=cache_key)

    async def get_multiple(self, cache_keys: list[str]) -> dict[str, Optional[dict[str, Any]]]:
        """批量获取缓存"""
        if not cache_keys:
            return {}

        full_keys = [self._make_key(key) for key in cache_keys]

        try:
            # 批量获取
            cached_values = await self._redis_client.mget(full_keys)

            results = {}
            for _i, (key, value) in enumerate(zip(cache_keys, cached_values, strict=False)):
                if value is not None:
                    try:
                        results[key] = json.loads(value.decode('utf-8'))
                        self._stats["hits"] += 1
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # 跳过损坏的数据
                        self._stats["misses"] += 1
                else:
                    results[key] = None
                    self._stats["misses"] += 1

            return results

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Batch cache get error: {e}")
            raise CacheError(f"Failed to get multiple cached predictions: {str(e)}")

    async def set_multiple(
        self,
        cache_data: dict[str, dict[str, Any]],
        ttl: Optional[int] = None
    ) -> dict[str, bool]:
        """批量设置缓存"""
        if not cache_data:
            return {}

        ttl = ttl or self.default_ttl
        results = {}

        try:
            # 使用pipeline提高性能
            pipe = self._redis_client.pipeline()

            for cache_key, data in cache_data.items():
                full_key = self._make_key(cache_key)
                json_data = json.dumps(data, default=str, ensure_ascii=False)
                pipe.setex(full_key, ttl, json_data)

            # 执行pipeline
            pipe_results = await pipe.execute()

            # 检查结果
            for _i, (cache_key, success) in enumerate(zip(cache_data.keys(), pipe_results, strict=False)):
                results[cache_key] = bool(success)
                if success:
                    self._stats["sets"] += 1
                else:
                    self._stats["errors"] += 1

            return results

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Batch cache set error: {e}")
            raise CacheError(f"Failed to set multiple cached predictions: {str(e)}")

    async def clear_pattern(self, pattern: str) -> int:
        """按模式清除缓存"""
        try:
            # 搜索匹配的键
            full_pattern = self._make_key(pattern)
            keys = await self._redis_client.keys(full_pattern)

            if not keys:
                return 0

            # 删除匹配的键
            deleted_count = await self._redis_client.delete(*keys)
            self._stats["deletes"] += deleted_count

            logger.info(f"Cleared {deleted_count} cache entries matching pattern: {pattern}")
            return deleted_count

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Cache clear pattern error for pattern {pattern}: {e}")
            raise CacheError(f"Failed to clear cache pattern: {str(e)}")

    async def health_check(self) -> dict[str, Any]:
        """健康检查"""
        try:
            # 检查Redis连接
            start_time = datetime.now()
            await self._redis_client.ping()
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            # 获取Redis信息
            info = await self._redis_client.info()

            self._last_health_check = datetime.utcnow()
            self._is_healthy = True

            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "redis_info": {
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses")
                },
                "cache_stats": self.get_stats(),
                "last_check": self._last_health_check.isoformat()
            }

        except Exception as e:
            self._is_healthy = False
            logger.error(f"Cache health check failed: {e}")

            return {
                "status": "unhealthy",
                "error": str(e),
                "cache_stats": self.get_stats(),
                "last_check": self._last_health_check.isoformat() if self._last_health_check else None
            }

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        total_operations = (
            self._stats["hits"] + self._stats["misses"] +
            self._stats["sets"] + self._stats["deletes"]
        )

        hit_rate = (
            self._stats["hits"] / (self._stats["hits"] + self._stats["misses"]) * 100
            if (self._stats["hits"] + self._stats["misses"]) > 0 else 0
        )

        uptime = (datetime.utcnow() - self._stats["created_at"]).total_seconds()

        return {
            **self._stats,
            "hit_rate": round(hit_rate, 2),
            "total_operations": total_operations,
            "uptime_seconds": round(uptime, 2),
            "is_healthy": self._is_healthy,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None
        }

    async def cleanup(self):
        """清理资源"""
        try:
            if self._redis_client:
                await self._redis_client.close()
            if self._pool:
                await self._pool.disconnect()

            logger.info("PredictionCache cleanup completed")

        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

    def _make_key(self, cache_key: str) -> str:
        """生成完整的缓存键"""
        return f"{self.key_prefix}{cache_key}"

    def _update_last_operation(self, operation: str, cache_key: str):
        """更新最后操作记录"""
        self._stats["last_operation"] = {
            "operation": operation,
            "cache_key": cache_key,
            "timestamp": datetime.utcnow().isoformat()
        }


# 全局实例
_prediction_cache: Optional[PredictionCache] = None


async def get_prediction_cache() -> PredictionCache:
    """获取全局预测缓存实例"""
    global _prediction_cache

    if _prediction_cache is None:
        # 从环境变量获取Redis配置
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        default_ttl = int(os.getenv("CACHE_DEFAULT_TTL", "300"))

        _prediction_cache = PredictionCache(
            redis_url=redis_url,
            default_ttl=default_ttl
        )
        await _prediction_cache.initialize()

    return _prediction_cache


def get_prediction_cache_sync() -> PredictionCache:
    """同步获取预测缓存实例（用于非异步上下文）"""
    global _prediction_cache

    if _prediction_cache is None:
        raise RuntimeError("PredictionCache not initialized. Call get_prediction_cache() first.")

    return _prediction_cache
