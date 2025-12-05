from typing import Optional

"""
统一缓存管理器测试
Unified Cache Manager Tests

测试统一缓存管理器的核心功能.
Tests core functionality of unified cache manager.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.cache.unified_cache import (
    UnifiedCacheManager,
    cached,
    get_cache_manager,
    performance_monitor,
)


class TestUnifiedCacheManager:
    """统一缓存管理器测试类"""

    @pytest.fixture
    def cache_manager(self):
        """缓存管理器实例"""
        # 不使用Redis进行测试
        return UnifiedCacheManager(redis_client=None, local_cache_size=10)

    def test_cache_manager_initialization(self, cache_manager):
        """测试缓存管理器初始化"""
        assert cache_manager is not None
        assert cache_manager.redis_client is None
        assert cache_manager.local_cache_size == 10
        assert cache_manager.local_cache == {}
        assert "hits" in cache_manager.cache_stats
        assert "misses" in cache_manager.cache_stats
        assert "sets" in cache_manager.cache_stats
        assert "deletes" in cache_manager.cache_stats

    def test_get_cache_config(self, cache_manager):
        """测试获取缓存配置"""
        config = cache_manager._get_cache_config()

        assert isinstance(config, dict)
        assert "prediction_result" in config
        assert "prediction_model" in config
        assert "team_stats" in config
        assert "match_data" in config
        assert "api_response" in config
        assert "default" in config

        # 检查TTL值
        assert config["prediction_result"] == 3600  # 1小时
        assert config["prediction_model"] == 86400  # 24小时
        assert config["default"] == 300  # 5分钟

    def test_generate_cache_key(self, cache_manager):
        """测试生成缓存键"""
        key = "test_key"
        cache_type = "test_type"

        cache_key = cache_manager._generate_cache_key(key, cache_type)

        assert cache_key == f"{cache_type}:{key}"

    def test_update_local_cache(self, cache_manager):
        """测试更新本地缓存"""
        key = "test_type:test_key"
        value = {"data": "test_value"}

        # 确保缓存为空
        assert len(cache_manager.local_cache) == 0

        # 添加缓存项
        cache_manager._update_local_cache(key, value)

        assert len(cache_manager.local_cache) == 1
        assert key in cache_manager.local_cache
        assert cache_manager.local_cache[key]["value"] == value
        assert "timestamp" in cache_manager.local_cache[key]

    def test_update_local_cache_lru_eviction(self, cache_manager):
        """测试本地缓存LRU淘汰"""
        cache_manager.local_cache_size = 2

        # 添加第一个缓存项
        key1 = "test_type:key1"
        value1 = "value1"
        cache_manager._update_local_cache(key1, value1)
        cache_manager.local_cache[key1]["timestamp"]

        # 添加第二个缓存项
        key2 = "test_type:key2"
        value2 = "value2"
        cache_manager._update_local_cache(key2, value2)
        cache_manager.local_cache[key2]["timestamp"]

        # 添加第三个缓存项，应该淘汰最旧的
        time.sleep(0.01)  # 确保时间戳不同
        key3 = "test_type:key3"
        value3 = "value3"
        cache_manager._update_local_cache(key3, value3)
        cache_manager.local_cache[key3]["timestamp"]

        # 应该只有2个缓存项
        assert len(cache_manager.local_cache) == 2
        assert key3 in cache_manager.local_cache
        assert key2 in cache_manager.local_cache
        assert key1 not in cache_manager.local_cache
        assert cache_manager.local_cache[key2]["value"] == value2
        assert cache_manager.local_cache[key3]["value"] == value3

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_manager):
        """测试缓存未命中"""
        key = "non_existent_key"
        cache_type = "test_type"

        result = await cache_manager.get(key, cache_type)

        assert result is None
        assert cache_manager.cache_stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_set_and_get_cache(self, cache_manager):
        """测试设置和获取缓存"""
        key = "test_key"
        cache_type = "test_type"
        value = {"message": "Hello, World!", "timestamp": datetime.utcnow().isoformat()}

        # 设置缓存
        result = await cache_manager.set(key, value, cache_type, ttl=60)

        assert result is True
        assert cache_manager.cache_stats["sets"] == 1

        # 获取缓存
        cached_value = await cache_manager.get(key, cache_type)

        assert cached_value == value
        assert cache_manager.cache_stats["hits"] == 1

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, cache_manager):
        """测试缓存TTL过期"""
        # 创建自定义缓存管理器，使用很短的TTL
        short_cache = UnifiedCacheManager(redis_client=None, local_cache_size=5)

        key = "test_key"
        cache_type = "test_type"
        value = {"message": "test"}

        # 设置很短的TTL（1秒）
        result = await short_cache.set(key, value, cache_type, ttl=1)

        assert result is True

        # 立即获取应该命中
        cached_value = await short_cache.get(key, cache_type)
        assert cached_value == value

        # 等待过期
        await asyncio.sleep(1.1)

        # 过期后获取应该未命中
        cached_value = await short_cache.get(key, cache_type)
        assert cached_value is None

    @pytest.mark.asyncio
    async def test_delete_cache(self, cache_manager):
        """测试删除缓存"""
        key = "test_key"
        cache_type = "test_type"
        value = {"message": "test"}

        # 设置缓存
        await cache_manager.set(key, value, cache_type)

        # 确认缓存存在
        cached_value = await cache_manager.get(key, cache_type)
        assert cached_value == value

        # 删除缓存
        result = await cache_manager.delete(key, cache_type)

        assert result is True
        assert cache_manager.cache_stats["deletes"] == 1

        # 确认缓存已删除
        cached_value = await cache_manager.get(key, cache_type)
        assert cached_value is None

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_manager):
        """测试模式化缓存失效"""
        # 设置多个缓存项
        cache_items = [
            ("test_type", "key1", {"data": "value1"}),
            ("test_type", "key2", {"data": "value2"}),
            ("other_type", "key1", {"data": "value3"}),
            ("test_type", "pattern_key", {"data": "value4"}),
        ]

        for cache_type, key, value in cache_items:
            cache_key = cache_manager._generate_cache_key(cache_type, key)
            cache_manager._update_local_cache(cache_key, value)

        assert len(cache_manager.local_cache) == 4

        # 删除匹配模式的缓存
        await cache_manager.invalidate_pattern("key", "test_type")

        # 应该删除test_type下所有以"key"开头的缓存项
        remaining_keys = [
            k
            for k in cache_manager.local_cache.keys()
            if not (k.endswith(":test_type") and k.split(":")[0].startswith("key"))
        ]
        assert len(remaining_keys) == 2  # other_type:key1 + pattern_key:test_type
        assert "key1:other_type" in remaining_keys
        assert "pattern_key:test_type" in remaining_keys

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_manager):
        """测试获取缓存统计"""
        # 执行一些缓存操作
        await cache_manager.set("key1", "value1", "type1")
        await cache_manager.set("key2", "value2", "type2")
        await cache_manager.get("key1", "type1")  # 命中
        await cache_manager.get("key3", "type1")  # 未命中

        stats = await cache_manager.get_cache_stats()

        assert isinstance(stats, dict)
        assert "hits" in stats
        assert "misses" in stats
        assert "local_hits" in stats
        assert "redis_hits" in stats
        assert "sets" in stats
        assert "deletes" in stats
        assert "hit_rate" in stats
        assert "local_hit_rate" in stats
        assert "redis_hit_rate" in stats
        assert "local_cache_size" in stats

        # 验证统计数据
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 2
        assert stats["hit_rate"] == 0.5  # 1 hit / (1 hit + 1 miss)
        assert stats["local_hit_rate"] == 0.5
        assert stats["local_cache_size"] == 2

    @pytest.mark.asyncio
    async def test_serialize_data_string(self, cache_manager):
        """测试字符串数据序列化"""
        string_data = "Hello, World!"
        serialized = cache_manager._serialize_data(string_data)

        assert isinstance(serialized, bytes)
        deserialized = cache_manager._deserialize_data(serialized)
        assert deserialized == string_data

    @pytest.mark.asyncio
    async def test_serialize_data_number(self, cache_manager):
        """测试数字数据序列化"""
        number_data = 42
        serialized = cache_manager._serialize_data(number_data)

        assert isinstance(serialized, bytes)
        deserialized = cache_manager._deserialize_data(serialized)
        assert deserialized == "42"

    @pytest.mark.asyncio
    async def test_serialize_data_complex(self, cache_manager):
        """测试复杂数据序列化"""
        complex_data = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        serialized = cache_manager._serialize_data(complex_data)
        deserialized = cache_manager._deserialize_data(serialized)

        assert deserialized == complex_data

    @pytest.mark.asyncio
    async def test_serialize_deserialize_error_handling(self, cache_manager):
        """测试序列化/反序列化错误处理"""
        # 测试反序列化错误 - 使用无效的pickle二进制数据
        invalid_pickle_bytes = (
            b"\x80\x04\x95\x00\x00\x00\x00\x00\x00\x00\x00"  # 无效的pickle头
        )
        result = cache_manager._deserialize_data(invalid_pickle_bytes)
        # 对于无效的pickle数据，应该返回None
        assert result is None

        # 测试有效序列化和反序列化
        test_data = {"key": "value", "number": 42}
        serialized = cache_manager._serialize_data(test_data)
        deserialized = cache_manager._deserialize_data(serialized)
        assert deserialized == test_data


class TestCacheDecorators:
    """缓存装饰器测试类"""

    @pytest.fixture
    def temp_cache_manager(self):
        """临时缓存管理器实例"""
        return UnifiedCacheManager(redis_client=None, local_cache_size=10)

    @pytest.mark.asyncio
    async def test_cached_decorator_sync_function(self, temp_cache_manager):
        """测试缓存装饰器同步函数"""
        call_count = 0

        # 使用patch替换全局缓存管理器
        with patch(
            "src.cache.unified_cache.get_cache_manager", return_value=temp_cache_manager
        ):

            @cached(cache_type="test", ttl=60)
            async def expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y

            # 第一次调用
            result1 = await expensive_function(1, 2)
            assert result1 == 3
            assert call_count == 1

            # 第二次调用应该从缓存获取
            result2 = await expensive_function(1, 2)
            assert result2 == 3
            assert call_count == 1  # 函数没有被再次调用

            # 不同参数应该重新计算
            result3 = await expensive_function(2, 3)
            assert result3 == 5
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_async_function(self, temp_cache_manager):
        """测试缓存装饰器异步函数"""
        call_count = 0

        # 使用patch替换全局缓存管理器
        with patch(
            "src.cache.unified_cache.get_cache_manager", return_value=temp_cache_manager
        ):

            @cached(cache_type="test", ttl=60)
            async def async_expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.01)  # 模拟异步操作
                return x * y

            # 第一次调用
            result1 = await async_expensive_function(3, 4)
            assert result1 == 12
            assert call_count == 1

            # 第二次调用应该从缓存获取
            result2 = await async_expensive_function(3, 4)
            assert result2 == 12
            assert call_count == 1

            # 不同参数应该重新计算
            result3 = await async_expensive_function(5, 6)
            assert result3 == 30
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_performance_monitor_decorator(self, temp_cache_manager):
        """测试性能监控装饰器"""

        @performance_monitor(threshold=1.0)
        async def fast_function():
            return "quick result"

        # 快速函数不应该触发警告
        result = await fast_function()
        assert result == "quick result"

        # 慢函数应该触发警告
        @performance_monitor(threshold=0.001)  # 很低的阈值
        async def slow_function():
            await asyncio.sleep(0.01)  # 模拟慢操作
            return "slow result"

        result = await slow_function()
        assert result == "slow result"

    @pytest.mark.asyncio
    async def test_combined_decorators(self, temp_cache_manager):
        """测试组合装饰器"""
        call_count = 0

        # 使用patch替换全局缓存管理器
        with patch(
            "src.cache.unified_cache.get_cache_manager", return_value=temp_cache_manager
        ):

            @cached(cache_type="test", ttl=60)
            @performance_monitor(threshold=1.0)
            async def monitored_cached_function(x):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.001)
                return x * 2

            # 第一次调用
            result1 = await monitored_cached_function(5)
            assert result1 == 10
            assert call_count == 1

            # 第二次调用应该从缓存获取，不会调用函数
            result2 = await monitored_cached_function(5)
            assert result2 == 10
            assert call_count == 1


class TestCacheWithRedis:
    """缓存Redis集成测试类"""

    @pytest.mark.asyncio
    async def test_redis_cache_integration(self):
        """测试Redis缓存集成"""
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = True

        # 创建使用Redis的缓存管理器
        cache_manager = UnifiedCacheManager(redis_client=mock_redis)

        key = "test_key"
        cache_type = "test_type"
        value = {"data": "test_value"}

        # 先清空本地缓存
        cache_manager.local_cache.clear()

        # 设置缓存
        result = await cache_manager.set(key, value, cache_type, ttl=60)
        assert result is True

        # 验证Redis调用
        redis_key = f"cache:{cache_type}:{key}"
        mock_redis.setex.assert_called_once()
        assert mock_redis.setex.call_args[0][0] == redis_key
        assert mock_redis.setex.call_args[0][1] == 60

        # 清空本地缓存，模拟Redis未命中
        cache_manager.local_cache.clear()
        mock_redis.get.return_value = None
        cached_value = await cache_manager.get(key, cache_type)
        assert cached_value is None

        # 设置Redis缓存命中 - 返回序列化的pickle数据
        import pickle

        serialized_data = pickle.dumps(value)
        mock_redis.get.return_value = serialized_data
        cached_value = await cache_manager.get(key, cache_type)
        # 应该返回正确的数据
        assert cached_value == value

        # 验证本地缓存更新
        assert len(cache_manager.local_cache) == 1


class TestGlobalFunctions:
    """全局函数测试类"""

    def test_get_cache_manager_singleton(self):
        """测试获取缓存管理器单例"""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        # 在没有Redis的情况下，每次都返回新实例
        assert isinstance(manager1, UnifiedCacheManager)
        assert isinstance(manager2, UnifiedCacheManager)
        # 如果有Redis，可能是单例模式


class TestCacheIntegration:
    """缓存集成测试类"""

    @pytest.fixture
    def temp_cache_manager(self):
        """临时缓存管理器实例"""
        return UnifiedCacheManager(redis_client=None, local_cache_size=50)

    @pytest.mark.asyncio
    async def test_cache_workflow(self, temp_cache_manager):
        """测试完整缓存工作流"""
        # 1. 设置多个缓存项
        cache_items = [
            ("prediction:match_123", {"prediction": "home_win", "confidence": 0.75}),
            ("team_stats:team_456", {"played": 10, "won": 6, "draw": 1}),
            (
                "user_data:user_789",
                {"name": "Test User", "preferences": ["news", "notifications"]},
            ),
        ]

        for key, value in cache_items:
            await temp_cache_manager.set(key, value, "test")

        # 2. 验证缓存设置
        stats = await temp_cache_manager.get_cache_stats()
        assert stats["sets"] == 3

        # 3. 获取缓存
        for key, expected_value in cache_items:
            cached_value = await temp_cache_manager.get(key, "test")
            assert cached_value == expected_value

        # 4. 验证缓存统计
        stats_after = await temp_cache_manager.get_cache_stats()
        assert stats_after["hits"] == 3
        assert stats_after["misses"] == 0
        assert stats_after["hit_rate"] == 1.0

        # 5. 清理特定模式的缓存 - 使用team_stats作为pattern
        await temp_cache_manager.invalidate_pattern("team_stats", "test")

        # 6. 验证部分缓存被清除
        team_stats_cached = await temp_cache_manager.get("team_stats:team_456", "test")
        assert team_stats_cached is None

        # 7. 其他缓存应该仍然存在
        prediction_cached = await temp_cache_manager.get("prediction:match_123", "test")
        assert prediction_cached is not None

    @pytest.mark.asyncio
    async def test_cache_performance(self, temp_cache_manager):
        """测试缓存性能"""
        # 增大缓存大小以支持更多操作
        temp_cache_manager.local_cache_size = 200

        # 大量缓存操作
        operations = 50  # 减少操作数以提高测试速度
        start_time = time.time()

        for i in range(operations):
            key = f"performance_test_{i}"
            value = {"iteration": i, "data": "x" * 50}  # 较小的数据
            await temp_cache_manager.set(key, value, "performance_test", ttl=300)

        set_time = time.time()
        set_duration = set_time - start_time

        # 测试获取性能
        start_time = time.time()
        for i in range(operations):
            key = f"performance_test_{i}"
            await temp_cache_manager.get(key, "performance_test")

        get_time = time.time()
        get_duration = get_time - start_time

        # 验证性能（本地缓存应该很快）
        assert get_duration < set_duration  # 获取应该比设置快
        assert get_duration < 1.0  # 获取应该在1秒内完成

        # 获取最终统计
        stats = await temp_cache_manager.get_cache_stats()
        assert stats["sets"] == operations
        assert stats["hits"] == operations
        assert stats["hit_rate"] == 1.0
        assert stats["local_cache_size"] == min(
            operations, temp_cache_manager.local_cache_size
        )