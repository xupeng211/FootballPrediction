"""
重试机制模块 / Retry Mechanism Module

包含所有重试相关的类和函数.
"""

import asyncio
import functools
import secrets
import time
from collections.abc import Callable
from typing import TypeVar

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
        delay: float = None,  # 兼容性参数，映射到base_delay
        backoff_strategy: str = None,  # 退避策略参数
    ):
        self.max_attempts = max_attempts
        # 支持delay参数以保持向后兼容
        if delay is not None:
            self.base_delay = delay
        else:
            self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.backoff_strategy = backoff_strategy


class RetryError(Exception):
    """重试失败异常"""


class FixedBackoffStrategy:
    """固定退避策略"""

    def __init__(self, delay: float = 1.0):
        self.delay = delay


class LinearBackoffStrategy:
    """线性退避策略"""

    def __init__(self, initial_delay: float = 1.0, increment: float = 0.5):
        self.initial_delay = initial_delay
        self.increment = increment
        self.delay = initial_delay  # 添加delay属性以兼容测试

    def get_delay(self, attempt: int = 0) -> float:
        """获取指定尝试次数的延迟时间"""
        return self.initial_delay + (self.increment * attempt)


class ExponentialBackoffStrategy:
    """指数退避策略"""

    def __init__(self, initial_delay: float = 1.0, multiplier: float = 2.0):
        self.initial_delay = initial_delay
        self.multiplier = multiplier
        self.delay = initial_delay  # 添加delay属性以兼容测试

    def get_delay(self, attempt: int = 0) -> float:
        """获取指定尝试次数的延迟时间"""
        return self.initial_delay * (self.multiplier**attempt)


class PolynomialBackoffStrategy:
    """多项式退避策略"""

    def __init__(self, initial_delay: float = 1.0, exponent: float = 2.0):
        self.initial_delay = initial_delay
        self.exponent = exponent
        self.delay = initial_delay  # 添加delay属性以兼容测试

    def get_delay(self, attempt: int = 0) -> float:
        """获取指定尝试次数的延迟时间"""
        return (
            self.initial_delay * (attempt**self.exponent)
            if attempt > 0
            else self.initial_delay
        )


class BackoffStrategy:
    """退避策略基类"""

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
                        if secrets.randbelow(100) / 100 < 0.1:  # 添加抖动
                            delay *= 0.5 + secrets.randbelow(100) / 100
                        await asyncio.sleep(delay)

            raise RetryError(
                f"Max attempts ({max_attempts}) exceeded"
            ) from last_exception

        return wrapper

    return decorator


def retry(
    config_or_max_attempts=None,
    delay=None,
    max_attempts=None,
    base_delay=None,
    **kwargs,
):
    """通用的重试装饰器（支持多种调用方式）"""

    # 支持旧接口：retry(max_attempts=3, delay=0.01)
    if config_or_max_attempts is None or isinstance(
        config_or_max_attempts, (int, float)
    ):
        max_attempts = (
            config_or_max_attempts if config_or_max_attempts is not None else 3
        )
        base_delay = delay if delay is not None else 1.0
        return retry_with_exponential_backoff(
            max_attempts=int(max_attempts),
            base_delay=base_delay,
            max_delay=kwargs.get("max_delay", 60.0),
            exceptions=kwargs.get("exceptions", (Exception,)),
        )

    # 支持新接口：retry(RetryConfig(...))
    if isinstance(config_or_max_attempts, RetryConfig):
        config = config_or_max_attempts
        return retry_with_exponential_backoff(
            max_attempts=config.max_attempts,
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            exceptions=config.retryable_exceptions,
        )

    # 默认配置
    config = RetryConfig()
    return retry_with_exponential_backoff(
        max_attempts=config.max_attempts,
        base_delay=config.base_delay,
        max_delay=config.max_delay,
        exceptions=config.retryable_exceptions,
    )


def async_retry(config: RetryConfig | None = None):
    """函数文档字符串"""
    pass  # 添加pass语句
    """通用的异步重试装饰器"""
    if config is None:
        config = RetryConfig()

    return async_retry_with_exponential_backoff(
        max_attempts=config.max_attempts,
        base_delay=config.base_delay,
        max_delay=config.max_delay,
    )


# 导出别名
retry_sync = retry
retry_async = async_retry


class CircuitState:
    """类文档字符串"""

    pass  # 添加pass语句
    """熔断器状态枚举"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """类文档字符串"""

    pass  # 添加pass语句
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
