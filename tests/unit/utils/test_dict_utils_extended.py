"""
字典工具扩展测试
Extended Tests for Dict Utils

基于DictUtils实际存在的方法创建测试。
"""

import pytest
from src.utils.dict_utils import DictUtils


@pytest.mark.unit

class TestDictUtilsExtended:
    """字典工具扩展测试"""

    # ==================== deep_merge测试 ====================

    def test_deep_merge_simple(self):
        """测试：简单深度合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        _result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert _result == expected

    def test_deep_merge_nested(self):
        """测试：嵌套字典深度合并"""
        dict1 = {"a": {"x": 1, "y": 2}}
        dict2 = {"a": {"y": 99, "z": 3}}
        _result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": {"x": 1, "y": 99, "z": 3}}
        assert _result == expected

    def test_deep_merge_multiple_levels(self):
        """测试：多级深度合并"""
        dict1 = {"level1": {"level2": {"a": 1, "b": 2}}}
        dict2 = {"level1": {"level2": {"b": 99, "c": 3}}}
        _result = DictUtils.deep_merge(dict1, dict2)
        expected = {"level1": {"level2": {"a": 1, "b": 99, "c": 3}}}
        assert _result == expected

    def test_deep_merge_with_lists(self):
        """测试：包含列表的深度合并"""
        dict1 = {"a": [1, 2], "b": {"x": 1}}
        dict2 = {"a": [3, 4], "b": {"y": 2}}
        _result = DictUtils.deep_merge(dict1, dict2)
        # 列表会被覆盖
        assert _result == {"a": [3, 4], "b": {"x": 1, "y": 2}}

    def test_deep_merge_empty_dicts(self):
        """测试：空字典深度合并"""
        assert DictUtils.deep_merge({}, {}) == {}
        assert DictUtils.deep_merge({"a": 1}, {}) == {"a": 1}
        assert DictUtils.deep_merge({}, {"b": 2}) == {"b": 2}

    def test_deep_merge_original_unchanged(self):
        """测试：原字典不变"""
        dict1 = {"a": {"x": 1}}
        dict2 = {"a": {"y": 2}}
        _result = DictUtils.deep_merge(dict1, dict2)
        # 原字典不应被修改
        assert dict1 == {"a": {"x": 1}}
        assert dict2 == {"a": {"y": 2}}
        # 结果是新字典
        assert _result == {"a": {"x": 1, "y": 2}}

    # ==================== flatten_dict测试 ====================

    def test_flatten_dict_simple(self):
        """测试：简单扁平化"""
        _data = {"a": 1, "b": 2}
        _result = DictUtils.flatten_dict(data)
        assert _result == {"a": 1, "b": 2}

    def test_flatten_dict_nested(self):
        """测试：嵌套字典扁平化"""
        _data = {"a": {"b": {"c": 1}}, "x": 2}
        _result = DictUtils.flatten_dict(data)
        assert _result == {"a.b.c": 1, "x": 2}

    def test_flatten_dict_custom_separator(self):
        """测试：自定义分隔符的扁平化"""
        _data = {"a": {"b": {"c": 1}}}
        _result = DictUtils.flatten_dict(data, sep="_")
        assert _result == {"a_b_c": 1}

    def test_flatten_dict_custom_prefix(self):
        """测试：自定义前缀的扁平化"""
        _data = {"a": {"b": 1}}
        # DictUtils不支持prefix参数，但可以通过修改结果实现
        _result = DictUtils.flatten_dict(data)
        prefixed_result = {f"prefix.{k}": v for k, v in result.items()}
        assert prefixed_result == {"prefix.a.b": 1}

    def test_flatten_dict_with_none(self):
        """测试：包含None值的扁平化"""
        _data = {"a": None, "b": {"c": None}}
        _result = DictUtils.flatten_dict(data)
        assert _result == {"a": None, "b.c": None}

    def test_flatten_dict_with_empty(self):
        """测试：空字典扁平化"""
        _data = {"a": {}, "b": {"c": {}}}
        _result = DictUtils.flatten_dict(data)
        assert _result == {}

    def test_flatten_dict_complex(self):
        """测试：复杂字典扁平化"""
        _data = {
            "user": {
                "profile": {
                    "name": "John",
                    "settings": {"theme": "dark", "notifications": True},
                },
                "stats": {"login_count": 100},
            },
            "active": True,
        }
        _result = DictUtils.flatten_dict(data)
        expected = {
            "user.profile.name": "John",
            "user.profile.settings.theme": "dark",
            "user.profile.settings.notifications": True,
            "user.stats.login_count": 100,
            "active": True,
        }
        assert _result == expected

    # ==================== filter_none_values测试 ====================

    def test_filter_none_values_simple(self):
        """测试：过滤None值（简单）"""
        _data = {"a": 1, "b": None, "c": 3, "d": None}
        _result = DictUtils.filter_none_values(data)
        assert _result == {"a": 1, "c": 3}

    def test_filter_none_values_nested(self):
        """测试：过滤None值（嵌套）"""
        # filter_none_values只处理顶层，不会递归
        _data = {"a": 1, "b": {"c": None, "d": 4, "e": {"f": None, "g": 7}}, "h": None}
        _result = DictUtils.filter_none_values(data)
        # 只会过滤顶层的None值
        expected = {"a": 1, "b": {"c": None, "d": 4, "e": {"f": None, "g": 7}}}
        assert _result == expected

    def test_filter_none_values_empty(self):
        """测试：过滤空字典的None值"""
        assert DictUtils.filter_none_values({}) == {}
        assert DictUtils.filter_none_values({"a": None, "b": None}) == {}

    def test_filter_none_values_all_none(self):
        """测试：所有值都是None"""
        _data = {"a": None, "b": {"c": None, "d": None}}
        _result = DictUtils.filter_none_values(data)
        # 顶层只有a是None，b是字典
        assert _result == {"b": {"c": None, "d": None}}

    def test_filter_none_values_no_none(self):
        """测试：没有None值"""
        _data = {"a": 1, "b": "test", "c": [1, 2, 3]}
        _result = DictUtils.filter_none_values(data)
        assert _result == data

    def test_filter_none_values_preserve_types(self):
        """测试：保留其他类型（0、False、空字符串等）"""
        _data = {
            "zero": 0,
            "false": False,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
            "none": None,
        }
        _result = DictUtils.filter_none_values(data)
        expected = {
            "zero": 0,
            "false": False,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
        }
        assert _result == expected

    # ==================== 组合测试 ====================

    def test_deep_merge_then_flatten(self):
        """测试：深度合并后扁平化"""
        dict1 = {"config": {"app": {"debug": False}}}
        dict2 = {"config": {"app": {"version": "1.0"}, "db": {"host": "localhost"}}}

        # 先合并
        merged = DictUtils.deep_merge(dict1, dict2)
        assert merged == {
            "config": {
                "app": {"debug": False, "version": "1.0"},
                "db": {"host": "localhost"},
            }
        }

        # 再扁平化
        flattened = DictUtils.flatten_dict(merged)
        expected = {
            "_config.app.debug": False,
            "_config.app.version": "1.0",
            "_config.db.host": "localhost",
        }
        assert flattened == expected

    def test_flatten_then_filter_none(self):
        """测试：扁平化后过滤None"""
        _data = {
            "user": {
                "name": None,
                "email": "test@example.com",
                "profile": {"age": None, "active": True},
            }
        }

        # 先扁平化
        flattened = DictUtils.flatten_dict(data)
        assert flattened == {
            "user.name": None,
            "user.email": "test@example.com",
            "user.profile.age": None,
            "user.profile.active": True,
        }

        # 再过滤None
        filtered = DictUtils.filter_none_values(flattened)
        expected = {"user.email": "test@example.com", "user.profile.active": True}
        assert filtered == expected

    # ==================== 边界条件测试 ====================

    def test_deep_merge_none_values(self):
        """测试：深度合并None值"""
        dict1 = {"a": None}
        dict2 = {"a": {"b": 1}}
        _result = DictUtils.deep_merge(dict1, dict2)
        assert _result == {"a": {"b": 1}}

    def test_deep_merge_conflicting_types(self):
        """测试：深度合并冲突类型"""
        dict1 = {"a": {"b": 1}}
        dict2 = {"a": 2}  # dict vs int
        _result = DictUtils.deep_merge(dict1, dict2)
        assert _result == {"a": 2}  # 第二个值覆盖

    def test_large_data_performance(self):
        """测试：大数据性能"""
        # 创建一个大字典
        _data = {}
        for i in range(100):
            _data[f"section{i}"] = {
                f"subsection{j}": {"value": i * j for j in range(10)} for j in range(10)
            }

        # 测试扁平化
        import time

        start = time.time()
        _result = DictUtils.flatten_dict(data)
        duration = time.time() - start

        # 验证结果
        assert len(result) == 1000  # 100 * 10
        # 性能应该在合理范围内（< 1秒）
        assert duration < 1.0
