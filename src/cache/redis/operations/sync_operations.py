"""
Redis同步操作

提供Redis的同步基础操作方法，包括get、set、delete等
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import redis

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


class RedisSyncOperations:
    """
    Redis同步操作类

    提供所有Redis同步操作的方法，包括基础CRUD、批量操作等
    """

    def __init__(self, connection_manager):
        """
        初始化同步操作类

        Args:
            connection_manager: Redis连接管理器实例
        """
        self.connection_manager = connection_manager

    def get(self, key: str, default: Any = None) -> Any:
        """
        同步获取缓存数据

        Args:
            key: 缓存Key
            default: 默认值

        Returns:
            Any: 缓存数据，如果不存在或出错则返回default
        """
        client = self.connection_manager._ensure_sync_client()
        if not client:
            logger.warning("同步Redis客户端未初始化")
            return default

        try:
            value = client.get(key)
            if value is None:
                return default

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
        client = self.connection_manager._ensure_sync_client()
        if not client:
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
            result = client.set(name=key, value=serialized_value, ex=ttl)

            if result:
                logger.debug(f"Redis SET成功 (key={key}, ttl={ttl})")

            return result  # type: ignore[return-value]

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
        client = self.connection_manager._ensure_sync_client()
        if not client:
            logger.warning("同步Redis客户端未初始化")
            return 0

        if not keys:
            return 0

        try:
            result = client.delete(*keys)
            logger.debug(f"Redis DELETE成功，删除了 {result} 个Key")
            return int(result)  # type: ignore[arg-type]

        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis DELETE操作失败 (keys={keys}): {e}")
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE操作异常 (keys={keys}): {e}")
            return 0

    def keys(self, pattern: str = "*") -> List[Any]:
        """获取匹配的键列表"""
        client = self.connection_manager._ensure_sync_client()
        if not client:
            return []

        try:
            return list(client.keys(pattern))
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis KEYS操作失败 (pattern={pattern}): {e}")
            return []
        except Exception as e:
            logger.error(f"Redis KEYS操作异常 (pattern={pattern}): {e}")
            return []

    def exists(self, *keys: str) -> int:
        """
        同步检查Key是否存在

        Args:
            *keys: 要检查的Key列表

        Returns:
            int: 存在的Key数量
        """
        client = self.connection_manager._ensure_sync_client()
        if not client:
            logger.warning("同步Redis客户端未初始化")
            return 0

        if not keys:
            return 0

        try:
            return int(client.exists(*keys))  # type: ignore[arg-type]
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
        client = self.connection_manager._ensure_sync_client()
        if not client:
            logger.warning("同步Redis客户端未初始化")
            return -2

        try:
            result = client.ttl(key)
            return int(result)  # type: ignore[arg-type]
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis TTL操作失败 (key={key}): {e}")
            return -2
        except Exception as e:
            logger.error(f"Redis TTL操作异常 (key={key}): {e}")
            return -2

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
            client = self.connection_manager._ensure_sync_client()
            if client is None:
                return False
            result = client.expire(key, ttl)
            return bool(result)  # type: ignore[return-value]
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"设置Key过期时间失败 (sync): {key}, error: {e}")
            return False

    def clear_all(self) -> Any:
        """清空当前数据库"""
        client = self.connection_manager._ensure_sync_client()
        if not client:
            logger.warning("同步Redis客户端未初始化，无法清理缓存")
            return None

        try:
            return client.flushdb()
        except Exception as e:
            logger.error(f"Redis FLUSHDB失败: {e}")
            raise

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
        client = self.connection_manager._ensure_sync_client()
        if not client or not keys:
            return [default] * len(keys)

        try:
            values = client.mget(keys)
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
        client = self.connection_manager._ensure_sync_client()
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
            result = client.mset(serialized_mapping)  # type: ignore[type-var]

            # 如果指定了TTL，需要逐个设置过期时间
            if result and ttl:
                pipe = client.pipeline()
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