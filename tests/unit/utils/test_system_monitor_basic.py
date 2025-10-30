# TODO: Consider creating a fixture for 5 repeated Mock creations

# TODO: Consider creating a fixture for 5 repeated Mock creations

from unittest.mock import Mock, patch

""""""""
系统监控模块基础测试
""""""""

import pytest


def test_module_import():
    """测试模块导入"""
    # 测试导入新模块
    # 测试导入兼容模块
    from src.monitoring.system_monitor_mod import PrometheusMetrics
    from src.monitoring.system_monitor_mod import SystemMonitor
    from src.monitoring.system_monitor_mod import SystemMonitor as LegacySystemMonitor
    from src.monitoring.system_monitor_mod import get_system_monitor

    assert SystemMonitor is not None
    assert PrometheusMetrics is not None
    assert get_system_monitor is not None
    assert LegacySystemMonitor is not None


def test_prometheus_metrics_creation():
    """测试Prometheus指标创建"""
    # 使用独立的注册表避免冲突
    from prometheus_client import CollectorRegistry

    from src.monitoring.system_monitor_mod.metrics import PrometheusMetrics

    registry = CollectorRegistry()
    metrics = PrometheusMetrics(registry=registry)

    # 验证指标已创建
    assert hasattr(metrics, "system_cpu_percent")
    assert hasattr(metrics, "app_requests_total")
    assert hasattr(metrics, "db_query_duration_seconds")


def test_system_monitor_basic():
    """测试系统监控器基本功能"""
    # Mock psutil to avoid system dependencies in tests
    with patch("src.monitoring.system_monitor_mod.collectors.psutil") as mock_psutil:
        # Setup mock values
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = Mock()
        mock_disk.percent = 70.0
        mock_psutil.disk_usage.return_value = mock_disk
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=1024 * 1024 * 100)  # 100MB
        mock_process.cpu_percent.return_value = 30.0
        mock_psutil.Process.return_value = mock_process

from src.monitoring.system_monitor_mod import SystemMonitor

        monitor = SystemMonitor()

        # 测试基本属性
        assert monitor.start_time > 0
        assert monitor.metrics is not None
        assert monitor.collector_manager is not None
        assert monitor.health_checker is not None
        assert monitor.is_monitoring is False

        # 测试便捷方法（不会抛出异常）
        monitor.record_request("GET", "/test", 200, 0.1)
        monitor.record_database_query("SELECT", "matches", 0.05)
        monitor.record_cache_operation("get", "redis", "hit")
        monitor.record_prediction("v1.0", "EPL")

        # 测试状态获取
        status = monitor.get_monitoring_status()
        assert "is_monitoring" in status
        assert "uptime_seconds" in status
        assert "collectors" in status
        assert "health_checkers" in status


@pytest.mark.asyncio
async def test_health_checker_basic():
    """测试健康检查器基本功能"""
    from src.monitoring.system_monitor_mod import HealthChecker

    checker = HealthChecker()

    # 测试获取检查器列表
    checkers = checker.get_checkers()
    assert "database" in checkers
    assert "redis" in checkers
    assert "system_resources" in checkers

    # 测试健康检查（可能失败但不会抛出异常）
    health = await checker.check_all()
    assert "status" in health
    assert "components" in health
    assert "timestamp" in health


def test_global_instance():
    """测试全局实例管理"""
    from src.monitoring.system_monitor_mod import get_system_monitor

    monitor1 = get_system_monitor()
    monitor2 = get_system_monitor()

    # 应该返回同一个实例
    assert monitor1 is monitor2


def test_convenience_functions():
    """测试便捷函数"""
        record_cache_op,
        record_db_query,
        record_http_request,
        record_prediction,
    )

    monitor = Mock()

    # Mock the get_system_monitor function
    with patch(
        "src.monitoring.system_monitor_mod.utils.get_system_monitor",
        return_value=monitor,
    ):
        # 测试便捷函数
        record_http_request("GET", "/api", 200, 0.123)
        monitor.record_request.assert_called_once_with("GET", "/api", 200, 0.123)

        monitor.reset_mock()
        record_db_query("SELECT", "matches", 0.045)
        monitor.record_database_query.assert_called_once_with(
            "SELECT", "matches", 0.045
        )

        monitor.reset_mock()
        record_cache_operation("get", "redis", "hit")
        monitor.record_cache_operation.assert_called_once_with("get", "redis", "hit")

        monitor.reset_mock()
        record_prediction("v1.0", "EPL")
        monitor.record_prediction.assert_called_once_with("v1.0", "EPL")
