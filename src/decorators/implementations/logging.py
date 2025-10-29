"""
日志装饰器实现
Logging Decorator Implementation

记录函数执行的前后信息。
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ...core.logging import get_logger
from ..base import Decorator, DecoratorContext

logger = get_logger(__name__)


class LoggingDecorator(Decorator):
    """日志装饰器，记录函数执行的前后信息"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        level: str = "INFO",
        log_args: bool = True,
        log_result: bool = True,
        log_exception: bool = True,
        include_context: bool = False,
    ):
        super().__init__(component, name)
        self.level = level.upper()
        self.log_args = log_args
        self.log_result = log_result
        self.log_exception = log_exception
        self.include_context = include_context

    async def _execute(self, *args, **kwargs) -> Any:
        """执行日志装饰器"""
        func_name = self.component.get_name()
        logger_instance = logger

        # 记录函数开始执行
        log_data = {
            "event": "function_start",
            "function": func_name,
            "decorator": self.name,
        }

        if self.log_args:
            # 安全地记录参数（避免记录敏感信息）
            safe_args = self._sanitize_args(args)
            safe_kwargs = self._sanitize_kwargs(kwargs)
            log_data["args"] = safe_args
            log_data["kwargs"] = safe_kwargs

        if self.include_context and "context" in kwargs:
            context = kwargs["context"]
            if isinstance(context, DecoratorContext):
                log_data["trace_id"] = context.trace_id

        logger_instance.log(getattr(logging, self.level), json.dumps(log_data))

        try:
            # 执行被装饰的函数
            result = await self.component.execute(*args, **kwargs)

            # 记录函数执行成功
            if self.log_result:
                success_log = {
                    "event": "function_success",
                    "function": func_name,
                    "decorator": self.name,
                    "result": self._sanitize_result(result),
                }

                if self.include_context and "context" in kwargs:
                    context = kwargs["context"]
                    if isinstance(context, DecoratorContext):
                        success_log["execution_time"] = context.get_execution_time()
                        success_log["execution_path"] = context.execution_path

                logger_instance.log(getattr(logging, self.level), json.dumps(success_log))

            return result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            # 记录函数执行失败
            if self.log_exception:
                error_log = {
                    "event": "function_error",
                    "function": func_name,
                    "decorator": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

                if self.include_context and "context" in kwargs:
                    context = kwargs["context"]
                    if isinstance(context, DecoratorContext):
                        error_log["execution_time"] = context.get_execution_time()

                logger_instance.error(json.dumps(error_log))

            raise

    def _sanitize_args(self, args: tuple) -> List[Any]:
        """清理参数，移除敏感信息"""
        sanitized: List[Any] = []

        for arg in args:
            if isinstance(arg, dict):
                sanitized.append(self._sanitize_dict(arg))
            elif isinstance(arg, (list, tuple)):
                sanitized.append(self._sanitize_sequence(arg))
            else:
                sanitized.append(str(arg)[:100])  # 限制长度

        return sanitized

    def _sanitize_kwargs(self, kwargs: dict) -> Dict[str, Any]:
        """清理关键字参数，移除敏感信息"""
        return self._sanitize_dict(kwargs)

    def _sanitize_dict(self, data: dict) -> Dict[str, Any]:
        """清理字典，移除敏感信息"""
        sensitive_keys = ["password", "token", "secret", "key", "auth"]
        sanitized: Dict[str, Any] = {}

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = self._sanitize_sequence(value)
            else:
                sanitized[key] = str(value)[:100]

        return sanitized

    def _sanitize_sequence(self, seq) -> List[Any]:
        """清理序列，移除敏感信息"""
        sanitized: List[Any] = []

        for item in seq:
            if isinstance(item, dict):
                sanitized.append(self._sanitize_dict(item))
            elif isinstance(item, (list, tuple)):
                sanitized.append(self._sanitize_sequence(item))
            else:
                sanitized.append(str(item)[:100])

        return sanitized

    def _sanitize_result(self, result: Any) -> Any:
        """清理结果，移除敏感信息"""
        if isinstance(result, dict):
            return self._sanitize_dict(result)
        elif isinstance(result, (list, tuple)):
            return self._sanitize_sequence(result)
        else:
            return str(result)[:100]
