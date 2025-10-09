"""
恢复处理模型
Recovery Handler Models

定义失败和恢复相关的数据模型。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


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
    EXPONENTIAL_BACKOFF = "exponential_backoff"
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
        context: Dict[str, Any] | None = None,
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
        self.recovery_attempts: List[Dict[str, Any]] = []

    def add_recovery_attempt(
        self,
        strategy: RecoveryStrategy,
        success: bool,
        attempt_time: datetime,
        details: str | None = None,
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

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"TaskFailure({self.task_id}, "
            f"type={self.failure_type.value}, "
            f"retries={self.retry_count})"
        )