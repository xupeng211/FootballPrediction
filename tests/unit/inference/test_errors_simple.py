"""
Unit Tests for Inference Errors (Simplified)
推理服务错误处理单元测试（简化版）

测试实际存在的错误类和功能。
"""

import pytest
from typing import Dict, Any

from src.inference.errors import (
    InferenceError,
    ModelLoadError,
    FeatureBuilderError,
    PredictionError,
    CacheError,
    HotReloadError,
    ErrorCode,
    handle_inference_error,
)


class TestErrorCode:
    """错误代码测试类"""

    def test_error_code_values(self):
        """测试错误代码枚举值"""
        assert ErrorCode.MODEL_NOT_FOUND.value == "MODEL_NOT_FOUND"
        assert ErrorCode.MODEL_LOAD_FAILED.value == "MODEL_LOAD_FAILED"
        assert ErrorCode.FEATURE_BUILD_FAILED.value == "FEATURE_BUILD_FAILED"
        assert ErrorCode.PREDICTION_FAILED.value == "PREDICTION_FAILED"
        assert ErrorCode.CACHE_CONNECTION_FAILED.value == "CACHE_CONNECTION_FAILED"
        assert ErrorCode.HOT_RELOAD_FAILED.value == "HOT_RELOAD_FAILED"
        assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"

    def test_error_code_creation(self):
        """测试错误代码创建"""
        error_code = ErrorCode.MODEL_NOT_FOUND
        assert error_code == "MODEL_NOT_FOUND"
        assert str(error_code) == "MODEL_NOT_FOUND"

    def test_invalid_error_code(self):
        """测试无效错误代码"""
        with pytest.raises(ValueError):
            ErrorCode("INVALID_ERROR_CODE")


class TestInferenceError:
    """推理错误基类测试类"""

    def test_inference_error_basic(self):
        """测试基本推理错误"""
        error = InferenceError("Basic error message")

        assert str(error) == "Basic error message"
        assert error.message == "Basic error message"
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.details == {}

    def test_inference_error_with_details(self):
        """测试带详细信息的推理错误"""
        details = {"model_name": "xgboost_v1", "attempt_count": 3}
        error = InferenceError(
            message="Complex error",
            error_code=ErrorCode.MODEL_LOAD_FAILED,
            details=details
        )

        assert error.message == "Complex error"
        assert error.error_code == ErrorCode.MODEL_LOAD_FAILED
        assert error.details == details

    def test_inference_error_to_dict(self):
        """测试推理错误转字典"""
        details = {"retry_after": 5}
        error = InferenceError(
            message="Test error",
            error_code=ErrorCode.PREDICTION_FAILED,
            details=details
        )

        error_dict = error.to_dict()

        expected = {
            "error": "PREDICTION_FAILED",
            "message": "Test error",
            "details": details
        }

        assert error_dict == expected


class TestModelLoadError:
    """模型加载错误测试类"""

    def test_model_load_error_basic(self):
        """测试基本模型加载错误"""
        error = ModelLoadError("Failed to load model file")

        assert str(error) == "Failed to load model file"
        assert error.error_code == ErrorCode.MODEL_LOAD_FAILED
        assert "model_name" in error.details

    def test_model_load_error_with_model_name(self):
        """测试带模型名称的加载错误"""
        error = ModelLoadError(
            "Model file not found",
            model_name="xgboost_v1"
        )

        assert error.details["model_name"] == "xgboost_v1"

    def test_model_load_error_with_details(self):
        """测试带详细信息的模型加载错误"""
        error = ModelLoadError(
            "Model file is empty",
            model_name="xgboost_v1",
            details={"file_path": "/path/to/model.pkl"}
        )

        assert error.details["model_name"] == "xgboost_v1"
        assert error.details["file_path"] == "/path/to/model.pkl"


class TestFeatureBuilderError:
    """特征构建错误测试类"""

    def test_feature_builder_error_basic(self):
        """测试基本特征构建错误"""
        error = FeatureBuilderError("Failed to build features")

        assert str(error) == "Failed to build features"
        assert error.error_code == ErrorCode.FEATURE_BUILD_FAILED

    def test_feature_builder_error_with_feature_name(self):
        """测试带特征名称的错误"""
        error = FeatureBuilderError(
            "Invalid feature value",
            feature_name="home_goals"
        )

        assert error.details["feature_name"] == "home_goals"


class TestPredictionError:
    """预测错误测试类"""

    def test_prediction_error_basic(self):
        """测试基本预测错误"""
        error = PredictionError("Prediction computation failed")

        assert str(error) == "Prediction computation failed"
        assert error.error_code == ErrorCode.PREDICTION_FAILED

    def test_prediction_error_with_prediction_id(self):
        """测试带预测ID的预测错误"""
        error = PredictionError(
            "Model prediction failed",
            prediction_id="pred_456"
        )

        assert error.details["prediction_id"] == "pred_456"


class TestCacheError:
    """缓存错误测试类"""

    def test_cache_error_basic(self):
        """测试基本缓存错误"""
        error = CacheError("Redis connection failed")

        assert str(error) == "Redis connection failed"
        assert error.error_code == ErrorCode.CACHE_OPERATION_FAILED

    def test_cache_error_with_cache_key(self):
        """测试带缓存键的缓存错误"""
        error = CacheError(
            "Cache operation failed",
            cache_key="prediction:match_123:xgboost_v1"
        )

        assert error.details["cache_key"] == "prediction:match_123:xgboost_v1"


class TestHotReloadError:
    """热更新错误测试类"""

    def test_hot_reload_error_basic(self):
        """测试基本热更新错误"""
        error = HotReloadError("Hot reload monitoring failed")

        assert str(error) == "Hot reload monitoring failed"
        assert error.error_code == ErrorCode.HOT_RELOAD_FAILED

    def test_hot_reload_error_with_model_name(self):
        """测试带模型名称的热更新错误"""
        error = HotReloadError(
            "Model reload failed",
            model_name="xgboost_v1"
        )

        assert error.details["model_name"] == "xgboost_v1"


class TestErrorHandlerUtility:
    """错误处理工具测试类"""

    def test_handle_inference_error_success(self):
        """测试成功处理的函数"""
        @handle_inference_error
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_handle_inference_error_with_inference_error(self):
        """测试处理推理错误的函数"""
        @handle_inference_error
        def function_with_inference_error():
            raise ModelLoadError("Model not found")

        with pytest.raises(ModelLoadError) as exc_info:
            function_with_inference_error()

        assert "Model not found" in str(exc_info.value)

    def test_handle_inference_error_with_general_error(self):
        """测试处理一般错误的函数"""
        @handle_inference_error
        def function_with_general_error():
            raise ValueError("General error")

        with pytest.raises(InferenceError) as exc_info:
            function_with_general_error()

        error = exc_info.value
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert "function_with_general_error" in error.message
        assert error.details["original_error"] == "General error"


class TestErrorIntegration:
    """错误集成测试类"""

    def test_error_inheritance_chain(self):
        """测试错误继承链"""
        # 所有自定义错误都应该继承自InferenceError
        assert issubclass(ModelLoadError, InferenceError)
        assert issubclass(FeatureBuilderError, InferenceError)
        assert issubclass(PredictionError, InferenceError)
        assert issubclass(CacheError, InferenceError)
        assert issubclass(HotReloadError, InferenceError)

        # 也应该继承自Exception
        assert issubclass(InferenceError, Exception)

    def test_error_serialization_roundtrip(self):
        """测试错误序列化往返"""
        original_error = HotReloadError(
            "Reload failed",
            model_name="neural_net_v2"
        )

        # 转换为字典
        error_dict = original_error.to_dict()

        # 验证关键字段
        assert error_dict["error"] == "HOT_RELOAD_FAILED"
        assert error_dict["message"] == "Reload failed"
        assert error_dict["details"]["model_name"] == "neural_net_v2"

    def test_multiple_error_types_response(self):
        """测试多种错误类型的响应"""
        errors = [
            ModelLoadError("Model not found", model_name="model1"),
            FeatureBuilderError("Invalid feature", feature_name="goals"),
            CacheError("Redis down")
        ]

        responses = [error.to_dict() for error in errors]

        assert len(responses) == 3
        assert responses[0]["error"] == "MODEL_LOAD_FAILED"
        assert responses[1]["error"] == "FEATURE_BUILD_FAILED"
        assert responses[2]["error"] == "CACHE_OPERATION_FAILED"

    def test_error_chain(self):
        """测试错误链"""
        try:
            try:
                raise ModelLoadError("Model file corrupted", model_name="xgboost_v1")
            except ModelLoadError as e:
                raise PredictionError("Failed to make prediction") from e
        except PredictionError as outer_error:
            assert outer_error.__cause__ is not None
            assert isinstance(outer_error.__cause__, ModelLoadError)
            assert "xgboost_v1" in str(outer_error.__cause__)
