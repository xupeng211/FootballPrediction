from typing import Optional

"""缓存模块 - 提供统一的缓存管理功能.

提供Redis缓存功能,支持:
- Redis连接池管理
- 同步和异步操作
- 缓存Key命名规范
- TTL过期策略
- 缓存装饰器
- 内存缓存（TTL Cache）
- 缓存一致性管理

统一接口:
- redis_manager: Redis缓存管理
- ttl_cache: 高性能内存缓存
- decorators: 缓存装饰器
- consistency_manager: 缓存一致性
"""

# 缓存一致性管理
from .consistency_manager import (
    CacheConsistencyManager,
    invalidate_entity_cache,
    sync_entity_cache,
)

# 缓存装饰器
from .decorators import (
    CacheDecorator,
    InvalidateCacheDecorator,
    UserCacheDecorator,
    cache_by_user,
    cache_invalidate,
    cache_match_data,
    cache_result,
    cache_team_stats,
    cache_user_predictions,
    cache_with_ttl,
)

# Redis缓存管理
from .redis_manager import (
    CacheKeyManager,  # 便捷函数 - 异步; 便捷函数 - 同步; 其他功能,
    RedisManager,
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
    get_redis_manager,
    mget_cache,
    mset_cache,
    set_cache,
    startup_warmup,
    ttl_cache,
)

# TTL缓存（内存缓存）
from .ttl_cache import (
    CACHES,
    AsyncTTLCache,
    CacheEntry,
    CacheFactory,
    TTLCache,
    cleanup_all_expired,
    clear_all_caches,
    config_cache,
    feature_cache,
    get_all_stats,
    odds_cache,
    prediction_cache,
    session_cache,
    start_auto_cleanup,
    stop_auto_cleanup,
    temp_cache,
)
from .ttl_cache import get_cache as get_ttl_cache

# 向后兼容别名
# 为了保持向后兼容,提供一些常用别名
TTLCacheEntry = CacheEntry


def get_prediction_cache():
    """函数文档字符串."""
    pass  # 添加pass语句
    return prediction_cache


def get_feature_cache():
    """函数文档字符串."""
    pass  # 添加pass语句
    return feature_cache


def get_odds_cache():
    """函数文档字符串."""
    pass  # 添加pass语句
    return odds_cache


__all__ = [
    # Redis管理器
    "RedisManager",
    "CacheKeyManager",
    "get_redis_manager",
    # Redis便捷函数 - 异步
    "adelete_cache",
    "aexists_cache",
    "aget_cache",
    "amget_cache",
    "amset_cache",
    "aset_cache",
    "attl_cache",
    # Redis便捷函数 - 同步
    "delete_cache",
    "exists_cache",
    "get_cache",
    "mget_cache",
    "mset_cache",
    "set_cache",
    "ttl_cache",
    # Redis其他功能
    "startup_warmup",
    # TTL缓存核心类
    "TTLCache",
    "AsyncTTLCache",
    "CacheEntry",
    "CacheFactory",
    # TTL缓存预定义实例
    "prediction_cache",
    "feature_cache",
    "odds_cache",
    "session_cache",
    "config_cache",
    "temp_cache",
    # TTL缓存工具函数
    "get_ttl_cache",
    "get_all_stats",
    "clear_all_caches",
    "cleanup_all_expired",
    "start_auto_cleanup",
    "stop_auto_cleanup",
    "CACHES",
    # 缓存装饰器
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
    # 缓存一致性管理
    "CacheConsistencyManager",
    "invalidate_entity_cache",
    "sync_entity_cache",
    # 向后兼容别名
    "TTLCacheEntry",
    "get_prediction_cache",
    "get_feature_cache",
    "get_odds_cache",
]
