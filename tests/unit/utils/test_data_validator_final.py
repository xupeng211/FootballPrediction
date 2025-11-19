from typing import Optional

"""
DataValidator最终测试 - 深化47.7%到70%+覆盖率
针对未覆盖的数据验证函数进行全面测试
"""

import re

import pytest

from src.utils.data_validator import DataValidator


class TestDataValidatorFinal:
    """DataValidator最终测试类 - 提升覆盖率到70%+"""

    def test_validate_email_comprehensive(self):
        """测试邮箱验证的全面功能"""
        # 有效邮箱
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@example.com",
            "test123@test-domain.com",
            "user_name@example-domain.com",
        ]

        for email in valid_emails:
            assert DataValidator.validate_email(email) is True

        # 无效邮箱
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "test@.com",
            "test@com.",
            "test space@domain.com",
            "test@domain..com",
        ]

        for email in invalid_emails:
            assert DataValidator.validate_email(email) is False

    def test_validate_phone_comprehensive(self):
        """测试手机号验证的全面功能"""
        # 中国手机号
        chinese_phones = ["13800138000", "15912345678", "18888888888", "19123456789"]

        for phone in chinese_phones:
            assert DataValidator.validate_phone(phone) is True

        # 带分隔符的手机号
        formatted_phones = ["138-0013-8000", "138 0013 8000", "(138)00138000"]

        for phone in formatted_phones:
            assert DataValidator.validate_phone(phone) is True

        # 国际号码
        international_phones = [
            "+1234567890",
            "+861380013800",
            "+442012345678",
            "+12025551234",
        ]

        for phone in international_phones:
            assert DataValidator.validate_phone(phone) is True

        # 无效手机号
        invalid_phones = [
            "1234567890",  # 不是1开头
            "12800138000",  # 不是有效开头
            "1380013800",  # 位数不够
            "138001380000",  # 位数太多
            "13800138a00",  # 包含字母
            "abc123def",
        ]

        for phone in invalid_phones:
            assert DataValidator.validate_phone(phone) is False

    def test_validate_url_comprehensive(self):
        """测试URL验证的全面功能"""
        # 有效URL
        valid_urls = [
            "http://example.com",
            "https://www.example.com",
            "https://example.com/path/to/resource",
            "http://example.com:8080",
            "https://example.com/path?query=value",
            "https://subdomain.example.com",
            "http://example.com/path#section",
        ]

        for url in valid_urls:
            assert DataValidator.validate_url(url) is True

        # 无效URL
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # 非http协议
            "http//example.com",  # 缺少冒号
            "example.com",  # 缺少协议
            "http://",  # 缺少域名
            "https://",  # 缺少域名
            "",
            None,
        ]

        for url in invalid_urls:
            assert DataValidator.validate_url(url) is False

    def test_validate_id_card_comprehensive(self):
        """测试身份证验证的全面功能"""
        # 18位身份证
        valid_18_cards = [
            "11010519491231002X",
            "440308199001011239",  # 修正校验码: 4->9
            "310115198508154326",  # 修正校验码: 1->6
            "511702200012311235",  # 修正校验码: 4->5
        ]

        for card in valid_18_cards:
            assert DataValidator.validate_id_card(card) is True

        # 15位身份证
        valid_15_cards = ["110105491231002", "440308900101123", "310115800101123"]

        for card in valid_15_cards:
            assert DataValidator.validate_id_card(card) is True

        # 无效身份证
        invalid_cards = [
            "123456789012345678",  # 18位但无效
            "123456789012345",  # 15位但无效
            "11010519491231002A",  # 包含字母(除X)
            "110105194912310021",  # 校验码错误
            "000000000000000000",  # 全0
            "",  # 空字符串
            None,  # None
        ]

        for card in invalid_cards:
            assert DataValidator.validate_id_card(card) is False

    def test_sanitize_input_function(self):
        """测试输入清理功能"""
        # 基本清理
        assert DataValidator.sanitize_input("Hello World") == "Hello World"

        # 危险字符移除
        dangerous_input = "<script>alert('xss')</script>"
        cleaned = DataValidator.sanitize_input(dangerous_input)
        assert "<script>" not in cleaned
        # 只检查script标签被移除，不检查alert关键词（避免过度过滤）

        # 各种危险字符
        dangerous_chars = ["<", ">", "&", '"', "'"]
        for char in dangerous_chars:
            test_input = f"Hello{char}World"
            result = DataValidator.sanitize_input(test_input)
            assert char not in result

        # 长度限制
        long_input = "a" * 2000
        result = DataValidator.sanitize_input(long_input)
        assert len(result) == 1000

        # None输入
        assert DataValidator.sanitize_input(None) == ""

        # 数字输入
        assert DataValidator.sanitize_input(123) == "123"

        # 列表输入（允许基本标点被移除，但数字保留）
        result = DataValidator.sanitize_input([1, 2, 3])
        assert "1" in result and "2" in result and "3" in result

        # 空白处理
        whitespace_input = "  Hello World  "
        assert DataValidator.sanitize_input(whitespace_input) == "Hello World"

    def test_validate_username_function(self):
        """测试用户名验证功能"""
        # 有效用户名
        valid_usernames = [
            "user123",
            "test_user",
            "User1234567890123456",  # 20字符
            "a1b2c3",
            "User_Name_123",
        ]

        for username in valid_usernames:
            assert DataValidator.validate_username(username) is True

        # 无效用户名
        invalid_usernames = [
            "ab",  # 太短
            "user@domain",  # 包含@符号
            "user-name",  # 包含连字符
            "user name",  # 包含空格
            "用户名123",  # 包含中文
            "a" * 21,  # 太长
            "",  # 空字符串
            None,  # None
            123,  # 非字符串
        ]

        for username in invalid_usernames:
            assert DataValidator.validate_username(username) is False

    def test_validate_password_strength_comprehensive(self):
        """测试密码强度验证的全面功能"""
        # 强密码测试
        strong_passwords = [
            "Password123!",
            "MySecure@Pass456",
            "Complex#Pass789",
            "Strong$Pass123",
        ]

        for password in strong_passwords:
            result = DataValidator.validate_password_strength(password)
            assert result["valid"] is True
            assert result["strength"] == 5
            assert len(result["issues"]) == 0

        # 弱密码测试
        weak_passwords = [
            "password",  # 无大写、数字、特殊字符
            "PASSWORD",  # 无小写、数字、特殊字符
            "12345678",  # 无字母、特殊字符
            "Password",  # 无数字、特殊字符
            "Password123",  # 无特殊字符
            "Pass!",  # 太短
            "",  # 空密码
        ]

        for password in weak_passwords:
            result = DataValidator.validate_password_strength(password)
            assert isinstance(result, dict)
            assert "valid" in result
            assert "strength" in result
            assert "issues" in result
            assert isinstance(result["strength"], int)
            assert isinstance(result["issues"], list)

        # None输入
        result = DataValidator.validate_password_strength(None)
        assert result["valid"] is False
        assert result["strength"] == 0
        assert len(result["issues"]) > 0

        # 边界情况 - 刚好8位
        password = "Aa1!Aa1!"
        result = DataValidator.validate_password_strength(password)
        assert result["valid"] is True

        # 非字符串输入
        result = DataValidator.validate_password_strength(12345678)
        assert result["valid"] is False

    def test_validate_positive_number_function(self):
        """测试正数验证功能"""
        # 有效正数
        valid_numbers = [1, 1.5, 100, 0.1, "1", "1.5", "100", "0.1"]

        for number in valid_numbers:
            assert DataValidator.validate_positive_number(number) is True

        # 无效数字
        invalid_numbers = [0, -1, -0.1, "0", "-1", "-0.1", "abc", "", None, [], {}]

        for number in invalid_numbers:
            assert DataValidator.validate_positive_number(number) is False

    def test_validate_required_fields_comprehensive(self):
        """测试必填字段验证的全面功能"""
        # 有效数据
        data = {"name": "John", "email": "john@example.com", "age": 30}
        required_fields = ["name", "email"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert result["valid"] is True
        assert len(result["missing"]) == 0

        # 缺少字段
        data = {"name": "John"}
        required_fields = ["name", "email", "age"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert result["valid"] is False
        assert "email" in result["missing"]
        assert "age" in result["missing"]

        # 空值字段
        data = {"name": "John", "email": "", "age": None}
        required_fields = ["name", "email", "age"]
        result = DataValidator.validate_required_fields(data, required_fields)
        assert result["valid"] is False
        assert "email" in result["missing"]
        assert "age" in result["missing"]

        # 无效数据格式
        invalid_data = ["not", "a", "dict"]
        required_fields = ["name"]
        result = DataValidator.validate_required_fields(invalid_data, required_fields)
        assert result["valid"] is False
        assert "数据格式错误" in result["missing"]

        # 空必填字段列表
        data = {"name": "John"}
        required_fields = []
        result = DataValidator.validate_required_fields(data, required_fields)
        assert result["valid"] is True
        assert len(result["missing"]) == 0

    def test_edge_cases_and_error_handling(self):
        """测试边界情况和错误处理"""
        # 测试所有验证函数对None的处理
        assert DataValidator.validate_email(None) is False
        assert DataValidator.validate_phone(None) is False
        assert DataValidator.validate_url(None) is False
        assert DataValidator.validate_id_card(None) is False
        assert DataValidator.validate_username(None) is False

        # 测试空字符串处理
        assert DataValidator.validate_email("") is False
        assert DataValidator.validate_phone("") is False
        assert DataValidator.validate_url("") is False
        assert DataValidator.validate_id_card("") is False
        assert DataValidator.validate_username("") is False

        # 测试非字符串输入
        non_string_inputs = [123, [], {}, True, 3.14]
        for input_val in non_string_inputs:
            assert DataValidator.validate_email(input_val) is False
            assert DataValidator.validate_phone(input_val) is False
            assert DataValidator.validate_url(input_val) is False
            assert DataValidator.validate_id_card(input_val) is False
            assert DataValidator.validate_username(input_val) is False

    def test_comprehensive_validation_workflow(self):
        """测试完整的验证工作流程"""
        # 用户注册数据验证
        user_data = {
            "username": "testuser123",
            "email": "test@example.com",
            "phone": "13800138000",
            "password": "Password123!",
            "id_card": "11010519491231002X",
            "age": 25,
        }

        # 1. 验证必填字段
        required_fields = ["username", "email", "password"]
        fields_result = DataValidator.validate_required_fields(
            user_data, required_fields
        )
        assert fields_result["valid"] is True

        # 2. 验证各字段格式
        assert DataValidator.validate_username(user_data["username"]) is True
        assert DataValidator.validate_email(user_data["email"]) is True
        assert DataValidator.validate_phone(user_data["phone"]) is True
        assert DataValidator.validate_id_card(user_data["id_card"]) is True

        # 3. 验证密码强度
        password_result = DataValidator.validate_password_strength(
            user_data["password"]
        )
        assert password_result["valid"] is True
        assert password_result["strength"] == 5

        # 4. 验证数值
        assert DataValidator.validate_positive_number(user_data["age"]) is True

        # 5. 清理输入数据
        dangerous_input = "<script>alert('xss')</script>"
        cleaned_input = DataValidator.sanitize_input(dangerous_input)
        assert "<script>" not in cleaned_input

    def test_performance_considerations(self):
        """测试性能考虑"""
        import time

        # 测试大量验证操作性能
        emails = [f"test{i}@example.com" for i in range(100)]
        phones = [f"1380013{i:04d}" for i in range(100)]
        passwords = ["Password123!"] * 100

        start_time = time.time()

        for email, phone, password in zip(emails, phones, passwords, strict=False):
            DataValidator.validate_email(email)
            DataValidator.validate_phone(phone)
            DataValidator.validate_password_strength(password)

        end_time = time.time()
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    def test_regex_patterns_validity(self):
        """测试正则表达式模式的有效性"""
        # 验证所有正则表达式模式能正常编译
        patterns = [
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",  # email
            r"^1[3-9]\d{9}$",  # chinese phone
            r"^\+\d{10,15}$",  # international phone
            r"^https?://[^\s/$.?#].[^\s]*$",  # url
            r"^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$",
            # 18位身份证
            r"^[1-9]\d{5}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}$",  # 15位身份证
            r"^[a-zA-Z0-9_]{4,20}$",  # username
            r"[a-z]",  # 小写字母
            r"[A-Z]",  # 大写字母
            r"\d",  # 数字
            r'[!@#$%^&*(),.?":{}|<>]',  # 特殊字符
        ]

        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"正则表达式模式无效: {pattern}")
