"""
模拟Redis管理器
Mock Redis Manager

用于开发和测试环境的内存缓存管理。
Memory cache manager for development and testing environments.
"""

import fnmatch
import time
from typing import Any


class MockRedis:
    """模拟Redis管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._ttl = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "MockRedis":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        if self._is_expired(key):
            self.delete(key)
            return None
        return self._data.get(key)

    def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        """设置缓存值"""
        self._data[key] = value
        if ex:
            self._ttl[key] = time.time() + ex
        return True

    def setex(self, key: str, seconds: int, value: Any) -> bool:
        """设置带TTL的缓存值"""
        return self.set(key, value, seconds)

    def delete(self, key: str) -> bool:
        """删除缓存键"""
        deleted = key in self._data
        self._data.pop(key, None)
        self._ttl.pop(key, None)
        return deleted

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if self._is_expired(key):
            self.delete(key)
            return False
        return key in self._data

    def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间"""
        if key in self._data:
            self._ttl[key] = time.time() + seconds
            return True
        return False

    def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        if key not in self._data:
            return -2

        if key not in self._ttl:
            return -1

        remaining = int(self._ttl[key] - time.time())
        if remaining <= 0:
            self.delete(key)
            return -2

        return remaining

    def keys(self, pattern: str = "*") -> list:
        """获取匹配模式的所有键"""
        # 清理过期键
        expired_keys = [k for k in self._data.keys() if self._is_expired(k)]
        for key in expired_keys:
            self.delete(key)

        return [key for key in self._data.keys() if fnmatch.fnmatch(key, pattern)]

    def flushall(self) -> bool:
        """清空所有数据"""
        self._data.clear()
        self._ttl.clear()
        return True

    def _is_expired(self, key: str) -> bool:
        """检查键是否过期"""
        if key not in self._ttl:
            return False
        return time.time() > self._ttl[key]

    def hget(self, name: str, key: str) -> Any | None:
        """获取哈希字段值"""
        hash_key = f"hash:{name}"
        hash_data = self.get(hash_key)
        if hash_data and isinstance(hash_data, dict):
            return hash_data.get(key)
        return None

    def hset(self, name: str, key: str, value: Any) -> int:
        """设置哈希字段值"""
        hash_key = f"hash:{name}"
        hash_data = self.get(hash_key) or {}
        if not isinstance(hash_data, dict):
            hash_data = {}

        is_new = key not in hash_data
        hash_data[key] = value
        self.set(hash_key, hash_data)
        return 1 if is_new else 0

    def hgetall(self, name: str) -> dict[str, Any]:
        """获取哈希所有字段值"""
        hash_key = f"hash:{name}"
        hash_data = self.get(hash_key)
        return hash_data if isinstance(hash_data, dict) else {}

    def incr(self, key: str) -> int:
        """将键值增1"""
        current = self.get(key) or 0
        try:
            new_value = int(current) + 1
        except (ValueError, TypeError):
            new_value = 1
        self.set(key, new_value)
        return new_value

    def decr(self, key: str) -> int:
        """将键值减1"""
        current = self.get(key) or 0
        try:
            new_value = int(current) - 1
        except (ValueError, TypeError):
            new_value = -1
        self.set(key, new_value)
        return new_value


class CacheKeyManager:
    """缓存键管理器"""

    @staticmethod
    def generate_key(prefix: str, *args) -> str:
        """生成缓存键"""
        if args:
            return f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return prefix

    @staticmethod
    def get_match_key(match_id: str) -> str:
        """获取比赛缓存键"""
        return f"match:{match_id}"

    @staticmethod
    def get_prediction_key(prediction_id: str) -> str:
        """获取预测缓存键"""
        return f"prediction:{prediction_id}"

    @staticmethod
    def get_user_key(user_id: str) -> str:
        """获取用户缓存键"""
        return f"user:{user_id}"


class MockRedisManager:
    """模拟Redis管理器"""

    def __init__(self):
        self.redis = MockRedis.get_instance()

    def ping(self):
        """检查连接状态"""
        return True

    def get(self, key: str, default=None):
        """获取值"""
        return self.redis.get(key) or default

    def set(self, key: str, value, ex=None):
        """设置值"""
        return self.redis.set(key, value, ex)

    def delete(self, key: str):
        """删除键"""
        return self.redis.delete(key)

    def exists(self, key: str):
        """检查键是否存在"""
        return self.redis.exists(key)

    def keys(self, pattern="*"):
        """获取键列表"""
        return self.redis.keys(pattern)

    def flushall(self):
        """清空所有数据"""
        return self.redis.flushall()


# 全局实例
mock_redis = MockRedis.get_instance()
cache_key_manager = CacheKeyManager()


# 异步便捷函数
async def adelete_cache(key: str) -> bool:
    """异步删除缓存"""
    return mock_redis.delete(key)


async def aexists_cache(key: str) -> bool:
    """异步检查键是否存在"""
    return mock_redis.exists(key)


async def aget_cache(key: str, default=None):
    """异步获取缓存值"""
    return mock_redis.get(key) or default


async def amget_cache(keys: list[str]) -> list:
    """异步批量获取缓存值"""
    return [mock_redis.get(key) for key in keys]


async def amset_cache(mapping: dict) -> bool:
    """异步批量设置缓存值"""
    for key, value in mapping.items():
        mock_redis.set(key, value)
    return True


async def aset_cache(key: str, value, ex=None) -> bool:
    """异步设置缓存值"""
    return mock_redis.set(key, value, ex)


async def attl_cache(key: str) -> int:
    """异步获取TTL"""
    return mock_redis.ttl(key)


# 同步便捷函数
def delete_cache(key: str) -> bool:
    """同步删除缓存"""
    return mock_redis.delete(key)


def exists_cache(key: str) -> bool:
    """同步检查键是否存在"""
    return mock_redis.exists(key)


def get_cache(key: str, default=None):
    """同步获取缓存值"""
    return mock_redis.get(key) or default


def mget_cache(keys: list[str]) -> list:
    """同步批量获取缓存值"""
    return [mock_redis.get(key) for key in keys]


def mset_cache(mapping: dict) -> bool:
    """同步批量设置缓存值"""
    for key, value in mapping.items():
        mock_redis.set(key, value)
    return True


def set_cache(key: str, value, ex=None) -> bool:
    """同步设置缓存值"""
    return mock_redis.set(key, value, ex)


def ttl_cache(key: str) -> int:
    """同步获取TTL"""
    return mock_redis.ttl(key)


def get_redis_manager():
    """获取Redis管理器实例"""
    return MockRedisManager()


def startup_warmup():
    """启动时预热缓存"""
    # Mock实现，实际Redis可能需要预热操作
    pass


__all__ = [
    "MockRedis",
    "mock_redis",
    "CacheKeyManager",
    "cache_key_manager",
    "MockRedisManager",
    "get_redis_manager",
    "startup_warmup",
    # 异步便捷函数
    "adelete_cache",
    "aexists_cache",
    "aget_cache",
    "amget_cache",
    "amset_cache",
    "aset_cache",
    "attl_cache",
    # 同步便捷函数
    "delete_cache",
    "exists_cache",
    "get_cache",
    "mget_cache",
    "mset_cache",
    "set_cache",
    "ttl_cache",
]
