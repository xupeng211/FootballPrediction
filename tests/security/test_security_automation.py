#!/usr/bin/env python3
"""
安全自动化响应系统测试
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

try:
    from src.security.security_automation import (
        BlockIPAction,
        NotifyAdminAction,
        RateLimitAction,
        ResponseAction,
        ResponsePriority,
        ResponseRule,
        ScanSystemAction,
        SecurityAutomationEngine,
        get_automation_engine,
        initialize_security_automation,
    )
    from src.security.security_monitor import (
        SecurityEvent,
        SecurityEventType,
        ThreatLevel,
    )
except ImportError as e:
    print(f"Warning: Could not import security automation modules: {e}")
    pytest.skip("安全自动化模块不可用", allow_module_level=True)


@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityActions:
    """安全动作测试"""

    @pytest.fixture
    def sample_event(self):
        """示例安全事件"""
        return SecurityEvent(
            event_id="test_event_001",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            threat_level=ThreatLevel.HIGH,
            timestamp=datetime.now(),
            source_ip="203.0.113.1",
            user_agent="malicious-scanner/1.0",
            request_path="/api/v1/users",
            request_method="POST",
            user_id=None,
            description="SQL注入尝试",
        )

    async def test_block_ip_action(self, sample_event):
        """测试IP阻止动作"""
        action = BlockIPAction()

        # 测试执行条件
        assert action.can_execute(sample_event, {}), "IP阻止条件检查失败"

        # 测试私有IP不能被阻止
        private_ip_event = SecurityEvent(
            event_id="test_private",
            event_type=SecurityEventType.AUTHENTICATION_FAILURE,
            threat_level=ThreatLevel.MEDIUM,
            timestamp=datetime.now(),
            source_ip="192.168.1.100",  # 私有IP
            user_agent="test",
            request_path="/test",
            request_method="GET",
            description="Test",
        )
        assert not action.can_execute(private_ip_event, {}), "私有IP不应该被阻止"

        # 测试已阻止的IP
        action.last_execution["block_ip:203.0.113.1"] = datetime.now() - timedelta(
            minutes=10
        )
        mock_monitor = Mock()
        mock_monitor.is_ip_blocked.return_value = True

        with patch(
            "src.security.security_automation.get_security_monitor",
            return_value=mock_monitor,
        ):
            assert not action.can_execute(sample_event, {}), "已阻止的IP不应该重复阻止"

    async def test_rate_limit_action(self, sample_event):
        """测试速率限制动作"""
        action = RateLimitAction()

        # 测试执行条件（通常总是允许）
        assert action.can_execute(sample_event, {}), "速率限制条件检查失败"

        # 测试执行
        result = await action.execute(
            sample_event, {"limit_requests": 10, "duration_minutes": 15}
        )

        assert result["success"], "速率限制执行失败"
        assert result["ip_limited"] == sample_event.source_ip
        assert result["limit_requests"] == 10
        assert result["duration_minutes"] == 15

    async def test_notify_admin_action(self, sample_event):
        """测试管理员通知动作"""
        action = NotifyAdminAction()

        # 测试冷却期
        action.last_execution["notify_admin:203.0.113.1"] = datetime.now() - timedelta(
            minutes=2
        )
        assert not action.can_execute(sample_event, {}), "冷却期内的动作不应该执行"

        # 重置冷却期
        action.last_execution.clear()
        assert action.can_execute(sample_event, {}), "冷却期外动作应该执行"

        # 测试执行
        result = await action.execute(
            sample_event, {"methods": ["email"], "severity": "high"}
        )

        assert result["success"], "管理员通知执行失败"
        assert "notifications" in result
        assert "email" in result["notifications"]

    async def test_scan_system_action(self, sample_event):
        """测试系统扫描动作"""
        action = ScanSystemAction()

        # 测试冷却期
        action.last_execution["scan_system:203.0.113.1"] = datetime.now() - timedelta(
            minutes=30
        )
        assert not action.can_execute(sample_event, {}), "冷却期内的扫描不应该执行"

        # 重置冷却期
        action.last_execution.clear()
        assert action.can_execute(sample_event, {}), "冷却期外扫描应该执行"

        # 测试执行
        result = await action.execute(sample_event, {"scan_types": ["security"]})

        assert result["success"], "系统扫描执行失败"
        assert "scan_results" in result
        assert "security" in result["scan_results"]


@pytest.mark.security
@pytest.mark.asyncio
class TestResponseRule:
    """响应规则测试"""

    @pytest.fixture
    def sample_rule(self):
        """示例响应规则"""
        return ResponseRule(
            rule_id="test_rule_001",
            name="测试规则",
            trigger_event_types=[SecurityEventType.INJECTION_ATTEMPT],
            trigger_threat_levels=[ThreatLevel.HIGH, ThreatLevel.CRITICAL],
            conditions={},
            actions=[ResponseAction.BLOCK_IP, ResponseAction.NOTIFY_ADMIN],
            priority=ResponsePriority.HIGH,
            description="测试响应规则",
        )

    def test_rule_matching(self, sample_rule):
        """测试规则匹配逻辑"""
        # 匹配的事件
        matching_event = SecurityEvent(
            event_id="match_event",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            threat_level=ThreatLevel.HIGH,
            timestamp=datetime.now(),
            source_ip="203.0.113.1",
            user_agent="test",
            request_path="/test",
            request_method="POST",
            description="匹配事件",
        )
        assert sample_rule.trigger_event_types[0] == matching_event.event_type
        assert sample_rule.trigger_threat_levels[0] == matching_event.threat_level

    def test_rule_conditions(self, sample_rule):
        """测试规则条件检查"""
        # 无条件规则
        event = SecurityEvent(
            event_id="test_event",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            threat_level=ThreatLevel.HIGH,
            timestamp=datetime.now(),
            source_ip="203.0.113.1",
            user_agent="test",
            request_path="/test",
            request_method="POST",
            description="测试",
        )
        assert sample_rule._check_conditions({}, event)  # 无条件应该总是匹配

        # 有条件规则
        conditional_rule = ResponseRule(
            rule_id="conditional_rule",
            name="条件规则",
            trigger_event_types=[SecurityEventType.SUSPICIOUS_REQUEST],
            trigger_threat_levels=[ThreatLevel.MEDIUM],
            conditions={"repeat_offender": True},
            actions=[ResponseAction.RATE_LIMIT],
            priority=ResponsePriority.MEDIUM,
        )

        # 不满足条件
        assert not conditional_rule._check_conditions({"repeat_offender": True}, event)


@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityAutomationEngine:
    """安全自动化引擎测试"""

    @pytest.fixture
    def automation_engine(self):
        """自动化引擎实例"""
        return SecurityAutomationEngine()

    async def test_rule_registration(self, automation_engine):
        """测试规则注册"""
        initial_count = len(automation_engine.rules)

        # 添加新规则
        new_rule = ResponseRule(
            rule_id="custom_rule",
            name="自定义规则",
            trigger_event_types=[SecurityEventType.DATA_EXFILTRATION],
            trigger_threat_levels=[ThreatLevel.CRITICAL],
            conditions={},
            actions=[ResponseAction.BLOCK_IP],
            priority=ResponsePriority.CRITICAL,
            description="自定义测试规则",
        )
        automation_engine.add_rule(new_rule)

        assert len(automation_engine.rules) == initial_count + 1
        assert new_rule in automation_engine.rules

        # 移除规则
        success = automation_engine.remove_rule("custom_rule")
        assert success
        assert len(automation_engine.rules) == initial_count
        assert new_rule not in automation_engine.rules

    def test_rule_enable_disable(self, automation_engine):
        """测试规则启用/禁用"""
        rule_id = "auto_block_high_threat"  # 默认规则ID

        # 禁用规则
        success = automation_engine.disable_rule(rule_id)
        assert success

        # 查找规则
        rule = next((r for r in automation_engine.rules if r.rule_id == rule_id), None)
        assert rule is not None
        assert not rule.enabled

        # 启用规则
        success = automation_engine.enable_rule(rule_id)
        assert success
        assert rule.enabled

    async def test_process_security_event(self, automation_engine):
        """测试处理安全事件"""
        # 创建高危事件
        event = SecurityEvent(
            event_id="test_auto_process",
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            threat_level=ThreatLevel.HIGH,
            timestamp=datetime.now(),
            source_ip="203.0.113.5",
            user_agent="sqlmap/1.0",
            request_path="/api/v1/users",
            request_method="POST",
            description="自动处理测试事件",
        )

        # Mock动作执行
        mock_block_action = Mock(spec=BlockIPAction)
        mock_block_action.can_execute.return_value = True
        mock_block_action.execute.return_value = {
            "success": True,
            "ip_blocked": "203.0.113.5",
        }

        mock_notify_action = Mock(spec=NotifyAdminAction)
        mock_notify_action.can_execute.return_value = True
        mock_notify_action.execute.return_value = {
            "success": True,
            "notifications": {"email": True},
        }

        automation_engine.actions["block_ip"] = mock_block_action
        automation_engine.actions["notify_admin"] = mock_notify_action

        # 处理事件
        executions = await automation_engine.process_security_event(event)

        # 验证执行结果
        assert len(executions) >= 1
        assert any(exec.action == ResponseAction.BLOCK_IP for exec in executions)
        assert any(exec.action == ResponseAction.NOTIFY_ADMIN for exec in executions)

    def test_execution_frequency_limiting(self, automation_engine):
        """测试执行频率限制"""
        rule = automation_engine.rules[0]  # 使用第一个默认规则

        # 模拟最近执行
        now = datetime.now()
        automation_engine.rule_executions[rule.rule_id] = [
            now - timedelta(minutes=1),
            now - timedelta(minutes=2),
            now - timedelta(minutes=5),
        ]

        # 规则有冷却期，不应该执行
        assert not automation_engine._can_execute_rule(rule)

        # 清除最近的执行记录
        automation_engine.rule_executions[rule.rule_id] = [
            now - timedelta(minutes=35)  # 超过冷却期
        ]

        # 现在应该可以执行
        assert automation_engine._can_execute_rule(rule)

    def test_get_automation_status(self, automation_engine):
        """测试获取自动化状态"""
        status = automation_engine.get_automation_status()

        # 验证基本结构
        assert "total_rules" in status
        assert "enabled_rules" in status
        assert "registered_actions" in status
        assert "executions_24h" in status
        assert "successful_executions_24h" in status
        assert "failed_executions_24h" in status
        assert "rules" in status
        assert "recent_executions" in status

        # 验证动作列表
        expected_actions = ["block_ip", "rate_limit", "notify_admin", "scan_system"]
        for action in expected_actions:
            assert action in status["registered_actions"]

        # 验证规则信息
        assert len(status["rules"]) > 0
        for rule_info in status["rules"]:
            assert "rule_id" in rule_info
            assert "name" in rule_info
            assert "enabled" in rule_info
            assert "priority" in rule_info
            assert "trigger_types" in rule_info
            assert "actions" in rule_info


@pytest.mark.security
class TestGlobalAutomationEngine:
    """全局自动化引擎实例测试"""

    def test_get_automation_engine(self):
        """测试获取全局自动化引擎实例"""
        engine1 = get_automation_engine()
        engine2 = get_automation_engine()

        # 应该返回相同的实例
        assert engine1 is engine2


@pytest.mark.security
@pytest.mark.asyncio
class TestSecurityAutomationIntegration:
    """安全自动化集成测试"""

    async def test_end_to_end_automation_workflow(self):
        """测试端到端自动化工作流程"""
        engine = get_automation_engine()
        monitor = get_security_monitor()

        # 模拟一系列安全事件
        attacker_ip = "203.0.113.20"

        # 1. 创建数据泄露事件（最高威胁级别）
        data_breach_event = await monitor.log_security_event(
            SecurityEventType.DATA_EXFILTRATION,
            attacker_ip,
            "/api/v1/sensitive-data/export",
            "GET",
            "custom-scanner/1.0",
            user_id="admin_user",
            description="检测到数据泄露尝试",
            metadata={"data_size": "large", "sensitive": True},
        )

        # 2. 处理事件（应该触发多个自动化响应）
        executions = await engine.process_security_event(data_breach_event)

        # 验证执行了响应动作
        assert len(executions) > 0, "应该执行自动化响应"

        # 3. 验证自动化状态
        status = engine.get_automation_status()
        assert status["executions_24h"] >= len(executions)

        # 4. 验证安全监控状态
        assert attacker_ip in monitor.blocked_ips or any(
            exec.affected_resources.get("blocked_ips") == [attacker_ip]
            for exec in executions
        ), "IP应该被自动阻止"

    async def test_multiple_event_types_automation(self):
        """测试多种事件类型的自动化响应"""
        engine = get_automation_engine()
        monitor = get_security_monitor()

        test_cases = [
            {
                "event_type": SecurityEventType.BRUTE_FORCE,
                "threat_level": ThreatLevel.HIGH,
                "ip": "203.0.113.30",
                "description": "暴力破解攻击",
            },
            {
                "event_type": SecurityEventType.XSS_ATTEMPT,
                "threat_level": ThreatLevel.HIGH,
                "ip": "203.0.113.31",
                "description": "XSS攻击尝试",
            },
            {
                "event_type": SecurityEventType.UNAUTHORIZED_ACCESS,
                "threat_level": ThreatLevel.MEDIUM,
                "ip": "203.0.113.32",
                "description": "未授权访问尝试",
            },
            {
                "event_type": SecurityEventType.ANOMALOUS_BEHAVIOR,
                "threat_level": ThreatLevel.MEDIUM,
                "ip": "203.0.113.33",
                "description": "异常用户行为",
                "metadata": {"anomaly_score": 60},
            },
        ]

        all_executions = []
        for i, test_case in enumerate(test_cases):
            event = await monitor.log_security_event(
                test_case["event_type"],
                test_case["ip"],
                f"/test/endpoint_{i}",
                "POST",
                "test-agent",
                user_id=f"user_{i}",
                description=test_case["description"],
                metadata=test_case.get("metadata", {}),
            )

            executions = await engine.process_security_event(event)
            all_executions.extend(executions)

        # 验证不同事件类型触发了不同的响应
        executed_actions = set()
        for execution in all_executions:
            for action in execution.actions:
                executed_actions.add(action)

        # 至少应该有一些动作被执行
        assert len(executed_actions) > 0, "应该执行一些自动化动作"

        # 验证威胁等级越高，响应动作越多
        high_threat_actions = 0
        medium_threat_actions = 0

        for execution in all_executions:
            for action in execution.actions:
                if execution.event_id in [
                    "test_auto_process_0",
                    "test_auto_process_1",
                ]:
                    high_threat_actions += len(execution.actions)
                else:
                    medium_threat_actions += len(execution.actions)

        # 高危事件通常触发更多响应动作
        assert high_threat_actions >= medium_threat_actions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
