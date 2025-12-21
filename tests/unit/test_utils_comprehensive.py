"""
工具函数库综合测试
第三层优化：专注工具函数库模块 (47% → 75%)
基于实际工具函数库结构的高覆盖率测试
"""

import pytest
import json
import tempfile
import os
import hashlib
import uuid
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, mock_open


class TestFileUtils:
    """文件处理工具测试"""

    def test_file_utils_ensure_dir_creation(self):
        """测试目录创建"""
        from src.utils import FileUtils

        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "nested", "directory")

            # 确保目录不存在
            assert not os.path.exists(new_dir)

            # 创建目录
            result = FileUtils.ensure_dir(new_dir)

            # 验证目录被创建
            assert os.path.exists(new_dir)
            assert os.path.isdir(new_dir)
            assert isinstance(result, Path)

    def test_file_utils_ensure_dir_existing(self):
        """测试确保已存在目录"""
        from src.utils import FileUtils

        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = os.path.join(temp_dir, "existing")
            os.makedirs(existing_dir)

            # 调用ensure_dir不应该出错
            result = FileUtils.ensure_dir(existing_dir)

            assert os.path.exists(existing_dir)
            assert isinstance(result, Path)

    def test_file_utils_read_json_success(self):
        """测试成功读取JSON文件"""
        from src.utils import FileUtils

        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        json_str = json.dumps(test_data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json_str)
            temp_file = f.name

        try:
            result = FileUtils.read_json(temp_file)
            assert result == test_data
            assert result["key"] == "value"
            assert result["number"] == 42
        finally:
            os.unlink(temp_file)

    def test_file_utils_read_json_file_not_found(self):
        """测试读取不存在的JSON文件"""
        from src.utils import FileUtils

        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json("nonexistent_file.json")

    def test_file_utils_read_json_invalid_json(self):
        """测试读取无效JSON文件"""
        from src.utils import FileUtils

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json}')  # 无效JSON
            temp_file = f.name

        try:
            with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
                FileUtils.read_json(temp_file)
        finally:
            os.unlink(temp_file)

    def test_file_utils_write_json_success(self):
        """测试成功写入JSON文件"""
        from src.utils import FileUtils

        test_data = {"name": "test", "items": [1, 2, 3]}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            FileUtils.write_json(test_data, temp_file)

            # 验证文件内容
            with open(temp_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data
        finally:
            os.unlink(temp_file)

    def test_file_utils_write_json_with_dir_creation(self):
        """测试写入JSON文件时自动创建目录"""
        from src.utils import FileUtils

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = os.path.join(temp_dir, "deeply", "nested", "dir")
            temp_file = os.path.join(nested_dir, "test.json")

            test_data = {"test": "data"}

            FileUtils.write_json(test_data, temp_file, ensure_dir=True)

            # 验证目录和文件都被创建
            assert os.path.exists(nested_dir)
            assert os.path.exists(temp_file)

    def test_file_utils_get_file_hash(self):
        """测试获取文件哈希"""
        from src.utils import FileUtils

        test_content = "Hello, World! This is a test file."

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(test_content)
            temp_file = f.name

        try:
            file_hash = FileUtils.get_file_hash(temp_file)

            # 验证哈希格式
            assert isinstance(file_hash, str)
            assert len(file_hash) == 32  # MD5哈希长度
            assert all(c in "0123456789abcdef" for c in file_hash)

            # 验证哈希一致性
            file_hash2 = FileUtils.get_file_hash(temp_file)
            assert file_hash == file_hash2
        finally:
            os.unlink(temp_file)

    def test_file_utils_get_file_size(self):
        """测试获取文件大小"""
        from src.utils import FileUtils

        test_content = "This is a test file for size measurement."

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(test_content)
            temp_file = f.name

        try:
            file_size = FileUtils.get_file_size(temp_file)

            assert isinstance(file_size, int)
            assert file_size == len(test_content.encode("utf-8"))
            assert file_size > 0
        finally:
            os.unlink(temp_file)


class TestDataValidator:
    """数据验证工具测试"""

    def test_data_validator_valid_email(self):
        """测试有效邮箱验证"""
        from src.utils import DataValidator

        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.org",
            "firstname.lastname@company.com",
        ]

        for email in valid_emails:
            assert DataValidator.is_valid_email(email) is True

    def test_data_validator_invalid_email(self):
        """测试无效邮箱验证"""
        from src.utils import DataValidator

        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user@.com",
            "",
            None,
        ]

        for email in invalid_emails:
            if email is not None:
                assert DataValidator.is_valid_email(email) is False

    def test_data_validator_valid_url(self):
        """测试有效URL验证"""
        from src.utils import DataValidator

        valid_urls = [
            "https://example.com",
            "http://localhost:8000",
            "https://sub.domain.co.uk/path",
            "http://192.168.1.1:3000",
            "https://example.com/path?query=value",
        ]

        for url in valid_urls:
            assert DataValidator.is_valid_url(url) is True

    def test_data_validator_invalid_url(self):
        """测试无效URL验证"""
        from src.utils import DataValidator

        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # 不支持ftp
            "example.com",  # 缺少协议
            "",
            None,
        ]

        for url in invalid_urls:
            if url is not None:
                assert DataValidator.is_valid_url(url) is False

    def test_data_validator_validate_required_fields_all_present(self):
        """测试验证必需字段 - 全部存在"""
        from src.utils import DataValidator

        data = {"name": "John Doe", "email": "john@example.com", "age": 30}

        required_fields = ["name", "email", "age"]
        missing = DataValidator.validate_required_fields(data, required_fields)

        assert missing == []

    def test_data_validator_validate_required_fields_missing_fields(self):
        """测试验证必需字段 - 缺失字段"""
        from src.utils import DataValidator

        data = {"name": "John Doe", "email": "john@example.com"}

        required_fields = ["name", "email", "age", "address"]
        missing = DataValidator.validate_required_fields(data, required_fields)

        assert set(missing) == {"age", "address"}

    def test_data_validator_validate_required_fields_none_values(self):
        """测试验证必需字段 - None值"""
        from src.utils import DataValidator

        data = {"name": "John Doe", "email": None, "age": 30, "address": ""}

        required_fields = ["name", "email", "age"]
        missing = DataValidator.validate_required_fields(data, required_fields)

        assert missing == ["email"]

    def test_data_validator_validate_data_types_all_valid(self):
        """测试验证数据类型 - 全部有效"""
        from src.utils import DataValidator

        data = {"name": "John", "age": 30, "active": True, "scores": [85, 90, 78]}

        type_specs = {"name": str, "age": int, "active": bool, "scores": list}

        invalid = DataValidator.validate_data_types(data, type_specs)
        assert invalid == []

    def test_data_validator_validate_data_types_invalid_types(self):
        """测试验证数据类型 - 无效类型"""
        from src.utils import DataValidator

        data = {
            "name": "John",
            "age": "30",  # 应该是int
            "active": "true",  # 应该是bool
            "scores": [85, 90, 78],
        }

        type_specs = {"name": str, "age": int, "active": bool, "scores": list}

        invalid = DataValidator.validate_data_types(data, type_specs)

        assert len(invalid) == 2
        assert any("age" in field for field in invalid)
        assert any("active" in field for field in invalid)

    def test_data_validator_validate_data_types_missing_fields(self):
        """测试验证数据类型 - 缺失字段"""
        from src.utils import DataValidator

        data = {"name": "John", "age": 30}

        type_specs = {"name": str, "age": int, "email": str}

        invalid = DataValidator.validate_data_types(data, type_specs)
        # 缺失字段不应该被视为类型错误
        assert invalid == []


class TestTimeUtils:
    """时间处理工具测试"""

    def test_time_utils_now_utc(self):
        """测试获取当前UTC时间"""
        from src.utils import TimeUtils

        now = TimeUtils.now_utc()

        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

        # 验证时间是合理的（最近的时间）
        current_time = datetime.now(timezone.utc)
        time_diff = abs((current_time - now).total_seconds())
        assert time_diff < 5  # 应该在5秒内

    def test_time_utils_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        from src.utils import TimeUtils

        # 使用固定时间戳
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert isinstance(dt, datetime)
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1

    def test_time_utils_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        from src.utils import TimeUtils

        # 固定datetime
        dt = datetime(2021, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(timestamp, float)
        assert timestamp > 1609459200  # 2021-01-01 00:00:00 UTC

    def test_time_utils_format_datetime_default(self):
        """测试格式化日期时间 - 默认格式"""
        from src.utils import TimeUtils

        dt = datetime(2021, 12, 25, 15, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt)

        assert formatted == "2021-12-25 15:30:45"

    def test_time_utils_format_datetime_custom(self):
        """测试格式化日期时间 - 自定义格式"""
        from src.utils import TimeUtils

        dt = datetime(2021, 12, 25, 15, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(dt, "%Y/%m/%d %H:%M")

        assert formatted == "2021/12/25 15:30"

    def test_time_utils_parse_datetime_default(self):
        """测试解析日期时间 - 默认格式"""
        from src.utils import TimeUtils

        date_str = "2021-12-25 15:30:45"
        dt = TimeUtils.parse_datetime(date_str)

        assert isinstance(dt, datetime)
        assert dt.year == 2021
        assert dt.month == 12
        assert dt.day == 25
        assert dt.hour == 15
        assert dt.minute == 30
        assert dt.second == 45

    def test_time_utils_parse_datetime_custom(self):
        """测试解析日期时间 - 自定义格式"""
        from src.utils import TimeUtils

        date_str = "2021/12/25 15:30"
        dt = TimeUtils.parse_datetime(date_str, "%Y/%m/%d %H:%M")

        assert dt.year == 2021
        assert dt.month == 12
        assert dt.day == 25
        assert dt.hour == 15
        assert dt.minute == 30

    def test_time_utils_roundtrip_conversion(self):
        """测试往返转换一致性"""
        from src.utils import TimeUtils

        # datetime -> timestamp -> datetime
        original_dt = datetime(2021, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(original_dt)
        converted_dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert original_dt == converted_dt

        # datetime -> string -> datetime
        original_dt = datetime(2021, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        formatted = TimeUtils.format_datetime(original_dt)
        parsed_dt = TimeUtils.parse_datetime(formatted)

        # 注意：解析的datetime没有时区信息，但时间部分应该匹配
        assert parsed_dt.year == original_dt.year
        assert parsed_dt.month == original_dt.month
        assert parsed_dt.day == original_dt.day
        assert parsed_dt.hour == original_dt.hour
        assert parsed_dt.minute == original_dt.minute
        assert parsed_dt.second == original_dt.second


class TestCryptoUtils:
    """加密工具测试"""

    def test_crypto_utils_generate_uuid(self):
        """测试生成UUID"""
        from src.utils import CryptoUtils

        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        # 验证格式
        assert isinstance(uuid1, str)
        assert len(uuid1) == 36
        assert uuid1.count("-") == 4

        # 验证唯一性
        assert uuid1 != uuid2

        # 验证可以转换为UUID对象
        uuid.UUID(uuid1)  # 不应该抛出异常

    def test_crypto_utils_generate_short_id(self):
        """测试生成短ID"""
        from src.utils import CryptoUtils

        short_id1 = CryptoUtils.generate_short_id()
        short_id2 = CryptoUtils.generate_short_id()

        # 验证格式
        assert isinstance(short_id1, str)
        assert len(short_id1) == 8

        # 验证唯一性
        assert short_id1 != short_id2

        # 验证自定义长度
        custom_id = CryptoUtils.generate_short_id(12)
        assert len(custom_id) == 12

    def test_crypto_utils_hash_string_md5(self):
        """测试字符串哈希 - MD5"""
        from src.utils import CryptoUtils

        text = "Hello, World!"
        hash_value = CryptoUtils.hash_string(text, "md5")

        # 验证格式
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

        # 验证一致性
        hash_value2 = CryptoUtils.hash_string(text, "md5")
        assert hash_value == hash_value2

        # 验证与标准MD5一致
        expected_hash = hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
        assert hash_value == expected_hash

    def test_crypto_utils_hash_string_sha256(self):
        """测试字符串哈希 - SHA256"""
        from src.utils import CryptoUtils

        text = "Hello, World!"
        hash_value = CryptoUtils.hash_string(text, "sha256")

        # 验证格式
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

        # 验证与标准SHA256一致
        expected_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert hash_value == expected_hash

    def test_crypto_utils_hash_string_invalid_algorithm(self):
        """测试字符串哈希 - 无效算法"""
        from src.utils import CryptoUtils

        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string("test", "invalid_algorithm")

    def test_crypto_utils_hash_password_default_salt(self):
        """测试密码哈希 - 默认盐值"""
        from src.utils import CryptoUtils

        password = "my_secure_password"
        hashed = CryptoUtils.hash_password(password)

        # 验证格式
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256长度

        # 验证每次生成的哈希都不同（因为盐值不同）
        hashed2 = CryptoUtils.hash_password(password)
        assert hashed != hashed2

    def test_crypto_utils_hash_password_custom_salt(self):
        """测试密码哈希 - 自定义盐值"""
        from src.utils import CryptoUtils

        password = "my_secure_password"
        salt = "custom_salt"
        hashed = CryptoUtils.hash_password(password, salt)

        # 验证一致性
        hashed2 = CryptoUtils.hash_password(password, salt)
        assert hashed == hashed2

        # 验证与手动计算一致
        expected = hashlib.sha256(f"{password}{salt}".encode("utf-8")).hexdigest()
        assert hashed == expected


class TestStringUtils:
    """字符串处理工具测试"""

    def test_string_utils_truncate_no_truncation(self):
        """测试字符串截断 - 无需截断"""
        from src.utils import StringUtils

        text = "Short text"
        result = StringUtils.truncate(text, 20)

        assert result == "Short text"

    def test_string_utils_truncate_with_truncation(self):
        """测试字符串截断 - 需要截断"""
        from src.utils import StringUtils

        text = "This is a very long text that needs to be truncated"
        result = StringUtils.truncate(text, 20)

        assert result == "This is a very l..."

    def test_string_utils_truncate_custom_suffix(self):
        """测试字符串截断 - 自定义后缀"""
        from src.utils import StringUtils

        text = "This is a very long text that needs to be truncated"
        result = StringUtils.truncate(text, 20, suffix=" [more]")

        assert result == "This is a very [more]"

    def test_string_utils_slugify_basic(self):
        """测试转换为URL友好字符串 - 基本"""
        from src.utils import StringUtils

        text = "Hello World! This is a Test"
        result = StringUtils.slugify(text)

        assert result == "hello-world-this-is-a-test"

    def test_string_utils_slugify_special_chars(self):
        """测试转换为URL友好字符串 - 特殊字符"""
        from src.utils import StringUtils

        text = "Python & Django: A Great Combination!"
        result = StringUtils.slugify(text)

        assert result == "python-django-a-great-combination"

    def test_string_utils_slugify_multiple_spaces(self):
        """测试转换为URL友好字符串 - 多个空格"""
        from src.utils import StringUtils

        text = "Multiple    spaces   and   dashes"
        result = StringUtils.slugify(text)

        assert result == "multiple-spaces-and-dashes"

    def test_string_utils_camel_to_snake_basic(self):
        """测试驼峰转下划线 - 基本"""
        from src.utils import StringUtils

        cases = [
            ("camelCase", "camel_case"),
            ("PascalCase", "pascal_case"),
            ("simpleXMLParser", "simple_x_m_l_parser"),
            ("HTTPRequest", "http_request"),
        ]

        for camel, expected_snake in cases:
            result = StringUtils.camel_to_snake(camel)
            assert result == expected_snake

    def test_string_utils_snake_to_camel_basic(self):
        """测试下划线转驼峰 - 基本"""
        from src.utils import StringUtils

        cases = [
            ("snake_case", "snakeCase"),
            ("camel_case", "camelCase"),
            ("http_request", "httpRequest"),
            ("simple_x_m_l_parser", "simpleXMLParser"),
        ]

        for snake, expected_camel in cases:
            result = StringUtils.snake_to_camel(snake)
            assert result == expected_camel

    def test_string_utils_clean_text_basic(self):
        """测试清理文本 - 基本"""
        from src.utils import StringUtils

        text = "  This   has   multiple   spaces  "
        result = StringUtils.clean_text(text)

        assert result == "This has multiple spaces"

    def test_string_utils_clean_text_newlines(self):
        """测试清理文本 - 换行符"""
        from src.utils import StringUtils

        text = "Line 1\n\nLine 2\r\n\r\nLine 3"
        result = StringUtils.clean_text(text)

        assert result == "Line 1 Line 2 Line 3"

    def test_string_utils_extract_numbers_basic(self):
        """测试提取数字 - 基本"""
        from src.utils import StringUtils

        text = "The price is $123.45 and the tax is 12.50"
        numbers = StringUtils.extract_numbers(text)

        assert numbers == [123.45, 12.50]

    def test_string_utils_extract_numbers_integers(self):
        """测试提取数字 - 整数"""
        from src.utils import StringUtils

        text = "There are 5 apples, 10 oranges, and -3 bananas"
        numbers = StringUtils.extract_numbers(text)

        assert numbers == [5.0, 10.0, -3.0]

    def test_string_utils_extract_numbers_no_numbers(self):
        """测试提取数字 - 无数字"""
        from src.utils import StringUtils

        text = "No numbers here"
        numbers = StringUtils.extract_numbers(text)

        assert numbers == []


class TestDictUtils:
    """字典处理工具测试"""

    def test_dict_utils_deep_merge_simple(self):
        """测试深度合并字典 - 简单情况"""
        from src.utils import DictUtils

        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

    def test_dict_utils_deep_merge_override(self):
        """测试深度合并字典 - 覆盖值"""
        from src.utils import DictUtils

        dict1 = {"a": 1, "b": 2, "c": 3}
        dict2 = {"b": 20, "d": 4}

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": 1, "b": 20, "c": 3, "d": 4}
        assert result == expected

    def test_dict_utils_deep_merge_nested(self):
        """测试深度合并字典 - 嵌套字典"""
        from src.utils import DictUtils

        dict1 = {
            "config": {
                "database": "postgres",
                "host": "localhost",
                "options": {"timeout": 30},
            },
            "version": "1.0",
        }

        dict2 = {
            "config": {"port": 5432, "options": {"max_connections": 100}},
            "environment": "production",
        }

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "config": {
                "database": "postgres",
                "host": "localhost",
                "port": 5432,
                "options": {"timeout": 30, "max_connections": 100},
            },
            "version": "1.0",
            "environment": "production",
        }

        assert result == expected

    def test_dict_utils_deep_merge_original_not_modified(self):
        """测试深度合并字典 - 原字典不被修改"""
        from src.utils import DictUtils

        dict1 = {"a": 1, "b": {"nested": 1}}
        dict2 = {"b": {"nested": 2}, "c": 3}

        dict1_copy = dict1.copy()
        dict1_copy["b"] = dict1["b"].copy()

        result = DictUtils.deep_merge(dict1, dict2)

        # 验证原字典未被修改
        assert dict1 == dict1_copy

    def test_dict_utils_flatten_dict_simple(self):
        """测试扁平化字典 - 简单情况"""
        from src.utils import DictUtils

        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.flatten_dict(d)

        assert result == {"a": 1, "b": 2, "c": 3}

    def test_dict_utils_flatten_dict_nested(self):
        """测试扁平化字典 - 嵌套字典"""
        from src.utils import DictUtils

        d = {
            "config": {
                "database": {"host": "localhost", "port": 5432},
                "cache": {"redis": {"host": "redis-server"}},
            },
            "version": "1.0",
        }

        result = DictUtils.flatten_dict(d)

        expected = {
            "config.database.host": "localhost",
            "config.database.port": 5432,
            "config.cache.redis.host": "redis-server",
            "version": "1.0",
        }

        assert result == expected

    def test_dict_utils_flatten_dict_custom_separator(self):
        """测试扁平化字典 - 自定义分隔符"""
        from src.utils import DictUtils

        d = {"a": {"b": {"c": 1}}}
        result = DictUtils.flatten_dict(d, sep="_")

        assert result == {"a_b_c": 1}

    def test_dict_utils_filter_none_values(self):
        """测试过滤None值"""
        from src.utils import DictUtils

        d = {
            "name": "John",
            "email": None,
            "age": 30,
            "address": None,
            "phone": "123-456-7890",
        }

        result = DictUtils.filter_none_values(d)

        expected = {"name": "John", "age": 30, "phone": "123-456-7890"}

        assert result == expected

    def test_dict_utils_filter_none_values_empty_dict(self):
        """测试过滤None值 - 空字典"""
        from src.utils import DictUtils

        d = {}
        result = DictUtils.filter_none_values(d)

        assert result == {}

    def test_dict_utils_filter_none_values_all_none(self):
        """测试过滤None值 - 全部为None"""
        from src.utils import DictUtils

        d = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(d)

        assert result == {}


class TestUtilsIntegration:
    """工具函数集成测试"""

    def test_utils_file_and_crypto_integration(self):
        """测试文件和加密工具集成"""
        from src.utils import FileUtils, CryptoUtils

        test_data = {"secret": "important_data", "timestamp": time.time()}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            # 写入数据
            FileUtils.write_json(test_data, temp_file)

            # 获取文件哈希
            file_hash = FileUtils.get_file_hash(temp_file)

            # 验证文件大小
            file_size = FileUtils.get_file_size(temp_file)

            # 验证一致性
            assert file_hash is not None
            assert file_size > 0

            # 读取并验证数据
            loaded_data = FileUtils.read_json(temp_file)
            assert loaded_data == test_data

        finally:
            os.unlink(temp_file)

    def test_utils_validation_and_string_integration(self):
        """测试验证和字符串工具集成"""
        from src.utils import DataValidator, StringUtils

        # 测试数据
        user_data = {
            "name": "  John Doe  ",
            "email": "JOHN.DOE@EXAMPLE.COM",
            "age": "30",  # 字符串形式的数字
            "bio": "This is a user biography with   extra   spaces.",
        }

        # 清理和标准化数据
        cleaned_data = {
            "name": StringUtils.clean_text(user_data["name"]),
            "email": user_data["email"].lower(),
            "bio": StringUtils.clean_text(user_data["bio"]),
        }

        # 验证邮箱
        is_valid_email = DataValidator.is_valid_email(cleaned_data["email"])

        # 提取年龄中的数字
        age_numbers = StringUtils.extract_numbers(user_data["age"])

        assert cleaned_data["name"] == "John Doe"
        assert cleaned_data["email"] == "john.doe@example.com"
        assert cleaned_data["bio"] == "This is a user biography with extra spaces."
        assert is_valid_email is True
        assert age_numbers == [30.0]

    def test_utils_time_and_dict_integration(self):
        """测试时间和字典工具集成"""
        from src.utils import TimeUtils, DictUtils

        # 创建带有时间戳的数据
        base_data = {
            "created_at": TimeUtils.now_utc(),
            "metadata": {"version": "1.0", "author": "system"},
        }

        # 转换为扁平字典用于存储
        flat_data = DictUtils.flatten_dict(base_data)

        # 转换时间戳为字符串
        flat_data["created_at"] = TimeUtils.format_datetime(flat_data["created_at"], "%Y-%m-%d %H:%M:%S")

        # 验证扁平化结果
        assert "created_at" in flat_data
        assert "metadata.version" in flat_data
        assert "metadata.author" in flat_data

        # 验证时间格式
        time_str = flat_data["created_at"]
        parsed_time = TimeUtils.parse_datetime(time_str)
        assert parsed_time.year == base_data["created_at"].year

    def test_utils_crypto_and_string_integration(self):
        """测试加密和字符串工具集成"""
        from src.utils import CryptoUtils, StringUtils

        # 生成用户友好的ID
        user_id = CryptoUtils.generate_short_id(10)
        username = "test_user_example"
        slug = StringUtils.slugify(username)

        # 创建组合标识符
        combined_id = f"{slug}_{user_id}"

        # 生成哈希用于验证
        verification_hash = CryptoUtils.hash_string(combined_id, "md5")

        # 验证各部分
        assert len(user_id) == 10
        assert slug == "test-user-example"
        assert combined_id.startswith("test-user-example_")
        assert len(verification_hash) == 32

        # 验证哈希一致性
        hash2 = CryptoUtils.hash_string(combined_id, "md5")
        assert verification_hash == hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
