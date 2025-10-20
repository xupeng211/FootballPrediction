"""
字典工具增强测试
Enhanced Tests for Dict Utils

确保DictUtils类的所有功能都被充分测试。
"""

import pytest
from typing import Any, Dict, List
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from src.utils.dict_utils import DictUtils


@pytest.mark.unit
class TestDictUtilsEnhanced:
    """字典工具类增强测试"""

    # ======== deep_merge 测试 ========

    def test_deep_merge_basic(self):
        """测试基本的深度合并"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": 1, "b": 3, "c": 4}
        assert result == expected

    def test_deep_merge_nested_dicts(self):
        """测试嵌套字典的深度合并"""
        dict1 = {"config": {"db": {"host": "localhost"}, "api": {"v1": True}}}
        dict2 = {"config": {"db": {"port": 5432}, "cache": {"enabled": True}}}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "config": {
                "db": {"host": "localhost", "port": 5432},
                "api": {"v1": True},
                "cache": {"enabled": True},
            }
        }
        assert result == expected

    def test_deep_merge_preserves_originals(self):
        """测试原始字典不被修改"""
        dict1 = {"a": {"b": 1}}
        dict2 = {"a": {"c": 2}}
        dict1_copy = dict1.copy()
        dict2_copy = dict2.copy()

        result = DictUtils.deep_merge(dict1, dict2)

        assert dict1 == dict1_copy
        assert dict2 == dict2_copy
        assert result != dict1

    def test_deep_merge_with_empty_dicts(self):
        """测试空字典的合并"""
        # 第一个为空
        result = DictUtils.deep_merge({}, {"a": 1})
        assert result == {"a": 1}

        # 第二个为空
        result = DictUtils.deep_merge({"a": 1}, {})
        assert result == {"a": 1}

        # 都为空
        result = DictUtils.deep_merge({}, {})
        assert result == {}

    def test_deep_merge_mixed_types(self):
        """测试混合类型的合并"""
        dict1 = {
            "str": "value1",
            "num": 1,
            "list": [1, 2],
            "bool": True,
            "nested": {"inner": "old"},
        }
        dict2 = {
            "str": "value2",
            "num": 2,
            "list": [3, 4],
            "bool": False,
            "nested": {"inner2": "new"},
        }
        result = DictUtils.deep_merge(dict1, dict2)

        # 非字典类型应该被覆盖
        assert result["str"] == "value2"
        assert result["num"] == 2
        assert result["list"] == [3, 4]
        assert result["bool"] is False

        # 嵌套字典应该合并
        assert result["nested"]["inner"] == "old"
        assert result["nested"]["inner2"] == "new"

    def test_deep_merge_complex_nested(self):
        """测试复杂嵌套结构"""
        dict1 = {
            "level1": {
                "level2": {"level3": {"data": [1, 2, 3], "config": {"enabled": True}}},
                "other": "value1",
            }
        }
        dict2 = {
            "level1": {
                "level2": {
                    "level3": {"data": [4, 5], "new_field": "new"},
                    "level2_other": "value2",
                }
            }
        }
        result = DictUtils.deep_merge(dict1, dict2)

        assert result["level1"]["level2"]["level3"]["data"] == [4, 5]
        assert result["level1"]["level2"]["level3"]["config"]["enabled"] is True
        assert result["level1"]["level2"]["level3"]["new_field"] == "new"
        assert result["level1"]["level2"]["level2_other"] == "value2"
        assert result["level1"]["other"] == "value1"

    # ======== flatten_dict 测试 ========

    def test_flatten_dict_simple(self):
        """测试简单字典扁平化"""
        data = {"a": 1, "b": 2}
        result = DictUtils.flatten_dict(data)
        assert result == {"a": 1, "b": 2}

    def test_flatten_dict_nested(self):
        """测试嵌套字典扁平化"""
        data = {
            "user": {
                "name": "John",
                "profile": {"age": 30, "settings": {"theme": "dark"}},
            },
            "active": True,
        }
        result = DictUtils.flatten_dict(data)
        expected = {
            "user.name": "John",
            "user.profile.age": 30,
            "user.profile.settings.theme": "dark",
            "active": True,
        }
        assert result == expected

    def test_flatten_dict_custom_separator(self):
        """测试自定义分隔符"""
        data = {"a": {"b": {"c": 1}}}

        # 使用下划线
        result = DictUtils.flatten_dict(data, sep="_")
        assert result == {"a_b_c": 1}

        # 使用双斜杠
        result = DictUtils.flatten_dict(data, sep="//")
        assert result == {"a//b//c": 1}

    def test_flatten_dict_empty(self):
        """测试空字典扁平化"""
        assert DictUtils.flatten_dict({}) == {}

        # 嵌套空字典
        data = {"a": {}, "b": {"c": {}}}
        result = DictUtils.flatten_dict(data)
        assert result == {}

    def test_flatten_dict_various_types(self):
        """测试各种数据类型"""
        data = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "empty_list": [],
            "empty_dict": {},
        }
        result = DictUtils.flatten_dict(data)

        assert result["string"] == "value"
        assert result["number"] == 42
        assert result["boolean"] is True
        assert result["none"] is None
        assert result["list"] == [1, 2, 3]
        assert result["dict.nested"] == "value"
        assert result["empty_list"] == []
        assert "empty_dict" not in result  # 空字典不产生键

    def test_flatten_dict_with_parent_key(self):
        """测试使用父键前缀"""
        data = {"a": {"b": 1}}
        result = DictUtils.flatten_dict(data, parent_key="root")
        assert result == {"root.a.b": 1}

    def test_flatten_dict_special_keys(self):
        """测试特殊键名"""
        data = {
            "": {"empty": "value"},
            "with space": {"nested": "value"},
            "with.dot": {"nested": "value"},
            "with/slash": {"nested": "value"},
            "中文": {"键": "值"},
        }
        result = DictUtils.flatten_dict(data)

        assert "empty" in result
        assert "with space.nested" in result
        assert "with.dot.nested" in result
        assert "with/slash.nested" in result
        assert "中文.键" in result

    # ======== filter_none_values 测试 ========

    def test_filter_none_values_basic(self):
        """测试基本的None值过滤"""
        data = {"keep": "value", "remove": None, "keep_too": 42, "remove_too": None}
        result = DictUtils.filter_none_values(data)
        expected = {"keep": "value", "keep_too": 42}
        assert result == expected

    def test_filter_none_values_all_none(self):
        """测试全为None的字典"""
        data = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(data)
        assert result == {}

    def test_filter_none_values_no_none(self):
        """测试没有None值的字典"""
        data = {"a": 1, "b": "", "c": False, "d": 0}
        result = DictUtils.filter_none_values(data)
        assert result == data

    def test_filter_none_values_empty(self):
        """测试空字典"""
        assert DictUtils.filter_none_values({}) == {}

    def test_filter_none_values_nested_not_filtered(self):
        """测试嵌套字典中的None不会被过滤"""
        data = {
            "top_level": None,  # 会被过滤
            "nested": {
                "inner": None  # 不会被过滤
            },
        }
        result = DictUtils.filter_none_values(data)
        assert "top_level" not in result
        assert "nested" in result
        assert result["nested"]["inner"] is None

    def test_filter_none_values_various_falsy_values(self):
        """测试各种假值但不是None"""
        data = {
            "empty_string": "",
            "zero": 0,
            "false": False,
            "empty_list": [],
            "empty_dict": {},
            "none": None,
        }
        result = DictUtils.filter_none_values(data)

        assert result["empty_string"] == ""
        assert result["zero"] == 0
        assert result["false"] is False
        assert result["empty_list"] == []
        assert result["empty_dict"] == {}
        assert "none" not in result

    # ======== 组合操作测试 ========

    def test_merge_then_flatten(self):
        """测试先合并后扁平化"""
        dict1 = {"config": {"db": {"host": "localhost"}}}
        dict2 = {"config": {"db": {"port": 5432}, "api": {"version": "v1"}}}

        merged = DictUtils.deep_merge(dict1, dict2)
        flattened = DictUtils.flatten_dict(merged)

        assert flattened["config.db.host"] == "localhost"
        assert flattened["config.db.port"] == 5432
        assert flattened["config.api.version"] == "v1"

    def test_flatten_then_filter(self):
        """测试先扁平化后过滤"""
        data = {"user": {"name": "John", "email": None}, "settings": None}

        flattened = DictUtils.flatten_dict(data)
        filtered = DictUtils.filter_none_values(flattened)

        assert "user.name" in filtered
        assert "user.email" not in filtered
        assert "settings" not in filtered

    def test_filter_then_merge(self):
        """测试先过滤后合并"""
        dict1 = {"a": 1, "b": None}
        dict2 = {"b": 2, "c": None}

        dict1_filtered = DictUtils.filter_none_values(dict1)
        dict2_filtered = DictUtils.filter_none_values(dict2)
        result = DictUtils.deep_merge(dict1_filtered, dict2_filtered)

        expected = {"a": 1, "b": 2}
        assert result == expected

    # ======== 边界条件和错误处理 ========

    def test_deep_merge_with_none_inputs(self):
        """测试使用None作为输入"""
        # 这些应该抛出异常，因为我们期望字典输入
        with pytest.raises((AttributeError, TypeError)):
            DictUtils.deep_merge(None, {"a": 1})

        with pytest.raises((AttributeError, TypeError)):
            DictUtils.deep_merge({"a": 1}, None)

    def test_flatten_dict_with_none_input(self):
        """测试使用None作为输入"""
        with pytest.raises((AttributeError, TypeError)):
            DictUtils.flatten_dict(None)

    def test_filter_none_with_none_input(self):
        """测试使用None作为输入"""
        with pytest.raises((AttributeError, TypeError)):
            DictUtils.filter_none_values(None)

    def test_deep_merge_max_depth(self):
        """测试最大深度合并"""
        # 创建10层嵌套
        dict1 = {}
        dict2 = {}
        current1 = dict1
        current2 = dict2
        for i in range(10):
            current1[f"level_{i}"] = {}
            current2[f"level_{i}"] = {"value": i}
            current1 = current1[f"level_{i}"]
            current2 = current2[f"level_{i}"]

        current1["final"] = "end"
        current2["final"] = "updated"

        result = DictUtils.deep_merge(dict1, dict2)

        # 验证所有层级都正确合并
        current = result
        for i in range(10):
            current = current[f"level_{i}"]
            assert current["value"] == i
        assert current["final"] == "updated"

    def test_flatten_dict_max_depth(self):
        """测试最大深度扁平化"""
        # 创建深层嵌套
        data = {}
        current = data
        for i in range(20):
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]
        current["value"] = "deep"

        result = DictUtils.flatten_dict(data)

        # 验证最终值存在
        long_key = ".".join([f"level_{i}" for i in range(20)] + ["value"])
        assert long_key in result
        assert result[long_key] == "deep"

    # ======== 性能测试 ========

    def test_deep_merge_performance(self):
        """测试深度合并性能"""
        import time

        # 创建大字典
        large_dict1 = {
            f"key_{i}": {"nested": {"data": list(range(10))}} for i in range(100)
        }
        large_dict2 = {
            f"key_{i}": {"nested": {"extra": f"value_{i}"}} for i in range(100)
        }

        start = time.time()
        result = DictUtils.deep_merge(large_dict1, large_dict2)
        duration = time.time() - start

        # 应该快速完成
        assert duration < 0.5
        assert len(result) == 100

        # 验证合并结果
        for i in range(100):
            key = f"key_{i}"
            assert "data" in result[key]["nested"]
            assert "extra" in result[key]["nested"]
            assert result[key]["nested"]["extra"] == f"value_{i}"

    def test_flatten_dict_performance(self):
        """测试扁平化性能"""
        import time

        # 创建宽而浅的字典
        wide_dict = {}
        for i in range(1000):
            wide_dict[f"key_{i}"] = {
                "value": i,
                "metadata": {"type": "test", "source": f"source_{i}"},
            }

        start = time.time()
        result = DictUtils.flatten_dict(wide_dict)
        duration = time.time() - start

        # 应该快速完成
        assert duration < 0.5
        assert len(result) == 3000  # 1000 * 3

        # 验证部分结果
        assert result["key_0.value"] == 0
        assert result["key_0.metadata.type"] == "test"
        assert result["key_999.metadata.source"] == "source_999"

    # ======== 实际应用场景测试 ========

    def test_merge_config_files(self):
        """测试合并配置文件的场景"""
        default_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "pool_size": 10,
                "options": {"timeout": 30, "retry": 3},
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "features": {"feature_a": True, "feature_b": False},
        }

        user_config = {
            "database": {
                "host": "production.db.com",
                "pool_size": 20,
                "options": {"timeout": 60},
            },
            "logging": {"level": "DEBUG"},
            "features": {"feature_c": True},
        }

        result = DictUtils.deep_merge(default_config, user_config)

        # 验证合并结果
        assert result["database"]["host"] == "production.db.com"
        assert result["database"]["port"] == 5432  # 保持默认值
        assert result["database"]["pool_size"] == 20  # 用户覆盖
        assert result["database"]["options"]["timeout"] == 60  # 用户覆盖
        assert result["database"]["options"]["retry"] == 3  # 保持默认值
        assert result["logging"]["level"] == "DEBUG"  # 用户覆盖
        assert (
            result["logging"]["format"] == default_config["logging"]["format"]
        )  # 保持默认
        assert result["features"]["feature_a"] is True  # 保持默认
        assert result["features"]["feature_b"] is False  # 保持默认
        assert result["features"]["feature_c"] is True  # 用户新加

    def test_flatten_for_dotenv(self):
        """测试为.env文件扁平化的场景"""
        config = {
            "database": {
                "connection": {
                    "host": "localhost",
                    "port": 5432,
                    "credentials": {"username": "admin", "password": "secret"},
                },
                "pool": {"min_size": 5, "max_size": 20},
            },
            "api": {"version": "v1", "rate_limit": 1000},
        }

        flattened = DictUtils.flatten_dict(config, sep="_")

        # 验证键名适合环境变量
        assert "database_connection_host" in flattened
        assert "database_connection_port" in flattened
        assert "database_connection_credentials_username" in flattened
        assert "database_connection_credentials_password" in flattened
        assert "database_pool_min_size" in flattened
        assert "database_pool_max_size" in flattened
        assert "api_version" in flattened
        assert "api_rate_limit" in flattened

    def test_filter_api_response(self):
        """测试过滤API响应的场景"""
        api_response = {
            "id": 123,
            "name": "John Doe",
            "email": "john@example.com",
            "phone": None,
            "address": {
                "street": "123 Main St",
                "city": "New York",
                "state": None,
                "zip": None,
            },
            "metadata": {"created_at": "2023-01-01", "updated_at": None, "version": 1},
            "last_login": None,
            "profile_picture": None,
        }

        filtered = DictUtils.filter_none_values(api_response)

        # 验证顶层None值被过滤
        assert "phone" not in filtered
        assert "last_login" not in filtered
        assert "profile_picture" not in filtered

        # 验证嵌套None值保留
        assert "address" in filtered
        assert filtered["address"]["state"] is None
        assert filtered["address"]["zip"] is None
        assert "metadata" in filtered
        assert filtered["metadata"]["updated_at"] is None

        # 验证正常值保留
        assert filtered["id"] == 123
        assert filtered["name"] == "John Doe"
        assert filtered["address"]["street"] == "123 Main St"
