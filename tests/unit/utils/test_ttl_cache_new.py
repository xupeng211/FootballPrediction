from unittest.mock import patch, MagicMock
"""TTL缓存测试"""

import pytest
import time
from src.cache.ttl_cache import TTLCache


@pytest.mark.unit
@pytest.mark.cache
@pytest.mark.slow

class TestTTLCache:
    """TTL缓存测试"""

    @pytest.fixture
    def cache(self):
        """创建缓存实例"""
        return TTLCache(ttl=60, max_size=100)

    def test_cache_set_and_get(self, cache):
        """测试缓存设置和获取"""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_expiration(self):
        """测试缓存过期"""
        cache = TTLCache(ttl=0.1, max_size=100)  # 0.1秒过期
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.2)
        time.sleep(0.2)
        time.sleep(0.2)
        time.sleep(0.2)
        time.sleep(0.2)
        assert cache.get("key1") is None

    def test_cache_eviction(self):
        """测试缓存淘汰"""
        cache = TTLCache(ttl=60, max_size=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # 应该淘汰 key1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_delete(self, cache):
        """测试缓存删除"""
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_cache_clear(self, cache):
        """测试清空缓存"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
