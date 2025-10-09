"""
测试模块化TTL缓存
Test Modular TTL Cache
"""

import pytest
import time
from unittest.mock import patch, MagicMock


def test_cache_entry():
    """测试缓存条目"""
    from src.cache.ttl_cache_improved_mod.cache_entry import CacheEntry

    # 创建条目
    entry = CacheEntry("key1", "value1", ttl=1.0)
    assert entry.key == "key1"
    assert entry.value == "value1"
    assert entry.access_count == 0
    assert entry.expires_at is not None

    # 测试访问
    value = entry.access()
    assert value == "value1"
    assert entry.access_count == 1

    # 测试过期
    time.sleep(1.1)
    assert entry.is_expired()


def test_ttl_cache_basic():
    """测试TTL缓存基本功能"""
    from src.cache.ttl_cache_improved_mod.ttl_cache import TTLCache

    cache = TTLCache(max_size=3, default_ttl=1.0)

    # 测试set和get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.size() == 1

    # 测试不存在的键
    assert cache.get("nonexistent") is None
    assert cache.get("nonexistent", "default") == "default"

    # 测试更新
    cache.set("key1", "value1_new")
    assert cache.get("key1") == "value1_new"

    # 测试过期
    time.sleep(1.1)
    assert cache.get("key1") is None
    assert cache.size() == 0


def test_ttl_cache_lru():
    """测试LRU淘汰策略"""
    from src.cache.ttl_cache_improved_mod.ttl_cache import TTLCache

    cache = TTLCache(max_size=2, default_ttl=None)  # 不自动过期

    # 添加两个项
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    assert cache.size() == 2

    # 访问key1使其成为最近使用
    cache.get("key1")

    # 添加第三个项，应该淘汰key2
    cache.set("key3", "value3")
    assert cache.size() == 2
    assert cache.get("key1") == "value1"  # key1还在
    assert cache.get("key2") is None  # key2被淘汰
    assert cache.get("key3") == "value3"


def test_ttl_cache_batch_operations():
    """测试批量操作"""
    from src.cache.ttl_cache_improved_mod.ttl_cache import TTLCache

    cache = TTLCache(max_size=10)

    # 批量设置
    data = {"key1": "value1", "key2": "value2", "key3": "value3"}
    cache.set_many(data)
    assert cache.size() == 3

    # 批量获取
    result = cache.get_many(["key1", "key2", "key4"])
    assert result == {"key1": "value1", "key2": "value2"}

    # 批量删除
    deleted = cache.delete_many(["key1", "key3"])
    assert deleted == 2
    assert cache.size() == 1


def test_ttl_cache_increment():
    """测试递增操作"""
    from src.cache.ttl_cache_improved_mod.ttl_cache import TTLCache

    cache = TTLCache()

    # 递增不存在的键
    result = cache.increment("counter", delta=1, default=0)
    assert result == 1
    assert cache.get("counter") == 1

    # 再次递增
    result = cache.increment("counter", delta=5)
    assert result == 6
    assert cache.get("counter") == 6

    # 测试非数字值
    cache.set("text", "hello")
    with pytest.raises(TypeError):
        cache.increment("text")


def test_ttl_cache_ttl_operations():
    """测试TTL相关操作"""
    from src.cache.ttl_cache_improved_mod.ttl_cache import TTLCache

    cache = TTLCache(default_ttl=10.0)

    # 设置带TTL的项
    cache.set("key1", "value1", ttl=2.0)
    remaining = cache.ttl("key1")
    assert 0 < remaining <= 2

    # 更新TTL
    success = cache.touch("key1", ttl=5.0)
    assert success
    remaining = cache.ttl("key1")
    assert 0 < remaining <= 5

    # 测试不存在的键
    assert cache.ttl("nonexistent") == -1
    assert cache.touch("nonexistent") is False


def test_ttl_cache_stats():
    """测试统计信息"""
    from src.cache.ttl_cache_improved_mod.ttl_cache import TTLCache

    cache = TTLCache()

    # 初始统计
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["sets"] == 0
    assert stats["size"] == 0

    # 设置和获取
    cache.set("key1", "value1")
    cache.get("key1")  # hit
    cache.get("nonexistent")  # miss

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["sets"] == 1
    assert stats["size"] == 1
    assert stats["hit_rate"] == 0.5

    # 重置统计
    cache.reset_stats()
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0


def test_async_cache():
    """测试异步缓存"""
    import asyncio
    from src.cache.ttl_cache_improved_mod.async_cache import AsyncTTLCache

    async def test_async():
        cache = AsyncTTLCache(max_size=10, default_ttl=1.0)

        # 异步设置和获取
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"

        # 批量操作
        data = {"key2": "value2", "key3": "value3"}
        await cache.set_many(data)
        results = await cache.get_many(["key1", "key2", "key4"])
        assert results == {"key1": "value1", "key2": "value2"}

        # 异步删除
        success = await cache.delete("key1")
        assert success
        assert await cache.get("key1") is None

    asyncio.run(test_async())


def test_cache_factory():
    """测试缓存工厂"""
    from src.cache.ttl_cache_improved_mod.cache_factory import CacheFactory

    # 创建同步缓存
    sync_cache = CacheFactory.create_cache("sync", max_size=100)
    assert hasattr(sync_cache, "get")
    assert hasattr(sync_cache, "set")

    # 创建异步缓存
    async_cache = CacheFactory.create_cache("async", max_size=100)
    assert hasattr(async_cache, "get")
    assert hasattr(async_cache, "set")

    # 创建预设缓存
    lru_cache = CacheFactory.create_lru_cache(128)
    ttl_cache = CacheFactory.create_ttl_cache(1000, 3600)
    assert lru_cache.max_size == 128
    assert ttl_cache.default_ttl == 3600

    # 创建业务专用缓存
    pred_cache = CacheFactory.create_prediction_cache()
    feature_cache = CacheFactory.create_feature_cache()
    odds_cache = CacheFactory.create_odds_cache()
    assert pred_cache.max_size == 10000
    assert feature_cache.default_ttl == 3600
    assert odds_cache.max_size == 20000

    # 测试可用类型
    types = CacheFactory.get_available_types()
    assert "sync" in types
    assert "async" in types

    # 测试预设配置
    configs = CacheFactory.get_preset_configs()
    assert "prediction" in configs
    assert configs["prediction"]["max_size"] == 10000

    # 测试不支持的类型
    with pytest.raises(ValueError):
        CacheFactory.create_cache("unsupported")


def test_cache_instances():
    """测试预定义缓存实例"""
    from src.cache.ttl_cache_improved_mod.cache_instances import (
        prediction_cache,
        feature_cache,
        odds_cache,
        session_cache,
        config_cache,
        temp_cache,
        get_cache,
        get_all_stats,
        clear_all_caches,
        cleanup_all_expired,
    )

    # 测试预定义实例
    assert prediction_cache.max_size == 10000
    assert feature_cache.default_ttl == 3600
    assert odds_cache.max_size == 20000
    assert session_cache.default_ttl == 7200
    assert config_cache.default_ttl == 86400
    assert temp_cache.max_size == 1000

    # 使用缓存
    prediction_cache.set("test", "value")
    assert prediction_cache.get("test") == "value"

    # 测试工具函数
    cache = get_cache("prediction")
    assert cache is prediction_cache
    assert get_cache("nonexistent") is None

    # 获取所有统计
    all_stats = get_all_stats()
    assert "prediction" in all_stats

    # 清理过期项
    cleaned = cleanup_all_expired()
    assert isinstance(cleaned, int)

    # 清空所有缓存
    clear_all_caches()
    assert prediction_cache.is_empty()


def test_module_import():
    """测试模块导入"""
    from src.cache.ttl_cache_improved_mod import (
        TTLCache,
        AsyncTTLCache,
        CacheEntry,
        CacheFactory,
        prediction_cache,
        feature_cache,
        odds_cache,
    )

    assert TTLCache is not None
    assert AsyncTTLCache is not None
    assert CacheEntry is not None
    assert CacheFactory is not None
    assert prediction_cache is not None


def test_backward_compatibility():
    """测试向后兼容性"""
    # 应该能从原始位置导入
    from src.cache.ttl_cache_improved import TTLCache, CacheFactory

    cache = TTLCache(max_size=100)
    cache.set("test", "value")
    assert cache.get("test") == "value"

    factory = CacheFactory()
    lru_cache = factory.create_lru_cache()
    assert lru_cache is not None


def test_cache_repr():
    """测试缓存的字符串表示"""
    from src.cache.ttl_cache_improved_mod.ttl_cache import TTLCache
    from src.cache.ttl_cache_improved_mod.cache_entry import CacheEntry

    cache = TTLCache(max_size=100)
    cache.set("test", "value")
    assert "TTLCache" in repr(cache)
    assert "size=1" in repr(cache)

    entry = CacheEntry("key", "value", ttl=10)
    assert "CacheEntry" in repr(entry)
    assert "key=key" in repr(entry)