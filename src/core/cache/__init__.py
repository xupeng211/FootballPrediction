"""高性能异步缓存模块
High-Performance Async Cache Module.

提供基于Redis的异步缓存基础设施，包括连接池管理、
序列化处理、缓存装饰器和优雅降级机制。
Provides Redis-based async cache infrastructure with connection pooling,
serialization handling, cache decorators, and graceful degradation.
"""

# 导入核心缓存模块
from src.core.cache_main import (
    RedisCache,
    get_cache,
    cache_get,
    cache_set,
    cache_delete,
    cache_key_builder,
    CacheSerializationError,
    CacheConnectionError,
)

# 导入装饰器模块
from src.core.cache_decorators import (
    cached,
    cached_long,
    cached_short,
    cached_medium,
    cached_method,
    BatchCache,
    invalidate_pattern,
    async_cache,
    cache,
)

__all__ = [
    # 核心缓存类
    'RedisCache',
    'get_cache',

    # 便捷函数
    'cache_get',
    'cache_set',
    'cache_delete',
    'cache_key_builder',

    # 异常类
    'CacheSerializationError',
    'CacheConnectionError',

    # 装饰器
    'cached',
    'cached_long',
    'cached_short',
    'cached_medium',
    'cached_method',

    # 批量操作
    'BatchCache',
    'invalidate_pattern',

    # 别名
    'async_cache',
    'cache',
]
