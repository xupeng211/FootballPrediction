#!/usr/bin/env python3
"""
字典工具测试
测试 src.utils.dict_utils 模块的功能
"""

import pytest

from src.utils.dict_utils import DictUtils


@pytest.mark.unit
class TestDictUtils:
    """字典工具测试"""

    def test_deep_merge_simple(self):
        """测试简单字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        dict1 = {"config": {"setting1": "value1", "setting2": "old"}, "other": "keep"}
        dict2 = {
            "config": {"setting2": "new", "setting3": "value3"},
            "new_key": "new_value",
        }

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "config": {"setting1": "value1", "setting2": "new", "setting3": "value3"},
            "other": "keep",
            "new_key": "new_value",
        }
        assert result == expected

    def test_deep_merge_empty_dicts(self):
        """测试空字典合并"""
        # 第一个字典为空
        result1 = DictUtils.deep_merge({}, {"a": 1})
        assert result1 == {"a": 1}

        # 第二个字典为空
        result2 = DictUtils.deep_merge({"a": 1}, {})
        assert result2 == {"a": 1}

        # 都为空
        result3 = DictUtils.deep_merge({}, {})
        assert result3 == {}

    def test_deep_merge_no_overlap(self):
        """测试无重叠键的字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

    def test_deep_merge_complex_nested(self):
        """测试复杂嵌套字典合并"""
        dict1 = {
            "level1": {
                "level2": {
                    "level3": {"a": "old_a", "b": "keep_b"},
                    "other": "keep_other",
                },
                "sibling": "keep_sibling",
            }
        }
        dict2 = {
            "level1": {
                "level2": {
                    "level3": {"a": "new_a", "c": "new_c"},
                    "new_sibling": "new_sibling",
                },
                "new_top": "new_top",
            }
        }

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "level1": {
                "level2": {
                    "level3": {"a": "new_a", "b": "keep_b", "c": "new_c"},
                    "other": "keep_other",
                    "new_sibling": "new_sibling",
                },
                "sibling": "keep_sibling",
                "new_top": "new_top",
            }
        }
        assert result == expected

    def test_deep_merge_different_types(self):
        """测试不同类型值的合并"""
        dict1 = {"config": {"setting": "old"}}
        dict2 = {"config": "string_value"}

        result = DictUtils.deep_merge(dict1, dict2)

        # dict2的值应该覆盖dict1的字典
        expected = {"config": "string_value"}
        assert result == expected

    def test_deep_merge_preserves_original(self):
        """测试原始字典不被修改"""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}

        # 备份原始字典
        original_dict1 = dict1.copy()
        original_dict1_b = dict1["b"].copy()

        result = DictUtils.deep_merge(dict1, dict2)

        # 验证原始字典未被修改
        assert dict1 == original_dict1
        assert dict1["b"] == original_dict1_b

        # 验证结果是新的合并字典
        assert result == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}

    def test_deep_merge_list_values(self):
        """测试列表值的合并（直接覆盖）"""
        dict1 = {"items": ["a", "b"]}
        dict2 = {"items": ["c", "d"]}

        result = DictUtils.deep_merge(dict1, dict2)

        # 列表应该被直接覆盖，不是合并
        expected = {"items": ["c", "d"]}
        assert result == expected

    def test_deep_merge_none_values(self):
        """测试None值的处理"""
        dict1 = {"a": None, "b": "value"}
        dict2 = {"a": "not_none", "c": None}

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": "not_none", "b": "value", "c": None}
        assert result == expected
