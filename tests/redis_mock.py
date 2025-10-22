# Redis Mock配置用于测试
import asyncio
from typing import Any, Dict, Optional
from unittest.mock import Mock, AsyncMock


class MockRedis:
    """模拟Redis客户端"""

    def __init__(self):
        self._data = {}
        self._connected = True

    def ping(self):
        return self._connected

    def get(self, key: str) -> Optional[bytes]:
        return self._data.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._data[key] = value
        return True

    def delete(self, key: str) -> int:
        return self._data.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        return key in self._data

    def keys(self, pattern: str = "*"):
        return [k.encode() for k in self._data.keys()]

    def flushdb(self):
        self._data.clear()
        return True

    def info(self):
        return {"used_memory": len(str(self._data)), "connected_clients": 1}


# 全局Redis客户端实例
redis_client = MockRedis()


def get_redis_client():
    """获取Redis客户端（测试用Mock）"""
    return redis_client


async def get_async_redis_client():
    """获取异步Redis客户端（测试用Mock）"""
    return redis_client
