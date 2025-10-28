#!/usr/bin/env python3
"""
辅助函数测试
测试 src.utils.helpers 模块的功能
"""

from datetime import datetime

import pytest

from src.utils.helpers import (
    format_timestamp,
    generate_hash,
    generate_uuid,
    safe_get,
    sanitize_string,
)


@pytest.mark.unit
class TestHelpers:
    """辅助函数测试"""

    def test_generate_uuid(self):
        """测试UUID生成"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        # 验证返回的是字符串
        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)

        # 验证UUID长度（标准UUID长度为36字符）
        assert len(uuid1) == 36
        assert len(uuid2) == 36

        # 验证每次生成的UUID都不同
        assert uuid1 != uuid2

        # 验证UUID格式（包含连字符）
        assert "-" in uuid1
        assert "-" in uuid2

    def test_generate_hash(self):
        """测试哈希生成"""
        # 测试相同输入产生相同哈希
        hash1 = generate_hash("test_string")
        hash2 = generate_hash("test_string")
        assert hash1 == hash2

        # 测试不同输入产生不同哈希
        hash3 = generate_hash("different_string")
        assert hash1 != hash3

        # 验证哈希长度（SHA256为64字符）
        assert len(hash1) == 64
        assert len(hash3) == 64

        # 验证哈希格式（十六进制）
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_safe_get_with_dict(self):
        """测试从字典中安全获取值"""
        data = {"key1": "value1", "key2": 123}

        # 测试存在的键
        assert safe_get(data, "key1") == "value1"
        assert safe_get(data, "key2") == 123

        # 测试不存在的键
        assert safe_get(data, "nonexistent") is None
        assert safe_get(data, "nonexistent", "default") == "default"

    def test_safe_get_with_none(self):
        """测试None输入的安全获取"""
        assert safe_get(None, "any_key") is None
        assert safe_get(None, "any_key", "default") == "default"

    def test_safe_get_with_empty_dict(self):
        """测试空字典的安全获取"""
        assert safe_get({}, "any_key") is None
        assert safe_get({}, "any_key", "default") == "default"

    def test_format_timestamp_default(self):
        """测试默认时间戳格式化"""
        result = format_timestamp()

        # 验证返回的是字符串
        assert isinstance(result, str)

        # 验证ISO格式（包含T和秒）
        assert "T" in result
        assert ":" in result

    def test_format_timestamp_custom(self):
        """测试自定义时间戳格式化"""
        dt = datetime(2024, 1, 1, 12, 30, 45)
        result = format_timestamp(dt)

        # 验证格式
        assert isinstance(result, str)
        assert "2024-01-01T12:30:45" in result

    def test_sanitize_string_normal(self):
        """测试普通字符串清理"""
        result = sanitize_string("  Hello World  ")
        assert result == "hello world"

    def test_sanitize_string_empty(self):
        """测试空字符串清理"""
        assert sanitize_string("") == ""
        assert sanitize_string("   ") == ""

    def test_sanitize_string_none(self):
        """测试None输入清理"""
        assert sanitize_string(None) == ""

    def test_sanitize_string_with_special_chars(self):
        """测试包含特殊字符的字符串清理"""
        result = sanitize_string("  Test@#%$String  ")
        assert result == "test@#%$string"

    def test_generate_hash_consistency(self):
        """测试哈希生成的一致性"""
        test_string = "consistency_test"

        # 多次生成应该产生相同结果
        hash1 = generate_hash(test_string)
        hash2 = generate_hash(test_string)
        hash3 = generate_hash(test_string)

        assert hash1 == hash2 == hash3

    def test_safe_get_nested_data(self):
        """测试嵌套数据的安全获取"""
        data = {"config": {"setting": "value"}}

        # 只能获取第一层的值
        assert safe_get(data, "config") == {"setting": "value"}
        assert safe_get(data, "nonexistent_nested") is None
