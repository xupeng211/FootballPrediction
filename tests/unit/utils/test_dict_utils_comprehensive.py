"""
字典工具综合测试
Comprehensive Tests for Dict Utils

测试DictUtils类的所有功能，包括：
- 嵌套值操作
- 字典合并
- 扁平化
- 路径操作
"""

import pytest
from src.utils.dict_utils import DictUtils


class TestDictUtilsComprehensive:
    """字典工具综合测试"""

    # ==================== 嵌套值操作测试 ====================

    def test_get_nested_simple(self):
        """测试：获取简单嵌套值"""
        data = {"a": {"b": {"c": 123}}}
        assert DictUtils.get_nested(data, "a.b.c") == 123
        assert DictUtils.get_nested(data, "a.b") == {"c": 123}
        assert DictUtils.get_nested(data, "a") == {"b": {"c": 123}}

    def test_get_nested_default(self):
        """测试：获取嵌套值（带默认值）"""
        data = {"a": {"b": 1}}
        assert DictUtils.get_nested(data, "a.c", default="missing") == "missing"
        assert DictUtils.get_nested(data, "x.y", default=0) == 0
        assert DictUtils.get_nested({}, "a.b", default={}) == {}

    def test_get_nested_none_values(self):
        """测试：处理None值"""
        data = {"a": None, "b": {"c": None}}
        assert DictUtils.get_nested(data, "a") is None
        assert DictUtils.get_nested(data, "b.c") is None
        assert DictUtils.get_nested(data, "b.c", default="default") is None

    def test_set_nested_new(self):
        """测试：设置新的嵌套值"""
        data = {}
        DictUtils.set_nested(data, "a.b.c", 123)
        assert data == {"a": {"b": {"c": 123}}}

    def test_set_nested_existing(self):
        """测试：覆盖现有嵌套值"""
        data = {"a": {"b": {"c": 1}}}
        DictUtils.set_nested(data, "a.b.c", 999)
        assert data["a"]["b"]["c"] == 999

    def test_set_nested_intermediate(self):
        """测试：设置中间路径的值"""
        data = {}
        DictUtils.set_nested(data, "a.b", {"c": 1})
        assert data == {"a": {"b": {"c": 1}}}

    def test_set_nested_overwrite_dict(self):
        """测试：覆盖字典值"""
        data = {"a": {"old": "value"}}
        DictUtils.set_nested(data, "a", {"new": "value"})
        assert data == {"a": {"new": "value"}}

    # ==================== 字典合并测试 ====================

    def test_merge_simple(self):
        """测试：简单字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        result = DictUtils.merge(dict1, dict2)
        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

    def test_merge_overwrite(self):
        """测试：合并时覆盖"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 99, "c": 3}
        result = DictUtils.merge(dict1, dict2)
        assert result == {"a": 1, "b": 99, "c": 3}

    def test_merge_deep(self):
        """测试：深度合并"""
        dict1 = {"a": {"x": 1, "y": 2}}
        dict2 = {"a": {"y": 99, "z": 3}}
        result = DictUtils.merge(dict1, dict2, deep=True)
        assert result == {"a": {"x": 1, "y": 99, "z": 3}}

    def test_merge_deep_new_keys(self):
        """测试：深度合并新键"""
        dict1 = {"a": {"x": 1}}
        dict2 = {"b": {"y": 2}}
        result = DictUtils.merge(dict1, dict2, deep=True)
        assert result == {"a": {"x": 1}, "b": {"y": 2}}

    def test_merge_deep_nested_levels(self):
        """测试：多级深度合并"""
        dict1 = {"a": {"b": {"c": 1, "d": 2}}}
        dict2 = {"a": {"b": {"c": 99, "e": 3}}}
        result = DictUtils.merge(dict1, dict2, deep=True)
        assert result == {"a": {"b": {"c": 99, "d": 2, "e": 3}}}

    def test_merge_three_dicts(self):
        """测试：合并三个字典"""
        dict1 = {"a": 1}
        dict2 = {"b": 2}
        dict3 = {"c": 3}
        result = DictUtils.merge(dict1, dict2, dict3)
        assert result == {"a": 1, "b": 2, "c": 3}

    # ==================== 扁平化测试 ====================

    def test_flatten_simple(self):
        """测试：简单扁平化"""
        data = {"a": 1, "b": 2}
        result = DictUtils.flatten(data)
        assert result == {"a": 1, "b": 2}

    def test_flatten_nested(self):
        """测试：嵌套扁平化"""
        data = {"a": {"b": {"c": 1}}, "x": 2}
        result = DictUtils.flatten(data)
        assert result == {"a.b.c": 1, "x": 2}

    def test_flatten_list(self):
        """测试：包含列表的扁平化"""
        data = {"a": [1, 2, 3], "b": {"c": [4, 5]}}
        result = DictUtils.flatten(data)
        assert result == {"a": [1, 2, 3], "b.c": [4, 5]}

    def test_flatten_empty(self):
        """测试：空字典扁平化"""
        assert DictUtils.flatten({}) == {}
        assert DictUtils.flatten({"a": {}}) == {}

    def test_flatten_mixed(self):
        """测试：混合类型扁平化"""
        data = {
            "user": {
                "name": "John",
                "address": {
                    "street": "123 Main St",
                    "city": "New York"
                }
            },
            "active": True
        }
        result = DictUtils.flatten(data)
        expected = {
            "user.name": "John",
            "user.address.street": "123 Main St",
            "user.address.city": "New York",
            "active": True
        }
        assert result == expected

    # ==================== 路径操作测试 ====================

    def test_get_path_exists(self):
        """测试：获取存在的路径"""
        data = {"a": {"b": {"c": 123}}}
        path = ["a", "b", "c"]
        assert DictUtils.get_path(data, path) == 123

    def test_get_path_not_exists(self):
        """测试：获取不存在的路径"""
        data = {"a": {"b": 1}}
        path = ["a", "c", "d"]
        assert DictUtils.get_path(data, path) is None
        assert DictUtils.get_path(data, path, default="missing") == "missing"

    def test_set_path_new(self):
        """测试：设置新路径"""
        data = {}
        path = ["a", "b", "c"]
        DictUtils.set_path(data, path, 123)
        assert data == {"a": {"b": {"c": 123}}}

    def test_set_path_existing(self):
        """测试：设置现有路径"""
        data = {"a": {"b": {"c": 1}}}
        path = ["a", "b", "c"]
        DictUtils.set_path(data, path, 999)
        assert data["a"]["b"]["c"] == 999

    def test_set_path_root(self):
        """测试：设置根路径"""
        data = {}
        DictUtils.set_path(data, [], 123)
        assert data == 123

    def test_set_path_partial(self):
        """测试：设置部分路径"""
        data = {"a": {"x": 1}}
        path = ["a", "b"]
        DictUtils.set_path(data, path, 2)
        assert data == {"a": {"x": 1, "b": 2}}

    # ==================== 其他功能测试 ====================

    def test_pick_keys(self):
        """测试：选择特定键"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["a", "c"]
        result = DictUtils.pick(data, keys)
        assert result == {"a": 1, "c": 3}

    def test_pick_missing_keys(self):
        """测试：选择缺失的键"""
        data = {"a": 1, "b": 2}
        keys = ["a", "c", "d"]
        result = DictUtils.pick(data, keys)
        assert result == {"a": 1}

    def test_omit_keys(self):
        """测试：排除特定键"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["b", "d"]
        result = DictUtils.omit(data, keys)
        assert result == {"a": 1, "c": 3}

    def test_omit_missing_keys(self):
        """测试：排除缺失的键"""
        data = {"a": 1, "b": 2}
        keys = ["b", "c", "d"]
        result = DictUtils.omit(data, keys)
        assert result == {"a": 1}

    def test_rename_keys(self):
        """测试：重命名键"""
        data = {"old_name": 1, "keep_name": 2}
        mapping = {"old_name": "new_name"}
        result = DictUtils.rename_keys(data, mapping)
        assert result == {"new_name": 1, "keep_name": 2}

    def test_rename_keys_conflict(self):
        """测试：重命名键（有冲突）"""
        data = {"a": 1, "b": 2}
        mapping = {"a": "b"}  # 会覆盖现有的b
        result = DictUtils.rename_keys(data, mapping)
        assert result == {"b": 1}  # 原来的b被覆盖

    def test_filter_by_value(self):
        """测试：按值过滤"""
        data = {"a": 1, "b": 2, "c": 3, "d": 1}
        result = DictUtils.filter_by_value(data, lambda v: v == 1)
        assert result == {"a": 1, "d": 1}

    def test_filter_by_key(self):
        """测试：按键过滤"""
        data = {"apple": 1, "banana": 2, "apricot": 3}
        result = DictUtils.filter_by_key(data, lambda k: k.startswith('a'))
        assert result == {"apple": 1, "apricot": 3}

    def test_invert_dict(self):
        """测试：反转字典"""
        data = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.invert(data)
        assert result == {1: "a", 2: "b", 3: "c"}

    def test_invert_dict_duplicate_values(self):
        """测试：反转字典（有重复值）"""
        data = {"a": 1, "b": 1, "c": 2}
        # 后面的键会覆盖前面的
        result = DictUtils.invert(data)
        assert result == {1: "b", 2: "c"}

    def test_group_by_key(self):
        """测试：按键分组"""
        data = [
            {"type": "fruit", "name": "apple"},
            {"type": "fruit", "name": "banana"},
            {"type": "vegetable", "name": "carrot"},
            {"type": "fruit", "name": "orange"},
        ]
        result = DictUtils.group_by_key(data, "type")
        assert set(result.keys()) == {"fruit", "vegetable"}
        assert len(result["fruit"]) == 3
        assert len(result["vegetable"]) == 1

    def test_deep_copy_dict(self):
        """测试：深拷贝字典"""
        data = {"a": {"b": {"c": [1, 2, 3]}}}
        copy = DictUtils.deep_copy(data)
        # 修改原数据不应影响拷贝
        data["a"]["b"]["c"].append(4)
        assert copy["a"]["b"]["c"] == [1, 2, 3]

    # ==================== 边界条件测试 ====================

    def test_empty_dict_operations(self):
        """测试：空字典操作"""
        assert DictUtils.get_nested({}, "a.b") is None
        DictUtils.set_nested({}, "a.b", 1) == {"a": {"b": 1}}
        assert DictUtils.flatten({}) == {}
        assert DictUtils.merge({}, {}) == {}

    def test_none_handling(self):
        """测试：None值处理"""
        # None作为数据
        assert DictUtils.get_nested(None, "a.b") is None
        assert DictUtils.flatten(None) == {}

        # None作为值
        data = {"a": None, "b": {"c": None}}
        assert DictUtils.get_nested(data, "a") is None
        assert DictUtils.get_nested(data, "b.c") is None

    def test_non_string_keys(self):
        """测试：非字符串键"""
        data = {1: {"a": 10}, (2, 3): {"b": 20}}
        # DictUtils主要处理字符串键路径，非字符串键需要特殊处理
        assert DictUtils.get_nested(data, "1.a") is None  # 不会自动转换

    def test_very_deep_nesting(self):
        """测试：非常深的嵌套"""
        # 创建深层嵌套
        data = {}
        current = data
        for i in range(100):
            current["level"] = {}
            current = current["level"]
        current["value"] = "deep"

        # 测试获取
        path = ".".join(["level"] * 100) + ".value"
        assert DictUtils.get_nested(data, path) == "deep"

    def test_large_dict_merge(self):
        """测试：大字典合并"""
        dict1 = {f"key{i}": i for i in range(1000)}
        dict2 = {f"key{i}": i * 2 for i in range(500, 1500)}
        result = DictUtils.merge(dict1, dict2)
        assert len(result) == 1500
        assert result["key100"] == 100  # 来自dict1
        assert result["key1200"] == 2400  # 来自dict2