#!/usr/bin/env python3
"""
V26.2 提取器异常处理装饰器 (Security Audit 优化版)
======================================================

功能:
  - 捕获解析异常，记录详细的 match_id 和堆栈
  - 跳过问题记录而非中断进程
  - 支持生产日志集成

Security Audit 优化 (2026-01-06):
  - P1-3: 完备类型注解
  - 改进错误上下文捕获
  - 支持堆栈跟踪长度限制

Author: Senior Data Architect
Version: V151.0 (Security Audit Fixed)
Date: 2026-01-06
"""

from collections.abc import Callable
from dataclasses import dataclass, field
import functools
import logging
import time
import traceback
from typing import Any, TypeVar

logger = logging.getLogger(__name__)


# ============================================================================
# 类型定义 (P1-3: 完备类型注解)
# ============================================================================

T = TypeVar("T")

ExtractorFunc = Callable[[dict[str, Any]], "ExtractionResult"]


@dataclass
class ErrorContext:
    """
    错误上下文信息

    Attributes:
        match_id: 比赛 ID
        error_type: 错误类型
        error_message: 错误消息
        function: 失败的函数名
        traceback: 堆栈跟踪
        timestamp: 发生时间戳
    """

    match_id: str
    error_type: str
    error_message: str
    function: str
    traceback: str
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# 安全提取装饰器 (优化版)
# ============================================================================


def safe_extract(
    match_id_field: str = "match_id",
    include_traceback: bool = True,
    max_error_length: int = 500,
) -> Callable[[ExtractorFunc], ExtractorFunc]:
    """
    安全提取装饰器 - 捕获异常并记录详细信息

    优化 (Security Audit):
        - P1-3: 完备的类型注解
        - 改进错误上下文捕获
        - 支持堆栈跟踪长度限制

    Args:
        match_id_field: 用于标识记录的字段名
        include_traceback: 是否包含完整堆栈跟踪
        max_error_length: 错误消息最大长度

    Example:
        @safe_extract(match_id_field='match_id')
        def extract_features(self, raw_data: dict) -> ExtractionResult:
            ...
    """

    def decorator(func: ExtractorFunc) -> ExtractorFunc:
        @functools.wraps(func)
        def wrapper(
            self: Any, raw_data: dict[str, Any], *args: Any, **kwargs: Any
        ) -> "ExtractionResult":
            try:
                return func(self, raw_data, *args, **kwargs)
            except Exception as e:
                # 提取 match_id 用于日志
                match_id = raw_data.get(match_id_field, "UNKNOWN")

                # 截断错误消息（防止日志爆炸）
                error_message = str(e)
                if len(error_message) > max_error_length:
                    error_message = error_message[:max_error_length] + "..."

                # 构建详细的错误信息
                error_details = ErrorContext(
                    match_id=match_id,
                    error_type=type(e).__name__,
                    error_message=error_message,
                    function=func.__name__,
                    traceback=traceback.format_exc() if include_traceback else "",
                )

                # 记录到生产日志
                logger.exception(
                    "Feature extraction failed",
                    match_id=error_details.match_id,
                    error_type=error_details.error_type,
                    error_message=error_details.error_message,
                    function=error_details.function,
                )

                # 返回失败结果而不是崩溃
                from src.processors.base_extractor import ExtractionResult, ExtractionStatus

                return ExtractionResult(
                    status=ExtractionStatus.FAILED,
                    features={},
                    errors=[error_message],
                    metadata={
                        "match_id": match_id,
                        "error_type": error_details.error_type,
                        "function": error_details.function,
                    },
                )

        return wrapper

    return decorator


# ============================================================================
# 自定义异常类
# ============================================================================


class ExtractionError(Exception):
    """
    特征提取专用异常

    Attributes:
        message: 错误消息
        match_id: 关联的比赛 ID
        context: 额外的上下文信息
    """

    def __init__(
        self, message: str, match_id: str | None = None, context: dict[str, Any] | None = None
    ):
        """
        初始化异常

        Args:
            message: 错误消息
            match_id: 关联的比赛 ID（可选）
            context: 额外的上下文信息（可选）
        """
        super().__init__(message)
        self.match_id = match_id
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "match_id": self.match_id,
            "context": self.context,
        }


class DataValidationError(ExtractionError):
    """
    数据验证失败异常

    当输入数据不符合预期格式时抛出。
    """

    def __init__(
        self,
        message: str,
        match_id: str | None = None,
        context: dict[str, Any] | None = None,
        field_name: str | None = None,
        expected_type: str | None = None,
        actual_type: str | None = None,
    ):
        """
        初始化验证错误

        Args:
            message: 错误消息
            match_id: 关联的比赛 ID
            context: 额外的上下文信息
            field_name: 字段名
            expected_type: 期望的类型
            actual_type: 实际的类型
        """
        super().__init__(message, match_id, context)
        self.field_name = field_name
        self.expected_type = expected_type
        self.actual_type = actual_type


class SparsityFilterError(ExtractionError):
    """
    剪枝过滤器异常

    当稀疏度过滤器失败时抛出。
    """

    def __init__(
        self,
        message: str,
        match_id: str | None = None,
        context: dict[str, Any] | None = None,
        feature_count: int | None = None,
        sparsity_threshold: float | None = None,
    ):
        """
        初始化剪枝过滤器错误

        Args:
            message: 错误消息
            match_id: 关联的比赛 ID
            context: 额外的上下文信息
            feature_count: 特征数量
            sparsity_threshold: 稀疏度阈值
        """
        super().__init__(message, match_id, context)
        self.feature_count = feature_count
        self.sparsity_threshold = sparsity_threshold
