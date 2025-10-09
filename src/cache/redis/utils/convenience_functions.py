"""

"""






    """

    """


    """

    """


    """

    """


    """便捷函数：获取缓存"""


    """便捷函数：设置缓存"""


    """便捷函数：删除缓存"""


    """便捷函数：检查缓存是否存在"""


    """便捷函数：获取缓存剩余TTL"""


    """便捷函数：批量获取缓存"""


    """便捷函数：批量设置缓存"""


    """便捷函数：异步获取缓存"""


    """便捷函数：异步设置缓存"""


    """便捷函数：异步删除缓存"""


    """便捷函数：异步检查缓存是否存在"""


    """便捷函数：异步获取缓存剩余TTL"""


    """便捷函数：异步批量获取缓存"""


    """便捷函数：异步批量设置缓存"""


    """

    """



from ..core.connection_manager import RedisConnectionManager
from ..operations.async_operations import RedisAsyncOperations
from ..operations.sync_operations import RedisSyncOperations
from ..warmup.warmup_manager import warmup_cache_on_startup

Redis便捷函数
提供全局单例和便捷的缓存操作函数
logger = logging.getLogger(__name__)
# 全局Redis管理器实例（单例模式）
_redis_connection_manager: Optional[RedisConnectionManager] = None
_redis_sync_ops: Optional[RedisSyncOperations] = None
_redis_async_ops: Optional[RedisAsyncOperations] = None
def get_redis_manager() -> RedisConnectionManager:
    获取全局Redis连接管理器实例（单例模式）
    Returns:
        RedisConnectionManager: Redis连接管理器实例
    global _redis_connection_manager
    if _redis_connection_manager is None:
        _redis_connection_manager = RedisConnectionManager()
        # 初始化操作类
        global _redis_sync_ops, _redis_async_ops
        _redis_sync_ops = RedisSyncOperations(_redis_connection_manager)
        _redis_async_ops = RedisAsyncOperations(_redis_connection_manager)
    return _redis_connection_manager
def get_sync_operations() -> RedisSyncOperations:
    获取同步操作实例
    Returns:
        RedisSyncOperations: 同步操作实例
    global _redis_sync_ops
    if _redis_sync_ops is None:
        manager = get_redis_manager()
        _redis_sync_ops = RedisSyncOperations(manager)
    return _redis_sync_ops
def get_async_operations() -> RedisAsyncOperations:
    获取异步操作实例
    Returns:
        RedisAsyncOperations: 异步操作实例
    global _redis_async_ops
    if _redis_async_ops is None:
        manager = get_redis_manager()
        _redis_async_ops = RedisAsyncOperations(manager)
    return _redis_async_ops
# 便捷函数，直接使用全局实例
def get_cache(key: str, default: Any = None) -> Any:
    ops = get_sync_operations()
    return ops.get(str(key), default)
def set_cache(
    key: str, value: Any, ttl: Optional[int] = None, cache_type: Optional[str] = None
) -> bool:
    ops = get_sync_operations()
    return ops.set(key, value, ttl, cache_type)
def delete_cache(*keys: str) -> int:
    ops = get_sync_operations()
    return ops.delete(*keys)
def exists_cache(*keys: str) -> int:
    ops = get_sync_operations()
    return ops.exists(*keys)
def ttl_cache(key: str) -> int:
    ops = get_sync_operations()
    return ops.ttl(key)
def mget_cache(keys: list, default: Any = None) -> list:
    ops = get_sync_operations()
    return ops.mget(keys, default)
def mset_cache(mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
    ops = get_sync_operations()
    return ops.mset(mapping, ttl)
async def aget_cache(key: str, default: Any = None) -> Any:
    ops = get_async_operations()
    return await ops.aget(key, default)
async def aset_cache(
    key: str, value: Any, ttl: Optional[int] = None, cache_type: Optional[str] = None
) -> bool:
    ops = get_async_operations()
    return await ops.aset(key, value, ttl, cache_type)
async def adelete_cache(*keys: str) -> int:
    ops = get_async_operations()
    return await ops.adelete(*keys)
async def aexists_cache(*keys: str) -> int:
    ops = get_async_operations()
    return await ops.aexists(*keys)
async def attl_cache(key: str) -> int:
    ops = get_async_operations()
    return await ops.attl(key)
async def amget_cache(keys: list, default: Any = None) -> list:
    ops = get_async_operations()
    return await ops.amget(keys, default)
async def amset_cache(mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
    ops = get_async_operations()
    return await ops.amset(mapping, ttl)
async def startup_warmup() -> Dict[str, int]:
    系统启动时的缓存预热便捷函数
    Returns:
        Dict[str, int]: 预热结果统计
    manager = get_redis_manager()
    return await warmup_cache_on_startup(manager)