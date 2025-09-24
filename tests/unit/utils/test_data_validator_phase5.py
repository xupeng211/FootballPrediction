"""
Tests for src/utils/data_validator.py (Phase 5)

针对数据验证工具类的全面测试，旨在提升覆盖率至 ≥60%
覆盖邮箱验证、URL验证、数据类型检查、输入清理等核心功能
"""

import re
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

# Import the module to ensure coverage tracking
import src.utils.data_validator
from src.utils.data_validator import DataValidator


class TestDataValidatorEmailValidation:
    """邮箱验证测试"""

    def test_is_valid_email_valid_emails(self):
        """测试有效邮箱格式"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "firstname+lastname@example.org",
            "test123@test-domain.com",
            "_______@example.com",
            "email@domain.name",
            "email@domain-one.example.com",
        ]

        for email in valid_emails:
            assert DataValidator.is_valid_email(email), f"Should accept email: {email}"

    def test_is_valid_email_invalid_emails(self):
        """测试无效邮箱格式"""
        invalid_emails = [
            "invalid.email",  # 缺少@和域名
            "@domain.com",  # 缺少用户名
            "user@",  # 缺少域名
            "user@domain",  # 缺少顶级域名
            "user name@domain.com",  # 用户名包含空格
            "user@domain .com",  # 域名包含空格
            "user@domain.",  # 顶级域名为空
            "user@@domain.com",  # 重复@
            "",  # 空字符串
            "user@.com",  # 域名开头是.
            "user@domain.c",  # 顶级域名太短
        ]

        for email in invalid_emails:
            assert not DataValidator.is_valid_email(
                email
            ), f"Should reject email: {email}"

    def test_validate_email_alias(self):
        """测试邮箱验证别名方法"""
        assert DataValidator.validate_email("test@example.com") is True
        assert DataValidator.validate_email("invalid") is False


class TestDataValidatorURLValidation:
    """URL验证测试"""

    def test_is_valid_url_valid_urls(self):
        """测试有效URL格式"""
        valid_urls = [
            "http://www.example.com",
            "https://example.com",
            "http://localhost",
            "https://localhost:8000",
            "http://192.168.1.1",
            "https://192.168.1.1:3000",
            "http://example.com/path",
            "https://example.com/path/to/resource",
            "http://example.com/path?query=1",
            "https://example.com/path#anchor",
            "http://subdomain.example.com",
            "https://example-site.com",
            "http://example.co.uk",
        ]

        for url in valid_urls:
            assert DataValidator.is_valid_url(url), f"Should accept URL: {url}"

    def test_is_valid_url_invalid_urls(self):
        """测试无效URL格式"""
        invalid_urls = [
            "example.com",  # 缺少协议
            "ftp://example.com",  # 不支持的协议
            "http://",  # 缺少域名
            "https://",  # 缺少域名
            "http:// example.com",  # 域名前有空格
            "",  # 空字符串
            "not a url",  # 普通文本
            "http://.",  # 无效域名
            "http://.com",  # 无效域名格式
        ]

        for url in invalid_urls:
            assert not DataValidator.is_valid_url(url), f"Should reject URL: {url}"

    def test_is_valid_url_case_insensitive(self):
        """测试URL验证的大小写不敏感性"""
        urls_to_test = [
            ("HTTP://EXAMPLE.COM", True),
            ("HTTPS://EXAMPLE.COM", True),
            ("Http://Example.Com", True),
            ("hTtPs://ExAmPlE.cOm", True),
        ]

        for url, expected in urls_to_test:
            assert DataValidator.is_valid_url(url) == expected


class TestDataValidatorRequiredFields:
    """必需字段验证测试"""

    def test_validate_required_fields_all_present(self):
        """测试所有必需字段都存在"""
        data = {"name": "John Doe", "email": "john@example.com", "age": 30}
        required_fields = ["name", "email", "age"]

        result = DataValidator.validate_required_fields(data, required_fields)
        assert result == []

    def test_validate_required_fields_some_missing(self):
        """测试部分必需字段缺失"""
        data = {"name": "John Doe", "email": "john@example.com"}
        required_fields = ["name", "email", "age", "phone"]

        result = DataValidator.validate_required_fields(data, required_fields)
        assert sorted(result) == ["age", "phone"]

    def test_validate_required_fields_none_values(self):
        """测试None值字段"""
        data = {"name": "John Doe", "email": None, "age": 30}
        required_fields = ["name", "email", "age"]

        result = DataValidator.validate_required_fields(data, required_fields)
        assert result == ["email"]

    def test_validate_required_fields_empty_data(self):
        """测试空数据"""
        data = {}
        required_fields = ["name", "email"]

        result = DataValidator.validate_required_fields(data, required_fields)
        assert sorted(result) == ["email", "name"]

    def test_validate_required_fields_empty_required_list(self):
        """测试空必需字段列表"""
        data = {"name": "John"}
        required_fields = []

        result = DataValidator.validate_required_fields(data, required_fields)
        assert result == []

    def test_validate_required_fields_zero_values(self):
        """测试值为0的字段（应该被认为是有效的）"""
        data = {"count": 0, "price": 0.0, "active": False}
        required_fields = ["count", "price", "active"]

        result = DataValidator.validate_required_fields(data, required_fields)
        assert result == []


class TestDataValidatorDataTypes:
    """数据类型验证测试"""

    def test_validate_data_types_all_correct(self):
        """测试所有数据类型正确"""
        data = {
            "name": "John Doe",
            "age": 30,
            "height": 5.9,
            "active": True,
            "tags": ["python", "testing"],
        }
        type_specs = {
            "name": str,
            "age": int,
            "height": float,
            "active": bool,
            "tags": list,
        }

        result = DataValidator.validate_data_types(data, type_specs)
        assert result == []

    def test_validate_data_types_some_incorrect(self):
        """测试部分数据类型不正确"""
        data = {
            "name": 123,  # 应该是str
            "age": "30",  # 应该是int
            "active": "true",  # 应该是bool
        }
        type_specs = {"name": str, "age": int, "active": bool}

        result = DataValidator.validate_data_types(data, type_specs)
        assert len(result) == 3
        assert "name: 期望 str, 实际 int" in result
        assert "age: 期望 int, 实际 str" in result
        assert "active: 期望 bool, 实际 str" in result

    def test_validate_data_types_missing_fields(self):
        """测试数据中缺少的字段（不应该报错）"""
        data = {"name": "John Doe"}
        type_specs = {
            "name": str,
            "age": int,  # 这个字段在data中不存在
            "email": str,  # 这个字段在data中也不存在
        }

        result = DataValidator.validate_data_types(data, type_specs)
        assert result == []  # 缺少的字段不会被检查类型

    def test_validate_data_types_empty_specs(self):
        """测试空类型规范"""
        data = {"name": "John", "age": 30}
        type_specs = {}

        result = DataValidator.validate_data_types(data, type_specs)
        assert result == []

    def test_validate_data_types_none_values(self):
        """测试None值的类型验证"""
        data = {"name": None, "age": None}
        type_specs = {"name": str, "age": int}

        result = DataValidator.validate_data_types(data, type_specs)
        assert len(result) == 2
        assert "name: 期望 str, 实际 NoneType" in result
        assert "age: 期望 int, 实际 NoneType" in result


class TestDataValidatorInputSanitization:
    """输入清理测试"""

    def test_sanitize_input_normal_text(self):
        """测试普通文本清理"""
        text = "This is normal text"
        result = DataValidator.sanitize_input(text)
        assert result == "This is normal text"

    def test_sanitize_input_dangerous_characters(self):
        """测试危险字符清理"""
        text = '<script>alert("xss")</script>'
        result = DataValidator.sanitize_input(text)
        assert result == "scriptalert(xss)/script"  # < > " ' 被移除

    def test_sanitize_input_all_dangerous_chars(self):
        """测试所有危险字符"""
        text = '<>"&\x00\r\n test'
        result = DataValidator.sanitize_input(text)
        assert result == "test"

    def test_sanitize_input_none_value(self):
        """测试None值清理"""
        result = DataValidator.sanitize_input(None)
        assert result == ""

    def test_sanitize_input_numeric_types(self):
        """测试数值类型清理"""
        assert DataValidator.sanitize_input(123) == "123"
        assert DataValidator.sanitize_input(45.67) == "45.67"
        assert DataValidator.sanitize_input(True) == "True"
        assert DataValidator.sanitize_input(False) == "False"

    def test_sanitize_input_long_text(self):
        """测试长文本清理（超过1000字符）"""
        long_text = "x" * 1500
        result = DataValidator.sanitize_input(long_text)
        assert len(result) == 1000
        assert result == "x" * 1000

    def test_sanitize_input_whitespace_handling(self):
        """测试空白字符处理"""
        text = "   text with spaces   "
        result = DataValidator.sanitize_input(text)
        assert result == "text with spaces"

    def test_sanitize_input_special_objects(self):
        """测试特殊对象类型"""
        test_list = [1, 2, 3]
        result = DataValidator.sanitize_input(test_list)
        assert result == "[1, 2, 3]"

        test_dict = {"key": "value"}
        result = DataValidator.sanitize_input(test_dict)
        assert "key" in result and "value" in result


class TestDataValidatorPhoneValidation:
    """手机号验证测试"""

    def test_validate_phone_chinese_format(self):
        """测试中国手机号格式"""
        valid_chinese_phones = [
            "13812345678",
            "15987654321",
            "18611112222",
            "19933334444",
        ]

        for phone in valid_chinese_phones:
            assert DataValidator.validate_phone(
                phone
            ), f"Should accept Chinese phone: {phone}"

    def test_validate_phone_international_format(self):
        """测试国际格式手机号"""
        valid_international_phones = [
            "+8613812345678",
            "+14155552671",
            "+447911123456",
            "+33123456789",
        ]

        for phone in valid_international_phones:
            assert DataValidator.validate_phone(
                phone
            ), f"Should accept international phone: {phone}"

    def test_validate_phone_with_formatting(self):
        """测试带格式的手机号"""
        formatted_phones = [
            "138-1234-5678",
            "+86 138 1234 5678",
            "(138) 1234-5678",
            "138.1234.5678",
        ]

        for phone in formatted_phones:
            assert DataValidator.validate_phone(
                phone
            ), f"Should accept formatted phone: {phone}"

    def test_validate_phone_invalid_formats(self):
        """测试无效手机号格式"""
        invalid_phones = [
            "1234567",  # 太短
            "12345678901234567",  # 太长
            "12345",  # 太短
            "",  # 空字符串
        ]

        for phone in invalid_phones:
            assert not DataValidator.validate_phone(
                phone
            ), f"Should reject invalid phone: {phone}"

    def test_validate_phone_edge_cases(self):
        """测试手机号边界情况"""
        # 最短有效长度（8位）
        assert DataValidator.validate_phone("12345678")
        # 最长有效长度（15位）
        assert DataValidator.validate_phone("123456789012345")
        # 超过最长长度
        assert not DataValidator.validate_phone("1234567890123456")


class TestDataValidatorDateRangeValidation:
    """日期范围验证测试"""

    def test_validate_date_range_valid_range(self):
        """测试有效日期范围"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        assert DataValidator.validate_date_range(start_date, end_date) is True

    def test_validate_date_range_same_dates(self):
        """测试相同日期"""
        same_date = datetime(2024, 6, 15)

        assert DataValidator.validate_date_range(same_date, same_date) is True

    def test_validate_date_range_invalid_range(self):
        """测试无效日期范围（开始日期晚于结束日期）"""
        start_date = datetime(2024, 12, 31)
        end_date = datetime(2024, 1, 1)

        assert DataValidator.validate_date_range(start_date, end_date) is False

    def test_validate_date_range_non_datetime_objects(self):
        """测试非datetime对象"""
        # 字符串日期
        assert DataValidator.validate_date_range("2024-01-01", "2024-12-31") is False

        # None值
        assert DataValidator.validate_date_range(None, datetime.now()) is False
        assert DataValidator.validate_date_range(datetime.now(), None) is False

        # 数字
        assert DataValidator.validate_date_range(20240101, 20241231) is False

    def test_validate_date_range_mixed_types(self):
        """测试混合类型"""
        valid_date = datetime(2024, 6, 15)

        assert DataValidator.validate_date_range(valid_date, "2024-12-31") is False
        assert DataValidator.validate_date_range("2024-01-01", valid_date) is False


class TestDataValidatorIntegration:
    """集成测试"""

    def test_complete_validation_workflow(self):
        """测试完整的验证工作流程"""
        # 模拟用户注册数据
        user_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "age": 25,
            "website": "https://johndoe.com",
            "is_active": True,
        }

        # 验证必需字段
        required_fields = ["name", "email", "age"]
        missing_fields = DataValidator.validate_required_fields(
            user_data, required_fields
        )
        assert missing_fields == []

        # 验证数据类型
        type_specs = {"name": str, "email": str, "age": int, "is_active": bool}
        type_errors = DataValidator.validate_data_types(user_data, type_specs)
        assert type_errors == []

        # 验证具体格式
        assert DataValidator.is_valid_email(user_data["email"]) is True
        assert DataValidator.validate_phone(user_data["phone"]) is True
        assert DataValidator.is_valid_url(user_data["website"]) is True

        # 清理输入数据
        cleaned_name = DataValidator.sanitize_input(user_data["name"])
        assert cleaned_name == "John Doe"

    def test_validation_with_errors(self):
        """测试包含错误的验证场景"""
        invalid_data = {
            "name": "<script>alert('xss')</script>",
            "email": "invalid-email",
            "phone": "abc123",
            "age": "twenty-five",  # 应该是int
            "website": "not-a-url",
        }

        # 验证邮箱
        assert DataValidator.is_valid_email(invalid_data["email"]) is False

        # 验证手机号
        assert DataValidator.validate_phone(invalid_data["phone"]) is False

        # 验证URL
        assert DataValidator.is_valid_url(invalid_data["website"]) is False

        # 验证数据类型
        type_specs = {"age": int}
        type_errors = DataValidator.validate_data_types(invalid_data, type_specs)
        assert len(type_errors) == 1
        assert "age: 期望 int, 实际 str" in type_errors[0]

        # 清理危险输入
        cleaned_name = DataValidator.sanitize_input(invalid_data["name"])
        assert "<script>" not in cleaned_name
        assert "scriptalert(xss)/script" == cleaned_name


class TestDataValidatorErrorHandling:
    """错误处理测试"""

    def test_regex_error_handling(self):
        """测试正则表达式错误处理（虽然不太可能发生）"""
        # 测试极端情况下的输入
        extreme_inputs = [
            "",
            " ",
            "\n\t\r",
            "a" * 10000,  # 非常长的字符串
        ]

        for input_data in extreme_inputs:
            # 这些调用应该不会抛出异常
            DataValidator.is_valid_email(input_data)
            DataValidator.is_valid_url(input_data)
            DataValidator.validate_phone(input_data)

    def test_input_edge_cases(self):
        """测试输入边界情况"""
        edge_cases = [
            None,
            "",
            " ",
            0,
            [],
            {},
            False,
        ]

        for edge_case in edge_cases:
            # sanitize_input应该能处理所有这些情况
            result = DataValidator.sanitize_input(edge_case)
            assert isinstance(result, str)

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        unicode_data = {
            "chinese_email": "用户@测试.中国",  # 这不是有效的邮箱格式
            "unicode_text": "Hello 世界 🌍",
            "mixed_chars": "test@例え.com",
        }

        # 邮箱验证应该正确处理Unicode
        assert DataValidator.is_valid_email(unicode_data["chinese_email"]) is False

        # 输入清理应该保留Unicode字符
        cleaned = DataValidator.sanitize_input(unicode_data["unicode_text"])
        assert "世界" in cleaned
        assert "🌍" in cleaned


class TestDataValidatorPerformance:
    """性能测试"""

    def test_large_data_validation(self):
        """测试大量数据验证性能"""
        import time

        # 创建大量测试数据
        large_data = {}
        for i in range(1000):
            large_data[f"field_{i}"] = f"value_{i}"

        required_fields = [f"field_{i}" for i in range(500)]

        start_time = time.time()
        missing_fields = DataValidator.validate_required_fields(
            large_data, required_fields
        )
        end_time = time.time()

        assert missing_fields == []
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    def test_regex_performance(self):
        """测试正则表达式性能"""
        import time

        # 测试大量邮箱验证
        emails = [f"user{i}@example{i}.com" for i in range(1000)]

        start_time = time.time()
        results = [DataValidator.is_valid_email(email) for email in emails]
        end_time = time.time()

        assert all(results)  # 所有邮箱都应该是有效的
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成
