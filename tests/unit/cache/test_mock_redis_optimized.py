from unittest.mock import Mock, patch

"""
Mock Redis 优化测试
Tests for Mock Redis (Optimized Version)

使用高性能Mock Redis测试缓存功能
"""

import asyncio
from datetime import datetime, timedelta

import pytest

# 导入优化的 mock
from tests.mocks.fast_mocks import FastRedisManager

# 测试导入
try:
    from src.cache.redis_manager import RedisManager

    REDIS_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    REDIS_MANAGER_AVAILABLE = False
    RedisManager = None


@pytest.fixture
def fast_redis():
    """快速 Redis 实例"""
    return FastRedisManager()


@pytest.fixture
def mock_redis_manager():
    """Mock Redis Manager"""
    if not REDIS_MANAGER_AVAILABLE:
        pytest.skip("Redis manager module not available")

    with patch("src.cache.redis_manager.RedisManager") as mock:
        redis_instance = FastRedisManager()
        mock.return_value = redis_instance
        yield redis_instance


@pytest.mark.skipif(
    not REDIS_MANAGER_AVAILABLE, reason="Redis manager module not available"
)
@pytest.mark.unit
class TestMockRedisOptimized:
    """Mock Redis 优化测试"""

    def test_basic_operations(self, fast_redis):
        """测试：基本操作"""
        # 测试 set/get
        assert fast_redis.set("key1", "value1") is True
        assert fast_redis.get("key1") == "value1"

        # 测试不存在的键
        assert fast_redis.get("nonexistent") is None

        # 测试 delete
        assert fast_redis.delete("key1") is True
        assert fast_redis.get("key1") is None

    def test_expiry_operations(self, fast_redis):
        """测试：过期时间操作"""
        # 设置带过期时间的键
        assert fast_redis.set("expire_key", "expire_value", ex=60) is True
        assert fast_redis.ttl("expire_key") == 60

        # 设置过期时间
        assert fast_redis.expire("expire_key", 120) is True
        assert fast_redis.ttl("expire_key") == 120

        # 不存在的键
        assert fast_redis.ttl("nonexistent") == -1

    def test_exists_operation(self, fast_redis):
        """测试：存在性检查"""
        # 初始状态
        assert fast_redis.exists("test_key") is False

        # 设置后
        fast_redis.set("test_key", "test_value")
        assert fast_redis.exists("test_key") is True

        # 删除后
        fast_redis.delete("test_key")
        assert fast_redis.exists("test_key") is False

    def test_increment_decrement(self, fast_redis):
        """测试：递增递减"""
        # 初始值为 0
        assert fast_redis.incr("counter") == 1
        assert fast_redis.incr("counter") == 2
        assert fast_redis.get("counter") == "2"

        # 递减
        assert fast_redis.decr("counter") == 1
        assert fast_redis.decr("counter") == 0
        assert fast_redis.get("counter") == "0"

    def test_hash_operations(self, fast_redis):
        """测试：哈希操作"""
        # 设置哈希字段
        assert fast_redis.hset("user:1", "name", "Alice") is True
        assert fast_redis.hset("user:1", "age", "30") is True

        # 获取所有哈希字段
        hash_data = fast_redis.hgetall("user:1")
        assert hash_data == {"name": "Alice", "age": "30"}

        # 不存在的哈希
        assert fast_redis.hgetall("nonexistent") == {}

    def test_sorted_set_operations(self, fast_redis):
        """测试：有序集合操作"""
        # 添加成员
        assert fast_redis.zadd("leaderboard", 100, "player1") == 1
        assert fast_redis.zadd("leaderboard", 200, "player2") == 1

        # 获取范围
        members = fast_redis.zrange("leaderboard", 0, -1)
        assert isinstance(members, list)

    def test_ping(self, fast_redis):
        """测试：Ping"""
        assert fast_redis.ping() is True

    def test_keys(self, fast_redis):
        """测试：获取键列表"""
        # 添加多个键
        fast_redis.set("test:1", "value1")
        fast_redis.set("test:2", "value2")
        fast_redis.set("other:1", "value3")

        # 获取所有键
        keys = fast_redis.keys("*")
        assert len(keys) == 3
        assert "test:1" in keys
        assert "test:2" in keys
        assert "other:1" in keys

    def test_flush_all(self, fast_redis):
        """测试：清空所有数据"""
        # 添加数据
        fast_redis.set("key1", "value1")
        fast_redis.set("key2", "value2")
        assert fast_redis.exists("key1") is True

        # 清空
        assert fast_redis.flushall() is True
        assert fast_redis.exists("key1") is False
        assert fast_redis.exists("key2") is False

    def test_performance_metrics(self, fast_redis):
        """测试：性能指标"""
        initial_count = fast_redis.operation_count

        # 执行一些操作
        fast_redis.set("perf_key", "perf_value")
        fast_redis.get("perf_key")
        fast_redis.delete("perf_key")

        # 验证操作计数
        assert fast_redis.operation_count == initial_count + 3

    def test_complex_data_types(self, fast_redis):
        """测试：复杂数据类型"""
        # JSON 数据
        import json

        json_data = {"name": "test", "values": [1, 2, 3]}
        fast_redis.set("json_key", json.dumps(json_data))
        retrieved = json.loads(fast_redis.get("json_key"))
        assert retrieved == json_data

        # 大文本
        large_text = "x" * 10000
        assert fast_redis.set("large_key", large_text) is True
        assert fast_redis.get("large_key") == large_text

    @pytest.mark.asyncio
    async def test_async_compatibility(self, fast_redis):
        """测试：异步兼容性"""
        # 模拟异步操作
        loop = asyncio.get_event_loop()

        # 在异步上下文中使用
        def sync_operation():
            fast_redis.set("async_key", "async_value")
            return fast_redis.get("async_key")

        _result = await loop.run_in_executor(None, sync_operation)
        assert _result == "async_value"


@pytest.mark.skipif(
    not REDIS_MANAGER_AVAILABLE, reason="Redis manager module not available"
)
class TestRedisManagerIntegration:
    """Redis Manager 集成测试"""

    def test_redis_manager_creation(self, mock_redis_manager):
        """测试：Redis Manager 创建"""
        assert mock_redis_manager is not None
        assert hasattr(mock_redis_manager, "get")
        assert hasattr(mock_redis_manager, "set")
        assert hasattr(mock_redis_manager, "delete")

    @pytest.mark.asyncio
    async def test_redis_cache_workflow(self, mock_redis_manager):
        """测试：Redis 缓存工作流"""
        # 模拟缓存工作流
        cache_key = "user:123:profile"
        cache_data = {"id": 123, "name": "Test User", "email": "test@example.com"}

        # 缓存数据
        import json

        mock_redis_manager.set(cache_key, json.dumps(cache_data), ex=3600)

        # 获取缓存
        cached = mock_redis_manager.get(cache_key)
        assert cached is not None

        # 解析数据
        _data = json.loads(cached)
        assert _data["id"] == 123
        assert _data["name"] == "Test User"

        # 删除缓存
        mock_redis_manager.delete(cache_key)
        assert mock_redis_manager.get(cache_key) is None

    def test_cache_invalidation(self, mock_redis_manager):
        """测试：缓存失效"""
        # 设置多个相关缓存
        mock_redis_manager.set("user:123:data", "data1")
        mock_redis_manager.set("user:123:profile", "profile1")
        mock_redis_manager.set("user:123:settings", "settings1")

        # 批量删除模式
        user_keys = mock_redis_manager.keys("user:123:*")
        assert len(user_keys) == 3

        # 删除所有用户相关缓存
        for key in user_keys:
            mock_redis_manager.delete(key)

        # 验证删除
        remaining_keys = mock_redis_manager.keys("user:123:*")
        assert len(remaining_keys) == 0
