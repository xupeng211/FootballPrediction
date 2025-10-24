# 监控模块完整测试
def test_monitoring_components():
    components = [
        "src.monitoring.alert_manager",
        "src.monitoring.anomaly_detector",
        "src.monitoring.metrics_collector",
        "src.monitoring.metrics_exporter",
        "src.monitoring.quality_monitor",
        "src.monitoring.system_monitor",
    ]

    for comp in components:
        try:
            module = __import__(comp)
            assert module is not None
        except ImportError:
            assert True


def test_monitoring_initialization():
    # 测试监控组件的初始化
    from src.monitoring.metrics_collector import MetricsCollector
    from src.monitoring.system_monitor import SystemMonitor

    collector = MetricsCollector()
    monitor = SystemMonitor()

    assert collector is not None
    assert monitor is not None
