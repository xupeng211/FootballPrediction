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
    """
    数据库相关异常
    """


class DatabaseConfigurationError(DatabaseError):
    """
    数据库配置异常 (V41.80)

    用于数据库配置错误、环境冲突等情况。

    Examples:
        >>> raise DatabaseConfigurationError("数据库配置错误", details={"db_name": "wrong_db"})
    """

    pass


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


# ============================================================================
# V41.80: 分层异常体系扩展
# ============================================================================


class NetworkError(BaseApplicationError):
    """
    网络相关异常 (V41.80)

    用于所有网络通信相关的错误，包括 HTTP 请求、连接超时、DNS 解析失败等。

    Examples:
        >>> raise NetworkError("无法连接到服务器", details={"host": "example.com", "port": 443})
    """

    pass


class DataAlignmentError(BaseApplicationError):
    """
    数据对齐异常 (V41.80)

    用于数据对齐过程中的各种错误。

    Examples:
        >>> raise DataAlignmentError("数据对齐失败")
    """

    pass


class URLParsingError(DataAlignmentError):
    """
    URL 解析异常 (V41.80)

    用于 URL 解析失败的情况。

    Examples:
        >>> raise URLParsingError("URL 格式无效", details={"url": "invalid-url"})
    """

    pass


class TeamMatchingError(DataAlignmentError):
    """
    队名匹配异常 (V41.80)

    用于队名匹配失败的情况。

    Examples:
        >>> raise TeamMatchingError("队名匹配失败", details={"team": "Unknown Team"})
    """

    pass


class HashExtractionError(DataAlignmentError):
    """
    哈希提取异常 (V41.80)

    用于哈希提取失败的情况。

    Examples:
        >>> raise HashExtractionError("哈希提取失败", details={"url": "example.com/xyz/"})
    """

    pass


class ProxyError(BaseApplicationError):
    """
    代理相关异常 (V41.80)

    用于代理操作相关的错误。

    Examples:
        >>> raise ProxyError("代理操作失败")
    """

    pass


class ProxyConnectionError(ProxyError):
    """
    代理连接异常 (V41.80)

    用于代理连接失败的情况。

    Examples:
        >>> raise ProxyConnectionError("代理连接失败", details={"host": "127.0.0.1", "port": 7891})
    """

    pass


class ProxyHealthError(ProxyError):
    """
    代理健康检查异常 (V41.80)

    用于代理健康检查失败的情况。

    Examples:
        >>> raise ProxyHealthError("代理不健康", details={"port": 7891, "failures": 3})
    """

    pass
