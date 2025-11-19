from typing import Optional

#!/usr/bin/env python3
"""
修复版预测模型测试 - 覆盖率优化
Fixed prediction model tests for coverage optimization
"""

import sys
from datetime import datetime

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, ".")


class TestModelsPredictionFixed:
    """修复版的预测模型测试类"""

    def test_prediction_result_creation(self):
        """测试预测结果创建"""
        from src.models.prediction import PredictionResult

        # 创建预测结果实例
        prediction = PredictionResult(
            match_id=1,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=datetime.utcnow(),
            model_version="v1.0.0",
        )
        assert prediction is not None

        # 测试基本属性
        assert prediction.match_id == 1
        assert prediction.predicted_result == "home_win"
        assert prediction.confidence == 0.75
        assert isinstance(prediction.prediction_time, datetime)
        assert prediction.model_version == "v1.0.0"
        assert prediction.features == {}

    def test_prediction_result_with_features(self):
        """测试带特性的预测结果"""
        from src.models.prediction import PredictionResult

        features = {
            "home_team_strength": 0.8,
            "away_team_strength": 0.6,
            "historical_performance": 0.7,
        }

        prediction = PredictionResult(
            match_id=2,
            predicted_result="draw",
            confidence=0.65,
            prediction_time=datetime.utcnow(),
            model_version="v1.0.0",
            features=features,
        )

        assert prediction.features == features
        assert len(prediction.features) == 3

    def test_prediction_cache_functionality(self):
        """测试预测缓存功能"""
        from src.models.prediction import PredictionCache, PredictionResult

        cache = PredictionCache()
        prediction = PredictionResult(
            match_id=1,
            predicted_result="home_win",
            confidence=0.75,
            prediction_time=datetime.utcnow(),
            model_version="v1.0.0",
        )

        # 测试缓存设置和获取
        cache.set("match_1", prediction)
        cached_prediction = cache.get("match_1")
        assert cached_prediction is not None
        assert cached_prediction.match_id == 1

        # 测试缓存清空
        cache.clear()
        cached_prediction = cache.get("match_1")
        assert cached_prediction is None

    def test_prediction_service_creation(self):
        """测试预测服务创建"""
        from src.models.prediction import PredictionService

        service = PredictionService()
        assert service is not None
        assert service.name == "PredictionService"
        assert service.cache is not None
        assert service.mlflow_tracking_uri == "http://localhost:5002"

    def test_prediction_service_with_custom_uri(self):
        """测试自定义URI的预测服务"""
        from src.models.prediction import PredictionService

        custom_uri = "http://custom-mlflow:8080"
        service = PredictionService(mlflow_tracking_uri=custom_uri)
        assert service.mlflow_tracking_uri == custom_uri

    def test_prediction_service_basic_methods(self):
        """测试预测服务基本方法"""
        from src.models.prediction import PredictionService

        service = PredictionService()

        # 测试服务存在方法
        assert hasattr(service, "predict_match")
        assert hasattr(service, "batch_predict_matches")
        assert hasattr(service, "verify_prediction")
        assert hasattr(service, "get_prediction_statistics")

    def test_prediction_service_async_methods(self):
        """测试预测服务异步方法"""
        import asyncio

        from src.models.prediction import PredictionService

        service = PredictionService()

        # 测试异步方法（简单验证，不实际运行）
        @pytest.mark.asyncio
        async def test_async_methods():
            # 这些方法存在且可调用
            assert callable(service.predict_match)
            assert callable(service.batch_predict_matches)
            assert callable(service.verify_prediction)
            assert callable(service.get_prediction_statistics)

        # 运行异步测试
        asyncio.run(test_async_methods())

    def test_monitoring_metrics_functionality(self):
        """测试监控指标功能"""
        from src.models.prediction import (
            prediction_accuracy,
            prediction_duration_seconds,
            predictions_total,
        )

        # 测试Counter指标
        initial_value = predictions_total()
        predictions_total.inc()
        assert predictions_total() == initial_value + 1

        # 测试Gauge指标
        prediction_accuracy.set(0.85)
        assert prediction_accuracy() == 0.85

        # 测试Histogram指标
        prediction_duration_seconds.observe(1.5)
        prediction_duration_seconds.observe(2.0)
        avg_duration = prediction_duration_seconds()
        assert avg_duration == 1.75  # (1.5 + 2.0) / 2

    def test_prometheus_classes_instantiation(self):
        """测试Prometheus类实例化"""
        from src.models.prediction import Counter, Gauge, Histogram

        # 测试Counter
        counter = Counter("test_counter", "Test counter")
        assert counter.name == "test_counter"
        assert counter.description == "Test counter"
        assert counter() == 0

        # 测试Histogram
        histogram = Histogram("test_histogram", "Test histogram")
        assert histogram.name == "test_histogram"
        assert histogram.description == "Test histogram"
        assert histogram() == 0.0  # 空直方图返回0

        # 测试Gauge
        gauge = Gauge("test_gauge", "Test gauge")
        assert gauge.name == "test_gauge"
        assert gauge.description == "Test gauge"
        assert gauge() == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
