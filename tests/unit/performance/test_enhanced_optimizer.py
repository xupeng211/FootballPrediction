"""
增强性能优化器测试
Enhanced Performance Optimizer Tests

测试性能监控、数据库优化、缓存优化等功能。
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.performance.enhanced_optimizer import (
    CacheMetrics,
    CacheOptimizer,
    ConcurrencyOptimizer,
    DatabaseMetrics,
    DatabaseOptimizer,
    EnhancedPerformanceOptimizer,
    PerformanceMonitor,
    SystemMetrics,
    cache_result,
    concurrency_optimizer,
    monitor_performance,
    performance_monitor,
)


class TestPerformanceMonitor:
    """性能监控器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = PerformanceMonitor(max_metrics=100)

    def test_record_request_start(self):
        """测试记录请求开始"""
        request_id = "test_request_1"
        self.monitor.record_request_start(request_id)

        assert request_id in self.monitor.active_requests
        assert len(self.monitor.active_requests) == 1

    def test_record_request_end(self):
        """测试记录请求结束"""
        request_id = "test_request_2"
        self.monitor.record_request_start(request_id)

        self.monitor.record_request_end(
            request_id=request_id,
            endpoint="/test/endpoint",
            method="GET",
            status_code=200,
            response_time=0.123,
        )

        assert request_id not in self.monitor.active_requests
        assert len(self.monitor.metrics_history) == 1
        assert self.monitor.request_counts["/test/endpoint"] == 1

    def test_get_system_metrics_empty(self):
        """测试获取系统指标（空数据）"""
        metrics = self.monitor.get_system_metrics()

        assert metrics.total_requests == 0
        assert metrics.active_connections == 0
        assert metrics.avg_response_time == 0.0

    def test_get_system_metrics_with_data(self):
        """测试获取系统指标（有数据）"""
        # 添加一些测试数据
        request_id = "test_request_3"
        self.monitor.record_request_start(request_id)

        self.monitor.record_request_end(
            request_id=request_id,
            endpoint="/test/endpoint",
            method="GET",
            status_code=200,
            response_time=0.250,
        )

        metrics = self.monitor.get_system_metrics()

        assert metrics.total_requests == 1
        assert metrics.avg_response_time == 0.250
        assert metrics.requests_per_second >= 0

    def test_get_slow_queries(self):
        """测试获取慢查询"""
        request_id = "test_request_4"
        self.monitor.record_request_start(request_id)

        # 模拟慢请求（超过1秒）
        self.monitor.record_request_end(
            request_id=request_id,
            endpoint="/slow/endpoint",
            method="POST",
            status_code=200,
            response_time=1.500,
        )

        slow_queries = self.monitor.get_slow_queries(threshold_ms=1000.0)
        assert len(slow_queries) == 1
        assert slow_queries[0].endpoint == "/slow/endpoint"
        assert slow_queries[0].response_time == 1.500

    def test_get_endpoint_stats(self):
        """测试获取端点统计"""
        # 添加多个请求
        endpoints = ["/api/users", "/api/posts", "/api/users"]
        for i, endpoint in enumerate(endpoints):
            request_id = f"request_{i}"
            self.monitor.record_request_start(request_id)
            self.monitor.record_request_end(
                request_id=request_id,
                endpoint=endpoint,
                method="GET",
                status_code=200 if endpoint != "/api/posts" else 500,
                response_time=0.100 + i * 0.050,
            )

        # 测试用户端点统计
        stats = self.monitor.get_endpoint_stats("/api/users")
        assert stats["request_count"] == 2
        assert stats["error_count"] == 0
        assert stats["error_rate"] == 0
        assert stats["avg_response_time"] == 0.125  # (0.100 + 0.150) / 2

        # 测试文章端点统计（有错误）
        posts_stats = self.monitor.get_endpoint_stats("/api/posts")
        assert posts_stats["request_count"] == 1
        assert posts_stats["error_count"] == 1
        assert posts_stats["error_rate"] == 100.0


class TestDatabaseOptimizer:
    """数据库优化器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.optimizer = DatabaseOptimizer()

    @pytest.mark.asyncio
    async def test_initialize_with_mock_engine(self):
        """测试初始化（模拟引擎）"""
        # 模拟create_async_engine
        mock_engine = AsyncMock()
        mock_engine.pool = MagicMock()
        mock_engine.pool.checkedin.return_value = 10
        mock_engine.pool.size.return_value = 20

        with patch(
            "src.performance.enhanced_optimizer.create_async_engine",
            return_value=mock_engine,
        ):
            await self.optimizer.initialize("sqlite+aiosqlite:///test.db")

        assert self.optimizer.engine == mock_engine

    @pytest.mark.asyncio
    async def test_get_session_context_manager(self):
        """测试数据库会话上下文管理器"""
        self.optimizer.engine = AsyncMock()
        mock_session = AsyncMock()
        mock_async_session = AsyncMock()
        mock_async_session.__aenter__.return_value = mock_session
        mock_async_session.__aexit__.return_value = None

        with patch(
            "src.performance.enhanced_optimizer.AsyncSession",
            return_value=mock_async_session,
        ):
            async with self.optimizer.get_session() as session:
                assert session == mock_session

    def test_get_database_metrics_uninitialized(self):
        """测试获取数据库指标（未初始化）"""
        metrics = self.optimizer.get_database_metrics()
        assert metrics.active_connections == 0
        assert metrics.total_connections == 0

    def test_get_database_metrics_with_mock_engine(self):
        """测试获取数据库指标（模拟引擎）"""
        mock_pool = MagicMock()
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 3
        mock_pool.size.return_value = 20

        self.optimizer.engine = MagicMock()
        self.optimizer.engine.pool = mock_pool

        metrics = self.optimizer.get_database_metrics()

        assert metrics.active_connections == 5
        assert metrics.total_connections == 23  # 5 + 3 + 20
        assert metrics.connection_pool_size == 20


class TestCacheOptimizer:
    """缓存优化器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.optimizer = CacheOptimizer()

    @pytest.mark.asyncio
    async def test_initialize_with_mock_redis(self):
        """测试初始化（模拟Redis）"""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with patch(
            "src.performance.enhanced_optimizer.get_redis_manager",
            return_value=mock_redis,
        ):
            await self.optimizer.initialize()

        assert self.optimizer.redis_client == mock_redis

    @pytest.mark.asyncio
    async def test_get_cached_data_hit(self):
        """测试获取缓存数据（命中）"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b"cached_value"

        self.optimizer.redis_client = mock_redis

        result = await self.optimizer.get_cached_data("test_key")
        assert result == b"cached_value"

        metrics = self.optimizer.get_cache_metrics()
        assert metrics.hit_count == 1
        assert metrics.miss_count == 0

    @pytest.mark.asyncio
    async def test_get_cached_data_miss(self):
        """测试获取缓存数据（未命中）"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        self.optimizer.redis_client = mock_redis

        result = await self.optimizer.get_cached_data("test_key", "default_value")
        assert result == "default_value"

        metrics = self.optimizer.get_cache_metrics()
        assert metrics.hit_count == 0
        assert metrics.miss_count == 1

    @pytest.mark.asyncio
    async def test_set_cached_data_success(self):
        """测试设置缓存数据（成功）"""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True

        self.optimizer.redis_client = mock_redis

        result = await self.optimizer.set_cached_data("test_key", "test_value")
        assert result is True

        metrics = self.optimizer.get_cache_metrics()
        assert metrics.set_count == 1

    @pytest.mark.asyncio
    async def test_set_cached_data_failure(self):
        """测试设置缓存数据（失败）"""
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Redis error")

        self.optimizer.redis_client = mock_redis

        result = await self.optimizer.set_cached_data("test_key", "test_value")
        assert result is False

    @pytest.mark.asyncio
    async def test_warm_up_cache(self):
        """测试缓存预热"""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True

        self.optimizer.redis_client = mock_redis

        warm_up_data = {"key1": "value1", "key2": "value2", "key3": "value3"}

        await self.optimizer.warm_up_cache(warm_up_data)

        # 验证所有数据都被尝试设置
        assert mock_redis.set.call_count == 3

    def test_get_cache_metrics(self):
        """测试获取缓存指标"""
        # 手动设置一些统计数据
        self.optimizer.cache_stats.hit_count = 100
        self.optimizer.cache_stats.miss_count = 25
        self.optimizer.cache_stats.set_count = 30
        self.optimizer.cache_stats.avg_response_time = 0.050

        metrics = self.optimizer.get_cache_metrics()

        assert metrics.hit_count == 100
        assert metrics.miss_count == 25
        assert metrics.hit_rate == 80.0  # 100 / (100 + 25) * 100
        assert metrics.avg_response_time == 0.050


class TestConcurrencyOptimizer:
    """并发优化器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.optimizer = ConcurrencyOptimizer()

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化"""
        await self.optimizer.initialize(max_concurrent_requests=100)

        assert self.optimizer.semaphore._value == 100
        assert len(self.optimizer.worker_tasks) == 10

    @pytest.mark.asyncio
    async def test_acquire_slot(self):
        """测试获取并发槽位"""
        await self.optimizer.initialize(max_concurrent_requests=2)

        async with self.optimizer.acquire_slot():
            # 在这个块内，槽位被占用
            assert self.optimizer.semaphore._value == 1

        # 退出后，槽位被释放
        assert self.optimizer.semaphore._value == 2

    @pytest.mark.asyncio
    async def test_submit_request(self):
        """测试提交请求"""
        await self.optimizer.initialize()

        # 模拟处理函数
        mock_handler = AsyncMock()

        await self.optimizer.submit_request(
            request_id="test_req_1",
            endpoint="/test",
            handler=mock_handler,
            param1="value1",
        )

        # 等待一小段时间让工作协程处理
        await asyncio.sleep(0.1)

        # 验证处理函数被调用
        mock_handler.assert_called_once_with(param1="value1")

    def test_get_concurrency_metrics(self):
        """测试获取并发指标"""
        metrics = self.optimizer.get_concurrency_metrics()

        assert "active_tasks" in metrics
        assert "queued_requests" in metrics
        assert "worker_count" in metrics
        assert "available_slots" in metrics


class TestEnhancedPerformanceOptimizer:
    """增强性能优化器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.optimizer = EnhancedPerformanceOptimizer()

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试完整初始化"""
        # 模拟各个组件的初始化
        with (
            patch.object(self.optimizer.db_optimizer, "initialize") as mock_db_init,
            patch.object(
                self.optimizer.cache_optimizer, "initialize"
            ) as mock_cache_init,
            patch.object(
                self.optimizer.concurrency_optimizer, "initialize"
            ) as mock_concurrency_init,
        ):

            await self.optimizer.initialize(
                database_url="sqlite+aiosqlite:///test.db", max_concurrent_requests=100
            )

            mock_db_init.assert_called_once_with("sqlite+aiosqlite:///test.db")
            mock_cache_init.assert_called_once()
            mock_concurrency_init.assert_called_once_with(100)

        assert self.optimizer.initialized is True

    @pytest.mark.asyncio
    async def test_get_comprehensive_metrics(self):
        """测试获取综合性能指标"""
        # 模拟初始化
        self.optimizer.initialized = True

        # 模拟各个组件返回指标
        system_metrics = SystemMetrics(
            total_requests=100, avg_response_time=0.250, error_rate=2.0
        )
        db_metrics = DatabaseMetrics(
            active_connections=5, avg_query_time=0.100, slow_queries=3
        )
        cache_metrics = CacheMetrics(hit_count=80, miss_count=20, hit_rate=80.0)

        with (
            patch.object(
                self.optimizer.monitor,
                "get_system_metrics",
                return_value=system_metrics,
            ),
            patch.object(
                self.optimizer.db_optimizer,
                "get_database_metrics",
                return_value=db_metrics,
            ),
            patch.object(
                self.optimizer.cache_optimizer,
                "get_cache_metrics",
                return_value=cache_metrics,
            ),
            patch.object(
                self.optimizer.concurrency_optimizer,
                "get_concurrency_metrics",
                return_value={"active_tasks": 5},
            ),
        ):

            metrics = await self.optimizer.get_comprehensive_metrics()

            assert "system" in metrics
            assert "database" in metrics
            assert "cache" in metrics
            assert "concurrency" in metrics

            assert metrics["system"]["total_requests"] == 100
            assert metrics["database"]["active_connections"] == 5
            assert metrics["cache"]["hit_rate"] == 80.0

    @pytest.mark.asyncio
    async def test_get_comprehensive_metrics_uninitialized(self):
        """测试获取综合指标（未初始化）"""
        with pytest.raises(RuntimeError, match="性能优化器未初始化"):
            await self.optimizer.get_comprehensive_metrics()

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """测试关闭优化器"""
        # 模拟初始化
        self.optimizer.initialized = True
        self.optimizer.db_optimizer.engine = AsyncMock()
        self.optimizer.concurrency_optimizer.worker_tasks = [
            AsyncMock() for _ in range(3)
        ]

        await self.optimizer.shutdown()

        # 验证引擎被关闭
        self.optimizer.db_optimizer.engine.dispose.assert_called_once()


class TestPerformanceDecorators:
    """性能装饰器测试"""

    @pytest.mark.asyncio
    async def test_monitor_performance_decorator_async(self):
        """测试性能监控装饰器（异步函数）"""

        @monitor_performance("test_endpoint")
        async def test_function():
            await asyncio.sleep(0.1)
            return "test_result"

        result = await test_function()
        assert result == "test_result"

        # 验证性能监控记录了请求
        assert len(performance_monitor.metrics_history) > 0
        last_metric = performance_monitor.metrics_history[-1]
        assert last_metric.endpoint == "test_endpoint"

    def test_monitor_performance_decorator_sync(self):
        """测试性能监控装饰器（同步函数）"""

        @monitor_performance("test_sync_endpoint")
        def test_sync_function():
            time.sleep(0.05)
            return "sync_result"

        result = test_sync_function()
        assert result == "sync_result"

        # 验证性能监控记录了请求
        assert len(performance_monitor.metrics_history) > 0
        last_metric = performance_monitor.metrics_history[-1]
        assert last_metric.endpoint == "test_sync_endpoint"

    @pytest.mark.asyncio
    async def test_cache_result_decorator_hit(self):
        """测试缓存结果装饰器（命中）"""
        call_count = 0

        @cache_result(ttl=3600)
        async def expensive_function(param):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"result_{param}"

        # 第一次调用
        result1 = await expensive_function("test")
        assert result1 == "result_test"
        assert call_count == 1

        # 第二次调用（应该从缓存获取）
        result2 = await expensive_function("test")
        assert result2 == "result_test"
        assert call_count == 1  # 没有再次调用

    @pytest.mark.asyncio
    async def test_cache_result_decorator_miss(self):
        """测试缓存结果装饰器（未命中）"""
        call_count = 0

        @cache_result(ttl=3600)
        async def expensive_function(param):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"result_{param}"

        # 第一次调用
        result1 = await expensive_function("test1")
        assert result1 == "result_test1"
        assert call_count == 1

        # 不同参数的调用（缓存未命中）
        result2 = await expensive_function("test2")
        assert result2 == "result_test2"
        assert call_count == 2


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_performance_workflow(self):
        """测试完整性能工作流程"""
        # 1. 初始化性能优化器
        optimizer = EnhancedPerformanceOptimizer()

        with (
            patch.object(optimizer.db_optimizer, "initialize"),
            patch.object(optimizer.cache_optimizer, "initialize"),
            patch.object(optimizer.concurrency_optimizer, "initialize"),
        ):

            await optimizer.initialize(
                database_url="sqlite+aiosqlite:///test.db", max_concurrent_requests=100
            )

        assert optimizer.initialized

        # 2. 模拟API请求处理
        @monitor_performance("integration_test")
        async def api_endpoint():
            async with optimizer.db_optimizer.get_session():
                # 模拟数据库查询
                await asyncio.sleep(0.05)
                return {"status": "success"}

        # 3. 执行请求
        result = await api_endpoint()
        assert result["status"] == "success"

        # 4. 验证性能指标
        system_metrics = performance_monitor.get_system_metrics()
        assert system_metrics.total_requests >= 1

        # 5. 关闭
        await optimizer.shutdown()


# ============================================================================
# 性能基准测试
# ============================================================================


class TestPerformanceBenchmarks:
    """性能基准测试"""

    @pytest.mark.asyncio
    async def test_performance_monitor_overhead(self):
        """测试性能监控开销"""

        # 测试没有装饰器的函数
        async def bare_function():
            await asyncio.sleep(0.01)

        # 测试有装饰器的函数
        @monitor_performance("benchmark")
        async def decorated_function():
            await asyncio.sleep(0.01)

        # 基准测试
        iterations = 100

        start_time = time.time()
        for _ in range(iterations):
            await bare_function()
        bare_time = time.time() - start_time

        start_time = time.time()
        for _ in range(iterations):
            await decorated_function()
        decorated_time = time.time() - start_time

        # 验证开销不超过100%
        overhead = (decorated_time - bare_time) / bare_time * 100
        assert overhead < 100, f"性能监控开销过高: {overhead:.2f}%"

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """测试并发请求处理"""
        await concurrency_optimizer.initialize(max_concurrent_requests=10)

        request_count = 0
        processed_requests = []

        async def mock_handler(request_id):
            nonlocal request_count
            request_count += 1
            await asyncio.sleep(0.01)
            processed_requests.append(request_id)

        # 提交多个并发请求
        tasks = []
        for i in range(20):
            task = concurrency_optimizer.submit_request(
                request_id=f"req_{i}", endpoint="/test", handler=mock_handler
            )
            tasks.append(task)

        # 等待所有请求处理完成
        await asyncio.sleep(0.5)

        # 验证所有请求都被处理
        assert request_count == 20
        assert len(processed_requests) == 20

        await concurrency_optimizer.shutdown()
