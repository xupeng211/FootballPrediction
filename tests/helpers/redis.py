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

    def llen(self, key: str) -> int:
        value = self._store.get(key)
        if isinstance(value, list):
            return len(value)
        return 0

    def lpush(self, key: str, value: Any) -> int:
        bucket = self._store.setdefault(key, [])
        if isinstance(bucket, list):
            bucket.insert(0, value)
            return len(bucket)
        return 0

    def rpush(self, key: str, value: Any) -> int:
        bucket = self._store.setdefault(key, [])
        if isinstance(bucket, list):
            bucket.append(value)
            return len(bucket)
        return 0

    def expire(self, key: str, ttl: int) -> bool:
        return key in self._store

    def close(self) -> None:
        return None


class MockAsyncRedis(MockRedis):
    """异步 Redis 替身"""

    async def get(self, key: str) -> Any:  # type: ignore[override]
        return super().get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:  # type: ignore[override]
        return super().set(key, value, ex)

    async def delete(self, *keys: str) -> int:  # type: ignore[override]
        return super().delete(*keys)

    async def ping(self) -> bool:  # type: ignore[override]
        return True

    async def close(self) -> None:  # type: ignore[override]
        return None


class MockRedisConnectionPool:
    """轻量级连接池对象"""

    def __init__(self, url: str, **_: Any) -> None:
        self.url = url

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> "MockRedisConnectionPool":
        return cls(url, **kwargs)


def _ensure_submodule(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        sys.modules[name] = module
    return module


def apply_redis_mocks(monkeypatch: MonkeyPatch) -> None:
    """替换 Redis 依赖为内存桩"""

    try:
        import redis  # type: ignore
    except ImportError:
        redis = ModuleType("redis")  # type: ignore
        sys.modules["redis"] = redis

    monkeypatch.setattr(redis, "Redis", MockRedis, raising=False)
    monkeypatch.setattr(redis, "from_url", lambda url, **kwargs: MockRedis(), raising=False)
    monkeypatch.setattr(redis, "ConnectionPool", MockRedisConnectionPool, raising=False)

    redis_async = getattr(redis, "asyncio", None)
    if redis_async is None:
        redis_async = _ensure_submodule("redis.asyncio")
        redis.asyncio = redis_async  # type: ignore[attr-defined]

    monkeypatch.setattr(redis_async, "Redis", MockAsyncRedis, raising=False)
    monkeypatch.setattr(redis_async, "from_url", lambda url, **kwargs: MockAsyncRedis(), raising=False)
    monkeypatch.setattr(redis_async, "ConnectionPool", MockRedisConnectionPool, raising=False)

    redis_exceptions = getattr(redis, "exceptions", None)
    if redis_exceptions is None:
        redis_exceptions = _ensure_submodule("redis.exceptions")
        redis.exceptions = redis_exceptions  # type: ignore[attr-defined]

    monkeypatch.setattr(redis_exceptions, "ConnectionError", RuntimeError, raising=False)
    monkeypatch.setattr(redis_exceptions, "RedisError", RuntimeError, raising=False)
    monkeypatch.setattr(redis_exceptions, "TimeoutError", TimeoutError, raising=False)


__all__ = [
    "MockRedis",
    "MockAsyncRedis",
    "MockRedisConnectionPool",
    "apply_redis_mocks",
]
