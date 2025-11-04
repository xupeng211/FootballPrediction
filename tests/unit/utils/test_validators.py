"""
工具类验证器测试
"""

from src.utils.validators import (is_valid_email, is_valid_phone, is_valid_url,
                                  validate_required_fields)


class TestValidators:
    """验证器测试类"""

    def test_is_valid_email_valid(self):
        """测试有效邮箱验证"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@example.com",
        ]

        for email in valid_emails:
            assert is_valid_email(email) is True

    def test_is_valid_email_invalid(self):
        """测试无效邮箱验证"""
        invalid_emails = [
            "",
            "invalid",
            "@example.com",
            "test@",
            "test.example.com",
            "test@.com",
        ]

        for email in invalid_emails:
            assert is_valid_email(email) is False

    def test_is_valid_phone_valid(self):
        """测试有效电话验证"""
        valid_phones = ["1234567890", "+1234567890", "(123) 456-7890", "123.456.7890"]

        for phone in valid_phones:
            assert is_valid_phone(phone) is True

    def test_is_valid_phone_invalid(self):
        """测试无效电话验证"""
        invalid_phones = ["", "abc", "123"]

        for phone in invalid_phones:
            assert is_valid_phone(phone) is False

    def test_is_valid_url_valid(self):
        """测试有效URL验证"""
        valid_urls = [
            "http://example.com",
            "https://www.example.com",
            "https://example.com/path",
        ]

        for url in valid_urls:
            assert is_valid_url(url) is True

    def test_is_valid_url_invalid(self):
        """测试无效URL验证"""
        invalid_urls = ["", "not-a-url", "www.example.com"]

        for url in invalid_urls:
            assert is_valid_url(url) is False

    def test_validate_required_fields(self):
        """测试必需字段验证"""
        data = {"name": "John", "email": "john@example.com"}
        required_fields = ["name", "email"]

        missing_fields = validate_required_fields(data, required_fields)
        assert len(missing_fields) == 0

        # 测试缺少字段
        data2 = {"name": "John"}
        missing_fields2 = validate_required_fields(data2, required_fields)
        assert "email" in missing_fields2
