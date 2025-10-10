"""
性能分析器测试
Performance Profiler Tests
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.performance.profiler import (
    PerformanceProfiler,
    get_profiler,
    profile_function,
    profile_method,
    DatabaseQueryProfiler,
    APIEndpointProfiler,
    MemoryProfiler,
    PerformanceMetric,
    FunctionProfile,
    QueryProfile,
    start_profiling,
    stop_profiling,
    get_performance_report,
)


class TestPerformanceProfiler:
    """性能分析器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.profiler = PerformanceProfiler()

    def test_init(self):
        """测试初始化"""
        assert self.profiler.metrics == []
        assert self.profiler.function_profiles == {}
        assert self.profiler.query_profiles == []
        assert self.profiler.active_profiling is False
        assert self.profiler.profiler is not None

    def test_start_profiling(self):
        """测试启动性能分析"""
        self.profiler.start_profiling()
        assert self.profiler.active_profiling is True

    def test_stop_profiling(self):
        """测试停止性能分析"""
        self.profiler.start_profiling()
        result = self.profiler.stop_profiling()

        assert self.profiler.active_profiling is False
        assert isinstance(result, dict)
        assert "function_count" in result
        assert "total_time" in result
        assert "function_profiles" in result

    def test_record_metric(self):
        """测试记录性能指标"""
        self.profiler.record_metric(
            name="test_metric", value=100.0, unit="ms", tags={"endpoint": "/test"}
        )

        assert len(self.profiler.metrics) == 1
        metric = self.profiler.metrics[0]
        assert metric.name == "test_metric"
        assert metric.value == 100.0
        assert metric.unit == "ms"
        assert metric.tags["endpoint"] == "/test"

    def test_record_function_call(self):
        """测试记录函数调用"""
        self.profiler.record_function_call(
            function_name="test_function",
            execution_time=0.05,
            args_count=2,
            kwargs_count=1,
            return_value_size=100,
        )

        assert "test_function" in self.profiler.function_profiles
        profile = self.profiler.function_profiles["test_function"]
        assert profile.call_count == 1
        assert profile.total_time == 0.05
        assert profile.average_time == 0.05

    def test_record_database_query(self):
        """测试记录数据库查询"""
        self.profiler.record_database_query(
            query="SELECT * FROM users",
            execution_time=0.1,
            rows_affected=10,
            query_type="SELECT",
        )

        assert len(self.profiler.query_profiles) == 1
        query = self.profiler.query_profiles[0]
        assert query.query == "SELECT * FROM users"
        assert query.execution_time == 0.1
        assert query.rows_affected == 10
        assert query.query_type == "SELECT"

    def test_get_metrics_summary(self):
        """测试获取指标摘要"""
        # 添加一些指标
        self.profiler.record_metric("response_time", 100.0, "ms")
        self.profiler.record_metric("response_time", 150.0, "ms")
        self.profiler.record_metric("memory_usage", 50.0, "MB")

        summary = self.profiler.get_metrics_summary()

        assert "response_time" in summary
        assert "memory_usage" in summary
        assert summary["response_time"]["count"] == 2
        assert summary["response_time"]["average"] == 125.0
        assert summary["memory_usage"]["count"] == 1

    def test_get_slow_functions(self):
        """测试获取慢函数"""
        # 添加一些函数调用
        self.profiler.record_function_call("fast_function", 0.01)
        self.profiler.record_function_call("slow_function", 0.5)
        self.profiler.record_function_call("very_slow_function", 1.0)

        slow_functions = self.profiler.get_slow_functions(threshold=0.1)

        assert len(slow_functions) == 2
        assert slow_functions[0].function_name == "very_slow_function"
        assert slow_functions[1].function_name == "slow_function"

    def test_get_slow_queries(self):
        """测试获取慢查询"""
        # 添加一些查询
        self.profiler.record_database_query("FAST QUERY", 0.05)
        self.profiler.record_database_query("SLOW QUERY", 0.2)

        slow_queries = self.profiler.get_slow_queries(threshold=0.1)

        assert len(slow_queries) == 1
        assert slow_queries[0].query == "SLOW QUERY"
        assert slow_queries[0].execution_time == 0.2

    def test_reset(self):
        """测试重置分析器"""
        # 添加一些数据
        self.profiler.record_metric("test", 100.0)
        self.profiler.record_function_call("test_func", 0.1)

        # 重置
        self.profiler.reset()

        assert self.profiler.metrics == []
        assert self.profiler.function_profiles == {}
        assert self.profiler.query_profiles == []


class TestDatabaseQueryProfiler:
    """数据库查询分析器测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.main_profiler = Mock()
        self.db_profiler = DatabaseQueryProfiler(self.main_profiler)

    def test_track_query(self):
        """测试跟踪查询"""
        self.db_profiler.track_query(
            query="SELECT * FROM users", execution_time=0.1, rows_affected=5
        )

        # 验证主分析器的方法被调用
        self.main_profiler.record_database_query.assert_called_once_with(
            query="SELECT * FROM users",
            execution_time=0.1,
            rows_affected=5,
            query_type="SELECT",
        )

    def test_get_query_type(self):
        """测试获取查询类型"""
        assert self.db_profiler._get_query_type("SELECT * FROM users") == "SELECT"
        assert self.db_profiler._get_query_type("INSERT INTO users") == "INSERT"
        assert self.db_profiler._get_query_type("  update users set") == "UPDATE"
        assert self.db_profiler._get_query_type("") == "UNKNOWN"


class TestAPIEndpointProfiler:
    """API端点分析器测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.main_profiler = Mock()
        self.api_profiler = APIEndpointProfiler(self.main_profiler)

    def test_record_endpoint_request(self):
        """测试记录端点请求"""
        self.api_profiler.record_endpoint_request(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            duration=0.05,
            request_size=100,
            response_size=500,
        )

        # 验证指标被记录
        self.main_profiler.record_metric.assert_called()

        # 检查端点统计
        assert "/api/test" in self.api_profiler.endpoint_stats
        stats = self.api_profiler.endpoint_stats["/api/test"]
        assert stats["request_count"] == 1
        assert stats["total_duration"] == 0.05
        assert stats["average_duration"] == 0.05

    def test_get_endpoint_stats(self):
        """测试获取端点统计"""
        # 添加一些请求
        self.api_profiler.record_endpoint_request("/api/test", "GET", 200, 0.1)
        self.api_profiler.record_endpoint_request("/api/test", "GET", 200, 0.2)
        self.api_profiler.record_endpoint_request("/api/other", "POST", 201, 0.15)

        stats = self.api_profiler.get_endpoint_stats()

        assert len(stats) == 2
        assert stats["/api/test"]["request_count"] == 2
        assert stats["/api/test"]["average_duration"] == 0.15
        assert stats["/api/other"]["request_count"] == 1

    def test_get_slow_endpoints(self):
        """测试获取慢端点"""
        # 添加一些请求
        self.api_profiler.record_endpoint_request("/api/fast", "GET", 200, 0.05)
        self.api_profiler.record_endpoint_request("/api/slow", "GET", 200, 0.5)

        slow_endpoints = self.api_profiler.get_slow_endpoints(threshold=0.1)

        assert len(slow_endpoints) == 1
        assert slow_endpoints[0]["endpoint"] == "/api/slow"
        assert slow_endpoints[0]["average_duration"] == 0.5


class TestMemoryProfiler:
    """内存分析器测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.main_profiler = Mock()
        self.memory_profiler = MemoryProfiler(self.main_profiler)

    @patch("src.performance.profiler.psutil")
    def test_track_memory_usage(self, mock_psutil):
        """测试跟踪内存使用"""
        # 模拟psutil返回值
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        mock_psutil.Process.return_value = mock_process
        mock_psutil.virtual_memory.return_value.percent = 50.0

        self.memory_profiler.track_memory_usage()

        # 验证内存指标被记录
        self.main_profiler.record_metric.assert_called()
        call_args = self.main_profiler.record_metric.call_args
        assert call_args[0][0] == "memory_usage"
        assert call_args[0][1] == 100.0  # MB

    @patch("src.performance.profiler.psutil")
    def test_detect_memory_leak(self, mock_psutil):
        """测试内存泄漏检测"""
        # 模拟内存使用历史
        self.memory_profiler.memory_samples = [100, 105, 110, 115, 120]  # 稳定增长

        leak_detected = self.memory_profiler.detect_memory_leak()

        # 由于内存持续增长，应该检测到泄漏
        assert isinstance(leak_detected, dict)
        assert "leak_detected" in leak_detected
        assert "trend" in leak_detected


class TestProfileDecorators:
    """性能分析装饰器测试"""

    def test_profile_function_decorator(self):
        """测试函数分析装饰器"""

        @profile_function
        def test_function(x, y):
            time.sleep(0.01)  # 模拟耗时操作
            return x + y

        # 调用函数
        result = test_function(1, 2)
        assert result == 3

        # 验证函数被分析
        profiler = get_profiler()
        assert "test_function" in profiler.function_profiles

    def test_profile_method_decorator(self):
        """测试方法分析装饰器"""

        class TestClass:
            @profile_method
            def test_method(self, value):
                time.sleep(0.01)
                return value * 2

        obj = TestClass()
        result = obj.test_method(5)
        assert result == 10

        # 验证方法被分析
        profiler = get_profiler()
        # 方法名可能包含类名
        method_found = any("test_method" in name for name in profiler.function_profiles)
        assert method_found


class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_profiler_singleton(self):
        """测试获取全局分析器实例"""
        profiler1 = get_profiler()
        profiler2 = get_profiler()
        assert profiler1 is profiler2

    def test_start_stop_profiling_functions(self):
        """测试全局启动/停止分析函数"""
        start_profiling()

        profiler = get_profiler()
        assert profiler.active_profiling is True

        results = stop_profiling()
        assert profiler.active_profiling is False
        assert isinstance(results, dict)

    def test_get_performance_report(self):
        """测试获取性能报告"""
        # 添加一些数据
        profiler = get_profiler()
        profiler.record_metric("test_metric", 100.0)

        report = get_performance_report()

        assert isinstance(report, dict)
        assert "timestamp" in report
        assert "metrics_summary" in report
