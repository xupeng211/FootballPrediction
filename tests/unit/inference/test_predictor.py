"""
Unit Tests for Predictor
预测器单元测试
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.inference.predictor import Predictor, PredictionResult
from src.inference.schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    ModelType,
    PredictionType,
)
from src.inference.errors import PredictionError


@pytest.fixture
async def mock_model_loader():
    """模拟模型加载器"""
    loader = AsyncMock()
    mock_model = Mock()
    mock_loaded_model = Mock()
    mock_loaded_model.model = mock_model
    mock_loaded_model.metadata.model_info.model_name = "test_model"
    mock_loaded_model.metadata.model_info.model_version = "1.0.0"
    mock_loaded_model.metadata.model_info.model_type = ModelType.XGBOOST
    mock_loaded_model.metadata.model_info.features = ["home_goals", "away_goals"]
    loader.get.return_value = mock_loaded_model
    return loader


@pytest.fixture
async def mock_feature_builder():
    """模拟特征构建器"""
    builder = AsyncMock()
    import pandas as pd
    mock_features_df = pd.DataFrame({
        "home_goals": [2],
        "away_goals": [1],
        "home_possession": [60.0],
        "away_possession": [40.0]
    })
    builder.build_features.return_value = mock_features_df
    return builder


@pytest.fixture
async def mock_cache():
    """模拟缓存"""
    cache = AsyncMock()
    cache.get_prediction.return_value = None
    cache.set_prediction.return_value = True
    return cache


@pytest.fixture
async def predictor(mock_model_loader, mock_feature_builder, mock_cache):
    """创建预测器实例"""
    with patch('src.inference.predictor.get_model_loader', return_value=mock_model_loader), \
         patch('src.inference.predictor.get_feature_builder', return_value=mock_feature_builder), \
         patch('src.inference.predictor.get_prediction_cache', return_value=mock_cache):
        predictor = Predictor()
        yield predictor
        await predictor.cleanup()


class TestPredictor:
    """预测器测试"""

    @pytest.mark.asyncio
    async def test_predict_success(self, predictor, mock_model_loader, mock_feature_builder):
        """测试成功预测"""
        request = PredictionRequest(
            match_id="test_match_001",
            model_name="test_model",
            features={"home_goals": 2, "away_goals": 1}
        )

        # 模拟模型预测返回
        mock_model_loader.get.return_value.model.predict_proba.return_value = np.array([[0.1, 0.3, 0.6]])

        result = await predictor.predict(request)

        assert isinstance(result, PredictionResponse)
        assert result.match_id == "test_match_001"
        assert result.model_name == "test_model"
        assert result.home_win_prob == 0.6
        assert result.draw_prob == 0.3
        assert result.away_win_prob == 0.1
        assert result.predicted_outcome == "home_win"

    @pytest.mark.asyncio
    async def test_predict_from_cache(self, predictor, mock_cache):
        """测试从缓存获取预测结果"""
        request = PredictionRequest(
            match_id="test_match_001",
            model_name="test_model"
        )

        # 模拟缓存命中
        cached_result = PredictionResult(
            home_win_prob=0.7,
            draw_prob=0.2,
            away_win_prob=0.1,
            predicted_outcome="home_win",
            confidence=0.75,
            model_name="test_model",
            model_version="1.0.0",
            model_type=ModelType.XGBOOST,
            features_used=["home_goals", "away_goals"],
            prediction_time_ms=45.0
        ).to_response("req_123", "test_match_001")

        mock_cache.get_prediction.return_value = cached_result.model_dump()

        result = await predictor.predict(request)

        assert result.cached is True
        assert result.home_win_prob == 0.7
        # 验证模型加载器没有被调用（因为来自缓存）
        from src.inference.predictor import get_model_loader
        get_model_loader.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_predict_batch_success(self, predictor):
        """测试批量预测成功"""
        request = BatchPredictionRequest(
            requests=[
                PredictionRequest(
                    match_id="test_match_001",
                    model_name="test_model",
                    features={"home_goals": 2, "away_goals": 1}
                ),
                PredictionRequest(
                    match_id="test_match_002",
                    model_name="test_model",
                    features={"home_goals": 1, "away_goals": 2}
                )
            ],
            parallel=True
        )

        # 模拟模型预测返回
        with patch('src.inference.predictor.get_model_loader') as mock_get_loader:
            mock_model = Mock()
            mock_model.predict_proba.return_value = np.array([[0.1, 0.3, 0.6]])
            mock_loaded_model = Mock()
            mock_loaded_model.model = mock_model
            mock_loaded_model.metadata.model_info.model_name = "test_model"
            mock_loaded_model.metadata.model_info.model_version = "1.0.0"
            mock_loaded_model.metadata.model_info.model_type = ModelType.XGBOOST
            mock_loaded_model.metadata.model_info.features = ["home_goals", "away_goals"]
            mock_get_loader.return_value.get.return_value = mock_loaded_model

            result = await predictor.predict_batch(request)

        assert isinstance(result, BatchPredictionResponse)
        assert result.total_requests == 2
        assert result.successful_predictions >= 0
        assert len(result.predictions) == result.successful_predictions

    @pytest.mark.asyncio
    async def test_predict_model_error(self, predictor):
        """测试模型错误"""
        request = PredictionRequest(
            match_id="test_match_001",
            model_name="nonexistent_model"
        )

        # 模拟模型加载失败
        from src.inference.errors import ModelLoadError
        with patch('src.inference.predictor.get_model_loader') as mock_get_loader:
            mock_get_loader.return_value.get.side_effect = ModelLoadError("Model not found")

            with pytest.raises(PredictionError):
                await predictor.predict(request)

    @pytest.mark.asyncio
    async def test_predict_feature_error(self, predictor):
        """测试特征构建错误"""
        request = PredictionRequest(
            match_id="test_match_001",
            model_name="test_model"
        )

        # 模拟特征构建失败
        with patch('src.inference.predictor.get_feature_builder') as mock_get_builder:
            mock_get_builder.return_value.build_features.side_effect = Exception("Feature build failed")

            with pytest.raises(PredictionError):
                await predictor.predict(request)

    def test_prediction_result_validation(self):
        """测试预测结果验证"""
        # 测试概率和不为1的情况
        result = PredictionResult(
            home_win_prob=0.7,
            draw_prob=0.3,
            away_win_prob=0.1,  # 总和为1.1
            predicted_outcome="home_win",
            confidence=0.6,
            model_name="test_model",
            model_version="1.0.0",
            model_type=ModelType.XGBOOST,
            features_used=["home_goals"],
            prediction_time_ms=50.0
        )

        # 验证概率被归一化
        assert abs(result.home_win_prob + result.draw_prob + result.away_win_prob - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_predict_with_different_prediction_types(self, predictor):
        """测试不同预测类型"""
        request = PredictionRequest(
            match_id="test_match_001",
            model_name="test_model",
            prediction_type=PredictionType.WINNER,
            features={"home_goals": 2, "away_goals": 1}
        )

        # 模拟模型预测返回
        with patch('src.inference.predictor.get_model_loader') as mock_get_loader:
            mock_model = Mock()
            # 模拟返回胜者预测（假设2表示home_win）
            mock_model.predict.return_value = np.array([2])
            mock_model.predict_proba.return_value = np.array([[0.1, 0.3, 0.6]])
            mock_loaded_model = Mock()
            mock_loaded_model.model = mock_model
            mock_loaded_model.metadata.model_info.model_name = "test_model"
            mock_loaded_model.metadata.model_info.model_version = "1.0.0"
            mock_loaded_model.metadata.model_info.model_type = ModelType.XGBOOST
            mock_loaded_model.metadata.model_info.features = ["home_goals", "away_goals"]
            mock_get_loader.return_value.get.return_value = mock_loaded_model

            result = await predictor.predict(request)

        assert result.predicted_outcome in ["home_win", "draw", "away_win"]
        assert 0.0 <= result.home_win_prob <= 1.0
        assert 0.0 <= result.draw_prob <= 1.0
        assert 0.0 <= result.away_win_prob <= 1.0

    @pytest.mark.asyncio
    async def test_get_prediction_stats(self, predictor):
        """测试获取预测统计"""
        stats = predictor.get_prediction_stats()

        assert "total_predictions" in stats
        assert "successful_predictions" in stats
        assert "failed_predictions" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "success_rate" in stats
        assert "cache_hit_rate" in stats

    @pytest.mark.asyncio
    async def test_generate_cache_key(self, predictor):
        """测试缓存键生成"""
        request = PredictionRequest(
            match_id="test_match_001",
            model_name="test_model",
            model_version="1.0.0",
            prediction_type=PredictionType.PROBABILITY
        )

        cache_key = predictor._generate_cache_key(request)

        assert "prediction:test_match_001:test_model:1.0.0:probability" in cache_key

        # 测试带自定义特征的缓存键
        request.features = {"home_goals": 2}
        cache_key_with_features = predictor._generate_cache_key(request)
        assert len(cache_key_with_features) > len(cache_key)  # 应该包含特征哈希

    @pytest.mark.asyncio
    async def test_post_process_prediction_calibration(self, predictor):
        """测试预测结果校准"""
        # 创建预测结果
        prediction_result = {
            "home_win_prob": 0.6,
            "draw_prob": 0.3,
            "away_win_prob": 0.1,
            "metadata": {}
        }

        # 模拟需要校准的模型
        mock_loaded_model = Mock()
        mock_loaded_model.metadata.model_info.model_type = ModelType.XGBOOST
        mock_loaded_model.metadata.model_info.accuracy = 0.7

        # 模拟请求
        request = PredictionRequest(
            match_id="test_match",
            model_name="test_model",
            prediction_type=PredictionType.PROBABILITY
        )

        processed_result = await predictor._post_process_prediction(
            prediction_result,
            mock_loaded_model,
            request
        )

        assert "predicted_outcome" in processed_result
        assert "confidence" in processed_result
        assert "metadata" in processed_result
        assert processed_result["metadata"]["calibration_applied"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
