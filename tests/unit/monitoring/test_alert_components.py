"""
测试告警组件

验证拆分后的各个告警组件的功能。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from prometheus_client import CollectorRegistry

from src.monitoring.alerts import (
    Alert,
    AlertChannel,
    AlertLevel,
    AlertManager,
    AlertRule,
    AlertRuleEngine,
    AlertSeverity,
    AlertStatus,
    AlertType,
    LogAlertChannel,
    PrometheusAlertChannel,
    PrometheusMetrics,
)


class TestAlert:
    """测试告警对象"""

    def test_alert_creation(self):
        """测试告警创建"""
        alert = Alert(
            alert_id="test-001",
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.WARNING,
            source="test",
        )

        assert alert.alert_id == "test-001"
        assert alert.title == "测试告警"
        assert alert.level == AlertLevel.WARNING
        assert alert.type == AlertType.WARNING
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.status == AlertStatus.ACTIVE
        assert alert.created_at is not None

    def test_alert_to_dict(self):
        """测试告警转换为字典"""
        alert = Alert(
            alert_id="test-001",
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.ERROR,
            source="test",
        )

        alert_dict = alert.to_dict()

        assert alert_dict["alert_id"] == "test-001"
        assert alert_dict["title"] == "测试告警"
        assert alert_dict["level"] == "error"
        assert alert_dict["type"] == "error"
        assert alert_dict["severity"] == "high"
        assert alert_dict["status"] == "active"

    def test_alert_resolve(self):
        """测试解决告警"""
        alert = Alert(
            alert_id="test-001",
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.WARNING,
            source="test",
        )

        alert.resolve()
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None

    def test_alert_silence(self):
        """测试静默告警"""
        alert = Alert(
            alert_id="test-001",
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.WARNING,
            source="test",
        )

        alert.silence()
        assert alert.status == AlertStatus.SILENCED


class TestAlertRule:
    """测试告警规则"""

    def test_rule_creation(self):
        """测试规则创建"""
        rule = AlertRule(
            rule_id="test-rule",
            name="测试规则",
            condition="data_quality_score < 0.5",
            level=AlertLevel.CRITICAL,
            channels=[AlertChannel.LOG, AlertChannel.PROMETHEUS],
        )

        assert rule.rule_id == "test-rule"
        assert rule.name == "测试规则"
        assert rule.enabled is True
        assert rule.last_fired is None

    def test_rule_throttle(self):
        """测试规则限流"""
        rule = AlertRule(
            rule_id="test-rule",
            name="测试规则",
            condition="data_quality_score < 0.5",
            level=AlertLevel.CRITICAL,
            channels=[AlertChannel.LOG],
            throttle_seconds=60,
        )

        now = datetime.now()

        # 首次触发不应该被限流
        assert rule.should_throttle(now) is False

        # 更新触发时间
        rule.update_last_fired(now)

        # 立即再次触发应该被限流
        assert rule.should_throttle(now) is True

        # 超过限流时间后不应该被限流
        later = now + timedelta(seconds=61)
        assert rule.should_throttle(later) is False


class TestAlertRuleEngine:
    """测试告警规则引擎"""

    @pytest.fixture
    def engine(self):
        """创建规则引擎实例"""
        return AlertRuleEngine()

    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert len(engine.rules) > 0  # 应该有默认规则
        assert "data_quality_critical" in engine.rules
        assert "anomaly_critical" in engine.rules

    def test_add_rule(self, engine):
        """测试添加规则"""
        rule = AlertRule(
            rule_id="custom-rule",
            name="自定义规则",
            condition="error_rate > 0.1",
            level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG],
        )

        engine.add_rule(rule)
        assert "custom-rule" in engine.rules
        assert engine.get_rule("custom-rule") == rule

    def test_remove_rule(self, engine):
        """测试删除规则"""
        assert "data_quality_warning" in engine.rules
        result = engine.remove_rule("data_quality_warning")
        assert result is True
        assert "data_quality_warning" not in engine.rules

    def test_evaluate_rule(self, engine):
        """测试规则评估"""
        # 测试数据质量规则
        context = {"data_quality_score": 0.3}
        result = engine.evaluate_rule("data_quality_critical", context)
        assert result is True

        # 测试高质量数据
        context = {"data_quality_score": 0.9}
        result = engine.evaluate_rule("data_quality_critical", context)
        assert result is False

    def test_enable_disable_rule(self, engine):
        """测试启用/禁用规则"""
        rule_id = "data_quality_critical"
        rule = engine.get_rule(rule_id)

        # 禁用规则
        engine.disable_rule(rule_id)
        assert rule.enabled is False

        # 评估应该返回False
        context = {"data_quality_score": 0.3}
        result = engine.evaluate_rule(rule_id, context)
        assert result is False

        # 启用规则
        engine.enable_rule(rule_id)
        assert rule.enabled is True


class TestLogAlertChannel:
    """测试日志告警渠道"""

    @pytest.fixture
    def channel(self):
        """创建渠道实例"""
        return LogAlertChannel()

    @pytest.mark.asyncio
    async def test_send_alert(self, channel):
        """测试发送告警"""
        alert = Alert(
            alert_id="test-001",
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.WARNING,
            source="test",
        )

        with patch.object(channel.logger, 'log') as mock_log:
            result = await channel.send_alert(alert)
            assert result is True
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection(self, channel):
        """测试连接测试"""
        with patch.object(channel.logger, 'info') as mock_info:
            result = await channel.test_connection()
            assert result is True
            mock_info.assert_called_once_with("日志告警渠道测试成功")


class TestPrometheusAlertChannel:
    """测试Prometheus告警渠道"""

    @pytest.fixture
    def channel(self):
        """创建渠道实例"""
        registry = CollectorRegistry()
        metrics = PrometheusMetrics(registry)
        return PrometheusAlertChannel(metrics=metrics)

    @pytest.mark.asyncio
    async def test_send_alert(self, channel):
        """测试发送告警"""
        alert = Alert(
            alert_id="test-001",
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.WARNING,
            source="test",
        )

        result = await channel.send_alert(alert, rule_id="test-rule")
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection(self, channel):
        """测试连接测试"""
        result = await channel.test_connection()
        assert result is True


class TestPrometheusMetrics:
    """测试Prometheus指标"""

    @pytest.fixture
    def metrics(self):
        """创建指标实例"""
        registry = CollectorRegistry()
        return PrometheusMetrics(registry)

    def test_update_quality_metrics(self, metrics):
        """测试更新质量指标"""
        quality_data = {
            "table_name": "test_table",
            "freshness_hours": 2.5,
            "completeness_ratio": 0.95,
            "quality_score": 0.88,
        }

        metrics.update_quality_metrics(quality_data)
        # 验证指标是否更新（需要通过收集器验证）
        # 这里简化测试，只确保没有异常

    def test_update_anomaly_metrics(self, metrics):
        """测试更新异常指标"""
        # 模拟异常对象
        class MockAnomaly:
            def __init__(self):
                self.table_name = "test_table"
                self.column_name = "test_col"
                self.anomaly_type = MagicMock()
                self.anomaly_type.value = "statistical"
                self.anomaly_score = 0.15

        anomalies = [MockAnomaly()]
        metrics.update_anomaly_metrics(anomalies)

    def test_record_check_duration(self, metrics):
        """测试记录检查持续时间"""
        metrics.record_check_duration("quality_check", 0.123)

    def test_record_error(self, metrics):
        """测试记录错误"""
        metrics.record_error("connection_error")


class TestAlertManager:
    """测试告警管理器"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        registry = CollectorRegistry()
        return AlertManager(registry)

    def test_manager_initialization(self, manager):
        """测试管理器初始化"""
        assert len(manager.alert_handlers) > 0
        assert AlertChannel.LOG in manager.alert_handlers
        assert AlertChannel.PROMETHEUS in manager.alert_handlers
        assert manager.rule_engine is not None
        assert manager.metrics is not None

    def test_fire_alert(self, manager):
        """测试触发告警"""
        alert = manager.fire_alert(
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.WARNING,
            source="test",
            labels={"test": "value"},
        )

        assert alert is not None
        assert alert.title == "测试告警"
        assert alert in manager.alerts
        assert manager.stats["alerts_created"] == 1

    def test_fire_alert_with_throttle(self, manager):
        """测试告警限流"""
        rule_id = "data_quality_critical"

        # 第一次触发
        alert1 = manager.fire_alert(
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.CRITICAL,
            source="test",
            rule_id=rule_id,
        )
        assert alert1 is not None

        # 立即再次触发（应该被限流）
        alert2 = manager.fire_alert(
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.CRITICAL,
            source="test",
            rule_id=rule_id,
        )
        assert alert2 is None

    def test_resolve_alert(self, manager):
        """测试解决告警"""
        # 先创建一个告警
        alert = manager.fire_alert(
            title="测试告警",
            message="这是一个测试告警",
            level=AlertLevel.WARNING,
            source="test",
        )
        assert alert is not None

        # 解决告警
        result = manager.resolve_alert(alert.alert_id)
        assert result is True
        assert alert.status == AlertStatus.RESOLVED
        assert manager.stats["alerts_resolved"] == 1

    def test_get_active_alerts(self, manager):
        """测试获取活跃告警"""
        # 创建不同级别的告警
        manager.fire_alert("警告1", "消息1", AlertLevel.WARNING, "test")
        manager.fire_alert("错误1", "消息2", AlertLevel.ERROR, "test")

        # 创建一个已解决的告警
        alert = manager.fire_alert("已解决", "消息3", AlertLevel.INFO, "test")
        manager.resolve_alert(alert.alert_id)

        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 2

        # 按级别过滤
        warning_alerts = manager.get_active_alerts(level=AlertLevel.WARNING)
        assert len(warning_alerts) == 1
        assert warning_alerts[0].level == AlertLevel.WARNING

    def test_get_alert_summary(self, manager):
        """测试获取告警摘要"""
        # 创建一些告警
        manager.fire_alert("警告1", "消息1", AlertLevel.WARNING, "test")
        manager.fire_alert("错误1", "消息2", AlertLevel.ERROR, "test")

        summary = manager.get_alert_summary()

        assert "total_alerts" in summary
        assert "active_alerts" in summary
        assert "by_level" in summary
        assert "by_source" in summary
        assert "statistics" in summary
        assert summary["total_alerts"] >= 2

    def test_update_quality_metrics(self, manager):
        """测试更新质量指标"""
        quality_data = {
            "table_name": "test_table",
            "quality_score": 0.3,  # 低质量，应该触发告警
            "freshness_hours": 2.5,
            "completeness_ratio": 0.95,
        }

        manager.update_quality_metrics(quality_data)

        # 应该触发一个严重告警
        critical_alerts = manager.get_active_alerts(level=AlertLevel.CRITICAL)
        assert len(critical_alerts) > 0

    def test_update_anomaly_metrics(self, manager):
        """测试更新异常指标"""
        # 模拟异常对象
        class MockAnomaly:
            def __init__(self, score):
                self.table_name = "test_table"
                self.column_name = "test_col"
                self.description = f"异常检测，评分: {score}"
                self.anomaly_score = score
                self.anomaly_type = MagicMock()
                self.anomaly_type.value = "statistical"

        # 高分异常应该触发告警
        anomalies = [MockAnomaly(0.25)]
        manager.update_anomaly_metrics(anomalies)

        critical_alerts = [a for a in manager.alerts if "异常严重" in a.title]
        assert len(critical_alerts) > 0

    def test_clear_resolved_alerts(self, manager):
        """测试清理已解决的告警"""
        # 创建并解决一些告警
        for i in range(3):
            alert = manager.fire_alert(f"告警{i}", f"消息{i}", AlertLevel.INFO, "test")
            manager.resolve_alert(alert.alert_id)

        # 修改解决时间为更早
        for alert in manager.alerts:
            if alert.status == AlertStatus.RESOLVED:
                alert.resolved_at = datetime.now() - timedelta(hours=25)

        # 清理24小时前的告警
        cleared_count = manager.clear_resolved_alerts(older_than_hours=24)
        assert cleared_count == 3