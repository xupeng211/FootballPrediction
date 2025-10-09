"""
改进的TTL缓存实现
Improved TTL Cache Implementation

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

# 向后兼容性导入
# Backward compatibility import
try:
    # 导入模块化的实现
    from .ttl_cache_improved_mod import (
        TTLCache,
        AsyncTTLCache,
        CacheEntry,
        CacheFactory,
        prediction_cache,
        feature_cache,
        odds_cache,
    )
except ImportError:
    # 如果导入失败，提供错误信息
    import logging

    logger = logging.getLogger(__name__)
    logger.error(
        "无法导入TTL缓存模块。请确保所有子模块都已正确安装。",
        "Failed to import TTL cache module. Please ensure all submodules are properly installed.",
    )
    raise

# 为了保持向后兼容，重新导出所有内容
# Re-export everything for backward compatibility
__all__ = [
    "TTLCache",
    "AsyncTTLCache",
    "CacheEntry",
    "CacheFactory",
    "prediction_cache",
    "feature_cache",
    "odds_cache",
]
