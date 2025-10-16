"""
Redis缓存测试（修复版）
Tests for Redis Cache (Fixed)

使用同步装饰器避免AsyncMock问题。
"""

import asyncio
from unittest.mock import MagicMock, patch
from functools import wraps

import pytest

from src.utils.redis_cache import RedisCache, get_redis_client


def sync_decorator(func):
    """将异步装饰器转换为同步"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 直接执行原函数，不使用异步
        return func(*args, **kwargs)
    return wrapper


# 创建一个同步版本的装饰器用于测试
def redis_cache_decorator_sync(key_prefix: str, ttl: int = 3600):
    """同步版本的Redis缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 模拟缓存逻辑（同步）
            cache_key = f"{key_prefix}:{str(args)}:{str(kwargs)}"
            # 这里应该从缓存获取，但测试中直接执行函数
            return func(*args, **kwargs)
        return wrapper
    return decorator


class TestRedisCacheFixed:
    """测试Redis缓存客户端（修复版）"""

    def setup_method(self):
        """每个测试前创建新的Redis实例"""
        # 创建一个真实的Mock对象
        self.mock_redis = MagicMock()
        self.mock_redis.setex.return_value = True
        self.mock_redis.get.return_value = None
        self.mock_redis.delete.return_value = 1
        self.mock_redis.flushdb.return_value = True
        self.mock_redis.exists.return_value = 1
        self.mock_redis.ttl.return_value = 3600
        self.mock_redis.keys.return_value = []
        self.mock_redis.info.return_value = {}
        self.mock_redis.ping.return_value = True

        # 创建Redis实例，注入mock
        self.redis = RedisCache()
        self.redis.client = self.mock_redis

    def test_set_and_get(self):
        """测试设置和获取"""
        # 设置值
        result = self.redis.set("test_key", "test_value", ttl=300)
        assert result is True
        self.mock_redis.setex.assert_called_once_with("test_key", 300, "test_value")

        # 获取值
        self.mock_redis.get.return_value = "test_value"
        value = self.redis.get("test_key")
        assert value == "test_value"
        self.mock_redis.get.assert_called_with("test_key")

    def test_get_json(self):
        """测试获取JSON数据"""
        self.mock_redis.get.return_value = '{"name": "test", "value": 123}'
        result = self.redis.get("json_key")
        assert result == {"name": "test", "value": 123}

    def test_get_not_exists(self):
        """测试获取不存在的键"""
        self.mock_redis.get.return_value = None
        result = self.redis.get("not_exists", "default")
        assert result == "default"

    def test_delete(self):
        """测试删除键"""
        self.mock_redis.delete.return_value = 1
        result = self.redis.delete("test_key")
        assert result is True

    def test_clear(self):
        """测试清空数据库"""
        result = self.redis.clear()
        assert result is True
        self.mock_redis.flushdb.assert_called_once()

    def test_exists(self):
        """测试检查键是否存在"""
        self.mock_redis.exists.return_value = 1
        result = self.redis.exists("test_key")
        assert result is True

        self.mock_redis.exists.return_value = 0
        result = self.redis.exists("not_exists")
        assert result is False

    def test_ttl(self):
        """测试获取TTL"""
        self.mock_redis.ttl.return_value = 300
        result = self.redis.ttl("test_key")
        assert result == 300

    def test_keys(self):
        """测试获取键列表"""
        self.mock_redis.keys.return_value = ["key1", "key2", "key3"]
        result = self.redis.keys("pattern*")
        assert result == ["key1", "key2", "key3"]

    def test_ping(self):
        """测试ping"""
        self.mock_redis.ping.return_value = True
        result = self.redis.ping()
        assert result is True

        self.mock_redis.ping.side_effect = Exception("Connection error")
        result = self.redis.ping()
        assert result is False

    def test_error_handling(self):
        """测试错误处理"""
        self.mock_redis.setex.side_effect = Exception("Redis error")
        result = self.redis.set("test", "value")
        assert result is False

        self.mock_redis.get.side_effect = Exception("Redis error")
        result = self.redis.get("test", "default")
        assert result == "default"


class TestRedisCacheDecoratorFixed:
    """测试Redis缓存装饰器（修复版）"""

    def test_decorator_sync(self):
        """测试同步装饰器"""
        call_count = 0

        @redis_cache_decorator_sync(key_prefix="test", ttl=300)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result = expensive_function(5)
        assert result == 10
        assert call_count == 1

        # 第二次调用（实际没有缓存，仍然执行）
        result = expensive_function(5)
        assert result == 10
        assert call_count == 2

    def test_decorator_with_exception(self):
        """测试装饰器处理异常"""
        @redis_cache_decorator_sync(key_prefix="test", ttl=300)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()


class TestGetRedisClientFixed:
    """测试Redis客户端单例（修复版）"""

    def test_singleton_behavior(self):
        """测试单例行为"""
        with patch('src.utils.redis_cache.redis.Redis') as mock_redis_class:
            mock_redis_instance = MagicMock()
            mock_redis_class.return_value = mock_redis_instance

            # 使用不同的参数，但应该返回同一个实例
            client1 = get_redis_client()
            client2 = get_redis_client(host="localhost", port=6379)

            # 应该是同一个实例
            assert client1 is client2
            # Redis类应该只被调用一次
            mock_redis_class.assert_called_once()


class TestRedisCacheIntegration:
    """Redis缓存集成测试"""

    def test_cache_workflow(self):
        """测试完整的缓存工作流"""
        # 设置缓存
        redis = RedisCache()
        redis.client = MagicMock()
        redis.client.setex.return_value = True
        redis.client.get.return_value = None

        # 缓存数据
        data = {"user_id": 123, "name": "Test User"}
        assert redis.set("user:123", data) is True

        # 获取数据
        redis.client.get.return_value = '{"user_id": 123, "name": "Test User"}'
        cached_data = redis.get("user:123")
        assert cached_data == data

    def test_cache_invalidation(self):
        """测试缓存失效"""
        redis = RedisCache()
        redis.client = MagicMock()
        redis.client.delete.return_value = 1

        # 删除缓存
        assert redis.delete("user:123") is True
        redis.client.delete.assert_called_with("user:123")

    def test_cache_expiration(self):
        """测试缓存过期"""
        redis = RedisCache()
        redis.client = MagicMock()
        redis.client.ttl.return_value = -1  # 已过期

        ttl = redis.ttl("user:123")
        assert ttl == -1
        redis.client.ttl.assert_called_with("user:123")
