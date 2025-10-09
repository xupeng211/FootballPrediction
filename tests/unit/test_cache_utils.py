"""缓存工具测试"""
import pytest
from unittest.mock import Mock, patch
from src.cache.redis_manager import RedisManager
from src.cache.ttl_cache import TTLCache


class TestCacheUtils:
    """测试缓存工具"""

    def test_redis_manager_creation(self):
        """测试Redis管理器创建"""
        manager = RedisManager()
        assert manager is not None

    def test_ttl_cache_creation(self):
        """测试TTL缓存创建"""
        cache = TTLCache(max_size=100, ttl=60)
        assert cache is not None
        assert cache.max_size == 100

    @patch('redis.Redis')
    def test_redis_connection_mock(self, mock_redis):
        """测试Redis连接mock"""
        mock_redis.return_value = Mock()
        manager = RedisManager()
        assert manager is not None

    def test_cache_basic_operations(self):
        """测试缓存基本操作"""
        cache = TTLCache(maxsize=10, ttl=60)

        # 测试设置和获取
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 测试不存在的键
        assert cache.get("nonexistent") is None

    def test_cache_eviction(self):
        """测试缓存淘汰"""
        cache = TTLCache(maxsize=2, ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # 应该淘汰key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"