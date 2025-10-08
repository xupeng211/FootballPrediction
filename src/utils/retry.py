"""
重试机制 / Retry Mechanism

提供带指数退避和抖动的重试功能，用于处理外部服务调用的临时故障。

Provides retry functionality with exponential backoff and jitter for handling transient failures in external service calls.

主要类 / Main Classes:
    RetryConfig: 重试配置 / Retry configuration
    CircuitBreaker: 熔断器实现 / Circuit breaker implementation
    CircuitState: 熔断器状态枚举 / Circuit breaker state enumeration

主要装饰器 / Main Decorators:
    retry: 重试装饰器 / Retry decorator

使用示例 / Usage Example:
    ```python
    from src.utils.retry import retry, RetryConfig

    # 配置重试策略
    config = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True
    )

    # 应用重试装饰器
    @retry(config)
    async def fetch_data_from_api():
        # 可能失败的外部调用
        response = await http_client.get("https://api.example.com/data")
        return response.json()

    # 调用函数（自动重试）
    data = await fetch_data_from_api()
    ```

环境变量 / Environment Variables:
    RETRY_MAX_ATTEMPTS: 最大重试次数，默认3 / Maximum retry attempts, default 3
    RETRY_BASE_DELAY: 基础延迟秒数，默认1.0 / Base delay in seconds, default 1.0
    RETRY_MAX_DELAY: 最大延迟秒数，默认60.0 / Maximum delay in seconds, default 60.0
"""

import asyncio
import functools
import logging
import random
import time
from enum import Enum
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, cast

T = TypeVar("T")

logger = logging.getLogger(__name__)


class RetryConfig:
    """
    重试配置 / Retry Configuration

    定义重试机制的配置参数，包括最大尝试次数、延迟策略等。
    Defines configuration parameters for retry mechanism, including maximum attempts, delay strategy, etc.

    Attributes:
        max_attempts (int): 最大尝试次数 / Maximum attempts
        base_delay (float): 基础延迟（秒） / Base delay (seconds)
        max_delay (float): 最大延迟（秒） / Maximum delay (seconds)
        exponential_base (float): 指数退避基数 / Exponential backoff base
        jitter (bool): 是否启用抖动 / Whether to enable jitter
        retryable_exceptions (tuple): 可重试的异常类型 / Retryable exception types

    Example:
        ```python
        from src.utils.retry import RetryConfig

        # 创建数据库重试配置
        db_config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )

        # 创建API重试配置
        api_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=60.0,
            retryable_exceptions=(ConnectionError, TimeoutError, ValueError)
        )
        ```
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        初始化重试配置 / Initialize retry configuration

        Args:
            max_attempts (int): 最大尝试次数 / Maximum attempts
                Defaults to 3
            base_delay (float): 基础延迟（秒） / Base delay (seconds)
                Defaults to 1.0
            max_delay (float): 最大延迟（秒） / Maximum delay (seconds)
                Defaults to 60.0
            exponential_base (float): 指数退避基数 / Exponential backoff base
                Defaults to 2.0
            jitter (bool): 是否启用抖动 / Whether to enable jitter
                Defaults to True
            retryable_exceptions (Tuple[Type[Exception], ...]): 可重试的异常类型 / Retryable exception types
                Defaults to (Exception,) - 所有异常都可重试 / All exceptions are retryable
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


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

                    # 计算延迟 / Calculate delay
                    delay = config.base_delay * (config.exponential_base**attempt)
                    if delay > config.max_delay:
                        delay = config.max_delay

                    # 添加抖动 / Add jitter
                    if config.jitter:
                        delay *= 0.5 + random.random() * 0.5

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

                    # 计算延迟 / Calculate delay
                    delay = config.base_delay * (config.exponential_base**attempt)
                    if delay > config.max_delay:
                        delay = config.max_delay

                    # 添加抖动 / Add jitter
                    if config.jitter:
                        delay *= 0.5 + random.random() * 0.5

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


class CircuitState(Enum):
    """
    熔断器状态枚举 / Circuit Breaker State Enumeration

    定义熔断器的三种状态。
    Defines the three states of a circuit breaker.

    States:
        CLOSED: 熔断器关闭，允许请求通过 / Circuit breaker closed, allowing requests
        OPEN: 熔断器打开，阻止请求 / Circuit breaker open, blocking requests
        HALF_OPEN: 熔断器半开，试探性允许请求 / Circuit breaker half-open, tentatively allowing requests
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    熔断器实现 / Circuit Breaker Implementation

    实现熔断器模式，防止级联故障。
    Implements the circuit breaker pattern to prevent cascading failures.

    Attributes:
        failure_threshold (int): 失败阈值 / Failure threshold
        recovery_timeout (float): 恢复超时（秒） / Recovery timeout (seconds)
        retry_timeout (float): 重试超时（秒） / Retry timeout (seconds)
        failure_count (int): 失败计数 / Failure count
        last_failure_time (Optional[float]): 最后失败时间 / Last failure time
        state (CircuitState): 当前状态 / Current state
        lock (asyncio.Lock): 异步锁 / Async lock

    Example:
        ```python
        from src.utils.retry import CircuitBreaker

        # 创建熔断器
        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            retry_timeout=30.0
        )

        # 使用熔断器调用函数
        try:
            result = await circuit_breaker.call(external_service_call, arg1, arg2)
        except Exception as e:
            print(f"服务调用被熔断: {e}")
        ```

    Note:
        熔断器在OPEN状态下会阻止所有请求，防止对已知故障的服务继续调用。
        The circuit breaker blocks all requests in OPEN state to prevent continued calls to known faulty services.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        retry_timeout: float = 30.0,
    ):
        """
        初始化熔断器 / Initialize circuit breaker

        Args:
            failure_threshold (int): 失败阈值，超过此值熔断器打开 /
                                   Failure threshold, circuit breaker opens after this many failures
                Defaults to 5
            recovery_timeout (float): 恢复超时（秒），熔断器打开后等待此时间尝试恢复 /
                                    Recovery timeout (seconds), time to wait before attempting recovery after opening
                Defaults to 60.0
            retry_timeout (float): 重试超时（秒），半开状态下等待此时间再次尝试 /
                                 Retry timeout (seconds), time to wait in half-open state before retrying
                Defaults to 30.0
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.retry_timeout = retry_timeout

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        使用熔断器调用函数 / Call function with circuit breaker

        Args:
            func (Callable): 要调用的函数 / Function to call
            *args: 函数参数 / Function arguments
            **kwargs: 函数关键字参数 / Function keyword arguments

        Returns:
            Any: 函数调用结果 / Function call result

        Raises:
            Exception: 当熔断器打开时抛出异常 / Raised when circuit breaker is open
            Exception: 当函数调用失败时抛出异常 / Raised when function call fails

        Example:
            ```python
            from src.utils.retry import CircuitBreaker

            circuit_breaker = CircuitBreaker()

            async def external_api_call():
                # 外部API调用
                pass

            try:
                result = await circuit_breaker.call(external_api_call)
                print(f"调用成功: {result}")
            except Exception as e:
                print(f"调用失败或被熔断: {e}")
            ```
        """
        async with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception("熔断器已打开 / Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except Exception:
                await self._on_failure()
                raise

    async def _on_success(self):
        """处理成功调用 / Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    async def _on_failure(self):
        """处理失败调用 / Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """
        检查是否应该尝试重置熔断器 / Check if circuit should attempt to reset

        Returns:
            bool: 如果应该尝试重置则返回True / True if should attempt reset
        """
        if self.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.last_failure_time
        timeout = (
            self.retry_timeout
            if self.state == CircuitState.HALF_OPEN
            else self.recovery_timeout
        )
        return time_since_failure >= timeout
