"""
缓存模块

提供Redis缓存功能，支持：
- Redis连接池管理
- 同步和异步操作
- 缓存Key命名规范
- TTL过期策略
- 缓存装饰器
"""

from typing import cast, Any, Optional, Union

from .redis_manager import CacheKeyManager, RedisManager
from .decorators import (
    cache_result,
    cache_with_ttl,
    cache_by_user,
    cache_invalidate,
    cache_user_predictions,
    cache_match_data,
    cache_team_stats,
    CacheDecorator,
    UserCacheDecorator,
    InvalidateCacheDecorator,
)

__all__ = [
    "RedisManager",
    "CacheKeyManager",
    "cache_result",
    "cache_with_ttl",
    "cache_by_user",
    "cache_invalidate",
    "cache_user_predictions",
    "cache_match_data",
    "cache_team_stats",
    "CacheDecorator",
    "UserCacheDecorator",
    "InvalidateCacheDecorator",
]
