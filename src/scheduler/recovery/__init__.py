"""
恢复处理模块
Recovery Handler Module

提供任务失败恢复和重试功能。
"""

from .alerting import AlertManager
from .classifiers import FailureClassifier
from .handler import RecoveryHandler
from .models import FailureType, RecoveryStrategy, TaskFailure
from .statistics import RecoveryStatistics
from .strategies import (

    ImmediateRetryStrategy,
    ExponentialBackoffStrategy,
    FixedDelayStrategy,
    ManualInterventionStrategy,
    SkipAndContinueStrategy,
    StrategyFactory,
)

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
