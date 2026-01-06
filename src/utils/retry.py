"""
连接重试装饰器 - 为数据库和 Redis 连接提供自动重试功能

支持同步和异步函数的自动重试，具有指数退避策略。
"""

import asyncio
from collections.abc import Callable
import functools
import logging
import time
from typing import ParamSpec, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential: bool = True,
        exceptions: tuple = (ConnectionError, TimeoutError),
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential = exponential
        self.exceptions = exceptions


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential: bool = True,
    exceptions: tuple | None = None,
) -> Callable:
    """连接重试装饰器

    Args:
        max_attempts: 最大重试次数（默认：3）
        base_delay: 基础延迟时间，秒（默认：1.0）
        max_delay: 最大延迟时间，秒（默认：30.0）
        exponential: 是否使用指数退避（默认：True）
        exceptions: 需要重试的异常类型（默认：ConnectionError, TimeoutError）

    Returns:
        装饰器函数

    Examples:
        >>> @with_retry(max_attempts=5, base_delay=2.0)
        ... def fetch_data():
        ...     return requests.get("https://api.example.com")

        >>> @with_retry()
        ... async def async_connect():
        ...     return await asyncpg.connect(...)
    """
    if exceptions is None:
        exceptions = (ConnectionError, TimeoutError, OSError)

    config = RetryConfig(max_attempts, base_delay, max_delay, exponential, exceptions)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.exceptions as e:
                    if attempt == config.max_attempts - 1:
                        logger.error(f"函数 {func.__name__} 达到最大重试次数 ({config.max_attempts}) 后失败: {e}")
                        raise

                    delay = _calculate_delay(attempt, config.base_delay, config.max_delay, config.exponential)
                    logger.warning(
                        f"函数 {func.__name__} 执行失败 ({attempt + 1}/{config.max_attempts}): {e}. "
                        f"{delay:.1f}秒后重试..."
                    )
                    await asyncio.sleep(delay)
            raise RuntimeError(f"最大重试次数 ({config.max_attempts}) 已用尽")

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.exceptions as e:
                    if attempt == config.max_attempts - 1:
                        logger.error(f"函数 {func.__name__} 达到最大重试次数 ({config.max_attempts}) 后失败: {e}")
                        raise

                    delay = _calculate_delay(attempt, config.base_delay, config.max_delay, config.exponential)
                    logger.warning(
                        f"函数 {func.__name__} 执行失败 ({attempt + 1}/{config.max_attempts}): {e}. "
                        f"{delay:.1f}秒后重试..."
                    )
                    time.sleep(delay)
            raise RuntimeError(f"最大重试次数 ({config.max_attempts}) 已用尽")

        # 根据函数是否为协程函数选择包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _calculate_delay(attempt: int, base_delay: float, max_delay: float, exponential: bool) -> float:
    """计算重试延迟时间

    Args:
        attempt: 当前尝试次数（从0开始）
        base_delay: 基础延迟时间
        max_delay: 最大延迟时间
        exponential: 是否使用指数退避

    Returns:
        延迟时间（秒）
    """
    if exponential:
        # 指数退避：base_delay * 2^attempt
        delay = base_delay * (2**attempt)
    else:
        # 固定延迟
        delay = base_delay

    return min(delay, max_delay)


# === 便捷函数 ===


def retry_on_connection_error(max_attempts: int = 3) -> Callable:
    """仅在连接错误时重试的装饰器

    Args:
        max_attempts: 最大重试次数

    Returns:
        装饰器函数

    Examples:
        >>> @retry_on_connection_error(max_attempts=5)
        ... def connect_db():
        ...     return psycopg2.connect(...)
    """
    return with_retry(
        max_attempts=max_attempts,
        exceptions=(ConnectionError, OSError),
    )


def retry_on_timeout(max_attempts: int = 3) -> Callable:
    """仅在超时时重试的装饰器

    Args:
        max_attempts: 最大重试次数

    Returns:
        装饰器函数

    Examples:
        >>> @retry_on_timeout(max_attempts=5)
        ... def fetch_with_timeout():
        ...     return requests.get(url, timeout=5)
    """
    return with_retry(
        max_attempts=max_attempts,
        exceptions=(TimeoutError,),
    )


# === 数据库特定装饰器 ===


def retry_db_connection(
    max_attempts: int = 3,
    base_delay: float = 2.0,
) -> Callable:
    """数据库连接重试装饰器

    专门用于数据库连接的重试，具有更长的默认延迟时间。

    Args:
        max_attempts: 最大重试次数（默认：3）
        base_delay: 基础延迟时间，秒（默认：2.0）

    Returns:
        装饰器函数

    Examples:
        >>> @retry_db_connection(max_attempts=5)
        ... def get_db_connection():
        ...     return psycopg2.connect(...)
    """
    import psycopg2

    return with_retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        exceptions=(psycopg2.Error, ConnectionError, OSError),
    )


def retry_redis_connection(
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> Callable:
    """Redis 连接重试装饰器

    专门用于 Redis 连接的重试。

    Args:
        max_attempts: 最大重试次数（默认：3）
        base_delay: 基础延迟时间，秒（默认：1.0）

    Returns:
        装饰器函数

    Examples:
        >>> @retry_redis_connection(max_attempts=5)
        ... def get_redis_client():
        ...     return redis.Redis(...)
    """
    import redis

    return with_retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        exceptions=(redis.ConnectionError, ConnectionError, OSError),
    )
