"""
审计服务
Audit Service

提供核心的审计功能实现。
"""

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.database.connection import DatabaseManager

from .context import AuditContext
from .models import (
    AuditAction,
    AuditLog,
    AuditSeverity,
    AuditLogSummary,
)

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
            "credential",
            "ssn",
            "credit_card",
            "bank_account",
        }

        # 合规类别映射
        self.compliance_mapping = {
            "users": "user_management",
            "permissions": "access_control",
            "tokens": "authentication",
            "payment": "financial",
            "personal_data": "privacy",
        }

    async def initialize(self) -> bool:
        """
        初始化服务 / Initialize Service

        Returns:
            初始化是否成功 / Whether initialization was successful
        """
        try:
            if not self.db_manager:
                self.db_manager = DatabaseManager()
                self.db_manager.initialize()

            self.logger.info("审计服务初始化完成")
            return True

        except Exception as e:
            self.logger.error(f"初始化审计服务失败: {e}")
            return False

    def _hash_sensitive_value(self, value: str) -> str:
        """
        哈希敏感值 / Hash Sensitive Value

        Args:
            value: 敏感值 / Sensitive value

        Returns:
            哈希值 / Hashed value
        """
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def _hash_sensitive_data(self, data: str) -> str:
        """
        哈希敏感数据 / Hash Sensitive Data

        Args:
            data: 敏感数据 / Sensitive data

        Returns:
            哈希后的数据 / Hashed data
        """
        try:
            # 尝试解析为JSON
            import json
            parsed_data = json.loads(data)
            # 递归处理嵌套结构
            return self._sanitize_data(parsed_data)
        except:
            # 如果不是JSON，直接哈希
            return self._hash_sensitive_value(data)

    def _sanitize_data(self, data: Any) -> Any:
        """
        清理敏感数据 / Sanitize Sensitive Data

        Args:
            data: 数据 / Data

        Returns:
            清理后的数据 / Sanitized data
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if key in self.sensitive_columns:
                    sanitized[key] = self._hash_sensitive_value(str(value))
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data

    def _create_audit_log_entry(
        self,
        context: AuditContext,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: str = "",
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None,
        severity: str = "medium",
        table_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        创建审计日志条目 / Create Audit Log Entry

        Args:
            context: 审计上下文 / Audit context
            action: 动作 / Action
            resource_type: 资源类型 / Resource type
            resource_id: 资源ID / Resource ID
            description: 描述 / Description
            old_values: 旧值 / Old values
            new_values: 新值 / New values
            error: 错误信息 / Error message
            duration: 执行时间 / Execution duration
            severity: 严重性 / Severity
            table_name: 表名 / Table name
            metadata: 元数据 / Metadata

        Returns:
            AuditLog: 审计日志对象 / Audit log object
        """
        # 转换枚举
        if isinstance(action, str):
            try:
                action = AuditAction(action)
            except ValueError:
                action = AuditAction.EXECUTE

        if isinstance(severity, str):
            try:
                severity = AuditSeverity(severity)
            except ValueError:
                severity = AuditSeverity.MEDIUM

        # 创建审计日志
        audit_log = AuditLog(
            timestamp=datetime.now(),
            user_id=context.user_id,
            username=context.username,
            user_role=context.user_role,
            session_id=context.session_id,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            request_id=context.request_id,
            correlation_id=context.correlation_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            severity=severity,
            table_name=table_name,
            metadata=metadata,
        )

        # 处理错误信息
        if error:
            audit_log.metadata = audit_log.metadata or {}
            audit_log.metadata["error"] = error

        # 处理执行时间
        if duration:
            audit_log.metadata = audit_log.metadata or {}
            audit_log.metadata["duration_ms"] = duration * 1000

        return audit_log

    def _is_sensitive_table(self, table_name: Any) -> bool:
        """
        检查是否为敏感表 / Check if Sensitive Table

        Args:
            table_name: 表名 / Table name

        Returns:
            是否敏感 / Whether sensitive
        """
        return table_name in self.sensitive_tables

    def _contains_pii(self, data: Dict[str, Any]) -> bool:
        """
        检查是否包含个人身份信息 / Check if Contains PII

        Args:
            data: 数据字典 / Data dictionary

        Returns:
            是否包含PII / Whether contains PII
        """
        pii_indicators = [
            "ssn", "social_security", "credit_card", "bank_account",
            "email", "phone", "address", "id_number",
            "passport", "license", "personal"
        ]

        for key in data.keys():
            key_lower = key.lower()
            if any(indicator in key_lower for indicator in pii_indicators):
                return True

        return False

    def _is_sensitive_data(
        self,
        data: Any,
        table_name: Optional[str] = None,
        action: Optional[str] = None,
    ) -> bool:
        """
        检查是否为敏感数据 / Check if Sensitive Data

        Args:
            data: 数据 / Data
            table_name: 表名 / Table name
            action: 动作 / Action

        Returns:
            是否敏感 / Whether sensitive
        """
        # 检查表名
        if table_name and self._is_sensitive_table(table_name):
            return True

        # 检查动作
        sensitive_actions = ["delete", "update_password", "reset_password", "change_role"]
        if action and action in sensitive_actions:
            return True

        # 检查数据内容
        if isinstance(data, dict) and self._contains_pii(data):
            return True

        return False

    def _determine_severity(
        self,
        action: str,
        table_name: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        确定严重性级别 / Determine Severity Level

        Args:
            action: 动作 / Action
            table_name: 表名 / Table name
            error: 错误信息 / Error message

        Returns:
            严重性级别 / Severity level
        """
        if error:
            return "critical"

        # 基于动作确定
        high_severity_actions = ["delete", "export", "import", "admin"]
        if action in high_severity_actions:
            return "high"

        # 基于表名确定
        if table_name:
            high_severity_tables = ["users", "permissions", "tokens"]
            if table_name in high_severity_tables:
                return "high"

        return "medium"

    def _determine_compliance_category(
        self,
        table_name: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Optional[str]:
        """
        确定合规类别 / Determine Compliance Category

        Args:
            table_name: 表名 / Table name
            action: 动作 / Action

        Returns:
            合规类别 / Compliance category
        """
        if table_name and table_name in self.compliance_mapping:
            return self.compliance_mapping[table_name]

        if action and action in ["login", "logout", "access"]:
            return "authentication"

        return None

    async def log_operation(
        self,
        context: AuditContext,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: str = "",
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None,
        severity: Optional[str] = None,
        table_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        记录操作日志 / Log Operation

        Args:
            context: 审计上下文 / Audit context
            action: 动作 / Action
            resource_type: 资源类型 / Resource type
            resource_id: 资源ID / Resource ID
            description: 描述 / Description
            old_values: 旧值 / Old values
            new_values: 新值 / New values
            error: 错误信息 / Error message
            duration: 执行时间 / Execution duration
            severity: 严重性 / Severity
            table_name: 表名 / Table name
            metadata: 元数据 / Metadata

        Returns:
            是否成功 / Whether successful
        """
        try:
            # 确定严重性
            if not severity:
                severity = self._determine_severity(action, table_name, error)

            # 确定合规类别
            compliance_category = self._determine_compliance_category(table_name, action)

            # 检查敏感数据
            is_sensitive = self._is_sensitive_data(
                new_values or old_values, table_name, action
            )

            # 创建审计日志条目
            audit_log = self._create_audit_log_entry(
                context=context,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                old_values=old_values,
                new_values=new_values,
                error=error,
                duration=duration,
                severity=severity,
                table_name=table_name,
                metadata=metadata,
            )

            # 如果是敏感数据，需要哈希处理
            if is_sensitive:
                if audit_log.old_values:
                    audit_log.old_values = self._hash_sensitive_data(
                        str(audit_log.old_values)
                    )
                if audit_log.new_values:
                    audit_log.new_values = self._hash_sensitive_data(
                        str(audit_log.new_values)
                    )

            # 添加合规类别
            if compliance_category:
                audit_log.compliance_category = compliance_category

            # 保存审计日志
            success = await self._save_audit_entry(audit_log)

            if success:
                self.logger.debug(
                    f"审计日志已记录: {action} - {context.user_id}"
                )

            return success

        except Exception as e:
            self.logger.error(f"记录审计日志失败: {e}")
            return False

    async def _save_audit_entry(self, audit_log: AuditLog) -> bool:
        """
        保存审计条目 / Save Audit Entry

        Args:
            audit_log: 审计日志 / Audit log

        Returns:
            是否成功 / Whether successful
        """
        try:
            if not self.db_manager:
                self.logger.error("数据库管理器未初始化")
                return False

            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import insert
                from src.database.models.audit_log import AuditLog as AuditLogModel

                # 创建审计日志记录
                audit_record = AuditLogModel(
                    timestamp=audit_log.timestamp,
                    user_id=audit_log.user_id,
                    username=audit_log.username,
                    user_role=audit_log.user_role,
                    session_id=audit_log.session_id,
                    action=audit_log.action.value,
                    resource_type=audit_log.resource_type,
                    resource_id=audit_log.resource_id,
                    description=audit_log.description,
                    ip_address=audit_log.ip_address,
                    user_agent=audit_log.user_agent,
                    old_values=audit_log.old_values,
                    new_values=audit_log.new_values,
                    severity=audit_log.severity.value,
                    table_name=audit_log.table_name,
                    compliance_category=audit_log.compliance_category,
                    request_id=audit_log.request_id,
                    correlation_id=audit_log.correlation_id,
                    metadata=audit_log.metadata,
                )

                session.add(audit_record)
                await session.commit()

                # 更新ID
                audit_log.id = audit_record.id

            return True

        except Exception as e:
            self.logger.error(f"保存审计条目失败: {e}")
            return False

    async def async_log_action(
        self,
        context: AuditContext,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: str = "",
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None,
        severity: Optional[str] = None,
        table_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        异步记录操作日志 / Async Log Operation

        与 log_operation 功能相同，但名称更明确地表明是异步的。
        Same functionality as log_operation, but with clearer async naming.

        Returns:
            是否成功 / Whether successful
        """
        return await self.log_operation(
            context=context,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            error=error,
            duration=duration,
            severity=severity,
            table_name=table_name,
            metadata=metadata,
        )

    def log_action(
        self,
        context: AuditContext,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: str = "",
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None,
        severity: Optional[str] = None,
        table_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录操作日志（同步版本） / Log Operation (Sync Version)

        用于同步环境下的审计日志记录。
        Used for audit logging in synchronous environments.

        Args:
            context: 审计上下文 / Audit context
            action: 动作 / Action
            resource_type: 资源类型 / Resource type
            resource_id: 资源ID / Resource ID
            description: 描述 / Description
            old_values: 旧值 / Old values
            new_values: 新值 / New values
            error: 错误信息 / Error message
            duration: 执行时间 / Execution duration
            severity: 严重性 / Severity
            table_name: 表名 / Table name
            metadata: 元数据 / Metadata
        """
        # 在新线程中执行异步操作
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            self.async_log_action(
                context=context,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                description=description,
                old_values=old_values,
                new_values=new_values,
                error=error,
                duration=duration,
                severity=severity,
                table_name=table_name,
                metadata=metadata,
            )
        )

    def batch_log_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量记录操作日志 / Batch Log Operations

        Args:
            actions: 操作列表 / List of operations

        Returns:
            处理结果列表 / List of processing results
        """
        results = []

        for action_data in actions:
            try:
                context = action_data.get("context")
                result = self.log_action(**action_data)
                results.append({
                    "action": action_data.get("action"),
                    "success": result is not None,
                    "error": None if result is not None else "Failed to log",
                })
            except Exception as e:
                results.append({
                    "action": action_data.get("action"),
                    "success": False,
                    "error": str(e),
                })

        return results

    async def get_user_audit_summary(
        self, user_id: str, days: int = 30
    ) -> Optional[AuditLogSummary]:
        """
        获取用户审计摘要 / Get User Audit Summary

        Args:
            user_id: 用户ID / User ID
            days: 天数 / Number of days

        Returns:
            审计摘要 / Audit summary
        """
        try:
            if not self.db_manager:
                return None

            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select, func, desc
                from src.database.models.audit_log import AuditLog as AuditLogModel

                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                # 获取用户审计日志
                query = select(AuditLogModel).where(
                    AuditLogModel.user_id == user_id,
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.timestamp <= end_date,
                )

                result = await session.execute(query)
                logs = result.scalars().all()

                # 创建摘要
                summary = AuditLogSummary()
                summary.total_logs = len(logs)
                summary.date_range = {
                    "start": start_date,
                    "end": end_date,
                }

                # 统计动作
                action_counts = {}
                severity_counts = {}

                for log in logs:
                    action = log.action.value if log.action else "unknown"
                    severity = log.severity.value if log.severity else "unknown"

                    action_counts[action] = action_counts.get(action, 0) + 1
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                summary.action_counts = action_counts
                summary.severity_counts = severity_counts

                # 获取前5个最频繁的操作
                top_actions = sorted(
                    action_counts.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]

                summary.top_actions = [
                    {"action": action, "count": count}
                    for action, count in top_actions
                ]

                # 获取高风险操作
                high_risk = [
                    log for log in logs
                    if log.severity and log.severity.value in ["high", "critical"]
                ]

                summary.high_risk_operations = [
                    {
                        "action": log.action.value,
                        "timestamp": log.timestamp.isoformat(),
                        "description": log.description,
                    }
                    for log in high_risk
                ]

                return summary

        except Exception as e:
            self.logger.error(f"获取用户审计摘要失败: {e}")
            return None

    async def get_high_risk_operations(
        self, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        获取高风险操作 / Get High Risk Operations

        Args:
            hours: 小时数 / Number of hours

        Returns:
            高风险操作列表 / List of high risk operations
        """
        try:
            if not self.db_manager:
                return []

            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select
                from src.database.models.audit_log import AuditLog as AuditLogModel

                # 计算时间范围
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)

                # 获取高风险操作
                query = select(AuditLogModel).where(
                    AuditLogModel.severity.in_(["high", "critical"]),
                    AuditLogModel.timestamp >= start_time,
                    AuditLogModel.timestamp <= end_time,
                ).order_by(AuditLogModel.timestamp.desc())

                result = await session.execute(query)
                logs = result.scalars().all()

                # 格式化结果
                operations = []
                for log in logs:
                    operations.append({
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "user_id": log.user_id,
                        "username": log.username,
                        "action": log.action.value,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "description": log.description,
                        "severity": log.severity.value,
                        "ip_address": log.ip_address,
                    })

                return operations

        except Exception as e:
            self.logger.error(f"获取高风险操作失败: {e}")
            return []

    def get_user_audit_logs(
        self, user_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取用户审计日志（同步版本） / Get User Audit Logs (Sync Version)

        Args:
            user_id: 用户ID / User ID
            limit: 限制数量 / Limit

        Returns:
            审计日志列表 / List of audit logs
        """
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(
            self.async_get_user_audit_logs(user_id, limit)
        )

    async def async_get_user_audit_logs(
        self, user_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取用户审计日志 / Get User Audit Logs

        Args:
            user_id: 用户ID / User ID
            limit: 限制数量 / Limit

        Returns:
            审计日志列表 / List of audit logs
        """
        try:
            if not self.db_manager:
                return []

            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select
                from src.database.models.audit_log import AuditLog as AuditLogModel

                query = select(AuditLogModel).where(
                    AuditLogModel.user_id == user_id
                ).order_by(AuditLogModel.timestamp.desc()).limit(limit)

                result = await session.execute(query)
                logs = result.scalars().all()

                return [
                    {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "action": log.action.value,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "description": log.description,
                        "severity": log.severity.value,
                    }
                    for log in logs
                ]

        except Exception as e:
            self.logger.error(f"获取用户审计日志失败: {e}")
            return []

    def get_audit_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        获取审计摘要（同步版本） / Get Audit Summary (Sync Version)

        Args:
            days: 天数 / Number of days

        Returns:
            审计摘要 / Audit summary
        """
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(
            self.async_get_audit_summary(days)
        )

    async def async_get_audit_summary(
        self, days: int = 30
    ) -> Dict[str, Any]:
        """
        获取审计摘要 / Get Audit Summary

        Args:
            days: 天数 / Number of days

        Returns:
            审计摘要 / Audit summary
        """
        try:
            if not self.db_manager:
                return {"error": "数据库管理器未初始化"}

            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select, func
                from src.database.models.audit_log import AuditLog as AuditLogModel

                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                # 获取统计数据
                query = select(
                    func.count(AuditLogModel.id).label("total_logs"),
                    func.count(
                        func.distinct(AuditLogModel.user_id)
                    ).label("unique_users"),
                    func.count(
                        func.distinct(AuditLogModel.action)
                    ).label("unique_actions"),
                ).where(
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.timestamp <= end_date,
                )

                result = await session.execute(query)
                stats = result.first()

                if not stats:
                    return {
                        "period_days": days,
                        "total_logs": 0,
                        "unique_users": 0,
                        "unique_actions": 0,
                        "action_counts": {},
                        "severity_counts": {},
                    }

                # 获取动作和严重性分布
                action_query = select(
                    AuditLogModel.action,
                    func.count(AuditLogModel.id).label("count")
                ).where(
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.timestamp <= end_date,
                ).group_by(AuditLogModel.action)

                action_result = await session.execute(action_query)
                action_counts = {
                    row.action.value: row.count for row in action_result
                }

                severity_query = select(
                    AuditLogModel.severity,
                    func.count(AuditLogModel.id).label("count")
                ).where(
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.timestamp <= end_date,
                ).group_by(AuditLogModel.severity)

                severity_result = await session.execute(severity_query)
                severity_counts = {
                    row.severity.value: row.count for row in severity_result
                }

                return {
                    "period_days": days,
                    "total_logs": stats.total_logs,
                    "unique_users": stats.unique_users,
                    "unique_actions": stats.unique_actions,
                    "action_counts": action_counts,
                    "severity_counts": severity_counts,
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                }

        except Exception as e:
            self.logger.error(f"获取审计摘要失败: {e}")
            return {"error": str(e)}

    def close(self) -> None:
        """关闭服务 / Close Service"""
        if self.db_manager:
            asyncio.create_task(self.db_manager.close_async())
            self.db_manager = None
        self.logger.info("审计服务已关闭")