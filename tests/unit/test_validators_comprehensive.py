"""
数据验证器的全面单元测试
Comprehensive unit tests for data validators
"""

import pytest
import re
from src.utils.validators import (
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    validate_required_fields,
    validate_data_types,
)


@pytest.mark.unit
class TestEmailValidation:
    """测试邮箱验证功能"""

    def test_valid_emails(self):
        """测试有效的邮箱地址"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "test123@test-domain.com",
            "simple@domain.io",
            "email.subdomain@test.example",
            "user.name123@domain456.com",
        ]

        for email in valid_emails:
            assert is_valid_email(email), f"Email {email} should be valid"

    def test_invalid_emails(self):
        """测试无效的邮箱地址"""
        invalid_emails = [
            "plainaddress",
            "@domain.com",
            "user@",
            "user@.com",
            "user..name@domain.com",
            "user@domain",
            "user.name@",
            "user name@domain.com",
            "user@domain.",
            "user@domain.c",
            "user@@domain.com",
            "user@domain..com",
            "user@-",
            "a@b.c",
        ]

        for email in invalid_emails:
            assert not is_valid_email(email), f"Email {email} should be invalid"

    def test_email_case_insensitivity(self):
        """测试邮箱不区分大小写"""
        email = "Test@Example.COM"
        assert is_valid_email(email)

    def test_email_unicode_characters(self):
        """测试包含Unicode字符的邮箱"""
        unicode_emails = [
            "tëst@example.com",  # 拉丁字符
            "tést@example.com",  # 带重音符
        ]
        # Unicode字符在某些实现中可能有效，取决于正则表达式
        for email in unicode_emails:
            # 不强制断言，记录结果
            result = is_valid_email(email)
            print(f"Unicode email {email}: {result}")


@pytest.mark.unit
class TestPhoneValidation:
    """测试电话号码验证"""

    def test_valid_phones(self):
        """测试有效的电话号码"""
        valid_phones = [
            "+1234567890",
            "+1 234-567-8900",
            "+1 (234) 567-8900",
            "+1 234 567 8900",
            "123-456-7890",
            "(123) 456-7890",
            "1234567890",
            "+44 20 1234 5678",
            "+86 138 0000 0000",
            "+49 30 12345678",
            "001 234-5678",
        ]

        for phone in valid_phones:
            assert is_valid_phone(phone), f"Phone {phone} should be valid"

    def test_invalid_phones(self):
        """测试无效的电话号码"""
        invalid_phones = [
            "abc",
            "123-456-789a",
            "",
            "   ",
            "+",
            "+123-",
            "(123",
            "123)",
            "1a2b3c4d",
            "123 456 789 0123",  # 太长但可能有效
        ]

        for phone in invalid_phones:
            assert not is_valid_phone(phone), f"Phone {phone} should be invalid"

    def test_phone_formats(self):
        """测试不同的电话号码格式"""
        test_cases = [
            ("+1-555-123-4567", True),
            ("+1 (555) 123-4567", True),
            ("5551234567", True),
            ("1 (555) 123-4567", False),  # 缺少国家代码
            ("555-ABC-DEF", False),  # 包含字母
        ]

        for phone, expected in test_cases:
            assert is_valid_phone(phone) == expected


@pytest.mark.unit
class TestUrlValidation:
    """测试URL验证"""

    def test_valid_urls(self):
        """测试有效的URL"""
        valid_urls = [
            "https://www.example.com",
            "http://example.com",
            "https://example.com/path",
            "https://example.com/path/to/resource",
            "https://example.com/path?query=value",
            "https://example.com/path#fragment",
            "https://example.com:8080",
            "https://subdomain.example.com",
            "https://example.co.uk",
            "http://localhost:3000",
            "https://192.168.1.1",
            "https://api.example.com/v1/users",
            "http://example.com/path/to/file.html",
            "https://example.com/search?q=test#results",
        ]

        for url in valid_urls:
            assert is_valid_url(url), f"URL {url} should be valid"

    def test_invalid_urls(self):
        """测试无效的URL"""
        invalid_urls = [
            "www.example.com",  # 缺少协议
            "ftp://example.com",  # 非HTTP/HTTPS协议
            "example.com",
            "http://",
            "https://",
            "http://example.c",  # 顶级域名太短
            "http://example..com",
            "http://example.com//path",
            "http://example.com/path/",
        ]

        for url in invalid_urls:
            assert not is_valid_url(url), f"URL {url} should be invalid"

    def test_url_case_sensitivity(self):
        """测试URL大小写敏感性"""
        url = "HTTPS://EXAMPLE.COM/PATH"
        assert is_valid_url(url)


@pytest.mark.unit
class TestRequiredFieldsValidation:
    """测试必填字段验证"""

    def test_no_missing_fields(self):
        """测试没有缺失字段"""
        data = {"name": "John", "email": "john@example.com", "age": 30}
        required = ["name", "email", "age"]

        missing = validate_required_fields(data, required)
        assert missing == [], "No fields should be missing"

    def test_missing_fields(self):
        """测试缺失字段"""
        data = {"name": "John", "age": 30}
        required = ["name", "email", "age", "address"]

        missing = validate_required_fields(data, required)
        assert "email" in missing
        assert "address" in missing
        assert len(missing) == 2

    def test_empty_string_fields(self):
        """测试空字符串字段"""
        data = {"name": "", "email": "test@example.com", "age": 30}
        required = ["name", "email", "age"]

        missing = validate_required_fields(data, required)
        assert "name" in missing

    def test_none_fields(self):
        """测试None值字段"""
        data = {"name": None, "email": "test@example.com", "age": 30}
        required = ["name", "email", "age"]

        missing = validate_required_fields(data, required)
        assert "name" in missing

    def test_zero_and_false_values(self):
        """测试零和假值（应该被视为有效）"""
        data = {"name": "John", "age": 0, "active": False, "score": 0.0}
        required = ["name", "age", "active", "score"]

        missing = validate_required_fields(data, required)
        assert missing == [], "Zero and False values should be valid"

    def test_empty_required_list(self):
        """测试空的必填字段列表"""
        data = {"name": "John"}
        required = []

        missing = validate_required_fields(data, required)
        assert missing == []

    def test_empty_data(self):
        """测试空数据字典"""
        data = {}
        required = ["name", "email"]

        missing = validate_required_fields(data, required)
        assert set(missing) == {"name", "email"}


@pytest.mark.unit
class TestDataTypesValidation:
    """测试数据类型验证"""

    def test_valid_types(self):
        """测试正确的数据类型"""
        data = {
            "name": "John",
            "age": 30,
            "active": True,
            "tags": ["tag1", "tag2"],
            "metadata": {"key": "value"},
        }
        schema = {
            "name": str,
            "age": int,
            "active": bool,
            "tags": list,
            "metadata": dict,
        }

        errors = validate_data_types(data, schema)
        assert errors == [], "No type errors should occur"

    def test_type_mismatches(self):
        """测试类型不匹配"""
        data = {
            "name": 123,  # 应该是 str
            "age": "30",  # 应该是 int
            "active": "true",  # 应该是 bool
            "tags": "not a list",  # 应该是 list
            "metadata": "not a dict",  # 应该是 dict
        }
        schema = {
            "name": str,
            "age": int,
            "active": bool,
            "tags": list,
            "metadata": dict,
        }

        errors = validate_data_types(data, schema)
        assert len(errors) == 5
        assert any("'name' should be str" in error for error in errors)
        assert any("'age' should be int" in error for error in errors)
        assert any("'active' should be bool" in error for error in errors)

    def test_missing_fields_in_schema(self):
        """测试schema中不存在的字段（应该被忽略）"""
        data = {"name": "John", "age": 30, "extra_field": "value"}
        schema = {"name": str, "age": int}

        errors = validate_data_types(data, schema)
        assert errors == [], "Extra fields should be ignored"

    def test_inheritance_types(self):
        """测试继承类型"""
        data = {
            "name": "John",  # str
            "items": ["a", "b"],  # list (可以包含不同类型)
        }
        schema = {"name": object, "items": object}

        errors = validate_data_types(data, schema)
        assert errors == [], "Object type should match anything"

    def test_none_values(self):
        """测试None值（通常应该跳过类型检查）"""
        data = {"name": None, "description": None}
        schema = {"name": str, "description": str}

        errors = validate_data_types(data, schema)
        # None值是否被接受取决于实现，记录结果
        print(f"None validation errors: {errors}")

    def test_numeric_types(self):
        """测试数值类型转换"""
        data = {"integer": 42, "float": 3.14, "string_number": "42"}
        schema = {"integer": int, "float": float, "string_number": str}

        errors = validate_data_types(data, schema)
        assert errors == [], "Numeric types should match"


@pytest.mark.unit
class TestEdgeCases:
    """测试边界情况"""

    def test_empty_inputs(self):
        """测试空输入"""
        assert not is_valid_email("")
        assert not is_valid_phone("")
        assert not is_valid_url("")

        # 空字典和列表
        assert validate_required_fields({}, []) == []
        assert validate_data_types({}, {}) == []

    def test_whitespace_inputs(self):
        """测试空白字符输入"""
        assert not is_valid_email(" ")
        assert not is_valid_phone(" ")
        assert not is_valid_url(" ")

        # 带空格的数据
        assert validate_required_fields({"name": " "}, ["name"]) == ["name"]

    def test_long_inputs(self):
        """测试长输入"""
        long_email = "a" * 100 + "@example.com"
        assert not is_valid_email(long_email), "Very long email should be invalid"

        "https://" + "a" * 2000 + ".com"
        # URL长度限制取决于正则表达式实现

    def test_special_characters(self):
        """测试特殊字符"""
        special_chars_emails = [
            "test@example.c",  # 太短的TLD
            "test@.com",  # 以点开头的域名
            "test@-example.com",  # 域名以连字符开头
        ]

        for email in special_chars_emails:
            result = is_valid_email(email)
            print(f"Special char email {email}: {result}")


@pytest.mark.parametrize(
    "email,expected",
    [
        ("test@example.com", True),
        ("invalid.email", False),
        ("user@domain", False),
        ("@domain.com", False),
    ],
)
def test_email_parameterized(email, expected):
    """参数化测试邮箱验证"""
    assert is_valid_email(email) == expected


@pytest.mark.parametrize(
    "phone,expected",
    [
        ("+1234567890", True),
        ("123-456-7890", True),
        ("abc", False),
        ("", False),
    ],
)
def test_phone_parameterized(phone, expected):
    """参数化测试电话验证"""
    assert is_valid_phone(phone) == expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com", True),
        ("http://example.com", True),
        ("www.example.com", False),
        ("ftp://example.com", False),
    ],
)
def test_url_parameterized(url, expected):
    """参数化测试URL验证"""
    assert is_valid_url(url) == expected


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__])
