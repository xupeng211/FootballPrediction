"""
测试字典处理工具模块
"""

from src.utils.dict_utils import DictUtils


class TestDictUtils:
    """测试DictUtils类"""

    def test_deep_merge_simple(self):
        """测试简单字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 3, "z": 4}, "c": 5}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}, "b": 3, "c": 5}

    def test_deep_merge_empty_dict1(self):
        """测试第一个字典为空"""
        dict1 = {}
        dict2 = {"a": 1, "b": 2}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 2}

    def test_deep_merge_empty_dict2(self):
        """测试第二个字典为空"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 2}

    def test_deep_merge_both_empty(self):
        """测试两个字典都为空"""
        dict1 = {}
        dict2 = {}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {}

    def test_deep_merge_with_none(self):
        """测试包含None值的合并"""
        dict1 = {"a": None, "b": 2}
        dict2 = {"a": 1, "c": None}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 2, "c": None}

    def test_deep_merge_different_types(self):
        """测试不同类型的值合并"""
        dict1 = {"a": {"x": 1}}
        dict2 = {"a": 2}  # dict2中的a不是字典
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 2}

    def test_deep_merge_complex_nested(self):
        """测试复杂嵌套结构"""
        dict1 = {"level1": {"level2": {"a": 1, "b": 2}, "c": 3}}
        dict2 = {"level1": {"level2": {"b": 4, "d": 5}, "e": 6}}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"level1": {"level2": {"a": 1, "b": 4, "d": 5}, "c": 3, "e": 6}}
        assert result == expected

    def test_deep_merge_original_unchanged(self):
        """测试原始字典不被修改"""
        dict1 = {"a": {"x": 1}}
        dict2 = {"a": {"y": 2}}
        original1 = {"a": {"x": 1}}
        original2 = {"a": {"y": 2}}

        result = DictUtils.deep_merge(dict1, dict2)

        # 原始字典不应被修改
        assert dict1 == original1
        assert dict2 == original2
        # 结果是新字典
        assert result == {"a": {"x": 1, "y": 2}}

    def test_flatten_dict_simple(self):
        """测试简单字典扁平化"""
        d = {"a": 1, "b": 2}
        result = DictUtils.flatten_dict(d)
        assert result == {"a": 1, "b": 2}

    def test_flatten_dict_nested(self):
        """测试嵌套字典扁平化"""
        d = {"a": {"x": 1, "y": 2}, "b": 3}
        result = DictUtils.flatten_dict(d)
        assert result == {"a.x": 1, "a.y": 2, "b": 3}

    def test_flatten_dict_deep_nested(self):
        """测试深层嵌套字典扁平化"""
        d = {"a": {"b": {"c": {"d": 1}}}}
        result = DictUtils.flatten_dict(d)
        assert result == {"a.b.c.d": 1}

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符"""
        d = {"a": {"x": 1}}
        result = DictUtils.flatten_dict(d, sep="_")
        assert result == {"a_x": 1}

    def test_flatten_dict_with_parent_key(self):
        """测试带父键的扁平化"""
        d = {"x": 1, "y": 2}
        result = DictUtils.flatten_dict(d, parent_key="parent")
        assert result == {"parent.x": 1, "parent.y": 2}

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        d = {}
        result = DictUtils.flatten_dict(d)
        assert result == {}

    def test_flatten_dict_with_list(self):
        """测试包含列表的字典（列表不被展开）"""
        d = {"a": [1, 2, 3], "b": {"c": 4}}
        result = DictUtils.flatten_dict(d)
        assert result == {"a": [1, 2, 3], "b.c": 4}

    def test_flatten_dict_none_values(self):
        """测试包含None值的字典"""
        d = {"a": None, "b": {"c": None}}
        result = DictUtils.flatten_dict(d)
        assert result == {"a": None, "b.c": None}

    def test_filter_none_values_with_none(self):
        """测试过滤None值"""
        d = {"a": 1, "b": None, "c": 3, "d": None}
        result = DictUtils.filter_none_values(d)
        assert result == {"a": 1, "c": 3}

    def test_filter_none_values_no_none(self):
        """测试没有None值的情况"""
        d = {"a": 1, "b": 2}
        result = DictUtils.filter_none_values(d)
        assert result == {"a": 1, "b": 2}

    def test_filter_none_values_all_none(self):
        """测试所有值都是None"""
        d = {"a": None, "b": None}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_empty(self):
        """测试空字典"""
        d = {}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_nested(self):
        """测试嵌套字典（不过滤嵌套的None）"""
        d = {"a": {"b": None}, "c": None}
        result = DictUtils.filter_none_values(d)
        assert result == {"a": {"b": None}}
