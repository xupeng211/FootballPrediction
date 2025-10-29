#!/usr/bin/env python3
"""
预测模型测试
测试 src.models.prediction 模块的功能
"""

from datetime import datetime

import pytest

from src.models.prediction import PredictionCache, PredictionResult


@pytest.mark.unit
class TestPredictionResult:
    """预测结果数据类测试"""

    def test_prediction_result_creation_with_minimal_data(self):
        """测试使用最小数据创建预测结果"""
        result = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=datetime(2024, 1, 1, 12, 0, 0),
            model_version="v1.0",
        )

        assert result.match_id == 123
        assert result.predicted_result == "home_win"
        assert result.confidence == 0.75
        assert result.prediction_time == datetime(2024, 1, 1, 12, 0, 0)
        assert result.model_version == "v1.0"
        assert result.features == {}  # 应该被初始化为空字典

    def test_prediction_result_creation_with_features(self):
        """测试创建包含特征的预测结果"""
        features = {"team_strength": 0.8, "home_advantage": 0.1}
        result = PredictionResult(
            match_id=456,
            predicted_result="draw",
            confidence=0.60,
            prediction_time=datetime(2024, 1, 1, 15, 30, 0),
            model_version="v1.1",
            features=features,
        )

        assert result.features == features
        assert result.match_id == 456
        assert result.predicted_result == "draw"

    def test_prediction_result_confidence_bounds(self):
        """测试预测置信度边界值"""
        # 测试有效置信度
        result_valid = PredictionResult(
            match_id=1,
            predicted_result="home_win",
            confidence=0.85,
            prediction_time=datetime.now(),
            model_version="v1.0",
        )
        assert 0 <= result_valid.confidence <= 1

        # 测试边界值
        result_zero = PredictionResult(
            match_id=2,
            predicted_result="away_win",
            confidence=0.0,
            prediction_time=datetime.now(),
            model_version="v1.0",
        )
        assert result_zero.confidence == 0.0

        result_one = PredictionResult(
            match_id=3,
            predicted_result="draw",
            confidence=1.0,
            prediction_time=datetime.now(),
            model_version="v1.0",
        )
        assert result_one.confidence == 1.0

    def test_prediction_result_different_results(self):
        """测试不同的预测结果类型"""
        results = ["home_win", "away_win", "draw"]

        for i, predicted_result in enumerate(results):
            result = PredictionResult(
                match_id=i,
                predicted_result=predicted_result,
                confidence=0.7,
                prediction_time=datetime.now(),
                model_version="v1.0",
            )
            assert result.predicted_result == predicted_result

    def test_prediction_result_equality(self):
        """测试预测结果的相等性比较"""
        prediction_time = datetime(2024, 1, 1, 12, 0, 0)

        result1 = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=prediction_time,
            model_version="v1.0",
        )

        result2 = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=prediction_time,
            model_version="v1.0",
        )

        # dataclass 应该支持相等性比较
        assert result1 == result2


@pytest.mark.unit
class TestPredictionCache:
    """预测缓存管理器测试"""

    def test_cache_initialization(self):
        """测试缓存初始化"""
        cache = PredictionCache()
        assert cache._cache == {}

    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache = PredictionCache()
        result = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=datetime.now(),
            model_version="v1.0",
        )

        # 设置缓存
        cache.set("match_123", result)

        # 获取缓存
        cached_result = cache.get("match_123")
        assert cached_result == result
        assert cached_result.match_id == 123
        assert cached_result.predicted_result == "home_win"

    def test_cache_get_nonexistent(self):
        """测试获取不存在的缓存项"""
        cache = PredictionCache()
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_set_with_ttl(self):
        """测试设置带TTL的缓存项"""
        cache = PredictionCache()
        result = PredictionResult(
            match_id=456,
            predicted_result="draw",
            confidence=0.60,
            prediction_time=datetime.now(),
            model_version="v1.1",
        )

        # 设置缓存（虽然当前实现没有真正使用TTL）
        cache.set("match_456", result, ttl=1800)

        cached_result = cache.get("match_456")
        assert cached_result == result

    def test_cache_clear(self):
        """测试清空缓存"""
        cache = PredictionCache()

        # 添加多个缓存项
        result1 = PredictionResult(
            match_id=1,
            predicted_result="home_win",
            confidence=0.8,
            prediction_time=datetime.now(),
            model_version="v1.0",
        )
        result2 = PredictionResult(
            match_id=2,
            predicted_result="away_win",
            confidence=0.6,
            prediction_time=datetime.now(),
            model_version="v1.0",
        )

        cache.set("match_1", result1)
        cache.set("match_2", result2)

        assert len(cache._cache) == 2

        # 清空缓存
        cache.clear()
        assert len(cache._cache) == 0
        assert cache.get("match_1") is None
        assert cache.get("match_2") is None

    def test_cache_overwrite(self):
        """测试覆盖已存在的缓存项"""
        cache = PredictionCache()

        result1 = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=datetime.now(),
            model_version="v1.0",
        )
        result2 = PredictionResult(
            match_id=123,
            predicted_result="draw",
            confidence=0.60,
            prediction_time=datetime.now(),
            model_version="v1.1",
        )

        # 设置第一个结果
        cache.set("match_123", result1)
        assert cache.get("match_123").predicted_result == "home_win"

        # 覆盖为第二个结果
        cache.set("match_123", result2)
        assert cache.get("match_123").predicted_result == "draw"
        assert cache.get("match_123").confidence == 0.60

    def test_cache_multiple_items(self):
        """测试缓存多个不同项目"""
        cache = PredictionCache()

        results = [
            ("match_1", PredictionResult(1, "home_win", 0.8, datetime.now(), "v1.0")),
            ("match_2", PredictionResult(2, "away_win", 0.6, datetime.now(), "v1.0")),
            ("match_3", PredictionResult(3, "draw", 0.5, datetime.now(), "v1.1")),
        ]

        # 设置多个缓存项
        for key, result in results:
            cache.set(key, result)

        # 验证所有项目都被正确缓存
        for key, original_result in results:
            cached_result = cache.get(key)
            assert cached_result == original_result
            assert cached_result.match_id == original_result.match_id

    def test_cache_key_types(self):
        """测试不同类型的缓存键"""
        cache = PredictionCache()
        result = PredictionResult(
            match_id=999,
            predicted_result="home_win",
            confidence=0.9,
            prediction_time=datetime.now(),
            model_version="v1.0",
        )

        # 测试字符串键
        cache.set("string_key", result)
        assert cache.get("string_key") == result

        # 测试数字键
        cache.set(123, result)
        assert cache.get(123) == result

        # 测试复合键
        cache.set("match_123_team_456", result)
        assert cache.get("match_123_team_456") == result
