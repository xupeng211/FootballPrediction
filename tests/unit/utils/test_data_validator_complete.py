from typing import Optional

"""
DataValidator完整测试 - 深化47.7%到70%+覆盖率
针对未覆盖的数据验证函数进行全面测试
"""

from src.utils.data_validator import DataValidator


class TestDataValidatorComplete:
    """DataValidator完整测试类 - 提升覆盖率到70%+"""

    def test_sanitize_input_function(self):
        """测试输入清理功能"""
        # 基本清理
        assert DataValidator.sanitize_input("Hello World") == "Hello World"

        # 危险字符移除
        dangerous_input = "<script>alert('xss')</script>"
        cleaned = DataValidator.sanitize_input(dangerous_input)
        assert "<script>" not in cleaned
        # alert关键词可能保留（避免过度过滤）

        # None输入
        assert DataValidator.sanitize_input(None) == ""

        # 数字输入
        assert DataValidator.sanitize_input(123) == "123"

        # 长度限制
        long_input = "a" * 2000
        result = DataValidator.sanitize_input(long_input)
        assert len(result) == 1000

    def test_validate_username_function(self):
        """测试用户名验证功能"""
        # 有效用户名
        valid_usernames = ["user123", "test_user", "User1234567890123456"]
        for username in valid_usernames:
            assert DataValidator.validate_username(username) is True

        # 无效用户名
        invalid_usernames = ["ab", "user@domain", "user-name", "用户名123", ""]
        for username in invalid_usernames:
            assert DataValidator.validate_username(username) is False

    def test_validate_password_strength_function(self):
        """测试密码强度验证功能"""
        # 强密码
        strong_password = "Password123!"
        result = DataValidator.validate_password_strength(strong_password)
        assert result["valid"] is True
        assert result["strength"] == 5
        assert len(result["issues"]) == 0

        # 弱密码
        weak_password = "password"
        result = DataValidator.validate_password_strength(weak_password)
        assert isinstance(result, dict)
        assert "valid" in result
        assert "strength" in result
        assert "issues" in result

        # None输入
        result = DataValidator.validate_password_strength(None)
        assert result["valid"] is False

    def test_validate_positive_number_function(self):
        """测试正数验证功能"""
        # 有效正数
        valid_numbers = [1, 1.5, "1", "1.5"]
        for number in valid_numbers:
            assert DataValidator.validate_positive_number(number) is True

        # 无效数字
        invalid_numbers = [0, -1, "0", "-1", "abc", None]
        for number in invalid_numbers:
            assert DataValidator.validate_positive_number(number) is False

    def test_validate_required_fields_function(self):
        """测试必填字段验证功能"""
        # 有效数据
        data = {"name": "John", "email": "john@example.com"}
        required_fields = ["name", "email"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert result["valid"] is True

        # 缺少字段
        data = {"name": "John"}
        required_fields = ["name", "email"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert result["valid"] is False
        assert "email" in result["missing"]

        # 空值字段
        data = {"name": "", "email": None}
        required_fields = ["name", "email"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert result["valid"] is False

    def test_edge_cases(self):
        """测试边界情况"""
        # 所有验证函数对None的处理
        assert DataValidator.validate_email(None) is False
        assert DataValidator.validate_phone(None) is False
        assert DataValidator.validate_url(None) is False
        assert DataValidator.validate_id_card(None) is False
        assert DataValidator.validate_username(None) is False

        # 空字符串处理
        assert DataValidator.validate_email("") is False
        assert DataValidator.validate_phone("") is False
        assert DataValidator.validate_url("") is False
        assert DataValidator.validate_id_card("") is False
        assert DataValidator.validate_username("") is False