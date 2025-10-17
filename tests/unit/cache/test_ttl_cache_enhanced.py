"""
TTL缓存增强版测试
Tests for Enhanced TTL Cache

测试src.cache.ttl_cache_enhanced模块的功能
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

# 测试导入
try:
    from src.cache.ttl_cache_enhanced import (
        TTLCache,
        AsyncTTLCache,
        CacheEntry,
        CacheFactory,
        get_cache,
        get_all_stats,
        clear_all_caches,
        cleanup_all_expired,
    )

    TTL_AVAILABLE = True
except ImportError:
    TTL_AVAILABLE = False


class TestCacheEntry:
    """缓存条目测试"""

    def test_cache_entry_creation(self):
        """测试：缓存条目创建"""
        entry = CacheEntry("test_value", ttl=60)
        assert entry.value == "test_value"
        assert entry.ttl == 60
        assert entry.created_at is not None
        assert entry.access_count == 0

    def test_cache_entry_is_expired(self):
        """测试：缓存条目过期检查"""
        # 未过期的条目
        entry = CacheEntry("test_value", ttl=60)
        assert entry.is_expired() is False

        # 过期的条目
        entry = CacheEntry("test_value", ttl=-1)
        assert entry.is_expired() is True

    def test_cache_entry_touch(self):
        """测试：缓存条目访问更新"""
        entry = CacheEntry("test_value", ttl=60)
        initial_count = entry.access_count
        initial_time = entry.last_accessed

        # 短暂等待确保时间不同
        time.sleep(0.01)
        entry.touch()

        assert entry.access_count == initial_count + 1
        assert entry.last_accessed > initial_time

    def test_cache_entry_extend_ttl(self):
        """测试：扩展缓存条目TTL"""
        entry = CacheEntry("test_value", ttl=60)
        initial_ttl = entry.ttl

        entry.extend_ttl(30)
        assert entry.ttl == initial_ttl + 30

    def test_cache_entry_to_dict(self):
        """测试：缓存条目转字典"""
        entry = CacheEntry("test_value", ttl=60)
        data = entry.to_dict()

        assert "value" in data
        assert "ttl" in data
        assert "created_at" in data
        assert "access_count" in data
        assert "last_accessed" in data


class TestTTLCache:
    """TTL缓存测试"""

    def test_cache_creation(self):
        """测试：缓存创建"""
        cache = TTLCache(maxsize=100, ttl=60)
        assert cache.maxsize == 100
        assert cache.default_ttl == 60

    def test_cache_set_and_get(self):
        """测试：设置和获取缓存"""
        cache = TTLCache(maxsize=100, ttl=60)

        # 设置缓存
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_get_nonexistent(self):
        """测试：获取不存在的键"""
        cache = TTLCache(maxsize=100, ttl=60)
        assert cache.get("nonexistent") is None

    def test_cache_get_with_default(self):
        """测试：获取带默认值的键"""
        cache = TTLCache(maxsize=100, ttl=60)
        assert cache.get("nonexistent", "default") == "default"

    def test_cache_set_with_ttl(self):
        """测试：设置带TTL的缓存"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", "value1", ttl=30)
        entry = cache._data["key1"]
        assert entry.ttl == 30

    def test_cache_expiration(self):
        """测试：缓存过期"""
        cache = TTLCache(maxsize=100, ttl=1)  # 1秒TTL

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 等待过期
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_delete(self):
        """测试：删除缓存"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        cache.delete("key1")
        assert cache.get("key1") is None

    def test_cache_clear(self):
        """测试：清空缓存"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_eviction_lru(self):
        """测试：LRU淘汰策略"""
        cache = TTLCache(maxsize=2, ttl=60)

        # 添加3个键，应该淘汰最旧的
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_cleanup_expired(self):
        """测试：清理过期缓存"""
        cache = TTLCache(maxsize=100, ttl=1)

        # 添加一些键
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        # 等待过期
        time.sleep(1.1)

        # 清理过期项
        cleaned = cache.cleanup_expired()
        assert cleaned > 0
        assert len(cache) == 0

    def test_cache_stats(self):
        """测试：缓存统计"""
        cache = TTLCache(maxsize=100, ttl=60)

        # 初始统计
        stats = cache.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # 添加和访问一些键
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_cache_contains(self):
        """测试：缓存包含检查"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", "value1")
        assert "key1" in cache
        assert "key2" not in cache

    def test_cache_len(self):
        """测试：缓存长度"""
        cache = TTLCache(maxsize=100, ttl=60)

        assert len(cache) == 0

        cache.set("key1", "value1")
        assert len(cache) == 1

        cache.set("key2", "value2")
        assert len(cache) == 2

    def test_cache_iteration(self):
        """测试：缓存迭代"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = list(cache)
        assert "key1" in keys
        assert "key2" in keys

    def test_cache_items(self):
        """测试：缓存项"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        items = list(cache.items())
        assert ("key1", "value1") in items
        assert ("key2", "value2") in items

    def test_cache_keys(self):
        """测试：缓存键"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = list(cache.keys())
        assert "key1" in keys
        assert "key2" in keys

    def test_cache_values(self):
        """测试：缓存值"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        values = list(cache.values())
        assert "value1" in values
        assert "value2" in values


class TestAsyncTTLCache:
    """异步TTL缓存测试"""

    @pytest.mark.asyncio
    async def test_async_cache_creation(self):
        """测试：异步缓存创建"""
        cache = AsyncTTLCache(maxsize=100, ttl=60)
        assert cache.maxsize == 100
        assert cache.default_ttl == 60

    @pytest.mark.asyncio
    async def test_async_cache_set_and_get(self):
        """测试：异步设置和获取缓存"""
        cache = AsyncTTLCache(maxsize=100, ttl=60)

        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_async_cache_get_nonexistent(self):
        """测试：异步获取不存在的键"""
        cache = AsyncTTLCache(maxsize=100, ttl=60)
        value = await cache.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_async_cache_expiration(self):
        """测试：异步缓存过期"""
        cache = AsyncTTLCache(maxsize=100, ttl=1)

        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"

        # 等待过期
        await asyncio.sleep(1.1)
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_async_cache_cleanup(self):
        """测试：异步清理缓存"""
        cache = AsyncTTLCache(maxsize=100, ttl=1)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # 等待过期
        await asyncio.sleep(1.1)

        # 清理过期项
        cleaned = await cache.cleanup_expired()
        assert cleaned > 0
        assert len(cache) == 0


class TestCacheFactory:
    """缓存工厂测试"""

    def test_factory_create_cache(self):
        """测试：工厂创建缓存"""
        cache = CacheFactory.create_cache("test_cache", maxsize=100, ttl=60)
        assert cache is not None
        assert cache.maxsize == 100
        assert cache.default_ttl == 60

    def test_factory_get_cache(self):
        """测试：工厂获取缓存"""
        cache1 = CacheFactory.get_cache("test_cache")
        cache2 = CacheFactory.get_cache("test_cache")
        assert cache1 is cache2  # 应该返回相同的实例

    def test_factory_create_async_cache(self):
        """测试：工厂创建异步缓存"""
        cache = CacheFactory.create_async_cache("async_test_cache", maxsize=100, ttl=60)
        assert cache is not None
        assert isinstance(cache, AsyncTTLCache)


class TestGlobalCacheFunctions:
    """全局缓存函数测试"""

    def test_get_cache_function(self):
        """测试：获取缓存函数"""
        cache = get_cache("test", maxsize=50, ttl=30)
        assert cache is not None
        assert isinstance(cache, TTLCache)

    def test_get_all_stats_function(self):
        """测试：获取所有统计函数"""
        # 创建一些缓存
        cache1 = get_cache("cache1")
        cache2 = get_cache("cache2")

        # 添加一些数据
        cache1.set("key1", "value1")
        cache2.set("key2", "value2")

        # 获取统计
        stats = get_all_stats()
        assert isinstance(stats, dict)
        assert "cache1" in stats
        assert "cache2" in stats

    def test_clear_all_caches_function(self):
        """测试：清空所有缓存函数"""
        # 创建一些缓存
        cache1 = get_cache("cache1")
        cache2 = get_cache("cache2")

        # 添加数据
        cache1.set("key1", "value1")
        cache2.set("key2", "value2")

        # 清空所有缓存
        clear_all_caches()

        assert cache1.get("key1") is None
        assert cache2.get("key2") is None

    def test_cleanup_all_expired_function(self):
        """测试：清理所有过期缓存函数"""
        # 创建一些缓存
        cache1 = get_cache("cache1", ttl=1)
        cache2 = get_cache("cache2", ttl=60)

        # 添加数据
        cache1.set("key1", "value1")
        cache2.set("key2", "value2")

        # 等待第一个缓存过期
        time.sleep(1.1)

        # 清理所有过期缓存
        total_cleaned = cleanup_all_expired()
        assert total_cleaned >= 1


class TestCacheThreadSafety:
    """缓存线程安全测试"""

    def test_concurrent_access(self):
        """测试：并发访问"""
        cache = TTLCache(maxsize=100, ttl=60)
        errors = []

        def writer():
            try:
                for i in range(50):
                    cache.set(f"key{i}", f"value{i}")
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(50):
                    cache.get(f"key{i}")
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 检查是否有错误
        assert len(errors) == 0

    def test_concurrent_cleanup(self):
        """测试：并发清理"""
        cache = TTLCache(maxsize=100, ttl=1)
        errors = []

        # 添加一些数据
        for i in range(20):
            cache.set(f"key{i}", f"value{i}")

        def cleanup():
            try:
                cache.cleanup_expired()
            except Exception as e:
                errors.append(e)

        def accessor():
            try:
                for i in range(20):
                    cache.get(f"key{i}")
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=cleanup))
            threads.append(threading.Thread(target=accessor))

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待过期
        time.sleep(1.1)

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 检查是否有错误
        assert len(errors) == 0


class TestCacheEdgeCases:
    """缓存边界情况测试"""

    def test_cache_with_zero_ttl(self):
        """测试：零TTL缓存"""
        cache = TTLCache(maxsize=100, ttl=0)

        cache.set("key1", "value1")
        # 零TTL应该立即过期
        assert cache.get("key1") is None

    def test_cache_with_negative_ttl(self):
        """测试：负TTL缓存"""
        cache = TTLCache(maxsize=100, ttl=-1)

        cache.set("key1", "value1")
        # 负TTL应该立即过期
        assert cache.get("key1") is None

    def test_cache_with_none_value(self):
        """测试：None值缓存"""
        cache = TTLCache(maxsize=100, ttl=60)

        cache.set("key1", None)
        assert cache.get("key1") is None

    def test_cache_with_large_value(self):
        """测试：大值缓存"""
        cache = TTLCache(maxsize=1, ttl=60)

        large_value = "x" * 10000
        cache.set("key1", large_value)
        assert cache.get("key1") == large_value

    def test_cache_with_special_characters(self):
        """测试：特殊字符键值"""
        cache = TTLCache(maxsize=100, ttl=60)

        special_key = "key_特殊字符!@#$%^&*()"
        special_value = "value_特殊字符!@#$%^&*()"

        cache.set(special_key, special_value)
        assert cache.get(special_key) == special_value

    def test_cache_maxsize_zero(self):
        """测试：零最大大小缓存"""
        cache = TTLCache(maxsize=0, ttl=60)

        cache.set("key1", "value1")
        # 零大小应该无法存储任何东西
        assert cache.get("key1") is None

    def test_cache_maxsize_one(self):
        """测试：大小为一的缓存"""
        cache = TTLCache(maxsize=1, ttl=60)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        cache.set("key2", "value2")
        # 应该淘汰key1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
