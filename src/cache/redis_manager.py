"""
import asyncio
Redis缓存管理器

实现Redis连接池、基础操作方法，支持异步和同步两种模式
"""

import json
import logging
import os
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, List, Optional, Union

import redis
import redis.asyncio as redis_async
from redis.exceptions import ConnectionError, RedisError, TimeoutError

logger = logging.getLogger(__name__)


class CacheKeyManager:
    """
    缓存Key命名规范管理器

    统一管理缓存Key的命名规则和TTL策略
    """

    # Key前缀定义
    PREFIXES = {
        "match": "match",
        "team": "team",
        "odds": "odds",
        "features": "features",
        "predictions": "predictions",
        "stats": "stats",
    }

    # TTL配置 (秒)
    TTL_CONFIG = {
        "match_info": 1800,  # 比赛信息: 30分钟
        "match_features": 1800,  # 比赛特征: 30分钟
        "team_stats": 3600,  # 球队统计: 1小时
        "team_features": 1800,  # 球队特征: 30分钟
        "odds_data": 300,  # 赔率数据: 5分钟
        "predictions": 3600,  # 预测结果: 1小时
        "historical_stats": 7200,  # 历史统计: 2小时
        "default": 1800,  # 默认: 30分钟
    }

    @classmethod
    def build_key(cls, prefix: str, *args, **kwargs) -> str:
        """
        构建缓存Key

        格式: {prefix}:{arg1}:{arg2}...[:additional_info]

        Args:
            prefix: Key前缀
            *args: Key组成部分
            **kwargs: 额外的Key信息

        Returns:
            str: 格式化的Key

        Examples:
            build_key('match', 123, 'features') -> 'match:123:features'
            build_key('team', 1, 'stats', type='recent') -> 'team:1:stats:recent'
        """
        if prefix not in cls.PREFIXES:
            logger.warning(f"未知的Key前缀: {prefix}")

        # 构建基础Key
        key_parts = [cls.PREFIXES.get(prefix, prefix)]
        # 过滤掉None和空字符串，但保留数字0
        key_parts.extend(
            str(arg)
            for arg in args
            if arg is not None and (str(arg).strip() or str(arg) == "0")
        )

        # 添加额外信息
        for k, v in kwargs.items():
            key_parts.append(f"{k}:{v}")

        return ":".join(key_parts)

    @classmethod
    def get_ttl(cls, cache_type: str) -> int:
        """
        获取缓存TTL

        Args:
            cache_type: 缓存类型

        Returns:
            int: TTL秒数
        """
        return cls.TTL_CONFIG.get(cache_type, cls.TTL_CONFIG["default"])

    # 常用Key模式定义
    @staticmethod
    def match_features_key(match_id: int) -> str:
        """比赛特征Key: match:{id}:features"""
        return CacheKeyManager.build_key("match", match_id, "features")

    @staticmethod
    def team_stats_key(team_id: int, stats_type: str = "recent") -> str:
        """球队统计Key: team:{id}:stats:{type}"""
        return CacheKeyManager.build_key("team", team_id, "stats", type=stats_type)

    @staticmethod
    def odds_key(match_id: int, bookmaker: str = "all") -> str:
        """赔率Key: odds:{match_id}:{bookmaker}"""
        return CacheKeyManager.build_key("odds", match_id, bookmaker)

    @staticmethod
    def prediction_key(match_id: int, model_version: str = "latest") -> str:
        """预测结果Key: predictions:{match_id}:{model_version}"""
        return CacheKeyManager.build_key("predictions", match_id, model_version)


class RedisManager:
    """
    Redis缓存管理器

    提供同步和异步的Redis操作，支持：
    - 连接池管理
    - 基础CRUD操作 (get/set/delete)
    - JSON数据序列化
    - TTL管理
    - 批量操作
    - 错误处理和重试
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_connections: int = 20,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
    ):
        """
        初始化Redis管理器

        Args:
            redis_url: Redis连接URL
            max_connections: 最大连接数
            socket_timeout: Socket超时时间
            socket_connect_timeout: Socket连接超时时间
            retry_on_timeout: 超时时是否重试
            health_check_interval: 健康检查间隔(秒)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval

        # 连接池
        self._sync_pool: Optional[redis.ConnectionPool] = None
        self._async_pool: Optional[redis_async.ConnectionPool] = None

        # 客户端
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[redis_async.Redis] = None

        # 初始化同步连接池
        self._init_sync_pool()

        logger.info(f"Redis管理器初始化完成，URL: {self._mask_password(self.redis_url)}")

    def _mask_password(self, url: str) -> str:
        """隐藏Redis URL中的密码"""
        import re

        return re.sub(r"(:)([^@/]+)(@)", r"\1****\3", url)

    def _init_sync_pool(self):
        """初始化同步连接池"""
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
            logger.info("同步Redis连接池初始化成功")
        except Exception as e:
            logger.error(f"同步Redis连接池初始化失败: {e}")
            self._sync_pool = None
            self._sync_client = None

    async def _init_async_pool(self):
        """初始化异步连接池"""
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
                logger.info("异步Redis连接池初始化成功")
            except Exception as e:
                logger.error(f"异步Redis连接池初始化失败: {e}")
                self._async_pool = None
                self._async_client = None

    @property
    def sync_client(self) -> Optional[redis.Redis]:
        """获取同步Redis客户端"""
        return self._sync_client

    async def get_async_client(self) -> Optional[redis_async.Redis]:
        """获取异步Redis客户端"""
        if self._async_client is None:
            await self._init_async_pool()
        return self._async_client

    # ================== 同步操作方法 ==================

    def get(self, key: str, default: Any = None) -> Any:
        """
        同步获取缓存数据

        Args:
            key: 缓存Key
            default: 默认值

        Returns:
            Any: 缓存数据，如果不存在或出错则返回default
        """
        if not self._sync_client:
            logger.warning("同步Redis客户端未初始化")
            return default

        try:
            value = self._sync_client.get(key)
            if value is None:
                return default

            # 尝试JSON反序列化
            try:
                return json.loads(value)  # type: ignore[arg-type]
            except json.JSONDecodeError:
                # 如果不是JSON，返回原始字符串
                return value.decode("utf-8") if isinstance(value, bytes) else value

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis GET操作失败 (key={key}): {e}")
            return default
        except Exception as e:
            logger.error(f"Redis GET操作异常 (key={key}): {e}")
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_type: Optional[str] = None,
    ) -> bool:
        """
        同步设置缓存数据

        Args:
            key: 缓存Key
            value: 缓存值
            ttl: 过期时间(秒)，如果为None则使用cache_type对应的TTL
            cache_type: 缓存类型，用于获取默认TTL

        Returns:
            bool: 是否设置成功
        """
        if not self._sync_client:
            logger.warning("同步Redis客户端未初始化")
            return False

        try:
            # 确定TTL
            if ttl is None:
                ttl = CacheKeyManager.get_ttl(cache_type or "default")

            # 序列化数据
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            else:
                serialized_value = str(value)

            # 设置缓存
            result = self._sync_client.setex(key, ttl, serialized_value)

            if result:
                logger.debug(f"Redis SET成功 (key={key}, ttl={ttl})")

            return bool(result)  # type: ignore[return-value]

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis SET操作失败 (key={key}): {e}")
            return False
        except Exception as e:
            logger.error(f"Redis SET操作异常 (key={key}): {e}")
            return False

    def delete(self, *keys: str) -> int:
        """
        同步删除缓存数据

        Args:
            *keys: 要删除的Key列表

        Returns:
            int: 成功删除的Key数量
        """
        if not self._sync_client:
            logger.warning("同步Redis客户端未初始化")
            return 0

        if not keys:
            return 0

        try:
            result = self._sync_client.delete(*keys)
            logger.debug(f"Redis DELETE成功，删除了 {result} 个Key")
            return int(result)  # type: ignore[arg-type]

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis DELETE操作失败 (keys={keys}): {e}")
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE操作异常 (keys={keys}): {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """
        同步检查Key是否存在

        Args:
            *keys: 要检查的Key列表

        Returns:
            int: 存在的Key数量
        """
        if not self._sync_client:
            logger.warning("同步Redis客户端未初始化")
            return 0

        if not keys:
            return 0

        try:
            return int(self._sync_client.exists(*keys))  # type: ignore[arg-type]
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis EXISTS操作失败 (keys={keys}): {e}")
            return 0
        except Exception as e:
            logger.error(f"Redis EXISTS操作异常 (keys={keys}): {e}")
            return 0

    def ttl(self, key: str) -> int:
        """
        同步获取Key的剩余TTL

        Args:
            key: 缓存Key

        Returns:
            int: 剩余TTL秒数，-1表示没有过期时间，-2表示Key不存在
        """
        if not self._sync_client:
            logger.warning("同步Redis客户端未初始化")
            return -2

        try:
            result = self._sync_client.ttl(key)
            return int(result)  # type: ignore[arg-type]
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis TTL操作失败 (key={key}): {e}")
            return -2
        except Exception as e:
            logger.error(f"Redis TTL操作异常 (key={key}): {e}")
            return -2

    # ================== 异步操作方法 ==================

    async def aget(self, key: str, default: Any = None) -> Any:
        """
        异步获取缓存数据

        Args:
            key: 缓存Key
            default: 默认值

        Returns:
            Any: 缓存数据，如果不存在或出错则返回default
        """
        client = await self.get_async_client()
        if not client:
            logger.warning("异步Redis客户端未初始化")
            return default

        try:
            value = await client.get(key)
            if value is None:
                return default

            # 尝试JSON反序列化
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # 如果不是JSON，返回原始字符串
                return value.decode("utf-8") if isinstance(value, bytes) else value

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"异步Redis GET操作失败 (key={key}): {e}")
            return default
        except Exception as e:
            logger.error(f"异步Redis GET操作异常 (key={key}): {e}")
            return default

    async def aset(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_type: Optional[str] = None,
    ) -> bool:
        """
        异步设置缓存数据

        Args:
            key: 缓存Key
            value: 缓存值
            ttl: 过期时间(秒)，如果为None则使用cache_type对应的TTL
            cache_type: 缓存类型，用于获取默认TTL

        Returns:
            bool: 是否设置成功
        """
        client = await self.get_async_client()
        if not client:
            logger.warning("异步Redis客户端未初始化")
            return False

        try:
            # 确定TTL
            if ttl is None:
                ttl = CacheKeyManager.get_ttl(cache_type or "default")

            # 序列化数据
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            else:
                serialized_value = str(value)

            # 设置缓存
            result = await client.setex(key, ttl, serialized_value)

            if result:
                logger.debug(f"异步Redis SET成功 (key={key}, ttl={ttl})")

            return result

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"异步Redis SET操作失败 (key={key}): {e}")
            return False
        except Exception as e:
            logger.error(f"异步Redis SET操作异常 (key={key}): {e}")
            return False

    async def adelete(self, *keys: str) -> int:
        """
        异步删除缓存数据

        Args:
            *keys: 要删除的Key列表

        Returns:
            int: 成功删除的Key数量
        """
        client = await self.get_async_client()
        if not client:
            logger.warning("异步Redis客户端未初始化")
            return 0

        if not keys:
            return 0

        try:
            result = await client.delete(*keys)
            logger.debug(f"异步Redis DELETE成功，删除了 {result} 个Key")
            return result

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"异步Redis DELETE操作失败 (keys={keys}): {e}")
            return 0
        except Exception as e:
            logger.error(f"异步Redis DELETE操作异常 (keys={keys}): {e}")
            return 0

    async def aexists(self, *keys: str) -> int:
        """
        异步检查Key是否存在

        Args:
            *keys: 要检查的Key列表

        Returns:
            int: 存在的Key数量
        """
        client = await self.get_async_client()
        if not client:
            logger.warning("异步Redis客户端未初始化")
            return 0

        if not keys:
            return 0

        try:
            return await client.exists(*keys)
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"异步Redis EXISTS操作失败 (keys={keys}): {e}")
            return 0
        except Exception as e:
            logger.error(f"异步Redis EXISTS操作异常 (keys={keys}): {e}")
            return 0

    async def attl(self, key: str) -> int:
        """
        异步获取Key的剩余TTL

        Args:
            key: 缓存Key

        Returns:
            int: 剩余TTL秒数，-1表示没有过期时间，-2表示Key不存在
        """
        client = await self.get_async_client()
        if not client:
            logger.warning("异步Redis客户端未初始化")
            return -2

        try:
            return await client.ttl(key)
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"异步Redis TTL操作失败 (key={key}): {e}")
            return -2
        except Exception as e:
            logger.error(f"异步Redis TTL操作异常 (key={key}): {e}")
            return -2

    # ================== 批量操作方法 ==================

    def mget(self, keys: List[str], default: Any = None) -> List[Any]:
        """
        同步批量获取缓存数据

        Args:
            keys: Key列表
            default: 默认值

        Returns:
            List[Any]: 缓存数据列表，与keys顺序对应
        """
        if not self._sync_client or not keys:
            return [default] * len(keys)

        try:
            values = self._sync_client.mget(keys)
            result = []

            for value in values:  # type: ignore[union-attr]
                if value is None:
                    result.append(default)
                else:
                    try:
                        result.append(json.loads(value))
                    except json.JSONDecodeError:
                        result.append(
                            value.decode("utf-8") if isinstance(value, bytes) else value
                        )

            return result

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis MGET操作失败 (keys={keys}): {e}")
            return [default] * len(keys)
        except Exception as e:
            logger.error(f"Redis MGET操作异常 (keys={keys}): {e}")
            return [default] * len(keys)

    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        同步批量设置缓存数据

        Args:
            mapping: Key-Value映射字典
            ttl: 过期时间(秒)

        Returns:
            bool: 是否全部设置成功
        """
        if not self._sync_client or not mapping:
            return False

        try:
            # 序列化所有值
            serialized_mapping: Dict[
                Union[str, bytes], Union[str, bytes, int, float]
            ] = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized_mapping[key] = json.dumps(
                        value, ensure_ascii=False, default=str
                    )
                else:
                    serialized_mapping[key] = str(value)

            # 批量设置
            result = self._sync_client.mset(serialized_mapping)  # type: ignore[type-var]

            # 如果指定了TTL，需要逐个设置过期时间
            if result and ttl:
                pipe = self._sync_client.pipeline()
                for key in mapping.keys():
                    pipe.expire(key, ttl)
                pipe.execute()

            return bool(result)  # type: ignore[return-value]

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis MSET操作失败: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis MSET操作异常: {e}")
            return False

    async def amget(self, keys: List[str], default: Any = None) -> List[Any]:
        """
        异步批量获取缓存数据

        Args:
            keys: Key列表
            default: 默认值

        Returns:
            List[Any]: 缓存数据列表，与keys顺序对应
        """
        client = await self.get_async_client()
        if not client or not keys:
            return [default] * len(keys)

        try:
            values = await client.mget(keys)
            result = []

            for value in values:
                if value is None:
                    result.append(default)
                else:
                    try:
                        result.append(json.loads(value))
                    except json.JSONDecodeError:
                        result.append(
                            value.decode("utf-8") if isinstance(value, bytes) else value
                        )

            return result

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"异步Redis MGET操作失败 (keys={keys}): {e}")
            return [default] * len(keys)
        except Exception as e:
            logger.error(f"异步Redis MGET操作异常 (keys={keys}): {e}")
            return [default] * len(keys)

    async def amset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        异步批量设置缓存数据

        Args:
            mapping: Key-Value映射字典
            ttl: 过期时间(秒)

        Returns:
            bool: 是否全部设置成功
        """
        client = await self.get_async_client()
        if not client or not mapping:
            return False

        try:
            # 序列化所有值
            serialized_mapping: Dict[
                Union[str, bytes], Union[str, bytes, int, float]
            ] = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized_mapping[key] = json.dumps(
                        value, ensure_ascii=False, default=str
                    )
                else:
                    serialized_mapping[key] = str(value)

            # 批量设置
            result = await client.mset(serialized_mapping)  # type: ignore[type-var]

            # 如果指定了TTL，需要逐个设置过期时间
            if result and ttl:
                async with client.pipeline() as pipe:
                    for key in mapping.keys():
                        pipe.expire(key, ttl)
                    await pipe.execute()

            return bool(result)  # type: ignore[return-value]

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"异步Redis MSET操作失败: {e}")
            return False
        except Exception as e:
            logger.error(f"异步Redis MSET操作异常: {e}")
            return False

    # ================== 连接管理和健康检查 ==================

    def ping(self) -> bool:
        """
        同步Redis连接健康检查

        Returns:
            bool: 连接是否健康
        """
        if not self._sync_client:
            return False

        try:
            response = self._sync_client.ping()
            return response is True
        except Exception as e:
            logger.error(f"Redis PING失败: {e}")
            return False

    async def aping(self) -> bool:
        """
        异步Redis连接健康检查

        Returns:
            bool: 连接是否健康
        """
        client = await self.get_async_client()
        if not client:
            return False

        try:
            response = await client.ping()
            return response is True
        except Exception as e:
            logger.error(f"异步Redis PING失败: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """
        获取Redis服务器信息

        Returns:
            Dict[str, Any]: Redis服务器信息
        """
        if not self._sync_client:
            return {}

        try:
            info = self._sync_client.info()  # type: ignore[union-attr]
            return {
                "version": info.get("redis_version", "unknown"),  # type: ignore[union-attr]
                "mode": info.get("redis_mode", "standalone"),  # type: ignore[union-attr]
                "connected_clients": info.get("connected_clients", 0),  # type: ignore[union-attr]
                "used_memory_human": info.get("used_memory_human", "0B"),  # type: ignore[union-attr]
                "keyspace_hits": info.get("keyspace_hits", 0),  # type: ignore[union-attr]
                "keyspace_misses": info.get("keyspace_misses", 0),  # type: ignore[union-attr]
                "total_commands_processed": info.get("total_commands_processed", 0),  # type: ignore[union-attr]
            }
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return {}

    def close(self):
        """关闭同步连接池"""
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
        """关闭异步连接池"""
        try:
            if self._async_pool:
                await self._async_pool.aclose()
                self._async_pool = None
                logger.info("异步Redis连接池已关闭")
        except Exception as e:
            logger.error(f"关闭异步Redis连接池失败: {e}")

    async def aexpire(self, key: str, ttl: int) -> bool:
        """
        异步设置Key的过期时间

        Args:
            key: 缓存Key
            ttl: 过期时间 (秒)

        Returns:
            bool: 是否成功
        """
        try:
            client = await self.get_async_client()
            if client:
                return await client.expire(key, ttl)
            return False
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"设置Key过期时间失败 (async): {key}, error: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """
        同步设置Key的过期时间

        Args:
            key: 缓存Key
            ttl: 过期时间 (秒)

        Returns:
            bool: 是否成功
        """
        try:
            result = self._sync_client.expire(key, ttl)
            return bool(result)  # type: ignore[return-value]
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"设置Key过期时间失败 (sync): {key}, error: {e}")
            return False

    # ================== 上下文管理器 ==================

    @contextmanager
    def sync_context(self):
        """同步Redis上下文管理器"""
        try:
            yield self
        finally:
            pass  # 连接池会自动管理连接

    @asynccontextmanager
    async def async_context(self):  # type: ignore[misc]
        """异步Redis上下文管理器"""
        try:
            yield self
        finally:
            pass  # 连接池会自动管理连接


# 全局Redis管理器实例（单例模式）
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """
    获取全局Redis管理器实例（单例模式）

    Returns:
        RedisManager: Redis管理器实例
    """
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


# 便捷函数，直接使用全局实例
def get_cache(key: str, default: Any = None) -> Any:
    """便捷函数：获取缓存"""
    return get_redis_manager().get(key, default)


def set_cache(
    key: str, value: Any, ttl: Optional[int] = None, cache_type: Optional[str] = None
) -> bool:
    """便捷函数：设置缓存"""
    return get_redis_manager().set(key, value, ttl, cache_type)


def delete_cache(*keys: str) -> int:
    """便捷函数：删除缓存"""
    return get_redis_manager().delete(*keys)


async def aget_cache(key: str, default: Any = None) -> Any:
    """便捷函数：异步获取缓存"""
    return await get_redis_manager().aget(key, default)


async def aset_cache(
    key: str, value: Any, ttl: Optional[int] = None, cache_type: Optional[str] = None
) -> bool:
    """便捷函数：异步设置缓存"""
    return await get_redis_manager().aset(key, value, ttl, cache_type)


async def adelete_cache(*keys: str) -> int:
    """便捷函数：异步删除缓存"""
    return await get_redis_manager().adelete(*keys)
