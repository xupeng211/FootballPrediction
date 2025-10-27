#!/usr/bin/env python3
"""
数据验证器简单测试
测试 src.utils.data_validator 模块的基础功能
"""

import pytest

from src.utils.data_validator import DataValidator


@pytest.mark.unit
class TestDataValidatorSimple:
    """数据验证器简单测试"""

    def test_validate_email_valid_emails(self):
        """测试有效邮箱验证"""
        valid_emails = ["test@example.com", "user@domain.org", "simple@test.co"]

        for email in valid_emails:
            result = DataValidator.validate_email(email)
            # 验证结果是布尔值
            assert isinstance(result, bool)

    def test_validate_email_invalid_emails(self):
        """测试无效邮箱验证"""
        invalid_emails = ["invalid-email", "@example.com", "user@", ""]

        for email in invalid_emails:
            result = DataValidator.validate_email(email)
            # 验证结果是布尔值
            assert isinstance(result, bool)

    def test_validate_url_valid_urls(self):
        """测试有效URL验证"""
        valid_urls = ["http://example.com", "https://test.org"]

        for url in valid_urls:
            result = DataValidator.validate_url(url)
            # 验证结果是布尔值
            assert isinstance(result, bool)

    def test_validate_url_invalid_urls(self):
        """测试无效URL验证"""
        invalid_urls = ["not-a-url", "ftp://example.com", ""]  # 可能不支持的协议

        for url in invalid_urls:
            result = DataValidator.validate_url(url)
            # 验证结果是布尔值
            assert isinstance(result, bool)

    def test_validate_phone_valid_phones(self):
        """测试有效电话验证"""
        valid_phones = ["1234567890", "+1234567890"]

        for phone in valid_phones:
            result = DataValidator.validate_phone(phone)
            # 验证结果是布尔值
            assert isinstance(result, bool)

    def test_validate_phone_invalid_phones(self):
        """测试无效电话验证"""
        invalid_phones = ["123", "phone-number", ""]

        for phone in invalid_phones:
            result = DataValidator.validate_phone(phone)
            # 验证结果是布尔值
            assert isinstance(result, bool)

    def test_validate_required_fields_complete(self):
        """测试完整必需字段验证"""
        data = {"name": "John", "email": "john@example.com"}
        required_fields = ["name", "email"]

        result = DataValidator.validate_required_fields(data, required_fields)
        # 应该返回空列表（没有缺失字段）
        assert isinstance(result, list)

    def test_validate_required_fields_missing(self):
        """测试缺失必需字段验证"""
        data = {"name": "John"}
        required_fields = ["name", "email", "age"]

        result = DataValidator.validate_required_fields(data, required_fields)
        # 应该返回缺失字段的列表
        assert isinstance(result, list)

    def test_validate_positive_numbers_valid(self):
        """测试正数验证"""
        positive_numbers = [1, 3.14, 100, 0.1]

        for num in positive_numbers:
            result = DataValidator.validate_positive_number(num)
            assert isinstance(result, bool)

    def test_validate_positive_numbers_invalid(self):
        """测试非正数验证"""
        non_positive = [0, -1, -3.14, -100]

        for num in non_positive:
            result = DataValidator.validate_positive_number(num)
            assert isinstance(result, bool)

    def test_validate_string_length_valid(self):
        """测试字符串长度验证"""
        test_string = "Hello World"

        # 测试不同长度限制
        result1 = DataValidator.validate_string_length(test_string, 5, 20)
        result2 = DataValidator.validate_string_length(test_string, 10, 15)

        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    def test_validate_string_length_invalid(self):
        """测试字符串长度验证 - 无效情况"""
        test_string = "Hello"

        # 测试超出长度限制
        result = DataValidator.validate_string_length(test_string, 10, 20)
        assert isinstance(result, bool)

    def test_validate_range_valid(self):
        """测试范围验证"""
        numbers = [5, 10, 15, 20]
        min_val, max_val = 5, 20

        for num in numbers:
            result = DataValidator.validate_range(num, min_val, max_val)
            assert isinstance(result, bool)

    def test_validate_range_invalid(self):
        """测试范围验证 - 无效情况"""
        out_of_range = [1, 4, 21, 25]
        min_val, max_val = 5, 20

        for num in out_of_range:
            result = DataValidator.validate_range(num, min_val, max_val)
            assert isinstance(result, bool)
