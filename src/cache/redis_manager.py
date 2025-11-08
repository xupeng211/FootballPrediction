"""
Redis缓存管理器
Redis Cache Manager

实现Redis连接池、基础操作方法，支持异步和同步两种模式，以及集群、哨兵等高级特性。
"""

import logging

from .mock_redis import (
    CacheKeyManager,
    adelete_cache,
    aexists_cache,
    aget_cache,
    amget_cache,
    amset_cache,
    aset_cache,
    attl_cache,
    delete_cache,
    exists_cache,
    get_cache,
    mget_cache,
    mset_cache,
    set_cache,
    startup_warmup,
    ttl_cache,
)
from .redis_enhanced import EnhancedRedisManager, get_redis_manager

logger = logging.getLogger(__name__)

# 向后兼容别名
RedisManager = EnhancedRedisManager

# 导出所有公共接口
__all__ = [
    # 主类
    "RedisManager",
    "EnhancedRedisManager",
    "CacheKeyManager",
    # 获取函数
    "get_redis_manager",
    # 异步操作函数
    "adelete_cache",
    "aexists_cache",
    "aget_cache",
    "amget_cache",
    "amset_cache",
    "aset_cache",
    "attl_cache",
    # 同步操作函数
    "delete_cache",
    "exists_cache",
    "get_cache",
    "mget_cache",
    "mset_cache",
    "set_cache",
    "ttl_cache",
    # 工具函数
    "startup_warmup",
]
