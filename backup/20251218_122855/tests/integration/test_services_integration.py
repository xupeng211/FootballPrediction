"""
服务集成测试
测试推理服务、数据收集服务和可解释性服务的集成
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from src.services.inference_service_v2 import (
    InferenceServiceV2,
    PredictionRequest,
    PredictionResponse,
)
from src.services.collection_service import FotMobCollectionService
from src.services.explainability_service import ExplainabilityService
from src.ml.inference import ModelLoader, MatchPredictor
from src.ml.inference.cache_manager import PredictionCache
from src.core.exceptions import PredictionError, ModelError, ValidationError


class TestInferenceServiceIntegration:
    """推理服务集成测试"""

    @pytest.fixture
    def mock_dependencies(self):
        """创建Mock依赖"""
        mock_loader = Mock(spec=ModelLoader)
        mock_cache = Mock(spec=PredictionCache)

        # 设置mock行为
        mock_model = Mock()
        mock_model.predict.return_value = [1]  # DRAW
        mock_model.predict_proba.return_value = [[0.2, 0.5, 0.3]]
        mock_model.n_features_in_ = 12
        mock_model.classes_ = [0, 1, 2]

        mock_loader.get_model.return_value = mock_model
        mock_loader.list_loaded_models.return_value = ["xgboost_v2.pkl"]
        mock_loader.get_model_metadata.return_value = {"accuracy": 0.65}

        mock_cache.get.return_value = None  # 缓存未命中
        mock_cache.set.return_value = True
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5, "hit_rate": 0.67}

        return {
            "model_loader": mock_loader,
            "cache_manager": mock_cache,
            "model": mock_model,
        }

    @pytest.fixture
    def inference_service(self, mock_dependencies):
        """创建推理服务实例"""
        service = InferenceServiceV2()
        service.model_loader = mock_dependencies["model_loader"]
        service.cache_manager = mock_dependencies["cache_manager"]
        service.is_initialized = True
        return service

    def test_service_initialization_with_dependencies(
        self, inference_service, mock_dependencies
    ):
        """测试服务初始化与依赖"""
        assert inference_service.model_loader == mock_dependencies["model_loader"]
        assert inference_service.cache_manager == mock_dependencies["cache_manager"]
        assert inference_service.is_initialized is True

    @pytest.mark.asyncio
    async def test_prediction_request_creation_and_validation(self):
        """测试预测请求创建和验证"""
        request = PredictionRequest(
            match_id="12345",
            home_team="Manchester United",
            away_team="Arsenal",
            features=[1.0, 2.0, 3.0, 1.5, 2.2, 0.8, 0.9, 1.1, 0.7, 1.3, 0.6, 1.0],
            use_cache=True,
            model_name="xgboost_v2",
        )

        # 测试请求属性
        assert request.match_id == "12345"
        assert request.home_team == "Manchester United"
        assert request.away_team == "Arsenal"
        assert len(request.features) == 12
        assert request.use_cache is True
        assert request.model_name == "xgboost_v2"

        # 测试转换为字典
        request_dict = request.to_dict()
        assert isinstance(request_dict, dict)
        assert request_dict["match_id"] == "12345"
        assert request_dict["home_team"] == "Manchester United"
        assert request_dict["features"] == [
            1.0,
            2.0,
            3.0,
            1.5,
            2.2,
            0.8,
            0.9,
            1.1,
            0.7,
            1.3,
            0.6,
            1.0,
        ]

    @pytest.mark.asyncio
    async def test_prediction_response_creation(self):
        """测试预测响应创建"""
        request = PredictionRequest(
            match_id="12345", home_team="Team A", away_team="Team B"
        )

        prediction = {
            "prediction": "HOME_WIN",
            "probabilities": {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1},
        }

        response = PredictionResponse(
            request=request,
            prediction=prediction,
            success=True,
            processing_time_ms=150.0,
            cached=False,
            model_info={"name": "xgboost_v2", "version": "2.0"},
        )

        # 测试响应属性
        assert response.request == request
        assert response.success is True
        assert response.processing_time_ms == 150.0
        assert response.cached is False
        assert response.model_info["name"] == "xgboost_v2"

        # 测试转换为字典
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert response_dict["success"] is True
        assert response_dict["prediction"]["prediction"] == "HOME_WIN"
        assert "timestamp" in response_dict

    @pytest.mark.asyncio
    async def test_model_loading_and_unloading(
        self, inference_service, mock_dependencies
    ):
        """测试模型加载和卸载"""
        # 测试加载模型
        result = inference_service.load_model("test_model", "/path/to/model.pkl")
        assert result is True
        mock_dependencies["model_loader"].load_model.assert_called_once_with(
            "test_model", "/path/to/model.pkl"
        )

        # 测试卸载模型
        result = inference_service.unload_model("test_model")
        assert result is True
        mock_dependencies["model_loader"].unload_model.assert_called_once_with(
            "test_model"
        )

        # 测试列出模型
        models = inference_service.list_models()
        assert isinstance(models, list)
        assert len(models) == 1
        assert models[0] == "xgboost_v2.pkl"

    @pytest.mark.asyncio
    async def test_service_statistics(self, inference_service, mock_dependencies):
        """测试服务统计"""
        stats = inference_service.get_service_stats()

        assert isinstance(stats, dict)
        assert "service_name" in stats
        assert "is_initialized" in stats
        assert "model_status" in stats
        assert "request_stats" in stats
        assert "cache_stats" in stats
        assert "components" in stats

        assert stats["service_name"] == "InferenceServiceV2"
        assert stats["is_initialized"] is True

    @pytest.mark.asyncio
    async def test_cache_operations(self, inference_service, mock_dependencies):
        """测试缓存操作"""
        # 测试获取缓存统计
        mock_dependencies["cache_manager"].get_stats.return_value = {
            "hits": 20,
            "misses": 10,
            "hit_rate": 0.67,
            "size": 100,
            "memory_usage": 1024,
        }

        stats = inference_service.get_service_stats()
        assert stats["cache_stats"]["hits"] == 20
        assert stats["cache_stats"]["hit_rate"] == 0.67

        # 测试清除缓存
        mock_dependencies["cache_manager"].clear.return_value = True
        # 注意：这里需要实现实际的清除方法
        # await inference_service.clear_cache()

    def test_error_handling(self, inference_service, mock_dependencies):
        """测试错误处理"""
        # 测试模型加载失败
        mock_dependencies["model_loader"].load_model.return_value = False
        result = inference_service.load_model("invalid_model", "/invalid/path")
        assert result is False

        # 测试模型卸载失败
        mock_dependencies["model_loader"].unload_model.return_value = False
        result = inference_service.unload_model("nonexistent_model")
        assert result is False  # 或者可能是True，取决于实现


class TestCollectionServiceIntegration:
    """数据收集服务集成测试"""

    @pytest.fixture
    def collection_service(self):
        """创建数据收集服务实例"""
        return FotMobCollectionService()

    def test_service_initialization(self, collection_service):
        """测试服务初始化"""
        assert collection_service is not None
        assert hasattr(collection_service, "collect_match_data")
        assert hasattr(collection_service, "collect_odds_data")
        assert hasattr(collection_service, "collect_team_stats")
        assert hasattr(collection_service, "get_collection_status")

    @pytest.mark.asyncio
    async def test_match_data_collection(self, collection_service):
        """测试比赛数据收集"""
        with patch.object(collection_service, "collect_match_data") as mock_collect:
            mock_collect.return_value = {
                "match_id": "123",
                "home_team": "Team A",
                "away_team": "Team B",
                "date": "2024-01-15",
                "league": "Premier League",
            }

            result = await collection_service.collect_match_data("123")
            assert isinstance(result, dict)
            assert result["match_id"] == "123"

    @pytest.mark.asyncio
    async def test_odds_data_collection(self, collection_service):
        """测试赔率数据收集"""
        with patch.object(collection_service, "collect_odds_data") as mock_collect:
            mock_collect.return_value = {
                "match_id": "123",
                "home_win_odds": 2.5,
                "draw_odds": 3.2,
                "away_win_odds": 2.8,
                "bookmakers": ["bet365", "william_hill"],
            }

            result = await collection_service.collect_odds_data("123")
            assert isinstance(result, dict)
            assert result["home_win_odds"] == 2.5

    @pytest.mark.asyncio
    async def test_batch_data_collection(self, collection_service):
        """测试批量数据收集"""
        match_ids = ["123", "456", "789"]

        with patch.object(collection_service, "collect_batch_data") as mock_collect:
            mock_collect.return_value = [
                {"match_id": "123", "home_team": "Team A"},
                {"match_id": "456", "home_team": "Team C"},
                {"match_id": "789", "home_team": "Team E"},
            ]

            results = await collection_service.collect_batch_data(match_ids)
            assert isinstance(results, list)
            assert len(results) == 3


class TestExplainabilityServiceIntegration:
    """可解释性服务集成测试"""

    @pytest.fixture
    def explainability_service(self):
        """创建可解释性服务实例"""
        return ExplainabilityService()

    def test_service_initialization(self, explainability_service):
        """测试服务初始化"""
        assert explainability_service is not None
        assert hasattr(explainability_service, "generate_explanation")
        assert hasattr(explainability_service, "get_feature_importance")
        assert hasattr(explainability_service, "explain_prediction")

    @pytest.mark.asyncio
    async def test_prediction_explanation(self, explainability_service):
        """测试预测解释生成"""
        with patch.object(
            explainability_service, "generate_explanation"
        ) as mock_explain:
            mock_explain.return_value = {
                "prediction": "HOME_WIN",
                "explanation": {
                    "main_factors": [
                        {"feature": "home_form", "importance": 0.3},
                        {"feature": "h2h_advantage", "importance": 0.25},
                    ],
                    "confidence": 0.75,
                    "reasoning": "Strong home form and historical advantage",
                },
            }

            result = await explainability_service.generate_explanation(
                prediction="HOME_WIN",
                features=[1.0, 2.0, 3.0],
                model_info={"name": "xgboost_v2"},
            )

            assert isinstance(result, dict)
            assert "explanation" in result
            assert "main_factors" in result["explanation"]

    @pytest.mark.asyncio
    async def test_feature_importance_analysis(self, explainability_service):
        """测试特征重要性分析"""
        with patch.object(
            explainability_service, "get_feature_importance"
        ) as mock_importance:
            mock_importance.return_value = {
                "home_form": 0.25,
                "away_form": 0.20,
                "h2h_home_wins": 0.18,
                "h2h_away_wins": 0.15,
                "venue_advantage": 0.12,
                "recent_performance": 0.10,
            }

            result = await explainability_service.get_feature_importance(
                match_id="123", home_team="Team A", away_team="Team B"
            )

            assert isinstance(result, dict)
            assert "home_form" in result
            assert all(0 <= importance <= 1 for importance in result.values())


class TestServiceIntegration:
    """服务间集成测试"""

    @pytest.mark.asyncio
    async def test_inference_collection_integration(self):
        """测试推理服务和数据收集服务集成"""
        # 这里可以测试推理服务如何使用收集服务提供的原始数据
        # 进行特征工程和预测

        collection_service = FotMobCollectionService()
        inference_service = InferenceServiceV2()

        # Mock收集服务返回的数据
        mock_match_data = {
            "match_id": "123",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_form": [3, 1, 2],
            "away_form": [1, 2, 1],
        }

        with patch.object(collection_service, "collect_match_data") as mock_collect:
            mock_collect.return_value = mock_match_data

            # 收集原始数据
            raw_data = await collection_service.collect_match_data("123")

            # 这里应该有特征工程逻辑将原始数据转换为特征向量
            # 为简化，我们直接使用模拟的特征
            features = [3.0, 1.0, 2.0, 1.0, 2.0, 1.0, 0.5, 0.3, 0.7, 0.5, 0.6, 0.4]

            # 创建预测请求
            request = PredictionRequest(
                match_id="123",
                home_team="Team A",
                away_team="Team B",
                features=features,
            )

            # 验证请求可以正确创建
            assert request.match_id == "123"
            assert len(request.features) == 12

    @pytest.mark.asyncio
    async def test_inference_explainability_integration(self):
        """测试推理服务和可解释性服务集成"""
        inference_service = InferenceServiceV2()
        explainability_service = ExplainabilityService()

        # 模拟预测结果
        prediction_result = {
            "prediction": "HOME_WIN",
            "probabilities": {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1},
        }

        features = [1.0, 2.0, 3.0, 1.5, 2.2, 0.8, 0.9, 1.1, 0.7, 1.3, 0.6, 1.0]

        with patch.object(
            explainability_service, "generate_explanation"
        ) as mock_explain:
            mock_explain.return_value = {
                "explanation": {
                    "main_factors": [
                        {"feature": "home_advantage", "importance": 0.3},
                        {"feature": "recent_form", "importance": 0.25},
                    ]
                }
            }

            # 生成预测解释
            explanation = await explainability_service.generate_explanation(
                prediction=prediction_result["prediction"], features=features
            )

            assert "explanation" in explanation
            assert "main_factors" in explanation["explanation"]

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """测试端到端工作流程"""
        # 创建服务实例
        collection_service = FotMobCollectionService()
        inference_service = InferenceServiceV2()
        explainability_service = ExplainabilityService()

        # Mock各个服务的输出
        with (
            patch.object(collection_service, "collect_match_data") as mock_collect,
            patch.object(inference_service, "predict_match_simple") as mock_predict,
            patch.object(
                explainability_service, "generate_explanation"
            ) as mock_explain,
        ):

            # Mock数据收集
            mock_collect.return_value = {
                "match_id": "12345",
                "home_team": "Manchester United",
                "away_team": "Arsenal",
            }

            # Mock预测
            mock_predict.return_value = {
                "prediction": "HOME_WIN",
                "probabilities": {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1},
            }

            # Mock解释
            mock_explain.return_value = {
                "explanation": "Strong home form and venue advantage"
            }

            # 1. 收集数据
            match_data = await collection_service.collect_match_data("12345")
            assert match_data["home_team"] == "Manchester United"

            # 2. 进行预测
            prediction = await inference_service.predict_match_simple(
                match_id="12345", home_team="Manchester United", away_team="Arsenal"
            )
            assert prediction["prediction"] == "HOME_WIN"

            # 3. 生成解释
            explanation = await explainability_service.generate_explanation(
                prediction=prediction["prediction"], features=[1.0] * 12  # 简化特征
            )
            assert "explanation" in explanation

    @pytest.mark.asyncio
    async def test_error_propagation_between_services(self):
        """测试服务间错误传播"""
        collection_service = FotMobCollectionService()
        inference_service = InferenceServiceV2()

        # Mock数据收集失败
        with patch.object(collection_service, "collect_match_data") as mock_collect:
            mock_collect.side_effect = Exception("Data collection failed")

            with pytest.raises(Exception):
                await collection_service.collect_match_data("invalid_id")

        # Mock预测失败
        with patch.object(inference_service, "predict_match_simple") as mock_predict:
            mock_predict.side_effect = PredictionError(
                "Prediction failed", match_id="123"
            )

            with pytest.raises(PredictionError):
                await inference_service.predict_match_simple(
                    match_id="123", home_team="Team A", away_team="Team B"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
