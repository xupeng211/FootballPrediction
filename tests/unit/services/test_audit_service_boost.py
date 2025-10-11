"""
测试审计服务 - 提升覆盖率
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.services.audit_service_mod import AuditService, DataSanitizer, SeverityAnalyzer
from src.services.audit_service_mod.models import AuditAction, AuditSeverity


class TestAuditServiceCoverage:
    """测试AuditService以提高覆盖率"""

    @pytest.fixture
    def audit_service(self):
        """创建审计服务实例"""
        service = AuditService()
        return service

    def test_data_sanitizer_coverage(self):
        """测试数据清理器的覆盖"""
        sanitizer = DataSanitizer()

        # 测试哈希敏感值
        value = "sensitive_data"
        hashed = sanitizer._hash_sensitive_value(value)
        assert isinstance(hashed, str)
        assert len(hashed) == 16
        assert hashed != value

        # 测试哈希敏感数据
        json_data = '{"password": "secret123"}'
        hashed_data = sanitizer._hash_sensitive_data(json_data)
        assert isinstance(hashed_data, str)

        # 测试清理数据（字典）
        data = {"username": "john", "password": "secret", "email": "john@example.com"}
        sanitized = sanitizer._sanitize_data(data)
        assert sanitized["username"] == "john"
        assert sanitized["password"] != "secret"
        assert len(sanitized["password"]) == 16

        # 测试清理数据（列表）
        data_list = [{"password": "secret1"}, {"username": "john"}]
        sanitized_list = sanitizer._sanitize_data(data_list)
        assert sanitized_list[0]["password"] != "secret1"
        assert sanitized_list[1]["username"] == "john"

        # 测试敏感表检查
        assert sanitizer._is_sensitive_table("users")
        assert sanitizer._is_sensitive_table("passwords")
        assert not sanitizer._is_sensitive_table("matches")

        # 测试PII检查
        pii_data = {
            "ssn": "123-45-6789",
            "email": "test@example.com",
            "normal_field": "value",
        }
        assert sanitizer._contains_pii(pii_data)

        # 测试敏感数据检查
        sensitive_data = {"password": "secret"}
        assert sanitizer._is_sensitive_data(sensitive_data, "users")
        assert sanitizer._is_sensitive_data(sensitive_data, action="delete")
        assert not sanitizer._is_sensitive_data({"name": "john"})

    def test_severity_analyzer_coverage(self):
        """测试严重性分析器的覆盖"""
        analyzer = SeverityAnalyzer()

        # 测试确定严重性
        # 高严重性动作
        high = analyzer._determine_severity("delete", "users")
        assert high == "high"

        # 中等严重性
        medium = analyzer._determine_severity("create", "matches")
        assert medium == "medium"

        # 错误情况
        error = analyzer._determine_severity("create", "matches", error="DB Error")
        assert error == "critical"

        # 测试合规类别
        # 用户管理
        user_category = analyzer._determine_compliance_category(table_name="users")
        assert user_category == "user_management"

        # 认证相关
        auth_category = analyzer._determine_compliance_category(action="login")
        assert auth_category == "authentication"

        # 未分类
        unknown = analyzer._determine_compliance_category(table_name="unknown")
        assert unknown is None

    @pytest.mark.asyncio
    async def test_audit_service_lifecycle(self, audit_service):
        """测试审计服务生命周期"""
        # 测试初始化
        initialized = await audit_service.initialize()
        assert initialized is True

        # 测试关闭
        audit_service.close()
        assert True  # 如果没有异常就算通过

    def test_audit_service_delegation(self, audit_service):
        """测试审计服务的委托方法"""
        # 测试委托给data_sanitizer
        value = "test_value"
        hashed = audit_service._hash_sensitive_value(value)
        assert len(hashed) == 16

        # 测试委托给severity_analyzer
        severity = audit_service._determine_severity("delete", "users", "admin")
        assert severity in ["low", "medium", "high", "critical"]
