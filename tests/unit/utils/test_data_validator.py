from datetime import datetime
from src.utils.data_validator import DataValidator

"""
测试数据验证工具模块
"""


class TestDataValidator:
    """测试DataValidator类"""

    def test_is_valid_email_valid_emails(self):
        """测试有效的邮箱地址"""
        valid_emails = [
            "user@example.com",
            "test.email@example.com",
            "user+tag@example.com",
            "user123@example-site.com",
            "test_email@example.co.uk",
        ]

        for email in valid_emails:
            assert DataValidator.is_valid_email(email), f"应该验证通过: {email}"

    def test_is_valid_email_invalid_emails(self):
        """测试无效的邮箱地址"""
        invalid_emails = [
            "invalid-email",  # 缺少@
            "@example.com",  # 缺少用户名
            "user@",  # 缺少域名
            "user@.com",  # 域名不能以点开头
            "user@com",  # 顶级域名太短
            "user..name@example.com",  # 连续点
            "",  # 空字符串
        ]

        for email in invalid_emails:
            assert not DataValidator.is_valid_email(email), f"应该验证失败: {email}"

    def test_validate_required_fields_all_present(self):
        """测试所有必需字段都存在"""
        data = {"name": "张三", "age": 25, "email": "zhangsan@example.com"}
        required = ["name", "age", "email"]
        missing = DataValidator.validate_required_fields(data, required)
        assert missing == []

    def test_validate_required_fields_missing_some(self):
        """测试缺少必需字段"""
        data = {"name": "张三"}
        required = ["name", "age", "email"]
        missing = DataValidator.validate_required_fields(data, required)
        assert set(missing) == {"age", "email"}

    def test_validate_required_fields_none_values(self):
        """测试字段值为None"""
        data = {"name": None, "age": 25}
        required = ["name", "age"]
        missing = DataValidator.validate_required_fields(data, required)
        assert missing == ["name"]

    def test_validate_data_types_all_valid(self):
        """测试所有字段类型正确"""
        data = {"name": "张三", "age": 25, "active": True}
        types = {"name": str, "age": int, "active": bool}
        invalid = DataValidator.validate_data_types(data, types)
        assert invalid == []

    def test_validate_data_types_invalid_types(self):
        """测试字段类型不正确"""
        data = {"name": "张三", "age": "25", "active": "true"}
        types = {"name": str, "age": int, "active": bool}
        invalid = DataValidator.validate_data_types(data, types)
        assert len(invalid) == 2
        assert any("age" in error for error in invalid)
        assert any("active" in error for error in invalid)

    def test_sanitize_input_none(self):
        """测试None输入"""
        result = DataValidator.sanitize_input(None)
        assert result == ""

    def test_sanitize_input_normal_text(self):
        """测试普通文本"""
        result = DataValidator.sanitize_input("Hello, World!")
        assert result == "Hello, World!"

    def test_sanitize_input_dangerous_chars(self):
        """测试危险字符"""
        result = DataValidator.sanitize_input("<script>alert('xss')</script>")
        assert result == "scriptalert(xss)script"

    def test_sanitize_input_newlines_and_tabs(self):
        """测试换行符和制表符"""
        result = DataValidator.sanitize_input("Line 1\nLine 2\tTab")
        assert result == "Line 1Line 2Tab"

    def test_sanitize_input_long_text(self):
        """测试超长文本"""
        long_text = "a" * 1500
        result = DataValidator.sanitize_input(long_text)
        assert len(result) == 1000
        assert result.endswith("a")

    def test_validate_email_alias(self):
        """测试邮箱验证别名方法"""
        assert DataValidator.validate_email("user@example.com")
        assert not DataValidator.validate_email("invalid-email")

    def test_validate_phone_chinese(self):
        """测试中国手机号"""
        assert DataValidator.validate_phone("13812345678")
        assert DataValidator.validate_phone("15098765432")

    def test_validate_phone_international(self):
        """测试国际手机号"""
        assert DataValidator.validate_phone("+8613812345678")
        assert DataValidator.validate_phone("+1234567890")

    def test_validate_phone_invalid(self):
        """测试无效手机号"""
        assert not DataValidator.validate_phone("12345678")  # 太短
        assert not DataValidator.validate_phone("abc1234567")  # 包含字母

    def test_validate_date_range_valid(self):
        """测试有效的日期范围"""
        start = datetime(2021, 1, 1)
        end = datetime(2021, 1, 31)
        assert DataValidator.validate_date_range(start, end)

    def test_validate_date_range_equal(self):
        """测试相等的日期"""
        start = datetime(2021, 1, 1, 12, 0, 0)
        end = datetime(2021, 1, 1, 12, 0, 0)
        assert DataValidator.validate_date_range(start, end)

    def test_validate_date_range_invalid(self):
        """测试无效的日期范围"""
        start = datetime(2021, 1, 31)
        end = datetime(2021, 1, 1)
        assert not DataValidator.validate_date_range(start, end)
