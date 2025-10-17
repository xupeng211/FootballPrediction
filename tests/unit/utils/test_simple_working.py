"""
简单的测试文件，用于增加覆盖率
测试一些基本的工具函数
"""

import pytest
from datetime import datetime, timedelta


def test_imports():
    """测试模块导入"""
    from src.utils import time_utils, file_utils, helpers

    assert time_utils is not None
    assert file_utils is not None
    assert helpers is not None


def test_time_utils_basic():
    """测试时间工具基本功能"""
    from src.utils.time_utils import format_duration, is_valid_timestamp

    # 测试持续时间格式化
    assert format_duration(3600) == "1h 0m"
    assert format_duration(90) == "1m 30s"
    assert format_duration(45) == "45s"

    # 测试时间戳验证
    now = datetime.now()
    assert is_valid_timestamp(now.timestamp()) is True
    assert is_valid_timestamp(-1) is False


def test_file_utils_basic():
    """测试文件工具基本功能"""
    from src.utils.file_utils import ensure_dir, get_file_size
    from pathlib import Path

    # 测试目录创建
    test_dir = Path("/tmp/test_football_prediction")
    if test_dir.exists():
        test_dir.rmdir()

    ensure_dir(test_dir)
    assert test_dir.exists()

    # 清理
    if test_dir.exists():
        test_dir.rmdir()


def test_helpers_basic():
    """测试辅助函数基本功能"""
    from src.utils.helpers import generate_uuid, sanitize_filename

    # 测试 UUID 生成
    uuid1 = generate_uuid()
    uuid2 = generate_uuid()
    assert uuid1 != uuid2
    assert len(uuid1) == 36  # 标准UUID长度

    # 测试文件名清理
    assert sanitize_filename("test file.txt") == "test_file.txt"
    assert sanitize_filename("test/file\\name.txt") == "test_filename.txt"


def test_dict_utils_simple():
    """测试字典工具简单功能"""
    from src.utils.dict_utils import flatten_dict, merge_dicts

    # 测试字典扁平化
    nested = {"a": {"b": {"c": 1}}, "x": 2}
    flat = flatten_dict(nested)
    assert "a.b.c" in flat
    assert flat["a.b.c"] == 1
    assert flat["x"] == 2

    # 测试字典合并
    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 3, "c": 4}
    merged = merge_dicts(dict1, dict2)
    assert merged["a"] == 1
    assert merged["b"] == 3
    assert merged["c"] == 4


def test_data_validator_simple():
    """测试数据验证器简单功能"""
    from src.utils.data_validator import validate_email, validate_phone

    # 测试邮箱验证
    assert validate_email("test@example.com") is True
    assert validate_email("invalid-email") is False
    assert validate_email("") is False

    # 测试电话验证
    assert validate_phone("123-456-7890") is True
    assert validate_phone("1234567890") is True
    assert validate_phone("abc") is False


def test_crypto_utils_simple():
    """测试加密工具简单功能"""
    from src.utils.crypto_utils import hash_password, verify_password

    # 测试密码哈希
    password = "test_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 50  # 哈希后应该更长

    # 测试密码验证
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_formatters_simple():
    """测试格式化工具简单功能"""
    from src.utils.formatters import format_currency, format_percentage

    # 测试货币格式化
    assert format_currency(1234.56) == "$1,234.56"
    assert format_currency(0) == "$0.00"

    # 测试百分比格式化
    assert format_percentage(0.1234) == "12.34%"
    assert format_percentage(1) == "100.00%"


def test_edge_cases():
    """测试边界情况"""
    from src.utils.helpers import safe_int, safe_float

    # 测试安全转换
    assert safe_int("123") == 123
    assert safe_int("abc") == 0
    assert safe_int(None) == 0

    assert safe_float("123.45") == 123.45
    assert safe_float("abc") == 0.0
    assert safe_float(None) == 0.0
