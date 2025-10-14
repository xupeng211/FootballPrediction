from typing import Any, Dict, List, Optional, Union
"""
恢复处理器

负责处理任务失败重试、错误恢复、告警通知等功能。
实现智能重试策略、错误分类处理、恢复机制等。

基于 DATA_DESIGN.md 第3节调度策略设计。
"""

import logging
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """失败类型枚举"""

    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    DATA_ERROR = "data_error"
    RESOURCE_ERROR = "resource_error"
    PERMISSION_ERROR = "permission_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """恢复策略枚举"""

    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backof"
    FIXED_DELAY = "fixed_delay"
    MANUAL_INTERVENTION = "manual_intervention"
    SKIP_AND_CONTINUE = "skip_and_continue"


class TaskFailure:
    """任务失败记录类"""

    def __init__(
        self,
        task_id: str,
        failure_time: datetime,
        failure_type: FailureType,
        error_message: str,
        retry_count: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化任务失败记录

        Args:
            task_id: 任务ID
            failure_time: 失败时间
            failure_type: 失败类型
            error_message: 错误消息
            retry_count: 当前重试次数
            context: 失败上下文信息
        """
        self.task_id = task_id
        self.failure_time = failure_time
        self.failure_type = failure_type
        self.error_message = error_message
        self.retry_count = retry_count
        self.context = context or {}
        self.recovery_attempts: List[Dict[str, Any] = []

    def add_recovery_attempt(
        self,
        strategy: RecoveryStrategy,
        success: bool,
        attempt_time: datetime,
        details: Optional[str] = None,
    ) -> None:
        """
        添加恢复尝试记录

        Args:
            strategy: 使用的恢复策略
            success: 是否成功
            attempt_time: 尝试时间
            details: 详细信息
        """
        self.recovery_attempts.append(
            {
                "strategy": strategy.value,
                "success": success,
                "attempt_time": attempt_time.isoformat(),
                "details": details,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "failure_time": self.failure_time.isoformat(),
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "context": self.context,
            "recovery_attempts": self.recovery_attempts,
        }


class RecoveryHandler:
    """
    恢复处理器主类

    负责处理任务失败和恢复，提供以下功能：
    - 失败分类和分析
    - 智能重试策略
    - 错误恢复机制
    - 告警通知
    - 失败统计和分析
    """

    def __init__(self):
        """初始化恢复处理器"""
        self.failure_history: List[TaskFailure] = []
        self.failure_patterns: Dict[str, List[FailureType] = {}
        self.recovery_configs = self._init_recovery_configs()
        self.alert_handlers: List[Callable] = []

        # 统计信息
        self.total_failures = 0
        self.successful_recoveries = 0
        self.failed_recoveries = 0

        logger.info("恢复处理器初始化完成")

    def _init_recovery_configs(self) -> Dict[str, Any][FailureType, Dict[str, Any]:
        """
        初始化恢复配置

        Returns:
            Dict[str, Any][FailureType, Dict[str, Any]: 失败类型对应的恢复配置
        """
        return {
            FailureType.TIMEOUT: {
                "strategy": RecoveryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 3,
                "base_delay": 60,  # 基础延迟（秒）
                "max_delay": 300,  # 最大延迟（秒）
                "backoff_factor": 2.0,
                "alert_threshold": 2,  # 重试几次后发送告警
            },
            FailureType.CONNECTION_ERROR: {
                "strategy": RecoveryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 5,
                "base_delay": 30,
                "max_delay": 600,
                "backoff_factor": 1.5,
                "alert_threshold": 3,
            },
            FailureType.DATA_ERROR: {
                "strategy": RecoveryStrategy.FIXED_DELAY,
                "max_retries": 2,
                "base_delay": 120,
                "alert_threshold": 1,
            },
            FailureType.RESOURCE_ERROR: {
                "strategy": RecoveryStrategy.EXPONENTIAL_BACKOFF,
                "max_retries": 4,
                "base_delay": 180,
                "max_delay": 900,
                "backoff_factor": 2.0,
                "alert_threshold": 2,
            },
            FailureType.PERMISSION_ERROR: {
                "strategy": RecoveryStrategy.MANUAL_INTERVENTION,
                "max_retries": 0,
                "alert_threshold": 0,
            },
            FailureType.UNKNOWN_ERROR: {
                "strategy": RecoveryStrategy.FIXED_DELAY,
                "max_retries": 2,
                "base_delay": 300,
                "alert_threshold": 1,
            },
        }

    def handle_task_failure(self, task: Any, error_message: str) -> bool:
        """
        处理任务失败

        Args:
            task: 失败的任务对象
            error_message: 错误消息

        Returns:
            bool: 是否成功处理失败
        """
        try:
            # 分析失败类型
            failure_type = self._classify_failure(error_message)

            # 创建失败记录
            failure = TaskFailure(
                task_id=task.task_id,
                failure_time=datetime.now(),
                failure_type=failure_type,
                error_message=error_message,
                retry_count=task.retry_count,
                context={
                    "task_name": task.name,
                    "cron_expression": task.cron_expression,
                    "priority": task.priority,
                    "timeout": task.timeout,
                },
            )

            # 添加到失败历史
            self.failure_history.append(failure)
            self.total_failures += 1

            # 更新失败模式
            self._update_failure_patterns(task.task_id, failure_type)

            # 执行恢复策略
            recovery_success = self._execute_recovery_strategy(task, failure)

            if recovery_success:
                self.successful_recoveries += 1
            else:
                self.failed_recoveries += 1

            # 检查是否需要发送告警
            self._check_and_send_alerts(task, failure)

            logger.info(
                f"任务失败处理完成: {task.task_id}, 恢复{'成功' if recovery_success else '失败'}"
            )
            return recovery_success

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"处理任务失败时发生异常: {task.task_id} - {e}")
            return False

    def _classify_failure(self, error_message: str) -> FailureType:
        """
        分类失败类型

        Args:
            error_message: 错误消息

        Returns:
            FailureType: 失败类型
        """
        error_lower = error_message.lower()

        # 超时错误
        if any(keyword in error_lower for keyword in ["timeout", "time out", "超时"]):
            return FailureType.TIMEOUT

        # 连接错误
        if any(
            keyword in error_lower
            for keyword in [
                "connection",
                "connect",
                "network",
                "socket",
                "连接",
                "网络",
                "unreachable",
                "refused",
            ]
        ):
            return FailureType.CONNECTION_ERROR

        # 数据错误
        if any(
            keyword in error_lower
            for keyword in [
                "data",
                "parse",
                "format",
                "json",
                "xml",
                "数据",
                "格式",
                "解析",
                "invalid",
            ]
        ):
            return FailureType.DATA_ERROR

        # 资源错误
        if any(
            keyword in error_lower
            for keyword in [
                "memory",
                "disk",
                "space",
                "resource",
                "内存",
                "磁盘",
                "空间",
                "资源",
            ]
        ):
            return FailureType.RESOURCE_ERROR

        # 权限错误
        if any(
            keyword in error_lower
            for keyword in [
                "permission",
                "access",
                "auth",
                "forbidden",
                "权限",
                "访问",
                "认证",
                "禁止",
            ]
        ):
            return FailureType.PERMISSION_ERROR

        # 未知错误
        return FailureType.UNKNOWN_ERROR

    def _update_failure_patterns(self, task_id: str, failure_type: FailureType) -> None:
        """
        更新失败模式

        Args:
            task_id: 任务ID
            failure_type: 失败类型
        """
        if task_id not in self.failure_patterns:
            self.failure_patterns[task_id] = []

        self.failure_patterns[task_id].append(failure_type)

        # 保留最近10次失败记录
        if len(self.failure_patterns[task_id]) > 10:
            self.failure_patterns[task_id] = self.failure_patterns[task_id][-10:]

    def _execute_recovery_strategy(self, task: Any, failure: TaskFailure) -> bool:
        """
        执行恢复策略

        Args:
            task: 任务对象
            failure: 失败记录

        Returns:
            bool: 恢复是否成功
        """
        _config = self.recovery_configs[failure.failure_type]
        strategy = config["strategy"]

        logger.info(f"执行恢复策略: {task.task_id}, 策略: {strategy.value}")

        try:
            if strategy == RecoveryStrategy.IMMEDIATE_RETRY:
                return self._immediate_retry(task, failure, config)

            elif strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                return self._exponential_backoff_retry(task, failure, config)

            elif strategy == RecoveryStrategy.FIXED_DELAY:
                return self._fixed_delay_retry(task, failure, config)

            elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
                return self._request_manual_intervention(task, failure, config)

            elif strategy == RecoveryStrategy.SKIP_AND_CONTINUE:
                return self._skip_and_continue(task, failure, config)

            else:
                logger.warning(f"未知的恢复策略: {strategy}")
                return False

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"执行恢复策略失败: {task.task_id} - {e}")
            failure.add_recovery_attempt(
                strategy, False, datetime.now(), f"策略执行异常: {str(e)}"
            )
            return False

    def _immediate_retry(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """
        立即重试

        Args:
            task: 任务对象
            failure: 失败记录
            config: 配置信息

        Returns:
            bool: 重试是否成功安排
        """
        if task.retry_count >= config["max_retries"]:
            failure.add_recovery_attempt(
                RecoveryStrategy.IMMEDIATE_RETRY,
                False,
                datetime.now(),
                f"已达到最大重试次数: {config['max_retries']}",
            )
            return False

        # 安排立即重试（通过重置next_run_time）
        task.next_run_time = datetime.now()
        task.retry_count += 1

        failure.add_recovery_attempt(
            RecoveryStrategy.IMMEDIATE_RETRY,
            True,
            datetime.now(),
            f"安排立即重试，当前重试次数: {task.retry_count}",
        )

        logger.info(f"安排立即重试: {task.task_id}")
        return True

    def _exponential_backoff_retry(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """
        指数退避重试

        Args:
            task: 任务对象
            failure: 失败记录
            config: 配置信息

        Returns:
            bool: 重试是否成功安排
        """
        if task.retry_count >= config["max_retries"]:
            failure.add_recovery_attempt(
                RecoveryStrategy.EXPONENTIAL_BACKOFF,
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

        # 安排延迟重试
        task.next_run_time = datetime.now() + timedelta(seconds=delay)
        task.retry_count += 1

        failure.add_recovery_attempt(
            RecoveryStrategy.EXPONENTIAL_BACKOFF,
            True,
            datetime.now(),
            f"安排 {delay} 秒后重试，当前重试次数: {task.retry_count}",
        )

        logger.info(f"安排指数退避重试: {task.task_id}, 延迟: {delay}秒")
        return True

    def _fixed_delay_retry(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """
        固定延迟重试

        Args:
            task: 任务对象
            failure: 失败记录
            config: 配置信息

        Returns:
            bool: 重试是否成功安排
        """
        if task.retry_count >= config["max_retries"]:
            failure.add_recovery_attempt(
                RecoveryStrategy.FIXED_DELAY,
                False,
                datetime.now(),
                f"已达到最大重试次数: {config['max_retries']}",
            )
            return False

        # 固定延迟
        delay = config["base_delay"]

        # 安排延迟重试
        task.next_run_time = datetime.now() + timedelta(seconds=delay)
        task.retry_count += 1

        failure.add_recovery_attempt(
            RecoveryStrategy.FIXED_DELAY,
            True,
            datetime.now(),
            f"安排 {delay} 秒后重试，当前重试次数: {task.retry_count}",
        )

        logger.info(f"安排固定延迟重试: {task.task_id}, 延迟: {delay}秒")
        return True

    def _request_manual_intervention(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """
        请求人工干预

        Args:
            task: 任务对象
            failure: 失败记录
            config: 配置信息

        Returns:
            bool: 请求是否成功发送
        """
        # 暂停任务（将下次执行时间设为很远的未来）
        task.next_run_time = datetime.now() + timedelta(days=365)

        failure.add_recovery_attempt(
            RecoveryStrategy.MANUAL_INTERVENTION,
            True,
            datetime.now(),
            "已请求人工干预，任务已暂停",
        )

        # 发送紧急告警
        self._send_alert(
            level="CRITICAL",
            message=f"任务 {task.task_id} 需要人工干预",
            details={
                "task_id": task.task_id,
                "failure_type": failure.failure_type.value,
                "error_message": failure.error_message,
                "action_required": "请检查任务配置和系统状态",
            },
        )

        logger.warning(f"请求人工干预: {task.task_id}")
        return True

    def _skip_and_continue(
        self, task: Any, failure: TaskFailure, config: Dict[str, Any]
    ) -> bool:
        """
        跳过并继续

        Args:
            task: 任务对象
            failure: 失败记录
            config: 配置信息

        Returns:
            bool: 是否成功安排下次执行
        """
        # 安排下次正常执行
        task.retry_count = 0  # 重置重试次数
        task._update_next_run_time()  # 计算下次执行时间

        failure.add_recovery_attempt(
            RecoveryStrategy.SKIP_AND_CONTINUE,
            True,
            datetime.now(),
            "跳过失败，安排下次正常执行",
        )

        logger.info(f"跳过失败并继续: {task.task_id}")
        return True

    def _check_and_send_alerts(self, task: Any, failure: TaskFailure) -> None:
        """
        检查并发送告警

        Args:
            task: 任务对象
            failure: 失败记录
        """
        _config = self.recovery_configs[failure.failure_type]
        alert_threshold = config["alert_threshold"]

        # 检查是否达到告警阈值
        if task.retry_count >= alert_threshold:
            self._send_alert(
                level="WARNING",
                message=f"任务 {task.task_id} 连续失败 {task.retry_count} 次",
                details={
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "failure_type": failure.failure_type.value,
                    "error_message": failure.error_message,
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries,
                },
            )

        # 检查失败模式
        self._check_failure_patterns(task.task_id)

    def _check_failure_patterns(self, task_id: str) -> None:
        """
        检查失败模式

        Args:
            task_id: 任务ID
        """
        if task_id not in self.failure_patterns:
            return

        recent_failures = self.failure_patterns[task_id]

        # 检查是否有重复的失败类型
        if len(recent_failures) >= 3:
            last_three = recent_failures[-3:]
            if len(set(last_three)) == 1:  # 连续三次同类型失败
                self._send_alert(
                    level="HIGH",
                    message=f"任务 {task_id} 连续发生 {last_three[0].value} 类型失败",
                    details={
                        "task_id": task_id,
                        "pattern": "连续同类型失败",
                        "failure_type": last_three[0].value,
                        "count": 3,
                    },
                )

    def _send_alert(self, level: str, message: str, details: Dict[str, Any]) -> None:
        """
        发送告警

        Args:
            level: 告警级别
            message: 告警消息
            details: 详细信息
        """
        alert_data = {
            "level": level,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "component": "scheduler",
        }

        # 记录告警日志
        logger.warning(f"发送告警: {level} - {message}")

        # 调用注册的告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert_data)
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                logger.error(f"告警处理器执行失败: {e}")

    def register_alert_handler(self, handler: Callable[[Dict[str, Any], None]) -> None:
        """
        注册告警处理器

        Args:
            handler: 告警处理函数
        """
        self.alert_handlers.append(handler)
        logger.info(f"告警处理器已注册: {handler.__name__}")

    def get_failure_statistics(self) -> Dict[str, Any]:
        """
        获取失败统计信息

        Returns:
            Dict[str, Any]: 失败统计信息
        """
        # 按失败类型统计
        failure_by_type: Dict[str, int] = {}
        for failure in self.failure_history:
            failure_type = failure.failure_type.value
            failure_by_type[failure_type] = (
                failure_by_type.get(str(failure_type), 0) + 1
            )

        # 按任务统计
        failure_by_task: Dict[str, int] = {}
        for failure in self.failure_history:
            task_id = failure.task_id
            failure_by_task[task_id] = failure_by_task.get(str(task_id), 0) + 1

        # 最近24小时统计
        recent_failures = [
            f
            for f in self.failure_history
            if datetime.now() - f.failure_time <= timedelta(hours=24)
        ]

        return {
            "total_failures": self.total_failures,
            "successful_recoveries": self.successful_recoveries,
            "failed_recoveries": self.failed_recoveries,
            "recovery_success_rate": (
                self.successful_recoveries / max(self.total_failures, 1) * 100
            ),
            "failure_by_type": failure_by_type,
            "failure_by_task": failure_by_task,
            "recent_24h_failures": len(recent_failures),
            "failure_patterns": {
                task_id: [ft.value for ft in failures]
                for task_id, failures in self.failure_patterns.items()
            },
        }

    def get_recent_failures(self, limit: int = 20) -> List[Dict[str, Any]:
        """
        获取最近的失败记录

        Args:
            limit: 返回记录数量限制

        Returns:
            List[Dict[str, Any]: 最近的失败记录
        """
        recent_failures = sorted(
            self.failure_history, key=lambda f: f.failure_time, reverse=True
        )[:limit]

        return [failure.to_dict() for failure in recent_failures]

    def clear_old_failures(self, days_to_keep: int = 30) -> int:
        """
        清理旧的失败记录

        Args:
            days_to_keep: 保留天数

        Returns:
            int: 清理的记录数量
        """
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        old_count = len(self.failure_history)

        self.failure_history = [
            f for f in self.failure_history if f.failure_time > cutoff_time
        ]

        cleared_count = old_count - len(self.failure_history)
        logger.info(f"清理了 {cleared_count} 条旧失败记录")

        return cleared_count
