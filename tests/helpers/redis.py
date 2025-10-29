from typing import Optional
from typing import Union
from typing import Any
from typing import List
from typing import Dict
"""
Redis测试辅助工具
提供Redis客户端的Mock实现
"""

import json
import time


class MockRedis:
    """模拟Redis客户端"""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._closed = False

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置键值"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        elif not isinstance(value, str):
            value = str(value)

        self._data[key] = value
        if ex:
            self._expiry[key] = time.time() + ex
        return True

    def get(self, key: str) -> Optional[str]:
        """获取值"""
        if self._is_expired(key):
            self.delete(key)
            return None
        return self._data.get(key)

    def delete(self, key: str) -> int:
        """删除键"""
        self._data.pop(key, None)
        self._expiry.pop(key, None)
        return 1

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if self._is_expired(key):
            self.delete(key)
            return False
        return key in self._data

    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if key in self._data:
            self._expiry[key] = time.time() + seconds
            return True
        return False

    def ttl(self, key: str) -> int:
        """获取剩余生存时间"""
        if not self.exists(key):
            return -2  # 键不存在
        if key not in self._expiry:
            return -1  # 永不过期
        remaining = int(self._expiry[key] - time.time())
        return max(0, remaining)

    def incr(self, key: str, amount: int = 1) -> int:
        """递增"""
        current = int(self._data.get(key, 0))
        new_value = current + amount
        self._data[key] = str(new_value)
        return new_value

    def decr(self, key: str, amount: int = 1) -> int:
        """递减"""
        return self.incr(key, -amount)

    def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        """设置哈希字段"""
        if name not in self._data:
            self._data[name] = {}
        elif isinstance(self._data[name], str):
            self._data[name] = json.loads(self._data[name])

        count = 0
        for key, value in mapping.items():
            if key not in self._data[name] or self._data[name][key] != value:
                count += 1
            self._data[name][key] = str(value)

        return count

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希字段"""
        if not self.exists(name):
            return None

        data = self._data[name]
        if isinstance(data, str):
            data = json.loads(data)

        return data.get(key)

    def hgetall(self, name: str) -> Dict[str, str]:
        """获取所有哈希字段"""
        if not self.exists(name):
            return {}

        data = self._data[name]
        if isinstance(data, str):
            data = json.loads(data)

        return {k: str(v) for k, v in data.items()}

    def hdel(self, name: str, *keys: str) -> int:
        """删除哈希字段"""
        if not self.exists(name):
            return 0

        data = self._data[name]
        if isinstance(data, str):
            data = json.loads(data)

        count = 0
        for key in keys:
            if key in data:
                del data[key]
                count += 1

        self._data[name] = data
        return count

    def lpush(self, name: str, *values: Any) -> int:
        """左侧推入列表"""
        if name not in self._data:
            self._data[name] = []
        elif isinstance(self._data[name], str):
            self._data[name] = json.loads(self._data[name])

        for value in reversed(values):
            self._data[name].insert(0, str(value))

        return len(self._data[name])

    def rpush(self, name: str, *values: Any) -> int:
        """右侧推入列表"""
        if name not in self._data:
            self._data[name] = []
        elif isinstance(self._data[name], str):
            self._data[name] = json.loads(self._data[name])

        for value in values:
            self._data[name].append(str(value))

        return len(self._data[name])

    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """获取列表范围"""
        if not self.exists(name):
            return []

        data = self._data[name]
        if isinstance(data, str):
            data = json.loads(data)

        if end == -1:
            return data[start:]
        return data[start : end + 1]

    def lpop(self, name: str) -> Optional[str]:
        """左侧弹出"""
        if not self.exists(name):
            return None

        data = self._data[name]
        if isinstance(data, str):
            data = json.loads(data)

        if data:
            return data.pop(0)
        return None

    def rpop(self, name: str) -> Optional[str]:
        """右侧弹出"""
        if not self.exists(name):
            return None

        data = self._data[name]
        if isinstance(data, str):
            data = json.loads(data)

        if data:
            return data.pop()
        return None

    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """添加到有序集合"""
        if name not in self._data:
            self._data[name] = {}
        elif isinstance(self._data[name], str):
            self._data[name] = json.loads(self._data[name])

        count = 0
        for member, score in mapping.items():
            if member not in self._data[name]:
                count += 1
            self._data[name][member] = score

        return count

    def zrange(
        self, name: str, start: int, end: int, withscores: bool = False
    ) -> List[Union[str, tuple]]:
        """获取有序集合范围"""
        if not self.exists(name):
            return []

        data = self._data[name]
        if isinstance(data, str):
            data = json.loads(data)

        # 按分数排序
        sorted_items = sorted(data.items(), key=lambda x: x[1])
        if end == -1:
            sorted_items = sorted_items[start:]
        else:
            sorted_items = sorted_items[start : end + 1]

        if withscores:
            return [(member, score) for member, score in sorted_items]
        return [member for member, _ in sorted_items]

    def ping(self) -> bool:
        """Ping"""
        return True

    def flushall(self) -> bool:
        """清空所有数据"""
        self._data.clear()
        self._expiry.clear()
        return True

    def keys(self, pattern: str = "*") -> List[str]:
        """获取键列表"""
        import fnmatch

        keys = list(self._data.keys())
        if pattern != "*":
            keys = [key for key in keys if fnmatch.fnmatch(key, pattern)]
        return keys

    def close(self) -> None:
        """关闭连接"""
        self._closed = True

    def _is_expired(self, key: str) -> bool:
        """检查键是否过期"""
        if key not in self._expiry:
            return False
        return time.time() > self._expiry[key]


class MockAsyncRedis(MockRedis):
    """模拟异步Redis客户端"""

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """异步设置键值"""
        return super().set(key, value, ex)

    async def get(self, key: str) -> Optional[str]:
        """异步获取值"""
        return super().get(key)

    async def delete(self, key: str) -> int:
        """异步删除键"""
        return super().delete(key)

    async def exists(self, key: str) -> bool:
        """异步检查键是否存在"""
        return super().exists(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """异步设置过期时间"""
        return super().expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """异步获取剩余生存时间"""
        return super().ttl(key)

    async def incr(self, key: str, amount: int = 1) -> int:
        """异步递增"""
        return super().incr(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """异步递减"""
        return super().decr(key, amount)

    async def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        """异步设置哈希字段"""
        return super().hset(name, mapping)

    async def hget(self, name: str, key: str) -> Optional[str]:
        """异步获取哈希字段"""
        return super().hget(name, key)

    async def hgetall(self, name: str) -> Dict[str, str]:
        """异步获取所有哈希字段"""
        return super().hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """异步删除哈希字段"""
        return super().hdel(name, *keys)

    async def lpush(self, name: str, *values: Any) -> int:
        """异步左侧推入列表"""
        return super().lpush(name, *values)

    async def rpush(self, name: str, *values: Any) -> int:
        """异步右侧推入列表"""
        return super().rpush(name, *values)

    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """异步获取列表范围"""
        return super().lrange(name, start, end)

    async def lpop(self, name: str) -> Optional[str]:
        """异步左侧弹出"""
        return super().lpop(name)

    async def rpop(self, name: str) -> Optional[str]:
        """异步右侧弹出"""
        return super().rpop(name)

    async def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """异步添加到有序集合"""
        return super().zadd(name, mapping)

    async def zrange(
        self, name: str, start: int, end: int, withscores: bool = False
    ) -> List[Union[str, tuple]]:
        """异步获取有序集合范围"""
        return super().zrange(name, start, end, withscores)

    async def ping(self) -> bool:
        """异步Ping"""
        return super().ping()

    async def flushall(self) -> bool:
        """异步清空所有数据"""
        return super().flushall()

    async def keys(self, pattern: str = "*") -> List[str]:
        """异步获取键列表"""
        return super().keys(pattern)

    async def close(self) -> None:
        """异步关闭连接"""
        super().close()


class MockRedisConnectionPool:
    """模拟Redis连接池"""

    def __init__(self, **kwargs):
        self._connections: List[MockRedis] = []
        self.max_connections = kwargs.get("max_connections", 10)

    def get_connection(self) -> MockRedis:
        """获取连接"""
        if self._connections:
            return self._connections.pop()
        return MockRedis()

    def release_connection(self, connection: MockRedis) -> None:
        """释放连接"""
        if len(self._connections) < self.max_connections:
            self._connections.append(connection)

    def disconnect(self) -> None:
        """断开所有连接"""
        for connection in self._connections:
            connection.close()
        self._connections.clear()


def apply_redis_mocks():
    """应用Redis mock装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # 创建mock Redis实例
            mock_redis = MockRedis()
            mock_async_redis = MockAsyncRedis()

            # 设置测试数据
            mock_redis.set("test_key", "test_value")
            mock_redis.hset("test_hash", {"field1": "value1", "field2": "value2"})

            return func(mock_redis, mock_async_redis, *args, **kwargs)

        return wrapper

    return decorator


# 全局mock实例
mock_redis = MockRedis()
mock_async_redis = MockAsyncRedis()
mock_redis_pool = MockRedisConnectionPool()
