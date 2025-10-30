"""Redis 测试桩 - 重构版本（不使用 monkeypatch）"""

from typing import Any, Dict, Optional


class MockRedis:
    """简化版同步 Redis 客户端"""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                count += 1
        return count

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    def keys(self, pattern: str = "*") -> list:
        if pattern == "*":
            return list(self._store.keys())
        return [k for k in self._store.keys() if pattern.replace("*", "") in k]

    def flushdb(self) -> bool:
        self._store.clear()
        return True

    def close(self) -> None:
        pass


class MockAsyncRedis:
    """简化版异步 Redis 客户端"""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Any:
        return self._store.get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                count += 1
        return count

    async def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    async def keys(self, pattern: str = "*") -> list:
        if pattern == "*":
            return list(self._store.keys())
        return [k for k in self._store.keys() if pattern.replace("*", "") in k]

    async def flushdb(self) -> bool:
        self._store.clear()
        return True

    async def close(self) -> None:
        pass


class MockRedisConnectionPool:
    """模拟 Redis 连接池"""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


# 创建全局 mock 实例（仅在测试中使用）
_global_redis_mock = None
_global_async_redis_mock = None


def get_mock_redis() -> MockRedis:
    """获取 Redis mock 实例（单例）"""
    global _global_redis_mock
    if _global_redis_mock is None:
        _global_redis_mock = MockRedis()
    return _global_redis_mock


def get_mock_async_redis() -> MockAsyncRedis:
    """获取异步 Redis mock 实例（单例）"""
    global _global_async_redis_mock
    if _global_async_redis_mock is None:
        _global_async_redis_mock = MockAsyncRedis()
    return _global_async_redis_mock


def reset_redis_mocks() -> None:
    """重置 Redis mock 实例（用于测试隔离）"""
    global _global_redis_mock, _global_async_redis_mock
    if _global_redis_mock:
        _global_redis_mock._store.clear()
    if _global_async_redis_mock:
        _global_async_redis_mock._store.clear()


# 向后兼容的函数（现在只是返回 mock 实例,不使用 monkeypatch）
def apply_redis_mocks(*args, **kwargs) -> Dict[str, Any]:
    """
    向后兼容:返回 Redis mocks
    不再使用 monkeypatch,而是返回 mock 实例供测试使用
    """
    return {
        "redis": get_mock_redis(),
        "redis.asyncio": get_mock_async_redis(),
    }


__all__ = [
    "MockRedis",
    "MockAsyncRedis",
    "MockRedisConnectionPool",
    "get_mock_redis",
    "get_mock_async_redis",
    "reset_redis_mocks",
    "apply_redis_mocks",
]
