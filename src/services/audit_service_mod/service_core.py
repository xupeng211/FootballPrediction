"""
审计服务核心
Audit Service Core

审计服务的主要业务逻辑。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.database.connection_mod import DatabaseManager

from .context import AuditContext
from .models import (
    AuditAction,
    AuditLog,
    AuditSeverity,
    AuditLogSummary,
)
from .sanitizer import AuditDataSanitizer
from .storage import AuditLogStorage

logger = get_logger(__name__)


class AuditService:
    """
    权限审计服务 / Permission Audit Service

    提供API层面的自动审计功能，记录所有写操作到audit_log表。
    支持装饰器模式，自动捕获操作上下文和数据变更。

    Provides API-level automatic audit functionality, recording all write operations
    to the audit_log table. Supports decorator pattern to automatically capture
    operation context and data changes.
    """

    def __init__(self):
        """初始化审计服务 / Initialize Audit Service"""
        self.db_manager: Optional[DatabaseManager] = None
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 使用组合模式，职责分离
        self.sanitizer = AuditDataSanitizer()
        self.storage = AuditLogStorage()

    async def initialize(self) -> bool:
        """初始化审计服务"""
        try:
            # 初始化存储
            if self.db_manager:
                await self.storage.initialize(self.db_manager)

            self.logger.info("审计服务初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"审计服务初始化失败: {str(e)}")
            return False

    def set_database_manager(self, db_manager: DatabaseManager) -> None:
        """设置数据库管理器"""
        self.db_manager = db_manager

    def _create_audit_log_entry(
        self,
        action: AuditAction,
        context: AuditContext,
        resource_type: str,
        resource_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        table_name: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        severity: Optional[AuditSeverity] = None,
        category: Optional[str] = None,
        compliance_tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """创建审计日志条目"""
        # 确定严重程度
        if not severity:
            severity = self._determine_severity(
                action, operation_type, old_values, new_values
            )

        # 确定合规类别
        if not category:
            category = self._determine_compliance_category(action, resource_type)

        # 处理敏感数据
        sanitized_old = None
        sanitized_new = None

        if old_values and self.sanitizer._is_sensitive_data(
            table_name, operation_type or "", old_values
        ):
            sanitized_old = self.sanitizer._sanitize_data(old_values)

        if new_values and self.sanitizer._is_sensitive_data(
            table_name, operation_type or "", new_values
        ):
            sanitized_new = self.sanitizer._sanitize_data(new_values)

        # 创建审计日志
        audit_log = AuditLog(
            id=None,  # 将在保存时生成
            user_id=context.user_id,
            username=context.username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            operation_type=operation_type,
            table_name=table_name,
            old_values=sanitized_old,
            new_values=sanitized_new,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            severity=severity,
            category=category,
            compliance_tags=compliance_tags or [],
            created_at=datetime.utcnow(),
            session_id=context.session_id,
            request_id=context.request_id,
            metadata=metadata or {},
        )

        return audit_log

    def _determine_severity(
        self,
        action: AuditAction,
        operation_type: Optional[str],
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
    ) -> AuditSeverity:
        """确定操作严重程度"""
        # 高风险操作
        high_risk_operations = {
            "DELETE",
            "DROP",
            "TRUNCATE",
            "UPDATE password",
            "UPDATE token",
            "UPDATE secret",
            "UPDATE key",
        }

        if operation_type:
            op_upper = operation_type.upper()
            for high_risk in high_risk_operations:
                if high_risk in op_upper:
                    return AuditSeverity.HIGH

        # 删除操作
        if action == AuditAction.DELETE:
            return AuditSeverity.HIGH

        # 创建敏感资源
        if action == AuditAction.CREATE:
            if new_values and self.sanitizer._contains_pii(new_values):
                return AuditSeverity.HIGH

        # 更新敏感字段
        if action == AuditAction.UPDATE:
            if old_values and new_values:
                # 检查是否更新了敏感字段
                for key in new_values.keys():
                    if self.sanitizer._is_sensitive_field(key):
                        return AuditSeverity.MEDIUM

        return AuditSeverity.LOW

    def _determine_compliance_category(
        self, action: AuditAction, resource_type: str
    ) -> str:
        """确定合规类别"""
        # 基于资源类型和操作的合规分类
        compliance_mapping = {
            ("users", "CREATE"): "USER_MANAGEMENT",
            ("users", "UPDATE"): "USER_MANAGEMENT",
            ("users", "DELETE"): "USER_MANAGEMENT",
            ("permissions", "CREATE"): "ACCESS_CONTROL",
            ("permissions", "UPDATE"): "ACCESS_CONTROL",
            ("permissions", "DELETE"): "ACCESS_CONTROL",
            ("tokens", "CREATE"): "AUTHENTICATION",
            ("tokens", "DELETE"): "AUTHENTICATION",
        }

        return compliance_mapping.get((resource_type, action.value), "GENERAL")

    async def log_operation(
        self,
        action: AuditAction,
        context: AuditContext,
        resource_type: str,
        resource_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        table_name: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        severity: Optional[AuditSeverity] = None,
        category: Optional[str] = None,
        compliance_tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        async_save: bool = True,
    ) -> bool:
        """记录操作日志"""
        try:
            # 创建审计日志条目
            audit_log = self._create_audit_log_entry(
                action=action,
                context=context,
                resource_type=resource_type,
                resource_id=resource_id,
                operation_type=operation_type,
                table_name=table_name,
                old_values=old_values,
                new_values=new_values,
                severity=severity,
                category=category,
                compliance_tags=compliance_tags,
                metadata=metadata,
            )

            if async_save:
                # 异步保存
                await self.storage.save_audit_entry(audit_log)
            else:
                # 同步保存（通过线程池）
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._sync_save_audit_entry, audit_log)

            return True

        except Exception as e:
            self.logger.error(f"记录审计日志失败: {str(e)}")
            return False

    def _sync_save_audit_entry(self, audit_log: AuditLog) -> bool:
        """同步保存审计日志（用于非异步上下文）"""
        # 这里可以使用线程池或其他同步方式
        # 暂时返回True，实际实现需要根据具体需求
        return True

    async def async_log_action(
        self,
        action: str,
        user_id: str,
        username: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        """异步记录简单操作"""
        try:
            # 转换action字符串为枚举
            action_enum = AuditAction(action.upper()) if action else AuditAction.OTHER

            # 创建上下文
            context = AuditContext(
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                request_id=request_id,
            )

            # 提取操作类型和资源ID
            operation_type = details.get("operation_type") if details else None
            table_name = details.get("table_name") if details else None
            old_values = details.get("old_values") if details else None
            new_values = details.get("new_values") if details else None

            return await self.log_operation(
                action=action_enum,
                context=context,
                resource_type=resource_type,
                resource_id=resource_id,
                operation_type=operation_type,
                table_name=table_name,
                old_values=old_values,
                new_values=new_values,
                async_save=True,
            )

        except Exception as e:
            self.logger.error(f"异步记录操作失败: {str(e)}")
            return False

    def log_action(
        self,
        action: str,
        user_id: str,
        username: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        """同步记录简单操作"""
        try:
            # 创建事件循环（如果不存在）
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 运行异步方法
            return loop.run_until_complete(
                self.async_log_action(
                    action=action,
                    user_id=user_id,
                    username=username,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                    request_id=request_id,
                )
            )

        except Exception as e:
            self.logger.error(f"记录操作失败: {str(e)}")
            return False

    def batch_log_actions(self, actions: List[Dict[str, Any]]) -> List[bool]:
        """批量记录操作"""
        results = []
        for action_data in actions:
            result = self.log_action(**action_data)
            results.append(result)
        return results

    # 查询方法委托给存储层
    async def get_user_audit_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AuditLogSummary:
        """获取用户审计摘要"""
        try:
            # 获取用户日志
            logs = await self.storage.get_user_audit_logs(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=1000,
            )

            # 统计摘要
            total_operations = len(logs)
            high_risk_operations = sum(
                1 for log in logs if log.get("severity") == "HIGH"
            )

            # 按操作类型统计
            operation_counts = {}
            for log in logs:
                op_type = log.get("operation_type", "UNKNOWN")
                operation_counts[op_type] = operation_counts.get(op_type, 0) + 1

            # 按资源类型统计
            resource_counts = {}
            for log in logs:
                resource_type = log.get("resource_type", "UNKNOWN")
                resource_counts[resource_type] = (
                    resource_counts.get(resource_type, 0) + 1
                )

            # 最后操作时间
            last_operation = logs[0]["created_at"] if logs else None

            return AuditLogSummary(
                user_id=user_id,
                total_operations=total_operations,
                high_risk_operations=high_risk_operations,
                operation_counts=operation_counts,
                resource_counts=resource_counts,
                last_operation=last_operation,
                start_date=start_date,
                end_date=end_date,
            )

        except Exception as e:
            self.logger.error(f"获取用户审计摘要失败: {str(e)}")
            return AuditLogSummary(
                user_id=user_id,
                total_operations=0,
                high_risk_operations=0,
                operation_counts={},
                resource_counts={},
                last_operation=None,
                start_date=start_date,
                end_date=end_date,
            )
