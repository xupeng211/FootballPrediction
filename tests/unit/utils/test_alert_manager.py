# TODO: Consider creating a fixture for 8 repeated Mock creations

# TODO: Consider creating a fixture for 8 repeated Mock creations

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.monitoring.alert_manager import AlertManager, AlertSeverity, AlertType

"""
监控模块测试 - 告警管理器
"""


@pytest.mark.unit
class TestAlertManager:
    """AlertManager测试"""

    @pytest.fixture
    def alert_manager(self):
        """创建告警管理器实例"""
        manager = AlertManager()
        manager.logger = MagicMock()
        return manager

    @pytest.fixture
    def sample_alert(self):
        """创建示例告警"""
        return {
            "id": "alert-12345",
            "type": AlertType.ERROR,
            "severity": AlertSeverity.HIGH,
            "message": "Database connection failed",
            "source": "database",
            "timestamp": datetime.now(),
            "metadata": {"error_code": "DB_CONN_ERROR", "retry_count": 3},
        }

    def test_alert_manager_initialization(self, alert_manager):
        """测试告警管理器初始化"""
        assert alert_manager is not None
        assert alert_manager.logger is not None
        assert hasattr(alert_manager, "active_alerts")
        assert hasattr(alert_manager, "alert_history")

    def test_create_alert(self, alert_manager):
        """测试创建告警"""
        alert = alert_manager.create_alert(
            type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            message="Test error",
            source="test",
        )

        assert alert["type"] == AlertType.ERROR
        assert alert["severity"] == AlertSeverity.HIGH
        assert alert["message"] == "Test error"
        assert alert["source"] == "test"
        assert "id" in alert
        assert "timestamp" in alert

    def test_alert_severity_levels(self):
        """测试告警严重级别"""
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_alert_types(self):
        """测试告警类型"""
        assert AlertType.ERROR.value == "error"
        assert AlertType.WARNING.value == "warning"
        assert AlertType.INFO.value == "info"
        assert AlertType.SYSTEM.value == "system"

    @pytest.mark.asyncio
    async def test_send_alert(self, alert_manager, sample_alert):
        """测试发送告警"""
        mock_notifier = AsyncMock()
        mock_notifier.send.return_value = True

        alert_manager.notifiers = [mock_notifier]

        _result = await alert_manager.send_alert(sample_alert)

        assert _result is True
        mock_notifier.send.assert_called_once_with(sample_alert)

    @pytest.mark.asyncio
    async def test_send_alert_multiple_notifiers(self, alert_manager, sample_alert):
        """测试发送告警到多个通知器"""
        mock_email_notifier = AsyncMock()
        mock_slack_notifier = AsyncMock()
        mock_pagerduty_notifier = AsyncMock()

        alert_manager.notifiers = [
            mock_email_notifier,
            mock_slack_notifier,
            mock_pagerduty_notifier,
        ]

        _result = await alert_manager.send_alert(sample_alert)

        assert _result is True
        mock_email_notifier.send.assert_called_once()
        mock_slack_notifier.send.assert_called_once()
        mock_pagerduty_notifier.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_failure(self, alert_manager, sample_alert):
        """测试发送告警失败"""
        mock_notifier = AsyncMock()
        mock_notifier.send.side_effect = Exception("Failed to send")

        alert_manager.notifiers = [mock_notifier]

        _result = await alert_manager.send_alert(sample_alert)

        assert _result is False
        alert_manager.logger.error.assert_called()

    def test_add_alert_to_active(self, alert_manager, sample_alert):
        """测试添加告警到活跃列表"""
        alert_manager.add_alert(sample_alert)

        assert len(alert_manager.active_alerts) == 1
        assert alert_manager.active_alerts[0]["id"] == sample_alert["id"]

    def test_remove_alert_from_active(self, alert_manager, sample_alert):
        """测试从活跃列表移除告警"""
        alert_manager.add_alert(sample_alert)
        alert_manager.remove_alert(sample_alert["id"])

        assert len(alert_manager.active_alerts) == 0

    def test_acknowledge_alert(self, alert_manager, sample_alert):
        """测试确认告警"""
        alert_manager.add_alert(sample_alert)

        alert = alert_manager.acknowledge_alert(
            sample_alert["id"], acknowledged_by="test_user"
        )

        assert alert["acknowledged"] is True
        assert alert["acknowledged_by"] == "test_user"
        assert "acknowledged_at" in alert

    def test_get_active_alerts(self, alert_manager):
        """测试获取活跃告警"""
        # 添加多个告警
        for i in range(5):
            alert = alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.HIGH,
                message=f"Error {i}",
                source="test",
            )
            alert_manager.add_alert(alert)

        active_alerts = alert_manager.get_active_alerts()

        assert len(active_alerts) == 5
        assert all(
            alert["id"] in [a["id"] for a in active_alerts]
            for alert in alert_manager.active_alerts
        )

    def test_get_alerts_by_severity(self, alert_manager):
        """测试按严重级别获取告警"""
        # 添加不同严重级别的告警
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.LOW,
                message="Low severity",
                source="test",
            )
        )
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.HIGH,
                message="High severity",
                source="test",
            )
        )
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.HIGH,
                message="Another high severity",
                source="test",
            )
        )

        high_alerts = alert_manager.get_alerts_by_severity(AlertSeverity.HIGH)
        low_alerts = alert_manager.get_alerts_by_severity(AlertSeverity.LOW)

        assert len(high_alerts) == 2
        assert len(low_alerts) == 1

    def test_get_alerts_by_type(self, alert_manager):
        """测试按类型获取告警"""
        # 添加不同类型的告警
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.HIGH,
                message="Error message",
                source="test",
            )
        )
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.WARNING,
                severity=AlertSeverity.MEDIUM,
                message="Warning message",
                source="test",
            )
        )
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.LOW,
                message="Another error",
                source="test",
            )
        )

        error_alerts = alert_manager.get_alerts_by_type(AlertType.ERROR)
        warning_alerts = alert_manager.get_alerts_by_type(AlertType.WARNING)

        assert len(error_alerts) == 2
        assert len(warning_alerts) == 1

    def test_archive_old_alerts(self, alert_manager):
        """测试归档旧告警"""
        # 添加告警
        old_alert = alert_manager.create_alert(
            type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            message="Old alert",
            source="test",
        )
        # 手动设置旧时间戳 (使用UTC时间)
        old_alert["timestamp"] = datetime.utcnow() - timedelta(hours=25)

        recent_alert = alert_manager.create_alert(
            type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            message="Recent alert",
            source="test",
        )

        alert_manager.add_alert(old_alert)
        alert_manager.add_alert(recent_alert)

        # 归档24小时前的告警
        archived_count = alert_manager.archive_old_alerts(hours=24)

        assert archived_count == 1
        assert len(alert_manager.active_alerts) == 1
        assert alert_manager.active_alerts[0]["message"] == "Recent alert"

    def test_check_alert_rate_limiting(self, alert_manager):
        """测试告警频率限制"""
        # 快速创建多个相同类型的告警
        for i in range(10):
            alert = alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.HIGH,
                message="Database error",
                source="database",
            )
            # 检查是否应该发送（使用告警类型作为key，限制10次，窗口60秒）
            should_send = alert_manager.check_rate_limit(
                key="database_error", limit=10, window=60
            )
            if should_send:
                alert_manager._update_rate_limit("database_error", 60)

        # 验证速率限制生效
        assert len(alert_manager.rate_limiter) > 0

    @pytest.mark.asyncio
    async def test_monitor_system_health(self, alert_manager):
        """测试系统健康监控"""
        # Mock系统指标
        mock_metrics = {
            "cpu_usage": 95.5,  # 高CPU使用率
            "memory_usage": 85.2,  # 高内存使用率
            "disk_usage": 50.0,
            "error_rate": 0.1,
        }

        with patch(
            "src.monitoring.alert_manager.get_system_metrics", return_value=mock_metrics
        ):
            alerts_created = await alert_manager.monitor_system_health()

            # 高CPU和内存应该触发告警
            assert len(alerts_created) >= 2

            # 验证告警内容
            cpu_alert = next((a for a in alerts_created if "CPU" in a["message"]), None)
            memory_alert = next(
                (a for a in alerts_created if "memory" in a["message"].lower()), None
            )

            assert cpu_alert is not None
            assert memory_alert is not None
            assert cpu_alert["severity"] == AlertSeverity.HIGH
            assert memory_alert["severity"] == AlertSeverity.HIGH

    @pytest.mark.asyncio
    async def test_monitor_database_connection(self, alert_manager):
        """测试数据库连接监控"""
        # Mock数据库检查失败
        with patch(
            "src.monitoring.alert_manager.check_database_health", return_value=False
        ):
            alert = await alert_manager.check_database_connection()

            assert alert is not None
            assert alert["type"] == AlertType.ERROR
            assert alert["severity"] == AlertSeverity.CRITICAL
            assert "database" in alert["message"].lower()

    @pytest.mark.asyncio
    async def test_monitor_api_response_time(self, alert_manager):
        """测试API响应时间监控"""
        # Mock慢响应时间
        mock_response_time = 5.5  # 5.5秒

        with patch(
            "src.monitoring.alert_manager.get_api_response_time",
            return_value=mock_response_time,
        ):
            alert = await alert_manager.check_api_response_time()

            assert alert is not None
            assert alert["type"] == AlertType.WARNING
            assert alert["severity"] == AlertSeverity.MEDIUM
            assert "response time" in alert["message"].lower()

    def test_alert_aggregation(self, alert_manager):
        """测试告警聚合"""
        # 创建多个相似的告警
        similar_alerts = []
        for i in range(5):
            alert = alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.HIGH,
                message="Database connection failed",
                source="database",
                _metadata={"error_code": "DB_CONN_ERROR"},
            )
            similar_alerts.append(alert)

        # 聚合告警
        aggregated = alert_manager.aggregate_alerts(similar_alerts)

        assert aggregated["count"] == 5
        assert aggregated["message"] == "Database connection failed (5 occurrences)"
        assert aggregated["aggregated"] is True

    def test_alert_suppression_rules(self, alert_manager):
        """测试告警抑制规则"""
        # 创建告警
        alert = alert_manager.create_alert(
            type=AlertType.INFO,
            severity=AlertSeverity.LOW,
            message="Info message",
            source="test",
        )

        # 设置抑制规则：低严重级别告警在维护窗口内被抑制
        alert_manager.suppression_rules.append(
            {
                "condition": lambda a: a["severity"] == AlertSeverity.LOW,
                "reason": "maintenance_window",
            }
        )

        should_suppress = alert_manager.check_suppression(alert)

        assert should_suppress is True

    @pytest.mark.asyncio
    async def test_send_digest_alert(self, alert_manager):
        """测试发送摘要告警"""
        # 添加多个告警
        alerts = []
        for i in range(5):
            alert = alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.HIGH,
                message=f"Error {i}",
                source="test",
            )
            alerts.append(alert)

        mock_notifier = AsyncMock()
        alert_manager.notifiers = [mock_notifier]

        digest = alert_manager.create_digest(alerts)
        _result = await alert_manager.send_digest(digest)

        assert _result is True
        mock_notifier.send.assert_called_once()

        # 验证摘要内容
        call_args = mock_notifier.send.call_args[0][0]
        assert call_args["type"] == AlertType.SYSTEM
        assert call_args["message"] == "Alert Digest: 5 alerts"
        assert "alerts" in call_args

    def test_get_alert_statistics(self, alert_manager):
        """测试获取告警统计"""
        # 添加不同类型和严重级别的告警
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.HIGH,
                message="Error 1",
                source="test",
            )
        )
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.ERROR,
                severity=AlertSeverity.LOW,
                message="Error 2",
                source="test",
            )
        )
        alert_manager.add_alert(
            alert_manager.create_alert(
                type=AlertType.WARNING,
                severity=AlertSeverity.MEDIUM,
                message="Warning 1",
                source="test",
            )
        )

        stats = alert_manager.get_alert_statistics()

        assert stats["total_alerts"] == 3
        assert stats["by_type"]["error"] == 2
        assert stats["by_type"]["warning"] == 1
        assert stats["by_severity"]["high"] == 1
        assert stats["by_severity"]["medium"] == 1
        assert stats["by_severity"]["low"] == 1

    @pytest.mark.asyncio
    async def test_auto_resolve_alerts(self, alert_manager):
        """测试自动解决告警"""
        # 创建告警
        alert = alert_manager.create_alert(
            type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            message="Service down",
            source="service",
        )
        alert_manager.add_alert(alert)

        # Mock服务恢复检查
        with patch(
            "src.monitoring.alert_manager.check_service_health", return_value=True
        ):
            resolved = await alert_manager.auto_resolve_alerts()

            assert len(resolved) == 1
            assert resolved[0]["id"] == alert["id"]
            assert resolved[0]["status"] == "resolved"

    def test_alert_export_format(self, alert_manager, sample_alert):
        """测试告警导出格式"""
        alert_manager.add_alert(sample_alert)

        # 导出为JSON
        json_export = alert_manager.export_alerts(format="json")
        exported_data = json.loads(json_export)

        assert len(exported_data["active_alerts"]) == 1
        assert exported_data["active_alerts"][0]["id"] == sample_alert["id"]

        # 导出为CSV
        csv_export = alert_manager.export_alerts(format="csv")
        assert "id,type,severity,message" in csv_export
        assert sample_alert["id"] in csv_export

    @pytest.mark.asyncio
    async def test_test_alert_system(self, alert_manager):
        """测试告警系统测试"""
        mock_notifier = AsyncMock()
        mock_notifier.send.return_value = True
        alert_manager.notifiers = [mock_notifier]

        test_result = await alert_manager.test_alert_system()

        assert test_result["success"] is True
        assert "test_alert_sent_at" in test_result
        mock_notifier.send.assert_called()

        # 验证测试告警内容
        call_args = mock_notifier.send.call_args[0][0]
        assert call_args["type"] == AlertType.SYSTEM
        assert "test" in call_args["message"].lower()
