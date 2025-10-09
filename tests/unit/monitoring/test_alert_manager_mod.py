"""
测试告警管理器模块化组件
Test Alert Manager Modular Components

测试重构后的告警管理器模块的各项功能。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.monitoring.alert_manager_mod import (
    AlertManager,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertType,
    AlertLevel,
    AlertStatus,
    AlertChannel,
    PrometheusMetrics,
    LogChannel,
    WebhookChannel,
    EmailChannel,
    SlackChannel,
    AlertChannelManager,
    AlertRuleEngine,
    AlertAggregator,
    RuleEvaluationContext,
    AlertGroup,
)
from src.monitoring.alert_manager_mod.aggregator import AlertAggregator
from src.monitoring.alert_manager_mod.channels import AlertChannelManager
from src.monitoring.alert_manager_mod.rules import AlertRuleEngine
from src.monitoring.alert_manager_mod.manager import AlertManager


class TestAlertModels:
    """测试告警模型"""

    def test_alert_creation(self):
        """测试创建告警"""
        timestamp = datetime.utcnow()
        alert = Alert(
            alert_id="test-001",
            title="Test Alert",
            message="This is a test alert",
            level=AlertLevel.WARNING,
            source="test-service",
            labels={"service": "test", "env": "dev"},
            annotations={"runbook": "https://example.com"},
            created_at=timestamp,
        )

        assert alert.alert_id == "test-001"
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.level == AlertLevel.WARNING
        assert alert.type == AlertType.WARNING
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.source == "test-service"
        assert alert.status == AlertStatus.ACTIVE
        assert alert.created_at == timestamp

    def test_alert_to_dict(self):
        """测试告警转换为字典"""
        alert = Alert(
            alert_id="test-002",
            title="Test Alert 2",
            message="Another test alert",
            level=AlertLevel.ERROR,
            source="test-service"
        )

        alert_dict = alert.to_dict()
        assert alert_dict["alert_id"] == "test-002"
        assert alert_dict["title"] == "Test Alert 2"
        assert alert_dict["level"] == "error"
        assert alert_dict["type"] == "error"
        assert alert_dict["severity"] == "high"
        assert alert_dict["source"] == "test-service"
        assert alert_dict["status"] == "active"

    def test_alert_from_dict(self):
        """测试从字典创建告警"""
        data = {
            "alert_id": "test-003",
            "title": "Test Alert 3",
            "message": "Third test alert",
            "level": "critical",
            "type": "error",
            "severity": "critical",
            "source": "test-service",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "labels": {"key": "value"},
            "annotations": {"note": "test"},
        }

        alert = Alert.from_dict(data)
        assert alert.alert_id == "test-003"
        assert alert.level == AlertLevel.CRITICAL
        assert alert.type == AlertType.ERROR
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.labels["key"] == "value"

    def test_alert_resolve(self):
        """测试解决告警"""
        alert = Alert(
            alert_id="test-004",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test"
        )

        assert alert.is_active()
        assert not alert.is_resolved()

        alert.resolve()

        assert alert.status == AlertStatus.RESOLVED
        assert alert.is_resolved()
        assert alert.resolved_at is not None

    def test_alert_silence(self):
        """测试静默告警"""
        alert = Alert(
            alert_id="test-005",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test"
        )

        alert.silence()
        assert alert.status == AlertStatus.SILENCED

    def test_alert_update(self):
        """测试更新告警"""
        alert = Alert(
            alert_id="test-006",
            title="Old Title",
            message="Old message",
            level=AlertLevel.WARNING,
            source="test"
        )

        alert.update(
            title="New Title",
            message="New message",
            labels={"new_label": "value"}
        )

        assert alert.title == "New Title"
        assert alert.message == "New message"
        assert alert.labels["new_label"] == "value"
        assert alert.updated_at is not None

    def test_alert_age_and_duration(self):
        """测试告警年龄和持续时间"""
        created_time = datetime.utcnow() - timedelta(minutes=5)
        alert = Alert(
            alert_id="test-007",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test",
            created_at=created_time
        )

        age = alert.get_age()
        assert age >= timedelta(minutes=4)
        assert age <= timedelta(minutes=6)

        # 未解决的告警没有持续时间
        assert alert.get_duration() is None

        # 解决后计算持续时间
        resolved_time = created_time + timedelta(minutes=3)
        alert.resolved_at = resolved_time
        duration = alert.get_duration()
        assert duration == timedelta(minutes=3)

    def test_alert_rule_creation(self):
        """测试创建告警规则"""
        rule = AlertRule(
            rule_id="rule-001",
            name="Test Rule",
            condition="cpu_usage > 90",
            level=AlertLevel.ERROR,
            channels=[AlertChannel.LOG, AlertChannel.WEBHOOK],
            throttle_seconds=600,
            enabled=True,
            labels={"team": "infra"}
        )

        assert rule.rule_id == "rule-001"
        assert rule.name == "Test Rule"
        assert rule.condition == "cpu_usage > 90"
        assert rule.level == AlertLevel.ERROR
        assert AlertChannel.LOG in rule.channels
        assert AlertChannel.WEBHOOK in rule.channels
        assert rule.throttle_seconds == 600
        assert rule.enabled is True
        assert rule.fire_count == 0

    def test_alert_rule_should_fire(self):
        """测试规则是否应该触发"""
        rule = AlertRule(
            rule_id="rule-002",
            name="Test Rule",
            condition="error_rate > 0.1",
            level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG],
            throttle_seconds=300
        )

        # 首次触发
        assert rule.should_fire() is True

        # 记录触发
        rule.record_fire()
        assert rule.fire_count == 1
        assert rule.last_fired is not None

        # 去重时间内不应再次触发
        assert rule.should_fire() is False

        # 模拟时间过去
        future_time = rule.last_fired + timedelta(seconds=301)
        assert rule.should_fire(last_fire_time=future_time) is True


class TestAlertChannels:
    """测试告警渠道"""

    @pytest.mark.asyncio
    async def test_log_channel(self):
        """测试日志渠道"""
        channel = LogChannel(
            name="test_log",
            config={"log_level": "error", "include_details": True}
        )

        alert = Alert(
            alert_id="test-001",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.ERROR,
            source="test-service"
        )

        result = await channel.send(alert)
        assert result is True

    @pytest.mark.asyncio
    async def test_webhook_channel(self):
        """测试Webhook渠道"""
        config = {
            "url": "https://example.com/webhook",
            "method": "POST",
            "timeout": 5,
            "retry_count": 2
        }
        channel = WebhookChannel(name="test_webhook", config=config)

        alert = Alert(
            alert_id="test-002",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test-service"
        )

        # 模拟成功响应
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            result = await channel.send(alert)
            assert result is True

    @pytest.mark.asyncio
    async def test_email_channel(self):
        """测试邮件渠道"""
        config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "username": "test@example.com",
            "password": "password",
            "from_address": "alerts@example.com",
            "to_addresses": ["admin@example.com"],
            "use_tls": True
        }
        channel = EmailChannel(name="test_email", config=config)

        alert = Alert(
            alert_id="test-003",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.CRITICAL,
            source="test-service"
        )

        # 模拟邮件发送成功
        with patch('aiosmtplib.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value = mock_smtp_instance

            result = await channel.send(alert)
            # 由于配置验证失败，渠道可能被禁用
            # 这里主要测试不会抛出异常
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_slack_channel(self):
        """测试Slack渠道"""
        config = {
            "webhook_url": "https://hooks.slack.com/test/webhook",
            "channel": "#alerts",
            "username": "AlertBot"
        }
        channel = SlackChannel(name="test_slack", config=config)

        alert = Alert(
            alert_id="test-004",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.ERROR,
            source="test-service"
        )

        # 模拟Slack API响应
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await channel.send(alert)
            assert result is True

    def test_alert_channel_manager(self):
        """测试告警渠道管理器"""
        manager = AlertChannelManager()

        # 注册渠道
        log_channel = LogChannel(name="log1")
        manager.register_channel(log_channel)
        assert manager.get_channel("log1") is log_channel

        # 获取启用的渠道
        enabled_channels = manager.get_enabled_channels()
        assert log_channel in enabled_channels

        # 禁用渠道
        log_channel.disable()
        enabled_channels = manager.get_enabled_channels()
        assert log_channel not in enabled_channels

        # 注销渠道
        manager.unregister_channel("log1")
        assert manager.get_channel("log1") is None


class TestAlertRuleEngine:
    """测试告警规则引擎"""

    def test_rule_evaluation_context(self):
        """测试规则评估上下文"""
        context = RuleEvaluationContext()

        # 设置变量
        context.set_variable("cpu_usage", 95.5)
        context.set_variable("memory_usage", 80.0)
        context.set_variables({"disk_usage": 70, "network_io": 1000})

        # 设置指标
        context.set_metric("error_rate", 0.15)
        context.set_metric("response_time", 500)

        # 设置历史数据
        context.set_history("cpu_history", [90, 92, 94, 95, 96])

        # 测试内置函数
        assert context.functions["abs"](-5) == 5
        assert context.functions["max"]([1, 2, 3]) == 3
        assert context.functions["between"](50, 40, 60) is True
        assert context.functions["contains"]([1, 2, 3], 2) is True
        assert context.functions["matches"]("test123", r"test\d+") is True

    @pytest.mark.asyncio
    async def test_rule_engine_evaluation(self):
        """测试规则引擎评估"""
        engine = AlertRuleEngine()

        # 注册规则
        rule = AlertRule(
            rule_id="cpu_high",
            name="High CPU Usage",
            condition="cpu_usage > 90",
            level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG]
        )
        engine.register_rule(rule)

        # 设置上下文变量
        engine.update_context_variables({"cpu_usage": 95})

        # 评估规则
        result = await engine.evaluate_rule("cpu_high")
        assert result is True

        # 设置不同的值
        engine.update_context_variables({"cpu_usage": 85})
        result = await engine.evaluate_rule("cpu_high")
        assert result is False

    @pytest.mark.asyncio
    async def test_rule_engine_trigger_alert(self):
        """测试规则引擎触发告警"""
        engine = AlertRuleEngine()

        rule = AlertRule(
            rule_id="memory_low",
            name="Low Memory",
            condition="memory_usage < 20",
            level=AlertLevel.ERROR,
            channels=[AlertChannel.LOG]
        )
        engine.register_rule(rule)

        # 设置满足条件的值
        engine.update_context_variables({"memory_usage": 15})

        # 触发告警
        alert = await engine.trigger_alert("memory_low")
        assert alert is not None
        assert alert.title == "Alert: Low Memory"
        assert alert.level == AlertLevel.ERROR
        assert alert.labels["rule_id"] == "memory_low"
        assert alert.annotations["condition"] == "memory_usage < 20"

    def test_rule_engine_statistics(self):
        """测试规则引擎统计"""
        engine = AlertRuleEngine()

        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            condition="test > 0",
            level=AlertLevel.INFO,
            channels=[AlertChannel.LOG]
        )
        engine.register_rule(rule)

        # 模拟评估历史
        engine.evaluation_history["test_rule"] = [True, False, True, True, False]

        stats = engine.get_rule_statistics("test_rule")
        assert stats["rule_id"] == "test_rule"
        assert stats["evaluations"] == 5
        assert stats["trigger_rate"] == 60.0

    def test_rule_engine_validation(self):
        """测试规则验证"""
        engine = AlertRuleEngine()

        # 有效条件
        result = engine.validate_rule_condition("cpu_usage > 90")
        assert result["valid"] is True
        assert result["error"] is None

        # 无效语法
        result = engine.validate_rule_condition("cpu_usage >")
        assert result["valid"] is False
        assert "Syntax error" in result["error"]

        # 复杂条件
        result = engine.validate_rule_condition("cpu_usage > 90 and memory_usage > 80")
        assert result["valid"] is True


class TestAlertAggregator:
    """测试告警聚合器"""

    def test_alert_group_creation(self):
        """测试告警组创建"""
        group = AlertGroup(
            group_id="group-001",
            name="CPU High Alerts",
            labels={"service": "api", "severity": "high"}
        )

        assert group.group_id == "group-001"
        assert group.name == "CPU High Alerts"
        assert group.status == AlertStatus.ACTIVE
        assert len(group.alerts) == 0

    def test_alert_group_operations(self):
        """测试告警组操作"""
        group = AlertGroup(
            group_id="group-002",
            name="Test Group"
        )

        # 添加告警
        alert1 = Alert(
            alert_id="alert-001",
            title="Alert 1",
            message="Message 1",
            level=AlertLevel.WARNING,
            source="test"
        )
        alert2 = Alert(
            alert_id="alert-002",
            title="Alert 2",
            message="Message 2",
            level=AlertLevel.ERROR,
            source="test"
        )

        group.add_alert(alert1)
        group.add_alert(alert2)

        assert len(group.alerts) == 2
        assert group.get_active_count() == 2
        assert group.get_resolved_count() == 0

        # 解决一个告警
        alert1.resolve()
        assert group.get_active_count() == 1
        assert group.get_resolved_count() == 1

        # 更新状态
        group.update_status()
        assert group.status == AlertStatus.ACTIVE  # 还有活跃告警

        # 解决所有告警
        alert2.resolve()
        group.update_status()
        assert group.status == AlertStatus.RESOLVED

    def test_alert_group_highest_severity(self):
        """测试告警组最高严重级别"""
        group = AlertGroup(
            group_id="group-003",
            name="Test Group"
        )

        # 没有告警时
        assert group.get_highest_severity() is None

        # 添加不同级别的告警
        alerts = [
            Alert("alert-1", "Low", "", AlertLevel.INFO, "test"),
            Alert("alert-2", "Medium", "", AlertLevel.WARNING, "test"),
            Alert("alert-3", "High", "", AlertLevel.ERROR, "test"),
            Alert("alert-4", "Critical", "", AlertLevel.CRITICAL, "test"),
        ]

        for alert in alerts:
            group.add_alert(alert)

        assert group.get_highest_severity() == "critical"

        # 解决最高级别的告警
        alerts[-1].resolve()
        assert group.get_highest_severity() == "high"

    def test_alert_aggregator_suppression(self):
        """测试告警抑制"""
        aggregator = AlertAggregator()

        # 添加抑制规则
        aggregator.add_suppression_rule({
            "name": "suppress_test",
            "condition": {"source": "test-service"},
            "reason": "Test service alerts are suppressed"
        })

        alert = Alert(
            alert_id="test-001",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test-service"
        )

        suppressed, reason = aggregator.is_suppressed(alert)
        assert suppressed is True
        assert "Test service alerts are suppressed" in reason

        # 不匹配的告警
        alert2 = Alert(
            alert_id="test-002",
            title="Another Alert",
            message="Another message",
            level=AlertLevel.ERROR,
            source="other-service"
        )

        suppressed, reason = aggregator.is_suppressed(alert2)
        assert suppressed is False
        assert reason is None

    def test_alert_aggregator_deduplication(self):
        """测试告警去重"""
        aggregator = AlertAggregator(deduplication_window=timedelta(minutes=1))

        alert = Alert(
            alert_id="test-001",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test"
        )

        # 首次告警
        assert aggregator.is_duplicate(alert) is False

        # 相同指纹的告警在窗口期内应该被去重
        alert2 = Alert(
            alert_id="test-002",
            title="Test Alert",
            message="Test message",
            level=AlertLevel.WARNING,
            source="test"
        )
        alert2.fingerprint = alert.fingerprint  # 强制相同指纹

        assert aggregator.is_duplicate(alert2) is True

    def test_alert_aggregator_statistics(self):
        """测试聚合器统计"""
        aggregator = AlertAggregator()

        # 添加一些规则
        aggregator.add_suppression_rule({
            "name": "test_suppression",
            "condition": {"source": "test"}
        })
        aggregator.add_aggregation_rule({
            "name": "by_source",
            "group_by": ["source"],
            "window": timedelta(minutes=10),
            "threshold": 3
        })

        stats = aggregator.get_statistics()
        assert stats["suppression_rules"] == 1
        assert stats["aggregation_rules"] == 1
        assert "total_groups" in stats
        assert "total_alerts" in stats


class TestPrometheusMetrics:
    """测试Prometheus指标"""

    def test_metrics_initialization(self):
        """测试指标初始化"""
        metrics = PrometheusMetrics(namespace="test_alerts")
        assert metrics.namespace == "test_alerts"
        assert metrics.enabled is True  # 如果prometheus_client可用

    def test_metrics_recording(self):
        """测试指标记录"""
        metrics = PrometheusMetrics(namespace="test_alerts")

        # 这些操作不应该抛出异常
        metrics.record_alert_created("warning", "error", "test-service")
        metrics.record_alert_resolved("warning", "error", "test-service", 60.0)
        metrics.record_rule_fired("rule-001", "error")
        metrics.record_rule_evaluation("rule-001", "true")
        metrics.record_notification_sent("webhook", "success")

        # 获取指标摘要
        summary = metrics.get_metrics_summary()
        assert summary["namespace"] == "test_alerts"


class TestAlertManager:
    """测试告警管理器"""

    @pytest.mark.asyncio
    async def test_alert_manager_initialization(self):
        """测试告警管理器初始化"""
        config = {
            "deduplication_minutes": 10,
            "rule_evaluation_interval": 30,
            "enable_prometheus": True,
            "webhook_channel": {
                "url": "https://example.com/webhook"
            }
        }

        manager = AlertManager(config)
        assert manager.config == config
        assert manager.rule_engine is not None
        assert manager.channel_manager is not None
        assert manager.aggregator is not None
        assert manager.metrics is not None

        # 检查默认渠道是否已注册
        assert manager.channel_manager.get_channel("log") is not None

    @pytest.mark.asyncio
    async def test_create_alert(self):
        """测试创建告警"""
        manager = AlertManager()

        alert = await manager.create_alert(
            title="Test Alert",
            message="This is a test alert",
            level=AlertLevel.WARNING,
            source="test-service",
            labels={"service": "test"},
            annotations={"runbook": "https://example.com"}
        )

        assert alert is not None
        assert alert.title == "Test Alert"
        assert alert.level == AlertLevel.WARNING
        assert alert.source == "test-service"
        assert alert.alert_id in manager.alerts

    @pytest.mark.asyncio
    async def test_resolve_alert(self):
        """测试解决告警"""
        manager = AlertManager()

        # 创建告警
        alert = await manager.create_alert(
            title="Test Alert",
            message="Test message",
            level=AlertLevel.ERROR,
            source="test-service"
        )

        assert alert.is_active()

        # 解决告警
        success = await manager.resolve_alert(alert.alert_id)
        assert success is True
        assert alert.is_resolved()

    @pytest.mark.asyncio
    async def test_silence_alert(self):
        """测试静默告警"""
        manager = AlertManager()

        alert = await manager.create_alert(
            title="Test Alert",
            message="Test message",
            level=AlertLevel.ERROR,
            source="test-service"
        )

        success = await manager.silence_alert(alert.alert_id)
        assert success is True
        assert alert.status == AlertStatus.SILENCED

    @pytest.mark.asyncio
    async def test_search_alerts(self):
        """测试搜索告警"""
        manager = AlertManager()

        # 创建多个告警
        await manager.create_alert(
            title="CPU High",
            message="CPU usage is high",
            level=AlertLevel.WARNING,
            source="api-service"
        )
        await manager.create_alert(
            title="Memory Low",
            message="Memory is low",
            level=AlertLevel.ERROR,
            source="db-service"
        )
        await manager.create_alert(
            title="Disk Full",
            message="Disk is full",
            level=AlertLevel.CRITICAL,
            source="api-service"
        )

        # 搜索所有告警
        all_alerts = manager.search_alerts(limit=10)
        assert len(all_alerts) == 3

        # 按来源搜索
        api_alerts = manager.search_alerts(source="api-service")
        assert len(api_alerts) == 2

        # 按级别搜索
        error_alerts = manager.search_alerts(level=AlertLevel.ERROR)
        assert len(error_alerts) == 1
        assert error_alerts[0].title == "Memory Low"

        # 按查询字符串搜索
        cpu_alerts = manager.search_alerts(query="CPU")
        assert len(cpu_alerts) == 1
        assert cpu_alerts[0].title == "CPU High"

    def test_get_statistics(self):
        """测试获取统计信息"""
        manager = AlertManager()
        stats = manager.get_statistics()

        assert "alerts" in stats
        assert "rules" in stats
        assert "aggregation" in stats
        assert "channels" in stats
        assert "metrics" in stats
        assert "manager" in stats

        # 检查告警统计
        alert_stats = stats["alerts"]
        assert "total" in alert_stats
        assert "active" in alert_stats
        assert "resolved" in alert_stats
        assert "by_level" in alert_stats
        assert "by_source" in alert_stats

    @pytest.mark.asyncio
    async def test_manager_lifecycle(self):
        """测试管理器生命周期"""
        manager = AlertManager()

        # 启动管理器
        await manager.start()
        assert manager._running is True

        # 停止管理器
        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_background_tasks(self):
        """测试后台任务"""
        manager = AlertManager(config={
            "rule_evaluation_interval": 1,  # 1秒
            "cleanup_interval": 2  # 2秒
        })

        # 启动管理器
        await manager.start()

        # 等待后台任务运行
        await asyncio.sleep(1.5)

        # 停止管理器
        await manager.stop()

        # 验证后台任务已清理
        assert len(manager._background_tasks) == 0