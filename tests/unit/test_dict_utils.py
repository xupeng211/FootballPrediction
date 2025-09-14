"""
单元测试：字典工具模块

测试DictUtils类的所有方法，确保字典处理功能正确性。
"""

from src.utils.dict_utils import DictUtils


class TestDictUtils:
    """测试字典工具类"""

    def test_deep_merge_simple(self):
        """测试简单字典深度合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

    def test_deep_merge_overlap_shallow(self):
        """测试有重叠键的浅层合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

    def test_deep_merge_nested(self):
        """测试嵌套字典的深度合并"""
        dict1 = {"user": {"name": "John", "age": 30}}
        dict2 = {"user": {"email": "john@example.com", "age": 31}}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"user": {"name": "John", "email": "john@example.com", "age": 31}}
        assert result == expected

    def test_deep_merge_complex_nesting(self):
        """测试复杂嵌套结构的合并"""
        dict1 = {
            "api": {
                "settings": {"timeout": 30, "retries": 3},
                "endpoints": {"auth": "/auth"},
            }
        }
        dict2 = {"api": {"settings": {"timeout": 60}, "endpoints": {"data": "/data"}}}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "api": {
                "settings": {"timeout": 60, "retries": 3},
                "endpoints": {"auth": "/auth", "data": "/data"},
            }
        }
        assert result == expected

    def test_deep_merge_immutable(self):
        """测试合并不会修改原字典"""
        dict1 = {"a": {"b": 1}}
        dict2 = {"a": {"c": 2}}
        original_dict1 = {"a": {"b": 1}}

        result = DictUtils.deep_merge(dict1, dict2)

        # 原字典不应该被修改
        assert dict1 == original_dict1
        # 结果应该包含合并的数据
        assert result == {"a": {"b": 1, "c": 2}}

    def test_flatten_dict_simple(self):
        """测试简单字典扁平化"""
        data = {"user": {"name": "John", "age": 30}}
        result = DictUtils.flatten_dict(data)
        expected = {"user.name": "John", "user.age": 30}
        assert result == expected

    def test_flatten_dict_deep_nesting(self):
        """测试深层嵌套字典扁平化"""
        data = {"api": {"response": {"data": {"items": [1, 2, 3]}}}}
        result = DictUtils.flatten_dict(data)
        expected = {"api.response.data.items": [1, 2, 3]}
        assert result == expected

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符的扁平化"""
        data = {"user": {"name": "John"}}
        result = DictUtils.flatten_dict(data, sep="_")
        expected = {"user_name": "John"}
        assert result == expected

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        result = DictUtils.flatten_dict({})
        assert result == {}

    def test_flatten_dict_no_nesting(self):
        """测试没有嵌套的字典"""
        data = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.flatten_dict(data)
        assert result == data

    def test_filter_none_values_basic(self):
        """测试基本的None值过滤"""
        data = {"name": "John", "age": None, "email": "john@example.com", "phone": None}
        result = DictUtils.filter_none_values(data)
        expected = {"name": "John", "email": "john@example.com"}
        assert result == expected

    def test_filter_none_values_all_none(self):
        """测试全为None值的字典"""
        data = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(data)
        assert result == {}

    def test_filter_none_values_no_none(self):
        """测试没有None值的字典"""
        data = {"name": "John", "age": 30, "active": True}
        result = DictUtils.filter_none_values(data)
        assert result == data

    def test_filter_none_values_empty_dict(self):
        """测试空字典的None值过滤"""
        result = DictUtils.filter_none_values({})
        assert result == {}

    def test_filter_none_values_falsy_but_not_none(self):
        """测试保留其他假值但过滤None"""
        data = {
            "zero": 0,
            "empty_str": "",
            "false": False,
            "none": None,
            "empty_list": [],
        }
        result = DictUtils.filter_none_values(data)
        expected = {"zero": 0, "empty_str": "", "false": False, "empty_list": []}
        assert result == expected


class TestDictUtilsEdgeCases:
    """测试字典工具的边界情况"""

    def test_deep_merge_none_handling(self):
        """测试深度合并的None处理"""
        dict1 = {"a": 1}
        dict2 = {"a": None}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": None}
        assert result == expected

    def test_deep_merge_empty_dicts(self):
        """测试空字典的深度合并"""
        result = DictUtils.deep_merge({}, {})
        assert result == {}

        result = DictUtils.deep_merge({"a": 1}, {})
        assert result == {"a": 1}

        result = DictUtils.deep_merge({}, {"b": 2})
        assert result == {"b": 2}

    def test_flatten_dict_with_lists_and_values(self):
        """测试包含列表和各种值类型的扁平化"""
        data = {
            "config": {
                "enabled": True,
                "count": 42,
                "items": ["a", "b", "c"],
                "nested": {"value": "test"},
            }
        }
        result = DictUtils.flatten_dict(data)
        expected = {
            "config.enabled": True,
            "config.count": 42,
            "config.items": ["a", "b", "c"],
            "config.nested.value": "test",
        }
        assert result == expected

    def test_flatten_dict_none_values(self):
        """测试扁平化包含None值的字典"""
        data = {"user": {"name": "John", "email": None}}
        result = DictUtils.flatten_dict(data)
        expected = {"user.name": "John", "user.email": None}
        assert result == expected

    def test_deep_merge_list_replacement(self):
        """测试列表在深度合并中的替换行为"""
        dict1 = {"items": [1, 2, 3]}
        dict2 = {"items": [4, 5]}
        result = DictUtils.deep_merge(dict1, dict2)
        # 列表应该被完全替换，不是合并
        expected = {"items": [4, 5]}
        assert result == expected

    def test_deep_merge_mixed_types(self):
        """测试不同类型值的深度合并"""
        dict1 = {"value": {"nested": True}}
        dict2 = {"value": "string"}
        result = DictUtils.deep_merge(dict1, dict2)
        # 字符串应该替换嵌套字典
        expected = {"value": "string"}
        assert result == expected
