"""
测试实际存在的工具类
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path


def test_string_utils_class():
    """测试 StringUtils 类"""
    from src.utils.string_utils import StringUtils

    # 测试所有静态方法
    assert hasattr(StringUtils, "truncate")
    assert hasattr(StringUtils, "slugify")
    assert hasattr(StringUtils, "camel_to_snake")
    assert hasattr(StringUtils, "snake_to_camel")
    assert hasattr(StringUtils, "clean_text")
    assert hasattr(StringUtils, "extract_numbers")

    # 测试截断
    result = StringUtils.truncate("Hello World Test", 8)
    assert result == "Hello..."

    # 测试 URL 化
    result = StringUtils.slugify("Hello, World!")
    assert result == "hello-world"

    # 测试驼峰转下划线
    result = StringUtils.camel_to_snake("testFunctionName")
    assert result == "test_function_name"

    # 测试下划线转驼峰
    result = StringUtils.snake_to_camel("test_function_name")
    assert result == "testFunctionName"

    # 测试文本清理
    result = StringUtils.clean_text("  Hello    World  ")
    assert result == "Hello World"

    # 测试数字提取
    result = StringUtils.extract_numbers("Price: $10.99")
    assert result == [10.0, 99.0]


def test_crypto_utils_class():
    """测试 CryptoUtils 类"""
    from src.utils.crypto_utils import CryptoUtils

    # 测试密码哈希
    password = "test_password_123"
    hashed = CryptoUtils.hash_password(password)
    assert hashed != password
    assert len(hashed) > 50

    # 测试密码验证
    assert CryptoUtils.verify_password(password, hashed) is True
    assert CryptoUtils.verify_password("wrong_password", hashed) is False

    # 测试生成 UUID
    uuid_val = CryptoUtils.generate_uuid()
    assert isinstance(uuid_val, str)
    assert len(uuid_val) == 36

    # 测试生成令牌
    token = CryptoUtils.generate_token(16)
    assert isinstance(token, str)
    assert len(token) == 32  # hex 编码

    # 测试生成随机数
    random_num = CryptoUtils.generate_random_number(1000, 9999)
    assert 1000 <= random_num <= 9999


def test_dict_utils_class():
    """测试 DictUtils 类"""
    from src.utils.dict_utils import DictUtils

    # 测试嵌套值获取
    nested = {"a": {"b": {"c": 1}}, "x": 2}
    value = DictUtils.get_nested_value(nested, "a.b.c")
    assert value == 1
    assert DictUtils.get_nested_value(nested, "a.b.x", "default") == "default"

    # 测试嵌套值设置
    DictUtils.set_nested_value(nested, "a.b.d", 2)
    assert nested["a"]["b"]["d"] == 2

    # 测试过滤 None 值
    data = {"a": 1, "b": None, "c": 0, "d": False}
    filtered = DictUtils.filter_none_values(data)
    assert "b" not in filtered
    assert filtered == {"a": 1, "c": 0, "d": False}

    # 测试深度合并
    dict1 = {"a": 1, "b": {"x": 1}}
    dict2 = {"b": {"y": 2}, "c": 3}
    merged = DictUtils.deep_merge(dict1, dict2)
    assert merged["a"] == 1
    assert merged["b"]["x"] == 1
    assert merged["b"]["y"] == 2
    assert merged["c"] == 3

    # 测试选择键
    data = {"a": 1, "b": 2, "c": 3}
    picked = DictUtils.pick_keys(data, ["a", "c"])
    assert picked == {"a": 1, "c": 3}


def test_time_utils_class():
    """测试 TimeUtils 类"""
    from src.utils.time_utils import TimeUtils

    # 测试时间格式化
    now = datetime.now(timezone.utc)
    formatted = TimeUtils.format_datetime(now)
    assert isinstance(formatted, str)
    assert len(formatted) > 0

    # 测试时间解析
    time_str = "2024-01-15 10:30:00"
    parsed = TimeUtils.parse_datetime(time_str)
    assert parsed.year == 2024
    assert parsed.month == 1

    # 测试时间差计算
    start = datetime.now()
    end = start + timedelta(hours=2, minutes=30)
    diff = TimeUtils.get_time_difference(start, end)
    assert diff.total_seconds() == 2.5 * 3600

    # 测试时间判断
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    assert TimeUtils.is_future(future) is True
    assert TimeUtils.is_past(past) is True

    # 测试持续时间格式化
    duration = TimeUtils.format_duration(3665)
    assert "1h" in duration or "hour" in duration
    assert "1m" in duration or "minute" in duration


def test_file_utils_class():
    """测试 FileUtils 类"""
    from src.utils.file_utils import FileUtils

    # 测试安全文件名
    unsafe = "test/file\\name.txt"
    safe = FileUtils.safe_filename(unsafe)
    assert "/" not in safe
    assert "\\" not in safe
    assert safe.endswith(".txt")

    # 测试获取文件扩展名
    ext = FileUtils.get_file_extension("test.txt")
    assert ext == ".txt"
    assert FileUtils.get_file_extension("no_extension") == ""

    # 测试创建临时文件
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_file = FileUtils.create_temp_file(tmpdir, "test", ".txt")
        assert temp_file.exists()
        assert temp_file.suffix == ".txt"

    # 测试目录大小计算
    size = FileUtils.get_directory_size("/tmp")
    assert isinstance(size, int)
    assert size >= 0

    # 测试文件读写
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write("test content")

    try:
        content = FileUtils.read_file(tmp_path)
        assert "test content" in content
    finally:
        os.unlink(tmp_path)


def test_data_validator_class():
    """测试 DataValidator 类"""
    from src.utils.data_validator import DataValidator

    # 测试字符串验证
    assert DataValidator.is_valid_string("test") is True
    assert DataValidator.is_valid_string("") is True
    assert DataValidator.is_valid_string(None) is False

    # 测试数字验证
    assert DataValidator.is_valid_number(123) is True
    assert DataValidator.is_valid_number(123.45) is True
    assert DataValidator.is_valid_number("123") is False
    assert DataValidator.is_valid_number(None) is False

    # 测试邮箱验证
    if hasattr(DataValidator, "is_valid_email"):
        assert DataValidator.is_valid_email("test@example.com") is True
        assert DataValidator.is_valid_email("invalid") is False

    # 测试 URL 验证
    if hasattr(DataValidator, "is_valid_url"):
        assert DataValidator.is_valid_url("https://example.com") is True
        assert DataValidator.is_valid_url("not-a-url") is False

    # 测试范围验证
    if hasattr(DataValidator, "is_in_range"):
        assert DataValidator.is_in_range(5, 1, 10) is True
        assert DataValidator.is_in_range(0, 1, 10) is False

    # 测试长度验证
    if hasattr(DataValidator, "has_valid_length"):
        assert DataValidator.has_valid_length("test", 1, 10) is True
        assert DataValidator.has_valid_length("test", 5, 10) is False


def test_helpers_class():
    """测试 Helpers 类"""
    from src.utils.helpers import Helpers

    # 测试生成 UUID
    uuid_val = Helpers.generate_uuid()
    assert isinstance(uuid_val, str)
    assert len(uuid_val) == 36

    # 测试生成随机字符串
    rand_str = Helpers.generate_random_string(10)
    assert len(rand_str) == 10
    assert rand_str.isalnum()

    # 测试列表去重
    dup_list = [1, 2, 2, 3, 3, 4]
    unique = Helpers.remove_duplicates(dup_list)
    assert unique == [1, 2, 3, 4]

    # 测试字典合并
    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 3, "c": 4}
    merged = Helpers.merge_dicts(dict1, dict2)
    assert merged["a"] == 1
    assert merged["b"] == 3
    assert merged["c"] == 4

    # 测试深度获取
    data = {"a": {"b": {"c": 123}}}
    value = Helpers.deep_get(data, "a.b.c")
    assert value == 123
    assert Helpers.deep_get(data, "a.b.x", "default") == "default"

    # 测试 JSON 判断
    assert Helpers.is_json('{"key": "value"}') is True
    assert Helpers.is_json("not json") is False


def test_formatters_class():
    """测试 Formatters 类"""
    from src.utils.formatters import Formatters

    # 测试货币格式化
    amount = 1234.56
    formatted = Formatters.format_currency(amount)
    assert "$" in formatted or "USD" in formatted
    assert "1,234.56" in formatted

    # 测试百分比格式化
    percent = 0.1234
    formatted = Formatters.format_percentage(percent * 100)
    assert "%" in formatted
    assert "12.34" in formatted

    # 测试数字格式化
    num = 1234567
    formatted = Formatters.format_number(num)
    assert "," in formatted
    assert "1,234,567" in formatted

    # 测试日期格式化
    date = datetime(2024, 1, 15)
    formatted = Formatters.format_date(date)
    assert "2024" in formatted
    assert "01" in formatted or "1" in formatted

    # 测试字节格式化
    bytes_val = 1024 * 1024  # 1MB
    formatted = Formatters.format_bytes(bytes_val)
    assert "MB" in formatted or "mb" in formatted

    # 测试持续时间格式化
    seconds = 3665
    formatted = Formatters.format_duration(seconds)
    assert "1h" in formatted or "hour" in formatted
    assert "1m" in formatted or "minute" in formatted
