"""字典工具基础测试"""

# from src.utils.dict_utils import DictUtils


class TestDictUtilsBasic:
    """字典工具基础测试"""

    def test_deep_merge_simple(self):
        """测试简单深度合并"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"b": {"y": 20}, "c": 3}

        _result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
        assert _result == expected

    def test_deep_merge_override(self):
        """测试深度合并覆盖"""
        dict1 = {"a": 1, "b": {"x": 10}}
        dict2 = {"a": 2, "b": {"x": 20}}

        _result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 2, "b": {"x": 20}}
        assert _result == expected

    def test_deep_merge_empty(self):
        """测试空字典合并"""
        dict1 = {}
        dict2 = {"a": 1}
        _result = DictUtils.deep_merge(dict1, dict2)
        assert _result == {"a": 1}

    def test_flatten_dict_simple(self):
        """测试简单扁平化"""
        d = {"a": 1, "b": {"c": 2}}
        _result = DictUtils.flatten_dict(d)
        expected = {"a": 1, "b.c": 2}
        assert _result == expected

    def test_flatten_dict_nested(self):
        """测试嵌套扁平化"""
        d = {"a": {"b": {"c": 1}}}
        _result = DictUtils.flatten_dict(d)
        expected = {"a.b.c": 1}
        assert _result == expected

    def test_flatten_dict_custom_sep(self):
        """测试自定义分隔符"""
        d = {"a": {"b": {"c": 1}}}
        _result = DictUtils.flatten_dict(d, sep="_")
        expected = {"a_b_c": 1}
        assert _result == expected

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        d = {}
        _result = DictUtils.flatten_dict(d)
        assert _result == {}

    def test_filter_none_values(self):
        """测试过滤None值"""
        d = {"a": 1, "b": None, "c": 3, "d": None}
        _result = DictUtils.filter_none_values(d)
        assert _result == {"a": 1, "c": 3}

    def test_filter_none_values_empty(self):
        """测试过滤None值（空字典）"""
        d = {}
        _result = DictUtils.filter_none_values(d)
        assert _result == {}

    def test_filter_none_values_no_none(self):
        """测试过滤None值（无None）"""
        d = {"a": 1, "b": 2}
        _result = DictUtils.filter_none_values(d)
        assert _result == {"a": 1, "b": 2}

    def test_filter_none_values_all_none(self):
        """测试过滤None值（全部None）"""
        d = {"a": None, "b": None}
        _result = DictUtils.filter_none_values(d)
        assert _result == {}

    def test_filter_none_values_preserve_falsey(self):
        """测试过滤None值（保留假值）"""
        d = {"a": 0, "b": "", "c": [], "d": {}, "e": None, "f": False}
        _result = DictUtils.filter_none_values(d)
        expected = {"a": 0, "b": "", "c": [], "d": {}, "f": False}
        assert _result == expected

    def test_complex_merge(self):
        """测试复杂合并"""
        dict1 = {
            "api": {
                "version": "v1",
                "endpoints": {"users": "/api/v1/users", "posts": "/api/v1/posts"},
            },
            "database": {"host": "localhost", "port": 5432},
        }

        dict2 = {
            "api": {"endpoints": {"comments": "/api/v1/comments"}, "timeout": 30},
            "cache": {"enabled": True},
        }

        _result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "api": {
                "version": "v1",
                "endpoints": {
                    "users": "/api/v1/users",
                    "posts": "/api/v1/posts",
                    "comments": "/api/v1/comments",
                },
                "timeout": 30,
            },
            "database": {"host": "localhost", "port": 5432},
            "cache": {"enabled": True},
        }
        assert _result == expected

    def test_complex_flatten(self):
        """测试复杂扁平化"""
        d = {
            "app": {
                "name": "test-app",
                "version": "1.0.0",
                "config": {
                    "database": {"host": "localhost", "port": 5432},
                    "redis": {"host": "localhost", "port": 6379},
                },
            }
        }

        _result = DictUtils.flatten_dict(d)
        assert "app.name" in result
        assert "app.version" in result
        assert "app.config.database.host" in result
        assert "app.config.database.port" in result
        assert "app.config.redis.host" in result
        assert "app.config.redis.port" in result
        assert result["app.name"] == "test-app"
        assert result["app.config.database.host"] == "localhost"
