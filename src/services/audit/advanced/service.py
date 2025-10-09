"""
主审计服务
Advanced Audit Service

提供核心的审计功能实现，整合所有子模块功能。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .analyzers.data_analyzer import DataAnalyzer
from .analyzers.pattern_analyzer import PatternAnalyzer
from .analyzers.risk_analyzer import RiskAnalyzer
from .context import AuditContext
from .decorators.audit_decorators import audit_action
from .loggers.async_logger import AsyncLogger
from .loggers.audit_logger import AuditLogger
from .loggers.structured_logger import StructuredLogger
from .models import (
    AuditAction,
    AuditLog,
    AuditSeverity,
)
from .reporters.export_manager import ExportManager
from .reporters.report_generator import ReportGenerator
from .reporters.template_manager import TemplateManager
from .sanitizer import DataSanitizer
from src.core.logging import get_logger
from src.database.connection import DatabaseManager
from src.database.connection import get_database_manager

logger = get_logger(__name__)


class AuditService:
    """
    高级权限审计服务 / Advanced Permission Audit Service

    提供全面的审计功能，包括日志记录、数据分析、风险评估等。
    Provides comprehensive audit functionality including logging, data analysis, risk assessment, etc.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        enable_async_logging: bool = True,
        enable_structured_logging: bool = True,
    ):
        """
        初始化审计服务 / Initialize Audit Service

        Args:
            db_manager: 数据库管理器
            enable_async_logging: 启用异步日志
            enable_structured_logging: 启用结构化日志
        """
        self.db_manager = db_manager or get_database_manager()

        # 初始化日志记录器
        self.async_logger = AsyncLogger() if enable_async_logging else None
        self.structured_logger = StructuredLogger() if enable_structured_logging else None
        self.base_logger = AuditLogger()

        # 初始化分析器
        self.data_analyzer = DataAnalyzer(self.db_manager)
        self.pattern_analyzer = PatternAnalyzer()
        self.risk_analyzer = RiskAnalyzer()

        # 初始化报告生成器
        self.report_generator = ReportGenerator()
        self.template_manager = TemplateManager()
        self.export_manager = ExportManager()

        # 初始化数据清理器
        self.sanitizer = DataSanitizer()

        # 审计上下文
        self.context = AuditContext()

        logger.info("高级审计服务初始化完成")

    async def log_action(
        self,
        action: AuditAction,
        user_id: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[AuditLog]:
        """
        记录审计操作 / Log Audit Action

        Args:
            action: 操作类型
            user_id: 用户ID
            resource_id: 资源ID
            details: 详细信息
            severity: 严重级别
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            审计日志记录
        """
        try:
            # 创建审计日志
            audit_log = AuditLog(
                action=action,
                user_id=user_id,
                resource_id=resource_id,
                details=details or {},
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow(),
                context=self.context.get_context(),
            )

            # 清理敏感数据
            audit_log = self.sanitizer.sanitize_log(audit_log)

            # 保存到数据库
            async with self.db_manager.get_async_session() as session:
                session.add(audit_log)
                await session.commit()
                await session.refresh(audit_log)

            # 异步日志记录
            if self.async_logger:
                await self.async_logger.log_async(audit_log)

            # 结构化日志记录
            if self.structured_logger:
                self.structured_logger.log_structured(audit_log)

            # 基础日志记录
            self.base_logger.log(audit_log)

            return audit_log

        except Exception as e:
            logger.error(f"记录审计操作失败: {e}")
            return None

    async def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        查询审计日志 / Query Audit Logs

        Args:
            start_time: 开始时间
            end_time: 结束时间
            user_id: 用户ID
            action: 操作类型
            resource_id: 资源ID
            severity: 严重级别
            limit: 限制数量
            offset: 偏移量

        Returns:
            审计日志列表
        """
        try:
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select, desc
                from src.database.models.audit_log import AuditLog as AuditLogModel

                # 构建查询
                query = select(AuditLogModel)

                # 添加过滤条件
                if start_time:
                    query = query.where(AuditLogModel.timestamp >= start_time)
                if end_time:
                    query = query.where(AuditLogModel.timestamp <= end_time)
                if user_id:
                    query = query.where(AuditLogModel.user_id == user_id)
                if action:
                    query = query.where(AuditLogModel.action == action.value)
                if resource_id:
                    query = query.where(AuditLogModel.resource_id == resource_id)
                if severity:
                    query = query.where(AuditLogModel.severity == severity.value)

                # 添加排序和分页
                query = query.order_by(desc(AuditLogModel.timestamp))
                query = query.limit(limit).offset(offset)

                # 执行查询
                result = await session.execute(query)
                logs = result.scalars().all()

                # 转换为AuditLog对象
                audit_logs = []
                for log in logs:
                    audit_log = AuditLog(
                        action=AuditAction(log.action),
                        user_id=log.user_id,
                        resource_id=log.resource_id,
                        details=log.details or {},
                        severity=AuditSeverity(log.severity),
                        ip_address=log.ip_address,
                        user_agent=log.user_agent,
                        timestamp=log.timestamp,
                        context=log.context or {},
                    )
                    audit_logs.append(audit_log)

                return audit_logs

        except Exception as e:
            logger.error(f"查询审计日志失败: {e}")
            return []

    async def analyze_user_activity(
        self, user_id: str, days: int = 30
    ) -> Dict:
        """
        分析用户活动 / Analyze User Activity

        Args:
            user_id: 用户ID
            days: 分析天数

        Returns:
            分析结果
        """
        try:
            # 获取用户活动数据
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            logs = await self.query_logs(
                start_time=start_time,
                end_time=end_time,
                user_id=user_id,
                limit=10000,
            )

            # 使用数据分析器
            analysis = await self.data_analyzer.analyze_user_patterns(user_id, logs)

            # 风险评估
            risk_assessment = await self.risk_analyzer.assess_user_risk(user_id, logs)

            # 模式识别
            patterns = await self.pattern_analyzer.identify_patterns(logs)

            return {
                "user_id": user_id,
                "analysis_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "days": days,
                },
                "activity_summary": analysis,
                "risk_assessment": risk_assessment,
                "identified_patterns": patterns,
                "total_actions": len(logs),
            }

        except Exception as e:
            logger.error(f"分析用户活动失败: {e}")
            return {}

    async def generate_report(
        self,
        report_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filters: Optional[Dict] = None,
        format: str = "json",
    ) -> Optional[Dict]:
        """
        生成审计报告 / Generate Audit Report

        Args:
            report_type: 报告类型
            start_time: 开始时间
            end_time: 结束时间
            filters: 过滤条件
            format: 输出格式

        Returns:
            报告数据
        """
        try:
            # 获取数据
            logs = await self.query_logs(
                start_time=start_time,
                end_time=end_time,
                **filters or {},
                limit=50000,
            )

            # 生成报告
            report_data = await self.report_generator.generate_report(
                report_type=report_type,
                logs=logs,
                period={
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None,
                },
            )

            # 应用模板
            if report_type in self.template_manager.templates:
                report_data = self.template_manager.apply_template(
                    report_type, report_data
                )

            return report_data

        except Exception as e:
            logger.error(f"生成审计报告失败: {e}")
            return None

    async def export_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = "csv",
        filters: Optional[Dict] = None,
    ) -> Optional[bytes]:
        """
        导出审计日志 / Export Audit Logs

        Args:
            start_time: 开始时间
            end_time: 结束时间
            format: 导出格式
            filters: 过滤条件

        Returns:
            导出数据
        """
        try:
            # 获取数据
            logs = await self.query_logs(
                start_time=start_time,
                end_time=end_time,
                **filters or {},
                limit=100000,
            )

            # 转换为DataFrame
            import pandas as pd

            data = []
            for log in logs:
                data.append({
                    "timestamp": log.timestamp.isoformat(),
                    "action": log.action.value,
                    "user_id": log.user_id,
                    "resource_id": log.resource_id,
                    "severity": log.severity.value,
                    "ip_address": log.ip_address,
                    "details": str(log.details),
                })

            df = pd.DataFrame(data)

            # 导出
            if format == "csv":
                return df.to_csv(index=False).encode("utf-8")
            elif format == "json":
                return df.to_json(orient="records", indent=2).encode("utf-8")
            elif format == "excel":
                return df.to_excel(index=False, engine="openpyxl")
            else:
                raise ValueError(f"不支持的导出格式: {format}")

        except Exception as e:
            logger.error(f"导出审计日志失败: {e}")
            return None

    async def get_statistics(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> Dict:
        """
        获取审计统计信息 / Get Audit Statistics

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            统计信息
        """
        try:
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import select, func
                from src.database.models.audit_log import AuditLog as AuditLogModel

                # 构建基础查询
                query = select(func.count(AuditLogModel.id))
                if start_time:
                    query = query.where(AuditLogModel.timestamp >= start_time)
                if end_time:
                    query = query.where(AuditLogModel.timestamp <= end_time)

                # 总数
                total_count = await session.scalar(query)

                # 按操作类型统计
                action_query = select(
                    AuditLogModel.action,
                    func.count(AuditLogModel.id).label("count")
                ).group_by(AuditLogModel.action)

                if start_time:
                    action_query = action_query.where(AuditLogModel.timestamp >= start_time)
                if end_time:
                    action_query = action_query.where(AuditLogModel.timestamp <= end_time)

                action_stats = await session.execute(action_query)
                by_action = {row.action: row.count for row in action_stats}

                # 按用户统计（Top 10）
                user_query = select(
                    AuditLogModel.user_id,
                    func.count(AuditLogModel.id).label("count")
                ).group_by(AuditLogModel.user_id).order_by(
                    func.count(AuditLogModel.id).desc()
                ).limit(10)

                if start_time:
                    user_query = user_query.where(AuditLogModel.timestamp >= start_time)
                if end_time:
                    user_query = user_query.where(AuditLogModel.timestamp <= end_time)

                user_stats = await session.execute(user_query)
                by_user = {row.user_id: row.count for row in user_stats}

                # 按严重级别统计
                severity_query = select(
                    AuditLogModel.severity,
                    func.count(AuditLogModel.id).label("count")
                ).group_by(AuditLogModel.severity)

                if start_time:
                    severity_query = severity_query.where(AuditLogModel.timestamp >= start_time)
                if end_time:
                    severity_query = severity_query.where(AuditLogModel.timestamp <= end_time)

                severity_stats = await session.execute(severity_query)
                by_severity = {row.severity: row.count for row in severity_stats}

                return {
                    "period": {
                        "start": start_time.isoformat() if start_time else None,
                        "end": end_time.isoformat() if end_time else None,
                    },
                    "total_logs": total_count,
                    "by_action": by_action,
                    "by_user": by_user,
                    "by_severity": by_severity,
                }

        except Exception as e:
            logger.error(f"获取审计统计失败: {e}")
            return {}

    @audit_action(action=AuditAction.VIEW_AUDIT_LOGS)
    async def view_audit_logs(
        self, user_id: str, filters: Optional[Dict] = None
    ) -> List[AuditLog]:
        """
        查看审计日志（带审计装饰器）
        View Audit Logs (with audit decorator)

        Args:
            user_id: 查看者用户ID
            filters: 过滤条件

        Returns:
            审计日志列表
        """
        return await self.query_logs(**filters or {})

    async def cleanup_old_logs(self, days: int = 365) -> int:
        """
        清理旧日志 / Cleanup Old Logs

        Args:
            days: 保留天数

        Returns:
            删除的日志数量
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import delete
                from src.database.models.audit_log import AuditLog as AuditLogModel

                # 删除旧日志
                delete_stmt = delete(AuditLogModel).where(
                    AuditLogModel.timestamp < cutoff_date
                )
                result = await session.execute(delete_stmt)
                await session.commit()

                deleted_count = result.rowcount
                logger.info(f"清理了 {deleted_count} 条超过 {days} 天的审计日志")

                return deleted_count

        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            return 0

    async def export_report(
        self, report_data: Dict, format: str = "json"
    ) -> Optional[bytes]:
        """
        导出报告 / Export Report

        Args:
            report_data: 报告数据 / Report data
            format: 导出格式 / Export format

        Returns:
            导出数据 / Export data
        """
        return self.export_manager.export(report_data, format)