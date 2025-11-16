"""
重试机制实现
Retry Mechanism Implementation
"""

import asyncio
import time
from collections.abc import Callable
from enum import Enum
from functools import wraps


class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = None,
        initial_delay: float = None,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
        **kwargs,
    ):
        self.max_attempts = max_attempts

        # 支持delay作为initial_delay的别名
        if delay is not None:
            self.initial_delay = delay
            self.delay = delay
        elif initial_delay is not None:
            self.initial_delay = initial_delay
            self.delay = initial_delay
        else:
            self.initial_delay = 1.0
            self.delay = 1.0

        # 设置其他参数
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions

        # 支持其他可能的参数
        for key, value in kwargs.items():
            setattr(self, key, value)

        # 验证参数
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")


class BackoffStrategy:
    """退避策略基类"""

    def __init__(self, initial_delay: float = 1.0):
        self.initial_delay = initial_delay

    def get_delay(self, attempt: int) -> float:
        """获取第attempt次重试的延迟时间"""
        return self.initial_delay


class FixedBackoffStrategy(BackoffStrategy):
    """固定退避策略"""

    def __init__(self, delay: float = 1.0):
        super().__init__(delay)
        self.delay = delay

    def get_delay(self, attempt: int) -> float:
        return self.delay


class LinearBackoffStrategy(BackoffStrategy):
    """线性退避策略"""

    def __init__(self, initial_delay: float = 1.0, increment: float = 0.5):
        super().__init__(initial_delay)
        self.increment = increment

    def get_delay(self, attempt: int) -> float:
        return self.initial_delay + (attempt - 1) * self.increment


class ExponentialBackoffStrategy(BackoffStrategy):
    """指数退避策略"""

    def __init__(self, initial_delay: float = 1.0, multiplier: float = 2.0):
        super().__init__(initial_delay)
        self.multiplier = multiplier

    def get_delay(self, attempt: int) -> float:
        return self.initial_delay * (self.multiplier ** (attempt - 1))


class PolynomialBackoffStrategy(BackoffStrategy):
    """多项式退避策略"""

    def __init__(self, initial_delay: float = 1.0, exponent: float = 2.0):
        super().__init__(initial_delay)
        self.exponent = exponent

    def get_delay(self, attempt: int) -> float:
        return self.initial_delay * (attempt**self.exponent)


class CircuitBreaker:
    """熔断器"""

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

    def __call__(self, func: Callable) -> Callable:
        """装饰器语法糖"""
        return self.wrap_function(func)

    def wrap_function(self, func: Callable) -> Callable:
        """包装函数"""
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._call_async(func, *args, **kwargs)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._call_sync(func, *args, **kwargs)

            return sync_wrapper

    async def _call_async(self, func: Callable, *args, **kwargs):
        """异步调用"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _call_sync(self, func: Callable, *args, **kwargs):
        """同步调用"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


def retry(
    max_attempts: int = 3,
    delay: float = None,
    initial_delay: float = None,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    strategy: BackoffStrategy | None = None,
):
    """重试装饰器

    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（向后兼容）
        initial_delay: 初始延迟时间
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        strategy: 退避策略
    """
    # 支持delay作为initial_delay的别名
    if delay is not None:
        initial_delay = delay
    elif initial_delay is None:
        initial_delay = 1.0

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            return _retry_async(
                func=func,
                max_attempts=max_attempts,
                delay=delay,
                backoff_factor=backoff_factor,
                exceptions=exceptions,
                strategy=strategy,
            )
        else:
            return _retry_sync(
                func=func,
                max_attempts=max_attempts,
                delay=delay,
                backoff_factor=backoff_factor,
                exceptions=exceptions,
                strategy=strategy,
            )

    return decorator


def retry_sync(
    max_attempts: int = 3,
    delay: float = None,
    initial_delay: float = None,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    strategy: BackoffStrategy | None = None,
):
    """同步重试装饰器"""
    # 支持delay作为initial_delay的别名
    if delay is not None:
        initial_delay = delay
    elif initial_delay is None:
        initial_delay = 1.0

    def decorator(func: Callable) -> Callable:
        return _retry_sync(
            func=func,
            max_attempts=max_attempts,
            delay=initial_delay,
            backoff_factor=backoff_factor,
            exceptions=exceptions,
            strategy=strategy,
        )

    return decorator


def retry_async(
    max_attempts: int = 3,
    delay: float = None,
    initial_delay: float = None,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    strategy: BackoffStrategy | None = None,
):
    """异步重试装饰器"""
    # 支持delay作为initial_delay的别名
    if delay is not None:
        initial_delay = delay
    elif initial_delay is None:
        initial_delay = 1.0

    def decorator(func: Callable) -> Callable:
        return _retry_async(
            func=func,
            max_attempts=max_attempts,
            delay=initial_delay,
            backoff_factor=backoff_factor,
            exceptions=exceptions,
            strategy=strategy,
        )

    return decorator


def _retry_sync(
    func: Callable,
    max_attempts: int,
    delay: float,
    backoff_factor: float,
    exceptions: tuple,
    strategy: BackoffStrategy | None,
) -> Callable:
    """同步重试实现"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None

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
                    sleep_time = delay * (backoff_factor ** (attempt - 1))

                time.sleep(sleep_time)

        raise last_exception

    return wrapper


def _retry_async(
    func: Callable,
    max_attempts: int,
    delay: float,
    backoff_factor: float,
    exceptions: tuple,
    strategy: BackoffStrategy | None,
) -> Callable:
    """异步重试实现"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                last_exception = e

                if attempt == max_attempts:
                    break

                # 计算延迟时间
                if strategy:
                    sleep_time = strategy.get_delay(attempt)
                else:
                    sleep_time = delay * (backoff_factor ** (attempt - 1))

                await asyncio.sleep(sleep_time)

        raise last_exception

    return wrapper
