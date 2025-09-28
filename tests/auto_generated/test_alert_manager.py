"""
Auto-generated tests for src.monitoring.alert_manager module
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, ANY
from collections import defaultdict
from prometheus_client import CollectorRegistry

from src.monitoring.alert_manager import (
    AlertLevel,
    AlertStatus,
    AlertChannel,
    Alert,
    AlertRule,
    PrometheusMetrics,
    AlertManager
)


class TestAlertLevel:
    """测试告警级别枚举"""

    def test_alert_level_values(self):
        """测试告警级别值"""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"

    def test_alert_level_iterable(self):
        """测试告警级别可迭代"""
        levels = list(AlertLevel)
        assert len(levels) == 4
        assert AlertLevel.INFO in levels
        assert AlertLevel.WARNING in levels
        assert AlertLevel.ERROR in levels
        assert AlertLevel.CRITICAL in levels


class TestAlertStatus:
    """测试告警状态枚举"""

    def test_alert_status_values(self):
        """测试告警状态值"""
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.SILENCED.value == "silenced"

    def test_alert_status_iterable(self):
        """测试告警状态可迭代"""
        statuses = list(AlertStatus)
        assert len(statuses) == 3
        assert AlertStatus.ACTIVE in statuses
        assert AlertStatus.RESOLVED in statuses
        assert AlertStatus.SILENCED in statuses


class TestAlertChannel:
    """测试告警渠道枚举"""

    def test_alert_channel_values(self):
        """测试告警渠道值"""
        assert AlertChannel.LOG.value == "log"
        assert AlertChannel.PROMETHEUS.value == "prometheus"
        assert AlertChannel.WEBHOOK.value == "webhook"
        assert AlertChannel.EMAIL.value == "email"

    def test_alert_channel_iterable(self):
        """测试告警渠道可迭代"""
        channels = list(AlertChannel)
        assert len(channels) == 4
        assert AlertChannel.LOG in channels
        assert AlertChannel.PROMETHEUS in channels
        assert AlertChannel.WEBHOOK in channels
        assert AlertChannel.EMAIL in channels


class TestAlert:
    """测试告警对象"""

    def test_alert_creation_minimal(self):
        """测试最小告警创建"""
        alert = Alert(
            alert_id="test123",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test_source"
        )

        assert alert.alert_id == "test123"
        assert alert.title == "Test Alert"
        assert alert.message == "Test message"
        assert alert.level == AlertLevel.WARNING
        assert alert.source == "test_source"
        assert alert.labels == {}
        assert alert.annotations == {}
        assert alert.status == AlertStatus.ACTIVE
        assert alert.resolved_at is None
        assert isinstance(alert.created_at, datetime)

    def test_alert_creation_with_all_parameters(self):
        """测试带所有参数的告警创建"""
        labels = {"env": "test", "service": "api"}
        annotations = {"runbook_url": "https://example.com"}
        created_at = datetime(2023, 1, 1, 12, 0, 0)

        alert = Alert(
            alert_id="test123",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.CRITICAL,
            source="test_source",
            labels=labels,
            annotations=annotations,
            created_at=created_at
        )

        assert alert.labels == labels
        assert alert.annotations == annotations
        assert alert.created_at == created_at

    def test_alert_to_dict(self):
        """测试告警转字典"""
        created_at = datetime(2023, 1, 1, 12, 0, 0)

        alert = Alert(
            alert_id="test123",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.ERROR,
            source="test_source",
            labels={"key": "value"},
            annotations={"note": "test"},
            created_at=created_at
        )

        result = alert.to_dict()

        # 检查基本字段（不检查可能变化的 resolved_at）
        expected = {
            "alert_id": "test123",
            "title": "Test Alert",
            "message": "Test message",
            "level": "error",
            "source": "test_source",
            "labels": {"key": "value"},
            "annotations": {"note": "test"},
            "status": "active",  # 初始状态
            "created_at": created_at.isoformat(),
        }

        # 验证所有期望字段都存在且值正确
        for key, value in expected.items():
            assert result[key] == value, f"Field {key} mismatch: expected {value}, got {result[key]}"

        # 验证 resolved_at 字段存在且是有效的 ISO 格式时间戳
        assert "resolved_at" in result
        assert result["resolved_at"] is None  # 初始状态应该是 None

        # 测试解析后的状态
        alert.resolve()
        result_resolved = alert.to_dict()
        assert result_resolved["status"] == "resolved"
        assert result_resolved["resolved_at"] is not None
        assert isinstance(result_resolved["resolved_at"], str)  # 应该是 ISO 格式字符串

    def test_alert_resolve(self):
        """测试告警解决"""
        alert = Alert(
            alert_id="test123",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test_source"
        )

        assert alert.status == AlertStatus.ACTIVE
        assert alert.resolved_at is None

        alert.resolve()

        assert alert.status == AlertStatus.RESOLVED
        assert isinstance(alert.resolved_at, datetime)

    def test_alert_silence(self):
        """测试告警静默"""
        alert = Alert(
            alert_id="test123",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test_source"
        )

        alert.silence()

        assert alert.status == AlertStatus.SILENCED


class TestAlertRule:
    """测试告警规则"""

    def test_alert_rule_creation_minimal(self):
        """测试最小告警规则创建"""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            condition="error_count > 10",
            level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG]
        )

        assert rule.rule_id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.condition == "error_count > 10"
        assert rule.level == AlertLevel.WARNING
        assert rule.channels == [AlertChannel.LOG]
        assert rule.throttle_seconds == 300
        assert rule.enabled is True
        assert rule.last_fired is None

    def test_alert_rule_creation_with_all_parameters(self):
        """测试带所有参数的告警规则创建"""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            condition="error_count > 10",
            level=AlertLevel.CRITICAL,
            channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
            throttle_seconds=600,
            enabled=False
        )

        assert rule.throttle_seconds == 600
        assert rule.enabled is False

    @pytest.mark.parametrize("enabled", [True, False])
    def test_alert_rule_enabled_parameter(self, enabled):
        """测试告警规则启用参数"""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            condition="test",
            level=AlertLevel.INFO,
            channels=[AlertChannel.LOG],
            enabled=enabled
        )
        assert rule.enabled == enabled

    @pytest.mark.parametrize("throttle_seconds", [0, 60, 300, 3600])
    def test_alert_rule_throttle_seconds(self, throttle_seconds):
        """测试告警规则去重时间"""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            condition="test",
            level=AlertLevel.INFO,
            channels=[AlertChannel.LOG],
            throttle_seconds=throttle_seconds
        )
        assert rule.throttle_seconds == throttle_seconds


class TestPrometheusMetrics:
    """测试Prometheus指标"""

    def test_prometheus_metrics_creation_default_registry(self):
        """测试使用默认注册表创建Prometheus指标"""
        with patch('src.monitoring.alert_manager.REGISTRY') as mock_registry:
            metrics = PrometheusMetrics()
            assert metrics.registry == mock_registry

    def test_prometheus_metrics_creation_custom_registry(self):
        """测试使用自定义注册表创建Prometheus指标"""
        custom_registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=custom_registry)
        assert metrics.registry == custom_registry

    @patch('src.monitoring.alert_manager.Gauge')
    @patch('src.monitoring.alert_manager.Counter')
    @patch('src.monitoring.alert_manager.Histogram')
    def test_prometheus_metrics_initialization(self, mock_histogram, mock_counter, mock_gauge):
        """测试Prometheus指标初始化"""
        custom_registry = CollectorRegistry()

        # Mock the metric classes
        mock_gauge_instance = MagicMock()
        mock_counter_instance = MagicMock()
        mock_histogram_instance = MagicMock()
        mock_gauge.return_value = mock_gauge_instance
        mock_counter.return_value = mock_counter_instance
        mock_histogram.return_value = mock_histogram_instance

        metrics = PrometheusMetrics(registry=custom_registry)

        # Verify metrics were created with correct parameters
        assert mock_gauge.call_count == 5  # 5 Gauges
        assert mock_counter.call_count == 3  # 3 Counters
        assert mock_histogram.call_count == 1  # 1 Histogram

    def test_prometheus_metrics_attributes_exist(self):
        """测试Prometheus指标属性存在"""
        custom_registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry=custom_registry)

        # Check that all metric attributes exist
        assert hasattr(metrics, 'data_freshness_hours')
        assert hasattr(metrics, 'data_completeness_ratio')
        assert hasattr(metrics, 'data_quality_score')
        assert hasattr(metrics, 'anomalies_detected_total')
        assert hasattr(metrics, 'anomaly_score')
        assert hasattr(metrics, 'alerts_fired_total')
        assert hasattr(metrics, 'active_alerts')
        assert hasattr(metrics, 'monitoring_check_duration_seconds')
        assert hasattr(metrics, 'monitoring_errors_total')


class TestAlertManager:
    """测试告警管理器"""

    @patch('src.monitoring.alert_manager.logger')
    def test_alert_manager_creation(self, mock_logger):
        """测试告警管理器创建"""
        manager = AlertManager()

        assert isinstance(manager.alerts, list)
        assert isinstance(manager.rules, dict)
        assert isinstance(manager.alert_handlers, defaultdict)
        assert hasattr(manager, 'metrics')
        assert len(manager.rules) > 0  # Should have default rules
        mock_logger.info.assert_called()

    @patch('src.monitoring.alert_manager.logger')
    def test_alert_manager_default_rules(self, mock_logger):
        """测试告警管理器默认规则"""
        manager = AlertManager()

        # Check that default rules exist
        assert "data_freshness_critical" in manager.rules
        assert "data_freshness_warning" in manager.rules
        assert "data_completeness_critical" in manager.rules
        assert "data_completeness_warning" in manager.rules
        assert "data_quality_critical" in manager.rules
        assert "anomaly_critical" in manager.rules
        assert "anomaly_warning" in manager.rules

    @patch('src.monitoring.alert_manager.logger')
    def test_alert_manager_default_handlers(self, mock_logger):
        """测试告警管理器默认处理器"""
        manager = AlertManager()

        # Check that default handlers are registered
        assert AlertChannel.LOG in manager.alert_handlers
        assert AlertChannel.PROMETHEUS in manager.alert_handlers
        assert len(manager.alert_handlers[AlertChannel.LOG]) > 0
        assert len(manager.alert_handlers[AlertChannel.PROMETHEUS]) > 0

    @patch('src.monitoring.alert_manager.logger')
    def test_add_rule(self, mock_logger):
        """测试添加告警规则"""
        manager = AlertManager()
        initial_count = len(manager.rules)

        rule = AlertRule(
            rule_id="new_rule",
            name="New Rule",
            condition="test_condition",
            level=AlertLevel.INFO,
            channels=[AlertChannel.LOG]
        )

        manager.add_rule(rule)

        assert len(manager.rules) == initial_count + 1
        assert "new_rule" in manager.rules
        mock_logger.info.assert_called()

    @patch('src.monitoring.alert_manager.logger')
    def test_remove_rule(self, mock_logger):
        """测试移除告警规则"""
        manager = AlertManager()
        initial_count = len(manager.rules)

        # Remove existing rule
        result = manager.remove_rule("data_freshness_critical")

        assert result is True
        assert len(manager.rules) == initial_count - 1
        assert "data_freshness_critical" not in manager.rules
        mock_logger.info.assert_called()

    @patch('src.monitoring.alert_manager.logger')
    def test_remove_nonexistent_rule(self, mock_logger):
        """测试移除不存在的规则"""
        manager = AlertManager()
        initial_count = len(manager.rules)

        # Reset mock after initialization to focus on remove_rule behavior
        mock_logger.reset_mock()

        result = manager.remove_rule("nonexistent_rule")

        assert result is False
        assert len(manager.rules) == initial_count
        mock_logger.info.assert_not_called()

    @patch('src.monitoring.alert_manager.logger')
    @patch('src.monitoring.alert_manager.datetime')
    def test_fire_alert_basic(self, mock_datetime, mock_logger):
        """测试基本告警触发"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        manager = AlertManager()
        initial_alerts_count = len(manager.alerts)

        alert = manager.fire_alert(
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test_source"
        )

        assert alert is not None
        assert len(manager.alerts) == initial_alerts_count + 1
        assert alert.title == "Test Alert"
        assert alert.message == "Test message"
        assert alert.level == AlertLevel.WARNING
        assert alert.source == "test_source"
        mock_logger.info.assert_called()

    @patch('src.monitoring.alert_manager.logger')
    @patch('src.monitoring.alert_manager.datetime')
    def test_fire_alert_with_throttling(self, mock_datetime, mock_logger):
        """测试带去重的告警触发"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        manager = AlertManager()

        # First alert should fire
        alert1 = manager.fire_alert(
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test_source",
            rule_id="data_freshness_warning"  # Use existing rule with throttling
        )

        assert alert1 is not None
        assert len(manager.alerts) == 1

        # Second alert should be throttled
        alert2 = manager.fire_alert(
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test_source",
            rule_id="data_freshness_warning"
        )

        assert alert2 is None  # Should be throttled
        assert len(manager.alerts) == 1
        mock_logger.debug.assert_called()

    @patch('src.monitoring.alert_manager.logger')
    @patch('src.monitoring.alert_manager.datetime')
    def test_fire_alert_without_throttling(self, mock_datetime, mock_logger):
        """测试无去重的告警触发"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        manager = AlertManager()

        # Multiple alerts without rule_id should not be throttled
        alert1 = manager.fire_alert(
            title="Test Alert 1",
            message="Test message 1",
            level=AlertLevel.WARNING,
            source="test_source"
        )

        alert2 = manager.fire_alert(
            title="Test Alert 2",
            message="Test message 2",
            level=AlertLevel.WARNING,
            source="test_source"
        )

        assert alert1 is not None
        assert alert2 is not None
        assert len(manager.alerts) == 2

    @patch('src.monitoring.alert_manager.logger')
    def test_register_handler(self, mock_logger):
        """测试注册告警处理器"""
        manager = AlertManager()

        def dummy_handler(alert):
            pass

        initial_count = len(manager.alert_handlers[AlertChannel.EMAIL])

        manager.register_handler(AlertChannel.EMAIL, dummy_handler)

        assert len(manager.alert_handlers[AlertChannel.EMAIL]) == initial_count + 1
        assert dummy_handler in manager.alert_handlers[AlertChannel.EMAIL]
        mock_logger.info.assert_called()

    @patch('src.monitoring.alert_manager.logger')
    def test_resolve_alert(self, mock_logger):
        """测试解决告警"""
        manager = AlertManager()

        # Create an alert
        alert = manager.fire_alert(
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test_source"
        )

        assert alert is not None
        assert alert.status == AlertStatus.ACTIVE

        # Resolve the alert
        result = manager.resolve_alert(alert.alert_id)

        assert result is True
        assert alert.status == AlertStatus.RESOLVED
        mock_logger.info.assert_called()

    @patch('src.monitoring.alert_manager.logger')
    def test_resolve_nonexistent_alert(self, mock_logger):
        """测试解决不存在的告警"""
        manager = AlertManager()

        # Reset mock after initialization to focus on resolve_alert behavior
        mock_logger.reset_mock()

        result = manager.resolve_alert("nonexistent_id")

        assert result is False
        mock_logger.info.assert_not_called()

    @patch('src.monitoring.alert_manager.logger')
    def test_get_active_alerts(self, mock_logger):
        """测试获取活跃告警"""
        manager = AlertManager()

        # Create alerts
        alert1 = manager.fire_alert("Alert 1", "Message 1", AlertLevel.WARNING, "source1")
        alert2 = manager.fire_alert("Alert 2", "Message 2", AlertLevel.ERROR, "source2")

        # Resolve one alert
        manager.resolve_alert(alert1.alert_id)

        # Get active alerts
        active_alerts = manager.get_active_alerts()

        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == alert2.alert_id

    @patch('src.monitoring.alert_manager.logger')
    def test_get_active_alerts_with_level_filter(self, mock_logger):
        """测试带级别过滤的活跃告警"""
        manager = AlertManager()

        # Create alerts with different levels
        alert1 = manager.fire_alert("Warning Alert", "Message 1", AlertLevel.WARNING, "source1")
        alert2 = manager.fire_alert("Error Alert", "Message 2", AlertLevel.ERROR, "source2")

        # Get only ERROR level alerts
        error_alerts = manager.get_active_alerts(level=AlertLevel.ERROR)

        assert len(error_alerts) == 1
        assert error_alerts[0].alert_id == alert2.alert_id
        assert error_alerts[0].level == AlertLevel.ERROR

    @patch('src.monitoring.alert_manager.logger')
    @patch('src.monitoring.alert_manager.datetime')
    def test_get_alert_summary(self, mock_datetime, mock_logger):
        """测试获取告警摘要"""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        manager = AlertManager()

        # Create some alerts
        alert1 = manager.fire_alert("Alert 1", "Message 1", AlertLevel.WARNING, "source1")
        alert2 = manager.fire_alert("Alert 2", "Message 2", AlertLevel.ERROR, "source2")
        alert3 = manager.fire_alert("Alert 3", "Message 3", AlertLevel.WARNING, "source1")

        # Resolve one alert
        manager.resolve_alert(alert1.alert_id)

        summary = manager.get_alert_summary()

        assert summary["total_alerts"] == 3
        assert summary["active_alerts"] == 2
        assert summary["resolved_alerts"] == 1
        assert summary["by_level"]["warning"] == 1
        assert summary["by_level"]["error"] == 1
        assert summary["by_source"]["source1"] == 1
        assert summary["by_source"]["source2"] == 1
        assert summary["critical_alerts"] == 0
        assert summary["rules_count"] > 0
        assert summary["summary_time"] == fixed_time.isoformat()

    @patch('src.monitoring.alert_manager.logger')
    def test_update_quality_metrics(self, mock_logger):
        """测试更新数据质量指标"""
        manager = AlertManager()

        quality_data = {
            "freshness": {
                "table1": {"hours_since_last_update": 2.5},
                "table2": {"hours_since_last_update": 10.0}
            },
            "completeness": {
                "table1": {"completeness_ratio": 0.95},
                "table2": {"completeness_ratio": 0.87}
            },
            "overall_score": 0.91
        }

        # Mock the metrics
        manager.metrics.data_freshness_hours = MagicMock()
        manager.metrics.data_completeness_ratio = MagicMock()
        manager.metrics.data_quality_score = MagicMock()

        manager.update_quality_metrics(quality_data)

        # Verify metrics were called
        manager.metrics.data_freshness_hours.labels.assert_any_call(table_name="table1")
        manager.metrics.data_freshness_hours.labels.assert_any_call(table_name="table2")
        manager.metrics.data_completeness_ratio.labels.assert_any_call(table_name="table1")
        manager.metrics.data_completeness_ratio.labels.assert_any_call(table_name="table2")
        manager.metrics.data_quality_score.labels.assert_any_call(table_name="table1")
        manager.metrics.data_quality_score.labels.assert_any_call(table_name="table2")

    @patch('src.monitoring.alert_manager.logger')
    def test_check_and_fire_quality_alerts(self, mock_logger):
        """测试检查数据质量并触发告警"""
        manager = AlertManager()

        quality_data = {
            "freshness": {
                "stale_table": {"hours_since_last_update": 30.0},  # Should trigger critical
                "warning_table": {"hours_since_last_update": 15.0}  # Should trigger warning
            },
            "completeness": {
                "incomplete_table": {"completeness_ratio": 0.7},  # Should trigger critical
                "low_completeness_table": {"completeness_ratio": 0.9}  # Should trigger warning
            },
            "overall_score": 0.65  # Should trigger critical
        }

        alerts = manager.check_and_fire_quality_alerts(quality_data)

        # Should have fired multiple alerts
        assert len(alerts) > 0

        # Check that we have critical and warning alerts
        levels = [alert.level for alert in alerts]
        assert AlertLevel.CRITICAL in levels
        assert AlertLevel.WARNING in levels

    @patch('src.monitoring.alert_manager.logger')
    def test_check_and_fire_quality_alerts_no_issues(self, mock_logger):
        """测试无问题时的数据质量检查"""
        manager = AlertManager()

        quality_data = {
            "freshness": {
                "fresh_table": {"hours_since_last_update": 1.0}
            },
            "completeness": {
                "complete_table": {"completeness_ratio": 0.99}
            },
            "overall_score": 0.95
        }

        alerts = manager.check_and_fire_quality_alerts(quality_data)

        # Should not have fired any alerts
        assert len(alerts) == 0

    def test_generate_alert_id(self):
        """测试告警ID生成"""
        manager = AlertManager()

        # Test without labels
        id1 = manager._generate_alert_id("Test Title", "test_source", None)
        assert isinstance(id1, str)
        assert len(id1) == 12

        # Test with labels
        labels = {"env": "test", "service": "api"}
        id2 = manager._generate_alert_id("Test Title", "test_source", labels)
        assert isinstance(id2, str)
        assert len(id2) == 12
        assert id1 != id2  # Different labels should produce different IDs

        # Test same input produces same ID
        id3 = manager._generate_alert_id("Test Title", "test_source", labels)
        assert id2 == id3

    @patch('src.monitoring.alert_manager.datetime')
    def test_should_throttle(self, mock_datetime):
        """测试去重逻辑"""
        manager = AlertManager()

        fixed_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            condition="test",
            level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG],
            throttle_seconds=300  # 5 minutes
        )

        # No last_fired time, should not throttle
        assert not manager._should_throttle("test_alert", "test_rule")

        # Set last_fired to 4 minutes ago, should throttle
        rule.last_fired = fixed_time - timedelta(minutes=4)
        assert manager._should_throttle("test_alert", "test_rule")

        # Set last_fired to 6 minutes ago, should not throttle
        rule.last_fired = fixed_time - timedelta(minutes=6)
        assert not manager._should_throttle("test_alert", "test_rule")

        # Non-existent rule, should not throttle
        assert not manager._should_throttle("test_alert", "nonexistent_rule")

        # No rule_id, should not throttle
        assert not manager._should_throttle("test_alert", None)

    @patch('src.monitoring.alert_manager.logger')
    def test_log_handler(self, mock_logger):
        """测试日志处理器"""
        manager = AlertManager()

        alert = Alert(
            alert_id="test123",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.ERROR,
            source="test_source",
            labels={"env": "test"}
        )

        manager._log_handler(alert)

        # Check that logger was called with correct level and message
        mock_logger.log.assert_called_once()
        args, kwargs = mock_logger.log.call_args
        assert args[0] == 40  # ERROR level
        assert "[ALERT] Test Alert: Test message" in args[1]
        assert "ID: test123" in args[1]
        assert "Source: test_source" in args[1]

    @patch('src.monitoring.alert_manager.logger')
    def test_prometheus_handler(self, mock_logger):
        """测试Prometheus处理器"""
        manager = AlertManager()

        alert = Alert(
            alert_id="test123",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test_source"
        )

        # Should not raise any exceptions
        manager._prometheus_handler(alert)

        # Prometheus handler doesn't do much logging by default
        mock_logger.log.assert_not_called()

    @patch('src.monitoring.alert_manager.logger')
    def test_integration_workflow(self, mock_logger):
        """测试集成工作流"""
        manager = AlertManager()

        # 1. Add custom rule
        custom_rule = AlertRule(
            rule_id="custom_rule",
            name="Custom Rule",
            condition="custom_metric > 100",
            level=AlertLevel.CRITICAL,
            channels=[AlertChannel.LOG, AlertChannel.EMAIL],
            throttle_seconds=60
        )
        manager.add_rule(custom_rule)

        # 2. Register custom handler
        custom_handler_called = False
        def custom_handler(alert):
            nonlocal custom_handler_called
            custom_handler_called = True

        manager.register_handler(AlertChannel.EMAIL, custom_handler)

        # 3. Fire alert with custom rule
        alert = manager.fire_alert(
            title="Custom Alert",
            message="Custom message",
            level=AlertLevel.CRITICAL,
            source="custom_source",
            rule_id="custom_rule"
        )

        assert alert is not None
        assert alert.title == "Custom Alert"

        # 4. Check alert is in active alerts
        active_alerts = manager.get_active_alerts()
        assert alert in active_alerts

        # 5. Resolve alert
        manager.resolve_alert(alert.alert_id)

        # 6. Check alert is no longer active
        active_alerts_after = manager.get_active_alerts()
        assert alert not in active_alerts_after

        # 7. Get summary
        summary = manager.get_alert_summary()
        assert summary["total_alerts"] > 0
        assert summary["resolved_alerts"] > 0