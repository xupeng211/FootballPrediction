"""核心缓存模块单元测试
Unit Tests for Core Cache Module.

测试Redis缓存基础设施和装饰器的功能。
Tests the functionality of Redis cache infrastructure and decorators.

Author: Claude Code
Version: 1.0.0
"""

import asyncio
import json
import pickle
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.core.cache_main import (
    RedisCache,
    get_cache,
    cache_key_builder,
    CacheSerializationError,
    CacheConnectionError,
    cache_get,
    cache_set,
    cache_delete
)
from src.core.cache_decorators import (
    cached,
    cached_long,
    cached_short,
    cached_method,
    BatchCache,
    invalidate_pattern
)


class TestRedisCache:
    """RedisCache类测试."""

    @pytest.fixture
    async def cache_instance(self):
        """创建缓存实例."""
        cache = RedisCache("redis://localhost:6379/1")  # 使用测试数据库
        yield cache
        await cache.close()

    @pytest.mark.asyncio
    async def test_cache_serialization_simple_types(self, cache_instance):
        """测试简单类型序列化."""
        # 测试字符串
        serialized = cache_instance._serialize("test_string")
        deserialized = cache_instance._deserialize(serialized)
        assert deserialized == "test_string"

        # 测试数字
        serialized = cache_instance._serialize(42)
        deserialized = cache_instance._deserialize(serialized)
        assert deserialized == 42

        # 测试布尔值
        serialized = cache_instance._serialize(True)
        deserialized = cache_instance._deserialize(serialized)
        assert deserialized is True

        # 测试None
        serialized = cache_instance._serialize(None)
        deserialized = cache_instance._deserialize(serialized)
        assert deserialized is None

    @pytest.mark.asyncio
    async def test_cache_serialization_complex_types(self, cache_instance):
        """测试复杂类型序列化."""
        # 测试字典
        test_dict = {"key1": "value1", "key2": 123, "key3": True}
        serialized = cache_instance._serialize(test_dict)
        deserialized = cache_instance._deserialize(serialized)
        assert deserialized == test_dict

        # 测试列表
        test_list = [1, "two", {"three": 3}]
        serialized = cache_instance._serialize(test_list)
        deserialized = cache_instance._deserialize(serialized)
        assert deserialized == test_list

        # 测试元组
        test_tuple = (1, "two", {"three": 3})
        serialized = cache_instance._serialize(test_tuple)
        deserialized = cache_instance._deserialize(serialized)
        assert deserialized == [1, "two", {"three": 3}]  # 元组会被转为列表

    @pytest.mark.asyncio
    async def test_cache_serialization_pickle(self, cache_instance):
        """测试Pickle序列化."""
        class CustomObject:
            def __init__(self, value):
                self.value = value

            def __eq__(self, other):
                return isinstance(other, CustomObject) and self.value == other.value

        test_obj = CustomObject("test_value")
        serialized = cache_instance._serialize(test_obj)
        deserialized = cache_instance._deserialize(serialized)
        assert deserialized.value == test_obj.value

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_instance):
        """测试缓存设置和获取."""
        key = "test_key"
        value = {"test": "data"}

        # 设置缓存
        result = await cache_instance.set(key, value, ttl=60)
        assert result is True

        # 获取缓存
        cached_value = await cache_instance.get(key)
        assert cached_value == value

        # 检查统计
        stats = await cache_instance.get_stats()
        assert stats['sets'] >= 1
        assert stats['hits'] >= 1

    @pytest.mark.asyncio
    async def test_cache_get_nonexistent(self, cache_instance):
        """测试获取不存在的缓存."""
        result = await cache_instance.get("nonexistent_key")
        assert result is None

        # 检查miss统计
        stats = await cache_instance.get_stats()
        assert stats['misses'] >= 1

    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_instance):
        """测试缓存删除."""
        key = "test_delete_key"
        value = "test_value"

        # 先设置缓存
        await cache_instance.set(key, value)

        # 删除缓存
        result = await cache_instance.delete(key)
        assert result is True

        # 确认缓存已删除
        cached_value = await cache_instance.get(key)
        assert cached_value is None

    @pytest.mark.asyncio
    async def test_cache_exists(self, cache_instance):
        """测试缓存存在性检查."""
        key = "test_exists_key"
        value = "test_value"

        # 设置前检查
        exists = await cache_instance.exists(key)
        assert exists is False

        # 设置缓存
        await cache_instance.set(key, value)

        # 设置后检查
        exists = await cache_instance.exists(key)
        assert exists is True

    @pytest.mark.asyncio
    async def test_cache_ttl(self, cache_instance):
        """测试缓存TTL."""
        key = "test_ttl_key"
        value = "test_value"
        ttl = 60

        # 设置缓存
        await cache_instance.set(key, value, ttl=ttl)

        # 检查TTL
        remaining_ttl = await cache_instance.ttl(key)
        assert 0 < remaining_ttl <= ttl

    @pytest.mark.asyncio
    async def test_cache_expire(self, cache_instance):
        """测试缓存过期设置."""
        key = "test_expire_key"
        value = "test_value"

        # 设置缓存（无过期）
        await cache_instance.set(key, value, ttl=0)

        # 检查TTL（应该为-1，表示永不过期）
        ttl_before = await cache_instance.ttl(key)
        assert ttl_before == -1

        # 设置过期时间
        result = await cache_instance.expire(key, 60)
        assert result is True

        # 检查TTL
        ttl_after = await cache_instance.ttl(key)
        assert 0 < ttl_after <= 60

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_instance):
        """测试缓存统计."""
        # 执行一些操作
        await cache_instance.set("stat_test", "value")
        await cache_instance.get("stat_test")
        await cache_instance.get("nonexistent")

        stats = await cache_instance.get_stats()
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'sets' in stats
        assert 'hit_rate' in stats
        assert 0 <= stats['hit_rate'] <= 1

    @pytest.mark.asyncio
    async def test_cache_health_check(self, cache_instance):
        """测试健康检查."""
        health = await cache_instance.health_check()
        assert 'status' in health
        assert 'response_time' in health

    @pytest.mark.asyncio
    async def test_cache_context_manager(self):
        """测试异步上下文管理器."""
        async with RedisCache("redis://localhost:6379/1") as cache:
            # 测试基本功能
            await cache.set("context_test", "value")
            value = await cache.get("context_test")
            assert value == "value"

        # 上下文退出后，连接应该已关闭
        # 这里我们无法直接测试连接状态，但可以确保没有异常


class TestCacheFunctions:
    """缓存功能函数测试."""

    @pytest.mark.asyncio
    async def test_cache_key_builder(self):
        """测试缓存键生成器."""
        # 测试简单参数
        key = cache_key_builder("test", "arg1", param2="value2")
        assert "test" in key
        assert "arg1" in key
        assert "param2:value2" in key

        # 测试复杂参数
        complex_obj = {"key": "value"}
        key = cache_key_builder("test", complex_obj)
        assert "test" in key
        assert len(key.split(":")) >= 2

    @pytest.mark.asyncio
    async def test_global_cache_functions(self):
        """测试全局缓存函数."""
        value = {"test": "global_functions"}

        # 使用便捷函数设置缓存
        result = await cache_set("global_test", value, ttl=60)
        assert result is True

        # 使用便捷函数获取缓存
        cached_value = await cache_get("global_test")
        assert cached_value == value

        # 使用便捷函数删除缓存
        result = await cache_delete("global_test")
        assert result is True


class TestCacheDecorators:
    """缓存装饰器测试."""

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """测试基本缓存装饰器."""
        call_count = 0

        @cached(ttl=60, namespace="test")
        async def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # 模拟耗时操作
            return x * 2

        # 第一次调用 - 应该执行函数
        result1 = await test_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用 - 应该从缓存获取
        result2 = await test_function(5)
        assert result2 == 10
        assert call_count == 1  # 函数没有被再次调用

        # 不同参数 - 应该执行函数
        result3 = await test_function(10)
        assert result3 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_unless(self):
        """测试unless条件."""
        call_count = 0

        @cached(ttl=60, unless=lambda x: x > 10)
        async def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 条件为True - 跳过缓存
        result1 = await test_function(20)
        assert result1 == 40
        assert call_count == 1

        # 再次调用相同参数 - 仍然跳过缓存
        result2 = await test_function(20)
        assert result2 == 40
        assert call_count == 2

        # 条件为False - 使用缓存
        result3 = await test_function(5)
        assert result3 == 10
        assert call_count == 3

        result4 = await test_function(5)
        assert result4 == 10
        assert call_count == 3  # 没有再次调用

    @pytest.mark.asyncio
    async def test_cached_decorator_custom_key_builder(self):
        """测试自定义键生成器."""
        call_count = 0

        def custom_key(x: int) -> str:
            return f"custom:{x}"

        @cached(ttl=60, key_builder=custom_key)
        async def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3

        # 第一次调用
        result1 = await test_function(5)
        assert result1 == 15
        assert call_count == 1

        # 第二次调用 - 应该命中缓存
        result2 = await test_function(5)
        assert result2 == 15
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_long_short_medium(self):
        """测试便捷装饰器."""
        call_count = 0

        @cached_long(ttl=7200)  # 2小时
        async def long_func():
            nonlocal call_count
            call_count += 1
            return "long"

        @cached_short(ttl=30)  # 30秒
        async def short_func():
            nonlocal call_count
            call_count += 1
            return "short"

        @cached_medium(ttl=300)  # 5分钟
        async def medium_func():
            nonlocal call_count
            call_count += 1
            return "medium"

        # 测试所有函数
        assert await long_func() == "long"
        assert await short_func() == "short"
        assert await medium_func() == "medium"
        assert call_count == 3

        # 第二次调用 - 应该都从缓存获取
        assert await long_func() == "long"
        assert await short_func() == "short"
        assert await medium_func() == "medium"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_cached_method_decorator(self):
        """测试方法装饰器."""
        call_count = 0

        class TestClass:
            def __init__(self, value):
                self.value = value

            @cached_method(ttl=60, namespace="test_method")
            async def get_value(self) -> int:
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.01)
                return self.value * 2

        # 测试实例缓存
        instance1 = TestClass(10)
        instance2 = TestClass(20)

        # 第一次调用
        result1a = await instance1.get_value()
        result2a = await instance2.get_value()
        assert result1a == 20
        assert result2a == 40
        assert call_count == 2

        # 第二次调用 - 应该命中缓存
        result1b = await instance1.get_value()
        result2b = await instance2.get_value()
        assert result1b == 20
        assert result2b == 40
        assert call_count == 2  # 没有再次调用


class TestBatchCache:
    """批量缓存操作测试."""

    @pytest.mark.asyncio
    async def test_batch_cache_get_many(self):
        """测试批量获取."""
        batch_cache = BatchCache()

        # 模拟一些缓存数据（通过直接操作Redis）
        cache = await get_cache()
        test_data = {
            "batch_key1": "value1",
            "batch_key2": {"nested": "data"},
            "batch_key3": [1, 2, 3]
        }

        for key, value in test_data.items():
            await cache.set(key, value, ttl=60)

        # 批量获取
        keys = list(test_data.keys())
        results = await batch_cache.get_many(keys)

        assert len(results) == len(test_data)
        for key, expected_value in test_data.items():
            assert key in results
            assert results[key] == expected_value

    @pytest.mark.asyncio
    async def test_batch_cache_set_many(self):
        """测试批量设置."""
        batch_cache = BatchCache()

        test_data = {
            "batch_set1": "value1",
            "batch_set2": {"nested": "data"},
            "batch_set3": [1, 2, 3]
        }

        # 批量设置
        results = await batch_cache.set_many(test_data, ttl=60)
        assert len(results) == len(test_data)
        for key in test_data:
            assert results.get(key, False) is True

        # 验证设置成功
        cache = await get_cache()
        for key, expected_value in test_data.items():
            cached_value = await cache.get(key)
            assert cached_value == expected_value

    @pytest.mark.asyncio
    async def test_batch_cache_delete_many(self):
        """测试批量删除."""
        batch_cache = BatchCache()
        cache = await get_cache()

        # 设置一些数据
        test_keys = ["batch_del1", "batch_del2", "batch_del3"]
        for key in test_keys:
            await cache.set(key, f"value_{key}", ttl=60)

        # 验证数据存在
        for key in test_keys:
            assert await cache.get(key) is not None

        # 批量删除
        results = await batch_cache.delete_many(test_keys)
        assert len(results) == len(test_keys)

        # 验证删除成功
        for key in test_keys:
            assert await cache.get(key) is None


class TestCacheErrorHandling:
    """缓存错误处理测试."""

    @pytest.mark.asyncio
    async def test_cache_graceful_degradation(self):
        """测试优雅降级."""
        # 使用无效的Redis URL
        cache = RedisCache("redis://invalid-host:6379/0")

        # 所有操作都应该优雅失败，不抛出异常
        assert await cache.get("test_key") is None
        assert await cache.set("test_key", "test_value") is False
        assert await cache.delete("test_key") is False
        assert await cache.exists("test_key") is False

    @pytest.mark.asyncio
    async def test_cache_serialization_error(self):
        """测试序列化错误处理."""
        cache = RedisCache("redis://localhost:6379/1")

        # 创建无法序列化的对象（通过mock模拟）
        class UnserializableObject:
            def __reduce__(self):
                raise TypeError("Cannot serialize")

        obj = UnserializableObject()

        # 序列化应该抛出CacheSerializationError
        with pytest.raises(CacheSerializationError):
            cache._serialize(obj)

    @pytest.mark.asyncio
    async def test_non_async_function_error(self):
        """测试非异步函数错误."""
        with pytest.raises(TypeError):
            @cached()
            def sync_function():
                return "sync"


class TestCachePerformance:
    """缓存性能测试."""

    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self):
        """测试缓存性能提升."""
        call_count = 0

        @cached(ttl=60, namespace="performance")
        async def expensive_operation(delay: float = 0.1) -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(delay)
            return "result"

        # 第一次调用 - 应该较慢
        import time
        start_time = time.time()
        result1 = await expensive_operation()
        first_duration = time.time() - start_time

        # 第二次调用 - 应该很快
        start_time = time.time()
        result2 = await expensive_operation()
        second_duration = time.time() - start_time

        # 验证结果一致性
        assert result1 == result2
        assert call_count == 1  # 函数只被调用一次

        # 验证性能提升（第二次应该快很多）
        assert second_duration < first_duration / 2
        assert second_duration < 0.01  # 应该小于10ms

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """测试并发缓存访问."""
        call_count = 0

        @cached(ttl=60, namespace="concurrent", stampede_protection=True)
        async def concurrent_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # 模拟耗时操作
            return x * 2

        # 并发调用相同参数
        tasks = [concurrent_function(5) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # 验证结果
        assert all(result == 10 for result in results)

        # 由于击穿保护，函数应该只被调用一次
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """测试缓存失效."""
        call_count = 0

        @cached(ttl=60, namespace="invalidate")
        async def test_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3

        # 第一次调用
        result1 = await test_func(5)
        assert result1 == 15
        assert call_count == 1

        # 第二次调用 - 应该命中缓存
        result2 = await test_func(5)
        assert result2 == 15
        assert call_count == 1

        # 使缓存失效
        await test_func.invalidate(5)

        # 第三次调用 - 应该重新执行函数
        result3 = await test_func(5)
        assert result3 == 15
        assert call_count == 2


if __name__ == "__main__":
    pytest.main([__file__])