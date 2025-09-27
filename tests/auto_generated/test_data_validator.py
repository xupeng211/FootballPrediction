"""
Auto-generated tests for src.utils.data_validator module
"""

import pytest
from datetime import datetime
from src.utils.data_validator import DataValidator


class TestDataValidator:
    """测试数据验证工具类"""

    # Email validation tests
    @pytest.mark.parametrize("valid_email", [
        "test@example.com",
        "user.name@domain.co.uk",
        "test+alias@gmail.com",
        "user123@sub.domain.com",
        "a@b.co"
    ])
    def test_is_valid_email_valid_cases(self, valid_email):
        """测试有效邮箱格式"""
        assert DataValidator.is_valid_email(valid_email) is True

    @pytest.mark.parametrize("invalid_email", [
        "",
        "invalid",
        "@example.com",
        "test@",
        "test@.com",
        "test..test@example.com",
        "test@example",
        "test@.com",
        "@test.com"
    ])
    def test_is_valid_email_invalid_cases(self, invalid_email):
        """测试无效邮箱格式"""
        assert DataValidator.is_valid_email(invalid_email) is False

    # URL validation tests
    @pytest.mark.parametrize("valid_url", [
        "https://example.com",
        "http://test.domain.co.uk",
        "https://localhost:8080",
        "http://192.168.1.1:3000",
        "https://example.com/path/to/resource?param=value"
    ])
    def test_is_valid_url_valid_cases(self, valid_url):
        """测试有效URL格式"""
        assert DataValidator.is_valid_url(valid_url) is True

    @pytest.mark.parametrize("invalid_url", [
        "",
        "not_a_url",
        "ftp://example.com",
        "http://",
        "https://",
        "http://invalid..com",
        "http://192.168.1.999"  # Invalid IP
    ])
    def test_is_valid_url_invalid_cases(self, invalid_url):
        """测试无效URL格式"""
        assert DataValidator.is_valid_url(invalid_url) is False

    # Required fields validation tests
    def test_validate_required_fields_all_present(self):
        """测试所有必需字段都存在的情况"""
        data = {"name": "John", "age": 25, "email": "john@example.com"}
        required_fields = ["name", "age", "email"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert result == []

    def test_validate_required_fields_missing_fields(self):
        """测试缺失必需字段的情况"""
        data = {"name": "John", "age": 25}
        required_fields = ["name", "age", "email", "address"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert set(result) == {"email", "address"}

    def test_validate_required_fields_none_values(self):
        """测试字段值为None的情况"""
        data = {"name": "John", "age": None, "email": ""}
        required_fields = ["name", "age", "email"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert set(result) == {"age"}

    def test_validate_required_fields_empty_dict(self):
        """测试空字典的情况"""
        data = {}
        required_fields = ["name", "age"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert set(result) == {"name", "age"}

    # Data types validation tests
    def test_validate_data_types_all_correct(self):
        """测试所有数据类型都正确的情况"""
        data = {"name": "John", "age": 25, "active": True, "score": 95.5}
        type_specs = {"name": str, "age": int, "active": bool, "score": float}
        result = DataValidator.validate_data_types(data, type_specs)
        assert result == []

    def test_validate_data_types_mixed_types(self):
        """测试混合数据类型的情况"""
        data = {"name": "John", "age": "25", "active": True, "score": 95}
        type_specs = {"name": str, "age": int, "active": bool, "score": float}
        result = DataValidator.validate_data_types(data, type_specs)
        assert len(result) == 2  # age and score should be in the list
        assert any("age" in item for item in result)
        assert any("score" in item for item in result)

    def test_validate_data_types_missing_fields(self):
        """测试缺失字段的情况"""
        data = {"name": "John", "age": 25}
        type_specs = {"name": str, "age": int, "email": str}
        result = DataValidator.validate_data_types(data, type_specs)
        assert result == []  # Missing fields should not be reported

    # Input sanitization tests
    @pytest.mark.parametrize("input_data,expected_output", [
        ("<script>alert('xss')</script>", "scriptalertxssscript"),
        ("Hello 'World'!", "Hello World!"),
        (None, ""),
        (123, "123"),
        ("", ""),
        ("   spaced string   ", "spaced string"),
        ("a" * 1200, "a" * 1000)  # Test length truncation
    ])
    def test_sanitize_input(self, input_data, expected_output):
        """测试输入数据清理"""
        result = DataValidator.sanitize_input(input_data)
        assert result == expected_output

    def test_sanitize_input_dangerous_chars(self):
        """测试危险字符清理"""
        dangerous_input = '<script>alert("xss");</script>\x00\r\n'
        result = DataValidator.sanitize_input(dangerous_input)
        # Should remove all dangerous characters
        assert '<' not in result
        assert '>' not in result
        assert '"' not in result
        assert "'" not in result
        assert '&' not in result
        assert '\x00' not in result
        assert '\r' not in result
        assert '\n' not in result

    # Email validation alias method tests
    def test_validate_email_alias_method(self):
        """测试邮箱验证别名方法"""
        # Should behave the same as is_valid_email
        email = "test@example.com"
        assert DataValidator.validate_email(email) == DataValidator.is_valid_email(email)

    # Phone validation tests
    @pytest.mark.parametrize("valid_phone", [
        "13812345678",  # Chinese mobile
        "+8613812345678",  # International format
        "12345678",  # Simple 8-digit
        "+123456789012",  # International with 12 digits
        "987654321098765",  # 15 digits
    ])
    def test_validate_phone_valid_cases(self, valid_phone):
        """测试有效手机号格式"""
        assert DataValidator.validate_phone(valid_phone) is True

    @pytest.mark.parametrize("invalid_phone", [
        "",
        "123",  # Too short
        "1234567890123456",  # Too long
        "+1234567890123456",  # International format too long
        "abc12345678",  # Contains letters
        "123-456-7890",  # Contains dashes
        "(123) 456-7890",  # Contains parentheses
    ])
    def test_validate_phone_invalid_cases(self, invalid_phone):
        """测试无效手机号格式"""
        assert DataValidator.validate_phone(invalid_phone) is False

    def test_validate_phone_with_special_chars(self):
        """测试包含特殊字符的手机号清理"""
        phone = "+86 (138) 1234-5678"
        assert DataValidator.validate_phone(phone) is True

    # Date range validation tests
    def test_validate_date_range_valid(self):
        """测试有效日期范围"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        assert DataValidator.validate_date_range(start_date, end_date) is True

    def test_validate_date_range_same_date(self):
        """测试相同日期"""
        date = datetime(2023, 6, 15)
        assert DataValidator.validate_date_range(date, date) is True

    def test_validate_date_range_invalid_order(self):
        """测试无效日期顺序"""
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)
        assert DataValidator.validate_date_range(start_date, end_date) is False

    def test_validate_date_range_invalid_types(self):
        """测试无效数据类型"""
        start_date = "2023-01-01"
        end_date = datetime(2023, 12, 31)
        assert DataValidator.validate_date_range(start_date, end_date) is False

        start_date = datetime(2023, 1, 1)
        end_date = "2023-12-31"
        assert DataValidator.validate_date_range(start_date, end_date) is False

        start_date = None
        end_date = datetime(2023, 12, 31)
        assert DataValidator.validate_date_range(start_date, end_date) is False

    # Edge cases and integration tests
    def test_comprehensive_validation_scenario(self):
        """测试综合验证场景"""
        # Simulate form data validation
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "website": "https://johndoe.com",
            "phone": "+1234567890"
        }

        # Validate required fields
        required_fields = ["name", "email", "age"]
        missing_fields = DataValidator.validate_required_fields(form_data, required_fields)
        assert missing_fields == []

        # Validate data types
        type_specs = {"name": str, "email": str, "age": int}
        invalid_types = DataValidator.validate_data_types(form_data, type_specs)
        assert invalid_types == []

        # Validate specific formats
        assert DataValidator.validate_email(form_data["email"]) is True
        assert DataValidator.validate_phone(form_data["phone"]) is True
        assert DataValidator.is_valid_url(form_data["website"]) is True

    def test_validation_error_accumulation(self):
        """测试验证错误累积"""
        data = {
            "name": 123,  # Should be string
            "age": "not_a_number",  # Should be int
            "email": "invalid_email"  # Invalid format
        }

        required_fields = ["name", "age", "email", "missing_field"]
        type_specs = {"name": str, "age": int, "email": str}

        missing_fields = DataValidator.validate_required_fields(data, required_fields)
        invalid_types = DataValidator.validate_data_types(data, type_specs)
        email_valid = DataValidator.validate_email(data["email"])

        assert len(missing_fields) == 1
        assert len(invalid_types) == 2
        assert email_valid is False