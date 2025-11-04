"""
任务错误日志记录器

负责记录任务执行过程中的错误信息,包括:
- API 调用失败日志
- 任务重试记录
- 系统异常日志
- 错误统计和分析

支持写入到 error_logs 表和数据采集日志表.
"""

import logging
import traceback
from datetime import datetime
from typing import Any

from sqlalchemy import text

from src.database.connection import DatabaseManager
from src.database.sql_compatibility import (CompatibleQueryBuilder,
                                            SQLCompatibilityHelper,
                                            get_db_type_from_engine)

from .models.data_collection_log import CollectionStatus, DataCollectionLog

logger = logging.getLogger(__name__)


class TaskErrorLogger:
    """类文档字符串"""

    pass  # 添加pass语句
    """任务错误日志记录器"""

    def __init__(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        self.db_manager = DatabaseManager()
        self._db_type = None
        self._query_builder = None

    async def log_task_error(
        self,
        task_name: str,
        task_id: str,
        error: Exception,
        context: dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> None:
        """
        记录任务错误日志

        Args:
            task_name: 任务名称
            task_id: 任务ID
            error: 异常对象
            context: 错误上下文信息
            retry_count: 当前重试次数
        """
        try:
            error_message = str(error)
            error_traceback = traceback.format_exc()

            # 构造错误信息
            error_details = {
                "task_name": task_name,
                "task_id": task_id,
                "error_type": type(error).__name__,
                "error_message": error_message,
                "traceback": error_traceback,
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat(),
                "context": context or {},
            }

            # 记录到数据库
            await self._save_error_to_db(error_details)

            # 记录到应用日志
            logger.error(
                f"任务错误: {task_name} (ID: {task_id}, 重试: {retry_count}), "
                f"错误: {error_message}",
                extra={
                    "task_name": task_name,
                    "task_id": task_id,
                    "retry_count": retry_count,
                    "error_type": type(error).__name__,
                },
            )

        except (RuntimeError, ValueError, ConnectionError) as log_error:
            # 如果记录日志失败,只能记录到应用日志
            logger.error(f"记录错误日志失败: {str(log_error)}")

    async def log_api_failure(
        self,
        task_name: str,
        api_endpoint: str,
        http_status: int | None,
        error_message: str,
        retry_count: int = 0,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """
        记录 API 调用失败日志

        Args:
            task_name: 任务名称
            api_endpoint: API端点
            http_status: HTTP状态码
            error_message: 错误消息
            retry_count: 重试次数
            response_data: 响应数据
        """
        try:
            error_details = {
                "task_name": task_name,
                "error_type": "API_FAILURE",
                "api_endpoint": api_endpoint,
                "http_status": http_status,
                "error_message": error_message,
                "retry_count": retry_count,
                "response_data": response_data,
                "timestamp": datetime.now().isoformat(),
            }

            await self._save_error_to_db(error_details)

            logger.warning(
                f"API调用失败: {api_endpoint} (状态码: {http_status}, 重试: {retry_count}), "
                f"错误: {error_message}",
                extra={
                    "task_name": task_name,
                    "api_endpoint": api_endpoint,
                    "http_status": http_status,
                    "retry_count": retry_count,
                },
            )

        except (RuntimeError, ValueError, ConnectionError) as log_error:
            logger.error(f"记录API错误日志失败: {str(log_error)}")

    async def log_data_collection_error(
        self,
        data_source: str,
        collection_type: str,
        error_message: str,
        records_processed: int = 0,
        success_count: int = 0,
        error_count: int = 0,
    ) -> int | None:
        """
        记录数据采集错误到 data_collection_logs 表

        Args:
            data_source: 数据源
            collection_type: 采集类型
            error_message: 错误信息
            records_processed: 处理记录数
            success_count: 成功数量
            error_count: 错误数量

        Returns:
            日志记录ID
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 创建数据采集日志记录
                log_entry = DataCollectionLog(
                    data_source=data_source,
                    collection_type=collection_type,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    records_collected=records_processed,
                    success_count=success_count,
                    error_count=error_count,
                    status=CollectionStatus.FAILED.value,
                    error_message=error_message,
                )

                session.add(log_entry)
                await session.commit()
                await session.refresh(log_entry)  # Refresh to get the actual ID

                logger.info(
                    f"数据采集错误已记录: {data_source} - {collection_type}, "
                    f"错误: {error_message}"
                )

                return int(log_entry.id) if log_entry.id is not None else None

        except (RuntimeError, ValueError, ConnectionError) as log_error:
            logger.error(f"记录数据采集错误失败: {str(log_error)}")
            return None

    async def _save_error_to_db(self, error_details: dict[str, Any]) -> None:
        """
        保存错误详情到数据库

        由于没有专门的 error_logs 表,这里使用原始SQL创建表并插入数据
        """
        try:
            async with self.db_manager.get_async_session() as session:
                # 确保 error_logs 表存在
                await self._ensure_error_logs_table_exists(session)

                # 插入错误日志
                insert_sql = text(
                    """
                    INSERT INTO error_logs (
                        task_name, task_id, error_type, error_message,
                        traceback, retry_count, context_data, created_at
                    ) VALUES (
                        :task_name, :task_id, :error_type, :error_message,
                        :traceback, :retry_count, :context_data, :created_at
                    )
                """
                )

                await session.execute(
                    insert_sql,
                    {
                        "task_name": error_details.get("task_name"),
                        "task_id": error_details.get("task_id"),
                        "error_type": error_details.get("error_type"),
                        "error_message": error_details.get("error_message"),
                        "traceback": error_details.get("traceback"),
                        "retry_count": error_details.get("retry_count", 0),
                        "context_data": str(error_details.get("context", {})),
                        "created_at": datetime.now(),
                    },
                )

                await session.commit()

        except (RuntimeError, ValueError, ConnectionError) as db_error:
            logger.error(f"保存错误到数据库失败: {str(db_error)}")

    async def _get_db_type(self) -> str:
        """获取数据库类型"""
        if self._db_type is None:
            try:
                # 获取数据库引擎来检测类型
                engine = self.db_manager._async_engine or self.db_manager._sync_engine
                if engine:
                    self._db_type = get_db_type_from_engine(engine)
                else:
                    self._db_type = "postgresql"  # 默认值
            except (ValueError, KeyError, RuntimeError):
                self._db_type = "postgresql"  # 默认值
        return self._db_type

    async def _get_query_builder(self) -> CompatibleQueryBuilder:
        """获取兼容性查询构建器"""
        if self._query_builder is None:
            db_type = await self._get_db_type()
            self._query_builder = CompatibleQueryBuilder(db_type)
        return self._query_builder

    async def _ensure_error_logs_table_exists(self, session) -> None:
        """确保 error_logs 表存在"""
        try:
            db_type = await self._get_db_type()
            create_table_sql = text(
                SQLCompatibilityHelper.create_error_logs_table_sql(db_type)
            )

            await session.execute(create_table_sql)
            await session.commit()

        except (RuntimeError, ValueError, ConnectionError) as create_error:
            logger.warning(f"创建 error_logs 表失败: {str(create_error)}")

    async def get_error_statistics(self, hours: int = 24) -> dict[str, Any]:
        """
        获取错误统计信息

        Args:
            hours: 统计时间范围(小时)

        Returns:
            错误统计数据
        """
        try:
            query_builder = await self._get_query_builder()

            async with self.db_manager.get_async_session() as session:
                # 获取错误总数
                error_count_sql = text(
                    query_builder.build_error_statistics_query(hours)
                )
                result = await session.execute(error_count_sql)
                total_errors = result.scalar() or 0

                # 按任务类型统计错误
                task_errors_sql = text(query_builder.build_task_errors_query(hours))
                result = await session.execute(task_errors_sql)
                task_errors = [
                    {"task_name": row.task_name, "error_count": row.error_count}
                    for row in result
                ]

                # 按错误类型统计
                type_errors_sql = text(query_builder.build_type_errors_query(hours))
                result = await session.execute(type_errors_sql)
                type_errors = [
                    {"error_type": row.error_type, "error_count": row.error_count}
                    for row in result
                ]

                return {
                    "total_errors": total_errors,
                    "task_errors": task_errors,
                    "type_errors": type_errors,
                    "time_range_hours": hours,
                    "timestamp": datetime.now().isoformat(),
                }

        except (RuntimeError, ValueError, ConnectionError) as stats_error:
            logger.error(f"获取错误统计失败: {str(stats_error)}")
            return {
                "total_errors": 0,
                "task_errors": [],
                "type_errors": [],
                "error": str(stats_error),
            }

    async def cleanup_old_errors(self, days_to_keep: int = 7) -> int:
        """
        清理旧的错误日志

        Args:
            days_to_keep: 保留天数

        Returns:
            清理的记录数
        """
        try:
            query_builder = await self._get_query_builder()

            async with self.db_manager.get_async_session() as session:
                cleanup_sql = text(
                    query_builder.build_cleanup_old_logs_query(days_to_keep)
                )
                result = await session.execute(cleanup_sql)
                await session.commit()

                deleted_count = result.rowcount
                logger.info(f"清理了 {deleted_count} 条旧的错误日志记录")

                return deleted_count

        except (RuntimeError, ValueError, ConnectionError) as cleanup_error:
            logger.error(f"清理错误日志失败: {str(cleanup_error)}")
            return 0

    async def cleanup_old_logs(self, days_to_keep: int = 7) -> int:
        """
        清理旧的错误日志(别名方法,兼容测试)

        Args:
            days_to_keep: 保留天数

        Returns:
            清理的记录数
        """
        return await self.cleanup_old_errors(days_to_keep)
