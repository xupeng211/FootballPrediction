"""
字典工具模块完整测试
"""

import pytest
from src.utils.dict_utils import DictUtils


class TestDictUtils:
    """字典工具类测试"""

    def test_deep_merge_simple(self):
        """测试简单字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        dict1 = {"config": {"host": "localhost", "port": 8000}, "debug": False}
        dict2 = {"config": {"port": 8080, "ssl": True}, "production": True}
        result = DictUtils.deep_merge(dict1, dict2)

        assert result == {
            "config": {"host": "localhost", "port": 8080, "ssl": True},
            "debug": False,
            "production": True,
        }

    def test_deep_merge_multiple_levels(self):
        """测试多级嵌套字典合并"""
        dict1 = {"level1": {"level2": {"a": 1, "b": 2}, "c": 3}}
        dict2 = {"level1": {"level2": {"b": 20, "d": 4}, "e": 5}}
        result = DictUtils.deep_merge(dict1, dict2)

        assert result == {
            "level1": {"level2": {"a": 1, "b": 20, "d": 4}, "c": 3, "e": 5}
        }

    def test_deep_merge_empty_dicts(self):
        """测试空字典合并"""
        dict1 = {}
        dict2 = {}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {}

    def test_deep_merge_with_empty_first(self):
        """测试第一个字典为空"""
        dict1 = {}
        dict2 = {"a": 1, "b": {"c": 2}}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": {"c": 2}}

    def test_deep_merge_with_empty_second(self):
        """测试第二个字典为空"""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": {"c": 2}}

    def test_deep_merge_non_dict_override(self):
        """测试非字典值覆盖"""
        dict1 = {"a": {"nested": 1}}
        dict2 = {"a": "string_value"}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": "string_value"}

    def test_deep_merge_no_modification(self):
        """测试原字典不被修改"""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}

        # 记录原始值
        original_dict1 = {"a": 1, "b": {"c": 2}}
        original_dict2 = {"b": {"d": 3}, "e": 4}

        result = DictUtils.deep_merge(dict1, dict2)

        # 确保原字典未被修改
        assert dict1 == original_dict1
        assert dict2 == original_dict2
        assert result != dict1
        assert result != dict2

    def test_deep_merge_with_none_values(self):
        """测试包含None值的合并"""
        dict1 = {"a": None, "b": {"c": None}}
        dict2 = {"a": 1, "b": {"d": 2}}
        result = DictUtils.deep_merge(dict1, dict2)

        assert result == {"a": 1, "b": {"c": None, "d": 2}}

    def test_deep_merge_with_different_types(self):
        """测试不同类型的值合并"""
        dict1 = {"str": "string", "num": 1, "list": [1, 2], "bool": True}
        dict2 = {"str": "new_string", "num": 2.5, "list": [3, 4], "bool": False}
        result = DictUtils.deep_merge(dict1, dict2)

        assert result == {
            "str": "new_string",
            "num": 2.5,
            "list": [3, 4],
            "bool": False,
        }

    def test_flatten_dict_simple(self):
        """测试简单字典扁平化"""
        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.flatten_dict(d)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_flatten_dict_nested(self):
        """测试嵌套字典扁平化"""
        d = {
            "config": {
                "database": {"host": "localhost", "port": 5432},
                "cache": {"type": "redis", "ttl": 300},
            },
            "debug": True,
        }
        result = DictUtils.flatten_dict(d)

        expected = {
            "config.database.host": "localhost",
            "config.database.port": 5432,
            "config.cache.type": "redis",
            "config.cache.ttl": 300,
            "debug": True,
        }
        assert result == expected

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符的扁平化"""
        d = {"a": {"b": {"c": 1}}}
        result = DictUtils.flatten_dict(d, sep="_")
        assert result == {"a_b_c": 1}

    def test_flatten_dict_with_parent_key(self):
        """测试带父键的扁平化"""
        d = {"b": {"c": 1}}
        result = DictUtils.flatten_dict(d, parent_key="a")
        assert result == {"a.b.c": 1}

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        result = DictUtils.flatten_dict({})
        assert result == {}

    def test_flatten_dict_mixed_types(self):
        """测试混合类型的扁平化"""
        d = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "none": None,
            "nested": {"list": [1, 2, 3], "dict": {"a": 1}},
        }
        result = DictUtils.flatten_dict(d)

        expected = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "none": None,
            "nested.list": [1, 2, 3],
            "nested.dict.a": 1,
        }
        assert result == expected

    def test_flatten_dict_single_level(self):
        """测试单层字典扁平化"""
        d = {"a": 1}
        result = DictUtils.flatten_dict(d)
        assert result == {"a": 1}

    def test_flatten_dict_deep_nesting(self):
        """测试深度嵌套的扁平化"""
        d = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}
        result = DictUtils.flatten_dict(d)

        expected = {"level1.level2.level3.level4.value": "deep"}
        assert result == expected

    def test_filter_none_values_all_present(self):
        """测试过滤None值 - 所有值都存在"""
        d = {"a": 1, "b": "string", "c": True, "d": []}
        result = DictUtils.filter_none_values(d)
        assert result == d

    def test_filter_none_values_with_none(self):
        """测试过滤None值 - 包含None值"""
        d = {"a": 1, "b": None, "c": "string", "d": None, "e": False}
        result = DictUtils.filter_none_values(d)
        assert result == {"a": 1, "c": "string", "e": False}

    def test_filter_none_values_all_none(self):
        """测试过滤None值 - 所有值都是None"""
        d = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_empty(self):
        """测试过滤None值 - 空字典"""
        result = DictUtils.filter_none_values({})
        assert result == {}

    def test_filter_none_values_nested_not_affected(self):
        """测试过滤None值 - 嵌套字典不受影响"""
        d = {"a": 1, "b": {"c": None, "d": 2}, "e": None}
        result = DictUtils.filter_none_values(d)
        # 注意：filter_none_values只过滤顶级键的None值
        assert result == {"a": 1, "b": {"c": None, "d": 2}}

    def test_complex_workflow(self):
        """测试复杂工作流"""
        # 创建复杂的嵌套配置
        config1 = {
            "app": {"name": "test_app", "settings": {"debug": False, "port": 8000}},
            "database": {
                "host": "localhost",
                "credentials": {"username": "admin", "password": "secret"},
            },
        }

        config2 = {
            "app": {
                "settings": {
                    "debug": True,  # 覆盖
                    "timeout": 30,  # 新增
                },
                "version": "1.0.0",  # 新增
            },
            "cache": {  # 新增
                "type": "redis",
                "config": {"host": "cache-server", "port": 6379},
            },
        }

        # 合并配置
        merged = DictUtils.deep_merge(config1, config2)

        # 扁平化
        flattened = DictUtils.flatten_dict(merged)

        # 过滤None值
        filtered = DictUtils.filter_none_values(flattened)

        # 验证结果
        assert "app.settings.debug" in filtered
        assert filtered["app.settings.debug"] is True
        assert "app.settings.port" in filtered
        assert filtered["app.settings.port"] == 8000
        assert "app.settings.timeout" in filtered
        assert filtered["app.settings.timeout"] == 30
        assert "database.credentials.username" in filtered
        assert filtered["database.credentials.username"] == "admin"
        assert "cache.type" in filtered
        assert filtered["cache.type"] == "redis"

    def test_unicode_keys_and_values(self):
        """测试Unicode键和值"""
        d = {"中文键": {"nested": "中文值", "emoji": "🏈⚽"}}

        # 测试所有方法
        merged = DictUtils.deep_merge(d, {"中文键": {"new": "新值"}})
        assert merged["中文键"]["nested"] == "中文值"
        assert merged["中文键"]["new"] == "新值"

        flattened = DictUtils.flatten_dict(d)
        assert "中文键.nested" in flattened
        assert flattened["中文键.emoji"] == "🏈⚽"
