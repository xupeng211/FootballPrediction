#!/usr/bin/env python3
"""
简单Smoke测试
测试基础功能确保可以运行
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestSimpleSmoke:
    """简单冒烟测试"""

    def test_utils_imports(self):
        """测试utils模块导入"""
        # 测试验证器
        from src.utils.validators import (
            is_valid_email,
            is_valid_phone,
            is_valid_url,
            is_valid_username,
            is_valid_password,
        )

        # 基本测试
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("invalid") is False
        assert is_valid_phone("+1234567890") is True
        assert is_valid_url("https://example.com") is True

    def test_crypto_utils(self):
        """测试加密工具"""
        from src.utils.crypto_utils import generate_uuid

        uuid = generate_uuid()
        assert uuid is not None
        assert len(uuid) > 0

    def test_string_utils(self):
        """测试字符串工具"""
        from src.utils.string_utils import clean_string, truncate_string

        assert clean_string("  test  ") == "test"
        assert truncate_string("long string", 5) == "long..."

    def test_time_utils(self):
        """测试时间工具"""
        from src.utils.time_utils import format_timestamp

        result = format_timestamp(1234567890)
        assert result is not None

    def test_response_utils(self):
        """测试响应工具"""
        from src.utils.response import success_response, error_response

        success = success_response({"data": "test"})
        assert success["status"] == "success"

        error = error_response("Error message")
        assert error["status"] == "error"

    def test_dict_utils(self):
        """测试字典工具"""
        from src.utils.dict_utils import get_nested_dict, set_nested_dict

        data = {}
        set_nested_dict(data, ["a", "b"], "value")
        assert get_nested_dict(data, ["a", "b"]) == "value"

    def test_formatters(self):
        """测试格式化工具"""
        from src.utils.formatters import format_json, format_text

        # 测试JSON格式化
        data = {"key": "value"}
        result = format_json(data)
        assert "key" in result

        # 测试文本格式化
        text = format_text("test")
        assert text is not None

    def test_warning_filters(self):
        """测试警告过滤器"""
        import warnings
        from src.utils.warning_filters import setup_warning_filters

        # 设置警告过滤器
        setup_warning_filters()

        # 测试警告被过滤
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            warnings.warn("test warning", DeprecationWarning)
            # 警告应该被过滤
