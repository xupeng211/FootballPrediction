from datetime import datetime, timedelta

from src.monitoring.alert_manager import (
from unittest.mock import MagicMock, patch, call

#!/usr/bin/env python3
"""
Unit tests for alert manager module.:

Tests for src/monitoring/alert_manager.py module classes and functions.
"""
    AlertLevel,
    AlertStatus,
    AlertChannel,
    Alert,
    AlertRule,
    PrometheusMetrics,
    AlertManager)
class TestAlertLevel:
    """Test cases for AlertLevel enum."""
    def test_alert_level_values(self):
        """Test AlertLevel enum values."""
        assert AlertLevel.INFO.value =="info[" assert AlertLevel.WARNING.value =="]warning[" assert AlertLevel.ERROR.value =="]error[" assert AlertLevel.CRITICAL.value =="]critical[" class TestAlertStatus:""""
    "]""Test cases for AlertStatus enum."""
    def test_alert_status_values(self):
        """Test AlertStatus enum values."""
        assert AlertStatus.ACTIVE.value =="active[" assert AlertStatus.RESOLVED.value =="]resolved[" assert AlertStatus.SILENCED.value =="]silenced[" class TestAlertChannel:""""
    "]""Test cases for AlertChannel enum."""
    def test_alert_channel_values(self):
        """Test AlertChannel enum values."""
        assert AlertChannel.LOG.value =="log[" assert AlertChannel.PROMETHEUS.value =="]prometheus[" assert AlertChannel.WEBHOOK.value =="]webhook[" assert AlertChannel.EMAIL.value =="]email[" class TestAlert:""""
    "]""Test cases for Alert class."""
    def test_alert_creation_minimal(self):
        """Test Alert creation with minimal parameters."""
        alert = Alert(
            alert_id="test-123[",": title="]Test Alert[",": message="]This is a test alert[",": level=AlertLevel.WARNING,": source="]test[")": assert alert.alert_id =="]test-123[" assert alert.title =="]Test Alert[" assert alert.message =="]This is a test alert[" assert alert.level ==AlertLevel.WARNING[""""
        assert alert.source =="]]test[" assert alert.labels =={}""""
        assert alert.annotations =={}
        assert alert.status ==AlertStatus.ACTIVE
        assert alert.resolved_at is None
        assert isinstance(alert.created_at, datetime)
    def test_alert_creation_with_all_parameters(self):
        "]""Test Alert creation with all parameters."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        labels = {"env[: "test"", "service[" "]api]}": annotations = {"runbook_url[: "https//example.com/runbook["}"]": alert = Alert(": alert_id="]test-456[",": title="]Complete Alert[",": message = "]Complete alert with all params[",": level=AlertLevel.CRITICAL,": source="]monitoring[",": labels=labels,": annotations=annotations,": created_at=custom_time)"
        assert alert.alert_id =="]test-456[" assert alert.labels ==labels[""""
        assert alert.annotations ==annotations
        assert alert.created_at ==custom_time
    def test_alert_to_dict(self):
        "]]""Test Alert to_dict conversion."""
        alert = Alert(alert_id="test-789[",": title="]Dict Test[",": message="]Test dictionary conversion[",": level=AlertLevel.ERROR,": source="]unittest[",": labels = {"]key[": ["]value["))": result = alert.to_dict()": expected = {""
            "]alert_id[: "test-789[","]"""
            "]title[: "Dict Test[","]"""
            "]message[: "Test dictionary conversion[","]"""
            "]level[": ["]error[",""""
            "]source[": ["]unittest[",""""
            "]labels[": {"]key[": "]value["},""""
            "]annotations[": {},""""
            "]status[": ["]active[",""""
            "]created_at[": alert.created_at.isoformat()": assert result ==expected[" def test_alert_resolve(self):""
        "]]""Test alert resolution."""
        alert = Alert(
            alert_id="test-resolve[",": title="]Resolve Test[",": message="]Test resolution[",": level=AlertLevel.INFO,": source="]test[")": initial_time = alert.created_at[": alert.resolve()": assert alert.status ==AlertStatus.RESOLVED"
        assert alert.resolved_at is not None
        assert alert.resolved_at > initial_time
    def test_alert_silence(self):
        "]]""Test alert silencing."""
        alert = Alert(
            alert_id="test-silence[",": title="]Silence Test[",": message="]Test silencing[",": level=AlertLevel.INFO,": source="]test[")": alert.silence()": assert alert.status ==AlertStatus.SILENCED[" class TestAlertRule:"
    "]]""Test cases for AlertRule class."""
    def test_alert_rule_creation(self):
        """Test AlertRule creation."""
        rule = AlertRule(
            rule_id="rule-123[",": name="]Test Rule[",": condition="]error_rate > 0.1[",": level=AlertLevel.WARNING,": channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],": throttle_seconds=600,"
            enabled=True)
        assert rule.rule_id =="]rule-123[" assert rule.name =="]Test Rule[" assert rule.condition =="]error_rate > 0.1[" assert rule.level ==AlertLevel.WARNING[""""
        assert AlertChannel.LOG in rule.channels
        assert AlertChannel.PROMETHEUS in rule.channels
        assert rule.throttle_seconds ==600
        assert rule.enabled is True
        assert rule.last_fired is None
    def test_alert_rule_defaults(self):
        "]]""Test AlertRule default parameters."""
        rule = AlertRule(
            rule_id="rule-default[",": name="]Default Rule[",": condition="]cpu_usage > 80[",": level=AlertLevel.ERROR,": channels=[AlertChannel.LOG])": assert rule.throttle_seconds ==300  # Default value"
        assert rule.enabled is True  # Default value
class TestPrometheusMetrics:
    "]""Test cases for PrometheusMetrics class."""
    def test_prometheus_metrics_creation_with_default_registry(self):
        """Test PrometheusMetrics creation with default registry."""
        metrics = PrometheusMetrics()
        assert metrics.registry is not None
    def test_prometheus_metrics_creation_with_custom_registry(self):
        """Test PrometheusMetrics creation with custom registry."""
        custom_registry = MagicMock()
        metrics = PrometheusMetrics(registry=custom_registry)
        assert metrics.registry ==custom_registry
    def test_all_metrics_are_initialized(self):
        """Test that all Prometheus metrics are properly initialized."""
        metrics = PrometheusMetrics()
        # Check that all expected metrics exist
        assert hasattr(metrics, "data_freshness_hours[")" assert hasattr(metrics, "]data_completeness_ratio[")" assert hasattr(metrics, "]data_quality_score[")" assert hasattr(metrics, "]anomalies_detected_total[")" assert hasattr(metrics, "]anomaly_score[")" assert hasattr(metrics, "]alerts_fired_total[")" assert hasattr(metrics, "]active_alerts[")" assert hasattr(metrics, "]monitoring_check_duration_seconds[")" assert hasattr(metrics, "]monitoring_errors_total[")""""
    @patch("]src.monitoring.alert_manager.REGISTRY[")": def test_metrics_use_custom_registry(self, mock_registry):"""
        "]""Test that metrics use the provided custom registry."""
        custom_registry = MagicMock()
        PrometheusMetrics(registry=custom_registry)
        # Verify that metrics were created with custom registry:
        custom_registry.register.assert_called()
class TestAlertManager:
    """Test cases for AlertManager class."""
    @patch("src.monitoring.alert_manager.logger[")": def test_alert_manager_initialization(self, mock_logger):"""
        "]""Test AlertManager initialization."""
        manager = AlertManager()
        assert isinstance(manager.alerts, list)
        assert isinstance(manager.rules, dict)
        assert len(manager.alerts) ==0
        assert len(manager.rules) > 0  # Should have default rules
        assert manager.metrics is not None
        mock_logger.info.assert_called_with("告警管理器初始化完成[")""""
    @patch("]src.monitoring.alert_manager.logger[")": def test_alert_manager_initializes_default_rules(self, mock_logger):"""
        "]""Test that AlertManager initializes default rules."""
        manager = AlertManager()
        # Check that default rules are present
        assert "data_freshness_critical[" in manager.rules[""""
        assert "]]data_freshness_warning[" in manager.rules[""""
        assert "]]data_completeness_critical[" in manager.rules[""""
        assert "]]data_completeness_warning[" in manager.rules[""""
        assert "]]data_quality_critical[" in manager.rules[""""
        assert "]]anomaly_critical[" in manager.rules[""""
        assert "]]anomaly_warning[" in manager.rules[""""
    @patch("]]src.monitoring.alert_manager.logger[")": def test_register_handler(self, mock_logger):"""
        "]""Test handler registration."""
        manager = AlertManager()
        handler = MagicMock()
        manager.register_handler(AlertChannel.LOG, handler)
        assert handler in manager.alert_handlers[AlertChannel.LOG]
        mock_logger.info.assert_called_with("注册告警处理器[": ["]log[")": def test_add_rule(self):"""
        "]""Test adding alert rule."""
        manager = AlertManager()
        new_rule = AlertRule(
            rule_id="custom_rule[",": name="]Custom Rule[",": condition="]custom_condition[",": level=AlertLevel.INFO,": channels=[AlertChannel.LOG])": manager.add_rule(new_rule)"
        assert "]custom_rule[" in manager.rules[""""
        assert manager.rules["]]custom_rule["] ==new_rule[" def test_remove_rule_success(self):"""
        "]]""Test successful rule removal."""
        manager = AlertManager()
        assert "data_freshness_critical[" in manager.rules[""""
        result = manager.remove_rule("]]data_freshness_critical[")": assert result is True[" assert "]]data_freshness_critical[" not in manager.rules[""""
    def test_remove_rule_not_found(self):
        "]]""Test rule removal when rule doesn't exist."""
        manager = AlertManager()
        result = manager.remove_rule("nonexistent_rule[")": assert result is False["""
    @patch("]]src.monitoring.alert_manager.logger[")": def test_fire_alert_success(self, mock_logger):"""
        "]""Test successful alert firing."""
        manager = AlertManager()
        alert = manager.fire_alert(title="Test Alert[",": message="]This is a test[",": level=AlertLevel.WARNING,": source="]test[",": labels = {"]env[": ["]test["))": assert alert is not None[" assert alert.title =="]]Test Alert[" assert alert in manager.alerts[""""
        mock_logger.info.assert_called_with("]]触发告警: Test Alert ["warning"")""""
    @patch("src.monitoring.alert_manager.logger[")": def test_fire_alert_throttled(self, mock_logger):"""
        "]""Test alert throttling."""
        manager = AlertManager()
        # First alert should fire
        alert1 = manager.fire_alert(
            title="Throttle Test[",": message="]First alert[",": level=AlertLevel.INFO,": source="]test[",": rule_id="]data_freshness_critical[")": assert alert1 is not None["""
        # Second identical alert should be throttled
        alert2 = manager.fire_alert(
            title="]]Throttle Test[",": message="]Second alert[",": level=AlertLevel.INFO,": source="]test[",": rule_id="]data_freshness_critical[")": assert alert2 is None[" mock_logger.debug.assert_called_once()""
        # Check that the debug call contains the throttling message
        call_args = mock_logger.debug.call_args[0][0]
        assert "]]告警被去重[" in call_args[""""
    @patch("]]src.monitoring.alert_manager.logger[")": def test_fire_alert_no_throttle_without_rule(self, mock_logger):"""
        "]""Test alert firing without throttling when no rule specified."""
        manager = AlertManager()
        # Multiple alerts without rule should all fire
        alert1 = manager.fire_alert(
            title="No Throttle Test[",": message="]First alert[",": level=AlertLevel.INFO,": source="]test[")": alert2 = manager.fire_alert(": title="]No Throttle Test[",": message="]Second alert[",": level=AlertLevel.INFO,": source="]test[")": assert alert1 is not None[" assert alert2 is not None[""
        assert len(manager.alerts) ==2
    def test_generate_alert_id(self):
        "]]]""Test alert ID generation."""
        manager = AlertManager()
        # Test without labels
        id1 = manager._generate_alert_id("Test Alert[", "]test[", None)": assert len(id1) ==12["""
        # Test with labels = labels {"]]env[: "test"", "service]}": id2 = manager._generate_alert_id("Test Alert[", "]test[", labels)": assert len(id2) ==12[" assert id1 != id2  # Should be different due to labels[""
        # Test consistent input produces consistent ID
        id3 = manager._generate_alert_id("]]]Test Alert[", "]test[", labels)": assert id2 ==id3[" def test_should_throttle_no_rule(self):""
        "]]""Test throttling logic when no rule is specified."""
        manager = AlertManager()
        result = manager._should_throttle("test-alert[", None)": assert result is False[" def test_should_throttle_nonexistent_rule(self):""
        "]]""Test throttling logic for nonexistent rule."""
        manager = AlertManager()
        result = manager._should_throttle("test-alert[", "]nonexistent_rule[")": assert result is False[" def test_should_throttle_never_fired(self):""
        "]]""Test throttling logic for rule that has never fired."""
        manager = AlertManager()
        rule = manager.rules["data_freshness_critical["]"]": assert rule.last_fired is None[" result = manager._should_throttle("]test-alert[", "]data_freshness_critical[")": assert result is False[" def test_should_throttle_within_window(self):""
        "]]""Test throttling logic within throttle window."""
        manager = AlertManager()
        rule = manager.rules["data_freshness_critical["]"]": rule.last_fired = datetime.now() - timedelta(minutes=10)  # 10 minutes ago[": result = manager._should_throttle("]test-alert[", "]data_freshness_critical[")": assert result is True  # Should be throttled (1800 second window)" def test_should_throttle_outside_window(self):""
        "]""Test throttling logic outside throttle window."""
        manager = AlertManager()
        rule = manager.rules["data_freshness_warning["]"]": rule.last_fired = datetime.now() - timedelta(minutes=61)  # 61 minutes ago[": result = manager._should_throttle("]test-alert[", "]data_freshness_warning[")": assert result is False  # Should not be throttled (3600 second window)"""
    @patch("]src.monitoring.alert_manager.logger[")": def test_send_alert_with_rule_channels(self, mock_logger):"""
        "]""Test sending alert with rule-defined channels."""
        manager = AlertManager()
        mock_handler = MagicMock()
        manager.register_handler(AlertChannel.LOG, mock_handler)
        alert = Alert(
            alert_id="test-send[",": title="]Send Test[",": message="]Test sending[",": level=AlertLevel.INFO,": source="]test[")": manager._send_alert(alert, "]data_freshness_critical[")  # Has LOG and PROMETHEUS[": mock_handler.assert_called_once_with(alert)"""
    @patch("]]src.monitoring.alert_manager.logger[")": def test_send_alert_without_rule(self, mock_logger):"""
        "]""Test sending alert without rule."""
        manager = AlertManager()
        mock_handler = MagicMock()
        manager.register_handler(AlertChannel.LOG, mock_handler)
        alert = Alert(
            alert_id="test-send-no-rule[",": title="]Send Test No Rule[",": message="]Test sending without rule[",": level=AlertLevel.INFO,": source="]test[")": manager._send_alert(alert, None)  # No rule specified[": mock_handler.assert_called_once_with(alert)""
    @patch("]]src.monitoring.alert_manager.logger[")": def test_send_alert_handler_error(self, mock_logger):"""
        "]""Test handling of alert handler errors."""
        manager = AlertManager()
        def error_handler(alert):
            raise Exception("Handler error[")": manager.register_handler(AlertChannel.LOG, error_handler)": alert = Alert(": alert_id="]test-error[",": title="]Error Test[",": message="]Test error handling[",": level=AlertLevel.INFO,": source="]test[")""""
        # Should not raise exception
        manager._send_alert(alert, "]data_freshness_critical[")""""
        # Should log error and increment error counter
        mock_logger.error.assert_called()
        # The main purpose is to test that errors are handled gracefully
        # Metrics testing is secondary and may vary based on Prometheus implementation
    def test_update_alert_metrics(self):
        "]""Test updating alert metrics."""
        manager = AlertManager()
        alert = Alert(
            alert_id="test-metrics[",": title="]Metrics Test[",": message="]Test metrics update[",": level=AlertLevel.WARNING,": source="]test[")": manager._update_alert_metrics(alert, "]test_rule[")""""
        # Verify metrics were updated
        manager.metrics.alerts_fired_total.labels.assert_called_with(
            level="]warning[", source="]test[", rule_id="]test_rule["""""
        )
        manager.metrics.alerts_fired_total.labels.return_value.inc.assert_called()
        manager.metrics.active_alerts.labels.assert_called_with(level="]warning[")": def test_log_handler_info_level(self):"""
        "]""Test log handler for INFO level alerts."""
        manager = AlertManager()
        with patch("src.monitoring.alert_manager.logger[") as mock_logger:": alert = Alert(alert_id="]test-log-info[",": title="]Log Info Test[",": message="]Test info logging[",": level=AlertLevel.INFO,": source="]test[",": labels = {"]env[": ["]test["))": manager._log_handler(alert)": mock_logger.log.assert_called_with(": logging.INFO,"
                "]": [["ALERT[": Log Info Test])": def test_log_handler_critical_level(self):"""
        "]""Test log handler for CRITICAL level alerts."""
        manager = AlertManager()
        with patch("src.monitoring.alert_manager.logger[") as mock_logger:": alert = Alert(": alert_id="]test-log-critical[",": title="]Log Critical Test[",": message="]Test critical logging[",": level=AlertLevel.CRITICAL,": source="]test[")": manager._log_handler(alert)": mock_logger.log.assert_called_with(": logging.CRITICAL,"
                "]": [["ALERT[": Log Critical Test])": def test_prometheus_handler(self):"""
        "]""Test Prometheus handler."""
        manager = AlertManager()
        alert = Alert(
            alert_id="test-prometheus[",": title="]Prometheus Test[",": message="]Test Prometheus handler[",": level=AlertLevel.WARNING,": source="]test[")""""
        # Should not raise exception
        manager._prometheus_handler(alert)
    def test_resolve_alert_success(self):
        "]""Test successful alert resolution."""
        manager = AlertManager()
        alert = Alert(
            alert_id="test-resolve-alert[",": title="]Resolve Alert Test[",": message="]Test alert resolution[",": level=AlertLevel.INFO,": source="]test[")": manager.alerts.append(alert)": result = manager.resolve_alert("]test-resolve-alert[")": assert result is True[" assert alert.status ==AlertStatus.RESOLVED[""
        assert alert.resolved_at is not None
    def test_resolve_alert_not_found(self):
        "]]]""Test alert resolution when alert not found."""
        manager = AlertManager()
        result = manager.resolve_alert("nonexistent-alert[")": assert result is False[" def test_resolve_alert_already_resolved(self):""
        "]]""Test alert resolution when alert is already resolved."""
        manager = AlertManager()
        alert = Alert(
            alert_id="test-already-resolved[",": title="]Already Resolved[",": message="]Test already resolved alert[",": level=AlertLevel.INFO,": source="]test[")": alert.resolve()": manager.alerts.append(alert)": result = manager.resolve_alert("]test-already-resolved[")": assert result is False  # Should not resolve already resolved alert[" def test_get_active_alerts_all(self):""
        "]]""Test getting all active alerts."""
        manager = AlertManager()
        # Create test alerts
        active_alert1 = Alert("id1[", "]Active 1[", "]msg1[", AlertLevel.INFO, "]test[")": active_alert2 = Alert("]id2[", "]Active 2[", "]msg2[", AlertLevel.WARNING, "]test[")": resolved_alert = Alert("]id3[", "]Resolved[", "]msg3[", AlertLevel.INFO, "]test[")": resolved_alert.resolve()": manager.alerts = ["]active_alert1[", active_alert2, resolved_alert]": active_alerts = manager.get_active_alerts()": assert len(active_alerts) ==2[" assert active_alert1 in active_alerts"
        assert active_alert2 in active_alerts
        assert resolved_alert not in active_alerts
    def test_get_active_alerts_filtered_by_level(self):
        "]]""Test getting active alerts filtered by level."""
        manager = AlertManager()
        active_info = Alert("id1[", "]Info[", "]msg1[", AlertLevel.INFO, "]test[")": active_warning = Alert("]id2[", "]Warning[", "]msg2[", AlertLevel.WARNING, "]test[")": active_critical = Alert("]id3[", "]Critical[", "]msg3[", AlertLevel.CRITICAL, "]test[")": manager.alerts = ["]active_info[", active_warning, active_critical]": warning_alerts = manager.get_active_alerts(level=AlertLevel.WARNING)": assert len(warning_alerts) ==1[" assert warning_alerts[0] ==active_warning"
    def test_get_alert_summary(self):
        "]]""Test getting alert summary."""
        manager = AlertManager()
        # Create test alerts
        active_critical = Alert(
            "id1[", "]Critical[", "]msg1[", AlertLevel.CRITICAL, "]source1["""""
        )
        active_warning = Alert("]id2[", "]Warning[", "]msg2[", AlertLevel.WARNING, "]source2[")": resolved_alert = Alert("]id3[", "]Resolved[", "]msg3[", AlertLevel.INFO, "]source1[")": resolved_alert.resolve()": manager.alerts = ["]active_critical[", active_warning, resolved_alert]": summary = manager.get_alert_summary()": assert summary["]total_alerts["] ==3[" assert summary["]]active_alerts["] ==2[" assert summary["]]resolved_alerts["] ==1[" assert summary["]]by_level["]"]critical[" ==1[" assert summary["]]by_level["]"]warning[" ==1[" assert summary["]]by_source["]"]source1[" ==1[" assert summary["]]by_source["]"]source2[" ==1[" assert summary["]]critical_alerts["] ==1[" assert "]]summary_time[" in summary[""""
    def test_get_alert_summary_empty(self):
        "]]""Test getting alert summary with no alerts."""
        manager = AlertManager()
        manager.alerts = []
        summary = manager.get_alert_summary()
        assert summary["total_alerts["] ==0["]"]" assert summary["active_alerts["] ==0["]"]" assert summary["resolved_alerts["] ==0["]"]" assert summary["by_level["] =={}"]" assert summary["by_source["] =={}"]" assert summary["critical_alerts["] ==0["]"]" assert "summary_time[" in summary[""""
    def test_update_quality_metrics_freshness(self):
        "]]""Test updating data quality metrics for freshness."""
        manager = AlertManager()
        quality_data = {
            "freshness[": {""""
                "]matches[": {"]hours_since_last_update[": 5.5},""""
                "]teams[": {"]hours_since_last_update[": 2.0}}""""
        }
        manager.update_quality_metrics(quality_data)
        # Verify metrics were updated
        manager.metrics.data_freshness_hours.labels.assert_has_calls(
            [
                call(table_name="]matches["),": call(table_name="]teams[")]""""
        )
    def test_update_quality_metrics_completeness(self):
        "]""Test updating data quality metrics for completeness."""
        manager = AlertManager()
        quality_data = {
            "completeness[": {""""
                "]matches[": {"]completeness_ratio[": 0.95},""""
                "]teams[": {"]completeness_ratio[": 0.88}}""""
        }
        manager.update_quality_metrics(quality_data)
        # Verify metrics were updated
        manager.metrics.data_completeness_ratio.labels.assert_has_calls(
            [
                call(table_name="]matches["),": call(table_name="]teams[")]""""
        )
    def test_update_quality_metrics_overall_score(self):
        "]""Test updating data quality metrics for overall score."""
        manager = AlertManager()
        quality_data = {
            "freshness[": {"]matches[": {"]hours_since_last_update[": 5.5}},""""
            "]overall_score[": 0.85}": manager.update_quality_metrics(quality_data)"""
        # Verify overall score was set for each table:
        manager.metrics.data_quality_score.labels.assert_called_with(
            table_name="]matches["""""
        )
    def test_update_anomaly_metrics(self):
        "]""Test updating anomaly metrics."""
        manager = AlertManager()
        # Mock anomaly object
        class MockAnomaly:
            def __init__(self):
                self.table_name = "matches[": self.column_name = "]home_score[": self.anomaly_type = MagicMock()": self.anomaly_type.value = "]outlier[": self.severity = MagicMock()": self.severity.value = "]high[": self.anomaly_score = 0.15[": anomalies = [MockAnomaly()]": manager.update_anomaly_metrics(anomalies)""
        # Verify metrics were updated
        manager.metrics.anomalies_detected_total.labels.assert_called_with(
            table_name="]]matches[",": column_name="]home_score[",": anomaly_type="]outlier[",": severity="]high[")": manager.metrics.anomaly_score.labels.assert_called_with(": table_name="]matches[", column_name="]home_score["""""
        )
    def test_check_and_fire_quality_alerts_freshness_critical(self):
        "]""Test quality alerts for critical freshness issues."""
        manager = AlertManager()
        quality_data = {
            "freshness[": {""""
                "]matches[": {"]hours_since_last_update[": 30.0},  # > 24 hours[""""
            }
        }
        alerts = manager.check_and_fire_quality_alerts(quality_data)
        assert len(alerts) ==1
        assert alerts[0].level ==AlertLevel.CRITICAL
        assert "]]数据新鲜度严重告警[" in alerts[0].title[""""
        assert "]]matches[" in alerts[0].title[""""
    def test_check_and_fire_quality_alerts_freshness_warning(self):
        "]]""Test quality alerts for warning freshness issues."""
        manager = AlertManager()
        quality_data = {
            "freshness[": {""""
                "]matches[": {"]hours_since_last_update[": 15.0},  # > 12 hours[""""
            }
        }
        alerts = manager.check_and_fire_quality_alerts(quality_data)
        assert len(alerts) ==1
        assert alerts[0].level ==AlertLevel.WARNING
        assert "]]数据新鲜度警告[" in alerts[0].title[""""
    def test_check_and_fire_quality_alerts_completeness_critical(self):
        "]]""Test quality alerts for critical completeness issues."""
        manager = AlertManager()
        quality_data = {
            "completeness[": {""""
                "]matches[": {"]completeness_ratio[": 0.75},  # < 0.8[""""
            }
        }
        alerts = manager.check_and_fire_quality_alerts(quality_data)
        assert len(alerts) ==1
        assert alerts[0].level ==AlertLevel.CRITICAL
        assert "]]数据完整性严重告警[" in alerts[0].title[""""
    def test_check_and_fire_quality_alerts_quality_score(self):
        "]]""Test quality alerts for overall quality score."""
        manager = AlertManager()
        quality_data = {
            "overall_score[": 0.65,  # < 0.7[""""
        }
        alerts = manager.check_and_fire_quality_alerts(quality_data)
        assert len(alerts) ==1
        assert alerts[0].level ==AlertLevel.CRITICAL
        assert "]]数据质量严重告警[" in alerts[0].title[""""
    def test_check_and_fire_quality_alerts_no_issues(self):
        "]]""Test quality alerts when no issues found."""
        manager = AlertManager()
        quality_data = {
            "freshness[": {"]matches[": {"]hours_since_last_update[": 1.0}},""""
            "]completeness[": {"]matches[": {"]completeness_ratio[": 0.98}},""""
            "]overall_score[": 0.85}": alerts = manager.check_and_fire_quality_alerts(quality_data)": assert len(alerts) ==0[" def test_check_and_fire_anomaly_alerts_critical(self):"
        "]]""Test anomaly alerts for critical anomalies."""
        manager = AlertManager()
        # Mock anomaly object
        class MockAnomaly:
            def __init__(self):
                self.table_name = "matches[": self.column_name = "]home_score[": self.anomaly_type = MagicMock()": self.anomaly_type.value = "]outlier[": self.anomaly_score = 0.25  # > 0.2[": self.description = "]]High score detected[": anomalies = [MockAnomaly()]": alerts = manager.check_and_fire_anomaly_alerts(anomalies)": assert len(alerts) ==1[" assert alerts[0].level ==AlertLevel.CRITICAL"
        assert "]]数据异常严重告警[" in alerts[0].title[""""
    def test_check_and_fire_anomaly_alerts_warning(self):
        "]]""Test anomaly alerts for warning anomalies."""
        manager = AlertManager()
        # Mock anomaly object
        class MockAnomaly:
            def __init__(self):
                self.table_name = "matches[": self.column_name = "]home_score[": self.anomaly_type = MagicMock()": self.anomaly_type.value = "]outlier[": self.anomaly_score = 0.15  # > 0.1[": self.description = "]]Medium score detected[": anomalies = [MockAnomaly()]": alerts = manager.check_and_fire_anomaly_alerts(anomalies)": assert len(alerts) ==1[" assert alerts[0].level ==AlertLevel.WARNING"
        assert "]]数据异常警告[" in alerts[0].title[""""
    def test_check_and_fire_anomaly_alerts_low_score(self):
        "]]""Test anomaly alerts for low score anomalies (should not fire)."""
        manager = AlertManager()
        # Mock anomaly object
        class MockAnomaly:
            def __init__(self):
                self.table_name = "matches[": self.column_name = "]home_score[": self.anomaly_type = MagicMock()": self.anomaly_type.value = "]outlier[": self.anomaly_score = 0.05  # < 0.1[": self.description = "]]Low score detected[": anomalies = [MockAnomaly()]": alerts = manager.check_and_fire_anomaly_alerts(anomalies)": assert len(alerts) ==0[" class TestAlertManagerIntegration:"
    "]]""Integration tests for AlertManager functionality."""
    @patch("src.monitoring.alert_manager.logger[")": def test_full_alert_workflow(self, mock_logger):"""
        "]""Test complete alert workflow from firing to resolution."""
        manager = AlertManager()
        # Fire alert
        alert = manager.fire_alert(
            title="Workflow Test[",": message="]Testing complete workflow[",": level=AlertLevel.WARNING,": source="]integration_test[",": rule_id="]data_freshness_warning[")": assert alert is not None[" assert alert.status ==AlertStatus.ACTIVE[""
        # Check active alerts
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) ==1
        assert active_alerts[0] ==alert
        # Get summary
        summary = manager.get_alert_summary()
        assert summary["]]]active_alerts["] ==1[" assert summary["]]by_level["]"]warning[" ==1[""""
        # Resolve alert
        resolved = manager.resolve_alert(alert.alert_id)
        assert resolved is True
        assert alert.status ==AlertStatus.RESOLVED
        # Verify active alerts is empty
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) ==0
        # Verify updated summary
        summary = manager.get_alert_summary()
        assert summary["]]active_alerts["] ==0[" assert summary["]]resolved_alerts["] ==1[""""
    @patch("]]src.monitoring.alert_manager.logger[")": def test_quality_monitoring_workflow(self, mock_logger):"""
        "]""Test quality monitoring workflow with alerts."""
        manager = AlertManager()
        # Simulate quality issues
        quality_data = {
            "freshness[": {""""
                "]matches[": {"]hours_since_last_update[": 30.0},  # Critical[""""
                "]]teams[": {"]hours_since_last_update[": 15.0},  # Warning[""""
            },
            "]]completeness[": {""""
                "]matches[": {"]completeness_ratio[": 0.75},  # Critical[""""
            },
            "]]overall_score[": 0.65,  # Critical[""""
        }
        # Fire quality alerts
        alerts = manager.check_and_fire_quality_alerts(quality_data)
        assert len(alerts) ==4  # 2 freshness + 1 completeness + 1 quality score
        # Verify alerts were added
        assert len(manager.alerts) ==4
        # Verify summary reflects alerts
        summary = manager.get_alert_summary()
        assert summary["]]active_alerts["] ==4[" assert summary["]]critical_alerts["] ==3  # freshness, completeness, score[" assert summary["]]by_level["]"]warning[" ==1  # freshness warning[""""
    @patch("]]src.monitoring.alert_manager.logger[")": def test_handler_error_handling(self, mock_logger):"""
        "]""Test that handler errors don't break alert processing."""
        manager = AlertManager()
        def error_handler(alert):
            raise Exception("Simulated handler error[")": def success_handler(alert):": pass[": manager.register_handler(AlertChannel.LOG, error_handler)"
        manager.register_handler(AlertChannel.LOG, success_handler)
        # This should not raise an exception despite handler error
        alert = manager.fire_alert(
            title="]]Error Handling Test[",": message="]Testing error handling[",": level=AlertLevel.INFO,": source="]test[")"]": assert alert is not None""
        # Error should be logged
        mock_logger.error.assert_called()