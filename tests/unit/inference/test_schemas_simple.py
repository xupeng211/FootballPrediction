"""
Unit Tests for Inference Schemas (Simplified)
推理服务模式定义单元测试（简化版）

测试实际存在的Pydantic模型。
"""

import json
import pytest
from datetime import datetime
from typing import Dict, Any
from pydantic import ValidationError

from src.inference.schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelInfo,
    ErrorResponse,
    ModelType,
    PredictionType
)


class TestModelType:
    """模型类型测试类"""

    def test_model_type_values(self):
        """测试模型类型枚举值"""
        assert ModelType.XGBOOST.value == "xgboost"
        assert ModelType.LSTM.value == "lstm"
        assert ModelType.ENSEMBLE.value == "ensemble"
        assert ModelType.MOCK.value == "mock"

    def test_model_type_creation(self):
        """测试模型类型创建"""
        xgb_type = ModelType("xgboost")
        assert xgb_type == ModelType.XGBOOST

    def test_invalid_model_type(self):
        """测试无效模型类型"""
        with pytest.raises(ValueError):
            ModelType("invalid_model_type")


class TestPredictionType:
    """预测类型测试类"""

    def test_prediction_type_values(self):
        """测试预测类型枚举值"""
        assert PredictionType.WINNER.value == "winner"
        assert PredictionType.SCORE.value == "score"
        assert PredictionType.OVER_UNDER.value == "over_under"
        assert PredictionType.PROBABILITY.value == "probability"

    def test_prediction_type_creation(self):
        """测试预测类型创建"""
        prob_type = PredictionType("probability")
        assert prob_type == PredictionType.PROBABILITY

    def test_invalid_prediction_type(self):
        """测试无效预测类型"""
        with pytest.raises(ValueError):
            PredictionType("invalid_prediction_type")


class TestPredictionRequest:
    """预测请求测试类"""

    def test_valid_prediction_request_minimal(self):
        """测试有效的最小预测请求"""
        data = {
            "match_id": "match_123",
        }

        request = PredictionRequest(**data)

        assert request.match_id == "match_123"
        assert request.model_name == "default"
        assert request.prediction_type == PredictionType.WINNER
        assert request.model_version is None
        assert request.features is None
        assert request.force_recalculate is False

    def test_valid_prediction_request_full(self):
        """测试有效的完整预测请求"""
        data = {
            "match_id": "match_456",
            "model_name": "lstm_v2",
            "prediction_type": "probability",
            "model_version": "2.1.0",
            "features": {
                "home_goals": 2,
                "away_goals": 1,
                "home_possession": 65.5
            },
            "force_recalculate": True
        }

        request = PredictionRequest(**data)

        assert request.match_id == "match_456"
        assert request.model_name == "lstm_v2"
        assert request.prediction_type == PredictionType.PROBABILITY
        assert request.model_version == "2.1.0"
        assert request.features["home_goals"] == 2
        assert request.force_recalculate is True

    def test_invalid_prediction_request_empty_match_id(self):
        """测试无效的预测请求 - 空比赛ID"""
        data = {
            "match_id": "",
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionRequest(**data)

        assert "match_id" in str(exc_info.value)

    def test_prediction_request_serialization(self):
        """测试预测请求序列化"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability",
            features={"home_goals": 2}
        )

        serialized = request.model_dump()

        assert serialized["match_id"] == "match_123"
        assert serialized["prediction_type"] == "probability"
        assert serialized["features"]["home_goals"] == 2

    def test_prediction_request_json_serialization(self):
        """测试预测请求JSON序列化"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability"
        )

        json_str = request.model_dump_json()

        # 解析JSON验证内容
        data = json.loads(json_str)
        assert data["match_id"] == "match_123"
        assert data["model_name"] == "xgboost_v1"
        assert data["prediction_type"] == "probability"


class TestPredictionResponse:
    """预测响应测试类"""

    def test_valid_prediction_response(self):
        """测试有效的预测响应"""
        data = {
            "request_id": "req_123",
            "match_id": "match_456",
            "predicted_at": datetime.utcnow().isoformat(),
            "home_win_prob": 0.65,
            "draw_prob": 0.25,
            "away_win_prob": 0.10,
            "predicted_outcome": "home_win",
            "confidence": 0.75,
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "model_type": "xgboost"
        }

        response = PredictionResponse(**data)

        assert response.request_id == "req_123"
        assert response.match_id == "match_456"
        assert response.home_win_prob == 0.65
        assert response.draw_prob == 0.25
        assert response.away_win_prob == 0.10
        assert response.predicted_outcome == "home_win"
        assert response.confidence == 0.75

    def test_invalid_probability_range(self):
        """测试无效的概率范围"""
        data = {
            "request_id": "req_123",
            "match_id": "match_456",
            "predicted_at": datetime.utcnow().isoformat(),
            "home_win_prob": 1.5,
            "draw_prob": -0.5,
            "away_win_prob": 0.0,
            "predicted_outcome": "home_win",
            "confidence": 0.75,
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "model_type": "xgboost",
            "features_used": ["home_goals"]
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionResponse(**data)

        assert "between 0 and 1" in str(exc_info.value)

    def test_invalid_predicted_outcome(self):
        """测试无效的预测结果"""
        data = {
            "request_id": "req_123",
            "match_id": "match_456",
            "predicted_at": datetime.utcnow().isoformat(),
            "home_win_prob": 0.6,
            "draw_prob": 0.3,
            "away_win_prob": 0.1,
            "predicted_outcome": "invalid_outcome",
            "confidence": 0.75,
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "model_type": "xgboost",
            "features_used": ["home_goals"]
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionResponse(**data)

        assert "predicted_outcome" in str(exc_info.value)

    def test_prediction_response_optional_fields(self):
        """测试预测响应可选字段"""
        data = {
            "request_id": "req_123",
            "match_id": "match_456",
            "predicted_at": datetime.utcnow().isoformat(),
            "home_win_prob": 0.6,
            "draw_prob": 0.3,
            "away_win_prob": 0.1,
            "predicted_outcome": "home_win",
            "confidence": 0.5,
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "model_type": "xgboost",
            "features_used": ["home_goals"]
        }

        response = PredictionResponse(**data)

        assert response.cached is False  # 默认值
        assert response.prediction_time_ms is None  # 默认值
        assert response.metadata == {}  # 默认值


class TestBatchPredictionRequest:
    """批量预测请求测试类"""

    def test_valid_batch_prediction_request(self):
        """测试有效的批量预测请求"""
        data = {
            "requests": [
                {
                    "match_id": "match_1",
                    "model_name": "xgboost_v1",
                    "prediction_type": "probability"
                },
                {
                    "match_id": "match_2",
                    "model_name": "xgboost_v1",
                    "prediction_type": "probability"
                }
            ],
            "batch_id": "batch_123",
            "parallel": True
        }

        batch_request = BatchPredictionRequest(**data)

        assert len(batch_request.requests) == 2
        assert batch_request.batch_id == "batch_123"
        assert batch_request.parallel is True

    def test_invalid_batch_prediction_request_empty_requests(self):
        """测试无效的批量预测请求 - 空请求列表"""
        data = {
            "requests": []
        }

        with pytest.raises(ValidationError) as exc_info:
            BatchPredictionRequest(**data)

        assert "requests" in str(exc_info.value)

    def test_batch_prediction_request_optional_fields(self):
        """测试批量预测请求可选字段"""
        data = {
            "requests": [
                {
                    "match_id": "match_1",
                    "model_name": "xgboost_v1",
                    "prediction_type": "probability"
                }
            ]
        }

        batch_request = BatchPredictionRequest(**data)

        assert batch_request.batch_id is None  # 默认值
        assert batch_request.parallel is True  # 默认值


class TestBatchPredictionResponse:
    """批量预测响应测试类"""

    def test_valid_batch_prediction_response(self):
        """测试有效的批量预测响应"""
        data = {
            "batch_id": "batch_123",
            "total_requests": 3,
            "successful_predictions": 2,
            "failed_predictions": 1,
            "predictions": [
                {
                    "request_id": "req_1",
                    "match_id": "match_1",
                    "predicted_at": datetime.utcnow().isoformat(),
                    "home_win_prob": 0.6,
                    "draw_prob": 0.3,
                    "away_win_prob": 0.1,
                    "predicted_outcome": "home_win",
                    "confidence": 0.5,
                    "model_name": "xgboost_v1",
                    "model_version": "1.0.0",
                    "model_type": "xgboost",
                    "features_used": ["home_goals"]
                }
            ],
            "errors": [
                {
                    "request_index": 1,
                    "match_id": "match_2",
                    "error": "Model load failed"
                }
            ],
            "batch_time_ms": 500
        }

        response = BatchPredictionResponse(**data)

        assert response.batch_id == "batch_123"
        assert response.total_requests == 3
        assert response.successful_predictions == 2
        assert response.failed_predictions == 1
        assert len(response.predictions) == 1
        assert len(response.errors) == 1
        assert response.cached_count == 0  # 默认值


class TestModelInfo:
    """模型信息测试类"""

    def test_valid_model_info(self):
        """测试有效的模型信息"""
        data = {
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "model_type": "xgboost",
            "created_at": datetime.utcnow().isoformat(),
            "features": ["home_goals", "away_goals"],
            "accuracy": 0.85,
            "description": "XGBoost football prediction model"
        }

        # Note: description is not in the actual schema, so we'll omit it
        data_without_description = {k: v for k, v in data.items() if k != 'description'}

        model_info = ModelInfo(**data_without_description)

        assert model_info.model_name == "xgboost_v1"
        assert model_info.model_version == "1.0.0"
        assert model_info.model_type == ModelType.XGBOOST
        assert model_info.accuracy == 0.85

    def test_invalid_accuracy_range(self):
        """测试无效的准确率范围"""
        data = {
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "model_type": "xgboost",
            "created_at": datetime.utcnow().isoformat(),
            "features": ["home_goals"],
            "accuracy": 1.5
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelInfo(**data)

        assert "accuracy" in str(exc_info.value)


class TestErrorResponse:
    """错误响应测试类"""

    def test_valid_error_response(self):
        """测试有效的错误响应"""
        error_response = ErrorResponse(
            error="ModelLoadError",
            message="Failed to load model: model file not found",
            details={
                "model_name": "xgboost_v1",
                "file_path": "/path/to/model.pkl"
            }
        )

        assert error_response.error == "ModelLoadError"
        assert "model file not found" in error_response.message
        assert error_response.details["model_name"] == "xgboost_v1"

    def test_error_response_minimal(self):
        """测试最小错误响应"""
        error_response = ErrorResponse(
            error="ValidationError",
            message="Invalid input data"
        )

        assert error_response.error == "ValidationError"
        assert error_response.details == {}

    def test_error_response_with_timestamp(self):
        """测试带时间戳的错误响应"""
        current_time = datetime.utcnow()
        error_response = ErrorResponse(
            error="PredictionError",
            message="Prediction failed",
            timestamp=current_time
        )

        assert error_response.timestamp == current_time


class TestSchemaIntegration:
    """模式集成测试类"""

    def test_request_response_roundtrip(self):
        """测试请求响应往返转换"""
        # 创建请求
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability",
            features={"home_goals": 2}
        )

        # 创建响应
        response = PredictionResponse(
            request_id="req_123",
            match_id=request.match_id,
            predicted_at=datetime.utcnow(),
            home_win_prob=0.6,
            draw_prob=0.3,
            away_win_prob=0.1,
            predicted_outcome="home_win",
            confidence=0.5,
            model_name=request.model_name,
            model_version="1.0.0",
            model_type="xgboost",
            features_used=["home_goals"]
        )

        # 序列化和反序列化
        request_json = request.model_dump_json()
        response_json = response.model_dump_json()

        request_restored = PredictionRequest.model_validate_json(request_json)
        response_restored = PredictionResponse.model_validate_json(response_json)

        assert request_restored.match_id == request.match_id
        assert response_restored.match_id == response.match_id

    def test_batch_request_response_integration(self):
        """测试批量请求响应集成"""
        batch_request = BatchPredictionRequest(
            requests=[
                PredictionRequest(
                    match_id=f"match_{i}",
                    model_name="xgboost_v1",
                    prediction_type="probability"
                )
                for i in range(3)
            ],
            parallel=True
        )

        # 模拟批量响应
        predictions = []
        for i, req in enumerate(batch_request.requests):
            pred = PredictionResponse(
                request_id=f"req_{i}",
                match_id=req.match_id,
                predicted_at=datetime.utcnow(),
                home_win_prob=0.6,
                draw_prob=0.3,
                away_win_prob=0.1,
                predicted_outcome="home_win",
                confidence=0.5,
                model_name=req.model_name,
                model_version="1.0.0",
                model_type="xgboost",
                features_used=["home_goals"]
            )
            predictions.append(pred)

        batch_response = BatchPredictionResponse(
            batch_id="batch_123",
            total_requests=len(batch_request.requests),
            successful_predictions=len(predictions),
            failed_predictions=0,
            predictions=predictions,
            batch_time_ms=500
        )

        assert batch_response.total_requests == 3
        assert len(batch_response.predictions) == 3
        assert all(pred.match_id.startswith("match_") for pred in batch_response.predictions)