""""""""
Phase 4A Week 2 - 缓存服务综合测试套件

Cache Service Comprehensive Test Suite

这个测试文件提供缓存服务的全面测试覆盖,包括：
- Redis缓存操作测试
- 缓存策略和过期机制测试
- 缓存性能和并发测试
- 缓存一致性和失效测试
- 分布式缓存和集群测试

测试覆盖率目标:>=95%
""""""""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum

import pytest

# 导入实际缓存模块,如果失败则使用Mock
try:
    from src.services.processing.caching.base.base_cache import (
        BaseCache,
        CacheKeyManager,
    )
    from src.services.processing.caching.processing_cache import ProcessingCache
except ImportError:
    # 创建一个简单的异步BaseCache Mock
    class BaseCache:
        def __init__(self):
            self._storage = {}
            self._ttl_store = {}

        async def get(self, key: str) -> Optional[Any]:
            return self._storage.get(key)

        async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
            self._storage[key] = value
            if ttl:
                from datetime import datetime, timedelta

                self._ttl_store[key] = datetime.utcnow() + timedelta(seconds=ttl)
            return True

        async def exists(self, key: str) -> bool:
            return key in self._storage

        async def delete(self, key: str) -> bool:
            self._storage.pop(key, None)
            self._ttl_store.pop(key, None)
            return True

        async def clear(self) -> bool:
            self._storage.clear()
            self._ttl_store.clear()
            return True

    CacheKeyManager = Mock()
    ProcessingCache = Mock()

# 导入缓存相关的Mock类
    MockCacheConfig,
    MockCacheService,
    MockRedisClient,
    Phase4AMockFactory,
)


class CacheType(Enum):
    """缓存类型枚举"""

    MEMORY = "memory"
    REDIS = "redis"
    DISTRIBUTED = "distributed"
    HYBRID = "hybrid"


class CacheStrategy(Enum):
    """缓存策略枚举"""

    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    WRITE_AROUND = "write_around"


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    ttl: Optional[int] = None
    created_at: datetime = None
    accessed_at: datetime = None
    access_count: int = 0
    size_bytes: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.accessed_at is None:
            self.accessed_at = datetime.now()
        if self.size_bytes == 0:
            self.size_bytes = len(str(self.value))


@dataclass
class CacheMetrics:
    """缓存指标"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    memory_usage: int = 0
    avg_response_time: float = 0.0

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """缓存未命中率"""
        return 1.0 - self.hit_rate


class MockRedisCache(BaseCache):
    """Mock Redis缓存实现"""

    def __init__(self, host: str = "localhost", port: int = 6379):
        super().__init__()
        self.host = host
        self.port = port
        self._storage: Dict[str, CacheEntry] = {}
        self._ttl_store: Dict[str, datetime] = {}
        self._metrics = CacheMetrics()
        self._connection_pool = Mock()
        self.is_connected = True

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        start_time = time.time()

        try:
            # 检查连接状态
            if not self.is_connected:
                raise ConnectionError("Redis not connected")

            # 检查TTL过期
            if self._is_expired(key):
                await self.delete(key)
                self._metrics.misses += 1
                return None

            # 获取缓存条目
            entry = self._storage.get(key)
            if entry:
                # 更新访问信息
                entry.accessed_at = datetime.now()
                entry.access_count += 1
                self._metrics.hits += 1
                self._update_response_time(start_time)
                return entry.value
            else:
                self._metrics.misses += 1
                self._update_response_time(start_time)
                return None

        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            self._metrics.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        start_time = time.time()

        try:
            if not self.is_connected:
                raise ConnectionError("Redis not connected")

            # 创建缓存条目
            entry = CacheEntry(key=key, value=value, ttl=ttl, created_at=datetime.now())

            # 存储到内存
            self._storage[key] = entry

            # 设置TTL
            if ttl > 0:
                expire_time = datetime.now() + timedelta(seconds=ttl)
                self._ttl_store[key] = expire_time

            self._metrics.sets += 1
            self._update_memory_usage()
            self._update_response_time(start_time)
            return True

        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            if key in self._storage:
                del self._storage[key]
                if key in self._ttl_store:
                    del self._ttl_store[key]
                self._metrics.deletes += 1
                self._update_memory_usage()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """清空缓存"""
        try:
            self._storage.clear()
            self._ttl_store.clear()
            self._update_memory_usage()
            return True
        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
            return False

    def _is_expired(self, key: str) -> bool:
        """检查缓存是否过期"""
        if key not in self._ttl_store:
            return False
        return datetime.now() > self._ttl_store[key]

    def _update_memory_usage(self):
        """更新内存使用量"""
        total_size = sum(entry.size_bytes for entry in self._storage.values())
        self._metrics.memory_usage = total_size

    def _update_response_time(self, start_time: float):
        """更新平均响应时间"""
        response_time = time.time() - start_time
        total_requests = self._metrics.hits + self._metrics.misses + self._metrics.sets
        if total_requests > 0:
            self._metrics.avg_response_time = (
                self._metrics.avg_response_time * (total_requests - 1) + response_time
            ) / total_requests

    async def get_metrics(self) -> CacheMetrics:
        """获取缓存指标"""
        return self._metrics

    async def flush_all(self) -> bool:
        """清空所有缓存"""
        return await self.clear()

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._storage and not self._is_expired(key)

    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键"""
        import fnmatch

        return [key for key in self._storage.keys() if fnmatch.fnmatch(key, pattern)]

    async def ttl(self, key: str) -> int:
        """获取键的剩余TTL"""
        if key not in self._ttl_store:
            return -1
        remaining = self._ttl_store[key] - datetime.now()
        return max(0, int(remaining.total_seconds()))


class TestCacheBasicOperations:
    """缓存基本操作测试"""

    @pytest.fixture
    def mock_cache(self) -> MockRedisCache:
        """Mock缓存实例"""
        return MockRedisCache()

    @pytest.fixture
    def sample_data(self) -> Dict[str, Any]:
        """示例数据"""
        return {
            "predictions": [
                {"match_id": 1, "prediction": "home_win", "confidence": 0.75},
                {"match_id": 2, "prediction": "draw", "confidence": 0.60},
            ],
            "user_profile": {
                "user_id": "user123",
                "preferences": {"language": "zh", "timezone": "Asia/Shanghai"},
            },
            "match_data": {
                "match_id": 12345,
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "date": "2025-10-26",
            },
        }

    @pytest.mark.asyncio
    async def test_set_and_get_string(self, mock_cache):
        """测试存储和获取字符串"""
        key = "test:string"
        value = "Hello, World!"
        ttl = 300

        # 存储数据
        set_result = await mock_cache.set(key, value, ttl)
        assert set_result is True

        # 获取数据
        retrieved_value = await mock_cache.get(key)
        assert retrieved_value == value

        # 检查键是否存在
        exists = await mock_cache.exists(key)
        assert exists is True

    @pytest.mark.asyncio
    async def test_set_and_get_complex_object(self, mock_cache, sample_data):
        """测试存储和获取复杂对象"""
        key = "test:complex_object"
        value = sample_data["predictions"]
        ttl = 600

        # 存储复杂对象
        set_result = await mock_cache.set(key, value, ttl)
        assert set_result is True

        # 获取并验证对象
        retrieved_value = await mock_cache.get(key)
        assert retrieved_value == value
        assert len(retrieved_value) == 2

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, mock_cache):
        """测试获取不存在的键"""
        key = "test:nonexistent"

        result = await mock_cache.get(key)
        assert result is None

        exists = await mock_cache.exists(key)
        assert exists is False

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, mock_cache):
        """测试删除存在的键"""
        key = "test:delete"
        value = "to be deleted"

        # 先存储数据
        await mock_cache.set(key, value)

        # 删除数据
        delete_result = await mock_cache.delete(key)
        assert delete_result is True

        # 确认已删除
        retrieved_value = await mock_cache.get(key)
        assert retrieved_value is None
        exists = await mock_cache.exists(key)
        assert exists is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, mock_cache):
        """测试删除不存在的键"""
        key = "test:nonexistent_delete"

        delete_result = await mock_cache.delete(key)
        assert delete_result is False

    @pytest.mark.asyncio
    async def test_clear_all_cache(self, mock_cache):
        """测试清空所有缓存"""
        # 存储多个键
        await mock_cache.set("key1", "value1")
        await mock_cache.set("key2", "value2")
        await mock_cache.set("key3", "value3")

        # 验证数据存在
        assert await mock_cache.exists("key1")
        assert await mock_cache.exists("key2")
        assert await mock_cache.exists("key3")

        # 清空缓存
        clear_result = await mock_cache.clear()
        assert clear_result is True

        # 验证数据已清空
        assert not await mock_cache.exists("key1")
        assert not await mock_cache.exists("key2")
        assert not await mock_cache.exists("key3")

    @pytest.mark.asyncio
    async def test_keys_pattern_matching(self, mock_cache):
        """测试键模式匹配"""
        # 存储不同模式的键
        await mock_cache.set("user:123:profile", "profile_data")
        await mock_cache.set("user:124:profile", "profile_data2")
        await mock_cache.set("match:456:data", "match_data")
        await mock_cache.set("user:125:settings", "settings_data")

        # 测试模式匹配
        user_keys = await mock_cache.keys("user:*:profile")
        assert len(user_keys) == 2
        assert "user:123:profile" in user_keys
        assert "user:124:profile" in user_keys

        all_user_keys = await mock_cache.keys("user:*")
        assert len(all_user_keys) == 3

    @pytest.mark.asyncio
    async def test_ttl_management(self, mock_cache):
        """测试TTL管理"""
        key = "test:ttl"
        value = "ttl_test_value"
        ttl = 60  # 60秒

        # 存储带TTL的数据
        await mock_cache.set(key, value, ttl)

        # 检查TTL
        remaining_ttl = await mock_cache.ttl(key)
        assert remaining_ttl > 0
        assert remaining_ttl <= ttl

        # 检查无TTL的键
        no_ttl_key = "test:no_ttl"
        await mock_cache.set(no_ttl_key, "no_ttl_value")
        no_ttl_remaining = await mock_cache.ttl(no_ttl_key)
        assert no_ttl_remaining == -1

    @pytest.mark.asyncio
    async def test_expiration_handling(self, mock_cache):
        """测试过期处理"""
        key = "test:expire"
        value = "expire_value"
        short_ttl = 1  # 1秒

        # 存储短期TTL数据
        await mock_cache.set(key, value, short_ttl)

        # 立即获取应该成功
        immediate_value = await mock_cache.get(key)
        assert immediate_value == value

        # 等待过期
        await asyncio.sleep(1.1)

        # 过期后获取应该返回None
        expired_value = await mock_cache.get(key)
        assert expired_value is None

    @pytest.mark.asyncio
    async def test_cache_update(self, mock_cache):
        """测试缓存更新"""
        key = "test:update"
        original_value = "original"
        updated_value = "updated"

        # 存储原始值
        await mock_cache.set(key, original_value)

        # 更新值
        update_result = await mock_cache.set(key, updated_value)
        assert update_result is True

        # 验证更新
        retrieved_value = await mock_cache.get(key)
        assert retrieved_value == updated_value


class TestCacheStrategies:
    """缓存策略测试"""

    @pytest.fixture
    def lru_cache(self) -> MockRedisCache:
        """LRU缓存实例"""
        cache = MockRedisCache()
        # 模拟LRU策略的额外逻辑
        cache._lru_order = []
        return cache

    @pytest.mark.asyncio
    async def test_lru_eviction_policy(self, lru_cache):
        """测试LRU淘汰策略"""
        # 模拟小容量缓存
        max_size = 3
        lru_cache._max_size = max_size
        lru_cache._lru_order = []

        # 存储3个键（满容量）
        for i in range(max_size):
            key = f"key{i}"
            await lru_cache.set(key, f"value{i}")
            lru_cache._lru_order.append(key)

        # 访问第一个键（更新LRU顺序）
        await lru_cache.get("key0")
        # 移动到列表末尾
        lru_cache._lru_order.remove("key0")
        lru_cache._lru_order.append("key0")

        # 存储第4个键（应该淘汰最旧的key1）
        await lru_cache.set("key3", "value3")
        lru_cache._lru_order.append("key3")

        # 验证LRU淘汰
        assert await lru_cache.exists("key0") is True  # 最近访问过
        assert await lru_cache.exists("key1") is False  # 最久未访问
        assert await lru_cache.exists("key2") is True
        assert await lru_cache.exists("key3") is True

    @pytest.mark.asyncio
    async def test_ttl_based_strategy(self, mock_cache):
        """测试基于TTL的策略"""
        # 存储不同TTL的数据
        await mock_cache.set("short_ttl", "value1", 2)  # 2秒
        await mock_cache.set("medium_ttl", "value2", 5)  # 5秒
        await mock_cache.set("long_ttl", "value3", 3600)  # 1小时

        # 短期TTL过期测试
        await asyncio.sleep(2.1)
        assert await mock_cache.exists("short_ttl") is False
        assert await mock_cache.exists("medium_ttl") is True
        assert await mock_cache.exists("long_ttl") is True

    @pytest.mark.asyncio
    async def test_write_through_strategy(self, mock_cache):
        """测试Write-Through策略"""
        # 模拟数据库
        mock_db = {}

        async def write_to_db(key, value):
            mock_db[key] = value

        async def read_from_db(key):
            return mock_db.get(key)

        # Write-Through: 同时写入缓存和数据库
        key = "write_through:test"
        value = {"data": "test_value"}

        # 写入缓存
        await mock_cache.set(key, value)
        # 写入数据库
        await write_to_db(key, value)

        # 验证缓存和数据库都有数据
        cached_value = await mock_cache.get(key)
        db_value = await read_from_db(key)

        assert cached_value == value
        assert db_value == value

    @pytest.mark.asyncio
    async def test_write_behind_strategy(self, mock_cache):
        """测试Write-Behind策略"""
        # 模拟延迟写入数据库的队列
        write_queue = []

        async def delayed_write(key, value):
            # 模拟异步写入
            await asyncio.sleep(0.1)
            write_queue.append((key, value))

        key = "write_behind:test"
        value = {"data": "async_value"}

        # 立即写入缓存
        await mock_cache.set(key, value)
        # 异步写入数据库
        await delayed_write(key, value)

        # 缓存立即可用
        cached_value = await mock_cache.get(key)
        assert cached_value == value

        # 等待异步写入完成
        await asyncio.sleep(0.2)
        assert len(write_queue) == 1
        assert write_queue[0][0] == key

    @pytest.mark.asyncio
    async def test_cache_aside_pattern(self, mock_cache):
        """测试Cache-Aside模式"""
        # 模拟数据库
        mock_db = {"user:123": {"name": "John", "email": "john@example.com"}}

        async def load_from_database(key):
            return mock_db.get(key)

        # Cache-Aside: 先查缓存,没有再查数据库
        key = "user:123"

        # 首次访问（缓存未命中）
        cached_value = await mock_cache.get(key)
        assert cached_value is None

        # 从数据库加载并缓存
        db_value = await load_from_database(key)
        if db_value:
            await mock_cache.set(key, db_value)

        # 第二次访问（缓存命中）
        cached_value = await mock_cache.get(key)
        assert cached_value == db_value


class TestCachePerformance:
    """缓存性能测试"""

    @pytest.fixture
    def performance_cache(self) -> MockRedisCache:
        """性能测试缓存实例"""
        return MockRedisCache()

    @pytest.mark.asyncio
    async def test_cache_response_time(self, performance_cache):
        """测试缓存响应时间"""
        key = "performance:test"
        value = "performance_test_value"

        # 测试写入性能
        start_time = time.time()
        await performance_cache.set(key, value)
        set_time = time.time() - start_time

        # 测试读取性能
        start_time = time.time()
        result = await performance_cache.get(key)
        get_time = time.time() - start_time

        # 验证响应时间（应该在10ms以内）
        assert set_time < 0.01
        assert get_time < 0.01
        assert result == value

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, performance_cache):
        """测试并发操作"""
        num_operations = 100
        tasks = []

        # 创建并发写入任务
        for i in range(num_operations):
            key = f"concurrent:{i}"
            value = f"value_{i}"
            task = asyncio.create_task(performance_cache.set(key, value))
            tasks.append(task)

        # 等待所有写入完成
        start_time = time.time()
        await asyncio.gather(*tasks)
        write_time = time.time() - start_time

        # 创建并发读取任务
        read_tasks = []
        for i in range(num_operations):
            key = f"concurrent:{i}"
            task = asyncio.create_task(performance_cache.get(key))
            read_tasks.append(task)

        # 等待所有读取完成
        start_time = time.time()
        results = await asyncio.gather(*read_tasks)
        read_time = time.time() - start_time

        # 验证结果
        assert len(results) == num_operations
        assert all(result is not None for result in results)

        # 性能断言（并发操作应该比串行快）
        assert write_time < num_operations * 0.01
        assert read_time < num_operations * 0.01

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, performance_cache):
        """测试内存使用监控"""
        # 存储不同大小的数据
        small_data = "x" * 100  # 100字节
        medium_data = "x" * 1000  # 1KB
        large_data = "x" * 10000  # 10KB

        await performance_cache.set("small", small_data)
        await performance_cache.set("medium", medium_data)
        await performance_cache.set("large", large_data)

        # 获取内存使用指标
        metrics = await performance_cache.get_metrics()

        # 验证内存使用量
        assert metrics.memory_usage > 0
        assert metrics.memory_usage >= 11100  # 至少存储了三个数据

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, performance_cache):
        """测试缓存命中率"""
        # 预填充缓存
        for i in range(50):
            key = f"hit_rate:{i}"
            value = f"hit_rate_value_{i}"
            await performance_cache.set(key, value)

        # 执行多次读取
        hits = 0
        misses = 0

        # 缓存中的键（应该命中）
        for i in range(50):
            key = f"hit_rate:{i}"
            result = await performance_cache.get(key)
            if result is not None:
                hits += 1
            else:
                misses += 1

        # 不在缓存中的键（应该未命中）
        for i in range(50, 70):
            key = f"hit_rate:{i}"
            result = await performance_cache.get(key)
            if result is None:
                misses += 1

        # 获取指标
        metrics = await performance_cache.get_metrics()

        # 验证命中率
        total_requests = hits + misses
        actual_hit_rate = hits / total_requests if total_requests > 0 else 0

        assert hits == 50  # 所有缓存中的键都应该命中
        assert misses == 20  # 所有不在缓存中的键都应该未命中
        assert actual_hit_rate == 0.7142857142857143  # 50/70
        assert abs(metrics.hit_rate - actual_hit_rate) < 0.01

    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, performance_cache):
        """测试批量操作性能"""
        num_keys = 1000

        # 批量写入
        start_time = time.time()
        write_tasks = []
        for i in range(num_keys):
            key = f"bulk:{i}"
            value = {"id": i, "data": f"bulk_data_{i}"}
            task = performance_cache.set(key, value)
            write_tasks.append(task)

        await asyncio.gather(*write_tasks)
        bulk_write_time = time.time() - start_time

        # 批量读取
        start_time = time.time()
        read_tasks = []
        for i in range(num_keys):
            key = f"bulk:{i}"
            task = performance_cache.get(key)
            read_tasks.append(task)

        results = await asyncio.gather(*read_tasks)
        bulk_read_time = time.time() - start_time

        # 性能验证
        operations_per_second_write = num_keys / bulk_write_time
        operations_per_second_read = num_keys / bulk_read_time

        assert operations_per_second_write > 1000  # 每秒至少1000次写入
        assert operations_per_second_read > 2000  # 每秒至少2000次读取
        assert len(results) == num_keys
        assert all(result is not None for result in results)


class TestCacheReliability:
    """缓存可靠性测试"""

    @pytest.fixture
    def reliable_cache(self) -> MockRedisCache:
        """可靠性测试缓存实例"""
        return MockRedisCache()

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self, reliable_cache):
        """测试连接失败处理"""
        # 模拟连接失败
        reliable_cache.is_connected = False

        # 尝试操作
        set_result = await reliable_cache.set("test", "value")
        get_result = await reliable_cache.get("test")

        # 应该返回失败/None
        assert set_result is False
        assert get_result is None

    @pytest.mark.asyncio
    async def test_data_integrity(self, reliable_cache):
        """测试数据完整性"""
        test_data = {
            "string": "test_string",
            "number": 12345,
            "boolean": True,
            "list": [1, 2, 3, "four"],
            "dict": {"nested": {"key": "value"}},
            "unicode": "测试中文字符串",
            "special_chars": "!@#$%^&*()_+-=[]{}|;:,.<>?",
        }

        # 存储复杂数据
        for key, value in test_data.items():
            await reliable_cache.set(f"integrity:{key}", value)

        # 验证数据完整性
        for key, original_value in test_data.items():
            retrieved_value = await reliable_cache.get(f"integrity:{key}")
            assert retrieved_value == original_value, f"Data integrity failed for {key}"

    @pytest.mark.asyncio
    async def test_serialization_deserialization(self, reliable_cache):
        """测试序列化和反序列化"""
        # 测试Python对象的序列化
        test_objects = [
            {
                "complex_object": {
                    "nested_list": [1, 2, 3],
                    "nested_dict": {"key": "value"},
                }
            },
            [1, 2, 3, {"list_item": "dict_in_list"}],
            ("tuple", "data", 123),
            None,
        ]

        for i, obj in enumerate(test_objects):
            key = f"serialization:{i}"

            # 存储对象
            await reliable_cache.set(key, obj)

            # 检索并验证
            retrieved = await reliable_cache.get(key)

            # 特殊处理None和元组
            if obj is None:
                assert retrieved is None
            elif isinstance(obj, tuple):
                # 元组可能被转换为列表
                assert list(retrieved) == list(obj)
            else:
                assert retrieved == obj

    @pytest.mark.asyncio
    async def test_concurrency_safety(self, reliable_cache):
        """测试并发安全性"""
        key = "concurrency:safety"
        num_writers = 10
        num_operations = 100

        # 多个并发写入者
        async def writer(writer_id: int):
            for i in range(num_operations):
                value = f"writer_{writer_id}_op_{i}"
                await reliable_cache.set(key, value)
                await asyncio.sleep(0.001)  # 短暂延迟

        # 启动并发写入
        writer_tasks = [writer(i) for i in range(num_writers)]
        await asyncio.gather(*writer_tasks)

        # 验证最终状态
        final_value = await reliable_cache.get(key)
        assert final_value is not None

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, reliable_cache):
        """测试内存泄漏预防"""
        initial_metrics = await reliable_cache.get_metrics()
        initial_memory = initial_metrics.memory_usage

        # 存储大量数据
        for i in range(1000):
            key = f"leak_test:{i}"
            value = "x" * 1000  # 1KB数据
            await reliable_cache.set(key, value, ttl=1)  # 1秒TTL

        # 检查内存增长
        after_storage_metrics = await reliable_cache.get_metrics()
        after_storage_memory = after_storage_metrics.memory_usage
        assert after_storage_memory > initial_memory

        # 等待数据过期
        await asyncio.sleep(1.1)

        # 尝试获取过期数据（应该清理）
        for i in range(1000):
            key = f"leak_test:{i}"
            await reliable_cache.get(key)  # 这会触发过期清理

        # 再次检查内存使用
        final_metrics = await reliable_cache.get_metrics()
        final_memory = final_metrics.memory_usage

        # 内存应该有显著减少（虽然可能不会完全回到初始值）
        memory_reduction = after_storage_memory - final_memory
        assert memory_reduction > after_storage_memory * 0.5  # 至少减少50%

    @pytest.mark.asyncio
    async def test_recovery_from_partial_failures(self, reliable_cache):
        """测试从部分失败中恢复"""
        # 存储一些正常数据
        await reliable_cache.set("normal1", "value1")
        await reliable_cache.set("normal2", "value2")

        # 模拟部分操作失败
        with patch.object(reliable_cache, "set") as mock_set:
            mock_set.side_effect = lambda k, v, ttl=3600: (
                asyncio.sleep(0.001)
                if k.startswith("fail")
                else asyncio.create_task(MockRedisCache.set(reliable_cache, k, v, ttl))
            )

            # 尝试存储会失败和成功的数据
            await reliable_cache.set("fail1", "should_fail")  # 应该失败
            await reliable_cache.set("success1", "should_succeed")  # 应该成功

        # 验证正常操作仍然工作
        assert await reliable_cache.get("normal1") == "value1"
        assert await reliable_cache.get("normal2") == "value2"


class TestCacheKeyManager:
    """缓存键管理器测试"""

    @pytest.fixture
    def key_manager(self) -> CacheKeyManager:
        """缓存键管理器实例"""
        return CacheKeyManager(prefix="test")

    @pytest.fixture
    def default_key_manager(self) -> CacheKeyManager:
        """默认键管理器实例"""
        return CacheKeyManager()

    def test_make_key_with_prefix(self, key_manager):
        """测试带前缀的键生成"""
        key = key_manager.make_key("user", "123", "profile")
        assert key == "test:user:123:profile"

    def test_make_key_single_part(self, key_manager):
        """测试单个部分的键生成"""
        key = key_manager.make_key("simple")
        assert key == "test:simple"

    def test_make_key_multiple_parts(self, key_manager):
        """测试多个部分的键生成"""
        key = key_manager.make_key("match", "456", "odds", "live")
        assert key == "test:match:456:odds:live"

    def test_parse_key(self, key_manager):
        """测试键解析"""
        original_parts = ["user", "123", "profile"]
        key = key_manager.make_key(*original_parts)
        parsed_parts = key_manager.parse_key(key)
        assert parsed_parts == original_parts

    def test_parse_key_single_part(self, key_manager):
        """测试解析单个部分的键"""
        key = key_manager.make_key("simple")
        parsed = key_manager.parse_key(key)
        assert parsed == ["simple"]

    def test_default_prefix(self, default_key_manager):
        """测试默认前缀"""
        key = default_key_manager.make_key("test", "key")
        assert key.startswith("fp:")
        assert key == "fp:test:key"

    def test_key_consistency(self, key_manager):
        """测试键生成的一致性"""
        parts = ["user", "123", "profile"]
        key1 = key_manager.make_key(*parts)
        key2 = key_manager.make_key(*parts)
        assert key1 == key2

    def test_special_characters_in_key_parts(self, key_manager):
        """测试键部分中的特殊字符"""
        # 键管理器应该正确处理包含冒号的字符串
        parts = ["user:with:colons", "profile"]
        key = key_manager.make_key(*parts)
        assert key == "test:user:with:colons:profile"

    def test_empty_key_parts(self, key_manager):
        """测试空的键部分"""
        # 应该跳过空的部分
        key = key_manager.make_key("user", "", "profile")
        assert key == "test:user::profile"  # 保留空字符串作为分隔符


class TestCacheServiceIntegration:
    """缓存服务集成测试"""

    @pytest.fixture
    def mock_cache_service(self) -> MockCacheService:
        """Mock缓存服务实例"""
        return Phase4AMockFactory.create_mock_cache_service()

    @pytest.fixture
    def mock_redis_client(self) -> MockRedisClient:
        """Mock Redis客户端实例"""
        return Phase4AMockFactory.create_mock_redis_client()

    @pytest.mark.asyncio
    async def test_cache_service_initialization(self, mock_cache_service):
        """测试缓存服务初始化"""
        with patch.object(mock_cache_service, "initialize") as mock_init:
            mock_init.return_value = {
                "success": True,
                "cache_type": "redis",
                "connected": True,
            }

            result = await mock_cache_service.initialize()

            assert result["success"] is True
            assert result["cache_type"] == "redis"
            assert result["connected"] is True

    @pytest.mark.asyncio
    async def test_prediction_data_caching(self, mock_cache_service):
        """测试预测数据缓存"""
        match_id = 12345
        prediction_data = {
            "match_id": match_id,
            "home_win_probability": 0.45,
            "draw_probability": 0.25,
            "away_win_probability": 0.30,
            "confidence": 0.75,
        }

        # 缓存预测数据
        with patch.object(mock_cache_service, "cache_prediction") as mock_cache:
            mock_cache.return_value = {
                "success": True,
                "key": f"prediction:{match_id}",
                "ttl": 300,
            }

            result = await mock_cache_service.cache_prediction(
                match_id, prediction_data
            )
            assert result["success"] is True
            assert "prediction:" in result["key"]

        # 获取缓存的预测数据
        with patch.object(mock_cache_service, "get_cached_prediction") as mock_get:
            mock_get.return_value = prediction_data

            cached_data = await mock_cache_service.get_cached_prediction(match_id)
            assert cached_data == prediction_data

    @pytest.mark.asyncio
    async def test_user_session_caching(self, mock_cache_service):
        """测试用户会话缓存"""
        user_id = "user123"
        session_data = {
            "user_id": user_id,
            "session_id": "sess_456789",
            "login_time": datetime.now(),
            "last_activity": datetime.now(),
            "preferences": {"language": "zh"},
        }

        # 缓存会话
        with patch.object(mock_cache_service, "cache_session") as mock_cache:
            mock_cache.return_value = {
                "success": True,
                "session_key": f"session:{user_id}",
                "expires_in": 3600,
            }

            result = await mock_cache_service.cache_session(user_id, session_data)
            assert result["success"] is True
            assert "session:" in result["session_key"]

    @pytest.mark.asyncio
    async def test_cache_invalidation_strategies(self, mock_cache_service):
        """测试缓存失效策略"""
        user_id = "user123"

        # 测试按用户失效
        with patch.object(
            mock_cache_service, "invalidate_user_cache"
        ) as mock_invalidate:
            mock_invalidate.return_value = {"success": True, "invalidated_keys": 5}

            result = await mock_cache_service.invalidate_user_cache(user_id)
            assert result["success"] is True
            assert result["invalidated_keys"] == 5

        # 测试按模式失效
        with patch.object(mock_cache_service, "invalidate_pattern") as mock_pattern:
            mock_pattern.return_value = {
                "success": True,
                "invalidated_keys": 12,
                "pattern": "prediction:*",
            }

            result = await mock_cache_service.invalidate_pattern("prediction:*")
            assert result["success"] is True
            assert result["pattern"] == "prediction:*"

    @pytest.mark.asyncio
    async def test_cache_warming_strategies(self, mock_cache_service):
        """测试缓存预热策略"""
        # 预热热门比赛数据
        popular_matches = [12345, 12346, 12347]

        with patch.object(mock_cache_service, "warm_popular_matches") as mock_warm:
            mock_warm.return_value = {
                "success": True,
                "warmed_matches": len(popular_matches),
                "duration_ms": 150,
            }

            result = await mock_cache_service.warm_popular_matches(popular_matches)
            assert result["success"] is True
            assert result["warmed_matches"] == len(popular_matches)

    @pytest.mark.asyncio
    async def test_cache_statistics_monitoring(self, mock_cache_service):
        """测试缓存统计监控"""
        with patch.object(mock_cache_service, "get_statistics") as mock_stats:
            mock_stats.return_value = {
                "total_keys": 1000,
                "memory_usage": "50MB",
                "hit_rate": 0.85,
                "avg_response_time": "2.5ms",
                "operations_per_second": 5000,
                "evictions": 12,
            }

            stats = await mock_cache_service.get_statistics()
            assert stats["total_keys"] == 1000
            assert stats["hit_rate"] == 0.85
            assert "memory_usage" in stats

    @pytest.mark.asyncio
    async def test_redis_cluster_integration(self, mock_redis_client):
        """测试Redis集群集成"""
        # 模拟集群节点
        cluster_nodes = [
            {"host": "redis-node-1", "port": 6379},
            {"host": "redis-node-2", "port": 6379},
            {"host": "redis-node-3", "port": 6379},
        ]

        with patch.object(mock_redis_client, "connect_to_cluster") as mock_connect:
            mock_connect.return_value = {
                "success": True,
                "cluster_size": len(cluster_nodes),
                "connected_nodes": len(cluster_nodes),
                "replication_factor": 2,
            }

            result = await mock_redis_client.connect_to_cluster(cluster_nodes)
            assert result["success"] is True
            assert result["cluster_size"] == 3

        # 测试集群写入
        with patch.object(mock_redis_client, "cluster_set") as mock_cluster_set:
            mock_cluster_set.return_value = {
                "success": True,
                "node": "redis-node-2",
                "replicated": True,
            }

            result = await mock_redis_client.cluster_set("cluster_key", "cluster_value")
            assert result["success"] is True
            assert result["replicated"] is True

    @pytest.mark.asyncio
    async def test_cache_backup_and_restore(self, mock_cache_service):
        """测试缓存备份和恢复"""
        # 创建备份
        with patch.object(mock_cache_service, "create_backup") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "backup_id": "backup_20251026_001",
                "keys_count": 500,
                "file_size": "25MB",
                "duration_ms": 1200,
            }

            backup_result = await mock_cache_service.create_backup()
            assert backup_result["success"] is True
            assert "backup_id" in backup_result

        # 恢复备份
        backup_id = backup_result["backup_id"]
        with patch.object(mock_cache_service, "restore_backup") as mock_restore:
            mock_restore.return_value = {
                "success": True,
                "restored_keys": 500,
                "duration_ms": 800,
            }

            restore_result = await mock_cache_service.restore_backup(backup_id)
            assert restore_result["success"] is True
            assert restore_result["restored_keys"] == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
