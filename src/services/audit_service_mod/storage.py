"""
审计日志存储
Audit Log Storage

负责将审计日志保存到数据库。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.database.connection_mod import DatabaseManager

from .models import AuditLog


class AuditLogStorage:
    """审计日志存储管理器"""

    def __init__(self):
        """初始化存储管理器"""
        self.db_manager: Optional[DatabaseManager] = None
        self.logger = get_logger(f"audit.{self.__class__.__name__}")
        self._batch_buffer: List[AuditLog] = []
        self._buffer_size = 100
        self._flush_interval = 30  # 秒
        self._last_flush = datetime.utcnow()

    async def initialize(self, db_manager: DatabaseManager) -> bool:
        """初始化存储"""
        try:
            self.db_manager = db_manager
            # 测试连接
            await self.db_manager.execute("SELECT 1")  # type: ignore
            self.logger.info("审计日志存储初始化成功")
            return True
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"审计日志存储初始化失败: {str(e)}")
            return False

    async def save_audit_entry(self, audit_log: AuditLog) -> bool:
        """保存单条审计日志"""
        try:
            if not self.db_manager:
                self.logger.error("数据库管理器未初始化")
                return False

            # 构建SQL
            sql = """
            INSERT INTO audit_logs (
                user_id, username, action, resource_type, resource_id,
                operation_type, table_name, old_values, new_values,
                ip_address, user_agent, severity, category, compliance_tags,
                created_at, session_id, request_id, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                $15, $16, $17, $18
            )
            """

            # 执行插入
            await self.db_manager.execute(  # type: ignore
                sql,
                audit_log.user_id,
                audit_log.username,
                audit_log.action.value,
                audit_log.resource_type,
                audit_log.resource_id,
                audit_log.operation_type,  # type: ignore
                audit_log.table_name,
                audit_log.old_values,
                audit_log.new_values,
                audit_log.ip_address,
                audit_log.user_agent,
                audit_log.severity.value,
                audit_log.category,  # type: ignore
                audit_log.compliance_tags,  # type: ignore
                audit_log.created_at,  # type: ignore
                audit_log.session_id,
                audit_log.request_id,
                audit_log.metadata,
            )

            self.logger.debug(f"审计日志已保存: {audit_log.id}")
            return True

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"保存审计日志失败: {str(e)}")
            return False

    async def batch_save(self, audit_logs: List[AuditLog]) -> List[bool]:
        """批量保存审计日志"""
        results = []
        for audit_log in audit_logs:
            result = await self.save_audit_entry(audit_log)
            results.append(result)
        return results

    async def add_to_batch(self, audit_log: AuditLog) -> None:
        """添加到批处理缓冲区"""
        self._batch_buffer.append(audit_log)

        # 检查是否需要刷新
        if (
            len(self._batch_buffer) >= self._buffer_size
            or (datetime.utcnow() - self._last_flush).seconds >= self._flush_interval
        ):
            await self.flush_batch()

    async def flush_batch(self) -> None:
        """刷新批处理缓冲区"""
        if not self._batch_buffer:
            return

        try:
            await self.batch_save(self._batch_buffer)
            self.logger.debug(f"批量保存了 {len(self._batch_buffer)} 条审计日志")
            self._batch_buffer.clear()
            self._last_flush = datetime.utcnow()
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"批量保存审计日志失败: {str(e)}")

    async def get_user_audit_logs(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取用户审计日志"""
        try:
            # 构建查询条件
            conditions = []
            params = []

            if user_id:
                conditions.append("user_id = $1")
                params.append(user_id)

            if start_date:
                conditions.append(f"created_at >= ${len(params) + 1}")
                params.append(start_date)  # type: ignore

            if end_date:
                conditions.append(f"created_at <= ${len(params) + 1}")
                params.append(end_date)  # type: ignore

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 添加分页参数
            params.extend([limit, offset])  # type: ignore

            sql = f"""
            SELECT * FROM audit_logs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """

            results = await self.db_manager.fetch_all(sql, *params)  # type: ignore
            return [dict(row) for row in results]

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"获取用户审计日志失败: {str(e)}")
            return []

    async def get_high_risk_operations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取高风险操作"""
        try:
            sql = (
                """
            SELECT * FROM audit_logs
            WHERE severity = 'HIGH'
            AND created_at >= NOW() - INTERVAL '%s hours'
            ORDER BY created_at DESC
            LIMIT 100
            """
                % hours
            )

            results = await self.db_manager.fetch_all(sql)  # type: ignore
            return [dict(row) for row in results]

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"获取高风险操作失败: {str(e)}")
            return []

    async def get_audit_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """获取审计摘要"""
        try:
            conditions = []
            params = []  # type: ignore

            if start_date:
                conditions.append(f"created_at >= ${len(params) + 1}")
                params.append(start_date)

            if end_date:
                conditions.append(f"created_at <= ${len(params) + 1}")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            sql = f"""
            SELECT
                COUNT(*) as total_operations,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_risk_count,
                COUNT(CASE WHEN operation_type = 'DELETE' THEN 1 END) as delete_count,
                COUNT(CASE WHEN operation_type = 'CREATE' THEN 1 END) as create_count,
                COUNT(CASE WHEN operation_type = 'UPDATE' THEN 1 END) as update_count
            FROM audit_logs
            WHERE {where_clause}
            """

            result = await self.db_manager.fetch_one(sql, *params)  # type: ignore
            return dict(result) if result else {}

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"获取审计摘要失败: {str(e)}")
            return {}
