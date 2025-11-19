from typing import Optional

"""Redis缓存管理器
Redis Cache Manager.

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
    "CacheKeyManager",
    "get_redis_manager",
    # 便捷函数
    "get_cache",
    "set_cache",
    "delete_cache",
    "exists_cache",
    "ttl_cache",
    "mget_cache",
    "mset_cache",
    "aget_cache",
    "aset_cache",
    "adelete_cache",
    "aexists_cache",
    "attl_cache",
    "amget_cache",
    "amset_cache",
    "startup_warmup",
]

# 版本信息
__version__ = "2.0.0"
__description__ = "重构后的Redis缓存管理器 - 提供模块化,可扩展的缓存管理功能"
