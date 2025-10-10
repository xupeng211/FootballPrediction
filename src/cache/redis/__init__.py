"""
Redis cache module - 提供完整的Redis缓存管理功能
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

import redis
import redis.asyncio as aioredis

from .core.connection_manager import RedisConnectionManager
from .core.key_manager import RedisKeyManager, CacheKeyManager
from .operations.async_operations import RedisAsyncOperations
from .operations.sync_operations import RedisSyncOperations
from .warmup.warmup_manager import startup_warmup

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis管理器主类，整合同步和异步操作"""

    def __init__(self, redis_url: Optional[str] = None):
        """初始化Redis管理器"""
        self.redis_url = redis_url or "redis://localhost:6379"
        self.connection_manager = RedisConnectionManager()
        self.key_manager = RedisKeyManager()
        self.async_ops = RedisAsyncOperations(self.redis_url)
        self.sync_ops = None
        self._sync_client = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def get_async_client(self) -> aioredis.Redis:
        """获取异步Redis客户端"""
        return await self.connection_manager.connect()

    def get_sync_client(self) -> redis.Redis:
        """获取同步Redis客户端"""
        if not self._sync_client:
            self._sync_client = redis.from_url(self.redis_url, decode_responses=True)  # type: ignore
            self.sync_ops = RedisSyncOperations(self._sync_client)  # type: ignore
        return self._sync_client  # type: ignore

    async def health_check(self) -> bool:
        """健康检查"""
        return await self.connection_manager.health_check()

    def get_key_manager(self) -> RedisKeyManager:
        """获取键管理器"""
        return self.key_manager


# 全局实例
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """获取全局Redis管理器实例"""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


# 便捷函数 - 异步版本
async def aget_cache(key: str) -> Optional[Any]:
    """异步获取缓存"""
    manager = get_redis_manager()
    return await manager.async_ops.get(key)


async def aset_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """异步设置缓存"""
    manager = get_redis_manager()
    return await manager.async_ops.set(key, value, ttl)


async def adelete_cache(key: str) -> bool:
    """异步删除缓存"""
    manager = get_redis_manager()
    return await manager.async_ops.delete(key)


async def aexists_cache(key: str) -> bool:
    """异步检查缓存是否存在"""
    manager = get_redis_manager()
    return await manager.async_ops.exists(key)


async def attl_cache(key: str) -> Optional[int]:
    """异步获取TTL"""
    try:
        client = await get_redis_manager().get_async_client()
        return await client.ttl(key)
    except Exception as e:
        logger.error(f"Error getting TTL for key {key}: {str(e)}")
        return None


async def amget_cache(keys: List[str]) -> List[Optional[Any]]:
    """异步批量获取缓存"""
    try:
        client = await get_redis_manager().get_async_client()
        values = await client.mget(keys)
        return [json.loads(v) if v else None for v in values]
    except Exception as e:
        logger.error(f"Error in mget: {str(e)}")
        return [None] * len(keys)


async def amset_cache(mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
    """异步批量设置缓存"""
    try:
        client = await get_redis_manager().get_async_client()
        pipe = client.pipeline()
        for key, value in mapping.items():
            serialized = json.dumps(value, default=str)
            if ttl:
                pipe.setex(key, ttl, serialized)
            else:
                pipe.set(key, serialized)
        await pipe.execute()
        return True
    except Exception as e:
        logger.error(f"Error in mset: {str(e)}")
        return False


# 便捷函数 - 同步版本
def get_cache(key: str) -> Optional[Any]:
    """同步获取缓存"""
    manager = get_redis_manager()
    manager.get_sync_client()
    return manager.sync_ops.get(key)  # type: ignore


def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """同步设置缓存"""
    manager = get_redis_manager()
    manager.get_sync_client()
    return manager.sync_ops.set(key, value, ttl)  # type: ignore


def delete_cache(key: str) -> bool:
    """同步删除缓存"""
    manager = get_redis_manager()
    manager.get_sync_client()
    return manager.sync_ops.delete(key)  # type: ignore


def exists_cache(key: str) -> bool:
    """同步检查缓存是否存在"""
    manager = get_redis_manager()
    manager.get_sync_client()
    return manager.sync_ops.exists(key)  # type: ignore


def ttl_cache(key: str) -> Optional[int]:
    """同步获取TTL"""
    try:
        client = get_redis_manager().get_sync_client()
        return client.ttl(key)
    except Exception as e:
        logger.error(f"Error getting TTL for key {key}: {str(e)}")
        return None


def mget_cache(keys: List[str]) -> List[Optional[Any]]:
    """同步批量获取缓存"""
    try:
        client = get_redis_manager().get_sync_client()
        values = client.mget(keys)
        return [json.loads(v) if v else None for v in values]
    except Exception as e:
        logger.error(f"Error in mget: {str(e)}")
        return [None] * len(keys)


def mset_cache(mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
    """同步批量设置缓存"""
    try:
        client = get_redis_manager().get_sync_client()
        pipe = client.pipeline()
        for key, value in mapping.items():
            serialized = json.dumps(value, default=str)
            if ttl:
                pipe.setex(key, ttl, serialized)
            else:
                pipe.set(key, serialized)
        pipe.execute()
        return True
    except Exception as e:
        logger.error(f"Error in mset: {str(e)}")
        return False


# 导出所有公共接口
__all__ = [
    # 主类
    "RedisManager",
    "CacheKeyManager",
    "RedisKeyManager",
    "get_redis_manager",
    # 便捷函数 - 异步
    "aget_cache",
    "aset_cache",
    "adelete_cache",
    "aexists_cache",
    "attl_cache",
    "amget_cache",
    "amset_cache",
    # 便捷函数 - 同步
    "get_cache",
    "set_cache",
    "delete_cache",
    "exists_cache",
    "ttl_cache",
    "mget_cache",
    "mset_cache",
    # 其他功能
    "startup_warmup",
    "RedisConnectionManager",
    "RedisAsyncOperations",
    "RedisSyncOperations",
]
