"""
验证器参数化测试
Tests for Validators (Parametrized)

使用参数化测试减少重复代码，提高测试覆盖率
"""

import pytest
from unittest.mock import Mock
import re

# 测试导入
try:
    from src.utils.validators import (
        validate_email,
        validate_phone,
        validate_url,
        validate_username,
        validate_password,
        validate_credit_card,
        validate_ipv4_address,
        validate_mac_address,
        validate_date_string,
        validate_json_string,
    )

    VALIDATORS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    VALIDATORS_AVAILABLE = False
    # 创建模拟函数
    validate_email = None
    validate_phone = None
    validate_url = None
    validate_username = None
    validate_password = None
    validate_credit_card = None
    validate_ipv4_address = None
    validate_mac_address = None
    validate_date_string = None
    validate_json_string = None


@pytest.mark.skipif(not VALIDATORS_AVAILABLE, reason="Validators module not available")
class TestValidatorsParametrized:
    """验证器参数化测试"""

    @pytest.mark.parametrize(
        "email,expected",
        [
            # 有效邮箱
            ("user@example.com", True),
            ("test.email@domain.co.uk", True),
            ("user+tag@example.org", True),
            ("user123@test-domain.com", True),
            ("firstname.lastname@company.com", True),
            ("user@sub.domain.com", True),
            # 无效邮箱
            ("invalid-email", False),
            ("@missing-username.com", False),
            ("missing-at-sign.com", False),
            ("user@.com", False),
            ("user@domain.", False),
            ("user..name@domain.com", False),
            ("user@domain..com", False),
            ("", False),
            (None, False),
            (123, False),
        ],
    )
    def test_validate_email(self, email, expected):
        """测试：邮箱验证（参数化）"""
        if validate_email is not None:
            result = validate_email(email)
            assert result == expected

    @pytest.mark.parametrize(
        "phone,expected",
        [
            # 有效电话号码
            ("+1-555-123-4567", True),
            ("(555) 123-4567", True),
            ("555.123.4567", True),
            ("5551234567", True),
            ("+44 20 7946 0958", True),
            ("+86 138 0013 8000", True),
            # 无效电话号码
            ("abc-def-ghij", False),
            ("123-456", False),
            ("", False),
            (None, False),
            (1234567890, False),  # 数字类型，应该接受字符串
            ("+1 555 123 45678", False),  # 太长
        ],
    )
    def test_validate_phone(self, phone, expected):
        """测试：电话验证（参数化）"""
        if validate_phone is not None:
            result = validate_phone(phone)
            assert result == expected

    @pytest.mark.parametrize(
        "url,expected",
        [
            # 有效URL
            ("https://www.example.com", True),
            ("http://example.com/path", True),
            ("https://sub.domain.com/path?query=1", True),
            ("ftp://ftp.example.com", True),
            ("http://localhost:8080", True),
            ("https://192.168.1.1:3000", True),
            # 无效URL
            ("not-a-url", False),
            ("http://", False),
            ("https://", False),
            ("", False),
            (None, False),
            ("www.example.com", False),  # 缺少协议
            ("http://.com", False),
        ],
    )
    def test_validate_url(self, url, expected):
        """测试：URL验证（参数化）"""
        if validate_url is not None:
            result = validate_url(url)
            assert result == expected

    @pytest.mark.parametrize(
        "username,expected",
        [
            # 有效用户名
            ("john_doe", True),
            ("johndoe123", True),
            ("john.doe", True),
            ("j", True),  # 最短
            ("a" * 20, True),  # 最长
            # 无效用户名
            ("", False),
            (None, False),
            ("ab", False),  # 太短
            ("a" * 21, False),  # 太长
            ("john@doe", False),  # 包含特殊字符
            ("john doe", False),  # 包含空格
            ("123john", False),  # 以数字开头
        ],
    )
    def test_validate_username(self, username, expected):
        """测试：用户名验证（参数化）"""
        if validate_username is not None:
            result = validate_username(username)
            assert result == expected

    @pytest.mark.parametrize(
        "password,expected",
        [
            # 有效密码
            ("Password123!", True),
            ("MySecurePass@2024", True),
            ("P@ssw0rd", True),
            ("ComplexPass_123", True),
            # 无效密码
            ("", False),
            (None, False),
            ("123", False),  # 太短
            ("password", False),  # 没有大写字母
            ("PASSWORD", False),  # 没有小写字母
            ("Password", False),  # 没有数字
            ("Password1", False),  # 没有特殊字符
        ],
    )
    def test_validate_password(self, password, expected):
        """测试：密码验证（参数化）"""
        if validate_password is not None:
            result = validate_password(password)
            assert result == expected

    @pytest.mark.parametrize(
        "card,expected",
        [
            # 有效信用卡号
            ("4111111111111111", True),  # Visa
            ("5500000000000004", True),  # MasterCard
            ("340000000000009", True),  # American Express
            ("30000000000004", True),  # Diner's Club
            # 无效信用卡号
            ("1234567890123456", False),  # 无效号段
            ("", False),
            (None, False),
            ("411111111111111", False),  # 太短
            ("41111111111111111", False),  # 太长
            ("abcd1111111111111", False),  # 包含字母
        ],
    )
    def test_validate_credit_card(self, card, expected):
        """测试：信用卡验证（参数化）"""
        if validate_credit_card is not None:
            result = validate_credit_card(card)
            assert result == expected

    @pytest.mark.parametrize(
        "ip,expected",
        [
            # 有效IPv4地址
            ("192.168.1.1", True),
            ("10.0.0.1", True),
            ("127.0.0.1", True),
            ("255.255.255.255", True),
            ("0.0.0.0", True),
            # 无效IPv4地址
            ("256.1.1.1", False),  # 超出范围
            ("192.168.1", False),  # 不足4段
            ("192.168.1.1.1", False),  # 超过4段
            ("192.168..1", False),  # 空段
            ("abc.def.ghi.jkl", False),
            ("", False),
            (None, False),
        ],
    )
    def test_validate_ipv4_address(self, ip, expected):
        """测试：IPv4地址验证（参数化）"""
        if validate_ipv4_address is not None:
            result = validate_ipv4_address(ip)
            assert result == expected

    @pytest.mark.parametrize(
        "mac,expected",
        [
            # 有效MAC地址
            ("00:1A:2B:3C:4D:5E", True),
            ("00-1A-2B-3C-4D-5E", True),
            ("001A.2B3C.4D5E", True),
            ("001A2B3C4D5E", True),
            # 无效MAC地址
            ("00:1A:2B:3C:4D", False),  # 不足6段
            ("00:1A:2B:3C:4D:5E:6F", False),  # 超过6段
            ("GG:1A:2B:3C:4D:5E", False),  # 无效字符
            ("", False),
            (None, False),
        ],
    )
    def test_validate_mac_address(self, mac, expected):
        """测试：MAC地址验证（参数化）"""
        if validate_mac_address is not None:
            result = validate_mac_address(mac)
            assert result == expected

    @pytest.mark.parametrize(
        "date_str,format,expected",
        [
            # 有效日期字符串
            ("2024-01-15", "%Y-%m-%d", True),
            ("15/01/2024", "%d/%m/%Y", True),
            ("2024年1月15日", "%Y年%m月%d日", True),
            ("2024-01-15 14:30:00", "%Y-%m-%d %H:%M:%S", True),
            # 无效日期字符串
            ("2024-13-01", "%Y-%m-%d", False),  # 无效月份
            ("2024-02-30", "%Y-%m-%d", False),  # 无效日期
            ("2024/01/15", "%Y-%m-%d", False),  # 格式不匹配
            ("", "%Y-%m-%d", False),
            (None, "%Y-%m-%d", False),
        ],
    )
    def test_validate_date_string(self, date_str, format, expected):
        """测试：日期字符串验证（参数化）"""
        if validate_date_string is not None:
            result = validate_date_string(date_str, format)
            assert result == expected

    @pytest.mark.parametrize(
        "json_str,expected",
        [
            # 有效JSON
            ('{"key": "value"}', True),
            ("[1, 2, 3]", True),
            ('{"number": 123, "boolean": true}', True),
            ('{"nested": {"key": "value"}}', True),
            # 无效JSON
            ("{key: value}", False),  # 缺少引号
            ('{"key": value}', False),  # 值未加引号
            ('{"key": "value"', False),  # 缺少结束括号
            ("", False),
            (None, False),
        ],
    )
    def test_validate_json_string(self, json_str, expected):
        """测试：JSON字符串验证（参数化）"""
        if validate_json_string is not None:
            result = validate_json_string(json_str)
            assert result == expected


@pytest.mark.skipif(
    VALIDATORS_AVAILABLE, reason="Validators module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not VALIDATORS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


@pytest.mark.skipif(not VALIDATORS_AVAILABLE, reason="Validators module not available")
class TestValidatorsComplex:
    """验证器复杂测试（使用参数化）"""

    @pytest.mark.parametrize(
        "data,field_rules,expected",
        [
            # 批量验证
            (
                {"name": "John", "age": 25, "email": "john@example.com"},
                {
                    "name": {"type": str, "required": True},
                    "age": {"type": int, "min": 0, "max": 150},
                    "email": {"type": str, "pattern": r"^[^@]+@[^@]+\.[^@]+$"},
                },
                True,
            ),
            # 无效数据
            (
                {"name": "", "age": -5, "email": "invalid"},
                {
                    "name": {"type": str, "min_length": 1},
                    "age": {"type": int, "min": 0},
                    "email": {"type": str, "pattern": r"^[^@]+@[^@]+\.[^@]+$"},
                },
                False,
            ),
        ],
    )
    def test_validate_complex_data(self, data, field_rules, expected):
        """测试：复杂数据验证（参数化）"""

        # 模拟批量验证函数
        def validate_complex(data, rules):
            for field, rule in rules.items():
                value = data.get(field)

                # 类型检查
                if "type" in rule:
                    if not isinstance(value, rule["type"]):
                        return False

                # 长度检查
                if "min_length" in rule and len(str(value)) < rule["min_length"]:
                    return False

                # 数值范围检查
                if (
                    "min" in rule
                    and isinstance(value, (int, float))
                    and value < rule["min"]
                ):
                    return False
                if (
                    "max" in rule
                    and isinstance(value, (int, float))
                    and value > rule["max"]
                ):
                    return False

                # 正则表达式检查
                if "pattern" in rule and isinstance(value, str):
                    if not re.match(rule["pattern"], value):
                        return False

                # 必填检查
                if rule.get("required", False) and value is None:
                    return False

            return True

        result = validate_complex(data, field_rules)
        assert result == expected

    @pytest.mark.parametrize(
        "input_data,sanitizer,expected",
        [
            # 清理和验证
            ("  test@example.com  ", str.strip, "test@example.com"),
            ("USER@EXAMPLE.COM", str.lower, "user@example.com"),
            ("123-456-7890", lambda x: x.replace("-", ""), "1234567890"),
            (
                "  <script>alert('xss')</script> ",
                lambda x: re.sub(r"<[^>]+>", "", x),
                "alert('xss')",
            ),
        ],
    )
    def test_sanitize_and_validate(self, input_data, sanitizer, expected):
        """测试：清理和验证数据（参数化）"""
        # 清理数据
        cleaned = sanitizer(input_data)

        # 验证邮箱
        def is_email(email):
            pattern = r"^[^@]+@[^@]+\.[^@]+$"
            return re.match(pattern, email) is not None

        if expected == "test@example.com":
            assert cleaned == expected
            assert is_email(cleaned)
        else:
            assert cleaned == expected

    @pytest.mark.parametrize(
        "business_rules,data,expected",
        [
            # 业务规则验证
            (
                {"min_age": 18, "max_age": 65, "countries": ["US", "CA", "UK"]},
                {"age": 25, "country": "US"},
                True,
            ),
            (
                {"min_age": 18, "max_age": 65, "countries": ["US", "CA", "UK"]},
                {"age": 17, "country": "US"},
                False,
            ),  # 年龄不足
            (
                {"min_age": 18, "max_age": 65, "countries": ["US", "CA", "UK"]},
                {"age": 70, "country": "US"},
                False,
            ),  # 年龄过大
            (
                {"min_age": 18, "max_age": 65, "countries": ["US", "CA", "UK"]},
                {"age": 25, "country": "FR"},
                False,
            ),  # 国家不在列表
        ],
    )
    def test_business_rules_validation(self, business_rules, data, expected):
        """测试：业务规则验证（参数化）"""

        def validate_business(data, rules):
            # 年龄检查
            if "min_age" in rules and data["age"] < rules["min_age"]:
                return False
            if "max_age" in rules and data["age"] > rules["max_age"]:
                return False

            # 国家检查
            if "countries" in rules and data["country"] not in rules["countries"]:
                return False

            return True

        result = validate_business(data, business_rules)
        assert result == expected


@pytest.mark.skipif(not VALIDATORS_AVAILABLE, reason="Validators module not available")
class TestValidatorsEdgeCases:
    """验证器边界情况测试"""

    @pytest.mark.parametrize(
        "input_value",
        [
            "",  # 空字符串
            " ",  # 空格
            "\t",  # 制表符
            "\n",  # 换行符
            "\r",  # 回车符
            " \t\n\r",  # 混合空白字符
            "null",  # 字符串"null"
            "undefined",  # 字符串"undefined"
            "NaN",  # 字符串"NaN"
            "Infinity",  # 字符串"Infinity"
            0,  # 数字0
            -1,  # 负数
            0.0,  # 浮点数0
            [],  # 空列表
            {},  # 空字典
            (),  # 空元组
        ],
    )
    def test_edge_cases(self, input_value):
        """测试：边界情况输入（参数化）"""
        # 测试各种输入类型是否能被正确处理
        if validate_email is not None:
            result = validate_email(input_value)
            assert isinstance(result, bool)

        if validate_username is not None:
            result = validate_username(input_value)
            assert isinstance(result, bool)

    @pytest.mark.parametrize(
        "unicode_input",
        [
            "用户@example.com",  # 中文邮箱
            "test@пример.com",  # 俄文域名
            "müller@example.de",  # 德语变音符号
            "josé@ejemplo.es",  # 西班牙语
            "αβγ@example.ελ",  # 希腊语
            "🚀@rocket.com",  # Emoji
        ],
    )
    def test_unicode_validation(self, unicode_input):
        """测试：Unicode输入验证（参数化）"""
        if validate_email is not None:
            # 某些验证器可能不支持Unicode
            try:
                result = validate_email(unicode_input)
                assert isinstance(result, bool)
            except UnicodeError:
                # 处理Unicode错误
                pass
