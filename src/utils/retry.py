"""
重试机制（向后兼容）
Retry Mechanism (Backward Compatible)

为了保持向后兼容性，此文件重新导出新的模块化重试系统。

Provides backward compatible exports for the modular retry system.
"""

# 重新导出主要类和函数
from ._retry import (
    RetryConfig,
    BackoffStrategy,
    ExponentialBackoffStrategy,
    FixedBackoffStrategy,
    LinearBackoffStrategy,
    PolynomialBackoffStrategy,
    retry,
    retry_async,
    retry_sync,
    CircuitState,
    CircuitBreaker,
)

# 导出所有符号
__all__ = [
    "RetryConfig",
    "BackoffStrategy",
    "ExponentialBackoffStrategy",
    "FixedBackoffStrategy",
    "LinearBackoffStrategy",
    "PolynomialBackoffStrategy",
    "retry",
    "retry_async",
    "retry_sync",
    "CircuitState",
    "CircuitBreaker",
]