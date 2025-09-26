"""
from unittest.mock import AsyncMock, Mock, patch
import asyncio
预测服务全面测试
重点解决实际业务问题，同时提升测试覆盖率
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from src.models.prediction_service import PredictionResult, PredictionService


class TestPredictionResult:
    """测试预测结果数据类"""

    def test_prediction_result_creation(self):
        """测试预测结果创建"""
        result = PredictionResult(
            match_id=123,
            model_version="1.0.0",
            home_win_probability=0.6,
            draw_probability=0.3,
            away_win_probability=0.1,
            predicted_result="home",
            confidence_score=0.6,
        )

    assert result.match_id == 123
    assert result.model_version == "1.0.0"
    assert result.predicted_result == "home"
    assert result.confidence_score == 0.6

    def test_prediction_result_to_dict(self):
        """测试预测结果转换为字典"""
        created_at = datetime.now()
        result = PredictionResult(
            match_id=123, model_version="1.0.0", created_at=created_at
        )

        result_dict = result.to_dict()

    assert result_dict["match_id"] == 123
    assert result_dict["model_version"] == "1.0.0"
    assert result_dict["created_at"] == created_at.isoformat()
    assert "home_win_probability" in result_dict
    assert "draw_probability" in result_dict
    assert "away_win_probability" in result_dict

    def test_prediction_result_validation_probabilities_sum(self):
        """测试预测概率总和验证（业务逻辑测试）"""
        result = PredictionResult(
            match_id=123,
            model_version="1.0.0",
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2,
        )

        total_prob = (
            result.home_win_probability
            + result.draw_probability
            + result.away_win_probability
        )

        # 业务规则：概率总和应该接近1.0
    assert abs(total_prob - 1.0) < 0.01


class TestPredictionService:
    """测试预测服务核心功能"""

    @pytest.fixture
    def mock_dependencies(self):
        """模拟依赖项"""
        with patch("src.models.prediction_service.DatabaseManager") as mock_db, patch(
            "src.models.prediction_service.FootballFeatureStore"
        ) as mock_fs, patch(
            "src.models.prediction_service.ModelMetricsExporter"
        ) as mock_metrics, patch(
            "src.models.prediction_service.mlflow"
        ) as mock_mlflow:
            yield {
                "db": mock_db,
                "feature_store": mock_fs,
                "metrics": mock_metrics,
                "mlflow": mock_mlflow,
            }

    def test_prediction_service_initialization(self, mock_dependencies):
        """测试预测服务初始化"""
        service = PredictionService(mlflow_tracking_uri="http:_/test:5002")

    assert service.mlflow_tracking_uri == "http://test:5002"
    assert isinstance(service.model_cache, dict)
    assert isinstance(service.model_metadata_cache, dict)
        mock_dependencies["mlflow"].set_tracking_uri.assert_called_with(
            "http://test:5002"
        )

    @pytest.mark.asyncio
    async def test_get_production_model_success(self, mock_dependencies):
        """测试成功获取生产模型"""
        # 模拟MLflow客户端
        mock_client = Mock()
        mock_version_info = Mock()
        mock_version_info.version = "1.0.0"
        mock_version_info.current_stage = "Production"
        mock_client.get_latest_versions.return_value = [mock_version_info]

        mock_model = Mock()

        with patch(
            "src.models.prediction_service.MlflowClient", return_value=mock_client
        ), patch(
            "src.models.prediction_service.mlflow.sklearn.load_model",
            return_value=mock_model,
        ):
            service = PredictionService()
            model, version = await service.get_production_model("test_model")

    assert model == mock_model
    assert version == "1.0.0"
    assert "models:_test_model/1.0.0" in service.model_cache

    @pytest.mark.asyncio
    async def test_get_production_model_fallback_to_staging(self, mock_dependencies):
        """测试回退到Staging版本（实际业务场景）"""
        mock_client = Mock()
        mock_version_info = Mock()
        mock_version_info.version = "0.9.0"
        mock_version_info.current_stage = "Staging"

        # 第一次调用（Production）返回空，第二次调用（Staging）返回版本
        mock_client.get_latest_versions.side_effect = [[], [mock_version_info]]

        mock_model = Mock()

        with patch(
            "src.models.prediction_service.MlflowClient", return_value=mock_client
        ), patch(
            "src.models.prediction_service.mlflow.sklearn.load_model",
            return_value=mock_model,
        ):
            service = PredictionService()
            model, version = await service.get_production_model("test_model")

    assert version == "0.9.0"
            # 验证调用了两次get_latest_versions（Production和Staging）
    assert mock_client.get_latest_versions.call_count == 2

    @pytest.mark.asyncio
    async def test_get_production_model_no_versions_error(self, mock_dependencies):
        """测试没有可用模型版本的错误处理"""
        mock_client = Mock()
        mock_client.get_latest_versions.return_value = []

        with patch(
            "src.models.prediction_service.MlflowClient", return_value=mock_client
        ):
            service = PredictionService()

            with pytest.raises(ValueError, match="模型 test_model 没有可用版本"):
                await service.get_production_model("test_model")

    @pytest.mark.asyncio
    async def test_get_production_model_caching(self, mock_dependencies):
        """测试模型缓存机制（性能优化测试）"""
        mock_client = Mock()
        mock_version_info = Mock()
        mock_version_info.version = "1.0.0"
        mock_version_info.current_stage = "Production"
        mock_client.get_latest_versions.return_value = [mock_version_info]

        mock_model = Mock()

        with patch(
            "src.models.prediction_service.MlflowClient", return_value=mock_client
        ), patch(
            "src.models.prediction_service.mlflow.sklearn.load_model",
            return_value=mock_model,
        ) as mock_load:
            service = PredictionService()

            # 第一次调用
            model1, version1 = await service.get_production_model("test_model")
            # 第二次调用（应该使用缓存）
            model2, version2 = await service.get_production_model("test_model")

    assert model1 == model2
    assert version1 == version2
            # 验证只加载了一次模型
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_match_success(self, mock_dependencies):
        """测试成功预测比赛结果"""
        service = PredictionService()

        # 模拟获取模型
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array(
            [[0.2, 0.3, 0.5]]
        )  # [away, draw, home]
        mock_model.predict.return_value = np.array(["home"])

        # 模拟比赛信息
        mock_match_info = {
            "home_team_id": 1,
            "away_team_id": 2,
            "match_date": datetime.now(),
        }

        # 模拟特征数据
        mock_features = {
            "home_team_form": 0.8,
            "away_team_form": 0.6,
            "head_to_head_ratio": 0.7,
        }

        # 创建异步mock
        async def mock_get_features(*args, **kwargs):
            return mock_features

        async def mock_get_match_info(match_id):
            return mock_match_info

        # 模拟异步方法
        service._get_match_info = AsyncMock(return_value=mock_match_info)
        service.feature_store.get_match_features_for_prediction = AsyncMock(
            return_value=mock_features
        )
        service._store_prediction = AsyncMock()
        service.metrics_exporter.export_prediction_metrics = AsyncMock()

        with patch.object(
            service, "get_production_model", return_value=(mock_model, "1.0.0")
        ), patch.object(
            service,
            "_prepare_features_for_prediction",
            return_value=np.array([[0.8, 0.6, 0.7]]),
        ):
            result = await service.predict_match(123)

    assert isinstance(result, PredictionResult)
    assert result.match_id == 123
    assert result.model_version == "1.0.0"
    assert result.predicted_result == "home"
    assert result.home_win_probability == 0.5
    assert result.draw_probability == 0.3
    assert result.away_win_probability == 0.2
    assert result.confidence_score == 0.5  # max probability

    @pytest.mark.asyncio
    async def test_predict_match_no_match_found(self, mock_dependencies):
        """测试比赛不存在的错误处理"""
        service = PredictionService()

        async def mock_get_match_info(match_id):
            return None

        with patch.object(
            service, "get_production_model", return_value=(Mock(), "1.0.0")
        ), patch.object(service, "_get_match_info", side_effect=mock_get_match_info):
            with pytest.raises(ValueError, match="比赛 999 不存在"):
                await service.predict_match(999)

    @pytest.mark.asyncio
    async def test_predict_match_no_features_fallback(self, mock_dependencies):
        """测试无特征时的回退机制（实际业务场景）"""
        service = PredictionService()

        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.33, 0.34, 0.33]])
        mock_model.predict.return_value = np.array(["draw"])

        mock_match_info = {"home_team_id": 1, "away_team_id": 2}
        mock_default_features = {"default_feature": 0.5}

        async def mock_get_match_info(match_id):
            return mock_match_info

        async def mock_get_features(*args, **kwargs):
            return None

        # 模拟异步方法
        service._get_match_info = AsyncMock(return_value=mock_match_info)
        service.feature_store.get_match_features_for_prediction = AsyncMock(
            return_value=None
        )
        service._store_prediction = AsyncMock()
        service.metrics_exporter.export_prediction_metrics = AsyncMock()

        with patch.object(
            service, "get_production_model", return_value=(mock_model, "1.0.0")
        ), patch.object(
            service, "_get_default_features", return_value=mock_default_features
        ), patch.object(
            service, "_prepare_features_for_prediction", return_value=np.array([[0.5]])
        ):
            result = await service.predict_match(123)

    assert result.predicted_result == "draw"
    assert result.features_used == mock_default_features
