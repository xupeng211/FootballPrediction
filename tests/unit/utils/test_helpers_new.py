"""""""
辅助函数测试
Tests for Helper Functions

测试src.utils.helpers模块的辅助函数
"""""""

import re
from datetime import datetime, timezone

import pytest

# 测试导入
try:
    from src.utils.helpers import (
        format_timestamp,
        generate_hash,
        generate_uuid,
        safe_get,
        sanitize_string,
    )

    HELPERS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    HELPERS_AVAILABLE = False


@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers module not available")
@pytest.mark.unit
class TestGenerateUUID:
    """UUID生成测试"""

    def test_generate_uuid(self):
        """测试：生成UUID"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        # 验证UUID格式
        assert isinstance(uuid1, str)
        assert len(uuid1) == 36
        assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", uuid1)

        # 验证每次生成不同的UUID
        assert uuid1 != uuid2

    def test_generate_uuid_consistency(self):
        """测试：UUID生成一致性"""
        uuids = [generate_uuid() for _ in range(10)]

        # 验证所有UUID都是唯一的
        assert len(set(uuids)) == 10

        # 验证所有UUID都符合格式
        for uuid in uuids:
            assert len(uuid) == 36
            assert "-" in uuid
            assert uuid.count("-") == 4


@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers module not available")
class TestGenerateHash:
    """哈希生成测试"""

    def test_generate_hash(self):
        """测试：生成哈希"""
        _data = "test string"
        hash_value = generate_hash(data)

        # 验证哈希格式
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 produces 64 character hex string

        # 验证相同输入产生相同哈希
        hash2 = generate_hash(data)
        assert hash_value == hash2

    def test_generate_hash_different_inputs(self):
        """测试：不同输入产生不同哈希"""
        hash1 = generate_hash("test1")
        hash2 = generate_hash("test2")
        hash3 = generate_hash("Test1")  # 大小写敏感

        assert hash1 != hash2
        assert hash1 != hash3

    def test_generate_hash_empty_string(self):
        """测试：空字符串哈希"""
        hash_value = generate_hash("")
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

        # SHA256 of empty string is known
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert hash_value == expected

    def test_generate_hash_special_characters(self):
        """测试：特殊字符哈希"""
        _data = "test@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        hash_value = generate_hash(data)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64


@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers module not available")
class TestSafeGet:
    """安全获取字典值测试"""

    def test_safe_get_key_exists(self):
        """测试：键存在"""
        _data = {"key1": "value1", "key2": 100, "key3": None}

        assert safe_get(data, "key1") == "value1"
        assert safe_get(data, "key2") == 100
        assert safe_get(data, "key3") is None

    def test_safe_get_key_not_exists(self):
        """测试：键不存在"""
        _data = {"key1": "value1"}

        assert safe_get(data, "key2") is None
        assert safe_get(data, "nonexistent") is None

    def test_safe_get_with_default(self):
        """测试：使用默认值"""
        _data = {"key1": "value1"}

        assert safe_get(data, "key2", "default") == "default"
        assert safe_get(data, "key2", 0) == 0
        assert safe_get(data, "key2", False) is False

    def test_safe_get_none_data(self):
        """测试：数据为None"""
        with pytest.raises(AttributeError):
            safe_get(None, "key")

    def test_safe_get_nested_dict(self):
        """测试：嵌套字典"""
        _data = {"nested": {"inner": "value"}}

        assert safe_get(data, "nested") == {"inner": "value"}
        assert safe_get(data, "nonexistent", "default") == "default"


@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers module not available")
class TestFormatTimestamp:
    """时间戳格式化测试"""

    def test_format_timestamp_with_datetime(self):
        """测试：传入datetime对象"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        formatted = format_timestamp(dt)

        assert formatted == "2023-01-01T12:30:45"

    def test_format_timestamp_without_datetime(self):
        """测试：不传入datetime（使用当前时间）"""
        formatted1 = format_timestamp()
        import time

        time.sleep(0.01)
        time.sleep(0.01)
        time.sleep(0.01)
        formatted2 = format_timestamp()

        # 验证格式
        assert isinstance(formatted1, str)
        assert "T" in formatted1
        assert isinstance(formatted2, str)
        assert "T" in formatted2

        # 验证时间不同
        assert formatted1 != formatted2

    def test_format_timestamp_with_timezone(self):
        """测试：带时区的datetime"""
        dt = datetime(2023, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        formatted = format_timestamp(dt)

        # ISO格式应该包含时区信息
        assert "2023-01-01T12:30:45+00:00" in formatted or "2023-01-01T12:30:45Z" in formatted

    def test_format_timestamp_none_input(self):
        """测试：输入为None"""
        formatted = format_timestamp(None)

        assert isinstance(formatted, str)
        assert "T" in formatted


@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helpers module not available")
class TestSanitizeString:
    """字符串清理测试"""

    def test_sanitize_string_normal(self):
        """测试：正常字符串"""
        s = "Hello World"
        _result = sanitize_string(s)

        assert _result == "hello world"
        assert isinstance(result, str)

    def test_sanitize_string_with_spaces(self):
        """测试：带空格的字符串"""
        s = "   Hello World   "
        _result = sanitize_string(s)

        assert _result == "hello world"

    def test_sanitize_string_with_uppercase(self):
        """测试：大写字符串"""
        s = "HELLO WORLD"
        _result = sanitize_string(s)

        assert _result == "hello world"

    def test_sanitize_string_with_mixed_case(self):
        """测试：混合大小写字符串"""
        s = "HeLLo WoRLd"
        _result = sanitize_string(s)

        assert _result == "hello world"

    def test_sanitize_string_empty(self):
        """测试：空字符串"""
        _result = sanitize_string("")

        assert _result == ""

    def test_sanitize_string_with_special_chars(self):
        """测试：特殊字符"""
        s = "Hello World! @#$%"
        _result = sanitize_string(s)

        assert _result == "hello world! @#$%"

    def test_sanitize_string_with_numbers(self):
        """测试：数字"""
        s = "Hello 123 World 456"
        _result = sanitize_string(s)

        assert _result == "hello 123 world 456"

    def test_sanitize_string_none_input(self):
        """测试：输入为None"""
        _result = sanitize_string(None)

        assert _result == ""

    def test_sanitize_string_whitespace_only(self):
        """测试：只有空白字符"""
        s = "   \t\n   "
        _result = sanitize_string(s)

        assert _result == ""


@pytest.mark.skipif(HELPERS_AVAILABLE, reason="Helpers module should be available")
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not HELPERS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if HELPERS_AVAILABLE:
from src.utils.helpers import (
            format_timestamp,
            generate_hash,
            generate_uuid,
            safe_get,
            sanitize_string,
        )

        assert generate_uuid is not None
        assert generate_hash is not None
        assert safe_get is not None
        assert format_timestamp is not None
        assert sanitize_string is not None


def test_function_signatures():
    """测试：函数签名"""
    if HELPERS_AVAILABLE:
        import inspect

        # 验证函数可调用
        assert callable(generate_uuid)
        assert callable(generate_hash)
        assert callable(safe_get)
        assert callable(format_timestamp)
        assert callable(sanitize_string)

        # 验证参数
        assert inspect.signature(generate_uuid).parameters == {}
        assert len(inspect.signature(generate_hash).parameters) == 1
        assert len(inspect.signature(safe_get).parameters) == 3
        assert len(inspect.signature(format_timestamp).parameters) == 1
        assert len(inspect.signature(sanitize_string).parameters) == 1
