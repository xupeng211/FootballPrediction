"""监控工具测试"""
import pytest
from unittest.mock import Mock
from src.monitoring.metrics_collector import MetricsCollector
from src.monitoring.system_monitor import SystemMonitor


class TestMonitoringUtils:
    """测试监控工具"""

    def test_metrics_collector_creation(self):
        """测试指标收集器创建"""
        collector = MetricsCollector()
        assert collector is not None

    def test_system_monitor_creation(self):
        """测试系统监控器创建"""
        monitor = SystemMonitor()
        assert monitor is not None

    def test_metrics_collection(self):
        """测试指标收集"""
        collector = MetricsCollector()

        # Mock内部方法
        collector.collect_system_metrics = Mock(return_value={"cpu": 50})
        collector.collect_database_metrics = Mock(return_value={"db": 100})
        collector.collect_application_metrics = Mock(return_value={"app": 200})

        # 调用收集方法
        system_metrics = collector.collect_system_metrics()
        db_metrics = collector.collect_database_metrics()
        app_metrics = collector.collect_application_metrics()

        # 验证方法被调用
        collector.collect_system_metrics.assert_called_once()
        collector.collect_database_metrics.assert_called_once()
        collector.collect_application_metrics.assert_called_once()

        # 验证返回值
        assert system_metrics == {"cpu": 50}
        assert db_metrics == {"db": 100}
        assert app_metrics == {"app": 200}

    def test_system_metrics(self):
        """测试系统指标"""
        monitor = SystemMonitor()

        # 测试记录方法
        monitor.record_request("GET", "/api/health", 200, 0.1)
        monitor.record_database_query("SELECT", "matches", 0.05, False)
        monitor.record_cache_operation("GET", "redis", "hit")
        monitor.record_prediction("v1.0", "premier_league")

        # 验证指标对象存在
        assert hasattr(monitor, 'app_requests_total')
        assert hasattr(monitor, 'db_query_duration_seconds')
        assert hasattr(monitor, 'cache_operations_total')
        assert hasattr(monitor, 'business_predictions_total')

        # 测试获取健康状态方法存在
        assert hasattr(monitor, 'get_health_status')
        assert callable(monitor.get_health_status)

    def test_metrics_export(self):
        """测试指标导出"""
        collector = MetricsCollector()

        # 测试格式化方法
        test_metrics = {"cpu": 80, "memory": 60}
        formatted = collector.format_metrics_for_export(test_metrics)

        assert "timestamp" in formatted
        assert "metrics" in formatted
        assert formatted["metrics"] == test_metrics
        assert formatted["export_format"] == "prometheus"

        # 测试获取状态
        status = collector.get_status()
        assert "running" in status
        assert "collection_interval" in status