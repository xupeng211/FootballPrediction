"""

"""






    """

    """

        """初始化审计日志器 / Initialize Audit Logger"""

        """


        """

        """


        """







        """


        """








        """


        """



















        """


        """













        """


        """






        """


        """












        """


        """







        """

        """

        """关闭日志器 / Close Logger"""



                from src.database.models.audit_log import AuditLog as AuditLogModel
                from src.database.models.audit_log import AuditLog as AuditLogModel
                from sqlalchemy import select, and_, desc, asc
                from src.database.models.audit_log import AuditLog as AuditLogModel
                from sqlalchemy import select, func, and_
                from src.database.models.audit_log import AuditLog as AuditLogModel
                from sqlalchemy import select
                from src.database.models.audit_log import AuditLog as AuditLogModel
                from sqlalchemy import select, func
                from src.database.models.audit_log import AuditLog as AuditLogModel
                from sqlalchemy import delete
                from src.database.models.audit_log import AuditLog as AuditLogModel
from datetime import datetime
from datetime import timedelta
from src.core.logging import get_logger

审计日志器
Audit Logger
负责审计日志的记录和管理。
logger = get_logger(__name__)
class AuditLogger:
    审计日志器 / Audit Logger
    提供审计日志的持久化存储和查询功能。
    Provides persistent storage and query functionality for audit logs.
    def __init__(self):
        self.logger = get_logger(f"audit.{self.__class__.__name__}")
        self.db_manager = None
        self._initialized = False
    async def initialize(self, db_manager) -> bool:
        初始化日志器 / Initialize Logger
        Args:
            db_manager: 数据库管理器 / Database manager
        Returns:
            bool: 初始化是否成功 / Whether initialization was successful
        try:
            self.db_manager = db_manager
            self._initialized = True
            self.logger.info("审计日志器初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"初始化审计日志器失败: {e}")
            return False
    async def save_audit_entry(self, audit_log: AuditLog) -> bool:
        保存审计条目 / Save Audit Entry
        Args:
            audit_log: 审计日志 / Audit log
        Returns:
            bool: 保存是否成功 / Whether save was successful
        if not self._initialized:
            self.logger.error("审计日志器未初始化")
            return False
        try:
            async with self.db_manager.get_async_session() as session:
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
            self.logger.debug(f"审计日志已保存: {audit_log.id}")
            return True
        except Exception as e:
            self.logger.error(f"保存审计条目失败: {e}")
            return False
    async def save_batch_audit_entries(self, audit_logs: List[AuditLog]) -> bool:
        批量保存审计条目 / Save Batch Audit Entries
        Args:
            audit_logs: 审计日志列表 / Audit logs list
        Returns:
            bool: 保存是否成功 / Whether save was successful
        if not self._initialized:
            self.logger.error("审计日志器未初始化")
            return False
        if not audit_logs:
            return True
        try:
            async with self.db_manager.get_async_session() as session:
                # 创建审计日志记录列表
                audit_records = []
                for audit_log in audit_logs:
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
                    audit_records.append(audit_record)
                # 批量插入
                session.add_all(audit_records)
                await session.commit()
                # 更新ID
                for i, audit_log in enumerate(audit_logs):
                    if i < len(audit_records):
                        audit_log.id = audit_records[i].id
            self.logger.info(f"批量保存审计日志完成: {len(audit_logs)} 条")
            return True
        except Exception as e:
            self.logger.error(f"批量保存审计条目失败: {e}")
            return False
    async def query_audit_logs(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "timestamp",
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        查询审计日志 / Query Audit Logs
        Args:
            filters: 过滤条件 / Filter conditions
            limit: 限制数量 / Limit
            offset: 偏移量 / Offset
            order_by: 排序字段 / Order by field
            order_desc: 是否降序 / Whether descending order
        Returns:
            List[Dict[str, Any]]: 审计日志列表 / Audit logs list
        if not self._initialized:
            self.logger.error("审计日志器未初始化")
            return []
        try:
            async with self.db_manager.get_async_session() as session:
                # 构建查询
                query = select(AuditLogModel)
                # 应用过滤条件
                if filters:
                    conditions = []
                    # 用户ID过滤
                    if filters.get("user_id"):
                        conditions.append(AuditLogModel.user_id == filters["user_id"])
                    # 动作过滤
                    if filters.get("action"):
                        if isinstance(filters["action"], list):
                            conditions.append(
                                AuditLogModel.action.in_(filters["action"])
                            )
                        else:
                            conditions.append(AuditLogModel.action == filters["action"])
                    # 严重性过滤
                    if filters.get("severity"):
                        if isinstance(filters["severity"], list):
                            conditions.append(
                                AuditLogModel.severity.in_(filters["severity"])
                            )
                        else:
                            conditions.append(
                                AuditLogModel.severity == filters["severity"]
                            )
                    # 资源类型过滤
                    if filters.get("resource_type"):
                        conditions.append(
                            AuditLogModel.resource_type == filters["resource_type"]
                        )
                    # 时间范围过滤
                    if filters.get("start_date"):
                        conditions.append(
                            AuditLogModel.timestamp >= filters["start_date"]
                        )
                    if filters.get("end_date"):
                        conditions.append(
                            AuditLogModel.timestamp <= filters["end_date"]
                        )
                    # IP地址过滤
                    if filters.get("ip_address"):
                        conditions.append(
                            AuditLogModel.ip_address == filters["ip_address"]
                        )
                    # 会话ID过滤
                    if filters.get("session_id"):
                        conditions.append(
                            AuditLogModel.session_id == filters["session_id"]
                        )
                    if conditions:
                        query = query.where(and_(*conditions))
                # 应用排序
                if hasattr(AuditLogModel, order_by):
                    order_column = getattr(AuditLogModel, order_by)
                    if order_desc:
                        query = query.order_by(desc(order_column))
                    else:
                        query = query.order_by(asc(order_column))
                # 应用分页
                query = query.offset(offset).limit(limit)
                # 执行查询
                result = await session.execute(query)
                logs = result.scalars().all()
                # 转换为字典格式
                audit_logs = []
                for log in logs:
                    audit_logs.append(
                        {
                            "id": log.id,
                            "timestamp": log.timestamp.isoformat(),
                            "user_id": log.user_id,
                            "username": log.username,
                            "user_role": log.user_role,
                            "session_id": log.session_id,
                            "action": log.action.value if log.action else "unknown",
                            "resource_type": log.resource_type,
                            "resource_id": log.resource_id,
                            "description": log.description,
                            "ip_address": log.ip_address,
                            "user_agent": log.user_agent,
                            "old_values": log.old_values,
                            "new_values": log.new_values,
                            "severity": log.severity.value
                            if log.severity
                            else "unknown",
                            "table_name": log.table_name,
                            "compliance_category": log.compliance_category,
                            "request_id": log.request_id,
                            "correlation_id": log.correlation_id,
                            "metadata": log.metadata,
                        }
                    )
                return audit_logs
        except Exception as e:
            self.logger.error(f"查询审计日志失败: {e}")
            return []
    async def count_audit_logs(self, filters: Optional[Dict[str, Any]] = None) -> int:
        统计审计日志数量 / Count Audit Logs
        Args:
            filters: 过滤条件 / Filter conditions
        Returns:
            int: 日志数量 / Log count
        if not self._initialized:
            self.logger.error("审计日志器未初始化")
            return 0
        try:
            async with self.db_manager.get_async_session() as session:
                # 构建查询
                query = select(func.count(AuditLogModel.id))
                # 应用过滤条件
                if filters:
                    conditions = []
                    if filters.get("user_id"):
                        conditions.append(AuditLogModel.user_id == filters["user_id"])
                    if filters.get("action"):
                        if isinstance(filters["action"], list):
                            conditions.append(
                                AuditLogModel.action.in_(filters["action"])
                            )
                        else:
                            conditions.append(AuditLogModel.action == filters["action"])
                    if filters.get("severity"):
                        if isinstance(filters["severity"], list):
                            conditions.append(
                                AuditLogModel.severity.in_(filters["severity"])
                            )
                        else:
                            conditions.append(
                                AuditLogModel.severity == filters["severity"]
                            )
                    if filters.get("start_date"):
                        conditions.append(
                            AuditLogModel.timestamp >= filters["start_date"]
                        )
                    if filters.get("end_date"):
                        conditions.append(
                            AuditLogModel.timestamp <= filters["end_date"]
                        )
                    if conditions:
                        query = query.where(and_(*conditions))
                # 执行查询
                result = await session.execute(query)
                count = result.scalar()
                return count or 0
        except Exception as e:
            self.logger.error(f"统计审计日志数量失败: {e}")
            return 0
    async def get_audit_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        根据ID获取审计日志 / Get Audit Log by ID
        Args:
            log_id: 日志ID / Log ID
        Returns:
            Optional[Dict[str, Any]]: 审计日志 / Audit log
        if not self._initialized:
            self.logger.error("审计日志器未初始化")
            return None
        try:
            async with self.db_manager.get_async_session() as session:
                query = select(AuditLogModel).where(AuditLogModel.id == log_id)
                result = await session.execute(query)
                log = result.scalar_one_or_none()
                if log:
                    return {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "user_id": log.user_id,
                        "username": log.username,
                        "user_role": log.user_role,
                        "session_id": log.session_id,
                        "action": log.action.value if log.action else "unknown",
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "description": log.description,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "old_values": log.old_values,
                        "new_values": log.new_values,
                        "severity": log.severity.value if log.severity else "unknown",
                        "table_name": log.table_name,
                        "compliance_category": log.compliance_category,
                        "request_id": log.request_id,
                        "correlation_id": log.correlation_id,
                        "metadata": log.metadata,
                    }
                return None
        except Exception as e:
            self.logger.error(f"获取审计日志失败: {e}")
            return None
    async def get_audit_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        获取审计统计信息 / Get Audit Statistics
        Args:
            start_date: 开始日期 / Start date
            end_date: 结束日期 / End date
        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        if not self._initialized:
            self.logger.error("审计日志器未初始化")
            return {}
        try:
            async with self.db_manager.get_async_session() as session:
                # 构建基础查询
                base_query = select(AuditLogModel)
                if start_date:
                    base_query = base_query.where(AuditLogModel.timestamp >= start_date)
                if end_date:
                    base_query = base_query.where(AuditLogModel.timestamp <= end_date)
                # 总日志数
                total_count_query = select(func.count()).select_from(
                    base_query.subquery()
                )
                total_result = await session.execute(total_count_query)
                total_logs = total_result.scalar() or 0
                # 按动作统计
                action_stats_query = (
                    select(
                        AuditLogModel.action,
                        func.count(AuditLogModel.id).label("count"),
                    )
                    .select_from(base_query.subquery())
                    .group_by(AuditLogModel.action)
                )
                action_result = await session.execute(action_stats_query)
                action_stats = {row.action.value: row.count for row in action_result}
                # 按严重性统计
                severity_stats_query = (
                    select(
                        AuditLogModel.severity,
                        func.count(AuditLogModel.id).label("count"),
                    )
                    .select_from(base_query.subquery())
                    .group_by(AuditLogModel.severity)
                )
                severity_result = await session.execute(severity_stats_query)
                severity_stats = {
                    row.severity.value: row.count for row in severity_result
                }
                # 按用户统计（前10名）
                user_stats_query = (
                    select(
                        AuditLogModel.user_id,
                        func.count(AuditLogModel.id).label("count"),
                    )
                    .select_from(base_query.subquery())
                    .group_by(AuditLogModel.user_id)
                    .order_by(func.count(AuditLogModel.id).desc())
                    .limit(10)
                )
                user_result = await session.execute(user_stats_query)
                user_stats = [
                    {"user_id": row.user_id, "count": row.count} for row in user_result
                ]
                return {
                    "total_logs": total_logs,
                    "action_distribution": action_stats,
                    "severity_distribution": severity_stats,
                    "top_users": user_stats,
                    "period": {
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None,
                    },
                    "generated_at": datetime.now().isoformat(),
                }
        except Exception as e:
            self.logger.error(f"获取审计统计信息失败: {e}")
            return {}
    async def cleanup_old_logs(self, retention_days: int = 365) -> int:
        清理旧日志 / Cleanup Old Logs
        Args:
            retention_days: 保留天数 / Retention days
        Returns:
            int: 清理的日志数量 / Number of cleaned logs
        if not self._initialized:
            self.logger.error("审计日志器未初始化")
            return 0
        try:
            async with self.db_manager.get_async_session() as session:
                # 计算截止日期
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                # 删除旧日志
                delete_query = delete(AuditLogModel).where(
                    AuditLogModel.timestamp < cutoff_date
                )
                result = await session.execute(delete_query)
                await session.commit()
                deleted_count = result.rowcount
                self.logger.info(f"清理了 {deleted_count} 条旧审计日志")
                return deleted_count
        except Exception as e:
            self.logger.error(f"清理旧日志失败: {e}")
            return 0
    def is_initialized(self) -> bool:
        检查是否已初始化 / Check if Initialized
        Returns:
            bool: 是否已初始化 / Whether initialized
        return self._initialized and self.db_manager is not None
    async def close(self) -> None:
        self._initialized = False
        self.db_manager = None
        self.logger.info("审计日志器已关闭")