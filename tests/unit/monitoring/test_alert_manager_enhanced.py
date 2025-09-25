"""
告警管理器增强测试 - 覆盖率提升版本

针对 AlertManager 和相关类的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import json
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.monitoring.alert_manager import (
    Alert,
    AlertRule,
    AlertLevel,
    AlertStatus,
    AlertChannel,
    PrometheusMetrics,
    AlertManager
)


class TestAlert:
    """告警类测试"""

    def test_init_minimal(self):
        """测试最小初始化"""
        alert = Alert(
            alert_id="test_alert_001",
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.WARNING,
            source="test_service"
        )

        assert alert.alert_id == "test_alert_001"
        assert alert.title == "测试告警"
        assert alert.message == "这是一个测试告警"
        assert alert.level == AlertLevel.WARNING
        assert alert.source == "test_service"
        assert alert.status == AlertStatus.ACTIVE
        assert isinstance(alert.created_at, datetime)
        assert alert.labels == {}
        assert alert.annotations == {}
        assert alert.resolved_at is None

    def test_init_with_metadata(self):
        """测试带元数据的初始化"""
        labels = {"error_code": "500", "endpoint": "/api/test"}
        annotations = {"severity": "high", "component": "api"}
        alert = Alert(
            alert_id="api_error_001",
            title="API错误",
            message="API调用失败",
            level=AlertLevel.ERROR,
            source="api_service",
            labels=labels,
            annotations=annotations
        )

        assert alert.labels == labels
        assert alert.annotations == annotations

    def test_resolve_alert(self):
        """测试解决告警"""
        alert = Alert("test_alert_001", "测试告警", "消息", AlertLevel.INFO, "test")
        original_resolved_at = alert.resolved_at

        # 解决告警
        alert.resolve()

        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None
        assert isinstance(alert.resolved_at, datetime)

    def test_silence_alert(self):
        """测试静默告警"""
        alert = Alert("test_alert_001", "测试告警", "消息", AlertLevel.WARNING, "test")

        # 静默告警
        alert.silence()

        assert alert.status == AlertStatus.SILENCED

    def test_to_dict(self):
        """测试转换为字典"""
        labels = {"component": "api", "error_code": "500"}
        annotations = {"severity": "critical", "action_required": "immediate"}

        alert = Alert(
            alert_id="critical_alert_001",
            title="严重告警",
            message="系统严重故障",
            level=AlertLevel.CRITICAL,
            source="api_service",
            labels=labels,
            annotations=annotations
        )

        alert_dict = alert.to_dict()

        assert isinstance(alert_dict, dict)
        assert alert_dict["alert_id"] == "critical_alert_001"
        assert alert_dict["title"] == "严重告警"
        assert alert_dict["message"] == "系统严重故障"
        assert alert_dict["level"] == "critical"
        assert alert_dict["source"] == "test_service"
        assert alert_dict["status"] == "active"
        assert alert_dict["labels"] == labels
        assert alert_dict["annotations"] == annotations
        assert "created_at" in alert_dict
        assert alert_dict["resolved_at"] is None

    def test_from_dict(self):
        """测试从字典创建"""
        alert_data = {
            "title": "来自字典的告警",
            "message": "消息内容",
            "severity": "HIGH",
            "source": "test_source",
            "metadata": {"test": "value"}
        }

        alert = Alert.from_dict(alert_data)

        assert alert.title == "来自字典的告警"
        assert alert.message == "消息内容"
        assert alert.severity == AlertLevel.HIGH
        assert alert.source == "test_source"
        assert alert.metadata == {"test": "value"}

    def test_severity_levels(self):
        """测试严重程度级别"""
        severities = [AlertLevel.LOW, AlertLevel.MEDIUM, AlertLevel.HIGH, AlertLevel.CRITICAL]

        for severity in severities:
            alert = Alert("测试", "消息", severity, "test")
            assert alert.severity == severity

    def test_status_transitions(self):
        """测试状态转换"""
        alert = Alert("测试", "消息", AlertLevel.MEDIUM, "test")

        # OPEN -> ACKNOWLEDGED
        alert.update_status(AlertStatus.ACKNOWLEDGED)
        assert alert.status == AlertStatus.ACKNOWLEDGED

        # ACKNOWLEDGED -> RESOLVED
        alert.update_status(AlertStatus.RESOLVED)
        assert alert.status == AlertStatus.RESOLVED

        # RESOLVED -> REOPENED
        alert.update_status(AlertStatus.REOPENED)
        assert alert.status == AlertStatus.REOPENED


class TestAlertRule:
    """告警规则类测试"""

    def test_init_minimal(self):
        """测试最小初始化"""
        rule = AlertRule(
            name="测试规则",
            metric_name="test_metric",
            threshold=10.0,
            comparison_operator=">"
        )

        assert rule.name == "测试规则"
        assert rule.metric_name == "test_metric"
        assert rule.threshold == 10.0
        assert rule.comparison_operator == ">"
        assert rule.severity == AlertLevel.MEDIUM
        assert rule.enabled is True
        assert rule.duration == 60
        assert rule.metadata == {}

    def test_init_full(self):
        """测试完整初始化"""
        rule = AlertRule(
            name="完整规则",
            metric_name="cpu_usage",
            threshold=80.0,
            comparison_operator=">=",
            severity=AlertLevel.HIGH,
            duration=300,
            notification_channels=["email", "slack"],
            metadata={"description": "CPU使用率过高"}
        )

        assert rule.severity == AlertLevel.HIGH
        assert rule.duration == 300
        assert rule.notification_channels == ["email", "slack"]
        assert rule.metadata["description"] == "CPU使用率过高"

    def test_evaluate_rule_greater_than(self):
        """测试大于规则评估"""
        rule = AlertRule("CPU规则", "cpu_usage", 80.0, ">")

        # 应该触发告警
        assert rule.evaluate({"cpu_usage": 85.0}) is True
        assert rule.evaluate({"cpu_usage": 80.1}) is True

        # 不应该触发告警
        assert rule.evaluate({"cpu_usage": 80.0}) is False
        assert rule.evaluate({"cpu_usage": 75.0}) is False

    def test_evaluate_rule_less_than(self):
        """测试小于规则评估"""
        rule = AlertRule("内存规则", "free_memory", 100.0, "<")

        # 应该触发告警
        assert rule.evaluate({"free_memory": 50.0}) is True
        assert rule.evaluate({"free_memory": 99.0}) is True

        # 不应该触发告警
        assert rule.evaluate({"free_memory": 100.0}) is False
        assert rule.evaluate({"free_memory": 150.0}) is False

    def test_evaluate_rule_equal(self):
        """测试等于规则评估"""
        rule = AlertRule("状态规则", "status_code", 200, "==")

        # 应该触发告警
        assert rule.evaluate({"status_code": 200}) is True

        # 不应该触发告警
        assert rule.evaluate({"status_code": 201}) is False
        assert rule.evaluate({"status_code": 500}) is False

    def test_evaluate_rule_not_equal(self):
        """测试不等于规则评估"""
        rule = AlertRule("错误规则", "error_count", 0, "!=")

        # 应该触发告警
        assert rule.evaluate({"error_count": 1}) is True
        assert rule.evaluate({"error_count": 5}) is True

        # 不应该触发告警
        assert rule.evaluate({"error_count": 0}) is False

    def test_evaluate_rule_missing_metric(self):
        """测试缺失指标的情况"""
        rule = AlertRule("测试规则", "cpu_usage", 80.0, ">")

        # 指标缺失时应该返回False
        assert rule.evaluate({"memory_usage": 50.0}) is False

    def test_to_dict(self):
        """测试转换为字典"""
        rule = AlertRule(
            name="测试规则",
            metric_name="test_metric",
            threshold=10.0,
            comparison_operator=">",
            severity=AlertLevel.CRITICAL,
            notification_channels=["email"]
        )

        rule_dict = rule.to_dict()

        assert isinstance(rule_dict, dict)
        assert rule_dict["name"] == "测试规则"
        assert rule_dict["metric_name"] == "test_metric"
        assert rule_dict["threshold"] == 10.0
        assert rule_dict["comparison_operator"] == ">"
        assert rule_dict["severity"] == "CRITICAL"
        assert rule_dict["notification_channels"] == ["email"]

    def test_from_dict(self):
        """测试从字典创建"""
        rule_data = {
            "name": "来自字典的规则",
            "metric_name": "test_metric",
            "threshold": 50.0,
            "comparison_operator": "<=",
            "severity": "LOW"
        }

        rule = AlertRule.from_dict(rule_data)

        assert rule.name == "来自字典的规则"
        assert rule.metric_name == "test_metric"
        assert rule.threshold == 50.0
        assert rule.comparison_operator == "<="
        assert rule.severity == AlertLevel.LOW

    def test_enable_disable(self):
        """测试启用/禁用"""
        rule = AlertRule("测试规则", "test_metric", 10.0, ">")

        # 禁用规则
        rule.disable()
        assert rule.enabled is False

        # 启用规则
        rule.enable()
        assert rule.enabled is True

    def test_evaluate_disabled_rule(self):
        """测试禁用规则的评估"""
        rule = AlertRule("测试规则", "test_metric", 10.0, ">")
        rule.disable()

        # 禁用的规则应该总是返回False
        assert rule.evaluate({"test_metric": 15.0}) is False


class TestPrometheusMetrics:
    """Prometheus指标类测试"""

    def test_init(self):
        """测试初始化"""
        metrics = PrometheusMetrics()

        assert metrics.metrics_registry is not None
        assert isinstance(metrics.metrics, dict)

    def test_create_counter(self):
        """测试创建计数器"""
        metrics = PrometheusMetrics()

        counter = metrics.create_counter(
            name="test_counter",
            description="测试计数器",
            labels=["method", "endpoint"]
        )

        assert counter is not None
        assert "test_counter" in metrics.metrics

    def test_create_gauge(self):
        """测试创建仪表盘"""
        metrics = PrometheusMetrics()

        gauge = metrics.create_gauge(
            name="test_gauge",
            description="测试仪表盘",
            labels=["service", "environment"]
        )

        assert gauge is not None
        assert "test_gauge" in metrics.metrics

    def test_create_histogram(self):
        """测试创建直方图"""
        metrics = PrometheusMetrics()

        histogram = metrics.create_histogram(
            name="test_histogram",
            description="测试直方图",
            labels=["operation"],
            buckets=[0.1, 0.5, 1.0, 2.0]
        )

        assert histogram is not None
        assert "test_histogram" in metrics.metrics

    def test_increment_counter(self):
        """测试增加计数器"""
        metrics = PrometheusMetrics()

        counter = metrics.create_counter("test_counter", "测试计数器", ["method"])

        # 增加计数器
        metrics.increment_counter("test_counter", 1.0, {"method": "GET"})
        metrics.increment_counter("test_counter", 2.0, {"method": "POST"})

        # 验证计数器存在
        assert "test_counter" in metrics.metrics

    def test_set_gauge(self):
        """测试设置仪表盘值"""
        metrics = PrometheusMetrics()

        gauge = metrics.create_gauge("test_gauge", "测试仪表盘", ["service"])

        # 设置仪表盘值
        metrics.set_gauge("test_gauge", 75.5, {"service": "api"})
        metrics.set_gauge("test_gauge", 25.0, {"service": "database"})

        # 验证仪表盘存在
        assert "test_gauge" in metrics.metrics

    def test_observe_histogram(self):
        """测试观察直方图"""
        metrics = PrometheusMetrics()

        histogram = metrics.create_histogram("test_histogram", "测试直方图", ["operation"])

        # 观察直方图
        metrics.observe_histogram("test_histogram", 0.05, {"operation": "query"})
        metrics.observe_histogram("test_histogram", 1.2, {"operation": "insert"})

        # 验证直方图存在
        assert "test_histogram" in metrics.metrics

    def test_get_metrics_data(self):
        """测试获取指标数据"""
        metrics = PrometheusMetrics()

        # 创建一些指标
        metrics.create_counter("test_counter", "测试计数器")
        metrics.create_gauge("test_gauge", "测试仪表盘")

        # 获取指标数据
        metrics_data = metrics.get_metrics_data()

        assert isinstance(metrics_data, dict)
        assert len(metrics_data) >= 2

    def test_get_nonexistent_metric(self):
        """测试获取不存在的指标"""
        metrics = PrometheusMetrics()

        # 应该返回None
        gauge = metrics.get_gauge("nonexistent_gauge")
        assert gauge is None

        counter = metrics.get_counter("nonexistent_counter")
        assert counter is None

        histogram = metrics.get_histogram("nonexistent_histogram")
        assert histogram is None

    @patch('prometheus_client.Counter')
    def test_create_counter_with_mock(self, mock_counter_class):
        """测试使用Mock创建计数器"""
        mock_counter = Mock()
        mock_counter_class.return_value = mock_counter

        metrics = PrometheusMetrics()
        counter = metrics.create_counter("test_counter", "测试计数器")

        assert counter == mock_counter
        mock_counter_class.assert_called_once()

    @patch('prometheus_client.Gauge')
    def test_create_gauge_with_mock(self, mock_gauge_class):
        """测试使用Mock创建仪表盘"""
        mock_gauge = Mock()
        mock_gauge_class.return_value = mock_gauge

        metrics = PrometheusMetrics()
        gauge = metrics.create_gauge("test_gauge", "测试仪表盘")

        assert gauge == mock_gauge
        mock_gauge_class.assert_called_once()

    @patch('prometheus_client.Histogram')
    def test_create_histogram_with_mock(self, mock_histogram_class):
        """测试使用Mock创建直方图"""
        mock_histogram = Mock()
        mock_histogram_class.return_value = mock_histogram

        metrics = PrometheusMetrics()
        histogram = metrics.create_histogram("test_histogram", "测试直方图")

        assert histogram == mock_histogram
        mock_histogram_class.assert_called_once()


class TestAlertChannel:
    """告警渠道测试"""

    def test_alert_channel_enum(self):
        """测试告警渠道枚举"""
        # 测试枚举值存在
        assert hasattr(AlertChannel, 'EMAIL')
        assert hasattr(AlertChannel, 'SLACK')
        assert hasattr(AlertChannel, 'WEBHOOK')

    def test_alert_channel_values(self):
        """测试告警渠道值"""
        # 验证枚举值
        channels = [AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.WEBHOOK]
        for channel in channels:
            assert isinstance(channel, AlertChannel)
            assert isinstance(channel.value, str)


class TestAlertManager:
    """告警管理器测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        db_manager = Mock()
        db_manager.execute_query = Mock()
        db_manager.execute_update = Mock()
        db_manager.connection = Mock()
        return db_manager

    @pytest.fixture
    def mock_prometheus_metrics(self):
        """模拟Prometheus指标"""
        metrics = Mock()
        metrics.create_counter = Mock()
        metrics.create_gauge = Mock()
        metrics.increment_counter = Mock()
        metrics.set_gauge = Mock()
        return metrics

    @pytest.fixture
    def alert_manager(self, mock_db_manager, mock_prometheus_metrics):
        """创建告警管理器实例"""
        with patch('src.monitoring.alert_manager.DatabaseManager', return_value=mock_db_manager), \
             patch('src.monitoring.alert_manager.PrometheusMetrics', return_value=mock_prometheus_metrics):

            manager = AlertManager()
            manager.db_manager = mock_db_manager
            manager.prometheus_metrics = mock_prometheus_metrics
            return manager

    def test_init(self, alert_manager):
        """测试初始化"""
        assert alert_manager.db_manager is not None
        assert alert_manager.prometheus_metrics is not None
        assert alert_manager.alert_rules == {}
        assert alert_manager.notification_channels == {}
        assert alert_manager.active_alerts == []

    def test_create_alert_rule(self, alert_manager):
        """测试创建告警规则"""
        rule_data = {
            "name": "CPU使用率告警",
            "metric_name": "cpu_usage",
            "threshold": 80.0,
            "comparison_operator": ">",
            "severity": "HIGH",
            "duration": 300
        }

        rule = alert_manager.create_alert_rule(rule_data)

        assert rule.name == "CPU使用率告警"
        assert rule.metric_name == "cpu_usage"
        assert rule.threshold == 80.0
        assert rule.comparison_operator == ">"
        assert rule.severity == AlertLevel.HIGH
        assert "CPU使用率告警" in alert_manager.alert_rules

    def test_create_notification_channel(self, alert_manager):
        """测试创建通知渠道"""
        channel_data = {
            "name": "邮件通知",
            "type": "email",
            "config": {
                "smtp_server": "smtp.gmail.com",
                "recipients": ["admin@example.com"]
            }
        }

        channel = alert_manager.create_notification_channel(channel_data)

        assert channel.name == "邮件通知"
        assert channel.type == "email"
        assert channel.config["smtp_server"] == "smtp.gmail.com"
        assert "邮件通知" in alert_manager.notification_channels

    def test_create_alert(self, alert_manager):
        """测试创建告警"""
        alert = alert_manager.create_alert(
            title="测试告警",
            message="系统异常",
            severity=AlertLevel.MEDIUM,
            source="test_service"
        )

        assert alert.title == "测试告警"
        assert alert.message == "系统异常"
        assert alert.severity == AlertLevel.MEDIUM
        assert alert.source == "test_service"
        assert len(alert_manager.active_alerts) == 1

    def test_resolve_alert(self, alert_manager):
        """测试解决告警"""
        # 创建告警
        alert = alert_manager.create_alert(
            title="测试告警",
            message="系统异常",
            severity=AlertLevel.MEDIUM,
            source="test_service"
        )

        # 解决告警
        resolved_alert = alert_manager.resolve_alert(alert.id)

        assert resolved_alert.status == AlertStatus.RESOLVED
        assert len(alert_manager.active_alerts) == 0

    def test_evaluate_rules(self, alert_manager):
        """测试评估规则"""
        # 创建规则
        rule_data = {
            "name": "CPU使用率告警",
            "metric_name": "cpu_usage",
            "threshold": 80.0,
            "comparison_operator": ">"
        }
        alert_manager.create_alert_rule(rule_data)

        # 模拟指标数据
        metrics_data = {"cpu_usage": 85.0}

        # 评估规则
        triggered_alerts = alert_manager.evaluate_rules(metrics_data)

        assert len(triggered_alerts) == 1
        assert triggered_alerts[0].title == "CPU使用率告警"

    def test_evaluate_rules_no_trigger(self, alert_manager):
        """测试评估规则但不触发"""
        # 创建规则
        rule_data = {
            "name": "CPU使用率告警",
            "metric_name": "cpu_usage",
            "threshold": 80.0,
            "comparison_operator": ">"
        }
        alert_manager.create_alert_rule(rule_data)

        # 模拟指标数据（不触发告警）
        metrics_data = {"cpu_usage": 75.0}

        # 评估规则
        triggered_alerts = alert_manager.evaluate_rules(metrics_data)

        assert len(triggered_alerts) == 0

    def test_send_notification(self, alert_manager):
        """测试发送通知"""
        # 创建通知渠道
        channel_data = {
            "name": "邮件通知",
            "type": "email",
            "config": {
                "smtp_server": "smtp.gmail.com",
                "recipients": ["admin@example.com"]
            }
        }
        channel = alert_manager.create_notification_channel(channel_data)

        # 创建告警
        alert = alert_manager.create_alert(
            title="测试告警",
            message="系统异常",
            severity=AlertLevel.HIGH,
            source="test_service"
        )

        # 发送通知
        result = alert_manager.send_notification(alert, channel.name)

        assert result is True

    def test_get_alert_statistics(self, alert_manager):
        """测试获取告警统计"""
        # 创建多个告警
        alert_manager.create_alert("告警1", "消息1", AlertLevel.LOW, "service1")
        alert_manager.create_alert("告警2", "消息2", AlertLevel.HIGH, "service2")
        alert_manager.create_alert("告警3", "消息3", AlertLevel.MEDIUM, "service1")

        # 获取统计信息
        stats = alert_manager.get_alert_statistics()

        assert isinstance(stats, dict)
        assert "total_alerts" in stats
        assert "alerts_by_severity" in stats
        assert "alerts_by_source" in stats
        assert "alerts_by_status" in stats

    def test_cleanup_old_alerts(self, alert_manager):
        """测试清理旧告警"""
        # 创建一些告警
        alert1 = alert_manager.create_alert("旧告警", "消息", AlertLevel.LOW, "service")
        alert2 = alert_manager.create_alert("新告警", "消息", AlertLevel.HIGH, "service")

        # 模拟告警创建时间
        alert1.created_at = datetime.now(timezone.utc) - timedelta(days=8)
        alert2.created_at = datetime.now(timezone.utc) - timedelta(days=1)

        # 清理7天前的告警
        cleaned_count = alert_manager.cleanup_old_alerts(days=7)

        assert cleaned_count == 1
        assert len(alert_manager.active_alerts) == 1
        assert alert_manager.active_alerts[0].title == "新告警"

    def test_health_check(self, alert_manager):
        """测试健康检查"""
        health_status = alert_manager.health_check()

        assert isinstance(health_status, dict)
        assert "status" in health_status
        assert "active_rules_count" in health_status
        assert "active_channels_count" in health_status
        assert "active_alerts_count" in health_status
        assert "last_evaluation_time" in health_status

    def test_get_rule_by_name(self, alert_manager):
        """测试根据名称获取规则"""
        # 创建规则
        rule_data = {
            "name": "测试规则",
            "metric_name": "test_metric",
            "threshold": 10.0,
            "comparison_operator": ">"
        }
        alert_manager.create_alert_rule(rule_data)

        # 获取规则
        rule = alert_manager.get_rule_by_name("测试规则")

        assert rule is not None
        assert rule.name == "测试规则"

        # 测试不存在的规则
        nonexistent_rule = alert_manager.get_rule_by_name("不存在的规则")
        assert nonexistent_rule is None

    def test_get_channel_by_name(self, alert_manager):
        """测试根据名称获取通知渠道"""
        # 创建通知渠道
        channel_data = {
            "name": "测试渠道",
            "type": "email",
            "config": {"recipients": ["test@example.com"]}
        }
        alert_manager.create_notification_channel(channel_data)

        # 获取渠道
        channel = alert_manager.get_channel_by_name("测试渠道")

        assert channel is not None
        assert channel.name == "测试渠道"

        # 测试不存在的渠道
        nonexistent_channel = alert_manager.get_channel_by_name("不存在的渠道")
        assert nonexistent_channel is None

    def test_disable_rule(self, alert_manager):
        """测试禁用规则"""
        # 创建规则
        rule_data = {
            "name": "测试规则",
            "metric_name": "test_metric",
            "threshold": 10.0,
            "comparison_operator": ">"
        }
        rule = alert_manager.create_alert_rule(rule_data)

        # 禁用规则
        alert_manager.disable_rule("测试规则")

        assert rule.enabled is False

    def test_enable_rule(self, alert_manager):
        """测试启用规则"""
        # 创建规则
        rule_data = {
            "name": "测试规则",
            "metric_name": "test_metric",
            "threshold": 10.0,
            "comparison_operator": ">"
        }
        rule = alert_manager.create_alert_rule(rule_data)

        # 先禁用
        alert_manager.disable_rule("测试规则")
        assert rule.enabled is False

        # 再启用
        alert_manager.enable_rule("测试规则")
        assert rule.enabled is True

    def test_update_rule(self, alert_manager):
        """测试更新规则"""
        # 创建规则
        rule_data = {
            "name": "测试规则",
            "metric_name": "test_metric",
            "threshold": 10.0,
            "comparison_operator": ">"
        }
        rule = alert_manager.create_alert_rule(rule_data)

        # 更新规则
        updated_rule = alert_manager.update_rule("测试规则", {
            "threshold": 15.0,
            "severity": "HIGH"
        })

        assert updated_rule.threshold == 15.0
        assert updated_rule.severity == AlertLevel.HIGH

    def test_delete_rule(self, alert_manager):
        """测试删除规则"""
        # 创建规则
        rule_data = {
            "name": "测试规则",
            "metric_name": "test_metric",
            "threshold": 10.0,
            "comparison_operator": ">"
        }
        alert_manager.create_alert_rule(rule_data)

        # 删除规则
        result = alert_manager.delete_rule("测试规则")

        assert result is True
        assert "测试规则" not in alert_manager.alert_rules

    def test_delete_channel(self, alert_manager):
        """测试删除通知渠道"""
        # 创建通知渠道
        channel_data = {
            "name": "测试渠道",
            "type": "email",
            "config": {"recipients": ["test@example.com"]}
        }
        alert_manager.create_notification_channel(channel_data)

        # 删除渠道
        result = alert_manager.delete_channel("测试渠道")

        assert result is True
        assert "测试渠道" not in alert_manager.notification_channels


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])