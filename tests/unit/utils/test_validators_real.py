"""
Validators 实际函数测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.validators import (
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    validate_required_fields,
    validate_data_types,
    validate_username,
)


class TestValidatorsReal:
    """测试实际可用的验证器函数"""

    # ================ Email验证 ================

    def test_is_valid_email_valid(self):
        """测试有效邮箱"""
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("user.name@domain.co.uk") is True
        assert is_valid_email("user+tag@domain.org") is True
        assert is_valid_email("123@456.com") is True
        assert is_valid_email("user@sub.domain.com") is True

    def test_is_valid_email_invalid(self):
        """测试无效邮箱"""
        assert is_valid_email("invalid-email") is False
        assert is_valid_email("@domain.com") is False
        assert is_valid_email("user@") is False
        assert is_valid_email("user..name@domain.com") is False
        assert is_valid_email("user@.domain.com") is False
        assert is_valid_email("") is False

    # ================ Phone验证 ================

    def test_is_valid_phone_valid(self):
        """测试有效手机号"""
        assert is_valid_phone("+86 138 0000 0000") is True
        assert is_valid_phone("138-0000-0000") is True
        assert is_valid_phone("13800000000") is True
        assert is_valid_phone("+1 (555) 123-4567") is True
        assert is_valid_phone("0044 20 7123 4567") is True
        assert is_valid_phone("(555) 123-4567") is True

    def test_is_valid_phone_invalid(self):
        """测试无效手机号"""
        assert is_valid_phone("123") is False
        assert is_valid_phone("abc") is False
        assert is_valid_phone("") is False
        assert is_valid_phone("12-34") is False
        assert is_valid_phone("phone") is False

    # ================ URL验证 ================

    def test_is_valid_url_valid(self):
        """测试有效URL"""
        assert is_valid_url("https://www.example.com") is True
        assert is_valid_url("http://localhost:8000") is True
        assert is_valid_url("https://api.example.com/v1/users") is True
        assert is_valid_url("http://example.com/path?query=param") is True
        assert is_valid_url("https://example.com/path#section") is True

    def test_is_valid_url_invalid(self):
        """测试无效URL"""
        assert is_valid_url("not-a-url") is False
        assert is_valid_url("www.example.com") is False
        assert is_valid_url("") is False
        assert is_valid_url("http://") is False
        assert is_valid_url("example.com") is False

    # ================ 必填字段验证 ================

    def test_validate_required_fields_all_present(self):
        """测试所有必填字段都存在"""
        data = {"name": "John", "email": "john@example.com", "age": 30}
        required = ["name", "email", "age"]
        missing = validate_required_fields(data, required)
        assert missing == []

    def test_validate_required_fields_missing_some(self):
        """测试部分必填字段缺失"""
        data = {"name": "John"}
        required = ["name", "email", "age"]
        missing = validate_required_fields(data, required)
        assert set(missing) == {"email", "age"}

    def test_validate_required_fields_empty_values(self):
        """测试空值被视为缺失"""
        data = {"name": "", "email": None, "age": 0}
        required = ["name", "email", "age"]
        missing = validate_required_fields(data, required)
        assert set(missing) == {"name", "email"}

    # ================ 数据类型验证 ================

    def test_validate_data_types_valid(self):
        """测试有效数据类型"""
        data = {"name": "John", "age": 30, "active": True}
        schema = {"name": str, "age": int, "active": bool}
        errors = validate_data_types(data, schema)
        assert errors == []

    def test_validate_data_types_invalid(self):
        """测试无效数据类型"""
        data = {"name": 123, "age": "30", "active": "true"}
        schema = {"name": str, "age": int, "active": bool}
        errors = validate_data_types(data, schema)
        assert len(errors) == 3
        assert "Field 'name' should be str, got int" in errors[0]
        assert "Field 'age' should be int, got str" in errors[1]
        assert "Field 'active' should be bool, got str" in errors[2]

    def test_validate_data_types_missing_fields(self):
        """测试缺失字段（应该跳过）"""
        data = {"name": "John"}
        schema = {"name": str, "age": int}
        errors = validate_data_types(data, schema)
        assert errors == []

    # ================ 用户名验证 ================

    def test_validate_username_valid(self):
        """测试有效用户名"""
        if hasattr(validate_username, "__call__"):
            assert validate_username("john_doe") is True
            assert validate_username("johndoe123") is True
            assert validate_username("JohnDoe") is True
            assert validate_username("user_name") is True

    def test_validate_username_invalid(self):
        """测试无效用户名"""
        if hasattr(validate_username, "__call__"):
            assert validate_username("") is False
            assert validate_username("ab") is False  # 太短
            assert validate_username("user@name") is False  # 特殊字符

    # ================ 参数化测试 ================

    @pytest.mark.parametrize(
        "email,expected",
        [
            ("test@example.com", True),
            ("user.name@domain.co.uk", True),
            ("user+tag@domain.org", True),
            ("invalid-email", False),
            ("@domain.com", False),
            ("user@", False),
            ("", False),
        ],
    )
    def test_is_valid_email_parametrized(self, email, expected):
        """参数化测试邮箱验证"""
        assert is_valid_email(email) == expected

    @pytest.mark.parametrize(
        "phone,expected",
        [
            ("+86 138 0000 0000", True),
            ("138-0000-0000", True),
            ("13800000000", True),
            ("(555) 123-4567", True),
            ("123", False),
            ("abc", False),
            ("", False),
            ("12-34", False),
        ],
    )
    def test_is_valid_phone_parametrized(self, phone, expected):
        """参数化测试手机号验证"""
        assert is_valid_phone(phone) == expected

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.example.com", True),
            ("http://localhost:8000", True),
            ("https://api.example.com/v1/users", True),
            ("http://example.com/path?query=param", True),
            ("not-a-url", False),
            ("www.example.com", False),
            ("", False),
            ("http://", False),
            ("example.com", False),
        ],
    )
    def test_is_valid_url_parametrized(self, url, expected):
        """参数化测试URL验证"""
        assert is_valid_url(url) == expected

    # ================ 边界条件测试 ================

    def test_edge_cases_empty_string(self):
        """测试空字符串边界情况"""
        assert is_valid_email("") is False
        assert is_valid_phone("") is False
        assert is_valid_url("") is False

    def test_edge_cases_special_characters(self):
        """测试特殊字符"""
        assert is_valid_email("test+tag@example.com") is True
        assert is_valid_phone("+1 (555) 123-4567") is True
        assert is_valid_url("https://example.com/path-with-dashes") is True

    # ================ 性能测试 ================

    def test_performance_bulk_validation(self):
        """测试批量验证性能"""
        import time

        emails = [f"user{i}@example.com" for i in range(1000)]

        start = time.time()
        for email in emails:
            is_valid_email(email)
        duration = time.time() - start

        assert duration < 0.1  # 应该在100ms内完成

    # ================ 复合验证场景 ================

    def test_complex_validation_scenario(self):
        """测试复杂验证场景"""
        # 用户注册数据
        user_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "phone": "+1 555-123-4567",
            "website": "https://johndoe.com",
            "age": 30,
            "active": True,
        }

        # 验证邮箱
        assert is_valid_email(user_data["email"]) is True

        # 验证手机号
        assert is_valid_phone(user_data["phone"]) is True

        # 验证URL
        assert is_valid_url(user_data["website"]) is True

        # 验证必填字段
        required = ["username", "email", "phone"]
        missing = validate_required_fields(user_data, required)
        assert missing == []

        # 验证数据类型
        schema = {"username": str, "email": str, "age": int, "active": bool}
        errors = validate_data_types(user_data, schema)
        assert errors == []
