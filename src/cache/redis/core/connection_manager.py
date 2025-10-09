"""

"""









    """

    """

        """

        """








        """隐藏Redis URL中的密码"""

        """初始化同步连接池"""

        """初始化异步连接池"""

        """确保同步客户端可用"""

        """获取同步Redis客户端"""

        """获取异步Redis客户端"""


        """

        """


        """

        """


        """对外的健康检查接口"""

        """

        """



        """暴露底层同步客户端"""

        """关闭同步连接池"""

        """关闭异步连接池"""


        """同步Redis上下文管理器"""

        """异步Redis上下文管理器"""


    from redis.exceptions import ConnectionError, RedisError, TimeoutError
        from redis import ConnectionError, RedisError, TimeoutError
        import sys
from typing import Optional
import os
import re
import redis
import redis.asyncio as redis_async

Redis连接管理器
管理Redis同步和异步连接池的创建、维护和健康检查
# 兼容性处理：支持不同版本的redis包
try:
except ImportError:
    # 如果redis.exceptions不可用，从redis模块直接导入
    try:
    except ImportError:
        # 如果还是没有，创建基本异常类
        class RedisError(Exception):
            pass
        class ConnectionError(RedisError):
            pass
        class TimeoutError(RedisError):
            pass
logger = logging.getLogger(__name__)
class RedisConnectionManager:
    Redis连接管理器
    负责管理同步和异步的Redis连接池，提供连接池的创建、
    健康检查和连接管理功能
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_connections: int = 50,  # 增加到50以支持更高并发
        socket_timeout: float = 3.0,  # 减少超时时间提高响应速度
        socket_connect_timeout: float = 3.0,  # 减少连接超时时间
        retry_on_timeout: bool = True,
        health_check_interval: int = 60,  # 增加健康检查频率
    ):
        初始化Redis连接管理器
        Args:
            redis_url: Redis连接URL
            max_connections: 最大连接数
            socket_timeout: Socket超时时间
            socket_connect_timeout: Socket连接超时时间
            retry_on_timeout: 超时时是否重试
            health_check_interval: 健康检查间隔(秒)
        # 检查是否在测试环境中
        is_test_env = (
            os.getenv("ENVIRONMENT") == "test"
            or "pytest" in sys.modules
            or "pytest" in sys.argv[0]
        )
        default_redis_host = "redis" if is_test_env else "localhost"
        default_redis_url = f"redis://{default_redis_host}:6379/0"
        # 使用环境变量 REDIS_URL，如果未设置则使用默认URL
        self.redis_url = redis_url or os.getenv("REDIS_URL", default_redis_url)
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval
        # 初始化连接池和客户端属性
        self._sync_pool: Optional[redis.ConnectionPool] = None
        self._async_pool: Optional[redis_async.ConnectionPool] = None
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[redis_async.Redis] = None
        # 处理Redis密码
        redis_password = os.getenv("REDIS_PASSWORD")
        if redis_password and not is_test_env:
            # 使用正则表达式在URL中插入密码（如果URL还没有密码）
            if "@" not in self.redis_url.split("://", 1)[-1].split("/", 1)[0]:
                self.redis_url = re.sub(r"://", f"://{redis_password}@", self.redis_url)
        # 初始化同步连接池，保证基础操作可用
        self._init_sync_pool()
    def _mask_password(self, url: str) -> str:
        return re.sub(r"(:)([^@/]+)(@)", r"\1****\3", url)
    def _init_sync_pool(self):
        try:
            self._sync_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                health_check_interval=self.health_check_interval,
            )
            self._sync_client = redis.Redis(connection_pool=self._sync_pool)
            logger.info(f"同步Redis连接池初始化成功: {self._mask_password(self.redis_url)}")
        except Exception as e:
            logger.error(f"同步Redis连接池初始化失败: {e}")
            self._sync_pool = None
            self._sync_client = None
    async def _init_async_pool(self):
        if self._async_pool is None:
            try:
                self._async_pool = redis_async.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.max_connections,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    retry_on_timeout=self.retry_on_timeout,
                    health_check_interval=self.health_check_interval,
                )
                self._async_client = redis_async.Redis(connection_pool=self._async_pool)
                logger.info(f"异步Redis连接池初始化成功: {self._mask_password(self.redis_url)}")
            except Exception as e:
                logger.error(f"异步Redis连接池初始化失败: {e}")
                self._async_pool = None
                self._async_client = None
    def _ensure_sync_client(self) -> Optional[redis.Redis]:
        if self._sync_client is None:
            self._init_sync_pool()
        return self._sync_client
    @property
    def sync_client(self) -> Optional[redis.Redis]:
        return self._sync_client
    async def get_async_client(self) -> Optional[redis_async.Redis]:
        if self._async_client is None:
            await self._init_async_pool()
        return self._async_client
    # ================== 健康检查方法 ==================
    def ping(self) -> bool:
        同步Redis连接健康检查
        Returns:
            bool: 连接是否健康
        client = self._ensure_sync_client()
        if not client:
            raise ConnectionError("Redis客户端未初始化")
        response = client.ping()
        if response is not True:
            raise RedisError("Redis PING返回异常")
        return True
    async def aping(self) -> bool:
        异步Redis连接健康检查
        Returns:
            bool: 连接是否健康
        client = await self.get_async_client()
        if not client:
            raise ConnectionError("异步Redis客户端未初始化")
        response = await client.ping()
        if response is not True:
            raise RedisError("异步Redis PING返回异常")
        return True
    def health_check(self) -> bool:
        try:
            return self.ping()
        except Exception as exc:
            logger.error("Redis健康检查失败: %s", exc)
            return False
    def get_info(self) -> dict:
        获取Redis服务器信息
        Returns:
            dict: Redis服务器信息
        client = self._ensure_sync_client()
        if not client:
            return {}
        try:
            return client.info()  # type: ignore[union-attr]
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return {}
    # ================== 连接管理方法 ==================
    @property
    def client(self) -> Optional[redis.Redis]:
        return self._ensure_sync_client()
    def close(self):
        try:
            if self._sync_pool:
                self._sync_pool.disconnect()
                self._sync_pool = None
            if self._sync_client:
                self._sync_client = None
            logger.info("同步Redis连接池已关闭")
        except Exception as e:
            logger.error(f"关闭同步Redis连接池失败: {e}")
    async def aclose(self):
        try:
            if self._async_pool:
                await self._async_pool.aclose()
                self._async_pool = None
                logger.info("异步Redis连接池已关闭")
        except Exception as e:
            logger.error(f"关闭异步Redis连接池失败: {e}")
    # ================== 上下文管理器 ==================
    @contextmanager
    def sync_context(self):
        try:
            yield self
        finally:
            pass  # 连接池会自动管理连接
    @asynccontextmanager
    async def async_context(self):
        try:
            yield self
        finally:
            pass  # 连接池会自动管理连接