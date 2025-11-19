#!/usr/bin/env python3
"""异常定义模块
Football Prediction SDK - 异常类定义.

Author: Claude Code
Version: 1.0.0
"""

from typing import Any


class FootballPredictionError(Exception):
    """基础异常类."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        response: Any | None = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.response = response

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class AuthenticationError(FootballPredictionError):
    """认证相关错误."""

    def __init__(self, message: str = "认证失败", **kwargs):
        super().__init__(message, **kwargs)


class ValidationError(FootballPredictionError):
    """数据验证错误."""

    def __init__(self, message: str = "数据验证失败", **kwargs):
        super().__init__(message, **kwargs)


class BusinessError(FootballPredictionError):
    """业务逻辑错误."""

    def __init__(self, message: str = "业务逻辑错误", **kwargs):
        super().__init__(message, **kwargs)


class SystemError(FootballPredictionError):
    """系统错误."""

    def __init__(self, message: str = "系统错误", **kwargs):
        super().__init__(message, **kwargs)


class RateLimitError(FootballPredictionError):
    """限流错误."""

    def __init__(
        self,
        message: str = "请求频率超限",
        retry_after: int | None = None,
        limit: int | None = None,
        window: int | None = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.limit = limit
        self.window = window

        if retry_after:
            self.details.update({
                "retry_after": retry_after,
                "retry_after_human": f"{retry_after}秒"
            })

    def get_retry_after_seconds(self) -> int | None:
        """获取重试等待时间（秒）."""
        return self.retry_after


class NotFoundError(BusinessError):
    """资源不存在错误."""

    def __init__(self, message: str = "资源不存在", resource_type: str = None, resource_id: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if resource_type:
            self.details["resource_type"] = resource_type
        if resource_id:
            self.details["resource_id"] = resource_id


class ConflictError(BusinessError):
    """冲突错误."""

    def __init__(self, message: str = "资源冲突", **kwargs):
        super().__init__(message, **kwargs)


class ExternalServiceError(SystemError):
    """外部服务错误."""

    def __init__(self, message: str = "外部服务错误", service_name: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if service_name:
            self.details["service_name"] = service_name


class ConfigurationError(FootballPredictionError):
    """配置错误."""

    def __init__(self, message: str = "配置错误", **kwargs):
        super().__init__(message, **kwargs)


# 错误代码映射
ERROR_CODE_MAP = {
    # 认证错误
    "AUTH_001": AuthenticationError,
    "AUTH_002": AuthenticationError,
    "AUTH_003": AuthenticationError,
    "AUTH_004": AuthenticationError,
    "AUTH_005": AuthenticationError,

    # 验证错误
    "VALIDATION_001": ValidationError,
    "VALIDATION_002": ValidationError,
    "VALIDATION_003": ValidationError,
    "VALIDATION_004": ValidationError,

    # 业务错误
    "BUSINESS_001": NotFoundError,
    "BUSINESS_002": BusinessError,
    "BUSINESS_003": ConflictError,
    "BUSINESS_004": BusinessError,

    # 系统错误
    "SYSTEM_001": SystemError,
    "SYSTEM_002": ExternalServiceError,
    "SYSTEM_003": SystemError,
    "SYSTEM_004": SystemError,

    # 外部服务错误
    "EXTERNAL_001": ExternalServiceError,
    "EXTERNAL_002": ExternalServiceError,

    # 限流错误
    "RATE_LIMIT_001": RateLimitError,
}


def create_exception_from_response(response_data: dict[str, Any], response: Any = None) -> FootballPredictionError:
    """从API响应创建对应的异常实例.

    Args:
        response_data: API错误响应数据
        response: HTTP响应对象

    Returns:
        FootballPredictionError: 对应的异常实例
    """
    error_info = response_data.get("error", {})
    error_code = error_info.get("code")
    message = error_info.get("message", "未知错误")
    details = error_info.get("details", {})

    # 根据错误码选择异常类型
    exception_class = ERROR_CODE_MAP.get(error_code, FootballPredictionError)

    # 特殊处理限流错误
    if error_code == "RATE_LIMIT_001":
        retry_after = details.get("retry_after")
        limit = details.get("limit")
        window = details.get("window")
        return exception_class(
            message=message,
            error_code=error_code,
            details=details,
            response=response,
            retry_after=retry_after,
            limit=limit,
            window=window
        )

    # 特殊处理资源不存在错误
    if error_code == "BUSINESS_001":
        resource_type = details.get("resource_type")
        resource_id = details.get("resource_id")
        return exception_class(
            message=message,
            error_code=error_code,
            details=details,
            response=response,
            resource_type=resource_type,
            resource_id=resource_id
        )

    # 通用异常创建
    return exception_class(
        message=message,
        error_code=error_code,
        details=details,
        response=response
    )
