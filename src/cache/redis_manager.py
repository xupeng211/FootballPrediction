"""
Redis缓存管理器
Redis Cache Manager

实现Redis连接池、基础操作方法，支持异步和同步两种模式，以及集群、哨兵等高级特性。
"""

from typing import Optional, Dict, List, Any, Union
import logging

from .redis_enhanced import EnhancedRedisManager, RedisConfig, get_redis_manager
from .mock_redis import MockRedisManager, CacheKeyManager

logger = logging.getLogger(__name__)

# 向后兼容别名
RedisManager = EnhancedRedisManager

# 从mock_redis导入便捷函数以确保向后兼容
from .mock_redis import (
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
    ttl_cache,
    startup_warmup,
)

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
