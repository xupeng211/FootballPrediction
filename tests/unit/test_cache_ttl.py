"""
TTL缓存模块测试
"""

import pytest
from unittest.mock import MagicMock, patch
import asyncio
import json
import time
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from dataclasses import dataclass, field

from src.cache.ttl_cache import TTLCache, CacheItem, CacheEntry


class TestCacheItem:
    """缓存项测试"""

    def test_cache_item_creation(self):
        """测试缓存项创建"""
        item = CacheItem(value="test_value", ttl=10.0)

        assert item.value == "test_value"
        assert item.ttl == 10.0
        assert isinstance(item.created_at, float)

    def test_cache_item_without_ttl(self):
        """测试没有TTL的缓存项"""
        item = CacheItem(value="no_ttl")

        assert item.value == "no_ttl"
        assert item.ttl is None
        assert item.created_at > 0

    def test_is_expired_with_ttl(self):
        """测试有TTL的过期检查"""
        # 未过期
        item = CacheItem(value="test", ttl=10.0)
        assert item.is_expired() is False

        # 已过期（使用过去的时间）
        item.created_at = time.time() - 15.0
        assert item.is_expired() is True

    def test_is_expired_without_ttl(self):
        """测试没有TTL的过期检查"""
        item = CacheItem(value="test")
        assert item.is_expired() is False

        # 即使是过去的时间也不会过期
        item.created_at = time.time() - 1000.0
        assert item.is_expired() is False

    def test_is_expired_with_custom_time(self):
        """测试使用自定义时间的过期检查"""
        now = time.time()
        item = CacheItem(value="test", ttl=10.0, created_at=now)

        # 5秒后未过期
        assert item.is_expired(now + 5.0) is False

        # 15秒后过期
        assert item.is_expired(now + 15.0) is True

    def test_remaining_ttl(self):
        """测试剩余TTL计算"""
        now = time.time()
        item = CacheItem(value="test", ttl=10.0, created_at=now)

        # 5秒后剩余5秒
        remaining = item.remaining_ttl(now + 5.0)
        assert remaining == 5.0

        # 10秒后剩余0秒
        remaining = item.remaining_ttl(now + 10.0)
        assert remaining == 0.0

        # 15秒后剩余0秒（不会为负）
        remaining = item.remaining_ttl(now + 15.0)
        assert remaining == 0.0

    def test_remaining_ttl_without_ttl(self):
        """测试没有TTL的剩余TTL"""
        item = CacheItem(value="test")
        assert item.remaining_ttl() is None

    def test_cache_entry_alias(self):
        """测试向后兼容的别名"""
        item = CacheEntry(value="test", ttl=10.0)
        assert isinstance(item, CacheItem)
        assert item.value == "test"


class TestTTLCache:
    """TTL缓存测试"""

    def test_cache_init_default(self):
        """测试默认初始化"""
        cache = TTLCache()

        assert cache.max_size == 1000
        assert cache.default_ttl is None
        assert cache.size() == 0

    def test_cache_init_with_params(self):
        """测试带参数初始化"""
        cache = TTLCache(max_size=500, ttl=60.0)

        assert cache.max_size == 500
        assert cache.default_ttl == 60.0

    def test_cache_init_with_maxsize_alias(self):
        """测试使用maxsize参数"""
        cache = TTLCache(maxsize=200)

        assert cache.max_size == 200

    def test_normalize_ttl(self):
        """测试TTL规范化"""
        # None
        assert TTLCache._normalize_ttl(None) is None

        # 数字
        assert TTLCache._normalize_ttl(60) == 60.0
        assert TTLCache._normalize_ttl(60.5) == 60.5

        # 负数
        assert TTLCache._normalize_ttl(-10) == 0.0

        # timedelta
        td = timedelta(minutes=5, seconds=30)
        assert TTLCache._normalize_ttl(td) == 330.0

    def test_set_and_get(self):
        """测试设置和获取"""
        cache = TTLCache()

        # 设置值
        assert cache.set("key1", "value1") is True

        # 获取值
        assert cache.get("key1") == "value1"

        # 获取不存在的键
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"

    def test_set_with_ttl(self):
        """测试设置带TTL的值"""
        cache = TTLCache()

        # 设置带TTL的值
        cache.set("key", "value", ttl=0.1)  # 0.1秒

        # 立即获取应该存在
        assert cache.get("key") == "value"

        # 等待过期
        time.sleep(0.2)
        assert cache.get("key") is None

    def test_set_with_timedelta_ttl(self):
        """测试使用timedelta设置TTL"""
        cache = TTLCache()

        # 使用timedelta
        cache.set("key", "value", ttl=timedelta(milliseconds=100))

        assert cache.get("key") == "value"
        time.sleep(0.2)
        assert cache.get("key") is None

    def test_delete(self):
        """测试删除"""
        cache = TTLCache()

        cache.set("key", "value")
        assert cache.delete("key") is True
        assert cache.get("key") is None

        # 删除不存在的键
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        """测试清空缓存"""
        cache = TTLCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None

    def test_size(self):
        """测试缓存大小"""
        cache = TTLCache(max_size=3)

        assert cache.size() == 0

        cache.set("key1", "value1")
        assert cache.size() == 1

        cache.set("key2", "value2")
        assert cache.size() == 2

        # 添加超过最大大小的项
        cache.set("key3", "value3")
        assert cache.size() == 3

        cache.set("key4", "value4")  # 应该驱逐最旧的
        assert cache.size() == 3

    def test_keys_values_items(self):
        """测试获取键、值、项"""
        cache = TTLCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = cache.keys()
        values = cache.values()
        items = cache.items()

        assert set(keys) == {"key1", "key2"}
        assert set(values) == {"value1", "value2"}
        assert set(items) == {("key1", "value1"), ("key2", "value2")}

    def test_set_many_get_many(self):
        """测试批量设置和获取"""
        cache = TTLCache()

        mapping = {"key1": "value1", "key2": "value2", "key3": "value3"}
        cache.set_many(mapping)

        # 获取多个
        results = cache.get_many(["key1", "key2", "key3", "key4"])
        expected = {"key1": "value1", "key2": "value2", "key3": "value3", "key4": None}
        assert results == expected

        # 带默认值
        results = cache.get_many(["key1", "key4"], default="default")
        expected = {"key1": "value1", "key4": "default"}
        assert results == expected

    def test_eviction_oldest(self):
        """测试驱逐最旧的项"""
        cache = TTLCache(max_size=2)

        cache.set("key1", "value1")
        time.sleep(0.01)  # 确保时间差异
        cache.set("key2", "value2")

        # 添加第三项应该驱逐最旧的key1
        cache.set("key3", "value3")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_purge_expired(self):
        """测试清理过期项"""
        cache = TTLCache(max_size=10)

        # 添加一些项
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")

        # 添加一些会过期的项
        cache.set("expired1", "value1", ttl=0.1)
        cache.set("expired2", "value2", ttl=0.1)

        assert cache.size() == 7

        # 等待过期
        time.sleep(0.2)

        # 获取一个不存在的项会触发清理
        cache.get("nonexistent")
        assert cache.size() == 5

    def test_contains(self):
        """测试包含操作符"""
        cache = TTLCache()

        cache.set("key", "value")
        assert "key" in cache
        assert "nonexistent" not in cache

    def test_get_stats(self):
        """测试获取统计信息"""
        cache = TTLCache()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0

        cache.set("key", "value")
        cache.get("key")  # hit
        cache.get("nonexistent")  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_save_to_file_and_load_from_file(self):
        """测试保存到文件和从文件加载"""
        cache = TTLCache()

        cache.set("key1", "value1", ttl=10.0)
        cache.set("key2", "value2", ttl=None)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            # 保存
            cache.save_to_file(temp_path)

            # 验证文件存在
            assert Path(temp_path).exists()

            # 读取文件内容
            data = json.loads(Path(temp_path).read_text())
            assert len(data) == 2
            assert data[0]["key"] in ["key1", "key2"]

            # 加载到新缓存
            new_cache = TTLCache()
            new_cache.load_from_file(temp_path)

            assert new_cache.get("key1") == "value1"
            assert new_cache.get("key2") == "value2"

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_from_file_merge(self):
        """测试加载时合并"""
        cache1 = TTLCache()
        cache2 = TTLCache()

        cache1.set("key1", "value1")
        cache2.set("key2", "value2")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            cache1.save_to_file(temp_path)

            # 合并加载
            cache2.load_from_file(temp_path, merge=True)

            assert cache2.get("key1") == "value1"
            assert cache2.get("key2") == "value2"

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_from_nonexistent_file(self):
        """测试从不存在的文件加载"""
        cache = TTLCache()

        # 不应该抛出异常
        cache.load_from_file("/nonexistent/path/cache.json")
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_async_methods(self):
        """测试异步方法"""
        cache = TTLCache()

        # 异步设置和获取
        await cache.set_async("key", "value")
        assert await cache.get_async("key") == "value"

        # 异步删除
        assert await cache.delete_async("key") is True
        assert await cache.get_async("key") is None

        # 异步清空
        await cache.set_async("key1", "value1")
        await cache.set_async("key2", "value2")
        await cache.clear_async()
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_async_batch_operations(self):
        """测试异步批量操作"""
        cache = TTLCache()

        mapping = {"key1": "value1", "key2": "value2", "key3": "value3"}
        await cache.set_many_async(mapping)

        results = await cache.get_many_async(["key1", "key2", "key3"])
        assert results == mapping

    def test_thread_safety(self):
        """测试线程安全性"""
        import threading

        cache = TTLCache()
        results = []

        def worker(value):
            cache.set(f"key{value}", f"value{value}")
            results.append(cache.get(f"key{value}"))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert all(r is not None for r in results)
