"""
API性能优化测试
API Performance Optimization Tests
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.optimization.enhanced_performance_middleware import (
    EnhancedPerformanceMiddleware,
    PerformanceMetrics,
    PerformanceOptimizer,
)
from src.api.optimization.smart_cache_system import CacheEntry, SmartCacheManager


class TestPerformanceMetrics:
    """性能指标测试"""

    def test_metrics_initialization(self):
        """测试指标初始化"""
        metrics = PerformanceMetrics(max_history=100)

        assert metrics.max_history == 100
        assert len(metrics.request_history) == 0
        assert len(metrics.endpoint_stats) == 0
        assert metrics.global_stats["total_requests"] == 0

    def test_record_request(self):
        """测试请求记录"""
        metrics = PerformanceMetrics()

        metrics.record_request("GET", "/api/v1/test", 200, 0.1, "/api/v1/test")

        assert metrics.global_stats["total_requests"] == 1
        assert metrics.global_stats["total_time"] == 0.1
        assert len(metrics.request_history) == 1
        assert "/api/v1/test" in metrics.endpoint_stats

    def test_get_endpoint_stats(self):
        """测试端点统计"""
        metrics = PerformanceMetrics()

        # 记录多个请求
        for i in range(5):
            metrics.record_request(
                "GET", "/api/v1/test", 200, 0.1 + i * 0.05, "/api/v1/test"
            )

        stats = metrics.get_endpoint_stats("/api/v1/test")

        assert stats["request_count"] == 5
        assert stats["avg_response_time"] == 0.2  # (0.1 + 0.15 + 0.2 + 0.25 + 0.3) / 5
        assert stats["min_response_time"] == 0.1
        assert stats["max_response_time"] == 0.3
        assert stats["error_rate"] == 0.0

    def test_error_rate_calculation(self):
        """测试错误率计算"""
        metrics = PerformanceMetrics()

        # 记录成功和失败请求
        metrics.record_request("GET", "/api/v1/test", 200, 0.1, "/api/v1/test")
        metrics.record_request("GET", "/api/v1/test", 500, 0.1, "/api/v1/test")
        metrics.record_request("GET", "/api/v1/test", 400, 0.1, "/api/v1/test")

        stats = metrics.get_endpoint_stats("/api/v1/test")

        assert stats["error_rate"] == 66.66666666666666  # 2/3 * 100


class TestPerformanceOptimizer:
    """性能优化器测试"""

    def test_analyze_performance_good_performance(self):
        """测试良好性能分析"""
        metrics = PerformanceMetrics()
        optimizer = PerformanceOptimizer()

        # 记录良好性能的请求
        for _i in range(10):
            metrics.record_request("GET", "/api/v1/fast", 200, 0.1, "/api/v1/fast")

        suggestions = optimizer.analyze_performance(metrics)

        # 良好性能应该没有高优先级建议
        high_severity = [
            s for s in suggestions if s["severity"] in ["critical", "high"]
        ]
        assert len(high_severity) == 0

    def test_analyze_slow_endpoints(self):
        """测试慢端点分析"""
        metrics = PerformanceMetrics()
        optimizer = PerformanceOptimizer()

        # 记录慢请求
        for _i in range(5):
            metrics.record_request("GET", "/api/v1/slow", 200, 1.5, "/api/v1/slow")

        suggestions = optimizer.analyze_performance(metrics)

        # 应该有响应时间相关的建议
        response_time_suggestions = [
            s for s in suggestions if s["type"] == "response_time"
        ]
        assert len(response_time_suggestions) > 0

    def test_analyze_high_error_rate(self):
        """测试高错误率分析"""
        metrics = PerformanceMetrics()
        optimizer = PerformanceOptimizer()

        # 记录高错误率请求
        for i in range(10):
            status = 500 if i % 2 == 0 else 200
            metrics.record_request("GET", "/api/v1/error", status, 0.1, "/api/v1/error")

        suggestions = optimizer.analyze_performance(metrics)

        # 应该有错误率相关的建议
        error_suggestions = [s for s in suggestions if s["type"] == "error_rate"]
        assert len(error_suggestions) > 0


class TestSmartCacheManager:
    """智能缓存管理器测试"""

    def test_cache_manager_initialization(self):
        """测试缓存管理器初始化"""
        cache_manager = SmartCacheManager()

        assert cache_manager.max_memory_size > 0
        assert len(cache_manager.local_cache) == 0
        assert cache_manager.cache_stats["hits"] == 0
        assert cache_manager.cache_stats["misses"] == 0

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache_manager = SmartCacheManager()

        # 设置缓存
        result = await cache_manager.set("test_key", {"data": "test_value"}, ttl=60)
        assert result is True

        # 获取缓存
        cached_value = await cache_manager.get("test_key")
        assert cached_value == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """测试缓存过期"""
        cache_manager = SmartCacheManager()

        # 设置短期缓存
        await cache_manager.set("expire_key", "test_value", ttl=1)

        # 等待过期
        await asyncio.sleep(2)

        # 应该返回None（已过期）
        cached_value = await cache_manager.get("expire_key")
        assert cached_value is None

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """测试缓存删除"""
        cache_manager = SmartCacheManager()

        # 设置缓存
        await cache_manager.set("delete_key", "test_value")

        # 确认缓存存在
        cached_value = await cache_manager.get("delete_key")
        assert cached_value == "test_value"

        # 删除缓存
        result = await cache_manager.delete("delete_key")
        assert result is True

        # 确认缓存已删除
        cached_value = await cache_manager.get("delete_key")
        assert cached_value is None

    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        entry = CacheEntry("test_key", {"data": "test"}, ttl=3600)

        assert entry.key == "test_key"
        assert entry.value == {"data": "test"}
        assert entry.ttl == 3600
        assert entry.access_count == 0
        assert not entry.is_expired()

    def test_cache_entry_access(self):
        """测试缓存条目访问"""
        entry = CacheEntry("test_key", {"data": "test"}, ttl=3600)

        initial_count = entry.access_count
        value = entry.access()

        assert value == {"data": "test"}
        assert entry.access_count == initial_count + 1
        assert entry.last_accessed > entry.created_at


class TestEnhancedPerformanceMiddleware:
    """增强性能中间件测试"""

    @pytest.mark.asyncio
    async def test_middleware_initialization(self):
        """测试中间件初始化"""
        # 创建模拟应用
        mock_app = MagicMock()

        middleware = EnhancedPerformanceMiddleware(mock_app, enabled=True)

        assert middleware.enabled is True
        assert middleware.metrics is not None
        assert middleware.optimizer is not None

    @pytest.mark.asyncio
    async def test_endpoint_extraction(self):
        """测试端点提取"""
        mock_app = MagicMock()
        middleware = EnhancedPerformanceMiddleware(mock_app, enabled=True)

        # 模拟请求
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/matches/123"
        mock_request.method = "GET"

        endpoint = middleware._extract_endpoint(mock_request)
        assert endpoint == "/api/v1/matches"

    @pytest.mark.asyncio
    async def test_middleware_disabled(self):
        """测试中间件禁用状态"""
        mock_app = MagicMock()
        middleware = EnhancedPerformanceMiddleware(mock_app, enabled=False)

        # 模拟下一个处理器
        mock_call_next = AsyncMock()
        mock_response = MagicMock()
        mock_call_next.return_value = mock_response

        # 模拟请求
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/test"

        # 处理请求
        result = await middleware.dispatch(mock_request, mock_call_next)

        # 禁用状态下应该直接返回结果
        assert result == mock_response
        # 不应该记录任何指标
        assert middleware.metrics.global_stats["total_requests"] == 0


class TestCacheIntegration:
    """缓存集成测试"""

    @pytest.mark.asyncio
    async def test_cache_with_redis_mock(self):
        """测试Redis缓存集成"""
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True

        cache_manager = SmartCacheManager(redis_client=mock_redis)

        # 设置缓存
        result = await cache_manager.set("integration_key", {"data": "test"})
        assert result is True

        # 验证Redis调用
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_stats_calculation(self):
        """测试缓存统计计算"""
        cache_manager = SmartCacheManager()

        # 添加一些缓存条目
        await cache_manager.set("key1", "value1")
        await cache_manager.set("key2", "value2")

        # 获取一些缓存（命中）
        await cache_manager.get("key1")
        await cache_manager.get("key2")

        # 获取一些缓存（未命中）
        await cache_manager.get("key3")

        stats = cache_manager.get_cache_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 66.66666666666666  # 2/3 * 100
        assert stats["sets"] == 2
        assert stats["local_cache_size"] == 2

    @pytest.mark.asyncio
    async def test_cache_optimization(self):
        """测试缓存优化"""
        cache_manager = SmartCacheManager(max_memory_size=1024)  # 1KB限制

        # 添加一个较大的缓存条目
        large_value = "x" * 2000  # 2KB
        result = await cache_manager.set("large_key", large_value)

        assert result is True

        # 检查是否被清理（超过内存限制）
        optimization_result = await cache_manager.optimize_cache()

        assert "evicted_lru" in optimization_result
        assert optimization_result["evicted_lru"] >= 0


if __name__ == "__main__":
    pytest.main([__file__])
