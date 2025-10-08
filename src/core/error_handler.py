"""
全局错误处理器
Global Error Handler

提供统一的错误处理和日志记录功能：
- 自定义异常类
- 错误码定义
- 错误响应格式化
- 错误通知和告警

Provides unified error handling and logging:
- Custom exception classes
- Error code definitions
- Error response formatting
- Error notifications and alerts
"""

import os
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

import sentry_sdk
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorCode(Enum):
    """错误码枚举"""
    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # 业务错误
    MATCH_NOT_FOUND = "MATCH_NOT_FOUND"
    TEAM_NOT_FOUND = "TEAM_NOT_FOUND"
    LEAGUE_NOT_FOUND = "LEAGUE_NOT_FOUND"
    PREDICTION_FAILED = "PREDICTION_FAILED"
    MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"

    # 数据错误
    DATA_COLLECTION_FAILED = "DATA_COLLECTION_FAILED"
    DATA_VALIDATION_FAILED = "DATA_VALIDATION_FAILED"
    CACHE_ERROR = "CACHE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"

    # 外部服务错误
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    MLFLOW_ERROR = "MLFLOW_ERROR"
    REDIS_ERROR = "REDIS_ERROR"


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseAppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        cause: Optional[Exception] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.severity = severity
        self.cause = cause
        self.timestamp = datetime.now()

        super().__init__(message)


class BusinessError(BaseAppException):
    """业务逻辑错误"""
    pass


class DataError(BaseAppException):
    """数据相关错误"""
    pass


class ExternalServiceError(BaseAppException):
    """外部服务错误"""
    pass


class ValidationError(BaseAppException):
    """数据验证错误"""
    def __init__(
        self,
        message: str,
        field: str,
        value: Any,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({
            "field": field,
            "value": str(value),
        })
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details,
            **kwargs
        )


class NotFoundError(BaseAppException):
    """资源未找到错误"""
    def __init__(self, resource_type: str, resource_id: Any, **kwargs):
        message = f"{resource_type} with ID {resource_id} not found"
        details = kwargs.get("details", {})
        details.update({
            "resource_type": resource_type,
            "resource_id": str(resource_id),
        })
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            status_code=404,
            details=details,
            **kwargs
        )


class PredictionError(BusinessError):
    """预测错误"""
    def __init__(self, match_id: int, reason: str, **kwargs):
        message = f"Prediction failed for match {match_id}: {reason}"
        details = kwargs.get("details", {})
        details.update({
            "match_id": match_id,
            "reason": reason,
        })
        super().__init__(
            message=message,
            error_code=ErrorCode.PREDICTION_FAILED,
            status_code=500,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs
        )


class DataCollectionError(DataError):
    """数据收集错误"""
    def __init__(self, source: str, error: str, **kwargs):
        message = f"Data collection failed from {source}: {error}"
        details = kwargs.get("details", {})
        details.update({
            "source": source,
            "error": error,
        })
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_COLLECTION_FAILED,
            details=details,
            **kwargs
        )


class CacheError(DataError):
    """缓存错误"""
    def __init__(self, operation: str, key: str, **kwargs):
        message = f"Cache {operation} failed for key {key}"
        details = kwargs.get("details", {})
        details.update({
            "operation": operation,
            "key": key,
        })
        super().__init__(
            message=message,
            error_code=ErrorCode.CACHE_ERROR,
            details=details,
            **kwargs
        )


class ErrorHandler:
    """错误处理器"""

    def __init__(self, enable_sentry: bool = False):
        self.enable_sentry = enable_sentry
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, Dict[str, Any]] = {}

    def handle_exception(
        self,
        exception: Exception,
        request: Optional[Request] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> JSONResponse:
        """处理异常并返回响应"""

        # 确定错误类型和状态码
        if isinstance(exception, BaseAppException):
            error_info = self._format_app_exception(exception)
        elif isinstance(exception, (StarletteHTTPException, HTTPException)):
            error_info = self._format_http_exception(exception)
        else:
            error_info = self._format_unknown_exception(exception)

        # 添加请求信息
        if request:
            error_info["request"] = {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client": request.client.host if request.client else None,
            }

        # 添加上下文信息
        if context:
            error_info["context"] = context

        # 记录错误
        self._log_error(error_info)

        # 发送到Sentry（如果启用）
        if self.enable_sentry:
            self._send_to_sentry(exception, request, context)

        # 更新错误统计
        self._update_error_stats(error_info)

        # 检查是否需要告警
        self._check_alert_conditions(error_info)

        # 返回响应
        return JSONResponse(
            status_code=error_info["status_code"],
            content=error_info["response"]
        )

    def _format_app_exception(self, exception: BaseAppException) -> Dict[str, Any]:
        """格式化应用异常"""
        return {
            "type": "app_exception",
            "status_code": exception.status_code,
            "response": {
                "error": {
                    "code": exception.error_code.value,
                    "message": exception.message,
                    "type": exception.error_code.value.lower(),
                    "details": exception.details,
                    "timestamp": exception.timestamp.isoformat(),
                }
            },
            "severity": exception.severity.value,
            "error_class": exception.__class__.__name__,
        }

    def _format_http_exception(self, exception: Union[StarletteHTTPException, HTTPException]) -> Dict[str, Any]:
        """格式化HTTP异常"""
        return {
            "type": "http_exception",
            "status_code": exception.status_code,
            "response": {
                "error": {
                    "code": f"HTTP_{exception.status_code}",
                    "message": exception.detail,
                    "type": "http_error",
                }
            },
            "severity": ErrorSeverity.MEDIUM.value,
            "error_class": exception.__class__.__name__,
        }

    def _format_unknown_exception(self, exception: Exception) -> Dict[str, Any]:
        """格式化未知异常"""
        return {
            "type": "unknown_exception",
            "status_code": 500,
            "response": {
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An unexpected error occurred",
                    "type": "internal_error",
                }
            },
            "severity": ErrorSeverity.HIGH.value,
            "error_class": exception.__class__.__name__,
            "traceback": traceback.format_exc(),
        }

    def _log_error(self, error_info: Dict[str, Any]):
        """记录错误日志"""
        severity = error_info.get("severity", ErrorSeverity.MEDIUM.value)
        message = error_info["response"]["error"]["message"]
        code = error_info["response"]["error"]["code"]

        if severity == ErrorSeverity.CRITICAL.value:
            logger.critical(f"[{code}] {message}", extra=error_info)
        elif severity == ErrorSeverity.HIGH.value:
            logger.error(f"[{code}] {message}", extra=error_info)
        elif severity == ErrorSeverity.MEDIUM.value:
            logger.warning(f"[{code}] {message}", extra=error_info)
        else:
            logger.info(f"[{code}] {message}", extra=error_info)

    def _send_to_sentry(
        self,
        exception: Exception,
        request: Optional[Request] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """发送错误到Sentry"""
        if not self.enable_sentry:
            return

        try:
            with sentry_sdk.configure_scope as scope:
                # 添加请求信息
                if request:
                    scope.set_context("request", {
                        "method": request.method,
                        "url": str(request.url),
                        "headers": dict(request.headers),
                    })

                # 添加上下文信息
                if context:
                    scope.set_context("application", context)

                # 添加标签
                scope.set_tag("error_type", exception.__class__.__name__)

                # 发送到Sentry
                sentry_sdk.capture_exception(exception)
        except Exception as e:
            logger.error(f"Failed to send error to Sentry: {e}")

    def _update_error_stats(self, error_info: Dict[str, Any]):
        """更新错误统计"""
        error_code = error_info["response"]["error"]["code"]

        # 更新计数
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1

        # 记录最近错误
        self.last_errors[error_code] = {
            "timestamp": datetime.now().isoformat(),
            "message": error_info["response"]["error"]["message"],
            "severity": error_info.get("severity"),
        }

    def _check_alert_conditions(self, error_info: Dict[str, Any]):
        """检查告警条件"""
        error_code = error_info["response"]["error"]["code"]
        severity = error_info.get("severity", ErrorSeverity.MEDIUM.value)

        # 严重错误立即告警
        if severity == ErrorSeverity.CRITICAL.value:
            self._send_alert(error_info, "Critical error occurred")

        # 错误频率过高告警
        if self.error_counts.get(error_code, 0) > 10:  # 1分钟内超过10次
            self._send_alert(
                error_info,
                f"High error frequency for {error_code}: {self.error_counts[error_code]} occurrences"
            )

    def _send_alert(self, error_info: Dict[str, Any], message: str):
        """发送告警通知"""
        # 这里可以实现各种告警方式：
        # - Slack通知
        # - 邮件通知
        # - 短信通知
        # - 钉钉/企业微信通知

        logger.error(f"ALERT: {message}", extra=error_info)

        # 示例：发送到Slack
        try:
            import requests

            slack_webhook_url = os.getenv("SLACK_ALERT_WEBHOOK_URL")
            if slack_webhook_url:
                payload = {
                    "text": message,
                    "attachments": [
                        {
                            "color": "red" if error_info.get("severity") == ErrorSeverity.CRITICAL.value else "yellow",
                            "fields": [
                                {
                                    "title": "Error Code",
                                    "value": error_info["response"]["error"]["code"],
                                    "short": True,
                                },
                                {
                                    "title": "Severity",
                                    "value": error_info.get("severity", "unknown"),
                                    "short": True,
                                },
                                {
                                    "title": "Message",
                                    "value": error_info["response"]["error"]["message"],
                                    "short": False,
                                },
                            ],
                            "timestamp": datetime.now().timestamp(),
                        }
                    ],
                }

                requests.post(slack_webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            "error_counts": self.error_counts,
            "last_errors": self.last_errors,
            "total_errors": sum(self.error_counts.values()),
        }

    def reset_stats(self):
        """重置错误统计"""
        self.error_counts.clear()
        self.last_errors.clear()


# 全局错误处理器实例
error_handler = ErrorHandler(enable_sentry=bool(os.getenv("SENTRY_DSN")))


def handle_exception(
    exception: Exception,
    request: Optional[Request] = None,
    context: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """全局异常处理入口"""
    return error_handler.handle_exception(exception, request, context)


# 装饰器：用于自动处理异常
def handle_errors(
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    error_message: Optional[str] = None,
    reraise: bool = False,
):
    """错误处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, BaseAppException):
                    if reraise:
                        raise
                    return handle_exception(e)
                else:
                    app_exception = BaseAppException(
                        message=error_message or str(e),
                        error_code=error_code,
                        cause=e,
                    )
                    if reraise:
                        raise app_exception
                    return handle_exception(app_exception)
        return wrapper
    return decorator


# 异步装饰器
def handle_async_errors(
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    error_message: Optional[str] = None,
    reraise: bool = False,
):
    """异步错误处理装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, BaseAppException):
                    if reraise:
                        raise
                    return handle_exception(e)
                else:
                    app_exception = BaseAppException(
                        message=error_message or str(e),
                        error_code=error_code,
                        cause=e,
                    )
                    if reraise:
                        raise app_exception
                    return handle_exception(app_exception)
        return wrapper
    return decorator