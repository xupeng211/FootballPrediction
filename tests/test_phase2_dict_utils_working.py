"""
Src模块扩展测试 - Phase 2: DictUtils工作版本测试
目标: 提升src模块覆盖率，向65%历史水平迈进

专门测试DictUtils模块的核心功能，基于实际模块行为编写测试
"""

import pytest
import sys
import os

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 直接导入DictUtils模块
from utils.dict_utils import DictUtils


class TestDictUtilsCoreWorking:
    """DictUtils核心功能测试（工作版本）"""

    def test_merge_basic_functionality(self):
        """测试基本合并功能"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}

        result = DictUtils.merge(dict1, dict2)

        assert result == {"a": 1, "b": 3, "c": 4}
        assert "a" in result
        assert result["b"] == 3  # dict2覆盖dict1
        assert "c" in result

    def test_merge_with_empty_dicts(self):
        """测试空字典合并"""
        # 第一个字典为空
        result = DictUtils.merge({}, {"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

        # 第二个字典为空
        result = DictUtils.merge({"a": 1}, {})
        assert result == {"a": 1}

        # 都为空
        result = DictUtils.merge({}, {})
        assert result == {}

    def test_merge_different_types(self):
        """测试不同类型值的合并"""
        dict1 = {
            "string": "value1",
            "number": 1,
            "boolean": True,
            "list": [1, 2],
            "nested": {"inner": "value"}
        }
        dict2 = {
            "string": "value2",
            "number": 2,
            "boolean": False,
            "list": [3, 4],
            "nested": {"new_inner": "new_value"}
        }

        result = DictUtils.merge(dict1, dict2)

        # dict2应该完全覆盖dict1的值
        assert result["string"] == "value2"
        assert result["number"] == 2
        assert result["boolean"] == False
        assert result["list"] == [3, 4]
        assert result["nested"] == {"new_inner": "new_value"}

    def test_get_basic_functionality(self):
        """测试基本获取功能"""
        d = {"a": 1, "b": "value", "c": [1, 2, 3]}

        # 获取存在的键
        assert DictUtils.get(d, "a") == 1
        assert DictUtils.get(d, "b") == "value"
        assert DictUtils.get(d, "c") == [1, 2, 3]

        # 获取不存在的键
        assert DictUtils.get(d, "nonexistent") is None

        # 带默认值的获取
        assert DictUtils.get(d, "nonexistent", "default") == "default"
        assert DictUtils.get(d, "a", "default") == 1  # 存在时忽略默认值

    def test_get_edge_cases(self):
        """测试获取功能边界情况"""
        # 空字典
        empty_dict = {}
        assert DictUtils.get(empty_dict, "key") is None
        assert DictUtils.get(empty_dict, "key", "default") == "default"

        # 嵌套字典中的值
        nested_dict = {
            "level1": {
                "level2": {
                    "value": "deep_value"
                }
            }
        }
        assert DictUtils.get(nested_dict, "level1") == {"level2": {"value": "deep_value"}}

    def test_has_key_functionality(self):
        """测试键检查功能"""
        d = {"a": 1, "b": 2, "c": None, "": "empty_key"}

        # 检查存在的键
        assert DictUtils.has_key(d, "a") == True
        assert DictUtils.has_key(d, "b") == True
        assert DictUtils.has_key(d, "c") == True  # 值为None但键存在
        assert DictUtils.has_key(d, "") == True  # 空字符串键

        # 检查不存在的键
        assert DictUtils.has_key(d, "nonexistent") == False

    def test_filter_keys_basic(self):
        """测试键过滤基本功能"""
        d = {"apple": 1, "banana": 2, "cherry": 3, "date": 4}

        # 过滤长度大于5的键
        result = DictUtils.filter_keys(d, lambda k: len(k) > 5)
        assert result == {"banana": 2, "cherry": 3}

        # 过滤以'a'开头的键
        result = DictUtils.filter_keys(d, lambda k: k.startswith('a'))
        assert result == {"apple": 1}

        # 过滤包含'e'的键
        result = DictUtils.filter_keys(d, lambda k: 'e' in k)
        assert result == {"apple": 1, "cherry": 3, "date": 4}

        # 过滤所有键（总是返回True）
        result = DictUtils.filter_keys(d, lambda k: True)
        assert result == d

        # 过滤没有键（总是返回False）
        result = DictUtils.filter_keys(d, lambda k: False)
        assert result == {}

    def test_filter_keys_with_values_condition(self):
        """测试基于值的条件过滤"""
        d = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}

        # 过滤值为偶数的键
        result = DictUtils.filter_keys(d, lambda k: d[k] % 2 == 0)
        assert result == {"b": 2, "d": 4}

        # 过滤值大于3的键
        result = DictUtils.filter_keys(d, lambda k: d[k] > 3)
        assert result == {"d": 4, "e": 5}

    def test_filter_keys_complex_logic(self):
        """测试复杂过滤逻辑"""
        d = {
            "user_id": 123,
            "username": "john_doe",
            "email": "john@example.com",
            "age": 25,
            "is_active": True,
            "created_at": "2024-01-01"
        }

        # 过滤以'user_'开头或包含'email'的键
        result = DictUtils.filter_keys(d, lambda k: k.startswith('user_') or 'email' in k)
        assert result == {"user_id": 123, "email": "john@example.com"}

        # 过滤键名长度在4-6之间的键
        result = DictUtils.filter_keys(d, lambda k: 4 <= len(k) <= 6)
        assert result == {"email": "john@example.com"}

    def test_performance_with_larger_dict(self):
        """测试较大字典的性能"""
        # 创建测试字典
        test_dict = {f"key_{i}": f"value_{i}" for i in range(100)}

        # 测试批量操作
        results = []
        for i in range(10):
            key = f"key_{i * 10}"
            value = DictUtils.get(test_dict, key)
            has_key = DictUtils.has_key(test_dict, key)
            results.append((value, has_key))

        # 验证结果
        for i, (value, has_key) in enumerate(results):
            expected_key = f"key_{i * 10}"
            expected_value = f"value_{i * 10}"
            assert value == expected_value
            assert has_key == True

    def test_dict_utils_integration_workflow(self):
        """测试DictUtils集成工作流程"""
        # 模拟配置管理场景
        default_config = {
            "app_name": "FootballPrediction",
            "debug": False,
            "port": 8000,
            "database": {"url": "sqlite:///default.db"}
        }

        user_config = {
            "debug": True,
            "port": 9000,
            "database": {"url": "postgresql://localhost/prod.db"},
            "log_level": "INFO"
        }

        # 合并配置
        merged_config = DictUtils.merge(default_config, user_config)

        # 验证合并结果
        assert DictUtils.get(merged_config, "app_name") == "FootballPrediction"  # 保留默认
        assert DictUtils.get(merged_config, "debug") == True  # 用户配置覆盖
        assert DictUtils.get(merged_config, "port") == 9000
        assert DictUtils.get(merged_config, "log_level") == "INFO"  # 新增字段

        # 过滤配置键
        db_keys = DictUtils.filter_keys(merged_config, lambda k: 'database' in k)
        assert len(db_keys) == 1
        assert DictUtils.has_key(db_keys, "database")

        # 检查特定配置
        assert DictUtils.has_key(merged_config, "debug")
        assert not DictUtils.has_key(merged_config, "nonexistent")


class TestDictUtilsErrorHandling:
    """DictUtils错误处理测试"""

    def test_invalid_input_handling(self):
        """测试无效输入处理"""
        # 对于DictUtils的实际实现，大多数方法需要有效的字典输入
        # 这里测试预期的错误行为

        import pytest

        # merge方法需要有效字典
        with pytest.raises(AttributeError):
            DictUtils.merge(None, {"a": 1})

        # get方法需要有效字典
        with pytest.raises(AttributeError):
            DictUtils.get(None, "key")

        # has_key方法需要有效字典
        with pytest.raises(TypeError):
            DictUtils.has_key(None, "key")

        # filter_keys方法需要有效字典
        with pytest.raises(AttributeError):
            DictUtils.filter_keys(None, lambda k: True)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])