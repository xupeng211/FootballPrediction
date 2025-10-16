"""
Redis缓存测试（简化版）
Tests for Redis Cache (Simple)

直接使用真实的Redis连接池对象，避免Mock问题。
"""

import pytest
from unittest.mock import MagicMock, patch
from unittest.mock import AsyncMock

from src.utils.redis_cache import RedisCache, get_redis_client, redis_cache_decorator


class TestRedisCacheSimple:
    """测试Redis缓存客户端（简化版）"""

    def setup_method(self):
        """每个测试前创建新的Redis实例"""
        # 创建一个真实的Mock对象，不是AsyncMock
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

    def test_init(self):
        """测试初始化"""
        assert self.redis.client is not None
        assert self.redis.default_ttl == 3600

    def test_set_string(self):
        """测试设置字符串"""
        result = self.redis.set("test", "value", ttl=300)
        assert result is True
        self.mock_redis.setex.assert_called_once_with("test", 300, "value")

    def test_set_dict(self):
        """测试设置字典"""
        data = {"key": "value"}
        result = self.redis.set("dict", data)
        assert result is True
        # 验证调用了setex
        self.mock_redis.setex.assert_called_once()

    def test_get_string(self):
        """测试获取字符串"""
        self.mock_redis.get.return_value = "value"
        result = self.redis.get("test")
        assert result == "value"
        self.mock_redis.get.assert_called_once_with("test")

    def test_get_json(self):
        """测试获取JSON"""
        self.mock_redis.get.return_value = '{"key": "value"}'
        result = self.redis.get("test")
        assert result == {"key": "value"}

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        self.mock_redis.get.return_value = None
        result = self.redis.get("nonexistent", "default")
        assert result == "default"

    def test_delete(self):
        """测试删除"""
        self.mock_redis.delete.return_value = 1
        result = self.redis.delete("test")
        assert result is True

    def test_delete_nonexistent(self):
        """测试删除不存在的键"""
        self.mock_redis.delete.return_value = 0
        result = self.redis.delete("nonexistent")
        assert result is False

    def test_clear(self):
        """测试清空"""
        result = self.redis.clear()
        assert result is True
        self.mock_redis.flushdb.assert_called_once()

    def test_exists_true(self):
        """测试检查存在的键"""
        self.mock_redis.exists.return_value = 1
        result = self.redis.exists("test")
        assert result is True

    def test_exists_false(self):
        """测试检查不存在的键"""
        self.mock_redis.exists.return_value = 0
        result = self.redis.exists("test")
        assert result is False

    def test_ttl(self):
        """测试获取TTL"""
        self.mock_redis.ttl.return_value = 300
        result = self.redis.ttl("test")
        assert result == 300

    def test_keys(self):
        """测试获取键列表"""
        self.mock_redis.keys.return_value = ["key1", "key2"]
        result = self.redis.keys("pattern")
        assert result == ["key1", "key2"]

    def test_info(self):
        """测试获取信息"""
        info = {"version": "6.0"}
        self.mock_redis.info.return_value = info
        result = self.redis.info()
        assert result == info

    def test_ping_success(self):
        """测试ping成功"""
        self.mock_redis.ping.return_value = True
        result = self.redis.ping()
        assert result is True

    def test_ping_failure(self):
        """测试ping失败"""
        self.mock_redis.ping.side_effect = Exception("Connection error")
        result = self.redis.ping()
        assert result is False

    def test_set_error_handling(self):
        """测试设置错误处理"""
        self.mock_redis.setex.side_effect = Exception("Redis error")
        result = self.redis.set("test", "value")
        assert result is False

    def test_get_error_handling(self):
        """测试获取错误处理"""
        self.mock_redis.get.side_effect = Exception("Redis error")
        result = self.redis.get("test", "default")
        assert result == "default"


class TestRedisCacheDecoratorSimple:
    """测试Redis缓存装饰器（简化版）"""

    def test_decorator_cache_miss(self):
        """测试缓存未命中"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.utils.redis_cache.get_redis_client', return_value=mock_redis):
            @redis_cache_decorator(key_prefix="test", ttl=300)
            def expensive_function(x):
                return x * 2

            result = expensive_function(5)
            assert result == 10
            mock_redis.get.assert_called()
            mock_redis.set.assert_called()

    def test_decorator_cache_hit(self):
        """测试缓存命中"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = 20

        with patch('src.utils.redis_cache.get_redis_client', return_value=mock_redis):
            @redis_cache_decorator(key_prefix="test", ttl=300)
            def expensive_function(x):
                return x * 2

            result = expensive_function(10)
            assert result == 20
            mock_redis.set.assert_not_called()

    def test_decorator_redis_unavailable(self):
        """测试Redis不可用"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = False

        with patch('src.utils.redis_cache.get_redis_client', return_value=mock_redis):
            call_count = 0

            @redis_cache_decorator(key_prefix="test", ttl=300)
            def test_function():
                nonlocal call_count
                call_count += 1
                return "result"

            result = test_function()
            assert result == "result"
            assert call_count == 1


class TestGetRedisClientSimple:
    """测试Redis客户端单例（简化版）"""

    def test_singleton(self):
        """测试单例模式"""
        with patch('src.utils.redis_cache.redis.Redis') as mock_redis_class:
            mock_redis_instance = MagicMock()
            mock_redis_class.return_value = mock_redis_instance

            client1 = get_redis_client()
            client2 = get_redis_client()

            assert client1 is client2
            assert client1.client is mock_redis_instance
            mock_redis_class.assert_called_once()

    def test_singleton_with_different_params(self):
        """测试不同参数返回同一实例"""
        with patch('src.utils.redis_cache.redis.Redis') as mock_redis_class:
            mock_redis_instance = MagicMock()
            mock_redis_class.return_value = mock_redis_instance

            client1 = get_redis_client(host="host1")
            client2 = get_redis_client(host="host2")

            assert client1 is client2
            mock_redis_class.assert_called_once()
