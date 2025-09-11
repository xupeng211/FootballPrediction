"""
任务调度器主模块

支持 cron 表达式的主调度器，负责管理和调度所有数据采集和处理任务。
实现动态任务注册、cron表达式解析、任务执行监控等功能。

基于 DATA_DESIGN.md 第3节调度策略设计。
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from croniter import croniter

from .dependency_resolver import DependencyResolver
from .job_manager import JobManager
from .recovery_handler import RecoveryHandler

logger = logging.getLogger(__name__)


class ScheduledTask:
    """调度任务类"""

    def __init__(
        self,
        task_id: str,
        name: str,
        cron_expression: str,
        task_function: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        priority: int = 5,
        max_retries: int = 3,
        timeout: int = 300,
        description: str = "",
    ):
        """
        初始化调度任务

        Args:
            task_id: 任务唯一标识
            name: 任务名称
            cron_expression: cron表达式，支持标准5段或6段格式
            task_function: 要执行的任务函数
            args: 任务函数参数
            kwargs: 任务函数关键字参数
            dependencies: 依赖的任务ID列表
            priority: 任务优先级（1-10，数字越小优先级越高）
            max_retries: 最大重试次数
            timeout: 任务超时时间（秒）
            description: 任务描述
        """
        self.task_id = task_id
        self.name = name
        self.cron_expression = cron_expression
        self.task_function = task_function
        self.args = args
        self.kwargs = kwargs or {}
        self.dependencies = dependencies or []
        self.priority = priority
        self.max_retries = max_retries
        self.timeout = timeout
        self.description = description

        # 状态信息
        self.last_run_time: Optional[datetime] = None
        self.next_run_time: Optional[datetime] = None
        self.is_running: bool = False
        self.retry_count: int = 0
        self.last_error: Optional[str] = None

        # 初始化cron迭代器
        self._update_next_run_time()

    def _update_next_run_time(self) -> None:
        """更新下次执行时间"""
        try:
            base_time = self.last_run_time or datetime.now()
            cron = croniter(self.cron_expression, base_time)
            self.next_run_time = cron.get_next(datetime)
        except Exception as e:
            logger.error(f"任务 {self.task_id} 的cron表达式解析失败: {e}")
            self.next_run_time = None

    def should_run(self, current_time: datetime) -> bool:
        """判断是否应该执行任务"""
        if self.is_running or self.next_run_time is None:
            return False
        return current_time >= self.next_run_time

    def mark_completed(self, success: bool = True, error: Optional[str] = None) -> None:
        """标记任务完成"""
        self.is_running = False
        self.last_run_time = datetime.now()

        if success:
            self.retry_count = 0
            self.last_error = None
        else:
            self.retry_count += 1
            self.last_error = error

        self._update_next_run_time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "cron_expression": self.cron_expression,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "description": self.description,
            "last_run_time": self.last_run_time.isoformat()
            if self.last_run_time
            else None,
            "next_run_time": self.next_run_time.isoformat()
            if self.next_run_time
            else None,
            "is_running": self.is_running,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
        }


class TaskScheduler:
    """
    任务调度器主类

    支持cron表达式的任务调度器，提供以下功能：
    - 动态任务注册和管理
    - cron表达式解析和调度
    - 任务依赖关系处理
    - 失败重试和错误恢复
    - 任务执行监控和日志记录
    """

    def __init__(self):
        """初始化调度器"""
        self.tasks: Dict[str, ScheduledTask] = {}
        self.job_manager = JobManager()
        self.dependency_resolver = DependencyResolver()
        self.recovery_handler = RecoveryHandler()

        # 调度器状态
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 配置参数
        self.check_interval = 30  # 检查间隔（秒）
        self.max_concurrent_tasks = 10  # 最大并发任务数

        logger.info("任务调度器初始化完成")

    def register_task(self, task: ScheduledTask) -> bool:
        """
        注册调度任务

        Args:
            task: 要注册的调度任务

        Returns:
            bool: 注册是否成功
        """
        try:
            # 验证cron表达式
            croniter(task.cron_expression)

            # 注册到依赖解析器
            self.dependency_resolver.add_task(task.task_id, task.dependencies)

            # 添加到任务列表
            self.tasks[task.task_id] = task

            logger.info(f"任务注册成功: {task.task_id} - {task.name}")
            return True

        except Exception as e:
            logger.error(f"任务注册失败: {task.task_id} - {e}")
            return False

    def register_predefined_tasks(self) -> None:
        """注册预定义的数据采集任务"""
        # 导入任务函数
        from .tasks import (calculate_features, cleanup_data, collect_fixtures,
                            collect_live_scores, collect_odds)

        # 定义预设任务
        predefined_tasks = [
            ScheduledTask(
                task_id="fixtures_collection",
                name="赛程数据采集",
                cron_expression="0 2 * * *",  # 每日凌晨2:00
                task_function=collect_fixtures,
                priority=1,
                max_retries=3,
                timeout=600,
                description="采集比赛赛程数据，更新比赛安排信息",
            ),
            ScheduledTask(
                task_id="odds_collection",
                name="赔率数据采集",
                cron_expression="*/5 * * * *",  # 每5分钟
                task_function=collect_odds,
                dependencies=["fixtures_collection"],
                priority=2,
                max_retries=2,
                timeout=300,
                description="采集博彩公司赔率数据，支持实时更新",
            ),
            ScheduledTask(
                task_id="live_scores_collection",
                name="实时比分采集",
                cron_expression="*/2 * * * *",  # 每2分钟（比赛期间）
                task_function=collect_live_scores,
                dependencies=["fixtures_collection"],
                priority=1,
                max_retries=5,
                timeout=120,
                description="采集比赛实时比分和状态数据",
            ),
            ScheduledTask(
                task_id="feature_calculation",
                name="特征计算",
                cron_expression="0 * * * *",  # 每小时
                task_function=calculate_features,
                dependencies=["fixtures_collection", "odds_collection"],
                priority=3,
                max_retries=3,
                timeout=900,
                description="计算机器学习特征，为预测模型提供数据",
            ),
            ScheduledTask(
                task_id="data_cleanup",
                name="数据清理",
                cron_expression="0 3 * * 0",  # 每周日凌晨3:00
                task_function=cleanup_data,
                priority=5,
                max_retries=2,
                timeout=1800,
                description="清理过期数据，优化数据库性能",
            ),
        ]

        # 注册所有预设任务
        for task in predefined_tasks:
            self.register_task(task)

        logger.info(f"已注册 {len(predefined_tasks)} 个预定义任务")

    def unregister_task(self, task_id: str) -> bool:
        """
        注销调度任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 注销是否成功
        """
        if task_id in self.tasks:
            # 从依赖解析器中移除
            self.dependency_resolver.remove_task(task_id)

            # 从任务列表中移除
            del self.tasks[task_id]

            logger.info(f"任务注销成功: {task_id}")
            return True
        else:
            logger.warning(f"任务不存在，无法注销: {task_id}")
            return False

    def get_ready_tasks(self, current_time: datetime) -> List[ScheduledTask]:
        """
        获取准备执行的任务列表

        Args:
            current_time: 当前时间

        Returns:
            List[ScheduledTask]: 准备执行的任务列表（按优先级排序）
        """
        ready_tasks = []

        for task in self.tasks.values():
            # 检查是否应该执行
            if not task.should_run(current_time):
                continue

            # 检查依赖是否满足
            if not self.dependency_resolver.can_execute(task.task_id, self.tasks):
                logger.debug(f"任务 {task.task_id} 依赖未满足，跳过执行")
                continue

            # 检查重试次数
            if task.retry_count >= task.max_retries:
                logger.warning(f"任务 {task.task_id} 重试次数已达上限，标记为失败")
                self.recovery_handler.handle_task_failure(task, "最大重试次数已达")
                continue

            ready_tasks.append(task)

        # 按优先级排序（数字越小优先级越高）
        ready_tasks.sort(key=lambda t: t.priority)
        return ready_tasks

    def execute_task(self, task: ScheduledTask) -> None:
        """
        执行单个任务

        Args:
            task: 要执行的任务
        """
        if task.is_running:
            logger.warning(f"任务 {task.task_id} 正在执行，跳过")
            return

        logger.info(f"开始执行任务: {task.task_id} - {task.name}")
        task.is_running = True

        try:
            # 通过作业管理器执行任务
            success = self.job_manager.execute_job(
                task_id=task.task_id,
                task_function=task.task_function,
                args=task.args,
                kwargs=task.kwargs,
                timeout=task.timeout,
            )

            if success:
                logger.info(f"任务执行成功: {task.task_id}")
                task.mark_completed(success=True)
            else:
                error_msg = f"任务执行失败: {task.task_id}"
                logger.error(error_msg)
                task.mark_completed(success=False, error=error_msg)

                # 通过恢复处理器处理失败
                self.recovery_handler.handle_task_failure(task, error_msg)

        except Exception as e:
            error_msg = f"任务执行异常: {task.task_id} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            task.mark_completed(success=False, error=error_msg)

            # 通过恢复处理器处理异常
            self.recovery_handler.handle_task_failure(task, error_msg)

    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        logger.info("调度器主循环开始")

        while not self.stop_event.is_set():
            try:
                current_time = datetime.now()

                # 获取准备执行的任务
                ready_tasks = self.get_ready_tasks(current_time)

                if ready_tasks:
                    logger.info(f"发现 {len(ready_tasks)} 个待执行任务")

                    # 控制并发数量
                    running_count = sum(
                        1 for task in self.tasks.values() if task.is_running
                    )
                    available_slots = self.max_concurrent_tasks - running_count

                    # 执行任务（限制并发数）
                    for task in ready_tasks[:available_slots]:
                        # 在单独线程中执行任务
                        task_thread = threading.Thread(
                            target=self.execute_task,
                            args=(task,),
                            name=f"Task-{task.task_id}",
                        )
                        task_thread.daemon = True
                        task_thread.start()

                # 等待下次检查
                self.stop_event.wait(self.check_interval)

            except Exception as e:
                logger.error(f"调度器循环异常: {e}", exc_info=True)
                time.sleep(60)  # 异常时等待1分钟后继续

        logger.info("调度器主循环结束")

    def start(self) -> bool:
        """
        启动调度器

        Returns:
            bool: 启动是否成功
        """
        if self.is_running:
            logger.warning("调度器已在运行")
            return False

        try:
            # 注册预定义任务
            self.register_predefined_tasks()

            # 重置停止事件
            self.stop_event.clear()

            # 启动调度器线程
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, name="TaskScheduler"
            )
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()

            self.is_running = True
            logger.info("任务调度器启动成功")
            return True

        except Exception as e:
            logger.error(f"调度器启动失败: {e}", exc_info=True)
            return False

    def stop(self, timeout: int = 30) -> bool:
        """
        停止调度器

        Args:
            timeout: 等待停止的超时时间（秒）

        Returns:
            bool: 停止是否成功
        """
        if not self.is_running:
            logger.warning("调度器未在运行")
            return True

        try:
            logger.info("正在停止任务调度器...")

            # 设置停止事件
            self.stop_event.set()

            # 等待调度器线程结束
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=timeout)

                if self.scheduler_thread.is_alive():
                    logger.warning("调度器线程未能在超时时间内停止")
                    return False

            self.is_running = False
            logger.info("任务调度器停止成功")
            return True

        except Exception as e:
            logger.error(f"调度器停止失败: {e}", exc_info=True)
            return False

    def get_task_status(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取任务状态信息

        Args:
            task_id: 任务ID，为空时返回所有任务状态

        Returns:
            Dict[str, Any]: 任务状态信息
        """
        if task_id:
            # 返回单个任务状态
            if task_id in self.tasks:
                return self.tasks[task_id].to_dict()
            else:
                return {"error": f"任务不存在: {task_id}"}
        else:
            # 返回所有任务状态
            return {
                "scheduler_status": {
                    "is_running": self.is_running,
                    "total_tasks": len(self.tasks),
                    "running_tasks": sum(
                        1 for task in self.tasks.values() if task.is_running
                    ),
                    "check_interval": self.check_interval,
                    "max_concurrent_tasks": self.max_concurrent_tasks,
                },
                "tasks": {
                    task_id: task.to_dict() for task_id, task in self.tasks.items()
                },
            }

    def update_task_schedule(self, task_id: str, new_cron_expression: str) -> bool:
        """
        更新任务的调度表达式

        Args:
            task_id: 任务ID
            new_cron_expression: 新的cron表达式

        Returns:
            bool: 更新是否成功
        """
        if task_id not in self.tasks:
            logger.error(f"任务不存在，无法更新: {task_id}")
            return False

        try:
            # 验证新的cron表达式
            croniter(new_cron_expression)

            # 更新任务
            task = self.tasks[task_id]
            task.cron_expression = new_cron_expression
            task._update_next_run_time()

            logger.info(f"任务调度表达式更新成功: {task_id} -> {new_cron_expression}")
            return True

        except Exception as e:
            logger.error(f"任务调度表达式更新失败: {task_id} - {e}")
            return False
