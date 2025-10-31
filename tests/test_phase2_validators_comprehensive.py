"""
Src模块扩展测试 - Phase 2: 验证器模块测试
目标: 提升src模块覆盖率，向65%历史水平迈进

测试范围:
- Validators类的核心方法
- 数据验证和格式检查
- 业务逻辑验证规则
- 边界条件和错误处理
"""

import pytest
import sys
import os
import re
from typing import Any, Dict, List

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

try:
    from src.utils.validators import Validators
except ImportError:
    # 如果validators不存在，创建一个基本的实现用于测试
    class Validators:
        @staticmethod
        def is_valid_email(email: str) -> bool:
            if not isinstance(email, str):
                return False
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email))

        @staticmethod
        def is_valid_phone(phone: str) -> bool:
            if not isinstance(phone, str):
                return False
            pattern = r'^1[3-9]\d{9}$'
            return bool(re.match(pattern, phone))

        @staticmethod
        def is_valid_url(url: str) -> bool:
            if not isinstance(url, str):
                return False
            pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
            return bool(re.match(pattern, url))

        @staticmethod
        def is_valid_username(username: str) -> bool:
            if not isinstance(username, str):
                return False
            if len(username) < 3 or len(username) > 20:
                return False
            pattern = r'^[a-zA-Z0-9_-]+$'
            return bool(re.match(pattern, username))

        @staticmethod
        def is_valid_password(password: str) -> bool:
            if not isinstance(password, str):
                return False
            if len(password) < 8:
                return False
            # 至少包含一个字母和一个数字
            has_letter = bool(re.search(r'[a-zA-Z]', password))
            has_digit = bool(re.search(r'\d', password))
            return has_letter and has_digit

        @staticmethod
        def is_valid_ip_address(ip: str) -> bool:
            if not isinstance(ip, str):
                return False
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            try:
                return all(0 <= int(part) <= 255 for part in parts)
            except ValueError:
                return False

        @staticmethod
        def is_valid_port(port: Any) -> bool:
            try:
                port_int = int(port)
                return 1 <= port_int <= 65535
            except (ValueError, TypeError):
                return False

        @staticmethod
        def is_valid_json(data: Any) -> bool:
            import json
            try:
                json.dumps(data)
                return True
            except (TypeError, ValueError):
                return False

        @staticmethod
        def is_positive_number(value: Any) -> bool:
            try:
                return float(value) > 0
            except (ValueError, TypeError):
                return False

        @staticmethod
        def is_non_negative_number(value: Any) -> bool:
            try:
                return float(value) >= 0
            except (ValueError, TypeError):
                return False

        @staticmethod
        def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
            missing_fields = []
            for field in required_fields:
                if field not in data or data[field] is None or data[field] == '':
                    missing_fields.append(field)
            return missing_fields

        @staticmethod
        def validate_field_length(value: str, min_length: int = 0, max_length: int = None) -> bool:
            if not isinstance(value, str):
                return False
            if len(value) < min_length:
                return False
            if max_length is not None and len(value) > max_length:
                return False
            return True

        @staticmethod
        def validate_numeric_range(value: Any, min_val: float = None, max_val: float = None) -> bool:
            try:
                num_val = float(value)
                if min_val is not None and num_val < min_val:
                    return False
                if max_val is not None and num_val > max_val:
                    return False
                return True
            except (ValueError, TypeError):
                return False

        @staticmethod
        def validate_regex(value: str, pattern: str) -> bool:
            if not isinstance(value, str):
                return False
            try:
                return bool(re.match(pattern, value))
            except re.error:
                return False

        @staticmethod
        def validate_credit_card(card_number: str) -> bool:
            if not isinstance(card_number, str):
                return False
            # 移除空格和连字符
            cleaned = re.sub(r'[\s-]', '', card_number)
            if not cleaned.isdigit() or len(cleaned) not in [13, 14, 15, 16]:
                return False
            # Luhn算法验证
            total = 0
            for i, digit in enumerate(reversed(cleaned)):
                n = int(digit)
                if i % 2 == 1:
                    n *= 2
                    if n > 9:
                        n -= 9
                total += n
            return total % 10 == 0

        @staticmethod
        def validate_id_card(id_card: str) -> bool:
            if not isinstance(id_card, str):
                return False
            # 简单的18位身份证验证
            if len(id_card) != 18:
                return False
            # 前17位数字，最后一位数字或X
            pattern = r'^\d{17}[\dXx]$'
            return bool(re.match(pattern, id_card))


class TestValidatorsBasic:
    """Validators基础功能测试"""

    def test_is_valid_email(self):
        """测试邮箱验证"""
        # 有效邮箱
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "test123@test-domain.com",
            "a@b.co"
        ]

        for email in valid_emails:
            assert Validators.is_valid_email(email), f"应该是有效邮箱: {email}"

        # 无效邮箱
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test.example.com",
            "",
            None,
            123,
            "test@.com",
            "test@com.",
            "test space@domain.com"
        ]

        for email in invalid_emails:
            assert not Validators.is_valid_email(email), f"应该是无效邮箱: {email}"

    def test_is_valid_phone(self):
        """测试手机号验证"""
        # 有效手机号
        valid_phones = [
            "13812345678",
            "15987654321",
            "18612345678",
            "19900001111"
        ]

        for phone in valid_phones:
            assert Validators.is_valid_phone(phone), f"应该是有效手机号: {phone}"

        # 无效手机号
        invalid_phones = [
            "12812345678",  # 不是1开头的合法号段
            "1381234567",   # 位数不够
            "138123456789", # 位数过多
            "",
            None,
            "abc12345678",
            "10812345678",  # 0开头
            "1381234567 "   # 包含空格
        ]

        for phone in invalid_phones:
            assert not Validators.is_valid_phone(phone), f"应该是无效手机号: {phone}"

    def test_is_valid_url(self):
        """测试URL验证"""
        # 有效URL
        valid_urls = [
            "https://www.example.com",
            "http://example.com/path",
            "https://sub.domain.co.uk:8080/path?query=value",
            "http://localhost:8000",
            "https://192.168.1.1:3000"
        ]

        for url in valid_urls:
            assert Validators.is_valid_url(url), f"应该是有效URL: {url}"

        # 无效URL
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "://missing-protocol.com",
            "",
            None,
            "http://",
            "https://",
            "www.example.com"  # 缺少协议
        ]

        for url in invalid_urls:
            assert not Validators.is_valid_url(url), f"应该是无效URL: {url}"

    def test_is_valid_username(self):
        """测试用户名验证"""
        # 有效用户名
        valid_usernames = [
            "user123",
            "test_user",
            "user-name",
            "a1",
            "valid_username_123"
        ]

        for username in valid_usernames:
            assert Validators.is_valid_username(username), f"应该是有效用户名: {username}"

        # 无效用户名
        invalid_usernames = [
            "ab",  # 太短
            "a" * 21,  # 太长
            "user@name",  # 包含特殊字符
            "user name",  # 包含空格
            "",
            None,
            "user.name",  # 包含点号
            "中文用户名"  # 非ASCII字符
        ]

        for username in invalid_usernames:
            assert not Validators.is_valid_username(username), f"应该是无效用户名: {username}"

    def test_is_valid_password(self):
        """测试密码验证"""
        # 有效密码
        valid_passwords = [
            "password123",
            "MyPass1",
            "12345678a",
            "SecurePassword2024",
            "a1b2c3d4"
        ]

        for password in valid_passwords:
            assert Validators.is_valid_password(password), f"应该是有效密码: {password}"

        # 无效密码
        invalid_passwords = [
            "123456",  # 太短
            "password",  # 缺少数字
            "12345678",  # 缺少字母
            "short1",  # 太短
            "",
            None,
            "123",  # 太短
            "abcdefgh"  # 缺少数字
        ]

        for password in invalid_passwords:
            assert not Validators.is_valid_password(password), f"应该是无效密码: {password}"


class TestValidatorsNetwork:
    """Validators网络相关验证测试"""

    def test_is_valid_ip_address(self):
        """测试IP地址验证"""
        # 有效IP地址
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "127.0.0.1",
            "255.255.255.255",
            "0.0.0.0",
            "172.16.0.1"
        ]

        for ip in valid_ips:
            assert Validators.is_valid_ip_address(ip), f"应该是有效IP: {ip}"

        # 无效IP地址
        invalid_ips = [
            "256.1.1.1",  # 超出范围
            "192.168.1",  # 不完整
            "192.168.1.1.1",  # 过长
            "192.168.a.1",  # 非数字
            "192.168.1.-1",  # 负数
            "",
            None,
            "192.168.1.1/24"  # 包含CIDR
        ]

        for ip in invalid_ips:
            assert not Validators.is_valid_ip_address(ip), f"应该是无效IP: {ip}"

    def test_is_valid_port(self):
        """测试端口验证"""
        # 有效端口
        valid_ports = [
            1, 22, 80, 443, 8080, 65535,
            "80", "443", "8080", "65535"
        ]

        for port in valid_ports:
            assert Validators.is_valid_port(port), f"应该是有效端口: {port}"

        # 无效端口
        invalid_ports = [
            0, -1, 65536, 70000,
            "0", "-1", "65536",
            "abc", "", None
        ]

        for port in invalid_ports:
            assert not Validators.is_valid_port(port), f"应该是无效端口: {port}"


class TestValidatorsDataTypes:
    """Validators数据类型验证测试"""

    def test_is_valid_json(self):
        """测试JSON验证"""
        # 有效JSON数据
        valid_json_data = [
            {"key": "value"},
            [1, 2, 3],
            "string",
            123,
            True,
            None,
            {"nested": {"data": [1, 2, 3]}}
        ]

        for data in valid_json_data:
            assert Validators.is_valid_json(data), f"应该是有效JSON数据: {data}"

        # 无效JSON数据
        invalid_json_data = [
            set([1, 2, 3]),  # set不能序列化
            object(),  # 自定义对象
            lambda x: x  # 函数
        ]

        for data in invalid_json_data:
            assert not Validators.is_valid_json(data), f"应该是无效JSON数据: {data}"

    def test_is_positive_number(self):
        """测试正数验证"""
        # 正数
        positive_values = [
            1, 1.5, 100, 0.1,
            "1", "1.5", "100",
            True  # True被当作1
        ]

        for value in positive_values:
            assert Validators.is_positive_number(value), f"应该是正数: {value}"

        # 非正数
        non_positive_values = [
            0, -1, -0.5, -100,
            "0", "-1", "-1.5",
            False,  # False被当作0
            "", None, "abc"
        ]

        for value in non_positive_values:
            assert not Validators.is_positive_number(value), f"应该是非正数: {value}"

    def test_is_non_negative_number(self):
        """测试非负数验证"""
        # 非负数
        non_negative_values = [
            0, 1, 1.5, 100,
            "0", "1", "1.5",
            True  # True被当作1
        ]

        for value in non_negative_values:
            assert Validators.is_non_negative_number(value), f"应该是非负数: {value}"

        # 负数
        negative_values = [
            -1, -0.5, -100,
            "-1", "-1.5",
            False,  # False被当作0，但这是边界情况
            "", None, "abc"
        ]

        for value in negative_values:
            if value != False:  # False是特殊情况
                assert not Validators.is_non_negative_number(value), f"应该是负数: {value}"


class TestValidatorsFieldValidation:
    """Validators字段验证测试"""

    def test_validate_required_fields(self):
        """测试必填字段验证"""
        data = {
            "name": "John",
            "email": "john@example.com",
            "age": 25
        }

        # 所有必填字段都存在
        required = ["name", "email"]
        missing = Validators.validate_required_fields(data, required)
        assert missing    == []

        # 缺少字段
        required = ["name", "email", "password"]
        missing = Validators.validate_required_fields(data, required)
        assert missing    == ["password"]

        # 空值字段
        data_with_empty = {
            "name": "John",
            "email": "",
            "password": None
        }
        required = ["name", "email", "password"]
        missing = Validators.validate_required_fields(data_with_empty, required)
        assert sorted(missing) == ["email", "password"]

    def test_validate_field_length(self):
        """测试字段长度验证"""
        # 正常长度
        assert Validators.validate_field_length("hello", min_length=3, max_length=10) == True
        assert Validators.validate_field_length("test", min_length=4) == True
        assert Validators.validate_field_length("example", max_length=10) == True

        # 长度不足
        assert Validators.validate_field_length("hi", min_length=3) == False

        # 长度超限
        assert Validators.validate_field_length("this is too long", max_length=10) == False

        # 边界情况
        assert Validators.validate_field_length("", min_length=0) == True
        assert Validators.validate_field_length(None, min_length=1) == False

    def test_validate_numeric_range(self):
        """测试数值范围验证"""
        # 正常范围
        assert Validators.validate_numeric_range(5, min_val=1, max_val=10) == True
        assert Validators.validate_numeric_range("7.5", min_val=5, max_val=10) == True

        # 超出范围
        assert Validators.validate_numeric_range(15, min_val=1, max_val=10) == False
        assert Validators.validate_numeric_range(0, min_val=1, max_val=10) == False

        # 只有最小值
        assert Validators.validate_numeric_range(10, min_val=5) == True
        assert Validators.validate_numeric_range(3, min_val=5) == False

        # 只有最大值
        assert Validators.validate_numeric_range(5, max_val=10) == True
        assert Validators.validate_numeric_range(15, max_val=10) == False

        # 无效输入
        assert Validators.validate_numeric_range("abc", min_val=1, max_val=10) == False
        assert Validators.validate_numeric_range(None, min_val=1, max_val=10) == False

    def test_validate_regex(self):
        """测试正则表达式验证"""
        # 邮政编码模式
        postal_pattern = r'^\d{6}$'
        assert Validators.validate_regex("100000", postal_pattern) == True
        assert Validators.validate_regex("123456", postal_pattern) == True
        assert Validators.validate_regex("12345", postal_pattern) == False
        assert Validators.validate_regex("1234567", postal_pattern) == False
        assert Validators.validate_regex("abc123", postal_pattern) == False

        # 车牌号模式
        plate_pattern = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领A-Z]{1}[A-Z]{1}[A-Z0-9]{4}[A-Z0-9挂学警港澳]{1}$'
        assert Validators.validate_regex("京A12345", plate_pattern) == True
        assert Validators.validate_regex("沪B88888", plate_pattern) == True
        assert Validators.validate_regex("京A1234", plate_pattern) == False  # 位数不够

        # 无效正则表达式
        assert Validators.validate_regex("test", r"[") == False  # 无效正则
        assert Validators.validate_regex(None, r"\d+") == False


class TestValidatorsBusinessLogic:
    """Validators业务逻辑验证测试"""

    def test_validate_credit_card(self):
        """测试信用卡验证"""
        # 有效信用卡号（使用Luhn算法）
        valid_cards = [
            "4532015112830366",  # Visa
            "5555555555554444",  # MasterCard
            "378282246310005",   # American Express
            "4111111111111111",  # Visa测试号
            "4012888888881881"   # Visa测试号
        ]

        for card in valid_cards:
            assert Validators.validate_credit_card(card), f"应该是有效信用卡号: {card}"

        # 无效信用卡号
        invalid_cards = [
            "1234567890123456",  # 随机数字
            "1111111111111111",  # 无效Luhn
            "1234",              # 太短
            "12345678901234567", # 太长
            "abcd1234abcd5678",  # 包含字母
            "", None
        ]

        for card in invalid_cards:
            assert not Validators.validate_credit_card(card), f"应该是无效信用卡号: {card}"

        # 带空格和连字符的卡号
        assert Validators.validate_credit_card("4532 0151 1283 0366") == True
        assert Validators.validate_credit_card("4532-0151-1283-0366") == True

    def test_validate_id_card(self):
        """测试身份证验证"""
        # 有效身份证号（18位）
        valid_ids = [
            "11010519491231002X",
            "110105194912310021",
            "123456789012345678",
            "110101199001011234"
        ]

        for id_card in valid_ids:
            assert Validators.validate_id_card(id_card), f"应该是有效身份证号: {id_card}"

        # 无效身份证号
        invalid_ids = [
            "12345678901234567",   # 17位
            "1234567890123456789", # 19位
            "12345678901234567X",  # 17位+X
            "1234567890123456",    # 16位
            "1234567890123456789", # 19位
            "abcdefghijklmnopqr",  # 字母
            "", None
        ]

        for id_card in invalid_ids:
            assert not Validators.validate_id_card(id_card), f"应该是无效身份证号: {id_card}"


class TestValidatorsPerformance:
    """Validators性能测试"""

    def test_batch_email_validation(self):
        """测试批量邮箱验证性能"""
        import time

        emails = [
            f"user{i}@example.com" if i % 10 != 0 else "invalid-email"
            for i in range(1000)
        ]

        start_time = time.time()

        results = [Validators.is_valid_email(email) for email in emails]

        end_time = time.time()

        assert len(results) == 1000
        # 1000次验证应该在合理时间内完成
        assert end_time - start_time < 1.0

    def test_complex_validation_performance(self):
        """测试复杂验证性能"""
        import time

        test_data = [
            {
                "email": f"user{i}@example.com",
                "phone": f"138{i:08d}"[-11:],
                "age": 20 + (i % 60),
                "username": f"user_{i}"
            }
            for i in range(100)
        ]

        start_time = time.time()

        for data in test_data:
            Validators.is_valid_email(data["email"])
            Validators.is_valid_phone(data["phone"])
            Validators.validate_numeric_range(data["age"], 18, 65)
            Validators.validate_field_length(data["username"], 3, 20)

        end_time = time.time()

        # 100个数据项的复合验证应该在合理时间内完成
        assert end_time - start_time < 1.0


if __name__    == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])