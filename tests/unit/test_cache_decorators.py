"""
缓存装饰器模块测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import time
from typing import Any, Dict, Optional


class TestCacheDecorators:
    """缓存装饰器测试"""

    def test_make_cache_key_basic(self):
        """测试基础缓存键生成"""
        from src.cache.decorators import _make_cache_key

        def test_func(a, b, c=None):
            return a + b + (c or 0)

        key = _make_cache_key(test_func, (1, 2), {"c": 3})
        assert isinstance(key, str)
        assert "test_func" in key

    def test_make_cache_key_with_prefix(self):
        """测试带前缀的缓存键生成"""
        from src.cache.decorators import _make_cache_key

        def test_func(x):
            return x * 2

        key = _make_cache_key(test_func, (5,), {}, prefix="custom")
        assert "custom" in key
        assert "test_func" in key

    def test_make_cache_key_with_user_id(self):
        """测试带用户ID的缓存键生成"""
        from src.cache.decorators import _make_cache_key

        def test_func(x):
            return x * 2

        key = _make_cache_key(test_func, (5,), {}, user_id=123)
        assert "123" in key
        assert "user" in key.lower()

    def test_make_cache_key_exclude_args(self):
        """测试排除参数的缓存键生成"""
        from src.cache.decorators import _make_cache_key

        def test_func(a, b, sensitive=None):
            return a + b

        key = _make_cache_key(
            test_func, (1, 2), {"sensitive": "secret"}, exclude_args=["sensitive"]
        )
        assert "secret" not in key
        assert "test_func" in key

    def test_cache_result_sync(self):
        """测试同步函数结果缓存"""
        # 由于redis可能不可用，使用模拟
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis

            # 模拟缓存未命中
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True

            from src.cache.decorators import cache_result

            @cache_result(ttl=60)
            def expensive_function(x):
                return x * 2

            # 第一次调用
            result = expensive_function(5)
            assert result == 10
            mock_redis.get.assert_called()
            mock_redis.set.assert_called()

    def test_cache_result_async(self):
        """测试异步函数结果缓存"""
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis

            # 模拟缓存未命中
            mock_redis.aget.return_value = None
            mock_redis.aset.return_value = True

            from src.cache.decorators import cache_result

            @cache_result(ttl=60)
            async def expensive_async_function(x):
                await asyncio.sleep(0.01)  # 模拟异步操作
                return x * 2

            async def test():
                result = await expensive_async_function(5)
                assert result == 10
                mock_redis.aget.assert_called()
                mock_redis.aset.assert_called()

            asyncio.run(test())

    def test_cache_result_with_cache_hit(self):
        """测试缓存命中"""
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis

            # 模拟缓存命中
            mock_redis.get.return_value = '{"value": 20}'

            from src.cache.decorators import cache_result

            call_count = 0

            @cache_result(ttl=60)
            def expensive_function(x):
                nonlocal call_count
                call_count += 1
                return x * 2

            # 第一次调用
            result1 = expensive_function(10)
            assert result1 == 20
            assert call_count == 0  # 由于缓存命中，函数不应该被调用

    def test_cache_with_ttl(self):
        """测试带TTL的缓存"""
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis
            mock_redis.get.return_value = None

            from src.cache.decorators import cache_with_ttl

            @cache_with_ttl(timedelta(minutes=5))
            def test_function(x):
                return x + 1

            result = test_function(10)
            assert result == 11

            # 验证TTL被正确转换
            mock_redis.set.assert_called()
            args, kwargs = mock_redis.set.call_args
            assert 300 <= kwargs.get("ex", 0) <= 301  # 5分钟 = 300秒

    def test_cache_by_user(self):
        """测试基于用户的缓存"""
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis
            mock_redis.get.return_value = None

            from src.cache.decorators import cache_by_user

            @cache_by_user(ttl=60)
            def user_specific_data(user_id, data_type):
                return f"data_{user_id}_{data_type}"

            # 模拟用户上下文
            with patch("src.cache.decorators.get_current_user_id", return_value=123):
                result = user_specific_data("profile")
                assert result == "data_123_profile"

    def test_cache_invalidate(self):
        """测试缓存失效"""
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis

            from src.cache.decorators import cache_invalidate

            @cache_invalidate
            def update_data(key):
                return f"updated_{key}"

            result = update_data("test_key")
            assert result == "updated_test_key"
            # 缓存失效应该被调用
            mock_redis.delete.assert_called()

    def test_cache_decorator_with_method(self):
        """测试装饰器用于方法"""
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis
            mock_redis.get.return_value = None

            from src.cache.decorators import cache_result

            class TestClass:
                def __init__(self, value):
                    self.value = value

                @cache_result(ttl=60)
                def compute(self, x):
                    return self.value + x

            obj = TestClass(10)
            result = obj.compute(5)
            assert result == 15

    def test_cache_key_uniqueness(self):
        """测试缓存键的唯一性"""
        from src.cache.decorators import _make_cache_key

        def func1(x):
            return x

        def func2(x):
            return x * 2

        key1 = _make_cache_key(func1, (5,), {})
        key2 = _make_cache_key(func2, (5,), {})

        # 不同函数应该产生不同的键
        assert key1 != key2

        # 相同函数不同参数应该产生不同的键
        key3 = _make_cache_key(func1, (10,), {})
        assert key1 != key3

    def test_cache_decorator_error_handling(self):
        """测试装饰器的错误处理"""
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis

            # Redis抛出异常时，函数应该正常执行
            mock_redis.get.side_effect = Exception("Redis error")

            from src.cache.decorators import cache_result

            @cache_result(ttl=60)
            def test_function(x):
                return x * 2

            # 即使Redis出错，函数也应该正常工作
            result = test_function(5)
            assert result == 10

    def test_cache_with_none_value(self):
        """测试缓存None值"""
        with patch("src.cache.decorators.RedisManager") as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis_class.return_value = mock_redis

            from src.cache.decorators import cache_result

            call_count = 0

            @cache_result(ttl=60)
            def returns_none():
                nonlocal call_count
                call_count += 1
                return None

            # 第一次调用
            result1 = returns_none()
            assert result1 is None
            assert call_count == 1

            # 第二次调用（如果缓存了None值）
            result2 = returns_none()
            assert result2 is None
            # 取决于实现，None值可能被缓存也可能不被缓存
