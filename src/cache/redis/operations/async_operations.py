"""
Redis异步操作

提供Redis的异步基础操作方法，包括aget、aset、adelete等
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis_async

# 兼容性处理：支持不同版本的redis包
try:
    from redis.exceptions import ConnectionError, RedisError, TimeoutError
except ImportError:
    # 如果redis.exceptions不可用，从redis模块直接导入
    try:
        from redis import ConnectionError, RedisError, TimeoutError
    except ImportError:
        # 如果还是没有，创建基本异常类
        class RedisError(Exception):
            pass

        class ConnectionError(RedisError):
            pass

        class TimeoutError(RedisError):
            pass

from ..core.key_manager import CacheKeyManager


logger = logging.getLogger(__name__)


class RedisAsyncOperations:
    """
    Redis异步操作类

    提供所有Redis异步操作的方法，包括基础CRUD、批量操作等
    """

    def __init__(self, connection_manager):
        """
        初始化异步操作类

        Args:
            connection_manager: Redis连接管理器实例
        """
        self.connection_manager = connection_manager

    async def aget(self, key: str, default: Any = None) -> Any:
        """
        异步获取缓存数据

        Args:
            key: 缓存Key
            default: 默认值

        Returns:
            Any: 缓存数据，如果不存在或出错则返回default
        """
        client = await self.connection_manager.get_async_client()
        if not client:
            logger.warning("异步Redis客户端未初始化")
            return default

        try:
            value = await client.get(key)
            if value is None:
                return default

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
        client = await self.connection_manager.get_async_client()
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
        client = await self.connection_manager.get_async_client()
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
        client = await self.connection_manager.get_async_client()
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
        client = await self.connection_manager.get_async_client()
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
            client = await self.connection_manager.get_async_client()
            if client:
                return await client.expire(key, ttl)
            return False
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"设置Key过期时间失败 (async): {key}, error: {e}")
            return False

    # ================== 批量操作方法 ==================

    async def amget(self, keys: List[str], default: Any = None) -> List[Any]:
        """
        异步批量获取缓存数据

        Args:
            keys: Key列表
            default: 默认值

        Returns:
            List[Any]: 缓存数据列表，与keys顺序对应
        """
        client = await self.connection_manager.get_async_client()
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
        client = await self.connection_manager.get_async_client()
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