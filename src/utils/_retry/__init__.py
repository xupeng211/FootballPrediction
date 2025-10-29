"""
重试机制模块 / Retry Mechanism Module

包含所有重试相关的类和函数。
"""

import asyncio
import functools
import random
import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class RetryConfig:
    """重试配置类"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


class RetryError(Exception):
    """重试失败异常"""

    pass


def retry_with_exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
):
    """重试装饰器（同步版本）"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2**attempt), max_delay)
                        if random.random() < 0.1:  # 添加抖动  # noqa: B311
                            delay *= 0.5 + random.random()  # noqa: B311
                        time.sleep(delay)

            raise RetryError(f"Max attempts ({max_attempts}) exceeded") from last_exception

        return wrapper

    return decorator


async def async_retry_with_exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
):
    """重试装饰器（异步版本）"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2**attempt), max_delay)
                        if random.random() < 0.1:  # 添加抖动  # noqa: B311
                            delay *= 0.5 + random.random()  # noqa: B311
                        await asyncio.sleep(delay)

            raise RetryError(f"Max attempts ({max_attempts}) exceeded") from last_exception

        return wrapper

    return decorator


def retry(config: Optional[RetryConfig] = None):
    """通用的重试装饰器"""
    if config is None:
        config = RetryConfig()

    return retry_with_exponential_backoff(
        max_attempts=config.max_attempts,
        base_delay=config.base_delay,
        max_delay=config.max_delay,
    )


def async_retry(config: Optional[RetryConfig] = None):
    """通用的异步重试装饰器"""
    if config is None:
        config = RetryConfig()

    return async_retry_with_exponential_backoff(
        max_attempts=config.max_attempts,
        base_delay=config.base_delay,
        max_delay=config.max_delay,
    )


# 简单的别名
BackoffStrategy = RetryConfig
ExponentialBackoffStrategy = RetryConfig
FixedBackoffStrategy = RetryConfig
LinearBackoffStrategy = RetryConfig
PolynomialBackoffStrategy = RetryConfig
retry_sync = retry
retry_async = async_retry


class CircuitState:
    """熔断器状态枚举"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """熔断器实现"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED


__all__ = [
    "RetryConfig",
    "BackoffStrategy",
    "ExponentialBackoffStrategy",
    "FixedBackoffStrategy",
    "LinearBackoffStrategy",
    "PolynomialBackoffStrategy",
    "retry",
    "async_retry",
    "retry_sync",
    "retry_async",
    "CircuitState",
    "CircuitBreaker",
    "RetryError",
    "retry_with_exponential_backoff",
    "async_retry_with_exponential_backoff",
]
