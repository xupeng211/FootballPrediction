"""
TTL cache module - 使用增强版TTL缓存实现

提供高性能的内存缓存功能,支持:
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

try:
    # 导入增强版的TTL缓存实现
    from .ttl_cache_enhanced import (
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
        get_cache,
        odds_cache,
        prediction_cache,
        session_cache,
        start_auto_cleanup,
        stop_auto_cleanup,
        temp_cache,
    )
except ImportError:
    # 如果导入失败,提供错误信息
    import logging

    logger = logging.getLogger(__name__)
    logger.error(
        "无法导入TTL缓存增强模块。请确保所有子模块都已正确安装.",
    "Failed to import enhanced TTL cache module. Please ensure all submodules are properly installed.",
    )
    raise

# 导出所有公共接口
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
