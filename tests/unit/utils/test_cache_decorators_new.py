"""
缓存装饰器测试
Tests for Cache Decorators

测试缓存装饰器的各种功能，包括：
- 内存缓存装饰器
- Redis缓存装饰器
- 批量缓存装饰器
- 缓存失效装饰器
- 条件缓存装饰器
"""

import time
from typing import Any
import pytest

from src.utils.cache_decorators import (
    memory_cache,
    redis_cache,
    batch_cache,
    cache_invalidate,
    conditional_cache,
    clear_cache,
    get_cache_info,
    _generate_cache_key,
    _cleanup_expired_cache,
)


class TestMemoryCache:
    """测试内存缓存装饰器"""

    def setup_method(self):
        """每个测试前清空缓存"""
        clear_cache()

    def test_basic_caching(self):
        """测试基本的缓存功能"""
        call_count = 0

        @memory_cache(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # 第二次调用，应该从缓存获取
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # 没有增加

    def test_cache_with_different_args(self):
        """测试不同参数的缓存"""
        call_count = 0

        @memory_cache(ttl=60)
        def add(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # 不同参数会生成不同的缓存
        assert add(1, 2) == 3
        assert call_count == 1

        assert add(1, 3) == 4
        assert call_count == 2

        # 相同参数会使用缓存
        assert add(1, 2) == 3
        assert call_count == 2

    def test_cache_with_kwargs(self):
        """测试关键字参数的缓存"""
        call_count = 0

        @memory_cache(ttl=60)
        def greet(name, greeting="Hello"):
            nonlocal call_count
            call_count += 1
            return f"{greeting}, {name}!"

        # 相同的参数，不管位置还是关键字
        assert greet("Alice", greeting="Hi") == "Hi, Alice!"
        assert call_count == 1

        # 相同参数使用缓存
        assert greet("Alice", greeting="Hi") == "Hi, Alice!"
        assert call_count == 1  # 使用缓存

        # 不同参数会重新执行
        assert greet(name="Alice", greeting="Hello") == "Hello, Alice!"
        assert call_count == 2

    def test_cache_expiration(self):
        """测试缓存过期"""
        call_count = 0

        @memory_cache(ttl=1)  # 1秒过期
        def timed_function():
            nonlocal call_count
            call_count += 1
            return call_count

        # 第一次调用
        result1 = timed_function()
        assert result1 == 1
        assert call_count == 1

        # 立即再次调用，使用缓存
        result2 = timed_function()
        assert result2 == 1
        assert call_count == 1

        # 等待过期
        time.sleep(1.1)

        # 缓存已过期，重新执行
        result3 = timed_function()
        assert result3 == 2
        assert call_count == 2

    def test_max_size_limit(self):
        """测试最大缓存大小限制"""
        call_count = 0

        @memory_cache(ttl=3600, max_size=2)
        def limited_cache(x):
            nonlocal call_count
            call_count += 1
            return x

        # 填满缓存
        assert limited_cache(1) == 1
        assert call_count == 1

        assert limited_cache(2) == 2
        assert call_count == 2

        # 第三个会淘汰最旧的
        assert limited_cache(3) == 3
        assert call_count == 3

        # 再次调用第一个，应该已经被淘汰
        assert limited_cache(1) == 1
        assert call_count == 4  # 重新执行

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        # 测试相同参数生成相同的键
        key1 = _generate_cache_key("func", (1, 2), {"a": 3})
        key2 = _generate_cache_key("func", (1, 2), {"a": 3})
        assert key1 == key2

        # 测试不同参数生成不同的键
        key3 = _generate_cache_key("func", (1, 3), {"a": 3})
        assert key1 != key3

        # 测试函数名影响键
        key4 = _generate_cache_key("other_func", (1, 2), {"a": 3})
        assert key1 != key4

    def test_cleanup_expired_cache(self):
        """测试清理过期缓存"""
        # 手动添加一些过期的缓存
        from src.utils.cache_decorators import _memory_cache
        current_time = time.time()

        # 添加一个过期的条目
        _memory_cache["expired_key"] = ("value", current_time - 100)
        # 添加一个未过期的条目
        _memory_cache["valid_key"] = ("value", current_time + 100)

        _cleanup_expired_cache(ttl=50)

        # 过期的应该被删除
        assert "expired_key" not in _memory_cache
        # 未过期的应该保留
        assert "valid_key" in _memory_cache

    def test_get_cache_info(self):
        """测试获取缓存信息"""
        @memory_cache(ttl=60)
        def test_func(x):
            return x

        # 执行几次生成缓存
        test_func(1)
        test_func(2)

        info = get_cache_info()
        assert info["size"] == 2
        assert len(info["keys"]) == 2

    def test_clear_cache(self):
        """测试清空缓存"""
        @memory_cache(ttl=60)
        def test_func(x):
            return x

        # 生成缓存
        test_func(1)
        assert get_cache_info()["size"] == 1

        # 清空缓存
        clear_cache()
        assert get_cache_info()["size"] == 0


class TestRedisCache:
    """测试Redis缓存装饰器（模拟实现）"""

    def setup_method(self):
        """每个测试前清空缓存"""
        clear_cache()

    def test_redis_cache_uses_memory(self):
        """测试Redis缓存装饰器实际上使用内存缓存"""
        call_count = 0

        @redis_cache(key_prefix="test", ttl=60)
        def redis_function(x):
            nonlocal call_count
            call_count += 1
            return x * 3

        # 验证它实际使用了内存缓存
        assert redis_function(5) == 15
        assert call_count == 1

        # 第二次调用应该从缓存获取
        assert redis_function(5) == 15
        assert call_count == 1

    def test_redis_cache_with_prefix(self):
        """测试Redis缓存带前缀"""
        call_count = 0

        @redis_cache(key_prefix="api", ttl=60)
        def api_call(endpoint):
            nonlocal call_count
            call_count += 1
            return f"data from {endpoint}"

        assert api_call("/users") == "data from /users"
        assert call_count == 1

        # 相同调用使用缓存
        assert api_call("/users") == "data from /users"
        assert call_count == 1


class TestBatchCache:
    """测试批量缓存装饰器"""

    def setup_method(self):
        """每个测试前清空缓存"""
        clear_cache()

    def test_batch_cache(self):
        """测试批量缓存"""
        call_count = 0

        @batch_cache(ttl=60)
        def batch_operation(items):
            nonlocal call_count
            call_count += 1
            return [item * 2 for item in items]

        items = [1, 2, 3]

        # 第一次调用
        result1 = batch_operation(items)
        assert result1 == [2, 4, 6]
        assert call_count == 1

        # 第二次调用，使用缓存
        result2 = batch_operation(items)
        assert result2 == [2, 4, 6]
        assert call_count == 1


class TestCacheInvalidate:
    """测试缓存失效装饰器"""

    def setup_method(self):
        """每个测试前清空缓存"""
        clear_cache()

    def test_cache_invalidate_pattern(self):
        """测试按模式清除缓存"""
        call_count = 0

        @memory_cache(ttl=60)
        def get_user(user_id):
            nonlocal call_count
            call_count += 1
            return f"user_{user_id}"

        @cache_invalidate(pattern="user")
        def update_user(user_id):
            return f"updated_{user_id}"

        # 生成一些缓存
        get_user(1)
        get_user(2)
        assert get_cache_info()["size"] == 2

        # 更新用户会清除相关缓存
        update_user(1)
        # 缓存应该被清除
        assert get_cache_info()["size"] == 0

    def test_cache_invalidate_no_pattern(self):
        """测试无模式的缓存失效"""
        @memory_cache(ttl=60)
        def test_func(x):
            return x

        @cache_invalidate()  # 无模式
        def no_invalidate_func():
            pass

        # 生成缓存
        test_func(1)
        assert get_cache_info()["size"] == 1

        # 调用不会清除任何缓存
        no_invalidate_func()
        assert get_cache_info()["size"] == 1


class TestConditionalCache:
    """测试条件缓存装饰器"""

    def setup_method(self):
        """每个测试前清空缓存"""
        clear_cache()

    def test_conditional_cache_true(self):
        """测试条件为真时的缓存"""
        call_count = 0

        @conditional_cache(condition=lambda x: x > 5, ttl=60)
        def conditional_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 条件为真，会缓存（但不检查已有缓存）
        result1 = conditional_func(10)
        assert result1 == 20
        assert call_count == 1

        # conditional_cache不会检查缓存，每次都会执行
        result2 = conditional_func(10)
        assert result2 == 20
        assert call_count == 2  # 每次都执行

    def test_conditional_cache_false(self):
        """测试条件为假时不缓存"""
        call_count = 0

        @conditional_cache(condition=lambda x: x > 5, ttl=60)
        def conditional_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 条件为假，不应该缓存
        assert conditional_func(3) == 6
        assert call_count == 1

        # 第二次调用重新执行
        assert conditional_func(3) == 6
        assert call_count == 2

    def test_conditional_cache_complex_condition(self):
        """测试复杂条件"""
        def is_success_response(response):
            return response.get("status") == "success"

        call_count = 0

        @conditional_cache(condition=is_success_response, ttl=60)
        def api_request(success=True):
            nonlocal call_count
            call_count += 1
            # 根据参数决定成功或失败
            if success:
                return {"status": "success", "data": "value"}
            else:
                return {"status": "error", "message": "failed"}

        # 第一次成功，会缓存
        result1 = api_request(success=True)
        assert result1["status"] == "success"
        assert call_count == 1

        # conditional_cache不会检查缓存，但成功的响应会被缓存
        result2 = api_request(success=True)
        assert result2["status"] == "success"
        assert call_count == 2

        # 失败的调用不会缓存
        result3 = api_request(success=False)
        assert result3["status"] == "error"
        assert call_count == 3

        # 验证成功的调用确实被缓存了
        from src.utils.cache_decorators import _memory_cache
        # 应该有一个缓存条目
        assert len(_memory_cache) > 0


class TestCacheIntegration:
    """缓存装饰器集成测试"""

    def setup_method(self):
        """每个测试前清空缓存"""
        clear_cache()

    def test_nested_decorators(self):
        """测试嵌套装饰器"""
        call_count = 0

        @memory_cache(ttl=60)
        @redis_cache(key_prefix="nested", ttl=30)
        def nested_function(x):
            nonlocal call_count
            call_count += 1
            return x

        # 测试嵌套装饰器工作
        assert nested_function(1) == 1
        assert call_count == 1

        assert nested_function(1) == 1
        assert call_count == 1

    def test_cache_with_unhashable_args(self):
        """测试不可哈希参数"""
        call_count = 0

        @memory_cache(ttl=60)
        def process_list(items):
            nonlocal call_count
            call_count += 1
            return sum(items)

        # 列表是不可哈希的，但装饰器应该能处理
        assert process_list([1, 2, 3]) == 6
        assert call_count == 1

        # 相同列表使用缓存
        assert process_list([1, 2, 3]) == 6
        assert call_count == 1

    def test_cache_with_none_values(self):
        """测试缓存None值"""
        call_count = 0

        @memory_cache(ttl=60)
        def returns_none():
            nonlocal call_count
            call_count += 1
            return None

        # 第一次返回None
        assert returns_none() is None
        assert call_count == 1

        # 第二次从缓存获取None
        assert returns_none() is None
        assert call_count == 1

    def test_cache_exception_handling(self):
        """测试缓存异常处理"""
        call_count = 0

        @memory_cache(ttl=60)
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "success"
            else:
                raise ValueError("Something went wrong")

        # 第一次成功并缓存
        assert sometimes_fails() == "success"
        assert call_count == 1

        # 第二次从缓存获取成功值（即使函数会失败）
        assert sometimes_fails() == "success"
        assert call_count == 1

    def test_memory_efficiency(self):
        """测试内存效率"""
        # 创建一个会生成大量数据的函数
        @memory_cache(ttl=60, max_size=10)
        def generate_data(i):
            return list(range(1000))  # 每次生成1000个元素的列表

        # 生成多个缓存
        for i in range(15):
            data = generate_data(i)
            assert len(data) == 1000

        # 验证缓存大小受限制
        info = get_cache_info()
        assert info["size"] <= 10
