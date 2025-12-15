"""
Unit Tests for Prediction Cache
预测缓存单元测试

测试Redis缓存的各项功能，包括缓存存储、检索、TTL管理和统计。
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.inference.cache import PredictionCache, get_prediction_cache
from src.inference.schemas import PredictionRequest, PredictionResponse
from src.inference.errors import CacheError


class TestPredictionCache:
    """预测缓存测试类"""

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.setex.return_value = True
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = 0
        mock_client.keys.return_value = []
        return mock_client

    @pytest.fixture
    def cache_instance(self, mock_redis_client):
        """缓存实例fixture"""
        with patch('src.inference.cache.redis.from_url', return_value=mock_redis_client):
            cache = PredictionCache(
                redis_url="redis://localhost:6379/0",
                default_ttl=3600,
                key_prefix="test_prediction"
            )
            return cache

    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_instance):
        """测试缓存初始化"""
        assert cache_instance.default_ttl == 3600
        assert cache_instance.key_prefix == "test_prediction"
        assert cache_instance._client is not None

    @pytest.mark.asyncio
    async def test_generate_cache_key(self, cache_instance):
        """测试缓存键生成"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability",
            features={"home_goals": 2, "away_goals": 1}
        )

        cache_key = cache_instance._generate_cache_key(request)

        expected_parts = [
            "test_prediction",
            "prediction",
            "match_123",
            "xgboost_v1",
            "latest",
            "probability"
        ]

        for part in expected_parts:
            assert part in cache_key

        # 验证特征哈希包含在内
        assert len(cache_key.split(':')) >= len(expected_parts) + 1

    @pytest.mark.asyncio
    async def test_set_prediction_success(self, cache_instance):
        """测试设置预测缓存成功"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        prediction_data = {
            "home_win_prob": 0.65,
            "draw_prob": 0.25,
            "away_win_prob": 0.10,
            "predicted_outcome": "home_win",
            "confidence": 0.75,
            "model_name": "xgboost_v1",
            "model_version": "1.0.0"
        }

        # 测试设置缓存
        await cache_instance.set_prediction(request, prediction_data)

        # 验证Redis客户端被调用
        cache_instance._client.setex.assert_called_once()

        # 验证调用参数
        call_args = cache_instance._client.setex.call_args
        call_args[0][0]
        ttl = call_args[0][1]
        stored_data = json.loads(call_args[0][2])

        assert ttl == 3600  # 默认TTL
        assert stored_data["home_win_prob"] == 0.65
        assert stored_data["match_id"] == "match_123"

    @pytest.mark.asyncio
    async def test_set_prediction_with_custom_ttl(self, cache_instance):
        """测试使用自定义TTL设置缓存"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        prediction_data = {
            "home_win_prob": 0.65,
            "draw_prob": 0.25,
            "away_win_prob": 0.10
        }

        # 使用自定义TTL
        custom_ttl = 7200
        await cache_instance.set_prediction(request, prediction_data, ttl=custom_ttl)

        # 验证使用了自定义TTL
        call_args = cache_instance._client.setex.call_args
        assert call_args[0][1] == custom_ttl

    @pytest.mark.asyncio
    async def test_get_prediction_cache_hit(self, cache_instance):
        """测试缓存命中"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        cached_data = {
            "home_win_prob": 0.65,
            "draw_prob": 0.25,
            "away_win_prob": 0.10,
            "predicted_outcome": "home_win",
            "confidence": 0.75,
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "cached_at": datetime.utcnow().isoformat()
        }

        # 模拟Redis返回缓存数据
        cache_instance._client.get.return_value = json.dumps(cached_data)

        result = await cache_instance.get_prediction(request)

        assert result is not None
        assert result["home_win_prob"] == 0.65
        assert result["predicted_outcome"] == "home_win"
        assert "cached_at" in result

    @pytest.mark.asyncio
    async def test_get_prediction_cache_miss(self, cache_instance):
        """测试缓存未命中"""
        request = PredictionRequest(
            match_id="match_456",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        # 模拟Redis返回None
        cache_instance._client.get.return_value = None

        result = await cache_instance.get_prediction(request)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prediction_invalid_json(self, cache_instance):
        """测试获取损坏的JSON数据"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        # 模拟Redis返回损坏的JSON
        cache_instance._client.get.return_value = "invalid json"

        result = await cache_instance.get_prediction(request)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_prediction_success(self, cache_instance):
        """测试删除预测缓存成功"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        # 模拟删除成功
        cache_instance._client.delete.return_value = 1

        result = await cache_instance.delete_prediction(request)

        assert result is True
        cache_instance._client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_prediction_not_found(self, cache_instance):
        """测试删除不存在的缓存"""
        request = PredictionRequest(
            match_id="match_789",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        # 模拟删除失败（键不存在）
        cache_instance._client.delete.return_value = 0

        result = await cache_instance.delete_prediction(request)

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_cache_with_pattern(self, cache_instance):
        """测试按模式清除缓存"""
        pattern = "match_*"

        # 模拟存在匹配的键
        cache_instance._client.keys.return_value = [
            "test_prediction:prediction:match_123:xgboost_v1:latest:probability",
            "test_prediction:prediction:match_456:xgboost_v1:latest:probability"
        ]
        cache_instance._client.delete.return_value = 2

        deleted_count = await cache_instance.clear_cache(pattern)

        assert deleted_count == 2
        cache_instance._client.keys.assert_called_once()
        cache_instance._client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_instance):
        """测试获取缓存统计"""
        # 模拟Redis info命令
        cache_instance._client.info.return_value = {
            "keyspace_hits": 100,
            "keyspace_misses": 50,
            "used_memory": 1048576,  # 1MB
            "used_memory_human": "1M"
        }

        stats = await cache_instance.get_cache_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "memory_usage" in stats
        assert stats["hits"] == 100
        assert stats["misses"] == 50
        assert stats["hit_rate"] == 100 / (100 + 50) * 100

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, cache_instance):
        """测试健康检查 - 健康"""
        # 模拟Redis ping成功
        cache_instance._client.ping.return_value = True

        health = await cache_instance.health_check()

        assert health["status"] == "healthy"
        assert health["redis_connected"] is True
        assert "response_time_ms" in health

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, cache_instance):
        """测试健康检查 - 不健康"""
        # 模拟Redis ping失败
        cache_instance._client.ping.side_effect = Exception("Redis connection failed")

        health = await cache_instance.health_check()

        assert health["status"] == "unhealthy"
        assert health["redis_connected"] is False
        assert "error" in health

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, cache_instance):
        """测试缓存错误处理"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        # 模拟Redis连接错误
        cache_instance._client.setex.side_effect = Exception("Redis connection error")

        with pytest.raises(CacheError) as exc_info:
            await cache_instance.set_prediction(request, {})

        assert "Failed to set prediction cache" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_batch_cache_operations(self, cache_instance):
        """测试批量缓存操作"""
        requests = [
            PredictionRequest(
                match_id=f"match_{i}",
                model_name="xgboost_v1",
                prediction_type="probability"
            )
            for i in range(3)
        ]

        predictions_data = [
            {
                "home_win_prob": 0.6 + i * 0.1,
                "draw_prob": 0.3,
                "away_win_prob": 0.1 - i * 0.05,
                "predicted_outcome": "home_win"
            }
            for i in range(3)
        ]

        # 批量设置
        results = await cache_instance.set_predictions_batch(requests, predictions_data)

        assert results["successful"] == 3
        assert results["failed"] == 0
        assert cache_instance._client.setex.call_count == 3

    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_instance):
        """测试缓存预热"""
        warmup_data = [
            {
                "request": PredictionRequest(
                    match_id="match_123",
                    model_name="xgboost_v1",
                    prediction_type="probability"
                ),
                "prediction": {
                    "home_win_prob": 0.65,
                    "draw_prob": 0.25,
                    "away_win_prob": 0.10
                }
            }
        ]

        results = await cache_instance.warm_cache(warmup_data)

        assert results["warmed"] == 1
        assert results["failed"] == 0
        cache_instance._client.setex.assert_called_once()

    def test_cache_key_uniqueness(self, cache_instance):
        """测试缓存键唯一性"""
        request1 = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        request2 = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v2",
            prediction_type="probability"
        )

        key1 = cache_instance._generate_cache_key(request1)
        key2 = cache_instance._generate_cache_key(request2)

        assert key1 != key2
        assert "xgboost_v1" in key1
        assert "xgboost_v2" in key2

    def test_cache_key_with_features(self, cache_instance):
        """测试包含特征的缓存键"""
        request1 = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability",
            features={"home_goals": 2}
        )

        request2 = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability",
            features={"home_goals": 3}
        )

        key1 = cache_instance._generate_cache_key(request1)
        key2 = cache_instance._generate_cache_key(request2)

        assert key1 != key2  # 不同的特征应该产生不同的键

    @pytest.mark.asyncio
    async def test_get_prediction_cache_singleton(self):
        """测试全局缓存实例"""
        with patch('src.inference.cache.redis.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            # 获取缓存实例
            cache1 = await get_prediction_cache()
            cache2 = await get_prediction_cache()

            # 应该返回同一个实例
            assert cache1 is cache2

    @pytest.mark.asyncio
    async def test_cache_cleanup(self, cache_instance):
        """测试缓存清理"""
        # 执行清理
        await cache_instance.cleanup()

        # 验证Redis客户端关闭被调用（如果实现了的话）
        # 这里只是测试清理方法不会抛出异常
        assert True
