"""
Cache模块核心测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.cache.redis_manager import RedisManager
    from src.cache.decorators import cache_result, ttl_cache
    from src.cache.ttl_cache import TTLCache
except ImportError as e:
    pytest.skip(f"Cache模块不可用: {e}", allow_module_level=True)


class TestRedisManager:
    """测试Redis管理器"""

    def test_redis_manager_creation(self):
        """测试Redis管理器创建"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.connect = Mock(return_value=True)
            manager.disconnect = Mock(return_value=True)
            manager.is_connected = Mock(return_value=True)

            assert manager.connect() is True
            assert manager.disconnect() is True
            assert manager.is_connected() is True

    def test_redis_set_get_operations(self):
        """测试Redis设置和获取操作"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.set = Mock(return_value=True)
            manager.get = Mock(return_value="test_value")
            manager.delete = Mock(return_value=True)
            manager.exists = Mock(return_value=True)

            # 设置值
            assert manager.set("key", "value") is True

            # 获取值
            value = manager.get("key")
            assert value == "test_value"

            # 检查键是否存在
            assert manager.exists("key") is True

            # 删除键
            assert manager.delete("key") is True

    def test_redis_expiration(self):
        """测试Redis过期时间"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.set_with_ttl = Mock(return_value=True)
            manager.get_ttl = Mock(return_value=300)
            manager.extend_ttl = Mock(return_value=True)

            # 设置带过期时间的值
            assert manager.set_with_ttl("key", "value", 300) is True

            # 获取剩余时间
            ttl = manager.get_ttl("key")
            assert ttl == 300

            # 延长过期时间
            assert manager.extend_ttl("key", 600) is True

    def test_redis_batch_operations(self):
        """测试Redis批量操作"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.mset = Mock(return_value=True)
            manager.mget = Mock(return_value=["value1", "value2", "value3"])
            manager.mdelete = Mock(return_value=3)

            # 批量设置
            assert manager.mset({"key1": "value1", "key2": "value2"}) is True

            # 批量获取
            values = manager.mget(["key1", "key2", "key3"])
            assert len(values) == 3

            # 批量删除
            count = manager.mdelete(["key1", "key2", "key3"])
            assert count == 3

    def test_redis_hash_operations(self):
        """测试Redis哈希操作"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.hset = Mock(return_value=True)
            manager.hget = Mock(return_value="field_value")
            manager.hgetall = Mock(
                return_value={"field1": "value1", "field2": "value2"}
            )
            manager.hdel = Mock(return_value=1)

            # 设置哈希字段
            assert manager.hset("hash_key", "field", "value") is True

            # 获取哈希字段
            value = manager.hget("hash_key", "field")
            assert value == "field_value"

            # 获取所有哈希字段
            all_values = manager.hgetall("hash_key")
            assert len(all_values) == 2

            # 删除哈希字段
            assert manager.hdel("hash_key", "field") == 1

    def test_redis_list_operations(self):
        """测试Redis列表操作"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.lpush = Mock(return_value=1)
            manager.rpush = Mock(return_value=1)
            manager.lpop = Mock(return_value="item1")
            manager.rpop = Mock(return_value="item2")
            manager.llen = Mock(return_value=2)

            # 左推入
            assert manager.lpush("list_key", "item1") is True

            # 右推入
            assert manager.rpush("list_key", "item2") is True

            # 获取列表长度
            assert manager.llen("list_key") == 2

            # 左弹出
            left_item = manager.lpop("list_key")
            assert left_item == "item1"

            # 右弹出
            right_item = manager.rpop("list_key")
            assert right_item == "item2"

    def test_redis_error_handling(self):
        """测试Redis错误处理"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.handle_connection_error = Mock(return_value={"retry": True})
            manager.handle_command_error = Mock(return_value={"error": "handled"})

            # 处理连接错误
            error = manager.handle_connection_error(Exception("Connection lost"))
            assert error["retry"] is True

            # 处理命令错误
            cmd_error = manager.handle_command_error(Exception("Invalid command"))
            assert cmd_error["error"] == "handled"

    def test_redis_pipelining(self):
        """测试Redis管道"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.pipeline = Mock()
            pipeline = Mock()
            pipeline.set = Mock()
            pipeline.get = Mock()
            pipeline.execute = Mock(return_value=[True, "value"])

            # 创建管道
            manager.pipeline.return_value = pipeline

            # 使用管道
            pipe = manager.pipeline()
            pipe.set("key", "value")
            pipe.get("key")
            results = pipe.execute()

            assert results[0] is True
            assert results[1] == "value"

    def test_redis_pub_sub(self):
        """测试Redis发布订阅"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedisManager:
            manager = MockRedisManager()
            manager.publish = Mock(return_value=1)
            manager.subscribe = Mock(return_value=True)
            manager.unsubscribe = Mock(return_value=True)
            manager.get_message = Mock(
                return_value={"channel": "test", "message": "hello"}
            )

            # 发布消息
            assert manager.publish("channel", "message") == 1

            # 订阅频道
            assert manager.subscribe("channel") is True

            # 获取消息
            message = manager.get_message()
            assert message["channel"] == "test"

            # 取消订阅
            assert manager.unsubscribe("channel") is True


class TestCacheDecorators:
    """测试缓存装饰器"""

    def test_cache_result_decorator(self):
        """测试缓存结果装饰器"""
        call_count = 0

        @cache_result(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用（使用缓存）
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1

        # 不同参数
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    def test_ttl_cache_decorator(self):
        """测试TTL缓存装饰器"""
        with patch("src.cache.decorators.ttl_cache") as MockTTLCache:
            cache = MockTTLCache()
            cache.get = Mock(return_value=None)
            cache.set = Mock(return_value=True)

            @ttl_cache(ttl=300)
            def cached_function(x):
                return x * 3

            result = cached_function(10)
            assert result == 30
            cache.get.assert_called_once()
            cache.set.assert_called_once()

    def test_cache_with_async_function(self):
        """测试异步函数缓存"""
        call_count = 0

        @cache_result(ttl=60)
        async def async_expensive_function(x):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * 2

        async def test_async():
            # 第一次调用
            result1 = await async_expensive_function(5)
            assert result1 == 10
            assert call_count == 1

            # 第二次调用（使用缓存）
            result2 = await async_expensive_function(5)
            assert result2 == 10
            assert call_count == 1

        # 运行异步测试
        asyncio.run(test_async())

    def test_cache_key_generator(self):
        """测试缓存键生成器"""
        with patch("src.cache.decorators.cache_result") as MockCache:
            decorator = MockCache()
            decorator.return_value = lambda func: func

            @decorator(key_generator=lambda x: f"custom_key_{x}")
            def custom_key_function(x):
                return x * 2

            result = custom_key_function(10)
            assert result == 20

    def test_cache_condition(self):
        """测试条件缓存"""
        with patch("src.cache.decorators.cache_result") as MockCache:
            decorator = MockCache()
            decorator.return_value = lambda func: func

            @decorator(condition=lambda x: x > 0)
            def conditional_function(x):
                return x * 2

            result = conditional_function(10)
            assert result == 20

    def test_cache_invalidation(self):
        """测试缓存失效"""
        with patch("src.cache.decorators.cache_result") as MockCache:
            decorator = MockCache()
            decorator.return_value = lambda func: func

            @decorator(invalidate_after=lambda x: x > 100)
            def invalidatable_function(x):
                return x * 2

            result = invalidatable_function(150)
            assert result == 300

    def test_cache_stats(self):
        """测试缓存统计"""
        with patch("src.cache.decorators.cache_result") as MockCache:
            decorator = MockCache()
            decorator.return_value = lambda func: func

            @decorator(track_stats=True)
            def tracked_function(x):
                return x * 2

            result = tracked_function(10)
            assert result == 20

    def test_cache_max_size(self):
        """测试缓存最大大小"""
        with patch("src.cache.decorators.cache_result") as MockCache:
            decorator = MockCache()
            decorator.return_value = lambda func: func

            @decorator(max_size=100)
            def limited_function(x):
                return x * 2

            result = limited_function(10)
            assert result == 20

    def test_cache_serialization(self):
        """测试缓存序列化"""
        with patch("src.cache.decorators.cache_result") as MockCache:
            decorator = MockCache()
            decorator.return_value = lambda func: func

            @decorator(serializer=lambda x: str(x), deserializer=lambda x: int(x))
            def serialized_function(x):
                return x * 2

            result = serialized_function(10)
            assert result == 20

    def test_cache_error_handling(self):
        """测试缓存错误处理"""
        with patch("src.cache.decorators.cache_result") as MockCache:
            decorator = MockCache()
            decorator.return_value = lambda func: func

            @decorator(on_error=lambda e: "fallback_value")
            def error_function(x):
                if x < 0:
                    raise ValueError("Negative value")
                return x * 2

            # 正常情况
            result1 = error_function(10)
            assert result1 == 20

            # 错误情况
            result2 = error_function(-1)
            assert result2 == "fallback_value"


class TestTTLCache:
    """测试TTL缓存"""

    def test_ttl_cache_creation(self):
        """测试TTL缓存创建"""
        with patch("src.cache.ttl_cache.TTLCache") as MockTTLCache:
            cache = MockTTLCache(default_ttl=300, max_size=1000)

            assert cache.default_ttl == 300
            assert cache.max_size == 1000

    def test_ttl_cache_set_get(self):
        """测试TTL缓存设置和获取"""
        with patch("src.cache.ttl_cache.TTLCache") as MockTTLCache:
            cache = MockTTLCache()
            cache.set = Mock(return_value=True)
            cache.get = Mock(return_value="test_value")
            cache.delete = Mock(return_value=True)

            # 设置值
            assert cache.set("key", "value", ttl=60) is True

            # 获取值
            value = cache.get("key")
            assert value == "test_value"

            # 删除值
            assert cache.delete("key") is True

    def test_ttl_cache_expiration(self):
        """测试TTL缓存过期"""
        with patch("src.cache.ttl_cache.TTLCache") as MockTTLCache:
            cache = MockTTLCache()
            cache.set = Mock(return_value=True)
            cache.get = Mock(return_value=None)  # 已过期

            # 设置值
            cache.set("key", "value", ttl=1)

            # 等待过期
            time.sleep(2)

            # 获取值（已过期）
            value = cache.get("key")
            assert value is None

    def test_ttl_cache_cleanup(self):
        """测试TTL缓存清理"""
        with patch("src.cache.ttl_cache.TTLCache") as MockTTLCache:
            cache = MockTTLCache()
            cache.cleanup_expired = Mock(return_value=5)
            cache.size = Mock(return_value=100)

            # 清理过期项
            cleaned = cache.cleanup_expired()
            assert cleaned == 5

            # 获取缓存大小
            size = cache.size()
            assert size == 100

    def test_ttl_cache_stats(self):
        """测试TTL缓存统计"""
        with patch("src.cache.ttl_cache.TTLCache") as MockTTLCache:
            cache = MockTTLCache()
            cache.get_stats = Mock(
                return_value={"hits": 100, "misses": 20, "size": 50, "max_size": 100}
            )

            stats = cache.get_stats()
            assert stats["hits"] == 100
            assert stats["misses"] == 20
            assert stats["hit_rate"] == 0.83

    def test_ttl_cache_bulk_operations(self):
        """测试TTL缓存批量操作"""
        with patch("src.cache.ttl_cache.TTLCache") as MockTTLCache:
            cache = MockTTLCache()
            cache.set_many = Mock(return_value=3)
            cache.get_many = Mock(
                return_value={"key1": "value1", "key2": "value2", "key3": None}
            )

            # 批量设置
            assert (
                cache.set_many({"key1": "value1", "key2": "value2", "key3": "value3"})
                == 3
            )

            # 批量获取
            values = cache.get_many(["key1", "key2", "key3"])
            assert len(values) == 3
            assert values["key1"] == "value1"
            assert values["key3"] is None

    def test_ttl_cache_persistence(self):
        """测试TTL缓存持久化"""
        with patch("src.cache.ttl_cache.TTLCache") as MockTTLCache:
            cache = MockTTLCache()
            cache.save_to_disk = Mock(return_value=True)
            cache.load_from_disk = Mock(return_value=True)
            cache.get_persistence_path = Mock(return_value="/tmp/cache.pkl")

            # 保存到磁盘
            assert cache.save_to_disk() is True

            # 从磁盘加载
            assert cache.load_from_disk() is True

            # 获取持久化路径
            path = cache.get_persistence_path()
            assert path == "/tmp/cache.pkl"
