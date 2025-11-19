from typing import Optional

"""
DictUtils最终测试 - 完善42%到65%+覆盖率
针对未覆盖的字典工具函数进行全面测试
"""

import pytest

from src.utils.dict_utils import DictUtils


class TestDictUtilsFinal:
    """DictUtils最终测试类 - 提升覆盖率到65%+"""

    def test_filter_none_values_function(self):
        """测试过滤None值功能"""
        data = {"name": "John", "age": None, "email": "john@example.com", "phone": None}
        result = DictUtils.filter_none_values(data)
        expected = {"name": "John", "email": "john@example.com"}
        assert result == expected

        # 空字典
        assert DictUtils.filter_none_values({}) == {}

        # 没有None值
        data = {"name": "John", "age": 30}
        result = DictUtils.filter_none_values(data)
        assert result == data

    def test_filter_empty_values_function(self):
        """测试过滤空值功能"""
        data = {
            "name": "John",
            "email": "",
            "age": 30,
            "hobbies": [],
            "address": {},
            "phone": None,
        }
        result = DictUtils.filter_empty_values(data)
        expected = {"name": "John", "age": 30}
        assert result == expected

        # 包含有效空值
        data = {"name": "John", "note": " ", "count": 0}
        result = DictUtils.filter_empty_values(data)
        assert result == data  # 空格、0不算空值

    def test_filter_by_keys_function(self):
        """测试按键过滤功能"""
        data = {
            "name": "John",
            "age": 30,
            "email": "john@example.com",
            "phone": "123456",
        }
        keys = ["name", "email"]
        result = DictUtils.filter_by_keys(data, keys)
        expected = {"name": "John", "email": "john@example.com"}
        assert result == expected

        # 不存在的键
        keys = ["name", "nonexistent"]
        result = DictUtils.filter_by_keys(data, keys)
        expected = {"name": "John"}
        assert result == expected

        # 空键列表
        result = DictUtils.filter_by_keys(data, [])
        assert result == {}

    def test_exclude_keys_function(self):
        """测试排除键功能"""
        data = {
            "name": "John",
            "age": 30,
            "email": "john@example.com",
            "phone": "123456",
        }
        exclude = ["age", "phone"]
        result = DictUtils.exclude_keys(data, exclude)
        expected = {"name": "John", "email": "john@example.com"}
        assert result == expected

        # 排除不存在的键
        exclude = ["name", "nonexistent"]
        result = DictUtils.exclude_keys(data, exclude)
        expected = {"age": 30, "email": "john@example.com", "phone": "123456"}
        assert result == expected

    def test_get_nested_value_function(self):
        """测试获取嵌套值功能"""
        data = {
            "user": {
                "profile": {"name": "John", "age": 30},
                "settings": {"theme": "dark"},
            }
        }

        # 获取嵌套值
        result = DictUtils.get_nested_value(data, "user.profile.name")
        assert result == "John"

        result = DictUtils.get_nested_value(data, "user.profile.age")
        assert result == 30

        # 不存在的路径
        result = DictUtils.get_nested_value(data, "user.profile.nonexistent")
        assert result is None

        result = DictUtils.get_nested_value(data, "nonexistent.path")
        assert result is None

        # 自定义默认值
        result = DictUtils.get_nested_value(data, "user.profile.nonexistent", "default")
        assert result == "default"

    def test_set_nested_value_function(self):
        """测试设置嵌套值功能"""
        data = {"user": {"profile": {"name": "John"}}}

        # 设置现有嵌套值
        DictUtils.set_nested_value(data, "user.profile.name", "Jane")
        assert data["user"]["profile"]["name"] == "Jane"

        # 设置新嵌套值
        DictUtils.set_nested_value(data, "user.profile.age", 30)
        assert data["user"]["profile"]["age"] == 30

        # 创建新的嵌套路径
        DictUtils.set_nested_value(data, "user.settings.theme", "dark")
        assert data["user"]["settings"]["theme"] == "dark"

        # 深层嵌套
        DictUtils.set_nested_value(data, "app.database.connection.host", "localhost")
        assert data["app"]["database"]["connection"]["host"] == "localhost"

    def test_rename_keys_function(self):
        """测试重命名键功能"""
        data = {"name": "John", "age": 30, "email": "john@example.com"}
        key_map = {"name": "full_name", "email": "email_address"}
        result = DictUtils.rename_keys(data, key_map)
        expected = {"full_name": "John", "age": 30, "email_address": "john@example.com"}
        assert result == expected

        # 不在映射中的键保持不变
        assert "age" in result

    def test_swap_keys_function(self):
        """测试交换键值功能"""
        data = {"name": "John", "age": 30, "active": True}
        result = DictUtils.swap_keys(data)
        expected = {"John": "name", "30": "age", "True": "active"}
        assert result == expected

        # 注意：如果值不是字符串，会被转换为字符串
        assert isinstance(list(result.keys())[0], str)

    def test_invert_dict_function(self):
        """测试反转字典功能"""
        data = {"name": "John", "age": 30, "status": "active"}
        result = DictUtils.invert_dict(data)
        expected = {"John": "name", 30: "age", "active": "status"}
        assert result == expected

        # 与swap_keys的区别在于值可以不是字符串
        data = {"a": 1, "b": 2}
        result = DictUtils.invert_dict(data)
        expected = {1: "a", 2: "b"}
        assert result == expected

    def test_pick_values_function(self):
        """测试提取值功能"""
        data = {
            "name": "John",
            "age": 30,
            "email": "john@example.com",
            "phone": "123456",
        }
        keys = ["name", "age", "nonexistent"]
        result = DictUtils.pick_values(data, keys)
        expected = ["John", 30, None]
        assert result == expected

        # 空键列表
        result = DictUtils.pick_values(data, [])
        assert result == []

    def test_count_values_function(self):
        """测试计数值功能"""
        data = {"name": "John", "age": 30, "email": "john@example.com"}
        result = DictUtils.count_values(data)
        assert result == 3

        # 空字典
        assert DictUtils.count_values({}) == 0

    def test_is_empty_function(self):
        """测试检查空字典功能"""
        assert DictUtils.is_empty({}) is True
        assert DictUtils.is_empty(None) is True
        assert DictUtils.is_empty({"key": "value"}) is False

    def test_merge_list_function(self):
        """测试合并字典列表功能"""
        dicts = [
            {"name": "John", "age": 30},
            {"email": "john@example.com"},
            {"phone": "123456", "age": 31},
        ]
        result = DictUtils.merge_list(dicts)
        expected = {
            "name": "John",
            "age": 31,
            "email": "john@example.com",
            "phone": "123456",
        }
        assert result == expected

        # 包含非字典项
        dicts = [{"name": "John"}, "not_a_dict", {"age": 30}]
        result = DictUtils.merge_list(dicts)
        expected = {"name": "John", "age": 30}
        assert result == expected

        # 空列表
        assert DictUtils.merge_list([]) == {}

    def test_chunk_dict_function(self):
        """测试字典分块功能"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
        result = DictUtils.chunk_dict(data, 2)
        expected = [{"a": 1, "b": 2}, {"c": 3, "d": 4}, {"e": 5}]
        assert result == expected

        # 分块大小大于字典大小
        result = DictUtils.chunk_dict(data, 10)
        assert len(result) == 1
        assert result[0] == data

        # 分块大小为1
        result = DictUtils.chunk_dict(data, 1)
        assert len(result) == 5
        assert result[0] == {"a": 1}

    def test_sort_keys_function(self):
        """测试按键排序功能"""
        data = {"z": 1, "a": 2, "m": 3}
        result = DictUtils.sort_keys(data)
        expected = {"a": 2, "m": 3, "z": 1}
        assert result == expected

        # 反向排序
        result = DictUtils.sort_keys(data, reverse=True)
        expected = {"z": 1, "m": 3, "a": 2}
        assert result == expected

        # 空字典
        assert DictUtils.sort_keys({}) == {}

    def test_group_by_first_char_function(self):
        """测试按首字母分组功能"""
        data = {"apple": 1, "banana": 2, "cherry": 3, "apricot": 4, "blueberry": 5}
        result = DictUtils.group_by_first_char(data)

        assert "A" in result
        assert "B" in result
        assert "C" in result
        assert result["A"]["apple"] == 1
        assert result["A"]["apricot"] == 4
        assert result["B"]["banana"] == 2
        assert result["B"]["blueberry"] == 5
        assert result["C"]["cherry"] == 3

        # 空键名
        data = {"": "empty", "test": "value"}
        result = DictUtils.group_by_first_char(data)
        assert "_" in result
        assert result["_"][""] == "empty"

    def test_validate_required_keys_function(self):
        """测试验证必需键功能"""
        data = {"name": "John", "age": 30, "email": "john@example.com"}
        required_keys = ["name", "email"]
        result = DictUtils.validate_required_keys(data, required_keys)
        assert result == []

        # 缺少必需键
        required_keys = ["name", "email", "phone"]
        result = DictUtils.validate_required_keys(data, required_keys)
        assert result == ["phone"]

        # 全部缺少
        required_keys = ["nonexistent1", "nonexistent2"]
        result = DictUtils.validate_required_keys(data, required_keys)
        assert set(result) == {"nonexistent1", "nonexistent2"}

        # 空必需键列表
        result = DictUtils.validate_required_keys(data, [])
        assert result == []

    def test_convert_keys_case_function(self):
        """测试转换键大小写功能"""
        data = {"Name": "John", "Age": 30, "Email": "john@example.com"}

        # 转小写
        result = DictUtils.convert_keys_case(data, "lower")
        expected = {"name": "John", "age": 30, "email": "john@example.com"}
        assert result == expected

        # 转大写
        result = DictUtils.convert_keys_case(data, "upper")
        expected = {"NAME": "John", "AGE": 30, "EMAIL": "john@example.com"}
        assert result == expected

        # 转标题格式
        result = DictUtils.convert_keys_case(data, "title")
        expected = {"Name": "John", "Age": 30, "Email": "john@example.com"}
        assert result == expected

        # 无效格式
        result = DictUtils.convert_keys_case(data, "invalid")
        assert result == data

    def test_deep_clone_function(self):
        """测试深度克隆功能"""
        original = {
            "name": "John",
            "profile": {"age": 30, "hobbies": ["reading", "coding"]},
        }

        cloned = DictUtils.deep_clone(original)

        # 验证内容相同
        assert cloned == original

        # 验证是不同对象
        assert cloned is not original
        assert cloned["profile"] is not original["profile"]
        assert cloned["profile"]["hobbies"] is not original["profile"]["hobbies"]

        # 修改克隆不应该影响原对象
        cloned["profile"]["age"] = 31
        assert original["profile"]["age"] == 30

    def test_merge_function(self):
        """测试浅度合并功能"""
        dict1 = {"name": "John", "age": 30}
        dict2 = {"email": "john@example.com", "age": 31}
        result = DictUtils.merge(dict1, dict2)
        expected = {"name": "John", "age": 31, "email": "john@example.com"}
        assert result == expected

        # 原字典不应该被修改
        assert dict1 == {"name": "John", "age": 30}
        assert dict2 == {"email": "john@example.com", "age": 31}

    def test_get_function(self):
        """测试获取值功能"""
        data = {"name": "John", "age": 30}

        # 获取存在的值
        assert DictUtils.get(data, "name") == "John"

        # 获取不存在的值（无默认值）
        assert DictUtils.get(data, "nonexistent") is None

        # 获取不存在的值（有默认值）
        assert DictUtils.get(data, "nonexistent", "default") == "default"

    def test_has_key_function(self):
        """测试检查键存在功能"""
        data = {"name": "John", "age": 30}

        assert DictUtils.has_key(data, "name") is True
        assert DictUtils.has_key(data, "nonexistent") is False

    def test_filter_keys_function(self):
        """测试根据函数过滤键功能"""
        data = {
            "name": "John",
            "age": 30,
            "email": "john@example.com",
            "phone": "123456",
        }

        # 过滤长度大于3的键
        result = DictUtils.filter_keys(data, lambda k: len(k) > 3)
        expected = {"name": "John", "email": "john@example.com", "phone": "123456"}
        assert result == expected

        # 过滤以'a'开头的键
        result = DictUtils.filter_keys(data, lambda k: k.startswith("a"))
        expected = {"age": 30}
        assert result == expected

    def test_edge_cases_and_error_handling(self):
        """测试边界情况和错误处理"""
        # 空字典操作
        assert DictUtils.filter_none_values({}) == {}
        assert DictUtils.filter_empty_values({}) == {}
        assert DictUtils.filter_by_keys({}, ["key"]) == {}
        assert DictUtils.exclude_keys({}, ["key"]) == {}

        # None输入处理
        assert DictUtils.is_empty(None) is True

        # 非字典输入（大部分函数应该能处理）
        with pytest.raises(AttributeError):
            DictUtils.filter_none_values("not_a_dict")

        # 复杂嵌套结构
        complex_data = {"level1": {"level2": {"level3": {"value": "deep"}}}}

        # 深度嵌套操作
        assert (
            DictUtils.get_nested_value(complex_data, "level1.level2.level3.value")
            == "deep"
        )
        DictUtils.set_nested_value(
            complex_data, "level1.level2.level3.new_value", "new"
        )
        assert complex_data["level1"]["level2"]["level3"]["new_value"] == "new"

    def test_comprehensive_workflow(self):
        """测试完整的字典工具工作流程"""
        # 1. 创建原始数据
        user_data = {
            "Name": "John Doe",
            "Age": 30,
            "Email": "john@example.com",
            "Profile": {
                "Bio": "Software Developer",
                "Skills": ["Python", "JavaScript", "SQL"],
            },
            "Settings": None,
            "Hobbies": [],
        }

        # 2. 清理数据
        cleaned = DictUtils.filter_empty_values(user_data)
        assert "Settings" not in cleaned
        assert "Hobbies" not in cleaned

        # 3. 转换键名格式
        converted = DictUtils.convert_keys_case(cleaned, "lower")
        assert "name" in converted
        assert "age" in converted

        # 4. 提取特定键的值
        keys = ["name", "age", "nonexistent"]
        values = DictUtils.pick_values(converted, keys)
        assert values[0] == "John Doe"
        assert values[1] == 30
        assert values[2] is None

        # 5. 处理嵌套数据
        bio = DictUtils.get_nested_value(converted, "profile.bio")
        assert bio == "Software Developer"

        # 6. 分组操作
        grouped = DictUtils.group_by_first_char(converted)
        assert "N" in grouped
        assert "P" in grouped

        # 7. 深度克隆和修改
        cloned = DictUtils.deep_clone(converted)
        DictUtils.set_nested_value(cloned, "profile.bio", "Senior Developer")
        assert converted["profile"]["bio"] == "Software Developer"
        assert cloned["profile"]["bio"] == "Senior Developer"
