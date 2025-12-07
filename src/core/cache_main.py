"""高性能异步缓存模块
High-Performance Async Cache Module.

提供基于Redis的异步缓存基础设施，包括连接池管理、
序列化处理和优雅降级机制。
Provides Redis-based async cache infrastructure with connection pooling,
serialization handling, and graceful degradation.

Author: Claude Code
Version: 1.0.0
"""

import asyncio
import json
import logging
import pickle
from functools import wraps
from typing import Any, Callable, Optional, Union
import hashlib

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, RedisError

from .config import get_settings

logger = logging.getLogger(__name__)


class CacheSerializationError(Exception):
    """缓存序列化错误"""
    pass


class CacheConnectionError(Exception):
    """缓存连接错误"""
    pass


class RedisCache:
    """高性能异步Redis缓存客户端.

    特性:
    - 连接池管理
    - 自动序列化/反序列化 (JSON/Pickle)
    - 优雅降级
    - 性能监控
    - 并发保护

    Features:
    - Connection pool management
    - Automatic serialization/deserialization (JSON/Pickle)
    - Graceful degradation
    - Performance monitoring
    - Concurrency protection
    """

    def __init__(self, redis_url: Optional[str] = None, **kwargs):
        """初始化Redis缓存客户端.

        Args:
            redis_url: Redis连接URL
            **kwargs: 额外的连接参数
        """
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.redis_url

        # 连接池配置
        self.pool_config = {
            'max_connections': kwargs.get('max_connections', 50),
            'retry_on_timeout': kwargs.get('retry_on_timeout', True),
            'socket_keepalive': kwargs.get('socket_keepalive', True),
            'socket_keepalive_options': kwargs.get('socket_keepalive_options', {}),
            'health_check_interval': kwargs.get('health_check_interval', 30),
        }

        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._lock = asyncio.Lock()

        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0,
            'connections': 0,
        }

        # 并发保护锁字典
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    async def _get_connection(self) -> Redis:
        """获取Redis连接.

        Returns:
            Redis: Redis客户端实例

        Raises:
            CacheConnectionError: 连接失败时抛出
        """
        if self._redis is None:
            async with self._lock:
                if self._redis is None:
                    try:
                        self._pool = ConnectionPool.from_url(
                            self.redis_url,
                            **self.pool_config
                        )
                        self._redis = Redis(connection_pool=self._pool)
                        # 测试连接
                        await self._redis.ping()
                        self.stats['connections'] += 1
                        logger.info(f"Redis连接建立成功: {self.redis_url}")
                    except (ConnectionError, RedisError) as e:
                        logger.error(f"Redis连接失败: {e}")
                        raise CacheConnectionError(f"无法连接到Redis: {e}")

        return self._redis

    def _serialize(self, value: Any) -> str:
        """序列化值.

        Args:
            value: 要序列化的值

        Returns:
            str: 序列化后的字符串

        Raises:
            CacheSerializationError: 序列化失败时抛出
        """
        try:
            # 对于简单类型，直接JSON序列化
            if isinstance(value, (str, int, float, bool)) or value is None:
                return json.dumps({'_type': 'simple', 'value': value})

            # 对于复杂类型，尝试JSON序列化
            if isinstance(value, (dict, list, tuple)):
                try:
                    return json.dumps({'_type': 'json', 'value': value})
                except (TypeError, ValueError):
                    pass

            # 对于其他复杂对象，使用pickle
            try:
                serialized = pickle.dumps(value)
                return json.dumps({'_type': 'pickle', 'value': serialized.hex()})
            except (pickle.PickleError, ValueError) as e:
                raise CacheSerializationError(f"无法序列化对象: {e}")

        except Exception as e:
            raise CacheSerializationError(f"序列化失败: {e}")

    def _deserialize(self, value: str) -> Any:
        """反序列化值.

        Args:
            value: 要反序列化的字符串

        Returns:
            Any: 反序列化后的值

        Raises:
            CacheSerializationError: 反序列化失败时抛出
        """
        try:
            data = json.loads(value)

            if data.get('_type') == 'simple':
                return data['value']
            elif data.get('_type') == 'json':
                return data['value']
            elif data.get('_type') == 'pickle':
                serialized_bytes = bytes.fromhex(data['value'])
                return pickle.loads(serialized_bytes)
            else:
                # 兼容旧格式
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

        except Exception as e:
            raise CacheSerializationError(f"反序列化失败: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值.

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存值，如果不存在则返回None
        """
        try:
            redis_client = await self._get_connection()
            value = await redis_client.get(key)

            if value is None:
                self.stats['misses'] += 1
                return None

            self.stats['hits'] += 1
            return self._deserialize(value.decode('utf-8'))

        except (CacheConnectionError, CacheSerializationError):
            raise
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"缓存获取失败 {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """设置缓存值.

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认300秒
            nx: 仅当键不存在时设置
            xx: 仅当键存在时设置

        Returns:
            bool: 设置成功返回True，失败返回False
        """
        try:
            redis_client = await self._get_connection()
            serialized_value = self._serialize(value)

            result = await redis_client.set(
                key,
                serialized_value,
                ex=ttl,
                nx=nx,
                xx=xx
            )

            if result:
                self.stats['sets'] += 1
            return result

        except (CacheConnectionError, CacheSerializationError):
            raise
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"缓存设置失败 {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存值.

        Args:
            key: 缓存键

        Returns:
            bool: 删除成功返回True，键不存在返回False
        """
        try:
            redis_client = await self._get_connection()
            result = await redis_client.delete(key)

            if result > 0:
                self.stats['deletes'] += 1
                return True
            return False

        except CacheConnectionError:
            raise
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"缓存删除失败 {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查键是否存在.

        Args:
            key: 缓存键

        Returns:
            bool: 键存在返回True，否则返回False
        """
        try:
            redis_client = await self._get_connection()
            return bool(await redis_client.exists(key))

        except CacheConnectionError:
            raise
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"缓存检查失败 {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间.

        Args:
            key: 缓存键
            ttl: 过期时间（秒）

        Returns:
            bool: 设置成功返回True，键不存在返回False
        """
        try:
            redis_client = await self._get_connection()
            return bool(await redis_client.expire(key, ttl))

        except CacheConnectionError:
            raise
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"缓存过期设置失败 {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """获取键的剩余过期时间.

        Args:
            key: 缓存键

        Returns:
            int: 剩余时间（秒），键不存在返回-2，永不过期返回-1
        """
        try:
            redis_client = await self._get_connection()
            return await redis_client.ttl(key)

        except CacheConnectionError:
            raise
        except Exception as e:
            self.stats['errors'] += 1
            logger.warning(f"获取TTL失败 {key}: {e}")
            return -2

    async def clear(self) -> bool:
        """清空所有缓存.

        Returns:
            bool: 清空成功返回True
        """
        try:
            redis_client = await self._get_connection()
            await redis_client.flushdb()
            logger.info("缓存已清空")
            return True

        except CacheConnectionError:
            raise
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"清空缓存失败: {e}")
            return False

    async def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息.

        Returns:
            dict: 统计信息字典
        """
        stats = self.stats.copy()

        # 计算命中率
        total_requests = stats['hits'] + stats['misses']
        stats['hit_rate'] = stats['hits'] / total_requests if total_requests > 0 else 0

        # 获取Redis信息
        try:
            redis_client = await self._get_connection()
            info = await redis_client.info()
            stats['redis_info'] = {
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 'N/A'),
                'total_commands_processed': info.get('total_commands_processed', 'N/A'),
            }
        except Exception:
            stats['redis_info'] = 'N/A'

        return stats

    async def health_check(self) -> dict[str, Any]:
        """健康检查.

        Returns:
            dict: 健康检查结果
        """
        try:
            redis_client = await self._get_connection()
            start_time = asyncio.get_event_loop().time()
            await redis_client.ping()
            response_time = asyncio.get_event_loop().time() - start_time

            return {
                'status': 'healthy',
                'response_time': f"{response_time:.3f}s",
                'connection_pool_size': self._pool.max_connections if self._pool else 'N/A',
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'response_time': 'N/A',
            }

    async def close(self):
        """关闭Redis连接."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis连接已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口."""
        await self.close()


# 全局缓存实例
_global_cache: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """获取全局缓存实例.

    Returns:
        RedisCache: 全局缓存实例
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = RedisCache()
    return _global_cache


def cache_key_builder(
    namespace: str = "",
    *args,
    **kwargs
) -> str:
    """构建缓存键.

    Args:
        namespace: 键命名空间
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        str: 缓存键
    """
    # 构建键的组成部分
    parts = [namespace] if namespace else []

    # 添加位置参数
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            parts.append(str(arg))
        else:
            # 对于复杂对象，使用安全哈希
            parts.append(hashlib.sha256(str(arg).encode()).hexdigest()[:8])

    # 添加关键字参数
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (str, int, float, bool)):
            parts.append(f"{key}:{value}")
        else:
            parts.append(f"{key}:{hashlib.sha256(str(value).encode()).hexdigest()[:8]}")

    return ":".join(parts)


# 便捷函数
async def cache_get(key: str) -> Optional[Any]:
    """便捷的缓存获取函数."""
    cache = await get_cache()
    return await cache.get(key)


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """便捷的缓存设置函数."""
    cache = await get_cache()
    return await cache.set(key, value, ttl)


async def cache_delete(key: str) -> bool:
    """便捷的缓存删除函数."""
    cache = await get_cache()
    return await cache.delete(key)