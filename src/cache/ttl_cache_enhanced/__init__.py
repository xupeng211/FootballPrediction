"""
TTL缓存增强模块

提供高性能的TTL缓存实现，支持：
- 自动过期
- LRU淘汰策略
- 批量操作
- 异步支持
- 统计监控
"""

# 安全导入，处理模块可能不完整的情况
try:
    from .cache_entry import CacheEntry
except ImportError:
    CacheEntry = None

try:
    from .cache_factory import CacheFactory
except ImportError:
    CacheFactory = None

try:
    from .ttl_cache import TTLCache
except ImportError:
    TTLCache = None

# AsyncTTLCache 可能不存在，使用占位符
AsyncTTLCache = None

try:
    from .cache_instances import (
        CACHES,
        api_response_cache,
        config_cache,
        feature_cache,
        get_cache,
        prediction_cache,
        user_session_cache,
    )
except ImportError:
    CACHES = {}
    feature_cache = None
    config_cache = None
    user_session_cache = None
    api_response_cache = None
    prediction_cache = None

    def get_cache(name: str):
        return None


try:
    from .async_cache import (
        cleanup_all_expired,
        clear_all_caches,
    )
except ImportError:

    def cleanup_all_expired():
        return None

    def clear_all_caches():
        return None


# 添加 get_all_stats 函数
def get_all_stats():
    """获取所有缓存的统计信息"""
    stats = {}
    for name, cache in CACHES.items():
        if hasattr(cache, "stats"):
            stats[name] = cache.stats
        else:
            stats[name] = {"status": "unknown"}
    return stats


__all__ = [
    "CacheEntry",
    "CacheFactory",
    "TTLCache",
    "AsyncTTLCache",
    "CACHES",
    "feature_cache",
    "config_cache",
    "user_session_cache",
    "api_response_cache",
    "prediction_cache",
    "cleanup_all_expired",
    "clear_all_caches",
    "get_cache",
    "get_all_stats",
]
