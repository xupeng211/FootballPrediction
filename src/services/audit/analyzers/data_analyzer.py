"""
审计数据分析器

分析审计日志，提取统计信息和异常模式。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from src.database.connection import get_async_session
from src.database.models.audit_log import (
    AuditAction,
    AuditLog,
    AuditLogSummary,
    AuditSeverity,
)


class AuditStatus(str, Enum):
    """审计状态枚举（临时定义）"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class AuditAnalyzer:
    """审计数据分析器"""

    def __init__(self):
        """初始化分析器"""
        self.logger = logging.getLogger(f"audit.{self.__class__.__name__}")

    async def get_audit_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> Optional[AuditLogSummary]:
        """
        获取审计日志摘要

        Args:
            start_date: 开始日期
            end_date: 结束日期
            user_id: 用户ID
            table_name: 表名

        Returns:
            AuditLogSummary: 审计日志摘要
        """
        try:
            # 默认查询最近7天
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=7)

            async with get_async_session() as session:
                # 构建查询条件
                conditions = [
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date,
                ]
                if user_id:
                    conditions.append(AuditLog.user_id == user_id)
                if table_name:
                    conditions.append(AuditLog.table_name == table_name)

                # 统计查询
                result = await session.execute(
                    session.query(AuditLog)
                    .filter(and_(*conditions))
                    .with_entities(
                        func.count(AuditLog.id).label("total_operations"),
                        func.count(func.distinct(AuditLog.user_id)).label("unique_users"),
                        func.count(func.distinct(AuditLog.table_name)).label(
                            "unique_tables"
                        ),
                        func.count(
                            func.case([(AuditLog.is_high_risk == True, 1)])
                        ).label("high_risk_operations"),
                        func.count(
                            func.case([(AuditLog.status == AuditStatus.FAILED, 1)])
                        ).label("failed_operations"),
                        func.avg(AuditLog.execution_time_ms).label(
                            "avg_execution_time_ms"
                        ),
                    )
                    .first()
                )

                if result:
                    return AuditLogSummary(
                        start_date=start_date,
                        end_date=end_date,
                        total_operations=result.total_operations or 0,
                        unique_users=result.unique_users or 0,
                        unique_tables=result.unique_tables or 0,
                        high_risk_operations=result.high_risk_operations or 0,
                        failed_operations=result.failed_operations or 0,
                        avg_execution_time_ms=float(result.avg_execution_time_ms or 0),
                    )

        except Exception as e:
            self.logger.error(f"获取审计摘要失败: {e}", exc_info=True)
            return None

    async def get_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        获取用户活动记录

        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回记录数限制

        Returns:
            List[AuditLog]: 审计日志列表
        """
        try:
            async with get_async_session() as session:
                query = (
                    session.query(AuditLog)
                    .filter(AuditLog.user_id == user_id)
                    .order_by(desc(AuditLog.timestamp))
                    .limit(limit)
                )

                if start_date:
                    query = query.filter(AuditLog.timestamp >= start_date)
                if end_date:
                    query = query.filter(AuditLog.timestamp <= end_date)

                result = await session.execute(query)
                return result.scalars().all()

        except Exception as e:
            self.logger.error(f"获取用户活动失败: {e}", exc_info=True)
            return []

    async def detect_anomalies(
        self,
        hours: int = 24,
        failed_threshold: int = 10,
        high_risk_threshold: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检测异常活动

        Args:
            hours: 检查最近多少小时
            failed_threshold: 失败操作阈值
            high_risk_threshold: 高风险操作阈值

        Returns:
            List[Dict]: 异常列表
        """
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            anomalies = []

            async with get_async_session() as session:
                # 检测失败率高的用户
                failed_users = await session.execute(
                    session.query(AuditLog.user_id, func.count(AuditLog.id))
                    .filter(
                        and_(
                            AuditLog.timestamp >= start_time,
                            AuditLog.status == AuditStatus.FAILED,
                        )
                    )
                    .group_by(AuditLog.user_id)
                    .having(func.count(AuditLog.id) >= failed_threshold)
                )

                for user_id, count in failed_users:
                    anomalies.append(
                        {
                            "type": "high_failure_rate",
                            "user_id": user_id,
                            "failed_operations": count,
                            "time_window_hours": hours,
                        }
                    )

                # 检测高风险操作频繁的用户
                risk_users = await session.execute(
                    session.query(AuditLog.user_id, func.count(AuditLog.id))
                    .filter(
                        and_(
                            AuditLog.timestamp >= start_time,
                            AuditLog.is_high_risk == True,
                        )
                    )
                    .group_by(AuditLog.user_id)
                    .having(func.count(AuditLog.id) >= high_risk_threshold)
                )

                for user_id, count in risk_users:
                    anomalies.append(
                        {
                            "type": "high_risk_activity",
                            "user_id": user_id,
                            "high_risk_operations": count,
                            "time_window_hours": hours,
                        }
                    )

                # 检测异常时间段的活动
                hourly_activity = await session.execute(
                    session.query(
                        func.date_trunc("hour", AuditLog.timestamp).label("hour"),
                        func.count(AuditLog.id).label("count"),
                    )
                    .filter(AuditLog.timestamp >= start_time)
                    .group_by(func.date_trunc("hour", AuditLog.timestamp))
                    .order_by(desc("count"))
                    .limit(5)
                )

                avg_count = sum(row.count for row in hourly_activity) / max(
                    len(hourly_activity.fetchall()), 1
                )

                for hour, count in hourly_activity:
                    if count > avg_count * 3:  # 超过平均值3倍
                        anomalies.append(
                            {
                                "type": "unusual_activity_spike",
                                "hour": hour,
                                "operation_count": count,
                                "average_count": avg_count,
                            }
                        )

            return anomalies

        except Exception as e:
            self.logger.error(f"检测异常失败: {e}", exc_info=True)
            return []

    async def get_operation_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取操作统计信息

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 统计信息
        """
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=7)

            async with get_async_session() as session:
                # 按操作类型统计
                action_stats = await session.execute(
                    session.query(
                        AuditLog.action,
                        func.count(AuditLog.id).label("count"),
                    )
                    .filter(
                        and_(
                            AuditLog.timestamp >= start_date,
                            AuditLog.timestamp <= end_date,
                        )
                    )
                    .group_by(AuditLog.action)
                    .order_by(desc("count"))
                )

                # 按表名统计
                table_stats = await session.execute(
                    session.query(
                        AuditLog.table_name,
                        func.count(AuditLog.id).label("count"),
                    )
                    .filter(
                        and_(
                            AuditLog.timestamp >= start_date,
                            AuditLog.timestamp <= end_date,
                            AuditLog.table_name.isnot(None),
                        )
                    )
                    .group_by(AuditLog.table_name)
                    .order_by(desc("count"))
                    .limit(10)
                )

                # 按用户统计
                user_stats = await session.execute(
                    session.query(
                        AuditLog.user_id,
                        AuditLog.username,
                        func.count(AuditLog.id).label("count"),
                    )
                    .filter(
                        and_(
                            AuditLog.timestamp >= start_date,
                            AuditLog.timestamp <= end_date,
                        )
                    )
                    .group_by(AuditLog.user_id, AuditLog.username)
                    .order_by(desc("count"))
                    .limit(10)
                )

                return {
                    "by_action": [
                        {"action": action.value, "count": count}
                        for action, count in action_stats
                    ],
                    "by_table": [
                        {"table_name": table_name, "count": count}
                        for table_name, count in table_stats
                    ],
                    "by_user": [
                        {"user_id": user_id, "username": username, "count": count}
                        for user_id, username, count in user_stats
                    ],
                }

        except Exception as e:
            self.logger.error(f"获取操作统计失败: {e}", exc_info=True)
            return {}