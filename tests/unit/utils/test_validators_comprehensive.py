"""
Validators综合测试 - 从0%提升到90%+覆盖率
覆盖所有验证函数
"""

import pytest
from src.utils.validators import (
    is_valid_email, is_valid_phone, is_valid_url,
    validate_required_fields, validate_data_types
)


class TestValidatorsComprehensive:
    """Validators综合测试类 - 提升覆盖率到90%+"""

    def test_is_valid_email_function(self):
        """测试邮箱验证功能"""
        # 有效邮箱
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@test-domain.com",
            "user_name@test-domain.com"
        ]

        for email in valid_emails:
            assert is_valid_email(email) is True

        # 无效邮箱
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "test@.com",
            "test@com.",
            "test space@domain.com",
            "test@domain..com"
        ]

        for email in invalid_emails:
            assert is_valid_email(email) is False

    def test_is_valid_phone_function(self):
        """测试手机号验证功能"""
        # 有效手机号
        valid_phones = [
            "+1234567890",
            "13800138000",
            "+86 138 0013 8000",
            "(123) 456-7890",
            "123-456-7890",
            "+1 (555) 123-4567"
        ]

        for phone in valid_phones:
            assert is_valid_phone(phone) is True

        # 无效手机号
        invalid_phones = [
            "abc123def",
            "1234567890abc",
            "phone number",
            "",
            "123@456"
        ]

        for phone in invalid_phones:
            assert is_valid_phone(phone) is False

    def test_is_valid_url_function(self):
        """测试URL验证功能"""
        # 有效URL
        valid_urls = [
            "http://example.com",
            "https://www.example.com",
            "https://example.com/path/to/resource",
            "http://example.com:8080",
            "https://example.com/path?query=value&param2=data",
            "https://example.com/path#section",
            "http://subdomain.example.com"
        ]

        for url in valid_urls:
            assert is_valid_url(url) is True

        # 无效URL
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "http//example.com",
            "example.com",
            "http://",
            "https://",
            "",
            "http://example .com"
        ]

        for url in invalid_urls:
            assert is_valid_url(url) is False

    def test_validate_required_fields_function(self):
        """测试必填字段验证功能"""
        # 完整数据
        data = {"name": "John", "email": "john@example.com", "age": 30}
        required_fields = ["name", "email"]
        result = validate_required_fields(data, required_fields)
        assert result == []

        # 缺少字段
        data = {"name": "John"}
        required_fields = ["name", "email", "age"]
        result = validate_required_fields(data, required_fields)
        assert set(result) == {"email", "age"}

        # 空值字段
        data = {"name": "", "email": None, "age": 0}
        required_fields = ["name", "email", "age"]
        result = validate_required_fields(data, required_fields)
        assert set(result) == {"name", "email"}

        # 空必填字段列表
        data = {"name": "John"}
        required_fields = []
        result = validate_required_fields(data, required_fields)
        assert result == []

    def test_validate_data_types_function(self):
        """测试数据类型验证功能"""
        # 正确类型
        data = {"name": "John", "age": 30, "active": True}
        schema = {"name": str, "age": int, "active": bool}
        result = validate_data_types(data, schema)
        assert result == []

        # 错误类型
        data = {"name": 123, "age": "30", "active": "true"}
        schema = {"name": str, "age": int, "active": bool}
        result = validate_data_types(data, schema)
        assert len(result) == 3
        assert any("name" in error for error in result)
        assert any("age" in error for error in result)
        assert any("active" in error for error in result)

        # 部分正确
        data = {"name": "John", "age": "30"}
        schema = {"name": str, "age": int, "email": str}
        result = validate_data_types(data, schema)
        assert len(result) == 1
        assert "age" in result[0]

        # 空schema
        data = {"name": "John"}
        schema = {}
        result = validate_data_types(data, schema)
        assert result == []

    def test_comprehensive_validation_workflow(self):
        """测试完整的验证工作流程"""
        # 1. 验证用户数据
        user_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1 555-123-4567",
            "website": "https://johndoe.com",
            "age": 30
        }

        # 验证格式
        assert is_valid_email(user_data["email"]) is True
        assert is_valid_phone(user_data["phone"]) is True
        assert is_valid_url(user_data["website"]) is True

        # 验证必填字段
        required_fields = ["name", "email", "age"]
        missing = validate_required_fields(user_data, required_fields)
        assert missing == []

        # 验证数据类型
        schema = {
            "name": str,
            "email": str,
            "age": int,
            "phone": str
        }
        type_errors = validate_data_types(user_data, schema)
        assert type_errors == []

    def test_edge_cases_and_boundary_values(self):
        """测试边界情况和边界值"""
        # 测试空字符串
        assert is_valid_email("") is False
        assert is_valid_phone("") is False
        assert is_valid_url("") is False

        # 测试极长字符串
        long_email = "a" * 100 + "@example.com"
        assert is_valid_email(long_email) is True

        # 测试特殊字符
        special_email = "test.email+tag@example-domain.com"
        assert is_valid_email(special_email) is True

        # 测试国际化字符（可能不支持）
        international_phone = "+86 138 0013 8000"
        assert is_valid_phone(international_phone) is True

        # 测试复杂URL
        complex_url = "https://example.com:8080/path/to/resource?param1=value1&param2=value2#section"
        assert is_valid_url(complex_url) is True

    def test_error_scenarios_and_robustness(self):
        """测试错误场景和健壮性"""
        # 测试None值处理
        assert is_valid_email(None) is False  # 可能会抛出异常，但期望False
        assert is_valid_phone(None) is False
        assert is_valid_url(None) is False

        # 测试非字符串输入
        non_string_inputs = [123, [], {}, True, lambda x: x]
        for input_val in non_string_inputs:
            try:
                assert is_valid_email(input_val) is False
            except (TypeError, AttributeError):
                pass  # 预期可能抛出异常

            try:
                assert is_valid_phone(input_val) is False
            except (TypeError, AttributeError):
                pass

            try:
                assert is_valid_url(input_val) is False
            except (TypeError, AttributeError):
                pass

        # 测试空数据结构
        assert validate_required_fields({}, []) == []
        assert validate_required_fields({}, ["field"]) == ["field"]
        assert validate_data_types({}, {}) == []
        assert validate_data_types({"field": "value"}, {"missing": str}) == []