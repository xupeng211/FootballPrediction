# TODO: Consider creating a fixture for 45 repeated Mock creations

# TODO: Consider creating a fixture for 45 repeated Mock creations

from unittest.mock import AsyncMock, Mock, patch

"""
性能监控中间件测试
Performance Monitoring Middleware Tests
"""

import asyncio
import time

import pytest
from fastapi import Request, Response

from src.performance.middleware import (
    BackgroundTaskPerformanceMonitor,
    CachePerformanceMiddleware,
    DatabasePerformanceMiddleware,
    PerformanceMonitoringMiddleware,
)


@pytest.mark.unit
class TestPerformanceMonitoringMiddleware:
    """性能监控中间件测试类"""

    @pytest.fixture
    def app(self):
        """创建模拟的FastAPI应用"""
        app = Mock()
        return app

    @pytest.fixture
    def middleware(self, app):
        """创建中间件实例"""
        return PerformanceMonitoringMiddleware(
            app,
            track_memory=True,
            track_concurrency=True,
            sample_rate=1.0,  # 100%采样用于测试
        )

    def test_init(self, app):
        """测试初始化"""
        middleware = PerformanceMonitoringMiddleware(
            app, track_memory=False, track_concurrency=False, sample_rate=0.5
        )

        assert middleware.track_memory is False
        assert middleware.track_concurrency is False
        assert middleware.sample_rate == 0.5
        assert middleware.total_requests == 0
        assert middleware.max_concurrent_requests == 0
        assert middleware.request_times == []

    @pytest.mark.asyncio
    async def test_dispatch_with_sampling(self, app):
        """测试请求处理与采样"""
        # 创建采样率为0的中间件（不采样）
        middleware = PerformanceMonitoringMiddleware(
            app,
            track_memory=True,
            track_concurrency=True,
            sample_rate=0.0,  # 不采样
        )

        # 创建模拟请求和响应
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"
        request.url.__str__ = Mock(return_value="http://test.com/test")
        request.body = AsyncMock(return_value=b"test data")

        call_next = AsyncMock()
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        call_next.return_value = response

        # 处理请求
        _result = await middleware.dispatch(request, call_next)

        # 由于采样率为0，应该直接返回响应
        assert _result == response
        assert middleware.total_requests == 0  # 没有被统计

    @pytest.mark.asyncio
    async def test_dispatch_with_full_tracking(self, middleware):
        """测试完整请求跟踪"""
        # 创建模拟请求和响应
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = Mock()
        request.url.path = "/api/test"
        request.url.__str__ = Mock(return_value="http://test.com/api/test")
        request.body = AsyncMock(return_value=b'{"key": "value"}')

        call_next = AsyncMock()
        response = Mock(spec=Response)
        response.status_code = 201
        response.headers = {}
        response.body = b'{"result": "success"}'
        call_next.return_value = response

        # 处理请求
        _result = await middleware.dispatch(request, call_next)

        # 验证响应
        assert _result == response
        assert _result.headers["X-Process-Time"] is not None
        assert _result.headers["X-Request-ID"] is not None

        # 验证统计
        assert middleware.total_requests == 1
        assert len(middleware.request_times) == 1

    @pytest.mark.asyncio
    @patch("src.performance.middleware.psutil")
    async def test_dispatch_with_memory_tracking(self, mock_psutil, middleware):
        """测试内存跟踪"""
        # 模拟psutil
        mock_process = Mock()
        memory_info1 = Mock()
        memory_info1.rss = 100 * 1024 * 1024  # 100MB
        memory_info2 = Mock()
        memory_info2.rss = 105 * 1024 * 1024  # 105MB
        mock_process.memory_info.side_effect = [memory_info1, memory_info2]
        mock_psutil.Process.return_value = mock_process

        # 创建模拟请求和响应
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/test"
        request.url.__str__ = Mock(return_value="http://test.com/test")
        request.body = AsyncMock(return_value=b"")

        call_next = AsyncMock()
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        call_next.return_value = response

        # 处理请求
        _result = await middleware.dispatch(request, call_next)

        # 验证内存增量头部
        assert "X-Memory-Delta" in result.headers
        assert float(result.headers["X-Memory-Delta"]) == 5.0

    @pytest.mark.asyncio
    async def test_dispatch_with_concurrency_tracking(self, middleware):
        """测试并发请求跟踪"""
        # 创建多个并发请求
        requests = []
        responses = []
        call_nexts = []

        for i in range(3):
            request = Mock(spec=Request)
            request.method = "GET"
            request.url = Mock()
            request.url.path = f"/test{i}"
            request.url.__str__ = Mock(return_value=f"http://test.com/test{i}")
            request.body = AsyncMock(return_value=b"")
            requests.append(request)

            response = Mock(spec=Response)
            response.status_code = 200
            response.headers = {}
            responses.append(response)

            call_next = AsyncMock(return_value=response)
            call_nexts.append(call_next)

        # 并发处理请求
        tasks = []
        for req, cn in zip(requests, call_nexts):
            task = asyncio.create_task(middleware.dispatch(req, cn))
            tasks.append(task)

        # 等待所有请求完成
        results = await asyncio.gather(*tasks)

        # 验证结果
        assert len(results) == 3
        assert middleware.total_requests == 3
        assert middleware.max_concurrent_requests == 3

    @pytest.mark.asyncio
    async def test_slow_request_logging(self, middleware, caplog):
        """测试慢请求日志记录"""
        # 创建模拟请求和响应
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/slow"
        request.url.__str__ = Mock(return_value="http://test.com/slow")
        request.body = AsyncMock(return_value=b"")

        call_next = AsyncMock()
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}

        # 模拟慢请求
        async def slow_call_next(req):
            await asyncio.sleep(1.1)  # 超过1秒阈值
            return response

        call_next.side_effect = slow_call_next

        # 处理请求
        with patch("src.performance.middleware.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            # 验证慢请求警告被记录
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0][0]
            assert "Slow request detected" in call_args

    @pytest.mark.asyncio
    async def test_error_request_logging(self, middleware, caplog):
        """测试错误请求日志记录"""
        # 创建模拟请求和响应
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/error"
        request.url.__str__ = Mock(return_value="http://test.com/error")
        request.body = AsyncMock(return_value=b"")

        call_next = AsyncMock()
        response = Mock(spec=Response)
        response.status_code = 404
        response.headers = {}
        call_next.return_value = response

        # 处理请求
        with patch("src.performance.middleware.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            # 验证错误请求警告被记录
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0][0]
            assert "Error request" in call_args
            assert "404" in call_args

    @pytest.mark.asyncio
    async def test_exception_handling(self, middleware):
        """测试异常处理"""
        # 创建模拟请求
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/error"
        request.url.__str__ = Mock(return_value="http://test.com/error")
        request.body = AsyncMock(return_value=b"")

        call_next = AsyncMock()
        call_next.side_effect = Exception("Test error")

        # 处理请求应该抛出异常
        with pytest.raises(Exception, match="Test error"):
            await middleware.dispatch(request, call_next)

        # 验证异常被记录
        assert middleware.total_requests == 0  # 失败的请求不计入总数

    def test_get_performance_stats(self, middleware):
        """测试获取性能统计"""
        # 添加一些请求时间
        middleware.request_times = [0.1, 0.2, 0.3, 0.4, 0.5]
        middleware.total_requests = 5
        middleware.max_concurrent_requests = 3

        # 模拟API分析器统计
        middleware.api_profiler.endpoint_stats = {
            "/api/test": {
                "request_count": 10,
                "total_duration": 1.0,
                "average_duration": 0.1,
                "status_codes": {200: 8, 404: 2},
            }
        }

        _stats = middleware.get_performance_stats()

        assert stats["total_requests"] == 5
        assert stats["max_concurrent_requests"] == 3
        assert "response_time" in stats
        assert stats["response_time"]["average"] == 0.3
        assert stats["response_time"]["min"] == 0.1
        assert stats["response_time"]["max"] == 0.5
        assert stats["response_time"]["p50"] == 0.3
        assert stats["response_time"]["p95"] == 0.5
        assert stats["response_time"]["p99"] == 0.5

    def test_percentile_calculation(self, middleware):
        """测试百分位数计算"""
        # 测试空数据
        assert middleware._percentile([], 50) == 0

        # 测试各种百分位数
        _data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert middleware._percentile(data, 0) == 1
        assert middleware._percentile(data, 50) == 5
        assert middleware._percentile(data, 95) == 10
        assert middleware._percentile(data, 100) == 10

    def test_reset_stats(self, middleware):
        """测试重置统计"""
        # 添加一些数据
        middleware.total_requests = 10
        middleware.max_concurrent_requests = 5
        middleware.request_times = [0.1, 0.2, 0.3]
        middleware.api_profiler.endpoint_stats = {"/test": {}}

        # 重置
        middleware.reset_stats()

        assert middleware.total_requests == 0
        assert middleware.max_concurrent_requests == 0
        assert middleware.request_times == []
        assert middleware.api_profiler.endpoint_stats == {}


class TestDatabasePerformanceMiddleware:
    """数据库性能监控中间件测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.db_middleware = DatabasePerformanceMiddleware()

    @pytest.mark.asyncio
    async def test_track_query(self):
        """测试跟踪查询"""
        await self.db_middleware.track_query(
            query="SELECT * FROM users WHERE id = 1", duration=0.05, rows_affected=1
        )

        _stats = self.db_middleware.get_query_stats()
        assert stats["total_queries"] == 1
        assert "SELECT" in stats["query_types"]
        assert stats["query_types"]["SELECT"]["count"] == 1
        assert stats["query_types"]["SELECT"]["average_time"] == 0.05
        assert stats["query_types"]["SELECT"]["rows_total"] == 1

    @pytest.mark.asyncio
    async def test_track_slow_query(self):
        """测试跟踪慢查询"""
        await self.db_middleware.track_query(
            query="SELECT * FROM large_table",
            duration=0.2,  # 超过0.1秒阈值
            rows_affected=1000,
        )

        _stats = self.db_middleware.get_query_stats()
        assert len(stats["slow_queries"]) == 1
        assert stats["slow_queries"][0]["duration"] == 0.2
        assert "SELECT * FROM large_table" in stats["slow_queries"][0]["query"]

    @pytest.mark.asyncio
    async def test_track_query_with_error(self):
        """测试跟踪带错误的查询"""
        await self.db_middleware.track_query(
            query="INVALID SQL QUERY",
            duration=0.01,
            rows_affected=0,
            error="syntax error",
        )

        _stats = self.db_middleware.get_query_stats()
        assert stats["query_types"]["UNKNOWN"]["error_count"] == 1
        assert stats["query_types"]["UNKNOWN"]["error_rate"] == 1.0

    def test_get_query_stats(self):
        """测试获取查询统计"""
        # 添加一些查询
        self.db_middleware.total_queries = 10
        self.db_middleware.query_stats = {
            "SELECT": {
                "count": 6,
                "total_time": 0.6,
                "rows_total": 600,
                "error_count": 0,
            },
            "INSERT": {
                "count": 3,
                "total_time": 0.15,
                "rows_total": 3,
                "error_count": 1,
            },
            "UPDATE": {
                "count": 1,
                "total_time": 0.05,
                "rows_total": 1,
                "error_count": 0,
            },
        }

        _stats = self.db_middleware.get_query_stats()

        assert stats["total_queries"] == 10
        assert len(stats["query_types"]) == 3
        assert stats["query_types"]["SELECT"]["average_time"] == 0.1
        assert stats["query_types"]["INSERT"]["error_rate"] == 1 / 3


class TestCachePerformanceMiddleware:
    """缓存性能监控中间件测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.cache_middleware = CachePerformanceMiddleware()

    def test_record_cache_hit(self):
        """测试记录缓存命中"""
        self.cache_middleware.record_cache_hit(0.001)

        _stats = self.cache_middleware.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["total_requests"] == 1
        assert stats["hit_rate"] == 1.0
        assert stats["average_hit_time"] == 0.001

    def test_record_cache_miss(self):
        """测试记录缓存未命中"""
        self.cache_middleware.record_cache_miss()

        _stats = self.cache_middleware.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["total_requests"] == 1
        assert stats["hit_rate"] == 0.0

    def test_mixed_cache_operations(self):
        """测试混合缓存操作"""
        # 记录多次操作
        self.cache_middleware.record_cache_hit(0.001)
        self.cache_middleware.record_cache_hit(0.002)
        self.cache_middleware.record_cache_miss()
        self.cache_middleware.record_cache_set(0.01)
        self.cache_middleware.record_cache_delete()

        _stats = self.cache_middleware.get_cache_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["deletes"] == 1
        assert stats["total_requests"] == 3  # hits + misses
        assert stats["hit_rate"] == 2 / 3
        assert stats["average_hit_time"] == 0.0015
        assert stats["average_set_time"] == 0.01

    def test_cache_time_history_limit(self):
        """测试缓存时间历史限制"""
        # 添加超过限制的时间记录
        for i in range(1005):
            self.cache_middleware.record_cache_hit(0.001 * i)

        _stats = self.cache_middleware.get_cache_stats()

        # 应该只保留最近1000条
        assert len(self.cache_middleware.cache_stats["hit_times"]) == 1000
        assert stats["hits"] == 1005  # 但计数器应该保留所有


class TestBackgroundTaskPerformanceMonitor:
    """后台任务性能监控器测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.task_monitor = BackgroundTaskPerformanceMonitor()

    def test_task_lifecycle(self):
        """测试任务生命周期"""
        task_id = "task_123"
        task_name = "data_processing"

        # 开始任务
        self.task_monitor.start_task(task_id, task_name)
        assert len(self.task_monitor.active_tasks) == 1
        assert self.task_monitor.active_tasks[task_id]["name"] == task_name

        # 模拟一些时间过去
        time.sleep(0.01)

        # 结束任务（成功）
        self.task_monitor.end_task(task_id, success=True)
        assert len(self.task_monitor.active_tasks) == 0

        # 检查统计
        _stats = self.task_monitor.get_task_stats()
        assert stats["active_tasks"] == 0
        assert task_name in stats["task_types"]
        assert stats["task_types"][task_name]["total_count"] == 1
        assert stats["task_types"][task_name]["success_count"] == 1
        assert stats["task_types"][task_name]["failure_count"] == 0
        assert stats["task_types"][task_name]["success_rate"] == 1.0
        assert stats["task_types"][task_name]["average_time"] > 0

    def test_task_failure(self):
        """测试任务失败"""
        task_id = "task_456"
        task_name = "failing_task"

        # 开始和结束任务（失败）
        self.task_monitor.start_task(task_id, task_name)
        self.task_monitor.end_task(task_id, success=False, error="Connection timeout")

        _stats = self.task_monitor.get_task_stats()

        assert stats["task_types"][task_name]["success_count"] == 0
        assert stats["task_types"][task_name]["failure_count"] == 1
        assert stats["task_types"][task_name]["success_rate"] == 0.0
        assert len(stats["recent_failures"]) == 1
        assert stats["recent_failures"][0]["error"] == "Connection timeout"

    def test_multiple_task_types(self):
        """测试多种任务类型"""
        # 添加不同类型的任务
        tasks = [
            ("task_1", "email_send", True, None),
            ("task_2", "email_send", True, None),
            ("task_3", "email_send", False, "SMTP error"),
            ("task_4", "data_sync", True, None),
            ("task_5", "data_sync", True, None),
        ]

        for task_id, task_name, success, error in tasks:
            self.task_monitor.start_task(task_id, task_name)
            time.sleep(0.001)  # 确保有不同的时间
            self.task_monitor.end_task(task_id, success=success, error=error)

        _stats = self.task_monitor.get_task_stats()

        # 验证email_send任务
        email_stats = stats["task_types"]["email_send"]
        assert email_stats["total_count"] == 3
        assert email_stats["success_rate"] == 2 / 3

        # 验证data_sync任务
        sync_stats = stats["task_types"]["data_sync"]
        assert sync_stats["total_count"] == 2
        assert sync_stats["success_rate"] == 1.0

    def test_nonexistent_task_end(self):
        """测试结束不存在的任务"""
        # 尝试结束一个不存在的任务
        self.task_monitor.end_task("nonexistent_task", success=True)

        # 应该不抛出错误
        _stats = self.task_monitor.get_task_stats()
        assert stats["active_tasks"] == 0

    def test_failure_history_limit(self):
        """测试失败历史限制"""
        # 添加超过限制的失败任务
        for i in range(105):
            task_id = f"task_{i}"
            self.task_monitor.start_task(task_id, "test_task")
            self.task_monitor.end_task(task_id, success=False, error=f"Error {i}")

        _stats = self.task_monitor.get_task_stats()

        # 应该只保留最近100个失败
        assert len(self.task_monitor.failed_tasks) == 100
        assert len(stats["recent_failures"]) == 10  # get_task_stats返回最近10个
