"""字典工具简单测试"""

import pytest
# from src.utils.dict_utils import DictUtils


class TestDictUtils:
    """测试字典工具函数"""

    def test_deep_merge(self):
        """测试深度合并"""
        dict1 = {"a": {"x": 1}, "b": 2}
        dict2 = {"a": {"y": 2}, "c": 3}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": {"x": 1, "y": 2}, "b": 2, "c": 3}

    def test_flatten_dict(self):
        """测试字典扁平化"""
        nested = {"a": {"b": {"c": 1}}, "x": 2}
        result = DictUtils.flatten_dict(nested)
        assert result == {"a.b.c": 1, "x": 2}

    def test_filter_none_values(self):
        """测试过滤 None 值"""
        data = {"a": 1, "b": None, "c": 0, "d": False}
        result = DictUtils.filter_none_values(data)
        assert result == {"a": 1, "c": 0, "d": False}
