"""
字典工具测试
"""

import pytest
from src.utils.dict_utils import (
    deep_merge,
    get_nested_value,
    set_nested_value,
    flatten_dict,
    filter_dict,
    rename_keys,
)


class TestDictUtils:
    """字典工具测试类"""

    def test_deep_merge(self):
        """测试深度合并"""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}

        result = deep_merge(dict1, dict2)
        expected = {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
        assert result == expected

    def test_get_nested_value(self):
        """测试获取嵌套值"""
        data = {"a": {"b": {"c": "value"}}}

        assert get_nested_value(data, ["a", "b", "c"]) == "value"
        assert get_nested_value(data, ["a", "b"]) == {"c": "value"}
        assert get_nested_value(data, ["x", "y"], "default") == "default"
        assert get_nested_value({}, ["a", "b"]) is None

    def test_set_nested_value(self):
        """测试设置嵌套值"""
        data = {}

        set_nested_value(data, ["a", "b", "c"], "value")
        assert data == {"a": {"b": {"c": "value"}}}

        set_nested_value(data, ["a", "b", "d"], "another")
        assert data["a"]["b"] == {"c": "value", "d": "another"}

    def test_flatten_dict(self):
        """测试字典扁平化"""
        data = {"a": {"b": {"c": 1}}, "d": 2}

        result = flatten_dict(data)
        expected = {"a.b.c": 1, "d": 2}
        assert result == expected

    def test_filter_dict(self):
        """测试字典过滤"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}

        # 按键过滤
        result1 = filter_dict(data, keys=["a", "c"])
        assert result1 == {"a": 1, "c": 3}

        # 按值过滤
        result2 = filter_dict(data, predicate=lambda k, v: v > 2)
        assert result2 == {"c": 3, "d": 4}

    def test_rename_keys(self):
        """测试键重命名"""
        data = {"old_key1": "value1", "old_key2": "value2", "keep_key": "value3"}
        mapping = {"old_key1": "new_key1", "old_key2": "new_key2"}

        result = rename_keys(data, mapping)
        expected = {"new_key1": "value1", "new_key2": "value2", "keep_key": "value3"}
        assert result == expected

    def test_edge_cases(self):
        """测试边界情况"""
        # 空字典
        assert deep_merge({}, {}) == {}
        assert flatten_dict({}) == {}
        assert filter_dict({}) == {}

        # None值
        assert get_nested_value(None, ["a"]) is None

        # 单层字典
        simple = {"a": 1}
        assert flatten_dict(simple) == {"a": 1}
