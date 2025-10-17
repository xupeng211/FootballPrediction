#!/usr/bin/env python3
"""
增强辅助工具测试
目标：将helpers覆盖率从50%提升到80%+
"""

import pytest
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestHelpersEnhanced:
    """增强辅助工具测试"""

    def test_deep_get_nested_dict(self):
        """测试深度获取嵌套字典值"""
        from src.utils.helpers import deep_get

        data = {
            "level1": {"level2": {"level3": "value", "null_value": None}},
            "list_data": [1, 2, {"nested": "item"}],
        }

        # 测试正常获取
        assert deep_get(data, "level1.level2.level3") == "value"
        assert deep_get(data, ["level1", "level2", "level3"]) == "value"

        # 测试获取不存在的键
        assert deep_get(data, "level1.nonexistent") is None
        assert deep_get(data, "level1.nonexistent", "default") == "default"

        # 测试获取null值
        assert deep_get(data, "level1.level2.null_value") is None

        # 测试列表索引
        assert deep_get(data, "list_data.0") == 1
        assert deep_get(data, "list_data.2.nested") == "item"

    def test_deep_set_nested_dict(self):
        """测试深度设置嵌套字典值"""
        from src.utils.helpers import deep_set

        data = {}

        # 设置嵌套值
        deep_set(data, "level1.level2.level3", "value")
        assert data["level1"]["level2"]["level3"] == "value"

        # 设置数组索引
        deep_set(data, "list.0", "first")
        assert data["list"][0] == "first"

        # 覆盖已有值
        deep_set(data, "level1.level2.level3", "new_value")
        assert data["level1"]["level2"]["level3"] == "new_value"

    def test_chunk_list(self):
        """测试列表分块"""
        from src.utils.helpers import chunk_list

        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        # 测试平均分块
        chunks = chunk_list(data, 3)
        assert len(chunks) == 4
        assert chunks[0] == [1, 2, 3]
        assert chunks[3] == [10]

        # 测试单个大块
        chunks = chunk_list(data, 20)
        assert len(chunks) == 1
        assert chunks[0] == data

        # 测试空列表
        chunks = chunk_list([], 3)
        assert len(chunks) == 0

    def test_flatten_dict(self):
        """测试扁平化字典"""
        from src.utils.helpers import flatten_dict

        data = {"a": {"b": {"c": 1}, "d": 2}, "e": 3}

        flattened = flatten_dict(data)
        assert flattened["a.b.c"] == 1
        assert flattened["a.d"] == 2
        assert flattened["e"] == 3

        # 测试自定义分隔符
        flattened = flatten_dict(data, separator="_")
        assert flattened["a_b_c"] == 1

    def test_merge_dicts(self):
        """测试合并字典"""
        from src.utils.helpers import merge_dicts

        dict1 = {"a": 1, "b": 2, "c": {"nested": 1}}
        dict2 = {"b": 3, "d": 4, "c": {"nested": 2, "new": 1}}

        merged = merge_dicts(dict1, dict2)
        assert merged["a"] == 1
        assert merged["b"] == 3  # dict2覆盖
        assert merged["d"] == 4
        assert merged["c"]["nested"] == 2  # 深度合并
        assert merged["c"]["new"] == 1

    def test_remove_none_values(self):
        """测试移除None值"""
        from src.utils.helpers import remove_none_values

        data = {"a": 1, "b": None, "c": {"d": None, "e": 2, "f": None}, "g": None}

        cleaned = remove_none_values(data)
        assert "a" in cleaned
        assert "b" not in cleaned
        assert "g" not in cleaned
        assert "d" not in cleaned["c"]
        assert "e" in cleaned["c"]

    def test_pick_dict_keys(self):
        """测试选择字典键"""
        from src.utils.helpers import pick_dict_keys

        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["a", "c"]

        picked = pick_dict_keys(data, keys)
        assert picked == {"a": 1, "c": 3}

        # 测试不存在的键
        keys = ["a", "x"]
        picked = pick_dict_keys(data, keys)
        assert picked == {"a": 1}

    def test_omit_dict_keys(self):
        """测试排除字典键"""
        from src.utils.helpers import omit_dict_keys

        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["b", "d"]

        omitted = omit_dict_keys(data, keys)
        assert omitted == {"a": 1, "c": 3}

    def test_rename_dict_keys(self):
        """测试重命名字典键"""
        from src.utils.helpers import rename_dict_keys

        data = {"old_name": 1, "b": 2}
        mapping = {"old_name": "new_name"}

        renamed = rename_dict_keys(data, mapping)
        assert renamed["new_name"] == 1
        assert renamed["b"] == 2
        assert "old_name" not in renamed

    def test_safe_cast(self):
        """测试安全类型转换"""
        from src.utils.helpers import safe_cast

        # 测试整数转换
        assert safe_cast("123", int) == 123
        assert safe_cast("invalid", int, 0) == 0

        # 测试浮点转换
        assert safe_cast("123.45", float) == 123.45
        assert safe_cast("invalid", float, 0.0) == 0.0

        # 测试布尔转换
        assert safe_cast("true", bool) is True
        assert safe_cast("false", bool) is False

        # 测试列表转换
        assert safe_cast("a,b,c", list) == ["a", "b", "c"]

    def test_retry_function(self):
        """测试重试函数"""
        from src.utils.helpers import retry

        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Fail")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 3

    def test_measure_time(self):
        """测试测量执行时间"""
        from src.utils.helpers import measure_time
        import time

        @measure_time()
        def slow_function():
            time.sleep(0.01)
            return "done"

        result, duration = slow_function()
        assert result == "done"
        assert duration > 0.01

    def test_cache_result(self):
        """测试缓存结果"""
        from src.utils.helpers import cache_result

        call_count = 0

        @cache_result(max_size=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用相同参数，应使用缓存
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # 没有增加

        # 调用不同参数
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    def test_debounce(self):
        """测试防抖功能"""
        from src.utils.helpers import debounce
        import time

        call_count = 0

        @debounce(delay=0.1)
        def debounced_function():
            nonlocal call_count
            call_count += 1

        # 快速调用多次
        debounced_function()
        debounced_function()
        debounced_function()

        # 等待防抖延迟
        time.sleep(0.15)

        # 再次调用
        debounced_function()

        time.sleep(0.15)

        # 应该只执行最后一次
        assert call_count == 2

    def test_throttle(self):
        """测试节流功能"""
        from src.utils.helpers import throttle
        import time

        call_count = 0

        @throttle(rate=2)  # 每秒最多2次
        def throttled_function():
            nonlocal call_count
            call_count += 1

        # 快速调用多次
        for _ in range(10):
            throttled_function()
            time.sleep(0.05)

        # 应该只执行部分调用
        assert call_count <= 2
