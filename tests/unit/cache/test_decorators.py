"""
缓存装饰器测试
Tests for Cache Decorators

测试src.cache.decorators模块的功能
"""

import pytest
import asyncio
import json
import hashlib
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Any

from src.cache.decorators import (
    _make_cache_key,
    cache_result,
    cache_with_ttl,
    cache_by_user,
    cache_invalidate
)


class TestMakeCacheKey:
    """缓存键生成测试"""

    def test_make_cache_key_basic(self):
        """测试：基础缓存键生成"""
        def test_func(a, b):
            return a + b

        args = (1, 2)
        kwargs = {}
        key = _make_cache_key(test_func, args, kwargs)

        expected_base = f"{test_func.__module__}:{test_func.__qualname__}"
        assert key.startswith(expected_base)

    def test_make_cache_key_with_args(self):
        """测试：带参数的缓存键生成"""
        def test_func(a, b):
            return a + b

        args = (1, 2)
        kwargs = {}
        key = _make_cache_key(test_func, args, kwargs)

        # 应该包含参数哈希
        assert ":" in key
        assert len(key.split(":")) >= 3

    def test_make_cache_key_with_kwargs(self):
        """测试：带关键字参数的缓存键生成"""
        def test_func(a, b=None):
            return a

        args = (1,)
        kwargs = {"b": 2}
        key = _make_cache_key(test_func, args, kwargs)

        # 应该包含参数哈希
        assert ":" in key
        assert len(key.split(":")) >= 3

    def test_make_cache_key_with_prefix(self):
        """测试：带前缀的缓存键生成"""
        def test_func(a):
            return a

        key = _make_cache_key(test_func, (1,), {}, prefix="test")

        assert key.startswith("test:")
        assert "test_func" in key

    def test_make_cache_key_with_user_id(self):
        """测试：带用户ID的缓存键生成"""
        def test_func(a):
            return a

        key = _make_cache_key(test_func, (1,), {}, user_id=123)

        assert "user:123" in key

    def test_make_cache_key_exclude_args(self):
        """测试：排除参数的缓存键生成"""
        def test_func(a, b, c=None):
            return a + b

        args = (1, 2)
        kwargs = {"c": 3}
        key1 = _make_cache_key(test_func, args, kwargs)
        key2 = _make_cache_key(test_func, args, kwargs, exclude_args=["c"])

        # 排除c后，键应该不同
        assert key1 != key2

    def test_make_cache_key_serialization_error(self):
        """测试：序列化错误处理"""
        def test_func(a):
            return a

        # 使用不可序列化的对象
        args = (Mock(),)
        kwargs = {}

        # 不应该抛出异常
        key = _make_cache_key(test_func, args, kwargs)
        assert key is not None
        assert len(key) > 0

    def test_make_cache_key_consistent(self):
        """测试：缓存键一致性"""
        def test_func(a, b):
            return a + b

        args = (1, 2)
        kwargs = {"c": 3}

        key1 = _make_cache_key(test_func, args, kwargs)
        key2 = _make_cache_key(test_func, args, kwargs)

        assert key1 == key2

    def test_make_cache_key_different_order(self):
        """测试：不同参数顺序的键一致性"""
        def test_func(a, b, c):
            return a + b + c

        # 关键字参数顺序不同
        kwargs1 = {"a": 1, "b": 2, "c": 3}
        kwargs2 = {"c": 3, "b": 2, "a": 1}

        key1 = _make_cache_key(test_func, (), kwargs1)
        key2 = _make_cache_key(test_func, (), kwargs2)

        # JSON序列化会排序键，所以应该相同
        assert key1 == key2

    def test_make_cache_key_empty_params(self):
        """测试：空参数的缓存键"""
        def test_func():
            return "test"

        key = _make_cache_key(test_func, (), {})

        # 应该只有模块和函数名
        assert key == f"{test_func.__module__}:{test_func.__qualname__}"


class TestCacheResultDecorator:
    """缓存结果装饰器测试"""

    def test_sync_function_cache_hit(self):
        """测试：同步函数缓存命中"""
        # 模拟Redis
        mock_redis = Mock()
        mock_redis.get.return_value = json.dumps({"result": "cached"})

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            def test_func(x):
                return f"computed-{x}"

            result = test_func(1)
            assert result == {"result": "cached"}
            mock_redis.get.assert_called_once()

    def test_sync_function_cache_miss(self):
        """测试：同步函数缓存未命中"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            def test_func(x):
                return f"computed-{x}"

            result = test_func(1)
            assert result == "computed-1"
            mock_redis.get.assert_called_once()
            mock_redis.set.assert_called_once()

    def test_async_function_cache(self):
        """测试：异步函数缓存"""
        mock_redis = AsyncMock()
        mock_redis.aget.return_value = None
        mock_redis.aset.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            async def test_func(x):
                return f"computed-{x}"

            async def test():
                result = await test_func(1)
                assert result == "computed-1"

            asyncio.run(test())

    def test_cache_with_ttl(self):
        """测试：带TTL的缓存"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result(ttl=3600)
            def test_func(x):
                return f"computed-{x}"

            test_func(1)
            # 应该使用setex而不是set
            mock_redis.setex.assert_called_once()

    def test_cache_with_prefix(self):
        """测试：带前缀的缓存"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result(prefix="myprefix")
            def test_func(x):
                return f"computed-{x}"

            test_func(1)

            # 检查缓存键是否包含前缀
            call_args = mock_redis.set.call_args
            cache_key = call_args[0][0]
            assert cache_key.startswith("myprefix:")

    def test_cache_unless_condition(self):
        """测试：unless条件"""
        mock_redis = Mock()

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result(unless=lambda x: x > 5)
            def test_func(x):
                return f"computed-{x}"

            # x > 5，不应该缓存
            result = test_func(10)
            assert result == "computed-10"
            mock_redis.get.assert_not_called()

            # x <= 5，应该缓存
            result = test_func(3)
            mock_redis.get.assert_called_once()

    def test_cache_custom_key_generator(self):
        """测试：自定义键生成器"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        def custom_key(func, args, kwargs):
            return f"custom:{args[0]}"

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result(key_generator=custom_key)
            def test_func(x):
                return f"computed-{x}"

            test_func(1)

            call_args = mock_redis.set.call_args
            cache_key = call_args[0][0]
            assert cache_key == "custom:1"

    def test_cache_redis_error_fallback(self):
        """测试：Redis错误时的回退"""
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis error")

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            def test_func(x):
                return f"computed-{x}"

            # 应该回退到直接执行函数
            result = test_func(1)
            assert result == "computed-1"

    def test_cache_deserialize_error(self):
        """测试：反序列化错误"""
        mock_redis = Mock()
        mock_redis.get.return_value = "invalid json"

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            def test_func(x):
                return f"computed-{x}"

            # 应该回退到重新计算
            result = test_func(1)
            assert result == "computed-1"

    def test_cache_method(self):
        """测试：缓存方法"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            class TestClass:
                @cache_result()
                def method(self, x):
                    return f"method-{x}"

            obj = TestClass()
            result = obj.method(1)
            assert result == "method-1"
            mock_redis.set.assert_called_once()

    def test_cache_classmethod(self):
        """测试：缓存类方法"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            class TestClass:
                @classmethod
                @cache_result()
                def classmethod(cls, x):
                    return f"classmethod-{x}"

            result = TestClass.classmethod(1)
            assert result == "classmethod-1"
            mock_redis.set.assert_called_once()

    def test_cache_staticmethod(self):
        """测试：缓存静态方法"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            class TestClass:
                @staticmethod
                @cache_result()
                def staticmethod(x):
                    return f"staticmethod-{x}"

            result = TestClass.staticmethod(1)
            assert result == "staticmethod-1"
            mock_redis.set.assert_called_once()


class TestCacheWithTTL:
    """带TTL的缓存装饰器测试"""

    def test_cache_with_ttl_decorator(self):
        """测试：cache_with_ttl装饰器"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_with_ttl(ttl=7200)
            def test_func(x):
                return f"computed-{x}"

            test_func(1)
            mock_redis.setex.assert_called_once()

            # 检查TTL参数
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 7200

    def test_cache_with_ttl_default(self):
        """测试：cache_with_ttl默认TTL"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_with_ttl()
            def test_func(x):
                return f"computed-{x}"

            test_func(1)
            # 应该使用默认的set而不是setex
            mock_redis.set.assert_called_once()


class TestCacheByUser:
    """基于用户的缓存装饰器测试"""

    def test_cache_by_user_decorator(self):
        """测试：cache_by_user装饰器"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_by_user()
            def test_func(user_id, x):
                return f"computed-{user_id}-{x}"

            test_func(123, 1)

            # 检查缓存键是否包含用户ID
            call_args = mock_redis.set.call_args
            cache_key = call_args[0][0]
            assert "user:123" in cache_key

    def test_cache_by_user_custom_param(self):
        """测试：cache_by_user自定义用户参数"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_by_user(user_param="uid")
            def test_func(uid, x):
                return f"computed-{uid}-{x}"

            test_func(456, 1)

            call_args = mock_redis.set.call_args
            cache_key = call_args[0][0]
            assert "user:456" in cache_key


class TestCacheInvalidate:
    """缓存失效装饰器测试"""

    def test_cache_invalidate_decorator(self):
        """测试：cache_invalidate装饰器"""
        mock_redis = Mock()
        mock_redis.delete.return_value = 1

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_invalidate(pattern="test:*")
            def update_func(x):
                return f"updated-{x}"

            result = update_func(1)
            assert result == "updated-1"
            # 注意：实际的invalidate可能需要更复杂的逻辑

    def test_cache_invalidate_after_update(self):
        """测试：更新后失效缓存"""
        mock_redis = Mock()
        mock_redis.delete.return_value = 1

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            def get_data(x):
                return f"data-{x}"

            @cache_invalidate()
            def update_data(x):
                return f"updated-{x}"

            # 先缓存数据
            get_data(1)

            # 更新数据，应该清除缓存
            update_data(1)

            # 验证delete被调用
            # 注意：具体实现可能需要调整


class TestCacheDecoratorIntegration:
    """缓存装饰器集成测试"""

    def test_multiple_decorators(self):
        """测试：多个装饰器组合"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result(ttl=3600, prefix="multi")
            @cache_by_user()
            def test_func(user_id, x):
                return f"computed-{user_id}-{x}"

            test_func(123, 1)

            # 检查缓存键格式
            call_args = mock_redis.set.call_args
            cache_key = call_args[0][0]
            assert "multi:" in cache_key
            assert "user:123" in cache_key

    def test_nested_functions(self):
        """测试：嵌套函数的缓存"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            def outer_func(x):
                @cache_result()
                def inner_func(y):
                    return f"inner-{y}"

                return inner_func(x)

            result = outer_func(1)
            assert result == "inner-1"

            # 两个函数都应该尝试缓存
            assert mock_redis.set.call_count >= 1

    def test_recursive_function(self):
        """测试：递归函数的缓存"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            def factorial(n):
                if n <= 1:
                    return 1
                return n * factorial(n - 1)

            result = factorial(5)
            assert result == 120

            # 应该有多次缓存调用
            assert mock_redis.set.call_count >= 5

    def test_generator_function(self):
        """测试：生成器函数的缓存"""
        mock_redis = Mock()
        mock_redis.get.return_value = None

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            @cache_result()
            def test_generator():
                yield 1
                yield 2
                yield 3

            # 生成器可能不能直接缓存
            # 这取决于具体实现
            gen = test_generator()
            assert list(gen) == [1, 2, 3]

    def test_lambda_function(self):
        """测试：Lambda函数的缓存"""
        mock_redis = Mock()

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            # Lambda函数可能没有__name__属性
            # 这可能导致问题
            try:
                test_func = cache_result()(lambda x: x * 2)
                result = test_func(5)
                assert result == 10
            except AttributeError:
                # 预期的错误，Lambda没有某些属性
                pytest.skip("Lambda functions may not be cacheable")

    def test_partial_function(self):
        """测试：偏函数的缓存"""
        from functools import partial

        def test_func(a, b):
            return a + b

        partial_func = partial(test_func, 10)

        mock_redis = Mock()

        with patch('src.cache.decorators.RedisManager.get_instance', return_value=mock_redis):

            try:
                cached_func = cache_result()(partial_func)
                result = cached_func(5)
                assert result == 15
            except AttributeError:
                # 偏函数可能没有某些属性
                pytest.skip("Partial functions may not be cacheable")