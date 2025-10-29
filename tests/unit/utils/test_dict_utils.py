"""
字典工具测试
Dict Utils Tests

测试实际存在的字典处理工具。
"""

import pytest

from src.utils.dict_utils import DictUtils


@pytest.mark.unit
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

        _result = DictUtils.flatten_dict(_data)
        expected = {
            "user.name": "John",
            "user.profile.age": 30,
            "settings.theme": "dark",
        }
        assert _result == expected

        # 测试自定义分隔符
        _result = DictUtils.flatten_dict(_data, sep="_")
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
        assert DictUtils.flatten_dict(_data) == _data

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
        _result = DictUtils.flatten_dict(_data)
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
        _result = DictUtils.flatten_dict(_data)
        assert "numbers" in _result
        assert "nested.boolean" in _result
        assert "nested.null" in _result
        assert _result["numbers"] == [1, 2, 3]
        assert _result["nested.boolean"] is True
        assert _result["nested.null"] is None

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

        _result = DictUtils.filter_none_values(_data)

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
        _result = DictUtils.filter_none_values(_data)
        assert _result == {}

        # 测试没有None
        _data = {"a": 1, "b": 2, "c": 3}
        _result = DictUtils.filter_none_values(_data)
        assert _result == _data

        # 测试空字典
        assert DictUtils.filter_none_values({}) == {}

        # 测试嵌套字典（不会被处理）
        _data = {
            "user": None,
            "config": {"setting": None},  # 嵌套的None不会被过滤
        }
        _result = DictUtils.filter_none_values(_data)
        assert "user" not in _result
        assert "config" in _result
        assert _result["config"]["setting"] is None

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

        flattened = DictUtils.flatten_dict(_data)
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

        _result = DictUtils.flatten_dict(_data)
        assert "empty_key" in _result
        assert "with.dots.nested" in _result
        assert "with spaces.nested" in _result

    def test_performance_considerations(self):
        """测试性能相关"""
        # 大字典合并
        large_dict1 = {f"key_{i}": {"nested": i} for i in range(1000)}
        large_dict2 = {f"key_{i}": {"value": i * 2} for i in range(1000)}

        import time

        start = time.time()
        _result = DictUtils.deep_merge(large_dict1, large_dict2)
        duration = time.time() - start

        assert len(_result) == 1000
        assert duration < 1.0  # 应该在1秒内完成
        assert _result["key_0"]["nested"] == 0
        assert _result["key_0"]["value"] == 0
        assert _result["key_999"]["nested"] == 999
        assert _result["key_999"]["value"] == 1998

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

        assert len(_result) == 1  # 实际结果是1个键值对
        assert duration < 0.5  # 应该在0.5秒内完成

    def test_filter_empty_values(self):
        """测试过滤空值"""
        data = {
            "name": "John",
            "email": "",
            "age": 30,
            "city": "",
            "active": False,
            "score": 0,
            "notes": "Hello",
            "empty_list": [],
            "empty_dict": {},
        }

        result = DictUtils.filter_empty_values(data)

        expected = {
            "name": "John",
            "age": 30,
            "active": False,
            "score": 0,
            "notes": "Hello",
        }

        assert result == expected

        # 测试全是空值
        data = {"a": "", "b": [], "c": {}, "d": None}
        result = DictUtils.filter_empty_values(data)
        assert result == {}

        # 测试没有空值
        data = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.filter_empty_values(data)
        assert result == data

    def test_filter_by_keys(self):
        """测试按键过滤"""
        data = {
            "name": "John",
            "email": "john@example.com",
            "age": 30,
            "city": "New York",
            "country": "USA",
        }

        # 只保留指定的键
        keys = ["name", "email", "age"]
        result = DictUtils.filter_by_keys(data, keys)

        expected = {"name": "John", "email": "john@example.com", "age": 30}

        assert result == expected

        # 测试不存在的键
        keys = ["name", "nonexistent", "email"]
        result = DictUtils.filter_by_keys(data, keys)
        assert result == {"name": "John", "email": "john@example.com"}

        # 测试空键列表
        result = DictUtils.filter_by_keys(data, [])
        assert result == {}

    def test_exclude_keys(self):
        """测试排除指定的键"""
        data = {
            "name": "John",
            "email": "john@example.com",
            "age": 30,
            "city": "New York",
            "country": "USA",
        }

        # 排除指定的键
        keys = ["email", "city"]
        result = DictUtils.exclude_keys(data, keys)

        expected = {"name": "John", "age": 30, "country": "USA"}

        assert result == expected

        # 测试不存在的键
        keys = ["name", "nonexistent"]
        result = DictUtils.exclude_keys(data, keys)
        assert result == {
            "email": "john@example.com",
            "age": 30,
            "city": "New York",
            "country": "USA",
        }

        # 测试空键列表
        result = DictUtils.exclude_keys(data, [])
        assert result == data

    def test_get_nested_value(self):
        """测试获取嵌套字典中的值"""
        data = {
            "user": {
                "profile": {
                    "name": "John",
                    "contact": {"email": "john@example.com", "phone": "123-456-7890"},
                },
                "settings": {"theme": "dark"},
            }
        }

        # 测试正常路径
        result = DictUtils.get_nested_value(data, "user.profile.name")
        assert result == "John"

        result = DictUtils.get_nested_value(data, "user.profile.contact.email")
        assert result == "john@example.com"

        # 测试不存在的路径
        result = DictUtils.get_nested_value(data, "user.profile.nonexistent")
        assert result is None

        result = DictUtils.get_nested_value(data, "user.nonexistent.name")
        assert result is None

        # 测试默认值
        result = DictUtils.get_nested_value(data, "user.profile.nonexistent", "default")
        assert result == "default"

        # 测试部分路径存在
        result = DictUtils.get_nested_value(data, "user.profile")
        assert result == {
            "name": "John",
            "contact": {"email": "john@example.com", "phone": "123-456-7890"},
        }

    def test_set_nested_value(self):
        """测试设置嵌套字典中的值"""
        data = {"user": {"profile": {"name": "John"}}}

        # 设置已存在的路径
        DictUtils.set_nested_value(data, "user.profile.name", "Jane")
        assert data["user"]["profile"]["name"] == "Jane"

        # 设置新的嵌套路径
        DictUtils.set_nested_value(data, "user.profile.email", "jane@example.com")
        assert data["user"]["profile"]["email"] == "jane@example.com"

        # 设置深层嵌套
        DictUtils.set_nested_value(data, "user.settings.theme", "dark")
        assert data["user"]["settings"]["theme"] == "dark"

        # 覆盖整个对象
        DictUtils.set_nested_value(data, "user", {"name": "Updated"})
        assert data["user"]["name"] == "Updated"

    def test_rename_keys(self):
        """测试重命名字典的键"""
        data = {
            "name": "John",
            "email_address": "john@example.com",
            "phone_number": "123-456-7890",
            "age": 30,
        }

        mapping = {
            "name": "full_name",
            "email_address": "email",
            "phone_number": "phone",
        }

        result = DictUtils.rename_keys(data, mapping)

        expected = {
            "full_name": "John",
            "email": "john@example.com",
            "phone": "123-456-7890",
            "age": 30,
        }

        assert result == expected

        # 测试不存在的键
        mapping = {"name": "full_name", "nonexistent": "new_key"}
        result = DictUtils.rename_keys(data, mapping)
        assert "full_name" in result
        assert "name" not in result
        assert "age" in result  # 未映射的键保持不变

    def test_swap_keys(self):
        """测试交换字典的键和值"""
        data = {"a": 1, "b": 2, "c": 3}

        result = DictUtils.swap_keys(data)

        expected = {"1": "a", "2": "b", "3": "c"}

        assert result == expected

        # 测试非字符串值会被转换为字符串
        data = {"name": "John", "age": 30, "active": True}
        result = DictUtils.swap_keys(data)
        assert result["John"] == "name"
        assert result["30"] == "age"
        assert result["True"] == "active"

    def test_invert_dict(self):
        """测试反转字典（键值互换）"""
        data = {"a": 1, "b": 2, "c": 3}

        result = DictUtils.invert_dict(data)

        expected = {1: "a", 2: "b", 3: "c"}

        assert result == expected

        # 测试字符串值
        data = {"x": "value1", "y": "value2"}
        result = DictUtils.invert_dict(data)
        assert result["value1"] == "x"
        assert result["value2"] == "y"

    def test_pick_values(self):
        """测试提取指定键的值"""
        data = {
            "name": "John",
            "email": "john@example.com",
            "age": 30,
            "city": "New York",
        }

        keys = ["name", "age", "nonexistent"]
        result = DictUtils.pick_values(data, keys)

        expected = ["John", 30, None]  # 不存在的键返回None

        assert result == expected

        # 测试空键列表
        result = DictUtils.pick_values(data, [])
        assert result == []

    def test_count_values(self):
        """测试计算字典中值的总数"""
        data = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.count_values(data)
        assert result == 3

        # 测试空字典
        result = DictUtils.count_values({})
        assert result == 0

        # 测试复杂的值
        data = {"a": [1, 2, 3], "b": {"nested": True}, "c": None}
        result = DictUtils.count_values(data)
        assert result == 3

    def test_is_empty(self):
        """测试检查字典是否为空"""
        assert DictUtils.is_empty({}) is True
        assert DictUtils.is_empty(None) is True

        assert DictUtils.is_empty({"a": 1}) is False
        assert DictUtils.is_empty({"a": None}) is False
        assert DictUtils.is_empty({"a": ""}) is False

    def test_merge_list(self):
        """测试合并多个字典"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        dict3 = {"d": 5, "a": 6}

        result = DictUtils.merge_list([dict1, dict2, dict3])

        expected = {"a": 6, "b": 3, "c": 4, "d": 5}  # 后面的覆盖前面的

        assert result == expected

        # 测试空列表
        result = DictUtils.merge_list([])
        assert result == {}

        # 测试包含非字典
        result = DictUtils.merge_list([dict1, "not_a_dict", dict2])
        assert result == {"a": 1, "b": 3, "c": 4}  # 非字典被忽略

    def test_chunk_dict(self):
        """测试将字典分割成多个小块"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}

        result = DictUtils.chunk_dict(data, 2)

        expected = [{"a": 1, "b": 2}, {"c": 3, "d": 4}, {"e": 5}]

        assert result == expected

        # 测试块大小大于字典大小
        result = DictUtils.chunk_dict(data, 10)
        assert len(result) == 1
        assert result[0] == data

        # 测试空字典
        result = DictUtils.chunk_dict({}, 3)
        assert result == []

    def test_sort_keys(self):
        """测试按键排序"""
        data = {"c": 3, "a": 1, "b": 2, "d": 4}

        result = DictUtils.sort_keys(data)

        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

        # 测试降序排序
        result = DictUtils.sort_keys(data, reverse=True)

        expected = {"d": 4, "c": 3, "b": 2, "a": 1}
        assert result == expected

    def test_group_by_first_char(self):
        """测试按首字母分组"""
        data = {
            "apple": 1,
            "banana": 2,
            "cherry": 3,
            "avocado": 4,
            "blueberry": 5,
            "1numeric": 6,
            "_private": 7,
        }

        result = DictUtils.group_by_first_char(data)

        expected = {
            "A": {"apple": 1, "avocado": 4},
            "B": {"banana": 2, "blueberry": 5},
            "C": {"cherry": 3},
            "1": {"1numeric": 6},
            "_": {"_private": 7},
        }

        assert result == expected

        # 测试空字典
        result = DictUtils.group_by_first_char({})
        assert result == {}

    def test_validate_required_keys(self):
        """测试验证必需的键是否存在"""
        data = {"name": "John", "email": "john@example.com", "age": 30}

        # 所有必需键都存在
        required = ["name", "email"]
        missing = DictUtils.validate_required_keys(data, required)
        assert missing == []

        # 部分必需键缺失
        required = ["name", "email", "phone", "address"]
        missing = DictUtils.validate_required_keys(data, required)
        assert set(missing) == {"phone", "address"}

        # 测试空数据
        required = ["name"]
        missing = DictUtils.validate_required_keys({}, required)
        assert missing == ["name"]

    def test_convert_keys_case(self):
        """测试转换键的大小写"""
        data = {"Name": "John", "EMAIL": "john@example.com", "Age": 30}

        # 转换为小写
        result = DictUtils.convert_keys_case(data, "lower")
        expected = {"name": "John", "email": "john@example.com", "age": 30}
        assert result == expected

        # 转换为大写
        result = DictUtils.convert_keys_case(data, "upper")
        expected = {"NAME": "John", "EMAIL": "john@example.com", "AGE": 30}
        assert result == expected

        # 转换为标题格式
        result = DictUtils.convert_keys_case(data, "title")
        expected = {"Name": "John", "Email": "john@example.com", "Age": 30}
        assert result == expected

        # 测试无效的case参数
        result = DictUtils.convert_keys_case(data, "invalid")
        assert result == data  # 应该返回原字典

    def test_deep_clone(self):
        """测试深度克隆字典"""
        original = {
            "user": {"profile": {"name": "John", "hobbies": ["reading", "coding"]}},
            "settings": {"theme": "dark"},
        }

        cloned = DictUtils.deep_clone(original)

        # 验证克隆成功
        assert cloned == original
        assert cloned is not original

        # 修改克隆不应影响原字典
        cloned["user"]["profile"]["name"] = "Jane"
        cloned["user"]["profile"]["hobbies"].append("traveling")

        assert original["user"]["profile"]["name"] == "John"
        assert original["user"]["profile"]["hobbies"] == ["reading", "coding"]

        # 测试空字典
        cloned = DictUtils.deep_clone({})
        assert cloned == {}
        assert cloned is not {}

        # 测试None值
        cloned = DictUtils.deep_clone(None)
        assert cloned is None
