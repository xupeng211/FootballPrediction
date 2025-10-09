"""
恢复策略
Recovery Strategies

实现各种恢复策略的具体逻辑。
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict

from .models import RecoveryStrategy, TaskFailure

logger = logging.getLogger(__name__)


class BaseRecoveryStrategy(ABC):
    """恢复策略基类"""

    def __init__(self, name: RecoveryStrategy):
        """初始化策略"""
        self.name = name

    @abstractmethod
    def execute(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """
        执行恢复策略

        Args:
            task: 任务对象
            failure: 失败记录
            config: 配置信息

        Returns:
            bool: 恢复是否成功
        """
        pass

    def _check_retry_limit(self, task: Any, config: Dict[str, Any]) -> bool:
        """检查是否达到重试限制"""
        return task.retry_count < config["max_retries"]

    def _schedule_retry(self, task: Any, delay: int = 0) -> None:
        """安排重试"""
        if delay > 0:
            task.next_run_time = datetime.now() + timedelta(seconds=delay)
        else:
            task.next_run_time = datetime.now()
        task.retry_count += 1


class ImmediateRetryStrategy(BaseRecoveryStrategy):
    """立即重试策略"""

    def __init__(self):
        super().__init__(RecoveryStrategy.IMMEDIATE_RETRY)

    def execute(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """执行立即重试"""
        if not self._check_retry_limit(task, config):
            failure.add_recovery_attempt(
                self.name,
                False,
                datetime.now(),
                f"已达到最大重试次数: {config['max_retries']}",
            )
            return False

        self._schedule_retry(task)

        failure.add_recovery_attempt(
            self.name,
            True,
            datetime.now(),
            f"安排立即重试，当前重试次数: {task.retry_count}",
        )

        logger.info(f"安排立即重试: {task.task_id}")
        return True


class ExponentialBackoffStrategy(BaseRecoveryStrategy):
    """指数退避重试策略"""

    def __init__(self):
        super().__init__(RecoveryStrategy.EXPONENTIAL_BACKOFF)

    def execute(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """执行指数退避重试"""
        if not self._check_retry_limit(task, config):
            failure.add_recovery_attempt(
                self.name,
                False,
                datetime.now(),
                f"已达到最大重试次数: {config['max_retries']}",
            )
            return False

        # 计算延迟时间（指数退避）
        base_delay = config["base_delay"]
        backoff_factor = config["backoff_factor"]
        max_delay = config["max_delay"]

        delay = min(base_delay * (backoff_factor**task.retry_count), max_delay)

        self._schedule_retry(task, delay)

        failure.add_recovery_attempt(
            self.name,
            True,
            datetime.now(),
            f"安排 {delay} 秒后重试，当前重试次数: {task.retry_count}",
        )

        logger.info(f"安排指数退避重试: {task.task_id}, 延迟: {delay}秒")
        return True


class FixedDelayStrategy(BaseRecoveryStrategy):
    """固定延迟重试策略"""

    def __init__(self):
        super().__init__(RecoveryStrategy.FIXED_DELAY)

    def execute(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """执行固定延迟重试"""
        if not self._check_retry_limit(task, config):
            failure.add_recovery_attempt(
                self.name,
                False,
                datetime.now(),
                f"已达到最大重试次数: {config['max_retries']}",
            )
            return False

        delay = config["base_delay"]
        self._schedule_retry(task, delay)

        failure.add_recovery_attempt(
            self.name,
            True,
            datetime.now(),
            f"安排 {delay} 秒后重试，当前重试次数: {task.retry_count}",
        )

        logger.info(f"安排固定延迟重试: {task.task_id}, 延迟: {delay}秒")
        return True


class ManualInterventionStrategy(BaseRecoveryStrategy):
    """人工干预策略"""

    def __init__(self):
        super().__init__(RecoveryStrategy.MANUAL_INTERVENTION)

    def execute(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """请求人工干预"""
        # 暂停任务（将下次执行时间设为很远的未来）
        task.next_run_time = datetime.now() + timedelta(days=365)

        failure.add_recovery_attempt(
            self.name,
            True,
            datetime.now(),
            "已请求人工干预，任务已暂停",
        )

        logger.warning(f"请求人工干预: {task.task_id}")
        return True


class SkipAndContinueStrategy(BaseRecoveryStrategy):
    """跳过并继续策略"""

    def __init__(self):
        super().__init__(RecoveryStrategy.SKIP_AND_CONTINUE)

    def execute(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """跳过失败并继续"""
        # 安排下次正常执行
        task.retry_count = 0  # 重置重试次数
        if hasattr(task, '_update_next_run_time'):
            task._update_next_run_time()  # 计算下次执行时间
        else:
            # 如果没有方法，使用默认的cron表达式计算
            task.next_run_time = datetime.now() + timedelta(hours=1)

        failure.add_recovery_attempt(
            self.name,
            True,
            datetime.now(),
            "跳过失败，安排下次正常执行",
        )

        logger.info(f"跳过失败并继续: {task.task_id}")
        return True


class StrategyFactory:
    """策略工厂"""

    _strategies = {
        RecoveryStrategy.IMMEDIATE_RETRY: ImmediateRetryStrategy,
        RecoveryStrategy.EXPONENTIAL_BACKOFF: ExponentialBackoffStrategy,
        RecoveryStrategy.FIXED_DELAY: FixedDelayStrategy,
        RecoveryStrategy.MANUAL_INTERVENTION: ManualInterventionStrategy,
        RecoveryStrategy.SKIP_AND_CONTINUE: SkipAndContinueStrategy,
    }

    @classmethod
    def get_strategy(cls, strategy: RecoveryStrategy) -> BaseRecoveryStrategy:
        """
        获取策略实例

        Args:
            strategy: 策略类型

        Returns:
            BaseRecoveryStrategy: 策略实例
        """
        strategy_class = cls._strategies.get(strategy)
        if not strategy_class:
            raise ValueError(f"未知的恢复策略: {strategy}")

        return strategy_class()

    @classmethod
    def register_strategy(
        cls, strategy: RecoveryStrategy, strategy_class: type
    ) -> None:
        """
        注册新的策略

        Args:
            strategy: 策略枚举
            strategy_class: 策略类
        """
        cls._strategies[strategy] = strategy_class
        logger.info(f"恢复策略已注册: {strategy.value}")