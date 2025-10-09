"""
重试配置
Retry Configuration
"""

from typing import Tuple, Type

from .strategies import ExponentialBackoffStrategy


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

        # 创建默认的退避策略
        self.backoff_strategy = ExponentialBackoffStrategy(
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter
        )