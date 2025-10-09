"""
测试预测服务模块化拆分
Test modular split of prediction service
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestPredictionModels:
    """测试预测模型"""

    def test_prediction_result_import(self):
        """测试预测结果类导入"""
        from src.models.prediction.models import PredictionResult

        assert PredictionResult is not None

    def test_prediction_result_creation(self):
        """测试预测结果创建"""
        from src.models.prediction.models import PredictionResult

        result = PredictionResult(
            match_id=12345,
            model_version="v1.0.0",
            model_name="football_model",
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2,
            predicted_result="home",
            confidence_score=0.75,
        )

        assert result.match_id == 12345
        assert result.model_version == "v1.0.0"
        assert result.model_name == "football_model"
        assert result.home_win_probability == 0.5
        assert result.predicted_result == "home"
        assert result.confidence_score == 0.75

    def test_prediction_result_to_dict(self):
        """测试预测结果转字典"""
        from src.models.prediction.models import PredictionResult

        result = PredictionResult(
            match_id=12345,
            model_version="v1.0.0",
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2,
            predicted_result="home",
            confidence_score=0.75,
            created_at=datetime.now(),
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["match_id"] == 12345
        assert result_dict["model_version"] == "v1.0.0"
        assert result_dict["predicted_result"] == "home"
        assert result_dict["confidence_score"] == 0.75

    def test_prediction_result_from_dict(self):
        """测试从字典创建预测结果"""
        from src.models.prediction.models import PredictionResult

        data = {
            "match_id": 12345,
            "model_version": "v1.0.0",
            "model_name": "football_model",
            "home_win_probability": 0.5,
            "draw_probability": 0.3,
            "away_win_probability": 0.2,
            "predicted_result": "home",
            "confidence_score": 0.75,
            "created_at": datetime.now().isoformat(),
        }

        result = PredictionResult.from_dict(data)
        assert result.match_id == 12345
        assert result.model_version == "v1.0.0"
        assert result.predicted_result == "home"

    def test_prediction_result_validation(self):
        """测试预测结果验证"""
        from src.models.prediction.models import PredictionResult

        result = PredictionResult(
            match_id=12345,
            model_version="v1.0.0",
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2,
            predicted_result="home",
            confidence_score=0.75,
        )

        assert result.is_probabilities_valid()

        # 测试无效概率
        result.home_win_probability = 0.6
        result.draw_probability = 0.6
        result.away_win_probability = 0.6
        assert not result.is_probabilities_valid()

    def test_get_highest_probability(self):
        """测试获取最高概率"""
        from src.models.prediction.models import PredictionResult

        result = PredictionResult(
            match_id=12345,
            model_version="v1.0.0",
            home_win_probability=0.6,
            draw_probability=0.3,
            away_win_probability=0.1,
            predicted_result="home",
            confidence_score=0.75,
        )

        highest_result, highest_prob = result.get_highest_probability()
        assert highest_result == "home"
        assert highest_prob == 0.6

    def test_update_actual_result(self):
        """测试更新实际结果"""
        from src.models.prediction.models import PredictionResult

        result = PredictionResult(
            match_id=12345,
            model_version="v1.0.0",
            predicted_result="home",
            confidence_score=0.75,
        )

        result.update_actual_result(2, 1)
        assert result.actual_result == "home"
        assert result.is_correct is True
        assert result.verified_at is not None


class TestPredictionMetrics:
    """测试预测指标"""

    def test_metrics_import(self):
        """测试指标导入"""
        from src.models.prediction.metrics import (
            predictions_total,
            prediction_duration_seconds,
            prediction_accuracy,
            model_load_duration_seconds,
            cache_hit_ratio,
        )

        assert predictions_total is not None
        assert prediction_duration_seconds is not None
        assert prediction_accuracy is not None
        assert model_load_duration_seconds is not None
        assert cache_hit_ratio is not None

    def test_metrics_are_callable(self):
        """测试指标可调用"""
        from src.models.prediction.metrics import (
            predictions_total,
            prediction_accuracy,
        )

        # 测试指标有labels方法
        assert hasattr(predictions_total, "labels")
        assert hasattr(prediction_accuracy, "labels")


class TestPredictionCache:
    """测试预测缓存"""

    def test_cache_import(self):
        """测试缓存导入"""
        from src.models.prediction.cache import PredictionCache

        assert PredictionCache is not None

    def test_cache_init(self):
        """测试缓存初始化"""
        from src.models.prediction.cache import PredictionCache

        cache = PredictionCache(
            model_cache_ttl_hours=2, prediction_cache_ttl_minutes=15
        )
        assert cache.model_cache is not None
        assert cache.prediction_cache is not None
        assert cache.feature_cache is not None

    @pytest.mark.asyncio
    async def test_cache_set_get_model(self):
        """测试缓存模型存取"""
        from src.models.prediction.cache import PredictionCache

        cache = PredictionCache()
        mock_model = MagicMock()

        # 设置模型
        await cache.set_model("test_model", "v1.0", mock_model)

        # 获取模型
        retrieved_model = await cache.get_model("test_model", "v1.0")
        assert retrieved_model == mock_model

    @pytest.mark.asyncio
    async def test_cache_set_get_prediction(self):
        """测试缓存预测结果存取"""
        from src.models.prediction.cache import PredictionCache

        cache = PredictionCache()
        prediction = {"match_id": 12345, "result": "home"}

        # 设置预测结果
        await cache.set_prediction(12345, prediction)

        # 获取预测结果
        retrieved_prediction = await cache.get_prediction(12345)
        assert retrieved_prediction == prediction

    @pytest.mark.asyncio
    async def test_cache_invalidate(self):
        """测试缓存失效"""
        from src.models.prediction.cache import PredictionCache

        cache = PredictionCache()
        prediction = {"match_id": 12345, "result": "home"}

        # 设置预测结果
        await cache.set_prediction(12345, prediction)
        assert await cache.get_prediction(12345) == prediction

        # 使缓存失效
        await cache.invalidate_prediction(12345)
        assert await cache.get_prediction(12345) is None


class TestMLflowClient:
    """测试MLflow客户端"""

    def test_mlflow_client_import(self):
        """测试MLflow客户端导入"""
        from src.models.prediction.mlflow_client import MLflowModelClient

        assert MLflowModelClient is not None

    def test_mlflow_client_init(self):
        """测试MLflow客户端初始化"""
        from src.models.prediction.mlflow_client import MLflowModelClient

        client = MLflowModelClient("http://localhost:5002")
        assert client.tracking_uri == "http://localhost:5002"
        assert client.model_name == "football_baseline_model"

    @pytest.mark.asyncio
    async def test_get_latest_model_version(self):
        """测试获取最新模型版本"""
        from src.models.prediction.mlflow_client import MLflowModelClient

        client = MLflowModelClient()

        with patch.object(client, "client") as mock_client:
            mock_version = MagicMock()
            mock_version.version = "v1.0.0"
            mock_client.get_latest_versions.return_value = [mock_version]

            version = await client.get_latest_model_version("Production")
            assert version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_get_production_model(self):
        """测试获取生产模型"""
        from src.models.prediction.mlflow_client import MLflowModelClient

        client = MLflowModelClient()
        mock_model = MagicMock()

        with patch("src.models.prediction.mlflow_client.mlflow") as mock_mlflow:
            with patch.object(client, "get_latest_model_version") as mock_get_version:
                mock_get_version.return_value = "v1.0.0"
                mock_mlflow.sklearn.load_model.return_value = mock_model

                model, version = await client.get_production_model()
                assert model == mock_model
                assert version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_get_model_info(self):
        """测试获取模型信息"""
        from src.models.prediction.mlflow_client import MLflowModelClient

        client = MLflowModelClient()

        with patch.object(client, "client") as mock_client:
            mock_details = MagicMock()
            mock_details.name = "football_model"
            mock_details.version = "v1.0.0"
            mock_details.current_stage = "Production"
            mock_details.creation_timestamp = 1234567890
            mock_details.last_updated_timestamp = 1234567891
            mock_details.run_id = "run_123"
            mock_details.description = "Test model"
            mock_client.get_model_version.return_value = mock_details

            info = await client.get_model_info("v1.0.0")
            assert info["name"] == "football_model"
            assert info["version"] == "v1.0.0"
            assert info["stage"] == "Production"


class TestFeatureProcessor:
    """测试特征处理器"""

    def test_feature_processor_import(self):
        """测试特征处理器导入"""
        from src.models.prediction.feature_processor import FeatureProcessor

        assert FeatureProcessor is not None

    def test_feature_processor_init(self):
        """测试特征处理器初始化"""
        from src.models.prediction.feature_processor import FeatureProcessor

        processor = FeatureProcessor()
        assert hasattr(processor, "feature_names")
        assert len(processor.feature_names) > 0

    def test_get_default_features(self):
        """测试获取默认特征"""
        from src.models.prediction.feature_processor import FeatureProcessor

        processor = FeatureProcessor()
        features = processor.get_default_features()

        assert isinstance(features, dict)
        assert "home_team_strength" in features
        assert "away_team_strength" in features
        assert "home_form" in features

    def test_prepare_features_for_prediction(self):
        """测试准备预测特征"""
        from src.models.prediction.feature_processor import FeatureProcessor
        import numpy as np

        processor = FeatureProcessor()
        features = processor.get_default_features()

        feature_array = processor.prepare_features_for_prediction(features)

        assert isinstance(feature_array, np.ndarray)
        assert feature_array.shape[1] == len(processor.feature_names)

    def test_extract_features_from_match_data(self):
        """测试从比赛数据提取特征"""
        from src.models.prediction.feature_processor import FeatureProcessor

        processor = FeatureProcessor()
        match_data = {
            "home_team_id": 1,
            "away_team_id": 2,
            "home_team": {
                "strength": 0.7,
                "form": 1.5,
                "goals_scored_avg": 2.0,
                "goals_conceded_avg": 0.5,
            },
            "away_team": {
                "strength": 0.5,
                "form": 0.5,
                "goals_scored_avg": 1.0,
                "goals_conceded_avg": 1.5,
            },
        }

        features = processor.extract_features_from_match_data(match_data)

        assert isinstance(features, dict)
        assert features["home_team_strength"] == 0.7
        assert features["away_team_strength"] == 0.5

    def test_validate_features(self):
        """测试验证特征"""
        from src.models.prediction.feature_processor import FeatureProcessor

        processor = FeatureProcessor()
        features = processor.get_default_features()

        assert processor.validate_features(features)

        # 测试无效特征
        invalid_features = {"invalid_feature": 1.0}
        assert not processor.validate_features(invalid_features)


class TestPredictionService:
    """测试预测服务"""

    def test_prediction_service_import(self):
        """测试预测服务导入"""
        from src.models.prediction.service import PredictionService

        assert PredictionService is not None

    def test_prediction_service_init(self):
        """测试预测服务初始化"""
        from src.models.prediction.service import PredictionService

        service = PredictionService("http://localhost:5002")
        assert service.mlflow_client is not None
        assert service.cache is not None
        assert service.feature_processor is not None

    @pytest.mark.asyncio
    async def test_get_production_model(self):
        """测试获取生产模型"""
        from src.models.prediction.service import PredictionService

        service = PredictionService()
        mock_model = MagicMock()

        with patch.object(
            service.mlflow_client, "get_production_model"
        ) as mock_get_model:
            mock_get_model.return_value = (mock_model, "v1.0.0")

            model, version = await service.get_production_model()
            assert model == mock_model
            assert version == "v1.0.0"

    @pytest.mark.asyncio
    async def test_predict_match(self):
        """测试预测比赛"""
        from src.models.prediction.service import PredictionService
        from src.models.prediction.models import PredictionResult

        service = PredictionService()
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.1, 0.3, 0.6]]
        mock_model.predict.return_value = ["home"]

        with patch.object(service, "get_production_model") as mock_get_model:
            with patch.object(service, "_get_match_info") as mock_get_match:
                with patch.object(service, "_get_features") as mock_get_features:
                    with patch.object(service, "_store_prediction"):
                        mock_get_model.return_value = (mock_model, "v1.0.0")
                        mock_get_match.return_value = {
                            "id": 12345,
                            "home_team_id": 1,
                            "away_team_id": 2,
                            "match_status": "SCHEDULED",
                        }
                        mock_get_features.return_value = {
                            "home_team_strength": 0.7,
                            "away_team_strength": 0.5,
                        }

                        result = await service.predict_match(12345)
                        assert isinstance(result, PredictionResult)
                        assert result.match_id == 12345
                        assert result.predicted_result == "home"

    @pytest.mark.asyncio
    async def test_batch_predict_matches(self):
        """测试批量预测比赛"""
        from src.models.prediction.service import PredictionService

        service = PredictionService()
        mock_result = MagicMock()

        with patch.object(service, "predict_match") as mock_predict:
            mock_predict.return_value = mock_result

            results = await service.batch_predict_matches([12345, 12346])
            assert len(results) == 2
            mock_predict.assert_called()

    @pytest.mark.asyncio
    async def test_verify_prediction(self):
        """测试验证预测"""
        from src.models.prediction.service import PredictionService

        service = PredictionService()

        with patch.object(service.db_manager, "get_async_session") as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.first.return_value = (
                2,
                1,
                "home",  # home_score, away_score, predicted_result
            )

            result = await service.verify_prediction(12345)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_prediction_statistics(self):
        """测试获取预测统计"""
        from src.models.prediction.service import PredictionService

        service = PredictionService()

        with patch.object(service.db_manager, "get_async_session") as mock_session:
            mock_row = MagicMock()
            mock_row.total_predictions = 100
            mock_row.correct_predictions = 60
            mock_row.avg_confidence = 0.75
            mock_row.model_versions_used = 3
            mock_session.return_value.__aenter__.return_value.execute.return_value.first.return_value = mock_row

            stats = await service.get_prediction_statistics(30)
            assert "total_predictions" in stats
            assert stats["accuracy"] == 0.6


class TestModularStructure:
    """测试模块化结构"""

    def test_import_from_main_module(self):
        """测试从主模块导入"""
        from src.models.prediction import (
            PredictionResult,
            PredictionService,
            PredictionCache,
            predictions_total,
        )

        assert PredictionResult is not None
        assert PredictionService is not None
        assert PredictionCache is not None
        assert predictions_total is not None

    def test_backward_compatibility_imports(self):
        """测试向后兼容性导入"""
        # 从原始文件导入应该仍然有效
        from src.models.prediction_service import (
            PredictionResult as old_result,
            PredictionService as old_service,
        )

        assert old_result is not None
        assert old_service is not None

    def test_all_classes_are_exported(self):
        """测试所有类都被导出"""
        from src.models.prediction import __all__

        expected_exports = [
            "PredictionResult",
            "PredictionService",
            "PredictionCache",
            "predictions_total",
            "prediction_duration_seconds",
            "prediction_accuracy",
            "model_load_duration_seconds",
            "cache_hit_ratio",
        ]

        for export in expected_exports:
            assert export in __all__

    def test_module_structure(self):
        """测试模块结构"""
        import src.models.prediction as prediction_module

        # 验证子模块存在
        assert hasattr(prediction_module, "models")
        assert hasattr(prediction_module, "service")
        assert hasattr(prediction_module, "cache")
        assert hasattr(prediction_module, "metrics")
        assert hasattr(prediction_module, "mlflow_client")
        assert hasattr(prediction_module, "feature_processor")


@pytest.mark.asyncio
async def test_integration_example():
    """测试集成示例"""
    from src.models.prediction import PredictionService, PredictionResult

    # 验证PredictionService可以正常使用
    service = PredictionService()
    assert hasattr(service, "predict_match")
    assert hasattr(service, "batch_predict_matches")
    assert hasattr(service, "verify_prediction")

    # 验证PredictionResult可以正常使用
    result = PredictionResult(
        match_id=12345,
        model_version="v1.0.0",
        home_win_probability=0.5,
        draw_probability=0.3,
        away_win_probability=0.2,
        predicted_result="home",
        confidence_score=0.75,
    )

    assert result.match_id == 12345
    assert result.predicted_result == "home"
    assert result.is_probabilities_valid()
