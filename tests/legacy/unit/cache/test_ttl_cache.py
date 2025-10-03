from datetime import datetime, timedelta

from src.cache.ttl_cache import CacheEntry, TTLCache
import asyncio
import pytest
import os

"""
TTL缓存测试 / TTL Cache Tests

测试TTL缓存管理器的功能，包括缓存设置、获取、过期和内存管理。

Tests for TTL cache manager functionality, including cache set, get, expiration, and memory management.:

测试类 / Test Classes:
    TestCacheEntry: 缓存条目测试 / Cache entry tests
    TestTTLCache: TTL缓存管理器测试 / TTL cache manager tests

测试方法 / Test Methods:
    test_cache_entry_expiration: 测试缓存条目过期 / Test cache entry expiration
    test_ttl_cache_set_get: 测试TTL缓存设置和获取 / Test TTL cache set and get
    test_ttl_cache_expiration: 测试TTL缓存过期 / Test TTL cache expiration
    test_ttl_cache_eviction: 测试TTL缓存淘汰 / Test TTL cache eviction

使用示例 / Usage Example:
    ```bash
    # 运行缓存测试
    pytest tests/unit/cache/test_ttl_cache.py -v

    # 运行特定测试
    pytest tests/unit/cache/test_ttl_cache.py:TestTTLCache:test_ttl_cache_set_get -v
    ```
"""

class TestCacheEntry:
    """缓存条目测试 / Cache Entry Tests"""
    def test_cache_entry_creation(self):
        """测试缓存条目创建 / Test cache entry creation"""
        value = os.getenv("TEST_TTL_CACHE_VALUE_38"): created_at = datetime.now()": ttl = timedelta(minutes=5)": entry = CacheEntry(value=value, created_at=created_at, ttl=ttl)": assert entry.value ==value"
        assert entry.created_at ==created_at
        assert entry.ttl ==ttl
    def test_cache_entry_without_ttl(self):
        "]""测试无TTL的缓存条目 / Test cache entry without TTL"""
        value = os.getenv("TEST_TTL_CACHE_VALUE_38"): created_at = datetime.now()": entry = CacheEntry(value=value, created_at=created_at)": assert entry.value ==value[" assert entry.created_at ==created_at"
        assert entry.ttl is None
    def test_cache_entry_is_expired_with_ttl(self):
        "]]""测试带TTL的缓存条目是否过期 / Test if cache entry with TTL is expired"""
        value = os.getenv("TEST_TTL_CACHE_VALUE_38"): created_at = datetime.now() - timedelta(minutes=10)  # 10分钟前创建[": ttl = timedelta(minutes=5)  # 5分钟TTL[": entry = CacheEntry(value=value, created_at=created_at, ttl=ttl)": assert entry.is_expired() is True"
    def test_cache_entry_is_not_expired_with_ttl(self):
        "]]]""测试带TTL的缓存条目未过期 / Test if cache entry with TTL is not expired"""
        value = os.getenv("TEST_TTL_CACHE_VALUE_38"): created_at = datetime.now() - timedelta(minutes=2)  # 2分钟前创建[": ttl = timedelta(minutes=5)  # 5分钟TTL[": entry = CacheEntry(value=value, created_at=created_at, ttl=ttl)": assert entry.is_expired() is False"
    def test_cache_entry_is_not_expired_without_ttl(self):
        "]]]""测试无TTL的缓存条目永不过期 / Test that cache entry without TTL never expires"""
        value = os.getenv("TEST_TTL_CACHE_VALUE_38"): created_at = datetime.now() - timedelta(days=365)  # 一年前创建[": entry = CacheEntry(value=value, created_at=created_at)": assert entry.is_expired() is False[" def test_cache_entry_get_remaining_ttl(self):"
        "]]]""测试获取缓存条目剩余TTL / Test getting remaining TTL for cache entry"""
        value = os.getenv("TEST_TTL_CACHE_VALUE_38"): created_at = datetime.now() - timedelta(minutes=2)  # 2分钟前创建[": ttl = timedelta(minutes=5)  # 5分钟TTL[": entry = CacheEntry(value=value, created_at=created_at, ttl=ttl)": remaining_ttl = entry.get_remaining_ttl()"
        assert remaining_ttl is not None
        assert remaining_ttl.total_seconds() > 0
        assert remaining_ttl.total_seconds() < 180  # 小于3分钟
    def test_cache_entry_get_remaining_ttl_expired(self):
        "]]]""测试获取已过期缓存条目的剩余TTL / Test getting remaining TTL for expired cache entry"""
        value = os.getenv("TEST_TTL_CACHE_VALUE_38"): created_at = datetime.now() - timedelta(minutes=10)  # 10分钟前创建[": ttl = timedelta(minutes=5)  # 5分钟TTL[": entry = CacheEntry(value=value, created_at=created_at, ttl=ttl)": remaining_ttl = entry.get_remaining_ttl()"
        assert remaining_ttl is not None
        assert remaining_ttl.total_seconds() ==0
    def test_cache_entry_get_remaining_ttl_without_ttl(self):
        "]]]""测试获取无TTL缓存条目的剩余TTL / Test getting remaining TTL for cache entry without TTL"""
        value = os.getenv("TEST_TTL_CACHE_VALUE_38"): created_at = datetime.now()": entry = CacheEntry(value=value, created_at=created_at)": remaining_ttl = entry.get_remaining_ttl()": assert remaining_ttl is None"
class TestTTLCache:
    "]""TTL缓存管理器测试 / TTL Cache Manager Tests"""
    @pytest.fixture
    def ttl_cache(self):
        """创建TTL缓存实例 / Create TTL cache instance"""
        return TTLCache(max_size=100)
    @pytest.mark.asyncio
    async def test_ttl_cache_set_get(self, ttl_cache):
        """测试TTL缓存设置和获取 / Test TTL cache set and get"""
        key = os.getenv("TEST_TTL_CACHE_KEY_71"): value = os.getenv("TEST_TTL_CACHE_VALUE_72")""""
        # 设置缓存值
        await ttl_cache.set(key, value)
        # 获取缓存值
        cached_value = await ttl_cache.get(key)
        assert cached_value ==value
    @pytest.mark.asyncio
    async def test_ttl_cache_get_nonexistent_key(self, ttl_cache):
        "]""测试获取不存在的缓存键 / Test getting non-existent cache key"""
        key = os.getenv("TEST_TTL_CACHE_KEY_80")""""
        # 获取不存在的键
        cached_value = await ttl_cache.get(key)
        assert cached_value is None
    @pytest.mark.asyncio
    async def test_ttl_cache_set_get_with_ttl(self, ttl_cache):
        "]""测试带TTL的缓存设置和获取 / Test TTL cache set and get with TTL"""
        key = os.getenv("TEST_TTL_CACHE_KEY_71"): value = os.getenv("TEST_TTL_CACHE_VALUE_72"): ttl = timedelta(milliseconds=100)  # 100毫秒TTL[""""
        # 设置带TTL的缓存值
        await ttl_cache.set(key, value, ttl=ttl)
        # 立即获取缓存值
        cached_value = await ttl_cache.get(key)
        assert cached_value ==value
    @pytest.mark.asyncio
    async def test_ttl_cache_expiration(self, ttl_cache):
        "]]""测试TTL缓存过期 / Test TTL cache expiration"""
        key = os.getenv("TEST_TTL_CACHE_KEY_71"): value = os.getenv("TEST_TTL_CACHE_VALUE_72"): ttl = timedelta(milliseconds=50)  # 50毫秒TTL[""""
        # 设置带TTL的缓存值
        await ttl_cache.set(key, value, ttl=ttl)
        # 人为调整创建时间以模拟过期，避免真实等待
        assert key in ttl_cache._cache
        ttl_cache._cache["]]key[".created_at -= ttl + timedelta(milliseconds=10)""""
        # 获取过期的缓存值
        cached_value = await ttl_cache.get(key)
        assert cached_value is None
    @pytest.mark.asyncio
    async def test_ttl_cache_delete(self, ttl_cache):
        "]""测试TTL缓存删除 / Test TTL cache deletion"""
        key = os.getenv("TEST_TTL_CACHE_KEY_71"): value = os.getenv("TEST_TTL_CACHE_VALUE_72")""""
        # 设置缓存值
        await ttl_cache.set(key, value)
        # 删除缓存值
        result = await ttl_cache.delete(key)
        assert result is True
        # 验证缓存值已删除
        cached_value = await ttl_cache.get(key)
        assert cached_value is None
    @pytest.mark.asyncio
    async def test_ttl_cache_delete_nonexistent_key(self, ttl_cache):
        "]""测试删除不存在的缓存键 / Test deleting non-existent cache key"""
        key = os.getenv("TEST_TTL_CACHE_KEY_80")""""
        # 删除不存在的键
        result = await ttl_cache.delete(key)
        assert result is False
    @pytest.mark.asyncio
    async def test_ttl_cache_clear(self, ttl_cache):
        "]""测试TTL缓存清空 / Test TTL cache clear"""
        # 设置多个缓存值
        await ttl_cache.set("key1[", "]value1[")": await ttl_cache.set("]key2[", "]value2[")": await ttl_cache.set("]key3[", "]value3[")""""
        # 清空缓存
        await ttl_cache.clear()
        # 验证所有缓存值已清空
        assert await ttl_cache.get("]key1[") is None[" assert await ttl_cache.get("]]key2[") is None[" assert await ttl_cache.get("]]key3[") is None[""""
    @pytest.mark.asyncio
    async def test_ttl_cache_eviction_lru(self, ttl_cache):
        "]]""测试TTL缓存LRU淘汰 / Test TTL cache LRU eviction"""
        # 创建小容量缓存
        small_cache = TTLCache(max_size=3)
        # 设置超过容量的缓存值
        await small_cache.set("key1[", "]value1[")": await small_cache.set("]key2[", "]value2[")": await small_cache.set("]key3[", "]value3[")": await small_cache.set("]key4[", "]value4[")  # 这应该触发LRU淘汰[""""
        # 所有操作均为同步await，直接验证状态
        # 验证缓存状态
        stats = await small_cache.get_stats()
        assert stats["]]total_entries["] <= 3[""""
    @pytest.mark.asyncio
    async def test_ttl_cache_get_stats(self, ttl_cache):
        "]]""测试TTL缓存统计信息 / Test TTL cache statistics"""
        # 设置一些缓存值
        await ttl_cache.set("key1[", "]value1[")": await ttl_cache.set("]key2[", "]value2[")""""
        # 设置带TTL的缓存值并等待过期
        await ttl_cache.set("]key3[", "]value3[", ttl=timedelta(milliseconds=10))": assert "]key3[" in ttl_cache._cache[""""
        ttl_cache._cache["]]key3["].created_at -= timedelta(milliseconds=20)""""
        # 获取统计信息
        stats = await ttl_cache.get_stats()
        assert stats["]total_entries["] >= 0[" assert stats["]]max_size["] ==100[" assert isinstance(stats["]]active_entries["], int)" assert isinstance(stats["]expired_entries["], int)""""
    @pytest.mark.asyncio
    async def test_ttl_cache_thread_safety(self, ttl_cache):
        "]""测试TTL缓存线程安全 / Test TTL cache thread safety"""
        # 创建多个并发任务
        async def set_and_get_task(task_id):
            key = f["key_{task_id}"]": value = f["value_{task_id}"]""""
            # 设置缓存
            await ttl_cache.set(key, value)
            # 获取缓存
            cached_value = await ttl_cache.get(key)
            return cached_value ==value
        # 并发执行多个任务
        tasks = [set_and_get_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        # 验证所有任务都成功
        assert all(results)