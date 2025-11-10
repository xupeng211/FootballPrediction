"""
审计服务测试
Audit Service Tests

测试审计服务的核心功能。
Tests core functionality of audit service.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.services.audit_service import (
    AuditAction,
    AuditContext,
    AuditEvent,
    AuditLog,
    AuditLogSummary,
    AuditSeverity,
    AuditService,
    DataSanitizer,
    SeverityAnalyzer,
)


class TestDataStructures:
    """测试数据结构"""

    def test_audit_severity_enum(self):
        """测试审计严重程度枚举"""
        assert AuditSeverity.LOW.value == "low"
        assert AuditSeverity.MEDIUM.value == "medium"
        assert AuditSeverity.HIGH.value == "high"
        assert AuditSeverity.CRITICAL.value == "critical"

    def test_audit_action_constants(self):
        """测试审计动作常量"""
        assert AuditAction.CREATE == "create"
        assert AuditAction.READ == "read"
        assert AuditAction.UPDATE == "update"
        assert AuditAction.DELETE == "delete"
        assert AuditAction.LOGIN == "login"
        assert AuditAction.LOGOUT == "logout"
        assert AuditAction.EXPORT == "export"

    def test_audit_context_creation(self):
        """测试审计上下文创建"""
        context = AuditContext(
            user_id="user123",
            session_id="session456",
            ip_address="192.168.1.1"
        )

        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.ip_address == "192.168.1.1"
        assert isinstance(context.timestamp, datetime)

    def test_audit_context_optional_fields(self):
        """测试审计上下文明可选字段"""
        context = AuditContext(user_id="user123")

        assert context.user_id == "user123"
        assert context.session_id is None
        assert context.ip_address is None
        assert isinstance(context.timestamp, datetime)

    def test_audit_log_creation(self):
        """测试审计日志创建"""
        context = AuditContext(user_id="user123")
        log = AuditLog(
            action=AuditAction.CREATE,
            context=context,
            severity=AuditSeverity.HIGH,
            details={"resource": "prediction", "id": 123}
        )

        assert log.action == AuditAction.CREATE
        assert log.context == context
        assert log.severity == AuditSeverity.HIGH
        assert log.details["resource"] == "prediction"
        assert isinstance(log.timestamp, datetime)

    def test_audit_log_summary_initialization(self):
        """测试审计日志摘要初始化"""
        summary = AuditLogSummary()

        assert summary.total_logs == 0
        assert summary.by_severity == {}
        assert summary.by_action == {}

    def test_audit_event_creation(self):
        """测试审计事件创建"""
        event = AuditEvent(
            action="create_prediction",
            user="user123",
            severity=AuditSeverity.MEDIUM,
            details={"prediction_id": 456, "confidence": 0.85}
        )

        assert event.action == "create_prediction"
        assert event._user == "user123"
        assert event.severity == AuditSeverity.MEDIUM
        assert event.details["prediction_id"] == 456
        assert isinstance(event.timestamp, datetime)


class TestDataSanitizer:
    """测试数据清理器"""

    @pytest.fixture
    def sanitizer(self):
        """数据清理器实例"""
        return DataSanitizer()

    def test_sanitize_password(self, sanitizer):
        """测试密码清理"""
        data = {"username": "john", "password": "secret123"}
        result = sanitizer.sanitize(data)

        assert result["username"] == "john"
        assert result["password"] == "***"

    def test_sanitize_token(self, sanitizer):
        """测试令牌清理"""
        data = {"token": "abc123xyz", "user_id": 456}
        result = sanitizer.sanitize(data)

        assert result["token"] == "***"
        assert result["user_id"] == 456

    def test_sanitize_multiple_sensitive_fields(self, sanitizer):
        """测试多个敏感字段清理"""
        data = {
            "username": "john",
            "password": "secret",
            "token": "abc123",
            "normal_field": "preserve_me"
        }
        result = sanitizer.sanitize(data)

        assert result["username"] == "john"
        assert result["password"] == "***"
        assert result["token"] == "***"
        assert result["normal_field"] == "preserve_me"

    def test_sanitize_no_sensitive_data(self, sanitizer):
        """测试无敏感数据清理"""
        data = {"name": "John", "age": 30}
        result = sanitizer.sanitize(data)

        assert result == data

    def test_sanitize_empty_dict(self, sanitizer):
        """测试空字典清理"""
        data = {}
        result = sanitizer.sanitize(data)

        assert result == {}


class TestSeverityAnalyzer:
    """测试严重程度分析器"""

    @pytest.fixture
    def analyzer(self):
        """严重程度分析器实例"""
        return SeverityAnalyzer()

    def test_analyze_delete_action(self, analyzer):
        """测试删除动作分析"""
        event = Mock()
        event.action = "delete_prediction"

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.HIGH

    def test_analyze_remove_action(self, analyzer):
        """测试移除动作分析"""
        event = Mock()
        event.action = "remove_user"

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.HIGH

    def test_analyze_modify_action(self, analyzer):
        """测试修改动作分析"""
        event = Mock()
        event.action = "modify_prediction"

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.MEDIUM

    def test_analyze_update_action(self, analyzer):
        """测试更新动作分析"""
        event = Mock()
        event.action = "update_settings"

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.MEDIUM

    def test_analyze_read_action(self, analyzer):
        """测试读取动作分析"""
        event = Mock()
        event.action = "read_predictions"

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.LOW

    def test_analyze_create_action(self, analyzer):
        """测试创建动作分析"""
        event = Mock()
        event.action = "create_prediction"

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.LOW

    def test_analyze_case_insensitive(self, analyzer):
        """测试大小写不敏感分析"""
        event = Mock()
        event.action = "DELETE_PREDICTION"

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.HIGH


class TestAuditService:
    """测试审计服务"""

    @pytest.fixture
    def audit_service(self):
        """审计服务实例"""
        return AuditService()

    def test_audit_service_initialization(self, audit_service):
        """测试审计服务初始化"""
        assert audit_service.events == []
        assert hasattr(audit_service, 'sanitizer')
        assert hasattr(audit_service, 'analyzer')
        assert isinstance(audit_service.sanitizer, DataSanitizer)
        assert isinstance(audit_service.analyzer, SeverityAnalyzer)

    @patch('src.services.audit_service.logger')
    def test_log_event_basic(self, mock_logger, audit_service):
        """测试基础事件记录"""
        details = {"action": "create_prediction", "prediction_id": 123}
        event = audit_service.log_event("create_prediction", "user123", details)

        assert len(audit_service.events) == 1
        assert event.action == "create_prediction"
        assert event._user == "user123"
        assert event.details["prediction_id"] == 123
        assert isinstance(event.timestamp, datetime)
        mock_logger.info.assert_called_once_with("Audit event logged: create_prediction by user123")

    @patch('src.services.audit_service.logger')
    def test_log_event_with_sensitive_data(self, mock_logger, audit_service):
        """测试包含敏感数据的事件记录"""
        details = {"username": "john", "password": "secret123", "token": "abc123"}
        event = audit_service.log_event("login", "user123", details)

        assert len(audit_service.events) == 1
        assert event.details["password"] == "***"
        assert event.details["token"] == "***"
        assert event.details["username"] == "john"

    def test_log_event_severity_analysis(self, audit_service):
        """测试事件严重程度分析"""
        # 测试删除动作
        delete_event = audit_service.log_event("delete_prediction", "user123", {})
        assert delete_event.severity == AuditSeverity.HIGH

        # 测试修改动作
        modify_event = audit_service.log_event("modify_prediction", "user123", {})
        assert modify_event.severity == AuditSeverity.MEDIUM

        # 测试读取动作
        read_event = audit_service.log_event("read_prediction", "user123", {})
        assert read_event.severity == AuditSeverity.LOW

    def test_get_events_default_limit(self, audit_service):
        """测试获取事件（默认限制）"""
        # 添加150个事件
        for i in range(150):
            audit_service.log_event(f"action_{i}", "user123", {"index": i})

        events = audit_service.get_events()
        assert len(events) == 100  # 默认限制
        # 检查获取的是最新的事件
        assert events[-1].details["index"] == 149

    def test_get_events_custom_limit(self, audit_service):
        """测试获取事件（自定义限制）"""
        # 添加50个事件
        for i in range(50):
            audit_service.log_event(f"action_{i}", "user123", {"index": i})

        events = audit_service.get_events(limit=25)
        assert len(events) == 25

    def test_get_events_empty(self, audit_service):
        """测试获取空事件列表"""
        events = audit_service.get_events()
        assert events == []

    def test_get_summary_empty(self, audit_service):
        """测试获取空摘要"""
        summary = audit_service.get_summary()

        assert summary.total_logs == 0
        assert summary.by_severity == {}
        assert summary.by_action == {}

    def test_get_summary_with_events(self, audit_service):
        """测试获取包含事件的摘要"""
        # 添加不同类型和严重程度的事件
        audit_service.log_event("delete_prediction", "user1", {})
        audit_service.log_event("delete_prediction", "user2", {})
        audit_service.log_event("create_prediction", "user1", {})
        audit_service.log_event("modify_prediction", "user3", {})

        summary = audit_service.get_summary()

        assert summary.total_logs == 4
        assert summary.by_severity["high"] == 2  # 两个删除动作
        assert summary.by_severity["medium"] == 1  # 一个修改动作
        assert summary.by_severity["low"] == 1  # 一个创建动作
        assert summary.by_action["delete_prediction"] == 2
        assert summary.by_action["create_prediction"] == 1
        assert summary.by_action["modify_prediction"] == 1

    def test_multiple_log_events_accumulation(self, audit_service):
        """测试多个事件累积"""
        users = ["user1", "user2", "user3"]
        actions = ["create", "read", "update", "delete"]

        for user in users:
            for action in actions:
                audit_service.log_event(f"{action}_prediction", user, {})

        assert len(audit_service.events) == 12  # 3 users * 4 actions

        summary = audit_service.get_summary()
        assert summary.total_logs == 12

        # 验证每个动作都有3个记录（每个用户一个）
        for action in actions:
            assert summary.by_action[f"{action}_prediction"] == 3

    def test_event_chronological_order(self, audit_service):
        """测试事件时间顺序"""
        import time

        event1 = audit_service.log_event("first_action", "user1", {})
        time.sleep(0.01)  # 小延迟确保时间戳不同
        event2 = audit_service.log_event("second_action", "user1", {})

        assert event1.timestamp < event2.timestamp
        # 最新事件应该在列表末尾
        assert audit_service.events[-1] == event2


class TestAuditServiceIntegration:
    """审计服务集成测试"""

    def test_full_audit_workflow(self):
        """测试完整审计工作流"""
        audit_service = AuditService()

        # 模拟用户会话
        context = AuditContext(
            user_id="user123",
            session_id="session456",
            ip_address="192.168.1.100"
        )

        # 1. 用户登录
        login_event = audit_service.log_event(
            AuditAction.LOGIN,
            context.user_id,
            {"session_id": context.session_id, "ip": context.ip_address}
        )

        # 2. 创建预测
        prediction_event = audit_service.log_event(
            "create_prediction",
            context.user_id,
            {"prediction_id": 789, "confidence": 0.92}
        )

        # 3. 读取预测
        read_event = audit_service.log_event(
            AuditAction.READ,
            context.user_id,
            {"prediction_id": 789}
        )

        # 4. 更新预测
        update_event = audit_service.log_event(
            "modify_prediction",
            context.user_id,
            {"prediction_id": 789, "new_confidence": 0.95}
        )

        # 5. 删除预测
        delete_event = audit_service.log_event(
            AuditAction.DELETE,
            context.user_id,
            {"prediction_id": 789}
        )

        # 6. 用户登出
        logout_event = audit_service.log_event(
            AuditAction.LOGOUT,
            context.user_id,
            {"session_id": context.session_id}
        )

        # 验证所有事件都被记录
        assert len(audit_service.events) == 6

        # 验证严重程度分析
        assert delete_event.severity == AuditSeverity.HIGH
        assert update_event.severity == AuditSeverity.MEDIUM
        assert login_event.severity == AuditSeverity.LOW
        assert logout_event.severity == AuditSeverity.LOW

        # 验证摘要统计
        summary = audit_service.get_summary()
        assert summary.total_logs == 6
        assert summary.by_action["create_prediction"] == 1
        assert summary.by_action["delete"] == 1
        assert summary.by_severity["high"] == 1  # 删除
        assert summary.by_severity["medium"] == 1  # 更新
        assert summary.by_severity["low"] == 4  # 登录、读取、登出、创建

    def test_concurrent_logging(self):
        """测试并发日志记录"""
        import threading
        import time

        audit_service = AuditService()
        results = []

        def log_user_events(user_id, event_count):
            """为用户记录事件"""
            for i in range(event_count):
                event = audit_service.log_event(
                    f"action_{i}",
                    user_id,
                    {"iteration": i}
                )
                results.append(event)

        # 创建多个线程同时记录事件
        threads = []
        for user_id in ["user1", "user2", "user3"]:
            thread = threading.Thread(
                target=log_user_events,
                args=(user_id, 5)
            )
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有事件都被记录
        assert len(audit_service.events) == 15  # 3 users * 5 events
        assert len(results) == 15

        # 验证摘要
        summary = audit_service.get_summary()
        assert summary.total_logs == 15