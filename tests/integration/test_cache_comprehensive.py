"""
缓存层综合集成测试
Comprehensive Cache Integration Tests

测试缓存系统各组件的集成，包括：
- Redis缓存操作
- 缓存策略（LRU、TTL、Write-through）
- 缓存一致性
- 分布式缓存
- 缓存穿透和雪崩防护
- 缓存预热和更新
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import uuid

# 测试导入
try:
    import redis.asyncio as redis
    from redis.asyncio import ConnectionPool
    from redis.exceptions import RedisError, ConnectionError, TimeoutError

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from src.cache.redis_manager import RedisManager
    from src.cache.decorators import cached, cache_result, invalidate_cache
    from src.cache.strategies import LRUCache, TTLCache, WriteThroughCache
    from src.cache.consistency import CacheConsistencyManager
    from src.cache.warmup import CacheWarmer

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    RedisManager = None
    cached = None
    cache_result = None
    invalidate_cache = None
    LRUCache = TTLCache = WriteThroughCache = None
    CacheConsistencyManager = None
    CacheWarmer = None


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache modules not available")
@pytest.mark.integration
@pytest.mark.cache
class TestRedisCacheOperations:
    """Redis缓存操作测试"""

    @pytest.fixture
    async def cache_manager(self, test_redis):
        """创建缓存管理器"""
        if isinstance(test_redis, Mock):
            # 使用模拟Redis
            manager = RedisManager(
                redis_client=test_redis, key_prefix="test:", default_ttl=3600
            )
        else:
            # 使用真实Redis
            manager = RedisManager(
                redis_url="redis://localhost:6380/1",
                key_prefix="test:",
                default_ttl=3600,
            )
            await manager.connect()

        yield manager

        if not isinstance(test_redis, Mock):
            await manager.disconnect()

    async def test_basic_cache_operations(self, cache_manager):
        """测试基本缓存操作"""
        # 测试数据
        test_key = f"test_key_{uuid.uuid4().hex[:8]}"
        test_value = {
            "id": "pred_001",
            "match_id": "match_123",
            "prediction": "HOME_WIN",
            "confidence": 0.85,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. 设置缓存
        result = await cache_manager.set(test_key, test_value, ttl=60)
        assert result is True

        # 2. 获取缓存
        cached_value = await cache_manager.get(test_key)
        assert cached_value == test_value

        # 3. 检查是否存在
        exists = await cache_manager.exists(test_key)
        assert exists is True

        # 4. 更新缓存
        updated_value = test_value.copy()
        updated_value["confidence"] = 0.90
        result = await cache_manager.set(test_key, updated_value)
        assert result is True

        # 5. 验证更新
        cached_value = await cache_manager.get(test_key)
        assert cached_value["confidence"] == 0.90

        # 6. 删除缓存
        result = await cache_manager.delete(test_key)
        assert result is True

        # 7. 验证删除
        cached_value = await cache_manager.get(test_key)
        assert cached_value is None

    async def test_cache_ttl_behavior(self, cache_manager):
        """测试TTL行为"""
        test_key = f"ttl_test_{uuid.uuid4().hex[:8]}"
        test_value = {"message": "This will expire"}

        # 设置短TTL
        await cache_manager.set(test_key, test_value, ttl=2)

        # 立即获取应该存在
        value = await cache_manager.get(test_key)
        assert value == test_value

        # 获取TTL
        ttl = await cache_manager.ttl(test_key)
        assert 0 < ttl <= 2

        # 等待过期
        await asyncio.sleep(2.5)

        # 过期后应该为None
        value = await cache_manager.get(test_key)
        assert value is None

        # TTL应该为-1（不存在）
        ttl = await cache_manager.ttl(test_key)
        assert ttl == -1

    async def test_batch_operations(self, cache_manager):
        """测试批量操作"""
        # 准备测试数据
        test_data = {
            f"batch_key_{i}": {
                "id": i,
                "value": f"test_value_{i}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for i in range(10)
        }

        # 批量设置
        results = await cache_manager.mset(test_data)
        assert all(results)  # 所有设置都应该成功

        # 批量获取
        keys = list(test_data.keys())
        values = await cache_manager.mget(keys)

        # 验证结果
        for i, value in enumerate(values):
            assert value == test_data[keys[i]]

        # 批量删除
        deleted_count = await cache_manager.mdelete(keys)
        assert deleted_count == len(keys)

        # 验证删除
        values = await cache_manager.mget(keys)
        assert all(v is None for v in values)

    async def test_cache_patterns(self, cache_manager):
        """测试缓存模式匹配"""
        # 创建多个键
        keys_pattern1 = [f"user:profile:{i}" for i in range(5)]
        keys_pattern2 = [f"match:prediction:{i}" for i in range(5)]

        # 设置值
        for key in keys_pattern1 + keys_pattern2:
            await cache_manager.set(key, {"key": key})

        # 获取所有匹配的键
        user_keys = await cache_manager.keys("user:profile:*")
        match_keys = await cache_manager.keys("match:prediction:*")

        assert len(user_keys) == 5
        assert len(match_keys) == 5
        assert all(k.startswith("user:profile:") for k in user_keys)
        assert all(k.startswith("match:prediction:") for k in match_keys)

        # 删除特定模式
        deleted_count = await cache_manager.delete_pattern("user:profile:*")
        assert deleted_count == 5

        # 验证删除
        user_keys = await cache_manager.keys("user:profile:*")
        assert len(user_keys) == 0
        match_keys = await cache_manager.keys("match:prediction:*")
        assert len(match_keys) == 5


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache modules not available")
@pytest.mark.integration
@pytest.mark.cache
class TestCacheStrategies:
    """缓存策略测试"""

    async def test_lru_cache_strategy(self):
        """测试LRU缓存策略"""
        cache = LRUCache(maxsize=3)

        # 添加项目
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.get("key1") == "value1"

        # 添加第4项，应该淘汰最旧的
        cache.set("key4", "value4")
        assert cache.get("key1") is None  # key1应该被淘汰
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

        # 访问key2使其成为最近使用
        cache.get("key2")

        # 添加第5项，应该淘汰key3
        cache.set("key5", "value5")
        assert cache.get("key2") == "value2"  # 仍然存在
        assert cache.get("key3") is None  # 被淘汰

    async def test_ttl_cache_strategy(self):
        """测试TTL缓存策略"""
        cache = TTLCache(ttl=1, maxsize=5)

        # 添加项目
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 立即获取应该存在
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # 等待过期
        await asyncio.sleep(1.1)

        # 过期后应该为None
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    async def test_write_through_cache(self, cache_manager):
        """测试Write-through缓存策略"""

        # 模拟数据库
        class MockDatabase:
            def __init__(self):
                self.data = {}

            async def get(self, key):
                return self.data.get(key)

            async def set(self, key, value):
                self.data[key] = value
                return True

        db = MockDatabase()
        cache = WriteThroughCache(cache_manager, db)

        # 第一次写入（缓存和数据库）
        test_key = "write_through_test"
        test_value = {"data": "test"}

        await cache.set(test_key, test_value)

        # 验证数据库中有数据
        db_value = await db.get(test_key)
        assert db_value == test_value

        # 验证缓存中有数据
        cache_value = await cache_manager.get(test_key)
        assert cache_value == test_value

        # 读取（应该从缓存获取）
        value = await cache.get(test_key)
        assert value == test_value

    async def test_cache_aside_pattern(self, cache_manager):
        """测试Cache-Aside模式"""

        # 模拟慢速数据源
        class SlowDataSource:
            def __init__(self):
                self.call_count = 0

            async def get_data(self, key):
                self.call_count += 1
                await asyncio.sleep(0.1)  # 模拟慢速操作
                return {"data": f"value_for_{key}", "source": "database"}

        data_source = SlowDataSource()

        # 第一次请求（应该访问数据源）
        key = "cache_aside_test"
        cached_data = await cache_manager.get(key)

        if cached_data is None:
            data = await data_source.get_data(key)
            await cache_manager.set(key, data, ttl=60)
            cached_data = data

        assert cached_data["source"] == "database"
        assert data_source.call_count == 1

        # 第二次请求（应该从缓存获取）
        cached_data = await cache_manager.get(key)

        if cached_data is None:
            data = await data_source.get_data(key)
            await cache_manager.set(key, data, ttl=60)
            cached_data = data

        assert cached_data["source"] == "database"
        assert data_source.call_count == 1  # 没有增加


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache modules not available")
@pytest.mark.integration
@pytest.mark.cache
class TestCacheConsistency:
    """缓存一致性测试"""

    async def test_cache_invalidation(self, cache_manager):
        """测试缓存失效"""
        test_key = f"invalidation_test_{uuid.uuid4().hex[:8]}"

        # 设置缓存
        await cache_manager.set(test_key, {"version": 1})
        value = await cache_manager.get(test_key)
        assert value["version"] == 1

        # 更新数据库（模拟）

        # 使缓存失效
        await cache_manager.delete(test_key)

        # 再次获取应该为None
        value = await cache_manager.get(test_key)
        assert value is None

    async def test_cache_versioning(self, cache_manager):
        """测试缓存版本控制"""
        test_key = f"version_test_{uuid.uuid4().hex[:8]}"

        # 设置带版本的数据
        version = 1
        data = {"id": "test", "value": "original", "_version": version}
        await cache_manager.set(test_key, data)

        # 获取并验证版本
        cached = await cache_manager.get(test_key)
        assert cached["_version"] == version

        # 更新数据并增加版本
        version += 1
        updated_data = data.copy()
        updated_data["value"] = "updated"
        updated_data["_version"] = version

        # 使用原子操作更新
        await cache_manager.set(test_key, updated_data)

        # 验证新版本
        cached = await cache_manager.get(test_key)
        assert cached["value"] == "updated"
        assert cached["_version"] == version

    async def test_distributed_cache_lock(self, cache_manager):
        """测试分布式缓存锁"""
        lock_key = f"lock_test_{uuid.uuid4().hex[:8]}"
        lock_value = str(uuid.uuid4())

        # 获取锁
        acquired = await cache_manager.set(
            lock_key,
            lock_value,
            ttl=10,
            nx=True,  # 只在不存在时设置
        )
        assert acquired is True

        # 尝试再次获取（应该失败）
        acquired_again = await cache_manager.set(
            lock_key, "another_value", ttl=10, nx=True
        )
        assert acquired_again is False

        # 验证锁的值
        current_value = await cache_manager.get(lock_key)
        assert current_value == lock_value

        # 释放锁（使用Lua脚本确保原子性）
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = await cache_manager.eval(lua_script, 1, lock_key, lock_value)
        assert result == 1

        # 验证锁已释放
        current_value = await cache_manager.get(lock_key)
        assert current_value is None

    async def test_cache_warmup(self, cache_manager):
        """测试缓存预热"""
        # 准备预热数据
        warmup_data = {
            f"warmup_key_{i}": {
                "id": i,
                "precomputed": True,
                "data": f"precomputed_value_{i}",
            }
            for i in range(10)
        }

        # 创建缓存预热器
        warmer = CacheWarmer(cache_manager)

        # 执行预热
        results = await warmer.warmup(warmup_data)
        assert results["success"] == 10
        assert results["failed"] == 0

        # 验证预热数据
        for key, expected_value in warmup_data.items():
            cached_value = await cache_manager.get(key)
            assert cached_value == expected_value

    async def test_cache_penetration_protection(self, cache_manager):
        """测试缓存穿透保护"""

        # 模拟缓存穿透防护
        class PenetrationProtectedCache:
            def __init__(self, cache_manager):
                self.cache = cache_manager
                self.null_cache = set()  # 记录空值

            async def get(self, key):
                # 检查是否在空值缓存中
                if key in self.null_cache:
                    return None

                # 尝试从缓存获取
                value = await self.cache.get(key)

                if value is None:
                    # 添加到空值缓存（短期）
                    self.null_cache.add(key)
                    # 可以设置一个定时器来清理
                else:
                    # 如果值不为None，从空值缓存中移除
                    self.null_cache.discard(key)

                return value

        protected_cache = PenetrationProtectedCache(cache_manager)

        # 测试不存在的键
        non_existent_key = "non_existent_key"

        # 第一次查询（缓存穿透）
        value = await protected_cache.get(non_existent_key)
        assert value is None
        assert non_existent_key in protected_cache.null_cache

        # 第二次查询（应该被空值缓存拦截）
        value = await protected_cache.get(non_existent_key)
        assert value is None


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache modules not available")
@pytest.mark.integration
@pytest.mark.cache
@pytest.mark.performance
class TestCachePerformance:
    """缓存性能测试"""

    async def test_cache_hit_ratio(self, cache_manager):
        """测试缓存命中率"""
        # 预填充部分数据
        keys = [f"perf_key_{i}" for i in range(100)]

        # 填充50%的数据
        for i in range(0, 100, 2):
            await cache_manager.set(keys[i], {"id": i, "value": f"cached_value_{i}"})

        # 执行1000次随机访问
        import random

        hits = 0
        misses = 0

        for _ in range(1000):
            random_key = random.choice(keys)
            value = await cache_manager.get(random_key)
            if value is not None:
                hits += 1
            else:
                misses += 1

        hit_ratio = hits / (hits + misses)

        # 命中率应该接近50%
        assert 0.4 < hit_ratio < 0.6

        print(f"Cache hit ratio: {hit_ratio:.2%}")

    async def test_cache_concurrent_access(self, cache_manager):
        """测试并发访问"""
        test_key = f"concurrent_test_{uuid.uuid4().hex[:8]}"

        # 并发写入
        async def writer(id):
            for i in range(10):
                await cache_manager.set(
                    f"{test_key}_writer_{id}", {"writer_id": id, "iteration": i}
                )
                await asyncio.sleep(0.01)

        # 并发读取
        async def reader(id):
            results = []
            for i in range(10):
                value = await cache_manager.get(f"{test_key}_writer_{id % 5}")
                results.append(value)
                await asyncio.sleep(0.01)
            return results

        # 启动并发任务
        tasks = []

        # 5个写入者
        for i in range(5):
            tasks.append(asyncio.create_task(writer(i)))

        # 10个读取者
        for i in range(10):
            tasks.append(asyncio.create_task(reader(i)))

        # 等待所有任务完成
        await asyncio.gather(*tasks)

        # 验证数据完整性
        for i in range(5):
            value = await cache_manager.get(f"{test_key}_writer_{i}")
            assert value is not None
            assert value["writer_id"] == i
            assert value["iteration"] == 9  # 最后一次迭代

    async def test_cache_memory_usage(self, cache_manager):
        """测试缓存内存使用"""
        # 监控内存使用
        import psutil

        process = psutil.Process()

        initial_memory = process.memory_info().rss

        # 创建大量缓存数据
        large_data_count = 1000
        data_size = 1024  # 1KB per item

        for i in range(large_data_count):
            await cache_manager.set(
                f"memory_test_{i}",
                {
                    "id": i,
                    "data": "x" * (data_size - 100),  # 填充数据
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_per_item = memory_increase / large_data_count

        # 内存增长应该合理（每个项目不超过10KB）
        assert memory_per_item < 10 * 1024

        print(f"Memory increase: {memory_increase / 1024 / 1024:.2f} MB")
        print(f"Memory per item: {memory_per_item:.2f} bytes")

        # 清理数据
        keys = [f"memory_test_{i}" for i in range(large_data_count)]
        await cache_manager.mdelete(keys)


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
@pytest.mark.skipif(not CACHE_AVAILABLE, reason="Cache modules not available")
@pytest.mark.integration
@pytest.mark.cache
class TestCacheDecorators:
    """缓存装饰器测试"""

    async def test_cached_decorator(self, cache_manager):
        """测试@cached装饰器"""
        call_count = 0

        @cached(key_prefix="decorator_test", ttl=60, cache_manager=cache_manager)
        async def expensive_operation(x, y):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # 模拟耗时操作
            return {"result": x + y, "call_count": call_count}

        # 第一次调用
        result1 = await expensive_operation(1, 2)
        assert result1["result"] == 3
        assert result1["call_count"] == 1

        # 第二次调用（应该从缓存获取）
        result2 = await expensive_operation(1, 2)
        assert result2["result"] == 3
        assert result2["call_count"] == 1  # 没有增加

        # 不同参数的调用
        result3 = await expensive_operation(2, 3)
        assert result3["result"] == 5
        assert result3["call_count"] == 2  # 增加了

    async def test_cache_invalidation_decorator(self, cache_manager):
        """测试缓存失效装饰器"""
        call_count = 0

        @cache_result(key_prefix="invalidate_test", cache_manager=cache_manager)
        async def get_data(id):
            nonlocal call_count
            call_count += 1
            return {"id": id, "data": f"data_{id}", "version": call_count}

        @invalidate_cache(pattern="invalidate_test:*", cache_manager=cache_manager)
        async def update_data(id, new_data):
            # 更新数据后使缓存失效
            return {"id": id, "updated": True, "new_data": new_data}

        # 获取数据
        data1 = await get_data("test_id")
        assert data1["version"] == 1

        # 再次获取（从缓存）
        data2 = await get_data("test_id")
        assert data2["version"] == 1

        # 更新数据（会失效缓存）
        await update_data("test_id", "new_value")

        # 再次获取（重新计算）
        data3 = await get_data("test_id")
        assert data3["version"] == 2

    async def test_conditional_caching(self, cache_manager):
        """测试条件缓存"""
        call_count = 0

        @cached(
            key_prefix="conditional_test",
            ttl=60,
            cache_manager=cache_manager,
            condition=lambda result: result["success"] is True,
        )
        async def conditional_operation(should_succeed):
            nonlocal call_count
            call_count += 1
            return {
                "success": should_succeed,
                "data": "some_data" if should_succeed else None,
                "call_count": call_count,
            }

        # 成功的操作（应该被缓存）
        result1 = await conditional_operation(True)
        assert result1["success"] is True
        assert result1["call_count"] == 1

        result2 = await conditional_operation(True)
        assert result2["call_count"] == 1  # 从缓存获取

        # 失败的操作（不应该被缓存）
        result3 = await conditional_operation(False)
        assert result3["success"] is False
        assert result3["call_count"] == 2

        result4 = await conditional_operation(False)
        assert result4["call_count"] == 3  # 重新计算

    async def test_cache_key_generation(self, cache_manager):
        """测试自定义缓存键生成"""
        call_count = 0

        def custom_key_generator(*args, **kwargs):
            # 自定义键生成逻辑
            key_parts = []
            if args:
                key_parts.append(f"args:{','.join(map(str, args))}")
            if kwargs:
                sorted_kwargs = sorted(kwargs.items())
                key_parts.append(
                    f"kwargs:{','.join(f'{k}={v}' for k, v in sorted_kwargs)}"
                )
            return ":".join(key_parts)

        @cached(
            key_prefix="custom_key",
            ttl=60,
            cache_manager=cache_manager,
            key_generator=custom_key_generator,
        )
        async def complex_operation(a, b=None, c=None):
            nonlocal call_count
            call_count += 1
            return {"result": a, "b": b, "c": c, "call_count": call_count}

        # 使用位置参数
        result1 = await complex_operation("test1")
        assert result1["call_count"] == 1

        # 相同的调用（应该命中缓存）
        result2 = await complex_operation("test1")
        assert result2["call_count"] == 1

        # 使用关键字参数
        result3 = await complex_operation("test1", b="value")
        assert result3["call_count"] == 2

        # 相同的调用（应该命中缓存）
        result4 = await complex_operation("test1", b="value")
        assert result4["call_count"] == 2

        # 验证不同的键生成
        keys = await cache_manager.keys("custom_key:*")
        assert len(keys) == 2  # 应该有两个不同的键
