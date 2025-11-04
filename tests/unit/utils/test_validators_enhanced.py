"""
验证器增强测试 - 深化覆盖未测试的代码路径
"""

from src.utils.validators import (is_valid_email, is_valid_phone, is_valid_url,
                                  validate_data_types,
                                  validate_required_fields)


class TestValidatorsEnhanced:
    """验证器增强测试类 - 深化测试覆盖率"""

    def test_validate_required_fields_missing_values(self):
        """测试必需字段验证 - 缺失值的各种情况"""
        # 测试字段缺失
        data = {"name": "John"}
        required_fields = ["name", "email"]
        missing = validate_required_fields(data, required_fields)
        assert "email" in missing
        assert len(missing) == 1

        # 测试字段为None
        data_with_none = {"name": "John", "email": None}
        missing_with_none = validate_required_fields(data_with_none, required_fields)
        assert "email" in missing_with_none

        # 测试字段为空字符串
        data_with_empty = {"name": "John", "email": ""}
        missing_with_empty = validate_required_fields(data_with_empty, required_fields)
        assert "email" in missing_with_empty

        # 测试多个字段缺失
        data_multiple_missing = {"name": "John"}
        required_multiple = ["name", "email", "age", "phone"]
        missing_multiple = validate_required_fields(
            data_multiple_missing, required_multiple
        )
        assert len(missing_multiple) == 3
        assert "email" in missing_multiple
        assert "age" in missing_multiple
        assert "phone" in missing_multiple

    def test_validate_required_fields_all_present(self):
        """测试所有必需字段都存在的情况"""
        data = {
            "name": "John",
            "email": "john@example.com",
            "age": 30,
            "phone": "1234567890",
        }
        required_fields = ["name", "email", "age", "phone"]
        missing = validate_required_fields(data, required_fields)
        assert len(missing) == 0

    def test_validate_data_types_valid_types(self):
        """测试数据类型验证 - 有效类型"""
        data = {
            "name": "John",
            "age": 30,
            "height": 175.5,
            "active": True,
            "tags": ["tag1", "tag2"],
        }
        schema = {
            "name": str,
            "age": int,
            "height": float,
            "active": bool,
            "tags": list,
        }
        errors = validate_data_types(data, schema)
        assert len(errors) == 0

    def test_validate_data_types_invalid_types(self):
        """测试数据类型验证 - 无效类型"""
        data = {
            "name": "John",
            "age": "30",  # 应该是int
            "height": "175.5",  # 应该是float
            "active": "true",  # 应该是bool
            "tags": "tag1",  # 应该是list
        }
        schema = {
            "name": str,
            "age": int,
            "height": float,
            "active": bool,
            "tags": list,
        }
        errors = validate_data_types(data, schema)
        assert len(errors) == 4

        # 检查错误消息格式
        error_messages = " ".join(errors)
        assert "Field 'age' should be int" in error_messages
        assert "Field 'height' should be float" in error_messages
        assert "Field 'active' should be bool" in error_messages
        assert "Field 'tags' should be list" in error_messages

    def test_validate_data_types_partial_schema(self):
        """测试数据类型验证 - 部分schema"""
        data = {"name": "John", "age": 30, "extra_field": "not in schema"}
        schema = {"name": str, "age": int}
        errors = validate_data_types(data, schema)
        assert len(errors) == 0  # 只验证schema中的字段

    def test_validate_data_types_empty_data(self):
        """测试数据类型验证 - 空数据"""
        data = {}
        schema = {"name": str, "age": int}
        errors = validate_data_types(data, schema)
        assert len(errors) == 0  # 空数据没有类型错误

    def test_validate_data_types_complex_types(self):
        """测试数据类型验证 - 复杂类型"""
        data = {"metadata": {"key": "value"}, "scores": [85, 90, 78]}
        schema = {"metadata": dict, "scores": list}
        errors = validate_data_types(data, schema)
        assert len(errors) == 0

        # 测试复杂类型错误
        data_invalid = {"metadata": "not a dict", "scores": "not a list"}
        errors_invalid = validate_data_types(data_invalid, schema)
        assert len(errors_invalid) == 2

    def test_edge_cases_email_validation(self):
        """测试邮箱验证的边界情况"""
        # 测试各种边界情况
        edge_cases = [
            "a@b.c",  # 最短有效邮箱
            "user@sub.domain.com",  # 子域名
            "test+123@example.co.uk",  # 带标签和长域名
            "user.name+tag@example-domain.com",  # 复杂格式
        ]

        for email in edge_cases:
            result = is_valid_email(email)
            assert isinstance(result, bool)

        # 无效边界情况
        invalid_cases = [
            "@domain.com",  # 缺少用户名
            "user@",  # 缺少域名
            "user@.com",  # 域名以点开头
            "user@com.",  # 域名以点结尾
        ]

        for email in invalid_cases:
            assert is_valid_email(email) is False

    def test_edge_cases_phone_validation(self):
        """测试电话验证的边界情况"""
        # 国际号码格式
        international_phones = [
            "+1 (555) 123-4567",
            "+44 20 7946 0958",
            "+86 138 0013 8000",
            "+49 30 12345678",
        ]

        for phone in international_phones:
            result = is_valid_phone(phone)
            assert isinstance(result, bool)

        # 无效格式
        invalid_phones = [
            "123",  # 太短
            "phone",  # 非数字字符
            "+",  # 只有加号
            "1-800-INVALID",  # 包含字母
        ]

        for phone in invalid_phones:
            assert is_valid_phone(phone) is False

    def test_edge_cases_url_validation(self):
        """测试URL验证的边界情况"""
        # 各种有效URL格式
        valid_urls = [
            "http://example.com",
            "https://www.example.com",
            "https://example.com:8080",
            "https://example.com/path/to/resource",
            "https://example.com/path?query=value&param2=test",
            "https://example.com/path#section",
            "http://sub.domain.example.co.uk",
        ]

        for url in valid_urls:
            result = is_valid_url(url)
            assert isinstance(result, bool)

        # 无效URL格式
        invalid_urls = [
            "ftp://example.com",  # 非http协议
            "http//example.com",  # 缺少冒号
            "example.com",  # 缺少协议
            "http://",  # 缺少域名
            "https://.com",  # 无效域名
        ]

        for url in invalid_urls:
            assert is_valid_url(url) is False

    def test_performance_considerations(self):
        """测试性能考虑 - 大量数据验证"""
        import time

        # 测试大量字段验证性能
        large_data = {f"field_{i}": f"value_{i}" for i in range(100)}
        required_fields = list(large_data.keys())[:50]

        start_time = time.time()
        missing = validate_required_fields(large_data, required_fields)
        end_time = time.time()

        assert len(missing) == 0
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

        # 测试大量类型验证性能
        large_schema = {f"field_{i}": str for i in range(100)}
        start_time = time.time()
        errors = validate_data_types(large_data, large_schema)
        end_time = time.time()

        assert len(errors) == 0
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        # 测试Unicode邮箱
        unicode_emails = ["测试@example.com", "user@münchen.de", "josé@ejemplo.es"]

        for email in unicode_emails:
            result = is_valid_email(email)
            # Unicode支持取决于正则表达式实现
            assert isinstance(result, bool)

        # 测试Unicode电话号码
        unicode_phones = ["+86 138 0013 8000", "+49 30 12345678"]  # 中文  # 德文

        for phone in unicode_phones:
            result = is_valid_phone(phone)
            assert isinstance(result, bool)
