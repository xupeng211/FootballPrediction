"""
重试策略和退避算法
Retry Strategies and Backoff Algorithms
"""

import random
from abc import ABC, abstractmethod
from typing import Optional


class BackoffStrategy(ABC):
    """
    退避策略基类 / Base class for backoff strategies

    所有退避策略都应继承此类并实现 get_delay 方法。
    All backoff strategies should inherit from this class and implement the get_delay method.
    """

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """
        获取重试延迟时间 / Get retry delay time

        Args:
            attempt (int): 当前尝试次数 / Current attempt number (0-based)

        Returns:
            float: 延迟时间（秒） / Delay time in seconds
        """
        pass


class FixedBackoffStrategy(BackoffStrategy):
    """
    固定退避策略 / Fixed backoff strategy

    使用固定的延迟时间进行重试。
    Uses a fixed delay time for retries.

    Example:
        ```python
        from src.utils.retry.strategies import FixedBackoffStrategy

        # 创建固定退避策略
        strategy = FixedBackoffStrategy(delay=2.0)

        # 获取延迟时间
        delay = strategy.get_delay(attempt=0)  # 返回 2.0
        delay = strategy.get_delay(attempt=1)  # 返回 2.0
        ```
    """

    def __init__(self, delay: float):
        """
        初始化固定退避策略 / Initialize fixed backoff strategy

        Args:
            delay (float): 固定延迟时间（秒） / Fixed delay time in seconds
        """
        self.delay = delay

    def get_delay(self, attempt: int) -> float:
        """获取固定延迟时间 / Get fixed delay time"""
        return self.delay


class LinearBackoffStrategy(BackoffStrategy):
    """
    线性退避策略 / Linear backoff strategy

    每次重试的延迟时间线性增加。
    The delay time increases linearly with each retry.

    Example:
        ```python
        from src.utils.retry.strategies import LinearBackoffStrategy

        # 创建线性退避策略
        strategy = LinearBackoffStrategy(base_delay=1.0, increment=0.5)

        # 获取延迟时间
        delay = strategy.get_delay(attempt=0)  # 返回 1.0
        delay = strategy.get_delay(attempt=1)  # 返回 1.5
        delay = strategy.get_delay(attempt=2)  # 返回 2.0
        ```
    """

    def __init__(self, base_delay: float = 1.0, increment: float = 0.5, max_delay: Optional[float] = None):
        """
        初始化线性退避策略 / Initialize linear backoff strategy

        Args:
            base_delay (float): 基础延迟时间（秒） / Base delay time in seconds
            increment (float): 每次增加的延迟时间（秒） / Increment in delay time per attempt
            max_delay (Optional[float]): 最大延迟时间（秒） / Maximum delay time in seconds
        """
        self.base_delay = base_delay
        self.increment = increment
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """获取线性增长的延迟时间 / Get linearly increasing delay time"""
        delay = self.base_delay + (attempt * self.increment)
        if self.max_delay is not None:
            delay = min(delay, self.max_delay)
        return delay


class ExponentialBackoffStrategy(BackoffStrategy):
    """
    指数退避策略 / Exponential backoff strategy

    使用指数退避算法计算重试延迟时间。
    Uses exponential backoff algorithm to calculate retry delay time.

    Example:
        ```python
        from src.utils.retry.strategies import ExponentialBackoffStrategy

        # 创建指数退避策略
        strategy = ExponentialBackoffStrategy(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=True
        )

        # 获取延迟时间
        delay = strategy.get_delay(attempt=0)  # 返回约 1.0
        delay = strategy.get_delay(attempt=1)  # 返回约 2.0
        delay = strategy.get_delay(attempt=2)  # 返回约 4.0
        ```
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        exponential_base: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        """
        初始化指数退避策略 / Initialize exponential backoff strategy

        Args:
            base_delay (float): 基础延迟时间（秒） / Base delay time in seconds
            exponential_base (float): 指数退避基数 / Exponential backoff base
            max_delay (float): 最大延迟时间（秒） / Maximum delay time in seconds
            jitter (bool): 是否启用抖动 / Whether to enable jitter
        """
        self.base_delay = base_delay
        self.exponential_base = exponential_base
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """获取指数增长的延迟时间 / Get exponentially increasing delay time"""
        # 计算基础延迟
        delay = self.base_delay * (self.exponential_base ** attempt)

        # 限制最大延迟
        delay = min(delay, self.max_delay)

        # 添加抖动
        if self.jitter:
            # 在 50% 到 100% 之间随机化
            delay *= 0.5 + random.random() * 0.5

        return delay


class PolynomialBackoffStrategy(BackoffStrategy):
    """
    多项式退避策略 / Polynomial backoff strategy

    使用多项式函数计算重试延迟时间。
    Uses polynomial function to calculate retry delay time.

    Example:
        ```python
        from src.utils.retry.strategies import PolynomialBackoffStrategy

        # 创建多项式退避策略
        strategy = PolynomialBackoffStrategy(
            base_delay=1.0,
            power=2.0,
            max_delay=60.0
        )

        # 获取延迟时间
        delay = strategy.get_delay(attempt=0)  # 返回 1.0
        delay = strategy.get_delay(attempt=1)  # 返回 2.0
        delay = strategy.get_delay(attempt=2)  # 返回 5.0
        ```
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        power: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = False
    ):
        """
        初始化多项式退避策略 / Initialize polynomial backoff strategy

        Args:
            base_delay (float): 基础延迟时间（秒） / Base delay time in seconds
            power (float): 多项式幂次 / Polynomial power
            max_delay (float): 最大延迟时间（秒） / Maximum delay time in seconds
            jitter (bool): 是否启用抖动 / Whether to enable jitter
        """
        self.base_delay = base_delay
        self.power = power
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """获取多项式增长的延迟时间 / Get polynomially increasing delay time"""
        # 计算基础延迟
        delay = self.base_delay * ((attempt + 1) ** self.power)

        # 限制最大延迟
        delay = min(delay, self.max_delay)

        # 添加抖动
        if self.jitter:
            # 在 90% 到 110% 之间随机化
            delay *= 0.9 + random.random() * 0.2

        return delay