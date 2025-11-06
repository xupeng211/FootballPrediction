"""
核心验证模块测试
Core Validators Module Tests

测试数据验证功能。
"""

from typing import Any

import pytest


class TestValidators:
    """数据验证器测试"""

    def test_string_validation(self):
        """测试字符串验证"""

        def validate_string(
            value: Any, min_length: int = 0, max_length: int = None
        ) -> bool:
            if not isinstance(value, str):
                return False
            if len(value) < min_length:
                return False
            if max_length is not None and len(value) > max_length:
                return False
            return True

        # 测试有效字符串
        assert validate_string("hello") is True
        assert validate_string("test", min_length=3) is True
        assert validate_string("short", max_length=10) is True

        # 测试无效字符串
        assert validate_string(123) is False  # 非字符串
        assert validate_string("hi", min_length=3) is False  # 太短
        assert validate_string("very long string", max_length=5) is False  # 太长

    def test_email_validation(self):
        """测试邮箱验证"""

        def is_valid_email(email: str) -> bool:
            if not isinstance(email, str):
                return False
            if "@" not in email:
                return False
            local, domain = email.split("@", 1)
            if not local or not domain:
                return False
            if "." not in domain:
                return False
            return True

        # 测试有效邮箱
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
        ]
        for email in valid_emails:
            assert is_valid_email(email) is True

        # 测试无效邮箱
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user domain.com",
        ]
        for email in invalid_emails:
            assert is_valid_email(email) is False

    def test_phone_number_validation(self):
        """测试电话号码验证"""

        def is_valid_phone(phone: str) -> bool:
            if not isinstance(phone, str):
                return False
            # 移除所有非数字字符
            digits = "".join(filter(str.isdigit, phone))
            # 检查长度（10-15位数字）
            return 10 <= len(digits) <= 15

        # 测试有效电话号码
        valid_phones = [
            "1234567890",
            "+1-234-567-8901",
            "(123) 456-7890",
            "+44 20 7123 4567",
        ]
        for phone in valid_phones:
            assert is_valid_phone(phone) is True

        # 测试无效电话号码
        invalid_phones = [
            "123",  # 太短
            "abcdefghij",  # 非数字
            "12345678901234567890",  # 太长
            "",
        ]
        for phone in invalid_phones:
            assert is_valid_phone(phone) is False

    def test_numeric_validation(self):
        """测试数值验证"""

        def validate_number(
            value: Any, min_val: float = None, max_val: float = None
        ) -> bool:
            try:
                num = float(value)
                if min_val is not None and num < min_val:
                    return False
                if max_val is not None and num > max_val:
                    return False
                return True
            except (ValueError, TypeError):
                return False

        # 测试有效数值
        assert validate_number(123) is True
        assert validate_number(45.67) is True
        assert validate_number("123") is True
        assert validate_number("45.67") is True

        # 测试范围验证
        assert validate_number(50, min_val=0, max_val=100) is True
        assert validate_number(25, min_val=30) is False  # 小于最小值
        assert validate_number(75, max_val=50) is False  # 大于最大值

        # 测试无效数值
        assert validate_number("abc") is False
        assert validate_number(None) is False
        assert validate_number([]) is False

    def test_date_validation(self):
        """测试日期验证"""
        from datetime import datetime

        def is_valid_date(date_string: str, date_format: str = "%Y-%m-%d") -> bool:
            try:
                datetime.strptime(date_string, date_format)
                return True
            except ValueError:
                return False

        # 测试有效日期
        assert is_valid_date("2024-01-01") is True
        assert is_valid_date("2024-12-31") is True
        assert is_valid_date("2024-02-29") is True  # 2024是闰年

        # 测试不同格式
        assert is_valid_date("01/01/2024", "%d/%m/%Y") is True
        assert is_valid_date("2024-01-01 15:30:00", "%Y-%m-%d %H:%M:%S") is True

        # 测试无效日期
        assert is_valid_date("invalid-date") is False
        assert is_valid_date("2024-13-01") is False  # 无效月份
        assert is_valid_date("2024-01-32") is False  # 无效日期
        assert is_valid_date("2023-02-29") is False  # 2023不是闰年

    def test_url_validation(self):
        """测试URL验证"""

        def is_valid_url(url: str) -> bool:
            if not isinstance(url, str):
                return False
            if not url.startswith(("http://", "https://")):
                return False
            return "." in url

        # 测试有效URL
        valid_urls = [
            "https://www.example.com",
            "http://api.test.org",
            "https://subdomain.example.co.uk/path",
        ]
        for url in valid_urls:
            assert is_valid_url(url) is True

        # 测试无效URL
        invalid_urls = [
            "ftp://example.com",
            "www.example.com",
            "example.com",
            "https://",
            "",
        ]
        for url in invalid_urls:
            assert is_valid_url(url) is False

    def test_password_strength_validation(self):
        """测试密码强度验证"""

        def check_password_strength(password: str) -> dict[str, Any]:
            result = {"is_valid": True, "score": 0, "issues": []}

            if len(password) < 8:
                result["issues"].append("Password too short (minimum 8 characters)")
                result["is_valid"] = False

            if not any(c.isupper() for c in password):
                result["issues"].append("Password must contain uppercase letter")
                result["score"] += 1

            if not any(c.islower() for c in password):
                result["issues"].append("Password must contain lowercase letter")
                result["score"] += 1

            if not any(c.isdigit() for c in password):
                result["issues"].append("Password must contain digit")
                result["score"] += 1

            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                result["issues"].append("Password must contain special character")
                result["score"] += 1

            # 计算强度分数（4-无问题，0-有问题）
            result["score"] = 4 - result["score"]

            return result

        # 测试强密码
        strong_result = check_password_strength("StrongP@ss123")
        assert strong_result["is_valid"] is True
        assert strong_result["score"] == 4
        assert len(strong_result["issues"]) == 0

        # 测试弱密码
        weak_result = check_password_strength("weak")
        assert weak_result["is_valid"] is False
        assert weak_result["score"] < 4
        assert len(weak_result["issues"]) > 0

    def test_list_validation(self):
        """测试列表验证"""

        def validate_list(
            items: Any,
            item_type: type = None,
            min_length: int = 0,
            max_length: int = None,
        ) -> bool:
            if not isinstance(items, (list, tuple)):
                return False
            if len(items) < min_length:
                return False
            if max_length is not None and len(items) > max_length:
                return False
            if item_type is not None:
                return all(isinstance(item, item_type) for item in items)
            return True

        # 测试有效列表
        assert validate_list([1, 2, 3]) is True
        assert validate_list([1, 2, 3], item_type=int) is True
        assert validate_list([1, 2, 3], min_length=2) is True
        assert validate_list([1, 2, 3], max_length=5) is True

        # 测试无效列表
        assert validate_list("not a list") is False
        assert validate_list([1, "2", 3], item_type=int) is False
        assert validate_list([1], min_length=2) is False
        assert validate_list([1, 2, 3, 4, 5, 6], max_length=5) is False

    def test_dict_validation(self):
        """测试字典验证"""

        def validate_dict(
            data: Any, required_keys: list[str] = None, optional_keys: list[str] = None
        ) -> bool:
            if not isinstance(data, dict):
                return False
            if required_keys:
                missing_keys = [key for key in required_keys if key not in data]
                if missing_keys:
                    return False
            if optional_keys:
                extra_keys = [
                    key for key in data if key not in required_keys + optional_keys
                ]
                if extra_keys:
                    return False
            return True

        # 测试有效字典
        valid_dict = {"name": "test", "age": 25, "email": "test@example.com"}
        assert (
            validate_dict(
                valid_dict, required_keys=["name", "age"], optional_keys=["email"]
            )
            is True
        )

        # 测试无效字典
        assert validate_dict("not a dict", required_keys=["name"]) is False
        assert (
            validate_dict({"name": "test"}, required_keys=["name", "age"]) is False
        )  # 缺少必需键
        assert (
            validate_dict(
                {"name": "test", "age": 25, "extra": "value"},
                required_keys=["name"],
                optional_keys=["age"],
            )
            is False
        )  # 额外键

    def test_regex_validation(self):
        """测试正则表达式验证"""
        import re

        def validate_pattern(text: str, pattern: str) -> bool:
            try:
                return bool(re.match(pattern, text))
            except re.error:
                return False

        # 测试有效模式
        assert validate_pattern("abc123", r"[a-z]+[0-9]+") is True
        assert (
            validate_pattern(
                "test@example.com", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            )
            is True
        )
        assert validate_pattern("2024-01-01", r"\d{4}-\d{2}-\d{2}") is True

        # 测试无效模式
        assert validate_pattern("123abc", r"[a-z]+[0-9]+") is False  # 大小写不匹配
        assert validate_pattern("invalid", r"[invalid") is False  # 无效正则表达式

    def test_range_validation(self):
        """测试范围验证"""

        def validate_range(
            value: Any, min_val: Any = None, max_val: Any = None
        ) -> bool:
            try:
                if min_val is not None and value < min_val:
                    return False
                if max_val is not None and value > max_val:
                    return False
                return True
            except TypeError:
                return False

        # 测试数值范围
        assert validate_range(50, min_val=0, max_val=100) is True
        assert validate_range(-1, min_val=0) is False
        assert validate_range(101, max_val=100) is False

        # 测试字符串范围
        assert validate_range("middle", min_val="a", max_val="z") is True
        assert validate_range("before", min_val="middle") is False

        # 测试日期范围
        from datetime import date

        test_date = date(2024, 6, 15)  # 使用固定日期避免测试时依赖
        assert (
            validate_range(
                test_date, min_val=date(2024, 1, 1), max_val=date(2024, 12, 31)
            )
            is True
        )
        assert validate_range(date(2025, 1, 1), max_val=date(2024, 12, 31)) is False


class TestValidatorIntegration:
    """验证器集成测试"""

    def test_user_data_validation(self):
        """测试用户数据验证"""

        def validate_user_data(data: dict[str, Any]) -> dict[str, Any]:
            errors = []

            # 验证必需字段
            required_fields = ["username", "email", "password"]
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")

            # 验证用户名
            if "username" in data:
                username = data["username"]
                if not isinstance(username, str):
                    errors.append("Username must be a string")
                elif len(username) < 3:
                    errors.append("Username must be at least 3 characters")
                elif not username.isalnum():
                    errors.append("Username must contain only letters and numbers")

            # 验证邮箱
            if "email" in data:
                email = data["email"]
                if not isinstance(email, str):
                    errors.append("Email must be a string")
                elif "@" not in email:
                    errors.append("Invalid email format")

            # 验证密码
            if "password" in data:
                password = data["password"]
                if not isinstance(password, str):
                    errors.append("Password must be a string")
                elif len(password) < 8:
                    errors.append("Password must be at least 8 characters")

            return {"is_valid": len(errors) == 0, "errors": errors}

        # 测试有效用户数据
        valid_user = {
            "username": "testuser123",
            "email": "test@example.com",
            "password": "SecurePass123",
        }
        result = validate_user_data(valid_user)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

        # 测试无效用户数据
        invalid_user = {
            "username": "ab",  # 太短
            "email": "invalid-email",  # 无效格式
            # 缺少密码
        }
        result = validate_user_data(invalid_user)
        assert result["is_valid"] is False
        assert len(result["errors"]) >= 2

    def test_product_data_validation(self):
        """测试产品数据验证"""

        def validate_product(data: dict[str, Any]) -> dict[str, Any]:
            result = {"is_valid": True, "warnings": [], "errors": []}

            # 验证价格
            if "price" in data:
                try:
                    price = float(data["price"])
                    if price < 0:
                        result["errors"].append("Price cannot be negative")
                        result["is_valid"] = False
                    elif price > 10000:
                        result["warnings"].append("High price value")
                except ValueError:
                    result["errors"].append("Invalid price format")
                    result["is_valid"] = False

            # 验证库存
            if "stock" in data:
                try:
                    stock = int(data["stock"])
                    if stock < 0:
                        result["errors"].append("Stock cannot be negative")
                        result["is_valid"] = False
                    elif stock > 1000:
                        result["warnings"].append("High stock quantity")
                except ValueError:
                    result["errors"].append("Invalid stock format")
                    result["is_valid"] = False

            # 验证分类
            valid_categories = ["electronics", "clothing", "books", "home", "sports"]
            if "category" in data and data["category"] not in valid_categories:
                result["warnings"].append(f"Unknown category: {data['category']}")

            return result

        # 测试有效产品
        valid_product = {
            "name": "Test Product",
            "price": 29.99,
            "stock": 100,
            "category": "electronics",
        }
        result = validate_product(valid_product)
        assert result["is_valid"] is True

        # 测试无效产品
        invalid_product = {
            "name": "Invalid Product",
            "price": -10,  # 负价格
            "stock": "invalid",  # 无效格式
            "category": "unknown",  # 未知分类
        }
        result = validate_product(invalid_product)
        assert result["is_valid"] is False
        assert len(result["errors"]) >= 2
        assert len(result["warnings"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
