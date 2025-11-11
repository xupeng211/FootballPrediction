"""
性能监控测试
Performance Monitoring Tests

测试性能监控系统的核心功能。
Tests core functionality of performance monitoring system.
"""

import time
from unittest.mock import Mock, patch

import pytest

from src.performance.monitoring import (
    PerformanceAnalyzer,
    PerformanceMetrics,
    SystemMonitor,
    get_performance_analyzer,
    get_system_monitor,
)


class TestPerformanceMetrics:
    """性能指标数据类测试"""

    def test_performance_metrics_creation(self):
        """测试性能指标创建"""
        timestamp = time.time()
        metrics = PerformanceMetrics(
            timestamp=timestamp,
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            memory_available_mb=2048.0,
            disk_usage_percent=30.0,
            active_connections=100,
            response_time_avg=0.5,
            requests_per_second=10.0,
            error_rate=0.01,
        )

        assert metrics.timestamp == timestamp
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 60.0
        assert metrics.memory_used_mb == 1024.0
        assert metrics.memory_available_mb == 2048.0
        assert metrics.disk_usage_percent == 30.0
        assert metrics.active_connections == 100
        assert metrics.response_time_avg == 0.5
        assert metrics.requests_per_second == 10.0
        assert metrics.error_rate == 0.01

    def test_performance_metrics_default_values(self):
        """测试性能指标默认值"""
        timestamp = time.time()
        metrics = PerformanceMetrics(
            timestamp=timestamp,
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_mb=0.0,
            memory_available_mb=0.0,
            disk_usage_percent=0.0,
            active_connections=0,
            response_time_avg=0.0,
            requests_per_second=0.0,
            error_rate=0.0,
        )

        assert metrics.timestamp == timestamp
        assert metrics.cpu_percent == 0.0
        assert metrics.memory_percent == 0.0
        assert metrics.memory_used_mb == 0.0
        assert metrics.memory_available_mb == 0.0
        assert metrics.disk_usage_percent == 0.0
        assert metrics.active_connections == 0
        assert metrics.response_time_avg == 0.0
        assert metrics.requests_per_second == 0.0
        assert metrics.error_rate == 0.0


class TestSystemMonitor:
    """系统监控器测试类"""

    @pytest.fixture
    def system_monitor(self):
        """系统监控器实例"""
        return SystemMonitor()

    def test_system_monitor_initialization(self, system_monitor):
        """测试系统监控器初始化"""
        assert system_monitor is not None
        assert hasattr(system_monitor, "metrics_history")
        assert hasattr(system_monitor, "max_history")
        assert system_monitor.max_history == 1000
        assert len(system_monitor.metrics_history) == 0

    def test_get_current_metrics(self, system_monitor):
        """测试获取当前指标"""
        with (
            patch("psutil.cpu_percent", return_value=45.5),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
            patch("psutil.net_connections") as mock_connections,
        ):
            # 模拟内存数据
            mock_memory_obj = Mock()
            mock_memory_obj.total = 8589934592
            mock_memory_obj.used = 4294967296
            mock_memory_obj.available = 4294967296
            mock_memory_obj.percent = 50.0
            mock_memory.return_value = mock_memory_obj

            # 模拟磁盘数据
            mock_disk_obj = Mock()
            mock_disk_obj.total = 1000000000000
            mock_disk_obj.used = 300000000000
            mock_disk_obj.percent = 30.0
            mock_disk.return_value = mock_disk_obj

            # 模拟网络连接数据
            mock_connections.return_value = [
                Mock(status="ESTABLISHED"),
                Mock(status="ESTABLISHED"),
                Mock(status="CLOSED"),
            ]

            metrics = system_monitor.get_current_metrics()

            assert isinstance(metrics, PerformanceMetrics)
            assert metrics.cpu_percent == 45.5
            assert metrics.memory_percent == 50.0
            assert metrics.memory_used_mb == mock_memory_obj.used / (1024 * 1024)
            assert metrics.memory_available_mb == mock_memory_obj.available / (
                1024 * 1024
            )
            assert metrics.disk_usage_percent == 30.0
            assert metrics.active_connections == 2  # 只有ESTABLISHED状态的连接

    def test_get_current_metrics_exception_handling(self, system_monitor):
        """测试获取当前指标时的异常处理"""
        with patch("psutil.cpu_percent", side_effect=Exception("PSUtil error")):
            metrics = system_monitor.get_current_metrics()

            # 应该返回默认值
            assert isinstance(metrics, PerformanceMetrics)
            assert metrics.cpu_percent == 0.0
            assert metrics.memory_percent == 0.0
            assert metrics.response_time_avg == 0.0

    def test_record_metrics(self, system_monitor):
        """测试记录指标"""
        timestamp = time.time()
        metrics = PerformanceMetrics(
            timestamp=timestamp,
            cpu_percent=60.0,
            memory_percent=70.0,
            memory_used_mb=1500.0,
            memory_available_mb=1000.0,
            disk_usage_percent=40.0,
            active_connections=150,
            response_time_avg=0.8,
            requests_per_second=15.0,
            error_rate=0.02,
        )

        system_monitor.record_metrics(metrics)

        assert len(system_monitor.metrics_history) == 1
        assert system_monitor.metrics_history[0] == metrics

    def test_metrics_history_limit(self, system_monitor):
        """测试指标历史记录限制"""
        # 添加超过限制的指标
        for i in range(1005):
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=float(i),
                memory_percent=float(i),
                memory_used_mb=float(i),
                memory_available_mb=float(i),
                disk_usage_percent=float(i),
                active_connections=i,
                response_time_avg=float(i),
                requests_per_second=float(i),
                error_rate=float(i) / 1000,
            )
            system_monitor.record_metrics(metrics)

        # 应该只保留最新的1000个记录
        assert len(system_monitor.metrics_history) == 1000
        # 最新的指标应该在历史记录中
        assert system_monitor.metrics_history[-1].cpu_percent == 1004.0

    def test_get_metrics_summary_empty(self, system_monitor):
        """测试空指标摘要"""
        summary = system_monitor.get_metrics_summary(minutes=5)

        assert summary == {}

    def test_get_metrics_summary_with_data(self, system_monitor):
        """测试有数据的指标摘要"""
        current_time = time.time()

        # 添加一些测试数据
        for i in range(10):
            timestamp = current_time - (i * 60)  # 每分钟一个数据点
            metrics = PerformanceMetrics(
                timestamp=timestamp,
                cpu_percent=50.0 + i * 2,
                memory_percent=60.0 + i * 1,
                memory_used_mb=1000.0 + i * 100,
                memory_available_mb=2000.0 - i * 50,
                disk_usage_percent=30.0,
                active_connections=100 + i * 5,
                response_time_avg=0.5 + i * 0.1,
                requests_per_second=10.0 + i,
                error_rate=0.01 + i * 0.001,
            )
            system_monitor.record_metrics(metrics)

        summary = system_monitor.get_metrics_summary(minutes=10)

        assert "time_range_minutes" in summary
        assert summary["time_range_minutes"] == 10
        assert "sample_count" in summary
        assert summary["sample_count"] == 10

        # 检查CPU统计
        assert "cpu" in summary
        cpu_stats = summary["cpu"]
        assert "avg" in cpu_stats
        assert "min" in cpu_stats
        assert "max" in cpu_stats
        assert "current" in cpu_stats
        assert (
            cpu_stats["avg"] == 59.0
        )  # (50 + 52 + 54 + 56 + 58 + 60 + 62 + 64 + 66 + 68) / 10

        # 检查内存统计
        assert "memory" in summary
        assert "performance" in summary
        assert "resources" in summary

    def test_check_performance_alerts_normal(self, system_monitor):
        """测试正常性能警报检查"""
        with (
            patch("psutil.cpu_percent", return_value=30.0),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
        ):
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 50.0
            mock_memory.return_value = mock_memory_obj

            mock_disk_obj = Mock()
            mock_disk_obj.percent = 40.0
            mock_disk.return_value = mock_disk_obj

            system_monitor.get_current_metrics()
            alerts = system_monitor.check_performance_alerts()

            # 正常情况下不应该有警报
            assert len(alerts) == 0

    def test_check_performance_alerts_high_cpu(self, system_monitor):
        """测试高CPU警报"""
        with (
            patch("psutil.cpu_percent", return_value=85.0),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
        ):
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 60.0
            mock_memory.return_value = mock_memory_obj

            mock_disk_obj = Mock()
            mock_disk_obj.percent = 40.0
            mock_disk.return_value = mock_disk_obj

            system_monitor.get_current_metrics()
            alerts = system_monitor.check_performance_alerts()

            assert len(alerts) >= 1
            cpu_alert = next(
                (alert for alert in alerts if alert["type"] == "cpu_high"), None
            )
            assert cpu_alert is not None
            assert cpu_alert["severity"] == "warning"
            assert cpu_alert["value"] == 85.0
            assert cpu_alert["threshold"] == 80

    def test_check_performance_alerts_critical_cpu(self, system_monitor):
        """测试严重CPU警报"""
        with (
            patch("psutil.cpu_percent", return_value=95.0),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
        ):
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 60.0
            mock_memory.return_value = mock_memory_obj

            mock_disk_obj = Mock()
            mock_disk_obj.percent = 40.0
            mock_disk.return_value = mock_disk_obj

            system_monitor.get_current_metrics()
            alerts = system_monitor.check_performance_alerts()

            cpu_alert = next(
                (alert for alert in alerts if alert["type"] == "cpu_high"), None
            )
            assert cpu_alert is not None
            assert cpu_alert["severity"] == "critical"
            assert cpu_alert["value"] == 95.0

    def test_check_performance_alerts_memory(self, system_monitor):
        """测试内存警报"""
        with (
            patch("psutil.cpu_percent", return_value=30.0),
            patch("psutil.virtual_memory"),
            patch("psutil.disk_usage"),
        ):
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 90.0
            mock_disk_obj = Mock()
            mock_disk_obj.percent = 40.0

            system_monitor.get_current_metrics()
            alerts = system_monitor.check_performance_alerts()

            memory_alert = next(
                (alert for alert in alerts if alert["type"] == "memory_high"), None
            )
            assert memory_alert is not None
            assert memory_alert["severity"] == "warning"
            assert memory_alert["value"] == 90.0
            assert memory_alert["threshold"] == 85

    def test_check_performance_alerts_response_time(self, system_monitor):
        """测试响应时间警报"""
        with (
            patch("psutil.cpu_percent", return_value=30.0),
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
        ):
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 60.0
            mock_memory.return_value = mock_memory_obj

            mock_disk_obj = Mock()
            mock_disk_obj.percent = 40.0
            mock_disk.return_value = mock_disk_obj

            # 模拟慢响应时间
            with patch.object(
                system_monitor, "_get_avg_response_time", return_value=2.5
            ):
                system_monitor.get_current_metrics()
                alerts = system_monitor.check_performance_alerts()

                response_alert = next(
                    (
                        alert
                        for alert in alerts
                        if alert["type"] == "response_time_high"
                    ),
                    None,
                )
                assert response_alert is not None
                assert response_alert["severity"] == "critical"
                assert response_alert["value"] == 2.5
                assert response_alert["threshold"] == 2.0

    def test_get_avg_response_time(self, system_monitor):
        """测试获取平均响应时间"""
        # 这个方法目前返回模拟数据
        response_time = system_monitor._get_avg_response_time()
        assert isinstance(response_time, float)
        assert response_time > 0


class TestPerformanceAnalyzer:
    """性能分析器测试类"""

    @pytest.fixture
    def performance_analyzer(self):
        """性能分析器实例"""
        return PerformanceAnalyzer()

    def test_performance_analyzer_initialization(self, performance_analyzer):
        """测试性能分析器初始化"""
        assert performance_analyzer is not None
        assert hasattr(performance_analyzer, "metrics_history")
        assert hasattr(performance_analyzer, "analysis_results")

    def test_analyze_trends_insufficient_data(self, performance_analyzer):
        """测试分析趋势（数据不足）"""
        trends = performance_analyzer.analyze_trends(hours=1)

        assert "error" in trends
        assert trends["error"] == "Insufficient data for trend analysis"

    def test_analyze_trends_with_data(self, performance_analyzer):
        """测试分析趋势（有足够数据）"""
        current_time = time.time()

        # 添加历史数据
        for i in range(10):
            timestamp = current_time - (i * 3600)  # 每小时一个数据点
            metrics = PerformanceMetrics(
                timestamp=timestamp,
                cpu_percent=40.0 + i * 2,
                memory_percent=50.0 + i * 1,
                memory_used_mb=800.0 + i * 50,
                memory_available_mb=1600.0 - i * 25,
                disk_usage_percent=25.0,
                active_connections=80 + i * 3,
                response_time_avg=0.4 + i * 0.05,
                requests_per_second=8.0 + i * 0.5,
                error_rate=0.008 + i * 0.0002,
            )
            performance_analyzer.metrics_history.append(metrics)

        trends = performance_analyzer.analyze_trends(hours=2)

        assert "time_range_hours" in trends
        assert trends["time_range_hours"] == 2
        assert "data_points" in trends
        assert trends["data_points"] == 10
        assert "trends" in trends

        # 检查CPU趋势
        cpu_trend = trends["trends"]["cpu"]
        assert "trend" in cpu_trend
        assert "change" in cpu_trend
        assert cpu_trend["trend"] in [
            "increasing",
            "decreasing",
            "stable",
            "insufficient_data",
        ]

    def test_calculate_trend_increasing(self, performance_analyzer):
        """测试计算递增趋势"""
        values = [10, 20, 30, 40, 50]
        trend = performance_analyzer._calculate_trend(values)

        assert trend == "increasing"

    def test_calculate_trend_decreasing(self, performance_analyzer):
        """测试计算递减趋势"""
        values = [50, 40, 30, 20, 10]
        trend = performance_analyzer._calculate_trend(values)

        assert trend == "decreasing"

    def test_calculate_trend_stable(self, performance_analyzer):
        """测试计算稳定趋势"""
        values = [30, 31, 29, 30, 30]
        trend = performance_analyzer._calculate_trend(values)

        assert trend == "stable"

    def test_calculate_trend_insufficient_data(self, performance_analyzer):
        """测试计算趋势（数据不足）"""
        values = [30]
        trend = performance_analyzer._calculate_trend(values)

        assert trend == "insufficient_data"

    def test_get_performance_recommendations(self, performance_analyzer):
        """测试获取性能建议"""
        metrics_summary = {
            "cpu": {"avg": 75.0},
            "memory": {"avg": 80.0},
            "performance": {
                "avg_response_time": 1.5,
                "avg_requests_per_second": 8.0,
                "avg_error_rate": 0.025,
            },
            "resources": {"avg_connections": 120},
        }

        recommendations = performance_analyzer.get_performance_recommendations(
            metrics_summary
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # 应该有CPU使用率建议
        cpu_recommendation = next(
            (rec for rec in recommendations if "CPU" in rec), None
        )
        assert cpu_recommendation is not None

        # 应该有内存使用率建议
        memory_recommendation = next(
            (rec for rec in recommendations if "内存" in rec), None
        )
        assert memory_recommendation is not None

        # 应该有响应时间建议
        response_recommendation = next(
            (rec for rec in recommendations if "响应时间" in rec), None
        )
        assert response_recommendation is not None


class TestGlobalFunctions:
    """全局函数测试类"""

    def test_get_system_monitor_singleton(self):
        """测试获取系统监控器单例"""
        monitor1 = get_system_monitor()
        monitor2 = get_system_monitor()

        assert monitor1 is monitor2
        assert isinstance(monitor1, SystemMonitor)

    def test_get_performance_analyzer_instance(self):
        """测试获取性能分析器实例"""
        analyzer1 = get_performance_analyzer()
        analyzer2 = get_performance_analyzer()

        assert isinstance(analyzer1, PerformanceAnalyzer)
        assert isinstance(analyzer2, PerformanceAnalyzer)
        # 注意：PerformanceAnalyzer不是单例，每次都创建新实例


class TestPerformanceMonitoringIntegration:
    """性能监控集成测试类"""

    def test_monitoring_workflow(self, system_monitor, performance_analyzer):
        """测试完整的监控工作流"""
        # 1. 收集指标
        current_time = time.time()

        # 模拟收集指标
        for i in range(20):
            timestamp = current_time - (i * 60)  # 每分钟一个数据点
            metrics = PerformanceMetrics(
                timestamp=timestamp,
                cpu_percent=45.0 + i * 0.5,
                memory_percent=55.0 + i * 0.3,
                memory_used_mb=900.0 + i * 20,
                memory_available_mb=1700.0 - i * 10,
                disk_usage_percent=35.0,
                active_connections=90 + i * 2,
                response_time_avg=0.45 + i * 0.02,
                requests_per_second=12.0 + i * 0.3,
                error_rate=0.012 + i * 0.0001,
            )
            system_monitor.record_metrics(metrics)

        # 2. 生成摘要
        summary = system_monitor.get_metrics_summary(minutes=20)

        # 3. 分析趋势
        trends = performance_analyzer.analyze_trends(hours=1)

        # 4. 检查警报
        alerts = system_monitor.check_performance_alerts()

        # 验证工作流结果
        assert "cpu" in summary
        assert "memory" in summary
        assert "trends" in trends
        assert isinstance(alerts, list)

        # 5. 获取建议
        recommendations = performance_analyzer.get_performance_recommendations(summary)
        assert isinstance(recommendations, list)
