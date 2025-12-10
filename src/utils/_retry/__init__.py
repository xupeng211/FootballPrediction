"""重试机制模块 / Retry Mechanism Module.

包含所有重试相关的类和函数.
"""

import asyncio
import functools
import secrets
import time
from collections.abc import Callable
from typing import Optional, TypeVar

T = TypeVar("T")


class RetryConfig:
    """重试配置类."""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = None,
        initial_delay: float = None,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,),
        exceptions: tuple = (Exception,),
        backoff_factor: float = 2.0,
        **kwargs,
    ):
        self.max_attempts = max_attempts

        # 支持多种参数名
        if initial_delay is not None:
            self.initial_delay = initial_delay
            self.delay = initial_delay
            self.base_delay = initial_delay
        elif delay is not None:
            self.initial_delay = delay
            self.delay = delay
            self.base_delay = delay
        else:
            self.initial_delay = base_delay
            self.delay = base_delay
            self.base_delay = base_delay

        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.exceptions = exceptions or retryable_exceptions

        # 支持其他参数
        for key, value in kwargs.items():
            setattr(self, key, value)


class RetryError(Exception):
    """重试失败异常."""


# 策略类和枚举
from enum import Enum


class CircuitState(Enum):
    """熔断器状态."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class BackoffStrategy:
    """退避策略基类."""

    def __init__(self, initial_delay: float = 1.0):
        self.initial_delay = initial_delay

    def get_delay(self, attempt: int) -> float:
        return self.initial_delay


class FixedBackoffStrategy(BackoffStrategy):
    """固定退避策略."""

    def __init__(self, delay: float = 1.0):
        super().__init__(delay)
        self.delay = delay

    def get_delay(self, attempt: int) -> float:
        return self.delay


class LinearBackoffStrategy(BackoffStrategy):
    """线性退避策略."""

    def __init__(self, initial_delay: float = 1.0, increment: float = 0.5):
        super().__init__(initial_delay)
        self.increment = increment

    def get_delay(self, attempt: int) -> float:
        return self.initial_delay + (attempt - 1) * self.increment


class ExponentialBackoffStrategy(BackoffStrategy):
    """指数退避策略."""

    def __init__(self, initial_delay: float = 1.0, multiplier: float = 2.0):
        super().__init__(initial_delay)
        self.multiplier = multiplier

    def get_delay(self, attempt: int) -> float:
        return self.initial_delay * (self.multiplier ** (attempt - 1))


class PolynomialBackoffStrategy(BackoffStrategy):
    """多项式退避策略."""

    def __init__(self, initial_delay: float = 1.0, exponent: float = 2.0):
        super().__init__(initial_delay)
        self.exponent = exponent

    def get_delay(self, attempt: int) -> float:
        return self.initial_delay * (attempt**self.exponent)


class CircuitBreaker:
    """熔断器."""

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


def retry_with_exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
):
    """重试装饰器（同步版本）."""

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
                        if secrets.randbelow(100) / 100 < 0.1:  # 添加抖动
                            delay *= 0.5 + secrets.randbelow(100) / 100
                        time.sleep(delay)

            raise RetryError(
                f"Max attempts ({max_attempts}) exceeded"
            ) from last_exception

        return wrapper

    return decorator


async def async_retry_with_exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
):
    """重试装饰器（异步版本）."""

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
                        if secrets.randbelow(100) / 100 < 0.1:  # 添加抖动
                            delay *= 0.5 + secrets.randbelow(100) / 100
                        await asyncio.sleep(delay)

            raise RetryError(
                f"Max attempts ({max_attempts}) exceeded"
            ) from last_exception

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = None,
    initial_delay: float = None,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    strategy: BackoffStrategy | None = None,
):
    """重试装饰器."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            # 使用提供的延迟或默认值
            current_delay = delay or initial_delay or 1.0

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        break

                    # 计算延迟时间
                    if strategy:
                        sleep_time = strategy.get_delay(attempt)
                    else:
                        sleep_time = current_delay * (backoff_factor ** (attempt - 1))

                    time.sleep(sleep_time)

            raise last_exception

        return wrapper

    return decorator


def retry_async(config: RetryConfig | None = None):
    """异步重试装饰器别名."""
    return async_retry_with_exponential_backoff()


def retry_sync(config: RetryConfig | None = None):
    """同步重试装饰器别名."""
    return retry_with_exponential_backoff()

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
