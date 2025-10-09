"""
审计装饰器
Audit Decorators

提供自动审计功能的装饰器。
"""

import time
import asyncio
from typing import Optional
import functools
import inspect
from contextvars import ContextVar
from typing import Any, Callable, TypeVar, cast

from .context import AuditContext
from .service import AuditService

# 上下文变量，用于在请求处理过程中传递审计信息
audit_context: ContextVar[AuditContext] = ContextVar("audit_context", default=None)

F = TypeVar("F", bound=Callable[..., Any])


def audit_action(
    action: str,
    resource_type: Optional[str] = None,
    description: Optional[str] = None,
    severity: str = "medium",
):
    """
    审计动作装饰器 / Audit Action Decorator

    自动记录函数或方法的执行信息到审计日志。
    Automatically records function or method execution information to audit log.

    Args:
        action (str): 动作名称 / Action name
        resource_type (Optional[str]): 资源类型 / Resource type
        description (Optional[str]): 描述 / Description
        severity (str): 严重性级别 / Severity level

    Returns:
        装饰后的函数 / Decorated function

    Example:
        ```python
        @audit_action(
            action="create_user",
            resource_type="user",
            description="创建新用户",
            severity="medium"
        )
        async def create_user(user_data: dict):
            # 函数实现
            pass
        ```
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取审计上下文
            context = audit_context.get()
            if not context:
                # 如果没有上下文，尝试从参数中获取
                context = _extract_context_from_args(args, kwargs)

            # 获取审计服务
            audit_service = AuditService()
            await audit_service.initialize()

            # 执行函数并捕获结果
            start_time = None
            result = None
            error = None

            try:
                start_time = time.time()
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                # 记录审计日志
                if context:
                    resource_id = _extract_resource_id(args, kwargs)
                    await audit_service.log_operation(
                        context=context,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        description=description or f"执行 {action} 操作",
                        old_values=kwargs.get("old_values"),
                        new_values=kwargs.get(
                            "new_values", result if result is not None else {}
                        ),
                        error=error,
                        duration=time.time() - start_time if start_time else None,
                        severity=severity,
                    )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取审计上下文
            context = audit_context.get()
            if not context:
                context = _extract_context_from_args(args, kwargs)

            # 获取审计服务
            audit_service = AuditService()
            asyncio.create_task(audit_service.initialize())

            # 执行函数并捕获结果
            start_time = None
            result = None
            error = None

            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                # 记录审计日志
                if context:
                    resource_id = _extract_resource_id(args, kwargs)
                    asyncio.create_task(
                        audit_service.async_log_action(
                            context=context,
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            description=description or f"执行 {action} 操作",
                            old_values=kwargs.get("old_values"),
                            new_values=kwargs.get(
                                "new_values", result if result is not None else {}
                            ),
                            error=error,
                            duration=time.time() - start_time if start_time else None,
                            severity=severity,
                        )
                    )

        # 返回适当的包装器
        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


def audit_api_operation(
    resource_type: Optional[str] = None,
    description: Optional[str] = None,
    severity: str = "medium",
):
    """
    API操作审计装饰器 / API Operation Audit Decorator

    专门用于审计API操作的装饰器。
    Decorator specifically for auditing API operations.

    Args:
        resource_type (Optional[str]): 资源类型 / Resource type
        description (Optional[str]): 描述 / Description
        severity (str): 严重性级别 / Severity level

    Returns:
        装饰后的函数 / Decorated function
    """
    return audit_action(
        action="api_operation",
        resource_type=resource_type,
        description=description,
        severity=severity,
    )


def audit_database_operation(
    table_name: Optional[str] = None,
    description: Optional[str] = None,
    severity: str = "medium",
):
    """
    数据库操作审计装饰器 / Database Operation Audit Decorator

    专门用于审计数据库操作的装饰器。
    Decorator specifically for auditing database operations.

    Args:
        table_name (Optional[str]): 表名 / Table name
        description (Optional[str]): 描述 / Description
        severity (str): 严重性级别 / Severity level

    Returns:
        装饰后的函数 / Decorated function
    """
    return audit_action(
        action="database_operation",
        resource_type="database",
        description=description,
        severity=severity,
        table_name=table_name,
    )


def audit_sensitive_operation(
    description: Optional[str] = None,
    severity: str = "high",
):
    """
    敏感操作审计装饰器 / Sensitive Operation Audit Decorator

    专门用于审计敏感操作的装饰器。
    Decorator specifically for auditing sensitive operations.

    Args:
        description (Optional[str]): 描述 / Description
        severity (str): 严重性级别 / Severity level

    Returns:
        装饰后的函数 / Decorated function
    """
    return audit_action(
        action="sensitive_operation",
        resource_type="sensitive_data",
        description=description or "执行敏感操作",
        severity=severity,
    )


def _extract_context_from_args(args: tuple, kwargs: dict) -> Optional[AuditContext]:
    """
    从参数中提取审计上下文 / Extract Audit Context from Arguments

    Args:
        args: 位置参数 / Positional arguments
        kwargs: 关键字参数 / Keyword arguments

    Returns:
        AuditContext: 审计上下文 / Audit context
    """
    # 尝试从第一个参数获取上下文（如果是AuditContext类型）
    if args and isinstance(args[0], AuditContext):
        return args[0]

    # 尝试从关键字参数获取
    context = kwargs.get("audit_context")
    if isinstance(context, AuditContext):
        return context

    # 尝试从request对象创建
    request = kwargs.get("request")
    if request:
        user_info = kwargs.get("user_info")
        return AuditContext.from_request(request, user_info)

    # 尝试从user_id参数创建
    user_id = kwargs.get("user_id")
    if user_id:
        return AuditContext(user_id=user_id)

    return None


def _extract_resource_id(args: tuple, kwargs: dict) -> Optional[str]:
    """
    从参数中提取资源ID / Extract Resource ID from Arguments

    Args:
        args: 位置参数 / Positional arguments
        kwargs: 关键字参数 / Keyword arguments

    Returns:
        Optional[str]: 资源ID / Resource ID
    """
    # 常见的资源ID参数名
    resource_id_params = [
        "resource_id",
        "id",
        "match_id",
        "user_id",
        "fixture_id",
        "prediction_id",
    ]

    # 从位置参数查找
    if args:
        for param in resource_id_params:
            if param in kwargs:
                return str(kwargs[param])

    # 从关键字参数查找
    for param in resource_id_params:
        if param in kwargs:
            return str(kwargs[param])

    return None
