#!/usr/bin/env python3
"""
数据验证工具测试
测试 src.utils.validators 模块的功能
"""

import pytest

from src.utils.validators import (
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    validate_data_types,
    validate_required_fields,
)


@pytest.mark.unit
class TestValidators:
    """数据验证工具测试"""

    def test_is_valid_email_valid_emails(self):
        """测试有效邮箱地址"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com",
            "simple@test.com",
        ]

        for email in valid_emails:
            assert is_valid_email(email), f"Email {email} should be valid"

    def test_is_valid_email_invalid_emails(self):
        """测试无效邮箱地址"""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user@.com",
            "user name@example.com",
            "user@example",
            "",
            "user@.",
            "test@.test.com",
        ]

        for email in invalid_emails:
            assert not is_valid_email(email), f"Email {email} should be invalid"

    def test_is_valid_phone_valid_phones(self):
        """测试有效电话号码"""
        valid_phones = [
            "+1234567890",
            "123-456-7890",
            "(123) 456-7890",
            "+1 (123) 456-7890",
            "1234567890",
            "+86 123 4567 8901",
        ]

        for phone in valid_phones:
            assert is_valid_phone(phone), f"Phone {phone} should be valid"

    def test_is_valid_phone_invalid_phones(self):
        """测试无效电话号码"""
        invalid_phones = [
            "123-abc-456",
            "phone-number",
            "",
            "12345",
            "+-123-456",
            "(123)456-7890)",  # 不匹配的括号
            "123-456-7890 ext 123",  # 包含扩展
            "phone",
        ]

        for phone in invalid_phones:
            assert not is_valid_phone(phone), f"Phone {phone} should be invalid"

    def test_is_valid_url_valid_urls(self):
        """测试有效URL"""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "https://www.example.com",
            "http://example.com:8080",
            "https://example.com/path/to/page",
            "https://example.com/path?query=value&other=test",
            "https://example.com/path#section",
            "https://subdomain.example.com/path",
            "http://localhost:3000",
        ]

        for url in valid_urls:
            assert is_valid_url(url), f"URL {url} should be valid"

    def test_is_valid_url_invalid_urls(self):
        """测试无效URL"""
        invalid_urls = [
            "ftp://example.com",  # 不支持的协议
            "example.com",  # 缺少协议
            "http://",  # 缺少域名
            "https://",  # 缺少域名
            "not-a-url",
            "",
            "http://invalid domain.com",  # 包含空格
            "javascript:alert('xss')",  # 危险协议
            "http:/example.com",  # 格式错误
        ]

        for url in invalid_urls:
            assert not is_valid_url(url), f"URL {url} should be invalid"

    def test_validate_required_fields_all_present(self):
        """测试所有必需字段都存在的情况"""
        data = {"name": "John", "email": "john@example.com", "age": 30}
        required_fields = ["name", "email", "age"]

        missing = validate_required_fields(data, required_fields)
        assert missing == []

    def test_validate_required_fields_missing_fields(self):
        """测试缺少必需字段的情况"""
        data = {"name": "John", "age": 30}
        required_fields = ["name", "email", "age", "phone"]

        missing = validate_required_fields(data, required_fields)
        assert set(missing) == {"email", "phone"}

    def test_validate_required_fields_none_values(self):
        """测试字段值为None或空字符串的情况"""
        data = {"name": "John", "email": None, "age": "", "phone": "123-456-7890"}
        required_fields = ["name", "email", "age", "phone"]

        missing = validate_required_fields(data, required_fields)
        assert set(missing) == {"email", "age"}

    def test_validate_required_fields_empty_data(self):
        """测试空数据的情况"""
        data = {}
        required_fields = ["name", "email"]

        missing = validate_required_fields(data, required_fields)
        assert set(missing) == {"name", "email"}

    def test_validate_data_types_all_correct(self):
        """测试所有数据类型都正确的情况"""
        data = {"name": "John", "age": 30, "active": True, "scores": [85, 90, 78]}
        schema = {"name": str, "age": int, "active": bool, "scores": list}

        errors = validate_data_types(data, schema)
        assert errors == []

    def test_validate_data_types_type_mismatches(self):
        """测试数据类型不匹配的情况"""
        data = {
            "name": "John",
            "age": "30",  # 字符串而不是整数
            "active": "true",  # 字符串而不是布尔值
            "scores": [85, 90, 78],
        }
        schema = {"name": str, "age": int, "active": bool, "scores": list}

        errors = validate_data_types(data, schema)
        assert len(errors) == 2
        assert any("age" in error for error in errors)
        assert any("active" in error for error in errors)

    def test_validate_data_types_missing_fields(self):
        """测试字段缺失的情况"""
        data = {"name": "John", "age": 30}
        schema = {"name": str, "age": int, "email": str, "active": bool}

        errors = validate_data_types(data, schema)
        # 缺失字段不应该产生类型错误,因为它们不存在
        assert errors == []

    def test_validate_data_types_empty_data(self):
        """测试空数据的类型验证"""
        data = {}
        schema = {"name": str, "email": str}

        errors = validate_data_types(data, schema)
        assert errors == []

    def test_is_valid_email_edge_cases(self):
        """测试邮箱验证的边界情况"""
        # 最小有效邮箱
        assert is_valid_email("a@b.co")

        # 带多个点的域名
        assert is_valid_email("test@mail.example.com")

        # 带数字的邮箱
        assert is_valid_email("user123@test456.com")

    def test_is_valid_phone_edge_cases(self):
        """测试电话验证的边界情况"""
        # 最短有效电话
        assert is_valid_phone("123")

        # 只有国家代码
        assert is_valid_phone("+1")

        # 带空格的电话
        assert is_valid_phone("123 456 7890")

    def test_is_valid_url_edge_cases(self):
        """测试URL验证的边界情况"""
        # 带端口的URL
        assert is_valid_url("http://localhost:80")

        # 带查询参数的URL
        assert is_valid_url("https://example.com?a=1&b=2")

        # 带锚点的URL
        assert is_valid_url("https://example.com#section")
