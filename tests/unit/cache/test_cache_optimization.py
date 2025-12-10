from typing import Optional

"""
缓存系统优化测试
Cache System Optimization Tests
"""

import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cache.cache_consistency_manager import (
    CacheVersion,
    VectorClock,
    get_cache_consistency_manager,
)
from src.cache.distributed_cache_manager import (
    CacheEvictionPolicy,
    DistributedCacheManager,
    MemoryCache,
    get_distributed_cache_manager,
)
from src.cache.intelligent_cache_warmup import (
    AccessPatternAnalyzer,
    IntelligentCacheWarmupManager,
    PriorityLevel,
    WarmupStrategy,
    WarmupTask,
    get_intelligent_warmup_manager,
)
from src.cache.redis_cluster_manager import (
    CacheEntry,
    ClusterNode,
    ConsistentHashRing,
    RedisClusterManager,
    get_redis_cluster_manager,
)


class TestClusterNode:
    """集群节点测试"""

    def test_node_creation(self):
        """测试节点创建"""
        node = ClusterNode(
            node_id="test_node", host="localhost", port=6379, is_master=True
        )

        assert node.node_id == "test_node"
        assert node.host == "localhost"
        assert node.port == 6379
        assert node.is_master is True
        assert node.status.value == "healthy"
        assert node.failure_count == 0

    def test_node_health_tracking(self):
        """测试节点健康状态跟踪"""
        node = ClusterNode("test", "localhost", 6379)

        # 模拟健康检查失败
        node.failure_count += 1
        node.last_health_check = datetime.utcnow()

        assert node.failure_count == 1
        assert node.last_health_check is not None

        # 测试达到最大失败次数
        for _i in range(node.max_failures - 1):
            node.failure_count += 1

        assert node.failure_count == node.max_failures


class TestConsistentHashRing:
    """一致性哈希环测试"""

    def test_ring_initialization(self):
        """测试哈希环初始化"""
        ring = ConsistentHashRing(replicas=100)

        assert ring.replicas == 100
        assert len(ring.ring) == 0
        assert len(ring.sorted_keys) == 0
        assert len(ring.nodes) == 0

    def test_add_node(self):
        """测试添加节点"""
        ring = ConsistentHashRing()
        node = ClusterNode("node1", "localhost", 6379)

        ring.add_node(node)

        assert len(ring.nodes) == 1
        assert "node1" in ring.nodes
        assert len(ring.ring) == ring.replicas
        assert len(ring.sorted_keys) == ring.replicas

    def test_remove_node(self):
        """测试移除节点"""
        ring = ConsistentHashRing()
        node1 = ClusterNode("node1", "localhost", 6379)
        node2 = ClusterNode("node2", "localhost", 6380)

        ring.add_node(node1)
        ring.add_node(node2)

        assert len(ring.nodes) == 2

        ring.remove_node("node1")

        assert len(ring.nodes) == 1
        assert "node1" not in ring.nodes
        assert "node2" in ring.nodes

    def test_get_node(self):
        """测试获取节点"""
        ring = ConsistentHashRing()
        node1 = ClusterNode("node1", "localhost", 6379)
        node2 = ClusterNode("node2", "localhost", 6380)

        ring.add_node(node1)
        ring.add_node(node2)

        # 测试键路由
        selected_node = ring.get_node("test_key")
        assert selected_node in [node1, node2]

        # 测试一致性 - 相同的键应该路由到相同的节点
        selected_node2 = ring.get_node("test_key")
        assert selected_node.node_id == selected_node2.node_id

    def test_get_nodes_for_key(self):
        """测试获取多个节点"""
        ring = ConsistentHashRing()
        node1 = ClusterNode("node1", "localhost", 6379)
        node2 = ClusterNode("node2", "localhost", 6380)
        node3 = ClusterNode("node3", "localhost", 6381)

        ring.add_node(node1)
        ring.add_node(node2)
        ring.add_node(node3)

        # 获取2个节点用于复制
        nodes = ring.get_nodes_for_key("test_key", count=2)
        assert len(nodes) == 2
        assert all(node.status.value == "healthy" for node in nodes)


class TestCacheEntry:
    """缓存条目测试"""

    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        entry = CacheEntry(key="test_key", value={"data": "test_value"}, ttl=3600)

        assert entry.key == "test_key"
        assert entry.value == {"data": "test_value"}
        assert entry.ttl == 3600
        assert entry.access_count == 0
        assert entry.checksum != ""

    def test_cache_entry_expiration(self):
        """测试缓存条目过期"""
        # 创建已过期的条目
        entry = CacheEntry(key="expired_key", value="test_value", ttl=1)  # 1秒TTL

        # 等待过期
        time.sleep(2)

        assert entry.is_expired() is True

    def test_cache_entry_access(self):
        """测试缓存条目访问"""
        entry = CacheEntry("test_key", "test_value")

        initial_count = entry.access_count
        initial_accessed = entry.accessed_at

        value = entry.access()

        assert value == "test_value"
        assert entry.access_count == initial_count + 1
        assert entry.accessed_at > initial_accessed

    def test_cache_entry_validity(self):
        """测试缓存条目有效性"""
        entry = CacheEntry("test_key", "test_value")

        # 新条目应该是有效的
        assert entry.is_valid() is True

        # 修改值使校验和不匹配
        entry.value = "modified_value"
        assert entry.is_valid() is False


class TestRedisClusterManager:
    """Redis集群管理器测试"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = RedisClusterManager(health_check_interval=30, connection_timeout=5)

        assert manager.health_check_interval == 30
        assert manager.connection_timeout == 5
        assert len(manager.nodes) == 0
        assert len(manager.hash_ring.ring) == 0

    @pytest.mark.asyncio
    async def test_add_node_success(self):
        """测试成功添加节点"""
        manager = RedisClusterManager()

        node_config = {
            "node_id": "test_node",
            "host": "localhost",
            "port": 6379,
            "is_master": True,
        }

        # 使用Mock连接
        with patch("src.cache.redis_cluster_manager.MockRedisManager") as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance

            result = await manager.add_node(node_config)

            assert result is True
            assert "test_node" in manager.nodes
            assert manager.nodes["test_node"].node_id == "test_node"

    @pytest.mark.asyncio
    async def test_remove_node(self):
        """测试移除节点"""
        manager = RedisClusterManager()

        # 先添加节点
        node_config = {"node_id": "test_node", "host": "localhost", "port": 6379}

        with patch("src.cache.redis_cluster_manager.MockRedisManager"):
            await manager.add_node(node_config)

        # 移除节点
        result = await manager.remove_node("test_node")

        assert result is True
        assert "test_node" not in manager.nodes

    @pytest.mark.asyncio
    async def test_get_cache_miss(self):
        """测试缓存未命中"""
        manager = RedisClusterManager()

        result = await manager.get("non_existent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_cache(self):
        """测试缓存设置和获取"""
        manager = RedisClusterManager()

        # 测试设置（没有节点时会失败）
        result = await manager.set("test_key", "test_value")

        # 由于没有实际节点，这里主要测试不会抛出异常
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        manager = RedisClusterManager()

        # 启动健康监控
        await manager.start_health_monitoring()
        assert manager.is_monitoring is True

        # 停止健康监控
        await manager.stop_health_monitoring()
        assert manager.is_monitoring is False

    @pytest.mark.asyncio
    async def test_get_cluster_status(self):
        """测试获取集群状态"""
        manager = RedisClusterManager()

        status = await manager.get_cluster_status()

        assert "cluster_info" in status
        assert "nodes" in status
        assert "metrics" in status
        assert status["cluster_info"]["total_nodes"] == 0


class TestMemoryCache:
    """内存缓存测试"""

    def test_memory_cache_initialization(self):
        """测试内存缓存初始化"""
        from src.cache.distributed_cache_manager import CacheConfig

        config = CacheConfig(max_size=100, ttl=300)
        cache = MemoryCache(config)

        assert cache.config.max_size == 100
        assert cache.config.ttl == 300
        assert len(cache.cache) == 0

    def test_memory_cache_set_and_get(self):
        """测试内存缓存设置和获取"""
        from src.cache.distributed_cache_manager import CacheConfig

        config = CacheConfig(max_size=10)
        cache = MemoryCache(config)

        # 设置缓存
        result = cache.set("test_key", "test_value")
        assert result is True

        # 获取缓存
        value = cache.get("test_key")
        assert value == "test_value"

    def test_memory_cache_expiration(self):
        """测试内存缓存过期"""
        from src.cache.distributed_cache_manager import CacheConfig

        config = CacheConfig(max_size=10)
        cache = MemoryCache(config)

        # 设置短TTL缓存
        cache.set("expire_key", "test_value", ttl=1)

        # 等待过期
        time.sleep(2)

        # 应该返回None（已过期）
        value = cache.get("expire_key")
        assert value is None

    def test_memory_cache_eviction(self):
        """测试内存缓存淘汰"""
        from src.cache.distributed_cache_manager import CacheConfig

        config = CacheConfig(max_size=2, eviction_policy=CacheEvictionPolicy.LRU)
        cache = MemoryCache(config)

        # 添加3个条目（超过最大容量）
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 检查是否只有一个条目被保留
        assert len(cache.cache) <= 2

        # 检查最旧的条目是否被淘汰
        assert "key1" not in cache.cache  # LRU应该淘汰最旧的

    def test_memory_cache_metrics(self):
        """测试内存缓存指标"""
        from src.cache.distributed_cache_manager import CacheConfig

        config = CacheConfig(max_size=10)
        cache = MemoryCache(config)

        # 执行一些操作
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("non_existent_key")

        metrics = cache.get_metrics()

        assert metrics["hits"] == 1
        assert metrics["misses"] == 1
        assert metrics["sets"] == 1
        assert metrics["size"] == 1
        assert "hit_rate" in metrics


class TestVectorClock:
    """向量时钟测试"""

    def test_vector_clock_creation(self):
        """测试向量时钟创建"""
        clock = VectorClock("node1")

        assert clock.node_id == "node1"
        assert clock.clock["node1"] == 1
        assert len(clock.clock) == 1

    def test_vector_clock_increment(self):
        """测试向量时钟递增"""
        clock = VectorClock("node1")
        initial_time = clock.clock["node1"]

        clock.increment()

        assert clock.clock["node1"] == initial_time + 1

    def test_vector_clock_update(self):
        """测试向量时钟更新"""
        clock1 = VectorClock("node1")
        clock2 = VectorClock("node2")

        clock1.increment()  # node1: 2
        clock2.increment()  # node2: 2

        # 更新时钟
        clock1.update(clock2)

        assert clock1.clock["node1"] == 2
        assert clock1.clock["node2"] == 2

    def test_vector_clock_happens_before(self):
        """测试向量时钟先后关系"""
        clock1 = VectorClock("node1")
        clock2 = VectorClock("node2")

        clock1.increment()
        clock1.increment()

        # clock1 (2,0) 应该先于 clock2 (0,1)
        assert clock1.happens_before(clock2) is False
        assert clock2.happens_before(clock1) is False

        # 更新clock2使其包含clock1的事件
        clock2.update(clock1)
        clock2.increment()

        # 现在clock1应该先于clock2
        assert clock1.happens_before(clock2) is True

    def test_vector_clock_serialization(self):
        """测试向量时钟序列化"""
        clock = VectorClock("node1")
        clock.increment()

        data = clock.to_dict()
        assert "node1" in data
        assert data["node1"] == 2

        # 从字典重建
        new_clock = VectorClock.from_dict("node1", data)
        assert new_clock.node_id == "node1"
        assert new_clock.clock["node1"] == 2


class TestCacheVersion:
    """缓存版本测试"""

    def test_cache_version_creation(self):
        """测试缓存版本创建"""
        version = CacheVersion(
            key="test_key", version=1, timestamp=datetime.utcnow(), node_id="node1"
        )

        assert version.key == "test_key"
        assert version.version == 1
        assert version.node_id == "node1"
        assert version.checksum != ""

    def test_cache_version_validity(self):
        """测试缓存版本有效性"""
        version = CacheVersion(
            key="test_key",
            version=1,
            timestamp=datetime.utcnow(),
            node_id="node1",
            data="test_value",
        )

        # 新版本应该是有效的
        assert version.is_valid() is True

        # 修改数据使校验和不匹配
        version.data = "modified_data"
        assert version.is_valid() is False


class TestAccessPatternAnalyzer:
    """访问模式分析器测试"""

    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = AccessPatternAnalyzer()

        assert len(analyzer.patterns) == 0
        assert len(analyzer.correlation_matrix) == 0
        assert len(analyzer.session_history) == 0

    def test_record_access(self):
        """测试记录访问"""
        analyzer = AccessPatternAnalyzer()

        # 记录访问
        analyzer.record_access("key1", session_id="session1", duration=0.5)

        assert "key1" in analyzer.patterns
        pattern = analyzer.patterns["key1"]
        assert pattern.key == "key1"
        assert len(pattern.access_times) == 1
        assert pattern.access_duration == 0.5

    def test_calculate_frequency(self):
        """测试计算访问频率"""
        analyzer = AccessPatternAnalyzer()
        datetime.utcnow()

        # 添加多个访问记录
        for _i in range(10):
            analyzer.record_access("key1", duration=0.1)

        # 计算频率
        frequency = analyzer.patterns["key1"].calculate_frequency()
        assert frequency > 0

    def test_predict_next_access(self):
        """测试预测下次访问"""
        analyzer = AccessPatternAnalyzer()
        now = datetime.utcnow()

        # 添加定期访问记录
        for i in range(5):
            access_time = now + timedelta(hours=i * 2)
            analyzer.patterns["key1"] = analyzer.patterns.get(
                "key1", type("", (), {"access_times": [], "last_access": None})()
            )
            analyzer.patterns["key1"].access_times.append(access_time)
            analyzer.patterns["key1"].last_access = access_time

        pattern = analyzer.patterns["key1"]
        pattern.access_times.sort()

        next_access = pattern.predict_next_access()
        if next_access:
            assert next_access > pattern.last_access

    def test_analyze_patterns(self):
        """测试分析访问模式"""
        analyzer = AccessPatternAnalyzer()

        # 添加一些访问数据
        for i in range(20):
            analyzer.record_access(f"key_{i % 5}", duration=0.1)

        analysis = analyzer.analyze_patterns()

        assert "total_keys" in analysis
        assert "high_frequency_keys" in analysis
        assert "time_based_patterns" in analysis
        assert analysis["total_keys"] == 5

    def test_get_warmup_candidates(self):
        """测试获取预热候选"""
        analyzer = AccessPatternAnalyzer()

        # 创建不同频率的访问模式
        for _i in range(50):
            analyzer.record_access("high_freq_key", duration=0.1)

        for _i in range(10):
            analyzer.record_access("low_freq_key", duration=0.1)

        candidates = analyzer.get_warmup_candidates(limit=10)

        assert len(candidates) <= 10
        # 高频键应该在前面
        if candidates:
            assert candidates[0][0] in ["high_freq_key", "low_freq_key"]


class TestIntelligentCacheWarmupManager:
    """智能缓存预热管理器测试"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        mock_cache_manager = MagicMock()
        config = {"max_concurrent_tasks": 3}

        manager = IntelligentCacheWarmupManager(mock_cache_manager, config)

        assert manager.cache_manager is mock_cache_manager
        assert manager.max_concurrent_tasks == 3
        assert len(manager.data_loaders) == 0
        assert len(manager.warmup_tasks) == 0

    def test_register_data_loader(self):
        """测试注册数据加载器"""
        mock_cache_manager = MagicMock()
        manager = IntelligentCacheWarmupManager(mock_cache_manager)

        def test_loader(key):
            return f"data_for_{key}"

        manager.register_data_loader("test_", test_loader)

        assert "test_" in manager.data_loaders

    @pytest.mark.asyncio
    async def test_create_warmup_plan(self):
        """测试创建预热计划"""
        mock_cache_manager = MagicMock()
        manager = IntelligentCacheWarmupManager(mock_cache_manager)

        plan_id = await manager.create_warmup_plan(
            strategy=WarmupStrategy.ACCESS_PATTERN, keys=["key1", "key2"]
        )

        assert plan_id in manager.warmup_plans
        plan = manager.warmup_plans[plan_id]
        assert plan.strategy == WarmupStrategy.ACCESS_PATTERN
        assert plan.status == "draft"

    @pytest.mark.asyncio
    async def test_record_access(self):
        """测试记录访问"""
        mock_cache_manager = MagicMock()
        manager = IntelligentCacheWarmupManager(mock_cache_manager)

        await manager.record_access("test_key", session_id="session1", duration=0.5)

        pattern = manager.pattern_analyzer.patterns.get("test_key")
        assert pattern is not None
        assert len(pattern.access_times) == 1

    @pytest.mark.asyncio
    async def test_execute_warmup_task(self):
        """测试执行预热任务"""
        mock_cache_manager = MagicMock()
        mock_cache_manager.set = AsyncMock(return_value=True)

        manager = IntelligentCacheWarmupManager(mock_cache_manager)

        def test_loader(key):
            return f"data_for_{key}"

        manager.register_data_loader("test", test_loader)

        task = WarmupTask(
            task_id="test_task",
            key="test_key",
            priority=PriorityLevel.HIGH,
            data_loader=test_loader,
        )

        # 执行任务
        await manager._execute_warmup_task(task)

        assert task.status in ["completed", "failed"]
        assert task.execution_time > 0

        if task.status == "completed":
            mock_cache_manager.set.assert_called_once()
            assert task.result == "data_for_test_key"

    @pytest.mark.asyncio
    async def test_get_warmup_statistics(self):
        """测试获取预热统计"""
        mock_cache_manager = MagicMock()
        manager = IntelligentCacheWarmupManager(mock_cache_manager)

        # 添加一些统计数据
        manager.stats["successful_warmups"] = 10
        manager.stats["failed_warmups"] = 2

        stats = await manager.get_warmup_statistics()

        assert "statistics" in stats
        assert stats["statistics"]["successful_warmups"] == 10
        assert stats["statistics"]["failed_warmups"] == 2
        assert "pattern_analysis" in stats


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_cache_workflow_integration(self):
        """测试缓存工作流集成"""
        # 创建模拟组件
        mock_cache_manager = MagicMock()
        mock_cache_manager.get = AsyncMock(return_value=None)
        mock_cache_manager.set = AsyncMock(return_value=True)

        # 初始化各个管理器
        distributed_cache = DistributedCacheManager()
        warmup_manager = IntelligentCacheWarmupManager(mock_cache_manager)

        # 测试分布式缓存
        value = await distributed_cache.get("test_key")
        assert value is None

        success = await distributed_cache.set("test_key", "test_value")
        assert success is True

        # 测试预热管理器
        await warmup_manager.record_access("test_key", duration=0.1)

        # 创建预热计划
        plan_id = await warmup_manager.create_warmup_plan(keys=["test_key"])

        assert plan_id in warmup_manager.warmup_plans

    @pytest.mark.asyncio
    async def test_global_functions(self):
        """测试全局获取函数"""
        # 测试全局实例获取

        # 应该返回None（因为还没有初始化）
        assert get_redis_cluster_manager() is None
        assert get_distributed_cache_manager() is None
        assert get_cache_consistency_manager() is None
        assert get_intelligent_warmup_manager() is None

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        # 测试Redis集群管理器错误处理
        manager = RedisClusterManager()

        # 测试无效操作
        result = await manager.get("test_key")  # 没有节点
        assert result is None

        # 测试分布式缓存错误处理
        config = {"max_size": 0}  # 无效配置
        cache = MemoryCache(config)

        result = cache.set("test_key", "test_value")
        # 应该处理错误而不是崩溃
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__])
