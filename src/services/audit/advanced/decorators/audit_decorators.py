"""
审计装饰器
Audit Decorators

提供审计功能的装饰器实现。
"""




logger = get_logger(__name__)


def audit_action(
    action: str,
    resource_type: Optional[str] = None,
    severity: str = "medium",
    auto_context: bool = True,
    capture_args: bool = False,
    capture_result: bool = False,
    capture_error: bool = True,
):
    """
    审计动作装饰器 / Audit Action Decorator

    Args:
        action: 动作名称 / Action name
        resource_type: 资源类型 / Resource type
        severity: 严重性级别 / Severity level
        auto_context: 自动获取上下文 / Auto get context
        capture_args: 捕获函数参数 / Capture function arguments
        capture_result: 捕获返回结果 / Capture return result
        capture_error: 捕获错误信息 / Capture error information

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            context = None
            error = None
            result = None

            try:
                # 获取审计上下文
                if auto_context:
                    context = _extract_audit_context(args, kwargs)

                # 执行原函数
                result = await func(*args, **kwargs)

                return result

            except Exception as e:
                error = str(e)
                logger.error(f"审计装饰器捕获错误: {e}")
                raise

            finally:
                # 记录审计日志
                await _log_audit_action(
                    context=context,
                    action=action,
                    resource_type=resource_type,
                    severity=severity,
                    args=args if capture_args else None,
                    kwargs=kwargs if capture_args else None,
                    result=result if capture_result else None,
                    error=error if capture_error else None,
                    duration=time.time() - start_time,
                    func_name=func.__name__,
                    func_module=func.__module__,
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            context = None
            error = None
            result = None

            try:
                # 获取审计上下文
                if auto_context:
                    context = _extract_audit_context(args, kwargs)

                # 执行原函数
                result = func(*args, **kwargs)

                return result

            except Exception as e:
                error = str(e)
                logger.error(f"审计装饰器捕获错误: {e}")
                raise

            finally:
                # 记录审计日志（同步版本）
                _log_audit_action_sync(
                    context=context,
                    action=action,
                    resource_type=resource_type,
                    severity=severity,
                    args=args if capture_args else None,
                    kwargs=kwargs if capture_args else None,
                    result=result if capture_result else None,
                    error=error if capture_error else None,
                    duration=time.time() - start_time,
                    func_name=func.__name__,
                    func_module=func.__module__,
                )

        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def audit_api_endpoint(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    severity: str = "medium",
    include_request_data: bool = False,
    include_response_data: bool = False,
):
    """
    API端点审计装饰器 / API Endpoint Audit Decorator

    Args:
        action: 动作名称 / Action name
        resource_type: 资源类型 / Resource type
        severity: 严重性级别 / Severity level
        include_request_data: 包含请求数据 / Include request data
        include_response_data: 包含响应数据 / Include response data

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            context = None
            error = None
            result = None

            try:
                # 从FastAPI请求中提取上下文
                context = _extract_api_context(args, kwargs)

                # 确定动作
                if not action:
                    func_action = _determine_action_from_method(func.__name__)
                else:
                    func_action = action

                # 执行原函数
                result = await func(*args, **kwargs)

                return result

            except Exception as e:
                error = str(e)
                logger.error(f"API端点审计装饰器捕获错误: {e}")
                raise

            finally:
                # 记录审计日志
                await _log_audit_action(
                    context=context,
                    action=func_action,
                    resource_type=resource_type,
                    severity=severity,
                    args=args if include_request_data else None,
                    kwargs=kwargs if include_request_data else None,
                    result=result if include_response_data else None,
                    error=error,
                    duration=time.time() - start_time,
                    func_name=func.__name__,
                    func_module=func.__module__,
                    endpoint_type="api",
                )

        return wrapper

    return decorator


def audit_database_operation(
    table_name: str,
    operation: str,
    severity: str = "medium",
    capture_changes: bool = True,
):
    """
    数据库操作审计装饰器 / Database Operation Audit Decorator

    Args:
        table_name: 表名 / Table name
        operation: 操作类型 / Operation type
        severity: 严重性级别 / Severity level
        capture_changes: 捕获变更数据 / Capture change data

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            context = None
            error = None
            result = None
            old_values = None
            new_values = None

            try:
                # 获取审计上下文
                context = _extract_audit_context(args, kwargs)

                # 如果需要捕获变更，尝试获取旧值
                if capture_changes and operation in ["update", "delete"]:
                    old_values = await _extract_old_values(table_name, args, kwargs)

                # 执行原函数
                result = await func(*args, **kwargs)

                # 如果需要捕获变更，尝试获取新值
                if capture_changes and operation in ["create", "update"]:
                    new_values = await _extract_new_values(result, table_name)

                return result

            except Exception as e:
                error = str(e)
                logger.error(f"数据库操作审计装饰器捕获错误: {e}")
                raise

            finally:
                # 记录审计日志
                await _log_audit_action(
                    context=context,
                    action=operation,
                    resource_type=table_name,
                    severity=severity,
                    old_values=old_values,
                    new_values=new_values,
                    error=error,
                    duration=time.time() - start_time,
                    func_name=func.__name__,
                    func_module=func.__module__,
                    operation_type="database",
                    table_name=table_name,
                )

        return wrapper

    return decorator


def audit_sensitive_operation(
    sensitivity_level: str = "high",
    require_approval: bool = False,
    approval_role: Optional[str] = None,
):
    """
    敏感操作审计装饰器 / Sensitive Operation Audit Decorator

    Args:
        sensitivity_level: 敏感度级别 / Sensitivity level
        require_approval: 是否需要审批 / Require approval
        approval_role: 审批角色 / Approval role

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            context = None
            error = None
            result = None

            try:
                # 获取审计上下文
                context = _extract_audit_context(args, kwargs)

                # 检查审批要求
                if require_approval:
                    await _check_approval(context, approval_role)

                # 确定严重性
                severity = "high" if sensitivity_level == "high" else "medium"

                # 执行原函数
                result = await func(*args, **kwargs)

                return result

            except Exception as e:
                error = str(e)
                logger.error(f"敏感操作审计装饰器捕获错误: {e}")
                raise

            finally:
                # 记录审计日志
                await _log_audit_action(
                    context=context,
                    action=func.__name__,
                    resource_type="sensitive_operation",
                    severity=severity,
                    error=error,
                    duration=time.time() - start_time,
                    func_name=func.__name__,
                    func_module=func.__module__,
                    operation_type="sensitive",
                    sensitivity_level=sensitivity_level,
                    approval_required=require_approval,
                )

        return wrapper

    return decorator


def audit_batch_operation(
    operation_type: str,
    severity: str = "medium",
    batch_size_threshold: int = 10,
):
    """
    批量操作审计装饰器 / Batch Operation Audit Decorator

    Args:
        operation_type: 操作类型 / Operation type
        severity: 严重性级别 / Severity level
        batch_size_threshold: 批量大小阈值 / Batch size threshold

    Returns:
        Callable: 装饰器函数 / Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            context = None
            error = None
            result = None
            batch_size = 0

            try:
                # 获取审计上下文
                context = _extract_audit_context(args, kwargs)

                # 获取批量大小
                batch_size = _extract_batch_size(args, kwargs)

                # 根据批量大小调整严重性
                if batch_size > batch_size_threshold:
                    severity = "high"

                # 执行原函数
                result = await func(*args, **kwargs)

                return result

            except Exception as e:
                error = str(e)
                logger.error(f"批量操作审计装饰器捕获错误: {e}")
                raise

            finally:
                # 记录审计日志
                await _log_audit_action(
                    context=context,
                    action=operation_type,
                    resource_type="batch_operation",
                    severity=severity,
                    error=error,
                    duration=time.time() - start_time,
                    func_name=func.__name__,
                    func_module=func.__module__,
                    operation_type="batch",
                    batch_size=batch_size,
                )

        return wrapper

    return decorator


# 辅助函数

def _extract_audit_context(args: tuple, kwargs: dict) -> Optional[AuditContext]:
    """
    从参数中提取审计上下文 / Extract Audit Context from Arguments

    Args:
        args: 位置参数 / Positional arguments
        kwargs: 关键字参数 / Keyword arguments

    Returns:
        Optional[AuditContext]: 审计上下文 / Audit context
    """
    # 尝试从kwargs中获取context
    if "context" in kwargs:
        context = kwargs["context"]
        if isinstance(context, AuditContext):
            return context

    # 尝试从args中获取context
    for arg in args:
        if isinstance(arg, AuditContext):
            return arg

    # 尝试从kwargs中获取用户信息创建上下文
    user_id = kwargs.get("user_id")
    if user_id:
        return AuditContext(
            user_id=user_id,
            username=kwargs.get("username"),
            user_role=kwargs.get("user_role"),
            session_id=kwargs.get("session_id"),
            ip_address=kwargs.get("ip_address"),
        )

    return None


def _extract_api_context(args: tuple, kwargs: dict) -> Optional[AuditContext]:
    """
    从API参数中提取上下文 / Extract Context from API Arguments

    Args:
        args: 位置参数 / Positional arguments
        kwargs: 关键字参数 / Keyword arguments

    Returns:
        Optional[AuditContext]: 审计上下文 / Audit context
    """
    # 在FastAPI中，第一个参数通常是request
    if args:
        request = args[0]
        if hasattr(request, 'client') and hasattr(request, 'headers'):
            user_info = kwargs.get("current_user") or kwargs.get("user")
            return AuditContext.from_request(request, user_info)

    # 尝试从kwargs中获取request
    if "request" in kwargs:
        request = kwargs["request"]
        if hasattr(request, 'client') and hasattr(request, 'headers'):
            user_info = kwargs.get("current_user") or kwargs.get("user")
            return AuditContext.from_request(request, user_info)

    return _extract_audit_context(args, kwargs)


def _determine_action_from_method(func_name: str) -> str:
    """
    根据方法名确定动作 / Determine Action from Method Name

    Args:
        func_name: 函数名 / Function name

    Returns:
        str: 动作名称 / Action name
    """
    func_lower = func_name.lower()

    if "create" in func_lower or "add" in func_lower or "post" in func_lower:
        return "create"
    elif "update" in func_lower or "edit" in func_lower or "put" in func_lower or "patch" in func_lower:
        return "update"
    elif "delete" in func_lower or "remove" in func_lower:
        return "delete"
    elif "get" in func_lower or "list" in func_lower or "fetch" in func_lower:
        return "read"
    elif "login" in func_lower:
        return "login"
    elif "logout" in func_lower:
        return "logout"
    else:
        return "execute"


async def _log_audit_action(
    context: Optional[AuditContext],
    action: str,
    resource_type: Optional[str] = None,
    severity: str = "medium",
    args: Optional[tuple] = None,
    kwargs: Optional[dict] = None,
    result: Any = None,
    error: Optional[str] = None,
    duration: Optional[float] = None,
    func_name: Optional[str] = None,
    func_module: Optional[str] = None,
    **metadata
) -> None:
    """
    记录审计动作 / Log Audit Action

    Args:
        context: 审计上下文 / Audit context
        action: 动作 / Action
        resource_type: 资源类型 / Resource type
        severity: 严重性 / Severity
        args: 参数 / Arguments
        kwargs: 关键字参数 / Keyword arguments
        result: 结果 / Result
        error: 错误 / Error
        duration: 执行时间 / Duration
        func_name: 函数名 / Function name
        func_module: 函数模块 / Function module
        **metadata: 其他元数据 / Other metadata
    """
    try:
        # 这里应该调用实际的审计服务
        # 为了简化，我们只记录日志
        logger.info(f"审计动作: {action}, 资源: {resource_type}, 用户: {context.user_id if context else 'unknown'}")

        # 构建日志数据
        log_data = {
            "action": action,
            "resource_type": resource_type,
            "severity": severity,
            "function": f"{func_module}.{func_name}" if func_module and func_name else func_name,
            "duration": duration,
            "error": error,
            "metadata": metadata,
        }

        if context:
            log_data["user_id"] = context.user_id
            log_data["session_id"] = context.session_id
            log_data["ip_address"] = context.ip_address

        if args or kwargs:
            log_data["arguments"] = {
                "args": str(args) if args else None,
                "kwargs": str(kwargs) if kwargs else None,
            }

        # 记录详细日志
        logger.debug(f"审计日志详情: {log_data}")

    except Exception as e:
        logger.error(f"记录审计动作失败: {e}")


def _log_audit_action_sync(
    context: Optional[AuditContext],
    action: str,
    resource_type: Optional[str] = None,
    severity: str = "medium",
    args: Optional[tuple] = None,
    kwargs: Optional[dict] = None,
    result: Any = None,
    error: Optional[str] = None,
    duration: Optional[float] = None,
    func_name: Optional[str] = None,
    func_module: Optional[str] = None,
    **metadata
) -> None:
    """
    同步记录审计动作 / Sync Log Audit Action

    Args:
        context: 审计上下文 / Audit context
        action: 动作 / Action
        resource_type: 资源类型 / Resource type
        severity: 严重性 / Severity
        args: 参数 / Arguments
        kwargs: 关键字参数 / Keyword arguments
        result: 结果 / Result
        error: 错误 / Error
        duration: 执行时间 / Duration
        func_name: 函数名 / Function name
        func_module: 函数模块 / Function module
        **metadata: 其他元数据 / Other metadata
    """
    # 使用asyncio.run在同步环境中调用异步函数
    try:
        asyncio.run(_log_audit_action(
            context=context,
            action=action,
            resource_type=resource_type,
            severity=severity,
            args=args,
            kwargs=kwargs,
            result=result,
            error=error,
            duration=duration,
            func_name=func_name,
            func_module=func_module,
            **metadata
        ))
    except Exception as e:
        logger.error(f"同步记录审计动作失败: {e}")


async def _extract_old_values(table_name: str, args: tuple, kwargs: dict) -> Optional[Dict[str, Any]]:
    """
    提取旧值 / Extract Old Values

    Args:
        table_name: 表名 / Table name
        args: 参数 / Arguments
        kwargs: 关键字参数 / Keyword arguments

    Returns:
        Optional[Dict[str, Any]]: 旧值 / Old values
    """
    # 这里应该实现从数据库中提取旧值的逻辑
    # 为了简化，返回None
    return None


async def _extract_new_values(result: Any, table_name: str) -> Optional[Dict[str, Any]]:
    """
    提取新值 / Extract New Values

    Args:
        result: 结果 / Result
        table_name: 表名 / Table name

    Returns:
        Optional[Dict[str, Any]]: 新值 / New values
    """
    # 这里应该实现从结果中提取新值的逻辑
    # 为了简化，返回None
    return None


def _extract_batch_size(args: tuple, kwargs: dict) -> int:
    """
    提取批量大小 / Extract Batch Size

    Args:
        args: 参数 / Arguments
        kwargs: 关键字参数 / Keyword arguments

    Returns:
        int: 批量大小 / Batch size
    """
    # 尝试从不同的参数名中获取批量大小
    batch_size_names = ["batch_size", "size", "count", "limit", "num_items"]

    for name in batch_size_names:
        if name in kwargs:
            return int(kwargs[name]) if kwargs[name] else 0

    # 尝试从第一个参数（如果是列表）获取大小
    if args and isinstance(args[0], (list, tuple)):
        return len(args[0])

    return 0


async def _check_approval(context: Optional[AuditContext], approval_role: Optional[str]) -> None:
    """
    检查审批 / Check Approval

    Args:
        context: 审计上下文 / Audit context
        approval_role: 审批角色 / Approval role

    Raises:
        PermissionError: 如果没有审批权限 / If no approval permission
    """
    if not context:
        raise PermissionError("无法验证审批权限：缺少上下文信息")

    if approval_role and context.user_role != approval_role:
        raise PermissionError(f"需要 {approval_role} 角色才能执行此操作")
from typing import Callable
import asyncio
import functools
import time

from ..context import AuditContext

