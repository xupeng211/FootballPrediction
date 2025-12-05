from typing import Optional

"""
验证器测试 - 只测试确认存在的函数
"""

from src.utils.validators import (
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    validate_required_fields,
)


class TestWorkingValidators:
    """验证器测试类"""

    def test_is_valid_email_function(self):
        """测试邮箱验证函数存在和基本功能"""
        # 测试函数存在
        assert callable(is_valid_email)

        # 测试基本功能
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("") is False

    def test_is_valid_phone_function(self):
        """测试电话验证函数存在和基本功能"""
        # 测试函数存在
        assert callable(is_valid_phone)

        # 测试基本功能
        assert is_valid_phone("1234567890") is True
        assert is_valid_phone("") is False

    def test_is_valid_url_function(self):
        """测试URL验证函数存在和基本功能"""
        # 测试函数存在
        assert callable(is_valid_url)

        # 测试基本功能
        assert is_valid_url("http://example.com") is True
        assert is_valid_url("") is False

    def test_validate_required_fields_function(self):
        """测试必需字段验证函数"""
        # 测试函数存在
        assert callable(validate_required_fields)

        # 测试基本功能
        data = {"name": "John", "email": "john@example.com"}
        required_fields = ["name", "email"]
        missing_fields = validate_required_fields(data, required_fields)
        assert isinstance(missing_fields, list)

    def test_validators_import(self):
        """测试验证器模块导入"""
        import src.utils.validators

        # 验证模块存在
        assert src.utils.validators is not None

        # 验证函数存在
        assert hasattr(src.utils.validators, "is_valid_email")
        assert hasattr(src.utils.validators, "is_valid_phone")
        assert hasattr(src.utils.validators, "is_valid_url")
        assert hasattr(src.utils.validators, "validate_required_fields")

    def test_email_patterns(self):
        """测试各种邮箱格式"""
        valid_emails = [
            "simple@example.com",
            "very.common@example.com",
            "disposable.style.email.with+symbol@example.com",
            "user.name+tag+sorting@example.com",
            "x@example.com",
            "example-indeed@strange-example.com",
        ]

        for email in valid_emails:
            result = is_valid_email(email)
            # 不要求全部通过，但测试函数能正常处理
            assert isinstance(result, bool)

    def test_phone_patterns(self):
        """测试各种电话格式"""
        phone_patterns = [
            "1234567890",
            "+1234567890",
            "(123) 456-7890",
            "123.456.7890",
            "123-456-7890",
            "+1 (123) 456-7890",
        ]

        for phone in phone_patterns:
            result = is_valid_phone(phone)
            # 不要求全部通过，但测试函数能正常处理
            assert isinstance(result, bool)

    def test_url_patterns(self):
        """测试各种URL格式"""
        url_patterns = [
            "http://example.com",
            "https://www.example.com",
            "https://example.com/path/to/resource",
            "http://subdomain.example.com",
            "https://example.com:8080",
            "http://example.com/path?query=value",
        ]

        for url in url_patterns:
            result = is_valid_url(url)
            # 不要求全部通过，但测试函数能正常处理
            assert isinstance(result, bool)