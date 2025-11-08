#!/usr/bin/env python3
"""
安全监控系统测试
"""

from datetime import datetime, timedelta

import pytest

try:
    from src.security.security_monitor import (
        SecurityEvent,
        SecurityEventType,
        SecurityMonitor,
        ThreatDetector,
        ThreatLevel,
        get_security_monitor,
        initialize_security_monitoring,
    )
except ImportError as e:
    print(f"Warning: Could not import security monitoring modules: {e}")
    pytest.skip("安全监控模块不可用", allow_module_level=True)


@pytest.mark.security
@pytest.mark.asyncio
class TestThreatDetector:
    """威胁检测器测试"""

    @pytest.fixture
    def threat_detector(self):
        """威胁检测器实例"""
        return ThreatDetector()

    def test_detect_sql_injection(self, threat_detector):
        """测试SQL注入检测"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1; DELETE FROM users WHERE 1=1; --",
            "SELECT * FROM users WHERE id = 1 UNION SELECT password FROM admin",
        ]

        for input_data in malicious_inputs:
            attacks = threat_detector.detect_injection_attempts(input_data)
            assert len(attacks) > 0, f"SQL注入检测失败: {input_data}"

    def test_detect_xss_attempts(self, threat_detector):
        """测试XSS攻击检测"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
        ]

        for payload in xss_payloads:
            attacks = threat_detector.detect_injection_attempts(payload)
            assert "xss" in attacks, f"XSS检测失败: {payload}"

    def test_detect_malicious_user_agent(self, threat_detector):
        """测试恶意用户代理检测"""
        malicious_agents = [
            "sqlmap/1.0",
            "nmap scripting scanner",
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "curl/7.68.0",
            "python-requests/2.25.1",
        ]

        # 应该检测到sqlmap和nmap，但不应该检测到正常的bot和工具
        detected_malicious = []
        for agent in malicious_agents:
            if threat_detector.detect_malicious_user_agent(agent):
                detected_malicious.append(agent)

        assert len(detected_malicious) >= 2, "恶意用户代理检测不准确"

    def test_detect_brute_force(self, threat_detector):
        """测试暴力破解检测"""
        now = datetime.now()
        ip_events = []

        # 创建5个认证失败事件
        for i in range(5):
            event = SecurityEvent(
                event_id=f"test_{i}",
                event_type=SecurityEventType.AUTHENTICATION_FAILURE,
                threat_level=ThreatLevel.LOW,
                timestamp=now - timedelta(minutes=i),
                source_ip="192.168.1.100",
                user_agent="test-agent",
                request_path="/api/auth/login",
                request_method="POST",
                description=f"Login failure {i+1}",
            )
            ip_events.append(event)

        # 应该检测到暴力破解
        assert threat_detector.detect_brute_force(ip_events), "暴力破解检测失败"

    def test_detect_anomalous_behavior(self, threat_detector):
        """测试异常行为检测"""
        now = datetime.now()
        user_events = []

        # 创建异常行为模式：16小时活动
        for hour in range(16):
            event = SecurityEvent(
                event_id=f"test_{hour}",
                event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                threat_level=ThreatLevel.LOW,
                timestamp=now - timedelta(hours=hour),
                source_ip=f"192.168.1.{hour % 255}",
                user_agent="test-agent",
                request_path=f"/api/endpoint_{hour}",
                request_method="GET",
                user_id="test_user",
                description=f"Activity {hour}",
            )
            user_events.append(event)

        # 应该检测到异常时间模式
        result = threat_detector.detect_anomalous_behavior(user_events)
        assert result["is_anomalous"], "异常行为检测失败"
        assert "unusual_time_pattern" in result["reasons"], "异常原因识别失败"

    def test_classify_threat_level(self, threat_detector):
        """测试威胁等级分类"""
        # 测试基础等级
        level = threat_detector.classify_threat_level(
            SecurityEventType.AUTHENTICATION_FAILURE, {}
        )
        assert level == ThreatLevel.LOW

        # 测试升级等级
        level = threat_detector.classify_threat_level(
            SecurityEventType.INJECTION_ATTEMPT, {}
        )
        assert level == ThreatLevel.HIGH

        # 测试重复违规者升级
        level = threat_detector.classify_threat_level(
            SecurityEventType.SUSPICIOUS_REQUEST, {"repeat_offender": True}
        )
        assert level == ThreatLevel.HIGH

        # 测试管理员目标升级
        level = threat_detector.classify_threat_level(
            SecurityEventType.UNAUTHORIZED_ACCESS, {"admin_target": True}
        )
        assert level == ThreatLevel.HIGH


@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityMonitor:
    """安全监控器测试"""

    @pytest.fixture
    def security_monitor(self):
        """安全监控器实例"""
        return SecurityMonitor()

    async def test_log_security_event(self, security_monitor):
        """测试记录安全事件"""
        event = await security_monitor.log_security_event(
            SecurityEventType.AUTHENTICATION_FAILURE,
            "192.168.1.100",
            "/api/auth/login",
            "POST",
            "Mozilla/5.0",
            user_id="test_user",
            description="测试安全事件",
        )

        assert event is not None
        assert event.event_type == SecurityEventType.AUTHENTICATION_FAILURE
        assert event.source_ip == "192.168.1.100"
        assert event.user_id == "test_user"
        assert not event.is_resolved

        # 验证事件被存储
        assert len(security_monitor.events) > 0
        assert "192.168.1.100" in security_monitor.ip_events

    async def test_analyze_request_security(self, security_monitor):
        """测试请求安全分析"""
        events = await security_monitor.analyze_request_security(
            source_ip="10.0.0.50",
            request_path="/api/v1/users/../etc/passwd",
            request_method="GET",
            user_agent="sqlmap/1.0",
            request_data="'; DROP TABLE users; --",
            user_id="test_user",
        )

        # 应该检测到路径遍历和SQL注入
        assert len(events) >= 1

        # 检查事件类型
        event_types = [event.event_type for event in events]
        assert (
            SecurityEventType.INJECTION_ATTEMPT in event_types
            or SecurityEventType.SUSPICIOUS_REQUEST in event_types
        )

    async def test_block_ip(self, security_monitor):
        """测试IP阻止功能"""
        ip_address = "203.0.113.1"  # 公网IP

        # 阻止IP
        success = await security_monitor.block_ip(
            ip_address, duration_hours=1, reason="测试阻止"
        )
        assert success, "IP阻止失败"
        assert ip_address in security_monitor.blocked_ips

        # 检查IP是否被阻止
        assert security_monitor.is_ip_blocked(ip_address), "IP阻止状态检查失败"

        # 解除阻止
        success = await security_monitor.unblock_ip(ip_address)
        assert success, "IP解除阻止失败"
        assert not security_monitor.is_ip_blocked(ip_address), "IP解除阻止状态检查失败"

    async def test_block_private_ip(self, security_monitor):
        """测试阻止私有IP（应该失败）"""
        private_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]

        for ip in private_ips:
            success = await security_monitor.block_ip(ip)
            assert not success, f"不应该阻止私有IP: {ip}"
            assert ip not in security_monitor.blocked_ips

    def test_get_security_dashboard(self, security_monitor):
        """测试获取安全仪表板数据"""
        dashboard = security_monitor.get_security_dashboard()

        # 验证基本结构
        assert "summary" in dashboard
        assert "threat_distribution" in dashboard
        assert "type_distribution" in dashboard
        assert "geo_distribution" in dashboard
        assert "blocked_ips_list" in dashboard

        # 验证摘要数据
        summary = dashboard["summary"]
        assert "total_events_24h" in summary
        assert "blocked_ips" in summary
        assert "auto_responses" in summary

    async def test_auto_respond(self, security_monitor):
        """测试自动响应功能"""
        # 创建高危事件
        event = await security_monitor.log_security_event(
            SecurityEventType.INJECTION_ATTEMPT,
            "203.0.113.2",
            "/api/v1/users",
            "POST",
            "sqlmap/1.0",
            description="SQL注入尝试",
            metadata={"attack_type": "sql_injection"},
        )

        # 高危事件应该触发自动响应
        assert event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        # 注意：实际的自动响应在真实环境中会执行，这里主要测试逻辑

    async def test_geo_location_lookup(self, security_monitor):
        """测试地理位置查找"""
        geo_location = await security_monitor._get_geo_location("8.8.8.8")
        # 在没有GeoIP数据库的情况下，应该返回空字典
        assert isinstance(geo_location, dict)

    def test_update_metrics(self, security_monitor):
        """测试指标更新"""
        event = SecurityEvent(
            event_id="test_metrics",
            event_type=SecurityEventType.AUTHENTICATION_FAILURE,
            threat_level=ThreatLevel.LOW,
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            user_agent="test",
            request_path="/test",
            request_method="GET",
            description="测试",
        )

        initial_total = security_monitor.metrics.total_events
        security_monitor._update_metrics(event)

        assert security_monitor.metrics.total_events == initial_total + 1
        assert security_monitor.metrics.events_by_type["auth_failure"] == 1
        assert security_monitor.metrics.events_by_level["low"] == 1
        assert security_monitor.metrics.top_source_ips["192.168.1.100"] == 1


@pytest.mark.security
class TestGlobalSecurityMonitor:
    """全局安全监控实例测试"""

    def test_get_security_monitor(self):
        """测试获取全局安全监控实例"""
        monitor1 = get_security_monitor()
        monitor2 = get_security_monitor()

        # 应该返回相同的实例
        assert monitor1 is monitor2


@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityMonitorIntegration:
    """安全监控集成测试"""

    async def test_complete_security_workflow(self):
        """测试完整的安全工作流程"""
        monitor = get_security_monitor()

        # 1. 模拟一系列攻击事件
        attacker_ip = "203.0.113.10"

        # 模拟暴力破解攻击
        for i in range(6):  # 超过5次阈值
            await monitor.log_security_event(
                SecurityEventType.AUTHENTICATION_FAILURE,
                attacker_ip,
                "/api/auth/login",
                "POST",
                "malicious-scanner/1.0",
                user_id=None,
                description=f"Failed login attempt {i+1}",
            )

        # 2. 模拟注入攻击
        await monitor.log_security_event(
            SecurityEventType.INJECTION_ATTEMPT,
            attacker_ip,
            "/api/v1/users",
            "POST",
            "sqlmap/1.0",
            description="SQL injection attempt",
        )

        # 3. 获取安全仪表板
        dashboard = monitor.get_security_dashboard()

        # 验证攻击被记录
        assert dashboard["summary"]["total_events_24h"] >= 7
        assert attacker_ip in [
            ip_info["ip"] for ip_info in dashboard["top_attacker_ips"]
        ]

        # 4. 检查IP是否被阻止（由于自动化响应）
        # 注意：这取决于自动响应是否实际执行
        ip_blocked = monitor.is_ip_blocked(attacker_ip)

        # 5. 验证事件存储
        attacker_events = monitor.ip_events[attacker_ip]
        assert len(attacker_events) >= 7

        # 验证事件类型多样性
        event_types = set(event.event_type for event in attacker_events)
        assert SecurityEventType.AUTHENTICATION_FAILURE in event_types
        assert SecurityEventType.INJECTION_ATTEMPT in event_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
