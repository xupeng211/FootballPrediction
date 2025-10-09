"""
异步日志器
Async Logger

提供高性能的异步审计日志记录功能。
"""

import asyncio
import queue
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.core.logging import get_logger
from src.database.connection import get_database_manager

from ..models import AuditLog

logger = get_logger(__name__)


class AsyncLogger:
    """
    异步日志器 / Async Logger

    提供异步批量的高性能日志记录功能。
    Provides high-performance async batch logging functionality.
    """

    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        """
        初始化异步日志器 / Initialize Async Logger

        Args:
            batch_size: 批量大小 / Batch size
            flush_interval: 刷新间隔 / Flush interval
        """
        self.logger = get_logger(f"audit.{self.__class__.__name__}")
        self.db_manager = None
        self._initialized = False

        # 批处理配置
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # 异步队列和事件
        self._log_queue = asyncio.Queue()
        self._flush_event = asyncio.Event()
        self._stop_event = asyncio.Event()

        # 后台任务
        self._background_task: Optional[asyncio.Task] = None
        self._flush_timer_task: Optional[asyncio.Task] = None

        # 统计信息
        self._stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_errors": 0,
            "queue_size": 0,
            "last_flush": None,
            "batches_processed": 0,
        }

    async def initialize(self, db_manager) -> bool:
        """
        初始化日志器 / Initialize Logger

        Args:
            db_manager: 数据库管理器 / Database manager

        Returns:
            bool: 初始化是否成功 / Whether initialization was successful
        """
        try:
            self.db_manager = db_manager
            self._initialized = True

            # 启动后台处理任务
            self._background_task = asyncio.create_task(self._process_logs())
            self._flush_timer_task = asyncio.create_task(self._flush_timer())

            self.logger.info("异步日志器初始化完成")
            return True

        except Exception as e:
            self.logger.error(f"初始化异步日志器失败: {e}")
            return False

    async def log_audit_entry(self, audit_log: AuditLog) -> bool:
        """
        异步记录审计条目 / Async Log Audit Entry

        Args:
            audit_log: 审计日志 / Audit log

        Returns:
            bool: 是否成功加入队列 / Whether successfully queued
        """
        if not self._initialized:
            self.logger.error("异步日志器未初始化")
            return False

        try:
            # 添加到队列
            await self._log_queue.put(audit_log)
            self._stats["total_queued"] += 1
            self._stats["queue_size"] = self._log_queue.qsize()

            return True

        except Exception as e:
            self.logger.error(f"异步记录审计条目失败: {e}")
            self._stats["total_errors"] += 1
            return False

    async def log_batch_entries(self, audit_logs: List[AuditLog]) -> bool:
        """
        批量异步记录审计条目 / Batch Async Log Audit Entries

        Args:
            audit_logs: 审计日志列表 / Audit logs list

        Returns:
            bool: 是否成功加入队列 / Whether successfully queued
        """
        if not self._initialized:
            self.logger.error("异步日志器未初始化")
            return False

        if not audit_logs:
            return True

        try:
            # 批量添加到队列
            for audit_log in audit_logs:
                await self._log_queue.put(audit_log)
                self._stats["total_queued"] += 1

            self._stats["queue_size"] = self._log_queue.qsize()
            self.logger.debug(f"批量加入队列: {len(audit_logs)} 条审计日志")

            return True

        except Exception as e:
            self.logger.error(f"批量异步记录审计条目失败: {e}")
            self._stats["total_errors"] += 1
            return False

    async def _process_logs(self) -> None:
        """处理日志的后台任务 / Background task to process logs"""
        self.logger.info("异步日志处理任务已启动")

        while not self._stop_event.is_set():
            try:
                # 收集一批日志
                batch = await self._collect_batch()

                if batch:
                    # 处理这批日志
                    await self._process_batch(batch)

                # 等待更多日志或停止信号
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=1.0
                )

            except asyncio.TimeoutError:
                # 超时是正常的，继续处理
                continue
            except Exception as e:
                self.logger.error(f"处理日志批次时发生错误: {e}")
                self._stats["total_errors"] += 1
                await asyncio.sleep(1.0)  # 避免快速重试

        # 处理剩余的日志
        await self._process_remaining_logs()

        self.logger.info("异步日志处理任务已停止")

    async def _collect_batch(self) -> List[AuditLog]:
        """
        收集一批日志 / Collect a Batch of Logs

        Returns:
            List[AuditLog]: 日志批次 / Log batch
        """
        batch = []

        try:
            # 等待第一个日志
            first_log = await asyncio.wait_for(
                self._log_queue.get(),
                timeout=1.0
            )
            batch.append(first_log)

            # 尝试收集更多日志直到达到批量大小
            while len(batch) < self.batch_size and not self._log_queue.empty():
                try:
                    log = await asyncio.wait_for(
                        self._log_queue.get(),
                        timeout=0.1
                    )
                    batch.append(log)
                except asyncio.TimeoutError:
                    break

        except asyncio.TimeoutError:
            # 没有日志可处理
            pass

        return batch

    async def _process_batch(self, batch: List[AuditLog]) -> None:
        """
        处理日志批次 / Process Log Batch

        Args:
            batch: 日志批次 / Log batch
        """
        if not batch:
            return

        try:
            # 保存到数据库
            success = await self._save_batch_to_database(batch)

            if success:
                self._stats["total_processed"] += len(batch)
                self._stats["batches_processed"] += 1
                self._stats["last_flush"] = datetime.now().isoformat()
                self._stats["queue_size"] = self._log_queue.qsize()

                self.logger.debug(f"成功处理日志批次: {len(batch)} 条")
            else:
                self._stats["total_errors"] += len(batch)
                self.logger.error(f"处理日志批次失败: {len(batch)} 条")

        except Exception as e:
            self._stats["total_errors"] += len(batch)
            self.logger.error(f"处理日志批次时发生异常: {e}")

    async def _save_batch_to_database(self, batch: List[AuditLog]) -> bool:
        """
        批量保存到数据库 / Save Batch to Database

        Args:
            batch: 日志批次 / Log batch

        Returns:
            bool: 是否成功 / Whether successful
        """
        if not self.db_manager:
            self.logger.error("数据库管理器未初始化")
            return False

        try:
            async with self.db_manager.get_async_session() as session:
                from src.database.models.audit_log import AuditLog as AuditLogModel

                # 创建数据库记录
                audit_records = []
                for audit_log in batch:
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

                return True

        except Exception as e:
            self.logger.error(f"批量保存到数据库失败: {e}")
            return False

    async def _flush_timer(self) -> None:
        """定时刷新任务 / Periodic Flush Task"""
        self.logger.info("异步日志刷新定时器已启动")

        while not self._stop_event.is_set():
            try:
                # 等待刷新间隔或停止信号
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.flush_interval
                )

                if self._stop_event.is_set():
                    break

                # 触发刷新
                self._flush_event.set()

            except asyncio.TimeoutError:
                # 触发刷新
                self._flush_event.set()
            except Exception as e:
                self.logger.error(f"刷新定时器错误: {e}")

        self.logger.info("异步日志刷新定时器已停止")

    async def _process_remaining_logs(self) -> None:
        """处理剩余的日志 / Process Remaining Logs"""
        try:
            # 获取剩余的所有日志
            remaining_logs = []
            while not self._log_queue.empty():
                try:
                    log = self._log_queue.get_nowait()
                    remaining_logs.append(log)
                except asyncio.QueueEmpty:
                    break

            if remaining_logs:
                # 处理剩余的日志
                await self._process_batch(remaining_logs)
                self.logger.info(f"处理剩余日志: {len(remaining_logs)} 条")

        except Exception as e:
            self.logger.error(f"处理剩余日志时发生错误: {e}")

    async def flush(self) -> bool:
        """
        手动刷新队列 / Manual Flush Queue

        Returns:
            bool: 是否成功 / Whether successful
        """
        if not self._initialized:
            self.logger.error("异步日志器未初始化")
            return False

        try:
            # 触发刷新事件
            self._flush_event.set()

            # 等待队列清空
            timeout = 30.0  # 30秒超时
            start_time = datetime.now()

            while not self._log_queue.empty():
                if (datetime.now() - start_time).total_seconds() > timeout:
                    self.logger.warning("刷新队列超时")
                    return False

                await asyncio.sleep(0.1)

            self.logger.info("队列刷新完成")
            return True

        except Exception as e:
            self.logger.error(f"刷新队列失败: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息 / Get Statistics

        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        """
        return {
            **self._stats,
            "queue_size": self._log_queue.qsize(),
            "is_initialized": self._initialized,
            "batch_size": self.batch_size,
            "flush_interval": self.flush_interval,
            "background_task_running": self._background_task and not self._background_task.done(),
            "flush_timer_running": self._flush_timer_task and not self._flush_timer_task.done(),
        }

    async def set_batch_size(self, batch_size: int) -> None:
        """
        设置批量大小 / Set Batch Size

        Args:
            batch_size: 新的批量大小 / New batch size
        """
        if batch_size > 0:
            self.batch_size = batch_size
            self.logger.info(f"批量大小已设置为: {batch_size}")

    async def set_flush_interval(self, flush_interval: float) -> None:
        """
        设置刷新间隔 / Set Flush Interval

        Args:
            flush_interval: 新的刷新间隔 / New flush interval
        """
        if flush_interval > 0:
            self.flush_interval = flush_interval
            self.logger.info(f"刷新间隔已设置为: {flush_interval} 秒")

    def is_initialized(self) -> bool:
        """
        检查是否已初始化 / Check if Initialized

        Returns:
            bool: 是否已初始化 / Whether initialized
        """
        return self._initialized and self.db_manager is not None

    async def close(self) -> None:
        """关闭异步日志器 / Close Async Logger"""
        if not self._initialized:
            return

        try:
            self.logger.info("正在关闭异步日志器...")

            # 停止后台任务
            self._stop_event.set()

            # 等待后台任务完成
            if self._background_task:
                await self._background_task

            if self._flush_timer_task:
                self._flush_timer_task.cancel()
                try:
                    await self._flush_timer_task
                except asyncio.CancelledError:
                    pass

            # 处理剩余日志
            await self._process_remaining_logs()

            # 清理
            self._initialized = False
            self.db_manager = None

            self.logger.info("异步日志器已关闭")

        except Exception as e:
            self.logger.error(f"关闭异步日志器时发生错误: {e}")

    async def __aenter__(self):
        """异步上下文管理器入口 / Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口 / Async context manager exit"""
        await self.close()