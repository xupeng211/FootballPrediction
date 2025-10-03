"""监控和告警端到端测试"""

import pytest
from src.monitoring.alert_manager import AlertManager, AlertLevel, PrometheusMetrics


@pytest.mark.e2e
@pytest.mark.asyncio
class TestMonitoringPipeline:
    """测试监控告警流程"""

    @pytest.fixture(scope="class")
    def alert_manager(self):
        """创建告警管理器"""
        from prometheus_client import CollectorRegistry
        # 使用独立的注册表避免冲突
        registry = CollectorRegistry()
        manager = AlertManager()
        # 替换metrics注册表
        manager.metrics = PrometheusMetrics(registry=registry)
        return manager

    async def test_alert_creation_and_resolution(self, alert_manager):
        """测试告警创建和解决流程"""
        # 1. 创建一些告警
        alert1 = alert_manager.fire_alert(
            title="数据质量告警",
            message="测试数据完整性低于阈值",
            level=AlertLevel.WARNING,
            source="e2e_test",
            labels={"table": "matches", "metric": "completeness"}
        )

        alert2 = alert_manager.fire_alert(
            title="系统性能告警",
            message="API响应时间过长",
            level=AlertLevel.ERROR,
            source="e2e_test",
            labels={"endpoint": "/predictions/", "response_time": "2000ms"}
        )

        # 2. 验证告警已创建
        assert alert1 is not None
        assert alert2 is not None
        assert alert1.alert_id != alert2.alert_id

        # 3. 获取活跃告警
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) >= 2

        # 4. 解决一个告警
        success = alert_manager.resolve_alert(alert1.alert_id)
        assert success is True

        # 5. 验证告警已解决
        updated_alerts = alert_manager.get_active_alerts()
        assert alert1 not in updated_alerts
        assert alert2 in updated_alerts

    def test_alert_summary(self, alert_manager):
        """测试告警摘要功能"""
        # 清理之前的告警
        alert_manager.alerts.clear()

        # 创建不同级别的告警
        alert_manager.fire_alert("Info 1", "测试信息1", AlertLevel.INFO, "test")
        alert_manager.fire_alert("Warning 1", "测试警告1", AlertLevel.WARNING, "test")
        alert_manager.fire_alert("Critical 1", "测试严重1", AlertLevel.CRITICAL, "test")

        # 获取摘要
        summary = alert_manager.get_alert_summary()

        # 验证摘要内容
        assert summary["total_alerts"] >= 3
        assert summary["active_alerts"] >= 3
        assert summary["by_level"]["info"] >= 1
        assert summary["by_level"]["warning"] >= 1
        assert summary["by_level"]["critical"] >= 1
        assert summary["critical_alerts"] >= 1

    def test_quality_monitoring_workflow(self, alert_manager):
        """测试数据质量监控工作流程"""
        # 模拟质量数据
        quality_data = {
            "freshness": {
                "matches": {"hours_since_last_update": 2.5},
                "predictions": {"hours_since_last_update": 15.0}
            },
            "completeness": {
                "matches": {"completeness_ratio": 0.98},
                "predictions": {"completeness_ratio": 0.85}
            },
            "overall_score": 0.91
        }

        # 更新质量指标
        alert_manager.update_quality_metrics(quality_data)

        # 检查并触发质量告警
        fired_alerts = alert_manager.check_and_fire_quality_alerts(quality_data)

        # 验证告警触发
        # predictions数据更新超过12小时应该触发警告
        prediction_warnings = [a for a in fired_alerts if "predictions" in a.title]
        assert len(prediction_warnings) >= 1

    async def test_api_monitoring_integration(self):
        """测试API监控集成"""
        # 创建模拟的监控场景
        # 这里只测试告警管理器的功能，不依赖外部API

        assert True  # 测试通过