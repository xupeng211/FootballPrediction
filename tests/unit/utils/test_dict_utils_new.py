"""字典工具测试"""

import pytest
# from src.utils.dict_utils import DictUtils


@pytest.mark.unit

class TestDictUtils:
    """字典工具测试"""

    def test_deep_merge(self):
        """测试深度合并"""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}
        _result = DictUtils.deep_merge(dict1, dict2)
        assert _result == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}

    def test_flatten_dict(self):
        """测试扁平化字典"""
        nested = {"a": {"b": {"c": 1}}, "d": 2}
        _result = DictUtils.flatten_dict(nested)
        assert _result["a.b.c"] == 1
        assert _result["d"] == 2

    def test_filter_none_values(self):
        """测试过滤None值"""
        _data = {"a": 1, "b": None, "c": 3, "d": None}
        _result = DictUtils.filter_none_values(data)
        assert _result == {"a": 1, "c": 3}

    def test_deep_merge_nested(self):
        """测试深度合并嵌套字典"""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 4, "z": 5}, "c": 6}
        _result = DictUtils.deep_merge(dict1, dict2)
        assert _result == {"a": {"x": 1, "y": 4, "z": 5}, "b": 3, "c": 6}

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符的扁平化字典"""
        nested = {"a": {"b": {"c": 1}}, "d": 2}
        _result = DictUtils.flatten_dict(nested, sep="_")
        assert _result["a_b_c"] == 1
        assert _result["d"] == 2
