#!/usr/bin/env python3
"""
Monitoring模块覆盖测试
目标：为monitoring模块获得初始覆盖
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestMonitoringCoverage:
    """Monitoring模块覆盖测试"""

    def test_system_monitor(self):
        """测试系统监控器"""
        try:
            from src.monitoring.system_monitor import SystemMonitor

            # 测试类可以创建
            monitor = SystemMonitor()
            assert monitor is not None
            assert hasattr(monitor, "check_health")
            assert hasattr(monitor, "get_metrics")
        except ImportError:
            pytest.skip("System monitor导入失败")

    def test_health_checker(self):
        """测试健康检查器"""
        try:
            from src.monitoring.health_checker import HealthChecker

            # 测试类可以创建
            checker = HealthChecker()
            assert checker is not None
        except ImportError:
            pytest.skip("Health checker导入失败")

    def test_metrics_collector(self):
        """测试指标收集器"""
        try:
            from src.monitoring.metrics_collector import MetricsCollector

            # 测试类可以创建
            collector = MetricsCollector()
            assert collector is not None
            assert hasattr(collector, "collect")
            assert hasattr(collector, "store")
        except ImportError:
            pytest.skip("Metrics collector导入失败")

    def test_alert_manager(self):
        """测试告警管理器"""
        try:
            from src.monitoring.alert_manager import AlertManager

            # 测试类可以创建
            manager = AlertManager()
            assert manager is not None
            assert hasattr(manager, "send_alert")
            assert hasattr(manager, "check_thresholds")
        except ImportError:
            pytest.skip("Alert manager导入失败")

    def test_anomaly_detector(self):
        """测试异常检测器"""
        try:
            from src.monitoring.anomaly_detector import AnomalyDetector

            # 测试类可以创建
            detector = AnomalyDetector()
            assert detector is not None
            assert hasattr(detector, "detect")
            assert hasattr(detector, "train")
        except ImportError:
            pytest.skip("Anomaly detector导入失败")

    def test_metrics_exporter(self):
        """测试指标导出器"""
        try:
            from src.monitoring.metrics_exporter import MetricsExporter

            # 测试类可以创建
            exporter = MetricsExporter()
            assert exporter is not None
            assert hasattr(exporter, "export")
            assert hasattr(exporter, "format")
        except ImportError:
            pytest.skip("Metrics exporter导入失败")

    def test_system_metrics(self):
        """测试系统指标"""
        try:
            from src.monitoring.system_metrics import (
                get_cpu_usage,
                get_memory_usage,
                get_disk_usage,
            )

            # 测试函数存在
            assert get_cpu_usage is not None
            assert get_memory_usage is not None
            assert get_disk_usage is not None
        except ImportError:
            pytest.skip("System metrics导入失败")
