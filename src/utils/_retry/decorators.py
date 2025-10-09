"""
重试装饰器
Retry Decorators
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Optional

from .config import RetryConfig

logger = logging.getLogger(__name__)


def retry(
    config: RetryConfig, on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    重试装饰器 / Retry Decorator

    为函数提供带指数退避和抖动的重试机制。
    Provides retry mechanism with exponential backoff and jitter for functions.

    Args:
        config (RetryConfig): 重试配置 / Retry configuration
        on_retry (Optional[Callable[[int, Exception], None]]): 重试回调函数 / Retry callback function
            在每次重试时调用，参数为尝试次数和异常 / Called on each retry with attempt number and exception
            Defaults to None

    Returns:
        Callable: 装饰器函数 / Decorator function

    Example:
        ```python
        from src.utils.retry import retry, RetryConfig

        # 配置重试策略
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )

        # 应用重试装饰器到异步函数
        @retry(config)
        async def fetch_user_data(user_id: int):
            # 可能失败的异步操作
            response = await http_client.get(f"https://api.example.com/users/{user_id}")
            return response.json()

        # 应用重试装饰器到同步函数
        @retry(config)
        def save_to_database(data: dict):
            # 可能失败的同步操作
            db_session.execute("INSERT INTO users VALUES (:data)", data)
            db_session.commit()

        # 使用带回调的重试装饰器
        def retry_callback(attempt: int, error: Exception):
            print(f"第 {attempt} 次重试失败: {error}")

        @retry(config, on_retry=retry_callback)
        async def critical_operation():
            # 关键操作
            pass
        ```

    Note:
        装饰器自动检测函数是同步还是异步，并应用相应的重试逻辑。
        The decorator automatically detects if the function is synchronous or asynchronous
        and applies the appropriate retry logic.
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """异步函数重试包装器 / Async function retry wrapper"""
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    # 如果这是最后一次尝试，重新抛出异常
                    # If this is the last attempt, re-raise the exception
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"达到最大重试次数 {config.max_attempts} for {func.__name__}: {e}"
                        )
                        raise

                    # 使用退避策略计算延迟
                    delay = config.backoff_strategy.get_delay(attempt)

                    logger.warning(
                        f"第 {attempt + 1} 次尝试失败 for {func.__name__}: {e}. "
                        f"将在 {delay:.2f} 秒后重试... / "
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )

                    # 调用重试回调函数（如果提供） / Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)

                    # 等待重试 / Wait before retry
                    await asyncio.sleep(delay)

            # 这应该永远不会到达，因为上面会重新抛出异常
            # This should never be reached due to the re-raise above
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """同步函数重试包装器 / Sync function retry wrapper"""
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    # 如果这是最后一次尝试，重新抛出异常
                    # If this is the last attempt, re-raise the exception
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"达到最大重试次数 {config.max_attempts} for {func.__name__}: {e}"
                        )
                        raise

                    # 使用退避策略计算延迟
                    delay = config.backoff_strategy.get_delay(attempt)

                    logger.warning(
                        f"第 {attempt + 1} 次尝试失败 for {func.__name__}: {e}. "
                        f"将在 {delay:.2f} 秒后重试... / "
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )

                    # 调用重试回调函数（如果提供） / Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)

                    # 等待重试 / Wait before retry
                    time.sleep(delay)

            # 这应该永远不会到达，因为上面会重新抛出异常
            # This should never be reached due to the re-raise above
            raise last_exception

        # 根据函数类型返回适当的包装器
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def retry_async(config: RetryConfig, on_retry: Optional[Callable[[int, Exception], None]] = None):
    """
    异步重试装饰器（专门用于异步函数） / Async retry decorator (for async functions only)

    Args:
        config (RetryConfig): 重试配置 / Retry configuration
        on_retry (Optional[Callable[[int, Exception], None]]): 重试回调函数 / Retry callback function

    Returns:
        Callable: 装饰器函数 / Decorator function

    Example:
        ```python
        from src.utils.retry.decorators import retry_async, RetryConfig

        config = RetryConfig(max_attempts=3)

        @retry_async(config)
        async def async_function():
            # 异步操作
            pass
        ```
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        logger.error(f"达到最大重试次数 {config.max_attempts} for {func.__name__}: {e}")
                        raise

                    delay = config.backoff_strategy.get_delay(attempt)

                    logger.warning(
                        f"第 {attempt + 1} 次尝试失败 for {func.__name__}: {e}. "
                        f"将在 {delay:.2f} 秒后重试..."
                    )

                    if on_retry:
                        on_retry(attempt + 1, e)

                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def retry_sync(config: RetryConfig, on_retry: Optional[Callable[[int, Exception], None]] = None):
    """
    同步重试装饰器（专门用于同步函数） / Sync retry decorator (for sync functions only)

    Args:
        config (RetryConfig): 重试配置 / Retry configuration
        on_retry (Optional[Callable[[int, Exception], None]]): 重试回调函数 / Retry callback function

    Returns:
        Callable: 装饰器函数 / Decorator function

    Example:
        ```python
        from src.utils.retry.decorators import retry_sync, RetryConfig

        config = RetryConfig(max_attempts=3)

        @retry_sync(config)
        def sync_function():
            # 同步操作
            pass
        ```
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        logger.error(f"达到最大重试次数 {config.max_attempts} for {func.__name__}: {e}")
                        raise

                    delay = config.backoff_strategy.get_delay(attempt)

                    logger.warning(
                        f"第 {attempt + 1} 次尝试失败 for {func.__name__}: {e}. "
                        f"将在 {delay:.2f} 秒后重试..."
                    )

                    if on_retry:
                        on_retry(attempt + 1, e)

                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator