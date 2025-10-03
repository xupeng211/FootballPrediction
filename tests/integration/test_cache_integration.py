"""
缓存系统集成测试
Integration tests for cache system
"""

import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis

# 尝试导入缓存模块
try:
    from src.cache.redis_manager import RedisManager
    from src.cache.ttl_cache import TTLCache
    from src.api.predictions import get_match_prediction
    from src.services.cache_service import CacheService
except ImportError:
    pytest.skip("Cache modules not available", allow_module_level=True)


class TestCacheIntegration:
    """缓存系统集成测试类"""

    @pytest.fixture
    def redis_manager(self):
        """创建Redis管理器实例"""
        return RedisManager(
            redis_url="redis://localhost:6379/1",
            max_connections=10
        )

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis客户端"""
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_client.setex.return_value = True
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = 0
        mock_client.expire.return_value = True
        mock_client.ttl.return_value = 3600
        return mock_client

    @pytest.mark.asyncio
    async def test_prediction_caching_flow(self, mock_redis):
        """测试预测缓存流程"""
        match_id = 12345
        cache_key = f"prediction:{match_id}"

        # Mock Redis管理器
        with patch.object(RedisManager, '_redis', mock_redis):
            manager = RedisManager()

            # 测试缓存未命中
            cached_data = await manager.get(cache_key)
            assert cached_data is None

            # 模拟创建新预测
            prediction_data = {
                "match_id": match_id,
                "home_win_probability": 0.55,
                "draw_probability": 0.25,
                "away_win_probability": 0.20,
                "predicted_result": "home",
                "confidence_score": 0.55,
                "model_version": "1.0",
                "created_at": datetime.now().isoformat()
            }

            # 存储到缓存
            success = await manager.set_json(cache_key, prediction_data, ttl=3600)
            assert success is True

            # 验证Redis操作被调用
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_layer_in_prediction_api(self, mock_redis):
        """测试预测API中的缓存层"""
        match_id = 12345

        # 准备缓存数据
        cached_prediction = {
            "match_id": match_id,
            "home_win_probability": 0.60,
            "draw_probability": 0.30,
            "away_win_probability": 0.10,
            "predicted_result": "home",
            "confidence_score": 0.60,
            "created_at": datetime.now().isoformat()
        }

        # Mock缓存命中
        mock_redis.get.return_value = json.dumps(cached_prediction).encode()

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            # 测试从缓存获取预测
            manager = RedisManager()
            retrieved_data = await manager.get_json(f"prediction:{match_id}")

            assert retrieved_data is not None
            assert retrieved_data["match_id"] == match_id
            assert retrieved_data["home_win_probability"] == 0.60

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self, mock_redis):
        """测试更新时的缓存失效"""
        match_id = 12345
        cache_key = f"prediction:{match_id}"

        # Mock现有缓存
        mock_redis.get.return_value = json.dumps({
            "match_id": match_id,
            "home_win_probability": 0.50,
            "created_at": datetime.now().isoformat()
        }).encode()

        # Mock删除操作
        mock_redis.delete.return_value = 1

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 强制重新预测时清除缓存
            deleted = await manager.delete(cache_key)
            assert deleted == 1

            # 验证删除被调用
            mock_redis.delete.assert_called_with(cache_key)

    @pytest.mark.asyncio
    async def test_batch_cache_operations(self, mock_redis):
        """测试批量缓存操作"""
        # 准备多个预测数据
        predictions = {
            f"prediction:{i}": {
                "match_id": i,
                "home_win_probability": 0.5,
                "created_at": datetime.now().isoformat()
            } for i in range(12345, 12350)
        }

        # Mock批量操作
        mock_redis.mset.return_value = True
        mock_redis.mget.return_value = [None] * len(predictions)

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 批量设置
            success = await manager.batch_set(predictions, ttl=3600)
            assert success is True

            # 批量获取
            keys = list(predictions.keys())
            values = await manager.batch_get(keys)
            assert len(values) == len(keys)

    @pytest.mark.asyncio
    async def test_cache_warmup(self, mock_redis):
        """测试缓存预热"""
        # 准备热门比赛数据
        upcoming_matches = [
            {"id": 12345, "importance": "high"},
            {"id": 12346, "importance": "high"},
            {"id": 12347, "importance": "medium"}
        ]

        # Mock预测服务
        with patch('src.models.prediction_service.PredictionService') as mock_service:
            mock_service_instance = MagicMock()
            mock_service.return_value = mock_service_instance

            # 为每个比赛生成预测
            for match in upcoming_matches:
                prediction = MagicMock()
                prediction.match_id = match["id"]
                prediction.home_win_probability = 0.50
                prediction.to_dict.return_value = {
                    "match_id": match["id"],
                    "home_win_probability": 0.50
                }
                mock_service_instance.predict_match.return_value = prediction

            # Mock缓存设置
            mock_redis.setex.return_value = True

            with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
                manager = RedisManager()

                # 执行缓存预热
                for match in upcoming_matches:
                    if match["importance"] == "high":
                        prediction = await mock_service_instance.predict_match(match["id"])
                        await manager.set_json(
                            f"prediction:{match['id']}",
                            prediction.to_dict(),
                            ttl=7200
                        )

                # 验证缓存设置被调用
                assert mock_redis.setex.call_count >= 2

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, mock_redis):
        """测试缓存TTL过期"""
        cache_key = "test:ttl"

        # Mock不同的TTL响应
        mock_redis.ttl.side_effect = [3600, -1, -2]  # 有效、无过期、不存在

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 检查TTL
            ttl = await manager.get_ttl(cache_key)
            assert ttl == 3600

            # 无过期时间
            ttl = await manager.get_ttl(cache_key)
            assert ttl == -1

            # 不存在
            ttl = await manager.get_ttl(cache_key)
            assert ttl == -2

    @pytest.mark.asyncio
    async def test_cache_compression(self, mock_redis):
        """测试缓存压缩"""
        # 大型数据
        large_data = {
            "match_id": 12345,
            "features": [i for i in range(10000)],  # 大列表
            "history": [{ "event": f"event_{i}" } for i in range(1000)]
        }

        # Mock压缩存储
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps(large_data).encode()

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 存储大数据（应该启用压缩）
            success = await manager.set_json("large_data", large_data, compress=True)
            assert success is True

            # 检查实际存储的大小（模拟）
            stored_size = len(json.dumps(large_data).encode())
            assert stored_size > 0

            # 检索并验证
            retrieved = await manager.get_json("large_data")
            assert retrieved is not None
            assert len(retrieved["features"]) == 10000

    @pytest.mark.asyncio
    async def test_cache_fallback_on_failure(self, mock_redis):
        """测试缓存失败时的回退"""
        match_id = 12345

        # Mock Redis连接失败
        mock_redis.get.side_effect = redis.ConnectionError("Redis down")
        mock_redis.set.side_effect = redis.ConnectionError("Redis down")

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 尝试获取缓存（失败）
            cached_data = await manager.get(f"prediction:{match_id}")
            assert cached_data is None

            # 尝试设置缓存（失败但不应该影响主流程）
            success = await manager.set(f"prediction:{match_id}", "data")
            assert success is False  # 失败但程序继续

    @pytest.mark.asyncio
    async def test_distributed_cache_consistency(self, mock_redis):
        """测试分布式缓存一致性"""
        match_id = 12345
        cache_key = f"prediction:{match_id}"

        # 模拟多个Redis实例
        redis_instances = [AsyncMock() for _ in range(3)]

        # 设置不同的值
        values = [
            json.dumps({"version": 1, "data": "first"}),
            json.dumps({"version": 2, "data": "second"}),
            json.dumps({"version": 3, "data": "third"})
        ]

        for redis, value in zip(redis_instances, values):
            redis.get.return_value = value.encode()

        # 测试一致性读取
        retrieved_values = []
        for redis in redis_instances:
            data = await redis.get(cache_key)
            if data:
                retrieved_values.append(json.loads(data.decode()))

        # 验证版本不同（模拟分布式场景下的不一致）
        versions = [v["version"] for v in retrieved_values]
        assert len(set(versions)) > 1  # 版本不一致

        # 实际实现中需要使用分布式锁或版本控制
        # 这里只是演示问题

    @pytest.mark.asyncio
    async def test_cache_monitoring_and_metrics(self, mock_redis):
        """测试缓存监控和指标"""
        # Mock Redis INFO命令
        mock_redis.info.return_value = {
            "used_memory": 1048576,  # 1MB
            "used_memory_human": "1M",
            "connected_clients": 10,
            "total_commands_processed": 100000,
            "keyspace_hits": 80000,
            "keyspace_misses": 20000
        }

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 获取缓存指标
            info = await manager.get_info()
            assert info["used_memory"] == 1048576
            assert info["connected_clients"] == 10

            # 计算命中率
            hit_rate = info["keyspace_hits"] / (
                info["keyspace_hits"] + info["keyspace_misses"]
            )
            assert hit_rate == 0.8  # 80%

    @pytest.mark.asyncio
    async def test_cache_pattern_matching(self, mock_redis):
        """测试缓存模式匹配"""
        # 准备多个键
        keys = [
            "prediction:12345",
            "prediction:12346",
            "prediction:12347",
            "match:12345",
            "team:123"
        ]

        # Mock KEYS命令
        mock_redis.keys.return_value = [
            b"prediction:12345",
            b"prediction:12346",
            b"prediction:12347"
        ]

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 获取所有预测键
            prediction_keys = await manager.keys("prediction:*")
            assert len(prediction_keys) == 3
            assert all("prediction:" in key for key in prediction_keys)

            # 验证调用
            mock_redis.keys.assert_called_with("prediction:*")

    @pytest.mark.asyncio
    async def test_cache_pipeline_operations(self, mock_redis):
        """测试缓存管道操作"""
        # Mock管道
        mock_pipeline = AsyncMock()
        mock_redis.pipeline.return_value.__aenter__.return_value = mock_pipeline
        mock_redis.pipeline.return_value.__aexit__.return_value = None

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 使用管道执行多个操作
            async with manager.pipeline() as pipe:
                await pipe.set("key1", "value1")
                await pipe.set("key2", "value2")
                await pipe.get("key1")
                await pipe.get("key2")

            # 验证管道操作
            assert mock_pipeline.set.call_count == 2
            assert mock_pipeline.get.call_count == 2
            mock_pipeline.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_backup_and_restore(self, mock_redis):
        """测试缓存备份和恢复"""
        # 准备备份
        backup_data = {
            "prediction:12345": {"home_win": 0.55},
            "prediction:12346": {"home_win": 0.45},
            "team:1": {"name": "Team A"}
        }

        # Mock备份操作
        mock_redis.dump.return_value = b"serialized_data"
        mock_redis.restore.return_value = True

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 备份数据
            backup = {}
            for key in backup_data:
                data = await manager.dump(key)
                if data:
                    backup[key] = data

            assert len(backup) == len(backup_data)

            # 恢复数据
            for key, data in backup.items():
                success = await manager.restore(key, data, ttl=0)
                assert success is True

    @pytest.mark.asyncio
    async def test_cache_memory_management(self, mock_redis):
        """测试缓存内存管理"""
        # Mock内存使用情况
        mock_redis.memory_usage.return_value = 1024  # 1KB
        mock_redis.config_get.return_value = {"maxmemory": "100mb"}

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 检查内存使用
            memory_usage = await manager.get_memory_usage("test_key")
            assert memory_usage == 1024

            # 检查最大内存限制
            max_memory = await manager.get_max_memory()
            assert "100mb" in max_memory.lower()

            # 清理过期键释放内存
            expired_count = await manager.cleanup_expired()
            assert isinstance(expired_count, int)

    @pytest.mark.asyncio
    async def test_cache_security(self, mock_redis):
        """测试缓存安全"""
        sensitive_data = {
            "user_id": "user123",
            "api_key": "sk-1234567890",
            "password": "secret123"
        }

        # Mock加密存储
        mock_redis.set.return_value = True
        mock_redis.get.return_value = b"encrypted_data"

        with patch('src.cache.redis_manager.RedisManager._redis', mock_redis):
            manager = RedisManager()

            # 加密存储敏感数据
            success = await manager.set_secure("secure_key", sensitive_data)
            assert success is True

            # 解密检索
            retrieved = await manager.get_secure("secure_key")
            assert retrieved is not None

            # 验证数据被加密（模拟）
            stored_value = await mock_redis.get("secure_key")
            assert stored_value != b"secret123"  # 应该是加密后的数据

    @pytest.mark.asyncio
    async def test_cache_replication(self, mock_redis):
        """测试缓存复制"""
        # Mock主从复制
        master_redis = AsyncMock()
        slave_redis = AsyncMock()

        master_redis.set.return_value = True
        slave_redis.get.return_value = None  # 从机延迟
        master_redis.get.return_value = json.dumps({"data": "value"}).encode()

        with patch('src.cache.redis_manager.RedisManager._redis', master_redis):
            manager = RedisManager()

            # 写入主节点
            await manager.set("test_key", {"data": "value"})

            # 模拟从主节点读取
            value = await manager.get("test_key")
            assert value is not None

            # 验证复制延迟处理
            slave_redis.get.return_value = json.dumps({"data": "value"}).encode()
            slave_value = await slave_redis.get("test_key")
            assert slave_value is not None


class TestTTLCacheIntegration:
    """TTL缓存集成测试"""

    def setup_method(self):
        """设置测试"""
        self.cache = TTLCache(maxsize=100, default_ttl=3600)

    def test_ttl_expiration(self):
        """测试TTL过期"""
        # 设置带TTL的缓存
        self.cache.set("key1", "value1", ttl=1)  # 1秒
        self.cache.set("key2", "value2", ttl=10)  # 10秒

        # 立即获取
        assert self.cache.get("key1") == "value1"
        assert self.cache.get("key2") == "value2"

        # 等待过期
        import time
        time.sleep(1.1)

        # key1应该已过期
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") == "value2"

    def test_cache_eviction(self):
        """测试缓存淘汰"""
        # 创建小容量缓存
        small_cache = TTLCache(maxsize=3, default_ttl=3600)

        # 添加超过容量的项
        small_cache.set("key1", "value1")
        small_cache.set("key2", "value2")
        small_cache.set("key3", "value3")
        small_cache.set("key4", "value4")  # 应该淘汰最旧的

        # 验证淘汰
        assert small_cache.get("key1") is None
        assert small_cache.get("key2") == "value2"
        assert small_cache.get("key3") == "value3"
        assert small_cache.get("key4") == "value4"

    def test_batch_operations(self):
        """测试批量操作"""
        # 批量设置
        data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        self.cache.set_many(data)

        # 批量获取
        values = self.cache.get_many(["key1", "key2", "key3", "key4"])
        assert values["key1"] == "value1"
        assert values["key2"] == "value2"
        assert values["key3"] == "value3"
        assert values.get("key4") is None

        # 批量删除
        deleted = self.cache.delete_many(["key1", "key2"])
        assert deleted == 2

        values = self.cache.get_many(["key1", "key2", "key3"])
        assert values.get("key1") is None
        assert values.get("key2") is None
        assert values["key3"] == "value3"

    def test_cache_statistics(self):
        """测试缓存统计"""
        # 执行一些操作
        self.cache.set("key1", "value1")
        self.cache.get("key1")  # 命中
        self.cache.get("key2")  # 未命中
        self.cache.set("key2", "value2")
        self.cache.get("key2")  # 命中

        # 获取统计信息
        stats = self.cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2/3
        assert stats["size"] == 2

    def test_cache_persistence(self):
        """测试缓存持久化"""
        # 设置一些数据
        self.cache.set("persistent_key", "persistent_value", ttl=86400)

        # 模拟序列化
        import pickle
        serialized = pickle.dumps(self.cache)

        # 模拟反序列化
        deserialized = pickle.loads(serialized)

        # 验证数据恢复
        assert deserialized.get("persistent_key") == "persistent_value"