#!/usr/bin/env python3
"""
安全仪表板测试
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

try:
    from src.security.security_automation import get_automation_engine
    from src.security.security_dashboard import (
        SecurityDashboardData,
        get_security_dashboard,
    )
    from src.security.security_monitor import (
        SecurityEventType,
        ThreatLevel,
        get_security_monitor,
    )
except ImportError as e:
    print(f"Warning: Could not import security dashboard modules: {e}")
    pytest.skip("安全仪表板模块不可用", allow_module_level=True)


@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityDashboardData:
    """安全仪表板数据测试"""

    @pytest.fixture
    def dashboard(self):
        """仪表板实例"""
        return SecurityDashboardData()

    async def test_get_dashboard_overview(self, dashboard):
        """测试获取仪表板概览"""
        # Mock监控和自动化引擎数据
        mock_monitor = Mock()
        mock_monitor.get_security_dashboard.return_value = {
            "summary": {
                "total_events_24h": 150,
                "blocked_ips": 25,
                "auto_responses": 120,
                "critical_threats": 5,
                "high_threats": 45,
            },
            "threat_distribution": {"low": 80, "medium": 50, "high": 45, "critical": 5},
            "type_distribution": {
                "auth_failure": 60,
                "injection": 30,
                "xss": 15,
                "brute_force": 25,
            },
            "geo_distribution": {"CN": 40, "US": 35, "RU": 20, "Other": 55},
            "blocked_ips_list": [],
            "recent_events": [],
        }

        mock_automation = Mock()
        mock_automation.get_automation_status.return_value = {
            "enabled_rules": 8,
            "total_rules": 10,
            "executions_24h": 85,
            "successful_executions_24h": 80,
            "failed_executions_24h": 5,
            "recent_executions": [],
        }

        with (
            patch(
                "src.security.security_dashboard.get_security_monitor",
                return_value=mock_monitor,
            ),
            patch(
                "src.security.security_dashboard.get_automation_engine",
                return_value=mock_automation,
            ),
            patch.object(dashboard, "_calculate_threat_trend", return_value={}),
            patch.object(dashboard, "_generate_threat_intelligence", return_value={}),
            patch.object(dashboard, "_get_system_health", return_value={}),
            patch.object(dashboard, "_generate_recommendations", return_value=[]),
        ):

            overview = await dashboard.get_dashboard_overview("24h")

            # 验证基本结构
            assert "timestamp" in overview
            assert "time_range" in overview
            assert "summary" in overview
            assert "threat_trend" in overview
            assert "threat_intelligence" in overview
            assert "automation_status" in overview
            assert "system_health" in overview
            assert "recommendations" in overview

            # 验证数据内容
            assert overview["time_range"] == "24h"
            assert overview["summary"]["total_events_24h"] == 150
            assert overview["automation_status"]["enabled_rules"] == 8
            assert overview["automation_status"]["total_rules"] == 10

    async def test_get_real_time_alerts(self, dashboard):
        """测试获取实时告警"""
        # 创建一些高危事件
        now = datetime.now()
        mock_events = []

        for i in range(5):
            event = Mock()
            event.event_id = f"alert_{i}"
            event.event_type = SecurityEventType.INJECTION_ATTEMPT
            event.threat_level = ThreatLevel.HIGH if i < 2 else ThreatLevel.CRITICAL
            event.timestamp = now - timedelta(minutes=i)
            event.source_ip = f"203.0.113.{10 + i}"
            event.description = f"安全告警 {i+1}"
            event.geo_location = {"country": "CN", "city": "Beijing"}
            event.is_resolved = False
            event.response_action = None
            mock_events.append(event)

        # 模拟监控器事件
        mock_monitor = Mock()
        mock_monitor.events = mock_events

        with patch(
            "src.security.security_dashboard.get_security_monitor",
            return_value=mock_monitor,
        ):
            alerts = await dashboard.get_real_time_alerts()

            # 验证告警结构
            assert len(alerts) == 5
            for alert in alerts:
                assert "id" in alert
                assert "type" in alert
                assert "level" in alert
                assert "timestamp" in alert
                assert "source_ip" in alert
                assert "description" in alert
                assert "resolved" in alert
                assert "actions_taken" in alert

            # 验证高危告警优先级
            critical_alerts = [
                alert for alert in alerts if alert["severity"] == "critical"
            ]
            high_alerts = [alert for alert in alerts if alert["severity"] == "high"]
            assert len(critical_alerts) == 2
            assert len(high_alerts) == 3

    async def test_get_security_metrics(self, dashboard):
        """测试获取安全指标"""
        # 创建测试事件
        now = datetime.now()
        test_events = []

        for i in range(20):
            event = Mock()
            event.event_type = (
                SecurityEventType.INJECTION_ATTEMPT
                if i % 2 == 0
                else SecurityEventType.AUTHENTICATION_FAILURE
            )
            event.threat_level = ThreatLevel.HIGH if i % 3 == 0 else ThreatLevel.MEDIUM
            event.timestamp = now - timedelta(hours=i % 24)
            test_events.append(event)

        # 模拟监控器事件
        mock_monitor = Mock()
        mock_monitor.events = test_events
        mock_monitor.blocked_ips = {"203.0.113.1", "203.0.113.2", "203.0.113.3"}
        mock_monitor.metrics.auto_responses = 15

        with patch(
            "src.security.security_dashboard.get_security_monitor",
            return_value=mock_monitor,
        ):
            metrics = await dashboard.get_security_metrics("24h")

            # 验证指标结构
            assert metrics.total_events == 20
            assert "injection_attempt" in metrics.events_by_type
            assert "auth_failure" in metrics.events_by_type
            assert "high" in metrics.events_by_level
            assert "medium" in metrics.events_by_level
            assert metrics.blocked_ips == 3
            assert metrics.auto_responses == 15
            assert "threat_trend" in metrics.dict()

    async def test_generate_threat_intelligence(self, dashboard):
        """测试生成威胁情报"""
        now = datetime.now()
        test_events = []

        # 创建多样化的测试事件
        for i in range(30):
            event = Mock()
            event.event_type = SecurityEventType.INJECTION_ATTEMPT
            event.timestamp = now - timedelta(days=i % 7)
            event.source_ip = f"203.0.113.{100 + i}"
            event.geo_location = {"country": ["CN", "US", "RU", "JP"][i % 4]}
            test_events.append(event)

        # 模拟监控器事件
        mock_monitor = Mock()
        mock_monitor.events = test_events

        with patch(
            "src.security.security_dashboard.get_security_monitor",
            return_value=mock_monitor,
        ):
            intelligence = await dashboard._generate_threat_intelligence(
                now - timedelta(days=7), now
            )

            # 验证威胁情报结构
            assert "top_attacker_ips" in intelligence
            assert "attack_patterns" in intelligence
            assert "geographic_threats" in intelligence
            assert "emerging_threats" in intelligence

            # 验证攻击者IP列表
            assert len(intelligence["top_attacker_ips"]) <= 10
            for ip_info in intelligence["top_attacker_ips"]:
                assert "ip" in ip_info
                assert "attack_count" in ip_info

            # 验证攻击模式
            assert len(intelligence["attack_patterns"]) > 0
            for pattern in intelligence["attack_patterns"]:
                assert "pattern" in pattern
                assert "count" in pattern
                assert "percentage" in pattern

            # 验证地理威胁
            assert len(intelligence["geographic_threats"]) <= 10
            for geo in intelligence["geographic_threats"]:
                assert "country" in geo
                assert "attack_count" in geo
                assert "percentage" in geo

    async def test_get_system_health(self, dashboard):
        """测试系统健康状态"""
        # 测试健康系统
        mock_monitor = Mock()
        mock_monitor.events = [Mock()]  # 有事件记录

        mock_automation = Mock()
        mock_automation.get_automation_status.return_value = {
            "enabled_rules": 5,
            "total_rules": 5,
        }

        with (
            patch(
                "src.security.security_dashboard.get_security_monitor",
                return_value=mock_monitor,
            ),
            patch(
                "src.security.security_dashboard.get_automation_engine",
                return_value=mock_automation,
            ),
            patch(
                "src.security.security_dashboard.datetime",
                side_effect=lambda x: now,
                autospec=True,
            ),
        ):

            health = await dashboard._get_system_health()

            # 验证健康状态结构
            assert "overall_status" in health
            assert "health_score" in health
            assert "components" in health
            assert "last_check" in health

            # 验证组件状态
            components = health["components"]
            assert "security_monitor" in components
            assert "automation_engine" in components
            assert "threat_detection" in components

            # 验证健康评分
            assert 0 <= health["health_score"] <= 100
            assert health["overall_status"] in [
                "excellent",
                "good",
                "warning",
                "critical",
                "error",
            ]

    async def test_generate_recommendations(self, dashboard):
        """测试生成安全建议"""
        # 测试正常状态
        with patch.object(
            dashboard,
            "_get_system_health",
            return_value={
                "overall_status": "good",
                "health_score": 85,
                "components": {},
            },
        ):
            recommendations = await dashboard._generate_recommendations()
            assert len(recommendations) > 0
            assert all("type" in rec for rec in recommendations)
            assert all("title" in rec for rec in recommendations)
            assert all("description" in rec for rec in recommendations)
            assert all("action" in rec for rec in recommendations)

        # 测试警告状态
        with patch.object(
            dashboard,
            "_get_system_health",
            return_value={
                "overall_status": "warning",
                "health_score": 60,
                "components": {},
            },
        ):
            recommendations = await dashboard._generate_recommendations()
            assert len(recommendations) > 0
            warning_types = [rec for rec in recommendations if rec["type"] == "warning"]
            assert len(warning_types) > 0

        # 测试严重状态
        with patch.object(
            dashboard,
            "_get_system_health",
            return_value={
                "overall_status": "critical",
                "health_score": 30,
                "components": {},
            },
        ):
            recommendations = await dashboard._generate_recommendations()
            critical_types = [
                rec for rec in recommendations if rec["type"] == "critical"
            ]
            assert len(critical_types) > 0

    def test_cache_functionality(self, dashboard):
        """测试缓存功能"""
        cache_key = "test_cache_key"
        test_data = {"test": "data", "timestamp": datetime.now().isoformat()}

        # 测试缓存未命中
        assert not dashboard._is_cache_valid(cache_key)

        # 设置缓存
        dashboard._cache[cache_key] = test_data
        dashboard._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=5)

        # 测试缓存命中
        assert dashboard._is_cache_valid(cache_key)

        # 测试缓存过期
        dashboard._cache_expiry[cache_key] = datetime.now() - timedelta(minutes=1)
        assert not dashboard._is_cache_valid(cache_key)

    def test_get_start_time(self, dashboard):
        """测试时间范围计算"""
        now = datetime.now()

        # 测试各种时间范围
        hour_ago = dashboard._get_start_time("1h", now)
        assert hour_ago == now - timedelta(hours=1)

        day_ago = dashboard._get_start_time("24h", now)
        assert day_ago == now - timedelta(hours=24)

        week_ago = dashboard._get_start_time("7d", now)
        assert week_ago == now - timedelta(days=7)

        month_ago = dashboard._get_start_time("30d", now)
        assert month_ago == now - timedelta(days=30)

        # 测试默认时间范围（24h）
        default_time = dashboard._get_start_time("invalid", now)
        assert default_time == day_ago


@pytest.mark.security
class TestGlobalSecurityDashboard:
    """全局安全仪表板实例测试"""

    def test_get_security_dashboard(self):
        """测试获取全局安全仪表板实例"""
        dashboard1 = get_security_dashboard()
        dashboard2 = get_security_dashboard()

        # 应该返回相同的实例
        assert dashboard1 is dashboard2


@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityDashboardIntegration:
    """安全仪表板集成测试"""

    async def test_dashboard_data_consistency(self):
        """测试仪表板数据一致性"""
        dashboard = get_security_dashboard()

        # 创建一些测试事件
        mock_monitor = Mock()
        test_events = []

        for i in range(10):
            event = Mock()
            event.event_type = SecurityEventType.INJECTION_ATTEMPT
            event.threat_level = (
                ThreatLevel.HIGH if i % 2 == 0 else ThreatLevel.CRITICAL
            )
            event.timestamp = datetime.now() - timedelta(hours=i)
            event.source_ip = f"192.168.1.{100 + i}"
            test_events.append(event)

        mock_monitor.events = test_events
        mock_monitor.blocked_ips = {"203.0.113.1"}
        mock_monitor.metrics.auto_responses = 5

        mock_automation = Mock()
        mock_automation.get_automation_status.return_value = {
            "enabled_rules": 3,
            "total_rules": 5,
            "executions_24h": 2,
            "successful_executions_24h": 2,
            "failed_executions_24h": 0,
        }

        with (
            patch(
                "src.security.security_dashboard.get_security_monitor",
                return_value=mock_monitor,
            ),
            patch(
                "src.security.security_dashboard.get_automation_engine",
                return_value=mock_automation,
            ),
            patch.object(dashboard, "_calculate_threat_trend", return_value={}),
            patch.object(dashboard, "_generate_threat_intelligence", return_value={}),
            patch.object(dashboard, "_get_system_health", return_value={}),
            patch.object(dashboard, "_generate_recommendations", return_value=[]),
        ):

            # 获取概览数据
            overview = await dashboard.get_dashboard_overview("24h")

            # 获取指标数据
            metrics = await dashboard.get_security_metrics("24h")

            # 验证数据一致性
            assert overview["summary"]["total_events_24h"] == metrics.total_events
            assert overview["summary"]["blocked_ips"] == metrics.blocked_ips
            assert overview["summary"]["auto_responses"] == metrics.auto_responses

            # 获取威胁情报
            intelligence = await dashboard.get_threat_intelligence()
            assert "top_attacker_ips" in intelligence.dict()
            assert "attack_patterns" in intelligence.dict()
            assert "geographic_threats" in intelligence.dict()
            assert "emerging_threats" in intelligence.dict()

    async def test_dashboard_error_handling(self):
        """测试仪表板错误处理"""
        dashboard = get_security_dashboard()

        # 测试监控系统异常
        with patch(
            "src.security.security_dashboard.get_security_monitor",
            side_effect=Exception("监控异常"),
        ):
            try:
                await dashboard.get_security_overview()
                assert False, "应该抛出异常"
            except Exception:
                pass  # 预期异常

        # 测试自动化引擎异常
        mock_monitor = Mock()
        mock_monitor.get_security_dashboard.return_value = {"summary": {}}

        with (
            patch(
                "src.security.security_dashboard.get_security_monitor",
                return_value=mock_monitor,
            ),
            patch(
                "src.security.security_dashboard.get_automation_engine",
                side_effect=Exception("自动化异常"),
            ),
        ):

            with (
                patch.object(dashboard, "_calculate_threat_trend", return_value={}),
                patch.object(
                    dashboard, "_generate_threat_intelligence", return_value={}
                ),
                patch.object(
                    dashboard,
                    "_get_system_health",
                    return_value={"overall_status": "error"},
                ),
                patch.object(dashboard, "_generate_recommendations", return_value=[]),
            ):

                overview = await dashboard.get_dashboard_overview("24h")

                # 系统健康应该返回错误状态
                assert overview["system_health"]["overall_status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
