"""
audit_service.py 测试文件
测试权限审计服务功能，基于实际实现
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
import inspect

# 添加 src 目录到路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.services.audit_service import AuditContext, AuditService, audit_operation, audit_context
from src.database.models.audit_log import AuditAction, AuditSeverity


class TestAuditContext:
    """测试审计上下文管理器"""

    def test_audit_context_creation(self):
        """测试审计上下文创建"""
        context = AuditContext(
            user_id="user123",
            username="test_user",
            user_role="admin",
            session_id="session456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        assert context.user_id == "user123"
        assert context.username == "test_user"
        assert context.user_role == "admin"
        assert context.session_id == "session456"
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "Mozilla/5.0"

    def test_audit_context_minimal(self):
        """测试最小审计上下文创建"""
        context = AuditContext(user_id="user123")

        assert context.user_id == "user123"
        assert context.username is None
        assert context.user_role is None
        assert context.session_id is None
        assert context.ip_address is None
        assert context.user_agent is None

    def test_audit_context_to_dict(self):
        """测试审计上下文转换为字典"""
        context = AuditContext(
            user_id="user123",
            username="test_user",
            user_role="admin",
            session_id="session456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        context_dict = context.to_dict()

        assert context_dict["user_id"] == "user123"
        assert context_dict["username"] == "test_user"
        assert context_dict["user_role"] == "admin"
        assert context_dict["session_id"] == "session456"
        assert context_dict["ip_address"] == "192.168.1.1"
        assert context_dict["user_agent"] == "Mozilla/5.0"

    def test_audit_context_methods(self):
        """测试审计上下文方法"""
        context = AuditContext(user_id="user123", username="test_user")

        # 测试to_dict方法
        context_dict = context.to_dict()
        assert context_dict["user_id"] == "user123"
        assert context_dict["username"] == "test_user"

        # 测试基本属性
        assert context.user_id == "user123"
        assert context.username == "test_user"


class TestAuditService:
    """测试审计服务功能"""

    def test_audit_service_creation(self):
        """测试审计服务创建"""
        with patch('src.services.audit_service.DatabaseManager') as mock_db_manager:
            service = AuditService()

            assert service.db_manager is not None
            assert service.logger is not None
            assert "users" in service.sensitive_tables
            assert "password" in service.sensitive_columns
            assert AuditAction.DELETE in service.high_risk_actions

    def test_hash_sensitive_value(self):
        """测试敏感数据哈希处理"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试正常值
            hashed = service._hash_sensitive_value("test_password")
            assert len(hashed) == 64  # SHA256哈希长度
            assert hashed != "test_password"

            # 测试空值
            empty_hashed = service._hash_sensitive_value("")
            assert empty_hashed == ""

            # 测试None值
            none_hashed = service._hash_sensitive_value(None)
            assert none_hashed == ""

    def test_hash_sensitive_data_alias(self):
        """测试敏感数据哈希处理别名方法"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试别名方法
            hashed = service._hash_sensitive_data("test_data")
            expected = service._hash_sensitive_value("test_data")
            assert hashed == expected

    def test_sanitize_data(self):
        """测试数据清理"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试包含敏感数据的字典
            data = {
                "username": "test_user",
                "password": "secret123",
                "email": "test@example.com",
                "profile": {
                    "age": 25,
                    "token": "secret_token"
                }
            }

            sanitized = service._sanitize_data(data)

            assert sanitized["username"] == "test_user"
            assert len(sanitized["password"]) == 64  # 哈希后的密码
            assert sanitized["email"] == "test@example.com"  # 邮箱不被认为是高敏感字段
            assert sanitized["profile"]["age"] == 25
            assert len(sanitized["profile"]["token"]) == 64  # 嵌套的敏感数据也被哈希

    def test_is_sensitive_table(self):
        """测试敏感表判断"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试敏感表
            assert service._is_sensitive_table("users") is True
            assert service._is_sensitive_table("passwords") is True
            assert service._is_sensitive_table("api_keys") is True

            # 测试非敏感表
            assert service._is_sensitive_table("matches") is False
            assert service._is_sensitive_table("teams") is False

            # 测试None值
            assert service._is_sensitive_table(None) is False

    def test_is_sensitive_data_with_column(self):
        """测试敏感数据判断（包含列名）"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试敏感列
            assert service._is_sensitive_data(None, "password") is True
            assert service._is_sensitive_data(None, "api_key") is True
            assert service._is_sensitive_data(None, "credit_card") is True

            # 测试非敏感列
            assert service._is_sensitive_data(None, "username") is False
            assert service._is_sensitive_data(None, "score") is False

            # 测试表和列组合
            assert service._is_sensitive_data("users", "email") is True
            assert service._is_sensitive_data("matches", "home_team_id") is False

    def test_contains_pii(self):
        """测试PII数据判断"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试包含PII的数据
            pii_data = {"email": "test@example.com", "phone": "1234567890"}
            assert service._contains_pii(pii_data) is True

            # 测试不包含PII的数据
            non_pii_data = {"username": "test_user", "age": 25}
            assert service._contains_pii(non_pii_data) is False

            # 测试空数据
            assert service._contains_pii({}) is False
            assert service._contains_pii(None) is False

    def test_determine_severity(self):
        """测试严重程度判断"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试高风险操作
            assert service._determine_severity(AuditAction.DELETE, "users") == AuditSeverity.HIGH
            assert service._determine_severity(AuditAction.GRANT, None) == AuditSeverity.HIGH

            # 测试敏感表操作
            assert service._determine_severity(AuditAction.UPDATE, "users") == AuditSeverity.HIGH
            assert service._determine_severity(AuditAction.CREATE, "api_keys") == AuditSeverity.HIGH

            # 测试包含PII的操作
            pii_data = {"email": "test@example.com", "username": "test"}
            assert service._determine_severity(AuditAction.UPDATE, "profiles", pii_data) == AuditSeverity.MEDIUM

            # 测试读操作
            assert service._determine_severity(AuditAction.READ, "teams") == AuditSeverity.LOW

            # 测试普通操作
            assert service._determine_severity(AuditAction.CREATE, "matches") == AuditSeverity.MEDIUM

    def test_determine_compliance_category(self):
        """测试合规分类判断"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试敏感数据分类
            assert service._determine_compliance_category(AuditAction.READ, "users", True) == "PII"

            # 测试访问控制分类
            assert service._determine_compliance_category(AuditAction.GRANT, None, False) == "ACCESS_CONTROL"
            assert service._determine_compliance_category(AuditAction.REVOKE, None, False) == "ACCESS_CONTROL"

            # 测试数据保护分类
            assert service._determine_compliance_category(AuditAction.BACKUP, None, False) == "DATA_PROTECTION"
            assert service._determine_compliance_category(AuditAction.RESTORE, None, False) == "DATA_PROTECTION"

    @patch('src.services.audit_service.DatabaseManager')
    def test_audit_operation_decorator(self, mock_db_manager):
        """测试审计操作装饰器"""
        # 创建审计服务实例
        service = AuditService()

        # 使用装饰器
        @audit_operation("test_operation", "test_table", service_instance=service)
        def test_function(param1, param2):
            return f"result_{param1}_{param2}"

        # 调用被装饰的函数
        result = test_function("value1", "value2")
        assert result == "result_value1_value2"

    @patch('src.services.audit_service.DatabaseManager')
    def test_audit_operation_decorator_async(self, mock_db_manager):
        """测试异步审计操作装饰器"""
        service = AuditService()

        @audit_operation("async_operation", "test_table", service_instance=service)
        async def async_test_function(param1, param2):
            await asyncio.sleep(0.001)
            return f"async_result_{param1}_{param2}"

        # 调用异步函数
        async def run_test():
            result = await async_test_function("value1", "value2")
            return result

        result = asyncio.run(run_test())
        assert result == "async_result_value1_value2"

    @patch('src.services.audit_service.DatabaseManager')
    def test_audit_context_variable_management(self, mock_db_manager):
        """测试审计上下文变量管理"""
        # 测试设置上下文
        context_data = {
            "user_id": "user123",
            "username": "test_user",
            "operation": "data_access"
        }

        token = audit_context.set(context_data)
        retrieved_context = audit_context.get()

        assert retrieved_context == context_data

        # 测试重置上下文
        audit_context.reset(token)
        # 上下文应该被重置为默认值
        reset_context = audit_context.get()
        assert reset_context == {}

    def test_audit_error_handling(self):
        """测试审计错误处理"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试哈希空值处理
            result1 = service._hash_sensitive_value(None)
            assert result1 == ""

            result2 = service._hash_sensitive_value("")
            assert result2 == ""

            # 测试清理非字典数据
            result3 = service._sanitize_data("not_a_dict")
            assert result3 == "not_a_dict"

            # 测试清理None数据
            result4 = service._sanitize_data(None)
            assert result4 is None

    def test_audit_service_configuration(self):
        """测试审计服务配置"""
        with patch('src.services.audit_service.DatabaseManager'):
            service = AuditService()

            # 测试敏感表配置
            expected_tables = {
                "users", "permissions", "tokens", "passwords", "api_keys",
                "user_profiles", "payment_info", "personal_data"
            }
            assert service.sensitive_tables == expected_tables

            # 测试敏感列配置
            expected_columns = {
                "password", "token", "secret", "key", "email", "phone",
                "ssn", "credit_card", "bank_account", "api_key"
            }
            assert service.sensitive_columns == expected_columns

            # 测试高风险操作配置
            expected_actions = {
                AuditAction.DELETE, AuditAction.GRANT, AuditAction.REVOKE,
                AuditAction.BACKUP, AuditAction.RESTORE, AuditAction.SCHEMA_CHANGE
            }
            assert service.high_risk_actions == expected_actions

    def test_audit_severity_levels(self):
        """测试审计严重程度级别"""
        # 测试严重程度枚举值
        assert AuditSeverity.LOW.value == "LOW"
        assert AuditSeverity.MEDIUM.value == "MEDIUM"
        assert AuditSeverity.HIGH.value == "HIGH"
        assert AuditSeverity.CRITICAL.value == "CRITICAL"

    def test_audit_action_types(self):
        """测试审计动作类型"""
        # 测试动作枚举值
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.READ.value == "READ"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DELETE.value == "DELETE"
        assert AuditAction.GRANT.value == "GRANT"
        assert AuditAction.LOGIN.value == "LOGIN"


class TestAuditServiceIntegration:
    """测试审计服务集成功能"""

    @patch('src.services.audit_service.DatabaseManager')
    def test_audit_service_logger_initialization(self, mock_db_manager):
        """测试审计服务日志器初始化"""
        service = AuditService()

        # 检查日志器名称
        expected_logger_name = f"audit.{service.__class__.__name__}"
        assert service.logger.name == expected_logger_name

    @patch('src.services.audit_service.DatabaseManager')
    def test_audit_service_database_manager_initialization(self, mock_db_manager):
        """测试审计服务数据库管理器初始化"""
        service = AuditService()

        # 检查数据库管理器是否正确初始化
        assert service.db_manager is not None
        mock_db_manager.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])