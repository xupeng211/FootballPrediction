"""
Auto-generated tests for src.utils.dict_utils module
"""

import pytest
from src.utils.dict_utils import DictUtils


class TestDictUtils:
    """测试字典处理工具类"""

    # Deep merge tests
    def test_deep_merge_simple(self):
        """测试简单字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        dict1 = {"a": 1, "b": {"x": 10, "y": 20}}
        dict2 = {"b": {"y": 30, "z": 40}, "c": 3}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": {"x": 10, "y": 30, "z": 40}, "c": 3}
        assert result == expected

    def test_deep_merge_empty_dict1(self):
        """测试第一个字典为空"""
        dict1 = {}
        dict2 = {"a": 1, "b": 2}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == dict2

    def test_deep_merge_empty_dict2(self):
        """测试第二个字典为空"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == dict1

    def test_deep_merge_both_empty(self):
        """测试两个字典都为空"""
        result = DictUtils.deep_merge({}, {})
        assert result == {}

    def test_deep_merge_preserves_original(self):
        """测试原始字典不被修改"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"y": 20}, "c": 3}
        original_dict1 = dict1.copy()
        original_dict2 = dict2.copy()

        DictUtils.deep_merge(dict1, dict2)

        assert dict1 == original_dict1
        assert dict2 == original_dict2

    def test_deep_merge_multiple_levels(self):
        """测试多层级嵌套合并"""
        dict1 = {"level1": {"level2": {"level3": {"a": 1}}}}
        dict2 = {"level1": {"level2": {"level3": {"b": 2}, "other": 3}}}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"level1": {"level2": {"level3": {"a": 1, "b": 2}, "other": 3}}}
        assert result == expected

    @pytest.mark.parametrize("dict1,dict2,expected", [
        ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
        ({"a": 1}, {"a": 2}, {"a": 2}),
        ({"a": {"b": 1}}, {"a": {"c": 2}}, {"a": {"b": 1, "c": 2}}),
        ({"a": {"b": 1}}, {"a": {"b": 2}}, {"a": {"b": 2}}),
        ({}, {"a": 1}, {"a": 1}),
        ({"a": 1}, {}, {"a": 1}),
    ])
    def test_deep_merge_parametrized(self, dict1, dict2, expected):
        """测试深度合并参数化"""
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == expected

    # Flatten dict tests
    def test_flatten_dict_simple(self):
        """测试简单字典扁平化"""
        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.flatten_dict(d)
        assert result == d

    def test_flatten_dict_nested(self):
        """测试嵌套字典扁平化"""
        d = {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
        result = DictUtils.flatten_dict(d)
        expected = {"a": 1, "b.x": 10, "b.y": 20, "c": 3}
        assert result == expected

    def test_flatten_dict_multiple_levels(self):
        """测试多层级字典扁平化"""
        d = {"level1": {"level2": {"level3": "value"}}}
        result = DictUtils.flatten_dict(d)
        expected = {"level1.level2.level3": "value"}
        assert result == expected

    def test_flatten_dict_mixed(self):
        """测试混合字典扁平化"""
        d = {
            "simple": "value",
            "nested": {"a": 1, "b": {"c": 2}},
            "another": "simple"
        }
        result = DictUtils.flatten_dict(d)
        expected = {
            "simple": "value",
            "nested.a": 1,
            "nested.b.c": 2,
            "another": "simple"
        }
        assert result == expected

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        result = DictUtils.flatten_dict({})
        assert result == {}

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符"""
        d = {"a": {"b": "value"}}
        result = DictUtils.flatten_dict(d, sep="_")
        expected = {"a_b": "value"}
        assert result == expected

    def test_flatten_dict_parent_key(self):
        """测试带父键的扁平化"""
        d = {"x": 1, "y": {"z": 2}}
        result = DictUtils.flatten_dict(d, parent_key="prefix")
        expected = {"prefix.x": 1, "prefix.y.z": 2}
        assert result == expected

    def test_flatten_dict_preserves_original(self):
        """测试原始字典不被修改"""
        d = {"a": {"b": 1}, "c": 2}
        original = d.copy()
        DictUtils.flatten_dict(d)
        assert d == original

    @pytest.mark.parametrize("d,expected", [
        ({"a": 1}, {"a": 1}),
        ({"a": {"b": 2}}, {"a.b": 2}),
        ({"a": {"b": {"c": 3}}}, {"a.b.c": 3}),
        ({"a": 1, "b": {"c": 2}}, {"a": 1, "b.c": 2}),
        ({}, {}),
    ])
    def test_flatten_dict_parametrized(self, d, expected):
        """测试字典扁平化参数化"""
        result = DictUtils.flatten_dict(d)
        assert result == expected

    # Filter none values tests
    def test_filter_none_values_simple(self):
        """测试简单None值过滤"""
        d = {"a": 1, "b": None, "c": 3, "d": None}
        result = DictUtils.filter_none_values(d)
        expected = {"a": 1, "c": 3}
        assert result == expected

    def test_filter_none_values_no_none(self):
        """测试没有None值的字典"""
        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.filter_none_values(d)
        assert result == d

    def test_filter_none_values_all_none(self):
        """测试全为None值的字典"""
        d = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_empty(self):
        """测试空字典"""
        result = DictUtils.filter_none_values({})
        assert result == {}

    def test_filter_none_values_nested_dicts_unchanged(self):
        """测试嵌套字典保持不变"""
        d = {"a": None, "b": {"x": 1, "y": None}, "c": 3}
        result = DictUtils.filter_none_values(d)
        expected = {"b": {"x": 1, "y": None}, "c": 3}
        assert result == expected

    def test_filter_none_values_preserves_original(self):
        """测试原始字典不被修改"""
        d = {"a": 1, "b": None, "c": {"d": None}}
        original = d.copy()
        DictUtils.filter_none_values(d)
        assert d == original

    @pytest.mark.parametrize("d,expected", [
        ({"a": 1, "b": None}, {"a": 1}),
        ({"a": None, "b": None}, {}),
        ({"a": 1, "b": 2}, {"a": 1, "b": 2}),
        ({}, {}),
        ({"nested": {"a": None}}, {"nested": {"a": None}}),
    ])
    def test_filter_none_values_parametrized(self, d, expected):
        """测试None值过滤参数化"""
        result = DictUtils.filter_none_values(d)
        assert result == expected

    # Integration tests
    def test_dict_operations_workflow(self):
        """测试字典操作工作流"""
        # 原始数据
        data1 = {"config": {"db": {"host": "localhost", "port": 5432}}, "cache": {"ttl": 3600}}
        data2 = {"config": {"db": {"port": 3306, "name": "myapp"}}, "cache": None, "new": "value"}

        # 合并配置
        merged = DictUtils.deep_merge(data1, data2)
        expected_merged = {
            "config": {"db": {"host": "localhost", "port": 3306, "name": "myapp"}},
            "cache": None,
            "new": "value"
        }
        assert merged == expected_merged

        # 过滤None值
        filtered = DictUtils.filter_none_values(merged)
        expected_filtered = {
            "config": {"db": {"host": "localhost", "port": 3306, "name": "myapp"}},
            "new": "value"
        }
        assert filtered == expected_filtered

        # 扁平化配置
        flattened = DictUtils.flatten_dict(filtered)
        assert "config.db.host" in flattened
        assert flattened["config.db.port"] == 3306
        assert flattened["new"] == "value"

    def test_complex_nested_scenario(self):
        """测试复杂嵌套场景"""
        deep_dict = {
            "app": {
                "name": "FootballPrediction",
                "settings": {
                    "database": {
                        "primary": {"host": "localhost", "port": 5432},
                        "replica": {"host": "backup", "port": 5432}
                    },
                    "cache": {"redis": {"url": "redis://localhost:6379"}}
                }
            }
        }

        # 扁平化
        flat = DictUtils.flatten_dict(deep_dict)
        assert flat["app.name"] == "FootballPrediction"
        assert flat["app.settings.database.primary.host"] == "localhost"

        # 测试合并
        override = {"app": {"settings": {"database": {"primary": {"port": 3306}}}}}
        merged = DictUtils.deep_merge(deep_dict, override)
        assert merged["app"]["settings"]["database"]["primary"]["port"] == 3306
        assert merged["app"]["settings"]["database"]["primary"]["host"] == "localhost"

    def test_edge_case_combinations(self):
        """测试边界情况组合"""
        # 测试各种特殊组合
        test_cases = [
            ({}, {}, {}),
            ({"a": None}, {}, {"a": None}),  # None值应该保留
            ({"a": {"b": None}}, {"a": {"c": 1}}, {"a": {"b": None, "c": 1}}),
            ({"a": [1, 2]}, {"a": [3]}, {"a": [3]}),  # 列表直接覆盖
        ]

        for dict1, dict2, expected_merged in test_cases:
            merged = DictUtils.deep_merge(dict1, dict2)
            assert merged == expected_merged

    def test_performance_considerations(self):
        """测试性能考虑"""
        # 测试大字典处理
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        nested_large = {"nested": large_dict}

        # 扁平化大字典
        flat_large = DictUtils.flatten_dict(nested_large)
        assert len(flat_large) == 1000
        assert "nested.key_0" in flat_large
        assert "nested.key_999" in flat_large

        # 合并大字典
        large_dict2 = {f"key_{i}": f"new_value_{i}" for i in range(500, 1500)}
        merged_large = DictUtils.deep_merge(large_dict, large_dict2)
        assert len(merged_large) == 1500
        assert merged_large["key_0"] == "value_0"
        assert merged_large["key_500"] == "new_value_500"

    def test_type_consistency(self):
        """测试类型一致性"""
        # 确保函数返回正确的类型
        d = {"a": 1, "b": {"c": 2}}

        merged = DictUtils.deep_merge(d, {"d": 3})
        assert isinstance(merged, dict)

        flattened = DictUtils.flatten_dict(d)
        assert isinstance(flattened, dict)

        filtered = DictUtils.filter_none_values(d)
        assert isinstance(filtered, dict)