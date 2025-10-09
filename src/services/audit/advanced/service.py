"""
主审计服务
Advanced Audit Service

提供核心的审计功能实现，整合所有子模块功能。
"""

from src.database.connection import DatabaseManager
from typing import Dict
from typing import List
from typing import Optional
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.database.connection import get_database_manager

from .context import AuditContext
from .models import (
    AuditAction,
    AuditLog,
    AuditSeverity,
    AuditLogSummary,
)
from .analyzers.data_analyzer import DataAnalyzer
from .analyzers.pattern_analyzer import PatternAnalyzer
from .analyzers.risk_analyzer import RiskAnalyzer
from .loggers.audit_logger import AuditLogger
from .loggers.structured_logger import StructuredLogger
from .loggers.async_logger import AsyncLogger
from .reporters.report_generator import ReportGenerator
from .reporters.template_manager import TemplateManager
from .reporters.export_manager import ExportManager
from .decorators.audit_decorators import audit_action
from .sanitizer import DataSanitizer

logger = get_logger(__name__)


class AuditService:
    """
    高级权限审计服务 / Advanced Permission Audit Service

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

        # 初始化各个子模块
        self.data_sanitizer = DataSanitizer()
        self.data_analyzer = DataAnalyzer()
        self.pattern_analyzer = PatternAnalyzer()
        self.risk_analyzer = RiskAnalyzer()
        self.audit_logger = AuditLogger()
        self.structured_logger = StructuredLogger()
        self.async_logger = AsyncLogger()
        self.report_generator = ReportGenerator()
        self.template_manager = TemplateManager()
        self.export_manager = ExportManager()

    async def initialize(self) -> bool:
        """
        初始化服务 / Initialize Service

        Returns:
            初始化是否成功 / Whether initialization was successful
        """
        try:
            if not self.db_manager:
                self.db_manager = get_database_manager()

            # 初始化各个子模块
            await self.audit_logger.initialize(self.db_manager)
            await self.async_logger.initialize(self.db_manager)

            self.logger.info("高级审计服务初始化完成")
            return True

        except Exception as e:
            self.logger.error(f"初始化高级审计服务失败: {e}")
            return False

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
                severity = self.risk_analyzer.determine_severity(
                    action, table_name, error
                )

            # 确定合规类别
            compliance_category = self.data_analyzer.determine_compliance_category(
                table_name, action
            )

            # 检查敏感数据
            is_sensitive = self.data_sanitizer.is_sensitive_data(
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
                    audit_log.old_values = self.data_sanitizer.hash_sensitive_data(
                        str(audit_log.old_values)
                    )
                if audit_log.new_values:
                    audit_log.new_values = self.data_sanitizer.hash_sensitive_data(
                        str(audit_log.new_values)
                    )

            # 添加合规类别
            if compliance_category:
                audit_log.compliance_category = compliance_category

            # 保存审计日志
            success = await self.audit_logger.save_audit_entry(audit_log)

            if success:
                self.logger.debug(f"审计日志已记录: {action} - {context.user_id}")

            return success

        except Exception as e:
            self.logger.error(f"记录审计日志失败: {e}")
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
                action_data.get("context")
                result = self.log_action(**action_data)
                results.append(
                    {
                        "action": action_data.get("action"),
                        "success": result is not None,
                        "error": None if result is not None else "Failed to log",
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "action": action_data.get("action"),
                        "success": False,
                        "error": str(e),
                    }
                )

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
                    {"action": action, "count": count} for action, count in top_actions
                ]

                # 获取高风险操作
                high_risk = [
                    log
                    for log in logs
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

    async def get_high_risk_operations(self, hours: int = 24) -> List[Dict[str, Any]]:
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
                query = (
                    select(AuditLogModel)
                    .where(
                        AuditLogModel.severity.in_(["high", "critical"]),
                        AuditLogModel.timestamp >= start_time,
                        AuditLogModel.timestamp <= end_time,
                    )
                    .order_by(AuditLogModel.timestamp.desc())
                )

                result = await session.execute(query)
                logs = result.scalars().all()

                # 格式化结果
                operations = []
                for log in logs:
                    operations.append(
                        {
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
                        }
                    )

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
        return loop.run_until_complete(self.async_get_user_audit_logs(user_id, limit))

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

                query = (
                    select(AuditLogModel)
                    .where(AuditLogModel.user_id == user_id)
                    .order_by(AuditLogModel.timestamp.desc())
                    .limit(limit)
                )

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
        return loop.run_until_complete(self.async_get_audit_summary(days))

    async def async_get_audit_summary(self, days: int = 30) -> Dict[str, Any]:
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
                    func.count(func.distinct(AuditLogModel.user_id)).label(
                        "unique_users"
                    ),
                    func.count(func.distinct(AuditLogModel.action)).label(
                        "unique_actions"
                    ),
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
                action_query = (
                    select(
                        AuditLogModel.action,
                        func.count(AuditLogModel.id).label("count"),
                    )
                    .where(
                        AuditLogModel.timestamp >= start_date,
                        AuditLogModel.timestamp <= end_date,
                    )
                    .group_by(AuditLogModel.action)
                )

                action_result = await session.execute(action_query)
                action_counts = {row.action.value: row.count for row in action_result}

                severity_query = (
                    select(
                        AuditLogModel.severity,
                        func.count(AuditLogModel.id).label("count"),
                    )
                    .where(
                        AuditLogModel.timestamp >= start_date,
                        AuditLogModel.timestamp <= end_date,
                    )
                    .group_by(AuditLogModel.severity)
                )

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
        self.logger.info("高级审计服务已关闭")

    # 装饰器接口
    def audit_operation(self, action: str, resource_type: Optional[str] = None):
        """
        审计装饰器 / Audit Decorator

        Args:
            action: 动作名称 / Action name
            resource_type: 资源类型 / Resource type

        Returns:
            装饰器函数 / Decorator function
        """
        return audit_action(action, resource_type)

    # 分析器接口
    def analyze_data_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析数据模式 / Analyze Data Patterns

        Args:
            data: 数据 / Data

        Returns:
            分析结果 / Analysis result
        """
        return self.pattern_analyzer.analyze_patterns(data)

    def analyze_risk_level(self, operation: Dict[str, Any]) -> str:
        """
        分析风险级别 / Analyze Risk Level

        Args:
            operation: 操作信息 / Operation info

        Returns:
            风险级别 / Risk level
        """
        return self.risk_analyzer.assess_risk(operation)

    # 报告生成接口
    def generate_report(self, report_type: str, **kwargs) -> Dict[str, Any]:
        """
        生成报告 / Generate Report

        Args:
            report_type: 报告类型 / Report type
            **kwargs: 报告参数 / Report parameters

        Returns:
            报告数据 / Report data
        """
        return self.report_generator.generate_report(report_type, **kwargs)

    def export_report(self, report_data: Dict[str, Any], format: str) -> bytes:
        """
        导出报告 / Export Report

        Args:
            report_data: 报告数据 / Report data
            format: 导出格式 / Export format

        Returns:
            导出数据 / Export data
        """
        return self.export_manager.export(report_data, format)
