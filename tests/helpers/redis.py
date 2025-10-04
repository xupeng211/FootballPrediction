"""Redis 测试桩"""

import sys
from types import ModuleType
from typing import Any, Dict, Optional

from pytest import MonkeyPatch


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


def apply_redis_mocks(monkeypatch: MonkeyPatch) -> None:
    """
    应用 Redis mock

    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    # 创建 mock 模块
    mock_redis = ModuleType("redis")
    mock_redis.Redis = MockRedis
    mock_redis.ConnectionPool = MockRedisConnectionPool

    # 创建 mock redis.asyncio 模块
    mock_redis_async = ModuleType("redis.asyncio")
    mock_redis_async.Redis = MockAsyncRedis
    mock_redis_async.ConnectionPool = MockRedisConnectionPool

    # 应用 mock
    monkeypatch.setitem(sys.modules, "redis", mock_redis)
    monkeypatch.setitem(sys.modules, "redis.asyncio", mock_redis_async)
    monkeypatch.setitem(sys.modules, "redis.client", mock_redis)
    monkeypatch.setitem(sys.modules, "redis.asyncio.client", mock_redis_async)


__all__ = [
    "MockRedis",
    "MockAsyncRedis",
    "MockRedisConnectionPool",
    "apply_redis_mocks",
]