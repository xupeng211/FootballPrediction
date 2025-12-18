"""
Unit Tests for Inference Schemas
推理服务模式定义单元测试

测试Pydantic模型的数据验证、序列化和反序列化功能。
"""

import json
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.inference.schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelInfo,
    ModelMetadata,
    PredictionMetadata,
    ErrorResponse,
    ModelType,
    PredictionType,
    FeatureImportance,
)


class TestPredictionRequest:
    """预测请求测试类"""

    def test_valid_prediction_request_minimal(self):
        """测试有效的最小预测请求"""
        data = {
            "match_id": "match_123",
            "model_name": "xgboost_v1",
            "prediction_type": "probability",
        }

        request = PredictionRequest(**data)

        assert request.match_id == "match_123"
        assert request.model_name == "xgboost_v1"
        assert request.prediction_type == PredictionType.PROBABILITY
        assert request.model_version is None
        assert request.features is None
        assert request.force_recalculate is False

    def test_valid_prediction_request_full(self):
        """测试有效的完整预测请求"""
        data = {
            "match_id": "match_456",
            "model_name": "lstm_v2",
            "prediction_type": "winner",
            "model_version": "2.1.0",
            "features": {"home_goals": 2, "away_goals": 1, "home_possession": 65.5},
            "force_recalculate": True,
        }

        request = PredictionRequest(**data)

        assert request.match_id == "match_456"
        assert request.model_name == "lstm_v2"
        assert request.prediction_type == PredictionType.WINNER
        assert request.model_version == "2.1.0"
        assert request.features["home_goals"] == 2
        assert request.force_recalculate is True

    def test_invalid_prediction_request_empty_match_id(self):
        """测试无效的预测请求 - 空比赛ID"""
        data = {
            "match_id": "",
            "model_name": "xgboost_v1",
            "prediction_type": "probability",
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionRequest(**data)

        assert "match_id" in str(exc_info.value)

    def test_invalid_prediction_request_empty_model_name(self):
        """测试无效的预测请求 - 空模型名称"""
        data = {
            "match_id": "match_123",
            "model_name": "",
            "prediction_type": "probability",
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionRequest(**data)

        assert "model_name" in str(exc_info.value)

    def test_invalid_prediction_request_invalid_prediction_type(self):
        """测试无效的预测请求 - 无效预测类型"""
        data = {
            "match_id": "match_123",
            "model_name": "xgboost_v1",
            "prediction_type": "invalid_type",
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionRequest(**data)

        assert "prediction_type" in str(exc_info.value)

    def test_prediction_request_serialization(self):
        """测试预测请求序列化"""
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability",
            features={"home_goals": 2},
        )

        serialized = request.model_dump()

        assert serialized["match_id"] == "match_123"
        assert serialized["prediction_type"] == "probability"
        assert serialized["features"]["home_goals"] == 2

    def test_prediction_request_json_serialization(self):
        """测试预测请求JSON序列化"""
        request = PredictionRequest(
            match_id="match_123", model_name="xgboost_v1", prediction_type="probability"
        )

        json_str = request.model_dump_json()

        # 解析JSON验证内容
        data = json.loads(json_str)
        assert data["match_id"] == "match_123"
        assert data["model_name"] == "xgboost_v1"
        assert data["prediction_type"] == "probability"

    def test_prediction_request_deserialization(self):
        """测试预测请求反序列化"""
        json_str = json.dumps(
            {
                "match_id": "match_123",
                "model_name": "xgboost_v1",
                "prediction_type": "probability",
                "features": {"home_goals": 2},
            }
        )

        request = PredictionRequest.model_validate_json(json_str)

        assert request.match_id == "match_123"
        assert request.features["home_goals"] == 2


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
            "model_type": "xgboost",
            "features_used": ["home_goals", "away_goals"],
            "prediction_time_ms": 150,
            "cached": False,
        }

        response = PredictionResponse(**data)

        assert response.request_id == "req_123"
        assert response.match_id == "match_456"
        assert response.home_win_prob == 0.65
        assert response.draw_prob == 0.25
        assert response.away_win_prob == 0.10
        assert response.predicted_outcome == "home_win"
        assert response.confidence == 0.75
        assert response.cached is False

    def test_invalid_probabilities_sum(self):
        """测试无效的概率和"""
        data = {
            "request_id": "req_123",
            "match_id": "match_456",
            "predicted_at": datetime.utcnow().isoformat(),
            "home_win_prob": 0.8,
            "draw_prob": 0.8,
            "away_win_prob": 0.8,
            "predicted_outcome": "home_win",
            "confidence": 0.75,
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "model_type": "xgboost",
            "features_used": ["home_goals"],
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionResponse(**data)

        assert "probabilities must sum to" in str(exc_info.value)

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
            "features_used": ["home_goals"],
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionResponse(**data)

        assert "between 0 and 1" in str(exc_info.value)

    def test_invalid_confidence_range(self):
        """测试无效的置信度范围"""
        data = {
            "request_id": "req_123",
            "match_id": "match_456",
            "predicted_at": datetime.utcnow().isoformat(),
            "home_win_prob": 0.6,
            "draw_prob": 0.3,
            "away_win_prob": 0.1,
            "predicted_outcome": "home_win",
            "confidence": 1.5,
            "model_name": "xgboost_v1",
            "model_version": "1.0.0",
            "model_type": "xgboost",
            "features_used": ["home_goals"],
        }

        with pytest.raises(ValidationError) as exc_info:
            PredictionResponse(**data)

        assert "confidence" in str(exc_info.value)

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
            "features_used": ["home_goals"],
        }

        response = PredictionResponse(**data)

        assert response.cached is False  # 默认值
        assert response.prediction_time_ms == 0  # 默认值
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
                    "prediction_type": "probability",
                },
                {
                    "match_id": "match_2",
                    "model_name": "xgboost_v1",
                    "prediction_type": "probability",
                },
            ],
            "batch_id": "batch_123",
            "parallel": True,
        }

        batch_request = BatchPredictionRequest(**data)

        assert len(batch_request.requests) == 2
        assert batch_request.batch_id == "batch_123"
        assert batch_request.parallel is True

    def test_invalid_batch_prediction_request_empty_requests(self):
        """测试无效的批量预测请求 - 空请求列表"""
        data = {"requests": []}

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
                    "prediction_type": "probability",
                }
            ]
        }

        batch_request = BatchPredictionRequest(**data)

        assert batch_request.batch_id is None  # 默认值
        assert batch_request.parallel is False  # 默认值


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
                    "features_used": ["home_goals"],
                }
            ],
            "errors": [
                {
                    "request_index": 1,
                    "match_id": "match_2",
                    "error": "Model load failed",
                }
            ],
            "batch_time_ms": 500,
            "cached_count": 1,
        }

        response = BatchPredictionResponse(**data)

        assert response.batch_id == "batch_123"
        assert response.total_requests == 3
        assert response.successful_predictions == 2
        assert response.failed_predictions == 1
        assert len(response.predictions) == 1
        assert len(response.errors) == 1
        assert response.cached_count == 1

    def test_batch_prediction_response_optional_fields(self):
        """测试批量预测响应可选字段"""
        data = {
            "batch_id": "batch_123",
            "total_requests": 1,
            "successful_predictions": 1,
            "failed_predictions": 0,
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
                    "features_used": ["home_goals"],
                }
            ],
        }

        response = BatchPredictionResponse(**data)

        assert response.errors == []  # 默认值
        assert response.batch_time_ms == 0  # 默认值
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
            "description": "XGBoost football prediction model",
        }

        model_info = ModelInfo(**data)

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
            "accuracy": 1.5,
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelInfo(**data)

        assert "accuracy" in str(exc_info.value)


class TestModelMetadata:
    """模型元数据测试类"""

    def test_valid_model_metadata(self):
        """测试有效的模型元数据"""
        model_info = ModelInfo(
            model_name="xgboost_v1",
            model_version="1.0.0",
            model_type="xgboost",
            created_at=datetime.utcnow().isoformat(),
            features=["home_goals"],
        )

        metadata = ModelMetadata(
            model_info=model_info,
            file_path="/path/to/model.pkl",
            file_size=1024000,
            checksum="md5_hash",
            loaded_at=datetime.utcnow(),
            load_time_ms=100,
        )

        assert metadata.model_info.model_name == "xgboost_v1"
        assert metadata.file_path == "/path/to/model.pkl"
        assert metadata.file_size == 1024000


class TestPredictionMetadata:
    """预测元数据测试类"""

    def test_valid_prediction_metadata(self):
        """测试有效的预测元数据"""
        metadata = PredictionMetadata(
            model_accuracy=0.85,
            calibration_applied=True,
            prediction_type="probability",
            feature_count=10,
            cache_hit=False,
        )

        assert metadata.model_accuracy == 0.85
        assert metadata.calibration_applied is True
        assert metadata.prediction_type == "probability"
        assert metadata.feature_count == 10
        assert metadata.cache_hit is False


class TestErrorResponse:
    """错误响应测试类"""

    def test_valid_error_response(self):
        """测试有效的错误响应"""
        error_response = ErrorResponse(
            error="ModelLoadError",
            message="Failed to load model: model file not found",
            details={"model_name": "xgboost_v1", "file_path": "/path/to/model.pkl"},
        )

        assert error_response.error == "ModelLoadError"
        assert "model file not found" in error_response.message
        assert error_response.details["model_name"] == "xgboost_v1"

    def test_error_response_minimal(self):
        """测试最小错误响应"""
        error_response = ErrorResponse(
            error="ValidationError", message="Invalid input data"
        )

        assert error_response.error == "ValidationError"
        assert error_response.details == {}


class TestFeatureImportance:
    """特征重要性测试类"""

    def test_valid_feature_importance(self):
        """测试有效的特征重要性"""
        data = {
            "feature_name": "home_goals",
            "importance_score": 0.85,
            "feature_type": "numeric",
            "description": "Number of goals scored by home team",
        }

        feature_importance = FeatureImportance(**data)

        assert feature_importance.feature_name == "home_goals"
        assert feature_importance.importance_score == 0.85
        assert feature_importance.feature_type == "numeric"

    def test_invalid_importance_score_range(self):
        """测试无效的重要性分数范围"""
        data = {
            "feature_name": "home_goals",
            "importance_score": 1.5,
            "feature_type": "numeric",
        }

        with pytest.raises(ValidationError) as exc_info:
            FeatureImportance(**data)

        assert "importance_score" in str(exc_info.value)


class TestEnums:
    """枚举类型测试类"""

    def test_model_type_values(self):
        """测试模型类型枚举值"""
        assert ModelType.XGBOOST.value == "xgboost"
        assert ModelType.LSTM.value == "lstm"
        assert ModelType.RANDOM_FOREST.value == "random_forest"
        assert ModelType.NEURAL_NETWORK.value == "neural_network"

    def test_prediction_type_values(self):
        """测试预测类型枚举值"""
        assert PredictionType.PROBABILITY.value == "probability"
        assert PredictionType.WINNER.value == "winner"
        assert PredictionType.SCORE.value == "score"
        assert PredictionType.OVER_UNDER.value == "over_under"

    def test_enum_creation_from_string(self):
        """测试从字符串创建枚举"""
        xgb_type = ModelType("xgboost")
        assert xgb_type == ModelType.XGBOOST

        prob_type = PredictionType("probability")
        assert prob_type == PredictionType.PROBABILITY

    def test_invalid_enum_creation(self):
        """测试无效枚举创建"""
        with pytest.raises(ValueError):
            ModelType("invalid_model_type")

        with pytest.raises(ValueError):
            PredictionType("invalid_prediction_type")


class TestSchemaIntegration:
    """模式集成测试类"""

    def test_request_response_roundtrip(self):
        """测试请求响应往返转换"""
        # 创建请求
        request = PredictionRequest(
            match_id="match_123",
            model_name="xgboost_v1",
            prediction_type="probability",
            features={"home_goals": 2},
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
            features_used=["home_goals"],
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
                    prediction_type="probability",
                )
                for i in range(3)
            ],
            parallel=True,
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
                features_used=["home_goals"],
            )
            predictions.append(pred)

        batch_response = BatchPredictionResponse(
            batch_id="batch_123",
            total_requests=len(batch_request.requests),
            successful_predictions=len(predictions),
            failed_predictions=0,
            predictions=predictions,
        )

        assert batch_response.total_requests == 3
        assert len(batch_response.predictions) == 3
        assert all(
            pred.match_id.startswith("match_") for pred in batch_response.predictions
        )
