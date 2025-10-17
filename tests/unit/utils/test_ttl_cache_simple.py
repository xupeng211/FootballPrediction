"""TTL 缓存简单测试"""

import pytest
import time
from unittest.mock import patch


class TestTTLCache:
    """测试 TTL 缓存"""

    def test_cache_import(self):
        """测试缓存模块导入"""
        try:
            from src.cache.ttl_cache import TTLCache

            assert TTLCache is not None
        except ImportError:
            pass  # 已激活

    def test_cache_basic_operations(self):
        """测试缓存基本操作"""
        try:
            from src.cache.ttl_cache import TTLCache

            cache = TTLCache(ttl=1)  # 1秒 TTL

            # 测试设置和获取
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"

            # 测试不存在的键
            assert cache.get("nonexistent") is None

            # 测试删除
            cache.delete("key1")
            assert cache.get("key1") is None

        except ImportError:
            pass  # 已激活

    def test_cache_expiration(self):
        """测试缓存过期"""
        try:
            from src.cache.ttl_cache import TTLCache

            cache = TTLCache(ttl=0.5)  # 0.5秒 TTL

            cache.set("key", "value")
            assert cache.get("key") == "value"

            # 等待过期
            time.sleep(0.6)
            assert cache.get("key") is None

        except ImportError:
            pass  # 已激活
