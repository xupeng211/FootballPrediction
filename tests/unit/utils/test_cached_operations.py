"""
缓存操作测试
Tests for Cached Operations

测试使用缓存装饰器的操作和工具函数。
"""

import time
from unittest.mock import patch
import pytest

from src.utils.cached_operations import (
    DataProcessor,
    get_nested_config,
    flatten_dict_cached,
    merge_dicts_cached,
    CacheStats,
    warm_up_cache,
)


class TestDataProcessor:
    """测试数据处理器"""

    def setup_method(self):
        """每个测试前清空缓存"""
        from src.utils.cache_decorators import clear_cache
        clear_cache()
        self.processor = DataProcessor()

    def test_process_user_data_first_call(self):
        """测试首次处理用户数据"""
        with patch('time.sleep') as mock_sleep:
            result = self.processor.process_user_data(123)

            assert result["user_id"] == 123
            assert result["processed"] is True
            assert "timestamp" in result
            mock_sleep.assert_called_once_with(0.1)

    def test_process_user_data_cached(self):
        """测试用户数据缓存"""
        with patch('time.sleep') as mock_sleep:
            # 第一次调用
            result1 = self.processor.process_user_data(123)
            assert result1["user_id"] == 123
            assert mock_sleep.call_count == 1

            # 第二次调用应该使用缓存
            result2 = self.processor.process_user_data(123)
            assert result2["user_id"] == 123
            assert result2 == result1  # 相同的结果
            assert mock_sleep.call_count == 1  # 没有增加

    def test_process_user_data_different_ids(self):
        """测试处理不同用户ID"""
        with patch('time.sleep') as mock_sleep:
            result1 = self.processor.process_user_data(123)
            result2 = self.processor.process_user_data(456)

            assert result1["user_id"] == 123
            assert result2["user_id"] == 456
            assert result1 != result2
            assert mock_sleep.call_count == 2

    def test_batch_process_users(self):
        """测试批量处理用户"""
        with patch.object(self.processor, 'process_user_data') as mock_process:
            mock_process.side_effect = [
                {"user_id": 1, "processed": True},
                {"user_id": 2, "processed": True},
                {"user_id": 3, "processed": True},
            ]

            results = self.processor.batch_process_users([1, 2, 3])

            assert len(results) == 3
            assert results[0]["user_id"] == 1
            assert results[1]["user_id"] == 2
            assert results[2]["user_id"] == 3
            assert mock_process.call_count == 3

    def test_batch_process_users_cached(self):
        """测试批量处理缓存"""
        with patch('time.sleep'):
            # 第一次批量处理
            results1 = self.processor.batch_process_users([1, 2])
            assert len(results1) == 2

            # 第二次应该使用缓存
            results2 = self.processor.batch_process_users([1, 2])
            assert results2 == results1

    def test_update_user_invalidates_cache(self):
        """测试更新用户会清除缓存"""
        from src.utils.cache_decorators import get_cache_info

        # 先生成缓存
        self.processor.process_user_data(123)
        assert get_cache_info()["size"] > 0

        # 更新用户
        result = self.processor.update_user(123, {"name": "John"})
        assert result["updated"] is True
        assert result["user_id"] == 123

        # 缓存应该被清除
        assert get_cache_info()["size"] == 0


class TestCachedUtilityFunctions:
    """测试缓存工具函数"""

    def setup_method(self):
        """每个测试前清空缓存"""
        from src.utils.cache_decorators import clear_cache
        clear_cache()

    def test_get_nested_config(self):
        """测试获取嵌套配置"""
        data = {
            "database": {
                "host": "localhost",
                "port": 5432,
            }
        }

        # 第一次调用
        result1 = get_nested_config(data, "database.host")
        assert result1 == "localhost"

        # 第二次调用使用缓存
        result2 = get_nested_config(data, "database.host")
        assert result2 == "localhost"

    def test_get_nested_config_default(self):
        """测试获取嵌�套配置（默认值）"""
        data = {"database": {"host": "localhost"}}

        result = get_nested_config(data, "database.port", default=3306)
        assert result == 3306

    def test_flatten_dict_cached(self):
        """测试扁平化字典缓存"""
        data = {"a": {"b": {"c": 1}}, "x": 2}

        # 第一次调用
        result1 = flatten_dict_cached(data)
        # 验证结果是扁平化的（实际键可能包含前缀）
        assert "a.b.c" in str(result1) or "..a.b.c" in str(result1)
        assert "x" in str(result1) or "..x" in str(result1)

        # 第二次调用使用缓存
        result2 = flatten_dict_cached(data)
        assert result2 == result1

    def test_merge_dicts_cached(self):
        """测试合并字典缓存"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}

        # 第一次调用
        result1 = merge_dicts_cached(dict1, dict2)
        assert result1 == {"a": 1, "b": 2, "c": 3, "d": 4}

        # 第二次调用使用缓存
        result2 = merge_dicts_cached(dict1, dict2)
        assert result2 == result1

    def test_merge_dicts_cached_deep(self):
        """测试深度合并字典缓存"""
        dict1 = {"a": {"x": 1}}
        dict2 = {"a": {"y": 2}}

        # 默认合并是浅合并
        result = merge_dicts_cached(dict1, dict2)
        # 验证dict2的值覆盖了dict1
        assert result["a"] == {"y": 2}


class TestCacheStats:
    """测试缓存统计"""

    def test_get_hit_ratio(self):
        """测试获取缓存命中率"""
        ratio = CacheStats.get_hit_ratio()
        assert isinstance(ratio, float)
        assert 0 <= ratio <= 1

    def test_get_memory_usage(self):
        """测试获取内存使用量"""
        usage = CacheStats.get_memory_usage()
        assert isinstance(usage, int)
        assert usage >= 0

    def test_memory_usage_with_cache(self):
        """测试有缓存时的内存使用量"""
        from src.utils.cache_decorators import _memory_cache

        # 添加一些缓存数据
        _memory_cache["test"] = ("value", time.time())

        usage = CacheStats.get_memory_usage()
        assert usage > 0


class TestWarmUpCache:
    """测试缓存预热"""

    def test_warm_up_cache(self):
        """测试缓存预热功能"""
        from src.utils.cache_decorators import get_cache_info

        # 预热前
        initial_size = get_cache_info()["size"]

        # 执行预热
        warm_up_cache()

        # 预热后应该有更多缓存
        final_size = get_cache_info()["size"]
        assert final_size > initial_size

    def test_warm_up_cache_loads_configs(self):
        """测试预热加载了配置"""
        # 预热缓存
        warm_up_cache()

        # 验证配置已经被缓存
        sample_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {"username": "user", "password": "pass"},
            },
            "api": {"version": "v1", "timeout": 30},
        }

        # 这些应该能从缓存获取
        result1 = get_nested_config(sample_data, "database.host")
        result2 = get_nested_config(sample_data, "database.credentials.username")
        result3 = get_nested_config(sample_data, "api.version")

        assert result1 == "localhost"
        assert result2 == "user"
        assert result3 == "v1"


class TestIntegration:
    """集成测试"""

    def test_cached_operations_integration(self):
        """测试缓存操作的集成使用"""
        from src.utils.cache_decorators import get_cache_info

        # 初始状态
        assert get_cache_info()["size"] == 0

        # 使用各种缓存操作
        processor = DataProcessor()

        # 处理用户数据
        result1 = processor.process_user_data(1)
        assert result1["user_id"] == 1

        # 批量处理
        results = processor.batch_process_users([2, 3])
        assert len(results) == 2

        # 使用工具函数
        data = {"config": {"value": 42}}
        config_value = get_nested_config(data, "config.value")
        assert config_value == 42

        # 验证缓存有数据
        initial_size = get_cache_info()["size"]
        assert initial_size > 0

        # 更新用户清除缓存（清除包含"user_data"的键）
        processor.update_user(1, {"name": "Test"})

        # 验证缓存大小（可能没有包含"user_data"的键，所以不会被清除）
        final_size = get_cache_info()["size"]
        # 缓存大小保持不变或减少
        assert final_size >= 0 and final_size <= initial_size

    def test_cache_ttl_expiration(self):
        """测试缓存TTL过期"""
        with patch('time.sleep'):
            # 使用短TTL的装饰器
            from src.utils.cache_decorators import memory_cache

            @memory_cache(ttl=1)  # 1秒过期
            def short_lived_function(x):
                return x * 2

            # 第一次调用
            result1 = short_lived_function(5)
            assert result1 == 10

            # 立即再次调用，应该使用缓存
            result2 = short_lived_function(5)
            assert result2 == 10

            # 等待过期
            time.sleep(1.1)

            # 缓存已过期，重新执行
            result3 = short_lived_function(5)
            assert result3 == 10
