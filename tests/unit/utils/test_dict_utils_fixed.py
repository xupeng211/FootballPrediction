"""
测试 dict_utils 的深度合并功能
确保修复后的代码满足预期行为
"""

import pytest
from src.utils.dict_utils import DictUtils


class TestDictUtilsFixed:
    """测试修复后的 DictUtils 功能"""

    def test_deep_merge_basic(self):
        """测试基本深度合并"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"y": 20}, "c": 3}

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
        assert result == expected

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        dict1 = {"level1": {"level2": {"a": 1, "b": 2}, "other": "value1"}}
        dict2 = {"level1": {"level2": {"b": 3, "c": 4}, "new": "value2"}}

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "level1": {
                "level2": {"a": 1, "b": 3, "c": 4},
                "other": "value1",
                "new": "value2",
            }
        }
        assert result == expected

    def test_deep_merge_no_mutation(self):
        """测试原始字典不被修改"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"y": 20}}
        dict1_copy = dict1.copy()
        dict1["b"] = dict1["b"].copy()

        result = DictUtils.deep_merge(dict1, dict2)

        # 确保原始字典未被修改
        assert dict1 == dict1_copy
        assert result != dict1

    def test_deep_merge_empty_dicts(self):
        """测试空字典合并"""
        assert DictUtils.deep_merge({}, {}) == {}
        assert DictUtils.deep_merge({"a": 1}, {}) == {"a": 1}
        assert DictUtils.deep_merge({}, {"b": 2}) == {"b": 2}
