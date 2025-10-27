"""
预测模块单元测试

测试 src/models/prediction.py 中的预测功能。
专注于业务逻辑测试，提高测试密度和质量。
"""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

# 导入要测试的模块
try:
    from src.models.prediction import (Counter, Gauge,  # 监控指标类; 监控指标实例
                                       Histogram, PredictionCache,
                                       PredictionResult, PredictionService,
                                       cache_hit_ratio,
                                       model_load_duration_seconds,
                                       prediction_accuracy,
                                       prediction_duration_seconds,
                                       predictions_total)

    PREDICTION_AVAILABLE = True
except ImportError:
    PREDICTION_AVAILABLE = False


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
@pytest.mark.unit
class TestPredictionResult:
    """PredictionResult业务逻辑测试"""

    def test_prediction_result_dataclass_structure(self):
        """测试PredictionResult dataclass结构"""
        import dataclasses

        assert dataclasses.is_dataclass(PredictionResult)

        # 验证字段
        fields = dataclasses.fields(PredictionResult)
        field_names = {f.name for f in fields}
        expected_fields = {
            "match_id",
            "predicted_result",
            "confidence",
            "prediction_time",
            "model_version",
            "features",
        }
        assert field_names == expected_fields

    def test_prediction_result_creation_with_business_scenarios(self):
        """测试业务场景下的PredictionResult创建"""
        base_time = datetime.datetime(2023, 12, 1, 20, 0, 0)

        # 足球比赛预测场景
        scenarios = [
            {
                "match_id": 12345,
                "predicted_result": "home_win",
                "confidence": 0.85,
                "features": {
                    "home_team_strength": 0.9,
                    "away_team_strength": 0.6,
                    "home_form": [1, 1, 0, 1, 1],
                    "away_form": [0, 0, 1, 0, 0],
                    "h2h_home_wins": 3,
                    "venue_advantage": "home",
                },
            },
            {
                "match_id": 12346,
                "predicted_result": "draw",
                "confidence": 0.65,
                "features": {
                    "home_team_strength": 0.7,
                    "away_team_strength": 0.72,
                    "home_form": [0, 1, 0, 1, 0],
                    "away_form": [1, 0, 1, 0, 1],
                    "h2h_draws": 2,
                    "venue_advantage": "neutral",
                },
            },
            {
                "match_id": 12347,
                "predicted_result": "away_win",
                "confidence": 0.78,
                "features": {},
            },
        ]

        for scenario in scenarios:
            result = PredictionResult(
                match_id=scenario["match_id"],
                predicted_result=scenario["predicted_result"],
                confidence=scenario["confidence"],
                prediction_time=base_time,
                model_version="v2.1.0",
                features=scenario["features"],
            )

            assert result.match_id == scenario["match_id"]
            assert result.predicted_result == scenario["predicted_result"]
            assert result.confidence == scenario["confidence"]
            assert result.features == scenario["features"]

    def test_prediction_result_edge_cases(self):
        """测试边界情况"""
        # 最小置信度
        result_min = PredictionResult(
            match_id=1,
            predicted_result="home_win",
            confidence=0.0,
            prediction_time=datetime.datetime.utcnow(),
            model_version="v1.0.0",
        )
        assert result_min.confidence == 0.0

        # 最大置信度
        result_max = PredictionResult(
            match_id=2,
            predicted_result="away_win",
            confidence=1.0,
            prediction_time=datetime.datetime.utcnow(),
            model_version="v1.0.0",
        )
        assert result_max.confidence == 1.0

        # 极端match_id值
        result_extreme = PredictionResult(
            match_id=0,
            predicted_result="draw",
            confidence=0.5,
            prediction_time=datetime.datetime.utcnow(),
            model_version="v1.0.0",
        )
        assert result_extreme.match_id == 0

    def test_prediction_result_features_handling(self):
        """测试features字段处理逻辑"""
        prediction_time = datetime.datetime.utcnow()

        # None特征自动转换为空字典
        result_none = PredictionResult(
            match_id=1,
            predicted_result="home_win",
            confidence=0.8,
            prediction_time=prediction_time,
            model_version="v1.0.0",
            features=None,
        )
        assert result_none.features == {}

        # 空字典保持不变
        result_empty = PredictionResult(
            match_id=2,
            predicted_result="draw",
            confidence=0.6,
            prediction_time=prediction_time,
            model_version="v1.0.0",
            features={},
        )
        assert result_empty.features == {}

        # 复杂嵌套特征
        complex_features = {
            "teams": {
                "home": {"name": "Team A", "rating": 85.5, "injuries": 1},
                "away": {"name": "Team B", "rating": 78.2, "injuries": 2},
            },
            "conditions": {
                "weather": "rain",
                "temperature": 15.0,
                "stadium": "Stadium X",
            },
            "statistics": {
                "home_goals_recent": [2, 1, 3, 0, 2],
                "away_goals_recent": [1, 0, 1, 2, 1],
            },
        }

        result_complex = PredictionResult(
            match_id=3,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=prediction_time,
            model_version="v3.0.0",
            features=complex_features,
        )
        assert result_complex.features == complex_features


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestPredictionCache:
    """PredictionCache业务逻辑测试"""

    def test_cache_basic_operations(self):
        """测试缓存基本操作"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        # 创建预测结果
        result = PredictionResult(
            match_id=12345,
            predicted_result="home_win",
            confidence=0.85,
            prediction_time=prediction_time,
            model_version="v2.1.0",
        )

        # 测试设置和获取
        cache.set("match_12345", result)
        cached_result = cache.get("match_12345")

        assert cached_result is not None
        assert cached_result.match_id == 12345
        assert cached_result.predicted_result == "home_win"
        assert cached_result.confidence == 0.85

        # 测试不存在的键
        assert cache.get("nonexistent") is None

    def test_cache_business_scenarios(self):
        """测试业务场景下的缓存使用"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        # 模拟多场比赛预测缓存
        matches = [
            (12345, "home_win", 0.85),
            (12346, "draw", 0.65),
            (12347, "away_win", 0.78),
            (12348, "home_win", 0.92),
        ]

        # 批量缓存
        for match_id, result, confidence in matches:
            prediction = PredictionResult(
                match_id=match_id,
                predicted_result=result,
                confidence=confidence,
                prediction_time=prediction_time,
                model_version="v2.1.0",
            )
            cache_key = f"match_{match_id}_v2.1.0"
            cache.set(cache_key, prediction)

        # 验证缓存命中
        for match_id, expected_result, expected_confidence in matches:
            cache_key = f"match_{match_id}_v2.1.0"
            cached = cache.get(cache_key)
            assert cached is not None
            assert cached.predicted_result == expected_result
            assert cached.confidence == expected_confidence

        # 验证缓存大小
        assert len(cache._cache) == len(matches)

    def test_cache_ttl_parameter_handling(self):
        """测试TTL参数处理（虽然当前实现忽略）"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        result = PredictionResult(
            match_id=999,
            predicted_result="home_win",
            confidence=0.80,
            prediction_time=prediction_time,
            model_version="v1.0.0",
        )

        # 不同TTL值
        cache.set("match_999_1h", result, ttl=3600)
        cache.set("match_999_24h", result, ttl=86400)
        cache.set("match_999_custom", result, ttl=12345)

        # 所有缓存都应该存在（当前实现忽略TTL）
        assert cache.get("match_999_1h") is not None
        assert cache.get("match_999_24h") is not None
        assert cache.get("match_999_custom") is not None

    def test_cache_overwrite_and_clear(self):
        """测试缓存覆盖和清空"""
        cache = PredictionCache()
        prediction_time = datetime.datetime.utcnow()

        # 初始缓存
        result1 = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.80,
            prediction_time=prediction_time,
            model_version="v1.0.0",
        )
        cache.set("match_123", result1)

        # 验证初始值
        cached = cache.get("match_123")
        assert cached.confidence == 0.80
        assert cached.model_version == "v1.0.0"

        # 覆盖缓存（更新后的预测）
        result2 = PredictionResult(
            match_id=123,
            predicted_result="home_win",
            confidence=0.85,  # 更新的置信度
            prediction_time=prediction_time,
            model_version="v1.1.0",  # 更新的模型版本
        )
        cache.set("match_123", result2)

        # 验证覆盖
        cached = cache.get("match_123")
        assert cached.confidence == 0.85
        assert cached.model_version == "v1.1.0"

        # 清空缓存
        cache.clear()
        assert len(cache._cache) == 0
        assert cache.get("match_123") is None


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestPredictionService:
    """PredictionService业务逻辑测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        # 默认初始化
        service = PredictionService()
        assert service.name == "PredictionService"
        assert service.mlflow_tracking_uri == "http://localhost:5002"
        assert isinstance(service.cache, PredictionCache)

        # 自定义URI初始化
        custom_uri = "http://custom-mlflow:8080"
        service_custom = PredictionService(mlflow_tracking_uri=custom_uri)
        assert service_custom.mlflow_tracking_uri == custom_uri

    def test_service_inheritance(self):
        """测试服务继承关系"""
        from src.services.base_unified import SimpleService

        assert issubclass(PredictionService, SimpleService)

    @pytest.mark.asyncio
    async def test_predict_match_business_logic(self):
        """测试单场比赛预测业务逻辑"""
        service = PredictionService()

        # 测试不同比赛ID的预测
        test_cases = [1, 123, 456, 789, 999999, 0, -1]

        for match_id in test_cases:
            result = await service.predict_match(match_id)

            # 验证结果结构
            assert isinstance(result, PredictionResult)
            assert result.match_id == match_id
            assert result.predicted_result == "home_win"  # 当前实现的默认值
            assert result.confidence == 0.75  # 当前实现的默认值
            assert result.model_version == "v1.0.0"
            assert isinstance(result.prediction_time, datetime.datetime)
            assert isinstance(result.features, dict)

    @pytest.mark.asyncio
    async def test_batch_predict_business_scenarios(self):
        """测试批量预测业务场景"""
        service = PredictionService()

        # 空列表
        results = await service.batch_predict_matches([])
        assert results == []

        # 单场比赛
        results = await service.batch_predict_matches([123])
        assert len(results) == 1
        assert results[0].match_id == 123

        # 多场比赛
        match_ids = [100, 200, 300, 400, 500]
        results = await service.batch_predict_matches(match_ids)

        assert len(results) == len(match_ids)
        for i, result in enumerate(results):
            assert result.match_id == match_ids[i]
            assert isinstance(result, PredictionResult)
            assert result.predicted_result == "home_win"
            assert result.confidence == 0.75

    @pytest.mark.asyncio
    async def test_service_auxiliary_methods(self):
        """测试服务辅助方法"""
        service = PredictionService()

        # 验证预测方法（当前实现总是返回True）
        test_ids = [1, 123, 456, 0, -1]
        for prediction_id in test_ids:
            result = await service.verify_prediction(prediction_id)
            assert result is True

        # 获取统计信息
        stats = await service.get_prediction_statistics()
        assert isinstance(stats, dict)
        assert "total_predictions" in stats
        assert "accuracy" in stats
        assert "model_version" in stats
        assert stats["total_predictions"] == 0
        assert stats["accuracy"] == 0.0
        assert stats["model_version"] == "v1.0.0"

    @pytest.mark.asyncio
    async def test_service_cache_integration(self):
        """测试服务与缓存集成"""
        service = PredictionService()

        # 创建预测
        result = await service.predict_match(12345)

        # 手动缓存
        cache_key = f"match_{result.match_id}_{result.model_version}"
        service.cache.set(cache_key, result)

        # 从缓存获取
        cached_result = service.cache.get(cache_key)
        assert cached_result is not None
        assert cached_result.match_id == 12345
        assert cached_result.predicted_result == result.predicted_result
        assert cached_result.confidence == result.confidence


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestMonitoringMetrics:
    """监控指标业务逻辑测试"""

    def test_counter_business_usage(self):
        """测试Counter业务使用场景"""
        counter = Counter("test_predictions", "Test prediction counter")

        # 初始状态
        assert counter() == 0

        # 模拟预测计数
        for i in range(10):
            counter.inc()

        assert counter() == 10
        assert counter.value == 10

    def test_histogram_business_usage(self):
        """测试Histogram业务使用场景"""
        histogram = Histogram("prediction_duration", "Prediction duration histogram")

        # 初始状态
        assert histogram() == 0.0

        # 模拟预测耗时记录（秒）
        durations = [0.5, 0.8, 1.2, 0.6, 1.5, 0.9, 1.1]
        for duration in durations:
            histogram.observe(duration)

        # 验证平均耗时
        expected_avg = sum(durations) / len(durations)
        assert histogram() == expected_avg

    def test_gauge_business_usage(self):
        """测试Gauge业务使用场景"""
        gauge = Gauge("accuracy", "Prediction accuracy gauge")

        # 初始状态
        assert gauge() == 0.0

        # 模拟准确率更新
        accuracy_values = [0.75, 0.80, 0.78, 0.82, 0.85]
        for accuracy in accuracy_values:
            gauge.set(accuracy)

        # 验证最终值
        assert gauge() == 0.85

    def test_predefined_metrics(self):
        """测试预定义监控指标"""
        # 验证指标存在
        assert predictions_total.name == "predictions_total"
        assert prediction_duration_seconds.name == "prediction_duration_seconds"
        assert prediction_accuracy.name == "prediction_accuracy"
        assert model_load_duration_seconds.name == "model_load_duration_seconds"
        assert cache_hit_ratio.name == "cache_hit_ratio"

        # 验证指标功能
        predictions_total.inc()
        assert predictions_total() == 1

        prediction_duration_seconds.observe(1.5)
        assert prediction_duration_seconds() == 1.5

        prediction_accuracy.set(0.88)
        assert prediction_accuracy() == 0.88


@pytest.mark.skipif(not PREDICTION_AVAILABLE, reason="Prediction module not available")
class TestPredictionIntegration:
    """预测模块集成测试"""

    @pytest.mark.asyncio
    async def test_complete_prediction_workflow(self):
        """测试完整预测工作流"""
        # 重置指标状态以避免测试间干扰
        initial_predictions = predictions_total()
        prediction_duration_seconds.values.copy()

        service = PredictionService()

        # 1. 执行预测
        result = await service.predict_match(12345)

        # 2. 缓存结果
        cache_key = f"match_{result.match_id}"
        service.cache.set(cache_key, result)

        # 3. 从缓存检索
        cached_result = service.cache.get(cache_key)

        # 4. 验证工作流
        assert cached_result is not None
        assert cached_result.match_id == result.match_id
        assert cached_result.predicted_result == result.predicted_result

        # 5. 更新监控指标
        predictions_total.inc()
        prediction_duration_seconds.observe(1.2)
        prediction_accuracy.set(0.85)

        # 6. 验证指标（基于增量变化）
        assert predictions_total() == initial_predictions + 1
        assert prediction_accuracy() == 0.85
        # 验证新增的duration值被记录
        assert 1.2 in prediction_duration_seconds.values

    @pytest.mark.asyncio
    async def test_batch_prediction_workflow(self):
        """测试批量预测工作流"""
        # 记录初始状态
        initial_predictions = predictions_total()
        initial_duration_values = prediction_duration_seconds.values.copy()

        service = PredictionService()

        # 1. 批量预测
        match_ids = [100, 200, 300]
        results = await service.batch_predict_matches(match_ids)

        # 2. 批量缓存
        for result in results:
            cache_key = f"batch_match_{result.match_id}"
            service.cache.set(cache_key, result)

        # 3. 验证缓存完整性
        for result in results:
            cache_key = f"batch_match_{result.match_id}"
            cached = service.cache.get(cache_key)
            assert cached is not None
            assert cached.match_id == result.match_id

        # 4. 更新批量监控指标
        batch_count = len(results)
        for _ in results:
            predictions_total.inc()
            prediction_duration_seconds.observe(0.8)

        # 5. 验证指标（基于增量变化）
        assert predictions_total() == initial_predictions + batch_count
        # 验证新增的duration值被正确记录
        new_duration_count = prediction_duration_seconds.values.__len__() - len(
            initial_duration_values
        )
        assert new_duration_count == batch_count

    def test_metrics_reset_and_independence(self):
        """测试指标重置和独立性"""
        # 重置指标状态
        predictions_total.value = 0
        prediction_duration_seconds.values = []
        model_load_duration_seconds.values = []
        prediction_accuracy.value = 0.0
        cache_hit_ratio.value = 0.0

        # 独立操作各个指标
        predictions_total.inc()  # 计数器
        prediction_accuracy.set(0.92)  # 仪表
        prediction_duration_seconds.observe(2.1)  # 直方图
        model_load_duration_seconds.observe(4.5)  # 另一个直方图
        cache_hit_ratio.set(0.87)  # 另一个仪表

        # 验证指标独立性
        assert predictions_total() == 1
        assert prediction_accuracy() == 0.92
        assert prediction_duration_seconds() == 2.1
        assert model_load_duration_seconds() == 4.5
        assert cache_hit_ratio() == 0.87
