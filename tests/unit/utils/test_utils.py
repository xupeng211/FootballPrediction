import pytest

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

pytestmark = pytest.mark.unit

import pytest

from src.utils import (
    CryptoUtils,
    DataValidator,
    DictUtils,
    FileUtils,
    StringUtils,
    TimeUtils,
)


class TestFileUtils:
    """测试文件处理工具类"""

    def test_ensure_dir(self):
        """测试确保目录存在"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test" / "nested" / "dir"
            result = FileUtils.ensure_dir(test_path)
            assert result.exists()
            assert result.is_dir()

    def test_read_json_success(self):
        """测试读取JSON文件成功"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = {"key": "value", "number": 123}
            json.dump(test_data, f)
            f.flush()

            result = FileUtils.read_json(f.name)
            assert result == test_data

    def test_read_json_file_not_found(self):
        """测试读取不存在的JSON文件"""
        with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
            FileUtils.read_json("nonexistent_file.json")

    def test_read_json_invalid_format(self):
        """测试读取格式错误的JSON文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            f.flush()

            with pytest.raises(FileNotFoundError, match="无法读取JSON文件"):
                FileUtils.read_json(f.name)

    def test_write_json(self):
        """测试写入JSON文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {"测试": "数据", "数字": 42}
            file_path = Path(temp_dir) / "test.json"

            FileUtils.write_json(test_data, file_path)

            assert file_path.exists()
            with open(file_path, "r", encoding="utf-8") as f:
                result = json.load(f)
            assert result == test_data

    def test_write_json_ensure_dir(self):
        """测试写入JSON文件时自动创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {"key": "value"}
            file_path = Path(temp_dir) / "nested" / "dir" / "test.json"

            FileUtils.write_json(test_data, file_path, ensure_dir=True)

            assert file_path.exists()
            assert file_path.parent.exists()

    def test_get_file_hash(self):
        """测试获取文件哈希值"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            f.flush()

            hash_value = FileUtils.get_file_hash(f.name)
            assert isinstance(hash_value, str)
            assert len(hash_value) == 32  # MD5哈希长度

    def test_get_file_size(self):
        """测试获取文件大小"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_content = "test content"
            f.write(test_content)
            f.flush()

            size = FileUtils.get_file_size(f.name)
            assert size == len(test_content.encode("utf-8"))


class TestDataValidator:
    """测试数据验证工具类"""

    def test_is_valid_email_valid(self):
        """测试有效邮箱验证"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
        ]
        for email in valid_emails:
            assert DataValidator.is_valid_email(email)

    def test_is_valid_email_invalid(self):
        """测试无效邮箱验证"""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@@domain.com",
        ]
        for email in invalid_emails:
            assert not DataValidator.is_valid_email(email)

    def test_is_valid_url_valid(self):
        """测试有效URL验证"""
        valid_urls = [
            "http://example.com",
            "https://www.example.com",
            "http://localhost:8080",
            "https://192.168.1.1:3000/path",
        ]
        for url in valid_urls:
            assert DataValidator.is_valid_url(url)

    def test_is_valid_url_invalid(self):
        """测试无效URL验证"""
        invalid_urls = [
            "invalid-url",
            "ftp://example.com",
            "example.com",
            "http://",
        ]
        for url in invalid_urls:
            assert not DataValidator.is_valid_url(url)

    def test_validate_required_fields_all_present(self):
        """测试验证必需字段 - 全部存在"""
        data = {"name": "test", "age": 25, "email": "test@example.com"}
        required_fields = ["name", "age", "email"]

        missing = DataValidator.validate_required_fields(data, required_fields)
        assert missing == []

    def test_validate_required_fields_some_missing(self):
        """测试验证必需字段 - 部分缺失"""
        data = {"name": "test", "age": None}
        required_fields = ["name", "age", "email"]

        missing = DataValidator.validate_required_fields(data, required_fields)
        assert "email" in missing
        assert "age" in missing
        assert "name" not in missing

    def test_validate_data_types_all_correct(self):
        """测试验证数据类型 - 全部正确"""
        data = {"name": "test", "age": 25, "active": True}
        type_specs = {"name": str, "age": int, "active": bool}

        invalid = DataValidator.validate_data_types(data, type_specs)
        assert invalid == []

    def test_validate_data_types_some_incorrect(self):
        """测试验证数据类型 - 部分错误"""
        data = {"name": "test", "age": "25", "active": 1}
        type_specs = {"name": str, "age": int, "active": bool}

        invalid = DataValidator.validate_data_types(data, type_specs)
        assert len(invalid) == 2
        assert any("age" in error for error in invalid)
        assert any("active" in error for error in invalid)


class TestTimeUtils:
    """测试时间处理工具类"""

    def test_now_utc(self):
        """测试获取当前UTC时间"""
        now = TimeUtils.now_utc()
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
        dt = TimeUtils.timestamp_to_datetime(timestamp)

        assert isinstance(dt, datetime)
        assert dt.tzinfo == timezone.utc

    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2022, 1, 1, tzinfo=timezone.utc)
        timestamp = TimeUtils.datetime_to_timestamp(dt)

        assert isinstance(timestamp, float)
        assert timestamp == 1640995200.0

    def test_format_datetime(self):
        """测试格式化日期时间"""
        dt = datetime(2022, 1, 1, 12, 30, 45)

        # 默认格式
        formatted = TimeUtils.format_datetime(dt)
        assert formatted == "2022-01-01 12:30:45"

        # 自定义格式
        formatted_custom = TimeUtils.format_datetime(dt, "%Y/%m/%d")
        assert formatted_custom == "2022/01/01"

    def test_parse_datetime(self):
        """测试解析日期时间字符串"""
        date_str = "2022-01-01 12:30:45"
        dt = TimeUtils.parse_datetime(date_str)

        assert isinstance(dt, datetime)
        assert dt.year == 2022
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12


class TestCryptoUtils:
    """测试加密工具类"""

    def test_generate_uuid(self):
        """测试生成UUID"""
        uuid1 = CryptoUtils.generate_uuid()
        uuid2 = CryptoUtils.generate_uuid()

        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # UUID长度

    def test_generate_short_id(self):
        """测试生成短ID"""
        # 默认长度
        short_id = CryptoUtils.generate_short_id()
        assert isinstance(short_id, str)
        assert len(short_id) == 8

        # 自定义长度
        custom_id = CryptoUtils.generate_short_id(12)
        assert len(custom_id) == 12

    def test_hash_string_md5(self):
        """测试字符串MD5哈希"""
        text = "test string"
        hash_value = CryptoUtils.hash_string(text, "md5")

        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

    def test_hash_string_sha256(self):
        """测试字符串SHA256哈希"""
        text = "test string"
        hash_value = CryptoUtils.hash_string(text, "sha256")

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

    def test_hash_string_unsupported_algorithm(self):
        """测试不支持的哈希算法"""
        with pytest.raises(ValueError, match="不支持的哈希算法"):
            CryptoUtils.hash_string("test", "unsupported")

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password"

        # 不提供salt
        hash1 = CryptoUtils.hash_password(password)
        hash2 = CryptoUtils.hash_password(password)
        assert hash1 != hash2  # 由于随机salt，结果不同

        # 提供salt
        salt = "fixed_salt"
        hash3 = CryptoUtils.hash_password(password, salt)
        hash4 = CryptoUtils.hash_password(password, salt)
        assert CryptoUtils.verify_password(password, hash3)  # 验证密码
        assert CryptoUtils.verify_password(password, hash4)  # 验证密码


class TestStringUtils:
    """测试字符串处理工具类"""

    def test_truncate_short_string(self):
        """测试截断短字符串"""
        text = "short"
        result = StringUtils.truncate(text, 10)
        assert result == text

    def test_truncate_long_string(self):
        """测试截断长字符串"""
        text = "这是一个很长的字符串需要被截断"
        result = StringUtils.truncate(text, 10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_slugify(self):
        """测试转换为URL友好字符串"""
        text = "Hello World Test"
        result = StringUtils.slugify(text)
        assert result == "hello-world-test"

    def test_camel_to_snake(self):
        """测试驼峰命名转下划线命名"""
        cases = [
            ("CamelCase", "camel_case"),
            ("simpleTest", "simple_test"),
            ("HTTPSConnection", "https_connection"),
        ]
        for camel, expected_snake in cases:
            result = StringUtils.camel_to_snake(camel)
            assert result == expected_snake

    def test_snake_to_camel(self):
        """测试下划线命名转驼峰命名"""
        cases = [
            ("snake_case", "snakeCase"),
            ("simple_test", "simpleTest"),
            ("multi_word_test", "multiWordTest"),
        ]
        for snake, expected_camel in cases:
            result = StringUtils.snake_to_camel(snake)
            assert result == expected_camel

    def test_clean_text(self):
        """测试清理文本"""
        text = "  这是   一个\t测试\n文本  "
        result = StringUtils.clean_text(text)
        assert result == "这是 一个 测试 文本"

    def test_extract_numbers(self):
        """测试从文本中提取数字"""
        text = "价格是123.45元，数量-10个"
        numbers = StringUtils.extract_numbers(text)
        assert 123.45 in numbers
        assert -10.0 in numbers


class TestDictUtils:
    """测试字典处理工具类"""

    def test_deep_merge_simple(self):
        """测试简单字典深度合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}

        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

    def test_deep_merge_nested(self):
        """测试嵌套字典深度合并"""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 3, "z": 4}, "c": 5}

        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": {"x": 1, "y": 3, "z": 4}, "b": 3, "c": 5}
        assert result == expected

    def test_flatten_dict_simple(self):
        """测试扁平化简单字典"""
        d = {"a": 1, "b": 2}
        result = DictUtils.flatten_dict(d)
        assert result == d

    def test_flatten_dict_nested(self):
        """测试扁平化嵌套字典"""
        d = {"a": 1, "b": {"x": 2, "y": {"z": 3}}}

        result = DictUtils.flatten_dict(d)
        expected = {"a": 1, "b.x": 2, "b.y.z": 3}
        assert result == expected

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符的扁平化"""
        d = {"a": {"b": {"c": 1}}}
        result = DictUtils.flatten_dict(d, sep="_")
        expected = {"a_b_c": 1}
        assert result == expected

    def test_filter_none_values(self):
        """测试过滤None值"""
        d = {"a": 1, "b": None, "c": "test", "d": None}
        result = DictUtils.filter_none_values(d)
        expected = {"a": 1, "c": "test"}
        assert result == expected
