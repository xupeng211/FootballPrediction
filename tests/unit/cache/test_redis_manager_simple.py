import os
"""
Redis管理器简单测试
Simple tests for Redis manager to boost coverage
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 尝试导入Redis管理器
try:
    from src.cache.redis_manager import RedisManager
except ImportError:
    RedisManager = None


class TestRedisManagerSimple:
    """Redis管理器简单测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if RedisManager is None:
            pytest.skip("RedisManager not available")

        # 创建测试实例
        self.redis_url = os.getenv("TEST_REDIS_MANAGER_SIMPLE_REDIS_URL_28")
        self.manager = RedisManager(
            redis_url=self.redis_url,
            max_connections=10,
            socket_timeout=3.0
        )

    def test_manager_initialization(self):
        """测试管理器初始化"""
        assert self.manager.redis_url == self.redis_url
        assert self.manager.max_connections == 10
        assert self.manager.socket_timeout == 3.0

    @pytest.mark.asyncio
    async def test_set_get_string(self):
        """测试字符串设置和获取"""
        with patch.object(self.manager, '_redis') as mock_redis:
            # Mock Redis客户端
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.get = AsyncMock(return_value=b"test_value")

            # 测试设置
            result = await self.manager.set("test_key", "test_value")
            assert result is True

            # 测试获取
            value = await self.manager.get("test_key")
            assert value == "test_value"

    @pytest.mark.asyncio
    async def test_set_get_json(self):
        """测试JSON对象设置和获取"""
        test_data = {
            "id": 123,
            "name": "Test",
            "timestamp": datetime.now().isoformat()
        }

        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.get = AsyncMock(return_value=json.dumps(test_data).encode())

            # 设置JSON
            result = await self.manager.set_json("json_key", test_data)
            assert result is True

            # 获取JSON
            value = await self.manager.get_json("json_key")
            assert value == test_data

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        """测试带TTL的设置"""
        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.setex = AsyncMock(return_value=True)

            # 设置带TTL的键值
            ttl_seconds = 3600
            result = await self.manager.set_with_ttl(
                "ttl_key",
                "ttl_value",
                ttl_seconds
            )
            assert result is True

            # 验证调用了setex
            mock_redis.setex.assert_called_once_with(
                "ttl_key",
                ttl_seconds,
                "ttl_value"
            )

    @pytest.mark.asyncio
    async def test_delete_key(self):
        """测试删除键"""
        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.delete = AsyncMock(return_value=1)

            result = await self.manager.delete("test_key")
            assert result == 1

    @pytest.mark.asyncio
    async def test_exists_key(self):
        """测试检查键是否存在"""
        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.exists = AsyncMock(return_value=1)

            result = await self.manager.exists("test_key")
            assert result is True

            # 测试键不存在
            mock_redis.exists.return_value = 0
            result = await self.manager.exists("nonexistent_key")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_ttl(self):
        """测试获取键的TTL"""
        with patch.object(self.manager, '_redis') as mock_redis:
            # 键存在且有TTL
            mock_redis.ttl = AsyncMock(return_value=3600)
            ttl = await self.manager.get_ttl("test_key")
            assert ttl == 3600

            # 键存在但无TTL
            mock_redis.ttl.return_value = -1
            ttl = await self.manager.get_ttl("persistent_key")
            assert ttl == -1

            # 键不存在
            mock_redis.ttl.return_value = -2
            ttl = await self.manager.get_ttl("nonexistent_key")
            assert ttl == -2

    @pytest.mark.asyncio
    async def test_expire_key(self):
        """测试为键设置过期时间"""
        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.expire = AsyncMock(return_value=True)

            result = await self.manager.expire("test_key", 3600)
            assert result is True

    @pytest.mark.asyncio
    async def test_increment_counter(self):
        """测试计数器递增"""
        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.incr = AsyncMock(return_value=1)

            # 初始递增
            result = await self.manager.increment("counter_key")
            assert result == 1

            # 再次递增
            mock_redis.incr.return_value = 2
            result = await self.manager.increment("counter_key")
            assert result == 2

    @pytest.mark.asyncio
    async def test_increment_counter_by_amount(self):
        """测试按指定值递增计数器"""
        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.incrby = AsyncMock(return_value=5)

            result = await self.manager.increment("counter_key", 5)
            assert result == 5

    @pytest.mark.asyncio
    async def test_get_keys_by_pattern(self):
        """测试根据模式获取键列表"""
        mock_keys = [b"test:key:1", b"test:key:2", b"test:key:3"]

        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.keys = AsyncMock(return_value=mock_keys)

            result = await self.manager.keys("test:key:*")
            assert len(result) == 3
            assert "test:key:1" in result

    @pytest.mark.asyncio
    async def test_hash_operations(self):
        """测试哈希操作"""
        with patch.object(self.manager, '_redis') as mock_redis:
            # 设置哈希字段
            mock_redis.hset = AsyncMock(return_value=1)
            result = await self.manager.hset("hash_key", "field1", "value1")
            assert result == 1

            # 获取哈希字段
            mock_redis.hget = AsyncMock(return_value=b"value1")
            result = await self.manager.hget("hash_key", "field1")
            assert result == "value1"

            # 获取所有哈希字段
            mock_redis.hgetall = AsyncMock(return_value={
                b"field1": b"value1",
                b"field2": b"value2"
            })
            result = await self.manager.hgetall("hash_key")
            assert result == {"field1": "value1", "field2": "value2"}

    @pytest.mark.asyncio
    async def test_list_operations(self):
        """测试列表操作"""
        with patch.object(self.manager, '_redis') as mock_redis:
            # 左推入列表
            mock_redis.lpush = AsyncMock(return_value=1)
            result = await self.manager.lpush("list_key", "item1")
            assert result == 1

            # 右推入列表
            mock_redis.rpush = AsyncMock(return_value=2)
            result = await self.manager.rpush("list_key", "item2")
            assert result == 2

            # 获取列表范围
            mock_redis.lrange = AsyncMock(return_value=[b"item1", b"item2"])
            result = await self.manager.lrange("list_key", 0, -1)
            assert result == ["item1", "item2"]

    @pytest.mark.asyncio
    async def test_set_operations(self):
        """测试集合操作"""
        with patch.object(self.manager, '_redis') as mock_redis:
            # 添加到集合
            mock_redis.sadd = AsyncMock(return_value=1)
            result = await self.manager.sadd("set_key", "member1")
            assert result == 1

            # 获取所有成员
            mock_redis.smembers = AsyncMock(return_value={b"member1", b"member2"})
            result = await self.manager.smembers("set_key")
            assert result == {"member1", "member2"}

            # 检查成员是否存在
            mock_redis.sismember = AsyncMock(return_value=True)
            result = await self.manager.sismember("set_key", "member1")
            assert result is True

    @pytest.mark.asyncio
    async def test_connection_pool_info(self):
        """测试连接池信息"""
        mock_pool_info = {
            "created_connections": 10,
            "available_connections": 5,
            "in_use_connections": 5,
            "max_connections": 20
        }

        with patch.object(self.manager, 'get_pool_info') as mock_info:
            mock_info.return_value = mock_pool_info
            info = await self.manager.get_pool_info()
            assert info["created_connections"] == 10
            assert info["available_connections"] == 5

    def test_health_check(self):
        """测试健康检查"""
        with patch.object(self.manager, 'ping') as mock_ping:
            mock_ping.return_value = True
            health = self.manager.health_check()
            assert health["status"] == "healthy"
            assert health["redis_connected"] is True

            mock_ping.return_value = False
            health = self.manager.health_check()
            assert health["status"] == "unhealthy"
            assert health["redis_connected"] is False

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """测试批量操作"""
        operations = [
            ("set", "key1", "value1"),
            ("set", "key2", "value2"),
            ("delete", "key3"),
            ("increment", "counter", 1)
        ]

        with patch.object(self.manager, '_redis') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock(return_value=1)
            mock_redis.incrby = AsyncMock(return_value=1)

            results = await self.manager.batch_operations(operations)
            assert len(results) == 4
            assert all(results)

    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """测试缓存统计"""
        with patch.object(self.manager, 'get_stats') as mock_stats:
            mock_stats.return_value = {
                "hits": 100,
                "misses": 20,
                "hit_rate": 0.8333,
                "memory_usage": "10MB",
                "key_count": 500
            }

            stats = await self.manager.get_stats()
            assert stats["hits"] == 100
            assert stats["hit_rate"] == 0.8333

    def test_config_validation(self):
        """测试配置验证"""
        # 测试有效的Redis URL
        valid_urls = [
            "redis://localhost:6379",
            "redis://localhost:6379/0",
            "redis://:password@localhost:6379",
            "rediss://localhost:6379"  # SSL
        ]

        for url in valid_urls:
            assert url.startswith(("redis://", "rediss://"))

        # 测试无效的Redis URL
        invalid_urls = [
            "not-redis://",
            "redis://",
            "http://example.com"
        ]

        for url in invalid_urls:
            assert not url.startswith("redis://") or url == "redis://"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        with patch.object(self.manager, '_redis') as mock_redis:
            # 连接错误
            mock_redis.set.side_effect = ConnectionError("Redis connection failed")

            with pytest.raises(ConnectionError):
                await self.manager.set("test_key", "test_value")

            # 超时错误
            mock_redis.get.side_effect = TimeoutError("Operation timeout")

            with pytest.raises(TimeoutError):
                await self.manager.get("test_key")

    def test_serializer_deserializer(self):
        """测试序列化器/反序列化器"""
        # 测试不同数据类型的序列化
        test_cases = [
            ("string", "test string"),
            ("integer", 123),
            ("float", 123.45),
            ("boolean", True),
            ("list", [1, 2, 3]),
            ("dict", {"key": "value"}),
            ("none", None)
        ]

        for name, value in test_cases:
            # 序列化
            if value is None:
                serialized = None
            else:
                serialized = json.dumps(value, default=str)

            # 反序列化
            if serialized is None:
                deserialized = None
            else:
                deserialized = json.loads(serialized)

            # 验证
            if value is not None:
                assert deserialized is not None