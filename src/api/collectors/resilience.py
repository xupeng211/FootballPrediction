#!/usr/bin/env python3
"""
V36.0 重试和并发控制工具
=======================
工业级弹性机制，增强 API 采集的可靠性

核心功能:
1. 指数退避重试装饰器
2. 并发限流器
3. 速率限制器

作者: ML Architect
日期: 2025-12-28
Phase: Production-Grade Refactor
Version: V36.0
"""

import asyncio
import functools
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimiter:
    """
    速率限制器

    防止被 API 提供方封禁 IP
    """

    def __init__(self, max_requests: int = 10, time_window: float = 1.0):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        获取许可（如果超过速率限制则等待）

        使用 Token Bucket 算法
        """
        async with self._lock:
            now = time.time()

            # 清理过期请求记录
            self.requests = [t for t in self.requests if now - t < self.time_window]

            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                # 计算需要等待的时间
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    logger.debug(f"⏳ 速率限制: 等待 {sleep_time:.2f} 秒")
                    await asyncio.sleep(sleep_time)

                    # 清理过期请求
                    now = time.time()
                    self.requests = [t for t in self.requests if now - t < self.time_window]

            # 记录本次请求
            self.requests.append(now)


class ConcurrentLimiter:
    """
    并发限制器

    控制同时进行的最大并发数
    """

    def __init__(self, max_concurrent: int = 5):
        """
        初始化并发限制器

        Args:
            max_concurrent: 最大并发数
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent

    async def __aenter__(self):
        """进入上下文（获取许可）"""
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文（释放许可）"""
        self.semaphore.release()


def retry_with_exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[type] | None = None,
):
    """
    指数退避重试装饰器

    Args:
        max_attempts: 最大尝试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        jitter: 是否添加随机抖动（防止雷击效应）
        retry_on: 需要重试的异常类型

    Example:
        @retry_with_exponential_backoff(max_attempts=3, retry_on=(aiohttp.ClientError,))
        async def fetch_data():
            ...
    """

    if retry_on is None:
        # 默认重试所有异常
        retry_on = (Exception,)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    # 最后一次尝试失败，不再重试
                    if attempt == max_attempts - 1:
                        logger.error(f"❌ 重试失败: {func.__name__}() (尝试 {attempt + 1}/{max_attempts})")
                        raise

                    # 计算延迟时间（指数退避 + 抖动）
                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"⚠️  {func.__name__}() 失败 (尝试 {attempt + 1}/{max_attempts}): {e} | {delay:.2f}秒后重试..."
                    )

                    await asyncio.sleep(delay)

            # 理论上不会到达这里
            raise last_exception  # type: ignore

        return wrapper

    return decorator


class CircuitBreaker:
    """
    熔断器模式

    当连续失败超过阈值时，暂时停止请求，避免雪崩效应
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """
        初始化熔断器

        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时（秒）
            expected_exception: 预期的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def is_open(self) -> bool:
        """检查熔断器是否打开"""
        if self.state == "OPEN":
            # 检查是否可以尝试恢复
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("🔄 熔断器进入半开状态，尝试恢复...")
                return False
            return True
        return False

    def record_success(self) -> None:
        """记录成功"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("✅ 熔断器已恢复到关闭状态")

    def record_failure(self, exc: Exception) -> None:
        """记录失败"""
        if isinstance(exc, self.expected_exception):
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                if self.state != "OPEN":
                    self.state = "OPEN"
                    logger.error(
                        f"🚨 熔断器已打开！连续失败 {self.failure_count} 次，将在 {self.recovery_timeout} 秒后尝试恢复"
                    )
