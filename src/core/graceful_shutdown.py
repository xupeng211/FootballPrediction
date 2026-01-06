#!/usr/bin/env python3
"""V105.0 优雅停机管理器 (Graceful Shutdown Manager).

实现信号监听和优雅停机机制：
1. 监听 SIGINT (Ctrl+C) 和 SIGTERM 信号
2. 确保数据库事务完成
3. 关闭浏览器内核
4. 保存检查点和状态
5. 保护数据一致性

Usage:
    >>> from src.core.graceful_shutdown import GracefulShutdownManager
    >>> shutdown_manager = GracefulShutdownManager()
    >>> shutdown_manager.register_cleanup_handler(close_database)
    >>> shutdown_manager.register_cleanup_handler(close_browser)
    >>> shutdown_manager.wait_for_shutdown()
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging
import signal

logger = logging.getLogger(__name__)


class ShutdownSignal(str, Enum):
    """停机信号类型"""

    SIGINT = "SIGINT"  # Ctrl+C
    SIGTERM = "SIGTERM"  # kill 命令
    TIMEOUT = "TIMEOUT"  # 超时


class ShutdownStatus(str, Enum):
    """停机状态"""

    RUNNING = "RUNNING"  # 正常运行
    SHUTTING_DOWN = "SHUTTING_DOWN"  # 正在停机
    SHUTDOWN_COMPLETE = "SHUTDOWN_COMPLETE"  # 停机完成
    SHUTDOWN_TIMEOUT = "SHUTDOWN_TIMEOUT"  # 停机超时


@dataclass
class ShutdownMetrics:
    """停机指标"""

    signal: ShutdownSignal | None = None
    initiated_at: datetime | None = None
    completed_at: datetime | None = None
    cleanup_handlers_registered: int = 0
    cleanup_handlers_executed: int = 0
    cleanup_handlers_failed: int = 0
    status: ShutdownStatus = ShutdownStatus.RUNNING

    @property
    def duration_seconds(self) -> float | None:
        """获取停机耗时"""
        if self.initiated_at and self.completed_at:
            return (self.completed_at - self.initiated_at).total_seconds()
        return None


class GracefulShutdownManager:
    """优雅停机管理器.

    管理应用的优雅停机流程，确保资源正确释放和数据一致性。

    Attributes:
        timeout: 停机超时时间（秒）
        metrics: 停机指标
    """

    def __init__(self, timeout: int = 30):
        """初始化停机管理器.

        Args:
            timeout: 停机超时时间（默认 30 秒）
        """
        self.timeout = timeout
        self.metrics = ShutdownMetrics()
        self._cleanup_handlers: list[Callable[[], None | Awaitable[None]]] = []
        self._shutdown_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

    def register_cleanup_handler(
        self,
        handler: Callable[[], None] | Callable[[], Awaitable[None]]
    ) -> None:
        """注册清理处理器.

        Args:
            handler: 清理函数（同步或异步）
        """
        self._cleanup_handlers.append(handler)
        self.metrics.cleanup_handlers_registered += 1
        logger.info(f"✅ 已注册清理处理器: {handler.__name__}")

    def unregister_cleanup_handler(
        self,
        handler: Callable[[], None] | Callable[[], Awaitable[None]]
    ) -> None:
        """取消注册清理处理器.

        Args:
            handler: 清理函数
        """
        if handler in self._cleanup_handlers:
            self._cleanup_handlers.remove(handler)
            self.metrics.cleanup_handlers_registered -= 1
            logger.info(f"❌ 已取消注册清理处理器: {handler.__name__}")

    def _handle_signal(self, signum: int, frame) -> None:
        """信号处理函数.

        Args:
            signum: 信号编号
            frame: 当前堆栈帧
        """
        signal_name = signal.Signals(signum).name
        logger.warning(f"📴 收到停机信号: {signal_name}")

        # 更新指标
        self.metrics.signal = ShutdownSignal(signal_name)
        self.metrics.initiated_at = datetime.now()
        self.metrics.status = ShutdownStatus.SHUTTING_DOWN

        # 触发停机事件
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._shutdown_event.set)
        else:
            self._shutdown_event.set()

    def setup_signal_handlers(self) -> None:
        """设置信号处理器."""
        logger.info("🔧 设置信号处理器...")
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        logger.info("✅ 信号处理器设置完成")

    async def execute_cleanup_handlers(self) -> None:
        """执行所有清理处理器."""
        logger.info("🧹 开始执行清理处理器...")

        for handler in self._cleanup_handlers:
            handler_name = getattr(handler, "__name__", "unknown")

            try:
                logger.info(f"⚙️ 执行: {handler_name}")

                # 检查是否为协程函数
                if asyncio.iscoroutinefunction(handler):
                    await asyncio.wait_for(handler(), timeout=10.0)
                else:
                    # 同步函数在线程池中执行
                    await asyncio.get_event_loop().run_in_executor(
                        None, handler
                    )

                self.metrics.cleanup_handlers_executed += 1
                logger.info(f"✅ 完成: {handler_name}")

            except TimeoutError:
                self.metrics.cleanup_handlers_failed += 1
                logger.error(f"⏱️ 超时: {handler_name}")
            except Exception as e:
                self.metrics.cleanup_handlers_failed += 1
                logger.error(f"❌ 失败: {handler_name} - {e}")

        logger.info("🧹 清理处理器执行完成")

    async def shutdown_async(self) -> None:
        """异步停机流程."""
        logger.info("=" * 60)
        logger.info("🛑 开始优雅停机流程")
        logger.info("=" * 60)

        try:
            # 执行清理处理器（带超时）
            await asyncio.wait_for(
                self.execute_cleanup_handlers(),
                timeout=self.timeout
            )

            self.metrics.completed_at = datetime.now()
            self.metrics.status = ShutdownStatus.SHUTDOWN_COMPLETE

            logger.info("=" * 60)
            logger.info("✅ 优雅停机完成")
            logger.info(f"⏱️ 耗时: {self.metrics.duration_seconds:.2f} 秒")
            logger.info(f"✅ 成功: {self.metrics.cleanup_handlers_executed}/{self.metrics.cleanup_handlers_registered}")
            logger.info(f"❌ 失败: {self.metrics.cleanup_handlers_failed}")
            logger.info("=" * 60)

        except TimeoutError:
            self.metrics.completed_at = datetime.now()
            self.metrics.status = ShutdownStatus.SHUTDOWN_TIMEOUT

            logger.error("=" * 60)
            logger.error("⏱️ 优雅停机超时")
            logger.error(f"⏱️ 已执行: {self.metrics.cleanup_handlers_executed}/{self.metrics.cleanup_handlers_registered}")
            logger.error("=" * 60)

    def wait_for_shutdown(self) -> None:
        """等待停机信号（同步版本）.

        阻塞当前线程，直到收到停机信号。
        """
        logger.info("⏳ 等待停机信号...")
        self._loop = asyncio.get_event_loop()

        # 运行停机流程
        try:
            self._loop.run_until_complete(self._shutdown_event.wait())
            self._loop.run_until_complete(self.shutdown_async())
        finally:
            # 清理事件循环
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()

    async def wait_for_shutdown_async(self) -> None:
        """等待停机信号（异步版本）.

        Args:
            coro: 主协程

        Returns:
            None
        """
        logger.info("⏳ 等待停机信号（异步模式）...")
        self._loop = asyncio.get_running_loop()

        # 等待停机信号
        await self._shutdown_event.wait()

        # 执行停机流程
        await self.shutdown_async()

    def get_metrics(self) -> dict:
        """获取停机指标.

        Returns:
            停机指标字典
        """
        return {
            "signal": self.metrics.signal.value if self.metrics.signal else None,
            "status": self.metrics.status.value,
            "initiated_at": self.metrics.initiated_at.isoformat() if self.metrics.initiated_at else None,
            "completed_at": self.metrics.completed_at.isoformat() if self.metrics.completed_at else None,
            "duration_seconds": self.metrics.duration_seconds,
            "handlers_registered": self.metrics.cleanup_handlers_registered,
            "handlers_executed": self.metrics.cleanup_handlers_executed,
            "handlers_failed": self.metrics.cleanup_handlers_failed,
        }


# ============================================================================
# 装饰器版本
# ============================================================================

def graceful_shutdown(timeout: int = 30):
    """优雅停机装饰器.

    Usage:
        >>> @graceful_shutdown(timeout=60)
        ... async def main():
        ...     # 主逻辑
        ...     pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = GracefulShutdownManager(timeout=timeout)
            manager.setup_signal_handlers()

            # 在后台任务中等待停机信号
            shutdown_task = asyncio.create_task(manager.wait_for_shutdown_async())

            try:
                # 执行主函数
                result = await func(*args, **kwargs)
                return result
            except asyncio.CancelledError:
                logger.info("主任务被取消，开始停机流程")
            finally:
                # 取消停机等待任务
                shutdown_task.cancel()
                try:
                    await shutdown_task
                except asyncio.CancelledError:
                    pass

        return wrapper
    return decorator
