#!/usr/bin/env python3
"""
L2 特征提取器 - 自定义异常
============================

定义了特征提取过程中可能抛出的所有异常类型。

设计原则:
    - 异常层次清晰，便于精确捕获
    - 包含详细的上下文信息
    - 支持异常链追踪

Author: Architecture Team
Version: V26.0 (Stable)
Date: 2025-12-27
"""

from typing import Any


class ExtractionError(Exception):
    """
    特征提取基础异常

    所有特征提取相关异常的父类。

    Attributes:
        message: 错误消息
        context: 错误上下文信息
        extractor_version: 提取器版本
    """

    def __init__(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        extractor_version: str | None = None,
    ):
        self.message = message
        self.context = context or {}
        self.extractor_version = extractor_version
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """格式化错误消息"""
        parts = [self.message]
        if self.extractor_version:
            parts.append(f"Version: {self.extractor_version}")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于日志记录）"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "extractor_version": self.extractor_version,
        }


class ValidationError(ExtractionError):
    """
    特征验证失败异常

    当提取的特征不符合验证规则时抛出。
    """

    def __init__(
        self,
        message: str,
        feature_count: int | None = None,
        required_keys: list[str] | None = None,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if feature_count is not None:
            context["feature_count"] = feature_count
        if required_keys is not None:
            context["required_keys"] = required_keys
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class InsufficientFeaturesError(ValidationError):
    """
    特征维度不足异常

    当提取的特征数量低于最小要求时抛出。
    """

    def __init__(
        self,
        message: str,
        actual_count: int,
        min_required: int,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        context.update(
            {
                "actual_features": actual_count,
                "min_required": min_required,
                "shortage": min_required - actual_count,
            }
        )
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class MissingRequiredKeyError(ValidationError):
    """
    缺少必需键异常

    当特征中缺少必需的键时抛出。
    """

    def __init__(
        self,
        message: str,
        missing_keys: list[str],
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        context["missing_keys"] = missing_keys
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class DataParsingError(ExtractionError):
    """
    数据解析异常

    当原始 JSON 数据格式错误或无法解析时抛出。
    """

    def __init__(
        self,
        message: str,
        raw_data_type: str | None = None,
        parse_error: str | None = None,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if raw_data_type:
            context["raw_data_type"] = raw_data_type
        if parse_error:
            context["parse_error"] = parse_error
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class SchemaMismatchError(DataParsingError):
    """
    数据结构不匹配异常

    当原始数据结构与预期不符时抛出。
    """

    def __init__(
        self,
        message: str,
        expected_path: str | None = None,
        actual_type: str | None = None,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if expected_path:
            context["expected_path"] = expected_path
        if actual_type:
            context["actual_type"] = actual_type
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class ConfigurationError(ExtractionError):
    """
    配置错误异常

    当提取器配置不正确时抛出。
    """

    pass


class CircuitBreakerOpenError(ExtractionError):
    """
    熔断器打开异常

    当熔断器触发时抛出，阻止继续执行。
    """

    def __init__(
        self,
        message: str,
        failure_count: int,
        last_error: str | None = None,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        context.update(
            {
                "failure_count": failure_count,
                "last_error": last_error,
            }
        )
        kwargs["context"] = context
        super().__init__(message, **kwargs)


class RateLimitError(ExtractionError):
    """
    速率限制异常

    当请求速率超过限制时抛出。
    """

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if retry_after is not None:
            context["retry_after_seconds"] = retry_after
        kwargs["context"] = context
        super().__init__(message, **kwargs)
