"""
推理服务v2测试 - 简化版本
基于实际InferenceService接口编写的测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.services.prediction_service import (
    PredictionRequest,
    PredictionResponse,
)
from src.services.inference_service import InferenceService


class TestInferenceServiceSimple:
    """V2推理服务简化测试"""

    @pytest.fixture
    def inference_service(self):
        """推理服务实例"""
        return InferenceService(model_path="test_model_path")

    def test_service_initialization(self, inference_service):
        """测试服务初始化"""
        # 检查组件是否正确初始化
        assert inference_service.model_loader is not None
        assert inference_service.cache_manager is not None
        assert inference_service.feature_extractor is not None
        assert inference_service.default_model_path == "test_model_path"
        assert inference_service.default_model_name == "football_model"
        assert not inference_service.is_initialized

    @pytest.mark.asyncio
    async def test_service_initialize(self, inference_service):
        """测试服务初始化流程"""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(inference_service, "_load_model_async", return_value=True),
            patch.object(
                inference_service.feature_extractor, "initialize", return_value=None
            ),
        ):

            result = await inference_service.initialize()

            assert result is True
            assert inference_service.is_initialized

    @pytest.mark.asyncio
    async def test_service_initialize_fallback(self, inference_service):
        """测试服务初始化降级模式"""
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch.object(
                inference_service.feature_extractor, "initialize", return_value=None
            ),
        ):

            result = await inference_service.initialize()

            assert result is True  # 降级模式应该成功
            assert inference_service.is_initialized

    @pytest.mark.asyncio
    async def test_predict_match_simple(self, inference_service):
        """测试简化预测接口"""
        with (
            patch.object(inference_service, "is_initialized", True),
            patch("src.ml.inference.MatchPredictor") as mock_predictor_class,
        ):

            # Mock预测器
            mock_predictor = Mock()
            mock_predictor.predict = AsyncMock(
                return_value={
                    "prediction": "HOME_WIN",
                    "probabilities": {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1},
                }
            )
            mock_predictor.get_model_info.return_value = {"name": "test_model"}
            mock_predictor_class.return_value = mock_predictor

            result = await inference_service.predict_match_simple(
                match_id="123", home_team="Manchester United", away_team="Arsenal"
            )

            # 验证结果结构
            assert isinstance(result, dict)
            assert "request" in result
            assert "prediction" in result
            assert "success" in result
            assert "timestamp" in result

            assert result["success"] is True
            assert result["prediction"]["prediction"] == "HOME_WIN"
            assert result["request"]["home_team"] == "Manchester United"
            assert result["request"]["away_team"] == "Arsenal"

    @pytest.mark.asyncio
    async def test_predict_match_not_initialized(self, inference_service):
        """测试服务未初始化时的预测"""
        with patch.object(inference_service, "is_initialized", False):
            result = await inference_service.predict_match_simple(
                match_id="123", home_team="Team A", away_team="Team B"
            )

            assert result["success"] is False
            assert "服务未初始化" in result["error"]

    @pytest.mark.asyncio
    async def test_predict_match_with_request_object(self, inference_service):
        """测试使用请求对象预测"""
        with (
            patch.object(inference_service, "is_initialized", True),
            patch("src.ml.inference.MatchPredictor") as mock_predictor_class,
        ):

            # Mock预测器
            mock_predictor = Mock()
            mock_predictor.predict = AsyncMock(
                return_value={
                    "prediction": "DRAW",
                    "probabilities": {"HOME_WIN": 0.2, "DRAW": 0.5, "AWAY_WIN": 0.3},
                }
            )
            mock_predictor.get_model_info.return_value = {"name": "test_model"}
            mock_predictor_class.return_value = mock_predictor

            request = PredictionRequest(
                match_id="456",
                home_team="Liverpool",
                away_team="Chelsea",
                features=[1.0, 2.0, 3.0],
            )

            response = await inference_service.predict_match(request)

            assert isinstance(response, PredictionResponse)
            assert response.success is True
            assert response.prediction["prediction"] == "DRAW"
            assert response.request.home_team == "Liverpool"

    @pytest.mark.asyncio
    async def test_batch_predict(self, inference_service):
        """测试批量预测"""
        with (
            patch.object(inference_service, "is_initialized", True),
            patch("src.ml.inference.MatchPredictor") as mock_predictor_class,
        ):

            # Mock预测器
            mock_predictor = Mock()
            mock_predictor.predict = AsyncMock(
                return_value={
                    "prediction": "HOME_WIN",
                    "probabilities": {"HOME_WIN": 0.7, "DRAW": 0.2, "AWAY_WIN": 0.1},
                }
            )
            mock_predictor.get_model_info.return_value = {"name": "test_model"}
            mock_predictor_class.return_value = mock_predictor

            requests = [
                PredictionRequest(match_id="1", home_team="Team A", away_team="Team B"),
                PredictionRequest(match_id="2", home_team="Team C", away_team="Team D"),
            ]

            responses = await inference_service.batch_predict(requests)

            assert len(responses) == 2
            assert all(isinstance(r, PredictionResponse) for r in responses)

    def test_get_service_stats(self, inference_service):
        """测试获取服务统计"""
        stats = inference_service.get_service_stats()

        assert isinstance(stats, dict)
        assert "service_name" in stats
        assert "is_initialized" in stats
        assert "model_status" in stats
        assert "request_stats" in stats
        assert "components" in stats

        assert stats["service_name"] == "InferenceService"
        assert not stats["is_initialized"]

    def test_load_model(self, inference_service):
        """测试模型加载"""
        with patch.object(
            inference_service.model_loader, "load_model", return_value=True
        ):
            result = inference_service.load_model("test_model", "test_path.pkl")

            assert result is True

    def test_load_model_failure(self, inference_service):
        """测试模型加载失败"""
        with patch.object(
            inference_service.model_loader, "load_model", return_value=False
        ):
            result = inference_service.load_model("test_model", "invalid_path.pkl")

            assert result is False

    def test_unload_model(self, inference_service):
        """测试模型卸载"""
        with patch.object(
            inference_service.model_loader, "unload_model", return_value=True
        ):
            result = inference_service.unload_model("test_model")

            assert result is True

    def test_list_models(self, inference_service):
        """测试列出模型"""
        with patch.object(
            inference_service.model_loader,
            "list_loaded_models",
            return_value=["model1", "model2"],
        ):
            models = inference_service.list_models()

            assert isinstance(models, list)
            assert len(models) == 2
            assert "model1" in models

    @pytest.mark.asyncio
    async def test_shutdown(self, inference_service):
        """测试服务关闭"""
        with (
            patch.object(inference_service.cache_manager, "shutdown", AsyncMock()),
            patch.object(inference_service.feature_extractor, "shutdown", AsyncMock()),
        ):

            await inference_service.shutdown()

            assert not inference_service.is_initialized

    def test_prediction_request_to_dict(self):
        """测试预测请求转换"""
        request = PredictionRequest(
            match_id="123",
            home_team="Team A",
            away_team="Team B",
            features=[1.0, 2.0, 3.0],
            model_name="test_model",
        )

        request_dict = request.to_dict()

        assert request_dict["match_id"] == "123"
        assert request_dict["home_team"] == "Team A"
        assert request_dict["away_team"] == "Team B"
        assert request_dict["features"] == [1.0, 2.0, 3.0]
        assert request_dict["model_name"] == "test_model"
        assert request_dict["use_cache"] is True

    def test_prediction_response_to_dict(self):
        """测试预测响应转换"""
        request = PredictionRequest(
            match_id="123", home_team="Team A", away_team="Team B"
        )

        response = PredictionResponse(
            request=request,
            prediction={"prediction": "HOME_WIN"},
            success=True,
            processing_time_ms=100.0,
            cached=True,
        )

        response_dict = response.to_dict()

        assert response_dict["success"] is True
        assert response_dict["prediction"]["prediction"] == "HOME_WIN"
        assert response_dict["processing_time_ms"] == 100.0
        assert response_dict["cached"] is True
        assert "timestamp" in response_dict
        assert response_dict["request"]["match_id"] == "123"

    def test_request_stats_initialization(self, inference_service):
        """测试请求统计初始化"""
        stats = inference_service.request_stats

        assert stats["total_requests"] == 0
        assert stats["successful_predictions"] == 0
        assert stats["cache_hits"] == 0
        assert stats["errors"] == 0
        assert stats["avg_processing_time_ms"] == 0.0

    @pytest.mark.asyncio
    async def test_feature_generation_fallback(self, inference_service):
        """测试特征生成降级处理"""
        with (
            patch.object(inference_service, "is_initialized", True),
            patch("src.ml.inference.MatchPredictor") as mock_predictor_class,
            patch.object(
                inference_service.feature_extractor,
                "extract_features_from_match",
                side_effect=Exception("Feature extraction failed"),
            ),
        ):

            # Mock预测器
            mock_predictor = Mock()
            mock_predictor.predict = AsyncMock(
                return_value={
                    "prediction": "HOME_WIN",
                    "probabilities": {"HOME_WIN": 0.4, "DRAW": 0.3, "AWAY_WIN": 0.3},
                }
            )
            mock_predictor.get_model_info.return_value = {"name": "test_model"}
            mock_predictor_class.return_value = mock_predictor

            request = PredictionRequest(
                match_id="789",
                home_team="Team X",
                away_team="Team Y",
                # 没有提供features，需要生成
            )

            response = await inference_service.predict_match(request)

            # 即使特征生成失败，也应该使用默认特征继续
            assert response.success is True
            mock_predictor.predict.assert_called_once()

            # 检查是否使用了默认特征（12个1.0）
            call_args = mock_predictor.predict.call_args
            features = call_args[1]["features"]
            assert features == [1.0] * 12
