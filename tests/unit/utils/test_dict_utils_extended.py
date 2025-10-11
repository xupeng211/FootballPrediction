# from src.utils.dict_utils import DictUtils

"""
测试字典处理工具模块 - 扩展测试
"""


class TestDictUtilsExtended:
    """扩展的DictUtils测试"""

    def test_deep_merge_simple(self):
        """测试简单字典合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

    def test_deep_merge_nested(self):
        """测试嵌套字典合并"""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 3, "z": 4}, "c": 5}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": {"x": 1, "y": 3, "z": 4}, "b": 3, "c": 5}
        assert result == expected

    def test_deep_merge_multiple_levels(self):
        """测试多级嵌套字典合并"""
        dict1 = {"a": {"b": {"c": 1, "d": 2}, "e": 3}, "f": 4}
        dict2 = {"a": {"b": {"c": 5, "g": 6}, "h": 7}, "i": 8}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "a": {"b": {"c": 5, "d": 2, "g": 6}, "e": 3, "h": 7},
            "f": 4,
            "i": 8,
        }
        assert result == expected

    def test_deep_merge_empty_dict(self):
        """测试与空字典合并"""
        dict1 = {"a": 1, "b": 2}
        result1 = DictUtils.deep_merge(dict1, {})
        assert result1 == dict1

        result2 = DictUtils.deep_merge({}, dict1)
        assert result2 == dict1

    def test_deep_merge_no_overlap(self):
        """测试无重叠键的合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

    def test_deep_merge_with_lists(self):
        """测试包含列表的字典合并"""
        dict1 = {"a": [1, 2, 3], "b": {"c": 4}}
        dict2 = {"a": [4, 5], "b": {"d": 5}}
        result = DictUtils.deep_merge(dict1, dict2)
        # 列表会被完全覆盖
        assert result == {"a": [4, 5], "b": {"c": 4, "d": 5}}

    def test_flatten_dict_simple(self):
        """测试简单字典扁平化"""
        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.flatten_dict(d)
        assert result == d

    def test_flatten_dict_nested(self):
        """测试嵌套字典扁平化"""
        d = {"a": {"b": {"c": 1}, "d": 2}, "e": 3}
        result = DictUtils.flatten_dict(d)
        expected = {"a.b.c": 1, "a.d": 2, "e": 3}
        assert result == expected

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符的扁平化"""
        d = {"a": {"b": 1}, "c": 2}
        result = DictUtils.flatten_dict(d, sep="_")
        expected = {"a_b": 1, "c": 2}
        assert result == expected

    def test_flatten_dict_with_parent_key(self):
        """测试带父键的扁平化"""
        d = {"a": 1, "b": {"c": 2}}
        result = DictUtils.flatten_dict(d, parent_key="root")
        expected = {"root.a": 1, "root.b.c": 2}
        assert result == expected

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        result = DictUtils.flatten_dict({})
        assert result == {}

    def test_flatten_dict_empty_nested(self):
        """测试包含空字典的扁平化"""
        d = {"a": {}, "b": {"c": 1}, "d": {}}
        result = DictUtils.flatten_dict(d)
        expected = {"b.c": 1}
        assert result == expected

    def test_flatten_dict_deep_nested(self):
        """测试深层嵌套字典扁平化"""
        d = {"a": {"b": {"c": {"d": {"e": 1}}}}}
        result = DictUtils.flatten_dict(d)
        expected = {"a.b.c.d.e": 1}
        assert result == expected

    def test_filter_none_values_all_present(self):
        """测试过滤None值（所有值都存在）"""
        d = {"a": 1, "b": "test", "c": [1, 2, 3], "d": {"x": 1}}
        result = DictUtils.filter_none_values(d)
        assert result == d

    def test_filter_none_values_with_none(self):
        """测试过滤None值"""
        d = {"a": 1, "b": None, "c": 2, "d": None, "e": 3}
        result = DictUtils.filter_none_values(d)
        expected = {"a": 1, "c": 2, "e": 3}
        assert result == expected

    def test_filter_none_values_all_none(self):
        """测试所有值都是None"""
        d = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_empty(self):
        """测试空字典"""
        result = DictUtils.filter_none_values({})
        assert result == {}

    def test_filter_none_values_false_values(self):
        """测试保留False值（但过滤None）"""
        d = {"a": False, "b": 0, "c": "", "d": None, "e": []}
        result = DictUtils.filter_none_values(d)
        expected = {"a": False, "b": 0, "c": "", "e": []}
        assert result == expected

    def test_combined_operations(self):
        """测试组合操作"""
        # 先深度合并
        dict1 = {"config": {"db": {"host": "localhost"}, "port": 5000}}
        dict2 = {"config": {"db": {"port": 5432, "user": "admin"}}, "debug": True}
        merged = DictUtils.deep_merge(dict1, dict2)

        # 然后扁平化
        flattened = DictUtils.flatten_dict(merged)
        expected = {
            "config.db.host": "localhost",
            "config.db.port": 5432,
            "config.db.user": "admin",
            "config.port": 5000,
            "debug": True,
        }
        assert flattened == expected

    def test_real_world_config_merge(self):
        """测试真实世界的配置合并场景"""
        default_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "pool": {"size": 5, "timeout": 30},
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        }

        user_config = {
            "database": {"host": "prod-server", "pool": {"size": 10}},
            "logging": {"level": "DEBUG"},
            "feature_flags": {"new_feature": True},
        }

        result = DictUtils.deep_merge(default_config, user_config)
        expected = {
            "database": {
                "host": "prod-server",
                "port": 5432,
                "pool": {"size": 10, "timeout": 30},
            },
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "feature_flags": {"new_feature": True},
        }

        assert result == expected
