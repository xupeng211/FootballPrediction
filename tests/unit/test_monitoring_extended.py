# 监控扩展测试
import pytest

from src.monitoring.metrics_collector import MetricsCollector
from src.monitoring.metrics_exporter import MetricsExporter
from src.monitoring.system_monitor import SystemMonitor


@pytest.mark.unit
@pytest.mark.monitoring
def test_metrics_collector_extended():
    collector = MetricsCollector()
    collector.record_metric("test_metric", 100)
    collector.record_metric("test_metric", 200)

    metrics = collector.get_metrics()
    assert "test_metric" in str(metrics)


def test_system_monitor():
    monitor = SystemMonitor()
    assert hasattr(monitor, "get_cpu_usage")
    assert hasattr(monitor, "get_memory_usage")


def test_metrics_exporter():
    exporter = MetricsExporter()
    assert exporter is not None
    assert hasattr(exporter, "export_metrics")
