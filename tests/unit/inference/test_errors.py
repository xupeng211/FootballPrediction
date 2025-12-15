"""
Unit Tests for Inference Errors
推理服务错误处理单元测试

测试自定义异常类、错误代码和错误处理机制。
"""

import pytest

from src.inference.errors import (
    InferenceError,
    ModelLoadError,
    FeatureBuilderError,
    PredictionError,
    CacheError,
    HotReloadError,
    ErrorCode,
)


class TestErrorCode:
    """错误代码测试类"""

    def test_error_code_values(self):
        """测试错误代码枚举值"""
        assert ErrorCode.MODEL_NOT_FOUND.value == "MODEL_NOT_FOUND"
        assert ErrorCode.MODEL_LOAD_FAILED.value == "MODEL_LOAD_FAILED"
        assert ErrorCode.FEATURE_VALIDATION_FAILED.value == "FEATURE_VALIDATION_FAILED"
        assert ErrorCode.PREDICTION_FAILED.value == "PREDICTION_FAILED"
        assert ErrorCode.CACHE_CONNECTION_FAILED.value == "CACHE_CONNECTION_FAILED"
        assert ErrorCode.HOT_RELOAD_FAILED.value == "HOT_RELOAD_FAILED"
        assert ErrorCode.INVALID_REQUEST.value == "INVALID_REQUEST"
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


# Note: ErrorSeverity and ErrorCategory are not implemented in the actual file


class TestInferenceError:
    """推理错误基类测试类"""

    def test_inference_error_basic(self):
        """测试基本推理错误"""
        error = InferenceError("Basic error message")

        assert str(error) == "Basic error message"
        assert error.message == "Basic error message"
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.category == ErrorCategory.SYSTEM_ERROR
        assert error.details == {}

    def test_inference_error_with_all_parameters(self):
        """测试包含所有参数的推理错误"""
        details = {"model_name": "xgboost_v1", "attempt_count": 3}
        error = InferenceError(
            message="Complex error",
            error_code=ErrorCode.MODEL_LOAD_FAILED,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.MODEL_ERROR,
            details=details,
        )

        assert error.message == "Complex error"
        assert error.error_code == ErrorCode.MODEL_LOAD_FAILED
        assert error.severity == ErrorSeverity.HIGH
        assert error.category == ErrorCategory.MODEL_ERROR
        assert error.details == details

    def test_inference_error_to_dict(self):
        """测试推理错误转字典"""
        details = {"retry_after": 5}
        error = InferenceError(
            message="Test error",
            error_code=ErrorCode.PREDICTION_FAILED,
            severity=ErrorSeverity.CRITICAL,
            details=details,
        )

        error_dict = error.to_dict()

        expected = {
            "error": "InferenceError",
            "error_code": "PREDICTION_FAILED",
            "message": "Test error",
            "severity": "critical",
            "category": "system_error",
            "details": details,
        }

        assert error_dict == expected

    def test_inference_error_with_prediction_id(self):
        """测试带预测ID的推理错误"""
        error = InferenceError(message="Prediction failed", prediction_id="pred_123")

        assert error.prediction_id == "pred_123"
        assert "prediction_id" in error.to_dict()


class TestModelLoadError:
    """模型加载错误测试类"""

    def test_model_load_error_basic(self):
        """测试基本模型加载错误"""
        error = ModelLoadError("Failed to load model file")

        assert str(error) == "Failed to load model file"
        assert error.error_code == ErrorCode.MODEL_LOAD_FAILED
        assert error.category == ErrorCategory.MODEL_ERROR
        assert error.severity == ErrorSeverity.HIGH

    def test_model_load_error_with_details(self):
        """测试带详细信息的模型加载错误"""
        details = {
            "model_name": "xgboost_v1",
            "file_path": "/path/to/model.pkl",
            "file_size": 0,
        }
        error = ModelLoadError("Model file is empty", details=details)

        assert error.details["model_name"] == "xgboost_v1"
        assert error.details["file_size"] == 0

    def test_model_load_error_file_not_found(self):
        """测试文件未找到错误"""
        error = ModelLoadError(
            "Model file not found",
            model_name="nonexistent_model",
            file_path="/path/to/nonexistent.pkl",
        )

        assert error.model_name == "nonexistent_model"
        assert error.file_path == "/path/to/nonexistent.pkl"
        assert error.error_code == ErrorCode.MODEL_NOT_FOUND


class TestFeatureBuilderError:
    """特征构建错误测试类"""

    def test_feature_builder_error_basic(self):
        """测试基本特征构建错误"""
        error = FeatureBuilderError("Failed to build features")

        assert str(error) == "Failed to build features"
        assert error.error_code == ErrorCode.FEATURE_VALIDATION_FAILED
        assert error.category == ErrorCategory.FEATURE_ERROR
        assert error.severity == ErrorSeverity.MEDIUM

    def test_feature_builder_error_with_feature_info(self):
        """测试带特征信息的错误"""
        error = FeatureBuilderError(
            "Invalid feature value",
            feature_name="home_goals",
            feature_value=-5,
            expected_range="[0, +∞)",
        )

        assert error.feature_name == "home_goals"
        assert error.feature_value == -5
        assert "expected_range" in error.details

    def test_feature_builder_error_missing_features(self):
        """测试缺失特征错误"""
        missing_features = ["home_possession", "away_corners"]
        error = FeatureBuilderError(
            "Required features are missing", missing_features=missing_features
        )

        assert error.missing_features == missing_features
        assert missing_features[0] in str(error)


class TestPredictionError:
    """预测错误测试类"""

    def test_prediction_error_basic(self):
        """测试基本预测错误"""
        error = PredictionError("Prediction computation failed")

        assert str(error) == "Prediction computation failed"
        assert error.error_code == ErrorCode.PREDICTION_FAILED
        assert error.category == ErrorCategory.PREDICTION_ERROR
        assert error.severity == ErrorSeverity.HIGH

    def test_prediction_error_with_prediction_id(self):
        """测试带预测ID的预测错误"""
        error = PredictionError(
            "Model prediction failed", prediction_id="pred_456", model_name="xgboost_v1"
        )

        assert error.prediction_id == "pred_456"
        assert error.model_name == "xgboost_v1"

    def test_prediction_error_model_inference_failed(self):
        """测试模型推理失败错误"""
        error = PredictionError(
            "Model inference returned invalid probabilities",
            model_name="lstm_v1",
            prediction_type="probability",
            invalid_output="[0.8, 0.3]",  # 概率和不为1
        )

        assert error.model_name == "lstm_v1"
        assert error.prediction_type == "probability"
        assert "invalid_output" in error.details


class TestCacheError:
    """缓存错误测试类"""

    def test_cache_error_basic(self):
        """测试基本缓存错误"""
        error = CacheError("Redis connection failed")

        assert str(error) == "Redis connection failed"
        assert error.error_code == ErrorCode.CACHE_CONNECTION_FAILED
        assert error.category == ErrorCategory.CACHE_ERROR
        assert error.severity == ErrorSeverity.MEDIUM

    def test_cache_error_with_cache_details(self):
        """测试带缓存详细信息的错误"""
        error = CacheError(
            "Cache set operation failed",
            cache_key="prediction:match_123:xgboost_v1",
            operation="set",
            redis_error="Connection timeout",
        )

        assert error.cache_key == "prediction:match_123:xgboost_v1"
        assert error.operation == "set"
        assert error.details["redis_error"] == "Connection timeout"

    def test_cache_error_serialization_failed(self):
        """测试序列化失败错误"""
        error = CacheError(
            "Failed to serialize prediction data",
            operation="serialize",
            data_type="PredictionResponse",
            serialization_error="Object not JSON serializable",
        )

        assert error.operation == "serialize"
        assert error.data_type == "PredictionResponse"


class TestHotReloadError:
    """热更新错误测试类"""

    def test_hot_reload_error_basic(self):
        """测试基本热更新错误"""
        error = HotReloadError("Hot reload monitoring failed")

        assert str(error) == "Hot reload monitoring failed"
        assert error.error_code == ErrorCode.HOT_RELOAD_FAILED
        assert error.category == ErrorCategory.SYSTEM_ERROR
        assert error.severity == ErrorSeverity.HIGH

    def test_hot_reload_error_with_reload_details(self):
        """测试带重载详细信息的错误"""
        error = HotReloadError(
            "Model reload failed",
            model_name="xgboost_v1",
            old_file_path="/path/to/old.pkl",
            new_file_path="/path/to/new.pkl",
            rollback_successful=True,
        )

        assert error.model_name == "xgboost_v1"
        assert error.old_file_path == "/path/to/old.pkl"
        assert error.new_file_path == "/path/to/new.pkl"
        assert error.rollback_successful is True

    def test_hot_reload_error_validation_failed(self):
        """测试验证失败错误"""
        error = HotReloadError(
            "New model validation failed",
            model_name="neural_net_v2",
            validation_errors=[
                "Accuracy below threshold (0.45 < 0.70)",
                "Feature count mismatch (expected: 20, actual: 15)",
            ],
        )

        assert error.model_name == "neural_net_v2"
        assert len(error.validation_errors) == 2
        assert "Accuracy below threshold" in error.validation_errors[0]


class TestErrorUtilityFunctions:
    """错误工具函数测试类"""

    def test_create_error_response(self):
        """测试创建错误响应"""
        error = ModelLoadError("Model file not found", model_name="xgboost_v1")

        error_response = create_error_response(error)

        expected = {
            "error": "ModelLoadError",
            "error_code": "MODEL_NOT_FOUND",
            "message": "Model file not found",
            "severity": "high",
            "category": "model_error",
            "details": {"model_name": "xgboost_v1"},
        }

        assert error_response == expected

    def test_create_error_response_without_details(self):
        """测试创建无详细信息的错误响应"""
        error = CacheError("Redis timeout")

        error_response = create_error_response(error)

        assert error_response["error"] == "CacheError"
        assert error_response["message"] == "Redis timeout"
        assert error_response["details"] == {}

    def test_format_error_message_basic(self):
        """测试基本错误消息格式化"""
        formatted = format_error_message(
            template="Model {model_name} failed to load from {file_path}",
            model_name="xgboost_v1",
            file_path="/path/to/model.pkl",
        )

        expected = "Model xgboost_v1 failed to load from /path/to/model.pkl"
        assert formatted == expected

    def test_format_error_message_missing_template(self):
        """测试缺失模板的错误消息格式化"""
        formatted = format_error_message(
            "Simple error message with {placeholder}", missing_param="value"
        )

        # 应该保留占位符，因为没有提供对应的值
        assert "{placeholder}" in formatted
        assert "missing_param" not in formatted

    def test_get_error_category(self):
        """测试获取错误类别"""
        # 测试各种错误类型
        assert get_error_category(ModelLoadError) == ErrorCategory.MODEL_ERROR
        assert get_error_category(FeatureBuilderError) == ErrorCategory.FEATURE_ERROR
        assert get_error_category(PredictionError) == ErrorCategory.PREDICTION_ERROR
        assert get_error_category(CacheError) == ErrorCategory.CACHE_ERROR
        assert get_error_category(HotReloadError) == ErrorCategory.SYSTEM_ERROR

        # 测试基类
        assert get_error_category(InferenceError) == ErrorCategory.SYSTEM_ERROR

    def test_get_error_category_unknown_type(self):
        """测试获取未知错误类型的类别"""

        class CustomError(Exception):
            pass

        category = get_error_category(CustomError)
        assert category == ErrorCategory.SYSTEM_ERROR

    def test_is_retryable_error(self):
        """测试错误是否可重试"""
        # 可重试的错误
        retryable_errors = [
            CacheError("Redis connection timeout"),
            HotReloadError("File monitoring failed"),
            InferenceError("Temporary system error"),
        ]

        for error in retryable_errors:
            assert is_retryable_error(error) is True

        # 不可重试的错误
        non_retryable_errors = [
            ModelLoadError("Model file not found"),
            FeatureBuilderError("Invalid feature value"),
            PredictionError("Model architecture mismatch"),
        ]

        for error in non_retryable_errors:
            assert is_retryable_error(error) is False

    def test_is_retryable_error_custom_severity(self):
        """测试基于严重程度的重试判断"""
        # 低严重程度错误通常可重试
        low_severity_error = InferenceError("Minor issue")
        low_severity_error.severity = ErrorSeverity.LOW
        assert is_retryable_error(low_severity_error) is True

        # 严重错误通常不可重试
        critical_error = PredictionError("Critical failure")
        critical_error.severity = ErrorSeverity.CRITICAL
        assert is_retryable_error(critical_error) is False

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

    def test_error_equality(self):
        """测试错误对象相等性"""
        error1 = ModelLoadError("Test message", model_name="model1")
        error2 = ModelLoadError("Test message", model_name="model1")
        error3 = ModelLoadError("Different message", model_name="model1")

        # 默认情况下，不同的实例不应该相等
        assert error1 != error2
        assert error1 != error3

        # 但是错误消息应该相同
        assert str(error1) == str(error2)
        assert str(error1) != str(error3)

    def test_error_context_management(self):
        """测试错误上下文管理（如果实现了的话）"""
        # 如果错误类实现了上下文管理器
        if hasattr(ModelLoadError, "__enter__"):
            try:
                with ModelLoadError("Test context") as error:
                    assert isinstance(error, ModelLoadError)
                    raise ValueError("Nested error")
            except ValueError:
                pass  # 预期的异常
            else:
                # 如果没有实现上下文管理器，这个测试应该跳过
                pytest.skip("Error class does not implement context manager")


class TestErrorIntegration:
    """错误集成测试类"""

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

    def test_error_serialization_roundtrip(self):
        """测试错误序列化往返"""
        original_error = HotReloadError(
            "Reload failed",
            model_name="neural_net_v2",
            validation_errors=["Error 1", "Error 2"],
        )

        # 转换为字典
        error_dict = original_error.to_dict()

        # 验证关键字段
        assert error_dict["error"] == "HotReloadError"
        assert error_dict["error_code"] == "HOT_RELOAD_FAILED"
        assert error_dict["details"]["model_name"] == "neural_net_v2"
        assert "validation_errors" in error_dict["details"]

    def test_multiple_error_types_response(self):
        """测试多种错误类型的响应"""
        errors = [
            ModelLoadError("Model not found", model_name="model1"),
            FeatureBuilderError("Invalid feature", feature_name="goals"),
            CacheError("Redis down"),
        ]

        responses = [create_error_response(error) for error in errors]

        assert len(responses) == 3
        assert responses[0]["error"] == "ModelLoadError"
        assert responses[1]["error"] == "FeatureBuilderError"
        assert responses[2]["error"] == "CacheError"

        # 验证不同的错误代码
        error_codes = [resp["error_code"] for resp in responses]
        assert len(set(error_codes)) == 3  # 所有错误代码都不同
