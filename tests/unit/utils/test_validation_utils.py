"""
验证工具测试
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch
import re


class TestValidationUtils:
    """测试验证工具"""

    def test_string_validation(self):
        """测试字符串验证"""

        # 非空字符串验证
        def validate_non_empty(value):
            if not isinstance(value, str):
                return False, "必须是字符串"
            if not value.strip():
                return False, "不能为空"
            return True, None

        # 有效字符串
        assert validate_non_empty("hello") == (True, None)
        assert validate_non_empty("  test  ") == (True, None)

        # 无效字符串
        assert validate_non_empty("") == (False, "不能为空")
        assert validate_non_empty("   ") == (False, "不能为空")
        assert validate_non_empty(None) == (False, "必须是字符串")
        assert validate_non_empty(123) == (False, "必须是字符串")

    def test_email_validation(self):
        """测试邮箱验证"""

        def is_valid_email(email):
            if not email:
                return False
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            return re.match(pattern, email) is not None

        # 有效邮箱
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("user.name+tag@domain.co.uk") is True
        assert is_valid_email("user123@test-domain.com") is True

        # 无效邮箱
        assert is_valid_email("invalid-email") is False
        assert is_valid_email("@domain.com") is False
        assert is_valid_email("user@") is False
        assert is_valid_email("") is False
        assert is_valid_email(None) is False

    def test_phone_validation(self):
        """测试手机号验证"""

        def is_valid_phone(phone, country="CN"):
            if not phone:
                return False

            # 清理输入
            phone = re.sub(r"[^\d+]", "", phone)

            if country == "CN":
                # 中国手机号
                pattern = r"^(\+86)?1[3-9]\d{9}$"
                return re.match(pattern, phone) is not None
            elif country == "US":
                # 美国手机号
                pattern = r"^(\+1)?\d{10}$"
                return re.match(pattern, phone) is not None
            else:
                # 通用验证
                return len(phone) >= 7 and len(phone) <= 15

        # 中国手机号
        assert is_valid_phone("13812345678", "CN") is True
        assert is_valid_phone("+8613812345678", "CN") is True
        assert is_valid_phone("12345678901", "CN") is False

        # 美国手机号
        assert is_valid_phone("4155552671", "US") is True
        assert is_valid_phone("+14155552671", "US") is True
        assert is_valid_phone("123", "US") is False

    def test_url_validation(self):
        """测试URL验证"""

        def is_valid_url(url):
            if not url:
                return False
            pattern = r"^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
            return re.match(pattern, url) is not None

        # 有效URL
        assert is_valid_url("http://example.com") is True
        assert is_valid_url("https://www.example.com/path") is True
        assert is_valid_url("https://localhost:8080") is True
        assert is_valid_url("https://example.com/path/to/resource?query=1") is True

        # 无效URL
        assert is_valid_url("example.com") is False
        assert is_valid_url("ftp://example.com") is False
        assert is_valid_url("http://") is False
        assert is_valid_url("") is False

    def test_numeric_validation(self):
        """测试数字验证"""

        def validate_number(value, min_val=None, max_val=None):
            try:
                num = float(value)
                if min_val is not None and num < min_val:
                    return False, f"不能小于{min_val}"
                if max_val is not None and num > max_val:
                    return False, f"不能大于{max_val}"
                return True, None
            except (ValueError, TypeError):
                return False, "必须是数字"

        # 有效数字
        assert validate_number(100) == (True, None)
        assert validate_number("100") == (True, None)
        assert validate_number(3.14) == (True, None)
        assert validate_number("3.14") == (True, None)

        # 带范围的验证
        assert validate_number(50, min_val=0, max_val=100) == (True, None)
        assert validate_number(-1, min_val=0) == (False, "不能小于0")
        assert validate_number(101, max_val=100) == (False, "不能大于100")

        # 无效数字
        assert validate_number("abc") == (False, "必须是数字")
        assert validate_number(None) == (False, "必须是数字")
        assert validate_number("") == (False, "必须是数字")

    def test_date_validation(self):
        """测试日期验证"""

        def validate_date(value, format="%Y-%m-%d"):
            if isinstance(value, (datetime, date)):
                return True, None
            if not isinstance(value, str):
                return False, "必须是日期或字符串"
            try:
                datetime.strptime(value, format)
                return True, None
            except ValueError:
                return False, f"日期格式错误，应为{format}"

        # 有效日期
        assert validate_date(date.today()) == (True, None)
        assert validate_date(datetime.now()) == (True, None)
        assert validate_date("2022-01-01") == (True, None)

        # 无效日期
        assert validate_date("2022-13-01") == (False, "日期格式错误，应为%Y-%m-%d")
        assert validate_date("2022-01-32") == (False, "日期格式错误，应为%Y-%m-%d")
        assert validate_date("01/01/2022") == (False, "日期格式错误，应为%Y-%m-%d")
        assert validate_date(123) == (False, "必须是日期或字符串")

    def test_range_validation(self):
        """测试范围验证"""

        def validate_range(value, min_val, max_val):
            return min_val <= value <= max_val

        # 有效范围
        assert validate_range(50, 0, 100) is True
        assert validate_range(0, 0, 100) is True
        assert validate_range(100, 0, 100) is True

        # 无效范围
        assert validate_range(-1, 0, 100) is False
        assert validate_range(101, 0, 100) is False

    def test_length_validation(self):
        """测试长度验证"""

        def validate_length(value, min_len=None, max_len=None):
            if not hasattr(value, "__len__"):
                return False, "必须有长度属性"
            length = len(value)
            if min_len is not None and length < min_len:
                return False, f"长度不能小于{min_len}"
            if max_len is not None and length > max_len:
                return False, f"长度不能大于{max_len}"
            return True, None

        # 字符串长度
        assert validate_length("hello", min_len=3, max_len=10) == (True, None)
        assert validate_length("hi", min_len=3) == (False, "长度不能小于3")
        assert validate_length("very long string", max_len=10) == (
            False,
            "长度不能大于10",
        )

        # 列表长度
        assert validate_length([1, 2, 3], min_len=1, max_len=5) == (True, None)
        assert validate_length([], min_len=1) == (False, "长度不能小于1")

    def test_regex_validation(self):
        """测试正则表达式验证"""

        def validate_regex(value, pattern):
            if not isinstance(value, str):
                return False
            return re.match(pattern, value) is not None

        # 用户名验证（字母数字下划线，3-20字符）
        username_pattern = r"^\w{3,20}$"
        assert validate_regex("user123", username_pattern) is True
        assert validate_regex("user_name", username_pattern) is True
        assert validate_regex("us", username_pattern) is False  # 太短
        assert validate_regex("user@name", username_pattern) is False  # 非法字符

        # 密码验证（至少8位，包含大小写字母和数字）
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$"
        assert validate_regex("Password123", password_pattern) is True
        assert validate_regex("password123", password_pattern) is False  # 没有大写
        assert validate_regex("PASSWORD123", password_pattern) is False  # 没有小写
        assert validate_regex("Password", password_pattern) is False  # 没有数字

    def test_required_fields_validation(self):
        """测试必填字段验证"""

        def validate_required(data, required_fields):
            missing = []
            for field in required_fields:
                if field not in data or _data[field] is None or _data[field] == "":
                    missing.append(field)
            return missing

        _data = {"name": "John", "email": "john@example.com", "age": 30, "phone": ""}

        # 验证必填字段
        missing = validate_required(data, ["name", "email"])
        assert missing == []

        missing = validate_required(data, ["name", "email", "password"])
        assert missing == ["password"]

        missing = validate_required(data, ["name", "phone"])
        assert missing == ["phone"]  # 空字符串视为缺失

    def test_type_validation(self):
        """测试类型验证"""

        def validate_type(value, expected_type):
            return isinstance(value, expected_type)

        # 基本类型
        assert validate_type("hello", str) is True
        assert validate_type(123, int) is True
        assert validate_type(3.14, float) is True
        assert validate_type(True, bool) is True
        assert validate_type([1, 2, 3], list) is True
        assert validate_type({"key": "value"}, dict) is True

        # 类型不匹配
        assert validate_type("123", int) is False
        assert validate_type(123, str) is False
        assert validate_type(None, str) is False

    def test_custom_validator(self):
        """测试自定义验证器"""

        def validate_even_number(value):
            """验证偶数"""
            try:
                num = int(value)
                if num % 2 == 0:
                    return True, None
                else:
                    return False, "必须是偶数"
            except (ValueError, TypeError):
                return False, "必须是整数"

        def validate_business_id(value):
            """验证营业执照号（15位数字）"""
            if not isinstance(value, str):
                return False, "必须是字符串"
            if len(value) != 15 or not value.isdigit():
                return False, "必须是15位数字"
            return True, None

        # 测试偶数验证
        assert validate_even_number(2) == (True, None)
        assert validate_even_number(4) == (True, None)
        assert validate_even_number(3) == (False, "必须是偶数")
        assert validate_even_number("abc") == (False, "必须是整数")

        # 测试营业执照验证
        assert validate_business_id("123456789012345") == (True, None)
        assert validate_business_id("12345678901234") == (False, "必须是15位数字")
        assert validate_business_id("12345678901234a") == (False, "必须是15位数字")

    def test_validation_chain(self):
        """测试验证链"""

        class ValidationChain:
            def __init__(self):
                self.validators = []

            def add_validator(self, validator_func, error_msg=None):
                self.validators.append((validator_func, error_msg))
                return self

            def validate(self, value):
                errors = []
                for validator_func, error_msg in self.validators:
                    try:
                        _result = validator_func(value)
                        if isinstance(result, tuple):
                            is_valid, msg = result
                            if not is_valid:
                                errors.append(msg or error_msg or "验证失败")
                        elif not result:
                            errors.append(error_msg or "验证失败")
                    except Exception:
                        errors.append(error_msg or "验证出错")
                return len(errors) == 0, errors

        # 创建验证链
        chain = ValidationChain()
        chain.add_validator(lambda x: isinstance(x, str), "必须是字符串")
        chain.add_validator(lambda x: len(x) >= 3, "长度至少3位")
        chain.add_validator(lambda x: len(x) <= 20, "长度不超过20位")
        chain.add_validator(lambda x: x.isalnum(), "只能包含字母数字")

        # 测试
        is_valid, errors = chain.validate("user123")
        assert is_valid is True
        assert errors == []

        is_valid, errors = chain.validate("us")
        # 太短
        assert is_valid is False
        assert "长度至少3位" in errors

        is_valid, errors = chain.validate("user@123")  # 非法字符
        assert is_valid is False
        assert "只能包含字母数字" in errors

    def test_conditional_validation(self):
        """测试条件验证"""

        def validate_conditional(
            data, condition_field, condition_value, field_to_validate, validator
        ):
            """条件验证：当某个字段满足条件时，验证另一个字段"""
            if condition_field not in data:
                return True, None  # 条件字段不存在，跳过验证

            if _data[condition_field] == condition_value:
                return validator(data.get(field_to_validate))
            else:
                return True, None  # 条件不满足，跳过验证

        _data = {
            "user_type": "premium",
            "payment_method": "credit_card",
            "card_number": "4111111111111111",
        }

        # 当用户类型是premium时，必须有支付方式
        def has_payment_method(value):
            return value is not None and value != "", "高级用户必须设置支付方式"

        is_valid, msg = validate_conditional(
            data, "user_type", "premium", "payment_method", has_payment_method
        )
        assert is_valid is True

        # 当支付方式是信用卡时，必须提供卡号
        def has_valid_card_number(value):
            if not value:
                return False, "信用卡支付必须提供卡号"
            if not value.isdigit() or len(value) != 16:
                return False, "卡号必须是16位数字"
            return True, None

        is_valid, msg = validate_conditional(
            data, "payment_method", "credit_card", "card_number", has_valid_card_number
        )
        assert is_valid is True

        # 测试无效情况
        _data["card_number"] = "1234"
        is_valid, msg = validate_conditional(
            data, "payment_method", "credit_card", "card_number", has_valid_card_number
        )
        assert is_valid is False
        assert "卡号必须是16位数字" in msg

    def test_bulk_validation(self):
        """测试批量验证"""

        def validate_bulk(data, validators):
            """批量验证多个字段"""
            results = {}
            all_valid = True

            for field, validator in validators.items():
                if field in data:
                    is_valid, error = validator(_data[field])
                    results[field] = {"valid": is_valid, "error": error}
                    if not is_valid:
                        all_valid = False
                else:
                    results[field] = {"valid": False, "error": "字段不存在"}
                    all_valid = False

            return all_valid, results

        # 定义验证器
        validators = {
            "name": lambda x: (isinstance(x, str) and len(x) > 0, "姓名不能为空"),
            "age": lambda x: (
                isinstance(x, int) and 0 < x < 150,
                "年龄必须在1-149之间",
            ),
            "email": lambda x: (isinstance(x, str) and "@" in x, "邮箱格式无效"),
        }

        # 测试数据
        _data = {"name": "John", "age": 30, "email": "john@example.com"}

        is_valid, results = validate_bulk(data, validators)
        assert is_valid is True
        assert all(r["valid"] for r in results.values())

        # 测试无效数据
        invalid_data = {"name": "", "age": 200, "email": "invalid-email"}

        is_valid, results = validate_bulk(invalid_data, validators)
        assert is_valid is False
        assert results["name"]["valid"] is False
        assert results["age"]["valid"] is False
        assert results["email"]["valid"] is False

    def test_async_validation_simulation(self):
        """测试异步验证模拟"""
        import asyncio

        async def async_validate_email(email):
            """模拟异步邮箱验证（检查域名MX记录）"""
            await asyncio.sleep(0.01)  # 模拟网络延迟
            if not email or "@" not in email:
                return False, "邮箱格式无效"
            domain = email.split("@")[1]
            # 模拟域名检查
            if domain == "invalid.com":
                return False, "域名不存在"
            return True, None

        async def validate_user_data(data):
            """异步验证用户数据"""
            tasks = []

            # 并行验证多个字段
            if "email" in data:
                tasks.append(async_validate_email(_data["email"]))

            # 可以添加更多异步验证任务
            # tasks.append(async_validate_phone(_data["phone"]))
            # tasks.append(async_check_username(_data["username"]))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_valid = True
            errors = []

            for result in results:
                if isinstance(result, Exception):
                    all_valid = False
                    errors.append(f"验证出错: {str(result)}")
                else:
                    is_valid, error = result
                    if not is_valid:
                        all_valid = False
                        errors.append(error)

            return all_valid, errors

        # 测试异步验证
        async def test_async():
            # 有效数据
            _data = {"email": "test@example.com"}
            is_valid, errors = await validate_user_data(data)
            assert is_valid is True
            assert len(errors) == 0

            # 无效数据
            invalid_data = {"email": "test@invalid.com"}
            is_valid, errors = await validate_user_data(invalid_data)
            assert is_valid is False
            assert "域名不存在" in errors

        # 运行异步测试
        asyncio.run(test_async())
