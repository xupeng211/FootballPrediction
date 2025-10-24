"""
预测模块测试
Prediction Module Tests

测试src/models/prediction.py中定义的预测功能，专注于实现100%覆盖率。
Tests prediction functionality defined in src/models/prediction.py, focused on achieving 100% coverage.
"""

import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

# 导入要测试的模块
try:
    from src.models.prediction import (
        PredictionResult,
        PredictionCache,
        PredictionService,
        # 监控指标类
        Counter,
        Histogram,
        Gauge,
        # 监控指标实例
        predictions_total,
        prediction_duration_seconds,
        prediction_accuracy,
        model_load_duration_seconds,
        cache_hit_ratio,
    )
    PREDICTION_AVAILABLE = True
except ImportError:
    PREDICTION_AVAILABLE = False


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestPredictionResult:
    """PredictionResult测试"""

    def test_prediction_result_dataclass(self):
        """测试PredictionResult dataclass"""
        # 验证它是一个dataclass
        import dataclasses
        assert dataclasses.is_dataclass(PredictionResult)

    def test_prediction_result_class_exists(self):
        """测试PredictionResult类存在"""
        assert PredictionResult is not None
        assert callable(PredictionResult)

    def test_prediction_result_instantiation_full(self):
        """测试PredictionResult完整实例化"""
        prediction_time = datetime.datetime(2023, 12, 1, 20, 0, 0)
        features = {"team_strength": 0.85, "form_index": 0.72}

        result = PredictionResult(
            match_id=12345,
            predicted_result="home_win",
            confidence=0.85,
            prediction_time=prediction_time,
            model_version="v2.1.0",
            features=features
        )

        assert result.match_id == 12345
        assert result.predicted_result == "home_win"
        assert result.confidence == 0.85
        assert result.prediction_time == prediction_time
        assert result.model_version == "v2.1.0"
        assert result.features == features

    def test_prediction_result_instantiation_minimal(self):
        """测试PredictionResult最小实例化"""
        prediction_time = datetime.datetime.utcnow()

        result = PredictionResult(
            match_id=67890,
            predicted_result="draw",
            confidence=0.60,
            prediction_time=prediction_time,
            model_version="v1.0.0"
        )

        assert result.match_id == 67890
        assert result.predicted_result == "draw"
        assert result.confidence == 0.60
        assert result.prediction_time == prediction_time
        assert result.model_version == "v1.0.0"
        # features应该自动初始化为空字典
        assert result.features == {}

    def test_prediction_result_post_init(self):
        """测试PredictionResult的__post_init__方法"""
        # 不提供features，应该自动设置为空字典
        result1 = PredictionResult(
            match_id=1,
            predicted_result="away_win",
            confidence=0.70,
            prediction_time=datetime.datetime.utcnow(),
            model_version="v1.0.0"
        )
        assert result1.features == {}

        # 显式提供features=None，也应该自动设置为空字典
        result2 = PredictionResult(
            match_id=2,
            predicted_result="home_win",
            confidence=0.80,
            prediction_time=datetime.datetime.utcnow(),
            model_version="v1.0.0",
            features=None
        )
        assert result2.features == {}

        # 提供非空features，应该保持不变
        custom_features = {"test": "value"}
        result3 = PredictionResult(
            match_id=3,
            predicted_result="draw",
            confidence=0.50,
            prediction_time=datetime.datetime.utcnow(),
            model_version="v1.0.0",
            features=custom_features
        )
        assert result3.features == custom_features

    def test_prediction_result_field_types(self):
        """测试PredictionResult字段类型"""
        result = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=datetime.datetime.utcnow(),
            model_version="v1.0.0"
        )

        assert isinstance(result.match_id, int)
        assert isinstance(result.predicted_result, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.prediction_time, datetime.datetime)
        assert isinstance(result.model_version, str)
        assert isinstance(result.features, dict)

    def test_prediction_result_different_results(self):
        """测试不同类型的预测结果"""
        base_time = datetime.datetime.utcnow()

        results = [
            ("home_win", 0.85),
            ("away_win", 0.70),
            ("draw", 0.60),
        ]

        for predicted_result, confidence in results:
            result = PredictionResult(
                match_id=100 + len([r for r in results if r[0] == predicted_result]),
                predicted_result=predicted_result,
                confidence=confidence,
                prediction_time=base_time,
                model_version="v1.0.0"
            )
            assert result.predicted_result == predicted_result
            assert result.confidence == confidence

    def test_prediction_result_complex_features(self):
        """测试复杂的features结构"""
        complex_features = {
            "home_team": {
                "rating": 85.5,
                "form": [1, 0, 1, 1, 0],
                "injuries": 2
            },
            "away_team": {
                "rating": 78.2,
                "form": [0, 1, 0, 0, 1],
                "injuries": 1
            },
            "match_conditions": {
                "venue": "home",
                "weather": "sunny",
                "temperature": 22.5
            }
        }

        result = PredictionResult(
            match_id=999,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=datetime.datetime.utcnow(),
            model_version="v3.0.0",
            features=complex_features
        )

        assert result.features == complex_features
        assert result.features["home_team"]["rating"] == 85.5


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestPredictionCache:
    """PredictionCache测试"""

    def test_prediction_cache_class_exists(self):
        """测试PredictionCache类存在"""
        assert PredictionCache is not None
        assert callable(PredictionCache)

    def test_prediction_cache_instantiation(self):
        """测试PredictionCache实例化"""
        cache = PredictionCache()
        assert cache._cache == {}

    def test_prediction_cache_set_and_get(self):
        """测试PredictionCache设置和获取"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        # 创建一个预测结果
        result = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.80,
            prediction_time=prediction_time,
            model_version="v1.0.0"
        )

        # 设置缓存
        cache.set("match_123", result)

        # 获取缓存
        cached_result = cache.get("match_123")
        assert cached_result is not None
        assert cached_result.match_id == 123
        assert cached_result.predicted_result == "home_win"
        assert cached_result.confidence == 0.80

    def test_prediction_cache_get_nonexistent(self):
        """测试获取不存在的缓存"""
        cache = PredictionCache()
        result = cache.get("nonexistent_key")
        assert result is None

    def test_prediction_cache_set_with_ttl(self):
        """测试设置缓存带TTL（尽管当前实现忽略TTL）"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        result = PredictionResult(
            match_id=456,
            predicted_result="draw",
            confidence=0.60,
            prediction_time=prediction_time,
            model_version="v1.0.0"
        )

        # 设置带TTL的缓存
        cache.set("match_456", result, ttl=7200)

        # 验证可以获取
        cached_result = cache.get("match_456")
        assert cached_result is not None
        assert cached_result.match_id == 456

    def test_prediction_cache_clear(self):
        """测试清空缓存"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        # 添加多个缓存项
        for i in range(3):
            result = PredictionResult(
                match_id=100 + i,
                predicted_result="home_win",
                confidence=0.75,
                prediction_time=prediction_time,
                model_version="v1.0.0"
            )
            cache.set(f"match_{100+i}", result)

        # 验证缓存不为空
        assert len(cache._cache) == 3

        # 清空缓存
        cache.clear()

        # 验证缓存已清空
        assert len(cache._cache) == 0
        assert cache.get("match_100") is None

    def test_prediction_cache_overwrite(self):
        """测试覆盖缓存"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        # 设置初始值
        result1 = PredictionResult(
            match_id=789,
            predicted_result="home_win",
            confidence=0.80,
            prediction_time=prediction_time,
            model_version="v1.0.0"
        )
        cache.set("match_789", result1)

        # 验证初始值
        cached_result = cache.get("match_789")
        assert cached_result.confidence == 0.80

        # 覆盖值
        result2 = PredictionResult(
            match_id=789,
            predicted_result="away_win",
            confidence=0.20,  # 不同的置信度
            prediction_time=prediction_time,
            model_version="v2.0.0"
        )
        cache.set("match_789", result2)

        # 验证覆盖成功
        cached_result = cache.get("match_789")
        assert cached_result.predicted_result == "away_win"
        assert cached_result.confidence == 0.20
        assert cached_result.model_version == "v2.0.0"

    def test_prediction_cache_complex_keys(self):
        """测试复杂的缓存键"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        # 使用复杂的键
        complex_keys = [
            "match_123_home",
            "match_456_away",
            "match_789_draw_v1.0.0",
            "user_123_match_456_model_v2.1.0"
        ]

        result = PredictionResult(
            match_id=999,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=prediction_time,
            model_version="v1.0.0"
        )

        for key in complex_keys:
            cache.set(key, result)
            cached_result = cache.get(key)
            assert cached_result is not None
            assert cached_result.match_id == 999


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestPredictionService:
    """PredictionService测试"""

    def test_prediction_service_class_exists(self):
        """测试PredictionService类存在"""
        assert PredictionService is not None
        assert callable(PredictionService)

    def test_prediction_service_instantiation_default(self):
        """测试PredictionService默认实例化"""
        service = PredictionService()
        assert service.name == "PredictionService"
        assert service.mlflow_tracking_uri == "http://localhost:5002"
        assert isinstance(service.cache, PredictionCache)

    def test_prediction_service_instantiation_custom_uri(self):
        """测试PredictionService自定义URI实例化"""
        custom_uri = "http://custom-mlflow:8080"
        service = PredictionService(mlflow_tracking_uri=custom_uri)
        assert service.mlflow_tracking_uri == custom_uri

    def test_prediction_service_inheritance(self):
        """测试PredictionService继承关系"""
        # 检查是否继承自SimpleService
        from src.services.base_unified import SimpleService
        assert issubclass(PredictionService, SimpleService)

    def test_prediction_service_predict_match(self):
        """测试predict_match方法"""
        service = PredictionService()

        # 由于是异步方法，我们需要使用pytest-asyncio或直接调用协程
        import asyncio

        async def test_predict():
            result = await service.predict_match(12345)
            assert isinstance(result, PredictionResult)
            assert result.match_id == 12345
            assert result.predicted_result == "home_win"
            assert result.confidence == 0.75
            assert result.model_version == "v1.0.0"
            assert isinstance(result.prediction_time, datetime.datetime)

        asyncio.run(test_predict())

    def test_prediction_service_predict_match_different_ids(self):
        """测试predict_match方法的不同ID"""
        service = PredictionService()

        async def test_different_ids():
            match_ids = [1, 123, 456, 789, 999999]

            for match_id in match_ids:
                result = await service.predict_match(match_id)
                assert result.match_id == match_id
                assert result.predicted_result == "home_win"
                assert result.confidence == 0.75

        import asyncio
        asyncio.run(test_different_ids())

    def test_prediction_service_batch_predict_matches(self):
        """测试batch_predict_matches方法"""
        service = PredictionService()

        async def test_batch_predict():
            match_ids = [123, 456, 789]
            results = await service.batch_predict_matches(match_ids)

            assert isinstance(results, list)
            assert len(results) == len(match_ids)

            for i, result in enumerate(results):
                assert isinstance(result, PredictionResult)
                assert result.match_id == match_ids[i]
                assert result.predicted_result == "home_win"

        import asyncio
        asyncio.run(test_batch_predict())

    def test_prediction_service_batch_predict_empty_list(self):
        """测试批量预测空列表"""
        service = PredictionService()

        async def test_empty_batch():
            results = await service.batch_predict_matches([])
            assert results == []

        import asyncio
        asyncio.run(test_empty_batch())

    def test_prediction_service_batch_predict_single_item(self):
        """测试批量预测单项"""
        service = PredictionService()

        async def test_single_batch():
            match_ids = [999]
            results = await service.batch_predict_matches(match_ids)

            assert len(results) == 1
            result = results[0]
            assert result.match_id == 999
            assert isinstance(result, PredictionResult)

        import asyncio
        asyncio.run(test_single_batch())

    def test_prediction_service_verify_prediction(self):
        """测试verify_prediction方法"""
        service = PredictionService()

        async def test_verify():
            result1 = await service.verify_prediction(123)
            result2 = await service.verify_prediction(456)
            result3 = await service.verify_prediction(0)

            # 当前简单实现总是返回True
            assert result1 is True
            assert result2 is True
            assert result3 is True

        import asyncio
        asyncio.run(test_verify())

    def test_prediction_service_get_prediction_statistics(self):
        """测试get_prediction_statistics方法"""
        service = PredictionService()

        async def test_statistics():
            stats = await service.get_prediction_statistics()

            assert isinstance(stats, dict)
            assert "total_predictions" in stats
            assert "accuracy" in stats
            assert "model_version" in stats

            # 验证当前简单实现的默认值
            assert stats["total_predictions"] == 0
            assert stats["accuracy"] == 0.0
            assert stats["model_version"] == "v1.0.0"

        import asyncio
        asyncio.run(test_statistics())

    def test_prediction_service_cache_integration(self):
        """测试PredictionService与缓存的集成"""
        service = PredictionService()
        prediction_time = datetime.datetime.utcnow()

        async def test_cache_integration():
            # 创建一个预测
            result = await service.predict_match(123)

            # 手动添加到缓存
            service.cache.set("test_key", result)

            # 从缓存获取
            cached_result = service.cache.get("test_key")
            assert cached_result is not None
            assert cached_result.match_id == 123

        import asyncio
        asyncio.run(test_cache_integration())


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestCounter:
    """Counter监控指标测试"""

    def test_counter_class_exists(self):
        """测试Counter类存在"""
        assert Counter is not None
        assert callable(Counter)

    def test_counter_instantiation(self):
        """测试Counter实例化"""
        counter = Counter("test_counter", "Test counter description")
        assert counter.name == "test_counter"
        assert counter.description == "Test counter description"
        assert counter.value == 0

    def test_counter_inc(self):
        """测试Counter递增"""
        counter = Counter("test_counter", "Test counter")

        # 初始值
        assert counter() == 0

        # 递增1次
        counter.inc()
        assert counter() == 1

        # 递增多次
        counter.inc()
        counter.inc()
        counter.inc()
        assert counter() == 4

    def test_counter_call_method(self):
        """测试Counter调用方法"""
        counter = Counter("call_test", "Call test counter")

        # 初始调用
        result = counter()
        assert result == 0
        assert isinstance(result, int)

        # 递增后调用
        counter.inc()
        result = counter()
        assert result == 1

    def test_counter_multiple_increments(self):
        """测试Counter多次递增"""
        counter = Counter("multi_test", "Multiple increment test")

        # 递增100次
        for _ in range(100):
            counter.inc()

        assert counter() == 100

    def test_counter_edge_cases(self):
        """测试Counter边界情况"""
        counter = Counter("edge_test", "Edge case test")

        # 大数值递增
        for _ in range(1000):
            counter.inc()

        assert counter() == 1000
        assert isinstance(counter.value, int)


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestHistogram:
    """Histogram监控指标测试"""

    def test_histogram_class_exists(self):
        """测试Histogram类存在"""
        assert Histogram is not None
        assert callable(Histogram)

    def test_histogram_instantiation(self):
        """测试Histogram实例化"""
        histogram = Histogram("test_histogram", "Test histogram description")
        assert histogram.name == "test_histogram"
        assert histogram.description == "Test histogram description"
        assert histogram.values == []

    def test_histogram_observe(self):
        """测试Histogram观察值"""
        histogram = Histogram("observe_test", "Observe test histogram")

        # 初始状态
        assert histogram() == 0.0  # 空列表时应该返回0.0

        # 观察单个值
        histogram.observe(1.5)
        assert histogram() == 1.5
        assert len(histogram.values) == 1

        # 观察多个值
        histogram.observe(2.5)
        histogram.observe(3.5)

        # 计算平均值
        expected_avg = (1.5 + 2.5 + 3.5) / 3
        assert histogram() == expected_avg

    def test_histogram_call_method_empty(self):
        """测试Histogram调用方法（空列表）"""
        histogram = Histogram("empty_test", "Empty histogram test")

        result = histogram()
        assert result == 0.0
        assert isinstance(result, float)

    def test_histogram_call_method_with_values(self):
        """测试Histogram调用方法（有值）"""
        histogram = Histogram("values_test", "Values test histogram")

        # 添加一些值
        test_values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in test_values:
            histogram.observe(value)

        result = histogram()
        expected_avg = sum(test_values) / len(test_values)
        assert result == expected_avg
        assert isinstance(result, float)

    def test_histogram_different_value_types(self):
        """测试Histogram不同数值类型"""
        histogram = Histogram("types_test", "Different value types test")

        # 测试整数
        histogram.observe(10)
        assert histogram() == 10.0

        # 测试浮点数
        histogram.observe(15.5)
        expected_avg = (10 + 15.5) / 2
        assert histogram() == expected_avg

        # 测试小数
        histogram.observe(0.25)
        expected_avg = (10 + 15.5 + 0.25) / 3
        assert histogram() == expected_avg

    def test_histogram_negative_values(self):
        """测试Histogram负值"""
        histogram = Histogram("negative_test", "Negative values test")

        # 添加负值
        histogram.observe(-5.0)
        histogram.observe(10.0)
        histogram.observe(-2.5)

        expected_avg = (-5.0 + 10.0 + -2.5) / 3
        assert histogram() == expected_avg

    def test_histogram_large_values(self):
        """测试Histogram大数值"""
        histogram = Histogram("large_test", "Large values test")

        # 添加大数值
        histogram.observe(1000000.0)
        histogram.observe(2000000.0)

        expected_avg = (1000000.0 + 2000000.0) / 2
        assert histogram() == expected_avg


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestGauge:
    """Gauge监控指标测试"""

    def test_gauge_class_exists(self):
        """测试Gauge类存在"""
        assert Gauge is not None
        assert callable(Gauge)

    def test_gauge_instantiation(self):
        """测试Gauge实例化"""
        gauge = Gauge("test_gauge", "Test gauge description")
        assert gauge.name == "test_gauge"
        assert gauge.description == "Test gauge description"
        assert gauge.value == 0.0

    def test_gauge_set(self):
        """测试Gauge设置值"""
        gauge = Gauge("set_test", "Set test gauge")

        # 初始值
        assert gauge() == 0.0

        # 设置新值
        gauge.set(5.5)
        assert gauge() == 5.5

        # 设置另一个值
        gauge.set(10.0)
        assert gauge() == 10.0

    def test_gauge_call_method(self):
        """测试Gauge调用方法"""
        gauge = Gauge("call_test", "Call test gauge")

        # 初始调用
        result = gauge()
        assert result == 0.0
        assert isinstance(result, float)

        # 设置值后调用
        gauge.set(7.25)
        result = gauge()
        assert result == 7.25
        assert isinstance(result, float)

    def test_gauge_different_value_types(self):
        """测试Gauge不同数值类型"""
        gauge = Gauge("types_test", "Different value types test")

        # 设置整数
        gauge.set(10)
        assert gauge() == 10.0

        # 设置浮点数
        gauge.set(15.75)
        assert gauge() == 15.75

        # 设置小数
        gauge.set(0.125)
        assert gauge() == 0.125

    def test_gauge_negative_values(self):
        """测试Gauge负值"""
        gauge = Gauge("negative_test", "Negative values test")

        gauge.set(-10.5)
        assert gauge() == -10.5

        gauge.set(0.0)
        assert gauge() == 0.0

    def test_gauge_zero_values(self):
        """测试Gauge零值"""
        gauge = Gauge("zero_test", "Zero values test")

        gauge.set(0.0)
        assert gauge() == 0.0

        gauge.set(0)
        assert gauge() == 0.0

    def test_gauge_large_values(self):
        """测试Gauge大数值"""
        gauge = Gauge("large_test", "Large values test")

        large_value = 999999.999
        gauge.set(large_value)
        assert gauge() == large_value


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestMonitoringMetrics:
    """监控指标实例测试"""

    def test_predictions_total_counter(self):
        """测试predictions_total计数器"""
        assert predictions_total.name == "predictions_total"
        assert predictions_total.description == "Total number of predictions"
        assert predictions_total() == 0

        # 测试递增
        predictions_total.inc()
        assert predictions_total() == 1

    def test_prediction_duration_seconds_histogram(self):
        """测试prediction_duration_seconds直方图"""
        assert prediction_duration_seconds.name == "prediction_duration_seconds"
        assert prediction_duration_seconds.description == "Prediction duration in seconds"
        assert prediction_duration_seconds() == 0.0

        # 测试观察
        prediction_duration_seconds.observe(1.25)
        assert prediction_duration_seconds() == 1.25

    def test_prediction_accuracy_gauge(self):
        """测试prediction_accuracy仪表"""
        assert prediction_accuracy.name == "prediction_accuracy"
        assert prediction_accuracy.description == "Prediction accuracy"
        assert prediction_accuracy() == 0.0

        # 测试设置
        prediction_accuracy.set(0.85)
        assert prediction_accuracy() == 0.85

    def test_model_load_duration_seconds_histogram(self):
        """测试model_load_duration_seconds直方图"""
        assert model_load_duration_seconds.name == "model_load_duration_seconds"
        assert model_load_duration_seconds.description == "Model load duration in seconds"
        assert model_load_duration_seconds() == 0.0

        # 测试观察
        model_load_duration_seconds.observe(5.75)
        assert model_load_duration_seconds() == 5.75

    def test_cache_hit_ratio_gauge(self):
        """测试cache_hit_ratio仪表"""
        assert cache_hit_ratio.name == "cache_hit_ratio"
        assert cache_hit_ratio.description == "Cache hit ratio"
        assert cache_hit_ratio() == 0.0

        # 测试设置
        cache_hit_ratio.set(0.92)
        assert cache_hit_ratio() == 0.92

    def test_all_metrics_independent(self):
        """测试所有指标实例独立工作"""
        # 保存当前状态并重置指标
        initial_total = predictions_total()

        # 重置计数器
        predictions_total.value = 0
        prediction_duration_seconds.values = []
        model_load_duration_seconds.values = []

        # 操作各个指标
        predictions_total.inc()
        prediction_accuracy.set(0.95)
        prediction_duration_seconds.observe(2.5)
        model_load_duration_seconds.observe(3.0)
        cache_hit_ratio.set(0.88)

        # 验证独立性
        assert predictions_total() == 1
        assert prediction_accuracy() == 0.95
        assert prediction_duration_seconds() == 2.5
        assert model_load_duration_seconds() == 3.0
        assert cache_hit_ratio() == 0.88


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestPredictionIntegration:
    """预测模块集成测试"""

    def test_complete_prediction_workflow(self):
        """测试完整的预测工作流"""
        import asyncio

        async def test_workflow():
            # 重置监控指标以避免干扰
            prediction_duration_seconds.values = []
            prediction_accuracy.value = 0.0

            # 1. 创建服务
            service = PredictionService()

            # 2. 预测比赛
            result = await service.predict_match(12345)

            # 3. 缓存结果
            service.cache.set(f"match_{result.match_id}", result)

            # 4. 从缓存获取
            cached_result = service.cache.get(f"match_{result.match_id}")

            # 5. 验证工作流
            assert cached_result is not None
            assert cached_result.match_id == result.match_id
            assert cached_result.predicted_result == result.predicted_result

            # 6. 更新监控指标
            predictions_total.inc()
            prediction_duration_seconds.observe(1.5)
            prediction_accuracy.set(0.85)

            # 7. 获取统计信息
            stats = await service.get_prediction_statistics()

            # 验证所有组件协同工作
            assert isinstance(stats, dict)
            assert predictions_total() >= 1
            assert prediction_duration_seconds() == 1.5
            assert prediction_accuracy() == 0.85

        asyncio.run(test_workflow())

    def test_batch_prediction_workflow(self):
        """测试批量预测工作流"""
        import asyncio

        async def test_batch_workflow():
            service = PredictionService()

            # 批量预测
            match_ids = [100, 200, 300, 400, 500]
            results = await service.batch_predict_matches(match_ids)

            # 验证结果
            assert len(results) == len(match_ids)

            # 缓存所有结果
            for result in results:
                service.cache.set(f"batch_match_{result.match_id}", result)

            # 验证缓存
            for result in results:
                cached = service.cache.get(f"batch_match_{result.match_id}")
                assert cached is not None
                assert cached.match_id == result.match_id

            # 更新批量预测监控指标
            for _ in results:
                predictions_total.inc()
                prediction_duration_seconds.observe(0.8)

            # 验证指标更新
            assert predictions_total() >= len(results)

        asyncio.run(test_batch_workflow())

    def test_monitoring_metrics_integration(self):
        """测试监控指标集成"""
        # 重置指标
        while predictions_total() > 0:
            predictions_total.value -= 1

        # 模拟预测操作
        for i in range(10):
            predictions_total.inc()
            prediction_duration_seconds.observe(0.5 + i * 0.1)
            cache_hit_ratio.set(0.8 + i * 0.02)

        # 验证指标
        assert predictions_total() == 10
        assert prediction_duration_seconds() > 0.0
        assert cache_hit_ratio() >= 0.8

    def test_prediction_service_error_handling(self):
        """测试预测服务错误处理"""
        service = PredictionService()

        async def test_error_handling():
            # 测试边界情况
            result = await service.predict_match(0)  # match_id = 0
            assert result.match_id == 0

            result = await service.predict_match(-1)  # 负数match_id
            assert result.match_id == -1

            # 测试大批量预测
            large_batch = list(range(1000))
            results = await service.batch_predict_matches(large_batch)
            assert len(results) == 1000

        import asyncio
        asyncio.run(test_error_handling())