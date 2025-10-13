"""
缓存装饰器测试
Tests for cache decorators

测试各种缓存装饰器的功能。
"""

import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.cache.decorators import (
    cache_result,
    cache_with_ttl,
    cache_by_user,
    cache_invalidate,
    cache_user_predictions,
    cache_match_data,
    cache_team_stats,
    _make_cache_key,
    CacheDecorator,
    UserCacheDecorator,
    InvalidateCacheDecorator,
)


# 模拟Redis管理器
class MockRedis:
    """模拟Redis客户端"""

    def __init__(self):
        self._data = {}
        self.expirations = {}

    def get(self, key):
        if key in self.expirations and time.time() > self.expirations[key]:
            self.data.pop(key, None)
            self.expirations.pop(key, None)
            return None
        return self.data.get(key)

    async def aget(self, key):
        return self.get(key)

    def set(self, key, value):
        self.data[key] = value

    async def aset(self, key, value):
        self.set(key, value)

    def setex(self, key, seconds, value):
        self.data[key] = value
        self.expirations[key] = time.time() + seconds

    async def asetex(self, key, seconds, value):
        self.setex(key, seconds, value)

    def delete(self, *keys):
        count = 0
        for key in keys:
            if self.data.pop(key, None) is not None:
                count += 1
            self.expirations.pop(key, None)
        return count

    async def adelete(self, *keys):
        return self.delete(*keys)

    def keys(self, pattern):
        if "*" in pattern:
            # 简单的通配符匹配
            import fnmatch

            return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]
        else:
            return [k for k in self.data.keys() if k == pattern]

    async def akeys(self, pattern):
        return self.keys(pattern)


@pytest.fixture
def mock_redis():
    """模拟Redis实例"""
    return MockRedis()


@pytest.fixture(autouse=True)
def patch_redis_manager(mock_redis):
    """自动补丁Redis管理器"""
    with patch(
        "src.cache.decorators.RedisManager.get_instance", return_value=mock_redis
    ):
        yield


class TestCacheKeyGeneration:
    """测试缓存键生成"""

    def test_make_cache_key_basic(self):
        """测试基础键生成"""

        def func(x, y):
            return x + y

        key = _make_cache_key(func, (1, 2), {})
        assert "test_decorators:" in key
        assert "func" in key
        assert ":" in key

    def test_make_cache_key_with_prefix(self):
        """测试带前缀的键生成"""

        def func(x):
            return x

        key = _make_cache_key(func, (1,), {}, prefix="test")
        assert key.startswith("test:")

    def test_make_cache_key_with_user(self):
        """测试带用户ID的键生成"""

        def func(x):
            return x

        key = _make_cache_key(func, (1,), {}, user_id=100)
        assert ":user:100" in key

    def test_make_cache_key_exclude_args(self):
        """测试排除参数的键生成"""

        def func(a, b, c):
            return a + b + c

        key1 = _make_cache_key(func, (1, 2, 3), {}, exclude_args=["c"])
        key2 = _make_cache_key(func, (1, 2, 4), {}, exclude_args=["c"])
        assert key1 == key2  # 排除c后，键应该相同


class TestCacheResult:
    """测试@cache_result装饰器"""

    def test_sync_function_cache(self, mock_redis):
        """测试同步函数缓存"""
        call_count = 0

        @cache_result(ttl=60)
        def compute(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # 第一次调用
        result1 = compute(1, 2)
        assert result1 == 3
        assert call_count == 1

        # 第二次调用（应该从缓存获取）
        _result2 = compute(1, 2)
        assert _result2 == 3
        assert call_count == 1  # 没有再次调用

        # 不同参数
        result3 = compute(2, 3)
        assert result3 == 5
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_function_cache(self, mock_redis):
        """测试异步函数缓存"""
        call_count = 0

        @cache_result(ttl=60)
        async def async_compute(x, y):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * y

        # 第一次调用
        result1 = await async_compute(3, 4)
        assert result1 == 12
        assert call_count == 1

        # 第二次调用（应该从缓存获取）
        _result2 = await async_compute(3, 4)
        assert _result2 == 12
        assert call_count == 1

    def test_cache_with_prefix(self, mock_redis):
        """测试带前缀的缓存"""
        call_count = 0

        @cache_result(ttl=60, prefix="test_prefix")
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(5)
        # 检查缓存键是否有正确前缀
        keys = mock_redis.keys("test_prefix:*")
        assert len(keys) == 1
        assert keys[0].startswith("test_prefix:")

    def test_cache_unless_condition(self, mock_redis):
        """测试unless条件"""
        call_count = 0

        @cache_result(unless=lambda x: x < 0)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # x >= 0 会被缓存
        compute(5)
        compute(5)
        assert call_count == 1

        # x < 0 不会被缓存
        compute(-1)
        compute(-1)
        assert call_count == 3

    def test_cache_with_ttl(self, mock_redis):
        """测试TTL过期"""
        call_count = 0

        @cache_with_ttl(ttl_seconds=1)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x + 1

        # 第一次调用
        compute(10)
        assert call_count == 1

        # 立即第二次调用（从缓存）
        compute(10)
        assert call_count == 1

        # 等待过期
        time.sleep(1.1)
        compute(10)
        assert call_count == 2


class TestCacheByUser:
    """测试@cache_by_user装饰器"""

    def test_user_based_cache(self, mock_redis):
        """测试基于用户的缓存"""
        call_count = 0

        @cache_by_user(ttl=60, user_param="user_id")
        def get_user_data(user_id, data_type):
            nonlocal call_count
            call_count += 1
            return f"data_{user_id}_{data_type}"

        # 用户1
        data1 = get_user_data(user_id=1, data_type="profile")
        assert data1 == "data_1_profile"
        assert call_count == 1

        # 相同用户和参数（从缓存）
        data2 = get_user_data(user_id=1, data_type="profile")
        assert data2 == "data_1_profile"
        assert call_count == 1

        # 不同用户
        data3 = get_user_data(user_id=2, data_type="profile")
        assert data3 == "data_2_profile"
        assert call_count == 2

        # 相同用户不同参数
        data4 = get_user_data(user_id=1, data_type="settings")
        assert data4 == "data_1_settings"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_user_based_cache(self, mock_redis):
        """测试异步用户缓存"""
        call_count = 0

        @cache_by_user(ttl=60, user_param="uid")
        async def get_user_prefs(uid):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {"user": uid, "theme": "dark"}

        # 第一次调用
        prefs1 = await get_user_prefs(uid=100)
        assert prefs1["user"] == 100
        assert call_count == 1

        # 第二次调用（从缓存）
        prefs2 = await get_user_prefs(uid=100)
        assert prefs2["user"] == 100
        assert call_count == 1


class TestCacheInvalidate:
    """测试@cache_invalidate装饰器"""

    def test_invalidate_by_pattern(self, mock_redis):
        """测试模式失效"""
        # 设置一些缓存
        mock_redis.set("user:1:data", "value1")
        mock_redis.set("user:2:data", "value2")
        mock_redis.set("other:key", "value3")

        @cache_invalidate(pattern="user:*")
        def update_user(user_id):
            return f"updated {user_id}"

        # 执行更新
        _result = update_user(1)
        assert _result == "updated 1"

        # 检查缓存
        assert mock_redis.get("user:1:data") is None
        assert mock_redis.get("user:2:data") is None
        assert mock_redis.get("other:key") == "value3"

    def test_invalidate_specific_keys(self, mock_redis):
        """测试指定键失效"""
        # 设置缓存
        mock_redis.set("key1", "value1")
        mock_redis.set("key2", "value2")
        mock_redis.set("key3", "value3")

        @cache_invalidate(keys=["key1", "key3"])
        def some_operation():
            return "done"

        some_operation()

        # 检查缓存
        assert mock_redis.get("key1") is None
        assert mock_redis.get("key2") == "value2"
        assert mock_redis.get("key3") is None

    def test_invalidate_with_key_generator(self, mock_redis):
        """测试键生成器失效"""
        call_count = 0

        def generate_keys(func, args, kwargs, result):
            user_id = args[0] if args else kwargs.get("user_id")
            return [f"user:{user_id}:profile", f"user:{user_id}:settings"]

        @cache_invalidate(key_generator=generate_keys)
        def update_user_profile(user_id, **updates):
            nonlocal call_count
            call_count += 1
            return {"user_id": user_id, "updated": True}

        # 设置缓存
        mock_redis.set("user:100:profile", "profile_data")
        mock_redis.set("user:100:settings", "settings_data")
        mock_redis.set("user:200:profile", "other_profile")

        # 执行更新
        _result = update_user_profile(100, name="New Name")
        assert result["updated"] is True
        assert call_count == 1

        # 检查缓存
        assert mock_redis.get("user:100:profile") is None
        assert mock_redis.get("user:100:settings") is None
        assert mock_redis.get("user:200:profile") == "other_profile"


class TestConvenienceDecorators:
    """测试便捷装饰器"""

    def test_cache_user_predictions(self, mock_redis):
        """测试用户预测缓存装饰器"""
        call_count = 0

        @cache_user_predictions(ttl_seconds=300)
        def get_predictions(user_id, match_id=None):
            nonlocal call_count
            call_count += 1
            return [{"match_id": match_id, "prediction": "2-1"}] if match_id else []

        # 调用并检查缓存键前缀
        get_predictions(100, 200)
        keys = mock_redis.keys("predictions:*")
        assert len(keys) == 1
        assert ":user:100:" in keys[0]

    def test_cache_match_data(self, mock_redis):
        """测试比赛数据缓存装饰器"""
        call_count = 0

        @cache_match_data(ttl_seconds=600)
        def get_match(match_id):
            nonlocal call_count
            call_count += 1
            return {"id": match_id, "status": "upcoming"}

        get_match(500)
        keys = mock_redis.keys("matches:*")
        assert len(keys) == 1

    def test_cache_team_stats(self, mock_redis):
        """测试球队统计缓存装饰器"""
        call_count = 0

        @cache_team_stats(ttl_seconds=3600)
        def get_stats(team_id, season):
            nonlocal call_count
            call_count += 1
            return {"team": team_id, "season": season, "points": 42}

        get_stats(10, "2023-2024")
        keys = mock_redis.keys("team_stats:*")
        assert len(keys) == 1


class TestDecoratorClasses:
    """测试装饰器类"""

    def test_cache_decorator_class(self, mock_redis):
        """测试CacheDecorator类"""
        call_count = 0

        decorator = CacheDecorator(ttl=60, prefix="class_test")

        @decorator
        def compute(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        compute(1, 2)
        compute(1, 2)
        assert call_count == 1

    def test_user_cache_decorator_class(self, mock_redis):
        """测试UserCacheDecorator类"""
        call_count = 0

        decorator = UserCacheDecorator(ttl=60, user_param="uid")

        @decorator
        def get_data(uid):
            nonlocal call_count
            call_count += 1
            return f"data_{uid}"

        get_data(uid=100)
        get_data(uid=100)
        assert call_count == 1

    def test_invalidate_cache_decorator_class(self, mock_redis):
        """测试InvalidateCacheDecorator类"""
        mock_redis.set("test:key1", "value1")
        mock_redis.set("test:key2", "value2")

        decorator = InvalidateCacheDecorator(pattern="test:*")

        @decorator
        def clear_data():
            return "cleared"

        clear_data()

        assert mock_redis.get("test:key1") is None
        assert mock_redis.get("test:key2") is None


class TestErrorHandling:
    """测试错误处理"""

    def test_cache_unavailable_no_fallback(self, mock_redis):
        """测试缓存不可用时不使用回退"""
        call_count = 0

        # 模拟Redis错误
        def failing_get(key):
            raise ConnectionError("Redis unavailable")

        mock_redis.get = failing_get

        @cache_result(use_cache_when_unavailable=False)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 应该抛出异常
        with pytest.raises(ConnectionError):
            compute(5)

    def test_cache_unavailable_with_fallback(self, mock_redis):
        """测试缓存不可用时使用回退"""
        call_count = 0

        # 模拟Redis错误
        def failing_get(key):
            raise ConnectionError("Redis unavailable")

        mock_redis.get = failing_get

        @cache_result(use_cache_when_unavailable=True)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 应该继续执行函数
        _result = compute(5)
        assert _result == 10
        assert call_count == 1

    def test_cache_serialization_error(self, mock_redis):
        """测试序列化错误处理"""
        call_count = 0

        # 创建不可序列化的对象
        class UnserializableObject:
            pass

        @cache_result(ttl=60)
        def get_object():
            nonlocal call_count
            call_count += 1
            return UnserializableObject()

        # 应该正常工作（存储字符串表示）
        obj1 = get_object()
        assert isinstance(obj1, UnserializableObject)
        assert call_count == 1

        # 从缓存获取
        obj2 = get_object()
        assert obj2 is not None  # 应该是字符串表示
        assert call_count == 1


class TestAsyncSupport:
    """测试异步支持"""

    @pytest.mark.asyncio
    async def test_async_cache_invalidate(self, mock_redis):
        """测试异步缓存失效"""
        # 设置缓存
        await mock_redis.aset("async:key1", "value1")
        await mock_redis.aset("async:key2", "value2")

        @cache_invalidate(pattern="async:*")
        async def async_operation():
            return "async_done"

        _result = await async_operation()
        assert _result == "async_done"

        # 检查缓存
        assert await mock_redis.aget("async:key1") is None
        assert await mock_redis.aget("async:key2") is None

    @pytest.mark.asyncio
    async def test_mixed_sync_async_decorators(self, mock_redis):
        """测试同步和异步装饰器混合使用"""
        sync_call_count = 0
        async_call_count = 0

        @cache_result(ttl=60)
        def sync_func(x):
            nonlocal sync_call_count
            sync_call_count += 1
            return x * 2

        @cache_result(ttl=60)
        async def async_func(x):
            nonlocal async_call_count
            async_call_count += 1
            await asyncio.sleep(0.01)
            return x * 3

        # 调用同步函数
        sync_result1 = sync_func(5)
        sync_result2 = sync_func(5)
        assert sync_result1 == 10
        assert sync_result2 == 10
        assert sync_call_count == 1

        # 调用异步函数
        async_result1 = await async_func(5)
        async_result2 = await async_func(5)
        assert async_result1 == 15
        assert async_result2 == 15
        assert async_call_count == 1
