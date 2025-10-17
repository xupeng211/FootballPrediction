"""
验证器参数化测试（简化版）
Tests for Validators (Parametrized - Simple)
"""

import pytest
from src.utils.validators import (
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    is_valid_username,
    is_valid_password,
    is_valid_credit_card,
    is_valid_ipv4_address,
    is_valid_mac_address,
    is_valid_date_string,
    is_valid_json_string,
)


@pytest.mark.unit
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
    def test_is_valid_email(self, email, expected):
        """测试：邮箱验证（参数化）"""
        result = is_valid_email(email)
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
    def test_is_valid_phone(self, phone, expected):
        """测试：电话验证（参数化）"""
        result = is_valid_phone(phone)
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
    def test_is_valid_username(self, username, expected):
        """测试：用户名验证（参数化）"""
        result = is_valid_username(username)
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
    def test_is_valid_password(self, password, expected):
        """测试：密码验证（参数化）"""
        result = is_valid_password(password)
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
    def test_is_valid_ipv4_address(self, ip, expected):
        """测试：IPv4地址验证（参数化）"""
        result = is_valid_ipv4_address(ip)
        assert result == expected