"""
权限审计服务

提供API层面的自动审计功能，记录所有写操作到audit_log表。
支持装饰器模式，自动捕获操作上下文和数据变更。

基于 DATA_DESIGN.md 中的权限控制设计。
"""

import asyncio
import hashlib
import inspect
import logging
import time
from contextvars import ContextVar
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

from fastapi import Request

from src.database.connection import DatabaseManager
from src.database.models.audit_log import AuditAction, AuditLog, AuditSeverity

# 类型定义
F = TypeVar("F", bound=Callable[..., Any])

# 上下文变量，用于在请求处理过程中传递审计信息
audit_context: ContextVar[Dict[str, Any]] = ContextVar("audit_context", default={})

logger = logging.getLogger(__name__)


class AuditContext:
    """审计上下文管理器"""

    def __init__(
        self,
        user_id: str,
        username: Optional[str] = None,
        user_role: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        初始化审计上下文

        Args:
            user_id: 用户ID
            username: 用户名
            user_role: 用户角色
            session_id: 会话ID
            ip_address: IP地址
            user_agent: 用户代理
        """
        self.user_id = user_id
        self.username = username
        self.user_role = user_role
        self.session_id = session_id
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "user_role": self.user_role,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


class AuditService:
    """权限审计服务"""

    def __init__(self):
        """初始化审计服务"""
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"audit.{self.__class__.__name__}")

        # 敏感数据配置
        self.sensitive_tables = {
            "users",
            "permissions",
            "tokens",
            "passwords",
            "api_keys",
            "user_profiles",
            "payment_info",
            "personal_data",
        }

        self.sensitive_columns = {
            "password",
            "token",
            "secret",
            "key",
            "email",
            "phone",
            "ssn",
            "credit_card",
            "bank_account",
            "api_key",
        }

        # 高风险操作配置
        self.high_risk_actions = {
            AuditAction.DELETE,
            AuditAction.GRANT,
            AuditAction.REVOKE,
            AuditAction.BACKUP,
            AuditAction.RESTORE,
            AuditAction.SCHEMA_CHANGE,
        }

    def _hash_sensitive_value(self, value: str) -> str:
        """对敏感数据进行哈希处理"""
        if not value:
            return ""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _is_sensitive_data(
        self, table_name: Optional[str], column_name: Optional[str]
    ) -> bool:
        """判断是否为敏感数据"""
        if table_name and table_name.lower() in self.sensitive_tables:
            return True

        if column_name:
            return any(
                sensitive in column_name.lower() for sensitive in self.sensitive_columns
            )

        return False

    def _determine_severity(self, action: str, table_name: Optional[str]) -> str:
        """确定操作严重级别"""
        if action in [AuditAction.DELETE, AuditAction.GRANT, AuditAction.REVOKE]:
            return AuditSeverity.HIGH
        elif action in [
            AuditAction.BACKUP,
            AuditAction.RESTORE,
            AuditAction.SCHEMA_CHANGE,
        ]:
            return AuditSeverity.CRITICAL
        elif action == AuditAction.READ:
            return AuditSeverity.LOW
        elif table_name and table_name.lower() in self.sensitive_tables:
            return AuditSeverity.HIGH
        else:
            return AuditSeverity.MEDIUM

    def _determine_compliance_category(
        self, action: str, table_name: Optional[str], is_sensitive: bool
    ) -> str:
        """确定合规分类"""
        if is_sensitive:
            return "PII"  # Personally Identifiable Information
        elif action in [AuditAction.GRANT, AuditAction.REVOKE]:
            return "ACCESS_CONTROL"
        elif action in [AuditAction.BACKUP, AuditAction.RESTORE]:
            return "DATA_PROTECTION"
        elif table_name and "financial" in table_name.lower():
            return "FINANCIAL"
        else:
            return "GENERAL"

    async def log_operation(
        self,
        action: str,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        record_id: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[int]:
        """
        记录操作到审计日志

        Args:
            action: 操作类型
            table_name: 目标表名
            column_name: 目标列名
            record_id: 记录ID
            old_value: 操作前值
            new_value: 操作后值
            request_path: 请求路径
            request_method: HTTP方法
            success: 操作是否成功
            error_message: 错误信息
            duration_ms: 操作耗时
            extra_data: 扩展元数据
            **kwargs: 其他参数

        Returns:
            Optional[int]: 审计日志ID，失败时返回None
        """
        try:
            # 获取审计上下文
            context = audit_context.get({})

            # 判断是否为敏感数据
            is_sensitive = self._is_sensitive_data(table_name, column_name)

            # 确定严重级别
            severity = self._determine_severity(action, table_name)

            # 确定合规分类
            compliance_category = self._determine_compliance_category(
                action, table_name, is_sensitive
            )

            # 处理敏感数据（对敏感值进行哈希）
            old_value_hash = None
            new_value_hash = None
            if is_sensitive:
                if old_value:
                    old_value_hash = self._hash_sensitive_value(old_value)
                    old_value = "[SENSITIVE]"  # 掩码处理
                if new_value:
                    new_value_hash = self._hash_sensitive_value(new_value)
                    new_value = "[SENSITIVE]"  # 掩码处理

            # 创建审计日志条目
            audit_entry = AuditLog(
                # 用户信息（从上下文获取）
                user_id=context.get("user_id", "system"),
                username=context.get("username"),
                user_role=context.get("user_role"),
                session_id=context.get("session_id"),
                # 操作信息
                action=action,
                severity=severity,
                table_name=table_name,
                column_name=column_name,
                record_id=str(record_id) if record_id else None,
                # 数据变更信息
                old_value=old_value,
                new_value=new_value,
                old_value_hash=old_value_hash,
                new_value_hash=new_value_hash,
                # 上下文信息
                ip_address=context.get("ip_address"),
                user_agent=context.get("user_agent"),
                request_path=request_path,
                request_method=request_method,
                # 操作结果
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
                # 扩展信息
                extra_data=extra_data,
                # 合规相关
                compliance_category=compliance_category,
                is_sensitive=is_sensitive,
                # 其他参数
                **kwargs,
            )

            # 保存到数据库
            async with self.db_manager.get_async_session() as session:
                session.add(audit_entry)
                await session.commit()
                await session.refresh(audit_entry)

                self.logger.info(
                    f"审计日志已记录: {action} on {table_name} by {context.get('user_id', 'system')}"
                )

                return int(audit_entry.id) if audit_entry.id is not None else None

        except Exception as e:
            self.logger.error(f"记录审计日志失败: {e}")
            return None

    def set_audit_context(self, context: AuditContext) -> None:
        """设置审计上下文"""
        audit_context.set(context.to_dict())

    def get_audit_context(self) -> Dict[str, Any]:
        """获取审计上下文"""
        return audit_context.get({})

    async def get_user_audit_summary(
        self, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """获取用户审计摘要"""
        from src.database.models.audit_log import AuditLogSummary

        async with self.db_manager.get_async_session() as session:
            summary = AuditLogSummary(session)
            return summary.get_user_activity_summary(user_id, days)

    async def get_high_risk_operations(
        self, hours: int = 24, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取高风险操作列表"""

        from sqlalchemy import and_, desc

        cutoff_time = datetime.now() - timedelta(hours=hours)

        async with self.db_manager.get_async_session() as session:
            high_risk_logs = await session.execute(
                session.query(AuditLog)
                .filter(
                    and_(
                        AuditLog.timestamp >= cutoff_time,
                        AuditLog.severity.in_(
                            [AuditSeverity.HIGH, AuditSeverity.CRITICAL]
                        ),
                    )
                )
                .order_by(desc(AuditLog.timestamp))
                .limit(limit)
            )

            return [log.to_dict() for log in high_risk_logs.scalars()]

    def log_action(self, action: str, user_id: str, metadata: dict = None) -> dict:
        """记录操作日志 - 同步版本用于测试"""
        log_entry = {
            "action": action,
            "user_id": user_id,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "success": True,
        }

        # Store in memory for testing
        if not hasattr(self, "_logs"):
            self._logs = []
        self._logs.append(log_entry)

        return log_entry

    def get_user_audit_logs(self, user_id: str) -> list:
        """获取用户审计日志"""
        if not hasattr(self, "_logs"):
            return []
        return [log for log in self._logs if log.get("user_id") == user_id]

    def get_audit_summary(self) -> dict:
        """获取审计摘要"""
        if not hasattr(self, "_logs"):
            return {"total_logs": 0, "users": []}

        users = set(log.get("user_id") for log in self._logs if log.get("user_id"))
        return {
            "total_logs": len(self._logs),
            "users": list(users),
            "actions": list(set(log.get("action") for log in self._logs)),
        }

    async def async_log_action(
        self, action: str, user_id: str, metadata: dict = None
    ) -> dict:
        """异步记录操作日志"""
        return self.log_action(action, user_id, metadata)

    def batch_log_actions(self, actions: list) -> list:
        """批量记录操作日志"""
        results = []
        for action_data in actions:
            result = self.log_action(
                action_data.get("action", ""),
                action_data.get("user_id", ""),
                action_data.get("metadata", {}),
            )
            results.append(result)
        return results


# 全局审计服务实例
audit_service = AuditService()


def extract_request_context(request: Request) -> AuditContext:
    """从请求中提取审计上下文"""
    # 从请求头或认证信息中提取用户信息
    # 这里需要根据实际的认证机制进行调整

    user_id = getattr(request.state, "user_id", "anonymous")
    username = getattr(request.state, "username", None)
    user_role = getattr(request.state, "user_role", None)
    session_id = request.headers.get("X-Session-ID")

    # 获取客户端IP地址
    ip_address = request.client.host if request.client else None
    if not ip_address:
        # 尝试从X-Forwarded-For获取真实IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()

    user_agent = request.headers.get("User-Agent")

    return AuditContext(
        user_id=user_id,
        username=username,
        user_role=user_role,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def audit_operation(
    action: str,
    table_name: Optional[str] = None,
    extract_changes: bool = True,
    ignore_read: bool = True,
) -> Callable[..., Any]:
    """
    API操作审计装饰器

    Args:
        action: 操作类型
        table_name: 目标表名
        extract_changes: 是否尝试提取数据变更
        ignore_read: 是否忽略读操作（避免日志过多）

    Usage:
        @audit_operation(AuditAction.CREATE, "users")
        async def create_user(user_data: dict):
            # 创建用户逻辑
            pass

        @audit_operation(AuditAction.UPDATE, "users", extract_changes=True)
        async def update_user(user_id: int, user_data: dict):
            # 更新用户逻辑
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            request_path = None
            request_method = None

            # 尝试从参数中提取Request对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # 如果没有找到Request对象，检查kwargs
            if not request:
                request = kwargs.get("request")

            # 设置审计上下文
            if request:
                context = extract_request_context(request)
                audit_service.set_audit_context(context)
                request_path = str(request.url.path)
                request_method = request.method

            # 如果是忽略的读操作，直接执行
            if ignore_read and action == AuditAction.READ:
                return await func(*args, **kwargs)

            try:
                # 执行原函数
                result = await func(*args, **kwargs)

                # 计算执行时间
                duration_ms = int((time.time() - start_time) * 1000)

                # 尝试提取记录ID和变更信息
                record_id = None
                old_value = None
                new_value = None
                extra_data = {}

                if extract_changes and result:
                    # 尝试从结果中提取ID
                    if hasattr(result, "id"):
                        record_id = result.id
                    elif isinstance(result, dict) and "id" in result:
                        record_id = result["id"]

                    # 记录操作的元数据
                    extra_data = {
                        "function_name": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                        "result_type": type(result).__name__,
                    }

                # 记录成功的操作
                await audit_service.log_operation(
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    old_value=old_value,
                    new_value=new_value,
                    request_path=request_path,
                    request_method=request_method,
                    success=True,
                    duration_ms=duration_ms,
                    extra_data=extra_data,
                )

                return result

            except Exception as e:
                # 计算执行时间
                duration_ms = int((time.time() - start_time) * 1000)

                # 记录失败的操作
                await audit_service.log_operation(
                    action=action,
                    table_name=table_name,
                    request_path=request_path,
                    request_method=request_method,
                    success=False,
                    error_message=str(e),
                    duration_ms=duration_ms,
                    extra_data={
                        "function_name": func.__name__,
                        "exception_type": type(e).__name__,
                    },
                )

                # 重新抛出异常
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步版本的包装器（如果需要）
            return asyncio.run(async_wrapper(*args, **kwargs))

        # 根据原函数是否为异步决定返回哪个包装器
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def audit_database_operation(
    action: str, table_name: str, extract_record_id: bool = True
):
    """
    数据库操作审计装饰器（适用于数据库服务方法）

    Args:
        action: 操作类型
        table_name: 目标表名
        extract_record_id: 是否提取记录ID
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # 执行原函数
                result = await func(*args, **kwargs)

                # 计算执行时间
                duration_ms = int((time.time() - start_time) * 1000)

                # 提取记录ID
                record_id = None
                if extract_record_id and result:
                    if hasattr(result, "id"):
                        record_id = result.id
                    elif isinstance(result, dict) and "id" in result:
                        record_id = result["id"]

                # 记录成功的操作
                await audit_service.log_operation(
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    success=True,
                    duration_ms=duration_ms,
                    extra_data={
                        "function_name": func.__name__,
                        "database_operation": True,
                    },
                )

                return result

            except Exception as e:
                # 计算执行时间
                duration_ms = int((time.time() - start_time) * 1000)

                # 记录失败的操作
                await audit_service.log_operation(
                    action=action,
                    table_name=table_name,
                    success=False,
                    error_message=str(e),
                    duration_ms=duration_ms,
                    extra_data={
                        "function_name": func.__name__,
                        "database_operation": True,
                        "exception_type": type(e).__name__,
                    },
                )

                # 重新抛出异常
                raise

        # 根据原函数是否为异步决定返回哪个包装器
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            # 同步版本
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(async_wrapper(*args, **kwargs))

            return sync_wrapper  # type: ignore

    return decorator


# 便捷的装饰器别名
def audit_create(table_name):
    """创建操作审计装饰器"""
    return audit_operation(AuditAction.CREATE, table_name)


def audit_read(table_name):
    """读取操作审计装饰器"""
    return audit_operation(AuditAction.READ, table_name, ignore_read=False)


def audit_update(table_name):
    """更新操作审计装饰器"""
    return audit_operation(AuditAction.UPDATE, table_name, extract_changes=True)


def audit_delete(table_name):
    """删除操作审计装饰器"""
    return audit_operation(AuditAction.DELETE, table_name)


# 导出主要组件
__all__ = [
    "AuditService",
    "AuditContext",
    "audit_service",
    "audit_operation",
    "audit_database_operation",
    "audit_create",
    "audit_read",
    "audit_update",
    "audit_delete",
    "extract_request_context",
]
