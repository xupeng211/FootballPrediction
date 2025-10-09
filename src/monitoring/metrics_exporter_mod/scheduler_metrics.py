"""

"""




    """调度器指标记录器

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


from datetime import datetime

调度器指标记录器 / Scheduler Metrics Recorder
负责记录调度器相关的各项指标。
logger = logging.getLogger(__name__)
class SchedulerMetrics:
    负责记录调度任务的延迟、执行时间、失败次数等指标。
    def __init__(self, metrics_defs):
        初始化调度器指标记录器
        Args:
            metrics_defs: 指标定义实例
        self.metrics = metrics_defs
    def record_task(
        self,
        task_name: str,
        scheduled_time: datetime,
        actual_start_time: datetime,
        duration: float,
        success: bool,
        failure_reason: Optional[str] = None,
    ) -> None:
        记录调度任务指标
        Args:
            task_name: 任务名称
            scheduled_time: 计划执行时间
            actual_start_time: 实际开始时间
            duration: 执行耗时（秒）
            success: 是否成功
            failure_reason: 失败原因（如果失败）
        try:
            # 计算延迟时间
            delay_seconds = (actual_start_time - scheduled_time).total_seconds()
            self.metrics.scheduler_task_delay.labels(
                task_name=task_name
            ).set(delay_seconds)
            # 记录执行耗时
            self.metrics.scheduler_task_duration.labels(
                task_name=task_name
            ).observe(duration)
            # 记录失败（如果失败）
            if not success and failure_reason:
                self.metrics.scheduler_task_failures.labels(
                    task_name=task_name,
                    failure_reason=failure_reason
                ).inc()
        except Exception as e:
            logger.error(f"记录调度任务指标失败: {e}")
    def record_task_simple(
        self,
        task_name: str,
        status: str,
        duration: float,
    ) -> None:
        记录调度任务指标 - 简化接口
        Args:
            task_name: 任务名称
            status: 任务状态 ("success" 或 "failed")
            duration: 执行耗时（秒）
        success = status == "success"
        failure_reason = None if success else "test_failure"
        # 使用当前时间作为计划时间
        now = datetime.now()
        self.record_task(
            task_name=task_name,
            scheduled_time=now,
            actual_start_time=now,
            duration=duration,
            success=success,
            failure_reason=failure_reason,
        )
    def record_delay(
        self,
        task_name: str,
        delay_seconds: float,
    ) -> None:
        记录调度任务延迟
        Args:
            task_name: 任务名称
            delay_seconds: 延迟时间（秒）
        try:
            self.metrics.scheduler_task_delay.labels(
                task_name=task_name
            ).set(delay_seconds)
        except Exception as e:
            logger.error(f"记录调度延迟指标失败: {e}")
    def record_failure(
        self,
        task_name: str,
        failure_reason: str,
    ) -> None:
        记录调度任务失败
        Args:
            task_name: 任务名称
            failure_reason: 失败原因
        try:
            self.metrics.scheduler_task_failures.labels(
                task_name=task_name,
                failure_reason=failure_reason
            ).inc()
        except Exception as e:
            logger.error(f"记录调度失败指标失败: {e}")
    def record_batch(
        self,
        tasks: list,
    ) -> None:
        批量记录调度任务指标
        Args:
            tasks: 任务记录列表，每个记录包含任务信息
        for task in tasks:
            self.record_task(**task)