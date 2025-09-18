"""
审计服务综合测试模块
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.database.models.audit_log import AuditAction, AuditSeverity
from src.services.audit_service import AuditContext, AuditService


class TestAuditContext:
    """审计上下文测试"""

    def test_audit_context_initialization(self):
        """测试审计上下文初始化"""
        context = AuditContext(
            user_id="test_user",
            username="testuser",
            user_role="admin",
            session_id="session123",
            ip_address="192.168.1.1",
            user_agent="test-agent",
        )

        assert context.user_id == "test_user"
        assert context.username == "testuser"
        assert context.user_role == "admin"
        assert context.session_id == "session123"
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "test-agent"

    def test_audit_context_to_dict(self):
        """测试审计上下文转换为字典"""
        context = AuditContext(
            user_id="test_user", username="testuser", user_role="admin"
        )

        result = context.to_dict()
        expected = {
            "user_id": "test_user",
            "username": "testuser",
            "user_role": "admin",
            "session_id": None,
            "ip_address": None,
            "user_agent": None,
        }

        assert result == expected

    def test_audit_context_minimal_init(self):
        """测试审计上下文最小初始化"""
        context = AuditContext(user_id="test_user")

        assert context.user_id == "test_user"
        assert context.username is None
        assert context.user_role is None
        assert context.session_id is None
        assert context.ip_address is None
        assert context.user_agent is None


class TestAuditService:
    """审计服务测试"""

    @pytest.fixture
    def audit_service(self):
        """创建审计服务实例"""
        with patch("src.services.audit_service.DatabaseManager"):
            service = AuditService()
            service.db_manager = Mock()
            return service

    def test_audit_service_initialization(self, audit_service):
        """测试审计服务初始化"""
        assert audit_service.db_manager is not None
        assert audit_service.logger is not None
        assert isinstance(audit_service.sensitive_tables, set)
        assert isinstance(audit_service.sensitive_columns, set)

    def test_sensitive_data_configuration(self, audit_service):
        """测试敏感数据配置"""
        # 检查敏感表配置
        expected_tables = {
            "users",
            "permissions",
            "tokens",
            "passwords",
            "api_keys",
            "user_profiles",
            "payment_info",
            "personal_data",
        }
        assert expected_tables.issubset(audit_service.sensitive_tables)

        # 检查敏感列配置
        expected_columns = {"password", "token", "secret", "key"}
        assert expected_columns.issubset(audit_service.sensitive_columns)

    def test_hash_sensitive_data(self, audit_service):
        """测试敏感数据哈希"""
        sensitive_data = "password123"
        hashed = audit_service._hash_sensitive_data(sensitive_data)

        assert hashed != sensitive_data
        assert len(hashed) == 64  # SHA256 hex digest length
        assert isinstance(hashed, str)

    def test_sanitize_data_with_sensitive_fields(self, audit_service):
        """测试敏感字段数据清理"""
        data = {
            "username": "testuser",
            "password": "secret123",
            "email": "test@example.com",
            "token": "abc123",
        }

        sanitized = audit_service._sanitize_data(data)

        assert sanitized["username"] == "testuser"
        assert sanitized["email"] == "test@example.com"
        assert sanitized["password"] != "secret123"
        assert sanitized["token"] != "abc123"
        assert len(sanitized["password"]) == 64  # SHA256 hash
        assert len(sanitized["token"]) == 64

    def test_sanitize_data_without_sensitive_fields(self, audit_service):
        """测试无敏感字段数据清理"""
        data = {"username": "testuser", "email": "test@example.com", "age": 25}

        sanitized = audit_service._sanitize_data(data)

        assert sanitized == data

    def test_sanitize_data_with_nested_dict(self, audit_service):
        """测试嵌套字典数据清理"""
        data = {
            "user": {"username": "testuser", "password": "secret123"},
            "settings": {"theme": "dark", "api_key": "key123"},
        }

        sanitized = audit_service._sanitize_data(data)

        assert sanitized["user"]["username"] == "testuser"
        assert sanitized["user"]["password"] != "secret123"
        assert sanitized["settings"]["theme"] == "dark"
        assert sanitized["settings"]["api_key"] != "key123"

    def test_sanitize_data_with_list(self, audit_service):
        """测试列表数据清理"""
        data = {
            "users": [
                {"username": "user1", "password": "pass1"},
                {"username": "user2", "password": "pass2"},
            ]
        }

        sanitized = audit_service._sanitize_data(data)

        assert len(sanitized["users"]) == 2
        assert sanitized["users"][0]["username"] == "user1"
        assert sanitized["users"][0]["password"] != "pass1"
        assert sanitized["users"][1]["username"] == "user2"
        assert sanitized["users"][1]["password"] != "pass2"

    @patch("src.services.audit_service.datetime")
    def test_create_audit_log_entry(self, mock_datetime, audit_service):
        """测试创建审计日志条目"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        context = AuditContext(user_id="test_user", username="testuser")

        entry = audit_service._create_audit_log_entry(
            context=context,
            action=AuditAction.CREATE,
            table_name="users",
            record_id="123",
            success=True,
            duration_ms=100,
            new_data={"username": "testuser", "email": "test@example.com"},
            severity=AuditSeverity.MEDIUM,
        )

        assert entry.action == AuditAction.CREATE
        assert entry.table_name == "users"
        assert entry.record_id == "123"
        assert entry.user_id == "test_user"
        assert entry.username == "testuser"
        assert entry.severity == AuditSeverity.MEDIUM
        assert entry.timestamp == mock_now

    def test_is_sensitive_table(self, audit_service):
        """测试敏感表检查"""
        assert audit_service._is_sensitive_table("users") is True
        assert audit_service._is_sensitive_table("passwords") is True
        assert audit_service._is_sensitive_table("public_data") is False
        assert audit_service._is_sensitive_table("matches") is False

    def test_contains_pii(self, audit_service):
        """测试PII数据检查"""
        # 测试包含邮箱的数据
        data_with_email = {"email": "test@example.com", "name": "Test User"}
        assert audit_service._contains_pii(data_with_email) is True

        # 测试包含电话的数据
        data_with_phone = {"phone": "123-456-7890", "name": "Test User"}
        assert audit_service._contains_pii(data_with_phone) is True

        # 测试不包含PII的数据
        clean_data = {"name": "Test User", "age": 25}
        assert audit_service._contains_pii(clean_data) is False

    def test_determine_severity(self, audit_service):
        """测试严重级别确定"""
        # 敏感表操作
        severity = audit_service._determine_severity(
            AuditAction.DELETE, "users", {"password": "hash"}
        )
        assert severity == AuditSeverity.HIGH

        # 包含PII的操作
        severity = audit_service._determine_severity(
            AuditAction.UPDATE, "profiles", {"email": "test@example.com"}
        )
        assert severity == AuditSeverity.MEDIUM

        # 普通操作
        severity = audit_service._determine_severity(
            "matches", AuditAction.CREATE, {"score": "2-1"}
        )
        assert severity == AuditSeverity.MEDIUM

    @patch("src.services.audit_service.datetime")
    async def test_log_operation_success(self, mock_datetime, audit_service):
        """测试记录操作成功"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        # Mock database session
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        audit_service.db_manager.get_async_session.return_value = mock_context_manager

        context = AuditContext(user_id="test_user")

        await audit_service.log_operation(
            action=AuditAction.CREATE,
            table_name="users",
            record_id="123",
            context=context,
            new_data={"username": "testuser"},
        )

        # 验证数据库操作被调用
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_log_operation_database_error(self, audit_service):
        """测试记录操作数据库错误"""
        # Mock database session to raise exception
        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("Database error")
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        audit_service.db_manager.get_async_session.return_value = mock_context_manager

        context = AuditContext(user_id="test_user")

        # 应该不抛出异常，只记录错误
        await audit_service.log_operation(
            action=AuditAction.CREATE,
            table_name="users",
            record_id="123",
            context=context,
            new_data={"username": "testuser"},
        )

        # 验证回滚被调用
        mock_session.rollback.assert_called_once()

    def test_audit_decorator_function_success(self, audit_service):
        """测试审计装饰器成功情况"""

        @audit_service.audit_operation(AuditAction.CREATE, "users")
        def create_user(user_data):
            return {"id": "123", "username": user_data["username"]}

        # Mock context
        with patch("src.services.audit_service.audit_context") as mock_context:
            mock_context.get.return_value = {"user_id": "test_user"}

            with patch.object(audit_service, "log_operation") as mock_log:
                result = create_user({"username": "testuser"})

                assert result == {"id": "123", "username": "testuser"}
                # 验证审计日志被调用
                mock_log.assert_called_once()

    def test_extract_record_id_from_result(self, audit_service):
        """测试从结果提取记录ID"""
        # 测试字典结果
        result_dict = {"id": "123", "username": "testuser"}
        record_id = audit_service._extract_record_id(result_dict)
        assert record_id == "123"

        # 测试对象结果
        class MockResult:
            def __init__(self):
                self.id = "456"

        result_obj = MockResult()
        record_id = audit_service._extract_record_id(result_obj)
        assert record_id == "456"

        # 测试无ID的结果
        result_no_id = {"username": "testuser"}
        record_id = audit_service._extract_record_id(result_no_id)
        assert record_id == "unknown"
