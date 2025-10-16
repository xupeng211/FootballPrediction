"""
Redis缓存测试（Mock版）
Tests for Redis Cache (Mocked)

使用Mock对象测试Redis缓存客户端功能，避免实际的Redis依赖。
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.utils.redis_cache import RedisCache, get_redis_client, redis_cache_decorator


class TestRedisCache:
    """测试Redis缓存客户端"""

    def setup_method(self):
        """每个测试前创建新的Redis实例"""
        # 创建完全模拟的redis.Redis实例
        self.mock_redis_instance = Mock()
        self.mock_redis_instance.setex.return_value = True
        self.mock_redis_instance.get.return_value = None
        self.mock_redis_instance.delete.return_value = 1
        self.mock_redis_instance.flushdb.return_value = True
        self.mock_redis_instance.exists.return_value = 1
        self.mock_redis_instance.ttl.return_value = 3600
        self.mock_redis_instance.keys.return_value = []
        self.mock_redis_instance.info.return_value = {}
        self.mock_redis_instance.ping.return_value = True

        # Mock redis.Redis类
        self.redis_patcher = patch('src.utils.redis_cache.redis.Redis',
                                  return_value=self.mock_redis_instance)
        self.redis_patcher.start()

        self.redis = RedisCache()

    def teardown_method(self):
        """每个测试后清理"""
        self.redis_patcher.stop()

    def test_init_default_values(self):
        """测试使用默认值初始化"""
        assert self.redis.client == self.mock_redis_instance
        assert self.redis.default_ttl == 3600

        # 验证redis.Redis被正确调用
        self.redis_patcher.stop()
        with patch('src.utils.redis_cache.redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_class.return_value = mock_redis_instance
            redis = RedisCache()

            mock_redis_class.assert_called_once_with(
                host="localhost",
                port=6379,
                db=0,
                password=None,
                decode_responses=True
            )
            assert redis.client == mock_redis_instance
        self.redis_patcher.start()

    def test_init_custom_values(self):
        """测试使用自定义值初始化"""
        self.redis_patcher.stop()
        with patch('src.utils.redis_cache.redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_class.return_value = mock_redis_instance

            redis = RedisCache(
                host="test-host",
                port=6380,
                db=1,
                password="secret",
                decode_responses=False,
                socket_timeout=5
            )

            mock_redis_class.assert_called_once_with(
                host="test-host",
                port=6380,
                db=1,
                password="secret",
                decode_responses=False,
                socket_timeout=5
            )
            assert redis.client == mock_redis_instance
        self.redis_patcher.start()

    def test_set_string_value(self):
        """测试设置字符串值"""
        self.mock_redis_instance.setex.return_value = True

        result = self.redis.set("test_key", "test_value", ttl=300)

        assert result is True
        self.mock_redis_instance.setex.assert_called_once_with("test_key", 300, "test_value")

    def test_set_numeric_value(self):
        """测试设置数字值"""
        self.mock_redis_instance.setex.return_value = True

        result = self.redis.set("number_key", 123, ttl=600)

        assert result is True
        self.mock_redis_instance.setex.assert_called_once_with("number_key", 600, 123)

    def test_set_dict_value(self):
        """测试设置字典值（自动序列化）"""
        self.mock_redis_instance.setex.return_value = True
        data = {"name": "test", "count": 10}

        result = self.redis.set("dict_key", data)

        assert result is True
        # 验证JSON序列化
        call_args = self.mock_redis_instance.setex.call_args
        assert call_args[0][0] == "dict_key"
        assert call_args[0][1] == self.redis.default_ttl
        assert json.loads(call_args[0][2]) == data

    def test_set_with_default_ttl(self):
        """测试使用默认TTL"""
        self.mock_redis_instance.setex.return_value = True

        result = self.redis.set("key", "value")

        assert result is True
        call_args = self.mock_redis_instance.setex.call_args
        assert call_args[0][1] == 3600  # 默认TTL

    def test_set_with_exception(self):
        """测试设置时出现异常"""
        self.mock_redis_instance.setex.side_effect = Exception("Redis error")

        result = self.redis.set("key", "value")

        assert result is False

    def test_get_existing_string_value(self):
        """测试获取存在的字符串值"""
        self.mock_redis_instance.get.return_value = "test_value"
        result = self.redis.get("test_key")
        assert result == "test_value"

    def test_get_existing_numeric_value(self):
        """测试获取存在的数字值（自动转换）"""
        self.mock_redis_instance.get.return_value = "123"
        result = self.redis.get("number_key")
        assert result == 123

    def test_get_existing_float_value(self):
        """测试获取浮点数值（自动转换）"""
        self.mock_redis_instance.get.return_value = "123.45"
        result = self.redis.get("float_key")
        assert result == 123.45

    def test_get_json_value(self):
        """测试获取JSON值（自动反序列化）"""
        self.mock_redis_instance.get.return_value = '{"name": "test", "count": 10}'

        result = self.redis.get("json_key")

        assert result == {"name": "test", "count": 10}

    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        self.mock_redis_instance.get.return_value = None

        result = self.redis.get("nonexistent", default="default")

        assert result == "default"

    def test_get_with_exception(self):
        """测试获取时出现异常"""
        self.mock_redis_instance.get.side_effect = Exception("Redis error")

        result = self.redis.get("key", default="default")

        assert result == "default"

    def test_delete_existing_key(self):
        """测试删除存在的键"""
        self.mock_redis_instance.delete.return_value = 1

        result = self.redis.delete("test_key")

        assert result is True

    def test_delete_nonexistent_key(self):
        """测试删除不存在的键"""
        self.mock_redis_instance.delete.return_value = 0

        result = self.redis.delete("nonexistent")

        assert result is False

    def test_delete_with_exception(self):
        """测试删除时出现异常"""
        self.mock_redis_instance.delete.side_effect = Exception("Redis error")

        result = self.redis.delete("key")

        assert result is False

    def test_clear_database(self):
        """测试清空数据库"""
        self.mock_redis_instance.flushdb.return_value = True

        result = self.redis.clear()

        assert result is True
        self.mock_redis_instance.flushdb.assert_called_once()

    def test_clear_with_exception(self):
        """测试清空时出现异常"""
        self.mock_redis_instance.flushdb.side_effect = Exception("Redis error")

        result = self.redis.clear()

        assert result is False

    def test_exists_true(self):
        """测试检查存在的键"""
        self.mock_redis_instance.exists.return_value = 1

        result = self.redis.exists("test_key")

        assert result is True

    def test_exists_false(self):
        """测试检查不存在的键"""
        self.mock_redis_instance.exists.return_value = 0

        result = self.redis.exists("nonexistent")

        assert result is False

    def test_exists_with_exception(self):
        """测试检查时出现异常"""
        self.mock_redis_instance.exists.side_effect = Exception("Redis error")

        result = self.redis.exists("key")

        assert result is False

    def test_ttl_existing_key(self):
        """测试获取键的TTL"""
        self.mock_redis_instance.ttl.return_value = 300

        result = self.redis.ttl("test_key")

        assert result == 300

    def test_ttl_no_key(self):
        """测试不存在键的TTL"""
        self.mock_redis_instance.ttl.return_value = -1

        result = self.redis.ttl("nonexistent")

        assert result == -1

    def test_ttl_with_exception(self):
        """测试获取TTL时出现异常"""
        self.mock_redis_instance.ttl.side_effect = Exception("Redis error")

        result = self.redis.ttl("key")

        assert result == -1

    def test_keys_with_pattern(self):
        """测试获取匹配模式的键"""
        self.mock_redis_instance.keys.return_value = ["key1", "key2", "key3"]

        result = self.redis.keys("test:*")

        assert result == ["key1", "key2", "key3"]
        self.mock_redis_instance.keys.assert_called_once_with("test:*")

    def test_keys_all(self):
        """测试获取所有键"""
        self.mock_redis_instance.keys.return_value = ["all_keys"]

        result = self.redis.keys()

        assert result == ["all_keys"]
        self.mock_redis_instance.keys.assert_called_once_with("*")

    def test_keys_with_exception(self):
        """测试获取键时出现异常"""
        self.mock_redis_instance.keys.side_effect = Exception("Redis error")

        result = self.redis.keys("pattern")

        assert result == []

    def test_info_success(self):
        """测试获取Redis信息"""
        mock_info = {
            "redis_version": "6.2.0",
            "used_memory": "1024000",
            "connected_clients": 10
        }
        self.mock_redis_instance.info.return_value = mock_info

        result = self.redis.info()

        assert result == mock_info

    def test_info_with_exception(self):
        """测试获取信息时出现异常"""
        self.mock_redis_instance.info.side_effect = Exception("Redis error")

        result = self.redis.info()

        assert result == {}

    def test_ping_success(self):
        """测试Redis连接测试"""
        self.mock_redis_instance.ping.return_value = True

        result = self.redis.ping()

        assert result is True

    def test_ping_failure(self):
        """测试Redis连接测试失败"""
        self.mock_redis_instance.ping.side_effect = Exception("Connection error")

        result = self.redis.ping()

        assert result is False


class TestRedisCacheDecorator:
    """测试Redis缓存装饰器"""

    def test_decorator_cache_miss(self):
        """测试缓存未命中"""
        with patch('src.utils.redis_cache.get_redis_client') as mock_get_client:
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True
            mock_get_client.return_value = mock_redis

            @redis_cache_decorator(key_prefix="test", ttl=300)
            def expensive_function(x):
                return x * 2

            # 第一次调用
            result1 = expensive_function(5)
            assert result1 == 10

            # 验证缓存操作
            mock_redis.ping.assert_called()
            mock_redis.get.assert_called()
            mock_redis.set.assert_called()

    def test_decorator_cache_hit(self):
        """测试缓存命中"""
        with patch('src.utils.redis_cache.get_redis_client') as mock_get_client:
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = 20  # 缓存命中
            mock_get_client.return_value = mock_redis

            @redis_cache_decorator(key_prefix="test", ttl=300)
            def expensive_function(x):
                return x * 2

            result = expensive_function(10)
            assert result == 20

            # 缓存命中，不应该设置
            mock_redis.set.assert_not_called()

    def test_decorator_redis_unavailable(self):
        """测试Redis不可用时直接执行"""
        with patch('src.utils.redis_cache.get_redis_client') as mock_get_client:
            mock_redis = Mock()
            mock_redis.ping.return_value = False
            mock_get_client.return_value = mock_redis

            call_count = 0

            @redis_cache_decorator(key_prefix="test", ttl=300)
            def test_function():
                nonlocal call_count
                call_count += 1
                return "result"

            result = test_function()
            assert result == "result"
            assert call_count == 1


class TestGetRedisClient:
    """测试Redis客户端单例"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        with patch('src.utils.redis_cache.redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_class.return_value = mock_redis_instance

            client1 = get_redis_client()
            client2 = get_redis_client()

            assert client1 is client2
            assert client1.client is mock_redis_instance
            mock_redis_class.assert_called_once()

    def test_multiple_calls_return_same_instance(self):
        """测试多次调用返回同一实例"""
        with patch('src.utils.redis_cache.redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_class.return_value = mock_redis_instance

            client1 = get_redis_client(host="test1")
            client2 = get_redis_client(host="test2")

            assert client1 is client2
            assert client1.client is mock_redis_instance


class TestRedisCacheIntegration:
    """Redis缓存集成测试"""

    def test_set_get_cycle(self):
        """测试完整的设置-获取循环"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 设置值
            result_set = redis.set("cycle_test", {"test": "data"})
            assert result_set is True

            # 模拟Redis返回存储的值
            mock_redis.get.return_value = '{"test": "data"}'

            # 获取值
            result_get = redis.get("cycle_test")
            assert result_get == {"test": "data"}

    def test_json_serialization_cycle(self):
        """测试JSON序列化/反序列化循环"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 测试复杂数据结构
            complex_data = {
                "string": "test",
                "number": 42,
                "boolean": True,
                "null": None,
                "list": [1, 2, 3],
                "nested": {
                    "inner": "value",
                    "array": [4, 5, 6]
                }
            }

            # 设置
            result_set = redis.set("complex", complex_data)
            assert result_set is True

            # 验证序列化
            call_args = mock_redis.setex.call_args
            serialized = json.loads(call_args[0][2])
            assert serialized == complex_data

            # 获取
            mock_redis.get.return_value = json.dumps(complex_data)
            result_get = redis.get("complex")
            assert result_get == complex_data

    def test_error_recovery_mechanism(self):
        """测试错误恢复机制"""
        mock_redis = Mock()

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 模拟连接失败
            mock_redis.setex.side_effect = [Exception("Connection lost"), True]

            # 第一次尝试失败
            result1 = redis.set("test", "value")
            assert result1 is False

            # 第二次成功
            result2 = redis.set("test", "value")
            assert result2 is True

    def test_ttl_management(self):
        """测试TTL管理"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache(default_ttl=1800)  # 30分钟

            # 使用默认TTL
            redis.set("default_ttl", "value")
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 1800

            # 使用自定义TTL
            redis.set("custom_ttl", "value", ttl=600)
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 600

    def test_large_data_handling(self):
        """测试大数据处理"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 创建大数据（模拟）
            large_data = {
                "items": [{"id": i, "data": f"data_{i}"} for i in range(100)],
                "metadata": {"total": 100, "page": 1}
            }

            # 测试设置大数据
            result = redis.set("large_data", large_data)
            assert result is True

            # 验证大数据能正确序列化
            call_args = mock_redis.setex.call_args
            serialized = json.loads(call_args[0][2])
            assert len(serialized["items"]) == 100

    def test_boolean_values(self):
        """测试布尔值处理"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 设置布尔值
            redis.set("bool_true", True)
            redis.set("bool_false", False)

            # 获取布尔值
            mock_redis.get.side_effect = ["True", "False"]
            assert redis.get("bool_true") is True
            assert redis.get("bool_false") is False

    def test_none_values(self):
        """测试None值处理"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 设置None值
            result = redis.set("none_value", None)
            assert result is True

            # None会被序列化为"null"
            call_args = mock_redis.setex.call_args
            assert call_args[0][2] is None

    def test_special_characters(self):
        """测试特殊字符处理"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 测试特殊字符
            special_data = {
                "unicode": "测试中文",
                "emoji": "🚀🔥💯",
                "symbols": "$€¥£¢",
                "quotes": '"single" and \'double\'',
                "whitespace": "  \t\n\r  "
            }

            result = redis.set("special", special_data)
            assert result is True

            # 验证序列化
            call_args = mock_redis.setex.call_args
            serialized = json.loads(call_args[0][2])
            assert serialized == special_data

    def test_decorator_with_complex_args(self):
        """测试装饰器处理复杂参数"""
        with patch('src.utils.redis_cache.get_redis_client') as mock_get_client:
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True
            mock_get_client.return_value = mock_redis

            @redis_cache_decorator(key_prefix="complex", ttl=300)
            def complex_function(a, b=10, *args, **kwargs):
                return a + b + sum(args) + sum(kwargs.values())

            # 调用函数
            result = complex_function(1, 2, 3, 4, x=5, y=6)
            assert result == 21

            # 验证缓存键生成
            mock_redis.get.assert_called()
            mock_redis.set.assert_called()

    def test_decorator_function_with_exception(self):
        """测试装饰器函数抛出异常"""
        with patch('src.utils.redis_cache.get_redis_client') as mock_get_client:
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis.get.return_value = None
            mock_get_client.return_value = mock_redis

            @redis_cache_decorator(key_prefix="error", ttl=300)
            def error_function():
                raise ValueError("Test error")

            # 异常应该传播，不应该被缓存
            with pytest.raises(ValueError):
                error_function()

            # 不应该设置缓存
            mock_redis.set.assert_not_called()


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_string_key(self):
        """测试空字符串键"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = "value"

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            result = redis.set("", "value")
            assert result is True

            result = redis.get("")
            assert result == "value"

    def test_very_long_key(self):
        """测试非常长的键"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = "value"

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            long_key = "x" * 1000
            result = redis.set(long_key, "value")
            assert result is True

            result = redis.get(long_key)
            assert result == "value"

    def test_zero_ttl(self):
        """测试零TTL"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            result = redis.set("key", "value", ttl=0)
            assert result is True

            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 0

    def test_negative_ttl(self):
        """测试负数TTL"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            result = redis.set("key", "value", ttl=-1)
            assert result is True

            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == -1

    def test_invalid_json_deserialization(self):
        """测试无效JSON反序列化"""
        mock_redis = Mock()
        mock_redis.get.return_value = "invalid json string"

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 应该返回原始字符串，而不是抛出异常
            result = redis.get("invalid_json")
            assert result == "invalid json string"

    def test_concurrent_operations(self):
        """测试并发操作（模拟）"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = "value1"
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = 1

        with patch('src.utils.redis_cache.redis.Redis', return_value=mock_redis):
            redis = RedisCache()

            # 模拟多个操作
            operations = [
                ("set", ("key1", "value1", 3600)),
                ("set", ("key2", "value2", 7200)),
                ("get", ("key1",)),
                ("delete", ("key3",)),
                ("exists", ("key2",))
            ]

            results = []
            for op, args in operations:
                if op == "set":
                    results.append(redis.set(*args))
                elif op == "get":
                    results.append(redis.get(*args))
                elif op == "delete":
                    results.append(redis.delete(*args))
                elif op == "exists":
                    results.append(redis.exists(*args))

            assert results == [True, True, "value1", True, True]
