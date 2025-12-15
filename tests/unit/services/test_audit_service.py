"""审计服务测试
Audit Service Tests.

测试src/services/audit_service.py模块中的审计服务功能。
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.services.audit_service import (
    AuditSeverity,
    AuditAction,
    AuditContext,
    AuditLog,
    AuditLogSummary,
    DataSanitizer,
    SeverityAnalyzer,
    AuditEvent,
    AuditService,
)


class TestAuditSeverity:
    """审计严重程度测试类."""

    def test_audit_severity_enum_values(self):
        """测试审计严重程度枚举值."""
        # 验证枚举值存在且正确
        assert AuditSeverity.LOW.value == "low"
        assert AuditSeverity.MEDIUM.value == "medium"
        assert AuditSeverity.HIGH.value == "high"
        assert AuditSeverity.CRITICAL.value == "critical"

    def test_audit_severity_comparison(self):
        """测试审计严重程度比较."""
        # 枚举值比较
        assert AuditSeverity.LOW != AuditSeverity.MEDIUM
        assert AuditSeverity.MEDIUM != AuditSeverity.HIGH
        assert AuditSeverity.HIGH != AuditSeverity.CRITICAL

    def test_audit_severity_string_representation(self):
        """测试审计严重程度字符串表示."""
        assert str(AuditSeverity.LOW) == "AuditSeverity.low"
        assert repr(AuditSeverity.LOW) == "<AuditSeverity.low: 'low'>"

    def test_audit_severity_iteration(self):
        """测试审计严重程度枚举迭代."""
        severities = list(AuditSeverity)
        assert len(severities) == 4
        assert AuditSeverity.LOW in severities
        assert AuditSeverity.MEDIUM in severities
        assert AuditSeverity.HIGH in severities
        assert AuditSeverity.CRITICAL in severities


class TestAuditAction:
    """审计动作测试类."""

    def test_audit_action_constants(self):
        """测试审计动作常量."""
        # 验证所有标准动作存在
        assert hasattr(AuditAction, "CREATE")
        assert hasattr(AuditAction, "READ")
        assert hasattr(AuditAction, "UPDATE")
        assert hasattr(AuditAction, "DELETE")
        assert hasattr(AuditAction, "LOGIN")
        assert hasattr(AuditAction, "LOGOUT")
        assert hasattr(AuditAction, "EXPORT")

    def test_audit_action_values(self):
        """测试审计动作值."""
        assert AuditAction.CREATE == "create"
        assert AuditAction.READ == "read"
        assert AuditAction.UPDATE == "update"
        assert AuditAction.DELETE == "delete"
        assert AuditAction.LOGIN == "login"
        assert AuditAction.LOGOUT == "logout"
        assert AuditAction.EXPORT == "export"

    def test_audit_action_custom_actions(self):
        """测试自定义审计动作."""
        # 可以添加自定义动作
        custom_action = "custom_operation"
        assert custom_action != AuditAction.CREATE
        assert custom_action != AuditAction.READ


class TestAuditContext:
    """审计上下文测试类."""

    def test_audit_context_initialization_minimal(self):
        """测试审计上下文最小初始化."""
        user_id = "user123"
        context = AuditContext(user_id=user_id)

        # 验证基本属性
        assert context.user_id == user_id
        assert context.session_id is None
        assert context.ip_address is None

    def test_audit_context_initialization_full(self):
        """测试审计上下文完整初始化."""
        user_id = "user123"
        session_id = "session456"
        ip_address = "192.168.1.1"

        context = AuditContext(
            user_id=user_id, session_id=session_id, ip_address=ip_address
        )

        # 验证完整属性
        assert context.user_id == user_id
        assert context.session_id == session_id
        assert context.ip_address == ip_address

    def test_audit_context_validation(self):
        """测试审计上下文验证."""
        # 测试空用户ID
        with pytest.raises(ValueError):
            AuditContext(user_id="")

        # 测试None用户ID
        with pytest.raises(ValueError):
            AuditContext(user_id=None)

        # 测试有效用户ID
        valid_context = AuditContext(user_id="valid_user")
        assert valid_context.user_id == "valid_user"


class TestAuditLog:
    """审计日志测试类."""

    def test_audit_log_initialization(self):
        """测试审计日志初始化."""
        event = Mock()
        timestamp = datetime.now()
        context = Mock()

        log = AuditLog(event=event, timestamp=timestamp, context=context)

        # 验证初始化
        assert log.event == event
        assert log.timestamp == timestamp
        assert log.context == context

    def test_audit_log_timestamp_default(self):
        """测试审计日志默认时间戳."""
        event = Mock()
        context = Mock()

        before = datetime.now()
        log = AuditLog(event=event, context=context)
        after = datetime.now()

        # 验证默认时间戳在合理范围内
        assert before <= log.timestamp <= after

    def test_audit_log_id_generation(self):
        """测试审计日志ID生成."""
        event = Mock()
        context = Mock()

        log = AuditLog(event=event, context=context)

        # 验证ID被生成且是字符串
        assert hasattr(log, "id")
        assert isinstance(log.id, str)
        assert len(log.id) > 0

    def test_audit_log_serialization(self):
        """测试审计日志序列化."""
        event_data = {"action": "login", "user": "test_user"}
        context_data = {"user_id": "123", "ip": "192.168.1.1"}

        event = Mock()
        event.to_dict.return_value = event_data
        context = Mock()
        context.to_dict.return_value = context_data

        log = AuditLog(event=event, context=context)

        # 验证序列化方法存在且可调用
        if hasattr(log, "to_dict"):
            result = log.to_dict()
            assert isinstance(result, dict)


class TestAuditLogSummary:
    """审计日志摘要测试类."""

    def test_audit_log_summary_initialization(self):
        """测试审计日志摘要初始化."""
        summary = AuditLogSummary()

        # 验证默认值
        assert summary.total_events == 0
        assert summary.error_count == 0
        assert summary.warning_count == 0
        assert summary.last_updated is not None

    def test_audit_log_summary_update(self):
        """测试审计日志摘要更新."""
        summary = AuditLogSummary()

        # 模拟更新摘要
        summary.total_events = 100
        summary.error_count = 5
        summary.warning_count = 10

        assert summary.total_events == 100
        assert summary.error_count == 5
        assert summary.warning_count == 10

    def test_audit_log_summary_time_tracking(self):
        """测试审计日志摘要时间跟踪."""
        summary = AuditLogSummary()

        initial_time = summary.last_updated
        # 模拟一些时间流逝
        summary.last_updated = datetime.now()

        # 验证时间更新
        assert summary.last_updated >= initial_time


class TestDataSanitizer:
    """数据清理器测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.sanitizer = DataSanitizer()

    def test_data_sanitizer_initialization(self):
        """测试数据清理器初始化."""
        sanitizer = DataSanitizer()
        assert sanitizer is not None
        assert callable(sanitizer.sanitize)

    def test_sanitize_basic_data(self):
        """测试基本数据清理."""
        data = {"username": "test_user", "email": "test@example.com", "action": "login"}

        result = self.sanitizer.sanitize(data)

        # 基本数据应该保持不变
        assert result["username"] == "test_user"
        assert result["email"] == "test@example.com"
        assert result["action"] == "login"

    def test_sanitize_sensitive_data(self):
        """测试敏感数据清理."""
        data = {
            "username": "test_user",
            "password": "secret123",
            "api_key": "sk-1234567890",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        }

        result = self.sanitizer.sanitize(data)

        # 敏感数据应该被清理
        assert result["username"] == "test_user"
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"

    def test_sanitize_nested_data(self):
        """测试嵌套数据清理."""
        data = {
            "user": {"name": "Test User", "password": "secret123"},
            "metadata": {"token": "secret_token", "public_info": "public_value"},
        }

        result = self.sanitizer.sanitize(data)

        # 验证嵌套数据也被清理
        assert result["user"]["name"] == "Test User"
        assert result["user"]["password"] == "[REDACTED]"
        assert result["metadata"]["token"] == "[REDACTED]"
        assert result["metadata"]["public_info"] == "public_value"

    def test_sanitize_list_data(self):
        """测试列表数据清理."""
        data = {
            "users": [
                {"name": "User1", "password": "pass1"},
                {"name": "User2", "password": "pass2"},
            ]
        }

        result = self.sanitizer.sanitize(data)

        # 验证列表中的敏感数据被清理
        assert result["users"][0]["name"] == "User1"
        assert result["users"][0]["password"] == "[REDACTED]"
        assert result["users"][1]["name"] == "User2"
        assert result["users"][1]["password"] == "[REDACTED]"

    def test_sanitize_empty_data(self):
        """测试空数据清理."""
        data = {}
        result = self.sanitizer.sanitize(data)
        assert result == {}

    def test_sanitize_none_data(self):
        """测试None数据处理."""
        result = self.sanitizer.sanitize(None)
        assert result is None


class TestSeverityAnalyzer:
    """严重程度分析器测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.analyzer = SeverityAnalyzer()

    def test_severity_analyzer_initialization(self):
        """测试严重程度分析器初始化."""
        analyzer = SeverityAnalyzer()
        assert analyzer is not None
        assert callable(analyzer.analyze)

    def test_analyze_low_severity_event(self):
        """测试低严重程度事件分析."""
        event = Mock()
        event.action = "read"
        event.details = {}

        severity = self.analyzer.analyze(event)
        assert severity == AuditSeverity.LOW

    def test_analyze_medium_severity_event(self):
        """测试中等严重程度事件分析."""
        event = Mock()
        event.action = "update"
        event.details = {}

        severity = self.analyzer.analyze(event)
        assert severity == AuditSeverity.MEDIUM

    def test_analyze_high_severity_event(self):
        """测试高严重程度事件分析."""
        event = Mock()
        event.action = "delete"
        event.details = {}

        severity = self.analyzer.analyze(event)
        assert severity == AuditSeverity.HIGH

    def test_analyze_critical_severity_event(self):
        """测试严重程度事件分析."""
        event = Mock()
        event.action = "delete"
        event.details = {"critical_system": True}

        severity = self.analyzer.analyze(event)
        assert severity == AuditSeverity.CRITICAL

    def test_analyze_login_event(self):
        """测试登录事件分析."""
        event = Mock()
        event.action = "login"
        event.details = {}

        severity = self.analyzer.analyze(event)
        # 登录事件通常为中等严重程度
        assert severity in [AuditSeverity.LOW, AuditSeverity.MEDIUM]

    def test_analyze_logout_event(self):
        """测试登出事件分析."""
        event = Mock()
        event.action = "logout"
        event.details = {}

        severity = self.analyzer.analyze(event)
        # 登出事件通常为低严重程度
        assert severity == AuditSeverity.LOW

    def test_analyze_unknown_action(self):
        """测试未知动作分析."""
        event = Mock()
        event.action = "unknown_action"
        event.details = {}

        severity = self.analyzer.analyze(event)
        # 未知动作默认为中等严重程度
        assert severity == AuditSeverity.MEDIUM


class TestAuditEvent:
    """审计事件测试类."""

    def test_audit_event_initialization_minimal(self):
        """测试审计事件最小初始化."""
        action = AuditAction.LOGIN
        user = "test_user"

        event = AuditEvent(action=action, user=user)

        # 验证基本属性
        assert event.action == action
        assert event.user == user
        assert event.details == {}

    def test_audit_event_initialization_full(self):
        """测试审计事件完整初始化."""
        action = AuditAction.UPDATE
        user = "test_user"
        details = {"target": "user_profile", "changes": ["email"]}

        event = AuditEvent(action=action, user=user, details=details)

        # 验证完整属性
        assert event.action == action
        assert event.user == user
        assert event.details == details

    def test_audit_event_timestamp(self):
        """测试审计事件时间戳."""
        event = AuditEvent(action=AuditAction.READ, user="test_user")

        # 验证时间戳被设置
        assert hasattr(event, "timestamp")
        assert isinstance(event.timestamp, datetime)

    def test_audit_event_id(self):
        """测试审计事件ID."""
        event = AuditEvent(action=AuditAction.CREATE, user="test_user")

        # 验证ID被生成
        assert hasattr(event, "id")
        assert isinstance(event.id, str)
        assert len(event.id) > 0

    def test_audit_event_serialization(self):
        """测试审计事件序列化."""
        action = AuditAction.DELETE
        user = "test_user"
        details = {"target": "record_123"}

        event = AuditEvent(action=action, user=user, details=details)

        # 验证可以转换为字典
        if hasattr(event, "to_dict"):
            result = event.to_dict()
            assert isinstance(result, dict)
            assert result["action"] == action
            assert result["user"] == user


class TestAuditService:
    """审计服务测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        self.audit_service = AuditService()

    def test_audit_service_initialization(self):
        """测试审计服务初始化."""
        service = AuditService()

        # 验证初始化
        assert service is not None
        assert hasattr(service, "logs")
        assert hasattr(service, "sanitizer")
        assert hasattr(service, "analyzer")

    def test_log_event_basic(self):
        """测试基本事件记录."""
        action = "login"
        user = "test_user"
        details = {"ip": "192.168.1.1"}

        # 记录事件
        self.audit_service.log_event(action, user, details)

        # 验证事件被记录
        assert len(self.audit_service.logs) > 0
        last_log = self.audit_service.logs[-1]
        assert last_log.event.action == action
        assert last_log.event.user == user

    def test_log_event_with_context(self):
        """测试带上下文的事件记录."""
        action = "update"
        user = "test_user"
        details = {"target": "profile"}
        context = AuditContext(
            user_id=user, session_id="session123", ip_address="192.168.1.1"
        )

        self.audit_service.log_event(action, user, details, context)

        # 验证上下文被记录
        assert len(self.audit_service.logs) > 0
        last_log = self.audit_service.logs[-1]
        assert last_log.context.user_id == user
        assert last_log.context.session_id == "session123"

    def test_log_event_sanitization(self):
        """测试事件记录时的数据清理."""
        action = "create"
        user = "test_user"
        details = {"username": "test_user", "password": "secret123"}

        self.audit_service.log_event(action, user, details)

        # 验证敏感数据被清理
        last_log = self.audit_service.logs[-1]
        assert "password" in last_log.event.details
        assert last_log.event.details["password"] == "[REDACTED]"

    def test_get_events_empty(self):
        """测试获取事件列表 - 空列表."""
        events = self.audit_service.get_events()
        assert events == []

    def test_get_events_with_data(self):
        """测试获取事件列表 - 有数据."""
        # 记录一些事件
        for i in range(5):
            self.audit_service.log_event("action", f"user{i}", {"index": i})

        events = self.audit_service.get_events()

        # 验证返回的事件
        assert len(events) == 5
        assert events[0].event.user == "user0"
        assert events[4].event.user == "user4"

    def test_get_events_with_limit(self):
        """测试获取事件列表 - 带限制."""
        # 记录一些事件
        for i in range(10):
            self.audit_service.log_event("action", f"user{i}", {"index": i})

        events = self.audit_service.get_events(limit=3)

        # 验证限制生效
        assert len(events) <= 3

    def test_get_summary_empty(self):
        """测试获取摘要 - 空日志."""
        summary = self.audit_service.get_summary()

        # 验证空日志摘要
        assert summary.total_events == 0
        assert summary.error_count == 0
        assert summary.warning_count == 0

    def test_get_summary_with_events(self):
        """测试获取摘要 - 有事件."""
        # 记录一些事件
        self.audit_service.log_event("login", "user1", {})
        self.audit_service.log_event("delete", "user2", {"critical": True})
        self.audit_service.log_event("read", "user3", {})

        summary = self.audit_service.get_summary()

        # 验证摘要统计
        assert summary.total_events == 3
        assert summary.last_updated is not None

    def test_multiple_services_isolation(self):
        """测试多个服务实例隔离."""
        service1 = AuditService()
        service2 = AuditService()

        # 在不同服务中记录事件
        service1.log_event("login", "user1", {})
        service2.log_event("login", "user2", {})

        # 验证事件隔离
        events1 = service1.get_events()
        events2 = service2.get_events()

        assert len(events1) == 1
        assert len(events2) == 1
        assert events1[0].event.user == "user1"
        assert events2[0].event.user == "user2"

    def test_concurrent_logging(self):
        """测试并发日志记录."""
        import threading

        results = []

        def log_events(service, user_id, results_list):
            for i in range(5):
                service.log_event("action", f"{user_id}_{i}", {"thread": user_id})
                results_list.append(f"{user_id}_{i}")

        # 创建多个线程
        service = AuditService()
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=log_events, args=(service, f"thread{i}", results)
            )
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有事件都被记录
        events = service.get_events()
        assert len(events) == 15  # 3 threads * 5 events each
