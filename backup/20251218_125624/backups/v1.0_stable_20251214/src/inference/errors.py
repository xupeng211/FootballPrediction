"""
Inference Service Error Definitions
推理服务错误定义

定义推理服务中使用的所有异常类和错误码。
"""

from typing import Any, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""

    # Model Loading Errors
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    MODEL_VERSION_INVALID = "MODEL_VERSION_INVALID"
    MODEL_CORRUPTED = "MODEL_CORRUPTED"

    # Feature Building Errors
    FEATURE_INVALID = "FEATURE_INVALID"
    FEATURE_MISSING = "FEATURE_MISSING"
    FEATURE_BUILD_FAILED = "FEATURE_BUILD_FAILED"
    FEATURE_MISMATCH = "FEATURE_MISMATCH"

    # Prediction Errors
    PREDICTION_FAILED = "PREDICTION_FAILED"
    PREDICTION_TIMEOUT = "PREDICTION_TIMEOUT"
    PREDICTION_INVALID_INPUT = "PREDICTION_INVALID_INPUT"

    # Cache Errors
    CACHE_CONNECTION_FAILED = "CACHE_CONNECTION_FAILED"
    CACHE_OPERATION_FAILED = "CACHE_OPERATION_FAILED"
    CACHE_SERIALIZATION_ERROR = "CACHE_SERIALIZATION_ERROR"

    # Hot Reload Errors
    HOT_RELOAD_FAILED = "HOT_RELOAD_FAILED"
    HOT_RELOAD_INVALID_MODEL = "HOT_RELOAD_INVALID_MODEL"
    HOT_RELOAD_ROLLBACK_FAILED = "HOT_RELOAD_ROLLBACK_FAILED"

    # General Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class InferenceError(Exception):
    """推理服务基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }


class ModelLoadError(InferenceError):
    """模型加载错误"""

    def __init__(self, message: str, model_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if model_name:
            details["model_name"] = model_name
        super().__init__(
            message=message, error_code=ErrorCode.MODEL_LOAD_FAILED, details=details
        )


class FeatureBuilderError(InferenceError):
    """特征构建错误"""

    def __init__(self, message: str, feature_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if feature_name:
            details["feature_name"] = feature_name
        super().__init__(
            message=message, error_code=ErrorCode.FEATURE_BUILD_FAILED, details=details
        )


class PredictionError(InferenceError):
    """预测错误"""

    def __init__(self, message: str, prediction_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if prediction_id:
            details["prediction_id"] = prediction_id
        super().__init__(
            message=message, error_code=ErrorCode.PREDICTION_FAILED, details=details
        )


class CacheError(InferenceError):
    """缓存错误"""

    def __init__(self, message: str, cache_key: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if cache_key:
            details["cache_key"] = cache_key
        super().__init__(
            message=message,
            error_code=ErrorCode.CACHE_OPERATION_FAILED,
            details=details,
        )


class HotReloadError(InferenceError):
    """热更新错误"""

    def __init__(self, message: str, model_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if model_name:
            details["model_name"] = model_name
        super().__init__(
            message=message, error_code=ErrorCode.HOT_RELOAD_FAILED, details=details
        )


# Error handler utilities
def handle_inference_error(func):
    """推理服务错误处理装饰器"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InferenceError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            # Convert unexpected errors to InferenceError
            raise InferenceError(
                message=f"Unexpected error in {func.__name__}: {str(e)}",
                error_code=ErrorCode.INTERNAL_ERROR,
                details={"original_error": str(e)},
            )

    return wrapper
