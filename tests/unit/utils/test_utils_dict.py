"""
测试src/utils/dict_utils.py模块
快速提升测试覆盖率的针对性测试
"""

from src.utils.dict_utils import DictUtils


class TestDictUtils:
    """测试DictUtils类的所有方法"""

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
        expected = {"a": {"x": 1, "y": 3, "z": 4}, "b": 3, "c": 5}
        assert result == expected

    def test_deep_merge_override_with_non_dict(self):
        """测试用非字典值覆盖字典值"""
        dict1 = {"a": {"x": 1}, "b": 2}
        dict2 = {"a": "string", "b": 3}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": "string", "b": 3}

    def test_deep_merge_deep_nesting(self):
        """测试深层嵌套合并"""
        dict1 = {"a": {"b": {"c": 1, "d": 2}}}
        dict2 = {"a": {"b": {"c": 3, "e": 4}}}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": {"b": {"c": 3, "d": 2, "e": 4}}}
        assert result == expected

    def test_deep_merge_empty_dicts(self):
        """测试空字典合并"""
        result = DictUtils.deep_merge({}, {})
        assert result == {}

        result = DictUtils.deep_merge({"a": 1}, {})
        assert result == {"a": 1}

        result = DictUtils.deep_merge({}, {"a": 1})
        assert result == {"a": 1}

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

    def test_flatten_dict_deep_nesting(self):
        """测试深层嵌套扁平化"""
        d = {"a": {"b": {"c": 1, "d": 2}, "e": 3}}
        result = DictUtils.flatten_dict(d)
        assert result == {"a.b.c": 1, "a.b.d": 2, "a.e": 3}

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符的扁平化"""
        d = {"a": {"x": 1}, "b": 2}
        result = DictUtils.flatten_dict(d, sep="_")
        assert result == {"a_x": 1, "b": 2}

    def test_flatten_dict_with_parent_key(self):
        """测试带父键的扁平化"""
        d = {"x": 1, "y": {"z": 2}}
        result = DictUtils.flatten_dict(d, parent_key="parent")
        assert result == {"parent.x": 1, "parent.y.z": 2}

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        result = DictUtils.flatten_dict({})
        assert result == {}

    def test_filter_none_values_basic(self):
        """测试基本None值过滤"""
        d = {"a": 1, "b": None, "c": 3, "d": None}
        result = DictUtils.filter_none_values(d)
        assert result == {"a": 1, "c": 3}

    def test_filter_none_values_no_none(self):
        """测试无None值的字典"""
        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.filter_none_values(d)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_filter_none_values_all_none(self):
        """测试全部为None的字典"""
        d = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_mixed_types(self):
        """测试混合类型值的过滤"""
        d = {"a": 0, "b": None, "c": "", "d": False, "e": [], "f": None}
        result = DictUtils.filter_none_values(d)
        # 只过滤None，保留其他falsy值
        assert result == {"a": 0, "c": "", "d": False, "e": []}

    def test_filter_none_values_empty_dict(self):
        """测试空字典过滤"""
        result = DictUtils.filter_none_values({})
        assert result == {}
