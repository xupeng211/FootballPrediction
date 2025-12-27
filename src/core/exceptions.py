"""
核心异常定义

定义项目中所有自定义异常类，提供清晰的错误分类和处理。
"""

from typing import Any


class BaseApplicationError(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class DatabaseError(BaseApplicationError):
    """数据库相关异常"""


class ModelError(BaseApplicationError):
    """机器学习模型相关异常"""


class FeatureExtractionError(BaseApplicationError):
    """特征提取相关异常"""


class PredictionError(BaseApplicationError):
    """预测相关异常"""


class ConfigurationError(BaseApplicationError):
    """配置相关异常"""


class ValidationError(BaseApplicationError):
    """数据验证异常"""


class ExternalAPIError(BaseApplicationError):
    """外部API调用异常"""


class CacheError(BaseApplicationError):
    """缓存相关异常"""


class ExplainabilityError(BaseApplicationError):
    """SHAP可解释性相关异常"""


class InferenceServiceError(BaseApplicationError):
    """推理服务相关异常"""


class DataCollectionError(BaseApplicationError):
    """数据收集相关异常"""


class ProcessingError(BaseApplicationError):
    """数据处理相关异常"""


class AuthenticationError(BaseApplicationError):
    """认证相关异常"""


class AuthorizationError(BaseApplicationError):
    """授权相关异常"""


class RateLimitError(BaseApplicationError):
    """速率限制异常"""


class ResourceNotFoundError(BaseApplicationError):
    """资源未找到异常"""


class ConflictError(BaseApplicationError):
    """资源冲突异常"""


class ServiceUnavailableError(BaseApplicationError):
    """服务不可用异常"""


class TimeoutError(BaseApplicationError):
    """超时异常"""


class IntegrationError(BaseApplicationError):
    """系统集成异常"""


class HealthCheckError(BaseApplicationError):
    """健康检查异常"""


class MonitoringError(BaseApplicationError):
    """监控相关异常"""


class CircuitBreakerError(BaseApplicationError):
    """熔断器异常"""


class RetryExhaustedError(BaseApplicationError):
    """重试耗尽异常"""
