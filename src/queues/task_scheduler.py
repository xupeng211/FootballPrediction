"""
任务调度器

提供任务调度和管理功能，包括：
- 任务优先级调度
- 定时任务支持
- 任务重试机制
- 调度统计和监控
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .fifo_queue import FIFOQueue, QueueTask, TaskPriority, QueueStatus, queue_manager

logger = logging.getLogger(__name__)


class SchedulerStatus(Enum):
    """调度器状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class ScheduledTask:
    """定时任务"""
    id: str
    task_type: str
    schedule_time: datetime
    data: Dict[str, Any]
    priority: TaskPriority
    is_recurring: bool = False
    recurrence_interval: Optional[timedelta] = None
    max_attempts: int = 3
    attempts: int = 0

    def to_queue_task(self) -> QueueTask:
        """转换为队列任务"""
        return QueueTask(
            id=self.id,
            task_type=self.task_type,
            data=self.data,
            priority=self.priority,
            created_at=datetime.now(),
            max_attempts=self.max_attempts,
            scheduled_at=self.schedule_time
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'task_type': self.task_type,
            'schedule_time': self.schedule_time.isoformat(),
            'data': self.data,
            'priority': self.priority.value,
            'is_recurring': self.is_recurring,
            'recurrence_interval': self.recurrence_interval.total_seconds() if self.recurrence_interval else None,
            'max_attempts': self.max_attempts,
            'attempts': self.attempts
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledTask':
        """从字典创建"""
        return cls(
            id=data['id'],
            task_type=data['task_type'],
            schedule_time=datetime.fromisoformat(data['schedule_time']),
            data=data['data'],
            priority=TaskPriority(data['priority']),
            is_recurring=data.get('is_recurring', False),
            recurrence_interval=timedelta(seconds=data['recurrence_interval']) if data.get('recurrence_interval') else None,
            max_attempts=data.get('max_attempts', 3),
            attempts=data.get('attempts', 0)
        )


class TaskHandler:
    """任务处理器接口"""

    async def handle_task(self, task: QueueTask) -> Dict[str, Any]:
        """处理任务"""
        raise NotImplementedError


class DefaultTaskHandler(TaskHandler):
    """默认任务处理器"""

    async def handle_task(self, task: QueueTask) -> Dict[str, Any]:
        """默认处理逻辑"""
        logger.info(f"处理任务: {task.id} (类型: {task.task_type})")

        # 模拟任务处理
        await asyncio.sleep(0.1)  # 模拟处理时间

        result = {
            'task_id': task.id,
            'task_type': task.task_type,
            'status': 'completed',
            'processed_at': datetime.now().isoformat(),
            'data': task.data
        }

        logger.debug(f"任务 {task.id} 处理完成")
        return result


class TaskScheduler:
    """任务调度器"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.current_workers = 0
        self.status = SchedulerStatus.IDLE
        self.handlers: Dict[str, TaskHandler] = {}
        self.scheduled_tasks: List[ScheduledTask] = []
        self.worker_tasks: Dict[str, asyncio.Task] = {}
        self.statistics = {
            'total_scheduled': 0,
            'total_completed': 0,
            'total_failed': 0,
            'average_processing_time': 0.0,
            'processing_times': [],
            'created_at': datetime.now().isoformat()
        }

    def register_handler(self, task_type: str, handler: TaskHandler):
        """注册任务处理器"""
        self.handlers[task_type] = handler
        logger.info(f"注册任务处理器: {task_type}")

    def schedule_task(self, task_type: str, data: Dict[str, Any],
                      schedule_time: Optional[datetime] = None,
                      priority: TaskPriority = TaskPriority.NORMAL,
                      is_recurring: bool = False,
                      recurrence_interval: Optional[timedelta] = None,
                      **kwargs) -> str:
        """调度任务"""
        if schedule_time is None:
            schedule_time = datetime.now()

        scheduled_task = ScheduledTask(
            id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.scheduled_tasks)}",
            task_type=task_type,
            schedule_time=schedule_time,
            data=data,
            priority=priority,
            is_recurring=is_recurring,
            recurrence_interval=recurrence_interval,
            **kwargs
        )

        self.scheduled_tasks.append(scheduled_task)
        self.scheduled_tasks.sort(key=lambda t: (t.schedule_time, t.priority.value, t.id))

        self.statistics['total_scheduled'] += 1
        logger.info(f"调度任务: {scheduled_task.id} (类型: {task_type}, 时间: {schedule_time})")

        return scheduled_task.id

    async def start(self):
        """启动调度器"""
        if self.status == SchedulerStatus.RUNNING:
            logger.warning("调度器已在运行中")
            return

        self.status = SchedulerStatus.RUNNING
        logger.info("任务调度器启动")

        # 启动调度循环
        asyncio.create_task(self._schedule_loop())
        # 启动工作循环
        asyncio.create_task(self._worker_loop())

    async def stop(self):
        """停止调度器"""
        if self.status == SchedulerStatus.STOPPED:
            logger.warning("调度器已停止")
            return

        self.status = SchedulerStatus.STOPPED
        logger.info("任务调度器停止")

        # 取消所有工作任务
        for task_id, worker_task in self.worker_tasks.items():
            worker_task.cancel()

        # 等待工作任务完成
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks.values(), return_exceptions=True)

    async def pause(self):
        """暂停调度器"""
        self.status = SchedulerStatus.PAUSED
        logger.info("任务调度器暂停")

    async def resume(self):
        """恢复调度器"""
        if self.status == SchedulerStatus.RUNNING:
            return

        self.status = SchedulerStatus.RUNNING
        logger.info("任务调度器恢复")

    async def _schedule_loop(self):
        """调度循环"""
        while self.status != SchedulerStatus.STOPPED:
            try:
                if self.status == SchedulerStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue

                now = datetime.now()
                tasks_to_schedule = []

                # 找到需要调度的任务
                for i, task in enumerate(self.scheduled_tasks):
                    if task.schedule_time <= now:
                        tasks_to_schedule.append(i)

                # 调度就绪的任务
                for task_index in tasks_to_schedule:
                    task = self.scheduled_tasks.pop(task_index)
                    queue_task = task.to_queue_task()

                    # 使用默认队列（可以配置不同的队列）
                    default_queue = queue_manager.get_queue("default")
                    if default_queue:
                        await default_queue.enqueue(queue_task)
                        logger.debug(f"任务 {task.id} 已加入队列")

                await asyncio.sleep(1)  # 每秒检查一次

            except Exception as e:
                logger.error(f"调度循环异常: {e}")
                await asyncio.sleep(5)  # 异常时等待更长时间

    async def _worker_loop(self):
        """工作循环"""
        while self.status != SchedulerStatus.STOPPED:
            try:
                if self.status == SchedulerStatus.PAUSED or self.current_workers >= self.max_workers:
                    await asyncio.sleep(0.5)
                    continue

                # 从默认队列获取任务
                default_queue = queue_manager.get_queue("default")
                if not default_queue:
                    await asyncio.sleep(1)
                    continue

                task = await default_queue.dequeue(timeout=5)
                if task:
                    # 创建工作任务
                    worker_task = asyncio.create_task(self._process_task(task))
                    self.worker_tasks[task.id] = worker_task
                    self.current_workers += 1

                    # 任务完成后清理
                    worker_task.add_done_callback(
                        lambda t: self._cleanup_task(t.get_name())
                    )

                # 检查并清理已完成的工作任务
                await self._cleanup_completed_tasks()

            except Exception as e:
                logger.error(f"工作循环异常: {e}")
                await asyncio.sleep(1)

    async def _process_task(self, task: QueueTask):
        """处理任务"""
        start_time = datetime.now()

        try:
            # 获取任务处理器
            handler = self.handlers.get(task.task_type, DefaultTaskHandler())

            # 处理任务
            result = await handler.handle_task(task)

            # 标记任务完成
            await self._complete_task(task, result)

        except Exception as e:
            logger.error(f"处理任务 {task.id} 失败: {e}")
            await self._fail_task(task, str(e))
        finally:
            # 更新统计信息
            processing_time = (datetime.now() - start_time).total_seconds()
            self.statistics['processing_times'].append(processing_time)

            # 保持最近100个处理时间的统计
            if len(self.statistics['processing_times']) > 100:
                self.statistics['processing_times'] = self.statistics['processing_times'][-100:]

            if self.statistics['processing_times']:
                self.statistics['average_processing_time'] = sum(self.statistics['processing_times']) / len(self.statistics['processing_times'])

    async def _complete_task(self, task: QueueTask, result: Dict[str, Any]):
        """完成任务"""
        self.statistics['total_completed'] += 1

        # 如果是Redis队列，标记任务完成
        default_queue = queue_manager.get_queue("default")
        if default_queue and hasattr(default_queue, 'complete_task'):
            await default_queue.complete_task(task.id)

        # 如果是定时任务且是重复任务，重新调度
        for scheduled_task in self.scheduled_tasks:
            if scheduled_task.id == task.id and scheduled_task.is_recurring:
                scheduled_task.attempts = 0  # 重置尝试次数
                scheduled_task.schedule_time = datetime.now() + scheduled_task.recurrence_interval
                self.scheduled_tasks.append(scheduled_task)
                self.scheduled_tasks.sort(key=lambda t: (t.schedule_time, t.priority.value, t.id))
                break

        logger.info(f"任务 {task.id} 处理完成")

    async def _fail_task(self, task: QueueTask, error_message: str):
        """任务失败处理"""
        self.statistics['total_failed'] += 1

        # 如果是Redis队列，标记任务失败
        default_queue = queue_manager.get_queue("default")
        if default_queue and hasattr(default_queue, 'fail_task'):
            await default_queue.fail_task(task.id, error_message)

        # 如果是定时任务，根据最大尝试次数决定是否重新调度
        for scheduled_task in self.scheduled_tasks:
            if scheduled_task.id == task.id:
                scheduled_task.attempts += 1

                if scheduled_task.attempts < scheduled_task.max_attempts:
                    # 延迟重新调度
                    delay = timedelta(minutes=5 * scheduled_task.attempts)
                    scheduled_task.schedule_time = datetime.now() + delay
                    self.scheduled_tasks.append(scheduled_task)
                    self.scheduled_tasks.sort(key=lambda t: (t.schedule_time, t.priority.value, t.id))
                else:
                    logger.error(f"任务 {task.id} 超过最大尝试次数，放弃调度")

                break

        logger.error(f"任务 {task.id} 处理失败: {error_message}")

    def _cleanup_task(self, task_name: str):
        """清理完成的任务"""
        task_id = task_name.split('_')[-1]  # 从任务名称提取ID

        # 查找并删除工作记录
        if task_id in self.worker_tasks:
            del self.worker_tasks[task_id]
            self.current_workers = max(0, self.current_workers - 1)

    async def _cleanup_completed_tasks(self):
        """清理已完成的工作任务"""
        completed_tasks = []

        for task_id, worker_task in self.worker_tasks.items():
            if worker_task.done():
                completed_tasks.append(task_id)

        for task_id in completed_tasks:
            del self.worker_tasks[task_id]
            self.current_workers = max(0, self.current_workers - 1)

    def get_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        stats = self.statistics.copy()
        stats['status'] = self.status.value
        stats['current_workers'] = self.current_workers
        stats['max_workers'] = self.max_workers
        stats['scheduled_tasks_count'] = len(self.scheduled_tasks)

        return stats

    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """获取定时任务列表"""
        return [task.to_dict() for task in self.scheduled_tasks]


# 全局调度器实例
global_scheduler = TaskScheduler()


# 便捷函数
def get_scheduler() -> TaskScheduler:
    """获取全局调度器实例"""
    return global_scheduler


def schedule_task(task_type: str, data: Dict[str, Any],
                 schedule_time: Optional[datetime] = None,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 **kwargs) -> str:
    """便捷的任务调度函数"""
    return global_scheduler.schedule_task(
        task_type=task_type,
        data=data,
        schedule_time=schedule_time,
        priority=priority,
        **kwargs
    )


def register_task_handler(task_type: str, handler: TaskHandler):
    """便捷的处理器注册函数"""
    global_scheduler.register_handler(task_type, handler)