"""
Redis工具模块

包含便捷函数和全局单例管理
"""

from .convenience_functions import (
    adelete_cache,
    aexists_cache,
    aget_cache,
    amget_cache,
    amset_cache,
    aset_cache,
    attl_cache,
    delete_cache,
    exists_cache,
    get_async_operations,
    get_cache,
    get_redis_manager,
    get_sync_operations,
    mget_cache,
    mset_cache,
    set_cache,
    startup_warmup,
    ttl_cache,
)

__all__ = [
    "get_redis_manager",
    "get_sync_operations",
    "get_async_operations",
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