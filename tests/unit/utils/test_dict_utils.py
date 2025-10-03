"""
字典工具模块测试
"""

import pytest
from src.utils.dict_utils import DictUtils


class TestDictUtils:
    """测试字典工具类"""

    def test_deep_merge_simple_dicts(self):
        """测试简单字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}

        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 3, "c": 4}

        assert result == expected

    def test_deep_merge_nested_dicts(self):
        """测试嵌套字典合并"""
        dict1 = {
            "config": {
                "database": {
                    "host": "localhost",
                    "port": 5432
                },
                "debug": True
            },
            "version": "1.0"
        }

        dict2 = {
            "config": {
                "database": {
                    "password": "secret"
                },
                "cache": {
                    "type": "redis"
                }
            },
            "version": "2.0"
        }

        result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "config": {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "password": "secret"
                },
                "debug": True,
                "cache": {
                    "type": "redis"
                }
            },
            "version": "2.0"
        }

        assert result == expected

    def test_deep_merge_empty_dicts(self):
        """测试空字典合并"""
        # 两个空字典
        result1 = DictUtils.deep_merge({}, {})
        assert result1 == {}

        # 第一个为空
        result2 = DictUtils.deep_merge({}, {"a": 1})
        assert result2 == {"a": 1}

        # 第二个为空
        result3 = DictUtils.deep_merge({"a": 1}, {})
        assert result3 == {"a": 1}

    def test_deep_merge_no_overlap(self):
        """测试无重叠键的字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}

        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 2, "c": 3, "d": 4}

        assert result == expected

    def test_deep_merge_with_none_values(self):
        """测试包含None值的字典合并"""
        dict1 = {"a": None, "b": 2}
        dict2 = {"a": 1, "c": None}

        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 2, "c": None}

        assert result == expected

    def test_deep_merge_preserves_original(self):
        """测试合并后不修改原始字典"""
        dict1 = {"a": {"b": 1}}
        dict2 = {"a": {"c": 2}}

        original1 = {"a": {"b": 1}}
        original2 = {"a": {"c": 2}}

        result = DictUtils.deep_merge(dict1, dict2)

        assert dict1 == original1
        assert dict2 == original2
        assert result == {"a": {"b": 1, "c": 2}}

    def test_deep_merge_complex_types(self):
        """测试包含复杂类型的字典合并"""
        dict1 = {
            "list": [1, 2, 3],
            "dict": {"a": 1},
            "string": "hello"
        }

        dict2 = {
            "list": [4, 5, 6],
            "dict": {"b": 2},
            "string": "world"
        }

        result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "list": [4, 5, 6],  # 非字典类型直接覆盖
            "dict": {"a": 1, "b": 2},  # 字典类型递归合并
            "string": "world"
        }

        assert result == expected

    def test_deep_merge_three_levels(self):
        """测试三级嵌套字典合并"""
        dict1 = {
            "level1": {
                "level2": {
                    "level3": {
                        "value1": "old",
                        "value2": "unchanged"
                    },
                    "other": "value"
                }
            }
        }

        dict2 = {
            "level1": {
                "level2": {
                    "level3": {
                        "value1": "new",
                        "value3": "added"
                    }
                }
            }
        }

        result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "level1": {
                "level2": {
                    "level3": {
                        "value1": "new",
                        "value2": "unchanged",
                        "value3": "added"
                    },
                    "other": "value"
                }
            }
        }

        assert result == expected

    def test_flatten_dict_simple(self):
        """测试简单字典扁平化"""
        d = {"a": 1, "b": 2}

        result = DictUtils.flatten_dict(d)
        expected = {"a": 1, "b": 2}

        assert result == expected

    def test_flatten_dict_nested(self):
        """测试嵌套字典扁平化"""
        d = {
            "config": {
                "database": {
                    "host": "localhost",
                    "port": 5432
                },
                "debug": True
            },
            "version": "1.0"
        }

        result = DictUtils.flatten_dict(d)
        expected = {
            "config.database.host": "localhost",
            "config.database.port": 5432,
            "config.debug": True,
            "version": "1.0"
        }

        assert result == expected

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符"""
        d = {"a": {"b": {"c": 1}}}

        result = DictUtils.flatten_dict(d, sep="_")
        expected = {"a_b_c": 1}

        assert result == expected

    def test_flatten_dict_with_parent_key(self):
        """测试带父键的扁平化"""
        d = {"b": {"c": 1}}

        result = DictUtils.flatten_dict(d, parent_key="a")
        expected = {"a.b.c": 1}

        assert result == expected

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        result = DictUtils.flatten_dict({})
        assert result == {}

    def test_flatten_dict_mixed_types(self):
        """测试混合类型的字典扁平化"""
        d = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {
                "inner": "value"
            }
        }

        result = DictUtils.flatten_dict(d)
        expected = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested.inner": "value"
        }

        assert result == expected

    def test_flatten_dict_deeply_nested(self):
        """测试深度嵌套字典扁平化"""
        d = {
            "a": {
                "b": {
                    "c": {
                        "d": {
                            "e": "deep_value"
                        }
                    }
                }
            }
        }

        result = DictUtils.flatten_dict(d)
        expected = {"a.b.c.d.e": "deep_value"}

        assert result == expected

    def test_flatten_dict_with_empty_dict(self):
        """测试包含空字典的扁平化"""
        d = {
            "a": {},
            "b": {
                "c": 1
            }
        }

        result = DictUtils.flatten_dict(d)
        expected = {"b.c": 1}

        assert result == expected

    def test_filter_none_values_all_none(self):
        """测试过滤全部为None的字典"""
        d = {"a": None, "b": None, "c": None}

        result = DictUtils.filter_none_values(d)
        expected = {}

        assert result == expected

    def test_filter_none_values_no_none(self):
        """测试过滤不含None的字典"""
        d = {"a": 1, "b": "value", "c": True}

        result = DictUtils.filter_none_values(d)
        expected = {"a": 1, "b": "value", "c": True}

        assert result == expected

    def test_filter_none_values_mixed(self):
        """测试过滤混合值的字典"""
        d = {
            "a": 1,
            "b": None,
            "c": "value",
            "d": None,
            "e": 0,  # 0不是None，应该保留
            "f": False,  # False不是None，应该保留
            "g": ""  # 空字符串不是None，应该保留
        }

        result = DictUtils.filter_none_values(d)
        expected = {
            "a": 1,
            "c": "value",
            "e": 0,
            "f": False,
            "g": ""
        }

        assert result == expected

    def test_filter_none_values_nested(self):
        """测试嵌套字典的None过滤"""
        # 注意：filter_none_values只过滤顶层字典的None值
        d = {
            "a": None,
            "nested": {
                "b": None,
                "c": 1
            },
            "d": 2
        }

        result = DictUtils.filter_none_values(d)
        expected = {
            "nested": {
                "b": None,
                "c": 1
            },
            "d": 2
        }

        assert result == expected

    def test_filter_none_values_empty_dict(self):
        """测试过滤空字典"""
        result = DictUtils.filter_none_values({})
        assert result == {}

    def test_filter_none_values_preserves_original(self):
        """测试过滤后不修改原始字典"""
        d = {"a": 1, "b": None, "c": 2}
        original = {"a": 1, "b": None, "c": 2}

        result = DictUtils.filter_none_values(d)

        assert d == original
        assert result == {"a": 1, "c": 2}

    def test_combined_operations(self):
        """测试组合操作：先合并再扁平化"""
        dict1 = {
            "config": {
                "app": {
                    "name": "MyApp",
                    "version": "1.0"
                }
            },
            "settings": {
                "debug": None
            }
        }

        dict2 = {
            "config": {
                "app": {
                    "version": "2.0",
                    "author": "Developer"
                },
                "database": {
                    "host": "localhost"
                }
            },
            "settings": {
                "port": 8080
            }
        }

        # 先深度合并
        merged = DictUtils.deep_merge(dict1, dict2)

        # 再过滤None值（只过滤顶层）
        filtered = DictUtils.filter_none_values(merged)

        # 最后扁平化
        flattened = DictUtils.flatten_dict(filtered)

        expected = {
            "config.app.name": "MyApp",
            "config.app.version": "2.0",
            "config.app.author": "Developer",
            "config.database.host": "localhost",
            "settings.debug": None,  # filter_none_values不会过滤嵌套的None
            "settings.port": 8080
        }

        assert flattened == expected

    def test_edge_case_key_names(self):
        """测试边界情况的键名"""
        d = {
            "": {"empty_key": "value"},
            "with.dot": {"nested": "value"},
            "with space": {"nested": "value"}
        }

        # 扁平化测试
        result = DictUtils.flatten_dict(d)
        expected = {
            "empty_key": "value",  # 空键名时不会加前缀
            "with.dot.nested": "value",
            "with space.nested": "value"
        }

        assert result == expected