"""

"""






    """

    """

        """

        """





        """同步获取缓存数据"""

        """同步设置缓存数据"""

        """同步删除缓存数据"""

        """获取匹配的键列表"""

        """同步检查Key是否存在"""

        """同步获取Key的剩余TTL"""

        """同步设置Key的过期时间"""

        """清空当前数据库"""

        """同步批量获取缓存数据"""

        """同步批量设置缓存数据"""


        """异步获取缓存数据"""

        """异步设置缓存数据"""

        """异步删除缓存数据"""

        """异步检查Key是否存在"""

        """异步获取Key的剩余TTL"""

        """异步设置Key的过期时间"""

        """异步批量获取缓存数据"""

        """异步批量设置缓存数据"""


        """同步Redis连接健康检查"""

        """异步Redis连接健康检查"""

        """对外的健康检查接口"""

        """获取Redis服务器信息"""

        """获取同步Redis客户端"""

        """获取异步Redis客户端"""

        """暴露底层同步客户端"""

        """关闭同步连接池"""

        """关闭异步连接池"""


        """同步Redis上下文管理器"""

        """异步Redis上下文管理器"""


        """预热比赛相关缓存"""

        """预热球队相关缓存"""

        """预热即将开始比赛的缓存"""

        """预热历史统计数据缓存"""

        """执行完整的缓存预热"""



from .core import CacheKeyManager, RedisConnectionManager
from .operations import RedisAsyncOperations, RedisSyncOperations
from .warmup import CacheWarmupManager

Redis缓存管理器主类
整合所有Redis功能模块，提供统一的接口
logger = logging.getLogger(__name__)
class RedisManager:
    Redis缓存管理器
    提供同步和异步的Redis操作，支持：
    - 连接池管理
    - 基础CRUD操作 (get/set/delete)
    - JSON数据序列化
    - TTL管理
    - 批量操作
    - 错误处理和重试
    - 缓存预热
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: float = 3.0,
        socket_connect_timeout: float = 3.0,
        retry_on_timeout: bool = True,
        health_check_interval: int = 60,
    ):
        初始化Redis管理器
        Args:
            redis_url: Redis连接URL
            max_connections: 最大连接数
            socket_timeout: Socket超时时间
            socket_connect_timeout: Socket连接超时时间
            retry_on_timeout: 超时时是否重试
            health_check_interval: 健康检查间隔(秒)
        # 初始化连接管理器
        self.connection_manager = RedisConnectionManager(
            redis_url=redis_url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            health_check_interval=health_check_interval,
        )
        # 初始化操作类
        self.sync_ops = RedisSyncOperations(self.connection_manager)
        self.async_ops = RedisAsyncOperations(self.connection_manager)
        # 初始化键管理器
        self.key_manager = CacheKeyManager()
        # 初始化预热管理器
        self.warmup_manager = CacheWarmupManager(self)
    # ================== 同步操作方法 ==================
    def get(self, key: str, default: Any = None) -> Any:
        return self.sync_ops.get(key, default)
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_type: Optional[str] = None,
    ) -> bool:
        return self.sync_ops.set(key, value, ttl, cache_type)
    def delete(self, *keys: str) -> int:
        return self.sync_ops.delete(*keys)
    def keys(self, pattern: str = "*") -> List[Any]:
        return self.sync_ops.keys(pattern)
    def exists(self, *keys: str) -> int:
        return self.sync_ops.exists(*keys)
    def ttl(self, key: str) -> int:
        return self.sync_ops.ttl(key)
    def expire(self, key: str, ttl: int) -> bool:
        return self.sync_ops.expire(key, ttl)
    def clear_all(self) -> Any:
        return self.sync_ops.clear_all()
    def mget(self, keys: List[str], default: Any = None) -> List[Any]:
        return self.sync_ops.mget(keys, default)
    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        return self.sync_ops.mset(mapping, ttl)
    # ================== 异步操作方法 ==================
    async def aget(self, key: str, default: Any = None) -> Any:
        return await self.async_ops.aget(key, default)
    async def aset(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_type: Optional[str] = None,
    ) -> bool:
        return await self.async_ops.aset(key, value, ttl, cache_type)
    async def adelete(self, *keys: str) -> int:
        return await self.async_ops.adelete(*keys)
    async def aexists(self, *keys: str) -> int:
        return await self.async_ops.aexists(*keys)
    async def attl(self, key: str) -> int:
        return await self.async_ops.attl(key)
    async def aexpire(self, key: str, ttl: int) -> bool:
        return await self.async_ops.aexpire(key, ttl)
    async def amget(self, keys: List[str], default: Any = None) -> List[Any]:
        return await self.async_ops.amget(keys, default)
    async def amset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        return await self.async_ops.amset(mapping, ttl)
    # ================== 连接管理和健康检查 ==================
    def ping(self) -> bool:
        return self.connection_manager.ping()
    async def aping(self) -> bool:
        return await self.connection_manager.aping()
    def health_check(self) -> bool:
        return self.connection_manager.health_check()
    def get_info(self) -> Dict[str, Any]:
        return self.connection_manager.get_info()
    @property
    def sync_client(self):
        return self.connection_manager.sync_client
    async def get_async_client(self):
        return await self.connection_manager.get_async_client()
    @property
    def client(self):
        return self.connection_manager.client
    def close(self):
        self.connection_manager.close()
    async def aclose(self):
        await self.connection_manager.aclose()
    # ================== 上下文管理器 ==================
    def sync_context(self):
        return self.connection_manager.sync_context()
    async def async_context(self):
        return await self.connection_manager.async_context()
    # ================== 缓存预热方法 ==================
    async def warmup_match_cache(self, match_id: int) -> bool:
        return await self.warmup_manager.warmup_match_cache(match_id)
    async def warmup_team_cache(self, team_id: int) -> bool:
        return await self.warmup_manager.warmup_team_cache(team_id)
    async def warmup_upcoming_matches(self, hours_ahead: int = 24) -> int:
        return await self.warmup_manager.warmup_upcoming_matches(hours_ahead)
    async def warmup_historical_stats(self, days: int = 7) -> bool:
        return await self.warmup_manager.warmup_historical_stats(days)
    async def full_warmup(self) -> Dict[str, int]:
        return await self.warmup_manager.full_warmup()