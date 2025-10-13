"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

审计服务测试
Tests for Audit Service

测试src.services.audit_service模块的功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 测试导入
try:
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

    AUDIT_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    AUDIT_AVAILABLE = False


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestAuditSeverity:
    """审计严重程度测试"""

    def test_severity_values(self):
        """测试：严重程度枚举值"""
        assert AuditSeverity.LOW.value == "low"
        assert AuditSeverity.MEDIUM.value == "medium"
        assert AuditSeverity.HIGH.value == "high"
        assert AuditSeverity.CRITICAL.value == "critical"

    def test_severity_comparison(self):
        """测试：严重程度比较"""
        # 测试枚举值比较
        assert AuditSeverity.LOW == AuditSeverity.LOW
        assert AuditSeverity.LOW != AuditSeverity.HIGH

    def test_severity_iteration(self):
        """测试：严重程度迭代"""
        severities = list(AuditSeverity)
        assert AuditSeverity.LOW in severities
        assert AuditSeverity.MEDIUM in severities
        assert AuditSeverity.HIGH in severities
        assert AuditSeverity.CRITICAL in severities


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestAuditAction:
    """审计动作测试"""

    def test_action_constants(self):
        """测试：动作常量"""
        assert AuditAction.CREATE == "create"
        assert AuditAction.READ == "read"
        assert AuditAction.UPDATE == "update"
        assert AuditAction.DELETE == "delete"
        assert AuditAction.LOGIN == "login"
        assert AuditAction.LOGOUT == "logout"
        assert AuditAction.EXPORT == "export"

    def test_action_combinations(self):
        """测试：动作组合"""
        actions = [
            AuditAction.CREATE,
            AuditAction.READ,
            AuditAction.UPDATE,
            AuditAction.DELETE,
        ]
        assert len(set(actions)) == 4  # 确保没有重复


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestAuditContext:
    """审计上下文测试"""

    def test_context_creation_minimal(self):
        """测试：创建最小上下文"""
        context = AuditContext(user_id="user123")

        assert context.user_id == "user123"
        assert context.session_id is None
        assert context.ip_address is None
        assert isinstance(context.timestamp, datetime)

    def test_context_creation_full(self):
        """测试：创建完整上下文"""
        context = AuditContext(
            user_id="user456", session_id="session789", ip_address="192.168.1.1"
        )

        assert context.user_id == "user456"
        assert context.session_id == "session789"
        assert context.ip_address == "192.168.1.1"
        assert isinstance(context.timestamp, datetime)

    def test_context_timestamp_auto(self):
        """测试：自动生成时间戳"""
        before = datetime.utcnow()
        context = AuditContext(user_id="test_user")
        after = datetime.utcnow()

        assert before <= context.timestamp <= after


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestAuditLog:
    """审计日志测试"""

    @pytest.fixture
    def sample_context(self):
        """示例上下文"""
        return AuditContext(user_id="user123", session_id="session456")

    def test_log_creation(self, sample_context):
        """测试：创建审计日志"""
        log = AuditLog(
            action=AuditAction.CREATE,
            context=sample_context,
            severity=AuditSeverity.MEDIUM,
            details={"resource": "prediction", "id": 789},
        )

        assert log.action == AuditAction.CREATE
        assert log.context.user_id == "user123"
        assert log.severity == AuditSeverity.MEDIUM
        assert log.details["resource"] == "prediction"
        assert log.details["id"] == 789
        assert isinstance(log.timestamp, datetime)

    def test_log_with_high_severity(self, sample_context):
        """测试：高严重性日志"""
        log = AuditLog(
            action=AuditAction.DELETE,
            context=sample_context,
            severity=AuditSeverity.CRITICAL,
            details={"resource": "user", "id": 123},
        )

        assert log.severity == AuditSeverity.CRITICAL
        assert log.action == AuditAction.DELETE

    def test_log_with_complex_details(self, sample_context):
        """测试：复杂详情日志"""
        complex_details = {
            "resource": "match",
            "id": 456,
            "changes": {
                "home_score": {"from": 1, "to": 2},
                "status": {"from": "IN_PLAY", "to": "FINISHED"},
            },
            "metadata": {"source": "api", "version": "v1.0"},
        }

        log = AuditLog(
            action=AuditAction.UPDATE,
            context=sample_context,
            severity=AuditSeverity.LOW,
            details=complex_details,
        )

        assert log.details["changes"]["home_score"]["to"] == 2
        assert log.details["metadata"]["source"] == "api"


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestAuditEvent:
    """审计事件测试"""

    def test_event_creation(self):
        """测试：创建审计事件"""
        event = AuditEvent(
            action=AuditAction.CREATE,
            _user ="test_user",
            severity=AuditSeverity.MEDIUM,
            details={"resource": "test"},
        )

        assert event.action == AuditAction.CREATE
        assert event._user == "test_user"
        assert event.severity == AuditSeverity.MEDIUM
        assert event.details["resource"] == "test"
        assert isinstance(event.timestamp, datetime)

    def test_event_with_different_actions(self):
        """测试：不同动作的事件"""
        actions = [
            AuditAction.LOGIN,
            AuditAction.UPDATE,
            AuditAction.DELETE,
            AuditAction.LOGOUT,
        ]

        for action in actions:
            event = AuditEvent(
                action=action, _user ="user123", severity=AuditSeverity.LOW, details={}
            )
            assert event.action == action

    def test_event_timestamp(self):
        """测试：事件时间戳"""
        before = datetime.utcnow()
        event = AuditEvent(
            action=AuditAction.READ,
            _user ="user456",
            severity=AuditSeverity.LOW,
            details={},
        )
        after = datetime.utcnow()

        assert before <= event.timestamp <= after


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestDataSanitizer:
    """数据清理器测试"""

    @pytest.fixture
    def sanitizer(self):
        """创建清理器实例"""
        return DataSanitizer()

    def test_sanitize_password(self, sanitizer):
        """测试：清理密码"""
        _data = {"username": "test", "password": "secret123"}
        sanitized = sanitizer.sanitize(data)

        assert sanitized["username"] == "test"
        assert sanitized["password"] == "***"

    def test_sanitize_token(self, sanitizer):
        """测试：清理令牌"""
        _data = {"token": "sk-1234567890", "user_id": 123}
        sanitized = sanitizer.sanitize(data)

        assert sanitized["user_id"] == 123
        assert sanitized["token"] == "***"

    def test_sanitize_multiple_sensitive_fields(self, sanitizer):
        """测试：清理多个敏感字段"""
        _data = {
            "username": "test",
            "password": "secret",
            "token": "abc123",
            "api_key": "def456",
            "normal_field": "value",
        }
        sanitized = sanitizer.sanitize(data)

        assert sanitized["username"] == "test"
        assert sanitized["normal_field"] == "value"
        assert sanitized["password"] == "***"
        assert sanitized["token"] == "***"
        # api_key 未在默认清理中，应该保留
        assert sanitized["api_key"] == "def456"

    def test_sanitize_empty_data(self, sanitizer):
        """测试：清理空数据"""
        _data = {}
        sanitized = sanitizer.sanitize(data)

        assert sanitized == {}

    def test_sanitize_nested_data(self, sanitizer):
        """测试：清理嵌套数据"""
        _data = {"user": {"username": "test", "password": "secret"}, "token": "abc123"}
        sanitized = sanitizer.sanitize(data)

        # 简化版清理器只处理顶层字段
        assert sanitized["token"] == "***"
        assert sanitized["user"]["password"] == "secret"  # 未清理嵌套字段


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestSeverityAnalyzer:
    """严重程度分析器测试"""

    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return SeverityAnalyzer()

    def test_analyze_delete_action(self, analyzer):
        """测试：分析删除动作"""
        event = AuditEvent(
            action="delete_user", _user ="admin", severity=AuditSeverity.LOW, details={}
        )

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.HIGH

    def test_analyze_modify_action(self, analyzer):
        """测试：分析修改动作"""
        event = AuditEvent(
            action="modify_config", _user ="admin", severity=AuditSeverity.LOW, details={}
        )

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.MEDIUM

    def test_analyze_other_action(self, analyzer):
        """测试：分析其他动作"""
        event = AuditEvent(
            action="read_data", _user ="user123", severity=AuditSeverity.LOW, details={}
        )

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.LOW

    def test_analyze_case_insensitive(self, analyzer):
        """测试：大小写不敏感分析"""
        event = AuditEvent(
            action="DELETE_USER", _user ="admin", severity=AuditSeverity.LOW, details={}
        )

        severity = analyzer.analyze(event)
        assert severity == AuditSeverity.HIGH


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestAuditService:
    """审计服务测试"""

    @pytest.fixture
    def audit_service(self):
        """创建审计服务实例"""
        return AuditService()

    def test_service_initialization(self, audit_service):
        """测试：服务初始化"""
        assert audit_service is not None
        assert isinstance(audit_service.events, list)
        assert len(audit_service.events) == 0
        assert hasattr(audit_service, "sanitizer")
        assert hasattr(audit_service, "analyzer")

    def test_log_event(self, audit_service):
        """测试：记录事件"""
        event = audit_service.log_event(
            action="create_prediction", _user ="user123", details={"prediction_id": 789}
        )

        assert event is not None
        assert event.action == "create_prediction"
        assert event._user == "user123"
        assert event.details["prediction_id"] == 789
        assert len(audit_service.events) == 1
        assert audit_service.events[0] is event

    def test_log_event_with_sanitization(self, audit_service):
        """测试：记录带清理的事件"""
        event = audit_service.log_event(
            action="login",
            _user ="user456",
            details={"username": "test", "password": "secret123"},
        )

        assert event.details["username"] == "test"
        assert event.details["password"] == "***"  # 应该被清理

    def test_log_multiple_events(self, audit_service):
        """测试：记录多个事件"""
        events = []

        for i in range(5):
            event = audit_service.log_event(
                action=f"action_{i}", _user =f"user_{i}", details={"index": i}
            )
            events.append(event)

        assert len(audit_service.events) == 5
        assert len(events) == 5

        # 验证事件顺序
        for i, event in enumerate(events):
            assert event.action == f"action_{i}"
            assert event._user == f"user_{i}"

    def test_get_events(self, audit_service):
        """测试：获取事件"""
        # 添加一些事件
        for i in range(10):
            audit_service.log_event(f"action_{i}", f"user_{i}", {"index": i})

        # 获取所有事件（默认限制100）
        all_events = audit_service.get_events()
        assert len(all_events) == 10

        # 获取限制数量的
        limited_events = audit_service.get_events(limit=5)
        assert len(limited_events) == 5

        # 验证获取的是最新的事件
        assert limited_events[-1].action == "action_9"

    def test_get_events_empty(self, audit_service):
        """测试：获取空事件列表"""
        events = audit_service.get_events()
        assert events == []

    def test_get_summary_empty(self, audit_service):
        """测试：获取空摘要"""
        summary = audit_service.get_summary()

        assert summary.total_logs == 0
        assert summary.by_severity == {}
        assert summary.by_action == {}

    def test_get_summary_with_events(self, audit_service):
        """测试：获取带事件的摘要"""
        # 添加不同类型的事件
        audit_service.log_event("delete_user", "admin", {})
        audit_service.log_event("create_prediction", "user1", {})
        audit_service.log_event("read_data", "user2", {})
        audit_service.log_event("modify_config", "admin", {})
        audit_service.log_event("delete_prediction", "user1", {})

        summary = audit_service.get_summary()

        assert summary.total_logs == 5

        # 验证严重程度统计
        assert summary.by_severity.get("high", 0) == 2  # 2个delete动作
        assert summary.by_severity.get("medium", 0) == 1  # 1个modify动作
        assert summary.by_severity.get("low", 0) == 2  # 其他动作

        # 验证动作统计
        assert summary.by_action["delete_user"] == 1
        assert summary.by_action["create_prediction"] == 1
        assert summary.by_action["read_data"] == 1
        assert summary.by_action["modify_config"] == 1
        assert summary.by_action["delete_prediction"] == 1

    def test_event_logging_with_logging(self, audit_service):
        """测试：事件记录时的日志"""
        with patch("src.services.audit_service.logger") as mock_logger:
            event = audit_service.log_event(
                action="test_action", _user ="test_user", details={}
            )

            mock_logger.info.assert_called_once_with(
                "Audit event logged: test_action by test_user"
            )
            assert event is not None

    def test_concurrent_logging(self, audit_service):
        """测试：并发记录日志"""
        import threading
        import time

        results = []

        def log_worker(worker_id):
            for i in range(10):
                audit_service.log_event(
                    action=f"worker_{worker_id}_action_{i}",
                    _user =f"worker_{worker_id}",
                    details={"iteration": i},
                )
                results.append((worker_id, i))

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有事件都被记录
        assert len(audit_service.events) == 50  # 5个线程 × 10个事件
        assert len(results) == 50

    def test_service_with_custom_sanitizer(self):
        """测试：使用自定义清理器的服务"""

        class CustomSanitizer:
            def sanitize(self, data):
                sanitized = data.copy()
                # 清理更多字段
                sensitive_fields = ["password", "token", "api_key", "secret"]
                for field in sensitive_fields:
                    if field in sanitized:
                        sanitized[field] = "****"
                return sanitized

        # 创建带自定义清理器的服务
        service = AuditService()
        service.sanitizer = CustomSanitizer()

        event = service.log_event(
            action="login",
            _user ="test",
            details={"password": "secret", "api_key": "abc123", "normal": "value"},
        )

        assert event.details["password"] == "****"
        assert event.details["api_key"] == "****"
        assert event.details["normal"] == "value"

    def test_service_with_custom_analyzer(self):
        """测试：使用自定义分析器的服务"""

        class CustomAnalyzer:
            def analyze(self, event):
                # 所有登录动作都是高风险
                if "login" in event.action.lower():
                    return AuditSeverity.HIGH
                return AuditSeverity.LOW

        # 创建带自定义分析器的服务
        service = AuditService()
        service.analyzer = CustomAnalyzer()

        event = service.log_event(action="login_attempt", _user ="test", details={})

        assert event.severity == AuditSeverity.HIGH

    def test_performance(self, audit_service):
        """测试：性能"""
        import time

        start_time = time.time()

        # 记录大量事件
        for i in range(1000):
            audit_service.log_event(
                action=f"action_{i}", _user ="perf_test", details={"index": i}
            )

        end_time = time.time()
        duration = end_time - start_time

        # 性能断言（应该在合理时间内完成）
        assert duration < 2.0  # 1000个事件应该在2秒内完成

        # 验证所有事件都被记录
        assert len(audit_service.events) == 1000


@pytest.mark.skipif(not AUDIT_AVAILABLE, reason="Audit service module not available")
class TestAuditLogSummary:
    """审计日志摘要测试"""

    def test_summary_creation(self):
        """测试：创建摘要"""
        summary = AuditLogSummary()

        assert summary.total_logs == 0
        assert summary.by_severity == {}
        assert summary.by_action == {}

    def test_summary_population(self):
        """测试：摘要数据填充"""
        summary = AuditLogSummary()
        summary.total_logs = 100
        summary.by_severity = {"low": 50, "medium": 30, "high": 20}
        summary.by_action = {"create": 40, "read": 35, "update": 25}

        assert summary.total_logs == 100
        assert summary.by_severity["low"] == 50
        assert summary.by_action["create"] == 40
