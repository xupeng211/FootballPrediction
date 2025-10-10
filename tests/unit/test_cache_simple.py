"""
简单缓存测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import time
from typing import Any, Dict, Optional


class TestSimpleCache:
    """简单缓存功能测试"""

    def test_basic_cache_logic(self):
        """测试基础缓存逻辑"""
        cache = {}

        # 设置值
        cache["key1"] = {"value": "value1", "created_at": time.time()}
        assert cache["key1"]["value"] == "value1"

        # 获取值
        item = cache.get("key1")
        assert item is not None
        assert item["value"] == "value1"

        # 删除值
        del cache["key1"]
        assert "key1" not in cache

    def test_cache_with_ttl(self):
        """测试带TTL的缓存"""
        cache = {}
        ttl = 1  # 1秒

        # 设置带TTL的值
        cache["key"] = {"value": "test_value", "created_at": time.time(), "ttl": ttl}

        # 立即检查未过期
        item = cache["key"]
        is_expired = time.time() >= item["created_at"] + item["ttl"]
        assert not is_expired

        # 等待过期
        time.sleep(1.1)
        item = cache["key"]
        is_expired = time.time() >= item["created_at"] + item["ttl"]
        assert is_expired

    def test_cache_eviction(self):
        """测试缓存驱逐"""
        max_size = 3
        cache = {}

        # 添加3个项
        for i in range(max_size):
            cache[f"key{i}"] = {
                "value": f"value{i}",
                "created_at": time.time() - i,  # 不同的创建时间
            }

        assert len(cache) == 3

        # 添加第4个项，应该驱逐最旧的
        cache["key3"] = {"value": "value3", "created_at": time.time()}

        # 手动驱逐最旧的
        oldest_key = min(cache.items(), key=lambda x: x[1]["created_at"])[0]
        del cache[oldest_key]

        assert len(cache) == 3
        assert "key3" in cache

    def test_cache_stats(self):
        """测试缓存统计"""
        stats = {"hits": 0, "misses": 0, "evictions": 0}
        cache = {}

        # Hit
        cache["key"] = {"value": "value"}
        if "key" in cache:
            stats["hits"] += 1

        # Miss
        if "nonexistent" not in cache:
            stats["misses"] += 1

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["evictions"] == 0

    @pytest.mark.asyncio
    async def test_async_cache_operations(self):
        """测试异步缓存操作"""
        cache = {}

        async def async_set(key, value):
            await asyncio.sleep(0.01)  # 模拟异步操作
            cache[key] = value

        async def async_get(key):
            await asyncio.sleep(0.01)  # 模拟异步操作
            return cache.get(key)

        # 异步设置和获取
        await async_set("async_key", "async_value")
        value = await async_get("async_key")

        assert value == "async_value"

    def test_cache_key_generation(self):
        """测试缓存键生成"""

        def make_cache_key(func_name, args, kwargs):
            import hashlib

            key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
            return hashlib.md5(key_data.encode()).hexdigest()

        def test_func(a, b, c=None):
            return a + b + (c or 0)

        key1 = make_cache_key("test_func", (1, 2), {"c": 3})
        key2 = make_cache_key("test_func", (1, 2), {"c": 3})
        key3 = make_cache_key("test_func", (1, 2), {"c": 4})

        assert key1 == key2
        assert key1 != key3

    def test_cache_serialization(self):
        """测试缓存序列化"""
        import json

        cache_data = {
            "key1": {"value": "value1", "created_at": time.time()},
            "key2": {"value": 123, "created_at": time.time()},
            "key3": {"value": {"nested": "data"}, "created_at": time.time()},
        }

        # 序列化
        serialized = json.dumps(cache_data, default=str)

        # 反序列化
        deserialized = json.loads(serialized)

        assert len(deserialized) == 3
        assert deserialized["key1"]["value"] == "value1"
        assert deserialized["key2"]["value"] == 123

    def test_cache_decorator_pattern(self):
        """测试缓存装饰器模式"""
        cache = {}

        def cache_decorator(ttl=None):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    # 生成缓存键
                    cache_key = f"{func.__name__}:{args}:{kwargs}"

                    # 尝试从缓存获取
                    if cache_key in cache:
                        item = cache[cache_key]
                        if ttl is None or time.time() - item["created_at"] < ttl:
                            return item["value"]

                    # 执行函数
                    result = func(*args, **kwargs)

                    # 存入缓存
                    cache[cache_key] = {"value": result, "created_at": time.time()}

                    return result

                return wrapper

            return decorator

        @cache_decorator(ttl=1)
        def expensive_function(x):
            time.sleep(0.1)  # 模拟耗时操作
            return x * 2

        # 第一次调用
        start = time.time()
        result1 = expensive_function(5)
        duration1 = time.time() - start

        # 第二次调用（应该从缓存获取）
        start = time.time()
        result2 = expensive_function(5)
        duration2 = time.time() - start

        assert result1 == 10
        assert result2 == 10
        assert duration2 < duration1  # 第二次应该更快

    def test_cache_invalidation(self):
        """测试缓存失效"""
        cache = {}

        def invalidate_pattern(pattern):
            keys_to_delete = [k for k in cache.keys() if pattern in k]
            for key in keys_to_delete:
                del cache[key]
            return len(keys_to_delete)

        # 添加一些键
        cache["user:123:data"] = {"value": "data1"}
        cache["user:456:data"] = {"value": "data2"}
        cache["config:setting"] = {"value": "setting1"}

        # 失效所有用户相关的缓存
        deleted = invalidate_pattern("user:")

        assert deleted == 2
        assert "user:123:data" not in cache
        assert "user:456:data" not in cache
        assert "config:setting" in cache

    def test_cache_warmup(self):
        """测试缓存预热"""
        cache = {}

        def warmup_cache(keys):
            for key in keys:
                # 模拟从数据源加载
                cache[key] = {"value": f"data_for_{key}", "created_at": time.time()}

        # 预热一些键
        keys_to_warm = ["key1", "key2", "key3"]
        warmup_cache(keys_to_warm)

        assert len(cache) == 3
        assert all(key in cache for key in keys_to_warm)

    def test_cache_consistency_check(self):
        """测试缓存一致性检查"""
        cache = {
            "key1": {"value": "value1", "checksum": "abc123"},
            "key2": {"value": "value2", "checksum": "def456"},
        }

        def calculate_checksum(value):
            import hashlib

            return hashlib.md5(str(value).encode()).hexdigest()

        def check_consistency():
            inconsistent = []
            for key, item in cache.items():
                expected = calculate_checksum(item["value"])
                if item["checksum"] != expected:
                    inconsistent.append(key)
            return inconsistent

        # 修改值但不更新checksum
        cache["key1"]["value"] = "modified_value"

        # 检查一致性
        inconsistent = check_consistency()

        assert "key1" in inconsistent
        assert "key2" not in inconsistent
