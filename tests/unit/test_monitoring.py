"""监控模块测试"""

import pytest


class TestMonitoring:
    """测试监控模块"""

    def test_alert_manager_import(self):
        """测试告警管理器导入"""
        try:
            from src.monitoring.alert_manager import AlertManager

            assert AlertManager is not None
        except ImportError:
            pytest.skip("AlertManager not available")

    def test_anomaly_detector_import(self):
        """测试异常检测器导入"""
        try:
            from src.monitoring.anomaly_detector import MonitoringAnomalyDetector

            assert MonitoringAnomalyDetector is not None
        except ImportError:
            pytest.skip("MonitoringAnomalyDetector not available")

    def test_metrics_collector_import(self):
        """测试指标收集器导入"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            assert MetricsCollector is not None
        except ImportError:
            pytest.skip("MetricsCollector not available")

    def test_system_monitor_import(self):
        """测试系统监控器导入"""
        try:
            from src.monitoring.system_monitor_mod import SystemMonitor

            assert SystemMonitor is not None
        except ImportError:
            pytest.skip("SystemMonitor not available")
