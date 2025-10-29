"""
基础工具模块测试
"""

from datetime import datetime

import pytest

from src.utils import dict_utils, string_utils, time_utils


@pytest.mark.unit
@pytest.mark.external_api
class TestStringUtils:
    """字符串工具测试"""

    def test_truncate(self):
        """测试字符串截断"""
        text = "This is a long string"
        assert string_utils.StringUtils.truncate(text, 10) == "This is..."
        assert string_utils.StringUtils.truncate(text, 20) == "This is a long st..."  # 调整预期值
        assert string_utils.StringUtils.truncate(text, 10, suffix="...") == "This is..."

    def test_slugify(self):
        """测试转换为URL友好格式"""
        assert string_utils.StringUtils.slugify("Hello World!") == "hello-world"
        assert string_utils.StringUtils.slugify("Python & Django") == "python-django"
        assert string_utils.StringUtils.slugify("  Multiple   Spaces  ") == "multiple-spaces"

    def test_camel_to_snake(self):
        """测试驼峰命名转下划线命名"""
        assert string_utils.StringUtils.camel_to_snake("HelloWorld") == "hello_world"
        assert string_utils.StringUtils.camel_to_snake("helloWorld") == "hello_world"
        assert string_utils.StringUtils.camel_to_snake("HTTPResponseCode") == "http_response_code"

    def test_snake_to_camel(self):
        """测试下划线命名转驼峰命名"""
        assert string_utils.StringUtils.snake_to_camel("hello_world") == "helloWorld"
        assert string_utils.StringUtils.snake_to_camel("user_name") == "userName"
        assert string_utils.StringUtils.snake_to_camel("alreadycamel") == "alreadycamel"

    def test_clean_text(self):
        """测试清理文本"""
        text = "  This    is  a   test  \n\n  string  "
        cleaned = string_utils.StringUtils.clean_text(text)
        assert cleaned == "This is a test string"  # 调整预期值

    def test_extract_numbers(self):
        """测试从文本中提取数字"""
        text = "The price is $19.99 and tax is 2.5%"
        numbers = string_utils.StringUtils.extract_numbers(text)
        assert 19.99 in numbers
        assert 2.5 in numbers
        assert len(numbers) == 2


class TestTimeUtils:
    """时间工具测试"""

    def test_now_utc(self):
        """测试获取当前UTC时间"""
        now = time_utils.TimeUtils.now_utc()
        assert isinstance(now, datetime)
        assert now.tzinfo is not None

    def test_timestamp_to_datetime(self):
        """测试时间戳转datetime"""
        ts = 1640995200  # 2022-01-01 00:00:00
        dt = time_utils.TimeUtils.timestamp_to_datetime(ts)
        assert isinstance(dt, datetime)
        assert dt.year == 2022
        assert dt.month == 1
        assert dt.day == 1

    def test_datetime_to_timestamp(self):
        """测试datetime转时间戳"""
        dt = datetime(2022, 1, 1, 0, 0, 0)
        ts = time_utils.TimeUtils.datetime_to_timestamp(dt)
        assert isinstance(ts, (int, float))
        assert ts > 0

    def test_format_datetime(self):
        """测试格式化datetime"""
        dt = datetime(2022, 1, 1, 12, 30, 45)
        formatted = time_utils.TimeUtils.format_datetime(dt, "%Y-%m-%d %H:%M:%S")
        assert formatted == "2022-01-01 12:30:45"

    def test_parse_datetime(self):
        """测试解析日期时间字符串"""
        date_str = "2022-01-01 12:30:45"
        dt = time_utils.TimeUtils.parse_datetime(date_str)
        assert dt.year == 2022
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45

    def test_utc_now_function(self):
        """测试向后兼容的utc_now函数"""
        now = time_utils.utc_now()
        assert isinstance(now, datetime)
        assert now.tzinfo is not None

    def test_parse_datetime_function(self):
        """测试向后兼容的parse_datetime函数"""
        # 标准格式
        dt = time_utils.parse_datetime("2022-01-01 12:30:45")
        assert dt.year == 2022

        # ISO格式
        dt = time_utils.parse_datetime("2022-01-01T12:30:45Z")
        assert dt is not None

        # 只有日期
        dt = time_utils.parse_datetime("2022-01-01")
        assert dt is not None

        # 无效格式
        dt = time_utils.parse_datetime("invalid date")
        assert dt is None

        # None输入
        dt = time_utils.parse_datetime(None)
        assert dt is None


class TestDictUtils:
    """字典工具测试"""

    def test_deep_merge(self):
        """测试深度合并字典"""
        dict1 = {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
        dict2 = {"b": {"y": 30, "z": 40}, "d": 4}

        merged = dict_utils.DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": {"x": 10, "y": 30, "z": 40}, "c": 3, "d": 4}
        assert merged == expected

    def test_deep_merge_empty(self):
        """测试与空字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {}

        merged = dict_utils.DictUtils.deep_merge(dict1, dict2)
        assert merged == {"a": 1, "b": 2}

        merged = dict_utils.DictUtils.deep_merge({}, dict1)
        assert merged == {"a": 1, "b": 2}

    def test_flatten_dict(self):
        """测试扁平化字典"""
        _data = {
            "user": {"name": "John", "address": {"city": "New York", "country": "USA"}},
            "active": True,
        }

        flattened = dict_utils.DictUtils.flatten_dict(data)
        expected = {
            "user.name": "John",
            "user.address.city": "New York",
            "user.address.country": "USA",
            "active": True,
        }
        assert flattened == expected

    def test_flatten_dict_with_separator(self):
        """测试使用自定义分隔符扁平化字典"""
        _data = {"a": {"b": {"c": 1}}}

        flattened = dict_utils.DictUtils.flatten_dict(data, sep="_")
        expected = {"a_b_c": 1}
        assert flattened == expected

    def test_flatten_dict_empty(self):
        """测试扁平化空字典"""
        flattened = dict_utils.DictUtils.flatten_dict({})
        assert flattened == {}

    def test_filter_none_values(self):
        """测试过滤None值"""
        _data = {"a": 1, "b": None, "c": "test", "d": None, "e": 0, "f": False}

        filtered = dict_utils.DictUtils.filter_none_values(data)
        expected = {"a": 1, "c": "test", "e": 0, "f": False}
        assert filtered == expected

    def test_filter_none_values_all_none(self):
        """测试过滤全部为None的字典"""
        _data = {"a": None, "b": None, "c": None}

        filtered = dict_utils.DictUtils.filter_none_values(data)
        assert filtered == {}

    def test_filter_none_values_empty(self):
        """测试过滤空字典"""
        filtered = dict_utils.DictUtils.filter_none_values({})
        assert filtered == {}
