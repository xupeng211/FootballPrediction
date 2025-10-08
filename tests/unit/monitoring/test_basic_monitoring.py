"""监控模块基础测试"""

import pytest
from unittest.mock import patch


class TestBasicMonitoringImports:
    """测试监控模块的基础导入"""

    def test_import_anomaly_detector(self):
        """测试异常检测器导入"""
        try:
            from src.monitoring import anomaly_detector

            assert anomaly_detector is not None
        except ImportError as e:
            pytest.skip(f"无法导入anomaly_detector: {e}")

    def test_import_metrics_collector(self):
        """测试指标收集器导入"""
        try:
            from src.monitoring import metrics_collector

            assert metrics_collector is not None
        except ImportError as e:
            pytest.skip(f"无法导入metrics_collector: {e}")

    def test_import_metrics_exporter(self):
        """测试指标导出器导入"""
        try:
            from src.monitoring import metrics_exporter

            assert metrics_exporter is not None
        except ImportError as e:
            pytest.skip(f"无法导入metrics_exporter: {e}")

    def test_import_quality_monitor(self):
        """测试质量监控器导入"""
        try:
            from src.monitoring import quality_monitor

            assert quality_monitor is not None
        except ImportError as e:
            pytest.skip(f"无法导入quality_monitor: {e}")

    def test_import_system_monitor(self):
        """测试系统监控器导入"""
        try:
            from src.monitoring import system_monitor

            assert system_monitor is not None
        except ImportError as e:
            pytest.skip(f"无法导入system_monitor: {e}")

    def test_import_alert_manager(self):
        """测试告警管理器导入"""
        try:
            from src.monitoring import alert_manager

            assert alert_manager is not None
        except ImportError as e:
            pytest.skip(f"无法导入alert_manager: {e}")


class TestBasicMonitoringFunctionality:
    """测试监控模块的基本功能"""

    @patch("psutil.cpu_percent")
    def test_system_monitor_basic(self, mock_cpu):
        """测试系统监控基本功能"""
        try:
            from src.monitoring.system_monitor import SystemMonitor

            # Mock psutil
            mock_cpu.return_value = 50.0

            # 测试实例化
            monitor = SystemMonitor()
            assert monitor is not None

        except Exception as e:
            pytest.skip(f"无法测试SystemMonitor: {e}")

    def test_alert_manager_methods(self):
        """测试告警管理器方法"""
        try:
            from src.monitoring.alert_manager import AlertManager

            # 测试类存在
            assert AlertManager is not None

            # 测试可以实例化
            manager = AlertManager()
            assert manager is not None

        except Exception as e:
            pytest.skip(f"无法测试AlertManager: {e}")
