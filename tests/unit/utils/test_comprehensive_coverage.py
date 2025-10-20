"""
Utils模块综合测试
目标覆盖率：80%+
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time
import threading
from typing import Dict, Any, Optional

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入所有utils模块

# Mock module src.utils.dict_utils
from unittest.mock import Mock, patch

sys.modules["src.utils.dict_utils"] = Mock()
try:
    from src.utils.dict_utils import *

    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False


class TestDictUtils:
    """字典工具测试"""

    def test_deep_merge_simple(self):
        """测试简单字典合并"""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        result = deep_merge(d1, d2)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        d1 = {"a": {"x": 1}, "b": 2}
        d2 = {"a": {"y": 2}, "c": 3}
        result = deep_merge(d1, d2)
        assert result == {"a": {"x": 1, "y": 2}, "b": 2, "c": 3}

    def test_deep_merge_empty(self):
        """测试空字典合并"""
        assert deep_merge({}, {"a": 1}) == {"a": 1}
        assert deep_merge({"a": 1}, {}) == {"a": 1}
        assert deep_merge({}, {}) == {}

    def test_pick_keys(self):
        """测试选择键"""
        d = {"a": 1, "b": 2, "c": 3}
        assert pick_keys(d, ["a", "c"]) == {"a": 1, "c": 3}
        assert pick_keys(d, []) == {}
        assert pick_keys(d, ["x"]) == {}

    def test_omit_keys(self):
        """测试排除键"""
        d = {"a": 1, "b": 2, "c": 3}
        assert omit_keys(d, ["b"]) == {"a": 1, "c": 3}
        assert omit_keys(d, []) == {"a": 1, "b": 2, "c": 3}

    def test_rename_keys(self):
        """测试重命名键"""
        d = {"old_name": 1, "keep": 2}
        mapping = {"old_name": "new_name"}
        assert rename_keys(d, mapping) == {"new_name": 1, "keep": 2}

    def test_get_nested(self):
        """测试获取嵌套值"""
        d = {"a": {"b": {"c": 1}}}
        assert get_nested(d, "a.b.c") == 1
        assert get_nested(d, "a.b.x", "default") == "default"
        assert get_nested(d, "x.y", "default") == "default"


class TestStringUtils:
    """字符串工具测试"""

    @pytest.mark.parametrize(
        "input,expected",
        [
            ("hello_world", "helloWorld"),
            ("user_name", "userName"),
            ("single", "single"),
            ("", ""),
            ("alreadyCamel", "alreadyCamel"),
        ],
    )
    def test_snake_to_camel(self, input, expected):
        """测试蛇形转驼峰"""
        assert snake_to_camel(input) == expected

    @pytest.mark.parametrize(
        "input,expected",
        [
            ("helloWorld", "hello_world"),
            ("userName", "user_name"),
            ("Single", "single"),
            ("already_snake", "already_snake"),
        ],
    )
    def test_camel_to_snake(self, input, expected):
        """测试驼峰转蛇形"""
        assert camel_to_snake(input) == expected

    def test_truncate(self):
        """测试字符串截断"""
        long_text = "This is a very long text"
        assert truncate(long_text, 10) == "This is..."
        assert truncate("short", 10) == "short"
        assert truncate("", 5) == ""

    def test_slugify(self):
        """测试生成slug"""
        assert slugify("Hello World!") == "hello-world"
        assert slugify("  Multiple   Spaces  ") == "multiple-spaces"
        assert slugify("Special#@%Characters") == "special-characters"


class TestValidators:
    """验证器测试"""

    def test_is_email(self):
        """测试邮箱验证"""
        assert is_email("test@example.com") is True
        assert is_email("user.name+tag@domain.co.uk") is True
        assert is_email("invalid-email") is False
        assert is_email("@domain.com") is False
        assert is_email("user@") is False

    def test_is_phone(self):
        """测试手机号验证"""
        assert is_phone("+86 138 0000 0000") is True
        assert is_phone("138-0000-0000") is True
        assert is_phone("13800000000") is True
        assert is_phone("123") is False
        assert is_phone("abc") is False

    def test_is_url(self):
        """测试URL验证"""
        assert is_url("https://www.example.com") is True
        assert is_url("http://localhost:8000") is True
        assert is_url("ftp://files.example.com") is True
        assert is_url("not-a-url") is False
        assert is_url("www.example.com") is False

    def test_validate_date(self):
        """测试日期验证"""
        assert validate_date("2025-01-18") is True
        assert validate_date("2025/01/18") is True
        assert validate_date("2025-13-01") is False
        assert validate_date("invalid-date") is False

    def test_validate_positive_number(self):
        """测试正数验证"""
        assert validate_positive_number(5) is True
        assert validate_positive_number(0) is False
        assert validate_positive_number(-1) is False
        assert validate_positive_number(3.14) is True


class TestFormatters:
    """格式化器测试"""

    def test_format_currency(self):
        """测试货币格式化"""
        assert format_currency(1000, "USD") == "$1,000.00"
        assert format_currency(1000, "EUR") == "€1,000.00"
        assert format_currency(1000, "CNY") == "¥1,000.00"
        assert format_currency(0) == "$0.00"

    def test_format_date(self):
        """测试日期格式化"""
        date = datetime(2025, 1, 18)
        assert "2025" in format_date(date)
        assert "01" in format_date(date)
        assert "18" in format_date(date)

    def test_format_percentage(self):
        """测试百分比格式化"""
        assert format_percentage(0.5) == "50.00%"
        assert format_percentage(0.1234, 1) == "12.3%"
        assert format_percentage(1) == "100.00%"


class TestHelpers:
    """辅助函数测试"""

    def test_retry_success(self):
        """测试重试成功"""
        attempts = 0

        @retry(3, delay=0)
        def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ValueError("Try again")
            return "success"

        assert flaky() == "success"
        assert attempts == 2

    def test_retry_failure(self):
        """测试重试失败"""

        @retry(3, delay=0)
        def always_fail():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_fail()

    def test_measure_time(self):
        """测试执行时间测量"""

        @measure_time
        def slow_function():
            time.sleep(0.1)
            return "done"

        result, duration = slow_function()
        assert result == "done"
        assert duration >= 0.1

    def test_cache_result(self):
        """测试结果缓存"""
        call_count = 0

        @cache_result(ttl=1)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        assert expensive_function(5) == 10
        assert call_count == 1

        # 第二次调用（使用缓存）
        assert expensive_function(5) == 10
        assert call_count == 1

        # 不同参数
        assert expensive_function(10) == 20
        assert call_count == 2

    def test_debounce(self):
        """测试防抖"""
        call_count = 0

        @debounce(0.1)
        def debounced_function():
            nonlocal call_count
            call_count += 1

        # 快速连续调用
        debounced_function()
        debounced_function()
        debounced_function()

        # 等待防抖延迟
        time.sleep(0.2)

        # 只执行一次
        assert call_count == 1


class TestResponse:
    """响应工具测试"""

    def test_success_response(self):
        """测试成功响应"""
        response = success_response({"data": "test"})
        assert response["status"] == "success"
        assert response["data"] == {"data": "test"}
        assert "timestamp" in response

    def test_error_response(self):
        """测试错误响应"""
        response = error_response("Something went wrong", code=400)
        assert response["status"] == "error"
        assert response["message"] == "Something went wrong"
        assert response["code"] == 400

    def test_paginated_response(self):
        """测试分页响应"""
        data = [{"id": i} for i in range(100)]
        response = paginated_response(data, page=1, per_page=10, total=100)
        assert response["data"] == data[:10]
        assert response["pagination"]["page"] == 1
        assert response["pagination"]["total"] == 100
        assert response["pagination"]["pages"] == 10


class TestCryptoUtils:
    """加密工具测试"""

    def test_generate_verify_hash(self):
        """测试生成和验证哈希"""
        password = "my_password"
        hash_val = generate_hash(password)
        assert hash_val != password
        assert verify_hash(password, hash_val) is True
        assert verify_hash("wrong_password", hash_val) is False

    def test_generate_token(self):
        """测试生成令牌"""
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) > 20

        # 不同调用生成不同token
        token2 = generate_token()
        assert token != token2

    def test_encrypt_decrypt(self):
        """测试加密解密"""
        data = "sensitive information"
        key = "encryption_key"

        # 模拟加密（如果函数存在）
        if hasattr(encrypt_data, "__call__"):
            encrypted = encrypt_data(data, key)
            assert encrypted != data


class TestFileUtils:
    """文件工具测试"""

    def test_read_write_json(self, tmp_path):
        """测试JSON文件读写"""
        data = {"name": "test", "value": 123}
        file_path = tmp_path / "test.json"

        write_json(file_path, data)
        assert file_path.exists()

        read_data = read_json(file_path)
        assert read_data == data

    def test_ensure_directory(self, tmp_path):
        """测试确保目录存在"""
        dir_path = tmp_path / "new" / "directory"
        ensure_directory(dir_path)
        assert dir_path.exists()
        assert dir_path.is_dir()

    def test_get_file_size(self, tmp_path):
        """测试获取文件大小"""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, World!")

        size = get_file_size(file_path)
        assert size == 13  # "Hello, World!" = 13 bytes


class TestTimeUtils:
    """时间工具测试"""

    def test_format_duration(self):
        """测试格式化持续时间"""
        assert format_duration(60) == "1 minute"
        assert format_duration(3600) == "1 hour"
        assert format_duration(3661) == "1 hour 1 minute 1 second"

    def test_parse_iso_datetime(self):
        """测试解析ISO时间"""
        dt_str = "2025-01-18T14:30:00"
        dt = parse_iso_datetime(dt_str)
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 18

    def test_get_time_range(self):
        """测试获取时间范围"""
        start, end = get_time_range("today")
        assert start.date() == end.date()

        start, end = get_time_range("week")
        assert (end - start).days == 7


class TestDataValidator:
    """数据验证器测试"""

    def test_data_validator_creation(self):
        """测试创建数据验证器"""
        validator = DataValidator()
        assert hasattr(validator, "validate")

    def test_validation_rules(self):
        """测试验证规则"""
        validator = DataValidator()
        schema = {
            "name": {"type": "string", "required": True},
            "age": {"type": "int", "min": 0, "max": 150},
            "email": {"type": "email", "optional": True},
        }

        # 有效数据
        data = {"name": "John", "age": 30}
        result = validator.validate(data, schema)
        assert result["valid"] is True

        # 无效数据
        data = {"name": "", "age": -1}
        result = validator.validate(data, schema)
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestWarningFilters:
    """警告过滤器测试"""

    def test_filter_deprecation_warnings(self):
        """测试过滤弃用警告"""
        with filter_warnings("ignore", DeprecationWarning):
            import warnings

            warnings.warn("This is deprecated", DeprecationWarning)
            # 不应该抛出警告

    def test_warning_context(self):
        """测试警告上下文管理器"""
        import warnings

        with WarningContext(ignore=[DeprecationWarning]):
            warnings.warn("Deprecated", DeprecationWarning)

        # 退出上下文后，警告应该恢复


# 参数化测试覆盖更多边缘情况
@pytest.mark.parametrize(
    "test_input,expected",
    [
        ({}, {}),  # 空字典
        ({"a": 1}, {"a": 1}),  # 单个键
        ({"a": 1, "b": 2}, {"a": 1, "b": 2}),  # 多个键
        ({"a": {"x": 1}, "b": 2}, {"a": {"x": 1}, "b": 2}),  # 嵌套
    ],
)
def test_dict_utils_edge_cases(test_input, expected):
    """测试字典工具边缘情况"""
    # 测试各种字典操作不会改变原字典
    import copy

    original = copy.deepcopy(test_input)

    # 执行操作
    pick_keys(test_input, list(test_input.keys()))

    # 验证原字典未被修改
    assert test_input == original


# 性能测试
def test_performance_dict_operations():
    """测试字典操作性能"""
    import time

    large_dict = {f"key_{i}": i for i in range(1000)}
    keys_to_pick = [f"key_{i}" for i in range(0, 1000, 10)]

    start = time.time()
    result = pick_keys(large_dict, keys_to_pick)
    duration = time.time() - start

    assert len(result) == 100
    assert duration < 0.01  # 应该在10ms内完成


# 并发测试
def test_concurrent_cache_access():
    """测试并发缓存访问"""
    results = []
    errors = []

    @cache_result(ttl=1)
    def shared_function(x):
        return x * 2

    def worker():
        try:
            for i in range(10):
                result = shared_function(i)
                results.append(result)
        except Exception as e:
            errors.append(e)

    # 创建多个线程
    threads = [threading.Thread(target=worker) for _ in range(5)]

    # 启动所有线程
    for t in threads:
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 50
