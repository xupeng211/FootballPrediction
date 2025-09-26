"""
审计服务测试 - 覆盖率提升版本

针对 audit_service.py 的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import asyncio
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock, AsyncMock
from typing import Any, Dict, List, Optional
import json

from src.services.audit_service import (
    AuditContext,
    AuditService,
    audit_operation,
    audit_database_operation,
    audit_create,
    audit_read,
    audit_update,
    audit_delete,
    extract_request_context
)
from src.database.models.audit_log import AuditAction, AuditLog, AuditSeverity


class TestAuditContext:
    """审计上下文测试类"""

    def test_init_minimal(self):
        """测试最小初始化"""
        context = AuditContext(user_id="user_123")

        assert context.user_id == "user_123"
        assert context.username is None
        assert context.user_role is None
        assert context.session_id is None
        assert context.ip_address is None
        assert context.user_agent is None

    def test_init_full(self):
        """测试完整初始化"""
        context = AuditContext(
            user_id="user_123",
            username="test_user",
            user_role="admin",
            session_id="session_456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        assert context.user_id == "user_123"
        assert context.username == "test_user"
        assert context.user_role == "admin"
        assert context.session_id == "session_456"
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "Mozilla/5.0"

    def test_to_dict(self):
        """测试转换为字典"""
        context = AuditContext(
            user_id="user_123",
            username="test_user",
            user_role="admin",
            session_id="session_456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        result = context.to_dict()

        assert isinstance(result, dict)
        assert result["user_id"] == "user_123"
        assert result["username"] == "test_user"
        assert result["user_role"] == "admin"
        assert result["session_id"] == "session_456"
        assert result["ip_address"] == "192.168.1.1"
        assert result["user_agent"] == "Mozilla/5.0"

    def test_to_dict_minimal(self):
        """测试最小字典转换"""
        context = AuditContext(user_id="user_123")
        result = context.to_dict()

        assert result["user_id"] == "user_123"
        assert result["username"] is None
        assert result["user_role"] is None


class TestAuditService:
    """审计服务测试类"""

    def test_init(self):
        """测试初始化"""
        service = AuditService()

        assert service.db_manager is not None
        assert service.logger is not None
        assert len(service.sensitive_tables) > 0
        assert len(service.sensitive_columns) > 0
        assert len(service.high_risk_actions) > 0

        # 验证敏感表配置
        assert "users" in service.sensitive_tables
        assert "passwords" in service.sensitive_tables
        assert "tokens" in service.sensitive_tables

        # 验证敏感列配置
        assert "password" in service.sensitive_columns
        assert "token" in service.sensitive_columns
        assert "email" in service.sensitive_columns

        # 验证高风险操作配置
        assert AuditAction.DELETE in service.high_risk_actions
        assert AuditAction.GRANT in service.high_risk_actions
        assert AuditAction.REVOKE in service.high_risk_actions

    def test_hash_sensitive_value(self):
        """测试敏感值哈希"""
        service = AuditService()

        # 测试空值
        result = service._hash_sensitive_value("")
        assert result == ""

        result = service._hash_sensitive_value(None)
        assert result == ""

        # 测试正常值
        test_value = "password123"
        result = service._hash_sensitive_value(test_value)

        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex length
        assert result != test_value

        # 验证哈希一致性
        result2 = service._hash_sensitive_value(test_value)
        assert result == result2

    def test_hash_sensitive_data_alias(self):
        """测试敏感数据哈希别名方法"""
        service = AuditService()

        test_data = "secret_data"
        result1 = service._hash_sensitive_value(test_data)
        result2 = service._hash_sensitive_data(test_data)

        assert result1 == result2

    def test_sanitize_data_dict(self):
        """测试字典数据清理"""
        service = AuditService()

        data = {
            "username": "test_user",
            "password": "secret123",
            "email": "test@example.com",
            "profile": {
                "name": "Test User",
                "token": "bearer_token"
            },
            "tags": ["tag1", "tag2"]
        }

        result = service._sanitize_data(data)

        assert isinstance(result, dict)
        assert result["username"] == "test_user"
        assert result["password"] != "secret123"  # Should be hashed
        assert result["email"] == "test@example.com"
        assert isinstance(result["profile"], dict)
        assert result["profile"]["name"] == "Test User"
        assert result["profile"]["token"] != "bearer_token"  # Should be hashed
        assert result["tags"] == ["tag1", "tag2"]

    def test_sanitize_data_non_dict(self):
        """测试非字典数据清理"""
        service = AuditService()

        # 测试非字典输入
        result = service._sanitize_data("not a dict")
        assert result == "not a dict"

        result = service._sanitize_data(123)
        assert result == 123

        result = service._sanitize_data(["list", "of", "items"])
        assert result == ["list", "of", "items"]

    def test_sanitize_data_list_of_dicts(self):
        """测试字典列表数据清理"""
        service = AuditService()

        data = {
            "users": [
                {"name": "user1", "password": "pass1"},
                {"name": "user2", "password": "pass2"}
            ]
        }

        result = service._sanitize_data(data)

        assert isinstance(result, dict)
        assert isinstance(result["users"], list)
        assert len(result["users"]) == 2
        assert result["users"][0]["name"] == "user1"
        assert result["users"][0]["password"] != "pass1"  # Should be hashed
        assert result["users"][1]["name"] == "user2"
        assert result["users"][1]["password"] != "pass2"  # Should be hashed

    def test_is_sensitive_table(self):
        """测试敏感表判断"""
        service = AuditService()

        # 测试敏感表
        assert service._is_sensitive_table("users") is True
        assert service._is_sensitive_table("passwords") is True
        assert service._is_sensitive_table("tokens") is True

        # 测试非敏感表
        assert service._is_sensitive_table("matches") is False
        assert service._is_sensitive_table("teams") is False
        assert service._is_sensitive_table("predictions") is False

        # 测试大小写不敏感
        assert service._is_sensitive_table("USERS") is True
        assert service._is_sensitive_table("Users") is True

        # 测试非字符串输入
        assert service._is_sensitive_table(123) is False
        assert service._is_sensitive_table(None) is False

    def test_contains_pii(self):
        """测试PII数据检测"""
        service = AuditService()

        # 测试包含PII的数据
        data_with_pii = {
            "email": "user@example.com",
            "phone": "123-456-7890",
            "ssn": "123-45-6789"
        }
        assert service._contains_pii(data_with_pii) is True

        # 测试不包含PII的数据
        data_without_pii = {
            "name": "John Doe",
            "age": 30,
            "city": "New York"
        }
        assert service._contains_pii(data_without_pii) is False

        # 测试嵌套PII数据
        nested_data = {
            "user": {
                "email": "user@example.com",
                "profile": {"name": "John"}
            }
        }
        assert service._contains_pii(nested_data) is True

        # 测试非字典输入
        assert service._contains_pii("not a dict") is False
        assert service._contains_pii(123) is False
        assert service._contains_pii(None) is False

    def test_create_audit_log_entry(self):
        """测试创建审计日志条目"""
        service = AuditService()
        context = AuditContext(
            user_id="user_123",
            username="test_user",
            user_role="admin"
        )

        # 测试基本参数
        log_entry = service._create_audit_log_entry(
            context=context,
            action="CREATE",
            table_name="users",
            record_id="record_456",
            success=True,
            duration_ms=100
        )

        assert isinstance(log_entry, AuditLog)
        assert log_entry.user_id == "user_123"
        assert log_entry.username == "test_user"
        assert log_entry.action == "CREATE"
        assert log_entry.table_name == "users"
        assert log_entry.record_id == "record_456"
        assert log_entry.success is True
        assert log_entry.duration_ms == 100
        assert log_entry.severity == AuditSeverity.INFO  # Default severity
        assert isinstance(log_entry.timestamp, datetime)

        # 测试带severity参数
        log_entry_with_severity = service._create_audit_log_entry(
            context=context,
            action="DELETE",
            table_name="users",
            record_id="record_456",
            success=False,
            duration_ms=200,
            severity="CRITICAL"
        )

        assert log_entry_with_severity.severity == "CRITICAL"

    @patch('src.services.audit_service.DatabaseManager')
    def test_log_operation_success(self, mock_db_manager):
        """测试成功记录操作"""
        # Mock database manager
        mock_session = AsyncMock()
        mock_db_manager.return_value.get_session.return_value = mock_session

        service = AuditService()
        context = AuditContext(user_id="user_123")

        # 测试成功操作记录
        result = asyncio.run(service.log_operation(
            context=context,
            action="CREATE",
            table_name="users",
            record_id="record_456",
            old_data=None,
            new_data={"name": "John Doe", "email": "john@example.com"},
            success=True,
            duration_ms=100
        ))

        assert result is True
        assert mock_session.add.called
        assert mock_session.commit.called

    @patch('src.services.audit_service.DatabaseManager')
    def test_log_operation_failure(self, mock_db_manager):
        """测试失败操作记录"""
        # Mock database manager with failure
        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("Database error")
        mock_db_manager.return_value.get_session.return_value = mock_session

        service = AuditService()
        context = AuditContext(user_id="user_123")

        # 测试失败操作记录
        result = asyncio.run(service.log_operation(
            context=context,
            action="DELETE",
            table_name="users",
            record_id="record_456",
            old_data={"name": "John Doe"},
            new_data=None,
            success=False,
            duration_ms=200
        ))

        assert result is False
        assert mock_session.add.called
        assert mock_session.rollback.called

    @patch('src.services.audit_service.DatabaseManager')
    def test_get_user_audit_summary(self, mock_db_manager):
        """测试获取用户审计摘要"""
        # Mock database query results
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            Mock(action="CREATE", table_name="users", success=True, timestamp=datetime.now()),
            Mock(action="UPDATE", table_name="users", success=True, timestamp=datetime.now()),
            Mock(action="DELETE", table_name="users", success=False, timestamp=datetime.now())
        ]
        mock_session.execute.return_value = mock_result
        mock_db_manager.return_value.get_session.return_value = mock_session

        service = AuditService()

        # 测试获取审计摘要
        summary = asyncio.run(service.get_user_audit_summary("user_123"))

        assert isinstance(summary, dict)
        assert "total_operations" in summary
        assert "successful_operations" in summary
        assert "failed_operations" in summary
        assert "last_activity" in summary
        assert summary["total_operations"] == 3
        assert summary["successful_operations"] == 2
        assert summary["failed_operations"] == 1

    @patch('src.services.audit_service.DatabaseManager')
    def test_get_high_risk_operations(self, mock_db_manager):
        """测试获取高风险操作"""
        # Mock database query results
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            Mock(
                user_id="user_123",
                username="admin_user",
                action="DELETE",
                table_name="users",
                success=True,
                timestamp=datetime.now(),
                ip_address="192.168.1.1"
            )
        ]
        mock_session.execute.return_value = mock_result
        mock_db_manager.return_value.get_session.return_value = mock_session

        service = AuditService()

        # 测试获取高风险操作
        operations = asyncio.run(service.get_high_risk_operations(hours=24))

        assert isinstance(operations, list)
        assert len(operations) == 1
        assert operations[0].action == "DELETE"
        assert operations[0].table_name == "users"

    def test_async_log_action_success(self):
        """测试异步日志记录成功"""
        service = AuditService()
        context = AuditContext(user_id="user_123")

        # Mock log_operation method
        service.log_operation = AsyncMock(return_value=True)

        # Test async decorator
        @service.async_log_action("users", "CREATE")
        async def test_create_user(user_data):
            return {"id": "new_user", **user_data}

        # 测试异步操作
        result = asyncio.run(test_create_user({"name": "John Doe"}))

        assert result["id"] == "new_user"
        assert result["name"] == "John Doe"
        service.log_operation.assert_called_once()

    def test_async_log_action_failure(self):
        """测试异步日志记录失败"""
        service = AuditService()
        context = AuditContext(user_id="user_123")

        # Mock log_operation method
        service.log_operation = AsyncMock(return_value=False)

        @service.async_log_action("users", "CREATE")
        async def test_create_user(user_data):
            return {"id": "new_user", **user_data}

        # 测试异步操作
        result = asyncio.run(test_create_user({"name": "John Doe"}))

        assert result["id"] == "new_user"
        service.log_operation.assert_called_once()


class TestAuditDecorators:
    """审计装饰器测试类"""

    def test_audit_operation_sync(self):
        """测试同步审计操作装饰器"""
        @audit_operation("users", "CREATE")
        def create_user(user_data):
            return {"id": "new_user", **user_data}

        # Mock audit context
        with patch('src.services.audit_service.audit_context') as mock_context:
            mock_context.get.return_value = {"user_id": "user_123"}

            # Mock audit service
            with patch('src.services.audit_service.AuditService') as mock_service_class:
                mock_service = Mock()
                mock_service.log_operation = AsyncMock(return_value=True)
                mock_service_class.return_value = mock_service

                # 测试装饰器函数
                result = create_user({"name": "John Doe"})

                assert result["id"] == "new_user"
                assert result["name"] == "John Doe"

    def test_audit_operation_async(self):
        """测试异步审计操作装饰器"""
        @audit_operation("users", "UPDATE")
        async def update_user(user_id, user_data):
            return {"id": user_id, **user_data}

        # Mock audit context
        with patch('src.services.audit_service.audit_context') as mock_context:
            mock_context.get.return_value = {"user_id": "user_123"}

            # Mock audit service
            with patch('src.services.audit_service.AuditService') as mock_service_class:
                mock_service = Mock()
                mock_service.log_operation = AsyncMock(return_value=True)
                mock_service_class.return_value = mock_service

                # 测试装饰器函数
                result = asyncio.run(update_user("user_456", {"name": "Jane Doe"}))

                assert result["id"] == "user_456"
                assert result["name"] == "Jane Doe"

    def test_audit_database_operation_sync(self):
        """测试同步数据库审计操作装饰器"""
        @audit_database_operation("profiles")
        def update_profile(profile_id, profile_data):
            return {"id": profile_id, **profile_data}

        # Mock audit context
        with patch('src.services.audit_service.audit_context') as mock_context:
            mock_context.get.return_value = {"user_id": "user_123"}

            # Mock audit service
            with patch('src.services.audit_service.AuditService') as mock_service_class:
                mock_service = Mock()
                mock_service.log_operation = AsyncMock(return_value=True)
                mock_service_class.return_value = mock_service

                # 测试装饰器函数
                result = update_profile("profile_789", {"name": "Updated Profile"})

                assert result["id"] == "profile_789"
                assert result["name"] == "Updated Profile"

    def test_audit_database_operation_async(self):
        """测试异步数据库审计操作装饰器"""
        @audit_database_operation("predictions")
        async def create_prediction(prediction_data):
            return {"id": "pred_123", **prediction_data}

        # Mock audit context
        with patch('src.services.audit_service.audit_context') as mock_context:
            mock_context.get.return_value = {"user_id": "user_123"}

            # Mock audit service
            with patch('src.services.audit_service.AuditService') as mock_service_class:
                mock_service = Mock()
                mock_service.log_operation = AsyncMock(return_value=True)
                mock_service_class.return_value = mock_service

                # 测试装饰器函数
                result = asyncio.run(create_prediction({"match_id": "match_456"}))

                assert result["id"] == "pred_123"
                assert result["match_id"] == "match_456"

    def test_audit_create_decorator(self):
        """测试创建操作装饰器"""
        @audit_create("users")
        def create_user(user_data):
            return {"id": "new_user", **user_data}

        # Mock audit context
        with patch('src.services.audit_service.audit_context') as mock_context:
            mock_context.get.return_value = {"user_id": "user_123"}

            # Mock audit service
            with patch('src.services.audit_service.AuditService') as mock_service_class:
                mock_service = Mock()
                mock_service.log_operation = AsyncMock(return_value=True)
                mock_service_class.return_value = mock_service

                result = create_user({"name": "John Doe"})
                assert result["id"] == "new_user"

    def test_audit_read_decorator(self):
        """测试读取操作装饰器"""
        @audit_read("users")
        def get_user(user_id):
            return {"id": user_id, "name": "John Doe"}

        # Mock audit context
        with patch('src.services.audit_service.audit_context') as mock_context:
            mock_context.get.return_value = {"user_id": "user_123"}

            # Mock audit service
            with patch('src.services.audit_service.AuditService') as mock_service_class:
                mock_service = Mock()
                mock_service.log_operation = AsyncMock(return_value=True)
                mock_service_class.return_value = mock_service

                result = get_user("user_456")
                assert result["id"] == "user_456"

    def test_audit_update_decorator(self):
        """测试更新操作装饰器"""
        @audit_update("users")
        def update_user(user_id, user_data):
            return {"id": user_id, **user_data}

        # Mock audit context
        with patch('src.services.audit_service.audit_context') as mock_context:
            mock_context.get.return_value = {"user_id": "user_123"}

            # Mock audit service
            with patch('src.services.audit_service.AuditService') as mock_service_class:
                mock_service = Mock()
                mock_service.log_operation = AsyncMock(return_value=True)
                mock_service_class.return_value = mock_service

                result = update_user("user_456", {"name": "Jane Doe"})
                assert result["id"] == "user_456"

    def test_audit_delete_decorator(self):
        """测试删除操作装饰器"""
        @audit_delete("users")
        def delete_user(user_id):
            return {"deleted": True, "id": user_id}

        # Mock audit context
        with patch('src.services.audit_service.audit_context') as mock_context:
            mock_context.get.return_value = {"user_id": "user_123"}

            # Mock audit service
            with patch('src.services.audit_service.AuditService') as mock_service_class:
                mock_service = Mock()
                mock_service.log_operation = AsyncMock(return_value=True)
                mock_service_class.return_value = mock_service

                result = delete_user("user_456")
                assert result["deleted"] is True


class TestAuditIntegration:
    """审计服务集成测试"""

    @patch('src.services.audit_service.os.environ.get')
    def test_environment_configuration(self, mock_get):
        """测试环境配置"""
        # Mock environment variables
        mock_get.side_effect = lambda key, default=None: {
            'AUDIT_LOG_LEVEL': 'DEBUG',
            'AUDIT_SENSITIVE_TABLES': 'users,tokens,passwords',
            'AUDIT_HIGH_RISK_ACTIONS': 'DELETE,GRANT,REVOKE'
        }.get(key, default)

        # Test that environment variables can be accessed
        from src.services.audit_service import logger
        assert logger is not None

    def test_sensitive_data_detection(self):
        """测试敏感数据检测"""
        service = AuditService()

        # Test various sensitive data patterns
        sensitive_data_patterns = [
            {"password": "secret123"},
            {"token": "bearer_token"},
            {"api_key": "sk_test_123"},
            {"credit_card": "4111111111111111"},
            {"ssn": "123-45-6789"},
            {"email": "user@example.com"},
            {"phone": "123-456-7890"}
        ]

        for data in sensitive_data_patterns:
            assert service._contains_pii(data) is True

    def test_data_sanitization_comprehensive(self):
        """测试数据清理全面性"""
        service = AuditService()

        # Test complex nested data structure
        complex_data = {
            "user": {
                "name": "John Doe",
                "password": "secret123",
                "profile": {
                    "email": "john@example.com",
                    "phone": "123-456-7890",
                    "preferences": {
                        "notifications": True,
                        "api_key": "secret_key"
                    }
                }
            },
            "metadata": [
                {"type": "login", "token": "session_token"},
                {"type": "logout", "timestamp": "2024-01-01"}
            ]
        }

        sanitized = service._sanitize_data(complex_data)

        # Verify sensitive data is hashed
        assert sanitized["user"]["password"] != "secret123"
        assert sanitized["user"]["profile"]["email"] == "john@example.com"  # Not high sensitive
        assert sanitized["user"]["profile"]["phone"] == "123-456-7890"  # Not high sensitive
        assert sanitized["user"]["profile"]["preferences"]["api_key"] != "secret_key"
        assert sanitized["metadata"][0]["token"] != "session_token"

        # Verify non-sensitive data is preserved
        assert sanitized["user"]["name"] == "John Doe"
        assert sanitized["user"]["profile"]["preferences"]["notifications"] is True

    def test_hashing_consistency(self):
        """测试哈希一致性"""
        service = AuditService()

        # Test same input produces same hash
        test_values = ["password123", "api_key_secret", "token_value"]

        for value in test_values:
            hash1 = service._hash_sensitive_value(value)
            hash2 = service._hash_sensitive_value(value)
            assert hash1 == hash2
            assert len(hash1) == 64

        # Test different inputs produce different hashes
        hash1 = service._hash_sensitive_value("value1")
        hash2 = service._hash_sensitive_value("value2")
        assert hash1 != hash2

    def test_audit_context_management(self):
        """测试审计上下文管理"""
        # Test context creation and conversion
        context = AuditContext(
            user_id="user_123",
            username="test_user",
            user_role="admin",
            session_id="session_456"
        )

        # Test context serialization
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)
        assert context_dict["user_id"] == "user_123"
        assert context_dict["username"] == "test_user"

        # Test context with minimal data
        minimal_context = AuditContext(user_id="user_789")
        minimal_dict = minimal_context.to_dict()
        assert minimal_dict["user_id"] == "user_789"
        assert minimal_dict["username"] is None

    def test_error_handling(self):
        """测试错误处理"""
        service = AuditService()

        # Test sanitization with invalid input
        assert service._sanitize_data(None) is None
        assert service._sanitize_data(123) == 123
        assert service._sanitize_data("string") == "string"

        # Test PII detection with invalid input
        assert service._contains_pii(None) is False
        assert service._contains_pii(123) is False
        assert service._contains_pii("string") is False

        # Test sensitive table detection with invalid input
        assert service._is_sensitive_table(None) is False
        assert service._is_sensitive_table(123) is False

        # Test hashing with invalid input
        assert service._hash_sensitive_value("") == ""
        assert service._hash_sensitive_value(None) == ""


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])