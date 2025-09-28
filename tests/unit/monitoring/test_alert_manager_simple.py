"""
Alert Manager增强测试（简化版）

只测试alert_manager.py模块中存在的方法
"""

from unittest.mock import Mock, patch, AsyncMock
import pytest
import asyncio
from datetime import datetime, timedelta
from enum import Enum

pytestmark = pytest.mark.unit


class TestAlertRule:
    """告警规则测试"""

    def test_alert_rule_import(self):
        """测试告警规则类导入"""
        from monitoring.alert_manager import AlertRule

        # 验证类可以导入
        assert AlertRule is not None

    def test_alert_rule_creation(self):
        """测试告警规则创建"""
        from monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel

        rule = AlertRule(
            rule_id="test_rule_id",
            name="test_rule",
            condition="cpu_usage > 80",
            level=AlertLevel.ERROR,
            channels=[AlertChannel.EMAIL],
            enabled=True
        )

        assert rule.rule_id == "test_rule_id"
        assert rule.name == "test_rule"
        assert rule.condition == "cpu_usage > 80"
        assert rule.level == AlertLevel.ERROR
        assert rule.channels == [AlertChannel.EMAIL]
        assert rule.enabled is True

    @pytest.mark.parametrize("condition,level_name,channel_name", [
        ("cpu_usage > 90", "ERROR", "EMAIL"),
        ("memory_usage < 10", "WARNING", "LOG"),
        ("disk_usage == 95", "INFO", "WEBHOOK"),
        ("network_traffic != 0", "CRITICAL", "PROMETHEUS"),
    ])
    def test_alert_rule_parameters(self, condition, level_name, channel_name):
        """测试告警规则参数"""
        from monitoring.alert_manager import AlertRule, AlertLevel, AlertChannel

        rule = AlertRule(
            rule_id=f"test_{level_name.lower()}",
            name=f"test_{level_name.lower()}",
            condition=condition,
            level=getattr(AlertLevel, level_name),
            channels=[getattr(AlertChannel, channel_name)],
            enabled=True
        )

        assert rule.condition == condition
        assert rule.level == getattr(AlertLevel, level_name)
        assert rule.channels == [getattr(AlertChannel, channel_name)]


class TestAlertManager:
    """告警管理器测试（简化版）"""

    def test_alert_manager_initialization(self):
        """测试告警管理器初始化"""
        from monitoring.alert_manager import AlertManager

        manager = AlertManager()

        # 验证基本属性存在
        assert hasattr(manager, 'rules')
        assert hasattr(manager, 'alerts')
        assert hasattr(manager, 'alert_handlers')
        assert hasattr(manager, 'metrics')

        # 验证规则是字典类型
        assert isinstance(manager.rules, dict)
        assert len(manager.rules) > 0  # 应该有默认规则

    def test_add_alert_rule(self):
        """测试添加告警规则"""
        from monitoring.alert_manager import AlertManager, AlertRule, AlertLevel, AlertChannel

        manager = AlertManager()
        initial_rule_count = len(manager.rules)

        rule = AlertRule(
            rule_id="memory_usage_rule",
            name="memory_usage",
            condition="memory_usage > 85",
            level=AlertLevel.ERROR,
            channels=[AlertChannel.EMAIL],
            enabled=True
        )

        manager.add_rule(rule)

        assert len(manager.rules) == initial_rule_count + 1
        assert manager.rules["memory_usage_rule"] == rule

    def test_remove_alert_rule(self):
        """测试移除告警规则"""
        from monitoring.alert_manager import AlertManager, AlertRule, AlertLevel, AlertChannel

        manager = AlertManager()
        initial_rule_count = len(manager.rules)

        rule = AlertRule(
            rule_id="disk_usage_rule",
            name="disk_usage",
            condition="disk_usage > 90",
            level=AlertLevel.CRITICAL,
            channels=[AlertChannel.EMAIL],
            enabled=True
        )

        manager.add_rule(rule)
        assert len(manager.rules) == initial_rule_count + 1

        manager.remove_rule("disk_usage_rule")
        assert len(manager.rules) == initial_rule_count

    def test_get_alert_rule(self):
        """测试获取告警规则"""
        from monitoring.alert_manager import AlertManager, AlertRule, AlertLevel, AlertChannel

        manager = AlertManager()
        rule = AlertRule(
            rule_id="network_traffic_rule",
            name="network_traffic",
            condition="network_traffic > 1000",
            level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG],
            enabled=True
        )

        manager.add_rule(rule)

        retrieved_rule = manager.rules.get("network_traffic_rule")
        assert retrieved_rule == rule

        non_existent_rule = manager.rules.get("non_existent")
        assert non_existent_rule is None

    def test_fire_alert(self):
        """测试触发告警"""
        from monitoring.alert_manager import AlertManager, AlertLevel

        manager = AlertManager()

        # 测试触发告警
        alert = manager.fire_alert(
            title="Test Alert",
            message="This is a test alert",
            level=AlertLevel.WARNING,
            source="test"
        )

        assert alert is not None
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.level == AlertLevel.WARNING
        assert alert.source == "test"

    def test_register_handler(self):
        """测试注册处理器"""
        from monitoring.alert_manager import AlertManager, AlertChannel

        manager = AlertManager()

        # 创建模拟处理器
        mock_handler = Mock()
        mock_handler.handle_alert = Mock()

        # 注册处理器（使用AlertChannel枚举）
        manager.register_handler(AlertChannel.LOG, mock_handler)

        assert AlertChannel.LOG in manager.alert_handlers
        assert mock_handler in manager.alert_handlers[AlertChannel.LOG]

    def test_resolve_alert(self):
        """测试解决告警"""
        from monitoring.alert_manager import AlertManager, AlertLevel

        manager = AlertManager()

        # 先触发一个告警
        alert = manager.fire_alert(
            title="Test Alert",
            message="This is a test alert",
            level=AlertLevel.WARNING,
            source="test"
        )

        # 解决告警
        result = manager.resolve_alert(alert.alert_id)

        assert result is True
        # 验证告警已被标记为已解决

    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        from monitoring.alert_manager import AlertManager, AlertLevel

        manager = AlertManager()

        # 触发多个告警
        alert1 = manager.fire_alert(
            title="Alert 1",
            message="First alert",
            level=AlertLevel.WARNING,
            source="test"
        )

        alert2 = manager.fire_alert(
            title="Alert 2",
            message="Second alert",
            level=AlertLevel.ERROR,
            source="test"
        )

        # 获取活跃告警
        active_alerts = manager.get_active_alerts()

        assert len(active_alerts) >= 2
        alert_ids = [alert.alert_id for alert in active_alerts]
        assert alert1.alert_id in alert_ids
        assert alert2.alert_id in alert_ids

    def test_get_alert_summary(self):
        """测试获取告警摘要"""
        from monitoring.alert_manager import AlertManager, AlertLevel

        manager = AlertManager()

        # 触发一些告警
        manager.fire_alert(
            title="Warning Alert",
            message="Warning level alert",
            level=AlertLevel.WARNING,
            source="test"
        )

        manager.fire_alert(
            title="Error Alert",
            message="Error level alert",
            level=AlertLevel.ERROR,
            source="test"
        )

        # 获取告警摘要
        summary = manager.get_alert_summary()

        assert isinstance(summary, dict)
        assert 'total_alerts' in summary
        assert 'by_level' in summary
        assert 'active_alerts' in summary
        assert summary['total_alerts'] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.monitoring.alert_manager", "--cov-report=term-missing"])