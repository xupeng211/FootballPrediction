"""
恢复处理模块
Recovery Handler Module

提供任务失败恢复和重试功能。
"""

from .models import FailureType, RecoveryStrategy, TaskFailure
from .handler import RecoveryHandler
from .strategies import (
    ImmediateRetryStrategy,
    ExponentialBackoffStrategy,
    FixedDelayStrategy,
    ManualInterventionStrategy,
    SkipAndContinueStrategy,
    StrategyFactory,
)
from .classifiers import FailureClassifier
from .alerting import AlertManager
from .statistics import RecoveryStatistics

__all__ = [
    # Models
    "FailureType",
    "RecoveryStrategy",
    "TaskFailure",
    # Main handler
    "RecoveryHandler",
    # Strategies
    "ImmediateRetryStrategy",
    "ExponentialBackoffStrategy",
    "FixedDelayStrategy",
    "ManualInterventionStrategy",
    "SkipAndContinueStrategy",
    "StrategyFactory",
    # Support components
    "FailureClassifier",
    "AlertManager",
    "RecoveryStatistics",
]