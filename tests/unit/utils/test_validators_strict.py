"""
数据验证器测试 - 严格测试规范（简化版）

专注于核心功能和基本异常处理
"""

from unittest.mock import Mock, patch
from typing import Dict, Any

import pytest
from src.utils.validators import (
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    validate_required_fields,
    validate_data_types,
)


@pytest.mark.unit
class TestEmailValidatorStrict:
    """邮箱验证器测试 - 严格规范"""

    def test_valid_emails_success(self) -> None:
        """✅ 成功用例：有效邮箱地址"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com",
        ]

        for email in valid_emails:
            assert is_valid_email(email) is True, f"应该验证通过: {email}"

    def test_invalid_emails_failure(self) -> None:
        """❌ 失败用例：无效邮箱地址"""
        invalid_emails = [
            "",
            "plainaddress",
            "@missing-local.org",
            "username@",
            "username@.com",
        ]

        for email in invalid_emails:
            assert is_valid_email(email) is False, f"应该验证失败: {email}"

    def test_email_exception_handling(self) -> None:
        """❌ 异常用例：异常处理"""
        with pytest.raises((TypeError, AttributeError)):
            is_valid_email(None)

    @patch('re.match')
    def test_email_regex_exception(self, mock_match: Mock) -> None:
        """❌ 异常用例：正则表达式异常"""
        mock_match.side_effect = Exception("Regex error")

        with pytest.raises(Exception, match="Regex error"):
            is_valid_email("test@example.com")


@pytest.mark.unit
class TestPhoneValidatorStrict:
    """电话号码验证器测试 - 严格规范"""

    def test_valid_phones_success(self) -> None:
        """✅ 成功用例：有效电话号码"""
        valid_phones = [
            "+1234567890",
            "1234567890",
            "123 456 7890",
            "123-456-7890",
            "(123) 456-7890",
        ]

        for phone in valid_phones:
            assert is_valid_phone(phone) is True, f"应该验证通过: {phone}"

    def test_invalid_phones_failure(self) -> None:
        """❌ 失败用例：无效电话号码"""
        invalid_phones = [
            "",
            "abc",
            "123abc456",
            "123-456-789a",
        ]

        for phone in invalid_phones:
            assert is_valid_phone(phone) is False, f"应该验证失败: {phone}"

    def test_phone_exception_handling(self) -> None:
        """❌ 异常用例：异常处理"""
        with pytest.raises((TypeError, AttributeError)):
            is_valid_phone(None)


@pytest.mark.unit
class TestURLValidatorStrict:
    """URL验证器测试 - 严格规范"""

    def test_valid_urls_success(self) -> None:
        """✅ 成功用例：有效URL"""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "https://www.example.com",
            "https://example.com/path",
        ]

        for url in valid_urls:
            assert is_valid_url(url) is True, f"应该验证通过: {url}"

    def test_invalid_urls_failure(self) -> None:
        """❌ 失败用例：无效URL"""
        invalid_urls = [
            "",
            "example.com",
            "ftp://example.com",
            "http://",
        ]

        for url in invalid_urls:
            assert is_valid_url(url) is False, f"应该验证失败: {url}"

    def test_url_exception_handling(self) -> None:
        """❌ 异常用例：异常处理"""
        with pytest.raises((TypeError, AttributeError)):
            is_valid_url(None)


@pytest.mark.unit
class TestRequiredFieldsValidatorStrict:
    """必填字段验证器测试 - 严格规范"""

    def test_all_required_fields_present_success(self) -> None:
        """✅ 成功用例：所有必填字段都存在"""
        data = {"name": "John", "email": "john@example.com"}
        required_fields = ["name", "email"]

        missing = validate_required_fields(data, required_fields)
        assert missing == []

    def test_missing_required_fields_failure(self) -> None:
        """❌ 失败用例：缺少必填字段"""
        data = {"name": "John"}
        required_fields = ["name", "email"]

        missing = validate_required_fields(data, required_fields)
        assert missing == ["email"]

    def test_null_and_empty_values_as_missing(self) -> None:
        """✅ 边界用例：None和空值被视为缺失"""
        data = {"name": "John", "email": None, "age": ""}
        required_fields = ["name", "email", "age"]

        missing = validate_required_fields(data, required_fields)
        assert set(missing) == {"email", "age"}

    def test_empty_data_with_requirements(self) -> None:
        """❌ 失败用例：空数据但有要求"""
        data: Dict[str, Any] = {}
        required_fields = ["name", "email"]

        missing = validate_required_fields(data, required_fields)
        assert set(missing) == {"name", "email"}


@pytest.mark.unit
class TestDataTypesValidatorStrict:
    """数据类型验证器测试 - 严格规范"""

    def test_all_valid_types_success(self) -> None:
        """✅ 成功用例：所有数据类型正确"""
        data = {"name": "John", "age": 30, "active": True}
        schema = {"name": str, "age": int, "active": bool}

        errors = validate_data_types(data, schema)
        assert errors == []

    def test_type_mismatch_errors(self) -> None:
        """❌ 失败用例：数据类型不匹配"""
        data = {"name": "John", "age": "thirty", "active": "true"}
        schema = {"name": str, "age": int, "active": bool}

        errors = validate_data_types(data, schema)
        assert len(errors) > 0
        assert any("'age' should be int" in error for error in errors)
        assert any("'active' should be bool" in error for error in errors)

    def test_extra_fields_ignored(self) -> None:
        """✅ 边界用例：额外字段被忽略"""
        data = {"name": "John", "extra": "field"}
        schema = {"name": str}

        errors = validate_data_types(data, schema)
        assert errors == []


@pytest.mark.unit
class TestValidatorsIntegrationStrict:
    """验证器集成测试 - 严格规范"""

    def test_complete_user_validation_success(self) -> None:
        """✅ 集成用例：完整用户验证成功"""
        user_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "age": 30,
        }

        # 验证必填字段
        required_fields = ["name", "email", "age"]
        missing = validate_required_fields(user_data, required_fields)
        assert missing == []

        # 验证数据类型
        schema = {"name": str, "email": str, "age": int}
        type_errors = validate_data_types(user_data, schema)
        assert type_errors == []

        # 验证邮箱格式
        assert is_valid_email(user_data["email"])

    def test_invalid_user_validation_failure(self) -> None:
        """❌ 集成用例：无效用户验证失败"""
        user_data = {
            "name": "John Doe",
            "email": "invalid-email",
            "age": "thirty",
        }

        # 验证邮箱格式
        assert not is_valid_email(user_data["email"])

        # 验证数据类型
        schema = {"name": str, "email": str, "age": int}
        type_errors = validate_data_types(user_data, schema)
        assert len(type_errors) > 0

    def test_performance_batch_validation(self) -> None:
        """✅ 性能用例：批量验证性能"""
        import time

        # 生成测试数据
        test_data = []
        for i in range(100):
            data = {"name": f"User {i}", "email": f"user{i}@example.com"}
            test_data.append(data)

        required_fields = ["name", "email"]
        schema = {"name": str, "email": str}

        start_time = time.time()

        # 批量验证
        all_errors = 0
        for data in test_data:
            missing = validate_required_fields(data, required_fields)
            type_errors = validate_data_types(data, schema)
            if missing or type_errors:
                all_errors += 1

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证性能
        assert processing_time < 1.0
        assert all_errors == 0


@pytest.fixture(autouse=True)
def setup_validators_strict_test():
    """自动应用的fixture"""
    yield
    # 清理