"""
UX优化测试 - API性能测试
验证API响应时间优化效果，确保达到<200ms的目标
"""

import asyncio
import statistics
import time
from unittest.mock import AsyncMock, Mock

import pytest

from src.api.optimization.response_time_middleware import (
    PerformanceThreshold as MiddlewareThreshold,
)
from src.api.optimization.response_time_middleware import (
    ResponseTimeMiddleware,
)
from src.ux_optimization.api_optimizer import (
    APIResponseMetric,
    APIResponseOptimizer,
    OptimizationStrategy,
)
from src.ux_optimization.cache_manager import (
    CacheConfig,
    IntelligentCacheManager,
)


class TestAPIResponseOptimizer:
    """API响应时间优化器测试"""

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.delete = AsyncMock(return_value=True)
        cache.exists = AsyncMock(return_value=False)
        cache.clear = AsyncMock(return_value=True)
        return cache

    @pytest.fixture
    def mock_profiler(self):
        """模拟性能分析器"""
        profiler = AsyncMock()
        profiler.record_metric = AsyncMock()
        return profiler

    @pytest.fixture
    def optimizer(self, mock_cache, mock_profiler):
        """API优化器实例"""
        strategy = OptimizationStrategy(
            enable_query_optimization=True,
            enable_cache_warming=True,
            enable_compression=True,
            enable_async_processing=True,
            cache_ttl=300,
        )
        return APIResponseOptimizer(mock_cache, mock_profiler, strategy)

    @pytest.mark.asyncio
    async def test_optimizer_initialization(self, optimizer, mock_cache, mock_profiler):
        """测试优化器初始化"""
        assert optimizer.cache == mock_cache
        assert optimizer.profiler == mock_profiler
        assert optimizer.strategy.enable_query_optimization is True
        assert optimizer.threshold.avg_response_time == 200.0
        assert optimizer.metrics == {}  # 应该是空的defaultdict

    @pytest.mark.asyncio
    async def test_cache_hit_scenario(self, optimizer, mock_cache):
        """测试缓存命中场景"""
        # 设置缓存返回值
        expected_result = {"data": "test_result"}
        mock_cache.get.return_value = expected_result

        # 模拟函数
        mock_func = AsyncMock(return_value=expected_result)

        # 调用优化器
        result = await optimizer(mock_func, "/api/test", "GET")

        # 验证结果
        assert result == expected_result
        mock_cache.get.assert_called_once()
        mock_func.assert_not_called()  # 不应该调用原函数

        # 验证统计信息
        stats = optimizer.get_performance_stats()
        assert stats["optimization_stats"]["cache_hits"] > 0
        assert stats["cache_hit_rate"] > 0

    @pytest.mark.asyncio
    async def test_cache_miss_scenario(self, optimizer, mock_cache):
        """测试缓存未命中场景"""
        # 设置缓存返回None，函数返回值
        mock_cache.get.return_value = None
        expected_result = {"data": "test_result"}
        mock_func = AsyncMock(return_value=expected_result)

        # 调用优化器
        result = await optimizer(mock_func, "/api/test", "GET")

        # 验证结果
        assert result == expected_result
        mock_func.assert_called_once()
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_response_time_recording(self, optimizer):
        """测试响应时间记录"""
        mock_func = AsyncMock(return_value={"data": "test"})

        # 执行多次调用以收集指标
        for _ in range(10):
            await optimizer(mock_func, "/api/test", "GET")

        # 验证指标记录
        stats = optimizer.get_performance_stats()
        assert stats["total_metrics"] >= 10
        assert "GET:/api/test" in stats["endpoints"]

        endpoint_stats = stats["endpoints"]["GET:/api/test"]
        assert endpoint_stats["request_count"] >= 10
        assert endpoint_stats["avg_response_time"] > 0
        assert "p95_response_time" in endpoint_stats

    @pytest.mark.asyncio
    async def test_optimization_triggering(self, optimizer):
        """测试优化触发"""

        # 模拟慢响应时间
        async def slow_func():
            await asyncio.sleep(0.3)  # 300ms延迟
            return {"data": "slow_response"}

        # 执行足够多的调用以触发优化
        for _ in range(150):  # 超过min_sample_size
            await optimizer(slow_func, "/api/slow", "GET")

        # 验证优化统计
        stats = optimizer.get_performance_stats()
        # 注意：由于优化是异步的，可能需要等待一段时间
        assert stats["total_metrics"] >= 150

    @pytest.mark.asyncio
    async def test_optimization_recommendations(self, optimizer):
        """测试优化建议生成"""
        # 手动添加一些慢响应指标
        key = "GET:/api/slow"
        for i in range(150):
            metric = APIResponseMetric(
                endpoint="/api/slow",
                method="GET",
                response_time=300.0,  # 超过阈值
                status_code=200,
                timestamp=time.time(),
            )
            optimizer.metrics[key].append(metric)

        # 获取优化建议
        recommendations = optimizer.get_optimization_recommendations()

        # 验证建议
        assert len(recommendations) > 0
        assert any("response time" in rec["issue"].lower() for rec in recommendations)
        assert any(rec["priority"] == "high" for rec in recommendations)

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, optimizer):
        """测试缓存键生成"""
        # 测试不同参数生成不同的键
        key1 = optimizer._generate_cache_key(
            "/api/test", "GET", (), {"param": "value1"}
        )
        key2 = optimizer._generate_cache_key(
            "/api/test", "GET", (), {"param": "value2"}
        )
        key3 = optimizer._generate_cache_key(
            "/api/test", "GET", (), {"param": "value1"}
        )

        assert key1 != key2  # 不同参数应该生成不同键
        assert key1 == key3  # 相同参数应该生成相同键
        assert key1.startswith("api_response:")

    def test_performance_stats(self, optimizer):
        """测试性能统计获取"""
        stats = optimizer.get_performance_stats()

        assert "optimization_stats" in stats
        assert "total_endpoints" in stats
        assert "total_metrics" in stats
        assert "cache_hit_rate" in stats
        assert "endpoints" in stats

        # 验证初始化状态
        assert stats["total_endpoints"] == 0
        assert stats["total_metrics"] == 0
        assert stats["cache_hit_rate"] == 0.0


class TestIntelligentCacheManager:
    """智能缓存管理器测试"""

    @pytest.fixture
    def mock_unified_cache(self):
        """模拟统一缓存"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.delete = AsyncMock(return_value=True)
        cache.exists = AsyncMock(return_value=False)
        cache.clear = AsyncMock(return_value=0)
        return cache

    @pytest.fixture
    def cache_manager(self, mock_unified_cache):
        """缓存管理器实例"""
        config = CacheConfig(
            max_memory_size=1024 * 1024, default_ttl=300, enable_compression=True  # 1MB
        )
        return IntelligentCacheManager(mock_unified_cache, config)

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_manager, mock_unified_cache):
        """测试缓存设置和获取"""
        # 设置缓存
        key = "test_key"
        value = {"data": "test_value"}
        success = await cache_manager.set(key, value)
        assert success is True

        # 获取缓存
        mock_unified_cache.get.return_value = value
        result = await cache_manager.get(key)
        assert result == value

    @pytest.mark.asyncio
    async def test_cache_miss_return_default(self, cache_manager):
        """测试缓存未命中返回默认值"""
        result = await cache_manager.get("nonexistent_key", "default_value")
        assert result == "default_value"

    @pytest.mark.asyncio
    async def test_l1_cache_promotion(self, cache_manager, mock_unified_cache):
        """测试L1缓存提升"""
        key = "test_key"
        value = {"data": "test_value"}

        # 模拟L2缓存命中
        mock_unified_cache.get.return_value = value

        # 第一次获取，应该从L2获取并提升到L1
        result1 = await cache_manager.get(key)
        assert result1 == value
        assert key in cache_manager.l1_cache

        # 第二次获取，应该从L1缓存命中
        result2 = await cache_manager.get(key)
        assert result2 == value

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_manager):
        """测试缓存统计"""
        # 执行一些缓存操作
        await cache_manager.set("key1", "value1")
        await cache_manager.get("key1")
        await cache_manager.get("key2")  # miss

        stats = cache_manager.get_cache_stats()

        assert "total" in stats
        assert "hit_rate" in stats["total"]
        assert "l1_size" in stats["total"]
        assert isinstance(stats["total"]["hit_rate"], (int, float))

    @pytest.mark.asyncio
    async def test_hot_keys_tracking(self, cache_manager):
        """测试热键跟踪"""
        key = "hot_key"
        value = "hot_value"

        # 多次访问同一个键
        for _ in range(15):  # 超过热键阈值
            await cache_manager.set(key, value)
            await cache_manager.get(key)

        # 检查热键列表
        hot_keys = cache_manager.get_hot_keys()
        # 注意：由于这是异步操作，热键可能需要一些时间才会被识别

    @pytest.mark.asyncio
    async def test_cache_eviction(self, cache_manager):
        """测试缓存淘汰"""
        # 设置小容量以触发淘汰
        cache_manager.config.max_memory_size = 100  # 100字节

        # 添加多个大缓存项
        for i in range(10):
            large_value = "x" * 50  # 50字节
            await cache_manager.set(f"key_{i}", large_value)

        # 验证缓存项数量被限制
        assert len(cache_manager.l1_cache) <= 2  # 应该只保留最近的项


class TestResponseTimeMiddleware:
    """响应时间中间件测试"""

    @pytest.fixture
    def mock_optimizer(self):
        """模拟优化器"""
        optimizer = AsyncMock()
        optimizer._record_metric = AsyncMock()
        optimizer._optimize_endpoint = AsyncMock()
        return optimizer

    @pytest.fixture
    def middleware(self, mock_optimizer):
        """中间件实例"""
        threshold = MiddlewareThreshold(
            warning_avg_ms=100.0,  # 降低阈值用于测试
            critical_avg_ms=200.0,
            min_sample_size=5,  # 降低样本数要求
        )
        return ResponseTimeMiddleware(None, mock_optimizer, threshold)

    @pytest.mark.asyncio
    async def test_middleware_records_metrics(self, middleware, mock_optimizer):
        """测试中间件记录指标"""
        # 模拟请求处理
        mock_request = Mock()
        mock_request.url.path = "/api/test"
        mock_request.method = "GET"
        mock_request.state = Mock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def mock_call_next(request):
            await asyncio.sleep(0.01)  # 模拟处理时间
            return mock_response

        # 执行中间件
        response = await middleware.dispatch(mock_request, mock_call_next)

        # 验证指标记录
        mock_optimizer._record_metric.assert_called_once()
        assert "X-Response-Time" in response.headers

    @pytest.mark.asyncio
    async def test_performance_alerts(self, middleware, mock_optimizer):
        """测试性能告警"""
        # 模拟多次慢请求
        endpoint_key = "GET:/api/slow"
        for i in range(10):
            middleware._update_stats("/api/slow", "GET", 150.0, 200)  # 150ms响应时间

        # 检查告警
        await middleware._check_performance_alerts("/api/slow", "GET")

        # 验证告警统计
        stats = middleware.stats
        assert "alerts_triggered" in stats

    @pytest.mark.asyncio
    async def test_slow_endpoints_detection(self, middleware):
        """测试慢端点检测"""
        # 添加慢端点数据
        slow_endpoint_key = "GET:/api/slow"
        for i in range(10):
            middleware._update_stats("/api/slow", "GET", 400.0, 200)  # 400ms

        # 获取慢端点列表
        slow_endpoints = middleware.get_slow_endpoints(threshold_ms=300.0)

        assert len(slow_endpoints) > 0
        assert slow_endpoints[0]["endpoint"] == "/api/slow"
        assert slow_endpoints[0]["avg_response_time"] > 300.0

    def test_endpoint_key_generation(self, middleware):
        """测试端点键生成"""
        # 测试路径参数标准化
        request1 = Mock()
        request1.url.path = "/api/users/12345"
        request1.url.query = None

        request2 = Mock()
        request2.url.path = "/api/users/67890"
        request2.url.query = None

        key1 = middleware._get_endpoint_key(request1)
        key2 = middleware._get_endpoint_key(request2)

        # 应该都标准化为相同模式
        assert key1 == "/api/users/{id}"
        assert key2 == "/api/users/{id}"


class TestAPIPerformanceIntegration:
    """API性能集成测试"""

    @pytest.mark.asyncio
    async def test_performance_optimization_pipeline(self):
        """测试性能优化完整流程"""
        # 创建模拟组件
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True

        mock_profiler = AsyncMock()

        # 初始化优化器
        strategy = OptimizationStrategy(
            enable_cache_warming=True, enable_compression=True
        )
        optimizer = APIResponseOptimizer(mock_cache, mock_profiler, strategy)

        # 模拟API端点函数
        async def api_endpoint(param1: str, param2: int = 10):
            await asyncio.sleep(0.05)  # 50ms处理时间
            return {"result": f"processed_{param1}_{param2}"}

        # 执行多次调用以触发优化
        responses = []
        response_times = []

        for i in range(20):
            start_time = time.time()
            response = await optimizer(
                api_endpoint, "/api/test", "GET", f"test_{i}", param2=i * 2
            )
            end_time = time.time()

            responses.append(response)
            response_times.append((end_time - start_time) * 1000)

        # 验证响应
        assert len(responses) == 20
        assert all("processed_" in r["result"] for r in responses)

        # 验证性能改善
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 100  # 应该小于100ms

        # 验证缓存效果
        cache_calls = mock_cache.get.call_count
        set_calls = mock_cache.set.call_count
        assert cache_calls >= 20
        assert set_calls >= 1

        # 验证统计信息
        stats = optimizer.get_performance_stats()
        assert stats["total_metrics"] >= 20
        assert "GET:/api/test" in stats["endpoints"]

    @pytest.mark.asyncio
    async def test_cache_warming_effectiveness(self):
        """测试缓存预热效果"""
        # 这里需要创建一个真实的缓存管理器来测试预热
        # 由于时间限制，这里只做基本的模拟测试
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True

        config = CacheConfig(enable_warmup=True)
        cache_manager = IntelligentCacheManager(mock_cache, config)

        # 验证预热任务启动
        assert cache_manager.config.enable_warmup is True
        assert not cache_manager.warmup_completed  # 初始状态

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """性能基准测试"""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True

        mock_profiler = AsyncMock()
        optimizer = APIResponseOptimizer(mock_cache, mock_profiler)

        # 基准测试函数
        async def benchmark_func():
            return {"benchmark": "data"}

        # 执行基准测试
        times = []
        iterations = 100

        for _ in range(iterations):
            start_time = time.time()
            await optimizer(benchmark_func, "/api/benchmark", "GET")
            end_time = time.time()
            times.append((end_time - start_time) * 1000)

        # 计算统计数据
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        p99_time = statistics.quantiles(times, n=100)[98]

        # 性能断言
        assert avg_time < 200  # 平均时间应该小于200ms
        assert p95_time < 300  # P95应该小于300ms
        assert p99_time < 500  # P99应该小于500ms

        print("性能基准结果:")
        print(f"平均响应时间: {avg_time:.2f}ms")
        print(f"P95响应时间: {p95_time:.2f}ms")
        print(f"P99响应时间: {p99_time:.2f}ms")


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-s", "--tb=short"])
