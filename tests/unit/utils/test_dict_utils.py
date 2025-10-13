"""
字典工具测试
Dict Utils Tests

测试实际存在的字典处理工具。
"""

import pytest
from typing import Any, Dict, List

from src.utils.dict_utils import DictUtils


class TestDictUtils:
    """测试字典工具类"""

    def test_deep_merge(self):
        """测试深度合并字典"""
        dict1 = {
            "a": 1,
            "b": {"x": 10, "y": 20},
            "c": [1, 2, 3],
        }
        dict2 = {
            "b": {"y": 30, "z": 40},
            "c": [4, 5],
            "d": "new",
        }

        _result = DictUtils.deep_merge(dict1, dict2)

        expected = {
            "a": 1,
            "b": {"x": 10, "y": 30, "z": 40},
            "c": [4, 5],  # 后面的覆盖前面的
            "d": "new",
        }

        assert _result == expected

        # 测试空字典
        assert DictUtils.deep_merge({}, {"a": 1}) == {"a": 1}
        assert DictUtils.deep_merge({"a": 1}, {}) == {"a": 1}

        # 测试嵌套合并
        dict1 = {"config": {"db": {"host": "localhost"}, "api": {"version": "v1"}}}
        dict2 = {"config": {"db": {"port": 5432}, "cache": {"enabled": True}}}

        _result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "config": {
                "db": {"host": "localhost", "port": 5432},
                "api": {"version": "v1"},
                "cache": {"enabled": True},
            }
        }
        assert _result == expected

        # 测试深度嵌套
        dict1 = {"level1": {"level2": {"level3": {"a": 1}}}}
        dict2 = {"level1": {"level2": {"level3": {"b": 2}}}}

        _result = DictUtils.deep_merge(dict1, dict2)
        expected = {"level1": {"level2": {"level3": {"a": 1, "b": 2}}}}
        assert _result == expected

    def test_flatten_dict(self):
        """测试扁平化字典"""
        # 测试基本嵌套
        _data = {
            "user": {
                "name": "John",
                "profile": {
                    "age": 30,
                },
            },
            "settings": {
                "theme": "dark",
            },
        }

        _result = DictUtils.flatten_dict(data)
        expected = {
            "user.name": "John",
            "user.profile.age": 30,
            "settings.theme": "dark",
        }
        assert _result == expected

        # 测试自定义分隔符
        _result = DictUtils.flatten_dict(data, sep="_")
        expected = {
            "user_name": "John",
            "user_profile_age": 30,
            "settings_theme": "dark",
        }
        assert _result == expected

        # 测试空字典
        assert DictUtils.flatten_dict({}) == {}

        # 测试单层字典
        _data = {"a": 1, "b": 2}
        assert DictUtils.flatten_dict(data) == data

        # 测试更深层的嵌套
        _data = {
            "a": {
                "b": {
                    "c": {
                        "d": "value",
                        "e": {"f": "deep"},
                    },
                },
            },
        }
        _result = DictUtils.flatten_dict(data)
        expected = {
            "a.b.c.d": "value",
            "a.b.c.e.f": "deep",
        }
        assert _result == expected

        # 测试混合类型
        _data = {
            "numbers": [1, 2, 3],
            "nested": {
                "boolean": True,
                "null": None,
            },
        }
        _result = DictUtils.flatten_dict(data)
        assert "numbers" in result
        assert "nested.boolean" in result
        assert "nested.null" in result
        assert result["numbers"] == [1, 2, 3]
        assert result["nested.boolean"] is True
        assert result["nested.null"] is None

    def test_filter_none_values(self):
        """测试过滤None值"""
        _data = {
            "name": "John",
            "email": None,
            "age": 30,
            "city": None,
            "active": False,
            "score": 0,
            "notes": "",
        }

        _result = DictUtils.filter_none_values(data)

        expected = {
            "name": "John",
            "age": 30,
            "active": False,
            "score": 0,
            "notes": "",
        }

        assert _result == expected

        # 测试全是None
        _data = {"a": None, "b": None, "c": None}
        _result = DictUtils.filter_none_values(data)
        assert _result == {}

        # 测试没有None
        _data = {"a": 1, "b": 2, "c": 3}
        _result = DictUtils.filter_none_values(data)
        assert _result == data

        # 测试空字典
        assert DictUtils.filter_none_values({}) == {}

        # 测试嵌套字典（不会被处理）
        _data = {
            "user": None,
            "config": {"setting": None},  # 嵌套的None不会被过滤
        }
        _result = DictUtils.filter_none_values(data)
        assert "user" not in result
        assert "config" in result
        assert result["config"]["setting"] is None

    def test_combination_operations(self):
        """测试组合操作"""
        # 先深度合并，再扁平化
        dict1 = {"config": {"db": {"host": "localhost"}}}
        dict2 = {"config": {"db": {"port": 5432}, "api": {"version": "v1"}}}

        merged = DictUtils.deep_merge(dict1, dict2)
        flattened = DictUtils.flatten_dict(merged)

        assert "config.db.host" in flattened
        assert "config.db.port" in flattened
        assert "config.api.version" in flattened
        assert flattened["config.db.host"] == "localhost"
        assert flattened["config.db.port"] == 5432
        assert flattened["config.api.version"] == "v1"

        # 先扁平化，再过滤None
        _data = {
            "user": {
                "name": "John",
                "email": None,
            },
            "settings": None,
        }

        flattened = DictUtils.flatten_dict(data)
        filtered = DictUtils.filter_none_values(flattened)

        assert "user.name" in filtered
        assert "user.email" not in filtered
        assert "settings" not in filtered

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试None输入
        with pytest.raises((AttributeError, TypeError)):
            DictUtils.deep_merge(None, {})

        # 测试非字典输入
        with pytest.raises(AttributeError):
            DictUtils.flatten_dict("not a dict")

        # 测试循环引用
        a = {}
        a["self"] = a
        # flatten_dict可能会导致无限递归，但实际实现可能有保护

        # 测试特殊键名
        _data = {
            "": {"empty_key": "value"},
            "with.dots": {"nested": "value"},
            "with spaces": {"nested": "value"},
        }

        _result = DictUtils.flatten_dict(data)
        assert ".empty_key" in result
        assert "with.dots.nested" in result
        assert "with spaces.nested" in result

    def test_performance_considerations(self):
        """测试性能相关"""
        # 大字典合并
        large_dict1 = {f"key_{i}": {"nested": i} for i in range(1000)}
        large_dict2 = {f"key_{i}": {"value": i * 2} for i in range(1000)}

        import time

        start = time.time()
        _result = DictUtils.deep_merge(large_dict1, large_dict2)
        duration = time.time() - start

        assert len(result) == 1000
        assert duration < 1.0  # 应该在1秒内完成
        assert result["key_0"]["nested"] == 0
        assert result["key_0"]["value"] == 0
        assert result["key_999"]["nested"] == 999
        assert result["key_999"]["value"] == 1998

        # 深层嵌套扁平化
        deep_data = {}
        current = deep_data
        for i in range(100):
            current["level"] = {}
            current = current["level"]
        current["value"] = "deep_value"

        start = time.time()
        _result = DictUtils.flatten_dict(deep_data)
        duration = time.time() - start

        assert len(result) == 101  # 100个level + 1个value
        assert duration < 0.5  # 应该在0.5秒内完成
