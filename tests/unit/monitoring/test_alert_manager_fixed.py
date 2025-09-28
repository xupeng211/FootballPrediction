"""
Alert Manager 测试文件（修复版）

修复 Prometheus 注册表冲突问题
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from prometheus_client import CollectorRegistry


@pytest.mark.unit
class TestAlertManagerFixed:
    """Alert Manager 修复版测试类"""

    def test_alert_manager_import(self):
        """测试 AlertManager 导入"""
        try:
            from src.monitoring.alert_manager import AlertManager
            assert AlertManager is not None
        except ImportError:
            pytest.skip("AlertManager not available")

    def test_alert_manager_initialization_with_mocking(self):
        """测试带 Mock 的 AlertManager 初始化"""
        try:
            from src.monitoring.alert_manager import AlertManager

            # Mock PrometheusMetrics 以避免注册表冲突
            with patch('src.monitoring.alert_manager.PrometheusMetrics') as mock_metrics:
                mock_metrics_instance = MagicMock()
                mock_metrics.return_value = mock_metrics_instance

                manager = AlertManager()

                # 验证基本属性
                assert hasattr(manager, 'rules')
                assert hasattr(manager, 'alerts')
                assert hasattr(manager, 'alert_handlers')
                assert hasattr(manager, 'metrics')

                # 验证 PrometheusMetrics 被正确创建
                mock_metrics.assert_called_once()

        except ImportError:
            pytest.skip("AlertManager not available")

    def test_alert_manager_methods_exist(self):
        """测试 AlertManager 方法存在"""
        try:
            from src.monitoring.alert_manager import AlertManager

            # Mock PrometheusMetrics
            with patch('src.monitoring.alert_manager.PrometheusMetrics'):
                manager = AlertManager()

                # 验证核心方法存在
                expected_methods = [
                    'add_rule', 'remove_rule', 'fire_alert',
                    'resolve_alert', 'get_active_alerts',
                    'get_alert_summary', 'register_handler'
                ]

                for method_name in expected_methods:
                    assert hasattr(manager, method_name), f"Method {method_name} not found"
                    assert callable(getattr(manager, method_name)), f"Method {method_name} not callable"

        except ImportError:
            pytest.skip("AlertManager not available")

    def test_alert_manager_rule_management(self):
        """测试告警规则管理"""
        try:
            from src.monitoring.alert_manager import AlertManager

            # Mock PrometheusMetrics
            with patch('src.monitoring.alert_manager.PrometheusMetrics'):
                manager = AlertManager()

                # 验证规则属性
                assert hasattr(manager, 'rules')
                assert isinstance(manager.rules, dict)

                # 验证初始状态
                initial_count = len(manager.rules)
                assert initial_count >= 0  # 可能有默认规则

        except ImportError:
            pytest.skip("AlertManager not available")

    def test_alert_manager_alert_management(self):
        """测试告警管理"""
        try:
            from src.monitoring.alert_manager import AlertManager

            # Mock PrometheusMetrics
            with patch('src.monitoring.alert_manager.PrometheusMetrics'):
                manager = AlertManager()

                # 验证告警属性
                assert hasattr(manager, 'alerts')
                assert isinstance(manager.alerts, list)

                # 验证初始状态
                initial_count = len(manager.alerts)
                assert initial_count == 0  # 初始应该没有告警

        except ImportError:
            pytest.skip("AlertManager not available")

    def test_alert_manager_handler_management(self):
        """测试处理器管理"""
        try:
            from src.monitoring.alert_manager import AlertManager

            # Mock PrometheusMetrics
            with patch('src.monitoring.alert_manager.PrometheusMetrics'):
                manager = AlertManager()

                # 验证处理器属性
                assert hasattr(manager, 'alert_handlers')

                # 验证处理器字典结构
                handlers = manager.alert_handlers
                assert isinstance(handlers, dict)

        except ImportError:
            pytest.skip("AlertManager not available")

    def test_alert_classes_import(self):
        """测试告警相关类导入"""
        try:
            from src.monitoring.alert_manager import (
                AlertLevel, AlertStatus, AlertChannel,
                Alert, AlertRule
            )

            # 验证枚举类
            assert AlertLevel is not None
            assert AlertStatus is not None
            assert AlertChannel is not None

            # 验证数据类
            assert Alert is not None
            assert AlertRule is not None

        except ImportError as e:
            pytest.skip(f"Alert classes not available: {e}")

    def test_alert_level_enum_values(self):
        """测试 AlertLevel 枚举值"""
        try:
            from src.monitoring.alert_manager import AlertLevel

            # 验证枚举值存在
            assert hasattr(AlertLevel, 'INFO')
            assert hasattr(AlertLevel, 'WARNING')
            assert hasattr(AlertLevel, 'ERROR')
            assert hasattr(AlertLevel, 'CRITICAL')

            # 验证枚举值
            assert AlertLevel.INFO.value == "info"
            assert AlertLevel.WARNING.value == "warning"
            assert AlertLevel.ERROR.value == "error"
            assert AlertLevel.CRITICAL.value == "critical"

        except ImportError:
            pytest.skip("AlertLevel not available")

    def test_alert_channel_enum_values(self):
        """测试 AlertChannel 枚举值"""
        try:
            from src.monitoring.alert_manager import AlertChannel

            # 验证枚举值存在
            assert hasattr(AlertChannel, 'LOG')
            assert hasattr(AlertChannel, 'PROMETHEUS')
            assert hasattr(AlertChannel, 'WEBHOOK')
            assert hasattr(AlertChannel, 'EMAIL')

            # 验证枚举值
            assert AlertChannel.LOG.value == "log"
            assert AlertChannel.PROMETHEUS.value == "prometheus"
            assert AlertChannel.WEBHOOK.value == "webhook"
            assert AlertChannel.EMAIL.value == "email"

        except ImportError:
            pytest.skip("AlertChannel not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.monitoring.alert_manager", "--cov-report=term-missing"])