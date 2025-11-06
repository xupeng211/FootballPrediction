"""
简化的缓存集成测试
Simplified Cache Integration Tests

使用改进的Mock策略进行缓存集成测试，避免依赖真实Redis。
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.cache.redis_manager import RedisManager


@pytest.mark.integration
@pytest.mark.cache_integration
class TestSimplifiedCacheOperations:
    """简化的缓存操作集成测试"""

    @pytest.fixture
    def mock_redis(self):
        """创建模拟的Redis客户端"""
        redis_client = MagicMock()

        # 模拟基本操作
        redis_client.ping.return_value = True
        redis_client.set.return_value = True
        redis_client.get.return_value = None
        redis_client.delete.return_value = 1
        redis_client.exists.return_value = False
        redis_client.setex.return_value = True
        redis_client.expire.return_value = True

        # 模拟信息查询
        redis_client.info.return_value = {
            "used_memory": "1048576",
            "used_memory_human": "1.00M",
        }

        return redis_client

    @pytest.fixture
    async def redis_manager(self, mock_redis):
        """创建带有Mock的Redis管理器"""
        with patch(
            "src.cache.redis_enhanced.redis.async_redis.from_url",
            return_value=mock_redis,
        ):
            # 直接创建RedisManager实例
            manager = RedisManager()
            manager._redis_client = mock_redis
            return manager

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, redis_manager, mock_redis):
        """测试基本缓存操作"""
        # 设置缓存
        test_key = "test_key"
        test_value = {"data": "test_value", "timestamp": str(datetime.now())}

        # Mock设置操作
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps(test_value)

        # 设置缓存
        result = await redis_manager.set(test_key, test_value)
        assert result is True

        # 获取缓存
        cached_value = await redis_manager.get(test_key)
        assert cached_value == test_value

        # 验证调用了正确的方法
        mock_redis.set.assert_called()
        mock_redis.get.assert_called()

    @pytest.mark.asyncio
    async def test_cache_expiration(self, redis_manager, mock_redis):
        """测试缓存过期策略"""
        test_key = "expire_test_key"
        test_value = {"data": "expires_soon"}
        expire_seconds = 60

        # Mock设置过期操作
        mock_redis.setex.return_value = True

        # 设置带过期时间的缓存
        result = await redis_manager.set_with_expire(
            test_key, test_value, expire_seconds
        )
        assert result is True

        # 验证调用了setex方法
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_delete_operations(self, redis_manager, mock_redis):
        """测试缓存删除操作"""
        test_key = "delete_test_key"
        test_value = {"data": "to_delete"}

        # Mock删除操作
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.get.return_value = None

        # 先设置缓存
        await redis_manager.set(test_key, test_value)

        # 删除缓存
        result = await redis_manager.delete(test_key)
        assert result is True

        # 验证删除
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_exists_operations(self, redis_manager, mock_redis):
        """测试缓存存在性检查"""
        test_key = "exists_test_key"

        # Mock存在性检查
        mock_redis.exists.return_value = False

        # 检查不存在的键
        exists_before = await redis_manager.exists(test_key)
        assert exists_before is False

        # Mock键存在
        mock_redis.exists.return_value = True

        # 检查存在的键
        exists_after = await redis_manager.exists(test_key)
        assert exists_after is True

    @pytest.mark.asyncio
    async def test_json_serialization(self, redis_manager, mock_redis):
        """测试缓存JSON序列化和反序列化"""
        # 复杂数据结构
        complex_data = {
            "user_id": 123,
            "preferences": {"theme": "dark", "language": "zh-CN"},
            "last_login": str(datetime.now()),
            "is_active": True,
            "tags": ["football", "predictions", "data"],
        }

        # Mock JSON操作
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps(complex_data)

        # 设置复杂对象
        result = await redis_manager.set("complex_key", complex_data)
        assert result is True

        # 获取复杂对象
        retrieved_data = await redis_manager.get("complex_key")
        assert retrieved_data == complex_data

    @pytest.mark.asyncio
    async def test_error_handling(self, redis_manager, mock_redis):
        """测试错误处理"""
        # Mock连接错误
        mock_redis.set.side_effect = Exception("Redis connection error")

        # 设置缓存应该优雅地处理错误
        result = await redis_manager.set("error_test", {"data": "test"})
        assert result is False

        # Mock获取错误
        mock_redis.get.side_effect = Exception("Redis get error")
        result = await redis_manager.get("error_test")
        assert result is None

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, redis_manager, mock_redis):
        """测试内存使用监控"""
        # Mock内存使用信息
        mock_redis.info.return_value = {
            "used_memory": "2097152",  # 2MB
            "used_memory_human": "2.00M",
        }

        # 检查内存使用
        memory_info = await redis_manager.get_memory_usage()
        assert "used_memory" in memory_info
        assert memory_info["used_memory_human"] == "2.00M"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, redis_manager, mock_redis):
        """测试并发操作"""
        # Mock并发安全的操作
        mock_redis.set.return_value = True
        mock_redis.get.return_value = '{"data": "concurrent"}'

        async def cache_operation(index):
            key = f"concurrent_test_{index}"
            value = {"index": index, "thread_id": id(asyncio.current_task())}

            await redis_manager.set(key, value)
            result = await redis_manager.get(key)
            return result

        # 创建并发任务
        tasks = []
        for i in range(10):  # 减少数量以提高测试速度
            task = asyncio.create_task(cache_operation(i))
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks)

        # 验证所有操作都成功
        assert len(results) == 10
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_business_cache_scenarios(self, redis_manager, mock_redis):
        """测试业务缓存场景"""
        # 测试用户会话缓存
        user_id = "user_123"
        session_data = {
            "user_id": user_id,
            "username": "test_user",
            "login_time": str(datetime.now()),
            "permissions": ["read", "write"],
            "preferences": {"theme": "dark", "language": "zh-CN"},
        }

        # Mock会话缓存操作
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.expire.return_value = True

        # 缓存用户会话
        result = await redis_manager.cache_user_session(
            user_id, session_data, expire_seconds=3600
        )
        assert result is True

        # 获取用户会话
        cached_session = await redis_manager.get_user_session(user_id)
        assert cached_session == session_data

    @pytest.mark.asyncio
    async def test_prediction_result_caching(self, redis_manager, mock_redis):
        """测试预测结果缓存"""
        match_id = 456
        prediction_data = {
            "match_id": match_id,
            "prediction": {
                "home_win_prob": 0.65,
                "draw_prob": 0.25,
                "away_win_prob": 0.10,
                "predicted_outcome": "home",
                "confidence": 0.78,
            },
            "model_version": "v2.1",
            "created_at": str(datetime.now()),
        }

        # Mock预测缓存操作
        mock_redis.set.return_value = True
        mock_redis.get.return_value = json.dumps(prediction_data)

        # 缓存预测结果
        result = await redis_manager.cache_prediction_result(
            match_id, prediction_data, expire_seconds=600
        )
        assert result is True

        # 获取缓存的预测
        cached_prediction = await redis_manager.get_prediction_result(match_id)
        assert cached_prediction == prediction_data

    @pytest.mark.asyncio
    async def test_cache_performance(self, redis_manager, mock_redis):
        """测试缓存性能"""
        # Mock高性能操作
        mock_redis.set.return_value = True
        mock_redis.get.return_value = '{"data": "cached"}'

        import time

        operations = 50  # 减少数量以提高测试速度
        start_time = time.time()

        # 批量设置操作
        for i in range(operations):
            key = f"perf_test_{i}"
            value = {"index": i, "data": f"test_data_{i}"}
            await redis_manager.set(key, value)

        set_time = time.time() - start_time

        # 设置操作应该在0.5秒内完成
        assert set_time < 0.5

        # 测试获取性能
        start_time = time.time()

        for i in range(operations):
            key = f"perf_test_{i}"
            await redis_manager.get(key)

        get_time = time.time() - start_time

        # 获取操作应该在0.3秒内完成
        assert get_time < 0.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
