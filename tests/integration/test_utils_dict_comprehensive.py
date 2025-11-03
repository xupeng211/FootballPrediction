#!/usr/bin/env python3
"""
Phase 3.1 - Utils模块全面测试
字典工具类comprehensive测试，快速提升覆盖率
"""

import pytest
from src.utils.dict_utils import DictUtils


class TestDictUtilsComprehensive:
    """DictUtils全面测试类"""

    def test_deep_merge_basic(self):
        """测试基本深度合并"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"y": 20}, "c": 3}
        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
        assert result              == expected

    def test_deep_merge_override(self):
        """测试深度合并覆盖"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"x": 99}, "a": 2}
        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": 2, "b": {"x": 99}}
        assert result              == expected

    def test_deep_merge_empty(self):
        """测试空字典合并"""
        assert DictUtils.deep_merge({}, {"a": 1}) == {"a": 1}
        assert DictUtils.deep_merge({"a": 1}, {}) == {"a": 1}
        assert DictUtils.deep_merge({}, {}) == {}

    def test_flatten_dict_basic(self):
        """测试基本扁平化"""
        nested = {"a": 1, "b": {"x": 10, "y": {"z": 20}}}
        result = DictUtils.flatten_dict(nested)

        expected = {"a": 1, "b.x": 10, "b.y.z": 20}
        assert result              == expected

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符扁平化"""
        nested = {"a": {"b": {"c": 1}}}
        result = DictUtils.flatten_dict(nested, sep="_")

        expected = {"a_b_c": 1}
        assert result              == expected

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        assert DictUtils.flatten_dict({}) == {}
        assert DictUtils.flatten_dict({"a": {}}) == {}

    def test_filter_none_values(self):
        """测试过滤None值"""
        data = {"a": 1, "b": None, "c": 0, "d": False, "e": ""}
        result = DictUtils.filter_none_values(data)

        expected = {"a": 1, "c": 0, "d": False, "e": ""}
        assert result              == expected

    def test_filter_empty_values(self):
        """测试过滤空值"""
        data = {"a": 1, "b": None, "c": 0, "d": [], "e": {}, "f": False}
        result = DictUtils.filter_empty_values(data)

        expected = {"a": 1, "c": 0, "f": False}
        assert result              == expected

    def test_filter_by_keys(self):
        """测试按键过滤"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["a", "c"]
        result = DictUtils.filter_by_keys(data, keys)

        expected = {"a": 1, "c": 3}
        assert result              == expected

    def test_exclude_keys(self):
        """测试排除键"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["b", "d"]
        result = DictUtils.exclude_keys(data, keys)

        expected = {"a": 1, "c": 3}
        assert result              == expected

    def test_get_nested_value_success(self):
        """测试获取嵌套值成功"""
        data = {"user": {"profile": {"name": "张三", "age": 25}}}

        assert DictUtils.get_nested_value(data, "user.profile.name") == "张三"
        assert DictUtils.get_nested_value(data, "user.profile.age") == 25

    def test_get_nested_value_default(self):
        """测试获取嵌套值默认值"""
        data = {"user": {"profile": {"name": "张三"}}}

        assert DictUtils.get_nested_value(data, "user.profile.age", 0) == 0
        assert DictUtils.get_nested_value(data, "user.address.city", "未知") == "未知"
        assert DictUtils.get_nested_value(data, "nonexistent", "默认值") == "默认值"

    def test_set_nested_value_create_path(self):
        """测试设置嵌套值创建路径"""
        data = {}
        DictUtils.set_nested_value(data, "user.profile.name", "李四")

        expected = {"user": {"profile": {"name": "李四"}}}
        assert data              == expected

    def test_set_nested_value_override(self):
        """测试设置嵌套值覆盖"""
        data = {"user": {"profile": {"name": "张三"}}}
        DictUtils.set_nested_value(data, "user.profile.name", "李四")

        expected = {"user": {"profile": {"name": "李四"}}}
        assert data              == expected

    def test_rename_keys(self):
        """测试重命名键"""
        data = {"old_name": "value1", "keep_name": "value2"}
        mapping = {"old_name": "new_name"}
        result = DictUtils.rename_keys(data, mapping)

        expected = {"new_name": "value1", "keep_name": "value2"}
        assert result              == expected

    def test_swap_keys(self):
        """测试交换键值"""
        data = {"a": 1, "b": 2}
        result = DictUtils.swap_keys(data)

        expected = {"1": "a", "2": "b"}
        assert result              == expected

    def test_invert_dict(self):
        """测试反转字典"""
        data = {"x": "a", "y": "b"}
        result = DictUtils.invert_dict(data)

        expected = {"a": "x", "b": "y"}
        assert result              == expected

    def test_pick_values(self):
        """测试提取值"""
        data = {"a": 1, "b": 2, "c": 3}
        keys = ["a", "c", "d"]
        result = DictUtils.pick_values(data, keys)

        expected = [1, 3, None]
        assert result              == expected

    def test_count_values(self):
        """测试计算值数量"""
        assert DictUtils.count_values({}) == 0
        assert DictUtils.count_values({"a": 1}) == 1
        assert DictUtils.count_values({"a": 1, "b": 2, "c": 3}) == 3

    def test_is_empty(self):
        """测试检查字典是否为空"""
        assert DictUtils.is_empty(None) is True
        assert DictUtils.is_empty({}) is True
        assert DictUtils.is_empty({"a": 1}) is False

    def test_merge_list(self):
        """测试合并字典列表"""
        dicts = [{"a": 1}, {"b": 2}, {"a": 3, "c": 4}]
        result = DictUtils.merge_list(dicts)

        expected = {"a": 3, "b": 2, "c": 4}
        assert result              == expected

    def test_merge_list_with_non_dict(self):
        """测试合并包含非字典的列表"""
        dicts = [{"a": 1}, "not_a_dict", {"b": 2}, None]
        result = DictUtils.merge_list(dicts)

        expected = {"a": 1, "b": 2}
        assert result              == expected

    def test_chunk_dict(self):
        """测试字典分块"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
        chunks = DictUtils.chunk_dict(data, 2)

        expected = [{"a": 1, "b": 2}, {"c": 3, "d": 4}, {"e": 5}]
        assert chunks              == expected

    def test_sort_keys(self):
        """测试按键排序"""
        data = {"c": 3, "a": 1, "b": 2}
        result = DictUtils.sort_keys(data)

        expected = {"a": 1, "b": 2, "c": 3}
        assert result              == expected

    def test_sort_keys_reverse(self):
        """测试按键倒序"""
        data = {"c": 3, "a": 1, "b": 2}
        result = DictUtils.sort_keys(data, reverse=True)

        expected = {"c": 3, "b": 2, "a": 1}
        assert result              == expected

    def test_group_by_first_char(self):
        """测试按首字母分组"""
        data = {"apple": 1, "banana": 2, "cherry": 3, "apricot": 4}
        result = DictUtils.group_by_first_char(data)

        expected = {"A": {"apple": 1, "apricot": 4}, "B": {"banana": 2}, "C": {"cherry": 3}}
        assert result              == expected

    def test_validate_required_keys_success(self):
        """测试验证必需键成功"""
        data = {"a": 1, "b": 2, "c": 3}
        required = ["a", "b"]
        missing = DictUtils.validate_required_keys(data, required)

        assert missing              == []

    def test_validate_required_keys_missing(self):
        """测试验证必需键缺失"""
        data = {"a": 1, "b": 2}
        required = ["a", "c", "d"]
        missing = DictUtils.validate_required_keys(data, required)

        assert missing              == ["c", "d"]

    def test_convert_keys_case_lower(self):
        """测试转换为小写"""
        data = {"A": 1, "B": 2, "C": 3}
        result = DictUtils.convert_keys_case(data, "lower")

        expected = {"a": 1, "b": 2, "c": 3}
        assert result              == expected

    def test_convert_keys_case_upper(self):
        """测试转换为大写"""
        data = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.convert_keys_case(data, "upper")

        expected = {"A": 1, "B": 2, "C": 3}
        assert result              == expected

    def test_convert_keys_case_title(self):
        """测试转换为标题格式"""
        data = {"hello_world": 1, "foo_bar": 2}
        result = DictUtils.convert_keys_case(data, "title")

        expected = {"Hello_World": 1, "Foo_Bar": 2}
        assert result              == expected

    def test_convert_keys_case_invalid(self):
        """测试无效大小写转换"""
        data = {"a": 1, "b": 2}
        result = DictUtils.convert_keys_case(data, "invalid")

        assert result              == data

    def test_deep_clone(self):
        """测试深度克隆"""
        original = {"a": 1, "b": {"x": [1, 2, 3]}}
        cloned = DictUtils.deep_clone(original)

        assert cloned              == original
        assert cloned is not original
        assert cloned["b"] is not original["b"]
        assert cloned["b"]["x"] is not original["b"]["x"]

    def test_all_methods_exist(self):
        """测试所有方法都存在"""
        methods = [
            "deep_merge",
            "flatten_dict",
            "filter_none_values",
            "filter_empty_values",
            "filter_by_keys",
            "exclude_keys",
            "get_nested_value",
            "set_nested_value",
            "rename_keys",
            "swap_keys",
            "invert_dict",
            "pick_values",
            "count_values",
            "is_empty",
            "merge_list",
            "chunk_dict",
            "sort_keys",
            "group_by_first_char",
            "validate_required_keys",
            "convert_keys_case",
            "deep_clone",
        ]

        for method in methods:
            assert hasattr(DictUtils, method), f"方法 {method} 不存在"


def test_dict_utils_comprehensive_suite(client, client, client, client, client, client):
    """DictUtils综合测试套件"""
    # 快速验证核心功能
    assert DictUtils.deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
    assert DictUtils.filter_none_values({"a": 1, "b": None}) == {"a": 1}
    assert DictUtils.is_empty({}) is True
    assert DictUtils.count_values({"a": 1, "b": 2}) == 2

    print("✅ DictUtils综合测试套件通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
