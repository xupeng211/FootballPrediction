#!/usr/bin/env python3
"""
Utils模块smoke测试
测试工具模块是否可以正常导入和初始化
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestUtilsSmoke:
    """Utils模块冒烟测试"""

    def test_crypto_utils(self):
        """测试加密工具"""
        from src.utils.crypto_utils import (
            generate_secure_token,
            hash_password,
            verify_password,
        )

        token = generate_secure_token()
        assert token is not None
        assert len(token) > 0

        password = "test_password"
        hashed = hash_password(password)
        assert hashed is not None
        assert verify_password(password, hashed) is True

    def test_dict_utils(self):
        """测试字典工具"""
        from src.utils.dict_utils import get_nested_dict, set_nested_dict, flatten_dict

        # 测试嵌套字典
        data = {"a": {"b": {"c": 1}}}
        value = get_nested_dict(data, ["a", "b", "c"])
        assert value == 1

        # 测试扁平化
        flat = flatten_dict(data)
        assert "a.b.c" in flat
        assert flat["a.b.c"] == 1

    def test_string_utils(self):
        """测试字符串工具"""
        from src.utils.string_utils import clean_string, truncate_string, is_empty

        assert clean_string("  test  ") == "test"
        assert truncate_string("long string", 5) == "long..."
        assert is_empty("") is True
        assert is_empty("test") is False

    def test_time_utils(self):
        """测试时间工具"""
        from src.utils.time_utils import format_datetime, parse_datetime, get_timestamp

        timestamp = get_timestamp()
        assert timestamp is not None

        formatted = format_datetime(timestamp)
        assert formatted is not None

    def test_validators(self):
        """测试验证器"""
        from src.utils.validators import is_valid_email, is_valid_phone, is_valid_url

        assert is_valid_email("test@example.com") is True
        assert is_valid_email("invalid") is False

        assert is_valid_url("https://example.com") is True
        assert is_valid_url("not-a-url") is False

    def test_formatters(self):
        """测试格式化工具"""
        from src.utils.formatters import (
            format_currency,
            format_percentage,
            format_number,
        )

        assert format_currency(1000) == "$1,000.00"
        assert format_percentage(0.5) == "50.00%"
        assert format_number(1000000) == "1,000,000"

    def test_response_utils(self):
        """测试响应工具"""
        from src.utils.response import (
            create_success_response,
            create_error_response,
            create_response,
        )

        success = create_success_response({"data": "test"})
        assert success["status"] == "success"

        error = create_error_response("Error message")
        assert error["status"] == "error"

    def test_file_utils(self):
        """测试文件工具"""
        from src.utils.file_utils import (
            get_file_extension,
            is_valid_filename,
            normalize_path,
        )

        assert get_file_extension("test.txt") == "txt"
        assert is_valid_filename("valid_name.txt") is True
        assert normalize_path("path//to//file") == "path/to/file"
