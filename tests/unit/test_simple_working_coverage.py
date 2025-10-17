#!/usr/bin/env python3
"""
简单有效覆盖率测试
只测试实际存在的功能
"""

import pytest
import sys
import warnings
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestSimpleWorkingCoverage:
    """简单有效覆盖率测试"""

    def test_warning_filters_basic(self):
        """测试警告过滤器基本功能"""
        from src.utils.warning_filters import setup_warning_filters

        # 设置过滤器
        setup_warning_filters()
        assert True  # 如果没有异常就算通过

    def test_formatters_json_format(self):
        """测试JSON格式化"""
        from src.utils.formatters import format_json

        # 测试基本JSON格式化
        data = {"key": "value", "number": 123}
        result = format_json(data)

        assert "key" in result
        assert "value" in result
        assert "number" in result
        assert "123" in result

    def test_formatters_text_format(self):
        """测试文本格式化"""
        from src.utils.formatters import format_text

        # 测试基本文本格式化
        text = "Hello, World!"
        result = format_text(text)

        assert result is not None
        assert "Hello" in result

    def test_string_utils_functions(self):
        """测试字符串工具函数"""
        from src.utils.string_utils import normalize_string, extract_numbers

        # 测试字符串标准化
        normalized = normalize_string("  Hello World  ")
        assert normalized == "hello world"

        # 测试提取数字
        numbers = extract_numbers("abc123def456")
        assert numbers == "123456"

    def test_time_utils_basic(self):
        """测试时间工具基本功能"""
        from src.utils.time_utils import format_timestamp

        # 测试时间戳格式化
        result = format_timestamp(1234567890)
        assert result is not None
        assert len(result) > 0

    def test_response_utils_basic(self):
        """测试响应工具基本功能"""
        from src.utils.response import create_response

        # 测试创建响应
        response = create_response("success", {"data": "test"})
        assert response["status"] == "success"
        assert response["data"]["data"] == "test"

    def test_validators_email(self):
        """测试邮箱验证器"""
        from src.utils.validators import is_valid_email

        # 测试有效邮箱
        assert is_valid_email("user@example.com") is True
        assert is_valid_email("test.email+tag@domain.co.uk") is True

        # 测试无效邮箱
        assert is_valid_email("invalid-email") is False
        assert is_valid_email("") is False
        assert is_valid_email("@domain.com") is False

    def test_validators_phone(self):
        """测试电话验证器"""
        from src.utils.validators import is_valid_phone

        # 测试有效电话
        assert is_valid_phone("+1-555-123-4567") is True
        assert is_valid_phone("+86 138 0013 8000") is True

        # 测试无效电话
        assert is_valid_phone("123") is False

    def test_validators_url(self):
        """测试URL验证器"""
        from src.utils.validators import is_valid_url

        # 测试有效URL
        assert is_valid_url("https://www.example.com") is True
        assert is_valid_url("http://localhost:8000") is True

        # 测试无效URL
        assert is_valid_url("not-a-url") is False
        assert is_valid_url("") is False

    def test_crypto_utils_hash(self):
        """测试加密工具哈希功能"""
        from src.utils.crypto_utils import hash_string, verify_hash

        # 测试哈希
        data = "test data"
        hashed = hash_string(data)
        assert hashed is not None
        assert hashed != data

        # 测试验证哈希
        assert verify_hash(data, hashed) is True
        assert verify_hash("wrong", hashed) is False

    def test_crypto_utils_token(self):
        """测试加密工具token生成"""
        from src.utils.crypto_utils import generate_token

        # 测试生成token
        token = generate_token()
        assert token is not None
        assert len(token) > 0

    def test_dict_utils_nested(self):
        """测试字典工具嵌套操作"""
        from src.utils.dict_utils import get_value, set_value

        # 测试设置和获取嵌套值
        data = {}
        set_value(data, "a.b.c", "value")
        assert get_value(data, "a.b.c") == "value"

        # 测试获取不存在的值
        assert get_value(data, "x.y.z", "default") == "default"

    def test_file_utils_basic(self):
        """测试文件工具基本功能"""
        from src.utils.file_utils import get_file_extension, is_valid_filename

        # 测试获取文件扩展名
        assert get_file_extension("test.txt") == "txt"
        assert get_file_extension("/path/to/file.json") == "json"

        # 测试文件名验证
        assert is_valid_filename("valid_name.txt") is True
        assert is_valid_filename("") is False
        assert is_valid_filename("invalid/name.txt") is False
