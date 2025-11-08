"""
异步任务管理和批处理系统
Async Task Management and Batch Processing System

提供企业级异步任务管理、批处理、负载均衡等功能。
"""

import asyncio
import logging
import time
from asyncio import PriorityQueue, Queue, gather
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================================
# 任务优先级和状态
# ============================================================================


class TaskPriority(Enum):
    """任务优先级"""

    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    """异步任务"""

    id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float | None = None
    retry_count: int = 0
    max_retries: int = 3
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None
    error: Exception | None = None
    execution_time: float = 0.0

    def __lt__(self, other):
        """优先级队列比较"""
        return (self.priority.value, self.created_at) < (
            other.priority.value,
            other.created_at,
        )


class AsyncTaskManager:
    """异步任务管理器"""

    def __init__(self, max_workers: int = 10, max_queue_size: int = 1000):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.task_queue: PriorityQueue[AsyncTask] = PriorityQueue(
            maxsize=max_queue_size
        )
        self.active_tasks: set[str] = set()
        self.completed_tasks: dict[str, AsyncTask] = {}
        self.failed_tasks: dict[str, AsyncTask] = {}
        self.task_stats: dict[str, dict[str, Any]] = defaultdict(dict)
        self.workers: list[asyncio.Task] = []
        self.running = False
        self.batch_processor: BatchTaskProcessor | None = None

    async def start(self):
        """启动任务管理器"""
        if self.running:
            return

        self.running = True

        # 启动工作线程
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        # 启动批量处理器
        self.batch_processor = BatchTaskProcessor()
        await self.batch_processor.start()

        logger.info(f"任务管理器已启动，工作线程数: {self.max_workers}")

    async def stop(self):
        """停止任务管理器"""
        if not self.running:
            return

        self.running = False

        # 停止工作线程
        for worker in self.workers:
            worker.cancel()

        # 等待工作线程完成
        if self.workers:
            await gather(*self.workers, return_exceptions=True)

        # 停止批量处理器
        if self.batch_processor:
            await self.batch_processor.stop()

        self.workers.clear()
        logger.info("任务管理器已停止")

    async def submit_task(
        self,
        task_id: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float | None = None,
        max_retries: int = 3,
    ) -> AsyncTask:
        """提交任务"""
        if kwargs is None:
            kwargs = {}

        task = AsyncTask(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
        )

        try:
            self.task_queue.put_nowait(task)
            logger.debug(f"任务已提交: {task_id}")
            return task
        except asyncio.QueueFull as e:
            raise ValueError("任务队列已满") from e

    async def get_task_result(self, task_id: str, timeout: float | None = None) -> Any:
        """获取任务结果"""
        start_time = time.time()

        while True:
            if task_id in self.completed_tasks:
                task = self.completed_tasks[task_id]
                if task.error:
                    raise task.error
                return task.result

            if task_id in self.failed_tasks:
                task = self.failed_tasks[task_id]
                raise RuntimeError(f"任务执行失败: {task.error}")

            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"等待任务结果超时: {task_id}")

            await asyncio.sleep(0.1)

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        # 标记任务为已取消
        if task_id in self.completed_tasks:
            return False  # 已完成无法取消

        if task_id in self.active_tasks:
            # 正在运行的任务无法直接取消，依赖函数的超时机制
            logger.warning(f"任务正在运行，无法立即取消: {task_id}")
            return False

        return True

    async def _worker(self, worker_name: str):
        """工作线程"""
        logger.debug(f"工作线程已启动: {worker_name}")

        while self.running:
            try:
                # 获取任务
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)

                if task.status == TaskStatus.CANCELLED:
                    continue

                self.active_tasks.add(task.id)

                # 执行任务
                await self._execute_task(task, worker_name)

            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"工作线程错误 {worker_name}: {e}")

        logger.debug(f"工作线程已停止: {worker_name}")

    async def _execute_task(self, task: AsyncTask, worker_name: str):
        """执行任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            logger.debug(f"开始执行任务: {task.id} (worker: {worker_name})")

            start_time = time.time()

            if task.timeout:
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs), timeout=task.timeout
                )
            else:
                result = await task.func(*task.args, **task.kwargs)

            execution_time = time.time() - start_time
            task.execution_time = execution_time
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            # 更新统计信息
            self._update_task_stats(task, success=True)

            # 添加到已完成任务
            self.completed_tasks[task.id] = task

            logger.debug(f"任务执行完成: {task.id} (耗时: {execution_time:.3f}s)")

        except TimeoutError:
            task.error = TimeoutError(f"任务执行超时: {task.timeout}s")
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            self._handle_task_failure(task, worker_name, "超时")

        except Exception as e:
            task.error = e
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            self._handle_task_failure(task, worker_name, str(e))

        finally:
            self.active_tasks.discard(task.id)

    def _handle_task_failure(self, task: AsyncTask, worker_name: str, error_msg: str):
        """处理任务失败"""
        task.retry_count += 1

        if task.retry_count <= task.max_retries:
            logger.warning(
                f"任务执行失败，准备重试: {task.id} (重试次数: {task.retry_count}/{task.max_retries})"
            )
            # 重置任务状态并重新加入队列
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.error = None

            try:
                self.task_queue.put_nowait(task)
            except asyncio.QueueFull:
                logger.error(f"重试任务加入队列失败，任务已丢弃: {task.id}")
                self.failed_tasks[task.id] = task
        else:
            logger.error(f"任务最终执行失败: {task.id} (错误: {error_msg})")
            self.failed_tasks[task.id] = task

        self._update_task_stats(task, success=False)

    def _update_task_stats(self, task: AsyncTask, success: bool):
        """更新任务统计信息"""
        func_name = (
            task.func.__name__ if hasattr(task.func, "__name__") else str(task.func)
        )

        if func_name not in self.task_stats:
            self.task_stats[func_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_execution_time": 0.0,
                "avg_execution_time": 0.0,
                "max_execution_time": 0.0,
                "min_execution_time": float("inf"),
            }

        stats = self.task_stats[func_name]
        stats["total_executions"] += 1
        stats["total_execution_time"] += task.execution_time

        if success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1

        stats["avg_execution_time"] = (
            stats["total_execution_time"] / stats["total_executions"]
        )
        stats["max_execution_time"] = max(
            stats["max_execution_time"], task.execution_time
        )
        stats["min_execution_time"] = min(
            stats["min_execution_time"], task.execution_time
        )

    def get_task_stats(self) -> dict[str, Any]:
        """获取任务统计信息"""
        return {
            "task_stats": dict(self.task_stats),
            "queue_size": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "workers_active": len(self.workers),
            "running": self.running,
        }

    async def submit_batch_tasks(
        self, tasks: list[dict[str, Any]], batch_size: int = 10
    ) -> list[AsyncTask]:
        """批量提交任务"""
        submitted_tasks = []

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]

            batch_futures = []
            for task_info in batch:
                task = await self.submit_task(**task_info)
                batch_futures.append(task)
                submitted_tasks.append(task)

            # 等待当前批次完成（可选）
            # await gather(*[self.get_task_result(task.id) for task in batch_futures], return_exceptions=True)

        return submitted_tasks


class BatchTaskProcessor:
    """批量任务处理器"""

    def __init__(self, batch_size: int = 50, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batch_queue: Queue[list[Any]] = Queue()
        self.running = False
        self.processor_task: asyncio.Task | None = None

    async def start(self):
        """启动批量处理器"""
        if self.running:
            return

        self.running = True
        self.processor_task = asyncio.create_task(self._process_batches())
        logger.info("批量处理器已启动")

    async def stop(self):
        """停止批量处理器"""
        self.running = False

        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass

        logger.info("批量处理器已停止")

    async def submit_batch(self, items: list[Any]):
        """提交批量数据"""
        try:
            self.batch_queue.put_nowait(items)
            logger.debug(f"批量数据已提交: {len(items)} 项")
        except asyncio.QueueFull:
            logger.warning("批量队列已满，数据被丢弃")

    async def _process_batches(self):
        """处理批量数据"""
        accumulated_items = []
        last_flush = time.time()

        while self.running:
            try:
                # 尝试获取批量数据
                batch = await asyncio.wait_for(self.batch_queue.get(), timeout=1.0)

                accumulated_items.extend(batch)

                # 检查是否需要刷新
                should_flush = (
                    len(accumulated_items) >= self.batch_size
                    or (time.time() - last_flush) >= self.flush_interval
                )

                if should_flush and accumulated_items:
                    await self._flush_batch(accumulated_items)
                    accumulated_items.clear()
                    last_flush = time.time()

            except TimeoutError:
                # 检查是否需要基于时间刷新
                if (
                    accumulated_items
                    and (time.time() - last_flush) >= self.flush_interval
                ):
                    await self._flush_batch(accumulated_items)
                    accumulated_items.clear()
                    last_flush = time.time()

            except Exception as e:
                logger.error(f"批量处理错误: {e}")

    async def _flush_batch(self, items: list[Any]):
        """刷新批量数据"""
        try:
            # 这里可以实现具体的批量处理逻辑
            # 例如：批量数据库插入、批量缓存更新、批量API调用等
            logger.info(f"处理批量数据: {len(items)} 项")

            # 示例：模拟批量处理
            await asyncio.sleep(0.1)  # 模拟处理时间

            logger.debug(f"批量数据处理完成: {len(items)} 项")

        except Exception as e:
            logger.error(f"批量数据刷新失败: {e}")
            raise


# 全局任务管理器实例
_async_task_manager: AsyncTaskManager | None = None


async def get_async_task_manager(max_workers: int = 10) -> AsyncTaskManager:
    """获取全局异步任务管理器实例"""
    global _async_task_manager

    if _async_task_manager is None:
        _async_task_manager = AsyncTaskManager(max_workers=max_workers)
        await _async_task_manager.start()

    return _async_task_manager
