#!/usr/bin/env python3
"""
DictUtils 模块增强测试套件
Enhanced DictUtils Test Suite

Phase 2 - 提升核心模块覆盖率至50%+
目标：覆盖dict_utils模块的所有功能和边界情况
"""

import pytest
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from utils.dict_utils import DictUtils


@pytest.mark.unit

class TestDictUtilsEnhanced:
    """DictUtils增强测试类"""

    # === 深度合并测试 ===

    def test_deep_merge_basic(self):
        """测试基础深度合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

    def test_deep_merge_nested_basic(self):
        """测试基础嵌套合并"""
        dict1 = {"a": {"x": 1}, "b": 2}
        dict2 = {"a": {"y": 2}, "c": 3}
        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": {"x": 1, "y": 2}, "b": 2, "c": 3}
        assert result == expected

    def test_deep_merge_no_mutation(self):
        """测试不修改原始字典"""
        dict1 = {"a": 1, "b": {"x": 1}}
        dict2 = {"b": {"y": 2}, "c": 3}

        # 备份原始字典
        original_dict1 = dict1.copy()
        original_dict2 = dict2.copy()

        result = DictUtils.deep_merge(dict1, dict2)

        # 验证原始字典未被修改
        assert dict1 == original_dict1
        assert dict2 == original_dict2
        # 验证返回的是新字典
        assert dict1 is not result
        assert dict2 is not result

    def test_deep_merge_empty_dicts(self):
        """测试空字典合并"""
        dict1 = {}
        dict2 = {}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {}

    def test_deep_merge_first_empty(self):
        """测试第一个字典为空"""
        dict1 = {}
        dict2 = {"a": 1, "b": 2}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 2}

    def test_deep_merge_second_empty(self):
        """测试第二个字典为空"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 2}

    def test_deep_merge_nested_multiple_levels(self):
        """测试多级嵌套合并"""
        dict1 = {"a": {"b": {"c": 1}}}
        dict2 = {"a": {"b": {"d": 2}}}
        result = DictUtils.deep_merge(dict1, dict2)

        expected = {"a": {"b": {"c": 1, "d": 2}}}
        assert result == expected

    def test_deep_merge_conflicting_types_dict_vs_value(self):
        """测试冲突类型：字典 vs 值"""
        dict1 = {"a": {"x": 1}}
        dict2 = {"a": 2}
        result = DictUtils.deep_merge(dict1, dict2)

        # 值应该覆盖字典
        assert result == {"a": 2}

    def test_deep_merge_conflicting_types_value_vs_dict(self):
        """测试冲突类型：值 vs 字典"""
        dict1 = {"a": 1}
        dict2 = {"a": {"x": 2}}
        result = DictUtils.deep_merge(dict1, dict2)

        # 字典应该覆盖值
        assert result == {"a": {"x": 2}}

    def test_deep_merge_complex_nested_structure(self):
        """测试复杂嵌套结构"""
        dict1 = {
            "level1": {
                "level2": {"data": [1, 2, 3], "config": {"option1": True}},
                "other": "value1",
            }
        }
        dict2 = {
            "level1": {
                "level2": {"config": {"option2": False}, "new_field": "added"},
                "new_other": "value2",
            }
        }
        result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "level1": {
                "level2": {
                    "data": [1, 2, 3],  # 保持原有
                    "config": {"option1": True, "option2": False},  # 合并
                    "new_field": "added",  # 新增
                },
                "other": "value1",  # 保持原有
                "new_other": "value2",  # 新增
            }
        }
        assert result == expected

    def test_deep_merge_with_none_values(self):
        """测试包含None值的合并"""
        dict1 = {"a": 1, "b": None}
        dict2 = {"b": 2, "c": None}
        result = DictUtils.deep_merge(dict1, dict2)

        # None值应该被正常处理
        assert result == {"a": 1, "b": 2, "c": None}

    # === 扁平化字典测试 ===

    def test_flatten_dict_basic(self):
        """测试基础扁平化"""
        d = {"a": 1, "b": {"c": 2}}
        result = DictUtils.flatten_dict(d)

        expected = {"a": 1, "b.c": 2}
        assert result == expected

    def test_flatten_dict_nested(self):
        """测试多层嵌套扁平化"""
        d = {"a": {"b": {"c": {"d": 1}}}}
        result = DictUtils.flatten_dict(d)

        expected = {"a.b.c.d": 1}
        assert result == expected

    def test_flatten_dict_mixed_types(self):
        """测试混合类型扁平化"""
        d = {"a": 1, "b": {"c": 2, "d": {"e": 3}}, "f": {"g": 4}}
        result = DictUtils.flatten_dict(d)

        expected = {"a": 1, "b.c": 2, "b.d.e": 3, "f.g": 4}
        assert result == expected

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符"""
        d = {"a": {"b": {"c": 1}}}
        result = DictUtils.flatten_dict(d, sep="_")

        expected = {"a_b_c": 1}
        assert result == expected

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        d = {}
        result = DictUtils.flatten_dict(d)
        assert result == {}

    def test_flatten_dict_no_nesting(self):
        """测试无嵌套字典扁平化"""
        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.flatten_dict(d)
        assert result == d

    def test_flatten_dict_with_empty_nested(self):
        """测试包含空嵌套字典"""
        d = {"a": {}, "b": {"c": 1}}
        result = DictUtils.flatten_dict(d)

        expected = {"b.c": 1}
        assert result == expected

    # === 过滤None值测试 ===

    def test_filter_none_values_basic(self):
        """测试基础None值过滤"""
        d = {"a": 1, "b": None, "c": 3, "d": None}
        result = DictUtils.filter_none_values(d)

        expected = {"a": 1, "c": 3}
        assert result == expected

    def test_filter_none_values_all_none(self):
        """测试全None值过滤"""
        d = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(d)

        assert result == {}

    def test_filter_none_values_no_none(self):
        """测试无None值"""
        d = {"a": 1, "b": 2, "c": "test"}
        result = DictUtils.filter_none_values(d)

        assert result == d

    def test_filter_none_values_empty(self):
        """测试空字典"""
        d = {}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_nested_values(self):
        """测试嵌套None值（不过滤嵌套）"""
        d = {"a": {"b": None}, "c": None}
        result = DictUtils.filter_none_values(d)

        # 只过滤顶层None值
        expected = {"a": {"b": None}}
        assert result == expected

    def test_filter_none_values_with_false_values(self):
        """测试包含假值但非None"""
        d = {"a": 0, "b": False, "c": "", "d": None, "e": []}
        result = DictUtils.filter_none_values(d)

        # 只有None被过滤
        expected = {"a": 0, "b": False, "c": "", "e": []}
        assert result == expected

    # === 边界情况和错误处理 ===

    def test_deep_merge_large_dictionaries(self):
        """测试大字典合并性能"""
        # 创建大字典
        dict1 = {f"key_{i}": {"nested": f"value_{i}"} for i in range(100)}
        dict2 = {f"key_{i}": {"additional": f"extra_{i}"} for i in range(100)}

        result = DictUtils.deep_merge(dict1, dict2)

        # 验证合并结果
        assert len(result) == 100
        for i in range(100):
            key = f"key_{i}"
            assert key in result
            assert result[key]["nested"] == f"value_{i}"
            assert result[key]["additional"] == f"extra_{i}"

    def test_flatten_dict_large_depth(self):
        """测试深度嵌套扁平化"""
        # 创建深度嵌套字典
        d = {}
        current = d
        for i in range(10):
            current["level"] = {}
            current = current["level"]
        current["value"] = "deep_value"

        result = DictUtils.flatten_dict(d)

        expected_key = ".".join(["level"] * 10) + ".value"
        assert expected_key in result
        assert result[expected_key] == "deep_value"

    def test_type_immutability(self):
        """测试类型不变性"""
        dict1 = {"a": (1, 2), "b": [3, 4]}  # 包含不可变和可变类型
        dict2 = {"a": (5, 6), "c": {7, 8}}

        result = DictUtils.deep_merge(dict1, dict2)

        # 元组应该被覆盖
        assert result["a"] == (5, 6)
        # 列表和集合保持原有
        assert result["b"] == [3, 4]
        assert result["c"] == {7, 8}

    def test_deep_merge_with_special_keys(self):
        """测试特殊键名"""
        dict1 = {"": "empty_key", "special-chars": "value1", "123numeric": "num1"}
        dict2 = {
            "": "override_empty",
            "special-chars": "value2",
            "new.special": "value3",
        }

        result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "": "override_empty",
            "special-chars": "value2",
            "123numeric": "num1",
            "new.special": "value3",
        }
        assert result == expected

    # === 性能和压力测试 ===

    def test_performance_deep_merge(self):
        """测试深度合并性能"""
        import time

        # 创建中等大小字典
        dict1 = {
            f"key_{i}": {"nested": f"value_{i}", "list": list(range(10))}
            for i in range(50)
        }
        dict2 = {
            f"key_{i}": {"additional": f"extra_{i}", "set": {i, i + 1, i + 2}}
            for i in range(50)
        }

        start_time = time.time()
        result = DictUtils.deep_merge(dict1, dict2)
        end_time = time.time()

        # 验证结果正确性
        assert len(result) == 50

        # 性能应该在合理范围内（小于1秒）
        execution_time = end_time - start_time
        assert execution_time < 1.0, f"Deep merge took too long: {execution_time}s"

    def test_memory_usage(self):
        """测试内存使用"""
        # 创建可能导致内存问题的字典
        large_dict1 = {f"key_{i}": "x" * 1000 for i in range(100)}
        large_dict2 = {f"key_{i}": "y" * 1000 for i in range(100)}

        # 执行合并
        result = DictUtils.deep_merge(large_dict1, large_dict2)

        # 验证结果大小合理
        assert len(result) == 100
        for key in result:
            assert len(result[key]) == 1000

    # === 集成测试 ===

    def test_combined_operations(self):
        """测试组合操作"""
        # 原始数据
        data = {
            "config": {
                "app": {"name": None, "version": "1.0"},
                "database": {"host": "localhost", "port": None},
            },
            "features": {"feature1": True, "feature2": None},
            "null_field": None,  # 顶层None值
        }

        # 1. 过滤None值（只过滤顶层）
        filtered = DictUtils.filter_none_values(data)

        # 验证顶层None被过滤
        assert "null_field" not in filtered
        # 验证features字典保留（因为它本身不是None）
        assert "features" in filtered

        # 2. 与新配置合并
        new_config = {"config": {"app": {"debug": True}, "cache": {"enabled": True}}}
        merged = DictUtils.deep_merge(filtered, new_config)

        # 3. 扁平化
        flattened = DictUtils.flatten_dict(merged)

        # 验证最终结果包含所有预期的键
        expected_keys = [
            "config.app.name",  # 嵌套的None不会被filter_none_values过滤
            "config.app.version",
            "config.database.host",
            "config.database.port",  # 嵌套的None不会被filter_none_values过滤
            "config.app.debug",
            "config.cache.enabled",
            "features.feature1",
            "features.feature2",  # 嵌套的None保留
        ]

        for key in expected_keys:
            assert key in flattened

        # 验证顶层None值被正确过滤
        assert "null_field" not in flattened
