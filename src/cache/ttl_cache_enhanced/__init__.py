"""
改进的TTL缓存模块
Improved TTL Cache Module

提供高性能的内存缓存功能，支持：
- 自动过期
- LRU淘汰策略
- 批量操作
- 异步支持
- 统计监控

Provides high-performance in-memory cache with:
- Auto expiration
- LRU eviction
- Batch operations
- Async support
- Statistics monitoring
"""

from .async_cache import AsyncTTLCache
from .cache_entry import CacheEntry
from .cache_factory import CacheFactory
from .cache_instances import (
    CACHES,
    cleanup_all_expired,
    clear_all_caches,
    config_cache,
    feature_cache,
    get_all_stats,
    get_cache,
    odds_cache,
    prediction_cache,
    session_cache,
    start_auto_cleanup,
    stop_auto_cleanup,
    temp_cache,
)
from .ttl_cache import TTLCache

__all__ = [
    # Core classes
    "TTLCache",
    "AsyncTTLCache",
    "CacheEntry",
    "CacheFactory",
    # Predefined instances
    "prediction_cache",
    "feature_cache",
    "odds_cache",
    "session_cache",
    "config_cache",
    "temp_cache",
    # Utility functions
    "get_cache",
    "get_all_stats",
    "clear_all_caches",
    "cleanup_all_expired",
    "start_auto_cleanup",
    "stop_auto_cleanup",
    # Cache registry
    "CACHES",
]

# 版本信息
__version__ = "1.0.0"
__author__ = "Football Prediction Team"
