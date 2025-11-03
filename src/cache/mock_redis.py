"""
模拟Redis管理器（用于测试和开发）
Mock Redis Manager for Testing and Development
"""

import time
from typing import Any, Optional


class MockRedisManager:
    """类文档字符串"""

    pass  # 添加pass语句
    """模拟Redis管理器"""

    _instance: Optional["MockRedisManager"] = None
    data: dict[str, Any]
    _expirations: dict[str, float]

    def __new__(cls) -> "MockRedisManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.data = {}
            cls._instance._expirations = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "MockRedisManager":
        """获取单例实例"""
        return cls()

    def get(self, key: str) -> str | None:
        """获取缓存值"""
        self._check_expiration(key)
        return self.data.get(key)

    def set(
        self, key: str, value: str, ex: int | None = None, px: int | None = None
    ) -> bool:
        """设置缓存值"""
        self.data[key] = value
        if ex is not None:
            self._expirations[key] = time.time() + ex
        elif px is not None:
            self._expirations[key] = time.time() + (px / 1000)
        return True

    def setex(self, key: str, seconds: int, value: str) -> bool:
        """设置带TTL的缓存值"""
        self.data[key] = value
        self._expirations[key] = time.time() + seconds
        return True

    def delete(self, *keys: str) -> int:
        """删除缓存键"""
        count = 0
        for key in keys:
            if self.data.pop(key, None) is not None:
                count += 1
            self._expirations.pop(key, None)
        return count

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        self._check_expiration(key)
        return key in self.data

    def keys(self, pattern: str) -> list[str]:
        """获取匹配模式的所有键"""
        self._cleanup_expired()
        if "*" in pattern:
            import fnmatch

            return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]
        else:
            return [k for k in self.data.keys() if k == pattern]

    def ttl(self, key: str) -> int:
        """获取键的TTL"""
        if key not in self.data:
            return -2
        if key not in self._expirations:
            return -1
        remaining = self._expirations[key] - time.time()
        return max(0, int(remaining))

    # 异步方法
    async def aget(self, key: str) -> str | None:
        """异步获取缓存值"""
        return self.get(key)

    async def aset(
        self, key: str, value: str, ex: int | None = None, px: int | None = None
    ) -> bool:
        """异步设置缓存值"""
        return self.set(key, value, ex=ex, px=px)

    async def asetex(self, key: str, seconds: int, value: str) -> bool:
        """异步设置带TTL的缓存值"""
        return self.setex(key, seconds, value)

    async def adelete(self, *keys: str) -> int:
        """异步删除缓存键"""
        return self.delete(*keys)

    async def aexists(self, key: str) -> bool:
        """异步检查键是否存在"""
        return self.exists(key)

    async def akeys(self, pattern: str) -> list[str]:
        """异步获取匹配模式的所有键"""
        return self.keys(pattern)

    async def attl(self, key: str) -> int:
        """异步获取键的TTL"""
        return self.ttl(key)

    async def aexpire(self, key: str, seconds: int) -> bool:
        """异步设置键的过期时间"""
        return self.expire(key, seconds)

    async def apexpire(self, key: str, milliseconds: int) -> bool:
        """异步设置键的毫秒过期时间"""
        return self.pexpire(key, milliseconds)

    async def apttl(self, key: str) -> int:
        """异步获取键的毫秒TTL"""
        return int(self.ttl(key) * 1000) if self.ttl(key) > 0 else self.ttl(key)

    async def amget(self, keys: list[str]) -> list[str | None]:
        """异步批量获取缓存值"""
        return self.mget(keys)

    async def amset(self, mapping: dict[str, str]) -> bool:
        """异步批量设置缓存值"""
        return self.mset(mapping)

    async def aping(self) -> bool:
        """异步健康检查"""
        return self.ping()

    async def aflushdb(self) -> bool:
        """异步清空当前数据库"""
        return self.flushdb()

    async def aflushall(self) -> bool:
        """异步清空所有数据库"""
        return self.flushall()

    # 内部方法
    def _check_expiration(self, key: str) -> None:
        """检查键是否过期"""
        if key in self._expirations and time.time() > self._expirations[key]:
            self.data.pop(key, None)
            self._expirations.pop(key, None)

    def _cleanup_expired(self) -> None:
        """清理所有过期键"""
        now = time.time()
        expired_keys = [k for k, exp in self._expirations.items() if now > exp]
        for key in expired_keys:
            self.data.pop(key, None)
            self._expirations.pop(key, None)

    def incr(self, key: str, amount: int = 1) -> int:
        """递增数值"""
        current = self.get(key) or "0"
        try:
            new_value = int(current) + amount
        except ValueError:
            new_value = amount
        self.set(key, str(new_value))
        return new_value

    def decr(self, key: str, amount: int = 1) -> int:
        """递减数值"""
        return self.incr(key, -amount)

    def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间"""
        if key in self.data:
            self._expirations[key] = time.time() + seconds
            return True
        return False

    def pexpire(self, key: str, milliseconds: int) -> bool:
        """设置键的毫秒过期时间"""
        return self.expire(key, milliseconds / 1000)

    def keys(self, pattern: str = "*") -> list[str]:
        """获取匹配模式的所有键"""
        self._cleanup_expired()
        if "*" in pattern:
            import fnmatch

            return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]
        else:
            return [k for k in self.data.keys() if k == pattern]

    def mget(self, keys: list[str]) -> list[str | None]:
        """批量获取缓存值"""
        return [self.get(k) for k in keys]

    def mset(self, mapping: dict[str, str]) -> bool:
        """批量设置缓存值"""
        for key, value in mapping.items():
            self.set(key, value)
        return True

    def ping(self) -> bool:
        """健康检查"""
        return True

    def flushdb(self) -> bool:
        """清空当前数据库"""
        self.clear()
        return True

    def flushall(self) -> bool:
        """清空所有数据库"""
        self.clear()
        return True

    def clear(self) -> None:
        """清空所有缓存"""
        self.data.clear()
        self._expirations.clear()

    def size(self) -> int:
        """获取缓存大小"""
        self._cleanup_expired()
        return len(self.data)


class CacheKeyManager:
    """类文档字符串"""

    pass  # 添加pass语句
    """缓存键管理器"""

    @staticmethod
    def build_key(*parts: str) -> str:
        """构建缓存键"""
        return ":".join(str(part) for part in parts)

    @staticmethod
    def user_key(user_id: int | str, suffix: str = "") -> str:
        """构建用户相关键"""
        key = f"user:{user_id}"
        if suffix:
            key = f"{key}:{suffix}"
        return key

    @staticmethod
    def match_key(match_id: int | str, suffix: str = "") -> str:
        """构建比赛相关键"""
        key = f"match:{match_id}"
        if suffix:
            key = f"{key}:{suffix}"
        return key

    @staticmethod
    def team_key(team_id: int | str, suffix: str = "") -> str:
        """构建球队相关键"""
        key = f"team:{team_id}"
        if suffix:
            key = f"{key}:{suffix}"
        return key

    @staticmethod
    def prediction_key(user_id: int | str, match_id: int | str) -> str:
        """构建预测相关键"""
        return f"prediction:{user_id}:{match_id}"


def get_redis_manager() -> MockRedisManager:
    """获取Redis管理器实例"""
    return MockRedisManager()


# 向后兼容的便捷函数
def get_cache(key: str) -> str | None:
    """获取缓存"""
    return get_redis_manager().get(key)


def set_cache(key: str, value: str, ttl: int | None = None) -> bool:
    """设置缓存"""
    manager = get_redis_manager()
    if ttl:
        return manager.setex(key, ttl, value)
    return manager.set(key, value)


def delete_cache(*keys: str) -> int:
    """删除缓存"""
    return get_redis_manager().delete(*keys)


def exists_cache(key: str) -> bool:
    """检查缓存是否存在"""
    return get_redis_manager().exists(key)


def ttl_cache(key: str) -> int:
    """获取缓存TTL"""
    return get_redis_manager().ttl(key)


def mget_cache(*keys: str) -> list[str | None]:
    """批量获取缓存"""
    manager = get_redis_manager()
    return [manager.get(k) for k in keys]


def mset_cache(mapping: dict[str, str], ttl: int | None = None) -> bool:
    """批量设置缓存"""
    manager = get_redis_manager()
    for key, value in mapping.items():
        if ttl:
            manager.setex(key, ttl, value)
        else:
            manager.set(key, value)
    return True


# 异步便捷函数
async def aget_cache(key: str) -> str | None:
    """异步获取缓存"""
    return await get_redis_manager().aget(key)


async def aset_cache(key: str, value: str, ttl: int | None = None) -> bool:
    """异步设置缓存"""
    manager = get_redis_manager()
    if ttl:
        return await manager.asetex(key, ttl, value)
    return await manager.aset(key, value)


async def adelete_cache(*keys: str) -> int:
    """异步删除缓存"""
    return await get_redis_manager().adelete(*keys)


async def aexists_cache(key: str) -> bool:
    """异步检查缓存是否存在"""
    return await get_redis_manager().aexists(key)


async def attl_cache(key: str) -> int:
    """异步获取缓存TTL"""
    return await get_redis_manager().attl(key)


async def amget_cache(*keys: str) -> list[str | None]:
    """异步批量获取缓存"""
    manager = get_redis_manager()
    return [await manager.aget(k) for k in keys]


async def amset_cache(mapping: dict[str, str], ttl: int | None = None) -> bool:
    """异步批量设置缓存"""
    manager = get_redis_manager()
    for key, value in mapping.items():
        if ttl:
            await manager.asetex(key, ttl, value)
        else:
            await manager.aset(key, value)
    return True


async def startup_warmup() -> None:
    """启动时预热"""
    pass
