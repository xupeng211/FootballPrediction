"""
核心工具类单元测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import time

from src.utils.string_utils import StringUtils
from src.utils.time_utils import TimeUtils
from src.utils.dict_utils import DictUtils
from src.utils.file_utils import FileUtils
from src.utils.crypto_utils import CryptoUtils
from src.utils.data_validator import DataValidator


class TestStringUtils:
    """字符串工具测试"""

    def test_snake_to_camel(self):
        """测试蛇形转驼峰"""
        assert StringUtils.snake_to_camel("hello_world") == "HelloWorld"
        assert StringUtils.snake_to_camel("test_string_case") == "TestStringCase"
        assert StringUtils.snake_to_camel("") == ""

    def test_camel_to_snake(self):
        """测试驼峰转蛇形"""
        assert StringUtils.camel_to_snake("HelloWorld") == "hello_world"
        assert StringUtils.camel_to_snake("TestStringCase") == "test_string_case"
        assert StringUtils.camel_to_snake("") == ""

    def test_pluralize(self):
        """测试复数化"""
        assert StringUtils.pluralize("match") == "matches"
        assert StringUtils.pluralize("team") == "teams"
        assert StringUtils.pluralize("class") == "classes"

    def test_slugify(self):
        """测试生成slug"""
        assert StringUtils.slugify("Hello World!") == "hello-world"
        assert StringUtils.slugify("Test & Example") == "test-example"
        assert StringUtils.slugify("  spaces  ") == "spaces"

    def test_is_empty(self):
        """测试是否为空"""
        assert StringUtils.is_empty("") is True
        assert StringUtils.is_empty("   ") is True
        assert StringUtils.is_empty("test") is False
        assert StringUtils.is_empty(None) is True


class TestTimeUtils:
    """时间工具测试"""

    def test_format_duration(self):
        """测试格式化时长"""
        assert TimeUtils.format_duration(60) == "1分0秒"
        assert TimeUtils.format_duration(3661) == "1时1分1秒"
        assert TimeUtils.format_duration(0) == "0秒"

    def test_get_timestamp(self):
        """测试获取时间戳"""
        ts = TimeUtils.get_timestamp()
        assert isinstance(ts, float)
        assert ts > 0

    def test_parse_datetime(self):
        """测试解析日期时间"""
        dt = TimeUtils.parse_datetime("2024-01-01 12:00:00")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

    def test_is_future(self):
        """测试是否为未来时间"""
        future = datetime.now() + timedelta(days=1)
        past = datetime.now() - timedelta(days=1)
        assert TimeUtils.is_future(future) is True
        assert TimeUtils.is_future(past) is False

    def test_time_ago(self):
        """测试计算时间差"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        assert TimeUtils.time_ago(one_hour_ago) == "1小时前"
        assert TimeUtils.time_ago(one_day_ago) == "1天前"


class TestDictUtils:
    """字典工具测试"""

    def test_get_nested_value(self):
        """测试获取嵌套值"""
        data = {"a": {"b": {"c": "value"}}}
        assert DictUtils.get_nested_value(data, "a.b.c") == "value"
        assert DictUtils.get_nested_value(data, "a.b.x", "default") == "default"

    def test_set_nested_value(self):
        """测试设置嵌套值"""
        data = {}
        DictUtils.set_nested_value(data, "a.b.c", "value")
        assert data == {"a": {"b": {"c": "value"}}}

    def test_flatten_dict(self):
        """测试扁平化字典"""
        data = {"a": {"b": {"c": 1}}, "d": 2}
        result = DictUtils.flatten_dict(data)
        assert result == {"a.b.c": 1, "d": 2}

    def test_filter_dict(self):
        """测试过滤字典"""
        data = {"a": 1, "b": 2, "c": None, "d": ""}
        result = DictUtils.filter_dict(data)
        assert result == {"a": 1, "b": 2}

    def test_merge_dicts(self):
        """测试合并字典"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.merge_dicts(dict1, dict2)
        assert result == {"a": 1, "b": 3, "c": 4}


class TestFileUtils:
    """文件工具测试"""

    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        assert FileUtils.get_file_extension("test.txt") == "txt"
        assert FileUtils.get_file_extension("test.tar.gz") == "gz"
        assert FileUtils.get_file_extension("test") == ""

    def test_is_text_file(self):
        """测试是否为文本文件"""
        assert FileUtils.is_text_file("test.txt") is True
        assert FileUtils.is_text_file("test.pdf") is False
        assert FileUtils.is_text_file("test.json") is True

    def test_format_file_size(self):
        """测试格式化文件大小"""
        assert FileUtils.format_file_size(1024) == "1.0 KB"
        assert FileUtils.format_file_size(1024 * 1024) == "1.0 MB"
        assert FileUtils.format_file_size(1) == "1.0 B"

    def test_generate_filename(self):
        """测试生成文件名"""
        with patch("time.time", return_value=1234567890):
            filename = FileUtils.generate_filename("test", "txt")
            assert "test" in filename
            assert filename.endswith(".txt")


class TestCryptoUtils:
    """加密工具测试"""

    def test_generate_salt(self):
        """测试生成盐值"""
        salt1 = CryptoUtils.generate_salt()
        salt2 = CryptoUtils.generate_salt()
        assert len(salt1) == 32
        assert len(salt2) == 32
        assert salt1 != salt2

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test123"
        salt = CryptoUtils.generate_salt()
        hashed = CryptoUtils.hash_password(password, salt)
        assert hashed != password
        assert len(hashed) == 64

    def test_verify_password(self):
        """测试验证密码"""
        password = "test123"
        salt = CryptoUtils.generate_salt()
        hashed = CryptoUtils.hash_password(password, salt)
        assert CryptoUtils.verify_password(password, salt, hashed) is True
        assert CryptoUtils.verify_password("wrong", salt, hashed) is False

    def test_generate_token(self):
        """测试生成令牌"""
        token1 = CryptoUtils.generate_token()
        token2 = CryptoUtils.generate_token()
        assert len(token1) == 32
        assert len(token2) == 32
        assert token1 != token2


class TestDataValidator:
    """数据验证器测试"""

    def test_validate_email(self):
        """测试验证邮箱"""
        assert DataValidator.validate_email("test@example.com") is True
        assert DataValidator.validate_email("invalid-email") is False
        assert DataValidator.validate_email("") is False

    def test_validate_phone(self):
        """测试验证手机号"""
        assert DataValidator.validate_phone("13800138000") is True
        assert DataValidator.validate_phone("12345678901") is False
        assert DataValidator.validate_phone("12345") is False

    def test_validate_url(self):
        """测试验证URL"""
        assert DataValidator.validate_url("https://example.com") is True
        assert DataValidator.validate_url("http://localhost:8000") is True
        assert DataValidator.validate_url("invalid-url") is False

    def test_validate_username(self):
        """测试验证用户名"""
        assert DataValidator.validate_username("testuser") is True
        assert DataValidator.validate_username("test_user123") is True
        assert DataValidator.validate_username("123") is False
        assert DataValidator.validate_username("") is False

    def test_validate_strength(self):
        """测试验证密码强度"""
        assert DataValidator.validate_strength("weak") == "weak"
        assert DataValidator.validate_strength("StrongPass123!") == "strong"
        assert DataValidator.validate_strength("Medium123") == "medium"
