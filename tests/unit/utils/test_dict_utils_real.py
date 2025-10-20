"""
DictUtils 实际可用方法测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.dict_utils import DictUtils


class TestDictUtilsReal:
    """测试DictUtils实际可用的方法"""

    def test_deep_merge_simple(self):
        """测试简单字典合并"""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(d1, d2)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        d1 = {"a": {"x": 1}, "b": 2}
        d2 = {"a": {"y": 2}, "c": 3}
        result = DictUtils.deep_merge(d1, d2)
        assert result == {"a": {"x": 1, "y": 2}, "b": 2, "c": 3}

    def test_deep_merge_empty(self):
        """测试空字典合并"""
        assert DictUtils.deep_merge({}, {"a": 1}) == {"a": 1}
        assert DictUtils.deep_merge({"a": 1}, {}) == {"a": 1}
        assert DictUtils.deep_merge({}, {}) == {}

    def test_deep_merge_preserve_original(self):
        """测试不修改原字典"""
        d1 = {"a": 1}
        d2 = {"b": 2}
        result = DictUtils.deep_merge(d1, d2)
        assert d1 == {"a": 1}
        assert d2 == {"b": 2}
        assert result == {"a": 1, "b": 2}

    def test_deep_merge_override_types(self):
        """测试不同类型值的覆盖"""
        d1 = {"a": {"nested": 1}}
        d2 = {"a": "string_value"}
        result = DictUtils.deep_merge(d1, d2)
        assert result == {"a": "string_value"}

    def test_flatten_dict_simple(self):
        """测试简单字典扁平化"""
        d = {"a": 1, "b": 2}
        result = DictUtils.flatten_dict(d)
        assert result == {"a": 1, "b": 2}

    def test_flatten_dict_nested(self):
        """测试嵌套字典扁平化"""
        d = {"a": {"x": 1, "y": {"z": 2}}, "b": 3}
        result = DictUtils.flatten_dict(d)
        assert result == {"a.x": 1, "a.y.z": 2, "b": 3}

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        assert DictUtils.flatten_dict({}) == {}

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符"""
        d = {"a": {"x": 1}}
        result = DictUtils.flatten_dict(d, sep="_")
        assert result == {"a_x": 1}

    def test_filter_none_values(self):
        """测试过滤None值"""
        d = {"a": 1, "b": None, "c": 0, "d": False, "e": ""}
        result = DictUtils.filter_none_values(d)
        assert result == {"a": 1, "c": 0, "d": False, "e": ""}

    def test_filter_none_values_all_none(self):
        """测试全None字典"""
        d = {"a": None, "b": None}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_empty(self):
        """测试空字典"""
        assert DictUtils.filter_none_values({}) == {}

    @pytest.mark.parametrize(
        "d1,d2,expected",
        [
            ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
            ({"a": 1}, {"a": 2}, {"a": 2}),
            ({"a": {"x": 1}}, {"a": {"y": 2}}, {"a": {"x": 1, "y": 2}}),
            ({}, {"a": 1}, {"a": 1}),
            ({"a": 1}, {}, {"a": 1}),
        ],
    )
    def test_deep_merge_parametrized(self, d1, d2, expected):
        """参数化测试深度合并"""
        assert DictUtils.deep_merge(d1, d2) == expected

    def test_complex_merge_scenario(self):
        """测试复杂合并场景"""
        config1 = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {"username": "admin", "password": "old_password"},
            },
            "logging": {"level": "INFO"},
        }

        config2 = {
            "database": {
                "credentials": {"password": "new_password", "database": "new_db"},
                "pool_size": 10,
            },
            "cache": {"type": "redis"},
        }

        result = DictUtils.deep_merge(config1, config2)
        expected = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "username": "admin",
                    "password": "new_password",
                    "database": "new_db",
                },
                "pool_size": 10,
            },
            "logging": {"level": "INFO"},
            "cache": {"type": "redis"},
        }

        assert result == expected

    def test_flatten_dict_with_none(self):
        """测试扁平化包含None的字典"""
        d = {"a": {"x": None, "y": 1}, "b": None}
        result = DictUtils.flatten_dict(d)
        assert result == {"a.x": None, "a.y": 1, "b": None}

    def test_deep_merge_with_lists(self):
        """测试合并包含列表的字典"""
        d1 = {"a": [1, 2], "b": {"x": 1}}
        d2 = {"a": [3, 4], "b": {"y": 2}}
        result = DictUtils.deep_merge(d1, d2)
        # 列表应该被覆盖，不是合并
        assert result == {"a": [3, 4], "b": {"x": 1, "y": 2}}

    def test_performance_large_dict(self):
        """测试大字典性能"""
        import time

        # 创建大字典
        d1 = {f"key_{i}": {"nested": i} for i in range(1000)}
        d2 = {f"key_{i}": {"value": i * 2} for i in range(500, 1500)}

        # 测试合并性能
        start = time.time()
        result = DictUtils.deep_merge(d1, d2)
        duration = time.time() - start

        assert len(result) == 1500
        assert duration < 0.1  # 应该在100ms内完成

    def test_deep_immutable_check(self):
        """测试深度合并的不可变性"""
        d1 = {"a": {"b": 1}}
        d2 = {"a": {"c": 2}}
        original_d1 = {"a": {"b": 1}}

        result = DictUtils.deep_merge(d1, d2)

        # 原字典不应被修改
        assert d1 == original_d1
        # 结果应该是新字典
        assert result == {"a": {"b": 1, "c": 2}}
        # 修改结果不应影响原字典
        result["a"]["b"] = 999
        assert d1["a"]["b"] == 1
