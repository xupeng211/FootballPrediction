"""
增强Redis缓存管理器
Enhanced Redis Cache Manager

提供完整的Redis缓存功能，支持连接池、集群、哨兵等高级特性。
"""

import asyncio
import json
import pickle
import time
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
import logging

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    aioredis = None

from .mock_redis import MockRedisManager

logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    encoding: str = "utf-8"
    decode_responses: bool = True
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    max_connections: int = 50
    connection_pool_kwargs: Optional[Dict] = None

    # 集群配置
    cluster_nodes: Optional[List[Dict[str, Union[str, int]]]] = None
    cluster_mode: bool = False

    # 哨兵配置
    sentinel_servers: Optional[List[Dict[str, Union[str, int]]]] = None
    sentinel_service_name: Optional[str] = None
    sentinel_mode: bool = False

    # SSL配置
    ssl: bool = False
    ssl_cert_reqs: Optional[str] = None
    ssl_ca_certs: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None


class EnhancedRedisManager:
    """增强Redis管理器"""

    def __init__(self, config: RedisConfig = None, use_mock: bool = None):
        """
        初始化Redis管理器

        Args:
            config: Redis配置
            use_mock: 是否使用模拟Redis，None时自动检测
        """
        self.config = config or RedisConfig()

        # 自动决定是否使用mock
        if use_mock is None:
            use_mock = not REDIS_AVAILABLE

        self.use_mock = use_mock
        self._sync_client = None
        self._async_client = None
        self._connection_pool = None
        self._async_connection_pool = None

        logger.info(f"Redis管理器初始化完成，使用{'模拟' if use_mock else '真实'}Redis")

    def _create_sync_client(self):
        """创建同步Redis客户端"""
        if self.use_mock:
            return MockRedisManager()

        if not REDIS_AVAILABLE:
            raise ImportError("redis包未安装，请安装: pip install redis")

        try:
            if self.config.cluster_mode and self.config.cluster_nodes:
                # 集群模式
                from rediscluster import RedisCluster
                client = RedisCluster(
                    startup_nodes=self.config.cluster_nodes,
                    decode_responses=self.config.decode_responses,
                    skip_full_coverage_check=True,
                    **(self.config.connection_pool_kwargs or {})
                )
            elif self.config.sentinel_mode and self.config.sentinel_servers:
                # 哨兵模式
                sentinel = redis.Sentinel(
                    [(s['host'], s['port']) for s in self.config.sentinel_servers],
                    socket_timeout=self.config.socket_timeout,
                    **(self.config.connection_pool_kwargs or {})
                )
                client = sentinel.master_for(
                    self.config.sentinel_service_name,
                    decode_responses=self.config.decode_responses
                )
            else:
                # 单机模式
                pool_kwargs = {
                    'host': self.config.host,
                    'port': self.config.port,
                    'db': self.config.db,
                    'password': self.config.password,
                    'encoding': self.config.encoding,
                    'decode_responses': self.config.decode_responses,
                    'socket_timeout': self.config.socket_timeout,
                    'socket_connect_timeout': self.config.socket_connect_timeout,
                    'retry_on_timeout': self.config.retry_on_timeout,
                    'health_check_interval': self.config.health_check_interval,
                    'max_connections': self.config.max_connections,
                    **(self.config.connection_pool_kwargs or {})
                }

                self._connection_pool = redis.ConnectionPool(**pool_kwargs)
                client = redis.Redis(connection_pool=self._connection_pool)

            # 测试连接
            client.ping()
            logger.info("Redis同步连接建立成功")
            return client

        except Exception as e:
            logger.error(f"Redis同步连接失败: {e}")
            raise

    def _create_async_client(self):
        """创建异步Redis客户端"""
        if self.use_mock:
            return MockRedisManager()

        if not REDIS_AVAILABLE:
            raise ImportError("redis包未安装，请安装: pip install redis")

        try:
            pool_kwargs = {
                'host': self.config.host,
                'port': self.config.port,
                'db': self.config.db,
                'password': self.config.password,
                'encoding': self.config.encoding,
                'decode_responses': self.config.decode_responses,
                'socket_timeout': self.config.socket_timeout,
                'socket_connect_timeout': self.config.socket_connect_timeout,
                'retry_on_timeout': self.config.retry_on_timeout,
                'max_connections': self.config.max_connections,
                **(self.config.connection_pool_kwargs or {})
            }

            self._async_connection_pool = aioredis.ConnectionPool(**pool_kwargs)
            client = aioredis.Redis(connection_pool=self._async_connection_pool)

            # 测试连接
            asyncio.create_task(client.ping())
            logger.info("Redis异步连接建立成功")
            return client

        except Exception as e:
            logger.error(f"Redis异步连接失败: {e}")
            raise

    @property
    def sync_client(self):
        """获取同步客户端（懒加载）"""
        if self._sync_client is None:
            self._sync_client = self._create_sync_client()
        return self._sync_client

    @property
    def async_client(self):
        """获取异步客户端（懒加载）"""
        if self._async_client is None:
            self._async_client = self._create_async_client()
        return self._async_client

    # 基础操作方法
    def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        return self.sync_client.get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None, px: Optional[int] = None) -> bool:
        """设置缓存值"""
        return self.sync_client.set(key, value, ex=ex, px=px)

    def setex(self, key: str, seconds: int, value: str) -> bool:
        """设置带TTL的缓存值"""
        return self.sync_client.setex(key, seconds, value)

    def psetex(self, key: str, milliseconds: int, value: str) -> bool:
        """设置带毫秒TTL的缓存值"""
        return self.sync_client.psetex(key, milliseconds, value)

    def delete(self, *keys: str) -> int:
        """删除缓存键"""
        return self.sync_client.delete(*keys)

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return bool(self.sync_client.exists(key))

    def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间"""
        return bool(self.sync_client.expire(key, seconds))

    def pexpire(self, key: str, milliseconds: int) -> bool:
        """设置键的毫秒过期时间"""
        return bool(self.sync_client.pexpire(key, milliseconds))

    def ttl(self, key: str) -> int:
        """获取键的TTL（秒）"""
        return self.sync_client.ttl(key)

    def pttl(self, key: str) -> int:
        """获取键的TTL（毫秒）"""
        return self.sync_client.pttl(key)

    def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的所有键"""
        return self.sync_client.keys(pattern)

    def flushdb(self) -> bool:
        """清空当前数据库"""
        return self.sync_client.flushdb()

    def flushall(self) -> bool:
        """清空所有数据库"""
        return self.sync_client.flushall()

    # 批量操作
    def mget(self, keys: List[str]) -> List[Optional[str]]:
        """批量获取缓存值"""
        return self.sync_client.mget(keys)

    def mset(self, mapping: Dict[str, str]) -> bool:
        """批量设置缓存值"""
        return self.sync_client.mset(mapping)

    # 异步操作
    async def aget(self, key: str) -> Optional[str]:
        """异步获取缓存值"""
        if self.use_mock:
            return self.sync_client.aget(key)
        else:
            return await self.async_client.get(key)

    async def aset(self, key: str, value: str, ex: Optional[int] = None, px: Optional[int] = None) -> bool:
        """异步设置缓存值"""
        if self.use_mock:
            return self.sync_client.aset(key, value, ex=ex, px=px)
        else:
            return await self.async_client.set(key, value, ex=ex, px=px)

    async def asetex(self, key: str, seconds: int, value: str) -> bool:
        """异步设置带TTL的缓存值"""
        if self.use_mock:
            return self.sync_client.asetex(key, seconds, value)
        else:
            return await self.async_client.setex(key, seconds, value)

    async def apsetex(self, key: str, milliseconds: int, value: str) -> bool:
        """异步设置带毫秒TTL的缓存值"""
        if self.use_mock:
            return self.sync_client.apsetex(key, milliseconds, value)
        else:
            return await self.async_client.psetex(key, milliseconds, value)

    async def adelete(self, *keys: str) -> int:
        """异步删除缓存键"""
        if self.use_mock:
            return self.sync_client.adelete(*keys)
        else:
            return await self.async_client.delete(*keys)

    async def aexists(self, key: str) -> bool:
        """异步检查键是否存在"""
        if self.use_mock:
            return self.sync_client.aexists(key)
        else:
            return bool(await self.async_client.exists(key))

    async def aexpire(self, key: str, seconds: int) -> bool:
        """异步设置键的过期时间"""
        if self.use_mock:
            return self.sync_client.aexpire(key, seconds)
        else:
            return bool(await self.async_client.expire(key, seconds))

    async def apexpire(self, key: str, milliseconds: int) -> bool:
        """异步设置键的毫秒过期时间"""
        if self.use_mock:
            return self.sync_client.apexpire(key, milliseconds)
        else:
            return bool(await self.async_client.pexpire(key, milliseconds))

    async def attl(self, key: str) -> int:
        """异步获取键的TTL（秒）"""
        if self.use_mock:
            return self.sync_client.attl(key)
        else:
            return await self.async_client.ttl(key)

    async def apttl(self, key: str) -> int:
        """异步获取键的TTL（毫秒）"""
        if self.use_mock:
            return self.sync_client.apttl(key)
        else:
            return await self.async_client.pttl(key)

    async def akeys(self, pattern: str = "*") -> List[str]:
        """异步获取匹配模式的所有键"""
        if self.use_mock:
            return self.sync_client.akeys(pattern)
        else:
            return await self.async_client.keys(pattern)

    async def amget(self, keys: List[str]) -> List[Optional[str]]:
        """异步批量获取缓存值"""
        if self.use_mock:
            return self.sync_client.amget(keys)
        else:
            return await self.async_client.mget(keys)

    async def amset(self, mapping: Dict[str, str]) -> bool:
        """异步批量设置缓存值"""
        if self.use_mock:
            return self.sync_client.amset(mapping)
        else:
            return await self.async_client.mset(mapping)

    # 高级操作
    def incr(self, key: str, amount: int = 1) -> int:
        """递增数值"""
        return self.sync_client.incr(key, amount)

    def decr(self, key: str, amount: int = 1) -> int:
        """递减数值"""
        return self.sync_client.decr(key, amount)

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希字段值"""
        return self.sync_client.hget(name, key)

    def hset(self, name: str, mapping: Dict[str, str]) -> int:
        """设置哈希字段值"""
        return self.sync_client.hset(name, mapping=mapping)

    def hgetall(self, name: str) -> Dict[str, str]:
        """获取所有哈希字段值"""
        return self.sync_client.hgetall(name)

    def lpush(self, name: str, *values: str) -> int:
        """左侧推入列表"""
        return self.sync_client.lpush(name, *values)

    def rpush(self, name: str, *values: str) -> int:
        """右侧推入列表"""
        return self.sync_client.rpush(name, *values)

    def lpop(self, name: str) -> Optional[str]:
        """左侧弹出列表元素"""
        return self.sync_client.lpop(name)

    def rpop(self, name: str) -> Optional[str]:
        """右侧弹出列表元素"""
        return self.sync_client.rpop(name)

    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[str]:
        """获取列表范围内的元素"""
        return self.sync_client.lrange(name, start, end)

    def sadd(self, name: str, *values: str) -> int:
        """添加到集合"""
        return self.sync_client.sadd(name, *values)

    def srem(self, name: str, *values: str) -> int:
        """从集合中删除"""
        return self.sync_client.srem(name, *values)

    def smembers(self, name: str) -> set:
        """获取集合所有成员"""
        return self.sync_client.smembers(name)

    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """添加到有序集合"""
        return self.sync_client.zadd(name, mapping)

    def zrange(self, name: str, start: int = 0, end: int = -1, desc: bool = False) -> List[str]:
        """获取有序集合范围内的元素"""
        return self.sync_client.zrange(name, start, end, desc=desc)

    def zrem(self, name: str, *values: str) -> int:
        """从有序集合中删除"""
        return self.sync_client.zrem(name, *values)

    # 序列化操作
    def set_json(self, key: str, obj: Any, ex: Optional[int] = None) -> bool:
        """设置JSON对象"""
        json_str = json.dumps(obj, ensure_ascii=False)
        return self.set(key, json_str, ex=ex)

    def get_json(self, key: str) -> Optional[Any]:
        """获取JSON对象"""
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def set_pickle(self, key: str, obj: Any, ex: Optional[int] = None) -> bool:
        """设置pickle对象"""
        pickle_bytes = pickle.dumps(obj)
        return self.sync_client.set(key, pickle_bytes, ex=ex)

    def get_pickle(self, key: str) -> Optional[Any]:
        """获取pickle对象"""
        value = self.sync_client.get(key)
        if value is None:
            return None
        try:
            return pickle.loads(value)
        except pickle.PickleError:
            return value

    # 健康检查
    def ping(self) -> bool:
        """健康检查"""
        try:
            result = self.sync_client.ping()
            return result
        except Exception:
            return False

    async def aping(self) -> bool:
        """异步健康检查"""
        try:
            result = await self.async_client.ping()
            return result
        except Exception:
            return False

    def info(self) -> Dict[str, Any]:
        """获取Redis信息"""
        try:
            info = self.sync_client.info()
            return dict(info)
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return {}

    # 关闭连接
    def close(self):
        """关闭连接"""
        if self._connection_pool:
            self._connection_pool.disconnect()
        if self._sync_client and hasattr(self._sync_client, 'close'):
            self._sync_client.close()

    async def aclose(self):
        """异步关闭连接"""
        if self._async_connection_pool:
            await self._async_connection_pool.disconnect()
        if self._async_client and hasattr(self._async_client, 'close'):
            await self._async_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()


# 全局实例
_global_redis_manager: Optional[EnhancedRedisManager] = None


def get_redis_manager(config: RedisConfig = None, use_mock: bool = None) -> EnhancedRedisManager:
    """获取全局Redis管理器实例"""
    global _global_redis_manager
    if _global_redis_manager is None:
        _global_redis_manager = EnhancedRedisManager(config, use_mock)
    return _global_redis_manager


def reset_redis_manager():
    """重置全局Redis管理器"""
    global _global_redis_manager
    if _global_redis_manager:
        _global_redis_manager.close()
    _global_redis_manager = None