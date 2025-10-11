"""
模拟Redis管理器（用于测试和开发）
Mock Redis Manager for Testing and Development
"""

import time
from typing import Any, Dict, List, Optional, Union


class MockRedisManager:
    """模拟Redis管理器"""

    _instance: Optional["MockRedisManager"] = None
    _data: Dict[str, Any]
    _expirations: Dict[str, float]

    def __new__(cls) -> "MockRedisManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._expirations = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "MockRedisManager":
        """获取单例实例"""
        return cls()

    def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        self._check_expiration(key)
        return self._data.get(key)

    def set(self, key: str, value: str) -> bool:
        """设置缓存值"""
        self._data[key] = value
        return True

    def setex(self, key: str, seconds: int, value: str) -> bool:
        """设置带TTL的缓存值"""
        self._data[key] = value
        self._expirations[key] = time.time() + seconds
        return True

    def delete(self, *keys: str) -> int:
        """删除缓存键"""
        count = 0
        for key in keys:
            if self._data.pop(key, None) is not None:
                count += 1
            self._expirations.pop(key, None)
        return count

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        self._check_expiration(key)
        return key in self._data

    def keys(self, pattern: str) -> List[str]:
        """获取匹配模式的所有键"""
        self._cleanup_expired()
        if "*" in pattern:
            import fnmatch

            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
        else:
            return [k for k in self._data.keys() if k == pattern]

    def ttl(self, key: str) -> int:
        """获取键的TTL"""
        if key not in self._data:
            return -2
        if key not in self._expirations:
            return -1
        remaining = self._expirations[key] - time.time()
        return max(0, int(remaining))

    # 异步方法
    async def aget(self, key: str) -> Optional[str]:
        """异步获取缓存值"""
        return self.get(key)

    async def aset(self, key: str, value: str) -> bool:
        """异步设置缓存值"""
        return self.set(key, value)

    async def asetex(self, key: str, seconds: int, value: str) -> bool:
        """异步设置带TTL的缓存值"""
        return self.setex(key, seconds, value)

    async def adelete(self, *keys: str) -> int:
        """异步删除缓存键"""
        return self.delete(*keys)

    async def aexists(self, key: str) -> bool:
        """异步检查键是否存在"""
        return self.exists(key)

    async def akeys(self, pattern: str) -> List[str]:
        """异步获取匹配模式的所有键"""
        return self.keys(pattern)

    async def attl(self, key: str) -> int:
        """异步获取键的TTL"""
        return self.ttl(key)

    # 内部方法
    def _check_expiration(self, key: str) -> None:
        """检查键是否过期"""
        if key in self._expirations and time.time() > self._expirations[key]:
            self._data.pop(key, None)
            self._expirations.pop(key, None)

    def _cleanup_expired(self) -> None:
        """清理所有过期键"""
        now = time.time()
        expired_keys = [k for k, exp in self._expirations.items() if now > exp]
        for key in expired_keys:
            self._data.pop(key, None)
            self._expirations.pop(key, None)

    def clear(self) -> None:
        """清空所有缓存"""
        self._data.clear()
        self._expirations.clear()

    def size(self) -> int:
        """获取缓存大小"""
        self._cleanup_expired()
        return len(self._data)


class CacheKeyManager:
    """缓存键管理器"""

    @staticmethod
    def build_key(*parts: str) -> str:
        """构建缓存键"""
        return ":".join(str(part) for part in parts)

    @staticmethod
    def user_key(user_id: Union[int, str], suffix: str = "") -> str:
        """构建用户相关键"""
        key = f"user:{user_id}"
        if suffix:
            key = f"{key}:{suffix}"
        return key

    @staticmethod
    def match_key(match_id: Union[int, str], suffix: str = "") -> str:
        """构建比赛相关键"""
        key = f"match:{match_id}"
        if suffix:
            key = f"{key}:{suffix}"
        return key

    @staticmethod
    def team_key(team_id: Union[int, str], suffix: str = "") -> str:
        """构建球队相关键"""
        key = f"team:{team_id}"
        if suffix:
            key = f"{key}:{suffix}"
        return key

    @staticmethod
    def prediction_key(user_id: Union[int, str], match_id: Union[int, str]) -> str:
        """构建预测相关键"""
        return f"prediction:{user_id}:{match_id}"


def get_redis_manager() -> MockRedisManager:
    """获取Redis管理器实例"""
    return MockRedisManager()


# 向后兼容的便捷函数
def get_cache(key: str) -> Optional[str]:
    """获取缓存"""
    return get_redis_manager().get(key)


def set_cache(key: str, value: str, ttl: Optional[int] = None) -> bool:
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


def mget_cache(*keys: str) -> List[Optional[str]]:
    """批量获取缓存"""
    manager = get_redis_manager()
    return [manager.get(k) for k in keys]


def mset_cache(mapping: Dict[str, str], ttl: Optional[int] = None) -> bool:
    """批量设置缓存"""
    manager = get_redis_manager()
    for key, value in mapping.items():
        if ttl:
            manager.setex(key, ttl, value)
        else:
            manager.set(key, value)
    return True


# 异步便捷函数
async def aget_cache(key: str) -> Optional[str]:
    """异步获取缓存"""
    return await get_redis_manager().aget(key)


async def aset_cache(key: str, value: str, ttl: Optional[int] = None) -> bool:
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


async def amget_cache(*keys: str) -> List[Optional[str]]:
    """异步批量获取缓存"""
    manager = get_redis_manager()
    return [await manager.aget(k) for k in keys]


async def amset_cache(mapping: Dict[str, str], ttl: Optional[int] = None) -> bool:
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
