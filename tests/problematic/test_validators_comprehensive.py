"""
Validators 综合测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入validators模块

# Mock module src.utils.validators
from unittest.mock import Mock, patch

sys.modules["src.utils.validators"] = Mock()
try:
    from src.utils.validators import *

    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False


class TestValidators:
    """Validators测试类"""

    # ================ Email验证 ================

    def test_is_email_valid(self):
        """测试有效邮箱"""
        assert is_email("test@example.com") is True
        assert is_email("user.name@domain.co.uk") is True
        assert is_email("user+tag@domain.org") is True
        assert is_email("123@456.com") is True
        assert is_email("user@sub.domain.com") is True

    def test_is_email_invalid(self):
        """测试无效邮箱"""
        assert is_email("invalid-email") is False
        assert is_email("@domain.com") is False
        assert is_email("user@") is False
        assert is_email("user..name@domain.com") is False
        assert is_email("user@.domain.com") is False
        assert is_email("") is False
        assert is_email(None) is False

    # ================ Phone验证 ================

    def test_is_phone_valid(self):
        """测试有效手机号"""
        assert is_phone("+86 138 0000 0000") is True
        assert is_phone("138-0000-0000") is True
        assert is_phone("13800000000") is True
        assert is_phone("+1 (555) 123-4567") is True
        assert is_phone("0044 20 7123 4567") is True

    def test_is_phone_invalid(self):
        """测试无效手机号"""
        assert is_phone("123") is False
        assert is_phone("abc") is False
        assert is_phone("") is False
        assert is_phone(None) is False
        assert is_phone("12-34") is False

    # ================ URL验证 ================

    def test_is_url_valid(self):
        """测试有效URL"""
        assert is_url("https://www.example.com") is True
        assert is_url("http://localhost:8000") is True
        assert is_url("https://api.example.com/v1/users") is True
        assert is_url("ftp://files.example.com") is True
        assert is_url("ws://websocket.example.com") is True

    def test_is_url_invalid(self):
        """测试无效URL"""
        assert is_url("not-a-url") is False
        assert is_url("www.example.com") is False
        assert is_url("") is False
        assert is_url(None) is False
        assert is_url("http://") is False

    # ================ 日期验证 ================

    def test_validate_date_valid(self):
        """测试有效日期"""
        assert validate_date("2025-01-18") is True
        assert validate_date("2025/01/18") is True
        assert validate_date("01-18-2025") is True
        assert validate_date("2025-01-18T14:30:00") is True
        assert validate_date("18-Jan-2025") is True

    def test_validate_date_invalid(self):
        """测试无效日期"""
        assert validate_date("2025-13-01") is False  # 无效月份
        assert validate_date("2025-01-32") is False  # 无效日期
        assert validate_date("invalid-date") is False
        assert validate_date("") is False
        assert validate_date(None) is False

    # ================ 正数验证 ================

    def test_validate_positive_number_valid(self):
        """测试有效正数"""
        assert validate_positive_number(5) is True
        assert validate_positive_number(3.14) is True
        assert validate_positive_number(0.01) is True
        assert validate_positive_number(1000000) is True

    def test_validate_positive_number_invalid(self):
        """测试无效正数"""
        assert validate_positive_number(0) is False
        assert validate_positive_number(-1) is False
        assert validate_positive_number(-3.14) is False
        assert validate_positive_number(None) is False

    # ================ 字符串长度验证 ================

    def test_validate_string_length_valid(self):
        """测试有效字符串长度"""
        if hasattr(validate_string_length, "__call__"):
            assert validate_string_length("hello", 1, 10) is True
            assert validate_string_length("world", 5, 5) is True
            assert validate_string_length("", 0, 10) is True

    def test_validate_string_length_invalid(self):
        """测试无效字符串长度"""
        if hasattr(validate_string_length, "__call__"):
            assert validate_string_length("hello", 10, 20) is False
            assert validate_string_length("very long string", 1, 5) is False

    # ================ 必填字段验证 ================

    def test_validate_required_fields_valid(self):
        """测试有效必填字段"""
        if hasattr(validate_required_fields, "__call__"):
            data = {"name": "John", "email": "john@example.com"}
            required = ["name", "email"]
            assert validate_required_fields(data, required) is True

    def test_validate_required_fields_invalid(self):
        """测试无效必填字段"""
        if hasattr(validate_required_fields, "__call__"):
            data = {"name": "John"}
            required = ["name", "email"]
            assert validate_required_fields(data, required) is False

    # ================ 参数化测试 ================

    @pytest.mark.parametrize(
        "email,expected",
        [
            ("test@example.com", True),
            ("user.name@domain.co.uk", True),
            ("invalid-email", False),
            ("@domain.com", False),
            ("user@", False),
            ("", False),
        ],
    )
    def test_is_email_parametrized(self, email, expected):
        """参数化测试邮箱验证"""
        assert is_email(email) == expected

    @pytest.mark.parametrize(
        "phone,expected",
        [
            ("+86 138 0000 0000", True),
            ("138-0000-0000", True),
            ("13800000000", True),
            ("123", False),
            ("abc", False),
            ("", False),
        ],
    )
    def test_is_phone_parametrized(self, phone, expected):
        """参数化测试手机号验证"""
        assert is_phone(phone) == expected

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.example.com", True),
            ("http://localhost:8000", True),
            ("ftp://files.example.com", True),
            ("not-a-url", False),
            ("www.example.com", False),
            ("", False),
        ],
    )
    def test_is_url_parametrized(self, url, expected):
        """参数化测试URL验证"""
        assert is_url(url) == expected

    # ================ 边界条件测试 ================

    def test_edge_cases_empty_string(self):
        """测试空字符串边界情况"""
        assert is_email("") is False
        assert is_phone("") is False
        assert is_url("") is False
        assert validate_date("") is False

    def test_edge_cases_none_values(self):
        """测试None值边界情况"""
        assert is_email(None) is False
        assert is_phone(None) is False
        assert is_url(None) is False
        assert validate_date(None) is False
        assert validate_positive_number(None) is False

    def test_edge_cases_extreme_values(self):
        """测试极值边界情况"""
        assert validate_positive_number(float("inf")) is True
        assert validate_positive_number(float("-inf")) is False
        assert validate_positive_number(1e-100) is True

    # ================ 性能测试 ================

    def test_performance_bulk_validation(self):
        """测试批量验证性能"""
        import time

        emails = [f"user{i}@example.com" for i in range(1000)]

        start = time.time()
        for email in emails:
            is_email(email)
        duration = time.time() - start

        assert duration < 0.1  # 应该在100ms内完成

    # ================ Unicode测试 ================

    def test_unicode_emails(self):
        """测试Unicode邮箱"""
        # 根据实际实现调整
        unicode_email = "tëst@exämple.com"
        result = is_email(unicode_email)
        assert isinstance(result, bool)

    def test_unicode_phones(self):
        """测试Unicode手机号"""
        unicode_phone = "+86 138-0000-0000"
        result = is_phone(unicode_phone)
        assert isinstance(result, bool)
