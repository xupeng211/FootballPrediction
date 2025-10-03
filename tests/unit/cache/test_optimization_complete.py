"""
缓存优化模块测试
Cache Optimization Module Tests

测试src/cache/optimization.py的主要功能
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta


class TestCacheLevel:
    """测试缓存级别枚举"""

    def test_cache_level_values(self):
        """测试缓存级别值"""
        from src.cache.optimization import CacheLevel

        assert CacheLevel.L1_MEMORY.value == 1
        assert CacheLevel.L2_REDIS.value == 2
        assert CacheLevel.L3_DATABASE.value == 3


class TestEvictionPolicy:
    """测试淘汰策略枚举"""

    def test_eviction_policy_values(self):
        """测试淘汰策略值"""
        from src.cache.optimization import EvictionPolicy

        assert EvictionPolicy.LRU.value == "lru"
        assert EvictionPolicy.LFU.value == "lfu"
        assert EvictionPolicy.TTL.value == "ttl"
        assert EvictionPolicy.FIFO.value == "fifo"


class TestCacheConfig:
    """测试缓存配置"""

    def test_default_config(self):
        """测试默认配置"""
        from src.cache.optimization import CacheConfig

        config = CacheConfig()
        assert config.l1_max_size == 1000
        assert config.l1_ttl == 300
        assert config.l2_ttl == 1800
        assert config.l2_max_memory == "100mb"
        assert config.preload_keys == []
        assert config.preload_batch_size == 100
        assert config.metrics_enabled is True
        assert config.stats_interval == 60

    def test_custom_config(self):
        """测试自定义配置"""
        from src.cache.optimization import CacheConfig

        config = CacheConfig(
            l1_max_size=2000,
            l1_ttl=600,
            preload_keys=["key1", "key2"]
        )
        assert config.l1_max_size == 2000
        assert config.l1_ttl == 600
        assert config.preload_keys == ["key1", "key2"]


class TestCacheStats:
    """测试缓存统计"""

    def test_stats_initialization(self):
        """测试统计初始化"""
        from src.cache.optimization import CacheStats

        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.evictions == 0
        assert stats.errors == 0
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        """测试命中率计算"""
        from src.cache.optimization import CacheStats

        stats = CacheStats()

        # 没有请求时
        assert stats.hit_rate == 0.0

        # 有命中和未命中
        stats.hits = 8
        stats.misses = 2
        assert stats.hit_rate == 0.8

        # 全部命中
        stats.hits = 10
        stats.misses = 0
        assert stats.hit_rate == 1.0

    def test_stats_reset(self):
        """测试统计重置"""
        from src.cache.optimization import CacheStats

        stats = CacheStats()
        stats.hits = 10
        stats.misses = 5
        stats.sets = 8

        old_last_reset = stats.last_reset
        time.sleep(0.01)  # 确保时间差

        stats.reset()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.last_reset > old_last_reset

    def test_stats_to_dict(self):
        """测试统计转换为字典"""
        from src.cache.optimization import CacheStats

        stats = CacheStats()
        stats.hits = 10
        stats.misses = 5
        stats.errors = 1

        result = stats.to_dict()

        assert isinstance(result, dict)
        assert result["hits"] == 10
        assert result["misses"] == 5
        assert result["errors"] == 1
        assert "hit_rate" in result
        assert "uptime" in result


class TestMemoryCache:
    """测试内存缓存"""

    def test_cache_initialization(self):
        """测试缓存初始化"""
        from src.cache.optimization import MemoryCache, EvictionPolicy

        cache = MemoryCache(max_size=100, ttl=600, eviction_policy=EvictionPolicy.LRU)
        assert cache.max_size == 100
        assert cache.ttl == 600
        assert cache.eviction_policy == EvictionPolicy.LRU
        assert len(cache._cache) == 0

    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        from src.cache.optimization import MemoryCache

        cache = MemoryCache()

        # 设置值
        result = cache.set("key1", "value1")
        assert result is True

        # 获取值
        value = cache.get("key1")
        assert value == "value1"

        # 获取不存在的值
        value = cache.get("nonexistent")
        assert value is None

    def test_cache_ttl_expiration(self):
        """测试TTL过期"""
        from src.cache.optimization import MemoryCache

        cache = MemoryCache(ttl=1)  # 1秒过期

        # 设置值
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 等待过期
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_custom_ttl(self):
        """测试自定义TTL"""
        from src.cache.optimization import MemoryCache

        cache = MemoryCache(ttl=10)  # 10秒默认TTL

        # 设置短TTL的值
        cache.set("key1", "value1", ttl=1)
        time.sleep(1.1)
        assert cache.get("key1") is None

        # 设置长TTL的值
        cache.set("key2", "value2", ttl=5)
        assert cache.get("key2") == "value2"

    def test_cache_delete(self):
        """测试缓存删除"""
        from src.cache.optimization import MemoryCache

        cache = MemoryCache()

        # 删除不存在的键
        result = cache.delete("nonexistent")
        assert result is False

        # 设置并删除存在的键
        cache.set("key1", "value1")
        result = cache.delete("key1")
        assert result is True

        # 确认已删除
        value = cache.get("key1")
        assert value is None

    def test_cache_clear(self):
        """测试清空缓存"""
        from src.cache.optimization import MemoryCache

        cache = MemoryCache()

        # 添加多个值
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert len(cache._cache) == 2

        # 清空缓存
        cache.clear()
        assert len(cache._cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_lru_eviction(self):
        """测试LRU淘汰策略"""
        from src.cache.optimization import MemoryCache, EvictionPolicy

        cache = MemoryCache(max_size=2, eviction_policy=EvictionPolicy.LRU)

        # 填满缓存
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert len(cache._cache) == 2

        # 访问key1（使其成为最近使用）
        cache.get("key1")

        # 添加新键，应该淘汰key2
        cache.set("key3", "value3")
        assert len(cache._cache) == 2
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    def test_cache_statistics(self):
        """测试缓存统计"""
        from src.cache.optimization import MemoryCache

        cache = MemoryCache()

        # 初始统计
        assert cache._stats.hits == 0
        assert cache._stats.misses == 0

        # 命中
        cache.set("key1", "value1")
        cache.get("key1")
        assert cache._stats.hits == 1

        # 未命中
        cache.get("nonexistent")
        assert cache._stats.misses == 1

        # 设置
        assert cache._stats.sets == 1

        # 删除
        cache.delete("key1")
        assert cache._stats.deletes == 1

    def test_cache_error_handling(self):
        """测试缓存错误处理"""
        from src.cache.optimization import MemoryCache

        cache = MemoryCache()

        # 模拟内部错误（通过破坏内部数据结构）
        original_cache = cache._cache
        cache._cache = None

        # 应该优雅地处理错误
        value = cache.get("key1")
        assert value is None
        assert cache._stats.errors > 0

        # 恢复
        cache._cache = original_cache


class TestMultiLevelCache:
    """测试多级缓存"""

    def test_multilevel_cache_initialization(self):
        """测试多级缓存初始化"""
        from src.cache.optimization import MultiLevelCache, CacheConfig

        config = CacheConfig()
        with patch('src.cache.optimization.RedisManager') as mock_redis:
            cache = MultiLevelCache(config, redis_manager=None)
            assert cache.config == config
            assert cache.l1_cache is not None
            assert cache.l2_cache is None

    def test_multilevel_cache_get_l1_hit(self):
        """测试L1缓存命中"""
        from src.cache.optimization import MultiLevelCache, CacheConfig

        config = CacheConfig()
        with patch('src.cache.optimization.RedisManager'):
            cache = MultiLevelCache(config, redis_manager=None)

            # 设置值到L1
            cache.l1_cache.set("key1", "value1")

            # 获取值（应该从L1命中）
            value = cache.get("key1")
            assert value == "value1"

    def test_multilevel_cache_get_l2_hit(self):
        """测试L2缓存命中"""
        from src.cache.optimization import MultiLevelCache, CacheConfig

        config = CacheConfig()
        mock_redis_manager = Mock()
        mock_redis_manager.get.return_value = b'"value2"'

        with patch('src.cache.optimization.RedisManager'):
            cache = MultiLevelCache(config, redis_manager=mock_redis_manager)
            cache.l2_cache = mock_redis_manager

            # L1没有，L2有
            value = cache.get("key2")
            assert value == "value2"

            # 应该回填到L1
            assert cache.l1_cache.get("key2") == "value2"

    def test_multilevel_cache_set(self):
        """测试多级缓存设置"""
        from src.cache.optimization import MultiLevelCache, CacheConfig

        config = CacheConfig()
        mock_redis_manager = Mock()

        with patch('src.cache.optimization.RedisManager'):
            cache = MultiLevelCache(config, redis_manager=mock_redis_manager)
            cache.l2_cache = mock_redis_manager

            # 设置值
            cache.set("key1", "value1")

            # 应该设置到L1
            assert cache.l1_cache.get("key1") == "value1"

            # 应该设置到L2
            mock_redis_manager.setex.assert_called()

    def test_multilevel_cache_delete(self):
        """测试多级缓存删除"""
        from src.cache.optimization import MultiLevelCache, CacheConfig

        config = CacheConfig()
        mock_redis_manager = Mock()

        with patch('src.cache.optimization.RedisManager'):
            cache = MultiLevelCache(config, redis_manager=mock_redis_manager)
            cache.l2_cache = mock_redis_manager

            # 设置并删除
            cache.set("key1", "value1")
            cache.delete("key1")

            # L1和L2都应该删除
            assert cache.l1_cache.get("key1") is None
            mock_redis_manager.delete.assert_called_with("key1")

    def test_multilevel_cache_clear(self):
        """测试多级缓存清空"""
        from src.cache.optimization import MultiLevelCache, CacheConfig

        config = CacheConfig()
        mock_redis_manager = Mock()

        with patch('src.cache.optimization.RedisManager'):
            cache = MultiLevelCache(config, redis_manager=mock_redis_manager)
            cache.l2_cache = mock_redis_manager

            # 设置值并清空
            cache.set("key1", "value1")
            cache.clear()

            # L1和L2都应该清空
            assert len(cache.l1_cache._cache) == 0
            mock_redis_manager.flushdb.assert_called()


class TestCacheWarmer:
    """测试缓存预热器"""

    @pytest.mark.asyncio
    async def test_cache_warmer_initialization(self):
        """测试缓存预热器初始化"""
        from src.cache.optimization import CacheWarmer, MultiLevelCache, CacheConfig

        config = CacheConfig()
        with patch('src.cache.optimization.MultiLevelCache') as mock_cache:
            warmer = CacheWarmer(mock_cache.return_value, config)
            assert warmer.cache == mock_cache.return_value
            assert warmer.config == config

    @pytest.mark.asyncio
    async def test_preload_single_batch(self):
        """测试单批次预热"""
        from src.cache.optimization import CacheWarmer, CacheConfig

        config = CacheConfig(preload_batch_size=2)
        mock_cache = AsyncMock()
        mock_cache.get.side_effect = [None, "value1", None, "value2"]

        # 模拟数据源
        async def mock_data_source(keys):
            return {"key1": "value1", "key2": "value2"}

        warmer = CacheWarmer(mock_cache, config)
        warmer.data_source = mock_data_source

        # 预热
        await warmer.preload_batch(["key1", "key2"])

        # 验证缓存设置
        assert mock_cache.set.call_count == 2

    @pytest.mark.asyncio
    async def test_preload_multiple_batches(self):
        """测试多批次预热"""
        from src.cache.optimization import CacheWarmer, CacheConfig

        config = CacheConfig(preload_batch_size=2, preload_keys=["key1", "key2", "key3", "key4"])
        mock_cache = AsyncMock()

        async def mock_data_source(keys):
            return {f"{k}": f"value_{k}" for k in keys}

        warmer = CacheWarmer(mock_cache, config)
        warmer.data_source = mock_data_source

        # 预热所有键
        await warmer.preload_all()

        # 验证分批处理
        assert mock_cache.set.call_count == 4

    @pytest.mark.asyncio
    async def test_preload_with_errors(self):
        """测试预热时的错误处理"""
        from src.cache.optimization import CacheWarmer, CacheConfig

        config = CacheConfig()
        mock_cache = AsyncMock()
        mock_cache.set.side_effect = Exception("Cache error")

        async def mock_data_source(keys):
            return {"key1": "value1"}

        warmer = CacheWarmer(mock_cache, config)
        warmer.data_source = mock_data_source

        # 预热应该优雅地处理错误
        await warmer.preload_batch(["key1"])

        # 即使出错，也应该继续


class TestCacheOptimizer:
    """测试缓存优化器"""

    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        from src.cache.optimization import CacheOptimizer, MultiLevelCache, CacheConfig

        config = CacheConfig()
        with patch('src.cache.optimization.MultiLevelCache') as mock_cache:
            optimizer = CacheOptimizer(mock_cache.return_value, config)
            assert optimizer.cache == mock_cache.return_value
            assert optimizer.config == config

    def test_analyze_cache_performance(self):
        """测试缓存性能分析"""
        from src.cache.optimization import CacheOptimizer, MultiLevelCache, CacheConfig

        config = CacheConfig()
        mock_cache = Mock()
        mock_cache.l1_cache._stats.hits = 80
        mock_cache.l1_cache._stats.misses = 20
        mock_cache.l1_cache._stats.errors = 0

        optimizer = CacheOptimizer(mock_cache, config)
        analysis = optimizer.analyze_performance()

        assert "l1_hit_rate" in analysis
        assert "recommendations" in analysis
        assert analysis["l1_hit_rate"] == 0.8

    def test_optimize_recommendations(self):
        """测试优化建议"""
        from src.cache.optimization import CacheOptimizer, MultiLevelCache, CacheConfig

        config = CacheConfig()
        mock_cache = Mock()

        # 模拟低命中率
        mock_cache.l1_cache._stats.hits = 30
        mock_cache.l1_cache._stats.misses = 70
        mock_cache.l1_cache._stats.errors = 5

        optimizer = CacheOptimizer(mock_cache, config)
        recommendations = optimizer.get_optimization_recommendations()

        assert isinstance(recommendations, list)
        # 低命中率应该有增加缓存大小的建议
        assert any("increase" in rec.lower() or "size" in rec.lower() for rec in recommendations)

    def test_auto_optimize(self):
        """测试自动优化"""
        from src.cache.optimization import CacheOptimizer, MultiLevelCache, CacheConfig

        config = CacheConfig()
        mock_cache = Mock()
        mock_cache.l1_cache.max_size = 1000

        optimizer = CacheOptimizer(mock_cache, config)

        # 模拟需要优化
        with patch.object(optimizer, 'get_optimization_recommendations', return_value=["Increase cache size"]):
            with patch.object(optimizer, 'apply_optimization') as mock_apply:
                optimizer.auto_optimize()
                mock_apply.assert_called_with(["Increase cache size"])


class TestCacheUtilities:
    """测试缓存工具函数"""

    def test_get_cache_manager(self):
        """测试获取缓存管理器"""
        from src.cache.optimization import get_cache_manager

        # 没有初始化时应该返回None
        manager = get_cache_manager()
        assert manager is None

    def test_init_cache_manager(self):
        """测试初始化缓存管理器"""
        from src.cache.optimization import init_cache_manager, get_cache_manager, CacheConfig

        config = CacheConfig()

        with patch('src.cache.optimization.MultiLevelCache') as mock_cache:
            init_cache_manager(config)

            # 验证管理器已设置
            manager = get_cache_manager()
            assert manager is not None
            mock_cache.assert_called_once()

    def test_cached_decorator(self):
        """测试缓存装饰器"""
        from src.cache.optimization import cached

        # 模拟缓存管理器
        mock_cache = Mock()
        mock_cache.get.return_value = None

        with patch('src.cache.optimization.get_cache_manager', return_value=mock_cache):
            @cached(ttl=300, key_prefix="test")
            def expensive_function(x):
                return x * 2

            # 第一次调用
            result = expensive_function(5)
            assert result == 10
            mock_cache.set.assert_called()

            # 重置mock
            mock_cache.get.return_value = 10

            # 第二次调用（从缓存）
            result = expensive_function(5)
            assert result == 10


class TestCacheIntegration:
    """测试缓存集成场景"""

    @pytest.mark.asyncio
    async def test_end_to_end_caching(self):
        """测试端到端缓存流程"""
        from src.cache.optimization import CacheConfig, MultiLevelCache, CacheWarmer, CacheOptimizer

        # 创建配置
        config = CacheConfig(
            l1_max_size=10,
            l1_ttl=60,
            preload_keys=["key1", "key2"]
        )

        # 创建多级缓存
        with patch('src.cache.optimization.RedisManager'):
            cache = MultiLevelCache(config, redis_manager=None)

            # 创建预热器
            warmer = CacheWarmer(cache, config)

            # 模拟数据源
            async def data_source(keys):
                return {k: f"value_{k}" for k in keys}

            warmer.data_source = data_source

            # 预热缓存
            await warmer.preload_all()

            # 验证缓存已预热
            assert cache.get("key1") == "value_key1"
            assert cache.get("key2") == "value_key2"

            # 创建优化器
            optimizer = CacheOptimizer(cache, config)

            # 分析性能
            analysis = optimizer.analyze_performance()
            assert "l1_hit_rate" in analysis

    def test_cache_error_recovery(self):
        """测试缓存错误恢复"""
        from src.cache.optimization import MemoryCache

        cache = MemoryCache()

        # 正常操作
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 模拟部分错误
        original_cache = cache._cache
        cache._cache = original_cache.copy()

        # 即使部分结构损坏，其他操作仍应正常
        cache.set("key2", "value2")
        assert cache.get("key2") == "value2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])