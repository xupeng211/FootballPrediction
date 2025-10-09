"""
                from enum import Enum

告警调度器
Alert Scheduler

实现告警系统的后台任务调度功能，从AlertManager中提取调度逻辑。
Extracted from AlertManager to handle background task scheduling logic.
"""


# 尝试从不同位置导入模型
# Import moved to top

try: AlertStatus
except ImportError:
    # Import moved to top

    try: AlertStatus
    except ImportError:
        # 创建基本类型
        from enum import Enum
        from datetime import datetime
        from typing import Any, Dict, Optional

        class AlertStatus(Enum):
            ACTIVE = "active"
            RESOLVED = "resolved"
            SUPPRESSED = "suppressed"
            SILENCED = "silenced"

        class Alert:
            def __init__(self, alert_id: str, title: str, message: str, level: Any, source: str, **kwargs):
                self.alert_id = alert_id
                self.title = title
                self.message = message
                self.level = level
                self.source = source
                self.status = AlertStatus.ACTIVE
                self.created_at = datetime.utcnow()
                self.labels = kwargs.get('labels', {})

            @property
            def type(self):
                class AlertType(Enum):
                    SYSTEM = "system"
                return AlertType.SYSTEM

            @property
            def severity(self):
                return self.level

            @property
            def source(self):
                return getattr(self, '_source', 'unknown')

            def is_resolved(self) -> bool:
                return self.status == AlertStatus.RESOLVED

logger = logging.getLogger(__name__)


class ScheduledTask:
    """
    调度任务
    Scheduled Task

    表示一个可调度的后台任务。
    Represents a schedulable background task.

    Attributes:
        task_id (str): 任务ID / Task ID
        name (str): 任务名称 / Task name
        func (Callable): 执行函数 / Execution function
        interval (timedelta): 执行间隔 / Execution interval
        enabled (bool): 是否启用 / Whether enabled
        created_at (datetime): 创建时间 / Creation time
        last_run (Optional[datetime]): 上次运行时间 / Last run time
        next_run (Optional[datetime]): 下次运行时间 / Next run time
        run_count (int): 运行次数 / Run count
        error_count (int): 错误次数 / Error count
    """

    def __init__(
        self,
        task_id: str,
        name: str,
        func: Callable,
        interval: timedelta,
        enabled: bool = True
    ):
        """
        初始化调度任务
        Initialize Scheduled Task

        Args:
            task_id: 任务ID / Task ID
            name: 任务名称 / Task name
            func: 执行函数 / Execution function
            interval: 执行间隔 / Execution interval
            enabled: 是否启用 / Whether enabled
        """
        self.task_id = task_id
        self.name = name
        self.func = func
        self.interval = interval
        self.enabled = enabled
        self.created_at = datetime.utcnow()
        self.last_run: Optional[datetime] = None
        self.next_run = datetime.utcnow() + interval
        self.run_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.is_running = False

    def should_run(self) -> bool:
        """
        检查是否应该运行
        Check if Should Run

        Returns:
            bool: 是否应该运行 / Whether should run
        """
        if not self.enabled or self.is_running:
            return False

        return datetime.utcnow() >= self.next_run

    async def run(self) -> bool:
        """
        执行任务
        Run Task

        Returns:
            bool: 是否成功 / Whether successful
        """
        if self.is_running:
            return False

        self.is_running = True
        self.last_run = datetime.utcnow()
        self.run_count += 1

        try:
            # 执行任务
            if asyncio.iscoroutinefunction(self.func):
                await self.func()
            else:
                self.func()

            # 计算下次运行时间
            self.next_run = datetime.utcnow() + self.interval
            self.last_error = None

            logger.debug(f"Task {self.task_id} completed successfully")
            return True

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            self.next_run = datetime.utcnow() + self.interval

            logger.error(f"Task {self.task_id} failed: {e}")
            return False

        finally:
            self.is_running = False

    def reset(self):
        """重置任务状态"""
        self.last_run = None
        self.next_run = datetime.utcnow() + self.interval
        self.run_count = 0
        self.error_count = 0
        self.last_error = None
        self.is_running = False

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        Convert to Dictionary

        Returns:
            Dict[str, Any]: 字典表示 / Dictionary representation
        """
        return {
            "task_id": self.task_id,
            "name": self.name,
            "enabled": self.enabled,
            "interval_seconds": self.interval.total_seconds(),
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_error": self.last_error,
            "is_running": self.is_running,
            "created_at": self.created_at.isoformat()
        }


class AlertScheduler:
    """
    告警调度器
    Alert Scheduler

    负责管理和执行告警系统的后台任务。
    Manages and executes background tasks for the alert system.

    Attributes:
        tasks (Dict[str, ScheduledTask]): 调度任务 / Scheduled tasks
        running (bool): 是否运行中 / Whether running
        background_tasks (Set[asyncio.Task]): 后台任务集合 / Background tasks set
        logger: 日志记录器 / Logger
    """

    def __init__(self):
        """初始化告警调度器"""
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.background_tasks: Set[asyncio.Task] = set()
        self.logger = logging.getLogger(__name__)
        self._scheduler_task: Optional[asyncio.Task] = None

    def add_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        interval: timedelta,
        enabled: bool = True
    ) -> ScheduledTask:
        """
        添加调度任务
        Add Scheduled Task

        Args:
            task_id: 任务ID / Task ID
            name: 任务名称 / Task name
            func: 执行函数 / Execution function
            interval: 执行间隔 / Execution interval
            enabled: 是否启用 / Whether enabled

        Returns:
            ScheduledTask: 创建的任务 / Created task
        """
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id} already exists")

        task = ScheduledTask(task_id, name, func, interval, enabled)
        self.tasks[task_id] = task

        self.logger.info(f"Added scheduled task: {task_id}")
        return task

    def remove_task(self, task_id: str):
        """
        移除调度任务
        Remove Scheduled Task

        Args:
            task_id: 任务ID / Task ID
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.logger.info(f"Removed scheduled task: {task_id}")

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """
        获取调度任务
        Get Scheduled Task

        Args:
            task_id: 任务ID / Task ID

        Returns:
            Optional[ScheduledTask]: 调度任务 / Scheduled task
        """
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[ScheduledTask]:
        """
        获取所有调度任务
        Get All Scheduled Tasks

        Returns:
            List[ScheduledTask]: 任务列表 / List of tasks
        """
        return list(self.tasks.values())

    def get_enabled_tasks(self) -> List[ScheduledTask]:
        """
        获取启用的调度任务
        Get Enabled Scheduled Tasks

        Returns:
            List[ScheduledTask]: 启用的任务列表 / List of enabled tasks
        """
        return [task for task in self.tasks.values() if task.enabled]

    def enable_task(self, task_id: str):
        """
        启用任务
        Enable Task

        Args:
            task_id: 任务ID / Task ID
        """
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self.logger.info(f"Enabled task: {task_id}")

    def disable_task(self, task_id: str):
        """
        禁用任务
        Disable Task

        Args:
            task_id: 任务ID / Task ID
        """
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self.logger.info(f"Disabled task: {task_id}")

    def reset_task(self, task_id: str):
        """
        重置任务
        Reset Task

        Args:
            task_id: 任务ID / Task ID
        """
        if task_id in self.tasks:
            self.tasks[task_id].reset()
            self.logger.info(f"Reset task: {task_id}")

    async def start(self):
        """
        启动调度器
        Start Scheduler

        启动主调度循环。
        Starts the main scheduling loop.
        """
        if self.running:
            return

        self.running = True
        self.logger.info("Starting Alert Scheduler")

        # 启动主调度任务
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """
        停止调度器
        Stop Scheduler

        停止所有后台任务。
        Stops all background tasks.
        """
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping Alert Scheduler")

        # 取消主调度任务
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None

        # 取消所有后台任务
        for task in self.background_tasks:
            task.cancel()

        # 等待任务完成
        if self.background_tasks:
            await asyncio.gather(
                *self.background_tasks,
                return_exceptions=True
            )
            self.background_tasks.clear()

        self.logger.info("Alert Scheduler stopped")

    async def _scheduler_loop(self):
        """主调度循环"""
        while self.running:
            try:
                # 检查需要运行的任务
                tasks_to_run = [
                    task for task in self.tasks.values()
                    if task.should_run()
                ]

                # 并发执行任务
                if tasks_to_run:
                    for task in tasks_to_run:
                        # 创建任务
                        background_task = asyncio.create_task(self._run_task_safely(task))
                        self.background_tasks.add(background_task)
                        background_task.add_done_callback(self.background_tasks.discard)

                # 等待下次检查（每秒检查一次）
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)  # 出错时等待5秒

    async def _run_task_safely(self, task: ScheduledTask):
        """安全运行任务"""
        try:
            await task.run()
        except Exception as e:
            self.logger.error(f"Unexpected error in task {task.task_id}: {e}")

    async def run_task_now(self, task_id: str) -> bool:
        """
        立即运行指定任务
        Run Task Immediately

        Args:
            task_id: 任务ID / Task ID

        Returns:
            bool: 是否成功 / Whether successful
        """
        task = self.tasks.get(task_id)
        if not task:
            self.logger.warning(f"Task not found: {task_id}")
            return False

        if task.is_running:
            self.logger.warning(f"Task {task_id} is already running")
            return False

        return await task.run()

    def get_task_statistics(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务统计信息
        Get Task Statistics

        Args:
            task_id: 任务ID / Task ID

        Returns:
            Optional[Dict[str, Any]]: 统计信息 / Statistics
        """
        task = self.tasks.get(task_id)
        if not task:
            return None

        return task.to_dict()

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取调度器统计信息
        Get Scheduler Statistics

        Returns:
            Dict[str, Any]: 统计信息 / Statistics
        """
        total_tasks = len(self.tasks)
        enabled_tasks = len(self.get_enabled_tasks())
        running_tasks = len([t for t in self.tasks.values() if t.is_running])

        total_runs = sum(task.run_count for task in self.tasks.values())
        total_errors = sum(task.error_count for task in self.tasks.values())

        # 计算最近运行的任务
        recent_tasks = [
            {
                "task_id": task.task_id,
                "name": task.name,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "run_count": task.run_count,
                "error_count": task.error_count,
                "enabled": task.enabled
            }
            for task in sorted(
                self.tasks.values(),
                key=lambda x: x.last_run or datetime.min,
                reverse=True
            )[:5]
        ]

        return {
            "scheduler": {
                "running": self.running,
                "background_tasks": len(self.background_tasks)
            },
            "tasks": {
                "total": total_tasks,
                "enabled": enabled_tasks,
                "disabled": total_tasks - enabled_tasks,
                "running": running_tasks
            },
            "execution": {
                "total_runs": total_runs,
                "total_errors": total_errors,
                "success_rate": (total_runs - total_errors) / total_runs if total_runs > 0 else 1.0
            },
            "recent_tasks": recent_tasks
        }


class AlertTaskFactory:
    """
    告警任务工厂
    Alert Task Factory

    提供常用的告警任务创建方法。
    Provides common alert task creation methods.
    """

    @staticmethod
    def create_periodic_rule_evaluation_task(
        rule_engine,
        update_context_func: Callable,
        evaluation_interval: int = 60
    ) -> Callable:
        """
        创建定期规则评估任务
        Create Periodic Rule Evaluation Task

        Args:
            rule_engine: 规则引擎实例 / Rule engine instance
            update_context_func: 更新上下文函数 / Update context function
            evaluation_interval: 评估间隔（秒） / Evaluation interval (seconds)

        Returns:
            Callable: 任务函数 / Task function
        """
        async def periodic_rule_evaluation():
            try:
                # 更新上下文数据
                await update_context_func()

                # 评估所有规则
                results = await rule_engine.evaluate_all_rules()

                # 处理触发的规则
                triggered_count = 0
                for rule_id, triggered in results.items():
                    if triggered:
                        triggered_count += 1

                logger.info(f"Rule evaluation completed: {triggered_count} rules triggered")

            except Exception as e:
                logger.error(f"Error in periodic rule evaluation: {e}")

        return periodic_rule_evaluation

    @staticmethod
    def create_periodic_cleanup_task(
        cleanup_func: Callable,
        cleanup_interval: int = 3600
    ) -> Callable:
        """
        创建定期清理任务
        Create Periodic Cleanup Task

        Args:
            cleanup_func: 清理函数 / Cleanup function
            cleanup_interval: 清理间隔（秒） / Cleanup interval (seconds)

        Returns:
            Callable: 任务函数 / Task function
        """
        async def periodic_cleanup():
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    cleanup_func()

                logger.info("Periodic cleanup completed")

            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

        return periodic_cleanup

    @staticmethod
    def create_alert_cleanup_task(
        alerts_dict: Dict[str, Alert],
        retention_hours: int = 24
    ) -> Callable:
        """
        创建告警清理任务
        Create Alert Cleanup Task

        Args:
            alerts_dict: 告警字典 / Alerts dictionary
            retention_hours: 保留时间（小时） / Retention time (hours)

        Returns:
            Callable: 任务函数 / Task function
        """
        def cleanup_resolved_alerts():
            retention_time = timedelta(hours=retention_hours)
            now = datetime.utcnow()


            to_remove = []
            for alert_id, alert in alerts_dict.items():
                if alert.is_resolved() and alert.resolved_at:
                    if now - alert.resolved_at > retention_time:
                        to_remove.append(alert_id)

            for alert_id in to_remove:
                del alerts_dict[alert_id]
                logger.debug(f"Cleaned up resolved alert: {alert_id}")

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} resolved alerts")

        return cleanup_resolved_alerts