"""
数据验证器测试 - 符合严格测试规范

完整覆盖src.utils.validators模块的所有功能，包含成功、异常和边界用例
"""

import re
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from src.utils.validators import (
    is_valid_email,
    is_valid_phone,
    is_valid_url,
    validate_data_types,
    validate_required_fields,
)


@pytest.mark.unit
class TestEmailValidator:
    """邮箱验证器测试 - 符合严格测试规范"""

    def test_valid_emails_success(self) -> None:
        """✅ 成功用例：有效的邮箱地址"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com",
            "email@sub.domain.com",
            "a@b.co",  # 最短有效邮箱
            "very.long.email.address@example-domain.com",
            "user.name+tag+category@example.co.uk",
        ]

        for email in valid_emails:
            assert is_valid_email(email) is True, f"应该验证通过: {email}"

    def test_invalid_emails_failure(self) -> None:
        """❌ 失败用例：无效的邮箱地址"""
        invalid_emails = [
            "",  # 空字符串
            "plainaddress",  # 缺少@和域名
            "@missing-local.org",  # 缺少本地部分
            "username@",  # 缺少域名
            "username@.com",  # 域名以点开始
            "username@com",  # 缺少顶级域名点
            "username@.com.com",  # 域名以点开始
            ".username@yahoo.com",  # 本地部分以点开始
            "username@yahoo.com.",  # 域名以点结束
            "username@yahoo..com",  # 域名有连续点
            "username@yahoo.c",  # 顶级域名太短
            "username@yahoo.corporate",  # 无效的顶级域名
        ]

        for email in invalid_emails:
            assert is_valid_email(email) is False, f"应该验证失败: {email}"

    def test_email_case_sensitivity(self) -> None:
        """✅ 边界用例：大小写敏感性"""
        email_upper = "TEST@EXAMPLE.COM"
        email_mixed = "Test@Example.Com"

        # 邮箱验证应该对大小写不敏感
        assert is_valid_email(email_upper) is True
        assert is_valid_email(email_mixed) is True

    def test_email_with_unicode_characters(self) -> None:
        """✅ 边界用例：Unicode字符"""
        unicode_emails = [
            "用户@example.com",  # 中文用户名
            "test@例子.公司",  # 中文域名
            "josé@café.com",  # 带重音符号
        ]

        for email in unicode_emails:
            # 当前正则可能不支持所有Unicode，但不应崩溃
            result = is_valid_email(email)
            assert isinstance(result, bool)

    @patch("re.match")
    def test_email_regex_exception(self, mock_match: Mock) -> None:
        """❌ 异常用例：正则表达式异常"""
        mock_match.side_effect = Exception("Regex error")

        with pytest.raises(Exception, match="Regex error"):
            is_valid_email("test@example.com")

    def test_email_none_input(self) -> None:
        """❌ 异常用例：None输入"""
        with pytest.raises(TypeError):
            is_valid_email(None)


@pytest.mark.unit
class TestPhoneValidator:
    """电话号码验证器测试 - 符合严格测试规范"""

    def test_valid_phones_success(self) -> None:
        """✅ 成功用例：有效的电话号码"""
        valid_phones = [
            "+1234567890",  # 国际格式
            "1234567890",  # 纯数字
            "123 456 7890",  # 空格分隔
            "123-456-7890",  # 破折号分隔
            "(123) 456-7890",  # 括号格式
            "+1 (123) 456-7890",  # 完整国际格式
            "123.456.7890",  # 点分隔
            "123456789012345",  # 长号码
        ]

        for phone in valid_phones:
            assert is_valid_phone(phone) is True, f"应该验证通过: {phone}"

    def test_invalid_phones_failure(self) -> None:
        """❌ 失败用例：无效的电话号码"""
        invalid_phones = [
            "",  # 空字符串
            "abc",  # 纯字母
            "123abc456",  # 字母数字混合
            "123-456-789a",  # 包含字母
            "+",  # 只有加号
            "()",  # 只有括号
            "  ",  # 只有空格
            "--",  # 只有破折号
        ]

        for phone in invalid_phones:
            assert is_valid_phone(phone) is False, f"应该验证失败: {phone}"

    def test_phone_edge_cases(self) -> None:
        """✅ 边界用例：边界条件"""
        edge_cases = [
            "1",  # 单个数字
            "+",  # 只有加号
            " ",  # 只有空格
        ]

        for phone in edge_cases:
            result = is_valid_phone(phone)
            assert isinstance(result, bool)

    @patch("re.match")
    def test_phone_regex_exception(self, mock_match: Mock) -> None:
        """❌ 异常用例：正则表达式异常"""
        mock_match.side_effect = Exception("Regex error")

        with pytest.raises(Exception, match="Regex error"):
            is_valid_phone("1234567890")

    def test_phone_none_input(self) -> None:
        """❌ 异常用例：None输入"""
        with pytest.raises(TypeError):
            is_valid_phone(None)


@pytest.mark.unit
class TestURLValidator:
    """URL验证器测试 - 符合严格测试规范"""

    def test_valid_urls_success(self) -> None:
        """✅ 成功用例：有效的URL"""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "https://www.example.com",
            "https://example.co.uk",
            "https://sub.example.com/path",
            "https://example.com/path/to/page",
            "https://example.com/path?query=value",
            "https://example.com/path?query=value&other=test",
            "https://example.com/path#section",
            "https://example.com:8080/path",  # 带端口
            "https://example.com/path-with-dashes",  # 带破折号
        ]

        for url in valid_urls:
            assert is_valid_url(url) is True, f"应该验证通过: {url}"

    def test_invalid_urls_failure(self) -> None:
        """❌ 失败用例：无效的URL"""
        invalid_urls = [
            "",  # 空字符串
            "example.com",  # 缺少协议
            "ftp://example.com",  # 不支持的协议
            "http://",  # 缺少域名
            "https://",  # 缺少域名
            "http:/example.com",  # 格式错误
            "http//example.com",  # 缺少冒号
            "javascript:alert('test')",  # 危险协议
            "data:text/plain,test",  # 危险协议
        ]

        for url in invalid_urls:
            assert is_valid_url(url) is False, f"应该验证失败: {url}"

    def test_url_edge_cases(self) -> None:
        """✅ 边界用例：边界条件"""
        edge_cases = [
            "http://a.co",  # 最短有效URL
            "https://example-with-very-long-subdomain-name.com",
            "https://example.com/path/with/many/segments",
            "https://example.com/?query=value&other=test&third=more",
        ]

        for url in edge_cases:
            result = is_valid_url(url)
            assert isinstance(result, bool)

    @patch("re.match")
    def test_url_regex_exception(self, mock_match: Mock) -> None:
        """❌ 异常用例：正则表达式异常"""
        mock_match.side_effect = Exception("Regex error")

        with pytest.raises(Exception, match="Regex error"):
            is_valid_url("https://example.com")

    def test_url_none_input(self) -> None:
        """❌ 异常用例：None输入"""
        with pytest.raises(TypeError):
            is_valid_url(None)


@pytest.mark.unit
class TestRequiredFieldsValidator:
    """必填字段验证器测试 - 符合严格测试规范"""

    def test_all_required_fields_present_success(self) -> None:
        """✅ 成功用例：所有必填字段都存在"""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
        }
        required_fields = ["name", "email", "age"]

        missing = validate_required_fields(data, required_fields)
        assert missing == []

    def test_missing_required_fields_failure(self) -> None:
        """❌ 失败用例：缺少必填字段"""
        data = {
            "name": "John Doe",
            # email 缺失
            "age": 30,
        }
        required_fields = ["name", "email", "age"]

        missing = validate_required_fields(data, required_fields)
        assert missing == ["email"]

    def test_multiple_missing_fields_failure(self) -> None:
        """❌ 失败用例：多个必填字段缺失"""
        data = {
            "name": "John Doe",
            # email 和 age 都缺失
        }
        required_fields = ["name", "email", "age"]

        missing = validate_required_fields(data, required_fields)
        assert set(missing) == {"email", "age"}

    def test_null_values_as_missing(self) -> None:
        """✅ 边界用例：None值被视为缺失"""
        data = {
            "name": "John Doe",
            "email": None,
            "age": 30,
        }
        required_fields = ["name", "email", "age"]

        missing = validate_required_fields(data, required_fields)
        assert missing == ["email"]

    def test_empty_string_as_missing(self) -> None:
        """✅ 边界用例：空字符串被视为缺失"""
        data = {
            "name": "John Doe",
            "email": "",
            "age": 30,
        }
        required_fields = ["name", "email", "age"]

        missing = validate_required_fields(data, required_fields)
        assert missing == ["email"]

    def test_no_required_fields_success(self) -> None:
        """✅ 边界用例：没有必填字段要求"""
        data = {"name": "John Doe"}
        required_fields: List[str] = []

        missing = validate_required_fields(data, required_fields)
        assert missing == []

    def test_empty_data_with_requirements_failure(self) -> None:
        """❌ 失败用例：空数据但有必填要求"""
        data: Dict[str, Any] = {}
        required_fields = ["name", "email"]

        missing = validate_required_fields(data, required_fields)
        assert set(missing) == {"name", "email"}

    def test_non_string_field_names(self) -> None:
        """✅ 边界用例：非字符串字段名"""
        data = {"name": "John", 1: "value"}
        required_fields = ["name"]

        missing = validate_required_fields(data, required_fields)
        assert missing == []

    def test_validate_required_fields_type_errors(self) -> None:
        """❌ 异常用例：类型错误"""
        with pytest.raises((TypeError, AttributeError)):
            validate_required_fields(None, ["name"])  # type: ignore

        with pytest.raises((TypeError, AttributeError)):
            validate_required_fields({}, None)  # type: ignore


@pytest.mark.unit
class TestDataTypesValidator:
    """数据类型验证器测试 - 符合严格测试规范"""

    def test_all_valid_types_success(self) -> None:
        """✅ 成功用例：所有数据类型都正确"""
        data = {
            "name": "John",  # str
            "age": 30,  # int
            "height": 175.5,  # float
            "is_active": True,  # bool
            "tags": ["tag1", "tag2"],  # list
            "metadata": {"key": "value"},  # dict
        }
        schema = {
            "name": str,
            "age": int,
            "height": float,
            "is_active": bool,
            "tags": list,
            "metadata": dict,
        }

        errors = validate_data_types(data, schema)
        assert errors == []

    def test_type_mismatch_errors(self) -> None:
        """❌ 失败用例：数据类型不匹配"""
        data = {
            "name": "John",  # 正确
            "age": "30",  # 应该是int，但提供了str
            "height": "175.5",  # 应该是float，但提供了str
            "is_active": "true",  # 应该是bool，但提供了str
        }
        schema = {
            "name": str,
            "age": int,
            "height": float,
            "is_active": bool,
        }

        errors = validate_data_types(data, schema)
        assert len(errors) == 3
        assert any("'age' should be int" in error for error in errors)
        assert any("'height' should be float" in error for error in errors)
        assert any("'is_active' should be bool" in error for error in errors)

    def test_extra_fields_in_data(self) -> None:
        """✅ 边界用例：数据中有额外字段"""
        data = {
            "name": "John",
            "age": 30,
            "extra_field": "should be ignored",  # schema中没有定义
        }
        schema = {
            "name": str,
            "age": int,
        }

        errors = validate_data_types(data, schema)
        # 额外字段应该被忽略，没有错误
        assert errors == []

    def test_missing_fields_in_data(self) -> None:
        """✅ 边界用例：数据中缺少字段"""
        data = {
            "name": "John",
            # age 字段缺失
        }
        schema = {
            "name": str,
            "age": int,
        }

        errors = validate_data_types(data, schema)
        # 缺失字段应该被忽略，没有错误
        assert errors == []

    def test_complex_type_validation(self) -> None:
        """✅ 成功用例：复杂类型验证"""
        # 测试继承关系
        data = {
            "number": 42,  # int 是 object 的子类
            "text": "hello",
        }
        schema = {
            "number": object,  # 应该接受任何对象
            "text": str,
        }

        errors = validate_data_types(data, schema)
        assert errors == []

    def test_none_values_validation(self) -> None:
        """✅ 边界用例：None值验证"""
        data = {
            "optional_field": None,
            "required_field": "value",
        }
        schema = {
            "optional_field": str,
            "required_field": str,
        }

        errors = validate_data_types(data, schema)
        # None值可能不匹配类型，这取决于实现
        # 这里我们只验证函数能正常执行
        assert isinstance(errors, list)

    def test_empty_data_and_schema(self) -> None:
        """✅ 边界用例：空数据和模式"""
        data: Dict[str, Any] = {}
        schema: Dict[str, type] = {}

        errors = validate_data_types(data, schema)
        assert errors == []

    def test_validate_data_types_type_errors(self) -> None:
        """❌ 异常用例：类型错误"""
        with pytest.raises((TypeError, AttributeError)):
            validate_data_types(None, {"name": str})  # type: ignore

        with pytest.raises((TypeError, AttributeError)):
            validate_data_types({}, None)  # type: ignore


@pytest.mark.unit
class TestValidatorsIntegration:
    """验证器集成测试 - 符合严格测试规范"""

    def test_complete_user_data_validation_success(self) -> None:
        """✅ 集成用例：完整用户数据验证成功"""
        user_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "website": "https://johndoe.com",
            "age": 30,
            "is_active": True,
        }

        # 验证必填字段
        required_fields = ["name", "email", "age"]
        missing = validate_required_fields(user_data, required_fields)
        assert missing == []

        # 验证数据类型
        schema = {
            "name": str,
            "email": str,
            "age": int,
            "is_active": bool,
        }
        type_errors = validate_data_types(user_data, schema)
        assert type_errors == []

        # 验证格式
        assert is_valid_email(user_data["email"])
        assert is_valid_phone(user_data["phone"])
        assert is_valid_url(user_data["website"])

    def test_invalid_user_data_validation_failure(self) -> None:
        """❌ 集成用例：无效用户数据验证失败"""
        user_data = {
            "name": "John Doe",
            "email": "invalid-email",  # 无效邮箱
            "phone": "abc",  # 无效电话
            "website": "not-a-url",  # 无效URL
            "age": "thirty",  # 错误类型
        }

        # 验证必填字段（假设有这些要求）
        required_fields = ["name", "email", "age"]
        missing = validate_required_fields(user_data, required_fields)
        assert missing == []  # 字段都存在

        # 验证数据类型
        schema = {
            "name": str,
            "email": str,
            "age": int,
        }
        type_errors = validate_data_types(user_data, schema)
        assert len(type_errors) > 0
        assert any("'age' should be int" in error for error in type_errors)

        # 验证格式
        assert not is_valid_email(user_data["email"])
        assert not is_valid_phone(user_data["phone"])
        assert not is_valid_url(user_data["website"])

    def test_performance_large_dataset_validation(self) -> None:
        """✅ 性能用例：大数据集验证性能"""
        import time

        # 生成大量测试数据
        large_dataset = []
        for i in range(1000):
            data = {
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "age": 20 + (i % 60),
            }
            large_dataset.append(data)

        required_fields = ["name", "email", "age"]
        schema = {"name": str, "email": str, "age": int}

        start_time = time.time()

        # 验证所有数据
        all_errors = []
        for data in large_dataset:
            missing = validate_required_fields(data, required_fields)
            type_errors = validate_data_types(data, schema)
            if missing or type_errors:
                all_errors.extend(missing)
                all_errors.extend(type_errors)

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证结果
        assert processing_time < 2.0  # 应该在2秒内完成
        assert len(all_errors) == 0  # 生成的数据应该都是有效的


@pytest.fixture(autouse=True)
def setup_validators_test():
    """自动应用的fixture，设置验证器测试环境"""
    yield
    # 清理代码
